"""Frontera pública/privada: autenticación remota real sustituida solo en tests.

No hay un modo de autenticación de prueba en el producto. El proveedor HTTP
se sustituye con MockTransport para comprobar validación, cookies y controles.
"""
import asyncio
import base64
import json
import re
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.routers import auth, calculos, documents
from app.services import supabase_service
from app.services.sesiones import COOKIE_SESION

USER_ID = "11111111-1111-4111-8111-111111111111"
USER = {"id": USER_ID, "email": "abogada@example.test", "role": "authenticated", "is_anonymous": False}


def jwt(seconds=600, sub=USER_ID):
    def b64(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")
    return b64({"alg": "RS256", "typ": "JWT"}) + "." + b64({"exp": int(time.time()) + seconds, "sub": sub, "role": "authenticated"}) + ".test-signature"


@pytest.fixture
def auth_remote(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://project.supabase.test")
    monkeypatch.setattr(settings, "SUPABASE_ANON_KEY", "public-test-key")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "APP_BASE_URL", "")
    monkeypatch.setattr(settings, "AUTH_COOKIE_MAX_AGE_SECONDS", 3600)
    supabase_service._TOKEN_CACHE.clear()
    allowed = {}
    requests = []
    real_client = httpx.AsyncClient

    def handle(request):
        requests.append(request)
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        if request.url.path == "/auth/v1/user" and token in allowed:
            return httpx.Response(200, json=allowed[token])
        return httpx.Response(401, json={"message": "Invalid JWT"})

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handle)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(supabase_service.httpx, "AsyncClient", factory)
    yield allowed, requests
    supabase_service._TOKEN_CACHE.clear()


def test_public_health_and_configuration_never_expose_secrets(auth_remote):
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert set(response.json()) == {"status", "app", "version"}
    config = client.get("/api/auth/config").json()
    assert config["auth_requerido"] is True
    assert config["configurado"] is True
    assert config["callback_path"] == "/auth/callback"
    assert "SUPABASE_SERVICE_ROLE_KEY" not in json.dumps(config)
    assert "jwt_secret" not in json.dumps(config).lower()


PRIVATE_ENDPOINTS = sorted({
    (next(iter(sorted(route.methods - {"HEAD", "OPTIONS"}))), route.path)
    for route in [*auth.router.routes, *documents.router.routes, *calculos.router.routes]
    if getattr(route, "path", "").startswith("/api/")
    and route.path not in {"/api/health", "/api/auth/config", "/api/auth/sesion"}
    and getattr(route, "methods", None)
})


@pytest.mark.parametrize("method,path", PRIVATE_ENDPOINTS)
def test_every_professional_endpoint_rejects_anonymous_before_body_parsing(auth_remote, method, path):
    response = TestClient(app).request(method, path.replace("{tipo_id}", "tutela"), json={})
    assert response.status_code == 401, (method, path, response.text)
    assert response.headers["cache-control"].startswith("private, no-store")


