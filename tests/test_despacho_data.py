"""Meaningful boundaries for the private vault and monitors; no live credentials."""
import copy
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException

from app.services import despacho_store as store
from app.services import despacho_fetch as fetch
from app.services import despacho_monitors as monitors

OWNER = "8b8835f2-f85f-4bc2-84f0-847d73cdf863"
OTHER = "05363426-9322-43e0-b45c-43501a16cc7d"
ITEM = "478a5916-c77f-4d9c-92aa-a6739eb6920f"
PARENT = "784b28df-8934-413c-a521-7902f29de522"


def item(kind="document", **overrides):
    return {"id": ITEM, "owner_id": OWNER, "kind": kind, "title": "Prueba", "matter_id": None,
            "data": {"text": "Texto anterior", "pages": [], "versions": []} if kind == "document" else {},
            "version": 1, "created_at": "2026-10-23T00:00:00Z", "updated_at": "2026-10-23T00:00:00Z", **overrides}


@pytest.fixture
def configured(monkeypatch):
    settings = SimpleNamespace(SUPABASE_URL="https://unit.supabase.test", SUPABASE_ANON_KEY="public-key",
                               SUPABASE_SERVICE_ROLE_KEY="server-only-key", GEMINI_API_KEY="", GROQ_API_KEY="",
                               DESPACHO_MONITORS_ENABLED=False, DESPACHO_MONITOR_POLL_SECONDS=60,
                               DESPACHO_MONITOR_ALLOWED_HOSTS=fetch.DEFAULT_HOSTS)
    for module in (store, fetch, monitors):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
    return settings


def transport(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: original(transport=httpx.MockTransport(handler)))


@pytest.mark.asyncio
async def test_get_filters_owner_and_never_uses_service_key(configured, monkeypatch):
    def handler(request):
        assert request.headers["authorization"] == "Bearer own-token"
        assert request.headers["apikey"] == "public-key"
        assert request.url.params["owner_id"] == "eq." + OWNER
        assert request.url.params["id"] == "eq." + ITEM
        return httpx.Response(200, json=[item()])
    transport(monkeypatch, handler)
    result = await store.fetch_item(OWNER, "own-token", ITEM)
    assert result["id"] == ITEM and "owner_id" not in result


@pytest.mark.asyncio
async def test_foreign_row_is_never_returned(configured, monkeypatch):
    transport(monkeypatch, lambda r: httpx.Response(200, json=[item(owner_id=OTHER)]))
    with pytest.raises(HTTPException) as error:
        await store.fetch_item(OWNER, "own-token", ITEM)
    assert error.value.status_code == 502


@pytest.mark.asyncio
async def test_cas_rejects_race_and_preserves_history(configured, monkeypatch):
    captured = []
    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=[item(data={"text": "Anterior", "pages": [{"page": 1, "text": "Anterior"}], "versions": []})])
        payload = json.loads(request.content)
        captured.append(payload)
        assert request.url.params["version"] == "eq.1"
        assert payload["version"] == 2
        return httpx.Response(200, json=[])
    transport(monkeypatch, handler)
    with pytest.raises(HTTPException) as error:
        await store.update_item(OWNER, "t", ITEM, {"data": {"text": "Actual", "pages": [{"page": 1, "text": "Anterior"}]}}, 1)
    assert error.value.status_code == 409
    assert captured[0]["data"]["versions"][0]["text"] == "Anterior"
    assert captured[0]["data"]["pages"] == []
    assert captured[0]["data"]["pagination"] == "segments"


@pytest.mark.asyncio
async def test_stale_version_stops_before_write(configured, monkeypatch):
    db = AsyncMock(return_value=[item(version=2)])
    monkeypatch.setattr(store, "db_request", db)
    with pytest.raises(HTTPException) as error:
        await store.update_item(OWNER, "t", ITEM, {"title": "Nuevo"}, 1)
    assert error.value.status_code == 409 and db.await_count == 1


