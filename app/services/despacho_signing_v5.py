"""Expedientes de firma: PDF congelado, varios destinatarios y correo con OTP.

El método verifica acceso al correo y registra consentimiento. No acredita un
documento de identidad ni expide certificados de firma digital.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import re
import secrets
from datetime import datetime, timezone
from urllib.parse import quote
from uuid import uuid4

import anyio
import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.services import despacho_delivery as delivery
from app.services import despacho_store as store
from app.services.despacho_export import make_pdf

BUCKET = "despacho-firmas-v5"
MAX_BUNDLE_BYTES = 25 * 1024 * 1024
MAX_BUNDLE_PAGES = 500
CONSENT = "He revisado los documentos del expediente y su huella, verifico mi acceso al correo destinatario y acepto firmarlos electrónicamente."
METHOD = "Enlace privado, código de un solo uso enviado al correo destinatario y aceptación expresa. No incluye verificación documental de identidad ni certificado de firma digital."


def available() -> dict:
    s = get_settings()
    storage = bool(s.SUPABASE_URL and s.SUPABASE_ANON_KEY and s.SUPABASE_SERVICE_ROLE_KEY and s.DESPACHO_SIGNING_ENABLED)
    otp = len(getattr(s, "DESPACHO_SIGNING_OTP_SECRET", "")) >= 32
    mail = delivery.status()
    return {"configured": bool(storage and otp and mail["configured"]), "storage": storage,
            "email": mail["configured"], "otp": otp, "method": METHOD, "bucket": BUCKET,
            "message": "Firma con correo verificado disponible; cada operación comprueba permisos y entrega." if storage and otp and mail["configured"] else "Configura las migraciones, SMTP y DESPACHO_SIGNING_OTP_SECRET para completar firmas verificadas."}


def _ensure(*, email=False):
    status = available()
    if not status["storage"]:
        raise HTTPException(503, "La firma verificada necesita Supabase, clave de servicio y habilitación de firma.")
    if email and not (status["email"] and status["otp"]):
        raise HTTPException(503, "La firma con correo verificado requiere configurar SMTP y el secreto de códigos OTP en el servidor.")


def digest(value: str | bytes) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _otp_hash(token: str, otp: str) -> str:
    secret = getattr(get_settings(), "DESPACHO_SIGNING_OTP_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(503, "El secreto de verificación de firmas no está configurado.")
    return hmac.new(secret.encode(), ("memorialista-signing-v5:" + token + ":" + otp).encode(), hashlib.sha256).hexdigest()


def check_token(token: str) -> str:
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise HTTPException(404, "El enlace de firma no está disponible.")
    return token


def masked_email(value: str) -> str:
    local, _, domain = value.partition("@")
    return (local[:1] + "***@" + domain) if domain else "correo del destinatario"


async def rpc(name: str, payload: dict, token: str | None = None, *, admin=False):
    _ensure()
    if admin:
        token = get_settings().SUPABASE_SERVICE_ROLE_KEY
    result = await store.db_request("POST", "rpc/" + name, token or "", service=admin, json=payload)
    if isinstance(result, dict) and result.get("error"):
        errors = {
            "NOT_FOUND": (404, "La solicitud de firma no existe en tu cuenta."),
            "LINK_UNAVAILABLE": (404, "El enlace caducó, fue sustituido o la solicitud fue cancelada."),
            "INVALID_INPUT": (422, "Revisa los datos de la solicitud y el consentimiento."),
            "NOT_PENDING": (409, "La solicitud ya fue completada o cancelada."),
            "WAIT_TURN": (409, "Otro destinatario debe firmar antes. Vuelve cuando haya completado su turno."),
            "LIMIT": (429, "Se alcanzó el límite de solicitudes. Inténtalo más tarde."),
            "OTP_WAIT": (429, "Espera un minuto antes de pedir otro código."),
            "OTP_LIMIT": (429, "Se alcanzó el límite de códigos o intentos para este enlace. Vuelve más tarde."),
            "OTP_INVALID": (422, "El código es incorrecto, caducó o ya se utilizó. Revisa el último correo recibido."),
            "LINK_WAIT": (429, "Espera treinta segundos antes de sustituir de nuevo este enlace."),
            "DOCUMENT_CHANGED": (409, "La huella no coincide con el expediente. Abre el enlace de nuevo antes de firmar."),
        }
        status, detail = errors.get(result["error"], (409, "La solicitud cambió. Recarga antes de continuar."))
        headers = {"Retry-After": str(result.get("retry_after", 60))} if status == 429 else None
        raise HTTPException(status, detail, headers=headers)
    if not isinstance(result, (dict, list)):
        raise HTTPException(502, "No se recibió confirmación de la operación de firma.")
    return result


def _storage_path(path: str, owner: str | None = None) -> str:
    match = re.fullmatch(r"([a-f0-9-]{36})/([a-f0-9-]{36})/expediente\.pdf", path or "")
    if not match or (owner and match.group(1) != store.uuid_text(owner)):
        raise HTTPException(403, "El original de firma no pertenece a esta cuenta.")
    store.uuid_text(match.group(1)); store.uuid_text(match.group(2))
    return path


async def _storage(method: str, path: str, content: bytes | None = None) -> bytes | None:
    _ensure()
    _storage_path(path)
    base, headers = store.connection(get_settings().SUPABASE_SERVICE_ROLE_KEY, service=True)
    headers.update({"Content-Type": "application/pdf", "x-upsert": "false"})
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
            if method == "DELETE":
                headers["Content-Type"] = "application/json"
                response = await client.request("DELETE", base + "/storage/v1/object/" + BUCKET, headers=headers, json={"prefixes": [path]})
                if response.status_code not in (200, 204):
                    raise HTTPException(502, "No se pudo retirar el PDF de una solicitud incompleta.")
                return None
            route = "/storage/v1/object/" + ("authenticated/" if method == "GET" else "") + BUCKET + "/" + quote(path, safe="/")
            async with client.stream(method, base + route, headers=headers, content=content) as response:
                if response.status_code not in (200, 201):
                    raise HTTPException(502, "No se pudo guardar o recuperar el PDF congelado. Comprueba el bucket privado de firma.")
                if method != "GET":
                    return None
                chunks, count = [], 0
                async for chunk in response.aiter_bytes():
                    count += len(chunk)
                    if count > MAX_BUNDLE_BYTES:
                        raise HTTPException(413, "El expediente supera el límite de descarga.")
                    chunks.append(chunk)
                return b"".join(chunks)
    except httpx.HTTPError:
        raise HTTPException(502, "No se confirmó la operación con el original de firma.") from None


def _combine(documents: list[tuple[dict, bytes]]) -> tuple[bytes, list[dict]]:
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()
    snapshots, pages, total_text = [], 0, 0
    try:
        for item, content in documents:
            reader = PdfReader(io.BytesIO(content), strict=False)
            if reader.is_encrypted:
                raise HTTPException(422, "Desbloquea los PDF con contraseña antes de preparar una firma.")
            root = reader.trailer["/Root"]
            names = root.get("/Names", {})
            if hasattr(names, "get_object"):
                names = names.get_object()
            if any(key in root for key in ("/OpenAction", "/AA")) or any(key in names for key in ("/JavaScript", "/EmbeddedFiles")):
                raise HTTPException(422, "El PDF contiene acciones o adjuntos activos. Exporta una copia plana antes de firmarlo.")
            form = root.get("/AcroForm", {})
            if hasattr(form, "get_object"):
                form = form.get_object()
            if form and (form.get("/Fields") or form.get("/XFA")):
                raise HTTPException(422, "El PDF contiene campos de formulario editables. Exporta una copia plana para congelar exactamente lo que se firmará.")
            for page in reader.pages:
                if "/AA" in page:
                    raise HTTPException(422, "El PDF contiene acciones activas. Exporta una copia plana antes de firmarlo.")
                for ref in page.get("/Annots", []):
                    annotation = ref.get_object()
                    action = annotation.get("/A", {})
                    if hasattr(action, "get_object"):
                        action = action.get_object()
                    if "/AA" in annotation or (action and action.get("/S") not in (None, "/URI", "/GoTo")):
                        raise HTTPException(422, "El PDF contiene acciones activas. Exporta una copia plana antes de firmarlo.")
            count = len(reader.pages)
            if count == 0 or pages + count > MAX_BUNDLE_PAGES:
                raise HTTPException(413, "El expediente de firma admite hasta 500 páginas en total.")
            text = str(item["data"].get("text", ""))
            total_text += len(text)
            if total_text > 1_000_000:
                raise HTTPException(413, "El texto de los documentos supera un millón de caracteres. Divide la solicitud.")
            snapshots.append({"id": item["id"], "title": item["title"], "version": item.get("version", 1),
                "text": text, "sha256": digest(content), "pages": count, "first_page": pages + 1,
                "last_page": pages + count, "representation": item.get("_representation", "pdf_original")})
            writer.append(reader, import_outline=False)
            pages += count
        output = io.BytesIO()
        writer.write(output)
        data = output.getvalue()
        if len(data) > MAX_BUNDLE_BYTES:
            raise HTTPException(413, "El PDF combinado supera 25 MB. Divide la solicitud de firma.")
        return data, snapshots
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "No se pudo construir un PDF de firma fiel. Comprueba los documentos seleccionados.") from None
    finally:
        writer.close()


def public_envelope(record: dict) -> dict:
    allowed = ("id", "title", "status", "signing_order", "expires_at", "created_at", "completed_at", "manifest_hash", "bundle_hash", "recipients", "audit", "version")
    result = {k: record.get(k) for k in allowed}
    result["documents"] = [{k: doc.get(k) for k in ("id", "title", "version", "pages", "first_page", "last_page", "sha256", "representation")} for doc in record.get("documents", [])]
    result["identity_method"] = METHOD
    return result


async def list_envelopes(owner: str, token: str) -> dict:
    rows = await rpc("despacho_signing_list", {"p_id": None}, token)
    if not isinstance(rows, list):
        raise HTTPException(502, "El servicio de firma devolvió una lista no válida.")
    for row in rows:
        if row.get("owner_id") != store.uuid_text(owner):
            raise HTTPException(502, "El servicio devolvió una solicitud fuera de tu cuenta.")
    return {"envelopes": [public_envelope(row) for row in rows], "has_more": len(rows) == 100, "capabilities": available()}


async def owned(owner: str, token: str, envelope_id: str) -> dict:
    rows = await rpc("despacho_signing_list", {"p_id": store.uuid_text(envelope_id)}, token)
    if not isinstance(rows, list) or not rows:
        raise HTTPException(404, "La solicitud de firma no existe en tu cuenta.")
    row = rows[0]
    if row.get("owner_id") != store.uuid_text(owner):
        raise HTTPException(502, "El servicio devolvió una solicitud fuera de tu cuenta.")
    return row


async def create(owner: str, token: str, title: str, document_ids: list[str], signers: list[dict], signing_order: str, expires_days: int) -> dict:
    _ensure(email=True)
    owner = store.uuid_text(owner)
    originals, size = [], 0
    for document_id in document_ids:
        item = await store.fetch_item(owner, token, document_id, kind="document")
        data = item["data"]
        if data.get("mime") == "application/pdf" and data.get("storage_path"):
            if data.get("pagination") == "segments":
                raise HTTPException(409, "Un PDF seleccionado contiene texto editado distinto del original. Exporta el escrito actualizado a PDF y súbelo como nueva versión antes de firmarlo.")
            binary = await store.download_bytes(owner, token, data["storage_path"])
            item["_representation"] = "pdf_original"
        else:
            if not str(data.get("text", "")).strip():
                raise HTTPException(422, "Un documento no contiene texto ni PDF legible para firmar.")
            binary = await anyio.to_thread.run_sync(make_pdf, item["title"], data["text"])
            item["_representation"] = "pdf_generado_desde_texto"
        size += len(binary)
        if size > MAX_BUNDLE_BYTES:
            raise HTTPException(413, "Los documentos seleccionados superan 25 MB.")
        originals.append((item, binary))
    binary, snapshots = await anyio.to_thread.run_sync(_combine, originals)
    envelope_id = str(uuid4())
    recipients = [{"id": str(uuid4()), "name": s["name"], "email": delivery.valid_email(s["email"]), "position": i + 1} for i, s in enumerate(signers)]
    manifest = {"format": "el-memorialista-firma-v5", "id": envelope_id, "title": title,
        "bundle_hash": digest(binary), "documents": [{k: d[k] for k in ("id", "version", "title", "sha256", "pages", "first_page", "last_page", "representation")} for d in snapshots],
        "recipients": recipients, "signing_order": signing_order}
    canonical_manifest = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    manifest_hash = digest(canonical_manifest)
    path = f"{owner}/{envelope_id}/expediente.pdf"
    await _storage("POST", path, binary)
    try:
        record = await rpc("despacho_signing_create", {"p_id": envelope_id, "p_title": title,
            "p_documents": snapshots, "p_recipients": recipients, "p_order": signing_order,
            "p_days": expires_days, "p_storage_path": path, "p_bundle_hash": manifest["bundle_hash"],
            "p_manifest_hash": manifest_hash, "p_manifest": canonical_manifest}, token)
    except HTTPException as exc:
        # A timeout can happen AFTER the database committed. Never delete the
        # frozen original until a read confirms that no envelope was created.
        try:
            recovered = await owned(owner, token, envelope_id)
        except HTTPException as read_error:
            if read_error.status_code != 404:
                raise HTTPException(502, "No se confirmó la creación. El PDF se conservó; revisa la lista de firmas antes de repetir la solicitud.") from None
        else:
            if recovered.get("manifest_hash") != manifest_hash:
                raise HTTPException(409, "El identificador de la solicitud no coincide con el expediente preparado.") from None
            return {"envelope": public_envelope(recovered), "notice": "La creación se confirmó al recuperar el estado. No se han enviado invitaciones."}
        try:
            await _storage("DELETE", path)
        except HTTPException:
            raise HTTPException(502, "No se confirmó la solicitud y no se pudo retirar su PDF. Comprueba el almacenamiento de firmas antes de reintentar.") from None
        raise exc
    return {"envelope": public_envelope(record), "notice": "El PDF y los destinatarios quedaron congelados. Revisa el PDF antes de compartir enlaces o enviar invitaciones. Los documentos sin PDF se presentan como PDF generado desde su texto; las invitaciones aún no se han enviado."}


async def link(owner: str, token: str, envelope_id: str, recipient_id: str, origin: str) -> dict:
    await owned(owner, token, envelope_id)
    secret = secrets.token_urlsafe(32)
    result = await rpc("despacho_signing_link", {"p_id": store.uuid_text(envelope_id),
        "p_recipient": store.uuid_text(recipient_id), "p_hash": digest(secret)}, token)
    return {"signing_url": origin + "/firmar-v5#" + secret,
            "recipient": result["recipient"], "notice": "Este enlace sustituye al anterior del destinatario y anula sus códigos pendientes. Para firmar deberá verificar su correo."}


async def invite(owner: str, token: str, envelope_id: str, recipient_ids: list[str], origin: str) -> dict:
    _ensure(email=True)
    record = await owned(owner, token, envelope_id)
    recipients = {r["id"]: r for r in record["recipients"]}
    if any(rid not in recipients for rid in recipient_ids):
        raise HTTPException(422, "Un destinatario no pertenece a esta solicitud.")
    results = []
    for recipient_id in dict.fromkeys(recipient_ids):
        try:
            invitation = await link(owner, token, envelope_id, recipient_id, origin)
            recipient = invitation["recipient"]
            text = (f"{recipient['name']},\n\nTienes una solicitud de firma electrónica: {record['title']}.\n\n"
                    "Revisa todos los documentos y verifica tu correo para decidir si los aceptas.\n"
                    + invitation["signing_url"] + "\n\n"
                    + ("La firma sigue un orden: puede que debas esperar a otros destinatarios.\n" if record["signing_order"] == "sequential" else "")
                    + "Vencimiento (UTC): " + str(record["expires_at"]) + "\n\nEl Memorialista\n" + METHOD)
            sent = await delivery.send_email(recipient["email"], "Solicitud de firma · El Memorialista", text)
            await rpc("despacho_signing_delivery", {"p_owner": owner, "p_id": envelope_id, "p_recipient": recipient_id,
                "p_status": "smtp_accepted", "p_message_id": sent["message_id"]}, admin=True)
            results.append({"recipient_id": recipient_id, "status": "smtp_accepted", "notice": sent["notice"]})
        except HTTPException as exc:
            try:
                await rpc("despacho_signing_delivery", {"p_owner": owner, "p_id": envelope_id, "p_recipient": recipient_id,
                    "p_status": "unconfirmed", "p_message_id": ""}, admin=True)
            except HTTPException:
                pass
            results.append({"recipient_id": recipient_id, "status": "unconfirmed", "error": str(exc.detail)})
    return {"results": results, "envelope": public_envelope(await owned(owner, token, envelope_id))}


async def cancel(owner: str, token: str, envelope_id: str) -> dict:
    await owned(owner, token, envelope_id)
    result = await rpc("despacho_signing_cancel", {"p_id": store.uuid_text(envelope_id)}, token)
    return {"envelope": public_envelope(result)}


async def public_record(token: str, *, ip: str = "", agent: str = "", record_open: bool = False) -> dict:
    return await rpc("despacho_signing_view", {"p_hash": digest(check_token(token)),
        "p_ip": ip[:64], "p_agent": agent[:512], "p_record_open": record_open}, admin=True)


async def public_view(token: str, *, ip: str, agent: str) -> dict:
    record = await public_record(token, ip=ip, agent=agent, record_open=True)
    recipient = record["recipient"]
    return {"id": record["id"], "title": record["title"], "status": record["status"],
        "manifest_hash": record["manifest_hash"], "bundle_hash": record["bundle_hash"], "expires_at": record["expires_at"],
        "documents": [{k: d.get(k) for k in ("title", "text", "pages", "sha256", "first_page", "last_page", "representation")} for d in record["documents"]],
        "recipient": {"name": recipient["name"], "email_masked": masked_email(recipient["email"]), "status": recipient["status"]},
        "can_sign": record["can_sign"], "consent_text": CONSENT, "identity_method": METHOD,
        "notice": "Revisa el PDF congelado completo: ese es el contenido que aceptarás. El texto mostrado es una ayuda de lectura y puede no reflejar imágenes, tablas o formato."}


async def request_otp(token: str) -> dict:
    _ensure(email=True)
    check_token(token)
    code, generation = f"{secrets.randbelow(1_000_000):06d}", str(uuid4())
    result = await rpc("despacho_signing_otp", {"p_hash": digest(token), "p_otp_hash": _otp_hash(token, code), "p_generation": generation}, admin=True)
    try:
        await delivery.send_email(result["email"], "Código para firmar · El Memorialista",
            "Tu código para la solicitud «" + result["title"] + "» es:\n\n" + code +
            "\n\nCaduca en 10 minutos. No compartas este código. Pedirlo no firma ningún documento.\n"
            "Si no solicitaste este código, ignora este mensaje.\n\nEl Memorialista")
    except HTTPException:
        await rpc("despacho_signing_otp_delivery", {"p_recipient": result["recipient_id"], "p_generation": generation, "p_sent": False}, admin=True)
        raise
    await rpc("despacho_signing_otp_delivery", {"p_recipient": result["recipient_id"], "p_generation": generation, "p_sent": True}, admin=True)
    return {"sent": True, "expires_seconds": 600, "email_masked": masked_email(result["email"]),
            "notice": "El servidor de correo aceptó el código. Revisa el buzón destinatario y la carpeta de correo no deseado."}


async def accept(token: str, otp: str, name: str, consent: bool, manifest_hash: str, *, ip: str, agent: str) -> dict:
    _ensure(email=True)
    check_token(token)
    if not consent or not re.fullmatch(r"\d{6}", otp) or not re.fullmatch(r"[a-f0-9]{64}", manifest_hash):
        raise HTTPException(422, "Revisa el código, la huella y el consentimiento antes de firmar.")
    if not 2 <= len(name.strip()) <= 160 or re.search(r"[\x00-\x1f\x7f]", name):
        raise HTTPException(422, "Escribe tu nombre completo.")
    return await rpc("despacho_signing_accept", {"p_hash": digest(token), "p_otp_hash": _otp_hash(token, otp),
        "p_name": name.strip(), "p_consent": CONSENT, "p_manifest_hash": manifest_hash,
        "p_ip": ip[:64], "p_agent": agent[:512]}, admin=True)


async def _verified_binary(record: dict) -> bytes:
    binary = await _storage("GET", record["storage_path"])
    if not binary or not hmac.compare_digest(digest(binary), record["bundle_hash"]):
        raise HTTPException(409, "La huella del PDF almacenado no coincide. La descarga se detuvo; no firmes esta solicitud.")
    return binary


async def private_document(owner: str, token: str, envelope_id: str) -> tuple[str, bytes]:
    record = await owned(owner, token, envelope_id)
    _storage_path(record["storage_path"], owner)
    return record["title"], await _verified_binary(record)


async def public_document(token: str) -> tuple[str, bytes]:
    record = await public_record(token)
    return record["title"], await _verified_binary(record)


def _receipt_pdf(record: dict, binary: bytes) -> bytes:
    from pypdf import PdfReader, PdfWriter
    lines = ["CONSTANCIA DE FIRMA ELECTRÓNICA", "Solicitud: " + record["id"],
             "Huella SHA-256 del PDF presentado: " + record["bundle_hash"],
             "Huella SHA-256 del manifiesto: " + record["manifest_hash"],
             "Completado (UTC): " + str(record.get("completed_at")), "Método: " + METHOD,
             "Este PDF añade una constancia; su huella difiere de la del PDF presentado para firma.", "", "DOCUMENTOS"]
    for doc in record["documents"]:
        lines.extend([doc["title"], f"Páginas {doc['first_page']}–{doc['last_page']} · SHA-256: {doc['sha256']}"])
    lines.extend(["", "DESTINATARIOS Y CONSENTIMIENTOS"])
    for r in record["recipients"]:
        lines.extend(["Nombre declarado al firmar: " + str(r.get("signed_name", "")),
            "Correo verificado por código: " + r["email"], "Fecha (UTC): " + str(r.get("signed_at", "")),
            "IP registrada: " + str(r.get("signer_ip", "")), "Navegador: " + str(r.get("signer_agent", "")),
            "Consentimiento: " + str(r.get("consent_text", "")), "Identificador: " + r["id"], ""])
    lines.append("TRAZABILIDAD")
    for event in record.get("audit", []):
        lines.append(str(event.get("at", "")) + " · " + str(event.get("event", "")) + " · " + str(event.get("recipient_id", "")))
    evidence = make_pdf("Constancia · " + record["title"], "\n".join(lines))
    writer = PdfWriter()
    try:
        writer.append(PdfReader(io.BytesIO(binary)), import_outline=False)
        writer.append(PdfReader(io.BytesIO(evidence)), import_outline=False)
        output = io.BytesIO(); writer.write(output)
        return output.getvalue()
    finally:
        writer.close()


async def receipt(owner: str, token: str, envelope_id: str) -> tuple[str, bytes]:
    record = await owned(owner, token, envelope_id)
    if record["status"] != "completed":
        raise HTTPException(409, "La constancia final se genera cuando todos los destinatarios han firmado.")
    binary = await _verified_binary(record)
    return record["title"], await anyio.to_thread.run_sync(_receipt_pdf, record, binary)


async def export_owner(owner: str, token: str) -> dict:
    """Account export hook: no link hashes, OTP hashes, access or refresh tokens."""
    owner = store.uuid_text(owner)
    # Account export must remain available when new signing operations are
    # disabled; it needs only the owner's JWT, never the service credential.
    rows = await store.db_request("POST", "rpc/despacho_signing_export", token, service=False, json={"p_owner": owner})
    if isinstance(rows, dict) and rows.get("error"):
        raise HTTPException(403, "No se autorizó la exportación de firmas de esta cuenta.")
    if not isinstance(rows, list) or any(not isinstance(row, dict) or row.get("owner_id") != owner for row in rows):
        raise HTTPException(502, "La exportación de firmas no se pudo verificar para esta cuenta.")
    return {"envelopes": rows, "method": METHOD, "binary_scope": "Descarga los PDF congelados y las constancias desde Firma antes de eliminar la cuenta."}


async def purge_owner_storage(owner: str) -> None:
    """Account deletion hook; invoke before deleting Auth so errors are actionable."""
    await purge_bucket_owner(owner, BUCKET)


async def purge_bucket_owner(owner: str, bucket: str) -> None:
    """Purge a known private product bucket, including interrupted creations."""
    if bucket not in {BUCKET, "despacho-salas-v5"}:
        raise HTTPException(422, "El almacenamiento privado solicitado no está disponible.")
    owner = store.uuid_text(owner)
    base, headers = store.connection(get_settings().SUPABASE_SERVICE_ROLE_KEY, service=True)
    try:
        async with httpx.AsyncClient(timeout=45, follow_redirects=False) as client:
            # Walk the owner's prefix, not just database rows: interrupted
            # creates can leave a frozen PDF before its envelope was committed.
            pending, paths, visited = [owner + "/"], [], 0
            while pending:
                prefix = pending.pop()
                visited += 1
                if visited > 10000:
                    raise HTTPException(413, "La limpieza de firmas requiere una exportación administrativa.")
                offset = 0
                while True:
                    response = await client.post(base + "/storage/v1/object/list/" + bucket, headers=headers,
                        json={"prefix": prefix, "limit": 1000, "offset": offset, "sortBy": {"column": "name", "order": "asc"}})
                    if response.status_code != 200:
                        raise HTTPException(502, "No se pudo comprobar el almacenamiento de firmas antes de eliminar la cuenta.")
                    rows = response.json()
                    if not isinstance(rows, list):
                        raise HTTPException(502, "La lista de originales de firma no es válida.")
                    for row in rows:
                        name = row.get("name", "")
                        if not isinstance(name, str) or not name or name in (".", "..") or re.search(r"[\x00-\x1f/\\]", name):
                            raise HTTPException(502, "Se encontró una ruta no válida en el almacenamiento de firmas.")
                        path = prefix + name
                        if row.get("id") is None:
                            pending.append(path + "/")
                        else:
                            paths.append(path)
                    if len(rows) < 1000:
                        break
                    offset += len(rows)
            for start in range(0, len(paths), 100):
                response = await client.request("DELETE", base + "/storage/v1/object/" + bucket, headers=headers, json={"prefixes": paths[start:start + 100]})
                if response.status_code not in (200, 204):
                    raise HTTPException(502, "No se pudo completar la limpieza de originales de firma.")
            check = await client.post(base + "/storage/v1/object/list/" + bucket, headers=headers,
                json={"prefix": owner + "/", "limit": 1, "offset": 0})
            if check.status_code != 200 or check.json() != []:
                raise HTTPException(502, "Aún quedan originales de firma. La eliminación de cuenta debe detenerse.")
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "No se confirmó la limpieza de los originales de firma.") from None
