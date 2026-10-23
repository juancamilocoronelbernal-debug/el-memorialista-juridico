"""Workspace persistence. Every ordinary request uses the owner's JWT and RLS.

No local or service-role fallback is used when a user's database is unavailable.
"""
from __future__ import annotations

import copy
import hmac
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException

from app.config import get_settings

log = logging.getLogger("memorialista.despacho")
TABLE = "despacho_items"
BUCKET = "despacho-documentos"
KINDS = frozenset({"matter", "document", "conversation", "event", "monitor", "playbook", "table", "source"})
MAX_ITEM_BYTES = 4 * 1024 * 1024
MAX_BACKUP_BYTES = 24 * 1024 * 1024
MAX_ITEMS = 2000
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def uuid_text(value: Any, field: str = "id") -> str:
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422, f"El identificador {field} no es válido.") from None


def is_service_token(token: str) -> bool:
    configured = str(get_settings().SUPABASE_SERVICE_ROLE_KEY or "").strip()
    return bool(configured and token and hmac.compare_digest(token, configured))


def connection(token: str, *, service: bool = False) -> tuple[str, dict]:
    s = get_settings()
    # Sólo los trabajadores poseen esta credencial. Una sesión de usuario jamás
    # se eleva como respaldo ante errores de RLS o de disponibilidad.
    key = s.SUPABASE_SERVICE_ROLE_KEY if service or is_service_token(token) else s.SUPABASE_ANON_KEY
    if not s.SUPABASE_URL or not key:
        raise HTTPException(503, "El almacenamiento del despacho todavía no está configurado.")
    if not token:
        raise HTTPException(401, "Inicia sesión para acceder a tus asuntos.")
    return s.SUPABASE_URL.rstrip("/"), {
        "apikey": key, "Authorization": "Bearer " + token,
        "Content-Type": "application/json", "Prefer": "return=representation",
    }


async def db_request(method: str, path: str, token: str, *, service: bool = False, **kwargs):
    base, headers = connection(token, service=service)
    headers.update(kwargs.pop("headers", {}))
    try:
        async with httpx.AsyncClient(timeout=35, follow_redirects=False) as client:
            response = await client.request(method, base + "/rest/v1/" + path, headers=headers, **kwargs)
    except httpx.HTTPError:
        raise HTTPException(503, "No se pudo comunicar con el almacenamiento. Puedes volver a intentarlo.") from None
    if response.status_code in (401, 403):
        raise HTTPException(403, "Tu sesión no tiene permiso para esta operación. Vuelve a iniciar sesión.")
    if response.status_code == 404:
        raise HTTPException(503, "Falta instalar la migración del despacho en Supabase.")
    if response.status_code == 409:
        raise HTTPException(409, "El registro cambió o tiene elementos relacionados. Recarga antes de continuar.")
    if response.status_code not in (200, 201, 204, 206):
        code = ""
        try:
            code = str(response.json().get("code", ""))
        except (ValueError, AttributeError):
            pass
        if code in {"42P01", "42883", "PGRST202", "PGRST204", "PGRST205"}:
            raise HTTPException(503, "Falta instalar o actualizar la migración del despacho en Supabase.")
        if code in {"23503", "23505", "40001", "55000"}:
            raise HTTPException(409, "El registro cambió, está protegido o conserva elementos relacionados.")
        if code in {"23514", "22023", "22007"}:
            raise HTTPException(422, "Los datos del registro no cumplen las restricciones del despacho.")
        log.warning("Workspace database failed: status=%s code=%s", response.status_code, code)
        raise HTTPException(502, "El almacenamiento no pudo completar la operación.")
    if response.status_code == 204 or not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        raise HTTPException(502, "El almacenamiento devolvió una respuesta no válida.") from None


def public_item(row: dict, user_id: str | None = None) -> dict:
    if not isinstance(row, dict) or (user_id and row.get("owner_id") != user_id):
        raise HTTPException(502, "El almacenamiento devolvió un registro fuera de tu cuenta.")
    return {k: row.get(k) for k in ("id", "kind", "title", "matter_id", "data", "version", "created_at", "updated_at")}


