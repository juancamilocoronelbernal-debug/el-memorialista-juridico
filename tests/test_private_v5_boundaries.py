"""Fronteras V5 sobre la aplicación y todos sus middlewares reales.

No se sustituye autenticación, parseo, rutas ni servicios por respuestas válidas.
Los guardas de transporte hacen fallar cualquier intento de red o correo. Las
peticiones ASGI permiten verificar que una denegación no consume el cuerpo.
"""
import asyncio
import json
import re
import socket

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import PRIVATE_DIR, app, csp_archivo_publico


UUID = "11111111-1111-4111-8111-111111111111"
JSON_LIMIT = 64 * 1024
ROOM_UPLOAD_LIMIT = 11 * 1024 * 1024
PUBLIC_POSTS = (
    "/api/firmas-v5/view", "/api/firmas-v5/document",
    "/api/firmas-v5/otp", "/api/firmas-v5/accept",
    "/api/salas-v5/view", "/api/salas-v5/document", "/api/salas-v5/upload",
)


def _included_endpoints(routes, prefix=""):
    """FastAPI puede conservar inclusiones anidadas en lugar de aplanarlas."""
    for route in routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is not None and methods:
            yield prefix + path, methods
        included = getattr(route, "original_router", None)
        if included is not None:
            context = getattr(route, "include_context", None)
            yield from _included_endpoints(included.routes, prefix + getattr(context, "prefix", ""))
        elif getattr(route, "routes", None):
            yield from _included_endpoints(route.routes, prefix + (path or ""))


APP_ENDPOINTS = tuple(_included_endpoints(app.routes))
PRIVATE_ENDPOINTS = sorted({
    (method, path)
    for path, methods in APP_ENDPOINTS
    if path == "/api/despacho" or path.startswith("/api/despacho/")
    for method in methods - {"OPTIONS"}
})


@pytest.fixture(autouse=True)
def no_external_requests(monkeypatch):
    """Configurar una URL no proporciona permisos ni simula una sesión."""
    settings = get_settings()
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://boundary.supabase.test")
    monkeypatch.setattr(settings, "SUPABASE_ANON_KEY", "public-boundary-test-key")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    attempts = []

    def deny_sync(*args, **kwargs):
        attempts.append("sync network")
        raise AssertionError("Esta petición no debe iniciar una conexión externa.")

    async def deny_async(*args, **kwargs):
        attempts.append("async network")
        raise AssertionError("Esta petición no debe iniciar una conexión externa.")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", deny_sync)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", deny_async)
    monkeypatch.setattr(socket, "create_connection", deny_sync)
    yield attempts
    assert attempts == [], "Se intentó acceder a un servicio externo desde una petición inválida."


async def _asgi_request(method, path, *, chunks=(b'{"incompleto":',), headers=()):
    """Envía al app completo y cuenta las lecturas reales del canal de entrada."""
    messages = []
    reads = 0
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1", "method": method, "scheme": "https",
        "path": path, "raw_path": path.encode(), "root_path": "", "query_string": b"",
        "headers": [(b"host", b"boundary.test"), *headers],
        "client": ("192.0.2.81", 43100), "server": ("boundary.test", 443), "state": {},
    }

    async def receive():
        nonlocal reads
        index = reads
        reads += 1
        if index >= len(chunks):
            return {"type": "http.disconnect"}
        return {"type": "http.request", "body": chunks[index], "more_body": index + 1 < len(chunks)}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    starts = [message for message in messages if message["type"] == "http.response.start"]
    assert len(starts) == 1
    response_headers = {key.decode().lower(): value.decode() for key, value in starts[0]["headers"]}
    body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return starts[0]["status"], response_headers, body, reads


def test_router_discovery_is_nonempty_and_contains_all_v5_modules():
    paths = {path for _, path in PRIVATE_ENDPOINTS}
    assert {
        "/api/despacho/chat", "/api/despacho/agent/jobs", "/api/despacho/agent/schedules",
        "/api/despacho/connections", "/api/despacho/knowledge/search",
        "/api/despacho/signing", "/api/despacho/rooms",
    } <= paths
    registered_public = {path for path, methods in APP_ENDPOINTS if "POST" in methods}
    assert set(PUBLIC_POSTS) <= registered_public


