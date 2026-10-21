"""El Memorialista · rutas de la API (v2.2.1)."""
import asyncio
import contextlib
import json
from typing import Any, AsyncIterator, Literal, Optional

import anyio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.gemini_service import Evento, gemini_service
from app.services.limites import limitador, verificar_acceso
from app.services.prompt import (
    cargar_areas,
    cargar_grupo_redaccion,
    construir_prompt,
    listar_tipos,
    obtener_tipo,
    validar_datos_tipo,
)
from app.services.verificador_citas import verificar_citas

router = APIRouter(prefix="/api", tags=["Documentos"])

SIN_CACHE = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
MARCA_INCOMPLETO = (
    "[COMPLETAR: el escrito se interrumpió en este punto. Usa «Ajustar con IA» → "
    "«Continúa donde quedó» o «Regenerar» antes de radicar]"
)


class PerfilAbogado(BaseModel):
    nombre: str = ""
    genero: Literal["f", "m", ""] = ""
    cedula: str = ""
    cedulaLugar: str = ""
    tp: str = ""
    correo: str = ""
    telefono: str = ""
    direccion: str = ""
    ciudad: str = ""


class PerfilEstilo(BaseModel):
    tratamiento: str = "auto"
    persona: str = "auto"
    numHechos: str = "auto"
    numPretensiones: str = "auto"
    tono: str = "sobrio"
    lenguaje: str = "auto"
    fecha: str = "arriba"
    esd: bool = True
    cierre: str = ""
    extension: str = "estandar"
    ficha: str = ""
    muestra: str = ""


class PerfilIA(BaseModel):
    calidad: Literal["default", "complex"] = "default"
    smmlv: int = 1750905


class PerfilPayload(BaseModel):
    abogado: Optional[PerfilAbogado] = Field(default_factory=PerfilAbogado)
    estilo: Optional[PerfilEstilo] = Field(default_factory=PerfilEstilo)
    ia: Optional[PerfilIA] = Field(default_factory=PerfilIA)


class RedactarRequest(BaseModel):
    # En desarrollo/test se permite prompt para pruebas unitarias de compatibilidad;
    # en producción se rechaza si viene definido.
    prompt: Optional[str] = Field(None, max_length=150_000)
    tipo: Optional[str] = None
    datos: Optional[dict[str, Any]] = None
    perfil: Optional[PerfilPayload] = None
    modo: Literal["nuevo", "regenerar", "ajuste", "continuar"] = "nuevo"
    instruccion: str = Field("", max_length=4_000)
    texto_previo: str = Field("", max_length=250_000)
    calidad: Optional[Literal["default", "complex"]] = None
    protocolo: Literal["texto", "ndjson"] = "texto"


class AnalizarEstiloRequest(BaseModel):
    muestra: str = Field(..., min_length=20, max_length=20_000)


class VerificarCitasRequest(BaseModel):
    texto: str = Field(..., min_length=1, max_length=500_000)


@router.get("/health")
async def health_check():
    return {"status": "online", "app": "El Memorialista", "version": get_settings().VERSION, **gemini_service.estado()}


@router.get("/catalogo")
async def obtener_catalogo():
    tipos = listar_tipos(incluir_guia=False)
    areas = cargar_areas()
    grupo_red = cargar_grupo_redaccion()
    return {
        "version": "2.2.1",
        "fecha_revision": "21 de octubre de 2026",
        "revisado_por": "Comité Jurídico El Memorialista",
        "areas": areas,
        "tipos": tipos,
        "grupo_redaccion": grupo_red,
    }


@router.post("/redactar")
async def redactar_documento(req: RedactarRequest, request: Request):
    verificar_acceso(request)
    limitador.verificar(request, "redactar")

    settings = get_settings()

    # 4) Con ENVIRONMENT=production, rechaza el campo "prompt" libre (400).
    if settings.ENVIRONMENT == "production":
        if req.prompt is not None:
            raise HTTPException(
                status_code=400,
                detail="En producción no se permite el campo 'prompt' libre. Debe enviar 'tipo', 'datos' y 'perfil'."
            )
        if not req.tipo or req.datos is None:
            raise HTTPException(
                status_code=400,
                detail="Faltan los campos requeridos 'tipo' y 'datos'."
            )

    if req.tipo:
        tipo_meta = obtener_tipo(req.tipo)
        if not tipo_meta:
            raise HTTPException(status_code=404, detail=f"Tipo de documento '{req.tipo}' no encontrado.")
        errores = validar_datos_tipo(tipo_meta, req.datos or {})
        if errores:
            raise HTTPException(status_code=422, detail="; ".join(errores))
        perfil_dict = req.perfil.model_dump() if req.perfil else {}
        prompt_final = construir_prompt(tipo_meta, req.datos or {}, perfil_dict)
    elif req.prompt:
        prompt_final = req.prompt
    else:
        raise HTTPException(status_code=400, detail="Debe proporcionar 'tipo' y 'datos' o un 'prompt'.")

    calidad = req.calidad
    if not calidad and req.perfil and req.perfil.ia:
        calidad = req.perfil.ia.calidad
    if not calidad:
        calidad = "default"

    eventos = gemini_service.generar(
        prompt=prompt_final,
        modo=req.modo,
        instruccion=req.instruccion,
        texto_previo=req.texto_previo,
        calidad=calidad,
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


@router.post("/verificar-citas")
async def endpoint_verificar_citas(req: VerificarCitasRequest, request: Request):
    verificar_acceso(request)
    limitador.verificar(request, "citas")
    return await verificar_citas(req.texto)


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
