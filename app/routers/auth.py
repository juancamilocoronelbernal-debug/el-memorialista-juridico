"""Router de Autenticación, Perfil y Privacidad de Datos (v2.3.0).

Endpoints:
- GET /api/auth/config: Configuración pública de Supabase para el cliente web.
- GET /api/usuario/perfil: Información del usuario autenticado, firma y cuota.
- GET /api/usuario/exportar-datos: Exportación completa de datos ("Exportar todos mis datos").
- DELETE /api/usuario/eliminar-cuenta: Eliminación irrevocable de cuenta y datos ("Eliminar mi cuenta").
"""

import json
import time
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.services.limites import verificar_acceso
from app.services.sesiones import (
    SIN_CACHE, COOKIE_SESION, token_bearer, usuario_de_sesion,
    validar_mismo_origen, poner_cookie_sesion, borrar_cookie_sesion,
)
from app.services.supabase_service import (
    exportar_todos_los_datos,
    eliminar_cuenta_usuario,
    invalidar_token,
    ErrorSupabase,
)

router = APIRouter(prefix="/api", tags=["Autenticación y Usuario"])


@router.get("/auth/config")
async def endpoint_auth_config():
    """Retorna las variables públicas para inicializar Supabase JS en el navegador."""
    settings = get_settings()
    return {
        "supabase_url": settings.SUPABASE_URL,
        "supabase_anon_key": settings.SUPABASE_ANON_KEY,
        "auth_requerido": True,
        "configurado": bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY),
        "allow_signup": settings.AUTH_ALLOW_SIGNUP,
        "callback_path": "/auth/callback",
        "storage_bucket": settings.SUPABASE_STORAGE_BUCKET,
        "limite_diario_usuario": settings.LIMITE_DIA_USUARIO,
    }


@router.post("/auth/sesion")
async def establecer_sesion(request: Request, response: Response):
    """Un JWT verificado habilita navegación privada; no se devuelve el token."""
    validar_mismo_origen(request)
    usuario = await verificar_acceso(request)
    poner_cookie_sesion(response, request, token_bearer(request))
    return {"ok": True, "autenticado": True, "redirect": "/app", "usuario": {
        "id": usuario["id"], "email": usuario.get("email", ""),
    }}


@router.get("/auth/sesion")
async def consultar_sesion(request: Request, response: Response):
    response.headers.update(SIN_CACHE)
    usuario = await usuario_de_sesion(request)
    if not usuario:
        raise HTTPException(status_code=401, detail="No hay una sesión activa.", headers=SIN_CACHE)
    return {"ok": True, "autenticado": True, "usuario": {"id": usuario["id"], "email": usuario.get("email", "")}}


@router.delete("/auth/sesion")
async def cerrar_sesion(request: Request, response: Response):
    validar_mismo_origen(request)
    # El cliente debe llamar también a supabase.auth.signOut para revocar sus
    # refresh tokens. Aquí se borra el puente y su validación local en caché.
    invalidar_token(token_bearer(request))
    invalidar_token(request.cookies.get(COOKIE_SESION, ""))
    borrar_cookie_sesion(response, request)
    return {"ok": True, "redirect": "/login"}


@router.get("/usuario/perfil")
async def endpoint_perfil_usuario(request: Request):
    """Retorna el perfil del usuario autenticado y su firma."""
    usuario = await verificar_acceso(request)
    if not usuario:
        raise HTTPException(status_code=401, detail="No autenticado.")

    settings = get_settings()
    user_id = usuario.get("id") or usuario.get("sub", "desconocido")
    email = usuario.get("email", "")

    return {
        "ok": True,
        "id": user_id,
        "email": email,
        "rol": usuario.get("user_metadata", {}).get("rol", "abogado"),
        "nombre": usuario.get("user_metadata", {}).get("nombre", email.split("@")[0] if email else "Abogado"),
        "limite_diario": settings.LIMITE_DIA_USUARIO,
    }


@router.get("/usuario/exportar-datos")
async def endpoint_exportar_datos(request: Request):
    """Exporta todos los datos del usuario (perfil, firma, clientes, casos, documentos, versiones) en JSON."""
    usuario = await verificar_acceso(request)
    if not usuario:
        raise HTTPException(status_code=401, detail="Se requiere sesión activa para exportar datos.")

    user_id = usuario.get("id") or usuario.get("sub")
    auth_header = request.headers.get("authorization", "")
    token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else ""

    try:
        datos_exportados = await exportar_todos_los_datos(user_id=user_id, token=token)
    except ErrorSupabase as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None

    fecha_hoy = time.strftime("%Y-%m-%d")
    nombre_archivo = f"el_memorialista_mis_datos_{fecha_hoy}.json"
    contenido_json = json.dumps(datos_exportados, indent=2, ensure_ascii=False)

    return Response(
        content=contenido_json,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre_archivo}"',
            "Cache-Control": "no-store",
        },
    )


@router.delete("/usuario/eliminar-cuenta")
async def endpoint_eliminar_cuenta(request: Request, response: Response):
    """Elimina definitivamente la cuenta del usuario y todos sus registros en la base de datos y storage."""
    usuario = await verificar_acceso(request)
    if not usuario:
        raise HTTPException(status_code=401, detail="Se requiere sesión activa para eliminar la cuenta.")

    user_id = usuario.get("id") or usuario.get("sub")
    auth_header = request.headers.get("authorization", "")
    token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else ""

    try:
        exito = await eliminar_cuenta_usuario(user_id=user_id, token=token)
    except ErrorSupabase as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    if not exito:
        raise HTTPException(status_code=500, detail="No se pudo completar la eliminación total de la cuenta.")

    borrar_cookie_sesion(response, request)
    return {
        "ok": True,
        "mensaje": "Tu cuenta, tus registros personales y los archivos personales de la aplicación fueron eliminados. Los registros compartidos de otras personas permanecen en su despacho.",
        "usuario_id": user_id,
    }
