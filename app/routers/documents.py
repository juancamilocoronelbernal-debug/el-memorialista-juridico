"""El Memorialista · rutas de la API (v2.2)."""
import asyncio
import contextlib
import json
from typing import AsyncIterator, Literal

import anyio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.gemini_service import Evento, gemini_service
from app.services.limites import limitador, verificar_acceso

router = APIRouter(prefix="/api", tags=["Documentos"])

SIN_CACHE = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
MARCA_INCOMPLETO = (
    "[COMPLETAR: el escrito se interrumpió en este punto. Usa «Ajustar con IA» → "
    "«Continúa donde quedó» o «Regenerar» antes de radicar]"
)


class RedactarRequest(BaseModel):
    prompt: str = Field(..., min_length=20, max_length=150_000)
    modo: Literal["nuevo", "regenerar", "ajuste", "continuar"] = "nuevo"
    instruccion: str = Field("", max_length=4_000)
    texto_previo: str = Field("", max_length=250_000)
    calidad: Literal["default", "complex"] = "default"
    protocolo: Literal["texto", "ndjson"] = "texto"


class AnalizarEstiloRequest(BaseModel):
    muestra: str = Field(..., min_length=20, max_length=20_000)


@router.get("/health")
async def health_check():
    return {"status": "online", "app": "El Memorialista", "version": get_settings().VERSION, **gemini_service.estado()}


@router.post("/redactar")
async def redactar_documento(req: RedactarRequest, request: Request):
    verificar_acceso(request)
    limitador.verificar(request, "redactar")
    eventos = gemini_service.generar(
        prompt=req.prompt,
        modo=req.modo,
        instruccion=req.instruccion,
        texto_previo=req.texto_previo,
        calidad=req.calidad,
    )
    if req.protocolo == "ndjson":
        return StreamingResponse(_como_ndjson(eventos), media_type="application/x-ndjson", headers=SIN_CACHE)
    return await _como_texto(eventos)


@router.post("/analizar-estilo")
async def analizar_estilo(req: AnalizarEstiloRequest, request: Request):
    verificar_acceso(request)
    limitador.verificar(request, "estilo")
    resultado = await gemini_service.analizar_estilo(req.muestra)
    if not resultado.get("ok"):
        raise HTTPException(status_code=502, detail=resultado.get("error", "No se pudo analizar la muestra."))
    return resultado


def _linea(evento: Evento) -> str:
    return json.dumps(evento.como_dict(), ensure_ascii=False) + "\n"


async def _como_ndjson(eventos: AsyncIterator[Evento]):
    """Protocolo nuevo: una línea JSON por evento y un 'ping' cada pocos segundos mientras el modelo piensa."""
    intervalo = max(1.0, float(get_settings().PING_NDJSON_S))
    cola: asyncio.Queue = asyncio.Queue()

    async def productor():
        try:
            async for evento in eventos:
                await cola.put(evento)
        except Exception:  # noqa: BLE001
            await cola.put(Evento("error", datos={"codigo": "interno", "mensaje": "Error inesperado en el servidor."}))
        finally:
            await cola.put(None)

    tarea = asyncio.create_task(productor())
    try:
        yield _linea(Evento("inicio"))
        while True:
            try:
                evento = await asyncio.wait_for(cola.get(), timeout=intervalo)
            except asyncio.TimeoutError:
                yield _linea(Evento("ping"))
                continue
            if evento is None:
                break
            yield _linea(evento)
    finally:
        # Si el abogado pulsa «Detener» o cierra la página, se corta también la llamada al proveedor de IA
        # (deja de gastar tokens). El escudo evita que la cancelación interrumpa ese cierre a medias.
        with anyio.move_on_after(10, shield=True):
            if not tarea.done():
                tarea.cancel()
            with contextlib.suppress(BaseException):
                await tarea


async def _como_texto(eventos: AsyncIterator[Evento]):
    """Protocolo anterior (texto plano), compatible con el frontend viejo.
    Espera el primer fragmento: si antes llega un error, responde con HTTP de error (no con texto)."""
    iterador = eventos.__aiter__()
    primero = None
    while primero is None:
        try:
            evento = await iterador.__anext__()
        except StopAsyncIteration:
            return JSONResponse(status_code=503, content={"detail": "El motor de IA no devolvió texto. Intenta de nuevo."})
        if evento.tipo == "delta":
            primero = evento
        elif evento.tipo == "error":
            await iterador.aclose()
            return JSONResponse(
                status_code=int(evento.datos.get("http") or 503),
                content={"detail": evento.datos.get("mensaje", "No se pudo redactar el escrito.")},
            )
        elif evento.tipo == "fin":
            await iterador.aclose()
            return JSONResponse(status_code=503, content={"detail": "El motor de IA no devolvió texto. Intenta de nuevo."})

    async def cuerpo():
        try:
            yield primero.texto
            async for evento in iterador:
                if evento.tipo == "delta":
                    yield evento.texto
                elif (evento.tipo == "fin" and evento.datos.get("truncado")) or evento.tipo == "error":
                    yield "\n\n" + MARCA_INCOMPLETO
        finally:
            with anyio.move_on_after(10, shield=True):
                await iterador.aclose()

    return StreamingResponse(cuerpo(), media_type="text/plain; charset=utf-8", headers=SIN_CACHE)
