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
from app.routers import despacho_ai, despacho_data, despacho_export, despacho_signatures, despacho_word
from app.routers import despacho_agent, despacho_connections, despacho_knowledge, despacho_signing_v5
from app.routers import despacho_corpus_fuentes
from app.routers import despacho_rooms_v5
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
    url_keep = (settings.RENDER_EXTERNAL_URL or settings.APP_BASE_URL or "").strip()
    if settings.KEEP_ALIVE and "onrender.com" in url_keep:
        tareas.append(asyncio.create_task(keep_alive_worker(url_keep)))
    if settings.DESPACHO_MONITORS_ENABLED:
        if settings.SUPABASE_SERVICE_ROLE_KEY:
            from app.services.despacho_monitors import monitor_worker
            tareas.append(asyncio.create_task(monitor_worker()))
            log.info("Trabajador de monitores iniciado (sondeo cada %d s).", settings.DESPACHO_MONITOR_POLL_SECONDS)
        else:
            log.warning("DESPACHO_MONITORS_ENABLED=True pero falta SUPABASE_SERVICE_ROLE_KEY en el servidor.")
    if settings.DESPACHO_AGENT_WORKER_ENABLED:
        if settings.SUPABASE_SERVICE_ROLE_KEY:
            from app.services.despacho_agent import agent_worker
            tareas.append(asyncio.create_task(agent_worker()))
            log.info("Trabajador del agente iniciado (sondeo cada %d s).", settings.DESPACHO_AGENT_POLL_SECONDS)
        else:
            log.warning("DESPACHO_AGENT_WORKER_ENABLED=True pero falta SUPABASE_SERVICE_ROLE_KEY en el servidor.")
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
        with contextlib.suppress(BaseException):
            from app.services.despacho_agent import close
            await close()


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
    FIRMAS_PUBLICAS = frozenset({"/api/firmas-publicas/ver", "/api/firmas-publicas/aceptar",
        "/api/firmas-v5/view", "/api/firmas-v5/document", "/api/firmas-v5/otp", "/api/firmas-v5/accept",
        "/api/salas-v5/view", "/api/salas-v5/document", "/api/salas-v5/upload"})

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path", "").startswith("/api/"):
            firma_por_enlace = scope["path"] in self.FIRMAS_PUBLICAS and scope.get("method") == "POST"
            if scope["path"] not in self.PUBLICAS and not firma_por_enlace and scope.get("method") != "OPTIONS":
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
                if path == "/word":
                    # El panel Word se integra en hosts de Office declarados en su CSP.
                    del cabeceras["X-Frame-Options"]
                if (cabeceras.get("content-type", "").startswith("text/html")
                        and path in {"/asesor/", "/asesor/offline-shell.html"}):
                    cabeceras.setdefault("Content-Security-Policy", csp_archivo_publico(asesor_pwa.PWA_DIR / "shell.html"))
                if path.startswith(("/api/", "/app", "/generador", "/auth/", "/login", "/word", "/firmar", "/sala-cliente", "/oauth/")) or path == "/auditor.js":
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