@pytest.mark.parametrize("method,path", PRIVATE_ENDPOINTS)
def test_every_private_route_denies_anonymous_without_reading_its_body(method, path):
    path = re.sub(r"\{[^}]+\}", UUID, path)
    status, headers, body, reads = asyncio.run(_asgi_request(method, path, headers=(
        (b"content-type", b"application/json"), (b"content-length", b"14"),
    )))
    assert status == 401, (method, path, body)
    assert reads == 0, (method, path, "El cuerpo se consumió antes de rechazar la sesión.")
    assert headers["www-authenticate"] == "Bearer"
    assert "private" in headers["cache-control"] and "no-store" in headers["cache-control"]
    assert "noindex" in headers["x-robots-tag"]


@pytest.mark.parametrize("path", PUBLIC_POSTS)
@pytest.mark.parametrize("token", [None, "enlace-invalido", "!" * 43])
def test_exact_public_posts_reach_link_validation_without_a_professional_session(path, token):
    payload = {} if token is None else {"token": token}
    if path.endswith("/accept"):
        payload.update(otp="123456", name="Persona ficticia", consent=True, manifest_hash="a" * 64)
    elif path == "/api/salas-v5/document":
        payload.update(document_id=UUID, mode="view")
    client = TestClient(app)
    try:
        if path.endswith("/upload"):
            response = client.post(path, data={**payload, "request_id": UUID}, files={
                "file": ("documento-ficticio.txt", b"Contenido ficticio.", "text/plain"),
            })
            expected = 404 if token == "!" * 43 else 422
        else:
            response = client.post(path, json=payload)
            expected = 422
        assert response.status_code == expected, (path, response.text)
        assert "www-authenticate" not in response.headers
        assert "no-store" in response.headers["cache-control"]
        assert "noindex" in response.headers["x-robots-tag"]
    finally:
        client.close()


@pytest.mark.parametrize("path", PUBLIC_POSTS)
@pytest.mark.parametrize("method", ["GET", "HEAD", "PUT", "PATCH", "DELETE", "TRACE"])
def test_link_exemption_does_not_apply_to_other_non_preflight_methods(path, method):
    status, headers, _, reads = asyncio.run(_asgi_request(method, path))
    assert status == 401
    assert headers["www-authenticate"] == "Bearer"
    assert reads == 0


LOOKALIKE_PATHS = sorted({variant for path in PUBLIC_POSTS for variant in (
    path + "/", path + "/extra", path.replace("-v5/", "-v50/"),
    path.rsplit("/", 1)[0] + "/" + path.rsplit("/", 1)[1].upper(),
)})


@pytest.mark.parametrize("path", [*LOOKALIKE_PATHS, "/api/despacho/ruta-no-registrada-v5"])
def test_similar_or_unknown_paths_are_not_implicitly_public(path):
    status, headers, _, reads = asyncio.run(_asgi_request("POST", path))
    assert status == 401
    assert headers["www-authenticate"] == "Bearer"
    assert reads == 0


@pytest.mark.parametrize("path", ["/api/despacho/rooms", "/api/firmas-v5/view", "/api/salas-v5/upload"])
def test_options_is_only_a_preflight_exception_and_never_returns_product_data(path):
    # AccesoAPI excluye OPTIONS expresamente para CORS; no es una lectura pública.
    status, _, body, reads = asyncio.run(_asgi_request("OPTIONS", path, chunks=()))
    assert status == 405
    assert json.loads(body)["detail"] == "Method Not Allowed"
    assert reads == 0


@pytest.mark.parametrize("path", PUBLIC_POSTS)
def test_public_json_over_64_kib_is_rejected_before_reading_or_parsing(path):
    status, _, body, reads = asyncio.run(_asgi_request("POST", path, headers=(
        (b"content-type", b"application/json"), (b"content-length", str(JSON_LIMIT + 1).encode()),
    )))
    assert status == 413
    assert "límite" in json.loads(body)["detail"]
    assert reads == 0


