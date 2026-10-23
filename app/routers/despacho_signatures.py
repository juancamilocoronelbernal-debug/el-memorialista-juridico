"""Solicitudes privadas y aceptación mediante enlace de un solo uso.

El acceso al enlace prueba posesión del enlace, no identidad acreditada. Toda
evidencia lo declara. Los RPC públicos se invocan exclusivamente desde servidor.
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
import secrets
import time
from collections import defaultdict, deque
from urllib.parse import urlsplit
from uuid import UUID

import anyio
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import get_settings
from app.services.despacho_export import filename, make_pdf
from app.services.limites import ip_cliente, verificar_acceso
from app.services.sesiones import token_bearer

router = APIRouter(prefix="/api/despacho", tags=["Firma electrónica"])
public_router = APIRouter(prefix="/api/firmas-publicas", tags=["Aceptación por enlace privado"])
_attempts = defaultdict(deque)
_last_clean = 0.0


class SignatureCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., min_length=1, max_length=240)
    text: str = Field(..., min_length=1, max_length=300_000)
    signer_name: str = Field(..., min_length=2, max_length=160)
    signer_email: str = Field(..., min_length=3, max_length=254)
    expires_days: int = Field(7, ge=1, le=30)

    @field_validator("title", "signer_name")
    @classmethod
    def printable_label(cls, value):
        value = value.strip()
        if not value or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("Usa texto legible para el nombre y el título.")
        return value

    @field_validator("text")
    @classmethod
    def document_text(cls, value):
        if not value.strip() or "\x00" in value:
            raise ValueError("El documento debe contener texto válido.")
        return value

    @field_validator("signer_email")
    @classmethod
    def email(cls, value):
        value = value.strip().lower()
        if re.search(r"[\x00-\x1f\x7f]", value) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Revisa el correo del destinatario.")
        return value


class LinkToken(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(..., pattern=r"^[A-Za-z0-9_-]{43}$")


class SignatureAccept(LinkToken):
    name: str = Field(..., min_length=2, max_length=160)
    email: str = Field(..., min_length=3, max_length=254)
    consent: bool

    @field_validator("name")
    @classmethod
    def printable_name(cls, value):
        value = value.strip()
        if len(value) < 2 or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("Escribe tu nombre completo.")
        return value

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        return SignatureCreate.email(value)


def signing_available():
    s = get_settings()
    return bool(s.DESPACHO_SIGNING_ENABLED and s.SUPABASE_URL and s.SUPABASE_ANON_KEY and s.SUPABASE_SERVICE_ROLE_KEY)


def _configuration(token=None, *, admin=False):
    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_ANON_KEY:
        raise HTTPException(503, "El almacenamiento del despacho aún no está configurado.")
    key = s.SUPABASE_SERVICE_ROLE_KEY if admin else s.SUPABASE_ANON_KEY
    if admin and not signing_available():
        raise HTTPException(503, "La firma por enlace requiere activar el servicio de firma del despacho.")
    return s.SUPABASE_URL.rstrip("/"), {"apikey": key, "Authorization": "Bearer " + (key if admin else token or ""), "Content-Type": "application/json"}


def _response(response):
    if response.status_code >= 400:
        try:
            error = response.json()
            message = str(error.get("message", ""))
            code = str(error.get("code", ""))
        except (ValueError, AttributeError):
            message, code = "", ""
        if code in {"42P01", "42883", "PGRST202", "PGRST205"}:
            raise HTTPException(503, "Falta aplicar la migración de firma electrónica del despacho.")
        if "LINK_UNAVAILABLE" in message or "NOT_FOUND" in message:
            raise HTTPException(404, "El enlace no está disponible, caducó o fue cancelado.")
        if "ALREADY_SIGNED" in message or "NOT_PENDING" in message:
            raise HTTPException(409, "Esta solicitud ya fue firmada o cancelada.")
        if "INVALID_ACCEPTANCE" in message:
            raise HTTPException(422, "Comprueba tu nombre, el correo del destinatario y la aceptación del documento.")
        if "SIGNATURE_LIMIT" in message:
            raise HTTPException(429, "Se alcanzó el límite diario de solicitudes de firma.")
        if "INVALID_INPUT" in message:
            raise HTTPException(422, "Revisa los datos de la solicitud de firma.")
        if response.status_code in (401,403):
            raise HTTPException(503, "El servicio de firma no pudo validar sus permisos. Revisa su configuración.")
        raise HTTPException(502, "No pudimos completar la operación de firma. No se confirmó ningún cambio.")
    try:
        return response.json()
    except ValueError:
        raise HTTPException(502, "El servicio de firma devolvió una respuesta no válida.") from None


async def _rpc(name, payload, token=None, *, admin=False):
    base, headers = _configuration(token, admin=admin)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            response = await client.post(base + "/rest/v1/rpc/" + name, headers=headers, json=payload)
        return _response(response)
    except httpx.HTTPError:
        raise HTTPException(502, "No se recibió confirmación del servicio de firma. Consulta el estado antes de reintentar.") from None


def _safe_origin(request):
    s = get_settings()
    local_hosts = {"localhost", "127.0.0.1", "::1", "testserver"}
    raw = s.APP_BASE_URL
    try:
        if not raw:
            if s.ENVIRONMENT == "production":
                raise ValueError("Falta el dominio canónico")
            raw = str(request.base_url)
            # El Host de una petición nunca decide el destino de una firma
            # compartida. Sólo se permite este atajo para un servidor local.
            if urlsplit(raw).hostname not in local_hosts:
                raise ValueError("El Host no sustituye APP_BASE_URL")
        if any(c.isspace() or ord(c) < 32 or c in "\\\"'<>" for c in raw):
            raise ValueError("Caracteres inválidos en el origen")
        parsed = urlsplit(raw)
        host = parsed.hostname
        port = parsed.port  # Fuerza validación incluso si no se utiliza.
        allowed_http = s.ENVIRONMENT != "production" and host in local_hosts
        if (not host or parsed.username is not None or parsed.password is not None or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment or port == 0
                or (parsed.scheme != "https" and not (parsed.scheme == "http" and allowed_http))):
            raise ValueError("Origen inválido")
        try:
            address = ipaddress.ip_address(host)
            host = f"[{address.compressed}]" if address.version == 6 else str(address)
        except ValueError:
            host = host.encode("idna").decode("ascii").lower()
            if len(host) > 253 or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part) for part in host.split(".")):
                raise ValueError("Dominio inválido")
        return f"{parsed.scheme}://{host}" + (f":{port}" if port is not None else "")
    except (ValueError, UnicodeError):
        raise HTTPException(503, "Configura APP_BASE_URL con el dominio HTTPS del despacho para compartir firmas.")


def _rate_limit(request, *, signing=False):
    global _last_clean
    now = time.monotonic()
    if now - _last_clean > 300:
        for key in list(_attempts):
            if not _attempts[key] or now - _attempts[key][-1] > 3600:
                del _attempts[key]
        _last_clean = now
    key = (ip_cliente(request), signing)
    queue = _attempts[key]
    while queue and queue[0] < now - 3600:
        queue.popleft()
    if len(queue) >= (20 if signing else 120):
        raise HTTPException(429, "Se alcanzó el límite de intentos. Espera antes de volver a intentarlo.", headers={"Retry-After":"3600"})
    queue.append(now)


async def _owned(request, signature_id=None):
    user = await verificar_acceso(request)
    base, headers = _configuration(token_bearer(request))
    fields = "id,title,signer_name,signer_email,status,created_at,expires_at,signed_at,document_hash,signed_name,signed_email,consent_text,signer_ip,signer_agent,audit"
    if signature_id:
        fields += ",document_text"
    query = {"owner_id":"eq."+user["id"], "select":fields, "order":"created_at.desc", "limit":1000}
    if signature_id:
        query["id"] = "eq."+str(signature_id)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            response = await client.get(base+"/rest/v1/despacho_firmas", headers=headers, params=query)
        rows = _response(response)
    except httpx.HTTPError:
        raise HTTPException(502, "No pudimos consultar las solicitudes de firma.") from None
    if not isinstance(rows,list):
        raise HTTPException(502, "El servicio de firma devolvió un formato no válido.")
    if signature_id:
        if not rows:
            raise HTTPException(404, "No se encontró la solicitud de firma en tu cuenta.")
        return rows[0]
    return {"signatures":rows, "has_more":len(rows)==1000}


@router.get("/signatures")
async def list_signatures(request: Request):
    return await _owned(request)


@router.post("/signatures")
async def create_signature(payload: SignatureCreate, request: Request):
    await verificar_acceso(request)
    if not signing_available():
        raise HTTPException(503, "La firma electrónica necesita configurar el servicio de firma y aplicar su migración.")
    origin = _safe_origin(request)  # validar antes de escribir
    token = secrets.token_urlsafe(32)
    record = await _rpc("despacho_crear_firma", {"p_title":payload.title,"p_text":payload.text,
        "p_name":payload.signer_name,"p_email":payload.signer_email,"p_token_hash":hashlib.sha256(token.encode()).hexdigest(),
        "p_days":payload.expires_days},token_bearer(request))
    # El secreto sólo se entrega una vez. No aparece en la base ni en la ruta HTTP.
    return {"signature":record,"signing_url":origin+"/firmar#"+token}


@router.get("/signatures/{signature_id}")
async def get_signature(signature_id: UUID, request: Request):
    return await _owned(request, signature_id)


@router.post("/signatures/{signature_id}/cancel")
async def cancel_signature(signature_id: UUID, request: Request):
    await verificar_acceso(request)
    return await _rpc("despacho_cancelar_firma", {"p_id":str(signature_id)}, token_bearer(request))


@router.post("/signatures/{signature_id}/link")
async def renew_signature_link(signature_id: UUID, request: Request):
    await verificar_acceso(request)
    if not signing_available():
        raise HTTPException(503, "El servicio de firma por enlace no está habilitado.")
    origin = _safe_origin(request)
    token = secrets.token_urlsafe(32)
    record = await _rpc("despacho_renovar_enlace_firma", {"p_id":str(signature_id),
        "p_token_hash":hashlib.sha256(token.encode()).hexdigest()}, token_bearer(request))
    return {"signature":record,"signing_url":origin+"/firmar#"+token,
            "notice":"El nuevo enlace vence en siete días y sustituye cualquier enlace anterior."}


@router.get("/signatures/{signature_id}/receipt")
async def receipt(signature_id: UUID, request: Request):
    record = await _owned(request, signature_id)
    if record["status"] != "signed":
        raise HTTPException(409, "El comprobante se genera cuando el destinatario acepta el documento.")
    proof = "\n\nCONSTANCIA DE ACEPTACIÓN ELECTRÓNICA\n\n" + "\n".join([
        "Solicitud: "+record["id"], "Nombre declarado: "+str(record.get("signed_name","")),
        "Correo declarado: "+str(record.get("signed_email","")),
        "Fecha de aceptación (UTC): "+str(record["signed_at"]),
        "Huella SHA-256 del texto UTF-8 original: "+record["document_hash"],
        "IP registrada por el servidor: "+str(record.get("signer_ip","")),
        "Consentimiento: "+str(record.get("consent_text","")),
        "Método: posesión de enlace privado e identidad declarada. No incluye verificación documental de identidad ni certificado de firma digital.",
        "La huella corresponde al texto original almacenado; este PDF añade esta constancia y no comparte la misma huella."
    ])
    data = await anyio.to_thread.run_sync(make_pdf, record["title"], record["document_text"]+proof)
    return Response(data, media_type="application/pdf", headers={"Content-Disposition":f'attachment; filename="{filename(record["title"]+"-constancia", "pdf")}"',"Cache-Control":"private, no-store"})


@public_router.post("/ver")
async def public_view(payload: LinkToken, request: Request):
    _rate_limit(request)
    return await _rpc("despacho_ver_firma", {"p_token_hash":hashlib.sha256(payload.token.encode()).hexdigest()}, admin=True)


@public_router.post("/aceptar")
async def public_accept(payload: SignatureAccept, request: Request):
    _rate_limit(request, signing=True)
    if not payload.consent:
        raise HTTPException(422, "Debes leer y aceptar el documento antes de firmarlo.")
    return await _rpc("despacho_aceptar_firma", {"p_token_hash":hashlib.sha256(payload.token.encode()).hexdigest(),
        "p_name":payload.name.strip(),"p_email":payload.email.strip().lower(),"p_consent":payload.consent,
        "p_ip":ip_cliente(request)[:64],"p_agent":request.headers.get("user-agent","")[:512]}, admin=True)
