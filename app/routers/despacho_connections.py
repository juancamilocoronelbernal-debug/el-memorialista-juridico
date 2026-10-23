"""API privada de conexiones; callback OAuth ligado a sesión y cookie de inicio."""
from __future__ import annotations

import re
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.routers.despacho_data import identity
from app.routers.despacho_signatures import _safe_origin
from app.services import despacho_connections as connections
from app.services.sesiones import SIN_CACHE, usuario_de_sesion, validar_mismo_origen

router = APIRouter(prefix="/api/despacho/connections", tags=["Conexiones externas"])
callback_router = APIRouter(prefix="/oauth/despacho", tags=["Retorno OAuth"])


class OAuthAccessLogFilter(logging.Filter):
    """Uvicorn normally logs callback query strings, including OAuth codes."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) >= 3:
            route = record.args[2]
            if isinstance(route, str) and route.startswith("/oauth/despacho/"):
                args = list(record.args)
                args[2] = route.split("?", 1)[0]
                record.args = tuple(args)
        return True


_access_logger = logging.getLogger("uvicorn.access")
if not any(isinstance(f, OAuthAccessLogFilter) for f in _access_logger.filters):
    _access_logger.addFilter(OAuthAccessLogFilter())


class ImportResource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_id: str = Field(min_length=1, max_length=512)
    drive_id: str = Field("", max_length=512)
    matter_id: UUID | None = None


@router.get("")
async def status(request: Request):
    owner, _ = await identity(request)
    return await connections.list_connections(owner)


@router.post("/{provider}/authorize")
async def authorize(provider: str, request: Request, response: Response):
    owner, _ = await identity(request)
    validar_mismo_origen(request)
    data, binding = await connections.begin(owner, provider, _safe_origin(request))
    response.set_cookie("em_oauth_" + provider, binding, max_age=900,
        httponly=True, secure=get_settings().ENVIRONMENT == "production" or request.url.scheme == "https",
        samesite="lax", path="/oauth/despacho/" + provider)
    response.headers.update(SIN_CACHE)
    return data


@callback_router.get("/{provider}")
async def callback(provider: str, request: Request, code: str = "", state: str = "", error: str = ""):
    # Callback fields are never reflected into HTML, redirects or logs.
    # Do not log query strings for /oauth/despacho in the reverse proxy.
    if provider not in connections.PROVIDERS:
        raise HTTPException(404, "La conexión no está disponible.")
    try:
        user = await usuario_de_sesion(request)
        if not user:
            raise HTTPException(401, "La sesión del despacho caducó. Inicia sesión y conecta de nuevo.")
        if error:
            raise HTTPException(400, "El proveedor no autorizó la conexión. Puedes volver a iniciarla desde Ajustes.")
        await connections.complete(user["id"], provider, state,
            request.cookies.get("em_oauth_" + provider, ""), code)
        response = RedirectResponse("/app#ajustes", status_code=303, headers=SIN_CACHE)
    except HTTPException as exc:
        # Fixed safe messages only; provider's error_description may contain secrets.
        from html import escape
        response = HTMLResponse("<!doctype html><html lang='es'><meta charset='utf-8'><title>Conexión externa</title>"
            "<main><h1>No se completó la conexión</h1><p>" + escape(str(exc.detail)) +
            "</p><p><a href='/app#ajustes'>Volver a los ajustes del despacho</a></p></main></html>", status_code=exc.status_code, headers=SIN_CACHE)
    response.delete_cookie("em_oauth_" + provider, path="/oauth/despacho/" + provider,
        httponly=True, secure=get_settings().ENVIRONMENT == "production" or request.url.scheme == "https", samesite="lax")
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.get("/{connection_id}/resources")
async def resources(connection_id: UUID, request: Request, q: str = Query("", max_length=300),
                    folder_id: str = Query("", max_length=512), drive_id: str = Query("", max_length=512),
                    site_id: str = Query("", max_length=512), cursor: str = Query("", max_length=16000)):
    owner, _ = await identity(request)
    return await connections.resources(owner, str(connection_id), q=q, folder_id=folder_id, drive_id=drive_id, site_id=site_id, cursor=cursor)


@router.post("/{connection_id}/import")
async def import_resource(connection_id: UUID, payload: ImportResource, request: Request):
    owner, token = await identity(request)
    return await connections.import_resource(owner, token, str(connection_id), payload.resource_id,
        drive_id=payload.drive_id, matter_id=str(payload.matter_id) if payload.matter_id else None)


@router.delete("/{connection_id}")
async def disconnect(connection_id: UUID, request: Request):
    owner, _ = await identity(request)
    return await connections.disconnect(owner, str(connection_id))
