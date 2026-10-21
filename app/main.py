"""El Memorialista · aplicación FastAPI (v2.2)."""
import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import MutableHeaders

from app.config import get_settings
from app.routers import documents
from app.services.gemini_service import gemini_service

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("memorialista")


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
    description="Redacción de demandas, tutelas, memoriales y derechos de petición",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url=None if es_produccion else "/docs",
    redoc_url=None,
    openapi_url=None if es_produccion else "/openapi.json",
)


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
                cabeceras.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
                cabeceras.setdefault("X-Frame-Options", "SAMEORIGIN")
                cabeceras.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=(self)")
            await send(mensaje)

        await self.app(scope, receive, enviar)


app.add_middleware(CabecerasSeguridad)

origenes = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
if origenes:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origenes,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Codigo-Acceso"],
    )


@app.exception_handler(RequestValidationError)
async def solicitud_invalida(request: Request, exc: RequestValidationError):
    campos = sorted({str((error.get("loc") or ["?"])[-1]) for error in exc.errors()})
    return JSONResponse(
        status_code=422,
        content={"detail": "La solicitud es inválida o demasiado grande (revisa: " + ", ".join(campos) + ")."},
    )


app.include_router(documents.router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def root_index():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return {"app": "El Memorialista API", "status": "online"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