class LimiteCuerpoDespacho:
    """Límite de transporte, incluso sin Content-Length, antes del parseo completo."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith(("/api/despacho/", "/api/firmas-publicas/", "/api/firmas-v5/", "/api/salas-v5/")):
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        multipart = headers.get(b"content-type", b"").startswith(b"multipart/form-data")
        # 24 MiB de respaldo + envoltorio JSON y margen de transporte.
        maximum = 60 * 1024 * 1024 if multipart else 26 * 1024 * 1024
        if scope["path"].startswith("/api/salas-v5/"):
            maximum = 11 * 1024 * 1024 if multipart else 64 * 1024
        elif scope["path"].startswith("/api/firmas-v5/"):
            maximum = 64 * 1024
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except (ValueError, TypeError):
            declared = 0
        if declared > maximum:
            return await JSONResponse({"detail":"La solicitud supera el límite de tamaño del despacho."}, status_code=413)(scope, receive, send)
        total = 0
        async def limited_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > maximum:
                    raise HTTPException(413, "La solicitud supera el límite de tamaño del despacho.")
            return message
        await self.app(scope, limited_receive, send)


app.add_middleware(LimiteCuerpoDespacho)

origenes = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
if origenes:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origenes,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
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
app.include_router(despacho_ai.router)
app.include_router(despacho_data.router)
app.include_router(despacho_export.router)
app.include_router(despacho_signatures.router)
app.include_router(despacho_signatures.public_router)
app.include_router(despacho_word.router)
app.include_router(despacho_agent.router)
app.include_router(despacho_connections.router)
app.include_router(despacho_connections.callback_router)
app.include_router(despacho_knowledge.router)
app.include_router(despacho_corpus_fuentes.router)
app.include_router(despacho_signing_v5.router)
app.include_router(despacho_signing_v5.public_router)
app.include_router(despacho_rooms_v5.router)
app.include_router(despacho_rooms_v5.public_router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
PRIVATE_DIR = Path(__file__).resolve().parent / "private"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
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


@app.api_route("/login", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/auth/callback", methods=["GET", "HEAD"], include_in_schema=False)
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
async def espacio_profesional(request: Request):
    if not await usuario_de_sesion(request):
        response = RedirectResponse("/login?next=/app", status_code=303, headers=SIN_CACHE)
        borrar_cookie_sesion(response, request)
        return response
    csp = csp_archivo_publico(PRIVATE_DIR / "despacho.html", ingreso=True).replace("frame-src 'none'", "frame-src 'self'")
    return FileResponse(PRIVATE_DIR / "despacho.html", headers={**SIN_CACHE, "Content-Security-Policy":csp})


@app.get("/generador", include_in_schema=False)
@app.get("/generador/", include_in_schema=False)
async def generador_profesional(request: Request):
    if not await usuario_de_sesion(request):
        response = RedirectResponse("/login?next=/generador", status_code=303, headers=SIN_CACHE)
        borrar_cookie_sesion(response, request)
        return response
    return FileResponse(PRIVATE_DIR / "generador.html", headers=SIN_CACHE)


@app.get("/app/assets/{filename}", include_in_schema=False)
async def despacho_asset(filename: str, request: Request):
    if filename not in {"despacho.js", "despacho.css", "generador-theme.css"}:
        raise HTTPException(404, "Recurso no encontrado.")
    if not await usuario_de_sesion(request):
        raise HTTPException(401, "Inicia sesión para acceder al despacho.", headers=SIN_CACHE)
    media = "application/javascript" if filename.endswith(".js") else "text/css"
    return FileResponse(PRIVATE_DIR / filename, media_type=media, headers=SIN_CACHE)


@app.get("/firmar", include_in_schema=False)
async def firma_por_enlace(request: Request):
    # Sólo una invitación de alta entropía permite leer un documento; esta página
    # contiene exclusivamente el formulario de aceptación y nunca datos del despacho.
    return FileResponse(PRIVATE_DIR / "firmar.html", headers={**SIN_CACHE,
        "Content-Security-Policy":csp_archivo_publico(PRIVATE_DIR / "firmar.html")})


@app.get("/word", include_in_schema=False)
async def word_panel(request: Request):
    csp = csp_archivo_publico(PRIVATE_DIR / "word.html", ingreso=True)
    csp = csp.replace("script-src 'self'", "script-src 'self' https://appsforoffice.microsoft.com")
    csp = csp.replace("frame-ancestors 'none'", "frame-ancestors 'self' https://*.officeapps.live.com https://*.office.com https://*.microsoft365.com https://*.cloud.microsoft")
    return FileResponse(PRIVATE_DIR / "word.html", headers={**SIN_CACHE,"Content-Security-Policy":csp})


@app.get("/firmar-v5", include_in_schema=False)
async def firma_verificada_page(request: Request):
    return FileResponse(PRIVATE_DIR / "firma-v5.html", headers={**SIN_CACHE,
        "Content-Security-Policy": csp_archivo_publico(PRIVATE_DIR / "firma-v5.html").replace("frame-src 'none'", "frame-src 'self' blob:")})


@app.get("/sala-cliente", include_in_schema=False)
async def sala_cliente_page(request: Request):
    return FileResponse(PRIVATE_DIR / "sala-cliente.html", headers={**SIN_CACHE,
        "Content-Security-Policy": csp_archivo_publico(PRIVATE_DIR / "sala-cliente.html").replace("frame-src 'none'", "frame-src 'self' blob:")})


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
