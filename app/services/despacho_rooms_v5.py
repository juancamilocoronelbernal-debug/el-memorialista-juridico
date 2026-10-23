"""Salas privadas con copias PDF, permisos revocables y recepción controlada."""
from __future__ import annotations

import hashlib
import hmac
import io
import re
import secrets
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import quote
from uuid import uuid4

import anyio
import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.services import despacho_store as store
from app.services import despacho_signing_v5 as signing
from app.services.despacho_export import make_pdf

BUCKET = "despacho-salas-v5"
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_SNAPSHOTS_BYTES = 25 * 1024 * 1024
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def available() -> dict:
    s = get_settings()
    configured = bool(s.SUPABASE_URL and s.SUPABASE_ANON_KEY and s.SUPABASE_SERVICE_ROLE_KEY)
    return {"configured": configured, "supported": True, "bucket": BUCKET,
            "max_documents": 20, "max_shared_bytes": MAX_SNAPSHOTS_BYTES, "max_upload_bytes": MAX_FILE_BYTES,
            "upload_quota_bytes": 100 * 1024 * 1024, "message": "Salas con permisos por enlace, copias PDF congeladas y aportes pendientes de revisión." if configured else "Configura Supabase y aplica la migración de salas para compartir documentos."}


def _ensure():
    if not available()["configured"]:
        raise HTTPException(503, "Las salas requieren Supabase, clave de servicio y su migración privada.")


async def rpc(name: str, payload: dict, token: str | None = None, *, admin=False):
    _ensure()
    value = await store.db_request("POST", "rpc/" + name,
        get_settings().SUPABASE_SERVICE_ROLE_KEY if admin else token or "", service=admin, json=payload)
    if isinstance(value, dict) and value.get("error"):
        codes = {"NOT_FOUND": (404, "El elemento no existe en esta sala o cuenta."),
            "LINK_UNAVAILABLE": (404, "El enlace de la sala caducó o fue revocado."),
            "INACTIVE": (409, "La sala está cerrada o caducó."), "FORBIDDEN": (403, "Este enlace no permite realizar esa operación."),
            "INVALID_INPUT": (422, "Revisa los datos, permisos y versiones de los documentos."),
            "LIMIT": (429, "Se alcanzó una cuota de la sala. Revisa sus archivos o inténtalo más tarde."),
            "BUSY": (409, "El aporte ya está incorporado o se está procesando. Recarga antes de continuar."),
            "CONFLICT": (409, "El estado del aporte cambió. Recarga la sala antes de continuar.")}
        status, detail = codes.get(value["error"], (409, "La sala cambió mientras se procesaba la operación."))
        raise HTTPException(status, detail)
    if not isinstance(value, (list, dict)):
        raise HTTPException(502, "No se recibió confirmación del servicio de salas.")
    return value


def public_room(record: dict) -> dict:
    return {key: record.get(key) for key in ("id", "title", "description", "matter_id", "status", "created_at", "expires_at", "revoked_at", "version", "documents", "links", "uploads", "audit", "audit_count")}


async def owned(owner: str, token: str, room_id: str) -> dict:
    values = await rpc("despacho_rooms_list", {"p_id": store.uuid_text(room_id)}, token)
    if not isinstance(values, list) or not values:
        raise HTTPException(404, "La sala no existe en tu cuenta.")
    if values[0].get("owner_id") != store.uuid_text(owner):
        raise HTTPException(502, "La sala devuelta no corresponde a tu cuenta.")
    return values[0]


async def list_rooms(owner: str, token: str, *, offset=0, limit=50) -> dict:
    values = await rpc("despacho_rooms_list", {"p_id": None, "p_offset": offset, "p_limit": limit}, token)
    if not isinstance(values, list) or any(v.get("owner_id") != store.uuid_text(owner) for v in values):
        raise HTTPException(502, "No se pudo comprobar la lista de salas de tu cuenta.")
    return {"rooms": [public_room(v) for v in values], "has_more": len(values) == limit, "offset": offset, "limit": limit, "capabilities": available()}


def _path(owner: str, room_id: str, object_id: str, *, upload=False) -> str:
    return "/".join([store.uuid_text(owner), store.uuid_text(room_id), "uploads" if upload else "documents", store.uuid_text(object_id) + (".bin" if upload else ".pdf")])


