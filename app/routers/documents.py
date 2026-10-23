"""El Memorialista · rutas de la API (v2.2.1)."""
import asyncio
import contextlib
import json
import re
from typing import Any, AsyncIterator, Literal, Optional

import anyio
from fastapi import APIRouter, HTTPException, Request, Response, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.gemini_service import Evento, gemini_service, ErrorIA
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
from app.services.revisor_requisitos import revisar_requisitos
from app.services.nit import calcular_dv_nit, validar_nit, formatear_nit
from app.services.radicado import obtener_catalogo_radicado, decodificar_radicado, validar_radicado, formatear_radicado
from app.services.numeros_letras import numero_a_letras
from app.services.plazos import (
    calcular_plazo,
    cargar_calendario_judicial_config,
    obtener_precargas_terminos,
    buscar_precarga,
)
from app.services.extractor_documentos import (
    validar_archivos_extraccion,
    extraer_datos_con_gemini,
)
from app.services.radicacion import (
    preparar_radicacion,
    PrepararRadicacionRequest,
    PrepararRadicacionResponse,
)
from app.services.comparador_versiones import (
    comparar_versiones,
    generar_docx_con_control_de_cambios,
    CompararVersionesRequest,
    CompararVersionesResponse,
    ExportarWordDiffRequest,
)

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


class RevisarRequest(BaseModel):
    escrito: str = Field(..., min_length=1, max_length=500_000)
    tipo: str = Field(..., min_length=1, max_length=100)


class PlazosRequest(BaseModel):
    tipo_termino: Optional[str] = None
    fecha_inicio: str = Field(..., description="Fecha de inicio o notificación en formato ISO (YYYY-MM-DD)")
    unidad: Optional[Literal["dias_habiles", "meses", "anios"]] = None
    cantidad: Optional[int] = Field(None, gt=0, description="Cantidad de días hábiles, meses o años")
    vacancia_colectiva: Optional[bool] = None
    notificacion_mensaje_datos: bool = Field(False, description="Aplica regla de mensaje de datos art. 8 Ley 2213/2022")
    fecha_acuse_recibo: Optional[str] = None
    hora_limite: str = "17:00"
    titulo_evento: Optional[str] = None


@router.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "online", "app": "El Memorialista", "version": get_settings().VERSION}


@router.get("/estado")
async def estado_servicio():
    """Diagnóstico de proveedores exclusivo del usuario autenticado, sin claves."""
    return {"status": "online", "app": "El Memorialista", "version": get_settings().VERSION, **gemini_service.estado()}


@router.get("/catalogo")
async def obtener_catalogo():
    tipos = listar_tipos(incluir_guia=False)
    areas = cargar_areas()
    grupo_red = cargar_grupo_redaccion()
    radicado_info = obtener_catalogo_radicado()
    plazos_info = cargar_calendario_judicial_config()
    return {
        "version": "2.2.1",
        "fecha_revision": "21 de octubre de 2026",
        "revisado_por": "Comité Jurídico El Memorialista",
        "areas": areas,
        "tipos": tipos,
        "grupo_redaccion": grupo_red,
        "radicado": radicado_info,
        "plazos": plazos_info,
    }


@router.post("/catalogo/auditar/{tipo_id}")
async def endpoint_auditar_tipo(tipo_id: str, request: Request):
    """Ejecuta la auditoría jurídica automatizada con IA sobre un tipo del catálogo."""
    from app.services.auditor_catalogo import auditar_tipo_por_id
    # Una sesión de usuario no autoriza reescribir el catálogo normativo global.
    # El resultado se devuelve para revisión; su publicación es administrativa.
    limitador.verificar(request, "redactar")
    try:
        dictamen = await auditar_tipo_por_id(tipo_id, actualizar_json=False)
        return dictamen
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tipo de escrito '{tipo_id}' no encontrado en el catálogo.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al auditar el tipo con IA: {e}")


@router.get("/radicado")
async def obtener_radicado_info():
    """Retorna la tabla y estructura oficial del radicado judicial de 23 dígitos."""
    return obtener_catalogo_radicado()


