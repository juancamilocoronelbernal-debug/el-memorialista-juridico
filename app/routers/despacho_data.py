"""Private, authenticated workspace API and document vault."""
from __future__ import annotations

import copy
import re
from pathlib import PurePath
from urllib.parse import quote
from uuid import uuid4

import anyio
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.services import despacho_store as store
from app.services.despacho_fetch import allowed_hosts
from app.services.despacho_monitors import monitoring_status, run_monitor
from app.services.limites import verificar_acceso
from app.services.sesiones import token_bearer

router = APIRouter(prefix="/api/despacho", tags=["Despacho"])


class CreateItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    title: str = Field(min_length=1, max_length=240)
    matter_id: str | None = None
    data: dict = Field(default_factory=dict)


class UpdateItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(None, min_length=1, max_length=240)
    matter_id: str | None = None
    data: dict | None = None
    expected_version: int = Field(ge=1)


class ImportRequest(BaseModel):
    backup: dict


class RestoreRequest(BaseModel):
    expected_version: int = Field(ge=1)
    version_index: int = Field(ge=0, le=49)


async def identity(request: Request) -> tuple[str, str]:
    user = await verificar_acceso(request)
    return user["id"], token_bearer(request)


@router.get("/items")
async def items(request: Request, kind: str | None = None, matter_id: str | None = None,
                offset: int = Query(0, ge=0, le=100000), limit: int = Query(100, ge=1, le=200)):
    uid, token = await identity(request)
    return await store.list_items(uid, token, kind=kind, matter_id=matter_id, offset=offset, limit=limit)


@router.get("/items/{item_id}")
async def item(item_id: str, request: Request):
    uid, token = await identity(request)
    return await store.fetch_item(uid, token, item_id)


@router.post("/items", status_code=201)
async def create(payload: CreateItem, request: Request):
    uid, token = await identity(request)
    return await store.create_item(uid, token, payload.model_dump())


@router.post("/items/{item_id}")
async def update(item_id: str, payload: UpdateItem, request: Request):
    uid, token = await identity(request)
    body = payload.model_dump(exclude_unset=True)
    body.pop("expected_version", None)
    return await store.update_item(uid, token, item_id, body, payload.expected_version)


@router.delete("/items/{item_id}")
async def delete(item_id: str, request: Request, version: int = Query(..., ge=1)):
    uid, token = await identity(request)
    return await store.delete_item(uid, token, item_id, version)


@router.get("/items/{item_id}/audit")
async def audit(item_id: str, request: Request):
    uid, token = await identity(request)
    return {"events": await store.audit_events(uid, token, item_id)}


@router.get("/export")
async def export(request: Request):
    uid, token = await identity(request)
    return await store.export_workspace(uid, token)


@router.post("/import")
async def import_data(payload: ImportRequest, request: Request):
    uid, token = await identity(request)
    return await store.import_workspace(uid, token, payload.backup)


@router.get("/capabilities")
async def capabilities(request: Request):
    from app.routers.despacho_signatures import signing_available
    from app.services import despacho_signing_v5, despacho_agent, despacho_connections, despacho_rooms_v5
    from app.services.despacho_knowledge import embedding_status
    from app.services.despacho_ocr import ocr_status
    uid, token = await identity(request)
    s = get_settings()
    storage = {"configured": bool(s.SUPABASE_URL and s.SUPABASE_ANON_KEY), "ready": False, "message": ""}
    try:
        await store.list_items(uid, token, limit=1)
        storage.update(ready=True, message="Almacenamiento privado disponible.")
    except HTTPException as exc:
        storage["message"] = str(exc.detail)
    return {"storage": storage, "ai": {"configured": bool(s.GEMINI_API_KEY or s.GROQ_API_KEY),
            "gemini": bool(s.GEMINI_API_KEY), "groq": bool(s.GROQ_API_KEY)},
            "monitoring": {**monitoring_status(), "allowed_hosts": allowed_hosts()},
            "limits": {"upload_bytes": store.MAX_UPLOAD_BYTES, "upload_files": 10,
                       "extracted_characters": 500000, "pdf_pages": 500, "versions": 50},
            "signatures": {"configured": signing_available(), "enabled": signing_available(),
                           "scope": "private_link", "message": "Firma por enlace privado con aceptación expresa y registro de evidencia. La identidad se declara por el firmante; no incluye certificado digital ni verificación documental de identidad."},
            "signatures_v5": {"supported": True, **despacho_signing_v5.available()},
            "rooms": despacho_rooms_v5.available(),
            "agent": despacho_agent.status(), "connections": despacho_connections.capabilities(),
            "automation_limits": {"user_daily": s.DESPACHO_AUTOMATION_DAILY_USER_CALLS,
                                   "global_daily": s.DESPACHO_AUTOMATION_DAILY_GLOBAL_CALLS,
                                   "reset_timezone": "UTC", "unit": "logical_call"},
            "knowledge": {"embeddings": embedding_status(), "ocr": ocr_status()},
            "collaboration": {"scope": "private_account", "message": "Cada cuenta conserva sus asuntos y documentos privados. No se comparte con otros integrantes automáticamente."}}


def _filename(value: str) -> str:
    name = PurePath(value.replace("\\", "/")).name
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)[:200]
    return name or "documento.txt"


def _snapshot(item: dict) -> dict:
    d = item["data"]
    return {"title": item["title"], "created_at": store.utcnow(), "version": item["version"],
            **{k: copy.deepcopy(d[k]) for k in ("text", "pages", "pagination", "storage_path", "filename", "mime", "warnings") if k in d}}


