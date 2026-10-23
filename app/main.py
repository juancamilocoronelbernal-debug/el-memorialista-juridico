"""El Memorialista: asesor público y espacio profesional con acceso verificado."""
import asyncio
import base64
import contextlib
import hashlib
import logging
import re
from contextlib import asynccontextmanager
from functools import lru_cache
from html.parser import HTMLParser
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import MutableHeaders

from app.config import get_settings
from app.routers import asesor_paginas, asesor_pwa, auth, calculos, documents
from app.services.asesor_paginas import metadatos_publicos
from app.services.gemini_service import gemini_service
from app.services.limites import verificar_acceso
from app.services.sesiones import SIN_CACHE, usuario_de_sesion, borrar_cookie_sesion

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("memorialista")


class _ScriptsPublicos(HTMLParser):
    """Hashes de scripts de una plantilla confiable, no de datos del visitante."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.hashes = set()
        self._contenido = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self._contenido = None if "src" in dict(attrs) else []

    def handle_data(self, data):
        if self._contenido is not None:
            self._contenido.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._contenido is not None:
            # El analizador HTML del navegador normaliza los saltos de línea.
            contenido = "".join(self._contenido).replace("\r\n", "\n").replace("\r", "\n")
            digest = base64.b64encode(hashlib.sha256(contenido.encode("utf-8")).digest()).decode("ascii")
            self.hashes.add(f"'sha256-{digest}'")
            self._contenido = None


def hashes_scripts_publicos(html: str) -> tuple[str, ...]:
    parser = _ScriptsPublicos()
    parser.feed(html)
    parser.close()
    return tuple(sorted(parser.hashes))


@lru_cache(maxsize=32)
def _hashes_archivo_publico(path: str, mtime_ns: int, size: int) -> tuple[str, ...]:
    # mtime y tamaño invalidan la caché tras reconstruir los activos públicos.
    return hashes_scripts_publicos(Path(path).read_text(encoding="utf-8"))


def _origenes_supabase_csp() -> tuple[str, ...]:
    """Solo un origen configurado y válido; jamás interpolar la URL sin validar."""
    valor = get_settings().SUPABASE_URL.strip()
    if not valor or any(c.isspace() or ord(c) < 32 or c in "\\'\";" for c in valor):
        return ()
    try:
        url = urlsplit(valor)
        if (url.scheme not in {"http", "https"} or not url.hostname or url.username is not None
                or url.password is not None or url.path not in {"", "/"} or url.query or url.fragment):
            return ()
        puerto = url.port
        if puerto is not None and puerto < 1:
            return ()
        host = url.hostname
        try:
            ip = ip_address(host)
            if "%" in host:
                return ()
            host = f"[{ip.compressed}]" if ip.version == 6 else str(ip)
        except ValueError:
            host = host.encode("idna").decode("ascii").lower()
            if len(host) > 253 or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", parte) for parte in host.split(".")):
                return ()
        autoridad = host + (f":{puerto}" if puerto is not None else "")
        return (f"{url.scheme}://{autoridad}", f"{'wss' if url.scheme == 'https' else 'ws'}://{autoridad}")
    except (ValueError, UnicodeError):
        return ()


def csp_publica(hashes: tuple[str, ...] = (), *, ingreso: bool = False) -> str:
    conexiones = ("'self'", *(_origenes_supabase_csp() if ingreso else ()))
    return "; ".join((
        "default-src 'none'",
        "script-src " + " ".join(("'self'", *hashes)),
        "script-src-attr 'none'",
        # Los formularios y la impresión aplican estilos desde JS; nunca código inline.
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src " + " ".join(conexiones),
        "media-src 'self' blob:",
        "object-src 'none'",
        "frame-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "worker-src 'self'",
        "manifest-src 'self'",
    ))


def csp_archivo_publico(path: Path, *, ingreso: bool = False) -> str:
    try:
        estado = path.stat()
        hashes = _hashes_archivo_publico(str(path), estado.st_mtime_ns, estado.st_size)
    except (OSError, UnicodeError):
        hashes = ()  # Un archivo ausente o inválido nunca habilita código arbitrario.
    return csp_publica(hashes, ingreso=ingreso)


async def keep_alive_worker(url_base: str) -> None:
    """Ping cada 9 minutos para que el plan gratuito de Render no se duerma (se apaga a los 15)."""
    await asyncio.sleep(45)
    destino = url_base.rstrip("/") + "/api/health"
    async with httpx.AsyncClient(timeout=15.0) as cliente:
        while True:
            try:
                respuesta = await cliente.get(destino)
                log.debug("Keep-alive %s -> HTTP %s", destino, respuesta.status_code)
            except httpx.HTTPError as exc:
                log.warning("Keep-alive falló: %s", type(exc).__name__)
            await asyncio.sleep(540)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await gemini_service.iniciar()
    tareas = [asyncio.create_task(gemini_service.descubrir_modelos())]
    if settings.KEEP_ALIVE and "onrender.com" in settings.RENDER_EXTERNAL_URL:
        tareas.append(asyncio.create_task(keep_alive_worker(settings.RENDER_EXTERNAL_URL)))
    try:
        yield
    finally:
        for tarea in tareas:
            tarea.cancel()
        for tarea in tareas:
            with contextlib.suppress(BaseException):
                await tarea
        with contextlib.suppress(BaseException):
            await gemini_service.cerrar()


es_produccion = settings.ENVIRONMENT == "production"
app = FastAPI(
    title="El Memorialista - Generador Jurídico de Colombia",
    description="Asesor ciudadano público y generador jurídico privado con sesión Supabase.",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url=None if es_produccion else "/docs",
    redoc_url=None,
    openapi_url=None if es_produccion else "/openapi.json",
)


class AccesoAPI:
    """Cierre por defecto de /api: las nuevas rutas también quedan protegidas.

    ASGI puro para autenticar antes de consumir uploads o iniciar streaming.
    La cookie de navegación no sustituye el Bearer exigido por verificar_acceso.
    """
    PUBLICAS = frozenset({"/api/health", "/api/auth/config", "/api/auth/sesion"})

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path", "").startswith("/api/"):
            if scope["path"] not in self.PUBLICAS and scope.get("method") != "OPTIONS":
                try:
                    await verificar_acceso(Request(scope))
                except HTTPException as exc:
                    response = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)


class CabecerasSeguridad:
    """Middleware ASGI puro (no interfiere con las respuestas en streaming)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def enviar(mensaje):
            if mensaje["type"] == "http.response.start":
                cabeceras = MutableHeaders(scope=mensaje)
                cabeceras.setdefault("X-Content-Type-Options", "nosniff")
                cabeceras.setdefault("Referrer-Policy", "no-referrer")
                cabeceras.setdefault("X-Frame-Options", "DENY")
                path = scope.get("path", "")
                if (cabeceras.get("content-type", "").startswith("text/html")
                        and path in {"/asesor/", "/asesor/offline-shell.html"}):
                    cabeceras.setdefault("Content-Security-Policy", csp_archivo_publico(asesor_pwa.PWA_DIR / "shell.html"))
                if path.startswith(("/api/", "/app", "/generador", "/auth/", "/login")) or path == "/auditor.js":
                    cabeceras["Cache-Control"] = "private, no-store, max-age=0"
                    cabeceras["Pragma"] = "no-cache"
                    cabeceras["Vary"] = "Cookie, Authorization"
                    cabeceras["X-Robots-Tag"] = "noindex, nofollow"
                if get_settings().ENVIRONMENT == "production":
                    cabeceras.setdefault("Strict-Transport-Security", "max-age=31536000")
                cabeceras.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=(self)")
            await send(mensaje)

        await self.app(scope, receive, enviar)


