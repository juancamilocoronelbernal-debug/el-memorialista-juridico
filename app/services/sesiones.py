"""Puente de sesión para navegación HTML; las APIs privadas siguen usando Bearer.

La cookie contiene un access token validado por Supabase, nunca una identidad
aportada por el navegador. Su duración nunca supera la expiración del JWT.
"""
from __future__ import annotations

import time
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, Response

from app.config import get_settings
from app.services import supabase_service

COOKIE_SESION = "em_session"
SIN_CACHE = {"Cache-Control": "private, no-store, max-age=0", "Pragma": "no-cache", "Vary": "Cookie, Authorization"}


def token_bearer(request: Request) -> str:
    esquema, _, token = request.headers.get("authorization", "").strip().partition(" ")
    return token.strip() if esquema.lower() == "bearer" else ""


def validar_mismo_origen(request: Request) -> None:
    """Protege el establecimiento y borrado de cookies frente a otro sitio."""
    if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
        raise HTTPException(status_code=403, detail="Esta operación debe realizarse desde El Memorialista.")
    origen = request.headers.get("origin")
    if origen is None:  # Clientes no navegador: POST sigue exigiendo Bearer.
        return
    s = get_settings()
    base = s.APP_BASE_URL.strip().rstrip("/") or str(request.base_url).rstrip("/")
    parsed = urlsplit(base)
    esperado = f"{parsed.scheme}://{parsed.netloc}"
    if origen.rstrip("/") != esperado:
        raise HTTPException(status_code=403, detail="El origen de la solicitud no está permitido.")


async def usuario_de_sesion(request: Request):
    """Solo para rutas HTML y el puente; nunca autoriza automáticamente la API."""
    token = token_bearer(request) or request.cookies.get(COOKIE_SESION, "")
    if not token:
        return None
    try:
        return await supabase_service.validar_token_supabase(token)
    except supabase_service.ErrorSupabase as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


def poner_cookie_sesion(response: Response, request: Request, token: str) -> None:
    expiracion = supabase_service.expiracion_token(token)
    restantes = int(expiracion - time.time()) if expiracion else 0
    if restantes <= 0:
        raise HTTPException(status_code=401, detail="La sesión ha expirado. Inicia sesión de nuevo.")
    if len(token.encode("utf-8")) > 3800:
        raise HTTPException(status_code=400, detail="La sesión es demasiado grande para este navegador. Contacta con el administrador.")
    s = get_settings()
    response.set_cookie(
        key=COOKIE_SESION,
        value=token,
        max_age=min(restantes, s.AUTH_COOKIE_MAX_AGE_SECONDS),
        httponly=True,
        secure=s.ENVIRONMENT == "production" or request.url.scheme == "https",
        samesite="lax",
        path="/",
    )
    response.headers.update(SIN_CACHE)


def borrar_cookie_sesion(response: Response, request: Request) -> None:
    response.delete_cookie(
        COOKIE_SESION, path="/", httponly=True, samesite="lax",
        secure=get_settings().ENVIRONMENT == "production" or request.url.scheme == "https",
    )
    response.headers.update(SIN_CACHE)