async def _storage(method: str, path: str, content: bytes | None = None) -> bytes | None:
    _ensure()
    if not re.fullmatch(r"[a-f0-9-]{36}/[a-f0-9-]{36}/(?:documents/[a-f0-9-]{36}\.pdf|uploads/[a-f0-9-]{36}\.bin)", path):
        raise HTTPException(422, "La ruta de la sala no es válida.")
    base, headers = store.connection(get_settings().SUPABASE_SERVICE_ROLE_KEY, service=True)
    headers.update({"Content-Type": "application/pdf" if path.endswith(".pdf") else "application/octet-stream", "x-upsert": "false"})
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
            if method == "DELETE":
                headers["Content-Type"] = "application/json"
                response = await client.request(method, base + "/storage/v1/object/" + BUCKET, headers=headers, json={"prefixes": [path]})
                if response.status_code not in (200, 204):
                    raise HTTPException(502, "No se confirmó el borrado del archivo privado de la sala.")
                return None
            url = base + "/storage/v1/object/" + ("authenticated/" if method == "GET" else "") + BUCKET + "/" + quote(path, safe="/")
            async with client.stream(method, url, headers=headers, content=content) as response:
                if response.status_code == 404:
                    raise HTTPException(404, "El archivo de la sala no está disponible.")
                if response.status_code not in (200, 201):
                    raise HTTPException(502, "No se pudo guardar o recuperar el archivo privado de la sala.")
                if method != "GET":
                    return None
                parts, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_SNAPSHOTS_BYTES:
                        raise HTTPException(413, "El archivo supera el límite de la sala.")
                    parts.append(chunk)
                return b"".join(parts)
    except httpx.HTTPError:
        raise HTTPException(502, "No se confirmó la operación con el almacenamiento privado de salas.") from None


async def _verified(path: str, sha: str) -> bytes:
    binary = await _storage("GET", path)
    if not binary or not hmac.compare_digest(hashlib.sha256(binary).hexdigest(), sha):
        raise HTTPException(409, "La huella del archivo no coincide. La descarga se detuvo.")
    return binary


async def _put(path: str, binary: bytes):
    try:
        await _storage("POST", path, binary)
    except HTTPException as exc:
        # A timeout/duplicate can follow a successful write. Verify before retry.
        try:
            await _verified(path, hashlib.sha256(binary).hexdigest())
            return
        except HTTPException:
            raise exc from None


async def create(owner: str, token: str, title: str, description: str, document_ids: list[str], matter_id: str | None, expires_days: int) -> dict:
    _ensure()
    owner, room_id = store.uuid_text(owner), str(uuid4())
    if matter_id:
        await store.fetch_item(owner, token, matter_id, kind="matter")
    snapshots, originals, size, total_pages = [], [], 0, 0
    for document_id in document_ids:
        item = await store.fetch_item(owner, token, document_id, kind="document")
        data = item["data"]
        if data.get("mime") == "application/pdf" and data.get("storage_path"):
            if data.get("pagination") == "segments":
                raise HTTPException(409, "Un PDF seleccionado tiene texto modificado. Exporta y carga la versión actualizada antes de compartirla.")
            binary = await store.download_bytes(owner, token, data["storage_path"])
            item["_representation"] = "pdf_original"
        else:
            if not str(data.get("text", "")).strip():
                raise HTTPException(422, "Un documento no contiene texto ni un PDF legible para compartir.")
            binary = await anyio.to_thread.run_sync(make_pdf, item["title"], data["text"])
            item["_representation"] = "pdf_generado_desde_texto"
        frozen, details = await anyio.to_thread.run_sync(signing._combine, [(item, binary)])
        size += len(frozen); total_pages += details[0]["pages"]
        if size > MAX_SNAPSHOTS_BYTES or total_pages > 500:
            raise HTTPException(413, "Una sala admite 25 MB y 500 páginas compartidas. Divide los documentos en varias salas.")
        snapshots.append({"id": item["id"], "title": item["title"], "source_version": item["version"], "sha256": signing.digest(frozen),
            "bytes": len(frozen), "pages": details[0]["pages"], "representation": item["_representation"]})
        originals.append((_path(owner, room_id, item["id"]), frozen))
    for path, binary in originals:
        await _put(path, binary)
    try:
        result = await rpc("despacho_rooms_create", {"p_id": room_id, "p_title": title, "p_description": description,
            "p_documents": snapshots, "p_matter": matter_id, "p_days": expires_days}, token)
    except HTTPException as exc:
        try:
            recovered = await owned(owner, token, room_id)
        except HTTPException as lookup:
            if lookup.status_code != 404:
                raise HTTPException(502, "No se confirmó la creación. Revisa la lista de salas antes de repetirla; las copias se conservaron para no perder una operación ya completada.") from None
        else:
            if recovered.get("documents") == snapshots:
                return public_room(recovered)
            raise HTTPException(409, "La sala cambió. Revisa su contenido antes de repetir la creación.") from None
        for path, _ in originals:
            await _storage("DELETE", path)
        raise exc
    return public_room(result)