async def fetch_item(user_id: str, token: str, item_id: str, *, kind: str | None = None) -> dict:
    owner, item_id = uuid_text(user_id), uuid_text(item_id)
    params = {"select": "*", "id": "eq." + item_id, "owner_id": "eq." + owner, "limit": 1}
    if kind:
        params["kind"] = "eq." + kind
    rows = await db_request("GET", TABLE, token, params=params)
    if not isinstance(rows, list) or not rows:
        raise HTTPException(404, "El elemento no existe en tu cuenta.")
    return public_item(rows[0], owner)


async def list_items(user_id: str, token: str, *, kind: str | None = None,
                     matter_id: str | None = None, offset: int = 0, limit: int = 100) -> dict:
    owner = uuid_text(user_id)
    if kind and kind not in KINDS:
        raise HTTPException(422, "Tipo de elemento desconocido.")
    if offset < 0 or offset > 100000 or not 1 <= limit <= 200:
        raise HTTPException(422, "La paginación no es válida.")
    params = {"select": "*", "owner_id": "eq." + owner, "order": "updated_at.desc,id.asc", "offset": offset, "limit": limit + 1}
    if kind:
        params["kind"] = "eq." + kind
    if matter_id:
        params["matter_id"] = "eq." + uuid_text(matter_id, "asunto")
    rows = await db_request("GET", TABLE, token, params=params)
    if not isinstance(rows, list):
        raise HTTPException(502, "No se pudo leer la lista de elementos.")
    return {"items": [public_item(r, owner) for r in rows[:limit]], "has_more": len(rows) > limit}


