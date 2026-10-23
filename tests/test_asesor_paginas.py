"""Cobertura pública, compatibilidad de URLs y aislamiento de metadatos SEO."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
from types import SimpleNamespace
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.routers.asesor_paginas import router
from app.services import asesor_paginas as paginas


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://documentos.example.test"


class PaginaHTML(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def attributes(self, tag):
        return [attrs for found, attrs in self.elements if found == tag]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(paginas, "get_settings", lambda: SimpleNamespace(APP_BASE_URL=ORIGIN))
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_catalogo_publico_cubre_los_66_casos_y_urls_originales():
    data = paginas.catalogo_publico()
    expected = json.loads((ROOT / "tests/fixtures/asesor_slugs_originales.json").read_text())
    assert len(data["casos"]) == 66
    assert data["referencias_totales"] == 169
    assert len(data["tipos"]) == 10
    assert sorted(paginas.ruta_caso(c) for c in data["casos"]) == expected["rutas"]
    assert len({c["id"] for c in data["casos"]}) == 66
    assert not {"con_arriendo_local", "con_promesa_inmueble", "con_trabajo", "con_prestacion_servicios"} & {c["id"] for c in data["casos"]}


def test_catalogo_generado_sigue_al_codigo_integrado():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node se necesita solo para comprobar el catálogo generado.")
    result = subprocess.run([node, "scripts/build_asesor_paginas.cjs", "--check"], cwd=ROOT, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_todas_las_paginas_tienen_contenido_util_sin_javascript(client):
    known_paths = set(paginas.rutas_publicas())
    for case in paginas.catalogo_publico()["casos"]:
        path = paginas.ruta_caso(case)
        response = client.get(path, headers={"Authorization": "Bearer private-sentinel", "Cookie": "private-sentinel=secret"})
        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith("text/html")
        assert "private-sentinel" not in response.text
        assert "set-cookie" not in response.headers
        assert "Qué información conviene preparar" in response.text
        assert "Revisa antes de presentar" in response.text
        parsed = PaginaHTML(response.text)
        assert len(parsed.attributes("h1")) == 1
        assert all(a.get("type") == "application/ld+json" for a in parsed.attributes("script"))
        assert not parsed.attributes("form")
        assert paginas.enlace_formulario(case) in [a.get("href") for a in parsed.attributes("a")]
        for anchor in parsed.attributes("a"):
            href = anchor.get("href", "")
            if href.startswith("/") and not href.startswith("/#"):
                assert href in known_paths or href == "/login", (path, href)
        canonical = [a["href"] for a in parsed.attributes("link") if a.get("rel") == "canonical"]
        assert canonical == [ORIGIN + path]
        assert "default-src 'none'" in response.headers["content-security-policy"]


def test_indice_enlaza_cada_plantilla_y_las_cuatro_guias(client):
    response = client.get("/plantillas/")
    assert response.status_code == 200
    links = [a.get("href") for a in PaginaHTML(response.text).attributes("a")]
    for case in paginas.catalogo_publico()["casos"]:
        assert links.count(paginas.ruta_caso(case)) == 1
    for slug in paginas.GUIAS:
        assert f"/{slug}/" in links
    ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', response.text, re.S).group(1))
    assert ld["mainEntity"]["numberOfItems"] == 66
    assert len(ld["mainEntity"]["itemListElement"]) == 66


@pytest.mark.parametrize("slug", list(paginas.GUIAS))
def test_guias_publicas_no_reintroducen_promesas_upstream(client, slug):
    response = client.get(f"/{slug}/")
    assert response.status_code == 200
    assert "Prepara el documento paso a paso" in response.text
    assert "Modelos relacionados" in response.text
    assert "normas y sentencias ya verificadas" not in response.text
    assert "juez decide en máximo 10 días" not in response.text
    assert "se entiende que aceptan" not in response.text
    assert "sin esperar 48 horas" not in response.text
    canonical = [a["href"] for a in PaginaHTML(response.text).attributes("link") if a.get("rel") == "canonical"]
    assert canonical == [f"{ORIGIN}/{slug}/"]
    if slug == "tutela-eps":
        assert "no esperes a terminar una petición" in response.text
        assert "plazo ordenado en el fallo" in response.text


def test_paginas_reflejan_correcciones_del_catalogo(client):
    consumer = client.get("/plantillas/reclamacion-garantia-consumidor/").text
    assert "no equivale por sí sola a aceptar la reclamación" in consumer
    family = client.get("/plantillas/conciliacion-cuota-alimentaria/").text
    assert "no debe confundirse con el término de respuesta a una petición" in family
    assert "15 días hábiles" not in family
    acoso = client.get("/plantillas/queja-acoso-laboral-acoso-sexual/").text
    assert "tres (3) años" in acoso
    assert "caduca en 6 meses" not in acoso


def test_sitemap_solo_incluye_las_72_urls_publicas(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    root = ET.fromstring(response.text)
    urls = [node.text for node in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    assert len(urls) == len(set(urls)) == 72
    assert set(urls) == {ORIGIN + path for path in paginas.rutas_publicas()}
    assert all(urlsplit(url).path not in {"/app", "/login", "/generador", "/docs"} for url in urls)
    assert all("#" not in url and "?" not in url for url in urls)


def test_robots_y_llms_respetan_separacion_publica_privada(client):
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    for path in ["/api/", "/app", "/generador", "/login", "/auth/", "/auditor.js", "/static/auditor.js"]:
        assert f"Disallow: {path}\n" in robots.text
    assert f"Sitemap: {ORIGIN}/sitemap.xml" in robots.text
    llms = client.get("/llms.txt")
    assert llms.status_code == 200
    assert "Índice de las 66 plantillas" in llms.text
    urls = re.findall(r"\]\(([^)]+)\)", llms.text)
    assert len(urls) == 71
    assert set(urls) == {ORIGIN + path for path in paginas.rutas_publicas() if path != "/"}


@pytest.mark.parametrize("configured", ["", "javascript:alert(1)", "https://user:password@example.test", "https://example.test/private", "https://example.test?x=1", "https://example.test#x", "https://example.test\n.attacker.test", "https://example.test:99999", "//example.test", "https://evil.test\\@example.test", 'https://evil.test\"onload=alert(1)', "https://-invalid.test", "https://invalid..test", "https://"])
def test_url_no_configurada_o_invalida_no_usa_host(client, monkeypatch, configured):
    monkeypatch.setattr(paginas, "get_settings", lambda: SimpleNamespace(APP_BASE_URL=configured))
    headers = {"Host": "attacker.test", "X-Forwarded-Host": "forwarded-attacker.test", "X-Forwarded-Proto": "https"}
    response = client.get("/plantillas/", headers=headers)
    assert response.status_code == 200
    assert 'rel="canonical"' not in response.text
    assert 'property="og:url"' not in response.text
    assert 'property="og:image"' not in response.text
    assert "attacker.test" not in response.text
    sitemap = client.get("/sitemap.xml", headers=headers)
    assert sitemap.status_code == 503
    assert sitemap.headers["cache-control"] == "no-store"
    assert "attacker.test" not in sitemap.text
    assert "Sitemap:" not in client.get("/robots.txt", headers=headers).text
    assert "](/plantillas/)" in client.get("/llms.txt", headers=headers).text


@pytest.mark.parametrize("configured,expected", [("https://EXAMPLE.test/", "https://example.test"), ("http://localhost:8000", "http://localhost:8000"), ("http://[::1]:8000/", "http://[::1]:8000")])
def test_origen_configurado_valido_se_normaliza(monkeypatch, configured, expected):
    monkeypatch.setattr(paginas, "get_settings", lambda: SimpleNamespace(APP_BASE_URL=configured))
    assert paginas.origen_publico() == expected


def test_metadata_social_usa_el_origen_configurado_y_no_el_host(client):
    response = client.get("/accion-de-tutela/", headers={"Host": "attacker.test"})
    metas = PaginaHTML(response.text).attributes("meta")
    values = {m.get("property") or m.get("name"): m.get("content") for m in metas}
    assert values["og:url"] == ORIGIN + "/accion-de-tutela/"
    assert values["og:image"] == ORIGIN + "/static/asesor/pwa/icon-512.png"
    assert values["twitter:image"] == values["og:image"]
    assert values["twitter:card"] == "summary"


def test_html_y_jsonld_no_ejecutan_contenido_del_catalogo(client, monkeypatch):
    malicious = '</script><img src=x onerror="alert(1)"><script>alert(2)</script>&"'
    data = deepcopy(paginas.catalogo_publico())
    case = data["casos"][0]
    case["titulo"] = malicious
    case["resumen"] = malicious
    case["campos"][0]["etiqueta"] = malicious
    case["guia"]["nota"] = malicious
    monkeypatch.setattr(paginas, "catalogo_publico", lambda: data)
    response = client.get(paginas.ruta_caso(case))
    assert response.status_code == 200
    parsed = PaginaHTML(response.text)
    assert not parsed.attributes("img")
    assert len(parsed.attributes("script")) == 1
    assert parsed.attributes("script")[0]["type"] == "application/ld+json"
    ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', response.text, re.S).group(1))
    assert ld["name"] == malicious
    assert "\\u003c/script\\u003e" in response.text
    assert "&lt;img" in response.text


@pytest.mark.parametrize("path", ["/plantillas/no-existe/", "/plantillas/con_trabajo/", "/plantillas/%2E%2E%2Fprivate%2Fgenerador.html/", "/plantillas/%3Cscript%3E/", "/plantillas/a/b/", "/private/generador.html"])
def test_rutas_no_disponibles_no_leen_archivos_ni_exponen_generador(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert "SUPABASE" not in response.text
    assert "auditor.js" not in response.text


def test_helper_no_admite_metadatos_de_rutas_privadas(client):
    for path in ["/app", "/generador", "/api/redactar", "https://attacker.test/"]:
        with pytest.raises(ValueError):
            paginas.metadatos_publicos("Privado", "No publicar", path)


def test_head_y_urls_sin_barra_final(client):
    for path in ["/plantillas/", "/plantilla-tutela/", "/sitemap.xml", "/robots.txt", "/llms.txt"]:
        response = client.head(path)
        assert response.status_code == 200
        assert response.content == b""
    response = client.get("/plantillas", follow_redirects=False)
    assert response.status_code == 307
    assert urlsplit(response.headers["location"]).path == "/plantillas/"