@router.get("/radicado/decodificar")
async def endpoint_decodificar_radicado(radicado: str):
    """Decodifica un radicado judicial de 23 dígitos."""
    return decodificar_radicado(radicado)


@router.get("/nit/validar")
async def endpoint_validar_nit(nit: str):
    """Calcula y valida el dígito de verificación DIAN de un NIT."""
    return validar_nit(nit)


@router.get("/numero-a-letras")
async def endpoint_numero_a_letras(valor: str):
    """Convierte deterministamente un valor numérico a letras en pesos colombianos ("M/CTE")."""
    return {"valor": valor, "letras": numero_a_letras(valor)}


@router.post("/plazos")
async def endpoint_calcular_plazos(req: PlazosRequest):
    """Calcula el vencimiento de términos procesales en Colombia (CGP, CPACA, D. 2591/91, Ley 2213/22, Ley 51/83)."""
    try:
        unidad = req.unidad
        cantidad = req.cantidad
        vacancia = req.vacancia_colectiva

        if req.tipo_termino:
            precarga = buscar_precarga(req.tipo_termino)
            if precarga:
                if unidad is None:
                    unidad = precarga.get("unidad", "dias_habiles")
                if cantidad is None:
                    cantidad = precarga.get("cantidad", 3)
                if vacancia is None:
                    vacancia = precarga.get("vacancia_colectiva", True)

        if unidad is None:
            unidad = "dias_habiles"
        if cantidad is None:
            cantidad = 3
        if vacancia is None:
            vacancia = True

        resultado = calcular_plazo(
            fecha_inicio=req.fecha_inicio,
            unidad=unidad,
            cantidad=cantidad,
            tipo_termino=req.tipo_termino,
            vacancia_colectiva=vacancia,
            notificacion_mensaje_datos=req.notificacion_mensaje_datos,
            fecha_acuse_recibo=req.fecha_acuse_recibo,
            hora_limite=req.hora_limite,
            titulo_evento=req.titulo_evento,
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en cómputo de plazos: {e}")


@router.get("/plazos/catalogo")
async def endpoint_catalogo_plazos():
    """Retorna las precargas de términos procesales y la configuración del calendario judicial."""
    return cargar_calendario_judicial_config()


@router.post("/plazos/ics")
async def endpoint_descargar_ics(req: PlazosRequest):
    """Descarga el evento de vencimiento procesal como archivo .ics (iCalendar RFC 5545)."""
    from fastapi.responses import Response

    resultado = calcular_plazo(
        fecha_inicio=req.fecha_inicio,
        unidad=req.unidad,
        cantidad=req.cantidad,
        tipo_termino=req.tipo_termino,
        vacancia_colectiva=req.vacancia_colectiva,
        notificacion_mensaje_datos=req.notificacion_mensaje_datos,
        fecha_acuse_recibo=req.fecha_acuse_recibo,
        hora_limite=req.hora_limite,
        titulo_evento=req.titulo_evento,
    )
    ics_text = resultado["evento_ics"]
    filename = f"vencimiento_{resultado['fecha_vencimiento']}.ics"
    return Response(
        content=ics_text,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.post("/radicacion/preparar", response_model=PrepararRadicacionResponse)
async def endpoint_preparar_radicacion(req: PrepararRadicacionRequest, request: Request):
    """
    Prepara el paquete de radicación judicial:
    - Nombres normalizados de archivos y paquete ZIP.
    - Genera el Poder Especial Judicial según art. 74 CGP y Ley 2213/2022 si el tipo lo amerita.
    - Extrae el capítulo de pruebas y formula el índice numerado según el protocolo del CSJ.
    - Analiza art. 6 Ley 2213/2022 (traslado simultáneo) y exención por medidas cautelares previas.
    - Construye los borradores y enlaces mailto: para radicación al despacho y traslado a la contraparte.
    """
    await verificar_acceso(request)
    limitador.verificar(request, "radicacion")
    return preparar_radicacion(req)


@router.post("/versiones/comparar", response_model=CompararVersionesResponse)
async def endpoint_comparar_versiones(req: CompararVersionesRequest, request: Request):
    """Compara dos versiones de un escrito judicial palabra por palabra y calcula estadísticas."""
    await verificar_acceso(request)
    limitador.verificar(request, "revisar")
    return comparar_versiones(req)


@router.post("/versiones/exportar-docx")
async def endpoint_exportar_docx_control_cambios(req: ExportarWordDiffRequest, request: Request):
    """Genera y descarga un documento Word (.docx) con control de cambios nativo (w:ins y w:del)."""
    await verificar_acceso(request)
    limitador.verificar(request, "revisar")
    docx_bytes = generar_docx_con_control_de_cambios(
        texto_base=req.texto_base,
        texto_comparado=req.texto_comparado,
        autor=req.autor or "El Memorialista",
        fecha=req.fecha,
        titulo=req.titulo or "Escrito con Control de Cambios",
        perfil=req.perfil,
    )
    safe_title = re.sub(r"[^\w\s-]", "", req.titulo or "Control_de_Cambios")[:50].strip().replace(" ", "_")
    filename = f"{safe_title}_Control_Cambios.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.post("/extraer")
async def endpoint_extraer_documentos(
    tipo: str = Form(..., description="Identificador del tipo de documento del catálogo"),
    archivos: list[UploadFile] = File(..., description="Archivos adjuntos del caso (máx 20 MB total)"),
    request: Request = None,
):
    """Extrae campos del caso desde documentos adjuntos (PDF, imágenes, audio) con Gemini 3.8 Flash.
    
    PRIVACIDAD: Los archivos se procesan 100% en memoria y se descartan tras el análisis.
    """
    if request:
        await verificar_acceso(request)

    tipo_info = obtener_tipo(tipo)
    if not tipo_info:
        raise HTTPException(
            status_code=400,
            detail=f"El tipo de documento '{tipo}' no existe en el catálogo.",
        )

    archivos_procesados, total_bytes = await validar_archivos_extraccion(archivos)

    try:
        resultado_extraccion = await extraer_datos_con_gemini(
            tipo_id=tipo,
            tipo_info=tipo_info,
            archivos=archivos_procesados,
        )
    except ErrorIA as e:
        raise HTTPException(status_code=e.http or 500, detail=e.mensaje)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la extracción de datos: {e}")

    if isinstance(resultado_extraccion, dict):
        propuestas = resultado_extraccion.get("propuestas", [])
        hechos_num = resultado_extraccion.get("hechos_numerados", [])
        decision_prov = resultado_extraccion.get("decision_providencia")
        fecha_notif = resultado_extraccion.get("fecha_notificacion_detectada")
    else:
        propuestas = resultado_extraccion
        hechos_num = []
        decision_prov = None
        fecha_notif = None

    return {
        "ok": True,
        "tipo": tipo,
        "total_archivos": len(archivos_procesados),
        "total_bytes": total_bytes,
        "propuestas": propuestas,
        "hechos_numerados": hechos_num,
        "decision_providencia": decision_prov,
        "fecha_notificacion_detectada": fecha_notif,
    }


@router.post("/redactar")
async def redactar_documento(req: RedactarRequest, request: Request):
    await verificar_acceso(request)
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
    await verificar_acceso(request)
    limitador.verificar(request, "estilo")
    resultado = await gemini_service.analizar_estilo(req.muestra)
    if not resultado.get("ok"):
        raise HTTPException(status_code=502, detail=resultado.get("error", "No se pudo analizar la muestra."))
    return resultado


@router.post("/verificar-citas")
async def endpoint_verificar_citas(req: VerificarCitasRequest, request: Request):
    await verificar_acceso(request)
    limitador.verificar(request, "citas")
    return await verificar_citas(req.texto)


@router.post("/revisar")
async def endpoint_revisar(req: RevisarRequest, request: Request):
    await verificar_acceso(request)
    limitador.verificar(request, "revisar")
    if not req.escrito.strip():
        raise HTTPException(status_code=400, detail="El escrito no puede estar vacío.")
    return await revisar_requisitos(req.escrito, req.tipo)


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