@pytest.mark.asyncio
async def test_locked_document_requires_separate_unlock(configured, monkeypatch):
    db = AsyncMock(return_value=[item(data={"text": "Original", "locked": True, "versions": []})])
    monkeypatch.setattr(store, "db_request", db)
    with pytest.raises(HTTPException) as error:
        await store.update_item(OWNER, "t", ITEM, {"data": {"text": "Reemplazo", "locked": False}}, 1)
    assert error.value.status_code == 409 and db.await_count == 1


@pytest.mark.asyncio
async def test_delete_matter_with_children_is_rejected(configured, monkeypatch):
    monkeypatch.setattr(store, "fetch_item", AsyncMock(return_value=store.public_item(item("matter"))))
    monkeypatch.setattr(store, "list_items", AsyncMock(return_value={"items": [item()], "has_more": False}))
    db = AsyncMock()
    monkeypatch.setattr(store, "db_request", db)
    with pytest.raises(HTTPException) as error:
        await store.delete_item(OWNER, "t", ITEM, 1)
    assert error.value.status_code == 409 and not db.called


@pytest.mark.asyncio
async def test_import_validates_every_item_before_writes(configured, monkeypatch):
    db = AsyncMock()
    monkeypatch.setattr(store, "db_request", db)
    backup = {"format": "memorialista-despacho", "version": 1, "items": [item(), {"id": "invalid"}]}
    with pytest.raises(HTTPException):
        await store.import_workspace(OWNER, "t", backup)
    assert not db.called


@pytest.mark.asyncio
async def test_import_conflicting_parent_copies_and_relinks_children(configured, monkeypatch):
    parent = store.public_item(item("matter", id=PARENT, title="Asunto actual"))
    document = store.public_item(item(matter_id=PARENT))
    original_parent = copy.deepcopy(parent)
    original_parent["title"] = "Asunto de la copia"
    incoming = {"format": "memorialista-despacho", "version": 1, "owner_id": OWNER, "items": [original_parent, document]}
    monkeypatch.setattr(store, "all_items", AsyncMock(return_value=[parent, document]))
    calls = []
    async def db(method, endpoint, token, **kwargs):
        assert endpoint == "rpc/despacho_importar_items"
        calls.extend(kwargs["json"]["p_items"])
        return {"imported": len(calls)}
    monkeypatch.setattr(store, "db_request", db)
    result = await store.import_workspace(OWNER, "t", incoming)
    assert result["imported"] == 2 and result["conflicts"] == 2
    matter = next(r for r in calls if r["kind"] == "matter")
    doc = next(r for r in calls if r["kind"] == "document")
    assert matter["id"] != PARENT and doc["id"] != ITEM and doc["matter_id"] == matter["id"]


@pytest.mark.asyncio
async def test_import_foreign_original_does_not_grant_access(configured, monkeypatch):
    document = item(data={"text": "Texto", "versions": [], "storage_path": f"{OTHER}/{ITEM}/{uuid4()}.pdf"})
    monkeypatch.setattr(store, "all_items", AsyncMock(return_value=[]))
    sent = []
    async def db(*args, **kwargs):
        sent.extend(kwargs["json"]["p_items"])
        return {"imported": 1}
    monkeypatch.setattr(store, "db_request", db)
    result = await store.import_workspace(OWNER, "t", {"format": "memorialista-despacho", "version": 1, "owner_id": OTHER, "items": [document]})
    assert result["originals_not_included"] == 1
    assert "storage_path" not in sent[0]["data"]
    assert sent[0]["data"]["text"] == "Texto"


@pytest.mark.parametrize("path", [f"{OTHER}/{ITEM}/{uuid4()}.pdf", f"{OWNER}/../other.pdf", "https://example.com/a.pdf", ""])
def test_storage_path_boundary(path):
    with pytest.raises(HTTPException):
        store.validate_storage_path(path, OWNER)