@pytest.mark.parametrize("path", [p for p in PUBLIC_POSTS if p.startswith("/api/salas-v5/")])
def test_room_multipart_over_11_mib_is_rejected_before_multipart_parsing(path):
    status, _, body, reads = asyncio.run(_asgi_request("POST", path, headers=(
        # Sin boundary: si el parser se ejecutara primero respondería 400/422.
        (b"content-type", b"multipart/form-data"),
        (b"content-length", str(ROOM_UPLOAD_LIMIT + 1).encode()),
    )))
    assert status == 413
    assert "límite" in json.loads(body)["detail"]
    assert reads == 0


def test_signature_multipart_cannot_expand_the_64_kib_signature_limit():
    status, _, _, reads = asyncio.run(_asgi_request("POST", "/api/firmas-v5/accept", headers=(
        (b"content-type", b"multipart/form-data"), (b"content-length", str(JSON_LIMIT + 1).encode()),
    )))
    assert status == 413 and reads == 0


@pytest.mark.parametrize("path", ["/api/firmas-v5/view", "/api/salas-v5/view"])
def test_json_at_the_declared_limit_reaches_schema_validation(path):
    status, _, _, reads = asyncio.run(_asgi_request("POST", path, chunks=(b"{}",), headers=(
        (b"content-type", b"application/json"), (b"content-length", str(JSON_LIMIT).encode()),
    )))
    assert status == 422
    assert reads == 1


@pytest.mark.parametrize("path", ["/api/firmas-v5/view", "/api/salas-v5/view"])
def test_chunked_json_without_content_length_cannot_bypass_the_limit(path):
    chunks = (b"{" + b" " * (32 * 1024 - 1), b" " * (32 * 1024), b"}")
    assert sum(map(len, chunks)) == JSON_LIMIT + 1
    status, _, body, reads = asyncio.run(_asgi_request("POST", path, chunks=chunks, headers=(
        (b"content-type", b"application/json"), (b"transfer-encoding", b"chunked"),
    )))
    assert status == 413
    assert "límite" in json.loads(body)["detail"]
    assert reads == 3


@pytest.mark.parametrize("path,filename", [
    ("/firmar-v5", "firma-v5.html"), ("/sala-cliente", "sala-cliente.html"),
])
def test_public_portals_are_uncached_unindexed_and_use_the_real_strict_csp(path, filename):
    client = TestClient(app)
    try:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 200
        assert "El Memorialista" in response.text
        assert response.headers["cache-control"] == "private, no-store, max-age=0"
        assert response.headers["pragma"] == "no-cache"
        assert response.headers["x-robots-tag"] == "noindex, nofollow"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["x-frame-options"] == "DENY"
        policy = response.headers["content-security-policy"]
        expected = csp_archivo_publico(PRIVATE_DIR / filename).replace("frame-src 'none'", "frame-src 'self' blob:")
        assert policy == expected
        directives = {parts[0]: parts[1:] for value in policy.split(";") if (parts := value.strip().split())}
        assert directives["default-src"] == ["'none'"]
        assert directives["connect-src"] == ["'self'"]
        assert directives["script-src"][0] == "'self'"
        assert all(value.startswith("'sha256-") for value in directives["script-src"][1:])
        assert directives["script-src-attr"] == ["'none'"]
        assert directives["frame-src"] == ["'self'", "blob:"]
        assert directives["frame-ancestors"] == ["'none'"]
        assert directives["object-src"] == ["'none'"]
        assert directives["base-uri"] == ["'none'"]
        assert directives["form-action"] == ["'self'"]
        assert "'unsafe-inline'" not in directives["script-src"]
        assert "'unsafe-eval'" not in directives["script-src"]
        assert "supabase" not in policy
        assert "set-cookie" not in response.headers
    finally:
        client.close()