def validate_payload(payload: dict, *, kind: str | None = None, user_id: str | None = None) -> dict:
    if not isinstance(payload, dict):
        raise HTTPException(422, "El elemento debe ser un objeto.")
    kind = kind or payload.get("kind")
    if kind not in KINDS:
        raise HTTPException(422, "Tipo de elemento desconocido.")
    title = payload.get("title", "Sin título")
    if not isinstance(title, str) or not title.strip() or len(title) > 240:
        raise HTTPException(422, "Escribe un título de hasta 240 caracteres.")
    data = payload.get("data", {})
    if not isinstance(data, dict):
        raise HTTPException(422, "Los datos deben ser un objeto.")
    try:
        encoded = json.dumps(data, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, RecursionError):
        raise HTTPException(422, "Los datos contienen valores no admitidos.") from None
    if len(encoded.encode()) > MAX_ITEM_BYTES:
        raise HTTPException(413, "Este registro supera 4 MB. Divide el expediente o conserva menos texto en cada documento.")
    data = copy.deepcopy(data)
    matter_id = uuid_text(payload["matter_id"], "asunto") if payload.get("matter_id") else None
    if kind == "matter" and matter_id:
        raise HTTPException(422, "Un asunto no puede estar dentro de otro asunto.")
    if kind == "document":
        if not isinstance(data.get("text", ""), str) or len(data.get("text", "")) > 500_000:
            raise HTTPException(413, "El documento admite hasta 500.000 caracteres extraídos.")
        pages = data.get("pages", [])
        if not isinstance(pages, list) or len(pages) > 500:
            raise HTTPException(422, "La lista de páginas no es válida.")
        for page in pages:
            if (not isinstance(page, dict) or type(page.get("page")) is not int or page["page"] < 1
                    or not isinstance(page.get("text"), str)):
                raise HTTPException(422, "Una página del documento no es válida.")
        versions = data.get("versions", [])
        if not isinstance(versions, list) or len(versions) > 50 or any(not isinstance(v, dict) for v in versions):
            raise HTTPException(422, "La lista de versiones no es válida o supera 50 versiones.")
        if user_id:
            for entry in [data, *versions]:
                if entry.get("storage_path"):
                    validate_storage_path(entry["storage_path"], user_id)
        for flag in ("locked", "final"):
            if flag in data and type(data[flag]) is not bool:
                raise HTTPException(422, "La protección del documento debe ser verdadera o falsa.")
    elif kind == "conversation":
        messages = data.get("messages", [])
        if not isinstance(messages, list) or len(messages) > 500:
            raise HTTPException(422, "Una conversación admite hasta 500 mensajes.")
        for message in messages:
            if (not isinstance(message, dict) or message.get("role") not in {"user", "assistant"}
                    or not isinstance(message.get("content"), str) or len(message["content"]) > 120_000):
                raise HTTPException(422, "Un mensaje de la conversación no es válido.")
    elif kind == "monitor":
        from app.services.despacho_fetch import validate_url
        data["url"] = validate_url(data.get("url", ""))
        keywords = data.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [s.strip() for s in keywords.split(",") if s.strip()]
        if not isinstance(keywords, list) or len(keywords) > 20 or any(not isinstance(s, str) or len(s) > 120 for s in keywords):
            raise HTTPException(422, "Indica hasta 20 palabras o frases de búsqueda.")
        data["keywords"] = keywords
        if data.get("analysis_mode", "keywords") not in {"keywords", "semantic"}:
            raise HTTPException(422, "Elige análisis por palabras clave o por condición jurídica.")
        condition = data.get("condition", "")
        if not isinstance(condition, str) or len(condition) > 4000:
            raise HTTPException(422, "La condición del monitor admite hasta 4.000 caracteres.")
        if data.get("analysis_mode") == "semantic" and not condition.strip():
            raise HTTPException(422, "Describe qué debe considerar relevante el monitor.")
        if "follow_links" in data and type(data["follow_links"]) is not bool:
            raise HTTPException(422, "La opción de seguir publicaciones debe ser verdadera o falsa.")
        if type(data.get("max_documents", 5)) is not int or not 1 <= data.get("max_documents", 5) <= 10:
            raise HTTPException(422, "Cada revisión admite entre uno y diez documentos enlazados.")
        interval = data.get("interval_minutes", 60)
        if type(interval) is not int or not 15 <= interval <= 10080:
            raise HTTPException(422, "La frecuencia debe estar entre 15 minutos y 7 días.")
        data["interval_minutes"] = interval
        if type(data.get("enabled", False)) is not bool:
            raise HTTPException(422, "El estado del monitor no es válido.")
        findings = data.get("findings", [])
        if not isinstance(findings, list) or len(findings) > 100 or any(not isinstance(f, dict) for f in findings):
            raise HTTPException(422, "El historial del monitor no es válido.")
    elif kind == "event":
        if data.get("date"):
            try:
                datetime.strptime(data["date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                raise HTTPException(422, "La fecha del acontecimiento no es válida.") from None
        if data.get("document_id"):
            data["document_id"] = uuid_text(data["document_id"], "documento")
    elif kind == "playbook":
        if not isinstance(data.get("instructions", ""), str) or len(data.get("instructions", "")) > 12000:
            raise HTTPException(422, "Las instrucciones admiten hasta 12.000 caracteres.")
    return {"kind": kind, "title": title.strip(), "matter_id": matter_id, "data": data}


async def _validate_relations(user_id: str, token: str, payload: dict) -> None:
    if payload.get("matter_id"):
        await fetch_item(user_id, token, payload["matter_id"], kind="matter")
    doc_id = payload.get("data", {}).get("document_id")
    if doc_id and payload["kind"] == "event":
        doc = await fetch_item(user_id, token, doc_id, kind="document")
        if payload.get("matter_id") and doc.get("matter_id") != payload["matter_id"]:
            raise HTTPException(422, "La prueba pertenece a otro asunto.")


async def create_item(user_id: str, token: str, payload: dict, *, item_id: str | None = None) -> dict:
    owner = uuid_text(user_id)
    validated = validate_payload(payload, user_id=owner)
    await _validate_relations(owner, token, validated)
    rows = await db_request("POST", TABLE, token, json={
        **validated, "id": uuid_text(item_id) if item_id else str(uuid4()), "owner_id": owner, "version": 1,
    })
    if not isinstance(rows, list) or len(rows) != 1:
        raise HTTPException(502, "No se confirmó el guardado del elemento.")
    return public_item(rows[0], owner)


def _assert_document_change(old: dict, new: dict) -> None:
    if old["kind"] != "document":
        return
    before, after = old["data"], new["data"]
    if before.get("locked") or before.get("final"):
        # Unlocking is a separate, explicit edit. It must not simultaneously replace content.
        changed = any(before.get(k) != after.get(k) for k in ("text", "pages", "versions", "storage_path", "filename", "mime"))
        if changed:
            raise HTTPException(409, "Desprotege el documento antes de modificarlo o restaurar una versión.")


async def update_item(user_id: str, token: str, item_id: str, payload: dict, expected_version: int) -> dict:
    if type(expected_version) is not int or expected_version < 1:
        raise HTTPException(422, "Debes indicar la versión que estás editando.")
    old = await fetch_item(user_id, token, item_id)
    if old["version"] != expected_version:
        raise HTTPException(409, "Otra ventana modificó este elemento. Recarga para conservar ambos cambios.")
    merged = {**old, **{k: v for k, v in payload.items() if k in {"title", "matter_id", "data"}}}
    if old["kind"] == "document" and isinstance(merged.get("data"), dict):
        data = copy.deepcopy(merged["data"])
        prior = old["data"]
        content_changed = any(data.get(k) != prior.get(k) for k in ("text", "pages", "storage_path"))
        # The server owns historical snapshots; a client's incomplete draft cannot erase history.
        history = copy.deepcopy(prior.get("versions", []))
        if content_changed:
            history.append({"title": old["title"], "created_at": utcnow(), "version": old["version"],
                **{k: copy.deepcopy(prior[k]) for k in ("text", "pages", "pagination", "storage_path", "filename", "mime", "warnings") if k in prior}})
            if data.get("text") != prior.get("text") and data.get("pages") == prior.get("pages"):
                data["pages"] = []
                data["pagination"] = "segments"
        data["versions"] = history
        merged["data"] = data
    validated = validate_payload(merged, kind=old["kind"], user_id=user_id)
    _assert_document_change(old, validated)
    await _validate_relations(user_id, token, validated)
    rows = await db_request("PATCH", TABLE, token,
        params={"id": "eq." + old["id"], "owner_id": "eq." + uuid_text(user_id), "version": "eq." + str(expected_version)},
        json={k: v for k, v in {**validated, "version": expected_version + 1}.items() if k != "kind"})
    if not isinstance(rows, list) or len(rows) != 1:
        raise HTTPException(409, "El elemento cambió mientras se guardaba. Recarga antes de continuar.")
    return public_item(rows[0], user_id)


async def all_items(user_id: str, token: str) -> list:
    items = []
    while True:
        page = await list_items(user_id, token, offset=len(items), limit=200)
        items.extend(page["items"])
        if len(items) > MAX_ITEMS:
            raise HTTPException(413, "La copia excede 2.000 registros. Solicita una exportación administrativa.")
        if not page["has_more"]:
            break
    return items


async def delete_item(user_id: str, token: str, item_id: str, expected_version: int) -> dict:
    item = await fetch_item(user_id, token, item_id)
    if item["version"] != expected_version:
        raise HTTPException(409, "El elemento cambió. Recarga antes de eliminarlo.")
    if item["kind"] == "document" and (item["data"].get("locked") or item["data"].get("final")):
        raise HTTPException(409, "Desprotege el documento antes de eliminarlo.")
    if item["kind"] == "matter":
        if (await list_items(user_id, token, matter_id=item_id, limit=1))["items"]:
            raise HTTPException(409, "El asunto conserva documentos u otros elementos. Muévelos o elimínalos primero.")
    rows = await db_request("DELETE", TABLE, token, params={"id": "eq." + item["id"], "owner_id": "eq." + uuid_text(user_id), "version": "eq." + str(expected_version)})
    if not isinstance(rows, list) or len(rows) != 1:
        raise HTTPException(409, "No se eliminó el registro porque cambió su versión.")
    warnings = []
    if item["kind"] == "document":
        try:
            remaining = await all_items(user_id, token)
            used = {p for row in remaining if row["kind"] == "document" for p in document_paths(row)}
            paths = [p for p in document_paths(item) if p not in used]
            await remove_storage_paths(user_id, token, paths)
        except HTTPException:
            warnings.append("El registro se eliminó, pero algún archivo original puede seguir almacenado. Contacta con el administrador para completar la limpieza.")
    return {"deleted": True, "warnings": warnings}


def validate_storage_path(path: Any, user_id: str) -> str:
    if not isinstance(path, str) or not re.fullmatch(r"[0-9a-f-]{36}/[0-9a-f-]{36}/[0-9a-f-]{36}\.[a-z0-9]{1,8}", path):
        raise HTTPException(422, "La ruta del archivo no es válida.")
    if path.split("/", 1)[0] != uuid_text(user_id):
        raise HTTPException(403, "El archivo no pertenece a tu cuenta.")
    return path


def document_paths(item: dict) -> list[str]:
    data = item.get("data") or {}
    return list(dict.fromkeys(v["storage_path"] for v in [data, *data.get("versions", [])]
                              if isinstance(v, dict) and v.get("storage_path")))


async def upload_bytes(user_id: str, token: str, path: str, content: bytes, mime: str) -> None:
    validate_storage_path(path, user_id)
    base, headers = connection(token)
    headers.update({"Content-Type": mime, "x-upsert": "false"})
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
            r = await client.post(base + "/storage/v1/object/" + BUCKET + "/" + quote(path, safe="/"), headers=headers, content=content)
    except httpx.HTTPError:
        raise HTTPException(503, "No se pudo subir el original. Inténtalo de nuevo.") from None
    if r.status_code not in (200, 201):
        raise HTTPException(502, "No se pudo guardar el original en el bucket privado del despacho. Revisa su migración y permisos.")


async def download_bytes(user_id: str, token: str, path: str) -> bytes:
    validate_storage_path(path, user_id)
    base, headers = connection(token)
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
            async with client.stream("GET", base + "/storage/v1/object/authenticated/" + BUCKET + "/" + quote(path, safe="/"), headers=headers) as r:
                if r.status_code != 200:
                    raise HTTPException(404, "El original no está disponible en tu almacenamiento.")
                parts, size = [], 0
                async for part in r.aiter_bytes():
                    size += len(part)
                    if size > MAX_UPLOAD_BYTES:
                        raise HTTPException(413, "El archivo supera el límite de descarga de esta instalación.")
                    parts.append(part)
                return b"".join(parts)
    except httpx.HTTPError:
        raise HTTPException(503, "La descarga se interrumpió. Puedes volver a intentarlo.") from None


async def remove_storage_paths(user_id: str, token: str, paths: list[str]) -> None:
    if not paths:
        return
    for path in paths:
        validate_storage_path(path, user_id)
    base, headers = connection(token)
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            r = await client.request("DELETE", base + "/storage/v1/object/" + BUCKET, headers=headers, json={"prefixes": paths})
        if r.status_code not in (200, 204):
            raise HTTPException(502, "No se completó el borrado del archivo original.")
    except httpx.HTTPError:
        raise HTTPException(503, "No se completó el borrado del archivo original.") from None


async def export_workspace(user_id: str, token: str) -> dict:
    items = await all_items(user_id, token)
    result = {"format": "memorialista-despacho", "version": 1, "exported_at": utcnow(), "owner_id": user_id,
              "scope": "Registros, texto extraído y versiones. Los archivos binarios originales se descargan por separado desde Biblioteca.", "items": items}
    if len(json.dumps(result, ensure_ascii=False).encode()) > MAX_BACKUP_BYTES:
        raise HTTPException(413, "El respaldo supera 24 MB. Solicita una exportación administrativa.")
    return result


def _rewrite_refs(value: Any, mapping: dict[str, str]) -> Any:
    # UUIDs may appear in source lists or nested timeline metadata. Replace only exact UUID values.
    if isinstance(value, dict):
        return {k: _rewrite_refs(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [_rewrite_refs(v, mapping) for v in value]
    return mapping.get(value, value) if isinstance(value, str) else value


async def import_workspace(user_id: str, token: str, backup: dict) -> dict:
    if not isinstance(backup, dict) or backup.get("format") != "memorialista-despacho" or backup.get("version") != 1:
        raise HTTPException(422, "Este archivo no es una copia del despacho compatible (versión 1). Las copias ciudadanas se importan en el orientador.")
    try:
        if len(json.dumps(backup, ensure_ascii=False, allow_nan=False).encode()) > MAX_BACKUP_BYTES:
            raise HTTPException(413, "El respaldo supera 24 MB.")
    except (ValueError, TypeError, RecursionError):
        raise HTTPException(422, "La copia contiene valores no admitidos.") from None
    incoming = backup.get("items")
    if not isinstance(incoming, list) or len(incoming) > MAX_ITEMS:
        raise HTTPException(422, "La copia debe contener una lista de hasta 2.000 elementos.")
    normalized, seen = [], set()
    same_owner = backup.get("owner_id") == user_id
    stripped_files = 0
    for raw in incoming:
        if not isinstance(raw, dict):
            raise HTTPException(422, "La copia contiene un elemento inválido.")
        item_id = uuid_text(raw.get("id"))
        if item_id in seen:
            raise HTTPException(422, "La copia repite identificadores; no se importó ningún elemento.")
        seen.add(item_id)
        raw = copy.deepcopy(raw)
        if raw.get("kind") == "document" and not same_owner:
            raw_data = raw.get("data", {})
            if not isinstance(raw_data, dict) or not isinstance(raw_data.get("versions", []), list):
                raise HTTPException(422, "La copia contiene un documento inválido.")
            for data in [raw_data, *raw_data.get("versions", [])]:
                if isinstance(data, dict) and data.pop("storage_path", None):
                    stripped_files += 1
            if not isinstance(raw_data.get("warnings", []), list):
                raise HTTPException(422, "Las advertencias del documento no son válidas.")
            raw_data.setdefault("warnings", []).append("El original binario pertenece a otra cuenta. Vuelve a subirlo para conservarlo aquí.")
        normalized.append({"id": item_id, **validate_payload(raw, user_id=user_id)})
    existing = {row["id"]: row for row in await all_items(user_id, token)}
    normalized_by_id = {r["id"]: r for r in normalized}
    for item in normalized:
        parent = item.get("matter_id")
        if parent:
            target = normalized_by_id.get(parent) or existing.get(parent)
            if not target or target["kind"] != "matter":
                raise HTTPException(422, "La copia contiene una referencia a un asunto ausente.")
        doc_id = item["data"].get("document_id") if item["kind"] == "event" else None
        if doc_id:
            target = normalized_by_id.get(doc_id) or existing.get(doc_id)
            if not target or target["kind"] != "document" or (parent and target.get("matter_id") != parent):
                raise HTTPException(422, "Una prueba de la copia no corresponde al asunto.")
    mapping, conflicts, skipped = {}, 0, 0
    for item in normalized:
        old = existing.get(item["id"])
        if old and all(old.get(k) == item.get(k) for k in ("kind", "title", "matter_id", "data")):
            continue
        mapping[item["id"]] = str(uuid4()) if old else item["id"]
        if old:
            conflicts += 1
    # If an ancestor was copied, its otherwise-identical children also need copies.
    for item in normalized:
        if item.get("matter_id") in mapping and mapping[item["matter_id"]] != item["matter_id"] and item["id"] not in mapping:
            mapping[item["id"]] = str(uuid4())
            conflicts += 1
    for item in normalized:
        doc_id = item["data"].get("document_id") if item["kind"] == "event" else None
        if doc_id in mapping and mapping[doc_id] != doc_id and item["id"] not in mapping:
            mapping[item["id"]] = str(uuid4())
            conflicts += 1
    writes = []
    for item in normalized:
        if item["id"] not in mapping:
            skipped += 1
            continue
        new = _rewrite_refs(item, mapping)
        # Una copia nunca debe conservar la clave única de una sincronización
        # ajena ni competir con el documento original de la misma conexión.
        if new["kind"] == "document" and (not same_owner or mapping[item["id"]] != item["id"]):
            for entry in [new["data"], *new["data"].get("versions", [])]:
                if isinstance(entry, dict):
                    entry.pop("external_key", None)
                    entry.pop("connection_id", None)
                    for field in ("source", "external_source"):
                        if isinstance(entry.get(field), dict):
                            entry[field].pop("connection_id", None)
        if item["id"] in existing:
            new["title"] = (new["title"][:210] + " · copia importada")
        writes.append({**new, "owner_id": uuid_text(user_id), "version": 1})
    # One PostgreSQL transaction. A failed import cannot leave a partially imported tree.
    if writes:
        if len(existing) + len(writes) > MAX_ITEMS:
            raise HTTPException(413, "La importación superaría 2.000 registros. No se importó ningún elemento.")
        writes.sort(key=lambda row: (row["kind"] != "matter", row["kind"] == "event"))
        result = await db_request("POST", "rpc/despacho_importar_items", token, json={"p_items": writes})
        if not isinstance(result, dict) or result.get("imported") != len(writes):
            raise HTTPException(502, "No se recibió la confirmación completa de la importación.")
    return {"imported": len(writes), "conflicts": conflicts, "skipped": skipped, "originals_not_included": stripped_files,
            "warnings": (["Los originales binarios de otra cuenta no se trasladan con este JSON."] if stripped_files else [])}


async def audit_events(user_id: str, token: str, item_id: str, *, limit: int = 100) -> list:
    await fetch_item(user_id, token, item_id)
    rows = await db_request("GET", "despacho_auditoria", token, params={
        "owner_id": "eq." + uuid_text(user_id), "item_id": "eq." + uuid_text(item_id),
        "select": "id,item_id,operation,version,created_at", "order": "created_at.desc", "limit": min(limit, 200)})
    return rows if isinstance(rows, list) else []


async def borrar_archivos_despacho(client, base: str, headers: dict, user_id: str) -> None:
    """Called by account deletion before Auth. Missing migration is an explicit error."""
    from app.services.supabase_service import ErrorSupabase
    root = uuid_text(user_id)
    pending, all_paths, visited = [root + "/"], [], 0
    while pending:
        prefix = pending.pop()
        visited += 1
        if visited > 5000:
            raise ErrorSupabase("El despacho contiene demasiadas carpetas para una baja automática. Solicita una eliminación administrativa.")
        offset = 0
        while True:
            response = await client.post(base + "/storage/v1/object/list/" + BUCKET, headers=headers,
                json={"prefix": prefix, "limit": 1000, "offset": offset, "sortBy": {"column": "name", "order": "asc"}})
            if response.status_code != 200:
                raise ErrorSupabase("No se pudo comprobar el bucket privado del despacho. La cuenta no se ha eliminado.")
            rows = response.json()
            if not isinstance(rows, list):
                raise ErrorSupabase("No se pudo verificar la lista de archivos del despacho.")
            for row in rows:
                name = row.get("name", "")
                if not isinstance(name, str) or not name or "/" in name or name in {".", ".."}:
                    raise ErrorSupabase("Una ruta del despacho no es válida. La baja se detuvo.")
                path = prefix + name
                if row.get("id") is None:
                    pending.append(path + "/")
                else:
                    all_paths.append(path)
            if len(rows) < 1000:
                break
            offset += len(rows)
    for offset in range(0, len(all_paths), 100):
        response = await client.request("DELETE", base + "/storage/v1/object/" + BUCKET, headers=headers,
            json={"prefixes": all_paths[offset:offset + 100]})
        if response.status_code not in (200, 204):
            raise ErrorSupabase("No se completó el borrado de originales del despacho. No se ha eliminado la cuenta.")