@router.post("/documents/upload")
async def upload(request: Request, files: list[UploadFile] = File(...), matter_id: str | None = Form(None),
                 document_id: str | None = Form(None), expected_version: int | None = Form(None)):
    uid, token = await identity(request)
    if not 1 <= len(files) <= 10 or (document_id and len(files) != 1):
        raise HTTPException(422, "Sube entre uno y diez archivos; una nueva versión admite un solo archivo.")
    if matter_id:
        await store.fetch_item(uid, token, matter_id, kind="matter")
    old = None
    if document_id:
        old = await store.fetch_item(uid, token, document_id, kind="document")
        if old["version"] != expected_version:
            raise HTTPException(409, "La versión del documento cambió. Recarga antes de subirlo.")
        if old["data"].get("locked") or old["data"].get("final"):
            raise HTTPException(409, "Desprotege el documento antes de añadir una versión.")
    results, errors, total_bytes = [], [], 0
    for file in files:
        path = None
        storage_attempted = False
        name = _filename(file.filename or "documento.txt")
        try:
            content = await file.read(store.MAX_UPLOAD_BYTES + 1)
            total_bytes += len(content)
            if len(content) > store.MAX_UPLOAD_BYTES or total_bytes > 30 * 1024 * 1024:
                raise HTTPException(413, "El límite es 10 MB por archivo y 30 MB por envío.")
            from app.services.despacho_ai import extract_document
            parsed = await anyio.to_thread.run_sync(extract_document, content, name)
            mime = parsed.get("mime", "text/plain")
            suffix = {"application/pdf": "pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
                      "text/markdown": "md", "image/png": "png", "image/jpeg": "jpg", "image/tiff": "tiff",
                      "image/webp": "webp", "message/rfc822": "eml"}.get(mime, "txt")
            item_id = old["id"] if old else str(uuid4())
            path = f"{uid}/{item_id}/{uuid4()}.{suffix}"
            data = {**(copy.deepcopy(old["data"]) if old else {}), **parsed, "filename": name,
                    "storage_path": path, "mime": mime, "uploaded_at": store.utcnow()}
            data["versions"] = [*old["data"].get("versions", []), _snapshot(old)] if old else []
            payload = {"kind": "document", "title": old["title"] if old else name,
                       "matter_id": old["matter_id"] if old else matter_id or None, "data": data}
            store.validate_payload(payload, user_id=uid)
            storage_attempted = True
            await store.upload_bytes(uid, token, path, content, mime)
            if old:
                saved = await store.update_item(uid, token, item_id, payload, old["version"])
            else:
                saved = await store.create_item(uid, token, payload, item_id=item_id)
            results.append(saved)
            path = None
        except HTTPException as exc:
            errors.append({"filename": name, "status": exc.status_code, "message": str(exc.detail)})
        except (ValueError, OSError) as exc:
            errors.append({"filename": name, "status": 422, "message": "No se pudo extraer el documento. Comprueba su formato."})
        finally:
            await file.close()
            if path and storage_attempted:
                try:
                    await store.remove_storage_paths(uid, token, [path])
                except HTTPException:
                    errors.append({"filename": name, "status": 502, "message": "Puede quedar un original sin vincular; el administrador debe comprobar el almacenamiento."})
    return {"items": results, "errors": errors}


@router.get("/documents/{item_id}/download")
async def download(item_id: str, request: Request, version_index: int | None = Query(None, ge=0, le=49)):
    uid, token = await identity(request)
    item = await store.fetch_item(uid, token, item_id, kind="document")
    data = item["data"]
    if version_index is not None:
        versions = data.get("versions", [])
        if version_index >= len(versions):
            raise HTTPException(404, "La versión no existe.")
        data = versions[version_index]
    if not data.get("storage_path"):
        raise HTTPException(404, "Esta versión conserva texto, pero no tiene un original binario. Usa exportar Word o PDF.")
    content = await store.download_bytes(uid, token, data["storage_path"])
    return Response(content, media_type=data.get("mime", "application/octet-stream"), headers={
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(_filename(data.get("filename", "documento"))),
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/documents/{item_id}/restore")
async def restore(item_id: str, payload: RestoreRequest, request: Request):
    uid, token = await identity(request)
    old = await store.fetch_item(uid, token, item_id, kind="document")
    if old["version"] != payload.expected_version:
        raise HTTPException(409, "El documento cambió. Recarga antes de restaurar.")
    versions = old["data"].get("versions", [])
    if payload.version_index >= len(versions):
        raise HTTPException(404, "La versión no existe.")
    selected = versions[payload.version_index]
    data = copy.deepcopy(old["data"])
    for key in ("text", "pages", "pagination", "storage_path", "filename", "mime", "warnings"):
        data.pop(key, None)
        if key in selected:
            data[key] = copy.deepcopy(selected[key])
    data["versions"] = [*versions, _snapshot(old)]
    data["restored_from"] = {"version_index": payload.version_index, "restored_at": store.utcnow()}
    return await store.update_item(uid, token, item_id, {"data": data}, payload.expected_version)


@router.post("/monitors/{item_id}/run")
async def monitor_run(item_id: str, request: Request):
    uid, token = await identity(request)
    from app.services.limites import limitador
    limitador.verificar(request, "redactar", user_id=uid)
    return await run_monitor(uid, token, item_id)
