"""Fallos y colaboración en exportaciones/bajas: ninguna escritura a servicios reales."""
import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import get_settings
from app.services import supabase_service as service


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(get_settings(), "SUPABASE_URL", "https://project.supabase.test")
    monkeypatch.setattr(get_settings(), "SUPABASE_ANON_KEY", "public-key")
    monkeypatch.setattr(get_settings(), "SUPABASE_SERVICE_ROLE_KEY", "service-key")
    requests = []
    responders = {}
    real_client = httpx.AsyncClient
    def handle(request):
        requests.append(request)
        responder = responders.get(request.url.path)
        return responder(request) if responder else httpx.Response(200, json=[])
    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handle)
        return real_client(*args, **kwargs)
    monkeypatch.setattr(service.httpx, "AsyncClient", factory)
    return responders, requests


def test_export_respects_user_rls_and_paginates(provider):
    responders, requests = provider
    def clients(request):
        offset = int(request.url.params["offset"])
        values = [{"id": f"row-{i}"} for i in range(offset, min(offset + 1000, 1001))]
        return httpx.Response(200, json=values, headers={"Content-Range": f"{offset}-{offset + len(values) - 1}/1001"})
    responders["/rest/v1/clientes"] = clients
    result = asyncio.run(service.exportar_todos_los_datos("owner", "owner-jwt"))
    assert len(result["clientes"]) == 1001
    assert all(r.headers["apikey"] == "public-key" for r in requests)
    assert all(r.headers["authorization"] == "Bearer owner-jwt" for r in requests)
    assert "binarios" in result["alcance"]


def test_export_does_not_claim_partial_data_as_complete(provider):
    provider[0]["/rest/v1/casos"] = lambda r: httpx.Response(500, json={"error": "down"})
    with pytest.raises(service.ErrorSupabase, match="Ningún archivo parcial"):
        asyncio.run(service.exportar_todos_los_datos("owner", "owner-jwt"))


def test_shared_case_blocks_account_deletion_before_any_write(provider):
    responders, requests = provider
    responders["/rest/v1/casos"] = lambda r: httpx.Response(200, json=[{"id": "case-1"}])
    def documents(request):
        values = [{"id": "doc-other", "creado_por": "colleague"}] if "caso_id" in request.url.params else []
        return httpx.Response(200, json=values)
    responders["/rest/v1/documentos"] = documents
    with pytest.raises(service.ErrorSupabase, match="transferir"):
        asyncio.run(service.eliminar_cuenta_usuario("owner", "owner-jwt"))
    assert requests and all(r.method == "GET" for r in requests)


def test_shared_version_blocks_account_deletion_before_any_write(provider):
    responders, requests = provider
    responders["/rest/v1/documentos"] = lambda r: httpx.Response(200, json=[{"id": "doc-1"}])
    responders["/rest/v1/versiones"] = lambda r: httpx.Response(200, json=[{"id": "version-2", "creado_por": "colleague"}])
    with pytest.raises(service.ErrorSupabase, match="No se ha borrado"):
        asyncio.run(service.eliminar_cuenta_usuario("owner", "owner-jwt"))
    assert all(r.method == "GET" for r in requests)


def test_auth_deletion_failure_is_reported_instead_of_false_success(provider):
    provider[0]["/auth/v1/admin/users/owner"] = lambda r: httpx.Response(500, json={"error": "down"})
    with pytest.raises(service.ErrorSupabase, match="cuenta no pudo eliminarse"):
        asyncio.run(service.eliminar_cuenta_usuario("owner", "owner-jwt"))
    assert any(r.method == "DELETE" for r in provider[1])