@pytest.mark.parametrize("url", ["http://www.corteconstitucional.gov.co/", "https://corteconstitucional.gov.co.evil.test/",
    "https://corteconstitucional.gov.co@evil.test/", "https://127.0.0.1/", "https://www.corteconstitucional.gov.co:8443/",
    "https://www.corteconstitucional.gov.co/\r\nHost:evil", "file:///etc/passwd"])
def test_url_boundary(configured, url):
    with pytest.raises(HTTPException):
        fetch.validate_url(url)


def test_official_url_normalization(configured):
    assert fetch.validate_url("https://WWW.CORTECONSTITUCIONAL.GOV.CO/relatoria/#ancla") == "https://www.corteconstitucional.gov.co/relatoria/"


@pytest.mark.asyncio
async def test_dns_private_resolution_rejected(configured, monkeypatch):
    import asyncio
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", AsyncMock(return_value=[(2,1,6,"",("127.0.0.1",443))]))
    with pytest.raises(HTTPException) as error:
        await fetch.resolve_public("corteconstitucional.gov.co")
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_monitor_baseline_then_changes_with_keywords(configured, monkeypatch):
    source = {"url": "https://corteconstitucional.gov.co/", "title": "Relatoría", "text": "Sentencia previa"}
    mock = AsyncMock(return_value=source)
    monkeypatch.setattr(monitors, "fetch_source", mock)
    watch = item("monitor", data={"url": source["url"], "keywords": ["tutela"], "interval_minutes": 60, "findings": []})
    baseline = await monitors.evaluate_monitor(watch)
    assert baseline["last_status"] == "baseline" and not baseline.get("findings")
    source["text"] = "Nueva publicación de tutela"
    watch["data"] = baseline
    changed = await monitors.evaluate_monitor(watch)
    assert changed["last_status"] == "changed" and changed["findings"][0]["matched_keywords"] == ["tutela"]
    watch["data"] = changed
    unchanged = await monitors.evaluate_monitor(watch)
    assert unchanged["last_status"] == "unchanged" and len(unchanged["findings"]) == 1


@pytest.mark.asyncio
async def test_fetch_failure_does_not_invent_finding(configured, monkeypatch):
    monkeypatch.setattr(monitors, "fetch_source", AsyncMock(side_effect=HTTPException(502, "Sin conexión")))
    result = await monitors.evaluate_monitor(item("monitor", data={"url": "https://corteconstitucional.gov.co/", "last_hash": "previous", "findings": []}))
    assert result["last_status"] == "error" and result["last_hash"] == "previous" and result["findings"] == []


@pytest.mark.asyncio
async def test_monitor_manual_cooldown(configured, monkeypatch):
    monkeypatch.setattr(store, "fetch_item", AsyncMock(return_value=item("monitor", data={"last_checked": datetime.now(timezone.utc).isoformat()})))
    with pytest.raises(HTTPException) as error:
        await monitors.run_monitor(OWNER, "t", ITEM)
    assert error.value.status_code == 429


@pytest.mark.asyncio
async def test_storage_cleanup_refuses_unverifiable_listing(configured):
    fake = SimpleNamespace(post=AsyncMock(return_value=httpx.Response(404, json={"error": "missing bucket"})))
    from app.services.supabase_service import ErrorSupabase
    with pytest.raises(ErrorSupabase):
        await store.borrar_archivos_despacho(fake, "https://unit.test", {}, OWNER)


@pytest.mark.asyncio
async def test_missing_migration_is_explained(configured, monkeypatch):
    transport(monkeypatch, lambda request: httpx.Response(404, json={"code": "PGRST205"}))
    with pytest.raises(HTTPException) as error:
        await store.list_items(OWNER, "t")
    assert error.value.status_code == 503 and "migración" in error.value.detail


def test_html_drops_executable_content():
    text, title = fetch.html_to_text("<title>Boletín</title><script>SECRET_INSTRUCTION</script><p>Texto oficial</p><style>hide</style>")
    assert "SECRET_INSTRUCTION" not in text and "hide" not in text
    assert title == "Boletín" and "Texto oficial" in text