app.add_middleware(AccesoAPI)
app.add_middleware(CabecerasSeguridad)

origenes = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
if origenes:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origenes,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )


@app.exception_handler(RequestValidationError)
async def solicitud_invalida(request: Request, exc: RequestValidationError):
    campos = sorted({str((error.get("loc") or ["?"])[-1]) for error in exc.errors()})
    return JSONResponse(
        status_code=422,
        content={"detail": "La solicitud es inválida o demasiado grande (revisa: " + ", ".join(campos) + ")."},
    )


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(calculos.router)
app.include_router(asesor_paginas.router)
app.include_router(asesor_pwa.router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
PRIVATE_DIR = Path(__file__).resolve().parent / "private"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/", include_in_schema=False)
async def root_index(request: Request):
    if await usuario_de_sesion(request):
        return RedirectResponse("/app", status_code=303, headers=SIN_CACHE)
    metadata = metadatos_publicos(
        "El Memorialista · Orientación jurídica para todos",
        "Orientación jurídica ciudadana gratuita en Colombia. Explora 66 casos y prepara un borrador con formularios guiados en tu navegador.",
        "/",
    )
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8").replace("<!-- PUBLIC_META -->", metadata)
    return HTMLResponse(html, headers={
        "Cache-Control": "no-store", "Vary": "Cookie",
        "Content-Security-Policy": csp_publica(hashes_scripts_publicos(html)),
    })


@app.get("/login", include_in_schema=False)
@app.get("/auth/callback", include_in_schema=False)
async def login_page(request: Request):
    # Callback siempre se procesa en el cliente: puede traer un enlace nuevo
    # cuando existe una cookie anterior de otro usuario.
    if request.url.path == "/login" and await usuario_de_sesion(request):
        return RedirectResponse("/app", status_code=303, headers=SIN_CACHE)
    return FileResponse(STATIC_DIR / "login.html", headers={
        **SIN_CACHE,
        "Content-Security-Policy": csp_archivo_publico(STATIC_DIR / "login.html", ingreso=True),
    })


@app.get("/app", include_in_schema=False)
@app.get("/app/", include_in_schema=False)
@app.get("/generador", include_in_schema=False)
@app.get("/generador/", include_in_schema=False)
async def espacio_profesional(request: Request):
    if not await usuario_de_sesion(request):
        response = RedirectResponse("/login?next=/app", status_code=303, headers=SIN_CACHE)
        borrar_cookie_sesion(response, request)
        return response
    return FileResponse(PRIVATE_DIR / "generador.html", headers=SIN_CACHE)


@app.get("/auditor.js", include_in_schema=False)
@app.get("/static/auditor.js", include_in_schema=False)
async def auditor_js(request: Request):
    if not await usuario_de_sesion(request):
        raise HTTPException(status_code=401, detail="Inicia sesión para acceder al espacio profesional.", headers=SIN_CACHE)
    return FileResponse(PRIVATE_DIR / "auditor.js", media_type="application/javascript", headers=SIN_CACHE)


class EstaticosPublicos(StaticFiles):
    """La misma CSP también protege el acceso directo a los HTML públicos."""

    async def get_response(self, path, scope):
        respuesta = await super().get_response(path, scope)
        if isinstance(respuesta, FileResponse) and respuesta.headers.get("content-type", "").startswith("text/html"):
            archivo = Path(respuesta.path)
            respuesta.headers["Content-Security-Policy"] = csp_archivo_publico(
                archivo, ingreso=archivo.resolve() == (STATIC_DIR / "login.html").resolve(),
            )
        return respuesta


# Solo activos públicos. app/private jamás se monta como StaticFiles.
app.mount("/static", EstaticosPublicos(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