async def create_link(owner: str, token: str, room_id: str, label: str, can_view: bool, can_download: bool, can_upload: bool, days: int, origin: str) -> dict:
    await owned(owner, token, room_id)
    secret = secrets.token_urlsafe(32)
    result = await rpc("despacho_rooms_link", {"p_room": store.uuid_text(room_id), "p_id": str(uuid4()), "p_label": label,
        "p_hash": signing.digest(secret), "p_view": can_view, "p_download": can_download, "p_upload": can_upload, "p_days": days}, token)
    return {"link": result, "url": origin + "/sala-cliente#" + secret,
            "notice": "Copia este enlace y compártelo con su destinatario. No se ha enviado ningún mensaje."}


async def revoke(owner: str, token: str, room_id: str, link_id: str | None = None) -> dict:
    await owned(owner, token, room_id)
    result = await rpc("despacho_rooms_revoke", {"p_room": store.uuid_text(room_id), "p_link": store.uuid_text(link_id) if link_id else None}, token)
    return public_room(result)


def _selected(rows: list, object_id: str) -> dict:
    object_id = store.uuid_text(object_id)
    selected = next((v for v in rows if v.get("id") == object_id), None)
    if not selected:
        raise HTTPException(404, "El archivo no pertenece a esta sala.")
    return selected


async def private_document(owner: str, token: str, room_id: str, document_id: str) -> tuple[str, bytes]:
    room = await owned(owner, token, room_id)
    doc = _selected(room["documents"], document_id)
    return doc["title"], await _verified(_path(owner, room_id, document_id), doc["sha256"])


async def public_record(secret: str, *, document_id: str | None = None, mode="open", ip="", agent="") -> dict:
    signing.check_token(secret)
    return await rpc("despacho_rooms_public", {"p_hash": signing.digest(secret), "p_document": document_id,
        "p_mode": mode, "p_ip": ip[:64], "p_agent": agent[:512]}, admin=True)


async def public_view(secret: str, *, ip: str, agent: str) -> dict:
    record = await public_record(secret, ip=ip, agent=agent)
    return {**{k: record.get(k) for k in ("id", "title", "description", "expires_at", "documents", "link")},
        "notice": "Las copias PDF están fijadas para esta sala. Cada apertura o descarga se comprueba y registra. El enlace permite acceso a quien lo posea; no verifica su identidad.",
        "max_upload_bytes": MAX_FILE_BYTES}


def watermark(binary: bytes, label: str, link_id: str, at: str) -> bytes:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    reader, writer = PdfReader(io.BytesIO(binary)), PdfWriter()
    try:
        for page in reader.pages:
            writer.add_page(page)
            page = writer.pages[-1]
            if page.rotation:
                page.transfer_rotation_to_content()
            width, height = float(page.mediabox.width), float(page.mediabox.height)
            overlay = io.BytesIO()
            drawing = canvas.Canvas(overlay, pagesize=(width, height))
            drawing.saveState(); drawing.setFillColorRGB(.18, .28, .24)
            drawing.setFillAlpha(.13); drawing.translate(width / 2, height / 2); drawing.rotate(35)
            drawing.setFont("Helvetica-Bold", max(12, min(30, width / 24)))
            drawing.drawCentredString(0, 0, "EL MEMORIALISTA · COPIA COMPARTIDA")
            drawing.restoreState(); drawing.setFont("Helvetica", 7); drawing.setFillColorRGB(.25, .3, .28)
            drawing.drawString(18, 12, (label[:55] + " · " + at + " · " + link_id[:8])[:120])
            drawing.save(); page.merge_page(PdfReader(io.BytesIO(overlay.getvalue())).pages[0])
        output = io.BytesIO(); writer.write(output)
        result = output.getvalue()
        if len(result) > 40 * 1024 * 1024:
            raise HTTPException(413, "La copia marcada supera el límite de descarga. Solicita una sala con archivos más pequeños.")
        return result
    finally:
        writer.close()


