"""PWA ciudadana aislada: /asesor/ nunca almacena una respuesta de sesión.

El shell que puede guardarse es un archivo generado y público, idéntico para
todas las personas. /asesor/ comprueba la sesión en línea y no se almacena.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.services.sesiones import SIN_CACHE, usuario_de_sesion

router = APIRouter(include_in_schema=False)
PWA_DIR = Path(__file__).resolve().parents[1] / "static" / "asesor" / "pwa"


def archivo_publico(nombre: str, media_type: str, **extra_headers) -> FileResponse:
    """Solo nombres constantes del router; nunca una ruta aportada por usuario."""
    path = PWA_DIR / nombre
    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail="La aplicación ciudadana se está preparando. Vuelve a intentarlo.",
            headers=SIN_CACHE,
        )
    return FileResponse(path, media_type=media_type, headers={
        "Cache-Control": "public, max-age=0, must-revalidate",
        "X-Content-Type-Options": "nosniff",
        "X-Robots-Tag": "noindex, follow",
        **extra_headers,
    })


@router.get("/asesor")
@router.get("/asesor/")
async def abrir_asesor(request: Request):
    try:
        usuario = await usuario_de_sesion(request)
    except HTTPException as exc:
        raise HTTPException(exc.status_code, exc.detail, headers=SIN_CACHE) from None
    if usuario:
        return RedirectResponse("/app", status_code=303, headers=SIN_CACHE)
    if request.url.path == "/asesor":
        return RedirectResponse("/asesor/", status_code=303, headers=SIN_CACHE)
    # Esta respuesta depende de la cookie. El worker jamás la guarda: usa el
    # shell independiente de abajo únicamente cuando no hay conexión.
    return archivo_publico("shell.html", "text/html", **SIN_CACHE)


@router.get("/asesor/offline-shell.html")
async def shell_publico():
    # No Request, sesión, cookies, consultas ni información generada de usuarios.
    return archivo_publico("shell.html", "text/html")


@router.get("/asesor/manifest.webmanifest")
async def manifest_publico():
    return archivo_publico("manifest.webmanifest", "application/manifest+json")


@router.get("/asesor/sw.js")
async def worker_publico():
    return archivo_publico(
        "sw.js", "application/javascript",
        **{"Cache-Control": "no-cache", "Service-Worker-Allowed": "/asesor/"},
    )