@pytest.mark.asyncio
async def test_upload_preserves_original_bytes_and_extracted_context(configured, monkeypatch):
    from fastapi import FastAPI
    from app.routers import despacho_data as api
    app = FastAPI()
    app.include_router(api.router)
    monkeypatch.setattr(api, "identity", AsyncMock(return_value=(OWNER, "user-token")))
    put = AsyncMock()
    captured = []
    async def create(uid, token, payload, **kwargs):
        captured.append(payload)
        return item(**payload)
    monkeypatch.setattr(store, "upload_bytes", put)
    monkeypatch.setattr(store, "create_item", create)
    raw = "Hecho: el documento llegó el 22 de octubre.\nAnexo original.".encode()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://unit.test") as client:
        response = await client.post("/api/despacho/documents/upload", files=[("files", ("anexo.txt", raw, "text/plain"))])
    assert response.status_code == 200 and len(response.json()["items"]) == 1
    assert response.json()["errors"] == []
    assert put.await_args.args[3] == raw
    assert captured[0]["data"]["text"] == raw.decode()
    assert captured[0]["data"]["pagination"] == "segments"
    assert captured[0]["data"]["storage_path"].startswith(OWNER + "/")


@pytest.mark.asyncio
async def test_new_version_conflict_stops_upload_before_storage(configured, monkeypatch):
    from fastapi import FastAPI
    from app.routers import despacho_data as api
    app = FastAPI()
    app.include_router(api.router)
    monkeypatch.setattr(api, "identity", AsyncMock(return_value=(OWNER, "user-token")))
    monkeypatch.setattr(store, "fetch_item", AsyncMock(return_value=item(version=3)))
    put = AsyncMock()
    monkeypatch.setattr(store, "upload_bytes", put)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://unit.test") as client:
        response = await client.post("/api/despacho/documents/upload", data={"document_id": ITEM, "expected_version": "2"}, files=[("files", ("anexo.txt", b"updated", "text/plain"))])
    assert response.status_code == 409 and not put.called


@pytest.mark.asyncio
async def test_restore_preserves_current_snapshot_and_selected_pagination(configured, monkeypatch):
    from fastapi import FastAPI
    from app.routers import despacho_data as api
    app = FastAPI()
    app.include_router(api.router)
    monkeypatch.setattr(api, "identity", AsyncMock(return_value=(OWNER, "user-token")))
    old = item(data={"text": "Nuevo", "pagination": "segments", "versions": [{"text": "Antiguo", "pages": [{"page": 1, "text": "Antiguo"}], "pagination": "pages"}]})
    monkeypatch.setattr(store, "fetch_item", AsyncMock(return_value=old))
    update = AsyncMock(return_value=old)
    monkeypatch.setattr(store, "update_item", update)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://unit.test") as client:
        response = await client.post(f"/api/despacho/documents/{ITEM}/restore", json={"expected_version": 1, "version_index": 0})
    assert response.status_code == 200
    data = update.await_args.args[3]["data"]
    assert data["text"] == "Antiguo" and data["pagination"] == "pages"
    assert data["versions"][-1]["text"] == "Nuevo"


@pytest.mark.asyncio
async def test_fetch_pins_address_and_blocks_redirect_to_private_domain(configured, monkeypatch):
    visited = []
    monkeypatch.setattr(fetch, "resolve_public", AsyncMock(return_value="8.8.8.8"))
    class Body(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b""
    def handler(request):
        visited.append(request)
        assert request.url.host == "8.8.8.8"
        assert request.headers["host"] == "corteconstitucional.gov.co"
        assert request.extensions["sni_hostname"] == "corteconstitucional.gov.co"
        return httpx.Response(302, headers={"location": "https://127.0.0.1/admin"}, stream=Body())
    transport(monkeypatch, handler)
    with pytest.raises(HTTPException) as error:
        await fetch.fetch_source("https://corteconstitucional.gov.co/")
    assert error.value.status_code == 422 and len(visited) == 1