@pytest.mark.parametrize("token", ["mock-admin-token", "test-owner-token", "anything", "", "Bearer mock-x-token"])
def test_legacy_or_forged_non_jwt_tokens_never_authenticate(auth_remote, token):
    response = TestClient(app).get("/api/catalogo", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 401
    assert not auth_remote[1]


def test_payload_with_exp_is_not_proof_of_authentication(auth_remote):
    token = jwt()
    assert asyncio.run(supabase_service.validar_token_supabase(token)) is None
    assert len(auth_remote[1]) == 1
    assert not supabase_service._TOKEN_CACHE


def test_expired_jwt_rejected_without_network_even_if_provider_would_allow(auth_remote):
    token = jwt(-20)
    auth_remote[0][token] = USER
    assert asyncio.run(supabase_service.validar_token_supabase(token)) is None
    assert auth_remote[1] == []


def test_anonymous_supabase_users_are_not_professional_logins(auth_remote):
    token = jwt()
    auth_remote[0][token] = {**USER, "is_anonymous": True}
    assert TestClient(app).get("/api/catalogo", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_unconfigured_development_is_closed(monkeypatch):
    monkeypatch.setattr(get_settings(), "SUPABASE_URL", "")
    monkeypatch.setattr(get_settings(), "ENVIRONMENT", "development")
    client = TestClient(app)
    assert client.get("/api/catalogo").status_code == 401
    assert client.get("/api/catalogo", headers={"Authorization": "Bearer " + jwt()}).status_code == 401
    config = client.get("/api/auth/config").json()
    assert config["auth_requerido"] is True and config["configurado"] is False


def test_private_html_never_available_through_static_or_anonymous_routes(auth_remote):
    client = TestClient(app)
    for path in ("/app", "/app/", "/generador", "/generador/"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login?next=/app"
        assert "formRedactar" not in response.text
    for path in ("/static/generador.html", "/private/generador.html", "/static/../private/generador.html"):
        assert client.get(path).status_code == 404
    assert client.get("/auditor.js").status_code == 401
    assert client.get("/static/auditor.js").status_code == 401


def test_session_bridge_cookie_navigation_api_and_logout(auth_remote):
    token = jwt(100)
    auth_remote[0][token] = USER
    client = TestClient(app)
    response = client.post("/api/auth/sesion", headers={"Authorization": "Bearer " + token, "Origin": "http://testserver"})
    assert response.status_code == 200
    assert response.json()["redirect"] == "/app"
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    max_age = int(re.search(r"Max-Age=(\d+)", cookie).group(1))
    assert 0 < max_age <= 100
    assert token not in response.text
    assert client.get("/api/auth/sesion").json()["usuario"]["id"] == USER_ID
    response = client.get("/app")
    assert response.status_code == 200 and "El Memorialista" in response.text
    assert "no-store" in response.headers["cache-control"]
    assert client.get("/auditor.js").status_code == 200
    assert client.get("/static/auditor.js").status_code == 200
    # La cookie sirve para HTML, pero no sustituye el Bearer en ninguna API.
    assert client.get("/api/catalogo").status_code == 401
    assert client.get("/api/catalogo", headers={"Authorization": "Bearer " + token}).status_code == 200
    for path in ("/", "/login"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303 and response.headers["location"] == "/app"
    assert client.delete("/api/auth/sesion", headers={"Origin": "http://testserver"}).status_code == 200
    assert not supabase_service._TOKEN_CACHE
    assert client.get("/api/auth/sesion").status_code == 401
    assert client.get("/app", follow_redirects=False).status_code == 303


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_cross_origin_session_mutation_rejected(auth_remote, method):
    token = jwt()
    auth_remote[0][token] = USER
    client = TestClient(app)
    response = client.request(method, "/api/auth/sesion", headers={"Authorization": "Bearer " + token, "Origin": "https://attacker.test"})
    assert response.status_code == 403
    assert COOKIE_SESION not in client.cookies
    response = client.request(method, "/api/auth/sesion", headers={"Authorization": "Bearer " + token, "Sec-Fetch-Site": "cross-site"})
    assert response.status_code == 403


def test_cookie_is_secure_in_production(auth_remote, monkeypatch):
    monkeypatch.setattr(get_settings(), "ENVIRONMENT", "production")
    token = jwt()
    auth_remote[0][token] = USER
    response = TestClient(app).post("/api/auth/sesion", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 200
    assert "Secure" in response.headers["set-cookie"]
    assert "max-age=31536000" in response.headers["strict-transport-security"]


def test_missing_admin_key_does_not_delete_anything(auth_remote):
    token = jwt()
    auth_remote[0][token] = USER
    response = TestClient(app).delete("/api/usuario/eliminar-cuenta", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 503
    assert "no se ha borrado ningún dato" in response.json()["detail"]
    assert all(r.method == "GET" and r.url.path == "/auth/v1/user" for r in auth_remote[1])


def test_cache_bounded_by_jwt_expiration(auth_remote, monkeypatch):
    token = jwt(3)
    auth_remote[0][token] = USER
    assert asyncio.run(supabase_service.validar_token_supabase(token))["id"] == USER_ID
    assert asyncio.run(supabase_service.validar_token_supabase(token))["id"] == USER_ID
    assert len(auth_remote[1]) == 1
    now = time.time()
    monkeypatch.setattr(supabase_service.time, "time", lambda: now + 10)
    assert asyncio.run(supabase_service.validar_token_supabase(token)) is None