async def public_document(secret: str, document_id: str, mode: str, *, ip: str, agent: str) -> tuple[str, bytes]:
    record = await public_record(secret, document_id=store.uuid_text(document_id), mode=mode, ip=ip, agent=agent)
    doc = record["document"]
    original = await _verified(_path(record["owner_id"], record["id"], document_id), doc["sha256"])
    stamped = await anyio.to_thread.run_sync(watermark, original, record["link"]["label"], record["link"]["id"], datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    # A room revoked while preparing a large PDF must not yield that new copy.
    await public_record(secret, mode="check")
    return doc["title"], stamped


def validate_upload(filename: str, binary: bytes) -> tuple[str, str]:
    filename = PurePosixPath(str(filename).replace("\\", "/")).name.strip()
    if not filename or len(filename) > 200 or re.search(r"[\x00-\x1f\x7f]", filename):
        raise HTTPException(422, "El nombre del archivo no es válido.")
    if not binary or len(binary) > MAX_FILE_BYTES:
        raise HTTPException(413, "Cada aporte admite un archivo de entre 1 byte y 10 MB.")
    suffix = PurePosixPath(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            from pypdf import PdfReader
            if not binary.lstrip().startswith(b"%PDF-"):
                raise ValueError()
            reader = PdfReader(io.BytesIO(binary))
            if reader.is_encrypted or not 1 <= len(reader.pages) <= 500:
                raise ValueError()
            mime = "application/pdf"
        elif suffix == ".docx":
            with zipfile.ZipFile(io.BytesIO(binary)) as archive:
                infos = archive.infolist()
                if len(infos) > 1500 or sum(i.file_size for i in infos) > 40 * 1024 * 1024 or "word/document.xml" not in archive.namelist():
                    raise ValueError()
                for entry in infos:
                    if entry.flag_bits & 1 or ".." in PurePosixPath(entry.filename).parts or entry.filename.startswith(("/", "\\")) or entry.file_size > 8 * 1024 * 1024:
                        raise ValueError()
                    if "vbaproject" in entry.filename.lower() or (entry.file_size > 1_000_000 and entry.file_size / max(1, entry.compress_size) > 200):
                        raise ValueError()
                xml = archive.read("word/document.xml")
                if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                    raise ValueError()
            mime = DOCX
        elif suffix == ".txt":
            text = binary.decode("utf-8-sig")
            if "\x00" in text:
                raise ValueError()
            mime = "text/plain"
        else:
            raise HTTPException(415, "La sala recibe PDF, DOCX y TXT. Exporta una copia compatible.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "El archivo no corresponde a un PDF, DOCX o TXT válido dentro de los límites de la sala.") from None
    return filename, mime


async def public_upload(secret: str, request_id: str, filename: str, binary: bytes, *, ip: str) -> dict:
    access = await public_record(secret, mode="upload", ip=ip)
    filename, mime = await anyio.to_thread.run_sync(validate_upload, filename, binary)
    row = await rpc("despacho_rooms_upload_reserve", {"p_hash": signing.digest(secret), "p_id": str(uuid4()),
        "p_request": store.uuid_text(request_id), "p_filename": filename, "p_mime": mime, "p_bytes": len(binary),
        "p_sha": signing.digest(binary), "p_ip": ip[:64]}, admin=True)
    if row["status"] in ("received", "importing", "imported"):
        return {"received": True, "id": row["id"], "filename": row["filename"], "idempotent": True}
    if row["status"] != "pending":
        raise HTTPException(409, "Este aporte fue rechazado o falló. Selecciona el archivo de nuevo para iniciar otro envío.")
    path = _path(access["owner_id"], access["id"], row["id"], upload=True)
    await _put(path, binary)
    try:
        saved = await rpc("despacho_rooms_upload_finish", {"p_hash": signing.digest(secret), "p_id": row["id"], "p_success": True}, admin=True)
    except HTTPException:
        # Leave the original for a retry with the same request ID. It can have
        # committed; deleting on an uncertain result would lose the received file.
        raise HTTPException(502, "No se confirmó la recepción. Usa Reintentar con este mismo archivo; el sistema comprobará si ya llegó sin duplicarlo.") from None
    return {"received": True, "id": saved["id"], "filename": filename,
            "notice": "El aporte quedó recibido para revisión. No se modificó ningún documento compartido."}


async def private_upload(owner: str, token: str, room_id: str, upload_id: str) -> tuple[str, str, bytes]:
    room = await owned(owner, token, room_id)
    row = _selected(room["uploads"], upload_id)
    if row["status"] in ("pending", "failed", "rejected"):
        raise HTTPException(409, "El aporte no está disponible para descargar en su estado actual.")
    binary = await _verified(_path(owner, room_id, upload_id, upload=True), row["sha256"])
    return row["filename"], row["mime"], binary


async def import_upload(owner: str, token: str, room_id: str, upload_id: str) -> dict:
    room = await owned(owner, token, room_id)
    lease = str(uuid4())
    row = await rpc("despacho_rooms_upload_claim", {"p_room": store.uuid_text(room_id), "p_id": store.uuid_text(upload_id), "p_lease": lease}, token)
    item_id = row["item_id"]
    try:
        item = await store.fetch_item(owner, token, item_id, kind="document")
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        item = None
    if item and item["data"].get("room_upload_id") != upload_id:
        raise HTTPException(409, "El destino del aporte no coincide. No se modificó el documento existente.")
    if row["status"] == "imported":
        if item is None:
            raise HTTPException(409, "El aporte ya se incorporó, pero ese documento se eliminó después del DMS.")
        return {"item": item, "idempotent": True}
    path = None
    try:
        if item is None:
            from app.services.despacho_ai import extract_document
            binary = await _verified(_path(owner, room_id, upload_id, upload=True), row["sha256"])
            parsed = await anyio.to_thread.run_sync(extract_document, binary, row["filename"])
            suffix = PurePosixPath(row["filename"]).suffix.lower()
            # The destination is fixed across retries; a lease cannot produce
            # several DMS originals for the same uploaded file.
            path = f"{store.uuid_text(owner)}/{item_id}/{store.uuid_text(upload_id)}{suffix}"
            payload = {"kind": "document", "title": row["filename"][:240], "matter_id": room.get("matter_id"),
                "data": {**parsed, "filename": row["filename"], "storage_path": path, "uploaded_at": store.utcnow(), "room_upload_id": upload_id,
                    "external_source": {"provider": "client_room", "room_id": room_id, "link_id": row["link_id"], "sha256": row["sha256"]}, "versions": []}}
            store.validate_payload(payload, user_id=owner)
            try:
                await store.upload_bytes(owner, token, path, binary, row["mime"])
            except HTTPException:
                existing = await store.download_bytes(owner, token, path)
                if not hmac.compare_digest(signing.digest(existing), row["sha256"]):
                    raise HTTPException(409, "El original de destino no coincide con el aporte.") from None
            try:
                item = await store.create_item(owner, token, payload, item_id=item_id)
            except HTTPException:
                item = await store.fetch_item(owner, token, item_id, kind="document")
                if item["data"].get("room_upload_id") != upload_id:
                    raise HTTPException(409, "No se pudo comprobar la incorporación del aporte.") from None
        saved = await rpc("despacho_rooms_upload_imported", {"p_room": room_id, "p_id": upload_id, "p_lease": lease, "p_success": True}, token)
        return {"item": item, "upload": saved}
    except HTTPException:
        # Preserve any committed document/original. Retrying claims the same ID
        # and verifies its ownership instead of creating another DMS document.
        try:
            await rpc("despacho_rooms_upload_imported", {"p_room": room_id, "p_id": upload_id, "p_lease": lease, "p_success": False}, token)
        except HTTPException:
            pass
        raise


async def reject_upload(owner: str, token: str, room_id: str, upload_id: str) -> dict:
    await owned(owner, token, room_id)
    row = await rpc("despacho_rooms_upload_reject", {"p_room": store.uuid_text(room_id), "p_id": store.uuid_text(upload_id)}, token)
    await _storage("DELETE", _path(owner, room_id, upload_id, upload=True))
    return {"upload": row, "deleted": True}


async def export_owner(owner: str, token: str) -> dict:
    owner = store.uuid_text(owner)
    rows = await store.db_request("POST", "rpc/despacho_rooms_export", token, service=False, json={"p_owner": owner})
    if isinstance(rows, dict) and rows.get("error"):
        raise HTTPException(403, "No se autorizó la exportación de salas de esta cuenta.")
    if not isinstance(rows, list) or any(v.get("owner_id") != owner for v in rows):
        raise HTTPException(502, "La exportación de salas no corresponde a esta cuenta.")
    return {"rooms": [public_room(r) for r in rows], "links": "Los secretos de los enlaces no se exportan.",
            "binary_scope": "Descarga las copias y los aportes que necesites conservar antes de eliminar la cuenta."}


async def purge_owner_storage(owner: str) -> None:
    await signing.purge_bucket_owner(owner, BUCKET)
