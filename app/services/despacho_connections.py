"""Conectores de lectura OAuth con consentimiento por cuenta y tokens cifrados.

Google Drive, OneDrive, SharePoint y Outlook se consumen por sus APIs oficiales.
El navegador nunca recibe access/refresh tokens. Los originales se importan
expresamente al DMS; no hay sincronización ni envíos implícitos.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import secrets
import time
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from pathlib import PurePath
from urllib.parse import quote, urlencode, urlsplit
from uuid import uuid4

import anyio
import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.services import despacho_store as store
from app.services.despacho_fetch import html_to_text, resolve_public

PROVIDERS = {
    "google_drive": {"label": "Google Drive", "scopes": ["openid", "email", "https://www.googleapis.com/auth/drive.readonly"]},
    "microsoft_onedrive": {"label": "OneDrive", "scopes": ["offline_access", "https://graph.microsoft.com/User.Read", "https://graph.microsoft.com/Files.Read"]},
    "microsoft_sharepoint": {"label": "SharePoint", "scopes": ["offline_access", "https://graph.microsoft.com/User.Read", "https://graph.microsoft.com/Sites.Read.All"]},
    "microsoft_outlook": {"label": "Outlook", "scopes": ["offline_access", "https://graph.microsoft.com/User.Read", "https://graph.microsoft.com/Mail.Read"]},
}
SAFE_CONNECTION_FIELDS = "id,owner_id,provider,label,scopes,created_at,updated_at"
MAX_REMOTE_BYTES = 10 * 1024 * 1024
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _provider(provider: str) -> dict:
    if provider not in PROVIDERS:
        raise HTTPException(422, "La conexión solicitada no está disponible.")
    return PROVIDERS[provider]


def _cipher():
    try:
        from cryptography.fernet import Fernet
        key = getattr(get_settings(), "DESPACHO_TOKEN_ENCRYPTION_KEY", "").strip()
        if not key:
            raise ValueError()
        return Fernet(key.encode("ascii"))
    except (ImportError, ValueError, UnicodeError):
        raise HTTPException(503, "Configura una clave Fernet válida para cifrar las conexiones externas.") from None


def encrypt(value: dict) -> str:
    return _cipher().encrypt(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()).decode()


def decrypt(value: str, *, ttl: int | None = None) -> dict:
    try:
        data = _cipher().decrypt(value.encode(), ttl=ttl)
        result = json.loads(data)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(409, "La conexión o el cursor ya no es válido. Reconecta la cuenta o reinicia la lista.") from None


def credentials(provider: str) -> tuple[str, str, str, str]:
    _provider(provider)
    s = get_settings()
    if not getattr(s, "DESPACHO_CONNECTIONS_ENABLED", False):
        raise HTTPException(503, "Las conexiones externas no están habilitadas en este servidor.")
    _cipher()
    if not s.SUPABASE_SERVICE_ROLE_KEY or not s.SUPABASE_URL or not s.SUPABASE_ANON_KEY:
        raise HTTPException(503, "Configura Supabase y la clave de servicio para proteger las conexiones externas.")
    if provider == "google_drive":
        client_id, secret = getattr(s, "GOOGLE_OAUTH_CLIENT_ID", ""), getattr(s, "GOOGLE_OAUTH_CLIENT_SECRET", "")
        auth_url, token_url = "https://accounts.google.com/o/oauth2/v2/auth", "https://oauth2.googleapis.com/token"
    else:
        client_id, secret = getattr(s, "MICROSOFT_OAUTH_CLIENT_ID", ""), getattr(s, "MICROSOFT_OAUTH_CLIENT_SECRET", "")
        tenant = getattr(s, "MICROSOFT_OAUTH_TENANT", "common")
        if not re.fullmatch(r"(?:common|organizations|consumers|[a-fA-F0-9-]{36})", tenant):
            raise HTTPException(503, "El tenant de Microsoft debe ser un identificador válido o common/organizations/consumers.")
        auth_url, token_url = (f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/{part}" for part in ("authorize", "token"))
    if not client_id or not secret:
        raise HTTPException(503, "Registra y configura la aplicación OAuth de este proveedor antes de conectarlo.")
    return client_id, secret, auth_url, token_url


def capabilities() -> list[dict]:
    results = []
    for provider, info in PROVIDERS.items():
        try:
            credentials(provider)
            configured, message = True, "Disponible para conectar con consentimiento de la cuenta."
        except HTTPException as exc:
            configured, message = False, str(exc.detail)
        results.append({"id": provider, **info, "configured": configured, "message": message})
    return results


async def admin(method: str, path: str, **kwargs):
    token = get_settings().SUPABASE_SERVICE_ROLE_KEY
    if not token:
        raise HTTPException(503, "Falta configurar el servicio de conexiones del despacho.")
    return await store.db_request(method, path, token, service=True, **kwargs)


async def rpc(name: str, payload: dict):
    result = await admin("POST", "rpc/" + name, json=payload)
    if isinstance(result, dict) and result.get("error"):
        errors = {"NOT_FOUND": (404, "La conexión no existe en tu cuenta."),
                  "STATE_INVALID": (400, "El acceso OAuth caducó o ya se utilizó. Inicia la conexión otra vez."),
                  "LIMIT": (429, "Se alcanzó el límite de conexiones o intentos. Inténtalo más tarde.")}
        status, message = errors.get(result["error"], (409, "La conexión cambió. Recarga antes de continuar."))
        raise HTTPException(status, message)
    return result


def public_connection(row: dict, owner: str) -> dict:
    if not isinstance(row, dict) or row.get("owner_id") != owner:
        raise HTTPException(502, "La conexión devuelta no pertenece a tu cuenta.")
    return {key: row.get(key) for key in SAFE_CONNECTION_FIELDS.split(",") if key != "owner_id"}


async def list_connections(owner: str) -> dict:
    owner = store.uuid_text(owner)
    if not get_settings().SUPABASE_SERVICE_ROLE_KEY:
        return {"providers": capabilities(), "connections": [], "notice": "Falta configurar el servicio de conexiones."}
    rows = await admin("GET", "despacho_conexiones", params={"owner_id": "eq." + owner, "select": SAFE_CONNECTION_FIELDS, "order": "created_at.desc", "limit": 20})
    return {"providers": capabilities(), "connections": [public_connection(row, owner) for row in rows]}


async def owned_connection(owner: str, connection_id: str, *, secret: bool = False) -> dict:
    owner, cid = store.uuid_text(owner), store.uuid_text(connection_id)
    rows = await admin("GET", "despacho_conexiones", params={"owner_id": "eq." + owner, "id": "eq." + cid,
        "select": "*" if secret else SAFE_CONNECTION_FIELDS, "limit": 1})
    if not isinstance(rows, list) or not rows:
        raise HTTPException(404, "La conexión no existe en tu cuenta.")
    public_connection(rows[0], owner)
    return rows[0]


async def begin(owner: str, provider: str, origin: str) -> tuple[dict, str]:
    owner = store.uuid_text(owner)
    client_id, _, auth_url, _ = credentials(provider)
    state, binding, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    redirect = origin + "/oauth/despacho/" + provider
    await rpc("despacho_oauth_begin", {"p_owner": owner, "p_provider": provider,
        "p_state_hash": hashlib.sha256(state.encode()).hexdigest(),
        "p_binding_hash": hashlib.sha256(binding.encode()).hexdigest(),
        "p_secret": encrypt({"verifier": verifier, "redirect_uri": redirect})})
    params = {"client_id": client_id, "redirect_uri": redirect, "response_type": "code",
              "scope": " ".join(PROVIDERS[provider]["scopes"]), "state": state,
              "code_challenge": challenge, "code_challenge_method": "S256"}
    if provider == "google_drive":
        params.update(access_type="offline", prompt="consent", include_granted_scopes="false")
    else:
        # GET response keeps the existing SameSite=Lax private session cookie.
        params.update(response_mode="query", prompt="select_account")
    return {"authorization_url": auth_url + "?" + urlencode(params)}, binding


async def _json(method: str, url: str, *, access: str | None = None, **kwargs) -> dict:
    headers = {"Accept": "application/json"}
    if access:
        headers["Authorization"] = "Bearer " + access
    headers.update(kwargs.pop("headers", {}))
    try:
        async with httpx.AsyncClient(timeout=35, follow_redirects=False, trust_env=False) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
        if response.status_code in (401, 403):
            raise HTTPException(403, "El proveedor rechazó el acceso. Revisa sus permisos o vuelve a conectar la cuenta.")
        if response.status_code == 429:
            raise HTTPException(429, "El proveedor limitó temporalmente las consultas. Inténtalo más tarde.")
        if response.status_code not in (200, 201, 204):
            raise HTTPException(502, "El proveedor no confirmó la operación. No se ha simulado un resultado.")
        if not response.content:
            return {}
        if len(response.content) > 3 * 1024 * 1024:
            raise HTTPException(413, "La respuesta del proveedor supera el límite de esta operación.")
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "No se pudo completar la consulta al proveedor externo.") from None


def _token_record(result: dict, previous: dict | None = None) -> dict:
    previous = previous or {}
    access = result.get("access_token")
    if not isinstance(access, str) or not access or len(access) > 32_000:
        raise HTTPException(502, "El proveedor no entregó un permiso de acceso utilizable.")
    try:
        seconds = max(30, min(int(result.get("expires_in", 3600)), 86400))
    except (ValueError, TypeError):
        raise HTTPException(502, "El proveedor devolvió una duración de acceso no válida.") from None
    return {"access_token": access, "refresh_token": result.get("refresh_token") or previous.get("refresh_token", ""),
            "expires_at": int(time.time()) + seconds, "scope": result.get("scope") or previous.get("scope", "")}


async def complete(owner: str, provider: str, state: str, binding: str, code: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", state or "") or not re.fullmatch(r"[A-Za-z0-9_-]{43}", binding or ""):
        raise HTTPException(400, "La conexión OAuth no se inició en este navegador.")
    if not code or len(code) > 8000 or re.search(r"[\x00-\x20\x7f]", code):
        raise HTTPException(400, "El proveedor no devolvió un código OAuth válido.")
    owner = store.uuid_text(owner)
    client_id, secret, _, token_url = credentials(provider)
    state_row = await rpc("despacho_oauth_consume", {"p_owner": owner, "p_provider": provider,
        "p_state_hash": hashlib.sha256(state.encode()).hexdigest(), "p_binding_hash": hashlib.sha256(binding.encode()).hexdigest()})
    data = decrypt(state_row["secret"], ttl=900)
    result = await _json("POST", token_url, data={"client_id": client_id, "client_secret": secret,
        "grant_type": "authorization_code", "code": code, "redirect_uri": data["redirect_uri"], "code_verifier": data["verifier"]})
    record = _token_record(result)
    if provider == "google_drive":
        profile = await _json("GET", "https://openidconnect.googleapis.com/v1/userinfo", access=record["access_token"])
        if profile.get("email_verified") is not True:
            raise HTTPException(403, "Google no confirmó el correo de esta cuenta.")
        label = str(profile.get("email") or "Google Drive")[:254]
    else:
        profile = await _json("GET", "https://graph.microsoft.com/v1.0/me", access=record["access_token"], params={"$select": "displayName,mail,userPrincipalName"})
        label = str(profile.get("mail") or profile.get("userPrincipalName") or profile.get("displayName") or PROVIDERS[provider]["label"])[:254]
    row = await rpc("despacho_oauth_save", {"p_owner": owner, "p_provider": provider, "p_label": label,
        "p_scopes": record["scope"].split() if record["scope"] else PROVIDERS[provider]["scopes"], "p_secret": encrypt(record)})
    return public_connection(row, owner)


async def _access(owner: str, connection_id: str) -> tuple[dict, str]:
    row = await owned_connection(owner, connection_id, secret=True)
    credentials(row["provider"])
    tokens = decrypt(row["secret"])
    if tokens.get("expires_at", 0) > time.time() + 90:
        return row, tokens["access_token"]
    lease = str(uuid4())
    claim = await rpc("despacho_oauth_claim_refresh", {"p_owner": owner, "p_id": row["id"], "p_lease": lease})
    if not claim.get("acquired"):
        raise HTTPException(409, "La conexión está renovando su permiso. Vuelve a intentarlo en unos segundos.")
    try:
        tokens = decrypt(claim["secret"])
        if not tokens.get("refresh_token"):
            raise HTTPException(403, "La conexión caducó y necesita tu consentimiento nuevamente.")
        client_id, secret, _, token_url = credentials(row["provider"])
        payload = {"grant_type": "refresh_token", "client_id": client_id, "client_secret": secret, "refresh_token": tokens["refresh_token"]}
        if row["provider"] != "google_drive":
            payload["scope"] = " ".join(PROVIDERS[row["provider"]]["scopes"])
        result = await _json("POST", token_url, data=payload)
        fresh = _token_record(result, tokens)
        saved = await rpc("despacho_oauth_finish_refresh", {"p_owner": owner, "p_id": row["id"], "p_lease": lease, "p_secret": encrypt(fresh)})
        if not saved.get("saved"):
            raise HTTPException(409, "La conexión cambió o se desconectó durante la renovación.")
        return row, fresh["access_token"]
    except BaseException:
        # Do not overwrite a revoked or concurrently replaced connection.
        try:
            await rpc("despacho_oauth_finish_refresh", {"p_owner": owner, "p_id": row["id"], "p_lease": lease, "p_secret": None})
        except HTTPException:
            pass
        raise


def remote_id(value: str, *, optional: bool = False) -> str:
    if optional and not value:
        return ""
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9!_.=,:@+-]{1,512}", value):
        raise HTTPException(422, "El identificador del recurso externo no es válido.")
    return value


def _web_url(value) -> str | None:
    if not isinstance(value, str) or len(value) > 2048 or re.search(r"[\x00-\x20\\]", value):
        return None
    try:
        p = urlsplit(value)
        if p.scheme == "https" and p.hostname and p.username is None and p.password is None and p.port in (None, 443):
            return value
    except ValueError:
        pass
    return None


def _next_cursor(cid: str, provider: str, next_value: str | None) -> str | None:
    return encrypt({"id": cid, "provider": provider, "next": next_value}) if next_value else None


def _read_cursor(cursor: str, cid: str, provider: str) -> str:
    if len(cursor) > 16_000:
        raise HTTPException(422, "El cursor es demasiado largo.")
    data = decrypt(cursor, ttl=1800)
    if data.get("id") != cid or data.get("provider") != provider or not isinstance(data.get("next"), str):
        raise HTTPException(400, "El cursor pertenece a otra conexión.")
    value = data["next"]
    if provider != "google_drive":
        p = urlsplit(value)
        if p.scheme != "https" or p.netloc != "graph.microsoft.com" or not p.path.startswith("/v1.0/") or len(value) > 8000:
            raise HTTPException(502, "El proveedor devolvió una continuación no admitida.")
    return value


async def resources(owner: str, cid: str, *, q: str = "", folder_id: str = "", drive_id: str = "", site_id: str = "", cursor: str = "") -> dict:
    row, access = await _access(owner, cid)
    provider = row["provider"]
    q = q.strip()[:300]
    for value in (folder_id, drive_id, site_id):
        remote_id(value, optional=True)
    items = []
    if provider == "google_drive":
        parts = ["trashed = false"]
        if folder_id:
            parts.append("'" + folder_id + "' in parents")
        if q:
            escaped = q.replace("\\", "\\\\").replace("'", "\\'")
            parts.append("name contains '" + escaped + "'")
        params = {"q": " and ".join(parts), "pageSize": 50, "fields": "nextPageToken,files(id,name,mimeType,size,webViewLink,modifiedTime)", "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
        if cursor:
            params["pageToken"] = _read_cursor(cursor, row["id"], provider)
        result = await _json("GET", "https://www.googleapis.com/drive/v3/files", access=access, params=params)
        for f in result.get("files", []):
            items.append({"id": f["id"], "name": f.get("name", "Documento"), "type": "folder" if f.get("mimeType") == "application/vnd.google-apps.folder" else "file", "mime": f.get("mimeType"), "size": f.get("size"), "web_url": _web_url(f.get("webViewLink")), "modified_at": f.get("modifiedTime")})
        nxt = result.get("nextPageToken")
    else:
        base = "https://graph.microsoft.com/v1.0"
        params = {"$top": 50}
        kind = "file"
        if provider == "microsoft_outlook":
            url = base + "/me/messages"
            params["$select"] = "id,subject,from,receivedDateTime,hasAttachments,webLink"
            if q:
                params["$search"] = '"' + q.replace('"', '').replace("\\", "") + '"'
            else:
                params["$orderby"] = "receivedDateTime desc"
            kind = "email"
        elif provider == "microsoft_sharepoint" and not drive_id and not site_id:
            url = base + ("/sites" if q else "/me/followedSites")
            if q:
                params["search"] = q
            kind = "site"
        elif provider == "microsoft_sharepoint" and site_id and not drive_id:
            url = base + "/sites/" + quote(site_id, safe="") + "/drives"
            kind = "drive"
        else:
            root = base + ("/drives/" + quote(drive_id, safe="") if drive_id else "/me/drive")
            if q and not folder_id:
                safe_q = q.replace("'", "''")
                url = root + "/root/search(q='" + quote(safe_q, safe="") + "')"
            else:
                url = root + ("/items/" + quote(folder_id, safe="") if folder_id else "/root") + "/children"
        if cursor:
            url, params = _read_cursor(cursor, row["id"], provider), None
        result = await _json("GET", url, access=access, params=params)
        for f in result.get("value", []):
            item_kind = "folder" if "folder" in f else kind
            item = {"id": f["id"], "name": f.get("subject") or f.get("name") or f.get("displayName") or "Sin título", "type": item_kind,
                    "mime": "message/rfc822" if kind == "email" else (f.get("file") or {}).get("mimeType"), "size": f.get("size"),
                    "web_url": _web_url(f.get("webUrl") or f.get("webLink")), "drive_id": drive_id or (f.get("parentReference") or {}).get("driveId"),
                    "modified_at": f.get("lastModifiedDateTime") or f.get("receivedDateTime")}
            if kind == "email":
                item["sender"] = ((f.get("from") or {}).get("emailAddress") or {}).get("address", "")
                item["has_attachments"] = bool(f.get("hasAttachments"))
            items.append(item)
        nxt = result.get("@odata.nextLink")
    return {"items": items, "next_cursor": _next_cursor(row["id"], provider, nxt), "provider": provider,
            "notice": "La lista muestra los recursos que el proveedor permite leer a esta conexión; importar crea una copia privada."}


def _download_host(url: str) -> str:
    try:
        p = urlsplit(url)
        if (p.scheme != "https" or p.username is not None or p.password is not None or p.port not in (None, 443)
                or not p.hostname or len(url) > 16_000 or re.search(r"[\x00-\x20\\]", url)):
            raise ValueError()
        host = p.hostname.lower()
        if not any(host == domain or host.endswith("." + domain) for domain in ("sharepoint.com", "sharepoint-df.com", "1drv.com", "onedrive.com", "live.com", "storage.live.com")):
            raise ValueError()
        return host
    except ValueError:
        raise HTTPException(502, "Microsoft devolvió un destino de descarga no admitido.") from None


async def _binary(url: str, access: str, *, microsoft_redirect: bool = False) -> bytes:
    """API origins are constants. Redirected Microsoft URLs get no OAuth header.

    Each signed download hop is host-checked, DNS-checked and IP-pinned while
    preserving TLS SNI. The short-lived download URL never leaves the backend.
    """
    current = url
    try:
        async with httpx.AsyncClient(timeout=45, follow_redirects=False, trust_env=False,
                transport=httpx.AsyncHTTPTransport(limits=httpx.Limits(max_keepalive_connections=0))) as client:
            for hop in range(4):
                headers, extensions = {"Accept-Encoding": "identity"}, {}
                target = current
                if hop == 0:
                    if urlsplit(current).netloc not in {"www.googleapis.com", "graph.microsoft.com"}:
                        raise HTTPException(422, "Origen de API no admitido.")
                    headers["Authorization"] = "Bearer " + access
                else:
                    host = _download_host(current)
                    target = httpx.URL(current).copy_with(host=await resolve_public(host))
                    headers["Host"], extensions["sni_hostname"] = host, host
                async with client.stream("GET", target, headers=headers, extensions=extensions) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        if not microsoft_redirect or hop >= 3:
                            raise HTTPException(502, "La descarga externa redirige a un destino no admitido.")
                        current = response.headers.get("location", "")
                        _download_host(current)
                        continue
                    if response.status_code != 200:
                        raise HTTPException(502, "No se pudo descargar el original con los permisos de esta conexión.")
                    parts, length = [], 0
                    async for part in response.aiter_bytes():
                        length += len(part)
                        if length > MAX_REMOTE_BYTES:
                            raise HTTPException(413, "El original externo supera 10 MB.")
                        parts.append(part)
                    return b"".join(parts)
    except httpx.HTTPError:
        raise HTTPException(502, "La descarga externa se interrumpió. No se ha confirmado su importación.") from None
    raise HTTPException(502, "La descarga externa no produjo un documento.")


def _name(value: str, fallback="documento.txt") -> str:
    result = re.sub(r"[\x00-\x1f\x7f]", "", PurePath(value.replace("\\", "/")).name)[:180]
    return result or fallback


def parse_email(content: bytes) -> tuple[dict, list[tuple[str, bytes]]]:
    if len(content) > MAX_REMOTE_BYTES:
        raise HTTPException(413, "El correo supera 10 MB.")
    try:
        message = BytesParser(policy=policy.default).parsebytes(content)
        body = message.get_body(preferencelist=("plain", "html"))
        text = body.get_content() if body else ""
        if body and body.get_content_type() == "text/html":
            text, _ = html_to_text(text)
        text = "\n".join(["Asunto: " + str(message.get("Subject", "")), "De: " + str(message.get("From", "")),
                          "Para: " + str(message.get("To", "")), "Fecha: " + str(message.get("Date", "")), "", text])
        attachments = []
        warnings = []
        for part in message.walk():
            if part.is_multipart() or not part.get_filename():
                continue
            if len(attachments) >= 10:
                warnings.append("El correo contiene más de 10 adjuntos; el original EML conserva el resto.")
                break
            filename = _name(part.get_filename())
            payload = part.get_payload(decode=True) or b""
            if len(payload) > MAX_REMOTE_BYTES:
                warnings.append(f"El adjunto {filename} supera el límite de importación; se conserva dentro del original EML.")
                continue
            attachments.append((filename, payload))
        if len(text) > 500000:
            warnings.append("El texto del correo se limitó a 500.000 caracteres; conserva el original EML para una lectura completa.")
        text = text[:500000].replace("\x00", "")
        return {"text": text, "pages": [{"page": 1, "text": text}], "pagination": "segments", "mime": "message/rfc822", "warnings": warnings}, attachments
    except HTTPException:
        raise
    except (ValueError, TypeError, LookupError):
        raise HTTPException(422, "No se pudo interpretar el correo original.") from None


async def _existing(owner: str, token: str, external_key: str) -> dict | None:
    rows = await store.db_request("GET", store.TABLE, token, params={"owner_id": "eq." + owner, "kind": "eq.document", "data->>external_key": "eq." + external_key, "limit": 1})
    return store.public_item(rows[0], owner) if rows else None


async def _save_import(owner: str, token: str, name: str, content: bytes, parsed: dict, source: dict, matter_id: str | None, key: str) -> dict:
    existing = await _existing(owner, token, key)
    if existing:
        return existing
    item_id = str(uuid4())
    suffix = PurePath(name).suffix.lower().lstrip(".") or "txt"
    if not re.fullmatch(r"[a-z0-9]{1,8}", suffix):
        suffix = "txt"
    path = f"{owner}/{item_id}/{uuid4()}.{suffix}"
    payload = {"kind": "document", "title": name[:240], "matter_id": matter_id,
               "data": {**parsed, "filename": name, "storage_path": path, "uploaded_at": store.utcnow(),
                        "external_key": key, "external_source": source, "versions": []}}
    store.validate_payload(payload, user_id=owner)
    await store.upload_bytes(owner, token, path, content, parsed.get("mime", "application/octet-stream"))
    try:
        return await store.create_item(owner, token, payload, item_id=item_id)
    except HTTPException as exc:
        # A database timeout may follow a committed item. Never delete the
        # original until its absence is positively confirmed with the user JWT.
        try:
            recovered = await store.fetch_item(owner, token, item_id, kind="document")
        except HTTPException as lookup:
            if lookup.status_code != 404:
                raise HTTPException(502, "No se confirmó la importación. Revisa el DMS antes de repetirla; se conservó el original para no perder un guardado ya completado.") from None
        else:
            if recovered.get("data", {}).get("external_key") == key:
                return recovered
            raise HTTPException(409, "La copia importada cambió. Revisa el DMS antes de repetir la operación.") from None
        existing = await _existing(owner, token, key)
        if existing and existing.get("data", {}).get("storage_path") == path:
            return existing
        try:
            await store.remove_storage_paths(owner, token, [path])
        except HTTPException:
            raise HTTPException(502, "La importación no se confirmó y puede quedar un original sin vincular. Revisa el almacenamiento antes de repetirla.") from None
        if existing:
            return existing
        raise


async def import_resource(owner: str, token: str, cid: str, resource_id: str, *, drive_id: str = "", matter_id: str | None = None) -> dict:
    owner, cid = store.uuid_text(owner), store.uuid_text(cid)
    resource_id, drive_id = remote_id(resource_id), remote_id(drive_id, optional=True)
    if matter_id:
        await store.fetch_item(owner, token, matter_id, kind="matter")
    row, access = await _access(owner, cid)
    key = hashlib.sha256(json.dumps([cid, resource_id, drive_id, matter_id], separators=(",", ":")).encode()).hexdigest()
    existing = await _existing(owner, token, key)
    if existing:
        return {"item": existing, "warnings": ["Este recurso ya fue importado en este asunto. Se conservó la copia existente; una modificación remota no la sobrescribe."], "attachments": []}
    provider, rid = row["provider"], quote(resource_id, safe="")
    attachments = []
    if provider == "google_drive":
        root = "https://www.googleapis.com/drive/v3/files/" + rid
        info = await _json("GET", root, access=access, params={"fields": "id,name,mimeType,modifiedTime,webViewLink,capabilities(canDownload)", "supportsAllDrives": "true"})
        if not info.get("capabilities", {}).get("canDownload", True):
            raise HTTPException(403, "El propietario externo no permite descargar este archivo.")
        name = _name(info.get("name", "documento"))
        mime = info.get("mimeType", "")
        if mime == "application/vnd.google-apps.document":
            name = name + ".docx" if not name.lower().endswith(".docx") else name
            url = root + "/export?" + urlencode({"mimeType": DOCX_MIME})
        elif mime.startswith("application/vnd.google-apps."):
            raise HTTPException(415, "Este tipo de archivo de Google no se importa al DMS. Exporta una copia PDF, Word o texto.")
        else:
            url = root + "?alt=media&supportsAllDrives=true"
        content = await _binary(url, access)
        source_url, modified = _web_url(info.get("webViewLink")), info.get("modifiedTime")
    elif provider == "microsoft_outlook":
        root = "https://graph.microsoft.com/v1.0/me/messages/" + rid
        info = await _json("GET", root, access=access, params={"$select": "subject,webLink,lastModifiedDateTime"})
        content = await _binary(root + "/$value", access)
        name = _name(info.get("subject") or "Correo") + ".eml"
        parsed, attachments = await anyio.to_thread.run_sync(parse_email, content)
        source_url, modified = _web_url(info.get("webLink")), info.get("lastModifiedDateTime")
    else:
        root = "https://graph.microsoft.com/v1.0" + ("/drives/" + quote(drive_id, safe="") if drive_id else "/me/drive") + "/items/" + rid
        if provider == "microsoft_sharepoint" and not drive_id:
            raise HTTPException(422, "Selecciona la biblioteca de SharePoint del documento.")
        info = await _json("GET", root, access=access, params={"$select": "id,name,file,size,webUrl,lastModifiedDateTime"})
        if "file" not in info:
            raise HTTPException(422, "Selecciona un archivo, no una carpeta o biblioteca.")
        name = _name(info.get("name", "documento.txt"))
        content = await _binary(root + "/content", access, microsoft_redirect=True)
        source_url, modified = _web_url(info.get("webUrl")), info.get("lastModifiedDateTime")
    if provider != "microsoft_outlook":
        from app.services.despacho_ai import extract_document
        parsed = await anyio.to_thread.run_sync(extract_document, content, name)
    source = {"provider": provider, "connection_id": cid, "resource_id": resource_id, "drive_id": drive_id or None,
              "url": source_url, "modified_at": modified, "imported_at": store.utcnow(), "sha256": hashlib.sha256(content).hexdigest()}
    item = await _save_import(owner, token, name, content, parsed, source, matter_id, key)
    warnings, saved_attachments = list(parsed.get("warnings", [])), []
    for index, (filename, binary) in enumerate(attachments):
        try:
            from app.services.despacho_ai import extract_document
            att = await anyio.to_thread.run_sync(extract_document, binary, filename)
            att_key = hashlib.sha256((key + ":" + str(index) + ":" + hashlib.sha256(binary).hexdigest()).encode()).hexdigest()
            saved_attachments.append(await _save_import(owner, token, filename, binary, att,
                {**source, "email_document_id": item["id"], "attachment_index": index}, matter_id, att_key))
        except HTTPException as exc:
            warnings.append(f"Adjunto {filename}: {exc.detail} El original EML conserva el adjunto.")
    return {"item": item, "attachments": saved_attachments, "warnings": warnings}


async def disconnect(owner: str, cid: str) -> dict:
    row = await owned_connection(owner, cid, secret=True)
    warnings = []
    # Remove server access first, even when the provider's revocation is down.
    rows = await admin("DELETE", "despacho_conexiones", params={"id": "eq." + row["id"], "owner_id": "eq." + owner})
    if not rows:
        raise HTTPException(409, "La conexión cambió mientras se desconectaba.")
    if row["provider"] == "google_drive":
        try:
            value = decrypt(row["secret"])
            token = value.get("refresh_token") or value.get("access_token")
            await _json("POST", "https://oauth2.googleapis.com/revoke", data={"token": token})
        except HTTPException:
            warnings.append("La credencial local se eliminó, pero Google no confirmó la revocación. Revisa los permisos de aplicaciones en tu cuenta Google.")
    else:
        warnings.append("La credencial se eliminó del despacho. El consentimiento de Microsoft se administra también desde los permisos de aplicaciones de tu cuenta; no se cierran tus otras sesiones.")
    return {"disconnected": True, "warnings": warnings}


async def cleanup_owner_connections(owner: str) -> dict:
    """Account deletion hook: remove local credentials without provider calls.

    Call before deleting Auth; the foreign-key cascade is an additional guard.
    A failed cleanup stops the account deletion instead of reporting success.
    """
    owner = store.uuid_text(owner)
    filters = {"owner_id": "eq." + owner}
    rows = await admin("GET", "despacho_conexiones", params={**filters, "select": SAFE_CONNECTION_FIELDS})
    if not isinstance(rows, list):
        raise HTTPException(502, "No se pudo comprobar las conexiones antes de eliminar la cuenta.")
    for row in rows:
        public_connection(row, owner)
    # Invalidate pending authorizations as well as saved refresh credentials.
    await admin("DELETE", "despacho_oauth_estados", params=filters)
    await admin("DELETE", "despacho_conexiones", params=filters)
    for table in ("despacho_oauth_estados", "despacho_conexiones"):
        remaining = await admin("GET", table, params={**filters, "select": "owner_id", "limit": 1})
        if remaining != []:
            raise HTTPException(502, "Aún quedan conexiones de la cuenta. La eliminación debe detenerse.")
    warnings = []
    if rows:
        warnings.append("Se eliminaron las credenciales del despacho. Puedes retirar también el consentimiento de la aplicación en los permisos de Google o Microsoft; la eliminación local no modifica tus otras sesiones.")
    return {"disconnected": len(rows), "warnings": warnings}


async def export_owner(owner: str, token: str) -> dict:
    """Export only connection metadata, authorized by the account's own JWT."""
    owner = store.uuid_text(owner)
    rows = await store.db_request("POST", "rpc/despacho_connections_export", token, json={"p_owner": owner})
    if not isinstance(rows, list):
        raise HTTPException(403, "No se pudo autorizar la exportación de conexiones de esta cuenta.")
    return {"connections": [public_connection(row, owner) for row in rows],
            "credentials": "Las credenciales no se exportan. Cada cuenta debe conectar los proveedores de nuevo."}
