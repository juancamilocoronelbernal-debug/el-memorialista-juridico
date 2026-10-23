"""Public PWA routes: session boundaries and a user-independent offline shell."""
from pathlib import Path
from unittest.mock import AsyncMock
import json

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from app.routers import asesor_pwa


@pytest.fixture
def pwa_client(monkeypatch):
    lookup = AsyncMock(return_value=None)
    monkeypatch.setattr(asesor_pwa, "usuario_de_sesion", lookup)
    app = FastAPI()
    app.include_router(asesor_pwa.router)
    with TestClient(app, follow_redirects=False) as client:
        yield client, lookup


def test_anonymous_entry_is_not_cacheable(pwa_client):
    client, lookup = pwa_client
    response = client.get("/asesor/")
    assert response.status_code == 200
    assert "no-store" in response.headers["cache-control"]
    assert response.headers["vary"] == "Cookie, Authorization"
    assert b"/static/asesor/js/app.js" in response.content
    lookup.assert_awaited_once()


def test_authenticated_entry_redirects_to_private_space(pwa_client):
    client, lookup = pwa_client
    lookup.return_value = {"id": "test-session-user"}
    response = client.get("/asesor/", headers={"Cookie": "em_session=example"})
    assert response.status_code == 303
    assert response.headers["location"] == "/app"
    assert "no-store" in response.headers["cache-control"]
    assert not response.content


def test_session_provider_failure_is_not_cacheable(pwa_client):
    client, lookup = pwa_client
    lookup.side_effect = HTTPException(status_code=503, detail="Proveedor no disponible")
    response = client.get("/asesor/")
    assert response.status_code == 503
    assert "no-store" in response.headers["cache-control"]


def test_entry_normalizes_to_public_worker_scope(pwa_client):
    client, _ = pwa_client
    response = client.get("/asesor")
    assert response.status_code == 303
    assert response.headers["location"] == "/asesor/"
    assert "no-store" in response.headers["cache-control"]


def test_offline_shell_is_identical_with_or_without_credentials(pwa_client):
    client, lookup = pwa_client
    normal = client.get("/asesor/offline-shell.html")
    with_credentials = client.get("/asesor/offline-shell.html", headers={
        "Cookie": "em_session=example", "Authorization": "Bearer example",
    })
    assert normal.status_code == with_credentials.status_code == 200
    assert normal.content == with_credentials.content
    assert normal.content == (asesor_pwa.PWA_DIR / "shell.html").read_bytes()
    assert normal.headers["cache-control"].startswith("public")
    assert "vary" not in normal.headers
    assert "set-cookie" not in normal.headers
    lookup.assert_not_awaited()
    assert b"/static/auth/" not in normal.content
    assert b"auditor.js" not in normal.content
    assert b"/api/" not in normal.content


def test_worker_may_control_only_the_public_advisor(pwa_client):
    client, lookup = pwa_client
    response = client.get("/asesor/sw.js")
    assert response.status_code == 200
    assert response.headers["service-worker-allowed"] == "/asesor/"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["content-type"].startswith("application/javascript")
    assert "set-cookie" not in response.headers
    lookup.assert_not_awaited()


def test_manifest_starts_and_stays_in_public_scope(pwa_client):
    client, lookup = pwa_client
    response = client.get("/asesor/manifest.webmanifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["id"] == manifest["start_url"] == manifest["scope"] == "/asesor/"
    assert manifest["display"] == "standalone"
    assert {item["sizes"] for item in manifest["icons"]} >= {"192x192", "512x512"}
    assert all(item["url"].startswith("/asesor/#") for item in manifest["shortcuts"])
    for icon in manifest["icons"]:
        icon_path = Path(__file__).resolve().parents[1] / "app" / icon["src"].lstrip("/")
        assert icon_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    lookup.assert_not_awaited()


@pytest.mark.parametrize("path", [
    "/", "/app", "/login", "/api/auth/sesion", "/asesor/api/auth/sesion",
    "/asesor/app", "/asesor/login", "/asesor/anything-else.html",
])
def test_router_does_not_claim_other_routes(pwa_client, path):
    client, _ = pwa_client
    assert client.get(path).status_code == 404


def test_missing_build_fails_closed_without_caching(pwa_client, monkeypatch, tmp_path):
    client, _ = pwa_client
    monkeypatch.setattr(asesor_pwa, "PWA_DIR", tmp_path)
    response = client.get("/asesor/offline-shell.html")
    assert response.status_code == 503
    assert "no-store" in response.headers["cache-control"]
