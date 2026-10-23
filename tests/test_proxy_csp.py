"""Confianza explícita de proxies y CSP de los documentos públicos, sin red externa."""
import base64
import hashlib
import re

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.requests import Request

from app.config import Settings, get_settings
from app.main import app, csp_archivo_publico, csp_publica, hashes_scripts_publicos
from app.services.limites import Limitador, ip_cliente


def peticion(peer="192.0.2.10", headers=()):
    return Request({
        "type": "http", "method": "GET", "scheme": "https", "path": "/api/redactar",
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers],
        "client": (peer, 443), "server": ("memorialista.test", 443),
    })


@pytest.fixture
def proxy(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "PROXY_IPS_CONFIABLES", "")
    monkeypatch.setattr(settings, "PROXIES_CONFIABLES", 0)
    monkeypatch.setattr(settings, "IP_CABECERA_CONFIABLE", "")
    return settings


def test_default_ignores_forged_headers_and_render_environment(proxy, monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    request = peticion(headers=(("X-Forwarded-For", "203.0.113.20"), ("True-Client-IP", "203.0.113.21")))
    assert ip_cliente(request) == "192.0.2.10"


def test_spoofed_headers_do_not_reset_the_ip_quota(proxy, monkeypatch):
    monkeypatch.setattr(proxy, "LIMITE_ESTILO_HORA", 1)
    limitador = Limitador()
    limitador.verificar(peticion(headers=(("X-Forwarded-For", "203.0.113.20"),)), "estilo")
    with pytest.raises(HTTPException) as error:
        limitador.verificar(peticion(headers=(("X-Forwarded-For", "203.0.113.21"),)), "estilo")
    assert error.value.status_code == 429


def test_xff_checks_the_peer_and_counts_from_the_right(proxy, monkeypatch):
    monkeypatch.setattr(proxy, "PROXY_IPS_CONFIABLES", "10.0.0.0/24")
    monkeypatch.setattr(proxy, "PROXIES_CONFIABLES", 2)
    headers = (("X-Forwarded-For", "198.51.100.99, 203.0.113.20, 10.0.0.4"),)
    assert ip_cliente(peticion("10.0.0.5", headers)) == "203.0.113.20"
    # The exact same header cannot authorize an untrusted direct client.
    assert ip_cliente(peticion("192.0.2.10", headers)) == "192.0.2.10"


@pytest.mark.parametrize("values", [
    ("203.0.113.20",),                         # a configured hop is missing
    ("203.0.113.20, 192.0.2.4",),             # an intervening proxy is not trusted
    ("unknown, 10.0.0.4",),
    ("203.0.113.20:9000, 10.0.0.4",),
    ("203.0.113.20, fe80::1%eth0",),
    ("203.0.113.20, 10.0.0.4,",),
    ("203.0.113.20", "10.0.0.4"),            # ambiguous repeated headers
])
def test_bad_proxy_chains_fall_back_to_the_peer(proxy, monkeypatch, values):
    monkeypatch.setattr(proxy, "PROXY_IPS_CONFIABLES", "10.0.0.0/24")
    monkeypatch.setattr(proxy, "PROXIES_CONFIABLES", 2)
    assert ip_cliente(peticion("10.0.0.5", tuple(("X-Forwarded-For", value) for value in values))) == "10.0.0.5"


def test_dedicated_header_requires_a_trusted_peer_and_a_single_numeric_ip(proxy, monkeypatch):
    monkeypatch.setattr(proxy, "PROXY_IPS_CONFIABLES", "10.0.0.5/32")
    monkeypatch.setattr(proxy, "IP_CABECERA_CONFIABLE", "true-client-ip")
    assert ip_cliente(peticion("10.0.0.5", (("True-Client-IP", "203.0.113.20"),))) == "203.0.113.20"
    assert ip_cliente(peticion("192.0.2.10", (("True-Client-IP", "203.0.113.20"),))) == "192.0.2.10"
    for value in ("203.0.113.20, 203.0.113.21", "unknown", "https://203.0.113.20", "[2001:db8::1]:443"):
        assert ip_cliente(peticion("10.0.0.5", (("True-Client-IP", value),))) == "10.0.0.5"
    assert ip_cliente(peticion("10.0.0.5", (("True-Client-IP", "203.0.113.20"), ("True-Client-IP", "203.0.113.21")))) == "10.0.0.5"


def test_ipv6_and_mapped_ipv4_are_canonicalized(proxy, monkeypatch):
    assert ip_cliente(peticion("2001:0db8:0:0::1")) == "2001:db8::1"
    assert ip_cliente(peticion("::ffff:192.0.2.10")) == "192.0.2.10"
    assert ip_cliente(peticion("not-an-address")) == "desconocida"
    monkeypatch.setattr(proxy, "PROXY_IPS_CONFIABLES", "2001:db8:10::/64")
    monkeypatch.setattr(proxy, "PROXIES_CONFIABLES", 1)
    assert ip_cliente(peticion("2001:db8:10::1", (("X-Forwarded-For", "2001:0db8:20:0::2"),))) == "2001:db8:20::2"


@pytest.mark.parametrize("overrides", [
    {"PROXIES_CONFIABLES": 1},
    {"IP_CABECERA_CONFIABLE": "True-Client-IP"},
    {"PROXY_IPS_CONFIABLES": "0.0.0.0/0"},
    {"PROXY_IPS_CONFIABLES": "::/0"},
    {"PROXY_IPS_CONFIABLES": "not-a-network"},
    {"PROXY_IPS_CONFIABLES": "127.0.0.1", "IP_CABECERA_CONFIABLE": "x-forwarded-for"},
    {"PROXY_IPS_CONFIABLES": "127.0.0.1", "IP_CABECERA_CONFIABLE": "X-Real-IP\nInjected"},
    {"PROXY_IPS_CONFIABLES": "127.0.0.1", "IP_CABECERA_CONFIABLE": "X-Real-IP", "PROXIES_CONFIABLES": 1},
])
def test_invalid_proxy_configuration_fails_closed(overrides):
    values = {"PROXY_IPS_CONFIABLES": "", "PROXIES_CONFIABLES": 0, "IP_CABECERA_CONFIABLE": "", **overrides}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def directivas(policy):
    return {parts[0]: parts[1:] for item in policy.split(";") if (parts := item.strip().split())}


@pytest.fixture
def cliente_publico(monkeypatch):
    monkeypatch.setattr(get_settings(), "SUPABASE_URL", "https://project.supabase.test")
    monkeypatch.setattr(get_settings(), "SUPABASE_ANON_KEY", "public-test-key")
    return TestClient(app)


@pytest.mark.parametrize("path", ["/", "/asesor/", "/asesor/offline-shell.html", "/static/index.html", "/static/asesor/pwa/shell.html"])
def test_public_documents_only_allow_owned_resources(cliente_publico, path):
    response = cliente_publico.get(path)
    assert response.status_code == 200
    policy = directivas(response.headers["content-security-policy"])
    assert policy["connect-src"] == ["'self'"]
    assert policy["script-src"][0] == "'self'"
    assert all(source.startswith("'sha256-") for source in policy["script-src"][1:])
    assert policy["script-src-attr"] == ["'none'"]
    assert policy["object-src"] == ["'none'"]
    assert policy["frame-ancestors"] == ["'none'"]
    assert "'unsafe-inline'" not in policy["script-src"]
    assert "'unsafe-eval'" not in policy["script-src"]
    assert "supabase" not in response.headers["content-security-policy"]
    # Structured metadata injected by the server has its exact permitted hash.
    for match in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', response.text, re.S):
        digest = base64.b64encode(hashlib.sha256(match[1].encode()).digest()).decode()
        assert f"'sha256-{digest}'" in policy["script-src"]


@pytest.mark.parametrize("path", ["/login", "/auth/callback", "/static/login.html"])
def test_login_allows_only_the_configured_auth_origin(cliente_publico, path):
    response = cliente_publico.get(path)
    assert response.status_code == 200
    policy = directivas(response.headers["content-security-policy"])
    assert set(policy["connect-src"]) == {"'self'", "https://project.supabase.test", "wss://project.supabase.test"}
    assert policy["script-src"] == ["'self'"]
    assert policy["form-action"] == ["'self'"]
    assert "https://project.supabase.test" not in policy["script-src"]


@pytest.mark.parametrize("url", [
    "https://project.test; connect-src *", "https://project.test\n.evil.test",
    "https://user:password@project.test", "https://project.test:99999",
    "https://project.test/path", "https://project.test/?url=evil", "//project.test",
])
def test_malformed_auth_urls_cannot_expand_csp(monkeypatch, url):
    monkeypatch.setattr(get_settings(), "SUPABASE_URL", url)
    assert directivas(csp_publica(ingreso=True))["connect-src"] == ["'self'"]


def test_inline_hashes_match_browser_newlines_and_update_with_static_file(tmp_path):
    source = 'window.example = "<&>";\r\n'
    html = f'<script src="/known.js"></script><script>{source}</script>'
    digest = base64.b64encode(hashlib.sha256(source.replace("\r\n", "\n").encode()).digest()).decode()
    assert hashes_scripts_publicos(html) == (f"'sha256-{digest}'",)
    path = tmp_path / "public.html"
    path.write_text(html, encoding="utf-8")
    first = csp_archivo_publico(path)
    path.write_text('<script>window.example = "changed";</script>', encoding="utf-8")
    assert csp_archivo_publico(path) != first
    assert "'unsafe-inline'" not in directivas(csp_archivo_publico(path))["script-src"]


def test_csp_does_not_relax_the_professional_boundary(cliente_publico):
    for path in ("/app", "/generador"):
        response = cliente_publico.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"].startswith("/login")
        assert "no-store" in response.headers["cache-control"]
    assert cliente_publico.get("/auditor.js").status_code == 401
    assert cliente_publico.get("/api/catalogo", headers={"Authorization": "Bearer mock-owner"}).status_code == 401
    assert cliente_publico.get("/static/generador.html").status_code == 404


def test_existing_read_only_guide_policy_stays_strict(cliente_publico):
    response = cliente_publico.get("/plantillas/")
    assert response.status_code == 200
    policy = directivas(response.headers["content-security-policy"])
    assert policy["default-src"] == ["'none'"]
    assert "script-src" not in policy
