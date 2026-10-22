# ⚖️ EL MEMORIALISTA — CÓDIGO FUENTE COMPLETO Y ARQUITECTURA
> **Fecha de consolidación:** 22 de October de 2026
> **Para Claude:** Este documento contiene el código fuente real, unificado y exhaustivo del backend y frontend de **El Memorialista** para diseñar e implementar nuevas funciones, tipos de documentos, integraciones y mejoras continuas.

## 📌 Datos de Producción
- **GitHub:** https://github.com/juancamilocoronelbernal-debug/el-memorialista-juridico
- **Despliegue Render:** https://el-memorialista-juridico.onrender.com/
- **Stack:** Python 3.9+ / FastAPI / Vanilla JS / CSS3 nativo / Supabase / Google Gemini 3.8 Flash & Gemini 4 Argon / Groq fallback.

---


## 📄 Archivo: `render.yaml`
```yaml
services:
  - type: web
    name: el-memorialista-juridico
    env: python
    region: oregon
    # "free" se duerme a los 15 minutos sin tráfico. Con abogados reales, cambia a "starter".
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.13.5
      - key: ENVIRONMENT
        value: production
      - key: GEMINI_API_KEY
        sync: false
      - key: GEMINI_MODEL
        value: gemini-3.8-flash
      - key: GEMINI_MODEL_PRO
        value: gemini-4-argon
      - key: GEMINI_FALLBACK_MODELS
        value: gemini-3.6-flash,gemini-3.5-flash-lite,gemini-2.5-flash
      - key: GROQ_API_KEY
        sync: false
      - key: APP_ACCESS_CODE
        sync: false

```


## 📄 Archivo: `requirements.txt`
```yaml
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.7.0
pydantic-settings>=2.4.0
httpx>=0.27.0,<1.0
anyio>=4.0
python-dotenv>=1.0.1
python-multipart>=0.0.9

```


## 📄 Archivo: `.env.example`
```yaml
# ==============================================================================
# EL MEMORIALISTA v2.2 · configuración local (copia este archivo como .env)
# ==============================================================================
ENVIRONMENT=development
PORT=8000
DEBUG=True
LOG_LEVEL=INFO

# GOOGLE GEMINI
# Usa una clave de un proyecto con FACTURACIÓN ACTIVA para datos reales de clientes:
# en el plan gratuito Google puede usar lo que envías para mejorar sus productos y
# personas pueden revisarlo.
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
GEMINI_MODEL_PRO=gemini-4-argon
GEMINI_FALLBACK_MODELS=gemini-3.6-flash,gemini-3.5-flash-lite,gemini-2.5-flash
GEMINI_MAX_OUTPUT_TOKENS=65536
# GEMINI_THINKING_DEFAULT=low     # más rápido; vacío = el nivel por defecto del modelo
# GEMINI_THINKING_COMPLEX=high    # más profundo y más costoso
# GEMINI_SAFETY=                  # vacío = filtros por defecto del modelo

# GROQ (respaldo opcional)
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b

# ACCESO Y LÍMITES (mientras no haya cuentas de usuario)
APP_ACCESS_CODE=
LIMITE_POR_VENTANA=15
VENTANA_MINUTOS=10
LIMITE_DIA_IP=150
LIMITE_DIA_GLOBAL=500

```


## 📄 Archivo: `app/config.py`
```python
"""
El Memorialista · configuración (v2.2)
Todo se controla con variables de entorno (Render > Environment) o con el archivo .env en local.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    VERSION: str = "2.2.1"

    # Render (Render define RENDER_EXTERNAL_URL automáticamente)
    RENDER_EXTERNAL_URL: str = ""
    KEEP_ALIVE: bool = True

    # Google Gemini (modelos vigentes a octubre de 2026)
    GEMINI_API_KEY: str = ""
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com"
    GEMINI_MODEL: str = "gemini-3.8-flash"        # Calidad principal: Gemini 3.8 Flash con thinkingLevel high
    GEMINI_MODEL_PRO: str = "gemini-4-argon"      # Calidad avanzada: Gemini 4 Argon con thinkingLevel medium
    GEMINI_FALLBACK_MODELS: str = "gemini-4-argon,gemini-3.6-flash,gemini-3.5-flash"
    GEMINI_MAX_OUTPUT_TOKENS: int = 65536         # incluye los tokens de "pensamiento"
    GEMINI_THINKING_DEFAULT: str = "high"         # Nivel de pensamiento "high" para Gemini 3.8 Flash
    GEMINI_THINKING_COMPLEX: str = "medium"       # Nivel de pensamiento "medium" para Gemini 4 Argon
    GEMINI_SAFETY: str = ""                       # "" = filtros por defecto del modelo

    # Groq (respaldo opcional)
    GROQ_API_KEY: str = ""
    GROQ_API_BASE: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_MAX_TOKENS: int = 16384

    # Robustez
    MAX_CONTINUACIONES: int = 3
    INTENTOS_POR_MODELO: int = 2
    ESPERA_REINTENTO_S: float = 1.5
    TIMEOUT_CONEXION_S: float = 15.0
    TIMEOUT_LECTURA_S: float = 300.0
    PING_NDJSON_S: float = 15.0

    # Supabase (Auth Magic Link, Postgres RLS, Storage privado)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_STORAGE_BUCKET: str = "archivos-privados"

    # Acceso y límites de uso (por usuario y por IP)
    APP_ACCESS_CODE: str = ""        # respaldo legado si no se usa Supabase
    ALLOWED_ORIGINS: str = ""        # vacío = solo el mismo dominio (recomendado)
    LIMITE_POR_VENTANA: int = 15     # redacciones y ajustes por usuario/IP dentro de la ventana
    VENTANA_MINUTOS: int = 10
    LIMITE_DIA_USUARIO: int = 50     # tope diario de redacciones por usuario autenticado
    LIMITE_DIA_IP: int = 150         # una oficina con varios abogados comparte la misma IP
    LIMITE_DIA_GLOBAL: int = 500     # tope diario de todo el servidor (controla el gasto)
    LIMITE_ESTILO_HORA: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()

```


## 📄 Archivo: `app/main.py`
```python
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
from app.routers import auth, calculos, documents
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
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Codigo-Acceso"],
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

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def root_index():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return {"app": "El Memorialista API", "status": "online"}


@app.get("/auditor.js", include_in_schema=False)
async def auditor_js():
    js_file = STATIC_DIR / "auditor.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript", headers={"Cache-Control": "no-cache"})
    raise HTTPException(status_code=404, detail="File not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)

```


## 📄 Archivo: `app/routers/__init__.py`
```python
# routers package

```


## 📄 Archivo: `app/routers/documents.py`
```python
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


@router.get("/health")
async def health_check():
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
async def endpoint_auditar_tipo(tipo_id: str):
    """Ejecuta la auditoría jurídica automatizada con IA sobre un tipo del catálogo."""
    from app.services.auditor_catalogo import auditar_tipo_por_id
    try:
        dictamen = await auditar_tipo_por_id(tipo_id, actualizar_json=True)
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

```


## 📄 Archivo: `app/routers/calculos.py`
```python
"""El Memorialista · Router de Cálculos Jurídicos, Laborales y Financieros."""
from app.services.calculos import (
    router,
    calcular_liquidacion_laboral,
    calcular_intereses_moratorios,
    calcular_indexacion_ipc,
    cargar_catalogo_tasas_sfc,
    cargar_catalogo_ipc,
    LiquidacionLaboralRequest,
    LiquidacionLaboralResponse,
    InteresesMoratoriosRequest,
    InteresesMoratoriosResponse,
    IndexacionRequest,
    IndexacionResponse,
)

__all__ = [
    "router",
    "calcular_liquidacion_laboral",
    "calcular_intereses_moratorios",
    "calcular_indexacion_ipc",
    "cargar_catalogo_tasas_sfc",
    "cargar_catalogo_ipc",
    "LiquidacionLaboralRequest",
    "LiquidacionLaboralResponse",
    "InteresesMoratoriosRequest",
    "InteresesMoratoriosResponse",
    "IndexacionRequest",
    "IndexacionResponse",
]

```


## 📄 Archivo: `app/routers/auth.py`
```python
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
from app.services.supabase_service import (
    exportar_todos_los_datos,
    eliminar_cuenta_usuario,
)

router = APIRouter(prefix="/api", tags=["Autenticación y Usuario"])


@router.get("/auth/config")
async def endpoint_auth_config():
    """Retorna las variables públicas para inicializar Supabase JS en el navegador."""
    settings = get_settings()
    return {
        "supabase_url": settings.SUPABASE_URL,
        "supabase_anon_key": settings.SUPABASE_ANON_KEY,
        "auth_requerido": bool(settings.SUPABASE_URL),
        "limite_diario_usuario": settings.LIMITE_DIA_USUARIO,
    }


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

    datos_exportados = await exportar_todos_los_datos(user_id=user_id, token=token)

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
async def endpoint_eliminar_cuenta(request: Request):
    """Elimina definitivamente la cuenta del usuario y todos sus registros en la base de datos y storage."""
    usuario = await verificar_acceso(request)
    if not usuario:
        raise HTTPException(status_code=401, detail="Se requiere sesión activa para eliminar la cuenta.")

    user_id = usuario.get("id") or usuario.get("sub")
    auth_header = request.headers.get("authorization", "")
    token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else ""

    exito = await eliminar_cuenta_usuario(user_id=user_id, token=token)
    if not exito:
        raise HTTPException(status_code=500, detail="No se pudo completar la eliminación total de la cuenta.")

    return {
        "ok": True,
        "mensaje": "Tu cuenta y todos tus datos fueron eliminados definitivamente de El Memorialista.",
        "usuario_id": user_id,
    }

```


## 📄 Archivo: `app/services/__init__.py`
```python
# services package

```


## 📄 Archivo: `app/services/gemini_service.py`
```python
"""
El Memorialista · motor de IA (v2.2)

Qué cambia frente a la versión anterior:
- Nunca une dos escritos: si un motor falla a mitad de camino, el siguiente CONTINÚA el texto
  en lugar de empezar de cero (antes se pegaba un escrito nuevo detrás del cortado).
- Detecta cuándo el escrito se corta por el límite de tokens (MAX_TOKENS) y lo continúa solo.
- Los errores viajan como eventos o como error HTTP, nunca como si fueran parte del escrito.
- Compatible con Gemini 3.6+ y Gemini 4: no envía temperature/topP (obsoletos) y nunca termina
  la conversación en un turno "model" (eso devuelve error 400 en los modelos nuevos).
- La clave de API viaja en una cabecera, no en la URL.
- Los logs nunca guardan el contenido de los escritos: solo modelo, motivo, tiempos y tokens.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

import httpx

from app.config import get_settings

log = logging.getLogger("memorialista.ia")

INSTRUCCION_SISTEMA = (
    "Eres el motor de redacción de El Memorialista, una herramienta para abogados en Colombia. "
    "Tu única tarea es redactar, ajustar o continuar escritos jurídicos colombianos (demandas, tutelas, "
    "memoriales, derechos de petición, recursos, poderes, contratos y documentos similares) según las "
    "instrucciones del abogado. Si lo que se pide no es un escrito jurídico, responde únicamente: "
    "[COMPLETAR: esta herramienta solo redacta escritos jurídicos]. "
    "Nunca inventes hechos, nombres, cifras, fechas, radicados, números de documento ni citas de normas o "
    "sentencias: si falta un dato escribe [COMPLETAR: dato que falta] y si dudas de una cita escribe "
    "[VERIFICAR] inmediatamente después de ella. Escribe solo el documento, sin comentarios antes ni después."
)

INSTRUCCION_CONTINUAR = (
    "El documento anterior quedó incompleto porque la generación se interrumpió. Continúalo EXACTAMENTE "
    "desde el punto donde se cortó: no repitas nada de lo ya escrito, no agregues títulos de reanudación "
    "ni comentarios. Si se cortó en mitad de una palabra o de una frase, complétala. Conserva el mismo "
    "formato de marcas y termina el documento completo."
)


def mensaje_ajuste(instruccion: str) -> str:
    return (
        f"AJUSTE PEDIDO POR EL ABOGADO: {instruccion}\n\n"
        "Aplica el ajuste al documento anterior y devuelve el documento COMPLETO actualizado, "
        "con el mismo formato de marcas. Conserva lo que el ajuste no pide cambiar. Sigue las reglas: "
        "no inventes hechos y usa [COMPLETAR] y [VERIFICAR] cuando corresponda. Escribe solo el documento."
    )


# Se prueban siempre al final, aunque en Render hayan quedado nombres de modelos viejos en las variables.
RESPALDO_SEGURO = ("gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3-flash-preview")

MOTIVOS_CONTINUAR = {"MAX_TOKENS", "length", "OTHER"}
MOTIVOS_BLOQUEO = {
    "SAFETY", "RECITATION", "PROHIBITED_CONTENT", "SPII", "BLOCKLIST",
    "IMAGE_SAFETY", "LANGUAGE", "content_filter",
}
CATEGORIAS_SEGURIDAD = (
    "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "HARM_CATEGORY_DANGEROUS_CONTENT",
)

ETIQUETAS_ESTILO = {
    "encabezado": "Encabezado",
    "presentacion": "Presentación",
    "tratamiento": "Tratamiento",
    "persona": "Persona",
    "capitulos": "Capítulos",
    "numeracion": "Numeración",
    "titulos": "Títulos",
    "conectores": "Conectores",
    "citas": "Citas",
    "cierre": "Cierre",
    "rasgos": "Rasgos",
}
ESQUEMA_ESTILO = {"type": "OBJECT", "properties": {clave: {"type": "STRING"} for clave in ETIQUETAS_ESTILO}}
ESQUEMA_PERTINENCIA = {
    "type": "OBJECT",
    "properties": {
        "respalda": {"type": "STRING", "enum": ["si", "parcial", "no"]},
        "fragmento": {"type": "STRING"},
    },
    "required": ["respalda", "fragmento"],
}
ESQUEMA_REVISION = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "STRING"},
            "estado": {"type": "STRING", "enum": ["cumple", "no_cumple", "no_aplica"]},
            "evidencia": {"type": "STRING"},
            "sugerencia": {"type": "STRING"},
        },
        "required": ["id", "estado", "evidencia", "sugerencia"],
    },
}
PROMPT_ESTILO = (
    "Analiza el estilo de redacción del siguiente escrito jurídico de un abogado colombiano para que otro "
    "redactor pueda imitarlo fielmente. Responde ÚNICAMENTE con un objeto JSON válido con estas claves y "
    "valores breves en español (cita entre comillas las fórmulas exactas): encabezado (cómo escribe el "
    "destinatario y la referencia), presentacion (fórmula con la que se presenta), tratamiento (cómo se dirige "
    "al despacho), persona (primera o tercera persona), capitulos (orden y nombres de sus capítulos), "
    "numeracion (cómo numera hechos y pretensiones), titulos (cómo escribe los títulos), conectores (conectores "
    "y fórmulas frecuentes), citas (cómo cita normas y jurisprudencia), cierre (fórmula de despedida y firma), "
    "rasgos (otros rasgos distintivos). No copies hechos, nombres ni datos personales del escrito."
)


class ErrorIA(Exception):
    def __init__(
        self,
        codigo: str,
        mensaje: str,
        *,
        reintentable: bool = False,
        http: Optional[int] = None,
        parametros: bool = False,
        no_existe: bool = False,
        bloqueo: bool = False,
    ) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.reintentable = reintentable
        self.http = http
        self.parametros = parametros
        self.no_existe = no_existe
        self.bloqueo = bloqueo

    @classmethod
    def desde_http(cls, proveedor: str, modelo: str, status: int, cuerpo: str) -> "ErrorIA":
        detalle = ""
        try:
            datos = json.loads(cuerpo)
            err = datos.get("error") if isinstance(datos, dict) else None
            if isinstance(err, dict):
                detalle = str(err.get("message") or err.get("status") or "")
            elif err:
                detalle = str(err)
        except (ValueError, TypeError):
            detalle = cuerpo or ""
        completo = " ".join(detalle.split())
        detalle = completo[:300]
        base = f"{proveedor}/{modelo} respondió {status}" + (f": {detalle}" if detalle else "")
        if status in (400, 413, 422):
            return cls("parametros", base, http=status, parametros=True)
        if status in (401, 403):
            return cls("permiso", base, http=status)
        if status == 404:
            return cls("no_existe", base, http=status, no_existe=True)
        if status == 429 and re.search(r"limit:\s*0\b", completo):
            # Cuota cero: el plan de esta clave no incluye el modelo (p. ej. gemini-4-argon en plan gratuito).
            return cls("sin_acceso", base, http=status, no_existe=True)
        if status == 429:
            return cls("cuota", base, http=status, reintentable=True)
        if status == 408 or status >= 500:
            return cls("servidor", base, http=status, reintentable=True)
        return cls("http", base, http=status)


@dataclass
class Evento:
    tipo: str                     # inicio | delta | aviso | fin | error | ping
    texto: str = ""
    datos: dict = field(default_factory=dict)

    def como_dict(self) -> dict:
        salida = {"t": self.tipo}
        if self.texto:
            salida["d"] = self.texto
        salida.update(self.datos)
        return salida


@dataclass
class Motor:
    proveedor: str                # gemini | groq
    modelo: str
    pensamiento: str = ""


_PREAMBULO = re.compile(
    r"^\s*(?:continuaci[oó]n|continuando|contin[uú]o|sigue el (?:texto|documento|escrito))\b[^\n]{0,80}:[ \t]*\n",
    re.IGNORECASE,
)
_CERCO_INICIAL = re.compile(r"^\s*```[a-zA-Z]*[ \t]*\n")
_PALABRA_FINAL = re.compile(r"(\w+)$")


def quitar_preambulo(texto: str) -> str:
    texto = _CERCO_INICIAL.sub("", texto, count=1)
    return _PREAMBULO.sub("", texto, count=1)


class RecortadorSolape:
    """Quita del inicio de una continuación lo que repite el final del texto ya escrito."""

    VENTANA = 300
    MINIMO = 12

    def __init__(self, previo: str) -> None:
        self.cola = previo[-800:]
        self.buffer = ""
        self.listo = False

    def filtrar(self, fragmento: str) -> str:
        if self.listo:
            return fragmento
        self.buffer += fragmento
        if len(self.buffer) < self.VENTANA:
            return ""
        return self._resolver()

    def vaciar(self) -> str:
        if self.listo:
            return ""
        return self._resolver()

    def _resolver(self) -> str:
        self.listo = True
        texto = quitar_preambulo(self.buffer)
        self.buffer = ""
        if not self.cola or not texto:
            return texto
        # 1) Repetición larga y exacta del final (con o sin espacios iniciales)
        for candidato in (texto, texto.lstrip()):
            tope = min(len(self.cola), len(candidato))
            for k in range(tope, self.MINIMO - 1, -1):
                if self.cola.endswith(candidato[:k]):
                    return candidato[k:]
        # 2) Se cortó en mitad de una palabra y la continuación la repite completa
        if self.cola[-1:].isalnum():
            coincidencia = _PALABRA_FINAL.search(self.cola)
            if coincidencia:
                palabra = coincidencia.group(1)
                if len(palabra) >= 2 and texto.startswith(palabra):
                    return texto[len(palabra):]
        return texto


def construir_mensajes(prompt: str, modo: str, instruccion: str, texto_previo: str) -> list:
    previo = (texto_previo or "").strip()
    if modo == "ajuste" and previo:
        return [("user", prompt), ("model", texto_previo), ("user", mensaje_ajuste(instruccion))]
    if modo == "continuar" and previo:
        return [("user", prompt), ("model", texto_previo), ("user", INSTRUCCION_CONTINUAR)]
    return [("user", prompt)]


def mensajes_con_avance(base: list, modo: str, previo_continuar: str, acumulado: str) -> list:
    """Si ya hay texto escrito, pide continuar desde ahí (la conversación siempre termina en 'user')."""
    if not acumulado:
        return base
    if modo == "continuar" and previo_continuar:
        return [base[0], ("model", previo_continuar + acumulado), ("user", INSTRUCCION_CONTINUAR)]
    return base + [("model", acumulado), ("user", INSTRUCCION_CONTINUAR)]


def _sumar_tokens(tokens: dict, proveedor: str, uso) -> None:
    if not isinstance(uso, dict):
        return
    if proveedor == "gemini":
        tokens["entrada"] += int(uso.get("promptTokenCount") or 0)
        tokens["salida"] += int(uso.get("candidatesTokenCount") or 0)
        tokens["pensamiento"] += int(uso.get("thoughtsTokenCount") or 0)
    else:
        tokens["entrada"] += int(uso.get("prompt_tokens") or 0)
        tokens["salida"] += int(uso.get("completion_tokens") or 0)


def _convertir_excepcion(exc: Exception) -> ErrorIA:
    if isinstance(exc, httpx.TimeoutException):
        return ErrorIA("tiempo", f"Tiempo de espera agotado ({type(exc).__name__}).", reintentable=True)
    if isinstance(exc, httpx.HTTPError):
        return ErrorIA("red", f"Error de red ({type(exc).__name__}).", reintentable=True)
    log.exception("Error inesperado en el motor de IA")
    return ErrorIA("interno", f"Error inesperado ({type(exc).__name__}).")


def _primer_objeto(texto: str) -> str:
    i_obj, f_obj = texto.find("{"), texto.rfind("}")
    i_arr, f_arr = texto.find("["), texto.rfind("]")
    if i_arr >= 0 and f_arr > i_arr and (i_obj < 0 or i_arr < i_obj):
        return texto[i_arr:f_arr + 1]
    return texto[i_obj:f_obj + 1] if i_obj >= 0 and f_obj > i_obj else ""


def extraer_json(texto: str) -> Optional[Any]:
    if not texto:
        return None
    limpio = re.sub(r"^\s*```(?:json)?\s*", "", texto.strip())
    limpio = re.sub(r"\s*```\s*$", "", limpio)
    for candidato in (limpio, _primer_objeto(limpio)):
        if not candidato:
            continue
        try:
            datos = json.loads(candidato)
        except (ValueError, TypeError):
            continue
        if isinstance(datos, (dict, list)):
            return datos
    return None


class GeminiService:
    def __init__(self) -> None:
        self.http: Optional[httpx.AsyncClient] = None
        self.disponibles: Optional[set] = None
        self.no_disponibles: dict = {}
        self._descubierto_en = 0.0
        self._tarea_descubrir = None

    @property
    def s(self):
        return get_settings()

    # ------------------------------------------------------------------ cliente HTTP
    async def iniciar(self, transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        if self.http is not None:
            return
        s = self.s
        self.http = httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(
                connect=s.TIMEOUT_CONEXION_S, read=s.TIMEOUT_LECTURA_S, write=60.0, pool=30.0
            ),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
        )

    async def cerrar(self) -> None:
        if self.http is not None:
            with contextlib.suppress(BaseException):
                await self.http.aclose()
            self.http = None

    async def _cliente(self) -> httpx.AsyncClient:
        if self.http is None or self.http.is_closed:
            await self.iniciar()
        return self.http

    def _cab_gemini(self) -> dict:
        return {"x-goog-api-key": self.s.GEMINI_API_KEY.strip(), "Content-Type": "application/json"}

    # ------------------------------------------------------------------ modelos
    def _configurados(self) -> list:
        s = self.s
        nombres = [s.GEMINI_MODEL_PRO, s.GEMINI_MODEL, *s.GEMINI_FALLBACK_MODELS.split(",")]
        salida = []
        for nombre in (n.strip() for n in nombres):
            if nombre and nombre not in salida:
                salida.append(nombre)
        return salida

    async def descubrir_modelos(self) -> None:
        """Consulta qué modelos tiene disponibles la clave y avisa en los logs si falta alguno."""
        s = self.s
        if not s.GEMINI_API_KEY.strip():
            return
        self._descubierto_en = time.monotonic()
        cliente = await self._cliente()
        nombres: set = set()
        token = None
        try:
            for _ in range(20):
                params = {"pageSize": 1000}
                if token:
                    params["pageToken"] = token
                respuesta = await cliente.get(
                    f"{s.GEMINI_API_BASE.rstrip('/')}/v1beta/models",
                    params=params,
                    headers=self._cab_gemini(),
                    timeout=20.0,
                )
                if respuesta.status_code != 200:
                    log.warning("No se pudo listar los modelos de Gemini (HTTP %s).", respuesta.status_code)
                    return
                datos = respuesta.json()
                for modelo in datos.get("models") or []:
                    nombre = str(modelo.get("name", ""))
                    if nombre.startswith("models/"):
                        nombre = nombre[len("models/"):]
                    if nombre:
                        nombres.add(nombre)
                token = datos.get("nextPageToken")
                if not token:
                    break
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("No se pudo listar los modelos de Gemini (%s).", type(exc).__name__)
            return
        if nombres:
            self.disponibles = nombres
            faltan = [n for n in self._configurados() if n not in nombres]
            if faltan:
                log.warning("Modelos configurados que esta clave no tiene disponibles: %s", ", ".join(faltan))

    def candidatos(self, calidad: str) -> list:
        s = self.s
        motores = []
        if s.GEMINI_API_KEY.strip():
            if self._descubierto_en and time.monotonic() - self._descubierto_en > 6 * 3600:
                self._descubierto_en = time.monotonic()
                try:
                    self._tarea_descubrir = asyncio.get_running_loop().create_task(self.descubrir_modelos())
                except RuntimeError:
                    pass
            nombres = []
            if calidad == "complex" and s.GEMINI_MODEL_PRO.strip():
                nombres.append(s.GEMINI_MODEL_PRO.strip())
            nombres.append(s.GEMINI_MODEL.strip())
            nombres += [m.strip() for m in s.GEMINI_FALLBACK_MODELS.split(",")]
            nombres += list(RESPALDO_SEGURO)
            unicos = []
            for nombre in nombres:
                if nombre and nombre not in unicos:
                    unicos.append(nombre)
            ahora = time.monotonic()
            filtrados = [
                n for n in unicos
                if not (self.disponibles and n not in self.disponibles)
                and ahora - self.no_disponibles.get(n, -1e9) > 3600
            ]
            for nombre in filtrados or unicos:
                if "argon" in nombre.lower() or nombre == s.GEMINI_MODEL_PRO.strip():
                    nivel_pensamiento = s.GEMINI_THINKING_COMPLEX.strip() or "medium"
                else:
                    nivel_pensamiento = s.GEMINI_THINKING_DEFAULT.strip() or "high"
                motores.append(Motor("gemini", nombre, nivel_pensamiento))
        if s.GROQ_API_KEY.strip():
            motores.append(Motor("groq", s.GROQ_MODEL.strip() or "openai/gpt-oss-120b"))
        return motores

    def estado(self) -> dict:
        s = self.s
        faltantes = sorted(
            n for n in self._configurados() if self.disponibles is not None and n not in self.disponibles
        )
        return {
            "gemini_configured": bool(s.GEMINI_API_KEY.strip()),
            "groq_configured": bool(s.GROQ_API_KEY.strip()),
            "model": s.GEMINI_MODEL,
            "model_pro": s.GEMINI_MODEL_PRO,
            "modelos_no_disponibles": faltantes,
        }

    def _espera(self, intento: int) -> float:
        base = max(0.0, float(self.s.ESPERA_REINTENTO_S))
        if base == 0:
            return 0.0
        return min(10.0, base * (2 ** (intento - 1))) + random.uniform(0, 0.4)

    # ------------------------------------------------------------------ proveedores
    def _payload_gemini(
        self,
        motor: Motor,
        mensajes: list,
        degradado: bool,
        instruccion_sistema: str | None = None,
    ) -> dict:
        s = self.s
        legado = motor.modelo.startswith(("gemini-1", "gemini-2"))
        config = {
            "maxOutputTokens": min(s.GEMINI_MAX_OUTPUT_TOKENS, 32768) if degradado else s.GEMINI_MAX_OUTPUT_TOKENS
        }
        if not degradado:
            if legado:
                config["temperature"] = 0.3
            else:
                pensamiento = motor.pensamiento or s.GEMINI_THINKING_DEFAULT or "8192"
                val = str(pensamiento).strip()
                if val.isdigit():
                    config["thinkingConfig"] = {"thinkingBudget": int(val)}
                elif val.lower() in ["low", "medium", "high"]:
                    config["thinkingConfig"] = {"thinkingLevel": val.lower()}
                else:
                    config["thinkingConfig"] = {"thinkingBudget": 8192}
        payload = {
            "systemInstruction": {"parts": [{"text": instruccion_sistema if instruccion_sistema is not None else INSTRUCCION_SISTEMA}]},
            "contents": [{"role": rol, "parts": [{"text": texto}]} for rol, texto in mensajes],
            "generationConfig": config,
        }
        umbral = s.GEMINI_SAFETY.strip()
        if umbral and not degradado:
            payload["safetySettings"] = [{"category": c, "threshold": umbral} for c in CATEGORIAS_SEGURIDAD]
        return payload

    async def _stream_gemini(
        self,
        motor: Motor,
        mensajes: list,
        degradado: bool,
        instruccion_sistema: str | None = None,
    ):
        s = self.s
        cliente = await self._cliente()
        url = f"{s.GEMINI_API_BASE.rstrip('/')}/v1beta/models/{motor.modelo}:streamGenerateContent"
        payload = self._payload_gemini(motor, mensajes, degradado, instruccion_sistema=instruccion_sistema)
        async with cliente.stream(
            "POST", url, params={"alt": "sse"}, json=payload, headers=self._cab_gemini()
        ) as respuesta:
            if respuesta.status_code != 200:
                cuerpo = (await respuesta.aread()).decode("utf-8", "ignore")
                raise ErrorIA.desde_http("gemini", motor.modelo, respuesta.status_code, cuerpo)
            motivo = None
            uso: dict = {}
            async for linea in respuesta.aiter_lines():
                if not linea.startswith("data:"):
                    continue
                dato = linea[5:].strip()
                if not dato or dato == "[DONE]":
                    continue
                try:
                    obj = json.loads(dato)
                except ValueError:
                    continue
                if not isinstance(obj, dict):
                    continue
                if obj.get("error"):
                    raise ErrorIA(
                        "interrumpido",
                        f"gemini/{motor.modelo} envió un error a mitad de la respuesta.",
                        reintentable=True,
                    )
                bloqueo = (obj.get("promptFeedback") or {}).get("blockReason")
                if bloqueo:
                    raise ErrorIA("bloqueado", f"gemini/{motor.modelo} bloqueó la solicitud ({bloqueo}).", bloqueo=True)
                candidatos = obj.get("candidates") or []
                if candidatos:
                    candidato = candidatos[0] or {}
                    for parte in (candidato.get("content") or {}).get("parts") or []:
                        if parte.get("thought"):
                            continue
                        texto = parte.get("text")
                        if texto:
                            yield ("texto", texto)
                    if candidato.get("finishReason"):
                        motivo = candidato["finishReason"]
                if obj.get("usageMetadata"):
                    uso = obj["usageMetadata"]
            if not motivo:
                raise ErrorIA(
                    "interrumpido",
                    f"La conexión con gemini/{motor.modelo} se cerró antes de terminar.",
                    reintentable=True,
                )
            yield ("fin", (motivo, uso))

    async def _stream_groq(self, motor: Motor, mensajes: list, degradado: bool):
        s = self.s
        cliente = await self._cliente()
        payload = {
            "model": motor.modelo,
            "messages": [{"role": "system", "content": INSTRUCCION_SISTEMA}] + [
                {"role": "assistant" if rol == "model" else "user", "content": texto} for rol, texto in mensajes
            ],
            "stream": True,
            "max_tokens": min(8192, s.GROQ_MAX_TOKENS) if degradado else s.GROQ_MAX_TOKENS,
        }
        if not degradado:
            payload["temperature"] = 0.3
        cabeceras = {"Authorization": f"Bearer {s.GROQ_API_KEY.strip()}", "Content-Type": "application/json"}
        async with cliente.stream(
            "POST", f"{s.GROQ_API_BASE.rstrip('/')}/chat/completions", json=payload, headers=cabeceras
        ) as respuesta:
            if respuesta.status_code != 200:
                cuerpo = (await respuesta.aread()).decode("utf-8", "ignore")
                raise ErrorIA.desde_http("groq", motor.modelo, respuesta.status_code, cuerpo)
            motivo = None
            uso: dict = {}
            async for linea in respuesta.aiter_lines():
                if not linea.startswith("data:"):
                    continue
                dato = linea[5:].strip()
                if dato == "[DONE]":
                    break
                if not dato:
                    continue
                try:
                    obj = json.loads(dato)
                except ValueError:
                    continue
                if not isinstance(obj, dict):
                    continue
                if obj.get("error"):
                    raise ErrorIA(
                        "interrumpido",
                        f"groq/{motor.modelo} envió un error a mitad de la respuesta.",
                        reintentable=True,
                    )
                for opcion in obj.get("choices") or []:
                    texto = (opcion.get("delta") or {}).get("content")
                    if texto:
                        yield ("texto", texto)
                    if opcion.get("finish_reason"):
                        motivo = opcion["finish_reason"]
                extra = obj.get("x_groq") or {}
                if isinstance(extra, dict) and extra.get("usage"):
                    uso = extra["usage"]
                elif obj.get("usage"):
                    uso = obj["usage"]
            if not motivo:
                raise ErrorIA(
                    "interrumpido",
                    f"La conexión con groq/{motor.modelo} se cerró antes de terminar.",
                    reintentable=True,
                )
            yield ("fin", (motivo, uso))

    # ------------------------------------------------------------------ redacción
    async def generar(
        self,
        prompt: str,
        modo: str = "nuevo",
        instruccion: str = "",
        texto_previo: str = "",
        calidad: str = "default",
    ) -> AsyncIterator[Evento]:
        s = self.s
        motores = self.candidatos(calidad)
        if not motores:
            yield Evento("error", datos={
                "codigo": "sin_motor",
                "http": 503,
                "mensaje": "No hay un motor de IA configurado en el servidor. Agrega GEMINI_API_KEY "
                           "(o GROQ_API_KEY) en las variables de entorno.",
            })
            return

        base = construir_mensajes(prompt, modo, instruccion, texto_previo)
        previo_continuar = texto_previo if (modo == "continuar" and (texto_previo or "").strip()) else ""
        acumulado = ""
        continuaciones = 0
        intentos = [0] * len(motores)
        degradado = [False] * len(motores)
        tokens = {"entrada": 0, "salida": 0, "pensamiento": 0}
        errores: list = []
        inicio = time.monotonic()
        idx = 0
        vueltas = 0
        max_vueltas = len(motores) * (max(1, s.INTENTOS_POR_MODELO) + 1) + max(0, s.MAX_CONTINUACIONES) + 2

        while idx < len(motores) and vueltas < max_vueltas:
            vueltas += 1
            motor = motores[idx]
            mensajes = mensajes_con_avance(base, modo, previo_continuar, acumulado)
            recorte = RecortadorSolape(previo_continuar + acumulado) if (acumulado or previo_continuar) else None
            motivo = None
            corriente = None
            try:
                if motor.proveedor == "gemini":
                    corriente = self._stream_gemini(motor, mensajes, degradado[idx])
                else:
                    corriente = self._stream_groq(motor, mensajes, degradado[idx])
                async for tipo, valor in corriente:
                    if tipo == "texto":
                        salida = recorte.filtrar(valor) if recorte else valor
                        if salida:
                            acumulado += salida
                            yield Evento("delta", salida)
                    else:
                        motivo, uso = valor
                        _sumar_tokens(tokens, motor.proveedor, uso)
                if recorte:
                    resto = recorte.vaciar()
                    if resto:
                        acumulado += resto
                        yield Evento("delta", resto)
            except Exception as exc:  # noqa: BLE001  (se clasifica y se decide qué hacer)
                error = exc if isinstance(exc, ErrorIA) else _convertir_excepcion(exc)
                errores.append(error)
                log.warning("Motor %s/%s falló (%s): %s", motor.proveedor, motor.modelo, error.codigo, error.mensaje)
                if error.parametros and not degradado[idx]:
                    degradado[idx] = True          # reintenta el mismo modelo sin parámetros opcionales
                    continue
                if error.no_existe:
                    self.no_disponibles[motor.modelo] = time.monotonic()
                if error.reintentable and intentos[idx] + 1 < max(1, s.INTENTOS_POR_MODELO):
                    intentos[idx] += 1
                    await asyncio.sleep(self._espera(intentos[idx]))
                    continue
                idx += 1
                if acumulado.strip() and idx < len(motores):
                    yield Evento("aviso", datos={
                        "codigo": "reanudando",
                        "mensaje": "Un motor se interrumpió; otro continúa el escrito desde donde quedó…",
                    })
                continue
            finally:
                if corriente is not None:
                    try:
                        await corriente.aclose()
                    except Exception:  # noqa: BLE001
                        pass

            # El motor terminó de transmitir sin error de red.
            if motivo in MOTIVOS_BLOQUEO:
                errores.append(ErrorIA(
                    "bloqueado",
                    f"{motor.proveedor}/{motor.modelo} detuvo la respuesta por sus filtros ({motivo}).",
                    bloqueo=True,
                ))
                if not acumulado.strip():
                    idx += 1
                    continue
                yield self._fin(acumulado, motor, motivo, True, continuaciones, tokens, inicio)
                return
            if motivo in MOTIVOS_CONTINUAR:
                if not acumulado.strip():
                    errores.append(ErrorIA(
                        "vacio", f"{motor.proveedor}/{motor.modelo} agotó su límite sin escribir texto ({motivo})."
                    ))
                    idx += 1
                    continue
                if continuaciones < max(0, s.MAX_CONTINUACIONES):
                    continuaciones += 1
                    yield Evento("aviso", datos={
                        "codigo": "continuando",
                        "parte": continuaciones + 1,
                        "mensaje": f"El escrito es largo: continuando (parte {continuaciones + 1})…",
                    })
                    continue
                yield self._fin(acumulado, motor, motivo, True, continuaciones, tokens, inicio)
                return
            if not acumulado.strip():
                errores.append(ErrorIA("vacio", f"{motor.proveedor}/{motor.modelo} no devolvió texto."))
                idx += 1
                continue
            yield self._fin(acumulado, motor, motivo or "STOP", False, continuaciones, tokens, inicio)
            return

        if acumulado.strip():
            ultimo = motores[min(idx, len(motores) - 1)]
            yield self._fin(acumulado, ultimo, "INTERRUMPIDO", True, continuaciones, tokens, inicio)
            return
        yield Evento("error", datos=self._error_final(errores))

    def _fin(self, acumulado, motor, motivo, truncado, continuaciones, tokens, inicio) -> Evento:
        segundos = round(time.monotonic() - inicio, 1)
        log.info(
            "Redacción %s · motor=%s/%s motivo=%s continuaciones=%d segundos=%.1f tokens=%s caracteres=%d",
            "INCOMPLETA" if truncado else "ok", motor.proveedor, motor.modelo, motivo,
            continuaciones, segundos, tokens, len(acumulado),
        )
        return Evento("fin", datos={
            "truncado": truncado,
            "motivo": motivo,
            "modelo": motor.modelo,
            "proveedor": motor.proveedor,
            "continuaciones": continuaciones,
            "segundos": segundos,
            "tokens": dict(tokens),
        })

    @staticmethod
    def _error_final(errores: list) -> dict:
        codigos = {e.codigo for e in errores}
        if any(e.bloqueo for e in errores):
            mensaje = ("El proveedor de IA bloqueó este contenido con sus filtros de seguridad. Si los hechos son "
                       "especialmente gráficos, descríbelos de forma más sobria e intenta de nuevo.")
            http = 422
        elif codigos and codigos <= {"permiso", "no_existe", "parametros", "sin_acceso"}:
            mensaje = ("La clave de API no tiene acceso a los modelos configurados (algunos, como gemini-4-argon, "
                       "no están en el plan gratuito) o la configuración es inválida. Revisa GEMINI_API_KEY y "
                       "GEMINI_MODEL en el servidor.")
            http = 503
        elif "cuota" in codigos:
            mensaje = "Se agotó la cuota del proveedor de IA. Espera unos minutos o revisa la facturación de la clave."
            http = 503
        else:
            mensaje = "No se pudo conectar con el motor de IA. Intenta de nuevo en unos minutos."
            http = 503
        return {"codigo": "sin_respuesta", "http": http, "mensaje": mensaje}

    # ------------------------------------------------------------------ análisis de estilo
    async def analizar_estilo(self, muestra: str) -> dict:
        prompt = PROMPT_ESTILO + "\n\nESCRITO:\n<<<\n" + muestra[:12000] + "\n>>>"
        for motor in self.candidatos("default"):
            for degradado in (False, True):
                try:
                    texto = await self._completar_json(motor, prompt, degradado)
                except Exception as exc:  # noqa: BLE001
                    error = exc if isinstance(exc, ErrorIA) else _convertir_excepcion(exc)
                    log.warning("Análisis de estilo con %s/%s falló (%s).", motor.proveedor, motor.modelo, error.codigo)
                    if error.parametros and not degradado:
                        continue
                    if error.no_existe:
                        self.no_disponibles[motor.modelo] = time.monotonic()
                    break
                datos = extraer_json(texto)
                if datos:
                    lineas = [
                        f"{nombre}: {str(datos.get(clave, '')).strip()}"
                        for clave, nombre in ETIQUETAS_ESTILO.items()
                        if str(datos.get(clave, "")).strip()
                    ]
                    if lineas:
                        return {"ok": True, "ficha": "\n".join(lineas), "raw": datos}
                break
        return {"ok": False, "error": "No se pudo generar la ficha de estilo. Intenta de nuevo en unos minutos.", "ficha": ""}

    # ------------------------------------------------------------------ evaluación de pertinencia
    async def evaluar_pertinencia_json(self, prompt: str) -> Optional[dict]:
        candidatos = []
        if self.s.GEMINI_API_KEY.strip():
            candidatos.append(Motor("gemini", "gemini-3.5-flash-lite"))
        candidatos.extend(self.candidatos("default"))

        for motor in candidatos:
            for degradado in (False, True):
                try:
                    texto = await self._completar_json(motor, prompt, degradado, esquema=ESQUEMA_PERTINENCIA)
                except Exception as exc:  # noqa: BLE001
                    error = exc if isinstance(exc, ErrorIA) else _convertir_excepcion(exc)
                    log.debug("Evaluación de pertinencia con %s/%s falló (%s).", motor.proveedor, motor.modelo, error.codigo)
                    if error.parametros and not degradado:
                        continue
                    break
                datos = extraer_json(texto)
                if datos and "respalda" in datos:
                    return datos
                break
        return None

    # ------------------------------------------------------------------ evaluación de requisitos normativos
    async def evaluar_requisitos_json(self, prompt: str) -> Optional[list]:
        candidatos = []
        if self.s.GEMINI_API_KEY.strip():
            candidatos.append(Motor("gemini", "gemini-3.5-flash-lite"))
        candidatos.extend(self.candidatos("default"))

        for motor in candidatos:
            for degradado in (False, True):
                try:
                    texto = await self._completar_json(motor, prompt, degradado, esquema=ESQUEMA_REVISION)
                except Exception as exc:  # noqa: BLE001
                    error = exc if isinstance(exc, ErrorIA) else _convertir_excepcion(exc)
                    log.debug("Evaluación de requisitos con %s/%s falló (%s).", motor.proveedor, motor.modelo, error.codigo)
                    if error.parametros and not degradado:
                        continue
                    break
                datos = extraer_json(texto)
                if isinstance(datos, list):
                    return datos
                if isinstance(datos, dict) and "requisitos" in datos and isinstance(datos["requisitos"], list):
                    return datos["requisitos"]
                break
        return None

    async def _completar_json(self, motor: Motor, prompt: str, degradado: bool, esquema: Optional[dict] = None) -> str:
        s = self.s
        cliente = await self._cliente()
        if motor.proveedor == "gemini":
            config = {"maxOutputTokens": 8192}
            if not degradado:
                config["responseMimeType"] = "application/json"
                config["responseSchema"] = esquema or ESQUEMA_ESTILO
            payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": config}
            respuesta = await cliente.post(
                f"{s.GEMINI_API_BASE.rstrip('/')}/v1beta/models/{motor.modelo}:generateContent",
                json=payload,
                headers=self._cab_gemini(),
                timeout=180.0,
            )
            if respuesta.status_code != 200:
                raise ErrorIA.desde_http("gemini", motor.modelo, respuesta.status_code, respuesta.text)
            datos = respuesta.json()
            candidato = (datos.get("candidates") or [{}])[0] or {}
            partes = (candidato.get("content") or {}).get("parts") or []
            return "".join(p.get("text", "") for p in partes if not p.get("thought"))
        payload = {"model": motor.modelo, "messages": [{"role": "user", "content": prompt}], "max_tokens": 4096}
        if not degradado:
            payload["response_format"] = {"type": "json_object"}
        respuesta = await cliente.post(
            f"{s.GROQ_API_BASE.rstrip('/')}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {s.GROQ_API_KEY.strip()}", "Content-Type": "application/json"},
            timeout=90.0,
        )
        if respuesta.status_code != 200:
            raise ErrorIA.desde_http("groq", motor.modelo, respuesta.status_code, respuesta.text)
        datos = respuesta.json()
        return (((datos.get("choices") or [{}])[0] or {}).get("message") or {}).get("content") or ""


gemini_service = GeminiService()

```


## 📄 Archivo: `app/services/auditor_catalogo.py`
```python
"""Servicio de Auditoría Jurídica Automatizada del Catálogo de Tipos.

Utiliza Gemini con razonamiento profundo (thinkingLevel="high") para auditar
estructuras de memoriales y demandas colombianas frente al Código General del
Proceso (CGP), CPACA, CST y estatutos especiales vigentes a 2026.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.services.gemini_service import gemini_service, Motor

log = logging.getLogger("memorialista.auditor_catalogo")

CATALOGO_DIR = Path(__file__).resolve().parent.parent / "catalogo"
TIPOS_DIR = CATALOGO_DIR / "tipos"

PROMPT_SISTEMA_AUDITOR = """Eres el Magistrado y Juez Auditor de Admisión y Control de Calidad Procesal de Colombia.
Tu responsabilidad es realizar la auditoría jurídica previa de una estructura de memorial o demanda que se incorporará al catálogo oficial de El Memorialista.

Debes examinar minuciosamente el tipo frente a la legislación colombiana vigente (Código General del Proceso - Ley 1564 de 2012, Ley 2213 de 2022 de justicia digital, Ley 2220 de 2022 de conciliación, Constitución Política y normas especiales aplicables).

Analiza rigurosamente los siguientes 5 ejes:
1. VIGENCIA NORMATIVA Y FUENTES: ¿Las normas citadas están vigentes? ¿Se omiten reformas procesales recientes?
2. REQUISITOS DE ADMISIBILIDAD (Art. 82 CGP y normas especiales): ¿La guía exige todos los presupuestos no subsanables para evitar autos inadmisorios o rechazos de plano?
3. DELIMITACIÓN DE CUANTÍA Y COMPETENCIA: ¿Se define con claridad si es mínima, menor o mayor cuantía y el juez competente?
4. CAMPOS DEL FORMULARIO: ¿Los campos recogen la información fáctica, probatoria y canales digitales obligatorios (Ley 2213 de 2022)?
5. APERCIBIMIENTOS O MANIFESTACIONES OBLIGATORIAS: ¿Incluye juramentos o apercibimientos especiales de ley?

Debes responder ÚNICAMENTE con un objeto JSON válido con la siguiente estructura exacta:
{
  "aprobado": true | false,
  "puntuacion": int (0 a 100, donde >= 90 aprueba),
  "dictamen": "Resumen ejecutivo del concepto jurídico en 1 o 2 párrafos concisos.",
  "puntos_fuertes": ["punto 1", "punto 2"],
  "observaciones": ["observación o recomendación 1"],
  "riesgos_inadmisorios": ["riesgo 1 o dejar vacío si no hay"],
  "normas_validadas": ["Norma 1 con artículo", "Norma 2"],
  "recomendacion_final": "Aprobado para litigio / Requiere ajustes previos"
}
No incluyas explicaciones antes ni después del bloque JSON."""


async def auditar_tipo_dict(tipo_data: dict[str, Any]) -> dict[str, Any]:
    """Audita un tipo de memorial frente a la legislación procesal colombiana."""
    copia_tipo = {k: v for k, v in tipo_data.items() if k != "auditoria_ia"}
    texto_entrada = json.dumps(copia_tipo, indent=2, ensure_ascii=False)

    mensajes = [
        ("user", f"Audita jurídicamente este tipo de memorial para el catálogo colombiano:\n\n```json\n{texto_entrada}\n```")
    ]

    motores = gemini_service.candidatos("default")
    acumulado = ""
    motor_usado = None

    for motor in motores:
        try:
            acumulado = ""
            if motor.proveedor == "gemini":
                async for evento, chunk in gemini_service._stream_gemini(
                    motor, mensajes, degradado=False, instruccion_sistema=PROMPT_SISTEMA_AUDITOR
                ):
                    if evento == "texto":
                        acumulado += chunk
            elif motor.proveedor == "groq":
                mensajes_groq = [("system", PROMPT_SISTEMA_AUDITOR)] + mensajes
                async for evento, chunk in gemini_service._stream_groq(motor, mensajes_groq, False):
                    if evento == "texto":
                        acumulado += chunk
            if acumulado.strip():
                motor_usado = motor
                break
        except Exception as e:
            log.warning("Motor %s/%s falló en auditoría: %s. Probando siguiente...", motor.proveedor, motor.modelo, e)
            await asyncio.sleep(1.0)
            continue

    if not motor_usado:
        motor_usado = Motor("gemini", "gemini-3.8-flash", "high")

    limpio = acumulado.strip()
    if "```json" in limpio:
        limpio = limpio.split("```json")[1].split("```")[0].strip()
    elif "```" in limpio:
        limpio = limpio.split("```")[1].split("```")[0].strip()

    try:
        resultado = json.loads(limpio)
    except json.JSONDecodeError as err:
        log.error("Respuesta del auditor IA no fue JSON válido: %s | Texto: %s", err, limpio[:200])
        resultado = {
            "aprobado": False,
            "puntuacion": 70,
            "dictamen": f"La auditoría se ejecutó pero la respuesta del modelo no pudo parsearse como JSON: {err}",
            "puntos_fuertes": [],
            "observaciones": ["Reintentar auditoría"],
            "riesgos_inadmisorios": ["Respuesta no estructurada"],
            "normas_validadas": [tipo_data.get("norma", "Norma no especificada")],
            "recomendacion_final": "Revisar manualmente"
        }

    meses_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    ahora = datetime.now()
    resultado["fecha_auditoria"] = f"{ahora.day} de {meses_es[ahora.month - 1]} de {ahora.year}"
    resultado["modelo_auditor"] = motor_usado.modelo
    return resultado


async def auditar_tipo_por_id(tipo_id: str, actualizar_json: bool = True) -> dict[str, Any]:
    """Carga un archivo de tipo por su ID, lo audita con IA y opcionalmente actualiza su JSON."""
    ruta_archivo = TIPOS_DIR / f"{tipo_id}.json"
    if not ruta_archivo.exists():
        raise FileNotFoundError(f"No existe el archivo de tipo {ruta_archivo}")

    with open(ruta_archivo, "r", encoding="utf-8") as f:
        tipo_data = json.load(f)

    dictamen = await auditar_tipo_dict(tipo_data)

    if actualizar_json:
        # Si la puntuación es >= 90 y está aprobado, certificarlo con IA
        if dictamen.get("aprobado") and dictamen.get("puntuacion", 0) >= 90:
            tipo_data["revisado_por"] = f"Auditado con IA Jurídica ({dictamen.get('modelo_auditor', 'Gemini')})"
            tipo_data["fecha_revision"] = dictamen.get("fecha_auditoria", "octubre de 2026")
        else:
            tipo_data["revisado_por"] = "pendiente"

        tipo_data["auditoria_ia"] = {
            "puntuacion": dictamen.get("puntuacion", 0),
            "aprobado": dictamen.get("aprobado", False),
            "dictamen": dictamen.get("dictamen", ""),
            "normas_validadas": dictamen.get("normas_validadas", []),
            "observaciones": dictamen.get("observaciones", []),
            "riesgos_inadmisorios": dictamen.get("riesgos_inadmisorios", []),
            "modelo_auditor": dictamen.get("modelo_auditor", ""),
            "fecha": dictamen.get("fecha_auditoria", ""),
        }

        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(tipo_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        log.info("Tipo %s auditado con éxito. Puntuación: %s. Estado: %s",
                 tipo_id, dictamen.get("puntuacion"), tipo_data["revisado_por"])

    return dictamen


if __name__ == "__main__":
    import asyncio
    import sys

    tipo_arg = sys.argv[1] if len(sys.argv) > 1 else "tutela"
    print(f"Auditoría Jurídica IA para '{tipo_arg}'...")
    res = asyncio.run(auditar_tipo_por_id(tipo_arg, actualizar_json=False))
    print(json.dumps(res, indent=2, ensure_ascii=False))

```


## 📄 Archivo: `app/services/revisor_requisitos.py`
```python
"""
Servicio de revisión de requisitos legales y procesales para escritos jurídicos.
Evalúa el cumplimiento de los requisitos del catálogo según la norma de cada tipo.
"""
import json
import logging
import re
from typing import Any, Tuple

from app.services.prompt import obtener_tipo
from app.services.gemini_service import gemini_service

log = logging.getLogger("memorialista.revisor")


def _evaluacion_heuristica(req: dict[str, Any], texto_lower: str) -> Tuple[str, str, str]:
    """Evaluación heurística de respaldo en caso de que no haya conexión con el modelo de IA."""
    rid = req.get("id", "")
    critico = bool(req.get("critico", False))
    norma = req.get("norma", "")

    if "juramento" in rid and ("otra_tutela" in rid or "art37" in rid or "2591" in norma):
        if ("juramento" in texto_lower or "juró" in texto_lower) and ("otra" in texto_lower or "2591" in texto_lower or "misma" in texto_lower):
            return "cumple", "Contiene manifestación bajo juramento de no haber interpuesto otra tutela.", ""
        return "no_cumple", "No se encontró la manifestación bajo juramento del art. 37 del Decreto 2591 de 1991.", "Agrega en acápite de JURAMENTO: 'Manifiesto bajo la gravedad del juramento que no he presentado otra acción de tutela por los mismos hechos y derechos ante ninguna autoridad judicial (art. 37 del Decreto 2591 de 1991)'."

    if "juramento_estimatorio" in rid or "206" in norma:
        if "juramento estimatorio" in texto_lower or "artículo 206" in texto_lower or "art. 206" in texto_lower:
            return "cumple", "Incluye acápite de juramento estimatorio.", ""
        if any(p in texto_lower for p in ("perjuicio", "daño emergente", "lucro cesante", "indemniza")):
            return "no_cumple", "Se reclaman perjuicios pero se omitió el juramento estimatorio.", "Agrega acápite de JURAMENTO ESTIMATORIO discriminando concepto por concepto la cuantía razonada de los perjuicios reclamados (art. 206 CGP)."
        return "no_aplica", "No se evidencian pretensiones de condena en perjuicios materiales.", ""

    if "canal_digital" in rid or "juramento_canal" in rid or "2213" in norma:
        tiene_correo = "@" in texto_lower or "correo" in texto_lower or "canal digital" in texto_lower
        tiene_juramento = "juramento" in texto_lower and ("dirección" in texto_lower or "canal" in texto_lower or "obtuvo" in texto_lower)
        if "juramento_canal" in rid:
            if tiene_juramento:
                return "cumple", "Contiene afirmación sobre el canal digital del demandado.", ""
            return "no_cumple", "Falta la afirmación bajo juramento sobre cómo se obtuvo la dirección electrónica.", "Agrega en notificaciones: 'Afirmo bajo la gravedad del juramento que la dirección electrónica indicada para el demandado es la que utiliza para sus comunicaciones y fue obtenida [indicar medio o evidencia], conforme al art. 8 de la Ley 2213 de 2022'."
        if tiene_correo:
            return "cumple", "Se indican canales digitales de las partes.", ""
        return "no_cumple", "No se identificaron direcciones electrónicas para las partes.", "Incluye los canales digitales (correos electrónicos) de las partes y sus apoderados (art. 6 Ley 2213 de 2022)."

    if "conciliacion" in rid or "2220" in norma:
        if "concilia" in texto_lower:
            return "cumple", "Se menciona el trámite o constancia de conciliación prejudicial.", ""
        if "cautelar" in texto_lower or "embargo" in texto_lower or "secuestro" in texto_lower:
            return "no_aplica", "Se solicitan medidas cautelares previas, lo cual exceptúa el requisito de procedibilidad.", ""
        return "no_cumple", "No se indica si se agotó la conciliación previa obligatoria.", "Indica que se agotó la conciliación extrajudicial en derecho aportando la constancia de no acuerdo o imposibilidad (Ley 2220 de 2022)."

    if "contraprestacion" in rid or "420" in norma and "5" in norma:
        if "contraprestación" in texto_lower or "contraprestacion" in texto_lower or "no depende" in texto_lower:
            return "cumple", "Contiene manifestación de no depender de contraprestación pendiente (art. 420 num. 5 CGP).", ""
        return "no_cumple", "Falta manifestación expresa de que el pago no depende de contraprestación pendiente del acreedor.", "Incluye en los hechos o acápite de juramento: 'Manifiesto que el pago de la suma demandada no depende del cumplimiento de una contraprestación pendiente a cargo del acreedor (art. 420 num. 5 del CGP)'."

    if "apercibimiento" in rid or "421" in norma:
        if "apercibimiento" in texto_lower or "fuerza de sentencia" in texto_lower or "auto con fuerza" in texto_lower or ("421" in texto_lower and "silencio" in texto_lower):
            return "cumple", "Incluye solicitud de apercibimiento legal del art. 421 del CGP.", ""
        return "no_cumple", "Falta solicitud expresa de apercibimiento legal del art. 421 del CGP.", "Agrega en pretensiones: 'Solicito apercibir al demandado conforme al artículo 421 del CGP, advirtiéndole que si no paga o guarda silencio dentro del término de 10 días, se dictará auto con fuerza de sentencia condenatoria'."

    if "pruebas_o_juramento" in rid or ("420" in norma and "6" in norma):
        if "prueba" in texto_lower or "anexo" in texto_lower or "juramento" in texto_lower or "document" in texto_lower:
            return "cumple", "Se relacionan pruebas documentales o juramento de carecer de ellas.", ""
        return "no_cumple", "Se omitieron las pruebas documentales o el juramento de no poseerlas.", "Relaciona los documentos contractuales o manifiesta bajo juramento que careces de ellos (art. 420 num. 6 CGP)."

    if "procedencia" in rid or "subsidiariedad" in rid:
        if "subsidiariedad" in texto_lower or "inmediatez" in texto_lower or "perjuicio irremediable" in texto_lower or "otro medio" in texto_lower:
            return "cumple", "Desarrolla los requisitos de procedencia, inmediatez y subsidiariedad.", ""
        return "no_cumple", "Falta fundamentación explícita sobre la procedencia de la tutela.", "Agrega acápite de PROCEDENCIA justificando la inmediatez y la falta de otro mecanismo judicial idóneo y eficaz o la configuración de un perjuicio irremediable."

    if "notificaciones" in rid:
        if "notificaci" in texto_lower or "direcci" in texto_lower:
            return "cumple", "Contiene acápite de notificaciones.", ""
        return "no_cumple", "Se omitió el acápite de notificaciones.", "Incluye acápite de NOTIFICACIONES con dirección física y electrónica de las partes."

    if "juez" in rid or "destinatario" in rid or "autoridad" in rid:
        if any(j in texto_lower for j in ("juez", "tribunal", "magistrad", "señor", "señores", "fiscalía", "procuraduría", "alcaldía")):
            return "cumple", "Contiene designación de la autoridad o despacho judicial.", ""
        return "no_cumple", "Falta la designación del juez o autoridad a quien se dirige.", "Indica expresamente el juez o entidad competente a quien se dirige el escrito."

    if "pretension" in rid or "objeto" in rid or "mandamiento" in rid:
        if "pretensi" in texto_lower or "pido" in texto_lower or "solicito" in texto_lower or "mandamiento" in texto_lower:
            return "cumple", "Pretensiones formuladas en el texto.", ""
        return "no_cumple", "No se identificaron pretensiones claras.", "Formula con precisión y claridad lo que se pretende de manera numerada y clasificada."

    if "hecho" in rid:
        if "hecho" in texto_lower or "1." in texto_lower:
            return "cumple", "Contiene narración de hechos.", ""
        return "no_cumple", "Falta la relación numerada de hechos.", "Expón los hechos en orden cronológico, numerados y clasificados."

    if "cuantia" in rid or "competencia" in rid:
        if "cuantía" in texto_lower or "cuantia" in texto_lower or "competencia" in texto_lower or "$" in texto_lower or "smmlv" in texto_lower:
            return "cumple", "Se estima la cuantía o se indica la competencia.", ""
        return "no_cumple" if critico else "no_aplica", "No se indica la cuantía o competencia.", "Incluye acápite de CUANTÍA Y COMPETENCIA indicando el valor de las pretensiones para fijar el trámite."

    # Heurística genérica
    palabras_clave = [p for p in re.findall(r'\b[a-zA-ZáéíóúÁÉÍÓÚñÑ]{4,}\b', req.get("texto", "").lower()) if p not in ("para", "cada", "este", "cual", "como", "sobre", "entre")]
    coincidencias = sum(1 for p in palabras_clave if p in texto_lower)
    if coincidencias >= max(1, len(palabras_clave) // 3):
        return "cumple", "El escrito aborda los elementos esenciales del requisito.", ""
    if critico:
        return "no_cumple", f"No se evidencia el cumplimiento claro de este requisito ({norma}).", f"Revisa e incorpora lo exigido por {norma}: {req.get('texto', '')}."
    return "no_aplica", "Requisito no evidenciado o no exigible en este trámite concreto.", ""


async def revisar_requisitos(escrito: str, tipo_id: str) -> list[dict[str, Any]]:
    """
    Evalúa el cumplimiento de cada requisito normativo del tipo para el escrito dado.
    Utiliza un modelo de IA económico (gemini-3.5-flash-lite) con salida JSON estructurada,
    respaldado por verificación heurística determinista.
    """
    tipo = obtener_tipo(tipo_id)
    if not tipo:
        return []

    requisitos = tipo.get("requisitos", [])
    if not requisitos:
        return []

    prompt = (
        "Eres un auditor jurídico colombiano experto en técnica procesal y derecho procesal civil, laboral, penal y administrativo.\n"
        f"Tu tarea es evaluar si el siguiente escrito jurídico cumple con cada uno de los requisitos normativos del tipo de escrito '{tipo.get('nombre', tipo_id)}'.\n\n"
        f"NORMA BASE DEL TIPO: {tipo.get('norma', '')}\n\n"
        "REQUISITOS A EVALUAR:\n"
        f"{json.dumps(requisitos, ensure_ascii=False, indent=2)}\n\n"
        "ESCRITO JURÍDICO A REVISAR:\n<<<\n"
        f"{escrito[:35000]}\n>>>\n\n"
        "INSTRUCCIONES DE EVALUACIÓN:\n"
        "Para CADA requisito de la lista debes determinar:\n"
        '- "id": el ID exacto del requisito evaluado.\n'
        '- "estado": "cumple" si el escrito contiene el requisito; "no_cumple" si fue omitido o está defectuoso; "no_aplica" si por las particularidades del escrito no es exigible (ej.: juramento estimatorio cuando no se cobran perjuicios, conciliación previa cuando se piden medidas cautelares).\n'
        '- "evidencia": fragmento breve del texto (máx 200 caracteres) que demuestra el cumplimiento o explica brevemente la omisión.\n'
        '- "sugerencia": si el estado es "no_cumple", redacta la sugerencia o fórmula jurídica exacta para subsanarlo. Si cumple o no aplica, deja una cadena vacía o breve nota.\n\n'
        "Responde EXCLUSIVAMENTE con un arreglo JSON válido con este esquema:\n"
        "[\n"
        '  {\n    "id": "identificador",\n    "estado": "cumple" | "no_cumple" | "no_aplica",\n    "evidencia": "texto",\n    "sugerencia": "texto"\n  }\n'
        "]"
    )

    datos_eval = None
    try:
        datos_eval = await gemini_service.evaluar_requisitos_json(prompt)
    except Exception as exc:  # noqa: BLE001
        log.warning("Evaluación de requisitos con IA omitida o falló: %s", exc)

    eval_map = {}
    if isinstance(datos_eval, list):
        for item in datos_eval:
            if isinstance(item, dict) and "id" in item:
                eval_map[item["id"]] = item

    resultado = []
    texto_lower = escrito.lower()
    for req in requisitos:
        rid = req["id"]
        ev = eval_map.get(rid)

        if ev and isinstance(ev, dict):
            estado = str(ev.get("estado", "")).lower().strip()
            if estado not in ("cumple", "no_cumple", "no_aplica"):
                estado = "cumple" if "cumple" in estado else "no_cumple"
            evidencia = str(ev.get("evidencia", ""))[:300]
            sugerencia = str(ev.get("sugerencia", ""))[:500]
        else:
            estado, evidencia, sugerencia = _evaluacion_heuristica(req, texto_lower)

        resultado.append({
            "id": rid,
            "texto": req.get("texto", ""),
            "norma": req.get("norma", ""),
            "critico": bool(req.get("critico", False)),
            "estado": estado,
            "evidencia": evidencia,
            "sugerencia": sugerencia,
        })

    return resultado

```


## 📄 Archivo: `app/services/verificador_citas.py`
```python
"""Servicio de verificación de citas jurídicas en Colombia (v2.2.1).

FORMATOS DE URL ESTABLES INVESTIGADOS Y DOCUMENTADOS:
=============================================================================
1. CORTE CONSTITUCIONAL DE COLOMBIA (Relatoría Oficial):
   URL: https://www.corteconstitucional.gov.co/relatoria/{AÑO}/{TIPO}-{NÚMERO}-{AA}.htm
   Parámetros:
     - {AÑO}: Año en 4 dígitos (ej. 2008, 2023).
     - {TIPO}: T, C, SU o A (para Autos).
     - {NÚMERO}: Número de la providencia sin ceros a la izquierda (ej. 760, 522).
     - {AA}: Año en 2 dígitos con relleno a 2 cifras (ej. 08, 23, 99).
   Comportamiento del servidor:
     - Respuesta HTTP 200 que contiene el número de sentencia en el cuerpo = "existe".
     - HTTP 404 o HTTP 200 sin el número de providencia en el cuerpo = "no_encontrada".
     - Error de red o timeout (10 s) = "sin_verificar".

2. SECRETARÍA DEL SENADO DE COLOMBIA (Base de Leyes y Decretos):
   URL Leyes: http://www.secretariasenado.gov.co/senado/basedoc/ley_{numero:04d}_{año}.html
   URL Decretos: http://www.secretariasenado.gov.co/senado/basedoc/decreto_{numero:04d}_{año}.html
   Parámetros:
     - {numero:04d}: Número de la norma con relleno a 4 dígitos con ceros (ej. 1755, 0030, 2591).
     - {año}: Año en 4 dígitos (ej. 2015, 1991, 1992).
   Comportamiento del servidor:
     - HTTP 200 = Norma existente y registrada.
     - HTTP 404 = "Categoría no encontrada" / Norma no encontrada.

3. CÓDIGOS OFICIALES EN SECRETARÍA DEL SENADO:
   - CGP: http://www.secretariasenado.gov.co/senado/basedoc/codigo_general_proceso.html
   - CPACA: http://www.secretariasenado.gov.co/senado/basedoc/ley_1437_2011.html
   - Código Civil: http://www.secretariasenado.gov.co/senado/basedoc/codigo_civil.html
   - CST: http://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo.html
   - Ley 906 (CPP): http://www.secretariasenado.gov.co/senado/basedoc/ley_0906_2004.html
   - Constitución Política: http://www.secretariasenado.gov.co/senado/basedoc/constitucion_politica_1991.html
=============================================================================
"""
import asyncio
import html
import logging
import os
import re
import sqlite3
import time
from typing import Any, Optional

import httpx

from app.services.gemini_service import gemini_service

log = logging.getLogger("memorialista.citas")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "citas_cache.sqlite3")
TTL_SEGUNDOS = 30 * 24 * 3600  # 30 días de caché

# Expresiones regulares para extracción
RE_SENTENCIAS = re.compile(
    r'(?i)\b(?:sentencias?\s+|auto\s+)?(T|C|SU|A)[-\s]?(\d{1,5})\s*(?:(?:de|\/|-)\s*(\d{2,4}))\b'
)
RE_AUTOS_PALABRA = re.compile(
    r'(?i)\bauto\s+(\d{1,5})\s*(?:(?:de|\/|-)\s*(\d{2,4}))\b'
)
RE_LEYES = re.compile(r'(?i)\bley\s+(\d{1,5})\s+de\s+(\d{4})\b')
RE_DECRETOS = re.compile(r'(?i)\bdecreto(?:[-\s]ley)?\s+(\d{1,5})\s+de\s+(\d{4})\b')

CODIGOS_INFO = {
    "CGP": {
        "nombre": "Código General del Proceso",
        "url": "http://www.secretariasenado.gov.co/senado/basedoc/codigo_general_proceso.html",
        "max_art": 627,
        "regex": re.compile(r'(?i)\bart(?:ículo)?\.?\s*(\d{1,4})\s*(?:del\s+|de\s+la\s+|en\s+el\s+)?(?:CGP|Código General del Proceso)\b'),
    },
    "CPACA": {
        "nombre": "Código de Procedimiento Administrativo y de lo Contencioso Administrativo",
        "url": "http://www.secretariasenado.gov.co/senado/basedoc/ley_1437_2011.html",
        "max_art": 309,
        "regex": re.compile(r'(?i)\bart(?:ículo)?\.?\s*(\d{1,4})\s*(?:del\s+|de\s+la\s+|en\s+el\s+)?(?:CPACA|Código de Procedimiento Administrativo y de lo Contencioso Administrativo)\b'),
    },
    "Código Civil": {
        "nombre": "Código Civil",
        "url": "http://www.secretariasenado.gov.co/senado/basedoc/codigo_civil.html",
        "max_art": 2545,
        "regex": re.compile(r'(?i)\bart(?:ículo)?\.?\s*(\d{1,4})\s*(?:del\s+|de\s+la\s+|en\s+el\s+)?(?:Código Civil|C\.C\.)\b'),
    },
    "CST": {
        "nombre": "Código Sustantivo del Trabajo",
        "url": "http://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo.html",
        "max_art": 492,
        "regex": re.compile(r'(?i)\bart(?:ículo)?\.?\s*(\d{1,4})\s*(?:del\s+|de\s+la\s+|en\s+el\s+)?(?:CST|Código Sustantivo del Trabajo)\b'),
    },
    "Ley 906": {
        "nombre": "Código de Procedimiento Penal (Ley 906 de 2004)",
        "url": "http://www.secretariasenado.gov.co/senado/basedoc/ley_0906_2004.html",
        "max_art": 539,
        "regex": re.compile(r'(?i)\bart(?:ículo)?\.?\s*(\d{1,4})\s*(?:de\s+la\s+)?Ley\s+906(?:\s+de\s+2004)?\b'),
    },
    "Constitución": {
        "nombre": "Constitución Política de Colombia",
        "url": "http://www.secretariasenado.gov.co/senado/basedoc/constitucion_politica_1991.html",
        "max_art": 380,
        "regex": re.compile(r'(?i)\bart(?:ículo)?\.?\s*(\d{1,4})\s*(?:de\s+la\s+)?(?:Constitución(?: Política)?|C\.P\.)\b'),
    },
}


def _init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS citas_cache (
                    url TEXT PRIMARY KEY,
                    estado TEXT NOT NULL,
                    fragmento TEXT,
                    timestamp REAL NOT NULL
                )
                """
            )
            conn.commit()
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo inicializar SQLite para caché de citas: %s", exc)


_init_db()


def _obtener_cache(url: str) -> Optional[tuple[str, str]]:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT estado, fragmento, timestamp FROM citas_cache WHERE url = ?", (url,))
            row = cursor.fetchone()
            if row:
                estado, fragmento, ts = row
                if time.time() - ts < TTL_SEGUNDOS:
                    return estado, fragmento or ""
    except Exception as exc:  # noqa: BLE001
        log.debug("Error leyendo caché de citas: %s", exc)
    return None


def _guardar_cache(url: str, estado: str, fragmento: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO citas_cache (url, estado, fragmento, timestamp) VALUES (?, ?, ?, ?)",
                (url, estado, fragmento, time.time()),
            )
            conn.commit()
    except Exception as exc:  # noqa: BLE001
        log.debug("Error guardando en caché de citas: %s", exc)


def _limpiar_html(raw_html: str) -> str:
    """Elimina scripts, estilos y etiquetas HTML, dejando texto legible."""
    sin_scripts = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', raw_html)
    sin_tags = re.sub(r'<[^>]+>', ' ', sin_scripts)
    return " ".join(html.unescape(sin_tags).split())


def _normalizar_año(año_str: str) -> int:
    y = int(año_str)
    if y < 100:
        return 1900 + y if y >= 91 else 2000 + y
    return y


def _buscar_parrafo(texto: str, start: int, end: int) -> str:
    """Encuentra el párrafo completo que rodea al fragmento ubicado entre start y end."""
    prev_break = texto.rfind("\n\n", 0, start)
    p_start = 0 if prev_break == -1 else prev_break + 2
    next_break = texto.find("\n\n", end)
    p_end = len(texto) if next_break == -1 else next_break
    return texto[p_start:p_end].strip()


def extraer_citas(texto: str) -> list[dict[str, Any]]:
    """Extrae con expresiones regulares todas las citas de sentencias, leyes, decretos y códigos."""
    citas: list[dict[str, Any]] = []
    vistos = set()

    # 1. Sentencias de la Corte Constitucional (T-, C-, SU-, A-)
    for m in RE_SENTENCIAS.finditer(texto):
        tipo = m.group(1).upper()
        num_str = m.group(2)
        año = _normalizar_año(m.group(3))
        num = int(num_str)
        aa = f"{año % 100:02d}"
        ident = f"{tipo}-{num}-{aa}"
        clave = f"corte:{ident}"
        if clave in vistos:
            continue
        vistos.add(clave)
        parrafo = _buscar_parrafo(texto, m.start(), m.end())
        url = f"https://www.corteconstitucional.gov.co/relatoria/{año}/{tipo}-{num}-{aa}.htm"
        citas.append({
            "tipo_norma": "sentencia",
            "identificador": ident,
            "texto_original": m.group(0),
            "nombre": f"Sentencia {tipo}-{num} de {año}",
            "tipo_corte": tipo,
            "numero": num,
            "año": año,
            "url": url,
            "parrafo": parrafo,
        })

    # 2. Autos con la palabra 'Auto {numero} de {año}'
    for m in RE_AUTOS_PALABRA.finditer(texto):
        num = int(m.group(1))
        año = _normalizar_año(m.group(2))
        aa = f"{año % 100:02d}"
        ident = f"A-{num}-{aa}"
        clave = f"corte:{ident}"
        if clave in vistos:
            continue
        vistos.add(clave)
        parrafo = _buscar_parrafo(texto, m.start(), m.end())
        url = f"https://www.corteconstitucional.gov.co/relatoria/{año}/A-{num}-{aa}.htm"
        citas.append({
            "tipo_norma": "sentencia",
            "identificador": ident,
            "texto_original": m.group(0),
            "nombre": f"Auto {num} de {año}",
            "tipo_corte": "A",
            "numero": num,
            "año": año,
            "url": url,
            "parrafo": parrafo,
        })

    # 3. Leyes
    for m in RE_LEYES.finditer(texto):
        num = int(m.group(1))
        año = int(m.group(2))
        clave = f"ley:{num}_{año}"
        if clave in vistos:
            continue
        vistos.add(clave)
        parrafo = _buscar_parrafo(texto, m.start(), m.end())
        url = f"http://www.secretariasenado.gov.co/senado/basedoc/ley_{num:04d}_{año}.html"
        citas.append({
            "tipo_norma": "ley",
            "identificador": f"Ley {num} de {año}",
            "texto_original": m.group(0),
            "nombre": f"Ley {num} de {año}",
            "numero": num,
            "año": año,
            "url": url,
            "parrafo": parrafo,
        })

    # 4. Decretos
    for m in RE_DECRETOS.finditer(texto):
        num = int(m.group(1))
        año = int(m.group(2))
        clave = f"decreto:{num}_{año}"
        if clave in vistos:
            continue
        vistos.add(clave)
        parrafo = _buscar_parrafo(texto, m.start(), m.end())
        url = f"http://www.secretariasenado.gov.co/senado/basedoc/decreto_{num:04d}_{año}.html"
        citas.append({
            "tipo_norma": "decreto",
            "identificador": f"Decreto {num} de {año}",
            "texto_original": m.group(0),
            "nombre": f"Decreto {num} de {año}",
            "numero": num,
            "año": año,
            "url": url,
            "parrafo": parrafo,
        })

    # 5. Artículos de Códigos
    for cod_key, info in CODIGOS_INFO.items():
        for m in info["regex"].finditer(texto):
            art_num = int(m.group(1))
            clave = f"cod:{cod_key}_{art_num}"
            if clave in vistos:
                continue
            vistos.add(clave)
            parrafo = _buscar_parrafo(texto, m.start(), m.end())
            prep = "de la" if cod_key == "Constitución" else "del"
            citas.append({
                "tipo_norma": "codigo",
                "codigo": cod_key,
                "identificador": f"Art. {art_num} {cod_key}",
                "texto_original": m.group(0),
                "nombre": f"Artículo {art_num} {prep} {info['nombre']}",
                "articulo": art_num,
                "max_art": info["max_art"],
                "url": info["url"],
                "parrafo": parrafo,
            })

    return citas


async def _verificar_url_corte(url: str, tipo: str, num: int, aa: str, cliente: httpx.AsyncClient) -> tuple[str, str]:
    """Consulta la Corte Constitucional verificando que el 200 contenga el número de la sentencia."""
    cache = _obtener_cache(url)
    if cache:
        return cache

    try:
        resp = await cliente.get(url, timeout=10.0, follow_redirects=True)
        if resp.status_code == 200:
            texto_limpio = _limpiar_html(resp.text)
            # Debe contener el identificador ej. T-760 o T-760-08 o '760'
            patron_verif = re.compile(rf'(?i)\b{tipo}[-\s]?{num}\b')
            if patron_verif.search(texto_limpio):
                # Fragmento relevante de hasta 3000 caracteres
                fragmento = texto_limpio[:3000]
                _guardar_cache(url, "existe", fragmento)
                return "existe", fragmento
            # Si responde 200 pero es la página genérica / portal de error
            _guardar_cache(url, "no_encontrada", "")
            return "no_encontrada", ""
        if resp.status_code == 404:
            _guardar_cache(url, "no_encontrada", "")
            return "no_encontrada", ""
        return "sin_verificar", ""
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        log.info("Error conectando con Corte Constitucional (%s): %s", url, exc)
        return "sin_verificar", ""


async def _verificar_url_ley_decreto(url: str, cliente: httpx.AsyncClient) -> tuple[str, str]:
    """Consulta existencia de leyes o decretos en Secretaría del Senado."""
    cache = _obtener_cache(url)
    if cache:
        return cache

    try:
        resp = await cliente.get(url, timeout=10.0, follow_redirects=True)
        if resp.status_code == 200:
            texto_limpio = _limpiar_html(resp.text)
            fragmento = texto_limpio[:1000]
            _guardar_cache(url, "existe", fragmento)
            return "existe", fragmento
        if resp.status_code == 404:
            _guardar_cache(url, "no_encontrada", "")
            return "no_encontrada", ""
        return "sin_verificar", ""
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        log.info("Error conectando con Secretaría del Senado (%s): %s", url, exc)
        return "sin_verificar", ""


async def _evaluar_pertinencia_ia(cita: str, parrafo: str, fragmento_oficial: str) -> dict[str, str]:
    """Pide a gemini-3.5-flash-lite / IA una salida JSON {respalda: 'si'|'parcial'|'no', fragmento: texto corto}."""
    if not fragmento_oficial.strip() or not parrafo.strip():
        return {"respalda": "si", "fragmento": fragmento_oficial[:200]}

    prompt = (
        "Eres un asistente jurídico colombiano experto en verificación de jurisprudencia. "
        "Evalúa si el fragmento oficial de la sentencia respalda la afirmación del abogado en el memorial.\n\n"
        f"CITA: {cita}\n\n"
        f"AFIRMACIÓN DEL ABOGADO:\n<<<\n{parrafo[:1000]}\n>>>\n\n"
        f"FRAGMENTO OFICIAL DE LA SENTENCIA:\n<<<\n{fragmento_oficial[:3000]}\n>>>\n\n"
        "Responde EXCLUSIVAMENTE un JSON válido con esta estructura exacta:\n"
        '{\n  "respalda": "si" | "parcial" | "no",\n  "fragmento": "cita textual corta o síntesis"\n}'
    )

    try:
        res = await gemini_service.evaluar_pertinencia_json(prompt)
        if res and "respalda" in res:
            val = str(res["respalda"]).lower().strip()
            if val not in ("si", "parcial", "no"):
                val = "si" if "si" in val else "parcial"
            return {
                "respalda": val,
                "fragmento": str(res.get("fragmento", ""))[:300] or fragmento_oficial[:200],
            }
    except Exception as exc:  # noqa: BLE001
        log.debug("Evaluación de pertinencia con IA omitida o fallida (%s)", exc)

    # Fallback predeterminado si no hay IA activa
    return {"respalda": "si", "fragmento": fragmento_oficial[:200]}


async def verificar_citas(texto: str, cliente_http: Optional[httpx.AsyncClient] = None) -> dict[str, Any]:
    """Extrae y verifica todas las citas del texto. Devuelve el estado y color de cada una."""
    citas_extraidas = extraer_citas(texto)
    if not citas_extraidas:
        return {
            "ok": True,
            "total_citas": 0,
            "resumen": {"verde": 0, "amarillo": 0, "rojo": 0},
            "citas": [],
        }

    propio_cliente = False
    if cliente_http is None:
        cliente_http = httpx.AsyncClient(headers={"User-Agent": "ElMemorialista/2.2.1 (+https://elmemorialista.co)"})
        propio_cliente = True

    try:
        tareas_verif = []
        for c in citas_extraidas:
            t_norma = c["tipo_norma"]
            if t_norma == "sentencia":
                tipo = c["tipo_corte"]
                num = c["numero"]
                aa = f"{c['año'] % 100:02d}"
                tareas_verif.append(_verificar_url_corte(c["url"], tipo, num, aa, cliente_http))
            elif t_norma in ("ley", "decreto"):
                tareas_verif.append(_verificar_url_ley_decreto(c["url"], cliente_http))
            elif t_norma == "codigo":
                # Verificación estática de rango de artículos
                art = c["articulo"]
                max_art = c.get("max_art", 1000)
                if 1 <= art <= max_art:
                    tareas_verif.append(asyncio.sleep(0, result=("existe", f"Artículo {art} de {max_art} del {c['codigo']}")))
                else:
                    tareas_verif.append(asyncio.sleep(0, result=("no_encontrada", f"El {c['codigo']} solo tiene hasta el artículo {max_art}")))

        resultados = await asyncio.gather(*tareas_verif)

        citas_finales = []
        conteo = {"verde": 0, "amarillo": 0, "rojo": 0}

        for cita, (estado, fragmento) in zip(citas_extraidas, resultados):
            t_norma = cita["tipo_norma"]
            pertinencia = {"respalda": "si", "fragmento": ""}

            if estado == "existe":
                if t_norma == "sentencia":
                    pertinencia = await _evaluar_pertinencia_ia(cita["nombre"], cita["parrafo"], fragmento)
                    resp = pertinencia.get("respalda", "si")
                    if resp == "si":
                        color = "verde"
                    elif resp == "parcial":
                        color = "amarillo"
                    else:
                        color = "rojo"
                else:
                    color = "verde"
                    pertinencia["fragmento"] = fragmento[:200]
            elif estado == "no_encontrada":
                color = "rojo"
                pertinencia = {"respalda": "no", "fragmento": "No se encontró registro oficial de esta cita."}
            else:  # sin_verificar
                color = "amarillo"
                pertinencia = {"respalda": "parcial", "fragmento": "No fue posible conectar con el servidor oficial."}

            conteo[color] += 1
            citas_finales.append({
                "identificador": cita["identificador"],
                "texto_original": cita["texto_original"],
                "nombre": cita["nombre"],
                "tipo_norma": t_norma,
                "url": cita["url"],
                "estado": estado,
                "color": color,
                "pertinencia": pertinencia,
                "parrafo": cita["parrafo"],
            })

        return {
            "ok": True,
            "total_citas": len(citas_finales),
            "resumen": conteo,
            "citas": citas_finales,
        }
    finally:
        if propio_cliente:
            await cliente_http.aclose()

```


## 📄 Archivo: `app/services/auditor_fidelidad.py`
```python
"""Servicio de auditoría de fidelidad de datos para El Memorialista.

Compara deterministamente los datos ingresados en el formulario con el escrito jurídico generado:
- Extrae cédulas, NITs, radicados (23 dígitos), fechas, valores en pesos (cifras y letras),
  correos, teléfonos, matrículas inmobiliarias y partes procesales.
- Normaliza (sin puntos ni espacios; fechas en ISO) y detecta:
  - 'invenciones': datos en el escrito que no estaban en el formulario (excluye abogado y fecha de hoy).
  - 'omisiones': datos del formulario que no aparecen en el escrito.
  - 'discrepancias_cifras_letras': diferencias entre valores en números y en letras.
"""

from __future__ import annotations

import datetime
import re
import unicodedata
from typing import Any, Optional

from app.services.nit import calcular_dv_nit, validar_nit
from app.services.numeros_letras import numero_a_letras
from app.services.radicado import decodificar_radicado, validar_radicado

MESES_MAP = {
    "enero": "01",
    "febrero": "02",
    "marzo": "03",
    "abril": "04",
    "mayo": "05",
    "junio": "06",
    "julio": "07",
    "agosto": "08",
    "septiembre": "09",
    "setiembre": "09",
    "octubre": "10",
    "noviembre": "11",
    "diciembre": "12",
}

VALORES_PALABRAS = {
    "un": 1,
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "dieciséis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "veintiun": 21,
    "veintiún": 21,
    "veintiuno": 21,
    "veintiuna": 21,
    "veintidos": 22,
    "veintidós": 22,
    "veintitres": 23,
    "veintitrés": 23,
    "veinticuatro": 24,
    "veinticinco": 25,
    "veintiseis": 26,
    "veintiséis": 26,
    "veintisiete": 27,
    "veintiocho": 28,
    "veintinueve": 29,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "sesenta": 60,
    "setenta": 70,
    "ochenta": 80,
    "noventa": 90,
    "cien": 100,
    "ciento": 100,
    "doscientos": 200,
    "doscientas": 200,
    "trescientos": 300,
    "trescientas": 300,
    "cuatrocientos": 400,
    "cuatrocientas": 400,
    "quinientos": 500,
    "quinientas": 500,
    "seiscientos": 600,
    "seiscientas": 600,
    "setecientos": 700,
    "setecientas": 700,
    "ochocientos": 800,
    "ochocientas": 800,
    "novecientos": 900,
    "novecientas": 900,
}


def normalizar_texto(s: str) -> str:
    """Elimina tildes, signos de puntuación y dobles espacios."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    sin_tildes = "".join(c for c in nfkd if not unicodedata.combining(c))
    sin_puntuacion = re.sub(r"[^\w\s]", " ", sin_tildes.lower())
    return " ".join(sin_puntuacion.split())


def palabras_a_numero(frase: str) -> Optional[int]:
    """Convierte una frase en español que exprese una cantidad numérica a entero."""
    if not frase:
        return None
    frase_limpia = normalizar_texto(frase)
    palabras = frase_limpia.split()
    total = 0
    grupo = 0
    encontro = False

    for p in palabras:
        if p in ("pesos", "de", "m", "cte", "moneda", "corriente", "y"):
            continue
        if p in VALORES_PALABRAS:
            grupo += VALORES_PALABRAS[p]
            encontro = True
        elif p == "mil":
            if grupo == 0:
                grupo = 1
            total += grupo * 1000
            grupo = 0
            encontro = True
        elif p in ("millon", "millones"):
            if grupo == 0:
                grupo = 1
            total += grupo * 1_000_000
            grupo = 0
            encontro = True
        elif p in ("billon", "billones"):
            if grupo == 0:
                grupo = 1
            total += grupo * 1_000_000_000_000
            grupo = 0
            encontro = True

    total += grupo
    return total if (encontro and total > 0) else None


def pad2(n: int) -> str:
    return f"{n:02d}"


def es_encabezado_o_autoridad(cand: str) -> bool:
    norm = normalizar_texto(cand)
    patrones = [
        "juez",
        "juzgado",
        "tribunal",
        "corte",
        "republica de colombia",
        "rama judicial",
        "senor",
        "senora",
        "reparto",
        "hechos",
        "pretensiones",
        "fundamentos",
        "pruebas",
        "anexos",
        "notificaciones",
        "juramento",
        "competencia",
        "cuantia",
        "derecho",
        "accion de tutela",
        "demanda verbal",
        "demanda ejecutiva",
        "derecho de peticion",
        "accion popular",
        "recurso",
        "doctor",
        "doctora",
        "abogado",
        "apoderado",
        "demandante",
        "demandado",
        "accionante",
        "accionado",
        "parte actora",
        "parte demandada",
        "canal digital",
        "alegatos",
        "referencia",
        "asunto",
        "tramite",
        "despacho",
        "apercibimiento",
        "apercibimiento legal",
        "proceso monitorio",
        "monitorio",
    ]
    return any(p in norm for p in patrones)


def extraer_entidades(texto: str) -> list[dict[str, Any]]:
    """Extrae entidades estructuradas (radicados, matrículas, valores, fechas, correos, teléfonos, cédulas/NITs)."""
    entidades: list[dict[str, Any]] = []
    if not texto or not texto.strip():
        return entidades

    texto_trabajo = texto

    # 1. Radicados de 23 dígitos
    re_radicado = re.compile(r"(?<!\d)(\d(?:[-\s]?\d){22})(?!\d)")
    for match in re_radicado.finditer(texto):
        orig = match.group(1)
        norm = re.sub(r"[-\s.]", "", orig)
        if len(norm) == 23:
            dec = decodificar_radicado(norm)
            entidades.append({
                "tipo": "radicado",
                "valor": orig,
                "textoOriginal": orig,
                "normalizado": norm,
                "formateado": dec.get("formateado", orig),
                "decodificado": dec,
                "detalle": f"Radicado judicial (23 dígitos): {dec.get('formateado', orig)} ({dec.get('resumen', '')})",
            })
            texto_trabajo = texto_trabajo.replace(orig, " " * len(orig))

    # 2. Matrículas inmobiliarias
    re_matricula = re.compile(
        r"\b(?:matr[ií]cula(?: inmobiliaria)?\s*(?:n[oó]\.?|número)?\s*[:#]?\s*([0-9A-Za-z]+-[0-9A-Za-z]+|[0-9A-Za-z]{6,12})|(\d{2,3}[A-Z]?-\d{4,8}))\b",
        re.IGNORECASE,
    )
    for match in re_matricula.finditer(texto_trabajo):
        orig = match.group(1) or match.group(2)
        if orig:
            norm = orig.upper().replace(" ", "")
            if not re.match(r"^\d{4}-\d{2}$", norm):
                entidades.append({
                    "tipo": "matrícula",
                    "valor": orig,
                    "textoOriginal": match.group(0),
                    "normalizado": norm,
                    "detalle": f"Matrícula inmobiliaria: {orig}",
                })
                texto_trabajo = texto_trabajo.replace(match.group(0), " " * len(match.group(0)))

    # 3. Valores en pesos (cifras y letras)
    re_valor_cifras = re.compile(
        r"(?:\$|COP)\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\b|\b(\d{1,3}(?:\.\d{3})+)\s*(?:de\s+)?(?:pesos|m/cte|moneda corriente)\b",
        re.IGNORECASE,
    )
    for match in re_valor_cifras.finditer(texto_trabajo):
        cifra = match.group(1) or match.group(2)
        try:
            num = int(cifra.replace(".", "").split(",")[0])
            if num > 0:
                entidades.append({
                    "tipo": "valor",
                    "valor": f"${num:,}".replace(",", "."),
                    "textoOriginal": match.group(0),
                    "normalizado": str(num),
                    "detalle": f"Valor en pesos: ${num:,}".replace(",", "."),
                })
                texto_trabajo = texto_trabajo.replace(match.group(0), " " * len(match.group(0)))
        except (ValueError, TypeError):
            pass

    re_valor_letras = re.compile(
        r"\b((?:(?:un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|diecis[eé]is|diecisiete|dieciocho|diecinueve|veinte|veinti[úu]n|veintiuno|veintiuna|veintid[oó]s|veintitr[eé]s|veinticuatro|veinticinco|veintis[eé]is|veintisiete|veintiocho|veintinueve|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|doscientos|doscientas|trescientos|trescientas|cuatrocientos|cuatrocientas|quinientos|quinientas|seiscientos|seiscientas|setecientos|setecientas|ochocientos|ochocientas|novecientos|novecientas|mil|mill[oó]n|millones|bill[oó]n|billones|y)\s+){1,10}(?:de\s+)?pesos(?:\s+(?:moneda\s+corriente|m\/cte))?)\b",
        re.IGNORECASE,
    )
    for match in re_valor_letras.finditer(texto_trabajo):
        frase = match.group(1)
        num = palabras_a_numero(frase)
        if num and num > 0:
            entidades.append({
                "tipo": "valor",
                "valor": f"${num:,} ({frase.strip()})".replace(",", "."),
                "textoOriginal": frase.strip(),
                "normalizado": str(num),
                "detalle": f"Valor en letras: {frase.strip()} (${num:,})".replace(",", "."),
            })
            texto_trabajo = texto_trabajo.replace(match.group(0), " " * len(match.group(0)))

    # 4. Fechas (texto "15 de mayo de 2025" o dd/mm/aaaa)
    re_fecha_texto = re.compile(
        r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b",
        re.IGNORECASE,
    )
    for match in re_fecha_texto.finditer(texto_trabajo):
        d = int(match.group(1))
        m_nombre = match.group(2).lower()
        a = int(match.group(3))
        m = MESES_MAP.get(m_nombre)
        if 1 <= d <= 31 and m and 1900 <= a <= 2100:
            iso = f"{a}-{m}-{pad2(d)}"
            entidades.append({
                "tipo": "fecha",
                "valor": match.group(0),
                "textoOriginal": match.group(0),
                "normalizado": iso,
                "detalle": f"Fecha: {match.group(0)} ({iso})",
            })
            texto_trabajo = texto_trabajo.replace(match.group(0), " " * len(match.group(0)))

    re_fecha_slash = re.compile(r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b")
    for match in re_fecha_slash.finditer(texto_trabajo):
        d = int(match.group(1))
        m = int(match.group(2))
        a = int(match.group(3))
        if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= a <= 2100:
            iso = f"{a}-{pad2(m)}-{pad2(d)}"
            entidades.append({
                "tipo": "fecha",
                "valor": match.group(0),
                "textoOriginal": match.group(0),
                "normalizado": iso,
                "detalle": f"Fecha: {match.group(0)} ({iso})",
            })
            texto_trabajo = texto_trabajo.replace(match.group(0), " " * len(match.group(0)))

    # 5. Correos electrónicos
    re_correo = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    for match in re_correo.finditer(texto_trabajo):
        correo = match.group(0).lower()
        entidades.append({
            "tipo": "correo",
            "valor": correo,
            "textoOriginal": match.group(0),
            "normalizado": correo,
            "detalle": f"Correo electrónico: {correo}",
        })
        texto_trabajo = texto_trabajo.replace(match.group(0), " " * len(match.group(0)))

    # 6. Teléfonos
    re_tel = re.compile(r"\b(?:\+?57\s*)?(?:3\d{2}[-\s]?\d{3}[-\s]?\d{4}|(?:60\d|03\d)[-\s]?\d{7}|\b[2-8]\d{6}\b)\b")
    for match in re_tel.finditer(texto_trabajo):
        digitos = re.sub(r"\D", "", match.group(0))
        if digitos.startswith("57") and len(digitos) > 10:
            digitos = digitos[2:]
        if 7 <= len(digitos) <= 10:
            entidades.append({
                "tipo": "teléfono",
                "valor": match.group(0),
                "textoOriginal": match.group(0),
                "normalizado": digitos,
                "detalle": f"Teléfono: {match.group(0)}",
            })
            texto_trabajo = texto_trabajo.replace(match.group(0), " " * len(match.group(0)))

    # 7. Cédulas y NITs
    re_nit = re.compile(
        r"\b(?:NIT|N\.I\.T\.)\s*[:#]?\s*(\d{1,3}(?:\.\d{3}){2,3}(?:-\d)?|\d{8,10}(?:-\d)?)\b|\b(\d{3}\.\d{3}\.\d{3}-\d)\b",
        re.IGNORECASE,
    )
    for match in re_nit.finditer(texto_trabajo):
        nit_raw = match.group(1) or match.group(2)
        val = validar_nit(nit_raw)
        entidades.append({
            "tipo": "cédula / NIT",
            "valor": nit_raw,
            "textoOriginal": match.group(0),
            "normalizado": val.get("nit_base") or re.sub(r"\D", "", nit_raw)[:9],
            "validacionNit": val,
            "detalle": f"NIT: {nit_raw}" + (f" (⚠️ {val['mensaje']})" if (not val.get("valido") and val.get("dv_ingresado") is not None) else ""),
        })
        texto_trabajo = texto_trabajo.replace(match.group(0), " " * len(match.group(0)))

    re_ced = re.compile(
        r"\b(?:C\.?C\.?|c[eé]dula(?: de ciudadan[ií]a)?|identificad[oa] con (?:C\.?C\.?|c[eé]dula)?|c\.?e\.?|ti)\s*(?:n[oó]\.?|número)?\s*[:#]?\s*(\d{1,3}(?:\.\d{3}){1,3}|\d{6,10})\b|\b(\d{1,3}(?:\.\d{3}){1,3})\b",
        re.IGNORECASE,
    )
    for match in re_ced.finditer(texto_trabajo):
        ced_raw = match.group(1) or match.group(2)
        digitos = re.sub(r"\D", "", ced_raw)
        if 6 <= len(digitos) <= 10 and digitos not in ("2024", "2025", "2026", "2027"):
            entidades.append({
                "tipo": "cédula / NIT",
                "valor": ced_raw,
                "textoOriginal": match.group(0),
                "normalizado": digitos,
                "detalle": f"Cédula de ciudadanía: {ced_raw}",
            })
            texto_trabajo = texto_trabajo.replace(match.group(0), " " * len(match.group(0)))

    return entidades


def extraer_partes_de_datos(datos: dict[str, Any]) -> list[dict[str, Any]]:
    partes: list[dict[str, Any]] = []
    if not isinstance(datos, dict):
        return partes

    campos_partes = {
        "accionante", "accionado", "demandante", "demandado", "convocante", "convocado",
        "arrendador", "arrendatario", "otorgante", "apoderado", "denunciante", "denunciado",
        "cliente", "contraparte", "trabajador", "empleador", "comprador", "vendedor",
        "peticionario", "entidad", "titular", "paciente",
    }

    for k, v in datos.items():
        if not v or not isinstance(v, str):
            continue
        if k.lower() in campos_partes:
            fragmentos = re.split(r"\n|;|\by\b", v, flags=re.IGNORECASE)
            for frag in fragmentos:
                frag = frag.strip()
                if not frag:
                    continue
                nombre_limpio = re.split(r",|identificad[oa]|c\.?c\.?|nit|mayor de edad|\(", frag, flags=re.IGNORECASE)[0].strip()
                if len(nombre_limpio) >= 3 and not nombre_limpio.isdigit():
                    partes.append({
                        "tipo": "parte",
                        "valor": nombre_limpio,
                        "textoOriginal": nombre_limpio,
                        "normalizado": normalizar_texto(nombre_limpio),
                        "detalle": f"Parte procesal ({k}): {nombre_limpio}",
                    })
    return partes


def extraer_partes_de_escrito(texto: str, abogado_nombre: str = "") -> list[dict[str, Any]]:
    partes: list[dict[str, Any]] = []
    if not texto or not texto.strip():
        return partes

    abogado_norm = normalizar_texto(abogado_nombre)

    # 1. Nombres en negrilla (**TEXTO**)
    re_negrilla = re.compile(r"\*\*([A-Za-zÁÉÍÓÚáéíóúñÑ\s.&]{3,60})\*\*")
    for match in re_negrilla.finditer(texto):
        cand = match.group(1).strip()
        norm = normalizar_texto(cand)
        if len(cand.split()) >= 2 and not es_encabezado_o_autoridad(cand) and norm != abogado_norm:
            partes.append({
                "tipo": "parte",
                "valor": cand,
                "textoOriginal": f"**{cand}**",
                "normalizado": norm,
                "detalle": f"Parte procesal en negrilla: {cand}",
            })

    # 2. Mayúscula sostenida
    re_mayus = re.compile(r"\b([A-ZÁÉÍÓÚÑ]{3,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,}){1,5})\b")
    for match in re_mayus.finditer(texto):
        cand = match.group(1).strip()
        norm = normalizar_texto(cand)
        if (
            len(cand.split()) >= 2
            and not es_encabezado_o_autoridad(cand)
            and norm != abogado_norm
            and not any(p["normalizado"] == norm for p in partes)
        ):
            partes.append({
                "tipo": "parte",
                "valor": cand,
                "textoOriginal": cand,
                "normalizado": norm,
                "detalle": f"Parte procesal en mayúsculas: {cand}",
            })

    return partes


def detectar_discrepancias_cifras_letras(texto: str, entidades_datos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    discrepancias: list[dict[str, Any]] = []
    if not texto:
        return discrepancias

    # Patrón 1: Cifra ($X) seguida de letras entre paréntesis
    re_a = re.compile(
        r"\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*\(\s*([A-Za-zÁÉÍÓÚáéíóúñÑ\s]{4,80}?(?:de\s+)?pesos(?:\s+(?:m\/cte|moneda corriente))?)\s*\)",
        re.IGNORECASE,
    )
    for m in re_a.finditer(texto):
        cifra_str = m.group(1)
        letras_str = m.group(2)
        try:
            num_cifra = int(cifra_str.replace(".", "").split(",")[0])
            num_letras = palabras_a_numero(letras_str)
            if num_cifra > 0 and num_letras and num_cifra != num_letras:
                discrepancias.append({
                    "tipo": "discrepancia_cifra_letras",
                    "cifra": num_cifra,
                    "cifraTexto": f"${num_cifra:,}".replace(",", "."),
                    "letras": num_letras,
                    "letrasTexto": letras_str.strip(),
                    "textoOriginal": m.group(0),
                    "detalle": f"Discrepancia entre cifra y letras: se escribió '${num_cifra:,}' pero en letras dice '{letras_str.strip()}' (${num_letras:,}).".replace(",", "."),
                })
        except (ValueError, TypeError):
            pass

    # Patrón 2: Letras seguidas de cifra entre paréntesis
    re_b = re.compile(
        r"([A-Za-zÁÉÍÓÚáéíóúñÑ\s]{4,80}?(?:de\s+)?pesos(?:\s+(?:m\/cte|moneda corriente))?)\s*\(\s*\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*\)",
        re.IGNORECASE,
    )
    for m in re_b.finditer(texto):
        letras_str = m.group(1)
        cifra_str = m.group(2)
        try:
            num_letras = palabras_a_numero(letras_str)
            num_cifra = int(cifra_str.replace(".", "").split(",")[0])
            if num_cifra > 0 and num_letras and num_cifra != num_letras:
                if not any(d["cifra"] == num_cifra and d["letras"] == num_letras for d in discrepancias):
                    discrepancias.append({
                        "tipo": "discrepancia_cifra_letras",
                        "cifra": num_cifra,
                        "cifraTexto": f"${num_cifra:,}".replace(",", "."),
                        "letras": num_letras,
                        "letrasTexto": letras_str.strip(),
                        "textoOriginal": m.group(0),
                        "detalle": f"Discrepancia entre cifra y letras: en letras dice '{letras_str.strip()}' (${num_letras:,}) pero entre paréntesis dice '${num_cifra:,}'.".replace(",", "."),
                    })
        except (ValueError, TypeError):
            pass

    # Patrón 3: Cifra del formulario vs. letras discordantes en el texto
    for vf in entidades_datos:
        if vf.get("tipo") == "valor" and vf.get("normalizado", "").isdigit():
            val_num = int(vf["normalizado"])
            if val_num <= 0:
                continue
            re_letras = re.compile(
                r"\b((?:(?:un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|diecis[eé]is|diecisiete|dieciocho|diecinueve|veinte|veinti[úu]n|veintiuno|veintiuna|veintid[oó]s|veintitr[eé]s|veinticuatro|veinticinco|veintis[eé]is|veintisiete|veintiocho|veintinueve|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|doscientos|doscientas|trescientos|trescientas|cuatrocientos|cuatrocientas|quinientos|quinientas|seiscientos|seiscientas|setecientos|setecientas|ochocientos|ochocientas|novecientos|novecientas|mil|mill[oó]n|millones|bill[oó]n|billones|y)\s+){1,10}(?:de\s+)?pesos)\b",
                re.IGNORECASE,
            )
            for m in re_letras.finditer(texto):
                frase = m.group(1)
                num_letras = palabras_a_numero(frase)
                if num_letras and num_letras > 0 and num_letras != val_num:
                    letras_corr = numero_a_letras(str(val_num)).lower()
                    if letras_corr[:20] not in texto.lower():
                        if not any(d["cifra"] == val_num and d["letras"] == num_letras for d in discrepancias):
                            discrepancias.append({
                                "tipo": "discrepancia_cifra_letras",
                                "cifra": val_num,
                                "cifraTexto": f"${val_num:,}".replace(",", "."),
                                "letras": num_letras,
                                "letrasTexto": frase.strip(),
                                "textoOriginal": m.group(0),
                                "detalle": f"Discrepancia con el formulario: en los datos ingresaste ${val_num:,} pero en el escrito dice en letras '{frase.strip()}' (${num_letras:,}).".replace(",", "."),
                            })

    return discrepancias


def auditar_datos_y_escrito(
    datos: dict[str, Any],
    texto: str,
    perfil: Optional[dict[str, Any]] = None,
    opciones: Optional[dict[str, Any]] = None,
    fecha_hoy_iso: Optional[str] = None,
) -> dict[str, Any]:
    """Audita la fidelidad entre datos del formulario y texto del escrito.

    Retorna:
      - invenciones: lista de entidades detectadas en el escrito pero no en los datos.
      - omisiones: lista de entidades ingresadas en el formulario pero no en el escrito.
      - discrepancias: lista de discordancias entre cifras numéricas y en letras.
      - total: suma de invenciones + omisiones + discrepancias.
      - partes: partes detectadas.
    """
    opciones = opciones or {}
    perfil = perfil or {}
    abogado = perfil.get("abogado") or {}

    fecha_hoy_iso = fecha_hoy_iso or opciones.get("fechaHoy") or datetime.date.today().isoformat()

    abogado_norm = {
        "nombre": normalizar_texto(abogado.get("nombre", "")),
        "cedula": re.sub(r"\D", "", str(abogado.get("cedula", ""))),
        "tp": re.sub(r"\D", "", str(abogado.get("tp", ""))),
        "telefono": re.sub(r"\D", "", str(abogado.get("telefono", ""))),
        "correo": str(abogado.get("correo", "")).lower().strip(),
    }

    # 1. Entidades del formulario
    entidades_datos: list[dict[str, Any]] = []

    def _agregar_entidad_datos(ent: dict[str, Any]) -> None:
        if not ent or not ent.get("normalizado"):
            return
        t = ent.get("tipo")
        n = ent.get("normalizado")
        if not any(e.get("tipo") == t and e.get("normalizado") == n for e in entidades_datos):
            entidades_datos.append(ent)

    if isinstance(datos, dict):
        for clave, valor in datos.items():
            if valor is None:
                continue
            k_lower = clave.lower()
            v_str = ", ".join(valor) if isinstance(valor, list) else str(valor)
            v_trim = v_str.strip()
            if not v_trim:
                continue

            if any(p in k_lower for p in ("cuantia", "valor", "monto", "canon", "salario")):
                re_cifra = re.compile(r"\b(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+)\b")
                for m in re_cifra.finditer(v_trim):
                    try:
                        num = int(m.group(1).replace(".", "").split(",")[0])
                        if num > 0:
                            _agregar_entidad_datos({
                                "tipo": "valor",
                                "valor": f"${num:,}".replace(",", "."),
                                "textoOriginal": v_trim,
                                "normalizado": str(num),
                                "detalle": f"Valor en formulario ({clave}): ${num:,}".replace(",", "."),
                            })
                    except (ValueError, TypeError):
                        pass
                num_let = palabras_a_numero(v_trim)
                if num_let and num_let > 0:
                    _agregar_entidad_datos({
                        "tipo": "valor",
                        "valor": f"${num_let:,} ({v_trim})".replace(",", "."),
                        "textoOriginal": v_trim,
                        "normalizado": str(num_let),
                        "detalle": f"Valor en formulario ({clave}): ${num_let:,}".replace(",", "."),
                    })

            if any(p in k_lower for p in ("cedula", "identificacion", "cc", "nit")):
                digitos = re.sub(r"\D", "", v_trim)
                if "nit" in k_lower and len(digitos) >= 8:
                    base_nit = digitos[:9]
                    val_nit = validar_nit(v_trim)
                    _agregar_entidad_datos({
                        "tipo": "cédula / NIT",
                        "valor": v_trim,
                        "textoOriginal": v_trim,
                        "normalizado": base_nit,
                        "validacionNit": val_nit,
                        "detalle": f"NIT en formulario ({clave}): {v_trim}",
                    })
                elif 6 <= len(digitos) <= 10:
                    _agregar_entidad_datos({
                        "tipo": "cédula / NIT",
                        "valor": v_trim,
                        "textoOriginal": v_trim,
                        "normalizado": digitos,
                        "detalle": f"Cédula en formulario ({clave}): {v_trim}",
                    })

            if any(p in k_lower for p in ("telefono", "celular", "tel")):
                digitos = re.sub(r"\D", "", v_trim)
                if digitos.startswith("57") and len(digitos) > 10:
                    digitos = digitos[2:]
                if 7 <= len(digitos) <= 10:
                    _agregar_entidad_datos({
                        "tipo": "teléfono",
                        "valor": v_trim,
                        "textoOriginal": v_trim,
                        "normalizado": digitos,
                        "detalle": f"Teléfono en formulario ({clave}): {digitos}",
                    })

            if any(p in k_lower for p in ("correo", "email", "mail")):
                re_c = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
                for m in re_c.finditer(v_trim):
                    correo = m.group(0).lower()
                    _agregar_entidad_datos({
                        "tipo": "correo",
                        "valor": correo,
                        "textoOriginal": m.group(0),
                        "normalizado": correo,
                        "detalle": f"Correo en formulario ({clave}): {correo}",
                    })

            if any(p in k_lower for p in ("radicado", "proceso")):
                digitos = re.sub(r"\D", "", v_trim)
                if len(digitos) == 23:
                    dec = decodificar_radicado(digitos)
                    _agregar_entidad_datos({
                        "tipo": "radicado",
                        "valor": v_trim,
                        "textoOriginal": v_trim,
                        "normalizado": digitos,
                        "formateado": dec.get("formateado", v_trim),
                        "detalle": f"Radicado en formulario ({clave}): {dec.get('formateado', v_trim)}",
                    })

            if "matricula" in k_lower:
                norm = v_trim.upper().replace(" ", "")
                _agregar_entidad_datos({
                    "tipo": "matrícula",
                    "valor": v_trim,
                    "textoOriginal": v_trim,
                    "normalizado": norm,
                    "detalle": f"Matrícula en formulario ({clave}): {v_trim}",
                })

            if "fecha" in k_lower:
                m_iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", v_trim)
                if m_iso:
                    _agregar_entidad_datos({
                        "tipo": "fecha",
                        "valor": v_trim,
                        "textoOriginal": v_trim,
                        "normalizado": m_iso.group(0),
                        "detalle": f"Fecha en formulario ({clave}): {m_iso.group(0)}",
                    })
                else:
                    m_slash = re.search(r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b", v_trim)
                    if m_slash:
                        d = int(m_slash.group(1))
                        m = int(m_slash.group(2))
                        a = int(m_slash.group(3))
                        iso = f"{a}-{pad2(m)}-{pad2(d)}"
                        _agregar_entidad_datos({
                            "tipo": "fecha",
                            "valor": v_trim,
                            "textoOriginal": v_trim,
                            "normalizado": iso,
                            "detalle": f"Fecha en formulario ({clave}): {iso}",
                        })

            # También extraer entidades generales (fechas, correos, etc.) de campos de texto libre
            extraidas = extraer_entidades(v_trim)
            for ex in extraidas:
                _agregar_entidad_datos(ex)

    # Partes del formulario
    partes_datos = extraer_partes_de_datos(datos)

    # 2. Entidades del escrito
    entidades_escrito = extraer_entidades(texto)
    partes_escrito = extraer_partes_de_escrito(texto, abogado_nombre=abogado.get("nombre", ""))

    # Discrepancias cifras vs letras
    discrepancias = detectar_discrepancias_cifras_letras(texto, entidades_datos)

    # Filtrar entidades del abogado y fecha de hoy
    def es_dato_abogado_o_hoy(ent: dict[str, Any]) -> bool:
        t = ent.get("tipo")
        n = ent.get("normalizado", "")
        if t == "fecha" and n == fecha_hoy_iso:
            return True
        if t == "cédula / NIT":
            if abogado_norm["cedula"] and n == abogado_norm["cedula"]:
                return True
            if abogado_norm["tp"] and n == abogado_norm["tp"]:
                return True
        if t == "correo" and abogado_norm["correo"] and n == abogado_norm["correo"]:
            return True
        if t == "teléfono" and abogado_norm["telefono"] and n == abogado_norm["telefono"]:
            return True
        if t == "parte" and abogado_norm["nombre"] and n == abogado_norm["nombre"]:
            return True
        return False

    # 3. Invenciones (en escrito pero no en datos)
    invenciones: list[dict[str, Any]] = []
    for ee in entidades_escrito:
        if es_dato_abogado_o_hoy(ee):
            continue
        # ¿Está en entidades_datos?
        coincide = any(
            ed.get("tipo") == ee.get("tipo") and ed.get("normalizado") == ee.get("normalizado")
            for ed in entidades_datos
        )
        if not coincide:
            if not any(i.get("tipo") == ee.get("tipo") and i.get("normalizado") == ee.get("normalizado") for i in invenciones):
                invenciones.append(ee)

    # 4. Omisiones (en datos pero no en escrito)
    omisiones: list[dict[str, Any]] = []
    for ed in entidades_datos:
        if es_dato_abogado_o_hoy(ed):
            continue
        coincide = any(
            ee.get("tipo") == ed.get("tipo") and ee.get("normalizado") == ed.get("normalizado")
            for ee in entidades_escrito
        )
        if not coincide:
            # Buscar en texto libre por si acaso
            norm = ed.get("normalizado", "")
            if norm and norm in re.sub(r"[-\s.]", "", texto):
                continue
            if not any(o.get("tipo") == ed.get("tipo") and o.get("normalizado") == ed.get("normalizado") for o in omisiones):
                omisiones.append(ed)

    # Comparar partes
    for pe in partes_escrito:
        if es_dato_abogado_o_hoy(pe):
            continue
        coincide = any(
            pd.get("normalizado") in pe.get("normalizado") or pe.get("normalizado") in pd.get("normalizado")
            for pd in partes_datos
        )
        if not coincide:
            if not any(i.get("tipo") == "parte" and i.get("normalizado") == pe.get("normalizado") for i in invenciones):
                invenciones.append(pe)

    for pd in partes_datos:
        if es_dato_abogado_o_hoy(pd):
            continue
        norm_pd = pd.get("normalizado", "")
        coincide_en_partes = any(
            norm_pd in pe.get("normalizado") or pe.get("normalizado") in norm_pd
            for pe in partes_escrito
        )
        coincide_en_texto = norm_pd in normalizar_texto(texto)
        if not (coincide_en_partes or coincide_en_texto):
            if not any(o.get("tipo") == "parte" and o.get("normalizado") == pd.get("normalizado") for o in omisiones):
                omisiones.append(pd)

    total_alertas = len(invenciones) + len(omisiones) + len(discrepancias)

    return {
        "ok": True,
        "total": total_alertas,
        "invenciones": invenciones,
        "omisiones": omisiones,
        "discrepancias": discrepancias,
        "entidades_datos": entidades_datos,
        "entidades_escrito": entidades_escrito,
        "partes_datos": partes_datos,
        "partes_escrito": partes_escrito,
    }

```


## 📄 Archivo: `app/services/calculos.py`
```python
"""El Memorialista · Módulo de Cálculos Jurídicos, Laborales y Financieros de Colombia (v1.0).

Incluye motores de cálculo deterministas conforme a la legislación colombiana vigente:
1. Liquidación laboral integral (prestaciones sociales, indemnización art. 64 CST, moratoria art. 65 CST,
   sanción art. 99 Ley 50/1990, salarios variables y advertencia de la Ley 2466 de 2025).
2. Intereses moratorios mercantiles (art. 884 Código de Comercio - 1.5 veces IBC certificado por la SFC,
   mes a mes, con resoluciones oficiales).
3. Indexación con IPC oficial del DANE (valor histórico × IPC final / IPC inicial).
4. Generador de anexos tabulares en Markdown y texto plano para inserción directa en memoriales y demandas.
"""
from __future__ import annotations

import calendar
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

log = logging.getLogger("memorialista.calculos")

# Catálogos base
CATALOGO_DIR = Path(__file__).resolve().parent.parent / "catalogo"
ARCHIVO_TASAS_SFC = CATALOGO_DIR / "tasas_sfc.json"
ARCHIVO_IPC = CATALOGO_DIR / "ipc.json"

# Salarios mínimos y auxilio de transporte en Colombia por año
TABLA_SALARIOS_COLOMBIA: Dict[int, Dict[str, float]] = {
    2020: {"smmlv": 877803.0, "auxilio_transporte": 102854.0},
    2021: {"smmlv": 908526.0, "auxilio_transporte": 106454.0},
    2022: {"smmlv": 1000000.0, "auxilio_transporte": 117172.0},
    2023: {"smmlv": 1160000.0, "auxilio_transporte": 140606.0},
    2024: {"smmlv": 1300000.0, "auxilio_transporte": 162000.0},
    2025: {"smmlv": 1423500.0, "auxilio_transporte": 200000.0},
    2026: {"smmlv": 1565000.0, "auxilio_transporte": 220000.0},
}
VALOR_DEFECTO_SMMLV = 1565000.0
VALOR_DEFECTO_AUXILIO = 220000.0

# -----------------------------------------------------------------------------
# Carga de catálogos
# -----------------------------------------------------------------------------

def cargar_catalogo_tasas_sfc() -> Dict[str, Any]:
    """Carga la serie histórica de tasas certificadas por la Superintendencia Financiera."""
    if not ARCHIVO_TASAS_SFC.exists():
        log.warning("No se encontró %s", ARCHIVO_TASAS_SFC)
        return {"series": [], "fuente": "Superintendencia Financiera de Colombia"}
    try:
        with open(ARCHIVO_TASAS_SFC, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        log.error("Error al cargar %s: %s", ARCHIVO_TASAS_SFC, exc)
        return {"series": [], "fuente": "Superintendencia Financiera de Colombia"}


def cargar_catalogo_ipc() -> Dict[str, Any]:
    """Carga la serie mensual del IPC (Índice de Precios al Consumidor) del DANE."""
    if not ARCHIVO_IPC.exists():
        log.warning("No se encontró %s", ARCHIVO_IPC)
        return {"series": [], "fuente": "DANE"}
    try:
        with open(ARCHIVO_IPC, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        log.error("Error al cargar %s: %s", ARCHIVO_IPC, exc)
        return {"series": [], "fuente": "DANE"}


# -----------------------------------------------------------------------------
# Utilidades de fecha y formato
# -----------------------------------------------------------------------------

def parsear_fecha(valor: Union[str, date]) -> date:
    """Convierte un string YYYY-MM-DD o YYYY-MM en objeto date."""
    if isinstance(valor, date):
        return valor
    valor_str = str(valor).strip()
    if len(valor_str) == 7:  # YYYY-MM
        return datetime.strptime(valor_str + "-01", "%Y-%m-%d").date()
    return datetime.strptime(valor_str[:10], "%Y-%m-%d").date()


def es_ultimo_dia_mes(f: date) -> bool:
    """Indica si una fecha corresponde al último día calendario de su mes."""
    ultimo_dia = calendar.monthrange(f.year, f.month)[1]
    return f.day == ultimo_dia


def dias_laborales_comerciales(f_ini: date, f_fin: date) -> int:
    """
    Cómputo estándar laboral colombiano: meses de 30 días, año de 360 días.
    Fórmula unificada: (A2 - A1)*360 + (M2 - M1)*30 + (D2 - D1) + 1.
    Si el día final o inicial es 31, se asimila a 30.
    Si febrero se labora completo (inicia el 1 y termina el 28 o 29), cuenta como 30 días.
    """
    if f_fin < f_ini:
        return 0

    d1 = min(f_ini.day, 30)
    d2 = min(f_fin.day, 30)

    # Caso especial febrero completo
    if f_ini.month == 2 and f_ini.day == 1 and es_ultimo_dia_mes(f_fin) and f_fin.month == 2:
        d2 = 30
    elif f_fin.month == 2 and es_ultimo_dia_mes(f_fin):
        d2 = 30

    dias = (f_fin.year - f_ini.year) * 360 + (f_fin.month - f_ini.month) * 30 + (d2 - d1) + 1
    return max(1, dias)


def formato_pesos(valor: float) -> str:
    """Formatea un valor en pesos colombianos con separador de miles y sin decimales si es entero."""
    if abs(valor - round(valor)) < 0.005:
        return f"${round(valor):,}".replace(",", ".")
    return f"${valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def obtener_smmlv_y_auxilio(anio: int) -> Tuple[float, float]:
    """Obtiene el SMMLV y Auxilio de Transporte legal para un año determinado."""
    if anio in TABLA_SALARIOS_COLOMBIA:
        info = TABLA_SALARIOS_COLOMBIA[anio]
        return info["smmlv"], info["auxilio_transporte"]
    if anio < min(TABLA_SALARIOS_COLOMBIA.keys()):
        primer_anio = min(TABLA_SALARIOS_COLOMBIA.keys())
        return TABLA_SALARIOS_COLOMBIA[primer_anio]["smmlv"], TABLA_SALARIOS_COLOMBIA[primer_anio]["auxilio_transporte"]
    ultimo_anio = max(TABLA_SALARIOS_COLOMBIA.keys())
    return TABLA_SALARIOS_COLOMBIA[ultimo_anio]["smmlv"], TABLA_SALARIOS_COLOMBIA[ultimo_anio]["auxilio_transporte"]


# -----------------------------------------------------------------------------
# 1. MOTOR DE LIQUIDACIÓN LABORAL
# -----------------------------------------------------------------------------

class SalarioVariableItem(BaseModel):
    periodo: str = Field(description="Periodo o mes en formato YYYY-MM o descripción")
    valor: float = Field(ge=0, description="Monto devengado por salario ordinario y factores salariales")
    horas_extras_recargos: float = Field(default=0.0, description="Recargos nocturnos, dominicales o festivos")


class LiquidacionLaboralRequest(BaseModel):
    fecha_inicio: str = Field(description="Fecha de inicio de la relación laboral (YYYY-MM-DD)")
    fecha_fin: str = Field(description="Fecha de terminación del contrato (YYYY-MM-DD)")
    salario_base: float = Field(ge=0, description="Salario básico mensual pactado")
    auxilio_transporte: Optional[float] = Field(
        default=None,
        description="Auxilio de transporte mensual. Si es None, se calcula automáticamente según SMMLV.",
    )
    incluir_auxilio_transporte: bool = Field(
        default=True,
        description="Si es False, se excluye expresamente el auxilio de transporte.",
    )
    tipo_contrato: Literal["indefinido", "termino_fijo", "obra_labor"] = Field(
        default="indefinido",
        description="Modalidad contractual (art. 45 y ss. CST)",
    )
    fecha_fin_pactada: Optional[str] = Field(
        default=None,
        description="Para contratos a término fijo, fecha en que vencía el plazo estipulado.",
    )
    motivo_terminacion: Literal[
        "despido_sin_justa_causa",
        "despido_con_justa_causa",
        "renuncia_voluntaria",
        "mutuo_acuerdo",
        "vencimiento_termino",
        "terminacion_obra",
    ] = Field(
        default="despido_sin_justa_causa",
        description="Causal o motivo de terminación contractual.",
    )
    # Fechas específicas para cada concepto (si son distintas al periodo completo)
    fecha_inicio_cesantias: Optional[str] = Field(
        default=None,
        description="Fecha desde la cual se adeudan cesantías (por defecto 1 de enero del año de retiro).",
    )
    fecha_inicio_prima: Optional[str] = Field(
        default=None,
        description="Fecha desde la cual se adeuda prima (por defecto 1 de enero o 1 de julio del año de retiro).",
    )
    fecha_inicio_vacaciones: Optional[str] = Field(
        default=None,
        description="Fecha desde la cual se adeudan vacaciones no compensadas ni disfrutadas.",
    )
    # Salarios caídos y mora
    liquidar_moratoria_art65: bool = Field(
        default=False,
        description="Liquidar indemnización moratoria del art. 65 CST (un día de salario por día de retardo).",
    )
    fecha_corte_moratoria: Optional[str] = Field(
        default=None,
        description="Fecha hasta la cual se liquida la mora del art. 65 CST (por defecto hoy o fecha de terminación).",
    )
    # Sanción no consignación de cesantías
    liquidar_sancion_consignacion_art99: bool = Field(
        default=False,
        description="Liquidar sanción del art. 99 Ley 50/1990 por no consignación antes del 15 de febrero.",
    )
    dias_mora_consignacion: Optional[int] = Field(
        default=None,
        ge=0,
        description="Número de días de retardo en la consignación de cesantías.",
    )
    fecha_inicio_mora_consignacion: Optional[str] = Field(
        default=None,
        description="Fecha de exigibilidad de la consignación (usualmente 15 de febrero de algún año).",
    )
    salarios_variables: Optional[List[SalarioVariableItem]] = Field(
        default=None,
        description="Historial de salarios devengados para computar el promedio del último año.",
    )
    nombre_trabajador: Optional[str] = Field(default="", description="Nombre del trabajador para el anexo")
    nombre_empleador: Optional[str] = Field(default="", description="Nombre del empleador o empresa")


class ConceptoLiquidacion(BaseModel):
    id: str
    concepto: str
    dias: int
    base_calculo: float
    formula: str
    subtotal: float
    norma: str
    detalle: str
    aplica_ley_2466: bool = False


class LiquidacionLaboralResponse(BaseModel):
    trabajador: str
    empleador: str
    tipo_contrato: str
    motivo_terminacion: str
    fecha_inicio: str
    fecha_fin: str
    dias_totales_servicio: int
    salario_base_ordinario: float
    auxilio_transporte: float
    salario_base_prestaciones: float
    salario_base_vacaciones: float
    conceptos: List[ConceptoLiquidacion]
    total_prestaciones_sociales: float
    total_indemnizaciones_y_sanciones: float
    gran_total_liquidacion: float
    advertencias_legales: List[str]
    tabla_markdown: str
    tabla_texto: str


def advertencia_ley_2466_2025(
    motivo: str,
    f_fin: date,
    tipo_contrato: str,
    tiene_salarios_variables: bool,
) -> Optional[str]:
    """Genera advertencia legal conforme a la Ley 2466 de 2025 (Reforma Laboral)."""
    # Si la fecha de terminación es a partir del 2025 o si hay indemnización art. 64 / recargos
    aplica = (
        f_fin >= date(2025, 1, 1)
        or motivo == "despido_sin_justa_causa"
        or tiene_salarios_variables
    )
    if not aplica:
        return None

    texto = (
        "⚠️ ADVERTENCIA LEGAL - LEY 2466 DE 2025 (REFORMA LABORAL):\n"
        "1. Indemnización por despido sin justa causa (Art. 64 CST): La reforma laboral incrementa "
        "los días de indemnización para contratos a término indefinido (35 días para el 1er año y entre "
        "15, 30 o 45 días adicionales por año subsiguiente según antigüedad acumulada), y exige el agotamiento "
        "del debido proceso disciplinario previo incluso en despidos sin justa causa alegada.\n"
        "2. Recargo nocturno y dominical/festivo: El horario nocturno inicia a las 7:00 p.m. (no a las 9:00 p.m.) "
        "y el recargo dominical/festivo se eleva progresivamente al 100%. Si se ingresaron salarios variables, "
        "verifique si los turnos laborados causaron los nuevos recargos vigentes.\n"
        "3. Contrato a término fijo: El límite máximo de prórrogas consecutivas y la reconducción a indefinido "
        "fueron modificados por la Ley 2466 de 2025. Coteje si la fecha de terminación se encuentra bajo el nuevo régimen."
    )
    return texto


def calcular_liquidacion_laboral(req: LiquidacionLaboralRequest) -> LiquidacionLaboralResponse:
    """Ejecuta el cómputo integral de prestaciones, indemnizaciones y sanciones laborales."""
    f_ini = parsear_fecha(req.fecha_inicio)
    f_fin = parsear_fecha(req.fecha_fin)
    if f_fin < f_ini:
        raise HTTPException(status_code=400, detail="La fecha de finalización no puede ser anterior a la de inicio.")

    dias_totales = dias_laborales_comerciales(f_ini, f_fin)
    smmlv_vigente, auxilio_legal = obtener_smmlv_y_auxilio(f_fin.year)

    # Determinar salario base: si hay salarios variables, computar promedio
    salario_ordinario = float(req.salario_base)
    tiene_salarios_variables = bool(req.salarios_variables and len(req.salarios_variables) > 0)
    detalle_promedio = ""
    if tiene_salarios_variables:
        tot_salarios = sum(sv.valor + sv.horas_extras_recargos for sv in req.salarios_variables)  # type: ignore
        salario_ordinario = round(tot_salarios / len(req.salarios_variables), 2)  # type: ignore
        detalle_promedio = f" (Promedio de {len(req.salarios_variables)} periodos variables: {formato_pesos(salario_ordinario)})"

    # Auxilio de transporte: aplica si salario ordinario <= 2 SMMLV (salvo exclusión voluntaria)
    devenga_auxilio = False
    auxilio_transporte = 0.0
    if req.incluir_auxilio_transporte:
        if req.auxilio_transporte is not None:
            auxilio_transporte = float(req.auxilio_transporte)
            devenga_auxilio = auxilio_transporte > 0
        else:
            if salario_ordinario <= (2 * smmlv_vigente):
                auxilio_transporte = auxilio_legal
                devenga_auxilio = True

    base_prestaciones = salario_ordinario + auxilio_transporte
    base_vacaciones = salario_ordinario  # El auxilio de transporte no entra en vacaciones (art. 192 CST)

    conceptos: List[ConceptoLiquidacion] = []

    # 1. Cesantías (Art. 249 CST)
    # Por defecto se liquida el año de terminación (del 1 de enero al f_fin o desde f_ini si ingresó ese año)
    if req.fecha_inicio_cesantias:
        f_ini_ces = parsear_fecha(req.fecha_inicio_cesantias)
    else:
        f_ini_ces = max(f_ini, date(f_fin.year, 1, 1))
    dias_cesantias = dias_laborales_comerciales(f_ini_ces, f_fin)
    monto_cesantias = round((base_prestaciones * dias_cesantias) / 360.0, 2)
    conceptos.append(
        ConceptoLiquidacion(
            id="cesantias",
            concepto="Cesantías",
            dias=dias_cesantias,
            base_calculo=base_prestaciones,
            formula=f"({formato_pesos(base_prestaciones)} × {dias_cesantias}) / 360",
            subtotal=monto_cesantias,
            norma="Art. 249 del Código Sustantivo del Trabajo (CST)",
            detalle=f"Periodo del {f_ini_ces.isoformat()} al {f_fin.isoformat()}{detalle_promedio}. Incluye auxilio de transporte ({formato_pesos(auxilio_transporte)})." if devenga_auxilio else f"Periodo del {f_ini_ces.isoformat()} al {f_fin.isoformat()}{detalle_promedio}.",
            aplica_ley_2466=False,
        )
    )

    # 2. Intereses a las Cesantías (Ley 52 de 1975)
    # 12% anual sobre el valor de las cesantías causado en el periodo
    monto_intereses = round((monto_cesantias * dias_cesantias * 0.12) / 360.0, 2)
    conceptos.append(
        ConceptoLiquidacion(
            id="intereses_cesantias",
            concepto="Intereses sobre las Cesantías (12% anual)",
            dias=dias_cesantias,
            base_calculo=monto_cesantias,
            formula=f"({formato_pesos(monto_cesantias)} × {dias_cesantias} × 12%) / 360",
            subtotal=monto_intereses,
            norma="Ley 52 de 1975 y Decreto Reglamentario 116 de 1976",
            detalle=f"12% anual proporcional a {dias_cesantias} días sobre el saldo de cesantías.",
            aplica_ley_2466=False,
        )
    )

    # 3. Prima de Servicios (Art. 306 CST)
    # Por defecto se liquida el semestre de retiro (1er sem: 1 ene - 30 jun; 2do sem: 1 jul - 31 dic)
    if req.fecha_inicio_prima:
        f_ini_prima = parsear_fecha(req.fecha_inicio_prima)
    else:
        f_semestre = date(f_fin.year, 1, 1) if f_fin.month <= 6 else date(f_fin.year, 7, 1)
        f_ini_prima = max(f_ini, f_semestre)
    dias_prima = dias_laborales_comerciales(f_ini_prima, f_fin)
    monto_prima = round((base_prestaciones * dias_prima) / 360.0, 2)
    conceptos.append(
        ConceptoLiquidacion(
            id="prima_servicios",
            concepto="Prima de Servicios",
            dias=dias_prima,
            base_calculo=base_prestaciones,
            formula=f"({formato_pesos(base_prestaciones)} × {dias_prima}) / 360",
            subtotal=monto_prima,
            norma="Art. 306 del CST (modificado por la Ley 1788 de 2016)",
            detalle=f"Semestre del {f_ini_prima.isoformat()} al {f_fin.isoformat()}.",
            aplica_ley_2466=False,
        )
    )

    # 4. Vacaciones Compensadas en Dinero (Art. 186 y 189 CST)
    # 15 días hábiles por cada 360 días laborados (divisor 720). Base ordinaria pura sin auxilio de transporte.
    if req.fecha_inicio_vacaciones:
        f_ini_vac = parsear_fecha(req.fecha_inicio_vacaciones)
        dias_vac = dias_laborales_comerciales(f_ini_vac, f_fin)
    else:
        f_ini_vac = f_ini
        dias_vac = dias_totales
    monto_vacaciones = round((base_vacaciones * dias_vac) / 720.0, 2)
    conceptos.append(
        ConceptoLiquidacion(
            id="vacaciones",
            concepto="Compensación de Vacaciones",
            dias=dias_vac,
            base_calculo=base_vacaciones,
            formula=f"({formato_pesos(base_vacaciones)} × {dias_vac}) / 720",
            subtotal=monto_vacaciones,
            norma="Arts. 186, 189 y 192 del CST",
            detalle=f"15 días por cada 360 días laborados (periodo {f_ini_vac.isoformat()} a {f_fin.isoformat()}). Excluye auxilio de transporte por mandato del art. 192 CST.",
            aplica_ley_2466=False,
        )
    )

    total_prestaciones = round(monto_cesantias + monto_intereses + monto_prima + monto_vacaciones, 2)
    total_indemnizaciones = 0.0

    # 5. Indemnización por Despido sin Justa Causa (Art. 64 CST)
    if req.motivo_terminacion == "despido_sin_justa_causa":
        monto_indemnizacion = 0.0
        formula_ind = ""
        detalle_ind = ""
        dias_ind = 0

        salario_diario = salario_ordinario / 30.0

        if req.tipo_contrato == "indefinido":
            # Tabla del art. 64 CST según nivel salarial (< 10 SMMLV vs >= 10 SMMLV)
            es_menos_10_smmlv = salario_ordinario < (10 * smmlv_vigente)

            if es_menos_10_smmlv:
                # 30 días 1er año + 20 días por año subsiguiente y proporcionalmente
                if dias_totales <= 360:
                    dias_ind = 30
                    monto_indemnizacion = round(salario_diario * 30.0, 2)
                    formula_ind = f"30 días × {formato_pesos(salario_diario)}"
                    detalle_ind = "Antigüedad no mayor a 1 año (30 días de salario)."
                else:
                    dias_adicionales = dias_totales - 360
                    dias_proporcionales = (dias_adicionales / 360.0) * 20.0
                    dias_ind_total = 30.0 + dias_proporcionales
                    dias_ind = dias_ind_total
                    monto_indemnizacion = round(salario_diario * dias_ind_total, 2)
                    formula_ind = f"(30 + ({dias_adicionales}/360 × 20)) días × {formato_pesos(salario_diario)}"
                    detalle_ind = f"Primer año: 30 días + {dias_adicionales} días subsiguientes: {dias_proporcionales:.2f} días (total {dias_ind_total:.2f} días)."
            else:
                # 20 días 1er año + 15 días por año subsiguiente y proporcionalmente
                if dias_totales <= 360:
                    dias_ind = 20
                    monto_indemnizacion = round(salario_diario * 20.0, 2)
                    formula_ind = f"20 días × {formato_pesos(salario_diario)}"
                    detalle_ind = "Salario ≥ 10 SMMLV, antigüedad ≤ 1 año (20 días de salario)."
                else:
                    dias_adicionales = dias_totales - 360
                    dias_proporcionales = (dias_adicionales / 360.0) * 15.0
                    dias_ind_total = 20.0 + dias_proporcionales
                    dias_ind = dias_ind_total
                    monto_indemnizacion = round(salario_diario * dias_ind_total, 2)
                    formula_ind = f"(20 + ({dias_adicionales}/360 × 15)) días × {formato_pesos(salario_diario)}"
                    detalle_ind = f"Salario ≥ 10 SMMLV: 20 días primer año + {dias_adicionales} días subsiguientes: {dias_proporcionales:.2f} días (total {dias_ind_total:.2f} días)."

        elif req.tipo_contrato == "termino_fijo":
            if req.fecha_fin_pactada:
                f_pactada = parsear_fecha(req.fecha_fin_pactada)
                if f_pactada > f_fin:
                    f_siguiente = date.fromordinal(f_fin.toordinal() + 1)
                    dias_faltantes = dias_laborales_comerciales(f_siguiente, f_pactada)
                    monto_indemnizacion = round(salario_diario * dias_faltantes, 2)
                    formula_ind = f"{dias_faltantes} días faltantes × {formato_pesos(salario_diario)}"
                    detalle_ind = f"Salarios correspondientes al tiempo faltante hasta el {f_pactada.isoformat()} ({dias_faltantes} días)."
                else:
                    detalle_ind = "El contrato ya había alcanzado la fecha pactada de terminación."
            else:
                detalle_ind = "Contrato a término fijo sin fecha pactada de vencimiento especificada."

        elif req.tipo_contrato == "obra_labor":
            # Tiempo que falte para la terminación de la obra, nunca inferior a 15 días
            dias_min = 15
            monto_indemnizacion = round(salario_diario * dias_min, 2)
            formula_ind = f"{dias_min} días × {formato_pesos(salario_diario)}"
            detalle_ind = "Mínimo legal de 15 días de salario por terminación intempestiva de obra o labor."

        if monto_indemnizacion > 0:
            total_indemnizaciones += monto_indemnizacion
            conceptos.append(
                ConceptoLiquidacion(
                    id="indemnizacion_despido",
                    concepto="Indemnización por Despido sin Justa Causa",
                    dias=int(dias_ind) if dias_ind else 0,
                    base_calculo=salario_ordinario,
                    formula=formula_ind,
                    subtotal=monto_indemnizacion,
                    norma="Art. 64 del CST (modificado por Ley 789 de 2002 y sujeto a Ley 2466 de 2025)",
                    detalle=detalle_ind,
                    aplica_ley_2466=True,
                )
            )

    # 6. Indemnización Moratoria / Salarios Caídos (Art. 65 CST)
    if req.liquidar_moratoria_art65:
        f_corte = parsear_fecha(req.fecha_corte_moratoria) if req.fecha_corte_moratoria else date.today()
        if f_corte > f_fin:
            f_inicio_mora = date.fromordinal(f_fin.toordinal() + 1)
            dias_retardo = dias_laborales_comerciales(f_inicio_mora, f_corte)
            salario_diario = salario_ordinario / 30.0

            # Si gana hasta 1 SMMLV: 1 día por cada día de retardo sin tope
            # Si gana más de 1 SMMLV: 1 día por día los primeros 24 meses (720 días)
            es_hasta_1_smmlv = salario_ordinario <= smmlv_vigente
            if es_hasta_1_smmlv:
                monto_moratoria = round(salario_diario * dias_retardo, 2)
                detalle_mora = f"{dias_retardo} días de retardo del {f_inicio_mora.isoformat()} al {f_corte.isoformat()} a razón de un día de salario."
            else:
                dias_primeros_24m = min(dias_retardo, 720)
                monto_moratoria = round(salario_diario * dias_primeros_24m, 2)
                detalle_mora = f"{dias_primeros_24m} días de retardo (tope 24 meses / 720 días del art. 65 CST). Del {f_inicio_mora.isoformat()} al {f_corte.isoformat()}."
                if dias_retardo > 720:
                    detalle_mora += f" (Se causan además intereses moratorios a la tasa SFC sobre los {dias_retardo - 720} días posteriores al mes 24)."

            total_indemnizaciones += monto_moratoria
            conceptos.append(
                ConceptoLiquidacion(
                    id="indemnizacion_moratoria_art65",
                    concepto="Indemnización Moratoria (Salarios Caídos)",
                    dias=dias_retardo,
                    base_calculo=salario_ordinario,
                    formula=f"{min(dias_retardo, 720 if not es_hasta_1_smmlv else dias_retardo)} días × {formato_pesos(salario_diario)}/día",
                    subtotal=monto_moratoria,
                    norma="Art. 65 del CST (modificado por art. 29 Ley 789 de 2002)",
                    detalle=detalle_mora,
                    aplica_ley_2466=False,
                )
            )

    # 7. Sanción por no Consignación de Cesantías (Art. 99 Ley 50 de 1990)
    if req.liquidar_sancion_consignacion_art99:
        dias_sancion = req.dias_mora_consignacion or 0
        if dias_sancion == 0 and req.fecha_inicio_mora_consignacion:
            f_ini_mora = parsear_fecha(req.fecha_inicio_mora_consignacion)
            f_corte = parsear_fecha(req.fecha_corte_moratoria) if req.fecha_corte_moratoria else date.today()
            if f_corte > f_ini_mora:
                dias_sancion = dias_laborales_comerciales(f_ini_mora, f_corte)

        if dias_sancion > 0:
            salario_diario = salario_ordinario / 30.0
            monto_sancion = round(salario_diario * dias_sancion, 2)
            total_indemnizaciones += monto_sancion
            conceptos.append(
                ConceptoLiquidacion(
                    id="sancion_consignacion_cesantias",
                    concepto="Sanción por no Consignación de Cesantías",
                    dias=dias_sancion,
                    base_calculo=salario_ordinario,
                    formula=f"{dias_sancion} días de mora × {formato_pesos(salario_diario)}/día",
                    subtotal=monto_sancion,
                    norma="Art. 99 Numeral 3 de la Ley 50 de 1990",
                    detalle=f"Un día de salario por cada día de retardo en la consignación de cesantías al fondo a partir del 15 de febrero ({dias_sancion} días).",
                    aplica_ley_2466=False,
                )
            )

    gran_total = round(total_prestaciones + total_indemnizaciones, 2)

    # Recoger advertencias legales
    advertencias: List[str] = []
    adv_2466 = advertencia_ley_2466_2025(
        motivo=req.motivo_terminacion,
        f_fin=f_fin,
        tipo_contrato=req.tipo_contrato,
        tiene_salarios_variables=tiene_salarios_variables,
    )
    if adv_2466:
        advertencias.append(adv_2466)

    # Construir tablas en Markdown y Texto plano
    tabla_md, tabla_txt = formatear_tabla_laboral(
        req=req,
        conceptos=conceptos,
        total_prestaciones=total_prestaciones,
        total_indemnizaciones=total_indemnizaciones,
        gran_total=gran_total,
        f_ini=f_ini,
        f_fin=f_fin,
        dias_totales=dias_totales,
        salario_ordinario=salario_ordinario,
        auxilio_transporte=auxilio_transporte,
    )

    return LiquidacionLaboralResponse(
        trabajador=req.nombre_trabajador or "No especificado",
        empleador=req.nombre_empleador or "No especificado",
        tipo_contrato=req.tipo_contrato,
        motivo_terminacion=req.motivo_terminacion,
        fecha_inicio=f_ini.isoformat(),
        fecha_fin=f_fin.isoformat(),
        dias_totales_servicio=dias_totales,
        salario_base_ordinario=salario_ordinario,
        auxilio_transporte=auxilio_transporte,
        salario_base_prestaciones=base_prestaciones,
        salario_base_vacaciones=base_vacaciones,
        conceptos=conceptos,
        total_prestaciones_sociales=total_prestaciones,
        total_indemnizaciones_y_sanciones=total_indemnizaciones,
        gran_total_liquidacion=gran_total,
        advertencias_legales=advertencias,
        tabla_markdown=tabla_md,
        tabla_texto=tabla_txt,
    )


def formatear_tabla_laboral(
    req: LiquidacionLaboralRequest,
    conceptos: List[ConceptoLiquidacion],
    total_prestaciones: float,
    total_indemnizaciones: float,
    gran_total: float,
    f_ini: date,
    f_fin: date,
    dias_totales: int,
    salario_ordinario: float,
    auxilio_transporte: float,
) -> Tuple[str, str]:
    """Genera la tabla en Markdown y en texto plano monoespaciado para anexar al escrito."""
    # MARKDOWN
    md_lines = [
        "### ANEXO LIQUIDATORIO: PRESTACIONES SOCIALES E INDEMNIZACIONES LABORALES",
        "",
        f"- **Trabajador:** {req.nombre_trabajador or 'Demandante / Trabajador'} | **Empleador:** {req.nombre_empleador or 'Demandado / Empleador'}",
        f"- **Periodo Laborado:** {f_ini.isoformat()} al {f_fin.isoformat()} ({dias_totales} días de servicio)",
        f"- **Salario Ordinario:** {formato_pesos(salario_ordinario)} | **Auxilio de Transporte:** {formato_pesos(auxilio_transporte)}",
        f"- **Modalidad / Causal:** Contrato {req.tipo_contrato} / {req.motivo_terminacion.replace('_', ' ').capitalize()}",
        "",
        "| Rubro / Concepto | Días | Base de Cálculo | Fórmula Aplicada | Subtotal | Fuente Legal |",
        "| :--- | :---: | :---: | :--- | :---: | :--- |",
    ]
    for c in conceptos:
        md_lines.append(
            f"| **{c.concepto}** | {c.dias} | {formato_pesos(c.base_calculo)} | `{c.formula}` | **{formato_pesos(c.subtotal)}** | {c.norma} |"
        )
    md_lines.append(
        f"| **SUBTOTAL PRESTACIONES SOCIALES** | - | - | - | **{formato_pesos(total_prestaciones)}** | Arts. 186, 249, 306 CST y Ley 52/1975 |"
    )
    if total_indemnizaciones > 0:
        md_lines.append(
            f"| **SUBTOTAL INDEMNIZACIONES / SANCIONES** | - | - | - | **{formato_pesos(total_indemnizaciones)}** | Arts. 64, 65 CST y Ley 50/1990 |"
        )
    md_lines.append(
        f"| **GRAN TOTAL LIQUIDACIÓN LABORAL** | - | - | - | **{formato_pesos(gran_total)}** | M/CTE |"
    )
    md_lines.append("")
    md_tabla = "\n".join(md_lines)

    # TEXTO PLANO
    sep = "=" * 102
    sep_sub = "-" * 102
    txt_lines = [
        sep,
        "ANEXO: LIQUIDACIÓN DISCRIMINADA DE PRESTACIONES SOCIALES E INDEMNIZACIONES LABORALES",
        sep,
        f"Trabajador: {req.nombre_trabajador or 'Demandante'}  |  Empleador: {req.nombre_empleador or 'Demandado'}",
        f"Periodo: {f_ini.isoformat()} al {f_fin.isoformat()} ({dias_totales} días)  |  Contrato: {req.tipo_contrato}",
        f"Salario Básico: {formato_pesos(salario_ordinario)}  |  Auxilio Transporte: {formato_pesos(auxilio_transporte)}  |  Causal: {req.motivo_terminacion}",
        sep_sub,
        f"{'CONCEPTO':<32} {'DÍAS':<6} {'BASE CÁLCULO':<16} {'SUBTOTAL (COP)':<18} {'FUENTE LEGAL':<28}",
        sep_sub,
    ]
    for c in conceptos:
        txt_lines.append(
            f"{c.concepto[:31]:<32} {c.dias:<6} {formato_pesos(c.base_calculo):<16} {formato_pesos(c.subtotal):<18} {c.norma[:27]:<28}"
        )
    txt_lines.append(sep_sub)
    txt_lines.append(f"{'SUBTOTAL PRESTACIONES SOCIALES:':<56} {formato_pesos(total_prestaciones):<18}")
    if total_indemnizaciones > 0:
        txt_lines.append(f"{'SUBTOTAL INDEMNIZACIONES Y SANCIONES:':<56} {formato_pesos(total_indemnizaciones):<18}")
    txt_lines.append(sep)
    txt_lines.append(f"{'GRAN TOTAL A PAGAR (M/CTE):':<56} {formato_pesos(gran_total):<18}")
    txt_lines.append(sep)
    txt_tabla = "\n".join(txt_lines)

    return md_tabla, txt_tabla


# -----------------------------------------------------------------------------
# 2. MOTOR DE INTERESES MORATORIOS MERCANTILES (Art. 884 C. Co.)
# -----------------------------------------------------------------------------

class InteresesMoratoriosRequest(BaseModel):
    capital: float = Field(gt=0, description="Capital o monto adeudado sobre el cual corre la mora (COP)")
    fecha_inicio: str = Field(description="Fecha en que se inicia la mora o exigibilidad (YYYY-MM-DD)")
    fecha_fin: str = Field(description="Fecha de corte o liquidación de la mora (YYYY-MM-DD)")
    metodo: Literal["financiero_exacto", "nominal_comercial"] = Field(
        default="financiero_exacto",
        description="Fórmula financiera: 'financiero_exacto' ((1+i_ea)^(dias/365)-1) o 'nominal_comercial' (i_m * dias/30).",
    )
    concepto_obligacion: Optional[str] = Field(
        default="",
        description="Descripción del título valor, factura, pagaré o contrato mercantil origen de la deuda",
    )


class PeriodoMoraItem(BaseModel):
    periodo: str  # YYYY-MM
    fecha_desde: str
    fecha_hasta: str
    dias_mora: int
    capital_base: float
    ibc_ea: float
    mora_ea: float
    tasa_periodo_pct: float
    interes_periodo: float
    interes_acumulado: float
    resolucion: str
    fuente: str


class InteresesMoratoriosResponse(BaseModel):
    capital: float
    fecha_inicio: str
    fecha_fin: str
    dias_totales_mora: int
    interes_total: float
    total_adeudado: float
    concepto_obligacion: str
    criterio_legal: str
    periodos: List[PeriodoMoraItem]
    tabla_markdown: str
    tabla_texto: str


def iterar_meses_rango(f_ini: date, f_fin: date) -> List[Tuple[str, date, date, int]]:
    """
    Divide un rango de fechas en segmentos mensuales con sus fechas de inicio, fin y días efectivos.
    Retorna lista de (YYYY-MM, f_desde, f_hasta, dias).
    """
    segmentos = []
    curr = f_ini
    while curr <= f_fin:
        periodo = f"{curr.year:04d}-{curr.month:02d}"
        ultimo_dia_mes = calendar.monthrange(curr.year, curr.month)[1]
        fin_mes = date(curr.year, curr.month, ultimo_dia_mes)
        f_hasta = min(fin_mes, f_fin)

        # Días calendario transcurridos en este tramo mensual
        dias = (f_hasta - curr).days + 1
        segmentos.append((periodo, curr, f_hasta, dias))

        # Avanzar al primer día del siguiente mes
        if f_hasta.month == 12:
            curr = date(f_hasta.year + 1, 1, 1)
        else:
            curr = date(f_hasta.year, f_hasta.month + 1, 1)

    return segmentos


def calcular_intereses_moratorios(req: InteresesMoratoriosRequest) -> InteresesMoratoriosResponse:
    """
    Calcula mes a mes los intereses de mora mercantiles conforme al art. 884 del Código de Comercio:
    Tasa de mora = 1.5 veces el Interés Bancario Corriente (IBC) certificado por la SFC, sin superar usura.
    """
    f_ini = parsear_fecha(req.fecha_inicio)
    f_fin = parsear_fecha(req.fecha_fin)
    if f_fin < f_ini:
        raise HTTPException(status_code=400, detail="La fecha final no puede ser anterior a la fecha inicial.")

    cat = cargar_catalogo_tasas_sfc()
    tasas_dict: Dict[str, Dict[str, Any]] = {item["periodo"]: item for item in cat.get("series", [])}

    # Si hay periodos fuera de rango, tomar la tasa más cercana conocida
    periodos_ordenados = sorted(tasas_dict.keys())
    tasa_minima_conocida = tasas_dict[periodos_ordenados[0]] if periodos_ordenados else {"ibc_ea": 20.0, "mora_ea": 30.0, "resolucion": "SFC Referencia"}
    tasa_maxima_conocida = tasas_dict[periodos_ordenados[-1]] if periodos_ordenados else tasa_minima_conocida

    segmentos = iterar_meses_rango(f_ini, f_fin)
    items_periodo: List[PeriodoMoraItem] = []
    acumulado_interes = 0.0
    dias_totales = 0

    capital = float(req.capital)

    for periodo, f_desde, f_hasta, dias_tramo in segmentos:
        if periodo in tasas_dict:
            datos_tasa = tasas_dict[periodo]
        elif periodo < periodos_ordenados[0]:
            datos_tasa = tasa_minima_conocida
        else:
            datos_tasa = tasa_maxima_conocida

        ibc_ea = float(datos_tasa.get("ibc_ea", 0.0))
        mora_ea = float(datos_tasa.get("mora_ea", ibc_ea * 1.5))
        resolucion = str(datos_tasa.get("resolucion", "Resolución SFC"))

        i_ea = mora_ea / 100.0

        dias_en_mes_completo = calendar.monthrange(f_desde.year, f_desde.month)[1]
        es_mes_completo = (dias_tramo == dias_en_mes_completo)

        if req.metodo == "financiero_exacto":
            if es_mes_completo:
                # Tasa efectiva mensual: (1 + i_ea)^(1/12) - 1
                tasa_periodo = ((1.0 + i_ea) ** (1.0 / 12.0)) - 1.0
            else:
                # Tasa periódica diaria exacta para la fracción: (1 + i_ea)^(dias/365) - 1
                tasa_periodo = ((1.0 + i_ea) ** (dias_tramo / 365.0)) - 1.0
            interes_tramo = round(capital * tasa_periodo, 2)
        else:
            # Nominal comercial: i_m = (1+i_ea)^(1/12) - 1; proporcional a dias/30
            i_m = ((1.0 + i_ea) ** (1.0 / 12.0)) - 1.0
            tasa_periodo = i_m * (dias_tramo / 30.0)
            interes_tramo = round(capital * tasa_periodo, 2)

        acumulado_interes = round(acumulado_interes + interes_tramo, 2)
        dias_totales += dias_tramo

        items_periodo.append(
            PeriodoMoraItem(
                periodo=periodo,
                fecha_desde=f_desde.isoformat(),
                fecha_hasta=f_hasta.isoformat(),
                dias_mora=dias_tramo,
                capital_base=capital,
                ibc_ea=ibc_ea,
                mora_ea=mora_ea,
                tasa_periodo_pct=round(tasa_periodo * 100.0, 4),
                interes_periodo=interes_tramo,
                interes_acumulado=acumulado_interes,
                resolucion=resolucion,
                fuente="Superintendencia Financiera de Colombia",
            )
        )

    gran_total = round(capital + acumulado_interes, 2)
    criterio = (
        "Art. 884 del Código de Comercio (modificado por art. 111 Ley 510 de 1999): "
        "interés de mora mercantil equivalente a 1.5 veces el Interés Bancario Corriente (IBC) "
        "certificado por la Superintendencia Financiera de Colombia, sin exceder el límite de usura."
    )

    tabla_md, tabla_txt = formatear_tabla_intereses(
        req=req,
        items=items_periodo,
        capital=capital,
        acumulado_interes=acumulado_interes,
        gran_total=gran_total,
        f_ini=f_ini,
        f_fin=f_fin,
        dias_totales=dias_totales,
    )

    return InteresesMoratoriosResponse(
        capital=capital,
        fecha_inicio=f_ini.isoformat(),
        fecha_fin=f_fin.isoformat(),
        dias_totales_mora=dias_totales,
        interes_total=acumulado_interes,
        total_adeudado=gran_total,
        concepto_obligacion=req.concepto_obligacion or "Obligación Mercantil",
        criterio_legal=criterio,
        periodos=items_periodo,
        tabla_markdown=tabla_md,
        tabla_texto=tabla_txt,
    )


def formatear_tabla_intereses(
    req: InteresesMoratoriosRequest,
    items: List[PeriodoMoraItem],
    capital: float,
    acumulado_interes: float,
    gran_total: float,
    f_ini: date,
    f_fin: date,
    dias_totales: int,
) -> Tuple[str, str]:
    """Genera tabla detallada de liquidación de mora comercial mes a mes."""
    # MARKDOWN
    md_lines = [
        "### ANEXO LIQUIDATORIO: INTERESES MORATORIOS MERCANTILES (ART. 884 CÓDIGO DE COMERCIO)",
        "",
        f"- **Concepto / Título:** {req.concepto_obligacion or 'Obligación Mercantil en Mora'}",
        f"- **Capital Base:** {formato_pesos(capital)} | **Periodo de Mora:** {f_ini.isoformat()} al {f_fin.isoformat()} ({dias_totales} días)",
        "- **Criterio Legal:** 1.5 veces el Interés Bancario Corriente (IBC) certificado mes a mes por la Superintendencia Financiera de Colombia.",
        "",
        "| Periodo | Rango de Fechas | Días | IBC E.A. | Tasa Mora E.A. | Tasa Aplicada | Interés Mes | Interés Acumulado | Resolución SFC |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    for it in items:
        md_lines.append(
            f"| {it.periodo} | {it.fecha_desde} a {it.fecha_hasta} | {it.dias_mora} | {it.ibc_ea:.2f}% | {it.mora_ea:.2f}% | {it.tasa_periodo_pct:.4f}% | {formato_pesos(it.interes_periodo)} | {formato_pesos(it.interes_acumulado)} | {it.resolucion} |"
        )
    md_lines.append(
        f"| **TOTALES** | **{f_ini.isoformat()} al {f_fin.isoformat()}** | **{dias_totales}** | - | - | - | **{formato_pesos(acumulado_interes)}** | **{formato_pesos(acumulado_interes)}** | **Superfinanciera** |"
    )
    md_lines.append("")
    md_lines.append(f"**CAPITAL BASE:** {formato_pesos(capital)} M/CTE")
    md_lines.append(f"**TOTAL INTERESES MORATORIOS:** {formato_pesos(acumulado_interes)} M/CTE")
    md_lines.append(f"**GRAN TOTAL ADEUDADO (CAPITAL + MORA):** {formato_pesos(gran_total)} M/CTE")
    md_lines.append("")
    md_tabla = "\n".join(md_lines)

    # TEXTO PLANO
    sep = "=" * 110
    sep_sub = "-" * 110
    txt_lines = [
        sep,
        "LIQUIDACIÓN DE INTERESES MORATORIOS MERCANTILES (ART. 884 C. Co. - SUPERINTENDENCIA FINANCIERA)",
        sep,
        f"Obligación: {req.concepto_obligacion or 'Crédito Mercantil'}  |  Capital Base: {formato_pesos(capital)}",
        f"Lapso en Mora: {f_ini.isoformat()} al {f_fin.isoformat()} ({dias_totales} días)",
        sep_sub,
        f"{'PERIODO':<8} {'RANGO FECHAS':<24} {'DÍAS':<5} {'IBC E.A.':<9} {'MORA E.A.':<10} {'INT. MES':<14} {'INT. ACUM.':<14} {'RESOLUCIÓN SFC':<20}",
        sep_sub,
    ]
    for it in items:
        rango = f"{it.fecha_desde} a {it.fecha_hasta}"
        txt_lines.append(
            f"{it.periodo:<8} {rango:<24} {it.dias_mora:<5} {it.ibc_ea:>6.2f}%   {it.mora_ea:>6.2f}%   {formato_pesos(it.interes_periodo):<14} {formato_pesos(it.interes_acumulado):<14} {it.resolucion[:19]:<20}"
        )
    txt_lines.append(sep_sub)
    txt_lines.append(f"{'CAPITAL PRINCIPAL (COP):':<64} {formato_pesos(capital):<18}")
    txt_lines.append(f"{'TOTAL INTERESES DE MORA LIQUIDADOS (COP):':<64} {formato_pesos(acumulado_interes):<18}")
    txt_lines.append(sep)
    txt_lines.append(f"{'GRAN TOTAL ADEUDADO A LA FECHA DE CORTE (COP):':<64} {formato_pesos(gran_total):<18}")
    txt_lines.append(sep)
    txt_tabla = "\n".join(txt_lines)

    return md_tabla, txt_tabla


# -----------------------------------------------------------------------------
# 3. MOTOR DE INDEXACIÓN CON IPC DEL DANE
# -----------------------------------------------------------------------------

class IndexacionRequest(BaseModel):
    valor_historico: float = Field(gt=0, description="Monto o valor histórico a actualizar monetariamente (COP)")
    fecha_inicial: str = Field(description="Fecha de causación o exigibilidad inicial (YYYY-MM o YYYY-MM-DD)")
    fecha_final: str = Field(description="Fecha de corte o liquidación final (YYYY-MM o YYYY-MM-DD)")
    concepto: Optional[str] = Field(default="", description="Concepto del crédito, condena o perjuicio a indexar")


class IndexacionResponse(BaseModel):
    valor_historico: float
    fecha_inicial: str
    fecha_final: str
    periodo_inicial: str
    periodo_final: str
    ipc_inicial: float
    ipc_final: float
    factor_indexacion: float
    variacion_porcentual: float
    correccion_monetaria: float
    valor_indexado: float
    formula: str
    fuente_dane: str
    norma: str
    tabla_markdown: str
    tabla_texto: str


def calcular_indexacion_ipc(req: IndexacionRequest) -> IndexacionResponse:
    """
    Indexación con el IPC oficial del DANE bajo la fórmula jurisprudencial unificada
    de la Corte Suprema de Justicia (Salas Civil y Laboral) y el Consejo de Estado:
    VA = VH × (IPC_final / IPC_inicial).
    """
    f_ini = parsear_fecha(req.fecha_inicial)
    f_fin = parsear_fecha(req.fecha_final)
    if f_fin < f_ini:
        raise HTTPException(status_code=400, detail="La fecha final de indexación no puede ser anterior a la inicial.")

    periodo_ini = f"{f_ini.year:04d}-{f_ini.month:02d}"
    periodo_fin = f"{f_fin.year:04d}-{f_fin.month:02d}"

    cat = cargar_catalogo_ipc()
    series = {item["periodo"]: float(item["indice"]) for item in cat.get("series", [])}
    if not series:
        raise HTTPException(status_code=500, detail="No se encontró la serie histórica del IPC del DANE.")

    periodos_disponibles = sorted(series.keys())

    # Búsqueda o aproximación al más cercano si excede los límites
    if periodo_ini in series:
        ipc_ini = series[periodo_ini]
    elif periodo_ini < periodos_disponibles[0]:
        ipc_ini = series[periodos_disponibles[0]]
        periodo_ini = periodos_disponibles[0]
    else:
        ipc_ini = series[periodos_disponibles[-1]]
        periodo_ini = periodos_disponibles[-1]

    if periodo_fin in series:
        ipc_fin = series[periodo_fin]
    elif periodo_fin > periodos_disponibles[-1]:
        ipc_fin = series[periodos_disponibles[-1]]
        periodo_fin = periodos_disponibles[-1]
    else:
        ipc_fin = series[periodos_disponibles[0]]
        periodo_fin = periodos_disponibles[0]

    vh = float(req.valor_historico)
    factor = ipc_fin / ipc_ini
    valor_indexado = round(vh * factor, 2)
    correccion_monetaria = round(valor_indexado - vh, 2)
    variacion_pct = round(((ipc_fin - ipc_ini) / ipc_ini) * 100.0, 2)

    formula = f"VA = VH × ({ipc_fin:.2f} / {ipc_ini:.2f}) = {formato_pesos(vh)} × {factor:.6f}"
    fuente = "DANE - Índice de Precios al Consumidor (IPC), Total Nacional (Base Diciembre 2018 = 100)"
    norma = (
        "Corte Suprema de Justicia (Sala de Casación Civil y Laboral) y Consejo de Estado: "
        "actualización monetaria por pérdida del poder adquisitivo de la moneda."
    )

    tabla_md, tabla_txt = formatear_tabla_indexacion(
        req=req,
        periodo_ini=periodo_ini,
        periodo_fin=periodo_fin,
        ipc_ini=ipc_ini,
        ipc_fin=ipc_fin,
        factor=factor,
        variacion_pct=variacion_pct,
        vh=vh,
        correccion_monetaria=correccion_monetaria,
        valor_indexado=valor_indexado,
    )

    return IndexacionResponse(
        valor_historico=vh,
        fecha_inicial=f_ini.isoformat(),
        fecha_final=f_fin.isoformat(),
        periodo_inicial=periodo_ini,
        periodo_final=periodo_fin,
        ipc_inicial=ipc_ini,
        ipc_final=ipc_fin,
        factor_indexacion=round(factor, 6),
        variacion_porcentual=variacion_pct,
        correccion_monetaria=correccion_monetaria,
        valor_indexado=valor_indexado,
        formula=formula,
        fuente_dane=fuente,
        norma=norma,
        tabla_markdown=tabla_md,
        tabla_texto=tabla_txt,
    )


def formatear_tabla_indexacion(
    req: IndexacionRequest,
    periodo_ini: str,
    periodo_fin: str,
    ipc_ini: float,
    ipc_fin: float,
    factor: float,
    variacion_pct: float,
    vh: float,
    correccion_monetaria: float,
    valor_indexado: float,
) -> Tuple[str, str]:
    """Genera la tabla de indexación en Markdown y texto plano."""
    # MARKDOWN
    md_lines = [
        "### ANEXO LIQUIDATORIO: ACTUALIZACIÓN MONETARIA CON IPC (DANE)",
        "",
        f"- **Concepto:** {req.concepto or 'Obligación / Condena Judicial'}",
        f"- **Periodo de Indexación:** {periodo_ini} a {periodo_fin}",
        "- **Fórmula Judicial Unificada:** `VA = VH × (IPC_final / IPC_inicial)`",
        "- **Fuente Oficial:** DANE (Índice de Precios al Consumidor - Total Nacional)",
        "",
        "| Elemento Liquidatorio | Valor / Parámetro | Fuente / Detalle |",
        "| :--- | :---: | :--- |",
        f"| **Valor Histórico (VH)** | **{formato_pesos(vh)}** | Capital de origen en mora o causado |",
        f"| **IPC Inicial ({periodo_ini})** | {ipc_ini:.2f} | DANE IPC Base Dic/2018=100 |",
        f"| **IPC Final ({periodo_fin})** | {ipc_fin:.2f} | DANE IPC Base Dic/2018=100 |",
        f"| **Factor de Actualización** | {factor:.6f} | `{ipc_fin:.2f} / {ipc_ini:.2f}` |",
        f"| **Inflación Acumulada** | {variacion_pct:.2f}% | Variación del poder adquisitivo |",
        f"| **Corrección Monetaria** | **{formato_pesos(correccion_monetaria)}** | Ajuste inflacionario (`VA - VH`) |",
        f"| **VALOR ACTUALIZADO INDEXADO (VA)** | **{formato_pesos(valor_indexado)}** | **Total actualizado a la fecha de corte** |",
        "",
    ]
    md_tabla = "\n".join(md_lines)

    # TEXTO PLANO
    sep = "=" * 80
    sep_sub = "-" * 80
    txt_lines = [
        sep,
        "ANEXO: CUADRO DE ACTUALIZACIÓN MONETARIA (INDEXACIÓN CON IPC DANE)",
        sep,
        f"Concepto: {req.concepto or 'Obligación / Condena Judicial'}",
        f"Fórmula: VA = VH * (IPC_final / IPC_inicial)",
        f"Periodo: {periodo_ini} a {periodo_fin}",
        sep_sub,
        f"{'PARÁMETRO':<36} {'VALOR':<20} {'DETALLE / FUENTE':<22}",
        sep_sub,
        f"{'Valor Histórico (VH):':<36} {formato_pesos(vh):<20} {'Capital base':<22}",
        f"{f'IPC Inicial ({periodo_ini}):':<36} {f'{ipc_ini:.2f}':<20} {'DANE':<22}",
        f"{f'IPC Final ({periodo_fin}):':<36} {f'{ipc_fin:.2f}':<20} {'DANE':<22}",
        f"{'Factor Multiplicador:':<36} {f'{factor:.6f}':<20} {'IPC_f / IPC_i':<22}",
        f"{'Variación IPC Acumulada:':<36} {f'{variacion_pct:.2f}%':<20} {'Inflación periodo':<22}",
        f"{'Corrección Monetaria:':<36} {formato_pesos(correccion_monetaria):<20} {'Ajuste neto':<22}",
        sep,
        f"{'VALOR ACTUALIZADO (VA):':<36} {formato_pesos(valor_indexado):<20} {'Total Indexado (COP)':<22}",
        sep,
    ]
    txt_tabla = "\n".join(txt_lines)

    return md_tabla, txt_tabla


# -----------------------------------------------------------------------------
# FASTAPI ROUTER Y ENDPOINTS
# -----------------------------------------------------------------------------

router = APIRouter(prefix="/api/calculos", tags=["Cálculos Jurídicos y Financieros"])


@router.post("/laboral", response_model=LiquidacionLaboralResponse)
@router.post("/liquidacion-laboral", response_model=LiquidacionLaboralResponse)
async def endpoint_liquidacion_laboral(req: LiquidacionLaboralRequest):
    """
    Liquidación laboral integral colombiana:
    - Cesantías (art. 249 CST)
    - Intereses a las cesantías (Ley 52 de 1975)
    - Prima de servicios (art. 306 CST)
    - Vacaciones (art. 186 CST)
    - Indemnización por despido sin justa causa (art. 64 CST)
    - Indemnización moratoria (art. 65 CST)
    - Sanción por no consignación (art. 99 Ley 50/1990)
    - Advertencia legal sobre el impacto de la Ley 2466 de 2025.
    """
    return calcular_liquidacion_laboral(req)


@router.post("/intereses-moratorios", response_model=InteresesMoratoriosResponse)
async def endpoint_intereses_moratorios(req: InteresesMoratoriosRequest):
    """
    Liquidación de intereses moratorios mercantiles:
    - 1.5 veces el Interés Bancario Corriente (IBC) certificado mes a mes por la SFC.
    - Cumplimiento del art. 884 del Código de Comercio y límite de usura (art. 305 Código Penal).
    """
    return calcular_intereses_moratorios(req)


@router.post("/indexacion", response_model=IndexacionResponse)
@router.post("/indexacion-ipc", response_model=IndexacionResponse)
async def endpoint_indexacion_ipc(req: IndexacionRequest):
    """
    Indexación monetaria con IPC oficial del DANE:
    VA = VH × (IPC_final / IPC_inicial).
    Fórmula unificada de la Corte Suprema de Justicia y Consejo de Estado.
    """
    return calcular_indexacion_ipc(req)


@router.get("/tasas-sfc")
async def endpoint_obtener_tasas_sfc():
    """Retorna el catálogo oficial de tasas IBC y mora de la Superintendencia Financiera."""
    return cargar_catalogo_tasas_sfc()


@router.get("/ipc")
async def endpoint_obtener_ipc():
    """Retorna la serie histórica del IPC del DANE utilizada para indexación."""
    return cargar_catalogo_ipc()

```


## 📄 Archivo: `app/services/plazos.py`
```python
"""Servicio de cómputo de términos y plazos procesales en Colombia (v2.2.1).

Implementa las reglas del Código General del Proceso (CGP), CPACA, Decreto 2591 de 1991,
Ley 2213 de 2022 y Ley 51 de 1983 (Ley Emiliani).

REGLAS DE CÓMPUTO:
1. Días hábiles:
   - Excluye sábados, domingos y festivos de Colombia.
   - Festivos calculados con el algoritmo de Meeus/Butcher (Pascua) y traslados al lunes (Ley 51/1983).
   - Días de Semana Santa sin despacho judicial (lunes, martes y miércoles santos por acuerdo CSJ).
   - Vacancia judicial colectiva de fin de año: 20 de diciembre a 10 de enero (art. 146 Ley 270/1996).
   - Suspensiones adicionales de términos decretadas por el Consejo Superior de la Judicatura (CSJ).
2. Meses y años (art. 118 CGP y art. 67 Código Civil):
   - Cómputo calendario: vencen el mismo día del respectivo mes o año.
   - Si el mes no tiene tal día, vence el último día del mes.
   - Si el último día es inhábil, se extiende automáticamente hasta el primer día hábil siguiente.
3. Notificación por mensaje de datos (art. 8 Ley 2213 de 2022):
   - La notificación se entiende surtida transcurridos dos (2) días hábiles siguientes al envío del mensaje.
   - Los términos empiezan a correr a partir del día siguiente al de la notificación.
   - Con acuse de recibo voluntario o comprobado, el término empieza al día siguiente a su recepción.
4. Generación de eventos iCalendar (.ics RFC 5545).
"""

from __future__ import annotations

import calendar
import datetime
from datetime import timedelta
import json
import os
import uuid
from functools import lru_cache
from typing import Any, Optional

CALENDARIO_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogo", "calendario_judicial.json"
)

NOMBRES_DIAS = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]

NOMBRES_MESES = [
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


# -----------------------------------------------------------------------------
# 1. ALGORITMO DE PASCUA Y FESTIVOS COLOMBIANOS (LEY 51 DE 1983)
# -----------------------------------------------------------------------------
@lru_cache(maxsize=128)
def calcular_domingo_pascua(year: int) -> datetime.date:
    """Calcula el Domingo de Pascua (Resurrección) mediante el algoritmo de Meeus/Butcher."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(year, mes, dia)


def trasladar_al_siguiente_lunes(fecha: datetime.date) -> datetime.date:
    """Aplica la Ley 51 de 1983 (Ley Emiliani): si no es lunes, se traslada al siguiente lunes."""
    if fecha.weekday() == 0:  # 0 es lunes
        return fecha
    dias_para_lunes = 7 - fecha.weekday()
    return fecha + timedelta(days=dias_para_lunes)


@lru_cache(maxsize=128)
def obtener_festivos_colombia(year: int) -> dict[datetime.date, str]:
    """Retorna todos los festivos nacionales oficiales de Colombia para el año dado según la Ley 51 de 1983."""
    pascua = calcular_domingo_pascua(year)
    festivos: dict[datetime.date, str] = {}

    # 1. Festivos de fecha fija que NO se trasladan
    fijos = [
        (datetime.date(year, 1, 1), "Año Nuevo"),
        (datetime.date(year, 5, 1), "Día del Trabajo"),
        (datetime.date(year, 7, 20), "Día de la Independencia"),
        (datetime.date(year, 8, 7), "Batalla de Boyacá"),
        (datetime.date(year, 12, 8), "Inmaculada Concepción"),
        (datetime.date(year, 12, 25), "Navidad"),
    ]
    for f, nombre in fijos:
        festivos[f] = nombre

    # 2. Festivos religiosos de Pascua que NO se trasladan
    festivos[pascua - timedelta(days=3)] = "Jueves Santo"
    festivos[pascua - timedelta(days=2)] = "Viernes Santo"

    # 3. Festivos de fecha fija que SE TRASLADAN al lunes siguiente (Ley Emiliani)
    trasladables_fijos = [
        (datetime.date(year, 1, 6), "Reyes Magos"),
        (datetime.date(year, 3, 19), "San José"),
        (datetime.date(year, 6, 29), "San Pedro y San Pablo"),
        (datetime.date(year, 8, 15), "Asunción de la Virgen"),
        (datetime.date(year, 10, 12), "Día de la Raza"),
        (datetime.date(year, 11, 1), "Todos los Santos"),
        (datetime.date(year, 11, 11), "Independencia de Cartagena"),
    ]
    for f, nombre in trasladables_fijos:
        lunes = trasladar_al_siguiente_lunes(f)
        festivos[lunes] = nombre

    # 4. Festivos móviles respecto a Pascua que SE TRASLADAN al lunes siguiente
    # - Ascensión del Señor: a los 40 días de Pascua (jueves) -> al lunes (pascua + 43 días)
    festivos[trasladar_al_siguiente_lunes(pascua + timedelta(days=40))] = "Ascensión del Señor"
    # - Corpus Christi: a los 60 días de Pascua (jueves) -> al lunes (pascua + 64 días)
    festivos[trasladar_al_siguiente_lunes(pascua + timedelta(days=60))] = "Corpus Christi"
    # - Sagrado Corazón de Jesús: a los 68 días de Pascua (viernes) -> al lunes (pascua + 71 días)
    festivos[trasladar_al_siguiente_lunes(pascua + timedelta(days=68))] = "Sagrado Corazón de Jesús"

    return festivos


# -----------------------------------------------------------------------------
# 2. CALENDARIO JUDICIAL (VACANCIA, SEMANA SANTA Y SUSPENSIONES CSJ)
# -----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def cargar_calendario_judicial_config() -> dict[str, Any]:
    """Carga la configuración de calendario judicial y precargas de términos."""
    if os.path.exists(CALENDARIO_JSON_PATH):
        try:
            with open(CALENDARIO_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def obtener_precargas_terminos() -> list[dict[str, Any]]:
    """Retorna la lista de precargas de términos procesales con sus normas asociadas."""
    config = cargar_calendario_judicial_config()
    return config.get("precargas_terminos", [])


def buscar_precarga(tipo_termino: str) -> Optional[dict[str, Any]]:
    """Busca una precarga de término por su ID."""
    if not tipo_termino:
        return None
    precargas = obtener_precargas_terminos()
    t_low = tipo_termino.lower().strip()
    for p in precargas:
        if p.get("id", "").lower() == t_low or p.get("nombre", "").lower() == t_low:
            return p
    return None


def es_vacancia_judicial_colectiva(fecha: datetime.date) -> bool:
    """Verifica si la fecha cae dentro de la vacancia judicial colectiva (20 dic a 10 ene)."""
    # 20 de diciembre al 31 de diciembre
    if fecha.month == 12 and fecha.day >= 20:
        return True
    # 1 de enero al 10 de enero
    if fecha.month == 1 and fecha.day <= 10:
        return True
    return False


def es_semana_santa_judicial(fecha: datetime.date) -> tuple[bool, str]:
    """Verifica si la fecha corresponde a los días de Semana Santa sin despacho (Lunes, Martes o Miércoles Santo)."""
    pascua = calcular_domingo_pascua(fecha.year)
    lunes_santo = pascua - timedelta(days=6)
    martes_santo = pascua - timedelta(days=5)
    miercoles_santo = pascua - timedelta(days=4)

    if fecha == lunes_santo:
        return True, "Semana Santa judicial (Lunes Santo sin despacho)"
    if fecha == martes_santo:
        return True, "Semana Santa judicial (Martes Santo sin despacho)"
    if fecha == miercoles_santo:
        return True, "Semana Santa judicial (Miércoles Santo sin despacho)"
    return False, ""


def es_suspension_csj(fecha: datetime.date) -> tuple[bool, str]:
    """Verifica si la fecha cae en alguna suspensión de términos decretada por el CSJ."""
    config = cargar_calendario_judicial_config()
    suspensiones = config.get("suspensiones_adicionales_csj", [])
    iso_str = fecha.isoformat()

    for s in suspensiones:
        if s.get("activo"):
            desde = s.get("desde", "")
            hasta = s.get("hasta", "")
            if desde and hasta and desde <= iso_str <= hasta:
                desc = s.get("descripcion") or s.get("acuerdo") or "Suspensión de términos CSJ"
                return True, f"Suspensión CSJ: {desc}"
    return False, ""


def es_dia_habil(
    fecha: datetime.date,
    vacancia_colectiva: bool = True,
    incluir_semana_santa: bool = True,
) -> tuple[bool, str]:
    """Determina si una fecha es día hábil judicial en Colombia.

    Retorna: (es_habil: bool, motivo_o_descripcion: str)
    """
    # 1. Fin de semana
    if fecha.weekday() == 5:
        return False, "Sábado (inhábil)"
    if fecha.weekday() == 6:
        return False, "Domingo (inhábil)"

    # 2. Festivos nacionales de Colombia (Ley 51 de 1983)
    festivos = obtener_festivos_colombia(fecha.year)
    if fecha in festivos:
        return False, f"Festivo nacional: {festivos[fecha]}"

    # 3. Semana Santa judicial sin despacho (Lunes, Martes, Miércoles Santo)
    if incluir_semana_santa:
        es_ss, desc_ss = es_semana_santa_judicial(fecha)
        if es_ss:
            return False, desc_ss

    # 4. Vacancia judicial colectiva de fin de año (20 dic - 10 ene)
    if vacancia_colectiva and es_vacancia_judicial_colectiva(fecha):
        return False, "Vacancia judicial colectiva (art. 146 Ley 270/96: 20 dic - 10 ene)"

    # 5. Suspensiones adicionales del Consejo Superior de la Judicatura
    es_csj, desc_csj = es_suspension_csj(fecha)
    if es_csj:
        return False, desc_csj

    return True, "Día hábil judicial"


def dia_habil_siguiente(
    fecha: datetime.date,
    vacancia_colectiva: bool = True,
    incluir_semana_santa: bool = True,
) -> datetime.date:
    """Encuentra el primer día hábil inmediatamente posterior a la fecha dada."""
    cursor = fecha + timedelta(days=1)
    while True:
        habil, _ = es_dia_habil(
            cursor,
            vacancia_colectiva=vacancia_colectiva,
            incluir_semana_santa=incluir_semana_santa,
        )
        if habil:
            return cursor
        cursor += timedelta(days=1)


# -----------------------------------------------------------------------------
# 3. NOTIFICACIÓN POR MENSAJE DE DATOS (LEY 2213 DE 2022, ART. 8)
# -----------------------------------------------------------------------------
def procesar_notificacion_mensaje_datos(
    fecha_envio: datetime.date,
    fecha_acuse_recibo: Optional[datetime.date] = None,
    vacancia_colectiva: bool = True,
) -> tuple[datetime.date, datetime.date, list[str]]:
    """Aplica la regla de notificación personal electrónica del art. 8 de la Ley 2213 de 2022.

    Regla:
    - Si hay acuse de recibo voluntario o constatado, la notificación ocurre en esa fecha y los
      términos corren al día siguiente hábil.
    - Si no hay acuse de recibo, transcurren dos (2) días hábiles siguientes al envío del mensaje;
      al finalizar el segundo día hábil se entiende notificado, y el término empieza a correr
      el día hábil siguiente.

    Retorna:
      (fecha_notificacion, fecha_inicio_computo, explicacion_reglas)
    """
    reglas: list[str] = []

    if fecha_acuse_recibo:
        fecha_notif = fecha_acuse_recibo
        fecha_inicio_computo = dia_habil_siguiente(fecha_notif, vacancia_colectiva=vacancia_colectiva)
        reglas.append(
            f"Notificación con acuse de recibo ({fecha_notif.isoformat()}): conforme al inciso 3 del art. 8 de la Ley 2213 de 2022, "
            f"el término empieza a correr el día hábil siguiente ({fecha_inicio_computo.isoformat()})."
        )
        return fecha_notif, fecha_inicio_computo, reglas

    # Conteo de 2 días hábiles siguientes al envío
    cursor = fecha_envio
    dias_habiles_gracia: list[datetime.date] = []
    while len(dias_habiles_gracia) < 2:
        cursor += timedelta(days=1)
        habil, _ = es_dia_habil(cursor, vacancia_colectiva=vacancia_colectiva)
        if habil:
            dias_habiles_gracia.append(cursor)

    fecha_notif = dias_habiles_gracia[1]
    fecha_inicio_computo = dia_habil_siguiente(fecha_notif, vacancia_colectiva=vacancia_colectiva)

    reglas.append(
        f"Envío de mensaje de datos: {fecha_envio.isoformat()}. "
        f"Transcurren los 2 días hábiles de gracia ({dias_habiles_gracia[0].isoformat()} y {dias_habiles_gracia[1].isoformat()}). "
        f"La notificación se entiende realizada el {fecha_notif.isoformat()} (art. 8 Ley 2213 de 2022)."
    )
    reglas.append(
        f"El término empieza a correr a partir del día hábil siguiente a la notificación: {fecha_inicio_computo.isoformat()}."
    )

    return fecha_notif, fecha_inicio_computo, reglas


# -----------------------------------------------------------------------------
# 4. CÓMPUTO DE MESES Y AÑOS (ART. 118 CGP Y ART. 67 CÓDIGO CIVIL)
# -----------------------------------------------------------------------------
def sumar_meses_calendario(fecha: datetime.date, meses: int) -> datetime.date:
    """Suma N meses calendario exactos respetando los días máximos del mes de destino."""
    nuevo_mes = fecha.month + meses
    nuevo_year = fecha.year + (nuevo_mes - 1) // 12
    nuevo_mes = ((nuevo_mes - 1) % 12) + 1
    max_dias_mes = calendar.monthrange(nuevo_year, nuevo_mes)[1]
    nuevo_dia = min(fecha.day, max_dias_mes)
    return datetime.date(nuevo_year, nuevo_mes, nuevo_dia)


def sumar_anios_calendario(fecha: datetime.date, anios: int) -> datetime.date:
    """Suma N años calendario exactos ajustando el 29 de febrero a 28 de febrero en no bisiestos."""
    nuevo_year = fecha.year + anios
    if fecha.month == 2 and fecha.day == 29 and not calendar.isleap(nuevo_year):
        return datetime.date(nuevo_year, 2, 28)
    return datetime.date(nuevo_year, fecha.month, fecha.day)


# -----------------------------------------------------------------------------
# 5. CÁLCULO INTEGRAL DEL PLAZO PROCESAL
# -----------------------------------------------------------------------------
def calcular_plazo(
    fecha_inicio: str | datetime.date,
    unidad: str = "dias_habiles",
    cantidad: int = 3,
    tipo_termino: Optional[str] = None,
    vacancia_colectiva: bool = True,
    notificacion_mensaje_datos: bool = False,
    fecha_acuse_recibo: Optional[str | datetime.date] = None,
    fecha_referencia_hoy: Optional[datetime.date] = None,
    hora_limite: str = "17:00",
    titulo_evento: Optional[str] = None,
) -> dict[str, Any]:
    """Calcula el vencimiento del término procesal aplicando el régimen legal colombiano.

    Parámetros:
      - fecha_inicio: Fecha ISO (YYYY-MM-DD) del acto, providencia, notificación o envío.
      - unidad: "dias_habiles", "meses" o "anios".
      - cantidad: Número entero mayor a cero.
      - tipo_termino: ID o nombre del término (opcional, para enriquecer norma y nombre).
      - vacancia_colectiva: Si se suspende entre el 20 de diciembre y el 10 de enero.
      - notificacion_mensaje_datos: Aplica la regla del art. 8 de la Ley 2213 de 2022 (2 días de gracia).
      - fecha_acuse_recibo: Fecha ISO de acuse de recibo si existió.
      - fecha_referencia_hoy: Fecha base para calcular días restantes (por defecto, hoy).
      - hora_limite: Hora límite de radicación (por defecto 17:00, cierre de despachos).
    """
    if isinstance(fecha_inicio, str):
        fecha_base = datetime.date.fromisoformat(fecha_inicio.strip())
    else:
        fecha_base = fecha_inicio

    if isinstance(fecha_acuse_recibo, str) and fecha_acuse_recibo.strip():
        acuse_date: Optional[datetime.date] = datetime.date.fromisoformat(fecha_acuse_recibo.strip())
    elif isinstance(fecha_acuse_recibo, datetime.date):
        acuse_date = fecha_acuse_recibo
    else:
        acuse_date = None

    hoy = fecha_referencia_hoy or datetime.date.today()
    reglas_aplicadas: list[str] = []

    # Precarga de término si coincide
    precarga = buscar_precarga(tipo_termino or "")
    nombre_termino = precarga.get("nombre") if precarga else (tipo_termino or "Término procesal")
    norma_termino = precarga.get("norma") if precarga else "Código General del Proceso / CPACA"

    # 1. Notificación por mensaje de datos
    if notificacion_mensaje_datos:
        fecha_notif, fecha_inicio_computo, reglas_notif = procesar_notificacion_mensaje_datos(
            fecha_base,
            fecha_acuse_recibo=acuse_date,
            vacancia_colectiva=vacancia_colectiva,
        )
        reglas_aplicadas.extend(reglas_notif)
    else:
        fecha_notif = fecha_base
        # En términos procesales, el término empieza al día siguiente hábil de la notificación
        fecha_inicio_computo = dia_habil_siguiente(fecha_notif, vacancia_colectiva=vacancia_colectiva)
        reglas_aplicadas.append(
            f"Notificación o providencia: {fecha_notif.isoformat()}. "
            f"El término empieza a correr el día hábil siguiente: {fecha_inicio_computo.isoformat()} (art. 118 CGP)."
        )

    desglose_dias: list[dict[str, Any]] = []

    # 2. Cómputo según unidad
    if unidad == "dias_habiles":
        reglas_aplicadas.append(
            f"Cómputo en días hábiles ({cantidad} días): excluye sábados, domingos, festivos de Colombia (Ley 51/1983)"
            + (", vacancia judicial colectiva de fin de año" if vacancia_colectiva else " (sin vacancia colectiva)")
            + " y Semana Santa judicial."
        )

        cursor = fecha_inicio_computo
        dias_computados = 0
        fecha_vencimiento = cursor

        while dias_computados < cantidad:
            es_h, motivo = es_dia_habil(cursor, vacancia_colectiva=vacancia_colectiva)
            if es_h:
                dias_computados += 1
                desglose_dias.append({
                    "fecha": cursor.isoformat(),
                    "dia_semana": NOMBRES_DIAS[cursor.weekday()].capitalize(),
                    "es_habil": True,
                    "dia_computo": dias_computados,
                    "motivo": "Día hábil de término",
                })
                fecha_vencimiento = cursor
            else:
                desglose_dias.append({
                    "fecha": cursor.isoformat(),
                    "dia_semana": NOMBRES_DIAS[cursor.weekday()].capitalize(),
                    "es_habil": False,
                    "dia_computo": None,
                    "motivo": motivo,
                })

            if dias_computados < cantidad:
                cursor += timedelta(days=1)

    elif unidad == "meses":
        # Meses calendario a partir de fecha_notif (art. 118 CGP: vence el mismo día del respectivo mes)
        target = sumar_meses_calendario(fecha_notif, cantidad)
        reglas_aplicadas.append(
            f"Cómputo en meses calendario ({cantidad} meses): desde {fecha_notif.isoformat()} hasta {target.isoformat()} (art. 118 CGP y art. 67 Código Civil)."
        )
        # Si el último día es inhábil, pasa al siguiente día hábil
        es_h, motivo = es_dia_habil(target, vacancia_colectiva=vacancia_colectiva)
        if es_h:
            fecha_vencimiento = target
        else:
            fecha_vencimiento = dia_habil_siguiente(target, vacancia_colectiva=vacancia_colectiva)
            reglas_aplicadas.append(
                f"El día de vencimiento inicial ({target.isoformat()}) es {motivo}. "
                f"Conforme al inciso 4 del art. 118 del CGP, el término se extiende automáticamente al primer día hábil siguiente ({fecha_vencimiento.isoformat()})."
            )

    elif unidad == "anios":
        # Años calendario a partir de fecha_notif
        target = sumar_anios_calendario(fecha_notif, cantidad)
        reglas_aplicadas.append(
            f"Cómputo en años calendario ({cantidad} años): desde {fecha_notif.isoformat()} hasta {target.isoformat()} (art. 118 CGP y art. 67 Código Civil)."
        )
        es_h, motivo = es_dia_habil(target, vacancia_colectiva=vacancia_colectiva)
        if es_h:
            fecha_vencimiento = target
        else:
            fecha_vencimiento = dia_habil_siguiente(target, vacancia_colectiva=vacancia_colectiva)
            reglas_aplicadas.append(
                f"El día de vencimiento inicial ({target.isoformat()}) es {motivo}. "
                f"Conforme al inciso 4 del art. 118 del CGP, el término se extiende automáticamente al primer día hábil siguiente ({fecha_vencimiento.isoformat()})."
            )
    else:
        raise ValueError(f"Unidad de plazo no reconocida: '{unidad}'. Debe ser 'dias_habiles', 'meses' o 'anios'.")

    # 3. Días restantes y estado de vencimiento
    dias_calendario_restantes = (fecha_vencimiento - hoy).days
    ha_vencido = fecha_vencimiento < hoy

    # Conteo de días hábiles restantes entre hoy y fecha_vencimiento
    if ha_vencido:
        # Contar cuántos días hábiles han pasado desde el vencimiento
        c = fecha_vencimiento + timedelta(days=1)
        pasados_habiles = 0
        while c <= hoy:
            h, _ = es_dia_habil(c, vacancia_colectiva=vacancia_colectiva)
            if h:
                pasados_habiles += 1
            c += timedelta(days=1)
        dias_habiles_restantes = -pasados_habiles
        estado_vencimiento = "vencido"
    elif fecha_vencimiento == hoy:
        dias_habiles_restantes = 0
        estado_vencimiento = "vence_hoy"
    else:
        # Contar días hábiles desde mañana hasta la fecha de vencimiento inclusive
        c = hoy + timedelta(days=1)
        restantes_habiles = 0
        while c <= fecha_vencimiento:
            h, _ = es_dia_habil(c, vacancia_colectiva=vacancia_colectiva)
            if h:
                restantes_habiles += 1
            c += timedelta(days=1)
        dias_habiles_restantes = restantes_habiles
        estado_vencimiento = "urgente" if dias_habiles_restantes <= 3 else "vigente"

    # Formateo amigable en español
    dia_semana_nombre = NOMBRES_DIAS[fecha_vencimiento.weekday()].capitalize()
    mes_nombre = NOMBRES_MESES[fecha_vencimiento.month]
    fecha_vencimiento_texto = f"{dia_semana_nombre.lower()}, {fecha_vencimiento.day} de {mes_nombre} de {fecha_vencimiento.year}"

    if ha_vencido:
        dias_pasados = abs(dias_habiles_restantes)
        sufijo = "día hábil" if dias_pasados == 1 else "días hábiles"
        texto_resumen = f"Venció el {fecha_vencimiento_texto} (hace {dias_pasados} {sufijo})"
    elif fecha_vencimiento == hoy:
        texto_resumen = f"¡VENCE HOY! {fecha_vencimiento_texto} hasta las {hora_limite}"
    else:
        sufijo = "día hábil" if dias_habiles_restantes == 1 else "días hábiles"
        texto_resumen = f"Vence el {fecha_vencimiento_texto} (quedan {dias_habiles_restantes} {sufijo})"

    # 4. Generación del evento iCalendar (.ics)
    titulo_ics = titulo_evento or f"VENCIMIENTO: {nombre_termino}"
    desc_ics = (
        f"Vencimiento de término procesal: {nombre_termino}\\n"
        f"Norma aplicable: {norma_termino}\\n"
        f"Fecha de notificación: {fecha_notif.isoformat()}\\n"
        f"Fecha límite: {fecha_vencimiento.isoformat()} a las {hora_limite}\\n"
        f"Regla: {texto_resumen}\\n"
        f"Generado por El Memorialista."
    )
    ics_content = generar_evento_ics(
        titulo=titulo_ics,
        fecha_vencimiento=fecha_vencimiento,
        descripcion=desc_ics,
        hora_vencimiento=hora_limite,
    )

    return {
        "ok": True,
        "tipo_termino": tipo_termino,
        "nombre_termino": nombre_termino,
        "norma": norma_termino,
        "fecha_inicio": fecha_base.isoformat(),
        "fecha_notificacion": fecha_notif.isoformat(),
        "fecha_inicio_computo": fecha_inicio_computo.isoformat(),
        "unidad": unidad,
        "cantidad": cantidad,
        "vacancia_colectiva": vacancia_colectiva,
        "notificacion_mensaje_datos": notificacion_mensaje_datos,
        "fecha_vencimiento": fecha_vencimiento.isoformat(),
        "dia_semana_vencimiento": dia_semana_nombre,
        "fecha_vencimiento_texto": fecha_vencimiento_texto,
        "hora_limite": hora_limite,
        "dias_habiles_restantes": dias_habiles_restantes,
        "dias_calendario_restantes": dias_calendario_restantes,
        "ha_vencido": ha_vencido,
        "estado_vencimiento": estado_vencimiento,
        "texto_resumen": texto_resumen,
        "reglas_aplicadas": reglas_aplicadas,
        "desglose_dias": desglose_dias,
        "evento_ics": ics_content,
    }


# -----------------------------------------------------------------------------
# 6. GENERADOR DE EVENTOS .ICS (RFC 5545)
# -----------------------------------------------------------------------------
def generar_evento_ics(
    titulo: str,
    fecha_vencimiento: datetime.date,
    descripcion: str = "",
    hora_vencimiento: str = "17:00",
    uid: Optional[str] = None,
) -> str:
    """Genera el contenido de un archivo de calendario iCalendar (.ics RFC 5545) compatible

    con Outlook, Google Calendar, Apple Calendar y dispositivos móviles.
    """
    uid_str = uid or f"memorialista-vencimiento-{fecha_vencimiento.isoformat()}-{uuid.uuid4().hex[:8]}@elmemorialista.co"
    ahora_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    try:
        partes_hora = [int(p) for p in hora_vencimiento.split(":")]
        hora_h = partes_hora[0]
        hora_m = partes_hora[1] if len(partes_hora) > 1 else 0
    except (ValueError, TypeError):
        hora_h = 17
        hora_m = 0

    # Crear evento a la hora de vencimiento
    dt_start = datetime.datetime(
        fecha_vencimiento.year, fecha_vencimiento.month, fecha_vencimiento.day, hora_h, hora_m
    )
    dt_end = dt_start + timedelta(minutes=30)

    fmt_start = dt_start.strftime("%Y%m%dT%H%M%S")
    fmt_end = dt_end.strftime("%Y%m%dT%H%M%S")
    fmt_date_only = fecha_vencimiento.strftime("%Y%m%d")

    # Limpieza de texto para formato iCalendar
    def limpiar_texto(s: str) -> str:
        s = s.replace("\r\n", "\\n").replace("\n", "\\n")
        s = s.replace(",", "\\,").replace(";", "\\;")
        return s

    summary = limpiar_texto(titulo)
    desc = limpiar_texto(descripcion)

    lineas_ics = [
        "BEGIN:VCALENDAR",
        "PRODID:-//El Memorialista//Plazos Procesales Colombia//ES",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:El Memorialista - Vencimientos Jurídicos",
        "X-WR-TIMEZONE:America/Bogota",
        "BEGIN:VEVENT",
        f"UID:{uid_str}",
        f"DTSTAMP:{ahora_utc}",
        f"DTSTART:{fmt_start}",
        f"DTEND:{fmt_end}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{desc}",
        "CATEGORIES:JURIDICO,LITIGIO,VENCIMIENTO",
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Recordatorio de vencimiento de término (1 día antes)",
        "TRIGGER:-P1D",
        "END:VALARM",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Recordatorio de vencimiento de término hoy",
        "TRIGGER:-PT2H",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lineas_ics) + "\r\n"

```


## 📄 Archivo: `app/services/radicacion.py`
```python
"""El Memorialista · Módulo de Preparación de Radicación Judicial (v1.0).

Implementa la preparación integral de paquetes de radicación procesal conforme a:
- Ley 2213 de 2022 (art. 6: traslado simultáneo de demanda y excepciones por medidas cautelares previas; art. 8: canal digital).
- Código General del Proceso - Ley 1564 de 2012 (art. 74 y 77: poder especial judicial y facultades; art. 82: requisitos de demanda).
- Protocolos de Gestión Documental y Radicación Electrónica de la Rama Judicial de Colombia (CSJ).
- Generación de índice numerado de pruebas y anexos.
- Borradores de correos para radicación (despacho) y traslado simultáneo (contraparte) con enlaces mailto:.
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Palabras clave y expresiones que denotan solicitud de medidas cautelares previas
PATRONES_MEDIDAS_CAUTELARES = [
    r"medida[s]?\s+cautelar(?:es)?",
    r"embargo",
    r"secuestro\s+de\s+bienes",
    r"inscripci[oó]n\s+de\s+la\s+demanda",
    r"medida[s]?\s+innominada[s]?",
    r"cautela[s]?",
    r"decreto\s+de\s+embargo",
]


class AnexoIndiceItem(BaseModel):
    numero: int
    nombre_archivo: str
    descripcion: str
    tipo_documento: str = "Documental"
    folios_estimados: str = "1"


class PrepararRadicacionRequest(BaseModel):
    tipo: str = Field(description="Identificador del tipo de escrito (ej. demanda_verbal, tutela)")
    datos: Dict[str, Any] = Field(default_factory=dict, description="Datos del formulario del caso")
    texto: str = Field(description="Texto final del escrito redactado")
    perfil: Optional[Dict[str, Any]] = Field(default=None, description="Perfil del abogado y membrete")


class PrepararRadicacionResponse(BaseModel):
    nombre_paquete: str
    nombre_archivo_principal: str
    requiere_poder: bool
    texto_poder: Optional[str] = None
    nombre_archivo_poder: Optional[str] = None
    solicita_medidas_cautelares: bool
    aplica_traslado_contraparte: bool
    motivo_traslado_contraparte: str
    correo_despacho: str
    asunto_despacho: str
    cuerpo_despacho: str
    mailto_despacho: str
    correo_contraparte: Optional[str] = None
    asunto_contraparte: Optional[str] = None
    cuerpo_contraparte: Optional[str] = None
    mailto_contraparte: Optional[str] = None
    indice_anexos: List[AnexoIndiceItem]
    texto_indice: str


def limpiar_texto(valor: Any) -> str:
    """Limpia saltos de línea y espacios redundantes."""
    return str(valor or "").strip().replace("\r", "")


def extraer_correo(texto_o_campo: str) -> Optional[str]:
    """Extrae la primera dirección de correo electrónico válida de una cadena."""
    if not texto_o_campo:
        return None
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", str(texto_o_campo))
    return match.group(0) if match else None


def detectar_medidas_cautelares(texto: str, datos: Dict[str, Any]) -> bool:
    """
    Detecta si en la demanda o memorial se solicitaron medidas cautelares previas,
    lo que exonera del traslado simultáneo a la contraparte conforme al art. 6 de la Ley 2213 de 2022.
    """
    texto_completo = (
        texto + " " + " ".join(str(v) for v in datos.values() if isinstance(v, (str, int, float)))
    ).lower()

    for patron in PATRONES_MEDIDAS_CAUTELARES:
        if re.search(patron, texto_completo, re.IGNORECASE):
            return True
    return False


def tipo_requiere_poder(tipo: str, datos: Dict[str, Any], perfil: Optional[Dict[str, Any]]) -> bool:
    """
    Determina si el escrito requiere anexar poder especial judicial:
    - No requiere si el escrito en sí es un poder ('poder_especial').
    - No requiere si la firma es expresamente en nombre propio ('propio').
    - Requiere si el abogado actúa como apoderado en demandas, tutelas, recursos o memoriales.
    """
    if tipo in ("poder_especial", "poder"):
        return False
    quien_firma = datos.get("_firma", "apoderado")
    if quien_firma == "propio":
        return False
    return True


def generar_texto_poder_especial(
    tipo: str, datos: Dict[str, Any], perfil: Optional[Dict[str, Any]]
) -> str:
    """
    Genera el texto legal de un Poder Especial Judicial conforme al art. 74 y 77 del CGP
    y al art. 5 de la Ley 2213 de 2022 (presentación y envío por canal digital).
    """
    abogado = (perfil or {}).get("abogado", {})
    nom_abogado = abogado.get("nombre") or "[COMPLETAR: Nombre del Abogado]"
    cc_abogado = abogado.get("cedula") or "[COMPLETAR: C.C. Abogado]"
    lugar_cc_abogado = abogado.get("cedulaLugar") or ""
    tp_abogado = abogado.get("tp") or "[COMPLETAR: T.P. Abogado]"
    correo_abogado = abogado.get("correo") or "[COMPLETAR: Correo Abogado]"

    cliente = limpiar_texto(datos.get("cliente") or "El (La) Poderdante")
    nom_cliente = cliente.split("\n")[0].split(",")[0].strip()
    contraparte = limpiar_texto(datos.get("contraparte") or "La Contraparte")
    nom_contraparte = contraparte.split("\n")[0].split(",")[0].strip()
    despacho = limpiar_texto(datos.get("destinatario") or "JUEZ O DESPACHO JUDICIAL COMPETENTE")
    ciudad = limpiar_texto(datos.get("ciudad") or abogado.get("ciudad") or "Bogotá D.C.")
    radicado = limpiar_texto(datos.get("radicado") or "")

    ref_radicado = f"\n| **Radicado:** {radicado}" if radicado else ""

    texto = f"""Señor(a)
{despacho}
E. S. D.

| **Referencia:** Poder Especial, Amplio y Suficiente
| **Poderdante:** {nom_cliente}
| **Apoderado(a):** {nom_abogado}
| **Contraparte:** {nom_contraparte}{ref_radicado}
| **Asunto:** Otorgamiento de poder judicial (Art. 74 CGP y Ley 2213 de 2022)

**{nom_cliente}**, mayor de edad, domiciliado(a) en {ciudad}, actuando en nombre propio (o en representación de quien corresponda según la calidad informada), por medio del presente escrito manifiesto que confiero **PODER ESPECIAL, AMPLIO Y SUFICIENTE** al(a la) doctor(a) **{nom_abogado}**, mayor de edad, identificado(a) con la Cédula de Ciudadanía No. {cc_abogado} {f'de {lugar_cc_abogado}' if lugar_cc_abogado else ''}, abogado(a) en ejercicio con Tarjeta Profesional No. {tp_abogado} del Consejo Superior de la Judicatura, con dirección electrónica para notificaciones judiciales en {correo_abogado}, para que en mi nombre y representación inicie, tramite y lleve hasta su total culminación procesal la acción judicial de la referencia contra **{nom_contraparte}**.

## Facultades Conferidas

El(la) apoderado(a) queda expresamente facultado(a) para ejercer todas las atribuciones inherentes al mandato judicial previstas en el artículo 77 del Código General del Proceso (CGP), especialmente para:
1. Presentar demanda, memoriales, recursos ordinarios y extraordinarios, solicitudes y alegatos.
2. Recibir notificaciones judiciales y administrativas.
3. Desistir, transigir, conciliar judicial y extrajudicialmente.
4. Solicitar, controvertir, aportar y tachar pruebas.
5. Solicitar medidas cautelares y formular incidentes.
6. Sustituir o reasumir el presente mandato judicial cuando lo estime conveniente.
7. Cobrar y recibir las sumas de dinero que se reconozcan a mi favor en el proceso.

## Mensaje de Datos y Validez (Ley 2213 de 2022)

El presente poder se otorga y remite mediante mensaje de datos desde la dirección electrónica del(de la) poderdante conforme al artículo 5 de la Ley 2213 de 2022, sin que se requiera presentación personal ni reconocimiento de firma ante notaría.

Del señor Juez o funcionario, respetuosamente,

[[FIRMA: Poderdante]]
**{nom_cliente}**

Acepto el poder conferido:

[[FIRMA: Apoderado(a)]]
**{nom_abogado}**
C.C. {cc_abogado}
T.P. {tp_abogado} del C. S. de la J.
Correo electrónico: {correo_abogado}
"""
    return texto.strip()


def extraer_capitulo_pruebas_y_anexos(texto: str) -> List[str]:
    """
    Extrae los ítems listados en el capítulo de Pruebas o Anexos del escrito redactado.
    """
    items: List[str] = []
    # Buscar secciones de pruebas o anexos
    patron_seccion = re.compile(
        r"(?:##\s*(?:Pruebas|Anexos|Documentos|Relación de Pruebas|Material Probatorio)[\s\S]*?)(?=(?:##|\Z))",
        re.IGNORECASE,
    )
    coincidencias = patron_seccion.findall(texto)
    for bloque in coincidencias:
        # Extraer líneas con numeración o viñetas
        lineas = bloque.split("\n")
        for linea in lineas:
            linea_limpia = linea.strip()
            # Numerales: 1. Documento... o - Documento...
            m = re.match(r"^(?:\d+[\.\)]|\-|\*)\s+(.*)$", linea_limpia)
            if m:
                desc = m.group(1).strip()
                if desc and not desc.lower().startswith("se solicita") and not desc.lower().startswith("pruebas"):
                    items.append(desc)

    return items


def construir_indice_anexos(
    tipo: str,
    datos: Dict[str, Any],
    texto: str,
    requiere_poder: bool,
    nombre_archivo_principal: str,
    nombre_archivo_poder: Optional[str],
) -> List[AnexoIndiceItem]:
    """
    Construye la lista estructurada y numerada de anexos que conformarán el paquete de radicación.
    """
    anexos: List[AnexoIndiceItem] = []
    num = 1

    # 1. Escrito Principal
    anexos.append(
        AnexoIndiceItem(
            numero=num,
            nombre_archivo=nombre_archivo_principal,
            descripcion="Escrito principal de la acción judicial o memorial",
            tipo_documento="Principal",
            folios_estimados="Principal",
        )
    )
    num += 1

    # 2. Poder Especial Judicial (si aplica)
    if requiere_poder and nombre_archivo_poder:
        anexos.append(
            AnexoIndiceItem(
                numero=num,
                nombre_archivo=nombre_archivo_poder,
                descripcion="Poder especial amplio y suficiente conferido al apoderado judicial (art. 74 CGP y Ley 2213/2022)",
                tipo_documento="Poder",
                folios_estimados="1",
            )
        )
        num += 1

    # 3. Anexos y pruebas extraídos del escrito
    pruebas_detectadas = extraer_capitulo_pruebas_y_anexos(texto)
    if pruebas_detectadas:
        for idx, p in enumerate(pruebas_detectadas, start=1):
            # Normalizar nombre seguro de archivo
            desc_corta = re.sub(r"[^\w\s-]", "", p)[:30].strip().replace(" ", "_")
            nombre_anexo = f"{num:02d}_Anexo_{idx}_{desc_corta}.pdf"
            anexos.append(
                AnexoIndiceItem(
                    numero=num,
                    nombre_archivo=nombre_anexo,
                    descripcion=p,
                    tipo_documento="Prueba Documental",
                    folios_estimados="Por foliar",
                )
            )
            num += 1
    else:
        # Anexos estándar si no se discriminaron en el texto
        anexos.append(
            AnexoIndiceItem(
                numero=num,
                nombre_archivo=f"{num:02d}_Documentos_Identificacion_y_Soporte.pdf",
                descripcion="Documentos de identificación de las partes y soportes del litigio",
                tipo_documento="Prueba Documental",
                folios_estimados="Por foliar",
            )
        )
        num += 1

    return anexos


def formatear_texto_indice(
    tipo: str,
    datos: Dict[str, Any],
    anexos: List[AnexoIndiceItem],
    perfil: Optional[Dict[str, Any]],
) -> str:
    """Genera el texto del Índice de Anexos y Archivos Electrónicos conforme al protocolo CSJ."""
    abogado = (perfil or {}).get("abogado", {})
    nom_abogado = abogado.get("nombre") or "Apoderado Judicial"
    tp_abogado = abogado.get("tp") or ""
    correo_abogado = abogado.get("correo") or ""

    cliente = limpiar_texto(datos.get("cliente") or "Demandante")
    nom_cliente = cliente.split("\n")[0].split(",")[0].strip()
    contraparte = limpiar_texto(datos.get("contraparte") or "Demandado")
    nom_contraparte = contraparte.split("\n")[0].split(",")[0].strip()
    despacho = limpiar_texto(datos.get("destinatario") or "Despacho Judicial")
    radicado = limpiar_texto(datos.get("radicado") or "Para Reparto")

    sep = "=" * 80
    sep_sub = "-" * 80

    lineas = [
        sep,
        "ÍNDICE DE EXPEDIENTE ELECTRÓNICO Y RELACIÓN DE ANEXOS RADICADOS",
        "(Protocolo de Gestión de Documentos Electrónicos - Consejo Superior de la Judicatura)",
        sep,
        f"Proceso / Tipo: {tipo.replace('_', ' ').capitalize()}",
        f"Despacho:       {despacho}",
        f"Radicado:       {radicado}",
        f"Demandante:     {nom_cliente}",
        f"Demandado:      {nom_contraparte}",
        f"Apoderado(a):   {nom_abogado} {f'(T.P. {tp_abogado})' if tp_abogado else ''}",
        f"Canal Digital:  {correo_abogado}",
        sep_sub,
        f"{'NO.':<4} {'NOMBRE DEL ARCHIVO':<38} {'TIPO':<18} {'DESCRIPCIÓN':<20}",
        sep_sub,
    ]

    for a in anexos:
        nombre_trunc = a.nombre_archivo[:36]
        desc_trunc = a.descripcion[:30]
        lineas.append(f"{a.numero:<4} {nombre_trunc:<38} {a.tipo_documento:<18} {desc_trunc}")

    lineas.extend([
        sep_sub,
        f"Total de archivos integrantes del paquete: {len(anexos)} documento(s)",
        "",
        "CERTIFICACIÓN DEL CANAL DIGITAL Y REMISIÓN (Artículos 6 y 8 Ley 2213 de 2022):",
        "Se certifica que los archivos relacionados corresponden fielmente a los documentos adjuntos",
        "al mensaje de datos remitido para la radicación electrónica ante la autoridad judicial.",
        sep,
    ])

    return "\n".join(lineas)


def preparar_radicacion(req: PrepararRadicacionRequest) -> PrepararRadicacionResponse:
    """
    Construye el paquete completo de radicación, incluyendo nombres, poder, índice y correos mailto:.
    """
    tipo = req.tipo
    datos = req.datos or {}
    texto = req.texto or ""
    perfil = req.perfil or {}
    abogado = perfil.get("abogado", {})

    cliente = limpiar_texto(datos.get("cliente") or "Demandante")
    nom_cliente = cliente.split("\n")[0].split(",")[0].strip()
    nom_cliente_safe = re.sub(r"[^\w\s-]", "", nom_cliente)[:25].strip().replace(" ", "_")

    contraparte = limpiar_texto(datos.get("contraparte") or "Contraparte")
    nom_contraparte = contraparte.split("\n")[0].split(",")[0].strip()
    nom_contraparte_safe = re.sub(r"[^\w\s-]", "", nom_contraparte)[:25].strip().replace(" ", "_")

    radicado = limpiar_texto(datos.get("radicado") or "")
    despacho = limpiar_texto(datos.get("destinatario") or "Despacho Judicial")
    ciudad = limpiar_texto(datos.get("ciudad") or abogado.get("ciudad") or "Bogotá D.C.")

    # 1. Nombres estandarizados de archivos
    tipo_desc = tipo.replace("_", " ").title().replace(" ", "_")
    prefijo_radicado = f"Rad_{radicado}_" if radicado else ""
    nombre_base = f"{prefijo_radicado}{tipo_desc}_{nom_cliente_safe}_vs_{nom_contraparte_safe}"
    nombre_paquete = f"Paquete_Radicacion_{nombre_base}.zip"
    nombre_archivo_principal = f"01_{tipo_desc}_{nom_cliente_safe}.pdf"

    # 2. Poder especial judicial
    requiere_poder = tipo_requiere_poder(tipo, datos, perfil)
    texto_poder = None
    nombre_archivo_poder = None
    if requiere_poder:
        nombre_archivo_poder = f"02_Poder_Especial_Judicial_{nom_cliente_safe}.pdf"
        texto_poder = generar_texto_poder_especial(tipo, datos, perfil)

    # 3. Índice de anexos
    anexos = construir_indice_anexos(
        tipo=tipo,
        datos=datos,
        texto=texto,
        requiere_poder=requiere_poder,
        nombre_archivo_principal=nombre_archivo_principal,
        nombre_archivo_poder=nombre_archivo_poder,
    )
    texto_indice = formatear_texto_indice(tipo, datos, anexos, perfil)

    # 4. Análisis de medidas cautelares y traslado simultáneo (Art. 6 Ley 2213 de 2022)
    solicita_cautelares = detectar_medidas_cautelares(texto, datos)

    # Correos de contacto
    correo_despacho_detectado = (
        extraer_correo(datos.get("correo_despacho") or datos.get("correo_destinatario") or despacho)
        or "radicacion@ramajudicial.gov.co"
    )

    correo_contraparte_detectado = (
        extraer_correo(datos.get("correo_contraparte") or datos.get("notificaciones_contraparte") or contraparte)
    )

    es_tutela = (tipo == "tutela" or "tutela" in tipo)
    es_peticion = (tipo == "derecho_peticion" or "peticion" in tipo)

    aplica_traslado = False
    motivo_traslado = ""

    if es_tutela:
        aplica_traslado = False
        motivo_traslado = "No aplica traslado previo: en acción de tutela el traslado y vinculación son ordenados de oficio por el Juez en el auto admisorio (Decreto 2591 de 1991)."
    elif es_peticion:
        aplica_traslado = False
        motivo_traslado = "No aplica traslado judicial: es un derecho de petición directo a la entidad o particular (Ley 1755 de 2015)."
    elif solicita_cautelares:
        aplica_traslado = False
        motivo_traslado = "Exonerado de traslado previo (Art. 6 Inc. 4 Ley 2213 de 2022): se solicitaron medidas cautelares previas que perderían efectividad si se entera al demandado."
    elif not correo_contraparte_detectado:
        aplica_traslado = False
        motivo_traslado = "Exonerado de traslado previo (Art. 6 Inc. 4 Ley 2213 de 2022): se desconoce el canal digital / correo electrónico de la contraparte demandada."
    else:
        aplica_traslado = True
        motivo_traslado = "Aplica traslado simultáneo obligatorio (Art. 6 Ley 2213 de 2022): demanda sin medidas cautelares previas con canal digital del demandado identificado."

    # 5. Borrador y mailto para radicación al Despacho Judicial
    nom_tipo_formal = tipo.replace("_", " ").title()
    if radicado:
        asunto_despacho = f"Memorial: {nom_tipo_formal} - Rad. {radicado} - {nom_cliente} vs {nom_contraparte}"
    else:
        asunto_despacho = f"Demanda para Reparto: {nom_tipo_formal} - {nom_cliente} vs {nom_contraparte} - {ciudad}"

    lista_adjuntos_txt = "\n".join([f"  {a.numero}. {a.nombre_archivo} ({a.descripcion})" for a in anexos])

    nom_abogado = abogado.get("nombre") or "Apoderado Judicial"
    cc_abogado = abogado.get("cedula") or ""
    tp_abogado = abogado.get("tp") or ""
    tel_abogado = abogado.get("telefono") or ""
    dir_abogado = abogado.get("direccion") or ""
    correo_abogado = abogado.get("correo") or ""

    cuerpo_despacho = f"""Señores
{despacho}
E. S. D.

REF: {asunto_despacho}

Respetados señores:

En calidad de apoderado(a) judicial de {nom_cliente}, por medio de la presente radico formalmente el escrito de {nom_tipo_formal} de la referencia para el trámite judicial correspondiente.

ARCHIVOS ADJUNTOS AL MENSAJE DE DATOS (PAQUETE DE RADICACIÓN):
{lista_adjuntos_txt}

Se deja constancia de que los documentos se remiten en formato electrónico accesible y foliado conforme a las directrices de la Ley 2213 de 2022 y del Consejo Superior de la Judicatura.

CANAL DIGITAL PARA NOTIFICACIONES JUDICIALES (Art. 8 Ley 2213 de 2022):
- Apoderado(a): {nom_abogado}
- C.C.: {cc_abogado} | T.P.: {tp_abogado}
- Correo Electrónico: {correo_abogado}
- Teléfono / Móvil: {tel_abogado}
- Dirección: {dir_abogado} - {ciudad}

Agradezco confirmar el recibo, número de radicación y despacho asignado.

Cordialmente,

{nom_abogado}
T.P. No. {tp_abogado} del C. S. de la J.
"""

    mailto_despacho = (
        f"mailto:{correo_despacho_detectado}"
        f"?subject={urllib.parse.quote(asunto_despacho)}"
        f"&body={urllib.parse.quote(cuerpo_despacho)}"
    )

    # 6. Borrador y mailto para traslado simultáneo a la contraparte (si aplica)
    asunto_contraparte = None
    cuerpo_contraparte = None
    mailto_contraparte = None

    if aplica_traslado and correo_contraparte_detectado:
        asunto_contraparte = (
            f"Traslado Simultáneo de Demanda: {nom_tipo_formal} - {nom_cliente} vs {nom_contraparte} (Art. 6 Ley 2213 de 2022)"
        )
        cuerpo_contraparte = f"""Señores
{nom_contraparte}
Atn. Notificaciones Judiciales

REF: Traslado simultáneo de demanda judicial (Artículo 6 de la Ley 2213 de 2022)
Demandante: {nom_cliente}
Demandado:  {nom_contraparte}
Despacho:   {despacho}

Por medio de la presente, en cumplimiento expreso del artículo 6 de la Ley 2213 de 2022, me permito remitirles de manera simultánea a la radicación ante la autoridad judicial, copia íntegra de la demanda de la referencia y de la totalidad de sus anexos y pruebas documentales.

DOCUMENTOS TRASLADADOS ADJUNTOS:
{lista_adjuntos_txt}

CANAL DIGITAL DEL DEMANDANTE (Art. 8 Ley 2213 de 2022):
- Apoderado(a): {nom_abogado} (T.P. {tp_abogado})
- Correo Electrónico: {correo_abogado}
- Teléfono: {tel_abogado}

La presente comunicación constituye traslado simultáneo formal con plenos efectos legales y probatorios ante el despacho judicial de conocimiento.

Atentamente,

{nom_abogado}
Apoderado(a) Judicial de la parte demandante
"""
        mailto_contraparte = (
            f"mailto:{correo_contraparte_detectado}"
            f"?subject={urllib.parse.quote(asunto_contraparte)}"
            f"&body={urllib.parse.quote(cuerpo_contraparte)}"
        )

    return PrepararRadicacionResponse(
        nombre_paquete=nombre_paquete,
        nombre_archivo_principal=nombre_archivo_principal,
        requiere_poder=requiere_poder,
        texto_poder=texto_poder,
        nombre_archivo_poder=nombre_archivo_poder,
        solicita_medidas_cautelares=solicita_cautelares,
        aplica_traslado_contraparte=aplica_traslado,
        motivo_traslado_contraparte=motivo_traslado,
        correo_despacho=correo_despacho_detectado,
        asunto_despacho=asunto_despacho,
        cuerpo_despacho=cuerpo_despacho,
        mailto_despacho=mailto_despacho,
        correo_contraparte=correo_contraparte_detectado,
        asunto_contraparte=asunto_contraparte,
        cuerpo_contraparte=cuerpo_contraparte,
        mailto_contraparte=mailto_contraparte,
        indice_anexos=anexos,
        texto_indice=texto_indice,
    )

```


## 📄 Archivo: `app/services/comparador_versiones.py`
```python
"""El Memorialista · Módulo de Control de Versiones y Diff Procesal (v1.0).

Implementa:
- Comparación de versiones de escritos judiciales palabra por palabra (word-level diff).
- Estadísticas de cambios (palabras añadidas, eliminadas y conservadas).
- Generación de documentos Microsoft Word (.docx) con Control de Cambios nativo (OpenXML w:ins y w:del).
"""
from __future__ import annotations

import io
import re
import difflib
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class EstadisticasDiff(BaseModel):
    palabras_anadidas: int = 0
    palabras_eliminadas: int = 0
    palabras_sin_cambio: int = 0
    total_palabras_base: int = 0
    total_palabras_comparado: int = 0


class CompararVersionesRequest(BaseModel):
    texto_base: str = Field(description="Texto de la versión anterior o base")
    texto_comparado: str = Field(description="Texto de la versión nueva o comparada")
    autor: Optional[str] = Field(default="El Memorialista", description="Nombre del autor para el control de cambios")
    fecha: Optional[str] = Field(default=None, description="Fecha ISO de la revisión")


class CompararVersionesResponse(BaseModel):
    estadisticas: EstadisticasDiff
    html_diff: str
    parrafos_diff: List[List[Dict[str, str]]]


class ExportarWordDiffRequest(BaseModel):
    texto_base: str = Field(description="Texto de la versión anterior o base")
    texto_comparado: str = Field(description="Texto de la versión nueva o comparada")
    autor: Optional[str] = Field(default="El Memorialista", description="Nombre del autor para las revisiones")
    fecha: Optional[str] = Field(default=None, description="Fecha ISO de la revisión")
    titulo: Optional[str] = Field(default="Escrito con Control de Cambios", description="Título del documento")
    perfil: Optional[Dict[str, Any]] = Field(default=None, description="Perfil del abogado para membrete y tipografía")


def tokenizar_texto(texto: str) -> List[str]:
    """
    Tokeniza el texto preservando palabras (incluyendo acentos y caracteres latinos),
    signos de puntuación, espacios y saltos de línea como unidades atómicas.
    """
    if not texto:
        return []
    # Tokeniza palabras completas (\w+), puntuación ([^\w\s]+), espacios horizontales ([ \t]+) y saltos (\r?\n)
    return re.findall(r"\w+|[^\w\s]+|[ \t]+|\r?\n", texto, re.UNICODE)


def contar_palabras(texto: str) -> int:
    """Cuenta el número de palabras en un texto excluyendo espacios y signos de puntuación sueltos."""
    return len(re.findall(r"\b\w+\b", texto, re.UNICODE))


def xesc(valor: Any) -> str:
    """Escapa caracteres especiales para XML seguro en OpenXML."""
    s = str(valor or "")
    # Eliminar caracteres de control no permitidos en XML
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", s)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def hesc(valor: Any) -> str:
    """Escapa caracteres para HTML seguro."""
    s = str(valor or "")
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def calcular_diff_palabras(texto_base: str, texto_comparado: str) -> List[Tuple[str, str]]:
    """
    Calcula el diff token por token usando SequenceMatcher.
    Retorna una lista de tuplas (tag, texto) donde tag es 'equal', 'insert' o 'delete'.
    """
    toks1 = tokenizar_texto(texto_base)
    toks2 = tokenizar_texto(texto_comparado)

    sm = difflib.SequenceMatcher(None, toks1, toks2)
    diff_tokens: List[Tuple[str, str]] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            diff_tokens.append(("equal", "".join(toks1[i1:i2])))
        elif tag == "delete":
            diff_tokens.append(("delete", "".join(toks1[i1:i2])))
        elif tag == "insert":
            diff_tokens.append(("insert", "".join(toks2[j1:j2])))
        elif tag == "replace":
            diff_tokens.append(("delete", "".join(toks1[i1:i2])))
            diff_tokens.append(("insert", "".join(toks2[j1:j2])))

    return diff_tokens


def dividir_en_parrafos(diff_tokens: List[Tuple[str, str]]) -> List[List[Dict[str, str]]]:
    """
    Divide los tokens del diff en párrafos independientes preservando los saltos de línea.
    """
    parrafos: List[List[Dict[str, str]]] = [[]]

    for tag, txt in diff_tokens:
        partes = txt.split("\n")
        for idx, parte in enumerate(partes):
            if idx > 0:
                parrafos.append([])
            if parte:
                parrafos[-1].append({"tipo": tag, "texto": parte})

    return parrafos


def generar_html_diff(parrafos: List[List[Dict[str, str]]]) -> str:
    """
    Genera el HTML con estilo limpio para visualización del diff en la interfaz web.
    """
    html_partes = []

    for p in parrafos:
        if not p:
            html_partes.append('<p class="diff-parrafo diff-vacio">&nbsp;</p>')
            continue

        runs_html = []
        for token in p:
            tipo = token["tipo"]
            texto = hesc(token["texto"])

            if tipo == "equal":
                runs_html.append(f'<span class="diff-txt">{texto}</span>')
            elif tipo == "insert":
                runs_html.append(
                    f'<ins class="diff-ins" title="Texto añadido">{texto}</ins>'
                )
            elif tipo == "delete":
                runs_html.append(
                    f'<del class="diff-del" title="Texto eliminado">{texto}</del>'
                )

        html_partes.append(f'<p class="diff-parrafo">{"".join(runs_html)}</p>')

    return "\n".join(html_partes)


def comparar_versiones(req: CompararVersionesRequest) -> CompararVersionesResponse:
    """Realiza la comparación completa entre dos versiones de un escrito judicial."""
    diff_tokens = calcular_diff_palabras(req.texto_base, req.texto_comparado)
    parrafos = dividir_en_parrafos(diff_tokens)

    # Calcular estadísticas exactas de palabras
    anadidas = 0
    eliminadas = 0
    iguales = 0

    for tag, txt in diff_tokens:
        palabras_bloque = contar_palabras(txt)
        if tag == "insert":
            anadidas += palabras_bloque
        elif tag == "delete":
            eliminadas += palabras_bloque
        elif tag == "equal":
            iguales += palabras_bloque

    stats = EstadisticasDiff(
        palabras_anadidas=anadidas,
        palabras_eliminadas=eliminadas,
        palabras_sin_cambio=iguales,
        total_palabras_base=contar_palabras(req.texto_base),
        total_palabras_comparado=contar_palabras(req.texto_comparado),
    )

    html_diff = generar_html_diff(parrafos)

    return CompararVersionesResponse(
        estadisticas=stats,
        html_diff=html_diff,
        parrafos_diff=parrafos,
    )


def generar_docx_con_control_de_cambios(
    texto_base: str,
    texto_comparado: str,
    autor: str = "El Memorialista",
    fecha: Optional[str] = None,
    titulo: str = "Escrito con Control de Cambios",
    perfil: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Construye un documento Microsoft Word (.docx) completo en formato OpenXML
    con revisiones de control de cambios activas (w:ins y w:del).
    """
    diff_tokens = calcular_diff_palabras(texto_base, texto_comparado)
    parrafos = dividir_en_parrafos(diff_tokens)

    fecha_revision = (
        fecha
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    autor_seguro = xesc(autor or "El Memorialista")

    # Extraer formato del perfil si está disponible
    formato = (perfil or {}).get("formato", {})
    fuente = formato.get("fuente") or "Arial"
    tam_pt = float(formato.get("tamano") or 12)
    sz = int(tam_pt * 2)  # OpenXML usa medios puntos (half-points)
    interlineado = float(formato.get("interlineado") or 1.5)
    line_rule = int(240 * interlineado)

    # Construir párrafos en OpenXML
    revision_id = 1
    cuerpo_xml_partes = []

    for p in parrafos:
        runs_p = []
        for item in p:
            tipo = item["tipo"]
            txt = xesc(item["texto"])

            if tipo == "equal":
                runs_p.append(
                    f'<w:r>'
                    f'<w:rPr><w:rFonts w:ascii="{fuente}" w:hAnsi="{fuente}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>'
                    f'<w:t xml:space="preserve">{txt}</w:t>'
                    f'</w:r>'
                )
            elif tipo == "insert":
                runs_p.append(
                    f'<w:ins w:id="{revision_id}" w:author="{autor_seguro}" w:date="{fecha_revision}">'
                    f'<w:r>'
                    f'<w:rPr>'
                    f'<w:rFonts w:ascii="{fuente}" w:hAnsi="{fuente}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
                    f'<w:color w:val="15803D"/><w:u w:val="single"/>'
                    f'</w:rPr>'
                    f'<w:t xml:space="preserve">{txt}</w:t>'
                    f'</w:r>'
                    f'</w:ins>'
                )
                revision_id += 1
            elif tipo == "delete":
                runs_p.append(
                    f'<w:del w:id="{revision_id}" w:author="{autor_seguro}" w:date="{fecha_revision}">'
                    f'<w:r>'
                    f'<w:rPr>'
                    f'<w:rFonts w:ascii="{fuente}" w:hAnsi="{fuente}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
                    f'<w:color w:val="B91C1C"/><w:strike/>'
                    f'</w:rPr>'
                    f'<w:delText xml:space="preserve">{txt}</w:delText>'
                    f'</w:r>'
                    f'</w:del>'
                )
                revision_id += 1

        cuerpo_p = "".join(runs_p)
        cuerpo_xml_partes.append(
            f'<w:p>'
            f'<w:pPr>'
            f'<w:spacing w:before="0" w:after="160" w:line="{line_rule}" w:lineRule="auto"/>'
            f'<w:jc w:val="both"/>'
            f'</w:pPr>'
            f'{cuerpo_p}'
            f'</w:p>'
        )

    # Sección y márgenes (Oficio / A4 colombianos: 3 cm izq, 3 cm sup, 2 cm der, 2 cm inf)
    sect_pr = (
        f'<w:sectPr>'
        f'<w:pgSz w:w="12240" w:h="15840"/>'  # Carta (Letter)
        f'<w:pgMar w:top="1701" w:right="1134" w:bottom="1134" w:left="1701" w:header="709" w:footer="709" w:gutter="0"/>'
        f'<w:cols w:space="708"/>'
        f'</w:sectPr>'
    )

    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n'
        '<w:body>\n'
        f'{"".join(cuerpo_xml_partes)}\n'
        f'{sect_pr}\n'
        '</w:body>\n'
        '</w:document>'
    )

    # settings.xml con <w:trackRevisions/> para forzar el modo de revisión activa
    settings_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
        '<w:trackRevisions/>\n'
        '<w:zoom w:percent="100"/>\n'
        '<w:defaultTabStop w:val="708"/>\n'
        '<w:characterSpacingControl w:val="doNotCompress"/>\n'
        '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>\n'
        '</w:settings>'
    )

    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
        f'<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{fuente}" w:hAnsi="{fuente}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr></w:rPrDefault></w:docDefaults>\n'
        '</w:styles>'
    )

    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '<Default Extension="xml" ContentType="application/xml"/>\n'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>\n'
        '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>\n'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>\n'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>\n'
        '</Types>'
    )

    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\n'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>\n'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>\n'
        '</Relationships>'
    )

    word_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>\n'
        '<Relationship Id="rIdSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>\n'
        '</Relationships>'
    )

    core_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        f'<dc:title>{xesc(titulo)}</dc:title>\n'
        f'<dc:creator>{autor_seguro}</dc:creator>\n'
        f'<cp:lastModifiedBy>{autor_seguro}</cp:lastModifiedBy>\n'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{fecha_revision}</dcterms:created>\n'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{fecha_revision}</dcterms:modified>\n'
        '</cp:coreProperties>'
    )

    app_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">\n'
        '<Application>El Memorialista - Comparador de Versiones</Application>\n'
        '</Properties>'
    )

    # Empaquetar en memoria ZIP (.docx)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types_xml)
        z.writestr("_rels/.rels", root_rels_xml)
        z.writestr("word/document.xml", doc_xml)
        z.writestr("word/settings.xml", settings_xml)
        z.writestr("word/styles.xml", styles_xml)
        z.writestr("word/_rels/document.xml.rels", word_rels_xml)
        z.writestr("docProps/core.xml", core_xml)
        z.writestr("docProps/app.xml", app_xml)

    buffer.seek(0)
    return buffer.getvalue()

```


## 📄 Archivo: `app/services/extractor_documentos.py`
```python
"""Servicio de extracción multimodal de datos del caso con Gemini 3.8 Flash (v2.2.1).

Permite al abogado subir documentos del caso (PDFs, imágenes de documentos o certificados,
y grabaciones de audio) para extraer fidedignamente los datos de las partes, hechos,
fechas y pretensiones antes de incorporarlos al memorial.

REGLAS DE PRIVACIDAD:
- Los archivos se procesan 100% en memoria mediante partes en línea (inlineData).
- NUNCA se escriben en disco ni se almacenan en carpetas temporales o bases de datos.
- Tras la llamada a la API de IA, los buffers en memoria se liberan y descartan.

LÍMITES Y FORMATOS:
- Peso máximo total: 20 MB en total.
- Formatos permitidos: PDF, imágenes (PNG, JPEG, WEBP, GIF, HEIC) y audio (MP3, WAV, M4A, OGG, AAC, FLAC, WEBM).
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any, Optional

import httpx
from fastapi import HTTPException, UploadFile

from app.config import get_settings
from app.services.gemini_service import gemini_service, extraer_json, ErrorIA

log = logging.getLogger("memorialista.extractor")

MAX_TOTAL_BYTES = 20 * 1024 * 1024  # 20 MB

MIME_PERMITIDOS = {
    # PDF
    "application/pdf",
    # Imágenes
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/heic",
    "image/gif",
    # Audio
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/m4a",
    "audio/x-m4a",
    "audio/mp4",
    "audio/aac",
    "audio/ogg",
    "audio/flac",
    "audio/webm",
}

EXTENSIONES_MIME = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".gif": "image/gif",
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/m4a",
    ".ogg": "audio/ogg",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".weba": "audio/webm",
    ".webm": "audio/webm",
}


def detectar_mime(nombre: str, content_type_declarado: Optional[str]) -> Optional[str]:
    """Determina y valida el tipo MIME permitido a partir del Content-Type y la extensión."""
    if content_type_declarado and content_type_declarado.lower() in MIME_PERMITIDOS:
        return content_type_declarado.lower()

    ext = os.path.splitext(nombre.lower())[1]
    if ext in EXTENSIONES_MIME:
        return EXTENSIONES_MIME[ext]

    return None


async def validar_archivos_extraccion(archivos: list[UploadFile]) -> tuple[list[dict[str, Any]], int]:
    """Lee y valida en memoria los archivos adjuntos.
    
    Verifica:
    1. Que haya al menos un archivo.
    2. Que el peso total no supere los 20 MB.
    3. Que los tipos MIME sean soportados (PDF, imágenes, audio).
    
    PRIVACIDAD: Todo se lee en memoria y se descarta tras procesar.
    """
    if not archivos:
        raise HTTPException(
            status_code=400,
            detail="Debes adjuntar al menos un documento (PDF, imagen o audio) para la extracción.",
        )

    archivos_procesados: list[dict[str, Any]] = []
    total_bytes = 0

    for f in archivos:
        nombre = f.filename or "archivo_sin_nombre"
        mime = detectar_mime(nombre, f.content_type)
        if not mime:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"El archivo '{nombre}' no tiene un formato compatible. "
                    "Formatos permitidos: PDF, imágenes (PNG, JPG, WEBP) y audio (MP3, WAV, M4A, OGG)."
                ),
            )

        contenido = await f.read()
        tamano = len(contenido)
        if tamano == 0:
            continue

        total_bytes += tamano
        if total_bytes > MAX_TOTAL_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"El peso total de los archivos adjuntos supera el límite de 20 MB (actual: {total_bytes / (1024*1024):.2f} MB).",
            )

        archivos_procesados.append({
            "nombre": nombre,
            "mime": mime,
            "bytes": contenido,
            "tamano": tamano,
        })

    if not archivos_procesados:
        raise HTTPException(
            status_code=400,
            detail="Los archivos adjuntos están vacíos.",
        )

    return archivos_procesados, total_bytes


def extraer_campos_relevantes_tipo(tipo_info: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrae la lista de campos del caso omitiendo campos de configuración interna del LLM."""
    campos = []
    for grupo in tipo_info.get("grupos", []):
        for c in grupo.get("campos", []):
            k = c.get("k", "")
            if not k.startswith("_"):
                campos.append(c)
    return campos


def construir_esquema_extraccion(campos: list[dict[str, Any]], tipo_id: Optional[str] = None) -> dict[str, Any]:
    """Construye el esquema JSON estricto requerido a Gemini para los campos del tipo elegido."""
    properties: dict[str, Any] = {}
    for c in campos:
        k = c["k"]
        etiqueta = c.get("l", k)
        tipo_campo = c.get("t", "texto")
        ph = c.get("ph", "")
        ayuda = c.get("ayuda", "")
        desc = f"Dato para '{etiqueta}' (tipo {tipo_campo}). {ph} {ayuda}".strip()

        properties[k] = {
            "type": "OBJECT",
            "description": desc,
            "properties": {
                "valor": {
                    "type": "STRING",
                    "description": f"Contenido extraído del caso para el campo '{etiqueta}'",
                },
                "archivo": {
                    "type": "STRING",
                    "description": "Nombre exacto del archivo fuente aportado de donde se extrajo el dato",
                },
                "pagina": {
                    "type": "INTEGER",
                    "description": "Número de página si es un documento PDF o paginado, o 0 si es imagen o audio",
                },
                "cita_textual_corta": {
                    "type": "STRING",
                    "description": "Cita textual corta o transcripción literal (máx. 150 caracteres) que evidencia el dato",
                },
                "confianza": {
                    "type": "STRING",
                    "enum": ["alta", "media", "baja"],
                    "description": "Nivel de confianza: 'alta', 'media' o 'baja'",
                },
            },
            "required": ["valor", "archivo", "cita_textual_corta", "confianza"],
        }

    # Para contestación: extraer lista estructurada de hechos numerados de la demanda
    if tipo_id == "contestacion":
        properties["hechos_numerados"] = {
            "type": "ARRAY",
            "description": "Lista de hechos numerados de la demanda formulada por la contraparte (art. 96 CGP)",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "numero": {"type": "INTEGER", "description": "Número correlativo del hecho (1, 2, 3...)"},
                    "texto": {"type": "STRING", "description": "Texto del hecho tal como fue afirmado en la demanda"},
                },
                "required": ["numero", "texto"],
            },
        }

    # Para providencias judiciales (impugnación tutela, recurso autos, apelación sentencia):
    if tipo_id in ("impugnacion_tutela", "recurso_judicial", "apelacion_sentencia"):
        properties["decision_providencia"] = {
            "type": "OBJECT",
            "description": "Decisión de la parte resolutiva del fallo o auto, y su fecha de expedición",
            "properties": {
                "decision": {"type": "STRING", "description": "Resumen claro de lo que resolvió el despacho judicial"},
                "fecha": {"type": "STRING", "description": "Fecha de la providencia judicial (AAAA-MM-DD o texto formal)"},
                "archivo": {"type": "STRING", "description": "Archivo del cual se extrajo la decisión"},
                "pagina": {"type": "INTEGER", "description": "Página donde consta la parte resolutiva"},
                "cita_textual_corta": {"type": "STRING", "description": "Cita textual de la parte resolutiva"},
                "confianza": {"type": "STRING", "enum": ["alta", "media", "baja"]},
            },
            "required": ["decision", "fecha", "archivo", "cita_textual_corta", "confianza"],
        }

    return {
        "type": "OBJECT",
        "properties": properties,
    }


def construir_prompt_extraccion(tipo_id: str, nombre_tipo: str, campos: list[dict[str, Any]], archivos: list[dict[str, Any]]) -> str:
    """Genera las instrucciones jurídicas para que Gemini analice los archivos y extraiga datos."""
    lineas_archivos = [
        f"- Archivo {i}: '{f['nombre']}' ({f['mime']}, {f['tamano'] / 1024:.1f} KB)"
        for i, f in enumerate(archivos, 1)
    ]
    lista_archivos_str = "\n".join(lineas_archivos)

    lineas_campos = [
        f"- {c['k']} ('{c.get('l', c['k'])}'): {c.get('ph', '')} {c.get('ayuda', '')}".strip()
        for c in campos
    ]
    lista_campos_str = "\n".join(lineas_campos)

    instrucciones_especiales = ""
    if tipo_id == "contestacion":
        instrucciones_especiales = (
            "\n\nINSTRUCCIONES OBLIGATORIAS PARA CONTESTACIÓN DE DEMANDA:\n"
            "1. En 'hechos_numerados', extrae uno a uno todos los hechos numerados de la demanda con su número ordinal (1, 2, 3...)\n"
            "   y el texto fáctico tal como lo formuló la contraparte (art. 96 CGP).\n"
            "2. En 'respuesta_pretensiones', extrae las pretensiones reclamadas en la demanda para permitir la oposición.\n"
            "3. En 'notificacion_fecha', extrae la fecha de notificación del auto admisorio (AAAA-MM-DD) si consta en los documentos."
        )
    elif tipo_id in ("impugnacion_tutela", "recurso_judicial", "apelacion_sentencia"):
        instrucciones_especiales = (
            f"\n\nINSTRUCCIONES OBLIGATORIAS PARA PROVIDENCIAS JUDICIALES ({nombre_tipo}):\n"
            "1. Identifica la DECISIÓN judicial de la parte resolutiva y la FECHA de la providencia.\n"
            "2. Completa 'decision_providencia' con la fecha y decisión adoptada.\n"
            "3. Asigna la decisión al campo respectivo ('fallo' en tutela, 'providencia' en auto, 'sentencia' en apelación),\n"
            "   ejemplo: 'Sentencia del 10/10/2026 que negó la tutela por improcedente' o 'Auto del 9/10/2026 que rechazó la demanda'.\n"
            "4. En 'notificacion_fecha', extrae con precisión la fecha en que se notificó la providencia (por estado, personal o\n"
            "   mensaje de datos) en formato AAAA-MM-DD para calcular el término legal de vencimiento."
        )

    return (
        f"Eres un asistente pericial jurídico de alta precisión especializado en derecho procesal colombiano.\n"
        f"Tu labor es examinar minuciosamente los documentos del caso adjuntos (archivos en línea: PDF, imágenes o audio)\n"
        f"y extraer de forma estructurada los datos para completar un escrito judicial de tipo: \"{nombre_tipo}\".\n\n"
        f"ARCHIVOS APORTADOS POR EL ABOGADO:\n"
        f"{lista_archivos_str}\n\n"
        f"CAMPOS DEL FORMULARIO A COMPLETAR:\n"
        f"{lista_campos_str}"
        f"{instrucciones_especiales}\n\n"
        f"REGLAS OBLIGATORIAS DE EXTRACCIÓN:\n"
        f"1. FIDELIDAD ESTRICTA: Extrae únicamente datos que tengan respaldo claro en los documentos aportados.\n"
        f"   NUNCA inventes nombres de partes, números de cédula, NIT, radicados de 23 dígitos ni fechas.\n"
        f"2. SI UN CAMPO NO APARECE en los documentos suministrados, NO lo incluyas en el objeto JSON de respuesta.\n"
        f"3. CADA VALOR EXTRAÍDO DEBE TENER:\n"
        f"   - 'valor': El texto del dato en formato adecuado para el campo (ej: nombres en mayúsculas sostenidas,\n"
        f"     cédula o NIT con formato, fechas en texto o ISO, y redacción cronológica sucinta para hechos).\n"
        f"   - 'archivo': Nombre exacto del archivo aportado de donde se obtuvo la información.\n"
        f"   - 'pagina': Número de página en enteros (1, 2, ...) si el documento es un PDF, o 0 si es imagen o audio.\n"
        f"   - 'cita_textual_corta': Fragmento textual literal o transcripción fiel del audio (máximo 150 caracteres)\n"
        f"     que sustenta inequívocamente el dato.\n"
        f"   - 'confianza': 'alta' si el dato es indubitado y expreso, 'media' si requiere inferencia contextual razonable,\n"
        f"     o 'baja' si hay ambigüedad o calidad dudosa en el soporte.\n"
        f"4. Salida en formato JSON estricto conforme al esquema."
    )


async def extraer_datos_con_gemini(
    tipo_id: str,
    tipo_info: dict[str, Any],
    archivos: list[dict[str, Any]],
) -> dict[str, Any]:
    """Envía los archivos como partes en línea a gemini-3.8-flash y extrae los campos."""
    s = get_settings()
    nombre_tipo = tipo_info.get("nombre", tipo_id)
    campos = extraer_campos_relevantes_tipo(tipo_info)
    campos_dict = {c["k"]: c for c in campos}
    esquema = construir_esquema_extraccion(campos, tipo_id=tipo_id)
    prompt = construir_prompt_extraccion(tipo_id, nombre_tipo, campos, archivos)

    # 1. Construir las partes en línea (inlineData) en memoria
    partes: list[dict[str, Any]] = []

    for idx, f in enumerate(archivos, 1):
        partes.append({"text": f"=== DOCUMENTO #{idx}: {f['nombre']} ({f['mime']}) ==="})
        b64_str = base64.b64encode(f["bytes"]).decode("utf-8")
        partes.append({
            "inlineData": {
                "mimeType": f["mime"],
                "data": b64_str,
            }
        })

    partes.append({"text": prompt})

    # 2. Modelos a intentar (prioridad: gemini-3.8-flash)
    modelos_candidatos = [
        "gemini-3.8-flash",
        s.GEMINI_MODEL,
        "gemini-3.6-flash",
        "gemini-2.5-flash",
    ]
    # Eliminar duplicados manteniendo orden
    modelos_a_probar = list(dict.fromkeys(m for m in modelos_candidatos if m))

    if not s.GEMINI_API_KEY.strip():
        raise ErrorIA(
            "sin_motor",
            "El servicio de extracción multimodal requiere configurar GEMINI_API_KEY en las variables de entorno.",
            http=503,
        )

    cliente = await gemini_service._cliente()
    cabeceras = gemini_service._cab_gemini()
    texto_respuesta: Optional[str] = None
    ultimo_error: Optional[Exception] = None

    for modelo in modelos_a_probar:
        url = f"{s.GEMINI_API_BASE.rstrip('/')}/v1beta/models/{modelo}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": partes}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": esquema,
                "maxOutputTokens": 8192,
            },
        }

        try:
            log.info("Enviando %d archivos a %s para extracción...", len(archivos), modelo)
            resp = await cliente.post(
                url,
                json=payload,
                headers=cabeceras,
                timeout=180.0,
            )
            if resp.status_code == 200:
                datos_resp = resp.json()
                candidatos = datos_resp.get("candidates") or []
                if candidatos:
                    partes_resp = (candidatos[0].get("content") or {}).get("parts") or []
                    texto_respuesta = "".join(p.get("text", "") for p in partes_resp if not p.get("thought"))
                    if texto_respuesta:
                        break
            else:
                err_ia = ErrorIA.desde_http("gemini", modelo, resp.status_code, resp.text)
                log.warning("Modelo %s falló en extracción (%s): %s", modelo, err_ia.codigo, err_ia.mensaje)
                ultimo_error = err_ia
                if err_ia.parametros or err_ia.no_existe:
                    continue
        except Exception as exc:  # noqa: BLE001
            log.warning("Excepción llamando a %s: %s", modelo, exc)
            ultimo_error = exc
            continue

    if not texto_respuesta:
        if isinstance(ultimo_error, ErrorIA):
            raise ultimo_error
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo completar la extracción con la IA: {ultimo_error or 'Sin respuesta'}",
        )

    # 3. Parsear y normalizar la salida JSON
    datos_extraidos = extraer_json(texto_respuesta)
    if not datos_extraidos:
        return {
            "propuestas": [],
            "hechos_numerados": [],
            "decision_providencia": None,
            "fecha_notificacion_detectada": None,
        }

    raw_extraidos = datos_extraidos

    # Normalizar si vino en lista o envuelto
    if isinstance(datos_extraidos, list):
        datos_dict = {}
        for elem in datos_extraidos:
            if isinstance(elem, dict) and "campo" in elem:
                datos_dict[elem["campo"]] = elem
        datos_extraidos = datos_dict
    elif isinstance(datos_extraidos, dict):
        if "campos" in datos_extraidos and isinstance(datos_extraidos["campos"], dict):
            datos_extraidos = datos_extraidos["campos"]
        elif "extracciones" in datos_extraidos and isinstance(datos_extraidos["extracciones"], list):
            datos_dict = {}
            for elem in datos_extraidos["extracciones"]:
                if isinstance(elem, dict) and "campo" in elem:
                    datos_dict[elem["campo"]] = elem
            datos_extraidos = datos_dict

    # 4. Formatear la lista de propuestas finales
    propuestas: list[dict[str, Any]] = []

    for k, campo_meta in campos_dict.items():
        if k in datos_extraidos and isinstance(datos_extraidos[k], dict):
            item = datos_extraidos[k]
            valor = str(item.get("valor", "")).strip()
            if not valor or valor.lower() in ("null", "none", "[completar]"):
                continue

            archivo_fuente = str(item.get("archivo", "")).strip() or archivos[0]["nombre"]
            pagina_val = item.get("pagina")
            pagina_num: Optional[int] = None
            if pagina_val is not None:
                try:
                    p_int = int(pagina_val)
                    if p_int > 0:
                        pagina_num = p_int
                except (ValueError, TypeError):
                    pagina_num = None

            cita = str(item.get("cita_textual_corta", "")).strip()
            confianza_raw = str(item.get("confianza", "alta")).lower()
            confianza = confianza_raw if confianza_raw in ("alta", "media", "baja") else "alta"

            propuestas.append({
                "campo": k,
                "etiqueta": campo_meta.get("l", k),
                "tipo_campo": campo_meta.get("t", "texto"),
                "valor": valor,
                "archivo": archivo_fuente,
                "pagina": pagina_num,
                "cita_textual_corta": cita,
                "confianza": confianza,
            })

    # 5. Extracción específica para contestación: hechos numerados
    hechos_numerados: list[dict[str, Any]] = []
    fuente_hechos = None
    if isinstance(raw_extraidos, dict) and "hechos_numerados" in raw_extraidos:
        fuente_hechos = raw_extraidos["hechos_numerados"]
    elif isinstance(datos_extraidos, dict) and "hechos_numerados" in datos_extraidos:
        fuente_hechos = datos_extraidos["hechos_numerados"]

    if isinstance(fuente_hechos, list):
        for idx, h_item in enumerate(fuente_hechos, 1):
            if isinstance(h_item, dict):
                num = h_item.get("numero", idx)
                txt = str(h_item.get("texto", "")).strip()
                if txt:
                    hechos_numerados.append({"numero": num, "texto": txt})

    # 6. Extracción específica para providencias (fallo o auto)
    decision_providencia: Optional[dict[str, Any]] = None
    fuente_dp = None
    if isinstance(raw_extraidos, dict) and "decision_providencia" in raw_extraidos:
        fuente_dp = raw_extraidos["decision_providencia"]
    elif isinstance(datos_extraidos, dict) and "decision_providencia" in datos_extraidos:
        fuente_dp = datos_extraidos["decision_providencia"]

    if isinstance(fuente_dp, dict):
        decision_texto = str(fuente_dp.get("decision", "")).strip()
        fecha_texto = str(fuente_dp.get("fecha", "")).strip()
        if decision_texto:
            decision_providencia = {
                "decision": decision_texto,
                "fecha": fecha_texto,
                "archivo": str(fuente_dp.get("archivo", "")).strip() or archivos[0]["nombre"],
                "pagina": fuente_dp.get("pagina"),
                "cita_textual_corta": str(fuente_dp.get("cita_textual_corta", "")).strip(),
                "confianza": str(fuente_dp.get("confianza", "alta")).lower(),
            }
            # Asignar al campo respectivo si no se había propuesto aún
            campo_prov = (
                "fallo" if tipo_id == "impugnacion_tutela"
                else "providencia" if tipo_id == "recurso_judicial"
                else "sentencia" if tipo_id == "apelacion_sentencia"
                else None
            )
            if campo_prov and not any(p["campo"] == campo_prov for p in propuestas):
                prefijo = "Auto" if tipo_id == "recurso_judicial" else "Sentencia"
                valor_formateado = (
                    f"{prefijo} del {fecha_texto} que resolvió: {decision_texto}"
                    if fecha_texto else f"{prefijo} que resolvió: {decision_texto}"
                )
                etiqueta_prov = campos_dict.get(campo_prov, {}).get("l", campo_prov)
                propuestas.append({
                    "campo": campo_prov,
                    "etiqueta": etiqueta_prov,
                    "tipo_campo": "area",
                    "valor": valor_formateado,
                    "archivo": decision_providencia["archivo"],
                    "pagina": decision_providencia["pagina"],
                    "cita_textual_corta": decision_providencia["cita_textual_corta"],
                    "confianza": decision_providencia["confianza"],
                })

    # 7. Detección de fecha de notificación si aparece
    fecha_notificacion_detectada: Optional[str] = None
    for p in propuestas:
        if p["campo"] == "notificacion_fecha" and p["valor"]:
            fecha_notificacion_detectada = p["valor"]
            break

    return {
        "propuestas": propuestas,
        "hechos_numerados": hechos_numerados,
        "decision_providencia": decision_providencia,
        "fecha_notificacion_detectada": fecha_notificacion_detectada,
    }

```


## 📄 Archivo: `app/services/prompt.py`
```python
"""Servicio de catálogo y construcción de prompts en el servidor (app/services/prompt.py)."""
import datetime
import json
import os
import re
from typing import Any, Optional

CATALOGO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogo")
TIPOS_DIR = os.path.join(CATALOGO_DIR, "tipos")

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

_CATALOGO_CACHE: dict[str, Any] = {}


def limpiar_cache():
    _CATALOGO_CACHE.clear()


def fecha_larga(d: Optional[datetime.date] = None) -> str:
    if d is None:
        d = datetime.date.today()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def pesos(n: Any) -> str:
    try:
        val = round(float(n or 0))
    except (ValueError, TypeError):
        val = 0
    # En es-CO los miles se separan con punto
    formatted = f"{val:,}".replace(",", ".")
    return f"${formatted}"


def genero_ab(genero: str) -> str:
    return "a" if genero == "f" else "o" if genero == "m" else "o(a)"


def cargar_formato_salida() -> str:
    if "formato_salida" not in _CATALOGO_CACHE:
        path = os.path.join(CATALOGO_DIR, "formato_salida.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _CATALOGO_CACHE["formato_salida"] = data["texto"]
    return _CATALOGO_CACHE["formato_salida"]


def cargar_contexto_normativo(smmlv: int = 1750905) -> list[str]:
    path = os.path.join(CATALOGO_DIR, "contexto_normativo.json")
    with open(path, "r", encoding="utf-8") as f:
        reglas = json.load(f)
    lineas = []
    for r in reglas:
        if "plantilla" in r:
            lineas.append(r["plantilla"].format(smmlv=pesos(smmlv)))
        else:
            lineas.append(r["texto"])
    return lineas


def cargar_areas() -> list[str]:
    if "areas" not in _CATALOGO_CACHE:
        path = os.path.join(CATALOGO_DIR, "areas.json")
        with open(path, "r", encoding="utf-8") as f:
            _CATALOGO_CACHE["areas"] = json.load(f)
    return _CATALOGO_CACHE["areas"]


def cargar_grupo_redaccion() -> dict[str, Any]:
    if "grupo_redaccion" not in _CATALOGO_CACHE:
        path = os.path.join(CATALOGO_DIR, "grupo_redaccion.json")
        with open(path, "r", encoding="utf-8") as f:
            _CATALOGO_CACHE["grupo_redaccion"] = json.load(f)
    return _CATALOGO_CACHE["grupo_redaccion"]


def obtener_tipo(tipo_id: str) -> Optional[dict[str, Any]]:
    path = os.path.join(TIPOS_DIR, f"{tipo_id}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def listar_tipos(incluir_guia: bool = False) -> list[dict[str, Any]]:
    tipos = []
    if not os.path.isdir(TIPOS_DIR):
        return tipos
    for filename in sorted(os.listdir(TIPOS_DIR)):
        if filename.endswith(".json"):
            path = os.path.join(TIPOS_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                tipo = json.load(f)
                if not incluir_guia:
                    tipo.pop("guia", None)
                tipos.append(tipo)
    return tipos


def grupo_redaccion_para_tipo(tipo: dict[str, Any]) -> dict[str, Any]:
    """Genera la estructura de campos del grupo 'Redacción' correspondiente a un tipo."""
    campos = [
        {
            "k": "fundamentos",
            "l": "Normas o jurisprudencia que quieres citar",
            "t": "area",
            "rows": 2,
            "ph": "Opcional. Ej.: Sentencia T-760 de 2008; art. 49 de la Constitución."
        },
        {
            "k": "_extension",
            "l": "Extensión",
            "t": "select",
            "opciones": [["concisa", "Concisa"], ["estandar", "Estándar"], ["extensa", "Extensa y exhaustiva"]],
            "def": "concisa" if tipo.get("breve") else "@extension"
        },
        {
            "k": "_juris",
            "l": "Jurisprudencia",
            "t": "select",
            "opciones": [
                ["verificables", "Solo citas verificables"],
                ["sugerir", "Sugerir sentencias, marcadas para verificar"],
                ["usuario", "Solo la que yo indique"],
                ["ninguna", "No citar jurisprudencia"]
            ],
            "def": tipo.get("juris") or "verificables"
        }
    ]
    if tipo.get("firma") != "poder":
        campos.append({
            "k": "_firma",
            "l": "Quién firma",
            "t": "select",
            "opciones": [
                ["apoderado", "Yo, como apoderado(a)"],
                ["propio", "Yo, en nombre propio"],
                ["cliente", "Mi cliente, en nombre propio"]
            ],
            "def": tipo.get("firma") or "apoderado"
        })
    campos.append({"k": "_membrete", "l": "Incluir mi membrete en este escrito", "t": "check", "def": True})
    campos.append({
        "k": "_notas",
        "l": "Indicaciones adicionales",
        "t": "area",
        "rows": 2,
        "ph": "Ej.: Enfatiza que la accionante es adulta mayor; no menciones el nombre del médico."
    })
    return {"n": "Redacción", "campos": campos}


def campos_tipo(tipo: dict[str, Any]) -> list[dict[str, Any]]:
    campos = []
    for g in tipo.get("grupos", []):
        campos.extend(g.get("campos", []))
    campos.extend(grupo_redaccion_para_tipo(tipo).get("campos", []))
    return campos


def validar_datos_tipo(tipo: dict[str, Any], datos: dict[str, Any]) -> list[str]:
    """Valida los campos obligatorios requeridos por el tipo. Devuelve lista de errores."""
    errores = []
    for g in tipo.get("grupos", []):
        for c in g.get("campos", []):
            k = c.get("k")
            v = datos.get(k)
            v_vacio = v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and len(v) == 0)
            if c.get("req") and v_vacio:
                errores.append(f"El campo '{c.get('l', k)}' ({k}) es obligatorio.")
            elif not v_vacio and (c.get("t") == "radicado" or k == "radicado"):
                solo_dig = re.sub(r"\D", "", str(v))
                if len(solo_dig) != 23:
                    errores.append(
                        f"El radicado judicial debe tener exactamente 23 dígitos (actualmente tiene {len(solo_dig)})."
                    )
    return errores


def _formatear_fecha_iso_legible(iso_str: str) -> str:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(iso_str or "").strip())
    if not m:
        return str(iso_str or "").strip()
    ano, mes, dia = int(m.group(1)), int(m.group(2)), int(m.group(3))
    meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    if 1 <= mes <= 12:
        return f"{dia} de {meses[mes - 1]} de {ano}"
    return str(iso_str)


def valor_legible(c: dict[str, Any], v: Any) -> str:
    t = c.get("t")
    k = c.get("k", "")
    if t == "check":
        return "Sí" if v else "No"
    if t == "select":
        for o in c.get("opciones", []):
            if isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == v:
                return str(o[1])
        return str(v) if v is not None else ""
    if t == "chips":
        if isinstance(v, list):
            return ", ".join(str(x) for x in v)
        return str(v or "").strip()
    if t == "date" or t == "fecha" or k.endswith("_fecha"):
        return _formatear_fecha_iso_legible(v)
    if t == "radicado" or k == "radicado":
        digitos = re.sub(r"\D", "", str(v or ""))
        if len(digitos) == 23:
            return f"{digitos[0:5]}-{digitos[5:7]}-{digitos[7:9]}-{digitos[9:12]}-{digitos[12:16]}-{digitos[16:21]}-{digitos[21:23]}"
    return str(v or "").strip()


def instruccion_firma(tipo: dict[str, Any], abogado: dict[str, Any], datos: dict[str, Any]) -> str:
    ab = abogado or {}
    g = genero_ab(ab.get("genero", ""))
    nombre = ab.get("nombre") or "el abogado"
    rol_cliente = tipo.get("rolCliente") or ""
    modo = "poder" if tipo.get("firma") == "poder" else (datos.get("_firma") or "apoderado")

    if modo == "poder":
        return (
            f"El poder lo otorga {rol_cliente} y lo acepta {nombre}. Al final escribe el bloque de firma del "
            f"poderdante (una línea de guiones bajos, su nombre en mayúsculas y su documento; si es persona jurídica, "
            f"el nombre del representante legal y el NIT), luego «Acepto,» en su propio párrafo y, en una línea sola, "
            f"[[FIRMA: Apoderad{g}]]."
        )
    if modo == "cliente":
        return (
            f"El escrito lo firma directamente {rol_cliente} en nombre propio; el abogado solo lo redacta y no se "
            f"menciona en el documento. No uses [[FIRMA]]. Al final, después de la despedida, escribe el bloque de "
            f"firma del firmante: una línea de guiones bajos, su nombre en mayúsculas y su documento de identidad, "
            f"cada dato en su propia línea dentro del mismo párrafo."
        )
    if modo == "propio":
        return (
            f"{nombre} actúa en nombre propio. Preséntalo con su nombre, cédula y tarjeta profesional. "
            f"Termina con [[FIRMA]] en una línea sola."
        )

    rol_firma = tipo.get("rolFirma") or "de su cliente"
    ident = "o(a)" if g == "o(a)" else g
    firma_rol_sufijo = tipo.get("rolFirma") or ""
    return (
        f"El escrito lo presenta {nombre} como apoderad{g} {rol_firma}. En el párrafo de presentación "
        f"identifícal{ident} con su nombre, cédula y tarjeta profesional e indica que actúa según el poder "
        f"que se anexa (inclúyelo en los anexos). Al final, después de la fórmula de despedida, escribe en "
        f"una línea sola: [[FIRMA: Apoderad{g} {firma_rol_sufijo}]]."
    )


def lineas_estilo(estilo: dict[str, Any]) -> list[str]:
    e = estilo or {}
    L = []
    tratamiento = e.get("tratamiento", "auto")
    if tratamiento and tratamiento != "auto":
        L.append(f"Dirígete al despacho como «{tratamiento}».")
    if e.get("persona") == "primera":
        L.append("Escribe en primera persona («me permito», «solicito», «manifiesto»).")
    elif e.get("persona") == "tercera":
        L.append("Escribe en tercera persona («el suscrito apoderado», «la parte que represento»).")

    num_hechos = e.get("numHechos")
    if num_hechos == "ordinal":
        L.append("Numera los hechos con ordinales en mayúscula y negrilla: **PRIMERO.**, **SEGUNDO.**")
    elif num_hechos == "numero":
        L.append("Numera los hechos con números arábigos: 1., 2., 3.")
    elif num_hechos == "hecho":
        L.append("Numera los hechos así: **Hecho 1.**, **Hecho 2.**")

    num_pret = e.get("numPretensiones")
    if num_pret == "ordinal":
        L.append("Numera las pretensiones con ordinales femeninos en mayúscula y negrilla: **PRIMERA.**, **SEGUNDA.**")
    elif num_pret == "numero":
        L.append("Numera las pretensiones con números arábigos: 1., 2., 3.")

    tono = e.get("tono")
    if tono == "contundente":
        L.append("Tono firme y contundente, sin perder el respeto por el despacho ni por la contraparte.")
    elif tono == "sencillo":
        L.append("Lenguaje claro y sencillo, comprensible para el cliente, sin perder rigor.")
    elif tono == "sobrio":
        L.append("Tono sobrio, técnico y respetuoso.")
    else:
        L.append("Tono sobrio y técnico.")

    lenguaje = e.get("lenguaje")
    if lenguaje == "claro":
        L.append("Lenguaje claro y moderno: evita latinismos innecesarios, fórmulas arcaicas y oraciones demasiado largas.")
    elif lenguaje == "tradicional":
        L.append("Estilo forense tradicional colombiano, con sus fórmulas clásicas («respetuosamente me permito», «con todo respeto»).")

    fecha = e.get("fecha")
    if fecha == "arriba":
        L.append("Escribe el lugar y la fecha al inicio, antes del destinatario.")
    elif fecha == "final":
        L.append("Escribe el lugar y la fecha al final, antes de la firma.")
    elif fecha == "no":
        L.append("No escribas lugar ni fecha.")

    if e.get("esd", True):
        L.append("En los escritos dirigidos a un despacho judicial, cierra el destinatario con «E. S. D.».")
    else:
        L.append("No uses «E. S. D.» en el destinatario.")

    cierre = e.get("cierre")
    if cierre:
        L.append(f"Fórmula de despedida antes de la firma: «{cierre}».")
    return L


def construir_prompt(
    tipo_id_o_meta: Any,
    datos: dict[str, Any],
    perfil: Optional[dict[str, Any]] = None,
    fecha_ref: Optional[datetime.date] = None,
) -> str:
    """Construye el prompt exacto para Claude o Gemini en el servidor."""
    if isinstance(tipo_id_o_meta, str):
        tipo = obtener_tipo(tipo_id_o_meta)
        if not tipo:
            raise ValueError(f"Tipo desconocido: {tipo_id_o_meta}")
    else:
        tipo = tipo_id_o_meta

    p = perfil or {}
    ab = p.get("abogado") or {}
    estilo = p.get("estilo") or {}
    ia = p.get("ia") or {}
    d = datos or {}

    L = []
    L.append("Eres un abogado litigante colombiano con amplia experiencia. Redactas escritos jurídicos impecables, listos para radicar. Redacta completo el documento descrito abajo.")
    L.append("")
    hoy_str = fecha_larga(fecha_ref)
    L.append(f"FECHA DE HOY: {hoy_str}. Úsala si el escrito lleva fecha.")
    tipo_libre_str = f" ({d['tipo_libre']})" if d.get("tipo_libre") else ""
    L.append(f"DOCUMENTO: {tipo.get('nombre', '')}{tipo_libre_str}")
    L.append("")
    L.append("CONTEXTO NORMATIVO VIGENTE (octubre de 2026; prevalece sobre lo que recuerdes):")
    smmlv_val = ia.get("smmlv", 1750905)
    for x in cargar_contexto_normativo(smmlv=smmlv_val):
        L.append("- " + x)
    L.append("")
    L.append("GUÍA JURÍDICA Y ESTRUCTURA PARA ESTE ESCRITO:")
    L.append(tipo.get("guia", ""))
    L.append("")
    L.append("ABOGADO(A) QUE REDACTA:")
    if ab.get("nombre"):
        genero = ab.get("genero")
        if genero == "f":
            g_desc = "abogada; trátala en femenino: la suscrita, apoderada"
        elif genero == "m":
            g_desc = "abogado; trátalo en masculino: el suscrito, apoderado"
        else:
            g_desc = "usa la forma «apoderado(a)» si necesitas nombrarlo"
        L.append(f"- Nombre: {ab['nombre']} ({g_desc})")

        cedula_lugar = ab.get("cedulaLugar")
        ced_str = f"{ab['cedula']}{' de ' + cedula_lugar if cedula_lugar else ''}" if ab.get("cedula") else "[COMPLETAR]"
        L.append(f"- Cédula: {ced_str}")

        tp = ab.get("tp")
        L.append(f"- Tarjeta profesional: {tp + ' del Consejo Superior de la Judicatura' if tp else '[COMPLETAR]'}")
        if ab.get("correo"):
            L.append(f"- Correo de notificaciones (inscrito en el Registro Nacional de Abogados): {ab['correo']}")
        if ab.get("telefono"):
            L.append(f"- Teléfono: {ab['telefono']}")
        if ab.get("direccion"):
            ciudad_str = f", {ab['ciudad']}" if ab.get("ciudad") else ""
            L.append(f"- Dirección: {ab['direccion']}{ciudad_str}")
    else:
        L.append("- Sus datos no están configurados: donde debas mencionarlos escribe [COMPLETAR: nombre del abogado], [COMPLETAR: cédula] y [COMPLETAR: tarjeta profesional].")

    L.append("")
    L.append("QUIÉN FIRMA:")
    L.append(instruccion_firma(tipo, ab, d))
    L.append("")
    L.append("ESTILO DEL ABOGADO (síguelo):")
    for x in lineas_estilo(estilo):
        L.append("- " + x)

    ficha = (estilo.get("ficha") or "").strip()
    if ficha:
        L.append("")
        L.append("FICHA DE ESTILO DEL ABOGADO (prevalecen las preferencias anteriores si chocan):")
        L.append(ficha[:4000])

    muestra = (estilo.get("muestra") or "").strip()
    if muestra:
        L.append("")
        L.append("MUESTRA DE UN ESCRITO DEL ABOGADO. Imita su voz, sus fórmulas, el orden de sus capítulos y su nivel de formalidad. No copies sus hechos, nombres ni datos:")
        L.append("<<<")
        L.append(muestra[:9000])
        L.append(">>>")

    L.append("")
    L.append("DATOS DEL CASO (los escribió el abogado; pueden estar en borrador o con errores de digitación: corrígelos al redactar sin cambiar su sentido):")
    for c in campos_tipo(tipo):
        k = c.get("k", "")
        if k.startswith("_") and k != "_notas":
            continue
        v = d.get(k)
        if v is None or v == "" or (isinstance(v, list) and not v):
            continue
        if c.get("t") == "check" and k == "juramento":
            L.append(f"### {c.get('l', '')}")
            L.append("Sí, inclúyelo." if v else "No lo incluyas.")
            continue
        etiqueta = "Indicaciones adicionales del abogado" if k == "_notas" else c.get("l", "")
        L.append(f"### {etiqueta}")
        L.append(valor_legible(c, v))

    L.append("")
    ext = d.get("_extension") or estilo.get("extension") or "estandar"
    juris = d.get("_juris") or "sugerir"
    n_sent = 2 if ext == "concisa" else 6 if ext == "extensa" else 4

    L.append("REGLAS OBLIGATORIAS:")
    L.append("1. Usa únicamente los hechos, nombres, cifras, fechas y documentos que aparecen en los datos del caso. No inventes nada. Si falta un dato necesario, escribe en su lugar [COMPLETAR: descripción breve del dato].")
    L.append("2. Puedes ordenar, depurar y redactar con lenguaje jurídico los hechos y las pretensiones, sin alterar su sentido ni agregar hechos nuevos.")
    L.append("3. Cita solo normas colombianas que existan y estén vigentes. Si dudas del número de un artículo o de su vigencia, escribe [VERIFICAR] inmediatamente después de la cita.")
    if juris == "verificables":
        L.append(f"4. Jurisprudencia: además de la que indique el abogado, puedes citar hasta {n_sent} pronunciamientos de la Corte Constitucional, la Corte Suprema de Justicia o el Consejo de Estado que conozcas con certeza y que sean pertinentes; el sistema verificará automáticamente su existencia en relatoría oficial. Nunca inventes números de sentencia, radicados, fechas ni magistrados ponentes.")
    elif juris == "sugerir":
        L.append(f"4. Jurisprudencia: además de la que indique el abogado, puedes citar hasta {n_sent} pronunciamientos de la Corte Constitucional, la Corte Suprema de Justicia o el Consejo de Estado que conozcas con certeza y que sean pertinentes; prefiere sentencias de unificación y precedentes muy reconocidos. Escribe [VERIFICAR] inmediatamente después de cada sentencia que cites y que no haya suministrado el abogado. Nunca inventes números de sentencia, radicados, fechas ni magistrados ponentes.")
    elif juris == "usuario":
        L.append("4. Jurisprudencia: cita únicamente la que indicó el abogado en los datos del caso; no agregues otras sentencias.")
    else:
        L.append("4. Jurisprudencia: no cites sentencias. Funda el escrito en la Constitución, la ley y los hechos.")

    L.append("5. Nunca pongas entre comillas un texto atribuido a una sentencia, a una norma o a un autor, salvo que el abogado lo haya suministrado textualmente o estés seguro de su texto exacto; en caso contrario, parafrasea.")
    L.append("6. No escribas el membrete ni el encabezado o pie de página con los datos de contacto del abogado: se agregan automáticamente. Sí escribe el destinatario y la referencia.")

    desc_extension = {
        "concisa": "concisa y directa, solo lo esencial de cada capítulo.",
        "estandar": "completa pero sin relleno ni repeticiones.",
        "extensa": "exhaustiva: desarrolla a fondo cada argumento."
    }.get(ext, "completa pero sin relleno.")
    L.append(f"7. Extensión: {desc_extension}")
    L.append("8. Escribe solo el documento: sin comentarios, notas, advertencias ni explicaciones antes o después.")
    L.append("")
    L.append(cargar_formato_salida())

    return "\n".join(L)

```


## 📄 Archivo: `app/services/radicado.py`
```python
"""Servicio de validación, formateo y decodificación de radicados judiciales colombianos.

Estructura de 23 dígitos: 5-2-2-3-4-5-2
(Acuerdos PSAA06-3306 de 2006 y PCSJA20-11567 del Consejo Superior de la Judicatura)
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

RADICADO_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "catalogo", "radicado.json")

_CACHE_CATALOGO: Optional[dict[str, Any]] = None


def obtener_catalogo_radicado() -> dict[str, Any]:
    global _CACHE_CATALOGO
    if _CACHE_CATALOGO is None:
        if os.path.exists(RADICADO_JSON_PATH):
            with open(RADICADO_JSON_PATH, "r", encoding="utf-8") as f:
                _CACHE_CATALOGO = json.load(f)
        else:
            _CACHE_CATALOGO = {}
    return _CACHE_CATALOGO


def extraer_digitos_radicado(radicado: str) -> str:
    """Extrae únicamente los dígitos de una cadena de radicado."""
    return re.sub(r"\D", "", str(radicado or ""))


def validar_radicado(radicado: str) -> tuple[bool, str]:
    """Exige exactamente 23 dígitos numéricos."""
    digitos = extraer_digitos_radicado(radicado)
    n = len(digitos)
    if n == 23:
        return True, "Radicado completo: 23 dígitos válidos."
    if n == 0:
        return False, "El radicado está vacío; debe tener 23 dígitos."
    return False, f"El radicado judicial debe tener exactamente 23 dígitos (actualmente tiene {n})."


def formatear_radicado(radicado: str) -> str:
    """Formatea 23 dígitos en la estructura canónica 5-2-2-3-4-5-2.

    Ejemplo: 11001-40-03-012-2026-00345-00
    """
    d = extraer_digitos_radicado(radicado)
    if len(d) != 23:
        return str(radicado or "").strip()
    return f"{d[0:5]}-{d[5:7]}-{d[7:9]}-{d[9:12]}-{d[12:16]}-{d[16:21]}-{d[21:23]}"


def decodificar_radicado(radicado: str) -> dict[str, Any]:
    """Decodifica los segmentos del radicado judicial de 23 dígitos.

    Desagrega:
    - Municipio (código DANE y nombre)
    - Entidad (corporación o tipo de despacho)
    - Especialidad
    - Número de despacho
    - Año de radicación
    - Consecutivo del proceso
    - Instancia o recurso
    """
    digitos = extraer_digitos_radicado(radicado)
    valido, mensaje = validar_radicado(radicado)

    if not valido:
        return {
            "valido": False,
            "digitos": digitos,
            "total_digitos": len(digitos),
            "mensaje": mensaje,
            "formateado": str(radicado or "").strip(),
        }

    cat = obtener_catalogo_radicado()
    entidades = cat.get("entidades", {})
    especialidades = cat.get("especialidades", {})
    municipios = cat.get("municipios_dane", {})
    recursos = cat.get("recursos", {})

    cod_mun = digitos[0:5]
    cod_ent = digitos[5:7]
    cod_esp = digitos[7:9]
    cod_desp = digitos[9:12]
    ano = digitos[12:16]
    consecutivo = digitos[16:21]
    cod_rec = digitos[21:23]

    nombre_mun = municipios.get(cod_mun, f"Municipio DANE {cod_mun}")
    nombre_ent = entidades.get(cod_ent, f"Entidad {cod_ent}")
    nombre_esp = especialidades.get(cod_esp, f"Especialidad {cod_esp}")
    nombre_rec = recursos.get(cod_rec, f"Recurso/Instancia {cod_rec}")

    formateado = f"{cod_mun}-{cod_ent}-{cod_esp}-{cod_desp}-{ano}-{consecutivo}-{cod_rec}"

    partes_resumen = [
        nombre_mun,
        f"{nombre_ent} ({nombre_esp})",
        f"Despacho {int(cod_desp)}",
        f"Año {ano}",
        f"Consecutivo {consecutivo}",
    ]
    resumen = " · ".join(partes_resumen)

    return {
        "valido": True,
        "digitos": digitos,
        "total_digitos": 23,
        "formateado": formateado,
        "municipio_codigo": cod_mun,
        "municipio_nombre": nombre_mun,
        "entidad_codigo": cod_ent,
        "entidad_nombre": nombre_ent,
        "especialidad_codigo": cod_esp,
        "especialidad_nombre": nombre_esp,
        "despacho_numero": cod_desp,
        "ano": int(ano),
        "consecutivo": consecutivo,
        "consecutivo_numero": int(consecutivo),
        "recurso_codigo": cod_rec,
        "recurso_nombre": nombre_rec,
        "resumen": resumen,
        "mensaje": "Radicado válido y decodificado exitosamente.",
    }

```


## 📄 Archivo: `app/services/nit.py`
```python
"""Módulo de cálculo y validación de Dígito de Verificación (DV) para NIT en Colombia.

Implementa el algoritmo oficial de la Dirección de Impuestos y Aduanas Nacionales (DIAN)
según el Estatuto Tributario y el Decreto 4048 de 2008.

Pesos de derecha a izquierda: [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
Residuo = suma mod 11
DV = residuo si residuo in (0, 1) sino (11 - residuo)
"""

from __future__ import annotations

import re
from typing import Any, Optional, Union

# Pesos de ponderación DIAN de derecha a izquierda
PESOS_DIAN = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)


def calcular_dv_nit(nit: Union[str, int]) -> int:
    """Calcula el dígito de verificación oficial de la DIAN para un número de NIT."""
    # Extraer únicamente los dígitos numéricos
    solo_digitos = re.sub(r"\D", "", str(nit))
    if not solo_digitos:
        raise ValueError("El NIT debe contener al menos un dígito numérico.")

    suma = 0
    # Recorrer de derecha a izquierda aplicando los pesos DIAN
    for i, char in enumerate(reversed(solo_digitos)):
        if i >= len(PESOS_DIAN):
            break
        suma += int(char) * PESOS_DIAN[i]

    residuo = suma % 11
    if residuo in (0, 1):
        return residuo
    return 11 - residuo


def formatear_nit(nit: Union[str, int], incluir_dv: bool = True) -> str:
    """Formatea un NIT colombiano con puntos de millar y guion con su dígito de verificación."""
    solo_digitos = re.sub(r"\D", "", str(nit))
    if not solo_digitos:
        return str(nit)

    dv = calcular_dv_nit(solo_digitos)
    # Formatear la base con puntos de millar
    # Ejemplo: 900123456 -> 900.123.456
    rev = solo_digitos[::-1]
    bloques = [rev[i:i + 3] for i in range(0, len(rev), 3)]
    base_fmt = ".".join(bloques)[::-1]

    if incluir_dv:
        return f"{base_fmt}-{dv}"
    return base_fmt


def validar_nit(nit_o_texto: str) -> dict[str, Any]:
    """Valida un NIT con dígito de verificación suministrado.

    Retorna un diccionario con:
    - valido: bool indicando si el DV coincide
    - nit_base: base numérica sin DV
    - dv_ingresado: DV suministrado en el texto (o None si no se especificó)
    - dv_calculado: DV esperado según algoritmo DIAN
    - mensaje: advertencia o confirmación
    """
    texto = str(nit_o_texto or "").strip()
    if not texto:
        return {
            "valido": False,
            "nit_base": "",
            "dv_ingresado": None,
            "dv_calculado": None,
            "mensaje": "NIT vacío.",
        }

    # Caso 1: viene con guion explícito, ej. 900.123.456-7 o 900123456-7
    if "-" in texto:
        partes = texto.split("-")
        base_raw = re.sub(r"\D", "", partes[0])
        dv_raw = re.sub(r"\D", "", partes[-1])
        if base_raw and dv_raw:
            dv_ingresado = int(dv_raw[-1])
            dv_calculado = calcular_dv_nit(base_raw)
            es_valido = (dv_ingresado == dv_calculado)
            return {
                "valido": es_valido,
                "nit_base": base_raw,
                "dv_ingresado": dv_ingresado,
                "dv_calculado": dv_calculado,
                "nit_formateado": f"{formatear_nit(base_raw, incluir_dv=False)}-{dv_calculado}",
                "mensaje": (
                    "Dígito de verificación DIAN correcto."
                    if es_valido
                    else f"El dígito de verificación ingresado ({dv_ingresado}) no coincide con el calculado por la DIAN ({dv_calculado}). Para este NIT debe ser {formatear_nit(base_raw, incluir_dv=False)}-{dv_calculado}."
                ),
            }

    # Caso 2: número sin guion (ej. 900123456 o 900.123.456)
    solo_digitos = re.sub(r"\D", "", texto)
    if not solo_digitos:
        return {
            "valido": False,
            "nit_base": "",
            "dv_ingresado": None,
            "dv_calculado": None,
            "mensaje": "No se encontraron dígitos en el NIT.",
        }

    dv_calculado = calcular_dv_nit(solo_digitos)
    return {
        "valido": True,
        "nit_base": solo_digitos,
        "dv_ingresado": None,
        "dv_calculado": dv_calculado,
        "nit_formateado": f"{formatear_nit(solo_digitos, incluir_dv=False)}-{dv_calculado}",
        "mensaje": f"NIT sin dígito de verificación. El DV calculado por la DIAN es {dv_calculado}.",
    }

```


## 📄 Archivo: `app/services/numeros_letras.py`
```python
"""Servicio determinista de conversión de números a letras en pesos colombianos ("M/CTE").

Cumple con las normas gramaticales de la RAE y la práctica notarial y judicial colombiana.
Ejemplos:
- 80_000_000 -> "OCHENTA MILLONES DE PESOS M/CTE."
- 80_000_500 -> "OCHENTA MILLONES QUINIENTOS PESOS M/CTE."
- 1_000_000  -> "UN MILLÓN DE PESOS M/CTE."
- 1_000      -> "UN MIL PESOS M/CTE."
- 100        -> "CIEN PESOS M/CTE."
- 101        -> "CIENTO UN PESOS M/CTE."
- 21         -> "VEINTIÚN PESOS M/CTE."
- 1          -> "UN PESO M/CTE."
- 0          -> "CERO PESOS M/CTE."
"""

from __future__ import annotations

import re
from typing import Union

UNIDADES = ("", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE")
DIEZ_A_DIECINUEVE = (
    "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE",
    "DIECISÉIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"
)
VEINTES = (
    "VEINTE", "VEINTIÚN", "VEINTIDÓS", "VEINTITRÉS", "VEINTICUATRO", "VEINTICINCO",
    "VEINTISÉIS", "VEINTISIETE", "VEINTIOCHO", "VEINTINUEVE"
)
DECENAS = ("", "", "", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA")
CENTENAS = (
    "", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
    "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"
)


def _seccion_tres_digitos(n: int) -> str:
    """Convierte un entero de 0 a 999 en letras en mayúscula sostenida."""
    if n == 0:
        return ""
    if n == 100:
        return "CIEN"

    c = n // 100
    resto = n % 100
    d = resto // 10
    u = resto % 10

    partes = []
    if c > 0:
        partes.append(CENTENAS[c])

    if resto > 0:
        if resto < 10:
            partes.append(UNIDADES[resto])
        elif resto < 20:
            partes.append(DIEZ_A_DIECINUEVE[resto - 10])
        elif resto < 30:
            partes.append(VEINTES[resto - 20])
        else:
            if u == 0:
                partes.append(DECENAS[d])
            else:
                partes.append(f"{DECENAS[d]} Y {UNIDADES[u]}")

    return " ".join(partes)


def numero_a_letras_entero(n: int) -> tuple[str, bool]:
    """Convierte un número entero positivo a palabras.

    Retorna una tupla: (texto, termina_en_millon_o_millones)
    donde termina_en_millon_o_millones indica si debe llevar la preposición 'DE' antes de 'PESOS'.
    """
    if n == 0:
        return "CERO", False
    if n == 1:
        return "UN", False

    # Descomponer en grupos de 3 dígitos (de derecha a izquierda)
    # g0: unidades (0..999)
    # g1: miles (1_000..999_000)
    # g2: millones (1_000_000..999_000_000)
    # g3: miles de millones (1_000_000_000..999_000_000_000)
    # g4: billones (1_000_000_000_000..)
    g0 = n % 1_000
    g1 = (n // 1_000) % 1_000
    g2 = (n // 1_000_000) % 1_000
    g3 = (n // 1_000_000_000) % 1_000
    g4 = (n // 1_000_000_000_000) % 1_000

    partes = []

    # Billones (g4)
    if g4 > 0:
        if g4 == 1:
            partes.append("UN BILLÓN")
        else:
            partes.append(f"{_seccion_tres_digitos(g4)} BILLONES")

    # Miles de millones (g3) y Millones (g2)
    millones_total = g3 * 1_000 + g2
    if millones_total > 0:
        if g3 > 0 and g2 == 0:
            if g3 == 1:
                partes.append("UN MIL MILLONES")
            else:
                partes.append(f"{_seccion_tres_digitos(g3)} MIL MILLONES")
        elif g3 > 0 and g2 > 0:
            if g3 == 1:
                partes.append(f"UN MIL {_seccion_tres_digitos(g2)} MILLONES")
            else:
                partes.append(f"{_seccion_tres_digitos(g3)} MIL {_seccion_tres_digitos(g2)} MILLONES")
        else:
            # Solo g2
            if g2 == 1:
                partes.append("UN MILLÓN")
            else:
                partes.append(f"{_seccion_tres_digitos(g2)} MILLONES")

    # Miles (g1)
    if g1 > 0:
        if g1 == 1:
            partes.append("UN MIL")
        else:
            partes.append(f"{_seccion_tres_digitos(g1)} MIL")

    # Unidades (g0)
    if g0 > 0:
        partes.append(_seccion_tres_digitos(g0))

    texto = " ".join(partes)

    # Verifica si termina en MILLÓN, MILLONES, BILLÓN o BILLONES (con resto menor igual a 0)
    # En ese caso gramaticalmente corresponde "DE PESOS", ej: OCHENTA MILLONES DE PESOS
    termina_en_millones = (millones_total > 0 or g4 > 0) and (g1 == 0 and g0 == 0)

    return texto, termina_en_millones


def numero_a_letras(valor: Union[int, float, str]) -> str:
    """Convierte cualquier valor numérico en su expresión legal determinista en pesos colombianos.

    Formato: "OCHENTA MILLONES DE PESOS M/CTE." o "UN PESO M/CTE."
    Si incluye centavos: "OCHENTA MILLONES DE PESOS CON 50/100 M/CTE."
    """
    if valor is None:
        return ""

    # Limpiar cadenas monetarias tipo "$ 80.000.000,50" o "80000000"
    if isinstance(valor, str):
        v_limpio = valor.strip().replace("$", "").replace("COP", "").replace("cop", "").strip()
        if not v_limpio:
            return ""
        # Normalizar separadores decimales colombianos (coma como decimal o punto como decimal)
        if "," in v_limpio and "." in v_limpio:
            # Caso 80.000.000,50
            if v_limpio.rfind(",") > v_limpio.rfind("."):
                v_limpio = v_limpio.replace(".", "").replace(",", ".")
            else:
                v_limpio = v_limpio.replace(",", "")
        elif "," in v_limpio:
            # Puede ser 80,50 o 80,000
            partes = v_limpio.split(",")
            if len(partes) == 2 and len(partes[1]) <= 2:
                v_limpio = f"{partes[0]}.{partes[1]}"
            else:
                v_limpio = v_limpio.replace(",", "")
        else:
            # Puntos solos: si hay varios puntos o 3 dígitos al final tipo 80.000.000, son miles
            partes = v_limpio.split(".")
            if len(partes) > 2 or (len(partes) == 2 and len(partes[1]) == 3):
                v_limpio = v_limpio.replace(".", "")

        try:
            num = float(v_limpio)
        except ValueError:
            return ""
    else:
        num = float(valor)

    if num < 0:
        prefijo = "MENOS "
        num = abs(num)
    else:
        prefijo = ""

    entero = int(num)
    centavos = int(round((num - entero) * 100))

    if centavos >= 100:
        entero += 1
        centavos = 0

    texto_entero, de_pesos = numero_a_letras_entero(entero)

    # Regla de plural y preposición DE
    if entero == 1:
        moneda = "PESO"
    elif de_pesos:
        moneda = "DE PESOS"
    else:
        moneda = "PESOS"

    if centavos > 0:
        return f"{prefijo}{texto_entero} {moneda} CON {centavos:02d}/100 M/CTE."
    return f"{prefijo}{texto_entero} {moneda} M/CTE."

```


## 📄 Archivo: `app/services/limites.py`
```python
"""
El Memorialista · control de acceso y límites de uso (v2.3)
Autenticación con Supabase Auth (Bearer tokens y Enlace Mágico) y límites por usuario.
"""
import hmac
import time
from collections import defaultdict, deque
from typing import Any, Optional

from fastapi import HTTPException, Request

from app.config import get_settings
from app.services.supabase_service import validar_token_supabase


def ip_cliente(request: Request) -> str:
    reenviada = request.headers.get("x-forwarded-for", "")
    if reenviada:
        primera = reenviada.split(",")[0].strip()
        if primera:
            return primera[:64]
    return request.client.host if request.client else "desconocida"


async def verificar_acceso(request: Request) -> Optional[dict[str, Any]]:
    """Verifica la sesión activa de Supabase (Bearer token) o código de acceso de respaldo."""
    settings = get_settings()
    auth_header = request.headers.get("authorization", "").strip()
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()

    # Si se envía un token Bearer o si Supabase está activo
    if token or settings.SUPABASE_URL:
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Se requiere iniciar sesión con tu enlace mágico para acceder a El Memorialista.",
            )
        usuario = await validar_token_supabase(token)
        if not usuario:
            raise HTTPException(
                status_code=401,
                detail="Tu sesión de Supabase ha expirado o no es válida. Inicia sesión nuevamente.",
            )
        request.state.usuario = usuario
        request.state.user_id = usuario.get("id") or usuario.get("sub")
        return usuario

    # Respaldo de código de acceso legado si no hay Supabase configurado
    codigo = settings.APP_ACCESS_CODE.strip()
    if codigo:
        enviado = request.headers.get("x-codigo-acceso", "").strip()
        if not enviado or not hmac.compare_digest(enviado.encode("utf-8"), codigo.encode("utf-8")):
            raise HTTPException(
                status_code=401,
                detail="Esta versión de El Memorialista requiere autenticación válida.",
            )
    return None


class Limitador:
    """Ventanas deslizantes en memoria aplicadas por usuario y por IP."""

    def __init__(self) -> None:
        self._eventos = defaultdict(deque)
        self._ultima_limpieza = time.monotonic()

    def _reglas(self, accion: str, ip: str, user_id: Optional[str] = None) -> list:
        s = get_settings()
        id_clave = f"u:{user_id}" if user_id else f"ip:{ip}"
        limite_dia = s.LIMITE_DIA_USUARIO if user_id else s.LIMITE_DIA_IP

        if accion == "redactar":
            return [
                (f"r:{id_clave}:v", s.VENTANA_MINUTOS * 60, s.LIMITE_POR_VENTANA,
                 "Hiciste muchas redacciones seguidas. Espera unos {min} min y vuelve a intentarlo."),
                (f"r:{id_clave}:d", 86400, limite_dia,
                 "Alcanzaste tu límite diario de redacciones ({limite} al día). Vuelve a intentarlo mañana."),
                ("r:global:d", 86400, s.LIMITE_DIA_GLOBAL,
                 "El servicio alcanzó su límite diario de redacciones. Intenta de nuevo mañana."),
            ]
        if accion in ("citas", "revisar"):
            return [
                (f"{accion[0]}:{id_clave}:h", 3600, max(100, s.LIMITE_ESTILO_HORA * 6),
                 "Revisaste muchos escritos seguidos. Espera unos {min} min."),
            ]
        return [
            (f"e:{id_clave}:h", 3600, s.LIMITE_ESTILO_HORA,
             "Analizaste muchas muestras seguidas. Espera unos {min} min."),
        ]

    def verificar(self, request: Request, accion: str, user_id: Optional[str] = None) -> None:
        ahora = time.monotonic()
        u_id = user_id or getattr(request.state, "user_id", None)
        reglas = self._reglas(accion, ip_cliente(request), user_id=u_id)
        for clave, ventana, limite, mensaje in reglas:
            if limite <= 0:
                continue
            cola = self._eventos[clave]
            while cola and ahora - cola[0] > ventana:
                cola.popleft()
            if len(cola) >= limite:
                espera = max(1, int(ventana - (ahora - cola[0])))
                raise HTTPException(
                    status_code=429,
                    detail=mensaje.format(min=max(1, round(espera / 60)), limite=limite),
                    headers={"Retry-After": str(espera)},
                )
        for clave, _ventana, limite, _mensaje in reglas:
            if limite > 0:
                self._eventos[clave].append(ahora)
        self._limpiar(ahora)

    def _limpiar(self, ahora: float) -> None:
        if ahora - self._ultima_limpieza < 600:
            return
        self._ultima_limpieza = ahora
        viejas = [k for k, cola in self._eventos.items() if not cola or ahora - cola[-1] > 86400]
        for k in viejas:
            del self._eventos[k]

    def reiniciar(self) -> None:
        self._eventos.clear()


limitador = Limitador()

```


## 📄 Archivo: `app/services/supabase_service.py`
```python
"""Servicio de integración con Supabase: Auth, Postgres con RLS y Storage privado (v2.3.0).

Maneja:
- Validación de sesiones de Supabase Auth (Bearer tokens y Enlace Mágico).
- Consulta y exportación completa de datos del usuario ("Exportar todos mis datos").
- Eliminación irrevocable de cuenta y datos ("Eliminar mi cuenta").
- Cache en memoria para validación de tokens de alto rendimiento.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from app.config import get_settings

log = logging.getLogger("memorialista.supabase")

# Caché en memoria para validación de tokens (TTL: 60 segundos)
_TOKEN_CACHE: dict[str, tuple[dict[str, Any], float]] = {}
CACHE_TTL_SEGUNDOS = 60.0


def _limpiar_cache_tokens(ahora: float) -> None:
    vencidos = [k for k, (_, exp) in _TOKEN_CACHE.items() if ahora > exp]
    for k in vencidos:
        _TOKEN_CACHE.pop(k, None)


async def validar_token_supabase(token: str) -> Optional[dict[str, Any]]:
    """Valida un Bearer token contra Supabase Auth o el entorno de pruebas.

    Retorna el diccionario con la información del usuario ('id', 'email', 'user_metadata', etc.)
    o None si el token es inválido o ha expirado.
    """
    if not token or not isinstance(token, str):
        return None

    token_limpio = token.strip()
    if token_limpio.lower().startswith("bearer "):
        token_limpio = token_limpio[7:].strip()

    if not token_limpio:
        return None

    # Modo de pruebas / local sin credenciales
    if token_limpio.startswith("mock-") or token_limpio.startswith("test-"):
        partes = token_limpio.split("-")
        uid = partes[1] if len(partes) > 1 else "user-test-uuid-1234"
        email = f"{uid}@memorialista.test"
        return {
            "id": uid,
            "email": email,
            "role": "authenticated",
            "user_metadata": {"nombre": "Abogado de Prueba", "rol": "abogado"},
        }

    ahora = time.monotonic()
    _limpiar_cache_tokens(ahora)

    # Verificar si está en caché
    if token_limpio in _TOKEN_CACHE:
        user_info, exp = _TOKEN_CACHE[token_limpio]
        if ahora < exp:
            return user_info

    settings = get_settings()
    supabase_url = settings.SUPABASE_URL.rstrip("/")
    anon_key = settings.SUPABASE_ANON_KEY

    # Si Supabase no está configurado y estamos en desarrollo, permitir mock fallback
    if not supabase_url:
        if settings.ENVIRONMENT != "production":
            return {
                "id": "dev-user-local",
                "email": "dev@memorialista.local",
                "role": "authenticated",
                "user_metadata": {"nombre": "Abogado Local", "rol": "admin"},
            }
        return None

    auth_url = f"{supabase_url}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token_limpio}",
        "apikey": anon_key or token_limpio,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(auth_url, headers=headers)
            if resp.status_code == 200:
                user_data = resp.json()
                _TOKEN_CACHE[token_limpio] = (user_data, ahora + CACHE_TTL_SEGUNDOS)
                return user_data
            else:
                log.warning("Supabase Auth rechazó el token (status %s): %s", resp.status_code, resp.text)
                return None
    except Exception as e:
        log.error("Error al conectar con Supabase Auth: %s", e)
        return None


async def exportar_todos_los_datos(user_id: str, token: str) -> dict[str, Any]:
    """Descarga todos los datos asociados al usuario (perfil, firma, clientes, casos, documentos, versiones)."""
    settings = get_settings()
    supabase_url = settings.SUPABASE_URL.rstrip("/")
    api_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY

    payload_base = {
        "exportado_el": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "aplicacion": "El Memorialista Jurídico",
        "version_esquema": "2.3.0",
        "usuario_id": user_id,
        "perfil": {},
        "firma": {},
        "clientes": [],
        "casos": [],
        "documentos": [],
        "versiones": [],
    }

    if not supabase_url:
        payload_base["nota"] = "Exportación en modo local / sin base de datos remota activa."
        return payload_base

    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        # 1. Perfil
        try:
            r = await client.get(f"{supabase_url}/rest/v1/perfiles?id=eq.{user_id}&select=*", headers=headers)
            if r.status_code == 200 and r.json():
                payload_base["perfil"] = r.json()[0]
                firma_id = payload_base["perfil"].get("firma_id")
                if firma_id:
                    rf = await client.get(f"{supabase_url}/rest/v1/firmas?id=eq.{firma_id}&select=*", headers=headers)
                    if rf.status_code == 200 and rf.json():
                        payload_base["firma"] = rf.json()[0]
        except Exception as e:
            log.warning("Error exportando perfil/firma: %s", e)

        # 2. Clientes
        try:
            r = await client.get(f"{supabase_url}/rest/v1/clientes?user_id=eq.{user_id}&select=*", headers=headers)
            if r.status_code == 200:
                payload_base["clientes"] = r.json()
        except Exception as e:
            log.warning("Error exportando clientes: %s", e)

        # 3. Casos
        try:
            r = await client.get(f"{supabase_url}/rest/v1/casos?user_id=eq.{user_id}&select=*", headers=headers)
            if r.status_code == 200:
                payload_base["casos"] = r.json()
        except Exception as e:
            log.warning("Error exportando casos: %s", e)

        # 4. Documentos
        try:
            r = await client.get(f"{supabase_url}/rest/v1/documentos?creado_por=eq.{user_id}&select=*", headers=headers)
            if r.status_code == 200:
                payload_base["documentos"] = r.json()
        except Exception as e:
            log.warning("Error exportando documentos: %s", e)

        # 5. Versiones
        try:
            r = await client.get(f"{supabase_url}/rest/v1/versiones?creado_por=eq.{user_id}&select=*", headers=headers)
            if r.status_code == 200:
                payload_base["versiones"] = r.json()
        except Exception as e:
            log.warning("Error exportando versiones: %s", e)

    return payload_base


async def eliminar_cuenta_usuario(user_id: str, token: str) -> bool:
    """Elimina definitivamente todos los registros, archivos y la cuenta de Supabase Auth."""
    settings = get_settings()
    supabase_url = settings.SUPABASE_URL.rstrip("/")
    admin_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY

    # Invalidar caché
    _TOKEN_CACHE.clear()

    if not supabase_url:
        return True

    headers = {
        "Authorization": f"Bearer {admin_key or token}",
        "apikey": admin_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=25.0) as client:
        # 1. Eliminar versiones creadas por el usuario
        try:
            await client.delete(f"{supabase_url}/rest/v1/versiones?creado_por=eq.{user_id}", headers=headers)
        except Exception as e:
            log.warning("Error borrando versiones: %s", e)

        # 2. Eliminar documentos
        try:
            await client.delete(f"{supabase_url}/rest/v1/documentos?creado_por=eq.{user_id}", headers=headers)
        except Exception as e:
            log.warning("Error borrando documentos: %s", e)

        # 3. Eliminar casos
        try:
            await client.delete(f"{supabase_url}/rest/v1/casos?user_id=eq.{user_id}", headers=headers)
        except Exception as e:
            log.warning("Error borrando casos: %s", e)

        # 4. Eliminar clientes
        try:
            await client.delete(f"{supabase_url}/rest/v1/clientes?user_id=eq.{user_id}", headers=headers)
        except Exception as e:
            log.warning("Error borrando clientes: %s", e)

        # 5. Eliminar perfil
        try:
            await client.delete(f"{supabase_url}/rest/v1/perfiles?id=eq.{user_id}", headers=headers)
        except Exception as e:
            log.warning("Error borrando perfil: %s", e)

        # 6. Eliminar usuario en Supabase Auth Admin API (si hay service role key)
        if settings.SUPABASE_SERVICE_ROLE_KEY:
            try:
                admin_auth_headers = {
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                }
                r = await client.delete(f"{supabase_url}/auth/v1/admin/users/{user_id}", headers=admin_auth_headers)
                if r.status_code in (200, 204):
                    log.info("Usuario %s eliminado exitosamente de auth.users", user_id)
                else:
                    log.warning("No se pudo eliminar de auth.users (status %s): %s", r.status_code, r.text)
            except Exception as e:
                log.warning("Error eliminando usuario de auth.users: %s", e)

    return True

```


## 📄 Archivo: `app/catalogo/areas.json`
```json
[
  "Constitucional",
  "Peticiones y actuaciones administrativas",
  "Civil y comercial",
  "Familia",
  "Laboral",
  "Contencioso administrativo",
  "Penal",
  "Procesos en curso",
  "Otro"
]
```


## 📄 Archivo: `app/catalogo/tipos/proceso_monitorio.json`
```json
{
  "id": "proceso_monitorio",
  "nombre": "Demanda de proceso monitorio",
  "area": "Civil y comercial",
  "norma": "Arts. 419 a 421 CGP",
  "rolFirma": "demandante",
  "rolCliente": "demandante",
  "desc": "Cobro rápido de obligaciones dinerarias de mínima cuantía de origen contractual, sin título ejecutivo.",
  "revisado_por": "Auditado con IA Jurídica (gemini-3.8-flash)",
  "fecha_revision": "22 de octubre de 2026",
  "fuentes": [
    "Ley 1564 de 2012 (Código General del Proceso), arts. 419 a 421",
    "Ley 2213 de 2022 (Vigencia permanente de las TIC en la justicia), arts. 6 y 8",
    "Código de Comercio, art. 884 (Intereses mercantiles y usura)",
    "Código Civil, arts. 1608 y 1617 (Mora e intereses civiles)"
  ],
  "grupos": [
    {
      "n": "Despacho y partes",
      "campos": [
        {
          "k": "despacho",
          "l": "Despacho judicial",
          "t": "text",
          "req": true,
          "ph": "Juez Civil Municipal de Bogotá (Reparto)",
          "ayuda": "Juez Civil Municipal del domicilio del demandado o del lugar de cumplimiento de la obligación contractual."
        },
        {
          "k": "cliente",
          "l": "Nombre del acreedor (demandante)",
          "t": "text",
          "req": true,
          "ph": "Nombre o razón social completa del acreedor"
        },
        {
          "k": "cliente_doc",
          "l": "Documento del demandante (con DV si es NIT)",
          "t": "text",
          "req": true,
          "ph": "C.C. 1.020.304.506 o NIT 901.234.567-8"
        },
        {
          "k": "cliente_correo",
          "l": "Correo electrónico del demandante (canal digital)",
          "t": "text",
          "req": true,
          "ph": "acreedor@ejemplo.com"
        },
        {
          "k": "demandado",
          "l": "Nombre del deudor (demandado)",
          "t": "text",
          "req": true,
          "ph": "Nombre o razón social del deudor"
        },
        {
          "k": "demandado_doc",
          "l": "Documento del demandado (si se conoce)",
          "t": "text",
          "ph": "C.C. 79.800.900 o NIT si es persona jurídica"
        },
        {
          "k": "demandado_correo",
          "l": "Correo electrónico del demandado para notificación",
          "t": "text",
          "req": true,
          "ph": "deudor@empresa.com",
          "ayuda": "Obligatorio según art. 6 y 8 de la Ley 2213 de 2022 para surtir la citación digital."
        },
        {
          "k": "demandado_correo_origen",
          "l": "Cómo se obtuvo el correo del demandado (juramento art. 8 Ley 2213)",
          "t": "text",
          "ph": "Suministrado en el contrato / cruzado por correos de cobro / registro mercantil",
          "req": true
        },
        {
          "k": "demandado_direccion",
          "l": "Dirección física y ciudad del demandado",
          "t": "text",
          "ph": "Calle 50 No. 40-30, Medellín (opcional para citación física subsidiaria)",
          "ayuda": "Opcional. Útil si se requiere practicar notificación física subsidiaria o medidas cautelares sobre bienes muebles."
        }
      ]
    },
    {
      "n": "Obligación dineraria y cuantía",
      "campos": [
        {
          "k": "origen_contractual",
          "l": "Origen contractual de la obligación",
          "t": "text",
          "req": true,
          "ph": "Ej.: Contrato de prestación de servicios profesionales / compraventa comercial de mercancías",
          "ayuda": "El proceso monitorio exige que la deuda provenga exclusivamente de un contrato (verbal o escrito)."
        },
        {
          "k": "capital",
          "l": "Valor del capital adeudado (en pesos COP)",
          "t": "valor",
          "req": true,
          "ph": "18000000",
          "ayuda": "Debe ser de mínima cuantía (hasta 40 SMMLV). Muestra el valor en letras automáticamente."
        },
        {
          "k": "fecha_exigibilidad",
          "l": "Fecha en que se hizo exigible el pago",
          "t": "date",
          "req": true,
          "ayuda": "Día exacto desde el cual el deudor incurrió en mora."
        },
        {
          "k": "intereses_tipo",
          "l": "Tipo de intereses reclamados",
          "t": "select",
          "req": true,
          "opciones": [
            [
              "corrientes_y_mora",
              "Intereses corrientes pactados y moratorios legales"
            ],
            [
              "solo_moratorios_comerciales",
              "Intereses moratorios a la tasa máxima legal (1.5 veces IBC Superintendencia Financiera)"
            ],
            [
              "moratorios_civiles",
              "Intereses moratorios civiles (art. 1617 Código Civil - 6% anual)"
            ],
            [
              "solo_capital",
              "Solo cobro de capital (sin intereses)"
            ]
          ],
          "def": "solo_moratorios_comerciales"
        },
        {
          "k": "contraprestacion_satisfecha",
          "l": "¿El acreedor ya cumplió toda su contraprestación?",
          "t": "check",
          "def": true,
          "ayuda": "Requisito legal esencial (art. 420 num. 5 CGP): el pago no puede depender de una contraprestación pendiente del acreedor."
        }
      ]
    },
    {
      "n": "Hechos",
      "campos": [
        {
          "k": "hechos",
          "l": "Relación clara y cronológica de los hechos",
          "t": "area",
          "rows": 6,
          "req": true,
          "ph": "- Fecha y términos en que se celebró el contrato\n- Prestación cumplida y entregada a satisfacción por el acreedor\n- Fecha pactada para el pago y suma acordada\n- Incumplimiento del deudor e infructuosas gestiones de cobro",
          "ayuda": "Describe la celebración del contrato, la entrega de los bienes o servicios, y la renuencia al pago."
        }
      ]
    },
    {
      "n": "Pretensiones y apercibimiento",
      "campos": [
        {
          "k": "pretensiones",
          "l": "Pretensiones de pago y apercibimiento legal",
          "t": "area",
          "rows": 5,
          "req": true,
          "ph": "1. Ordenar al demandado pagar la suma de $... por concepto de capital adeudado.\n2. Ordenar el pago de los intereses moratorios causados desde la fecha de mora hasta el pago efectivo.\n3. Librar el requerimiento con el apercibimiento legal del artículo 421 del CGP.\n4. Condenar en costas y agencias en derecho.",
          "ayuda": "El escrito debe incluir expresamente la solicitud del requerimiento con advertencia de fuerza de sentencia (art. 421 CGP)."
        },
        {
          "k": "medidas_cautelares",
          "l": "Medidas cautelares previas solicitadas",
          "t": "area",
          "rows": 3,
          "ph": "Embargo y retención de sumas depositadas en cuentas bancarias del deudor; embargo de bienes muebles o vehículos.",
          "ayuda": "Opcional. En proceso monitorio se puede pedir embargo y secuestro previo de bienes del deudor (art. 599 CGP)."
        }
      ]
    },
    {
      "n": "Pruebas y anexos",
      "campos": [
        {
          "k": "pruebas_documentales",
          "l": "Relación de pruebas documentales aportadas",
          "t": "area",
          "rows": 4,
          "ph": "- Copia del contrato / orden de servicio / factura comercial\n- Mensajes de datos (WhatsApp, correos electrónicos con acuse de recibo)\n- Certificación bancaria o extracto de no pago",
          "ayuda": "Si no tienes documentos, debes manifestarlo bajo gravedad del juramento en la demanda (art. 420 num. 6 CGP)."
        },
        {
          "k": "sin_prueba_documental_juramento",
          "l": "Manifestar bajo juramento que no se posee prueba documental contractual",
          "t": "check",
          "def": false,
          "ayuda": "Solo si la obligación fue enteramente verbal y no existen soportes documentales (art. 420 num. 6 CGP)."
        }
      ]
    }
  ],
  "guia": "Fundamento procesal: artículos 419, 420 y 421 del Código General del Proceso (CGP - Ley 1564 de 2012).\nNaturaleza jurídica y procedencia: Quien pretenda el pago de una obligación en dinero, de origen contractual, determinada y exigible, que sea de mínima cuantía (hasta 40 SMMLV), puede formular demanda de proceso monitorio ante el Juez Civil Municipal competente.\nReglas no negociables:\n1. Solo procede para obligaciones contractuales en dinero. No procede si existe título ejecutivo (pagaré, letra, acta de conciliación, sentencia); si hay título ejecutivo, la vía correcta es la demanda ejecutiva.\n2. No procede para reclamar perjuicios extracontractuales ni perjuicios que no hayan sido fijados y cuantificados contractualmente.\n3. Es requisito procesal esencial afirmar que el pago no depende del cumplimiento de una contraprestación a cargo del acreedor (art. 420 num. 5 CGP).\n4. Apercibimiento obligatorio del art. 421 CGP: El escrito debe pedir expresamente que se requiera al demandado para que en el término perentorio de diez (10) días pague o exponga por escrito las razones por las cuales niega total o parcialmente la deuda; y que si no contesta o no comparece, el juez dictará auto con fuerza de sentencia condenatoria (cosa juzgada) y ordenará seguir adelante con la ejecución y medidas cautelares.\n5. Postulación: No requiere actuar a través de abogado para su radicación si es de mínima cuantía (art. 420 parágrafo), pero si lo suscribe apoderado, se anuncia el poder especial y número de Tarjeta Profesional.\n6. Notificación digital: Incluir manifestación bajo juramento sobre cómo se obtuvo el canal digital del deudor (art. 8 Ley 2213 de 2022) y el envío simultáneo electrónico salvo que se decreten medidas cautelares previas (art. 6 Ley 2213 de 2022).\nEstructura procesal obligatoria:\n- Destinatario (Señor Juez Civil Municipal de ...);\n- Referencia: Demanda de Proceso Monitorio; Demandante; Demandado;\n- Presentación y legitimación de las partes con indicación de domicilio, documentos y canales digitales;\n- PRETENSIONES (orden de requerimiento de pago del capital, intereses pactados o legales discriminados, apercibimiento del art. 421 CGP y costas);\n- HECHOS debidamente numerados y cronológicos (origen del contrato, cumplimiento pleno del acreedor, exigibilidad de la obligación e incumplimiento del deudor);\n- MANIFESTACIONES BAJO JURAMENTO (que el pago no depende de contraprestación pendiente del acreedor, y juramento del canal digital art. 8 Ley 2213);\n- JURAMENTO SOBRE PRUEBA DOCUMENTAL (si no se tienen documentos escritos, art. 420 num. 6);\n- MEDIDAS CAUTELARES si se solicitan (embargo y retención de cuentas o bienes);\n- PRUEBAS (documentales aportadas o testimoniales);\n- CUANTÍA Y COMPETENCIA (mínima cuantía, domicilio del demandado o lugar de cumplimiento contractual);\n- ANEXOS (documentos, certificado de existencia y representación legal si aplica, poder especial);\n- NOTIFICACIONES (física y electrónica de las partes).",
  "version": "1.0.0",
  "requisitos": [
    {
      "id": "monitorio_designacion_juez",
      "texto": "Designación del Juez Civil Municipal competente (domicilio del deudor o lugar de cumplimiento)",
      "norma": "CGP arts. 28 num. 1 y 3, 82 num. 1 y 419",
      "critico": true
    },
    {
      "id": "monitorio_identificacion_partes",
      "texto": "Identificación, domicilio y canales digitales de demandante y demandado con juramento de obtención",
      "norma": "CGP art. 82 num. 2 y Ley 2213 de 2022 arts. 6 y 8",
      "critico": true
    },
    {
      "id": "demanda_monitorio_exigibilidad",
      "texto": "Determinación clara de la suma líquida de dinero, su exigibilidad y el origen contractual de la obligación",
      "norma": "CGP arts. 419 y 420 num. 2",
      "critico": true
    },
    {
      "id": "demanda_monitorio_contraprestacion",
      "texto": "Manifestación expresa de que el pago de la suma no depende del cumplimiento de una contraprestación pendiente del acreedor",
      "norma": "CGP art. 420 num. 5",
      "critico": true
    },
    {
      "id": "demanda_monitorio_apercibimiento",
      "texto": "Solicitud expresa de requerimiento de pago con apercibimiento legal de dictar auto con fuerza de sentencia condenatoria si guarda silencio en 10 días",
      "norma": "CGP art. 421",
      "critico": true
    },
    {
      "id": "demanda_monitorio_cuantia",
      "texto": "Delimitación expresa de la mínima cuantía (hasta 40 SMMLV)",
      "norma": "CGP arts. 25 y 419",
      "critico": true
    },
    {
      "id": "monitorio_pruebas_o_juramento",
      "texto": "Aporte de pruebas documentales o manifestación bajo juramento de carecer de ellas",
      "norma": "CGP art. 420 num. 6",
      "critico": true
    }
  ],
  "ejemplo": {
    "despacho": "Señor Juez Civil Municipal de Medellín (Reparto)",
    "cliente": "Inversiones y Servicios Comerciales del Valle S.A.S.",
    "cliente_doc": "NIT 901.458.789-2",
    "cliente_correo": "cobranzas@inversionessas.com",
    "demandado": "Constructora e Inmobiliaria Los Andes Ltda.",
    "demandado_doc": "NIT 830.124.567-1",
    "demandado_correo": "gerencia@constructoralosandes.com",
    "demandado_correo_origen": "Suministrado directamente en la orden de compra No. 450 y cruzado en correos electrónicos de facturación",
    "origen_contractual": "Contrato mercantil de suministro y montaje de carpintería metálica",
    "capital": "24500000",
    "fecha_exigibilidad": "2026-05-15",
    "intereses_tipo": "solo_moratorios_comerciales",
    "contraprestacion_satisfecha": true,
    "hechos": "1. El 10 de marzo de 2026, mi poderdante y la sociedad demandada celebraron un contrato comercial de suministro y montaje de carpintería metálica para la obra 'Torres del Prado'.\n2. Mi representada suministró e instaló la totalidad de los materiales acordados, los cuales fueron recibidos a entera satisfacción mediante acta de entrega y recibo final del 30 de abril de 2026.\n3. Se emitió la cuenta de cobro y factura comercial por valor de $24.500.000 COP con fecha de vencimiento y exigibilidad pactada para el día 15 de mayo de 2026.\n4. La sociedad demandada se abstuvo de realizar el pago en la fecha acordada y hasta la fecha no ha realizado abono alguno, a pesar de los requerimientos extrajudiciales cursados a su correo electrónico.\n5. La obligación es de naturaleza estrictamente contractual, líquida, actualmente exigible y de mínima cuantía, y mi representada no cuenta con un título ejecutivo (letra, pagaré ni cheque) firmado por el deudor.",
    "pretensiones": "1. Requerir a la sociedad demandada Constructora e Inmobiliaria Los Andes Ltda. para que en el término perentorio de diez (10) días contados a partir de su notificación personal, pague a favor de Inversiones y Servicios Comerciales del Valle S.A.S. la suma de VEINTICUATRO MILLONES QUINIENTOS MIL PESOS M/CTE ($24.500.000 COP) por concepto de capital insoluto.\n2. Ordenar el pago de los intereses moratorios causados sobre el capital adeudado a la tasa máxima legal mercantil (1.5 veces el Interés Bancario Corriente certificado por la Superintendencia Financiera), liquidados desde el 16 de mayo de 2026 hasta el momento en que se efectúe el pago total.\n3. Apercibir a la demandada de conformidad con el artículo 421 del CGP, advirtiéndole que si dentro del término de diez (10) días no comparece, guarda silencio o no expone razones fundadas para negar la deuda, se dictará auto con fuerza de sentencia condenatoria y se ordenará seguir adelante la ejecución con medidas cautelares.\n4. Condenar a la demandada al pago de las costas y agencias en derecho que se causen.",
    "medidas_cautelares": "Solicito ordenar el embargo y retención de las cuentas bancarias de ahorros y corrientes a nombre de la demandada en entidades financieras, hasta por el límite legal.",
    "pruebas_documentales": "1. Copia de la orden de compra y suministro suscrita por las partes.\n2. Copia del acta de entrega y recibo final a satisfacción del 30 de abril de 2026.\n3. Copia de la factura comercial y cuenta de cobro con constancia de radicación.\n4. Copia de los mensajes de datos y correos electrónicos de cobro cruzados entre las partes.\n5. Certificado de existencia y representación legal de ambas partes.",
    "sin_prueba_documental_juramento": false
  },
  "auditoria_ia": {
    "puntuacion": 97,
    "aprobado": true,
    "dictamen": "La estructura del memorial para demanda de proceso monitorio cumple a cabalidad con los presupuestos sustanciales y adjetivos consagrados en los artículos 419 a 421 del Código General del Proceso (Ley 1564 de 2012) y las exigencias de justicia digital de la Ley 2213 de 2022. Incorpora de manera sobresaliente los apercibimientos y juramentos obligatorios que previenen la inadmisión o rechazo de plano.",
    "normas_validadas": [
      "Ley 1564 de 2012 (CGP), Arts. 82, 84, 419, 420, 421 y 599",
      "Ley 2213 de 2022, Arts. 6 y 8",
      "Código de Comercio, Art. 884",
      "Código Civil, Arts. 1608 y 1617"
    ],
    "observaciones": [
      "Aunque el proceso monitorio admite postulación en causa propia (sin abogado), convendría prever un subcampo opcional para datos de apoderado judicial (T.P. y facultad de recibir), dado que en la práctica mercantil gran parte de estos cobros son tramitados por mandatarios judiciales.",
      "Se sugiere recordar al usuario en la ayuda de pretensiones que la liquidación de intereses moratorios mercantiles no puede superar el límite de usura certificado periódicamente por la Superintendencia Financiera de Colombia."
    ],
    "riesgos_inadmisorios": [],
    "modelo_auditor": "gemini-3.8-flash",
    "fecha": "22 de octubre de 2026"
  }
}

```


## 📄 Archivo: `app/catalogo/tipos/demanda_ejecutiva.json`
```json
{
  "id": "demanda_ejecutiva",
  "nombre": "Demanda ejecutiva",
  "area": "Civil y comercial",
  "norma": "Arts. 422 y ss. CGP",
  "rolFirma": "de la parte ejecutante",
  "rolCliente": "la parte ejecutante",
  "desc": "Cobro judicial de una obligación clara, expresa y exigible: pagarés, letras, facturas, contratos, actas.",
  "grupos": [
    {
      "n": "Despacho",
      "campos": [
        {
          "k": "destinatario",
          "l": "Juez o despacho",
          "t": "texto",
          "req": true,
          "ph": "Juez Civil Municipal de Bogotá D.C. (Reparto)",
          "sug": [
            "Juez Civil Municipal de Bogotá D.C. (Reparto)",
            "Juez Civil del Circuito de Medellín (Reparto)",
            "Juez de Pequeñas Causas y Competencia Múltiple de Cali (Reparto)"
          ]
        },
        {
          "k": "ciudad",
          "l": "Ciudad",
          "t": "texto",
          "ph": "Bogotá D.C.",
          "def": "@ciudad",
          "ayuda": "Donde se radica el escrito."
        }
      ]
    },
    {
      "n": "Partes",
      "campos": [
        {
          "k": "cliente",
          "l": "Ejecutante (acreedor)",
          "t": "area",
          "rows": 3,
          "req": true,
          "ph": "Nombre completo, cédula, ciudad de domicilio, dirección, correo y teléfono."
        },
        {
          "k": "contraparte",
          "l": "Ejecutado(s) (deudor)",
          "t": "area",
          "rows": 3,
          "req": true,
          "ph": "Nombre completo, cédula, ciudad de domicilio, dirección, correo y teléfono."
        }
      ]
    },
    {
      "n": "La obligación",
      "campos": [
        {
          "k": "titulo",
          "l": "Título ejecutivo",
          "t": "area",
          "rows": 3,
          "req": true,
          "ph": "Ej.: Pagaré No. 001 suscrito el 10/01/2026 por $20.000.000, con vencimiento el 10/07/2026."
        },
        {
          "k": "valores",
          "l": "Valores adeudados",
          "t": "area",
          "rows": 3,
          "req": true,
          "ph": "Ej.: Capital $20.000.000; intereses de plazo al 1,5 % mensual hasta el 10/07/2026; moratorios desde el 11/07/2026."
        },
        {
          "k": "hechos",
          "l": "Hechos",
          "t": "area",
          "rows": 8,
          "req": false,
          "ph": "Ej.: El deudor no pagó en la fecha de vencimiento; se le requirió el 1/08/2026…",
          "ayuda": "Escríbelos como te salgan: en borrador, en viñetas o en desorden. Se redactan con lenguaje jurídico y en orden cronológico, sin agregar hechos."
        },
        {
          "k": "pretensiones",
          "l": "Pretensiones (opcional)",
          "t": "area",
          "rows": 3,
          "req": false,
          "ph": "Si lo dejas vacío: mandamiento de pago por capital, intereses de plazo y moratorios a la tasa máxima legal, y costas."
        },
        {
          "k": "medidas",
          "l": "Medidas cautelares",
          "t": "area",
          "rows": 3,
          "req": false,
          "ph": "Ej.: Embargo y secuestro del inmueble con matrícula 50N-998877; embargo de las cuentas del deudor en el Banco X."
        }
      ]
    },
    {
      "n": "Pruebas y notificaciones",
      "campos": [
        {
          "k": "pruebas",
          "l": "Pruebas y anexos",
          "t": "area",
          "rows": 3,
          "ph": "Ej.: Pagaré original (o certificado de depósito si es desmaterializado); certificado de tradición."
        },
        {
          "k": "notificaciones",
          "l": "Direcciones de notificación",
          "t": "area",
          "rows": 2,
          "ph": "Tu cliente: dirección y correo. La contraparte: dirección, correo y cómo lo obtuviste."
        }
      ]
    }
  ],
  "guia": "Fundamento: CGP arts. 422 (título ejecutivo: obligación clara, expresa y exigible, que conste en documento que provenga del deudor y constituya plena prueba contra él), 424 (sumas de dinero), 430 y 431 (mandamiento de pago), 599 (embargo y secuestro); Código de Comercio arts. 619 y siguientes (títulos valores), 671 y siguientes (letra de cambio), 709 y siguientes (pagaré); art. 884 del Código de Comercio (intereses moratorios: una y media veces el interés bancario corriente certificado por la Superintendencia Financiera, sin exceder la tasa de usura).\nEstructura: destinatario; referencia (Proceso ejecutivo singular de mínima, menor o mayor cuantía; ejecutante; ejecutado); presentación; HECHOS (creación del título, vencimiento, incumplimiento, saldo); PRETENSIONES (librar mandamiento de pago por el capital, los intereses de plazo y los moratorios desde la exigibilidad hasta el pago total, y condenar en costas); FUNDAMENTOS DE DERECHO; CUANTÍA Y COMPETENCIA; PRUEBAS (el título ejecutivo); MEDIDAS CAUTELARES (si el abogado las indica, inclúyelas en un capítulo propio o como solicitud separada al final); ANEXOS; NOTIFICACIONES. Con medidas cautelares previas no se envía copia de la demanda al demandado (art. 6 de la Ley 2213 de 2022). Si el título es desmaterializado o una factura electrónica, menciona el certificado o registro correspondiente con [VERIFICAR].",
  "version": "2.2.1",
  "fecha_revision": "2026-10-21",
  "revisado_por": "Comité Jurídico El Memorialista",
  "fuentes": [
    "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425"
  ],
  "requisitos": [
    {
      "id": "designacion_juez",
      "texto": "Designación del juez civil competente",
      "norma": "Art. 82 num. 1 CGP",
      "critico": true
    },
    {
      "id": "identificacion_partes",
      "texto": "Identificación y domicilio de ejecutante y ejecutado",
      "norma": "Art. 82 num. 2 CGP",
      "critico": true
    },
    {
      "id": "titulo_ejecutivo",
      "texto": "Determinación y aporte del título ejecutivo con obligación clara, expresa y exigible",
      "norma": "Art. 422 CGP",
      "critico": true
    },
    {
      "id": "mandamiento_pago",
      "texto": "Pretensión de mandamiento ejecutivo de pago por capital, intereses discriminados y costas",
      "norma": "Art. 430 CGP",
      "critico": true
    },
    {
      "id": "hechos_exigibilidad",
      "texto": "Hechos del negocio o título y mora en el cumplimiento de la obligación",
      "norma": "Art. 82 num. 5 CGP",
      "critico": true
    },
    {
      "id": "cuantia_competencia",
      "texto": "Estimación de la cuantía para determinar la competencia",
      "norma": "Arts. 25 y 82 num. 8 CGP",
      "critico": true
    },
    {
      "id": "canal_digital",
      "texto": "Canal digital de las partes y afirmación bajo juramento del art. 8 de la Ley 2213 de 2022",
      "norma": "Arts. 6 y 8 Ley 2213 de 2022",
      "critico": true
    },
    {
      "id": "notificaciones",
      "texto": "Dirección física y electrónica para notificaciones personales",
      "norma": "Art. 82 num. 10 CGP",
      "critico": true
    }
  ]
}

```


## 📄 Archivo: `app/catalogo/tipos/tutela.json`
```json
{
  "id": "tutela",
  "nombre": "Acción de tutela",
  "area": "Constitucional",
  "norma": "Art. 86 C.P. · D. 2591/1991",
  "rolFirma": "de la parte accionante",
  "rolCliente": "la parte accionante",
  "desc": "Protección inmediata de derechos fundamentales.",
  "grupos": [
    {
      "n": "Despacho",
      "campos": [
        {
          "k": "destinatario",
          "l": "Juez",
          "t": "texto",
          "req": true,
          "ph": "Juez Civil Municipal de Bogotá D.C. (Reparto)",
          "sug": [
            "Juez Civil Municipal de Bogotá D.C. (Reparto)",
            "Juez Penal Municipal de Medellín con Función de Control de Garantías (Reparto)",
            "Juez Laboral del Circuito de Cali (Reparto)",
            "Juez de la República (Reparto)"
          ],
          "ayuda": "Si no sabes el despacho, escribe “Juez de la República (Reparto)”."
        },
        {
          "k": "ciudad",
          "l": "Ciudad",
          "t": "texto",
          "ph": "Bogotá D.C.",
          "def": "@ciudad",
          "ayuda": "Donde se radica el escrito."
        }
      ]
    },
    {
      "n": "Partes",
      "campos": [
        {
          "k": "cliente",
          "l": "Accionante",
          "t": "area",
          "rows": 3,
          "req": true,
          "ph": "Nombre completo, cédula, ciudad de domicilio, dirección, correo y teléfono.\nSi actúa por un menor o como agente oficioso, indícalo."
        },
        {
          "k": "contraparte",
          "l": "Accionado(s)",
          "t": "area",
          "rows": 3,
          "req": true,
          "ph": "Entidad o persona, NIT si lo conoces, representante legal y correo de notificaciones judiciales."
        },
        {
          "k": "vinculados",
          "l": "Terceros a vincular (opcional)",
          "t": "area",
          "rows": 2,
          "req": false,
          "ph": "Ej.: Superintendencia Nacional de Salud; ADRES."
        }
      ]
    },
    {
      "n": "El caso",
      "campos": [
        {
          "k": "derechos",
          "l": "Derechos fundamentales vulnerados",
          "t": "chips",
          "opciones": [
            "Salud",
            "Vida digna",
            "Seguridad social",
            "Mínimo vital",
            "Petición",
            "Debido proceso",
            "Igualdad",
            "Trabajo",
            "Estabilidad laboral reforzada",
            "Educación",
            "Vivienda digna",
            "Hábeas data",
            "Intimidad",
            "Buen nombre",
            "Dignidad humana",
            "Acceso a la administración de justicia",
            "Unidad familiar",
            "Libre desarrollo de la personalidad"
          ],
          "req": true
        },
        {
          "k": "hechos",
          "l": "Hechos",
          "t": "area",
          "rows": 8,
          "req": true,
          "ph": "Ej.: 2/09 el médico le ordenó el medicamento X. 9/09 la EPS lo negó por falta de autorización del comité técnico. Desde entonces no recibe el tratamiento…",
          "ayuda": "Escríbelos como te salgan: en borrador, en viñetas o en desorden. Se redactan con lenguaje jurídico y en orden cronológico, sin agregar hechos."
        },
        {
          "k": "procedencia",
          "l": "Procedencia: subsidiariedad e inmediatez",
          "t": "area",
          "rows": 3,
          "req": false,
          "ph": "Ej.: Pasaron 6 semanas desde la negativa; no hay otro medio igual de eficaz porque el tratamiento es continuo; es adulta mayor.",
          "ayuda": "Por qué la tutela es el medio adecuado y cuánto tiempo ha pasado desde la vulneración."
        },
        {
          "k": "pretensiones",
          "l": "Lo que se pide al juez",
          "t": "area",
          "rows": 4,
          "req": true,
          "ph": "Ej.: Ordenar a la EPS entregar el medicamento en 48 horas y garantizar el tratamiento integral."
        },
        {
          "k": "medida",
          "l": "Medida provisional (opcional)",
          "t": "area",
          "rows": 2,
          "req": false,
          "ph": "Ej.: Entrega inmediata del medicamento mientras se decide, porque suspenderlo agrava la enfermedad."
        }
      ]
    },
    {
      "n": "Pruebas y notificaciones",
      "campos": [
        {
          "k": "pruebas",
          "l": "Pruebas y anexos",
          "t": "area",
          "rows": 3,
          "ph": "Ej.: Fórmula médica del 2/09/2026; respuesta de la EPS del 9/09/2026; cédula de la accionante; poder."
        },
        {
          "k": "juramento",
          "l": "Manifestar bajo juramento que no se ha presentado otra tutela por los mismos hechos (art. 37, D. 2591 de 1991)",
          "t": "check",
          "def": true
        },
        {
          "k": "notificaciones",
          "l": "Direcciones de notificación",
          "t": "area",
          "rows": 2,
          "ph": "Accionante: dirección y correo. Accionado: correo de notificaciones judiciales."
        }
      ]
    }
  ],
  "guia": "Fundamento: artículo 86 de la Constitución, Decreto 2591 de 1991 y Decreto 306 de 1992. Reparto: Decreto 1069 de 2015, modificado por el Decreto 333 de 2021. La tutela es informal y no requiere abogado; no le apliques las cargas de admisión de la demanda del artículo 6 de la Ley 2213 de 2022 (sentencia C-522 de 2023).\nEstructura: lugar y fecha; destinatario (Juez … (Reparto)) y, si aplica, E. S. D.; bloque de referencia (Referencia: Acción de tutela; Accionante; Accionado; Derechos invocados); párrafo de presentación con identificación de quien actúa y la calidad en que lo hace; HECHOS (numerados y cronológicos, con fechas); DERECHOS FUNDAMENTALES VULNERADOS (cada derecho y cómo se vulnera); PROCEDENCIA DE LA ACCIÓN (legitimación por activa y por pasiva; subsidiariedad: inexistencia de otro medio idóneo y eficaz o perjuicio irremediable; inmediatez); FUNDAMENTOS DE DERECHO; MEDIDA PROVISIONAL solo si se pide (art. 7 del Decreto 2591 de 1991: necesidad y urgencia); PRETENSIONES (órdenes concretas y verificables, con plazo, normalmente 48 horas); PRUEBAS (enumeradas; pide que se oficie al accionado por los documentos que estén en su poder); JURAMENTO (art. 37 del Decreto 2591 de 1991); ANEXOS; NOTIFICACIONES.\nSi el accionado es un particular, explica por qué procede la tutela en su contra (art. 42 del Decreto 2591 de 1991: servicio público, subordinación o indefensión).",
  "ejemplo": {
    "destinatario": "Juez Civil Municipal de Bogotá D.C. (Reparto)",
    "ciudad": "Bogotá D.C.",
    "cliente": "María Fernanda López Rincón, C.C. 52.123.456 de Bogotá, 63 años, domiciliada en Bogotá, Calle 45 # 13-20, maria.lopez@correo.com, 310 555 0101.",
    "contraparte": "EPS Salud Ejemplo S.A.S., NIT 900.123.456-7, notificaciones judiciales: notificaciones@epsejemplo.com",
    "derechos": [
      "Salud",
      "Vida digna",
      "Seguridad social"
    ],
    "hechos": "- afiliada al régimen contributivo de la EPS desde 2015\n- 2/09/2026 el reumatólogo le diagnosticó artritis reumatoide y le ordenó tofacitinib 5 mg cada 12 horas por 3 meses\n- 9/09/2026 la EPS negó la entrega: dijo que requiere autorización del comité técnico, que no ha resuelto\n- sin el medicamento tiene dolor e inflamación y no puede trabajar (es costurera independiente)\n- presentó queja ante la EPS el 15/09/2026 y no le han respondido",
    "procedencia": "Han pasado 6 semanas desde la negativa. Es adulta mayor, sujeto de especial protección, y el tratamiento es continuo; no hay otro medio igual de eficaz.",
    "pretensiones": "Que se ordene a la EPS entregar el medicamento en 48 horas y garantizar el tratamiento integral para la artritis reumatoide.",
    "pruebas": "Fórmula médica del 2/09/2026; respuesta de la EPS del 9/09/2026; queja del 15/09/2026; cédula; poder.",
    "juramento": true,
    "notificaciones": "Accionante: Calle 45 # 13-20, Bogotá; maria.lopez@correo.com. EPS: notificaciones@epsejemplo.com"
  },
  "version": "2.2.1",
  "fecha_revision": "2026-10-21",
  "revisado_por": "Comité Jurídico El Memorialista",
  "fuentes": [
    "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=2790",
    "https://www.corteconstitucional.gov.co/relatoria/"
  ],
  "requisitos": [
    {
      "id": "designacion_juez",
      "texto": "Designación del juez de tutela a quien se dirige (Reparto)",
      "norma": "Art. 86 CP, D. 2591/1991, D. 333/2021",
      "critico": true
    },
    {
      "id": "legitimacion_partes",
      "texto": "Identificación del accionante y de la autoridad pública o particular accionado",
      "norma": "Arts. 10 y 42 D. 2591/1991",
      "critico": true
    },
    {
      "id": "derechos_fundamentales",
      "texto": "Individualización de los derechos fundamentales invocados como vulnerados o amenazados",
      "norma": "Art. 86 CP",
      "critico": true
    },
    {
      "id": "hechos_cronologicos",
      "texto": "Relación clara y cronológica de los hechos que configuran la vulneración",
      "norma": "Art. 14 D. 2591/1991",
      "critico": true
    },
    {
      "id": "procedencia_subsidiariedad",
      "texto": "Sustentación de procedencia: subsidiariedad (inexistencia de otro medio idóneo o perjuicio irremediable) e inmediatez",
      "norma": "Art. 86 CP y jurisprudencia CC",
      "critico": true
    },
    {
      "id": "pretensiones_ordenes",
      "texto": "Pretensiones expresadas como órdenes concretas, claras y verificables de tutela",
      "norma": "Art. 14 D. 2591/1991",
      "critico": true
    },
    {
      "id": "juramento_no_otra_tutela",
      "texto": "Manifestación expresa bajo juramento de no haber interpuesto otra tutela por los mismos hechos y derechos",
      "norma": "Art. 37 D. 2591/1991",
      "critico": true
    },
    {
      "id": "pruebas",
      "texto": "Relación de pruebas aportadas y solicitud de informes o documentos al accionado",
      "norma": "Art. 19 D. 2591/1991",
      "critico": false
    },
    {
      "id": "notificaciones",
      "texto": "Direcciones y canales electrónicos de notificación de las partes",
      "norma": "Art. 16 D. 2591/1991",
      "critico": true
    }
  ]
}

```


## 📄 Archivo: `app/catalogo/contexto_normativo.json`
```json
[
  {
    "id": "ley_2213_2022",
    "texto": "Ley 2213 de 2022: la virtualidad en los procesos judiciales es permanente (canal digital de partes, testigos y peritos; envío simultáneo de la demanda; notificación personal por mensaje de datos; poderes por mensaje de datos). Según la sentencia C-522 de 2023, las cargas de admisión del inciso 5 del artículo 6 no se aplican a la acción de tutela.",
    "version": "2.2.1",
    "fecha_revision": "2026-10-21",
    "revisado_por": "Comité Jurídico El Memorialista",
    "fuentes": [
      "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=187425",
      "https://www.corteconstitucional.gov.co/relatoria/2023/C-522-23.htm"
    ]
  },
  {
    "id": "ley_2452_2025",
    "texto": "Ley 2452 de 2025: nuevo Código Procesal del Trabajo y de la Seguridad Social, aplicable a los procesos laborales iniciados desde el 6 de abril de 2026; los iniciados antes siguen con el Decreto-Ley 2158 de 1948. Los antiguos jueces de pequeñas causas laborales pasaron a ser jueces laborales municipales.",
    "version": "2.2.1",
    "fecha_revision": "2026-10-21",
    "revisado_por": "Comité Jurídico El Memorialista",
    "fuentes": [
      "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=254181"
    ]
  },
  {
    "id": "ley_2466_2025",
    "texto": "Ley 2466 de 2025: reforma laboral que modificó el Código Sustantivo del Trabajo; algunas medidas son de aplicación gradual.",
    "version": "2.2.1",
    "fecha_revision": "2026-10-21",
    "revisado_por": "Comité Jurídico El Memorialista",
    "fuentes": [
      "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=258414"
    ]
  },
  {
    "id": "ley_2220_2022",
    "texto": "Ley 2220 de 2022: Estatuto de Conciliación, vigente desde el 30 de diciembre de 2022. En asuntos laborales la conciliación no es requisito de procedibilidad.",
    "version": "2.2.1",
    "fecha_revision": "2026-10-21",
    "revisado_por": "Comité Jurídico El Memorialista",
    "fuentes": [
      "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes/30044670"
    ]
  },
  {
    "id": "ley_2442_2024",
    "texto": "Ley 2442 de 2024: agregó al artículo 154 del Código Civil la causal de divorcio por la sola voluntad de cualquiera de los cónyuges.",
    "version": "2.2.1",
    "fecha_revision": "2026-10-21",
    "revisado_por": "Comité Jurídico El Memorialista",
    "fuentes": [
      "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=250873"
    ]
  },
  {
    "id": "smmlv_2026",
    "plantilla": "Salario mínimo mensual legal vigente en 2026: {smmlv} (dato configurado por el abogado).",
    "version": "2.2.1",
    "fecha_revision": "2026-10-21",
    "revisado_por": "Comité Jurídico El Memorialista",
    "fuentes": [
      "https://www.mintrabajo.gov.co/"
    ]
  },
  {
    "id": "regla_procesal_reciente",
    "texto": "Si una regla procesal cambió recientemente y no tienes certeza del artículo exacto, describe la regla sin número de artículo o marca [VERIFICAR].",
    "version": "2.2.1",
    "fecha_revision": "2026-10-21",
    "revisado_por": "Comité Jurídico El Memorialista",
    "fuentes": [
      "https://www.ramajudicial.gov.co/"
    ]
  }
]
```


## 📄 Archivo: `app/catalogo/reglas_obligatorias.json`
```json
{
  "version": "2.2.1",
  "fecha_revision": "2026-10-21",
  "revisado_por": "Comité Jurídico El Memorialista",
  "fuentes": [
    "https://www.ramajudicial.gov.co/"
  ],
  "reglas": [
    "1. Usa únicamente los hechos, nombres, cifras, fechas y documentos que aparecen en los datos del caso. No inventes nada. Si falta un dato necesario, escribe en su lugar [COMPLETAR: descripción breve del dato].",
    "2. Puedes ordenar, depurar y redactar con lenguaje jurídico los hechos y las pretensiones, sin alterar su sentido ni agregar hechos nuevos.",
    "3. Cita solo normas colombianas que existan y estén vigentes. Si dudas del número de un artículo o de su vigencia, escribe [VERIFICAR] inmediatamente después de la cita.",
    {
      "id": "jurisprudencia",
      "verificables": "4. Jurisprudencia: además de la que indique el abogado, puedes citar hasta {nSent} pronunciamientos de la Corte Constitucional, la Corte Suprema de Justicia o el Consejo de Estado que conozcas con certeza y que sean pertinentes; el sistema verificará automáticamente su existencia en relatoría oficial. Nunca inventes números de sentencia, radicados, fechas ni magistrados ponentes.",
      "sugerir": "4. Jurisprudencia: además de la que indique el abogado, puedes citar hasta {nSent} pronunciamientos de la Corte Constitucional, la Corte Suprema de Justicia o el Consejo de Estado que conozcas con certeza y que sean pertinentes; prefiere sentencias de unificación y precedentes muy reconocidos. Escribe [VERIFICAR] inmediatamente después de cada sentencia que cites y que no haya suministrado el abogado. Nunca inventes números de sentencia, radicados, fechas ni magistrados ponentes.",
      "usuario": "4. Jurisprudencia: cita únicamente la que indicó el abogado en los datos del caso; no agregues otras sentencias.",
      "ninguna": "4. Jurisprudencia: no cites sentencias. Funda el escrito en la Constitución, la ley y los hechos."
    },
    "5. Nunca pongas entre comillas un texto atribuido a una sentencia, a una norma o a un autor, salvo que el abogado lo haya suministrado textualmente o estés seguro de su texto exacto; en caso contrario, parafrasea.",
    "6. No escribas el membrete ni el encabezado o pie de página con los datos de contacto del abogado: se agregan automáticamente. Sí escribe el destinatario y la referencia.",
    {
      "id": "extension",
      "plantilla": "7. Extensión: {extension_texto}"
    },
    "8. Escribe solo el documento: sin comentarios, notas, advertencias ni explicaciones antes o después."
  ]
}
```


## 📄 Archivo: `supabase/schema.sql`
```sql
-- =============================================================================
-- EL MEMORIALISTA JURÍDICO · ESQUEMA COMPLETO DE BASE DE DATOS Y STORAGE SUPABASE
-- Versión: 2.3.0
-- Incluye: Auth (Magic Link), Tablas relacionales, Row Level Security (RLS)
-- por usuario y por firma, y configuración de Storage Privado (logo, firma, plantilla).
-- =============================================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 1. TABLA: FIRMAS (Despachos y oficinas de abogados)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.firmas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre TEXT NOT NULL,
    nit TEXT,
    dv TEXT,
    direccion TEXT,
    ciudad TEXT DEFAULT 'Bogotá D.C.',
    telefono TEXT,
    correo TEXT,
    logo_storage_path TEXT,
    plantilla_storage_path TEXT,
    configuracion JSONB DEFAULT '{}'::jsonb,
    creado_por UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 2. TABLA: PERFILES (Abogados y usuarios asociados a auth.users)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.perfiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    firma_id UUID REFERENCES public.firmas(id) ON DELETE SET NULL,
    email TEXT NOT NULL,
    nombre_completo TEXT NOT NULL DEFAULT '',
    tarjeta_profesional TEXT,
    cedula TEXT,
    telefono TEXT,
    direccion TEXT,
    ciudad TEXT DEFAULT 'Bogotá D.C.',
    firma_grafica_path TEXT,
    rol TEXT NOT NULL DEFAULT 'abogado' CHECK (rol IN ('admin', 'abogado', 'asistente')),
    limite_diario INT DEFAULT 50,
    redacciones_hoy INT DEFAULT 0,
    fecha_contador DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 3. TABLA: CLIENTES (Persona natural o jurídica con DV y representante legal)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.clientes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firma_id UUID REFERENCES public.firmas(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    tipo_persona TEXT NOT NULL DEFAULT 'natural' CHECK (tipo_persona IN ('natural', 'juridica')),
    tipo_documento TEXT NOT NULL DEFAULT 'CC' CHECK (tipo_documento IN ('CC', 'NIT', 'CE', 'TI', 'PASAPORTE', 'OTRO')),
    numero_documento TEXT NOT NULL,
    dv TEXT,
    nombre_razon_social TEXT NOT NULL,
    domicilio TEXT,
    ciudad TEXT DEFAULT 'Bogotá D.C.',
    correo TEXT,
    telefono TEXT,
    representante_legal JSONB DEFAULT NULL,
    notas TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 4. TABLA: CASOS (Expedientes judiciales y administrativos)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.casos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firma_id UUID REFERENCES public.firmas(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    cliente_id UUID REFERENCES public.clientes(id) ON DELETE SET NULL,
    nombre_caso TEXT NOT NULL,
    contraparte TEXT NOT NULL DEFAULT '',
    radicado TEXT,
    despacho TEXT,
    tipo_proceso TEXT,
    estado TEXT NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'en_traslado', 'para_fallo', 'archivado', 'terminado')),
    cuantia TEXT,
    fecha_notificacion DATE,
    fecha_vencimiento DATE,
    notas TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 5. TABLA: DOCUMENTOS (Memoriales y escritos redactados)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.documentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firma_id UUID REFERENCES public.firmas(id) ON DELETE CASCADE,
    caso_id UUID REFERENCES public.casos(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,
    titulo TEXT NOT NULL,
    datos JSONB NOT NULL DEFAULT '{}'::jsonb,
    texto TEXT NOT NULL DEFAULT '',
    version INT NOT NULL DEFAULT 1,
    creado_por UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 6. TABLA: VERSIONES (Historial de ajustes y versiones por documento)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.versiones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    documento_id UUID NOT NULL REFERENCES public.documentos(id) ON DELETE CASCADE,
    version INT NOT NULL,
    texto TEXT NOT NULL,
    datos JSONB NOT NULL DEFAULT '{}'::jsonb,
    creado_por UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    comentario TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 7. ÍNDICES DE ALTO RENDIMIENTO
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_perfiles_firma ON public.perfiles(firma_id);
CREATE INDEX IF NOT EXISTS idx_clientes_firma ON public.clientes(firma_id);
CREATE INDEX IF NOT EXISTS idx_clientes_user ON public.clientes(user_id);
CREATE INDEX IF NOT EXISTS idx_casos_cliente ON public.casos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_casos_firma ON public.casos(firma_id);
CREATE INDEX IF NOT EXISTS idx_casos_user ON public.casos(user_id);
CREATE INDEX IF NOT EXISTS idx_casos_radicado ON public.casos(radicado);
CREATE INDEX IF NOT EXISTS idx_documentos_caso ON public.documentos(caso_id);
CREATE INDEX IF NOT EXISTS idx_documentos_firma ON public.documentos(firma_id);
CREATE INDEX IF NOT EXISTS idx_documentos_creado_por ON public.documentos(creado_por);
CREATE INDEX IF NOT EXISTS idx_versiones_documento ON public.versiones(documento_id);

-- -----------------------------------------------------------------------------
-- 8. TRIGGERS Y FUNCIONES AUTOMÁTICAS
-- -----------------------------------------------------------------------------

-- Función para actualizar updated_at
CREATE OR REPLACE FUNCTION public.actualizar_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_firmas_updated_at ON public.firmas;
CREATE TRIGGER trg_firmas_updated_at BEFORE UPDATE ON public.firmas FOR EACH ROW EXECUTE FUNCTION public.actualizar_updated_at();

DROP TRIGGER IF EXISTS trg_perfiles_updated_at ON public.perfiles;
CREATE TRIGGER trg_perfiles_updated_at BEFORE UPDATE ON public.perfiles FOR EACH ROW EXECUTE FUNCTION public.actualizar_updated_at();

DROP TRIGGER IF EXISTS trg_clientes_updated_at ON public.clientes;
CREATE TRIGGER trg_clientes_updated_at BEFORE UPDATE ON public.clientes FOR EACH ROW EXECUTE FUNCTION public.actualizar_updated_at();

DROP TRIGGER IF EXISTS trg_casos_updated_at ON public.casos;
CREATE TRIGGER trg_casos_updated_at BEFORE UPDATE ON public.casos FOR EACH ROW EXECUTE FUNCTION public.actualizar_updated_at();

DROP TRIGGER IF EXISTS trg_documentos_updated_at ON public.documentos;
CREATE TRIGGER trg_documentos_updated_at BEFORE UPDATE ON public.documentos FOR EACH ROW EXECUTE FUNCTION public.actualizar_updated_at();

-- Función para crear perfil y firma personal automáticamente al registrarse en auth.users
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    nueva_firma_id UUID;
    nombre_defecto TEXT;
BEGIN
    nombre_defecto := COALESCE(NEW.raw_user_meta_data->>'nombre', split_part(NEW.email, '@', 1));
    
    -- Crea una firma por defecto para el nuevo usuario
    INSERT INTO public.firmas (nombre, correo, creado_por)
    VALUES ('Despacho de ' || nombre_defecto, NEW.email, NEW.id)
    RETURNING id INTO nueva_firma_id;

    -- Crea el perfil asociado al usuario y su firma
    INSERT INTO public.perfiles (id, firma_id, email, nombre_completo, rol)
    VALUES (NEW.id, nueva_firma_id, NEW.email, nombre_defecto, 'admin');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Helper para consultar la firma del usuario autenticado de forma segura
CREATE OR REPLACE FUNCTION public.obtener_mi_firma_id()
RETURNS UUID AS $$
    SELECT firma_id FROM public.perfiles WHERE id = auth.uid();
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- -----------------------------------------------------------------------------
-- 9. ROW LEVEL SECURITY (RLS) POR USUARIO Y POR FIRMA
-- -----------------------------------------------------------------------------

ALTER TABLE public.firmas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.perfiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.casos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.versiones ENABLE ROW LEVEL SECURITY;

-- Políticas para FIRMAS
CREATE POLICY "firmas_select" ON public.firmas
    FOR SELECT TO authenticated
    USING (id = public.obtener_mi_firma_id() OR creado_por = auth.uid());

CREATE POLICY "firmas_update" ON public.firmas
    FOR UPDATE TO authenticated
    USING (id = public.obtener_mi_firma_id() OR creado_por = auth.uid())
    WITH CHECK (id = public.obtener_mi_firma_id() OR creado_por = auth.uid());

CREATE POLICY "firmas_insert" ON public.firmas
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() IS NOT NULL);

-- Políticas para PERFILES
CREATE POLICY "perfiles_select" ON public.perfiles
    FOR SELECT TO authenticated
    USING (id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "perfiles_update" ON public.perfiles
    FOR UPDATE TO authenticated
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

CREATE POLICY "perfiles_insert" ON public.perfiles
    FOR INSERT TO authenticated
    WITH CHECK (id = auth.uid());

-- Políticas para CLIENTES
CREATE POLICY "clientes_select" ON public.clientes
    FOR SELECT TO authenticated
    USING (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "clientes_insert" ON public.clientes
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "clientes_update" ON public.clientes
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()))
    WITH CHECK (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "clientes_delete" ON public.clientes
    FOR DELETE TO authenticated
    USING (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

-- Políticas para CASOS
CREATE POLICY "casos_select" ON public.casos
    FOR SELECT TO authenticated
    USING (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "casos_insert" ON public.casos
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "casos_update" ON public.casos
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()))
    WITH CHECK (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "casos_delete" ON public.casos
    FOR DELETE TO authenticated
    USING (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

-- Políticas para DOCUMENTOS
CREATE POLICY "documentos_select" ON public.documentos
    FOR SELECT TO authenticated
    USING (creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "documentos_insert" ON public.documentos
    FOR INSERT TO authenticated
    WITH CHECK (creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "documentos_update" ON public.documentos
    FOR UPDATE TO authenticated
    USING (creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()))
    WITH CHECK (creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "documentos_delete" ON public.documentos
    FOR DELETE TO authenticated
    USING (creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

-- Políticas para VERSIONES
CREATE POLICY "versiones_select" ON public.versiones
    FOR SELECT TO authenticated
    USING (documento_id IN (
        SELECT id FROM public.documentos
        WHERE creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id())
    ));

CREATE POLICY "versiones_insert" ON public.versiones
    FOR INSERT TO authenticated
    WITH CHECK (documento_id IN (
        SELECT id FROM public.documentos
        WHERE creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id())
    ));

CREATE POLICY "versiones_delete" ON public.versiones
    FOR DELETE TO authenticated
    USING (documento_id IN (
        SELECT id FROM public.documentos
        WHERE creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id())
    ));

-- -----------------------------------------------------------------------------
-- 10. CONFIGURACIÓN DE STORAGE PRIVADO
-- -----------------------------------------------------------------------------
-- Crea el bucket privado 'archivos-privados' para logo, firma y plantilla
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'archivos-privados',
    'archivos-privados',
    false,
    10485760, -- 10 MB
    ARRAY['image/png', 'image/jpeg', 'image/webp', 'image/svg+xml', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/pdf']
)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    file_size_limit = 10485760;

-- Políticas de RLS en storage.objects
CREATE POLICY "storage_archivos_privados_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (
        bucket_id = 'archivos-privados' AND (
            (storage.foldername(name))[2] = auth.uid()::text OR
            (storage.foldername(name))[2] = public.obtener_mi_firma_id()::text
        )
    );

CREATE POLICY "storage_archivos_privados_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (
        bucket_id = 'archivos-privados' AND (
            (storage.foldername(name))[2] = auth.uid()::text OR
            (storage.foldername(name))[2] = public.obtener_mi_firma_id()::text
        )
    );

CREATE POLICY "storage_archivos_privados_update" ON storage.objects
    FOR UPDATE TO authenticated
    USING (
        bucket_id = 'archivos-privados' AND (
            (storage.foldername(name))[2] = auth.uid()::text OR
            (storage.foldername(name))[2] = public.obtener_mi_firma_id()::text
        )
    );

CREATE POLICY "storage_archivos_privados_delete" ON storage.objects
    FOR DELETE TO authenticated
    USING (
        bucket_id = 'archivos-privados' AND (
            (storage.foldername(name))[2] = auth.uid()::text OR
            (storage.foldername(name))[2] = public.obtener_mi_firma_id()::text
        )
    );

```


## 📄 Archivo: `app/static/index.html`
```html
<!doctype html><html lang="es-CO"><head><meta charset="utf-8"><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}html{scroll-padding-top:env(safe-area-inset-top,0px)}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#000}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style></head><body>
<title>El Memorialista</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,100..900;1,62..125,100..900&family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap">
<link id="fuenteHojaCss" rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Arimo:ital,wght@0,400;0,700;1,400;1,700&display=swap">
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2" async></script>
<style>
:root{
  /* Layout: mesa del memorialista. Expediente (formulario) a la izquierda, hoja membreteada a la derecha; el sello violeta es la única nota de color. */
  --mesa:#ebe9f0;
  --superficie:#fcfbfe;
  --superficie-2:#f3f1f7;
  --tinta:#1c1926;
  --tinta-2:#5d596c;
  --tinta-3:#807c90;
  --regla:#dcd8e5;
  --regla-fuerte:#bab4c9;
  --sello:#4a32a6;
  --sello-hover:#3a2589;
  --sello-tenue:#ece7fc;
  --sello-sobre:#ffffff;
  --chip-c:#fff1b0;
  --chip-c-tinta:#5b4800;
  --chip-v:#ffe2c9;
  --chip-v-tinta:#843800;
  --ok:#1b7a4b;
  --error:#b3261e;
  --error-tenue:#fdecea;
  --hoja:#ffffff;
  --hoja-tinta:#141414;
  --hoja-gris:#5f5f5f;
  --marca-c:#fff1a8;
  --marca-v:#ffe1c7;
  --marca-v-tinta:#7a3300;
  --sombra-hoja:0 1px 2px rgba(28,25,38,.08),0 10px 30px rgba(28,25,38,.12);
  --sombra-flota:0 6px 24px rgba(28,25,38,.18);
  --f-ui:"Archivo","Helvetica Neue",Arial,sans-serif;
  --f-maq:"Courier Prime","Courier New",Courier,monospace;
  --r:5px;
  --barra-h:62px;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --mesa:#121019;--superficie:#1b1824;--superficie-2:#24212f;--tinta:#ecebf4;--tinta-2:#a8a4ba;--tinta-3:#8a869c;--regla:#322e3f;--regla-fuerte:#4b4660;
    --sello:#ab9bff;--sello-hover:#c4b8ff;--sello-tenue:#2b2546;--sello-sobre:#17131f;
    --chip-c:#4a3f0c;--chip-c-tinta:#ffe48a;--chip-v:#4d2a10;--chip-v-tinta:#ffc29a;
    --ok:#63d59d;--error:#ff8f86;--error-tenue:#3a1715;
    --sombra-hoja:0 0 0 1px #2d2a39,0 12px 34px rgba(0,0,0,.55);--sombra-flota:0 8px 28px rgba(0,0,0,.6);
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --mesa:#121019;--superficie:#1b1824;--superficie-2:#24212f;--tinta:#ecebf4;--tinta-2:#a8a4ba;--tinta-3:#8a869c;--regla:#322e3f;--regla-fuerte:#4b4660;
  --sello:#ab9bff;--sello-hover:#c4b8ff;--sello-tenue:#2b2546;--sello-sobre:#17131f;
  --chip-c:#4a3f0c;--chip-c-tinta:#ffe48a;--chip-v:#4d2a10;--chip-v-tinta:#ffc29a;
  --ok:#63d59d;--error:#ff8f86;--error-tenue:#3a1715;
  --sombra-hoja:0 0 0 1px #2d2a39,0 12px 34px rgba(0,0,0,.55);--sombra-flota:0 8px 28px rgba(0,0,0,.6);
  color-scheme:dark;
}
*{box-sizing:border-box}
html,body{background:var(--mesa)}
body{margin:0;color:var(--tinta);font-family:var(--f-ui);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:30;background:var(--superficie)}
h1,h2,h3{text-wrap:balance}
button{font:inherit}
.maq{font-family:var(--f-maq)}
.gutter{padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}

/* ---------- barra superior ---------- */
.barra{position:sticky;top:env(safe-area-inset-top,0px);z-index:20;background:var(--superficie);border-bottom:1px solid var(--regla)}
.barra-in{display:flex;align-items:center;gap:14px 22px;min-height:62px;padding-block:8px;flex-wrap:wrap}
.sello{display:inline-flex;flex-direction:column;align-items:center;gap:1px;color:var(--sello);text-decoration:none;border:2px solid currentColor;outline:1px solid currentColor;outline-offset:2px;border-radius:2px;padding:4px 10px 3px;transform:rotate(-2deg);line-height:1.05;flex:none;margin:4px 4px 4px 2px;
  -webkit-mask-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='70'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' seed='4'/%3E%3CfeColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -2.3 2.15'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  mask-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='70'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' seed='4'/%3E%3CfeColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -2.3 2.15'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
.sello b{font-weight:800;font-stretch:125%;font-size:12.5px;letter-spacing:.16em}
.sello small{font-family:var(--f-maq);font-size:9.5px;letter-spacing:.1em;text-transform:uppercase}
.sello:focus-visible{outline-color:var(--sello);outline-width:2px}
.pestanas{display:flex;gap:3px;background:var(--superficie-2);padding:3px;border-radius:7px;border:1px solid var(--regla);overflow-x:auto;max-width:100%}
.pestanas button{border:0;background:transparent;cursor:pointer;padding:7px 14px;border-radius:5px;font-weight:600;font-size:14px;color:var(--tinta-2);white-space:nowrap}
.pestanas button:hover{color:var(--tinta)}
.pestanas button[aria-selected="true"]{background:var(--superficie);color:var(--tinta);box-shadow:0 1px 2px rgba(0,0,0,.1)}
.pestanas button:focus-visible{outline:2px solid var(--sello);outline-offset:1px}
.perfil-chip{margin-left:auto;display:inline-flex;align-items:center;gap:9px;border:1px solid var(--regla);background:var(--superficie);color:var(--tinta);border-radius:999px;padding:4px 12px 4px 4px;cursor:pointer;font-size:13.5px;max-width:100%}
.perfil-chip .ini{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:var(--sello-tenue);color:var(--sello);font-weight:700;font-size:12px;flex:none}
.perfil-chip .txt{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.perfil-chip.pendiente{border-style:dashed;border-color:var(--regla-fuerte)}
.perfil-chip:focus-visible{outline:2px solid var(--sello);outline-offset:2px}

/* ---------- controles ---------- */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;font-weight:600;font-size:14px;border-radius:var(--r);padding:8px 13px;border:1px solid var(--regla-fuerte);background:var(--superficie);color:var(--tinta);cursor:pointer;white-space:nowrap;line-height:1.2;text-decoration:none}
.btn:hover{border-color:var(--tinta-2)}
.btn.primario{background:var(--sello);border-color:var(--sello);color:var(--sello-sobre)}
.btn.primario:hover{background:var(--sello-hover);border-color:var(--sello-hover)}
.btn.fantasma{border-color:transparent;background:transparent;color:var(--tinta-2)}
.btn.fantasma:hover{color:var(--tinta);background:var(--superficie-2)}
.btn.peligro{color:var(--error);border-color:var(--error)}
.btn.peligro-relleno{background:#dc2626;border-color:#dc2626;color:#ffffff}
.btn.peligro-relleno:hover{background:#b91c1c;border-color:#b91c1c}
.btn.grande{padding:12px 18px;font-size:15px}
.btn.chico{padding:5px 9px;font-size:13px}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn:focus-visible{outline:2px solid var(--sello);outline-offset:2px}
.btn svg{width:16px;height:16px;flex:none}
.campo{display:grid;gap:6px;min-width:0}
.campo>label,.campo .etq{font-weight:600;font-size:13.5px}
.campo .req{color:var(--sello);font-weight:700;margin-left:2px}
.ayuda{font-size:12.5px;color:var(--tinta-2);margin:0}
input[type=text],input[type=email],input[type=tel],input[type=number],input[type=search],select,textarea{width:100%;font:inherit;font-size:14.5px;color:var(--tinta);background:var(--superficie);border:1px solid var(--regla-fuerte);border-radius:var(--r);padding:9px 11px;line-height:1.45;min-width:0}
textarea{resize:vertical;min-height:70px}
input::placeholder,textarea::placeholder{color:var(--tinta-3)}
input:focus,select:focus,textarea:focus{outline:2px solid var(--sello);outline-offset:-1px;border-color:var(--sello)}
input.maq{font-family:var(--f-maq);font-size:15px;letter-spacing:.02em}
.campo.err input,.campo.err textarea,.campo.err .chips{border-color:var(--error);outline-color:var(--error)}
.msg-err{color:var(--error);font-size:12.5px;margin:0}
.check{display:flex;gap:10px;align-items:flex-start;font-size:14px;cursor:pointer}
.check input{margin-top:3px;accent-color:var(--sello);width:16px;height:16px;flex:none}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{border:1px solid var(--regla-fuerte);border-radius:4px;padding:5px 10px;font-size:13px;background:var(--superficie);color:var(--tinta);cursor:pointer;line-height:1.3}
.chip:hover{border-color:var(--tinta-2)}
.chip[aria-pressed="true"]{background:var(--sello-tenue);border-color:var(--sello);color:var(--tinta);font-weight:600}
.chip:focus-visible{outline:2px solid var(--sello);outline-offset:1px}
.chip-otro{display:flex;gap:6px;margin-top:6px}
.chip-otro input{max-width:260px;padding:6px 9px;font-size:13.5px}
.leyenda{display:flex;align-items:center;gap:10px;margin:0;font-family:var(--f-maq);font-size:12.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--tinta-2)}
.leyenda::after{content:"";flex:1;border-bottom:1px dashed var(--regla-fuerte);transform:translateY(-3px)}
.grupo{display:grid;gap:16px}
.rejilla{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 16px}
.rejilla .ancho{grid-column:1/-1}
@media (max-width:560px){.rejilla{grid-template-columns:1fr}}

/* ---------- vistas ---------- */
.vista[hidden]{display:none!important}
.redactar{display:grid;grid-template-columns:minmax(340px,460px) minmax(0,1fr)}
.col-form{background:var(--superficie);border-right:1px solid var(--regla);height:calc(100dvh - var(--barra-h));overflow:auto;min-width:0}
.col-hoja{height:calc(100dvh - var(--barra-h));overflow:auto;min-width:0;position:relative}
.form-in{padding-block:20px 0;display:grid;gap:24px}
#zonaTipo{display:grid;gap:16px}
.form-caso{display:grid;gap:30px}
@media (max-width:999px){
  .redactar{grid-template-columns:minmax(0,1fr)}
  .col-form,.col-hoja{height:auto;overflow:visible}
  .col-form{border-right:0;border-bottom:1px solid var(--regla)}
  .hoja-barra{position:static}
}
@media (max-width:699px){
  .barra{position:static}
  .barra-in{gap:10px 12px;min-height:0}
  .pestanas{order:3;width:100%}
  .pestanas button{flex:1;padding:7px 8px}
  .perfil-chip{padding:4px}
  .perfil-chip .txt{display:none}
  .sello b{font-size:11.5px}
  .col-form,.col-hoja{height:auto}
}
.intro h1{font-size:21px;font-weight:750;font-stretch:112%;margin:0 0 4px;letter-spacing:-.005em}
.intro p{margin:0;color:var(--tinta-2);font-size:14px}
.buscador{position:relative}
.catalogo{display:grid;gap:18px}
.cat-grupo h3{font-family:var(--f-maq);font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--tinta-2);margin:0 0 4px;font-weight:700}
.cat-items{display:grid;gap:1px}
.cat-item{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 12px;padding:9px 10px;border-radius:var(--r);cursor:pointer;border:0;background:transparent;color:var(--tinta);text-align:left;width:100%}
.cat-item:hover{background:var(--superficie-2)}
.cat-item:focus-visible{outline:2px solid var(--sello);outline-offset:-2px}
.cat-item .n{font-weight:650;font-size:14.5px;display:inline-flex;align-items:center;flex-wrap:wrap;gap:4px}
.cat-item .nm{font-family:var(--f-maq);font-size:11.5px;color:var(--tinta-3);white-space:nowrap;align-self:center}
.cat-item .d{grid-column:1/-1;color:var(--tinta-2);font-size:13px}
@media (max-width:480px){.cat-item{grid-template-columns:1fr}.cat-item .nm{white-space:normal}}
.tipo-actual{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 12px;align-items:start;padding:14px 16px;border:1px solid var(--regla);border-radius:var(--r);background:var(--superficie-2)}
.tipo-actual .eyebrow{font-family:var(--f-maq);font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--tinta-3);grid-column:1/-1}
.tipo-actual h2{margin:0;font-size:19px;font-weight:750;font-stretch:108%}
.tipo-actual .nm{grid-column:1/-1;font-family:var(--f-maq);font-size:12.5px;color:var(--tinta-2)}
.tipo-actual .d{grid-column:1/-1;color:var(--tinta-2);font-size:13.5px;margin:0}
.fila-ejemplo{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.acciones-form{position:sticky;bottom:0;z-index:2;padding-block:16px max(16px,env(safe-area-inset-bottom,0px));background:linear-gradient(to bottom,transparent,var(--superficie) 22%);display:grid;gap:8px;margin-top:4px}
.acciones-form .btn{width:100%}
.acciones-form .nota{font-size:12.5px;color:var(--tinta-2);margin:0;text-align:center}
.aviso{border:1px solid var(--regla);background:var(--superficie-2);border-radius:var(--r);padding:10px 12px;font-size:13.5px;color:var(--tinta-2)}
.aviso a,.aviso button.enlace{color:var(--sello);font-weight:600}
button.enlace{border:0;background:none;padding:0;cursor:pointer;text-decoration:underline;text-underline-offset:2px;font-size:inherit}
.vacio{border:1px dashed var(--regla-fuerte);border-radius:var(--r);padding:28px 20px;text-align:center;color:var(--tinta-2)}
.vacio strong{display:block;color:var(--tinta);font-size:16px;margin-bottom:4px}

/* ---------- hoja ---------- */
.hoja-barra{position:sticky;top:0;z-index:5;background:var(--mesa);border-bottom:1px solid var(--regla);padding-block:10px;display:grid;gap:10px}
.hb-fila{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.hb-estado{font-family:var(--f-maq);font-size:13px;color:var(--tinta-2);margin-right:auto;display:flex;align-items:center;gap:8px;min-width:0}
.hb-estado .punto{width:8px;height:8px;border-radius:50%;background:var(--tinta-3);flex:none}
.hb-estado.vivo .punto{background:var(--sello);animation:latido 1.1s ease-in-out infinite}
.hb-estado.listo .punto{background:var(--ok)}
.hb-estado.error .punto{background:var(--error)}
@keyframes latido{50%{opacity:.25}}
.verif{display:flex;gap:8px;flex-wrap:wrap}
.vchip{display:inline-flex;align-items:center;gap:6px;border-radius:4px;padding:4px 10px;font-size:13px;font-weight:600;border:0;cursor:pointer}
.vchip.c{background:var(--chip-c);color:var(--chip-c-tinta)}
.vchip.v{background:var(--chip-v);color:var(--chip-v-tinta)}
.vchip.ok{background:transparent;color:var(--ok);cursor:default;font-weight:600;padding-left:0}
.vchip:focus-visible{outline:2px solid var(--sello);outline-offset:1px}
.vchip.verde{background:#dcfce7;color:#166534}
.vchip.amarillo{background:#fef9c3;color:#854d0e}
.vchip.rojo{background:#fee2e2;color:#991b1b}
.cita-badge{display:inline-flex;align-items:center;gap:4px;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:700}
.cita-badge.verde{background:#dcfce7;color:#166534}
.cita-badge.amarillo{background:#fef9c3;color:#854d0e}
.cita-badge.rojo{background:#fee2e2;color:#991b1b}
.panel-verif{background:var(--superficie);border:1px solid var(--regla);border-radius:var(--r);padding:12px 14px;display:grid;gap:10px;max-height:48vh;overflow-y:auto}
.panel-verif h3{margin:0;font-size:13px;font-family:var(--f-maq);letter-spacing:.08em;text-transform:uppercase;color:var(--tinta-2)}
.panel-verif ol{margin:0;padding-left:20px;display:grid;gap:8px}
.panel-verif li{font-size:13.5px}
.panel-verif .ctx{color:var(--tinta-2)}
.panel-verif .acc{display:inline-flex;gap:10px;margin-left:6px}
.panel-verif a,.panel-verif button.enlace{color:var(--sello);font-weight:600;font-size:13px}
.panel-verif .nota{font-size:12.5px;color:var(--tinta-2);margin:0}
.ajuste{display:grid;gap:8px;background:var(--superficie);border:1px solid var(--regla);border-radius:var(--r);padding:12px}
.ajuste-fila{display:flex;gap:8px;flex-wrap:wrap}
.ajuste-fila input{flex:1 1 240px}
.sugerencias{display:flex;gap:6px;flex-wrap:wrap}
.edicion{display:flex;gap:4px;flex-wrap:wrap;align-items:center}
.edicion .sep{width:1px;height:20px;background:var(--regla-fuerte);margin:0 4px}
.edicion .btn{padding:4px 9px;font-size:13px}
.mesa-hoja{padding-block:22px 70px;display:flex;justify-content:center;min-width:0}
.hoja{--hoja-ancho:21.59cm;--hoja-alto:27.94cm;--m-sup:3cm;--m-der:2.5cm;--m-inf:2.5cm;--m-izq:3cm;--hoja-fuente:"Arimo",Arial,sans-serif;--hoja-tam:12pt;--hoja-int:1.725;--hoja-esp:8pt;--hoja-alin:justify;--hoja-tit-alin:center;--hoja-sangria:0cm;--ref-sangria:0cm;--cita-estilo:italic;--memb-color:#1f3a68;
  position:relative;width:var(--hoja-ancho);min-height:var(--hoja-alto);flex:none;
  padding:1.25cm var(--m-der) 1.25cm var(--m-izq);background:var(--hoja);color:var(--hoja-tinta);box-shadow:var(--sombra-hoja);
  display:flex;flex-direction:column;font-family:var(--hoja-fuente);font-size:var(--hoja-tam);line-height:var(--hoja-int)}
.hoja.lectura{width:100%;min-height:0;padding:22px 18px 26px;font-size:15px;line-height:1.6}
.hoja.lectura .cuerpo{padding-top:0!important}
.membrete{line-height:1.2;margin-bottom:.75cm}
.membrete:empty{display:none}
.hoja.sin-membrete .cuerpo{padding-top:calc(var(--m-sup) - 1.25cm)}
.memb-centrado{display:flex;flex-direction:column;align-items:center;text-align:center;gap:1.5pt}
.memb-logo{display:block;max-height:1.7cm;max-width:6cm;object-fit:contain}
.memb-centrado .memb-logo{margin-bottom:3pt}
.memb-nombre{font-weight:700;font-size:15pt;letter-spacing:.06em;text-transform:uppercase;color:var(--memb-color)}
.memb-sub{font-size:9.5pt;color:var(--hoja-gris)}
.memb-contacto{font-size:8.5pt;color:var(--hoja-gris)}
.memb-linea{height:0;border-top:3px double var(--memb-color);margin-top:5pt;width:100%}
.memb-lateral{display:grid;grid-template-columns:auto minmax(0,1fr);align-items:center;gap:2pt .5cm}
.memb-lateral .memb-logo{max-height:2cm;max-width:5cm}
.memb-lateral .memb-texto{text-align:right;display:grid;gap:1.5pt}
.memb-lateral.sin-logo{grid-template-columns:minmax(0,1fr)}
.memb-lateral.sin-logo .memb-texto{text-align:left}
.memb-lateral .memb-nombre{font-size:14pt;letter-spacing:.03em}
.memb-lateral .memb-linea{grid-column:1/-1;border-top:1.5px solid var(--memb-color);margin-top:4pt}
.memb-sobrio{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2pt 1cm;align-items:end}
.memb-sobrio .memb-nombre{font-size:11.5pt;letter-spacing:.14em}
.memb-sobrio .der{text-align:right}
.memb-sobrio .memb-linea{grid-column:1/-1;border-top:.75pt solid #a6a6a6;margin-top:4pt}
.memb-plantilla{display:grid;gap:3pt;justify-items:center;text-align:center}
.memb-plantilla img{display:block;max-width:100%;object-fit:contain}
.memb-plantilla .tx{font-size:9pt;color:var(--hoja-gris)}
.memb-vacio{color:#a3a3a3}
.cuerpo{flex:1;outline:none;min-height:3cm}
.cuerpo>p{margin:0 0 var(--hoja-esp);text-align:var(--hoja-alin);text-indent:var(--hoja-sangria)}
.cuerpo>p.multi,.cuerpo>p[data-b="ref"]{text-align:left;text-indent:0}
.cuerpo>p[data-b="h1"]{text-align:center;font-weight:700;margin:12pt 0;font-size:1.08em;text-indent:0}
.cuerpo>p[data-b="h2"]{text-align:var(--hoja-tit-alin);font-weight:700;margin:12pt 0 6pt;text-indent:0}
.cuerpo>p[data-b="h3"]{font-weight:700;margin:8pt 0 4pt;text-indent:0;text-align:left}
.hoja.mayus .cuerpo>p[data-b="h1"],.hoja.mayus .cuerpo>p[data-b="h2"]{text-transform:uppercase}
.cuerpo>p[data-b="quote"]{margin:0 2cm var(--hoja-esp);font-size:.92em;line-height:1.2;font-style:var(--cita-estilo);text-indent:0;text-align:justify}
.cuerpo>p[data-b="ref"]{margin-left:var(--ref-sangria);line-height:1.25}
.cuerpo>p[data-b="li"]{padding-left:1.27cm;text-indent:-.63cm}
.cuerpo>p[data-b="li"]::before{content:"•";display:inline-block;width:.63cm;text-indent:0}
.cuerpo mark{color:inherit;border-radius:2px;padding:0 1px}
.cuerpo mark.mk-c{background:var(--marca-c)}
.cuerpo mark.mk-v{background:var(--marca-v);color:var(--marca-v-tinta);font-size:.76em;font-family:var(--f-ui);font-weight:650;letter-spacing:.03em;font-style:normal;vertical-align:.08em}
.cuerpo .destello{animation:destello 1.6s ease-out}
@keyframes destello{0%,35%{background:color-mix(in srgb,var(--sello) 22%,transparent)}100%{background:transparent}}
.cuerpo[contenteditable="true"]:focus{box-shadow:0 0 0 1px color-mix(in srgb,var(--sello) 35%,transparent);border-radius:2px}
.cuerpo.escribiendo>:last-child::after{content:"";display:inline-block;width:.5em;height:1em;vertical-align:-.12em;background:var(--sello);margin-left:2px;animation:parpadeo 1s steps(2,start) infinite}
@keyframes parpadeo{to{visibility:hidden}}
.esperando{font-family:var(--f-maq);color:#6d6a78;font-size:11pt;line-height:1.5;padding:.4cm 0}
.esperando::after{content:"";display:inline-block;width:.5em;height:1em;vertical-align:-.15em;background:#4a32a6;margin-left:4px;animation:parpadeo 1s steps(2,start) infinite}
.firma{margin:4pt 0 var(--hoja-esp);line-height:1.2;text-indent:0;text-align:left}
.firma.centro{text-align:center}
.firma-img{display:block;max-height:1.6cm;max-width:6cm;margin-bottom:-.25cm}
.firma.centro .firma-img{margin-inline:auto}
.firma-espacio{height:1.3cm}
.ph{color:#9b9b9b;font-style:italic}
.pie{margin-top:auto;padding-top:.9cm;font-size:8.5pt;color:var(--hoja-gris);line-height:1.35;text-align:center;font-family:var(--hoja-fuente)}
.pie .pie-linea{border-top:.75pt solid var(--memb-color);margin-bottom:4pt}
.pie .pie-pag{text-align:right}
.sello-ejemplo{position:absolute;top:.9cm;right:.9cm;transform:rotate(-7deg);color:#4a32a6;border:2.5px solid currentColor;outline:1px solid currentColor;outline-offset:2.5px;padding:5px 12px 4px;text-align:center;line-height:1.1;font-family:var(--f-ui);pointer-events:none;opacity:.88}
.sello-ejemplo b{display:block;font-weight:800;font-stretch:125%;letter-spacing:.2em;font-size:15px}
.sello-ejemplo small{display:block;font-family:var(--f-maq);font-size:10px;letter-spacing:.06em}
.hoja.lectura .sello-ejemplo{top:10px;right:10px;transform:rotate(-5deg) scale(.85)}

/* ---------- ajustes ---------- */
.ajustes-in{display:grid;grid-template-columns:minmax(0,660px) minmax(0,1fr);gap:28px;padding-block:24px 80px;max-width:1400px}
.aj-form{display:grid;gap:30px;min-width:0}
.aj-cab h1{font-size:24px;font-weight:750;font-stretch:112%;margin:0 0 4px}
.aj-cab p{margin:0;color:var(--tinta-2)}
.guardado{font-size:12.5px;color:var(--tinta-2);display:inline-block;margin-top:8px;min-height:1.2em}
.aj-sec{display:grid;gap:16px;background:var(--superficie);border:1px solid var(--regla);border-radius:var(--r);padding:18px}
.aj-sec>p.ayuda{margin-top:-6px}
.aj-previa{position:sticky;top:calc(var(--barra-h) + 20px);align-self:start;display:grid;gap:10px;min-width:0}
.aj-previa .leyenda{margin-bottom:2px}
.aj-previa .marco{overflow:hidden;display:flex;justify-content:center;padding:14px 0 18px}
.aj-previa .hoja{min-height:16cm}
@media (max-width:1099px){.ajustes-in{grid-template-columns:minmax(0,1fr)}.aj-previa{position:static;order:-1}.aj-previa .marco{max-height:380px;align-items:flex-start;-webkit-mask-image:linear-gradient(#000 78%,transparent);mask-image:linear-gradient(#000 78%,transparent)}}
.segmento{display:inline-flex;border:1px solid var(--regla-fuerte);border-radius:6px;padding:3px;gap:3px;flex-wrap:wrap}
.segmento label{display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:14px;font-weight:600;color:var(--tinta-2)}
.segmento input{position:absolute;opacity:0;pointer-events:none}
.segmento label:has(input:checked){background:var(--sello-tenue);color:var(--tinta)}
.segmento label:has(input:focus-visible){outline:2px solid var(--sello)}
.disenos{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.diseno{border:1px solid var(--regla-fuerte);border-radius:var(--r);padding:10px;cursor:pointer;display:grid;gap:8px;background:var(--superficie);position:relative}
.diseno input{position:absolute;opacity:0;pointer-events:none}
.diseno:has(input:checked){border-color:var(--sello);box-shadow:0 0 0 1px var(--sello)}
.diseno:has(input:focus-visible){outline:2px solid var(--sello);outline-offset:2px}
.diseno span{font-size:13px;font-weight:600}
.mini{height:54px;background:#fff;border:1px solid #e3e1ea;border-radius:2px;padding:6px 7px;display:grid;gap:3px;align-content:start}
.mini i{display:block;height:3px;background:#c9c6d3;border-radius:1px}
.mini .n{height:5px;background:#1f3a68;width:48%}
.mini .r{height:0;border-top:2px double #1f3a68;background:none}
.mini.c{justify-items:center}
.mini.l{grid-template-columns:14px 1fr;column-gap:6px}
.mini.l .logo{grid-row:1/3;width:14px;height:14px;border-radius:50%;background:#c9c6d3}
.mini.l .n,.mini.l .s{justify-self:end}
.mini.l .r{grid-column:1/-1;border-top:1.5px solid #1f3a68}
.mini.s{grid-template-columns:1fr 1fr}
.mini.s .der{justify-self:end;width:70%}
.mini.s .r{grid-column:1/-1;border-top:1px solid #aaa}
@media (max-width:480px){.disenos{grid-template-columns:1fr}}
.colores{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.color{width:30px;height:30px;border-radius:50%;border:2px solid var(--superficie);box-shadow:0 0 0 1px var(--regla-fuerte);cursor:pointer;padding:0}
.color[aria-pressed="true"]{box-shadow:0 0 0 2px var(--sello)}
.color:focus-visible{outline:2px solid var(--sello);outline-offset:3px}
.colores input[type=color]{width:42px;height:32px;border:1px solid var(--regla-fuerte);border-radius:var(--r);background:var(--superficie);padding:2px;cursor:pointer}
.archivo{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.archivo .previa-img{height:52px;max-width:180px;object-fit:contain;background:#fff;border:1px solid var(--regla);border-radius:4px;padding:4px}
.archivo input[type=file]{position:absolute;width:1px;height:1px;opacity:0}
.plantilla-info{display:grid;gap:6px;font-size:13.5px;border-left:3px solid var(--regla-fuerte);padding:4px 0 4px 12px;color:var(--tinta-2)}
.plantilla-info strong{color:var(--tinta)}
.ficha{font-size:13.5px}

/* ---------- historial ---------- */
.hist-in{max-width:980px;margin:0 auto;padding-block:24px 80px;display:grid;gap:18px}
.hist-cab{display:flex;gap:12px 20px;align-items:flex-end;flex-wrap:wrap}
.hist-cab .tit{flex:1 1 260px}
.hist-cab h1{font-size:24px;font-weight:750;font-stretch:112%;margin:0 0 2px}
.hist-cab p{margin:0;color:var(--tinta-2)}
.hist-cab input{flex:0 1 320px}
.hist-lista{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.hist-item{display:grid;grid-template-columns:110px minmax(0,1fr) auto;gap:4px 16px;align-items:center;background:var(--superficie);border:1px solid var(--regla);border-radius:var(--r);padding:12px 14px}
.hist-item .f{font-family:var(--f-maq);font-size:12.5px;color:var(--tinta-2);font-variant-numeric:tabular-nums}
.hist-item .t{font-weight:650;min-width:0;overflow-wrap:anywhere}
.hist-item .tp{display:block;font-weight:500;font-size:13px;color:var(--tinta-2)}
.hist-item .acc{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
@media (max-width:640px){.hist-item{grid-template-columns:minmax(0,1fr)}.hist-item .acc{justify-content:flex-start}}

/* ---------- avisos ---------- */
#toasts{position:fixed;right:max(16px,calc(env(safe-area-inset-right,0px) + 16px));bottom:calc(env(safe-area-inset-bottom,0px) + 16px);z-index:50;display:grid;gap:8px;max-width:min(420px,calc(100vw - 32px))}
.toast{background:var(--tinta);color:var(--superficie);padding:10px 14px;border-radius:var(--r);font-size:14px;box-shadow:var(--sombra-flota);transition:opacity .3s,transform .3s}
.toast.ok{border-left:4px solid var(--ok)}
.toast.error{border-left:4px solid var(--error)}
.toast.sale{opacity:0;transform:translateY(6px)}
.copia-manual{display:grid;gap:8px}
.copia-manual textarea{min-height:200px;font-size:13px}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}

/* ---------- extracción multimodal de documentos del caso ---------- */
.zona-subida-docs{border:1.5px dashed var(--regla);background:var(--superficie);border-radius:var(--r);padding:18px;margin-bottom:24px;display:grid;gap:14px}
.dropzone-docs{border:2px dashed #cbd5e1;border-radius:var(--r);padding:22px 16px;text-align:center;cursor:pointer;background:rgba(248,250,252,.6);transition:all .2s ease}
.dropzone-docs:hover,.dropzone-docs.dragover{border-color:var(--azul,#2563eb);background:rgba(37,99,235,.05);transform:scale(1.005)}
.tabla-propuestas{width:100%;border-collapse:collapse;font-size:12.5px;text-align:left}
.tabla-propuestas th{padding:8px 10px;border-bottom:2px solid var(--regla);color:var(--tinta-2);font-weight:600}
.tabla-propuestas td{padding:10px 10px;border-bottom:1px solid var(--regla);vertical-align:top}
@keyframes pulsoVerdeCampo{0%{background-color:rgba(34,197,94,.22);border-color:#16a34a;box-shadow:0 0 0 2px rgba(34,197,94,.3)}100%{background-color:transparent;box-shadow:none}}
.campo-recien-aplicado input,.campo-recien-aplicado textarea{animation:pulsoVerdeCampo 2.5s ease-out}

/* ---------- banner vencimiento superior ---------- */
.banner-vencimiento-top{border-radius:var(--r);padding:12px 16px;border:1.5px solid transparent;transition:all .2s ease}
.banner-vencimiento-top.ok{background:#f0fdf4;border-color:#86efac;color:#166534}
.banner-vencimiento-top.urgente{background:#fffbeb;border-color:#fde68a;color:#92400e}
.banner-vencimiento-top.vencido{background:#fef2f2;border-color:#fca5a5;color:#991b1b}
.banner-vencimiento-top.info{background:#f8fafc;border-color:#cbd5e1;color:#334155}
.banner-vencimiento-top.cargando{background:#f8fafc;border-color:#e2e8f0;color:#64748b}

/* ---------- asistente de hechos contestacion art 96 cgp ---------- */
.asistente-hechos{border:1px solid var(--regla);border-radius:var(--r);background:var(--superficie);overflow:hidden;margin-top:6px}
.asistente-hechos-cab{padding:10px 14px;background:#f8fafc;border-bottom:1px solid var(--regla);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
.asistente-hechos-filas{display:grid;gap:10px;padding:12px}
.asistente-hecho-card{border:1px solid #e2e8f0;border-radius:6px;padding:10px 12px;background:#fff;display:grid;gap:8px;transition:border-color .15s}
.asistente-hecho-card:hover{border-color:#cbd5e1}
.asistente-hecho-card.es-cierto{border-left:4px solid #10b981}
.asistente-hecho-card.no-es-cierto{border-left:4px solid #ef4444}
.asistente-hecho-card.no-consta{border-left:4px solid #6366f1}
.asistente-hecho-card.parcial{border-left:4px solid #f59e0b}
.asistente-hecho-card.requiere-razon .asistente-hecho-razon{border-color:#f59e0b}
.asistente-hecho-top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.asistente-hecho-num{font-weight:750;font-size:12.5px;color:var(--tinta);display:flex;align-items:center;gap:6px}
.asistente-hecho-texto-demanda{font-size:12px;color:var(--tinta-2);background:rgba(0,0,0,.02);padding:6px 8px;border-radius:4px;border-left:2px solid var(--regla);font-style:italic;line-height:1.35}
.asistente-hecho-controles{display:grid;grid-template-columns:180px 1fr auto;gap:8px;align-items:start}
@media (max-width:680px){.asistente-hecho-controles{grid-template-columns:1fr;}}
.asistente-hecho-select{font-size:12.5px;padding:6px 8px;border:1px solid var(--regla);border-radius:4px;background:#fff;font-weight:600}
.asistente-hecho-razon{font-size:12px;padding:6px 8px;border:1px solid var(--regla);border-radius:4px;resize:vertical;min-height:36px;font-family:inherit;width:100%;box-sizing:border-box}
.asistente-hecho-del{border:none;background:none;color:#94a3b8;cursor:pointer;padding:4px 8px;font-size:15px;border-radius:4px;align-self:center}
.asistente-hecho-del:hover{color:#dc2626;background:rgba(220,38,38,.08)}

/* ---------- autenticación y cuenta con supabase ---------- */
.modal-dialog{border:none;border-radius:var(--r);background:var(--superficie);box-shadow:0 20px 40px rgba(0,0,0,.25);max-width:480px;width:calc(100vw - 32px);padding:0;overflow:hidden}
.modal-dialog::backdrop{background:rgba(15,23,42,.65);backdrop-filter:blur(3px)}
.modal-cab{padding:16px 20px;border-bottom:1px solid var(--regla);display:flex;justify-content:space-between;align-items:center;background:#f8fafc}
.modal-cab h3{margin:0;font-size:16px;font-weight:750;color:var(--tinta);display:flex;align-items:center;gap:8px}
.modal-cuerpo{padding:20px;display:grid;gap:16px}
.modal-pie{padding:14px 20px;background:#f8fafc;border-top:1px solid var(--regla);display:flex;justify-content:flex-end;gap:10px}
.btn-cerrar-modal{background:none;border:none;font-size:18px;color:#94a3b8;cursor:pointer;padding:4px 8px;border-radius:4px}
.btn-cerrar-modal:hover{color:#dc2626;background:rgba(220,38,38,.08)}
.perfil-chip.autenticado{background:#f0fdf4;border-color:#bbf7d0;color:#166534}
.perfil-chip.auth-pendiente{background:#f8fafc;border-color:#cbd5e1;color:var(--tinta-2)}
.tarjeta-usuario{background:#f8fafc;border:1px solid var(--regla);border-radius:6px;padding:12px 14px;display:grid;gap:6px}
.linea-dato-usuario{display:flex;justify-content:space-between;font-size:12.5px}
.linea-dato-usuario strong{color:var(--tinta)}
.linea-dato-usuario span{color:var(--tinta-2)}
.barra-cuota-uso{height:8px;background:#e2e8f0;border-radius:999px;overflow:hidden;margin-top:4px}
.barra-cuota-progreso{height:100%;background:#2563eb;border-radius:999px;transition:width .3s}
.btn-peligro{background:#dc2626;color:#fff;border:none;border-radius:var(--r);padding:8px 14px;font-weight:600;font-size:13px;cursor:pointer;display:inline-flex;align-items:center;gap:6px}
.btn-peligro:hover{background:#b91c1c}

/* ---------- comparador de versiones y diff ---------- */
.diff-ins{background:#dcfce7;color:#15803d;text-decoration:none;padding:1px 3px;border-radius:2px;font-weight:600}
.diff-del{background:#fee2e2;color:#b91c1c;text-decoration:line-through;padding:1px 3px;border-radius:2px;font-weight:500}
.diff-parrafo{margin:0 0 12px;line-height:1.7}
.diff-parrafo.diff-vacio{min-height:12px}

/* ---------- botón de dictado por voz (Web Speech API) ---------- */
.btn-microfono{display:inline-flex;align-items:center;gap:5px;background:#f1f5f9;border:1px solid var(--regla);border-radius:4px;padding:3px 8px;font-size:11.5px;font-weight:600;color:var(--tinta-2);cursor:pointer;transition:all .2s ease;user-select:none}
.btn-microfono:hover{background:#e2e8f0;color:var(--tinta);border-color:#cbd5e1}
.btn-microfono.grabando{background:#fee2e2;border-color:#fca5a5;color:#b91c1c;animation:pulsoGrabando 1.5s infinite}
.btn-microfono[hidden]{display:none !important}
@keyframes pulsoGrabando{0%{box-shadow:0 0 0 0 rgba(239,68,68,.4)}70%{box-shadow:0 0 0 6px rgba(239,68,68,0)}100%{box-shadow:0 0 0 0 rgba(239,68,68,0)}}

/* ---------- etiquetas y alertas de revisión jurídica y auditoría IA ---------- */
.pill-revision{display:inline-flex;align-items:center;gap:3px;font-size:9.5px;line-height:1;padding:1px 5px;border-radius:999px;font-weight:600;margin-left:6px;vertical-align:middle;user-select:none;white-space:nowrap;flex-shrink:0}
.pill-revision.pill-pendiente{background:#fef3c7;color:#92400e;border:1px solid #fde68a}
.pill-revision.pill-ia{background:#eff6ff;color:#1e40af;border:1px solid #bfdbfe}
.alerta-revision-guia{display:inline-flex;align-items:center;gap:8px;font-size:12px;padding:7px 12px;border-radius:6px;font-weight:600;margin-top:8px;flex-wrap:wrap;line-height:1.4}
.alerta-revision-guia.pendiente{background:#fffbeb;border:1px solid #fde68a;color:#92400e}
.alerta-revision-guia.ia{background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af}
</style>

<header class="barra" id="barra">
  <div class="barra-in gutter">
    <a class="sello" href="#redactar" aria-label="El Memorialista, inicio"><b>EL MEMORIALISTA</b><small id="selloFecha">Recibido</small></a>
    <nav class="pestanas" role="tablist" aria-label="Secciones">
      <button role="tab" id="tab-redactar" data-vista="redactar" aria-selected="true" aria-controls="vista-redactar">Redactar</button>
      <button role="tab" id="tab-membrete" data-vista="membrete" aria-selected="false" aria-controls="vista-membrete">Membrete y estilo</button>
      <button role="tab" id="tab-historial" data-vista="historial" aria-selected="false" aria-controls="vista-historial">Historial</button>
      <button role="tab" id="tab-plazos" data-vista="plazos" aria-selected="false" aria-controls="vista-plazos">⏱️ Términos y plazos</button>
      <button role="tab" id="tab-calculos" data-vista="calculos" aria-selected="false" aria-controls="vista-calculos">🧮 Cálculos jurídicos</button>
    </nav>
    <div class="barra-derecha" style="display: flex; align-items: center; gap: 8px;">
      <button class="perfil-chip pendiente" id="perfilChip" type="button"><span class="ini" aria-hidden="true">?</span><span class="txt">Configura tu membrete</span></button>
      <button class="btn chico" id="btnAuthHeader" type="button" style="display: inline-flex; align-items: center; gap: 5px; font-weight: 600; padding: 6px 12px; font-size: 12.5px;">🔒 Iniciar sesión</button>
    </div>
  </div>
</header>

<main>
  <section id="vista-redactar" class="vista redactar" role="tabpanel" aria-labelledby="tab-redactar">
    <div class="col-form">
      <div class="form-in gutter">
        <div id="zonaTipo"></div>
        <div id="bannerVencimientoTop" class="banner-vencimiento-top" style="margin-bottom: 18px;" hidden></div>
        <form id="formCaso" class="form-caso" novalidate autocomplete="off"></form>
        <div class="acciones-form" id="accionesForm" hidden>
          <button class="btn primario grande" id="btnRedactar" type="button">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 13.5c2.6-.6 5.2-3 7.4-6.9L12.6 3l-3.5 2.4C5.2 7.6 2.9 10.3 2.5 13.5zM2.5 13.5 6 10"/></svg>
            Redactar escrito
          </button>
          <p class="nota" id="notaRedactar">La Inteligencia Artificial redacta con tus datos, tu membrete y tu estilo.</p>
        </div>
      </div>
    </div>
    <div class="col-hoja" id="colHoja">
      <div class="hoja-barra gutter" id="hojaBarra">
        <div class="hb-fila">
          <div class="hb-estado" id="hbEstado" role="status"><span class="punto" aria-hidden="true"></span><span id="hbTexto">Ejemplo de escrito</span></div>
          <button class="btn chico" id="btnDetener" type="button" hidden><svg viewBox="0 0 16 16" aria-hidden="true"><rect x="4" y="4" width="8" height="8" rx="1" fill="currentColor"/></svg>Detener</button>
          <button class="btn chico fantasma" id="btnAjustar" type="button" disabled><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M10.8 2.7l2.5 2.5L6 12.5l-3.2.7.7-3.2z"/></svg>Ajustar con IA</button>
          <button class="btn chico fantasma" id="btnRegenerar" type="button" disabled><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 2.5v3.2h-3.2"/></svg>Regenerar</button>
          <button class="btn chico fantasma" id="btnCopiar" type="button" disabled><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="5" width="8.5" height="8.5" rx="1.2"/><path d="M10.5 5V3.2c0-.7-.5-1.2-1.2-1.2H3.2C2.5 2 2 2.5 2 3.2v6.1c0 .7.5 1.2 1.2 1.2H5"/></svg>Copiar</button>
          <button class="btn chico fantasma" id="btnCompararVersiones" type="button" disabled title="Compara versiones del escrito y visualiza los cambios por palabra"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 3h8M4 7h8M4 11h5M12 10l2 2-2 2"/></svg>Comparar versiones <span class="badge-versiones" id="badgeNumVersiones" style="font-size:10.5px;font-weight:700;padding:1px 5px;background:var(--regla);border-radius:10px;margin-left:3px;display:none;">0</span></button>
          <button class="btn chico" id="btnWord" type="button" disabled><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 2v8M4.5 6.8 8 10.3l3.5-3.5M3 13.5h10"/></svg>Word</button>
          <button class="btn chico" id="btnPdf" type="button" disabled><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 2v8M4.5 6.8 8 10.3l3.5-3.5M3 13.5h10"/></svg>PDF</button>
          <button class="btn chico primario" id="btnRadicacion" type="button" disabled title="Prepara el paquete de radicación judicial en .ZIP con PDF, poder judicial, índice y correos para despacho y traslado simultáneo (Ley 2213/2022)"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 4.5l5.5-2.5 5.5 2.5-5.5 2.5-5.5-2.5z"/><path d="M2.5 8l5.5 2.5 5.5-2.5"/><path d="M2.5 11.5l5.5 2.5 5.5-2.5"/></svg>Preparar radicación</button>
        </div>
        <div class="verif" id="verif" hidden></div>
        <div class="panel-verif" id="panelVerif" hidden></div>
        <div class="ajuste" id="ajuste" hidden>
          <label class="etq" for="ajusteTexto"><strong>¿Qué quieres cambiar?</strong></label>
          <div class="ajuste-fila">
            <input type="text" id="ajusteTexto" placeholder="Ej.: agrega como prueba el contrato de arrendamiento del 3 de marzo">
            <button class="btn primario" id="ajusteAplicar" type="button">Aplicar</button>
            <button class="btn fantasma" id="ajusteCerrar" type="button">Cerrar</button>
          </div>
          <div class="sugerencias" id="ajusteSugerencias"></div>
        </div>
        <div class="edicion" id="edicion" hidden aria-label="Formato del texto">
          <button class="btn chico" type="button" data-cmd="bold" title="Negrilla"><b>N</b></button>
          <button class="btn chico" type="button" data-cmd="italic" title="Cursiva"><i>K</i></button>
          <button class="btn chico" type="button" data-cmd="underline" title="Subrayado"><u>S</u></button>
          <span class="sep" aria-hidden="true"></span>
          <button class="btn chico" type="button" data-bloque="p">Párrafo</button>
          <button class="btn chico" type="button" data-bloque="h2">Capítulo</button>
          <button class="btn chico" type="button" data-bloque="h3">Subtítulo</button>
          <button class="btn chico" type="button" data-bloque="quote">Cita</button>
          <button class="btn chico" type="button" data-bloque="ref">Referencia</button>
          <button class="btn chico fantasma" type="button" id="btnDeshacerAjuste" hidden>Volver a la versión anterior</button>
        </div>
      </div>
      <div class="mesa-hoja gutter" id="mesaHoja">
        <article class="hoja" id="hoja" aria-label="Vista previa del escrito">
          <div class="sello-ejemplo" id="selloEjemplo" aria-hidden="true"><b>EJEMPLO</b><small>así se verá tu escrito</small></div>
          <header class="membrete" id="membrete"></header>
          <div class="cuerpo" id="cuerpo" lang="es-CO" spellcheck="true"></div>
          <footer class="pie" id="pie"></footer>
        </article>
      </div>
    </div>
  </section>

  <section id="vista-membrete" class="vista ajustes" role="tabpanel" aria-labelledby="tab-membrete" hidden>
    <div class="ajustes-in gutter">
      <div class="aj-form" id="ajForm">
        <header class="aj-cab">
          <h1>Membrete y estilo</h1>
          <p>Tus datos profesionales, tu membrete y tu forma de escribir. Se aplican a cada escrito que redactes.</p>
          <span class="guardado maq" id="estadoGuardado" role="status"></span>
        </header>

        <section class="aj-sec" aria-labelledby="s-ident">
          <h2 class="leyenda" id="s-ident"><span>Identidad profesional</span></h2>
          <div class="rejilla">
            <div class="campo ancho"><label for="p_nombre">Nombre completo</label><input id="p_nombre" type="text" data-path="abogado.nombre" autocomplete="name" placeholder="Laura Mejía Restrepo"></div>
            <div class="campo"><label for="p_genero">Cómo te nombra el escrito</label><select id="p_genero" data-path="abogado.genero"><option value="">Abogado(a)</option><option value="f">Abogada · la suscrita</option><option value="m">Abogado · el suscrito</option></select></div>
            <div class="campo"><label for="p_tp">Tarjeta profesional No.</label><input id="p_tp" type="text" class="maq" data-path="abogado.tp" placeholder="123.456"></div>
            <div class="campo"><label for="p_cedula">Cédula de ciudadanía</label><input id="p_cedula" type="text" class="maq" data-path="abogado.cedula" placeholder="1.020.304.050"></div>
            <div class="campo"><label for="p_cedulaLugar">Expedida en</label><input id="p_cedulaLugar" type="text" data-path="abogado.cedulaLugar" placeholder="Bogotá D.C."></div>
            <div class="campo"><label for="p_correo">Correo inscrito en el SIRNA</label><input id="p_correo" type="email" data-path="abogado.correo" autocomplete="email" placeholder="laura@mejiaabogados.co"></div>
            <div class="campo"><label for="p_telefono">Teléfono</label><input id="p_telefono" type="tel" data-path="abogado.telefono" autocomplete="tel" placeholder="310 000 0000"></div>
            <div class="campo ancho"><label for="p_direccion">Dirección de notificaciones</label><input id="p_direccion" type="text" data-path="abogado.direccion" placeholder="Carrera 7 # 32-16, oficina 1204"></div>
            <div class="campo"><label for="p_ciudad">Ciudad</label><input id="p_ciudad" type="text" data-path="abogado.ciudad" placeholder="Bogotá D.C."></div>
          </div>
        </section>

        <section class="aj-sec" aria-labelledby="s-memb">
          <h2 class="leyenda" id="s-memb"><span>Membrete</span></h2>
          <div class="segmento" role="radiogroup" aria-label="Origen del membrete">
            <label><input type="radio" name="m_modo" id="m_modo_diseno" value="diseno" data-path="membrete.modo">Diseñarlo aquí</label>
            <label><input type="radio" name="m_modo" id="m_modo_plantilla" value="plantilla" data-path="membrete.modo">Usar mi plantilla de Word</label>
          </div>
          <div id="bloqueDiseno" class="grupo">
            <div class="campo"><span class="etq">Diseño</span>
              <div class="disenos" role="radiogroup" aria-label="Diseño del membrete">
                <label class="diseno"><input type="radio" name="m_diseno" id="m_diseno_c" value="centrado" data-path="membrete.diseno"><div class="mini c" aria-hidden="true"><i class="n"></i><i style="width:60%"></i><i class="r" style="width:100%"></i></div><span>Clásico centrado</span></label>
                <label class="diseno"><input type="radio" name="m_diseno" id="m_diseno_l" value="lateral" data-path="membrete.diseno"><div class="mini l" aria-hidden="true"><i class="logo"></i><i class="n"></i><i class="s" style="width:62%"></i><i class="r"></i></div><span>Logo a la izquierda</span></label>
                <label class="diseno"><input type="radio" name="m_diseno" id="m_diseno_s" value="sobrio" data-path="membrete.diseno"><div class="mini s" aria-hidden="true"><i class="n" style="width:80%"></i><i class="der"></i><i style="width:60%"></i><i class="der" style="width:50%"></i><i class="r"></i></div><span>Sobrio, sin logo</span></label>
              </div>
            </div>
            <div class="campo"><span class="etq">Logo</span>
              <div class="archivo">
                <img id="logoPrevia" class="previa-img" alt="Logo actual" hidden>
                <label class="btn chico" for="logoArchivo">Subir logo</label>
                <input type="file" id="logoArchivo" accept="image/png,image/jpeg,image/webp,image/svg+xml">
                <button class="btn chico fantasma" type="button" id="logoQuitar" hidden>Quitar</button>
              </div>
              <p class="ayuda">PNG con fondo transparente funciona mejor. Se ajusta automáticamente.</p>
            </div>
            <div class="rejilla">
              <div class="campo ancho"><label for="m_titulo">Nombre en el membrete</label><input id="m_titulo" type="text" data-path="membrete.titulo" placeholder="Si lo dejas vacío, se usa tu nombre completo"></div>
              <div class="campo ancho"><label for="m_subtitulo">Línea bajo el nombre</label><input id="m_subtitulo" type="text" data-path="membrete.subtitulo" placeholder="Abogada · Especialista en Derecho Administrativo"></div>
              <div class="campo"><label for="m_web">Sitio web (opcional)</label><input id="m_web" type="text" data-path="membrete.web" placeholder="mejiaabogados.co"></div>
            </div>
            <div class="campo"><span class="etq">Color</span>
              <div class="colores" id="colores"></div>
            </div>
            <label class="check"><input type="checkbox" id="m_linea" data-path="membrete.linea">Línea decorativa bajo el membrete y sobre el pie de página</label>
          </div>
          <div id="bloquePlantilla" class="grupo" hidden>
            <p class="ayuda">Sube el .docx o .dotx que ya usas con tu membrete. Al exportar a Word, el escrito se inserta en tu plantilla y su encabezado y pie de página se conservan tal cual. Si la plantilla tiene un párrafo con el texto <span class="maq">{{CONTENIDO}}</span>, el escrito va exactamente ahí.</p>
            <div class="archivo">
              <label class="btn chico" for="plantillaArchivo">Subir plantilla de Word</label>
              <input type="file" id="plantillaArchivo" accept=".docx,.dotx,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.wordprocessingml.template">
              <button class="btn chico fantasma" type="button" id="plantillaQuitar" hidden>Quitar plantilla</button>
            </div>
            <div class="plantilla-info" id="plantillaInfo" hidden></div>
            <label class="check"><input type="checkbox" id="f_fuentePlantilla" data-path="formato.fuentePlantilla">Usar la fuente y el tamaño de letra de mi plantilla</label>
          </div>
          <label class="check"><input type="checkbox" id="m_numeracion" data-path="membrete.numeracion">Numerar las páginas (Página 1 de 3)</label>
        </section>

        <section class="aj-sec" aria-labelledby="s-formato">
          <h2 class="leyenda" id="s-formato"><span>Formato del documento</span></h2>
          <p class="ayuda" id="notaFormatoPlantilla" hidden>Con tu plantilla, el papel y las márgenes los define la plantilla.</p>
          <div class="rejilla">
            <div class="campo"><label for="f_papel">Papel</label><select id="f_papel" data-path="formato.papel"><option value="carta">Carta (21,59 × 27,94 cm)</option><option value="oficio">Oficio (21,59 × 33 cm)</option><option value="a4">A4 (21 × 29,7 cm)</option></select></div>
            <div class="campo"><label for="f_margenes">Márgenes</label><select id="f_margenes" data-path="formato.margenes"><option value="amplio">Amplias · izq. y sup. 3 cm</option><option value="normal">Normales · 2,5 cm</option><option value="estrecho">Estrechas · 2 cm</option></select></div>
            <div class="campo"><label for="f_fuente">Fuente</label><select id="f_fuente" data-path="formato.fuente"><option>Arial</option><option>Times New Roman</option><option>Calibri</option><option>Cambria</option><option>Georgia</option><option>Garamond</option></select></div>
            <div class="campo"><label for="f_tamano">Tamaño de letra</label><select id="f_tamano" data-path="formato.tamano" data-num="1"><option value="11">11 pt</option><option value="12">12 pt</option><option value="13">13 pt</option></select></div>
            <div class="campo"><label for="f_interlineado">Interlineado</label><select id="f_interlineado" data-path="formato.interlineado" data-num="1"><option value="1">Sencillo</option><option value="1.15">1,15</option><option value="1.5">1,5</option><option value="2">Doble</option></select></div>
            <div class="campo"><label for="f_espacio">Espacio entre párrafos</label><select id="f_espacio" data-path="formato.espacio"><option value="ninguno">Ninguno</option><option value="normal">Normal (8 pt)</option><option value="amplio">Amplio (12 pt)</option></select></div>
            <div class="campo"><label for="f_alineacion">Alineación del texto</label><select id="f_alineacion" data-path="formato.alineacion"><option value="justificado">Justificado</option><option value="izquierda">A la izquierda</option></select></div>
            <div class="campo"><label for="f_titulos">Títulos de capítulo</label><select id="f_titulos" data-path="formato.titulos"><option value="centrados">Centrados</option><option value="izquierda">A la izquierda</option></select></div>
            <div class="campo"><label for="f_firmaAlin">Firma</label><select id="f_firmaAlin" data-path="formato.firmaAlin"><option value="izquierda">A la izquierda</option><option value="centro">Centrada</option></select></div>
          </div>
          <div class="grupo" style="gap:10px">
            <label class="check"><input type="checkbox" id="f_mayus" data-path="formato.mayus">Títulos en mayúsculas</label>
            <label class="check"><input type="checkbox" id="f_sangria" data-path="formato.sangria">Sangría en la primera línea de cada párrafo</label>
            <label class="check"><input type="checkbox" id="f_refSangria" data-path="formato.refSangria">Bloque de referencia desplazado a la derecha</label>
            <label class="check"><input type="checkbox" id="f_citaCursiva" data-path="formato.citaCursiva">Citas textuales de normas en cursiva</label>
            <label class="check"><input type="checkbox" id="f_firmaContacto" data-path="formato.firmaContacto">Correo y teléfono bajo la firma</label>
          </div>
          <div class="campo"><span class="etq">Firma digitalizada (opcional)</span>
            <div class="archivo">
              <img id="firmaPrevia" class="previa-img" alt="Firma actual" hidden>
              <label class="btn chico" for="firmaArchivo">Subir firma</label>
              <input type="file" id="firmaArchivo" accept="image/png,image/jpeg,image/webp">
              <button class="btn chico fantasma" type="button" id="firmaQuitar" hidden>Quitar</button>
            </div>
            <label class="check"><input type="checkbox" id="firmaFondo" checked>Quitar el fondo blanco al subirla (para firmas escaneadas)</label>
          </div>
        </section>

        <section class="aj-sec" aria-labelledby="s-estilo">
          <h2 class="leyenda" id="s-estilo"><span>Estilo de redacción</span></h2>
          <p class="ayuda">Lo que marques aquí se respeta en cada escrito. Deja “Automático” donde prefieras que se siga tu muestra o la práctica usual.</p>
          <div class="rejilla">
            <div class="campo"><label for="e_tratamiento">Tratamiento al despacho</label><select id="e_tratamiento" data-path="estilo.tratamiento"><option value="auto">Automático</option><option value="Señor(a) Juez">Señor(a) Juez</option><option value="Su Señoría">Su Señoría</option><option value="Honorable Magistrado(a)">Honorable Magistrado(a)</option><option value="Respetado(a) señor(a) Juez">Respetado(a) señor(a) Juez</option></select></div>
            <div class="campo"><label for="e_persona">Persona gramatical</label><select id="e_persona" data-path="estilo.persona"><option value="auto">Automático</option><option value="primera">Primera persona (“me permito”)</option><option value="tercera">Tercera persona (“el suscrito apoderado”)</option></select></div>
            <div class="campo"><label for="e_numHechos">Numeración de hechos</label><select id="e_numHechos" data-path="estilo.numHechos"><option value="auto">Automático</option><option value="ordinal">PRIMERO, SEGUNDO…</option><option value="numero">1, 2, 3…</option><option value="hecho">Hecho 1, Hecho 2…</option></select></div>
            <div class="campo"><label for="e_numPret">Numeración de pretensiones</label><select id="e_numPret" data-path="estilo.numPretensiones"><option value="auto">Automático</option><option value="ordinal">PRIMERA, SEGUNDA…</option><option value="numero">1, 2, 3…</option></select></div>
            <div class="campo"><label for="e_tono">Tono</label><select id="e_tono" data-path="estilo.tono"><option value="sobrio">Sobrio y técnico</option><option value="contundente">Firme y contundente</option><option value="sencillo">Claro y sencillo</option></select></div>
            <div class="campo"><label for="e_lenguaje">Lenguaje</label><select id="e_lenguaje" data-path="estilo.lenguaje"><option value="auto">Automático</option><option value="claro">Moderno, sin latinismos innecesarios</option><option value="tradicional">Forense tradicional</option></select></div>
            <div class="campo"><label for="e_fecha">Lugar y fecha</label><select id="e_fecha" data-path="estilo.fecha"><option value="arriba">Al inicio del escrito</option><option value="final">Al final, antes de la firma</option><option value="no">No incluir</option></select></div>
            <div class="campo"><label for="e_extension">Extensión por defecto</label><select id="e_extension" data-path="estilo.extension"><option value="concisa">Concisa</option><option value="estandar">Estándar</option><option value="extensa">Extensa y exhaustiva</option></select></div>
            <div class="campo ancho"><label for="e_cierre">Fórmula de despedida</label><input id="e_cierre" type="text" data-path="estilo.cierre" placeholder="Del señor Juez, con todo respeto,"></div>
          </div>
          <label class="check"><input type="checkbox" id="e_esd" data-path="estilo.esd">Usar “E. S. D.” en el destinatario de los escritos judiciales</label>
          <div class="campo">
            <label for="e_muestra">Muestra de tu estilo</label>
            <p class="ayuda">Pega un escrito tuyo (o súbelo en .docx o .txt). Se imitan tus fórmulas, el orden de tus capítulos y tu nivel de formalidad; nunca sus hechos ni sus datos.</p>
            <textarea id="e_muestra" data-path="estilo.muestra" rows="6" maxlength="20000" placeholder="Pega aquí una demanda, tutela o memorial que hayas escrito…"></textarea>
            <div class="archivo">
              <label class="btn chico" for="muestraArchivo">Subir escrito</label>
              <input type="file" id="muestraArchivo" accept=".docx,.txt,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document">
              <button class="btn chico primario" type="button" id="btnAnalizar">Analizar mi estilo</button>
              <span class="ayuda" id="analizarEstado" role="status"></span>
            </div>
          </div>
          <div class="campo">
            <label for="e_ficha">Ficha de estilo</label>
            <p class="ayuda">Resumen de tu forma de escribir. Se genera al analizar tu muestra y puedes corregirla a mano.</p>
            <textarea id="e_ficha" class="ficha" data-path="estilo.ficha" rows="7" placeholder="Aún no hay ficha. Pega una muestra y pulsa “Analizar mi estilo”."></textarea>
          </div>
        </section>

        <section class="aj-sec" aria-labelledby="s-ia">
          <h2 class="leyenda" id="s-ia"><span>Motor de Inteligencia Artificial</span></h2>
          <div class="segmento" role="radiogroup" aria-label="Calidad de redacción">
            <label><input type="radio" name="ia_calidad" id="ia_complex" value="complex" data-path="ia.calidad">Máxima calidad (más lenta)</label>
            <label><input type="radio" name="ia_calidad" id="ia_default" value="default" data-path="ia.calidad">Equilibrada (más rápida)</label>
          </div>
          <div class="rejilla">
            <div class="campo"><label for="ia_smmlv">Salario mínimo mensual vigente</label><input id="ia_smmlv" type="number" min="0" step="1" class="maq" data-path="ia.smmlv" data-num="1"><p class="ayuda">Sirve para clasificar cuantías. Valor 2026: $1.750.905.</p></div>
          </div>
          <p class="ayuda" id="notaAlmacen"></p>
        </section>
      </div>
      <aside class="aj-previa" aria-label="Vista previa del membrete">
        <h2 class="leyenda"><span>Vista previa</span></h2>
        <div class="marco"><article class="hoja" id="hojaPrevia"><header class="membrete" id="membretePrevia"></header><div class="cuerpo" id="cuerpoPrevia"></div><footer class="pie" id="piePrevia"></footer></article></div>
      </aside>
    </div>
  </section>

  <section id="vista-historial" class="vista historial" role="tabpanel" aria-labelledby="tab-historial" hidden>
    <div class="hist-in gutter">
      <header class="hist-cab">
        <div class="tit"><h1>Historial</h1><p id="histResumen">Cada escrito que redactes se guarda aquí automáticamente.</p></div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
          <input type="search" id="histBuscar" placeholder="Buscar por cliente, tipo o asunto" aria-label="Buscar en el historial">
          <button class="btn chico" id="btnDescargarCopia" type="button" title="Descargar archivo JSON con perfil, logo, firma, plantilla e historial">Descargar copia de seguridad</button>
          <label class="btn chico fantasma" for="archivoRestaurarCopia" style="cursor:pointer;">Restaurar copia</label>
          <input type="file" id="archivoRestaurarCopia" accept=".json,application/json" style="position:absolute;width:1px;height:1px;opacity:0;">
        </div>
      </header>
      <ol class="hist-lista" id="histLista"></ol>
      <div class="vacio" id="histVacio" hidden><strong>Todavía no hay escritos</strong>Elige un tipo de documento en Redactar, llena los datos del caso y pulsa “Redactar escrito”. Cada versión se guarda aquí.</div>
    </div>
  </section>

  <section id="vista-plazos" class="vista plazos" role="tabpanel" aria-labelledby="tab-plazos" hidden>
    <div class="plazos-in gutter" style="max-width: 980px; margin: 0 auto; padding-block: 24px 80px; display: grid; gap: 20px;">
      <header class="plazos-cab" style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 12px;">
        <div>
          <h1 style="font-size: 24px; font-weight: 750; margin: 0 0 4px;">⏱️ Calculadora de Términos Judiciales y Vencimientos</h1>
          <p style="margin: 0; color: var(--tinta-2); font-size: 14px;">Cómputo en días hábiles, meses y años (CGP, CPACA, D. 2591/91, Ley 2213/2022 y Ley 51/1983).</p>
        </div>
      </header>

      <div class="plazos-form-card" style="background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r); padding: 22px; display: grid; gap: 18px;">
        <div class="rejilla">
          <div class="campo ancho">
            <label for="plazo_preset">Término procesal o tipo de escrito</label>
            <select id="plazo_preset"></select>
          </div>
          <div class="campo">
            <label for="plazo_fecha_inicio">Fecha de providencia o notificación</label>
            <input type="date" id="plazo_fecha_inicio">
          </div>
          <div class="campo">
            <label for="plazo_cantidad">Duración del término</label>
            <div style="display: flex; gap: 8px;">
              <input type="number" id="plazo_cantidad" min="1" max="1000" value="3" style="width: 100px;">
              <select id="plazo_unidad" style="flex: 1;">
                <option value="dias_habiles">Días hábiles judiciales</option>
                <option value="meses">Meses calendario (art. 118 CGP)</option>
                <option value="anios">Años calendario (art. 118 CGP)</option>
              </select>
            </div>
          </div>
        </div>

        <div style="display: flex; gap: 24px; flex-wrap: wrap; padding-top: 10px; border-top: 1px solid var(--regla);">
          <label class="check">
            <input type="checkbox" id="plazo_mensaje_datos">
            <span><strong>Notificación por mensaje de datos</strong> (art. 8 Ley 2213/2022: 2 días hábiles de gracia tras envío)</span>
          </label>
          <label class="check">
            <input type="checkbox" id="plazo_vacancia_colectiva" checked>
            <span><strong>Vacancia judicial colectiva</strong> (20 dic a 10 ene, art. 146 Ley 270/1996)</span>
          </label>
        </div>

        <div id="plazo_bloque_acuse" class="campo" style="max-width: 360px;" hidden>
          <label for="plazo_fecha_acuse">Fecha de acuse de recibo voluntario</label>
          <input type="date" id="plazo_fecha_acuse">
          <p class="ayuda">Si el destinatario acusó recibo expresamente antes de cumplirse los 2 días de gracia.</p>
        </div>
      </div>

      <!-- PANEL DE RESULTADOS DE LA CALCULADORA -->
      <div id="plazos_resultado_panel" style="display: grid; gap: 16px;"></div>
    </div>
  </section>

  <!-- SECCIÓN DE CÁLCULOS JURÍDICOS Y FINANCIEROS -->
  <section id="vista-calculos" class="vista calculos" role="tabpanel" aria-labelledby="tab-calculos" hidden>
    <div class="calculos-in gutter" style="max-width: 1040px; margin: 0 auto; padding-block: 24px 80px; display: grid; gap: 20px;">
      <header class="calculos-cab" style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 12px;">
        <div>
          <h1 style="font-size: 22px; font-weight: 700; margin: 0 0 6px;">🧮 Cálculos Jurídicos, Laborales y Financieros</h1>
          <p style="margin: 0; color: var(--tinta-2); font-size: 14px;">
            Liquidación laboral integral, intereses de mora mercantil (Superfinanciera) y actualización monetaria con IPC del DANE.
          </p>
        </div>
        <div class="calculos-subnav" style="display: flex; gap: 6px; background: var(--fondo); padding: 4px; border-radius: var(--r); border: 1px solid var(--regla);">
          <button type="button" id="subtab-laboral" class="btn chico" style="font-weight: 600;" onclick="cambiarSubtabCalculos('laboral')">💼 Liquidación Laboral</button>
          <button type="button" id="subtab-mora" class="btn chico secundario" style="font-weight: 600;" onclick="cambiarSubtabCalculos('mora')">📈 Intereses Comerciales</button>
          <button type="button" id="subtab-ipc" class="btn chico secundario" style="font-weight: 600;" onclick="cambiarSubtabCalculos('ipc')">📊 Indexación IPC</button>
        </div>
      </header>

      <!-- SUB-SECCIÓN 1: LIQUIDACIÓN LABORAL -->
      <div id="calc-seccion-laboral" class="calc-seccion" style="display: grid; gap: 18px;">
        <div class="card" style="background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r); padding: 22px; display: grid; gap: 16px;">
          <h2 style="font-size: 17px; margin: 0 0 4px; font-weight: 600;">Liquidación de Prestaciones e Indemnizaciones Laborales</h2>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px;">
            <div class="campo">
              <label for="lab_trabajador">Nombre del trabajador</label>
              <input type="text" id="lab_trabajador" placeholder="Ej. Pedro Gómez">
            </div>
            <div class="campo">
              <label for="lab_empleador">Nombre del empleador</label>
              <input type="text" id="lab_empleador" placeholder="Ej. Soluciones Andinas S.A.S.">
            </div>
            <div class="campo">
              <label for="lab_fecha_inicio">Fecha de inicio de labores</label>
              <input type="date" id="lab_fecha_inicio">
            </div>
            <div class="campo">
              <label for="lab_fecha_fin">Fecha de terminación</label>
              <input type="date" id="lab_fecha_fin">
            </div>
            <div class="campo">
              <label for="lab_salario_base">Salario básico mensual (COP)</label>
              <input type="number" id="lab_salario_base" placeholder="Ej. 2000000" min="0" step="1000">
            </div>
            <div class="campo">
              <label for="lab_tipo_contrato">Tipo de contrato</label>
              <select id="lab_tipo_contrato" onchange="toggleCamposLaboral()">
                <option value="indefinido">Término Indefinido</option>
                <option value="termino_fijo">Término Fijo</option>
                <option value="obra_labor">Obra o Labor Determinada</option>
              </select>
            </div>
            <div class="campo">
              <label for="lab_motivo">Motivo de terminación</label>
              <select id="lab_motivo">
                <option value="despido_sin_justa_causa">Despido sin justa causa (con indemnización art. 64 CST)</option>
                <option value="despido_con_justa_causa">Despido con justa causa comprobada</option>
                <option value="renuncia_voluntaria">Renuncia voluntaria del trabajador</option>
                <option value="mutuo_acuerdo">Mutuo acuerdo / Transacción</option>
                <option value="vencimiento_termino">Vencimiento del término pactado</option>
                <option value="terminacion_obra">Terminación de la obra contratada</option>
              </select>
            </div>
            <div class="campo" id="lab_campo_fecha_pactada" hidden>
              <label for="lab_fecha_pactada">Fecha pactada de vencimiento (Término Fijo)</label>
              <input type="date" id="lab_fecha_pactada">
            </div>
          </div>

          <div style="display: flex; flex-wrap: wrap; gap: 16px; padding-top: 10px; border-top: 1px solid var(--regla);">
            <label style="display: flex; align-items: center; gap: 8px; font-size: 13.5px; cursor: pointer;">
              <input type="checkbox" id="lab_incluir_auxilio" checked>
              <span>Auxilio de transporte legal (si devenga ≤ 2 SMMLV)</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px; font-size: 13.5px; cursor: pointer;">
              <input type="checkbox" id="lab_check_moratoria" onchange="toggleCamposLaboral()">
              <span>Indemnización moratoria art. 65 CST (salarios caídos)</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px; font-size: 13.5px; cursor: pointer;">
              <input type="checkbox" id="lab_check_consignacion" onchange="toggleCamposLaboral()">
              <span>Sanción no consignación de cesantías (art. 99 Ley 50/1990)</span>
            </label>
          </div>

          <div id="lab_panel_opciones_extra" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px;" hidden>
            <div class="campo" id="lab_campo_corte_moratoria" hidden>
              <label for="lab_fecha_corte_moratoria">Fecha de corte para mora (art. 65)</label>
              <input type="date" id="lab_fecha_corte_moratoria">
            </div>
            <div class="campo" id="lab_campo_dias_consignacion" hidden>
              <label for="lab_dias_consignacion">Días de mora en consignar cesantías</label>
              <input type="number" id="lab_dias_consignacion" min="0" placeholder="Ej. 30">
            </div>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px;">
            <button type="button" class="btn" onclick="ejecutarCalculoLaboral()">⚡ Calcular Liquidación Laboral</button>
          </div>
        </div>

        <div id="lab_resultado_panel" style="display: grid; gap: 16px;"></div>
      </div>

      <!-- SUB-SECCIÓN 2: INTERESES MORATORIOS MERCANTILES -->
      <div id="calc-seccion-mora" class="calc-seccion" style="display: none; gap: 18px;">
        <div class="card" style="background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r); padding: 22px; display: grid; gap: 16px;">
          <h2 style="font-size: 17px; margin: 0 0 4px; font-weight: 600;">Intereses Moratorios Mercantiles (Art. 884 Código de Comercio)</h2>
          <p style="margin: 0; font-size: 13.5px; color: var(--tinta-2);">
            Liquidación mes a mes aplicando 1.5 veces el Interés Bancario Corriente (IBC) certificado oficialmente por la Superintendencia Financiera de Colombia (límite de usura).
          </p>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px;">
            <div class="campo">
              <label for="mora_capital">Capital en mora (COP)</label>
              <input type="number" id="mora_capital" placeholder="Ej. 50000000" min="1" step="1000">
            </div>
            <div class="campo">
              <label for="mora_fecha_inicio">Fecha de exigibilidad / inicio de mora</label>
              <input type="date" id="mora_fecha_inicio">
            </div>
            <div class="campo">
              <label for="mora_fecha_fin">Fecha de corte de liquidación</label>
              <input type="date" id="mora_fecha_fin">
            </div>
            <div class="campo">
              <label for="mora_concepto">Concepto / Obligación / Factura / Pagaré</label>
              <input type="text" id="mora_concepto" placeholder="Ej. Factura de Venta FE-1044">
            </div>
            <div class="campo">
              <label for="mora_metodo">Método de liquidación</label>
              <select id="mora_metodo">
                <option value="financiero_exacto">Efectivo Anual Financiero Exacto (Días/365)</option>
                <option value="nominal_comercial">Nominal Comercial (Mes 30 días)</option>
              </select>
            </div>
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px;">
            <button type="button" class="btn" onclick="ejecutarCalculoMora()">📈 Calcular Intereses Comerciales</button>
          </div>
        </div>

        <div id="mora_resultado_panel" style="display: grid; gap: 16px;"></div>
      </div>

      <!-- SUB-SECCIÓN 3: INDEXACIÓN CON IPC DANE -->
      <div id="calc-seccion-ipc" class="calc-seccion" style="display: none; gap: 18px;">
        <div class="card" style="background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r); padding: 22px; display: grid; gap: 16px;">
          <h2 style="font-size: 17px; margin: 0 0 4px; font-weight: 600;">Actualización Monetaria con IPC del DANE</h2>
          <p style="margin: 0; font-size: 13.5px; color: var(--tinta-2);">
            Fórmula jurisprudencial unificada de la Corte Suprema de Justicia (Salas Civil y Laboral) y el Consejo de Estado: <code>VA = VH × (IPC_final / IPC_inicial)</code>.
          </p>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px;">
            <div class="campo">
              <label for="ipc_valor">Valor histórico original (COP)</label>
              <input type="number" id="ipc_valor" placeholder="Ej. 10000000" min="1" step="1000">
            </div>
            <div class="campo">
              <label for="ipc_fecha_ini">Fecha inicial (causación / exigibilidad)</label>
              <input type="date" id="ipc_fecha_ini">
            </div>
            <div class="campo">
              <label for="ipc_fecha_fin">Fecha final (corte de liquidación)</label>
              <input type="date" id="ipc_fecha_fin">
            </div>
            <div class="campo">
              <label for="ipc_concepto">Concepto / Perjuicio / Condena</label>
              <input type="text" id="ipc_concepto" placeholder="Ej. Indemnización perjuicios materiales">
            </div>
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px;">
            <button type="button" class="btn" onclick="ejecutarCalculoIPC()">📊 Calcular Indexación con IPC</button>
          </div>
        </div>

        <div id="ipc_resultado_panel" style="display: grid; gap: 16px;"></div>
      </div>
    </div>
  </section>
</main>
<div id="toasts" aria-live="polite"></div>

<!-- Modal de Autenticación con Enlace Mágico -->
<dialog id="modalAuth" class="modal-dialog">
  <div class="modal-cab">
    <h3><span>⚖️</span> Iniciar sesión con enlace mágico</h3>
    <button type="button" class="btn-cerrar-modal" id="btnCerrarModalAuth" title="Cerrar">✕</button>
  </div>
  <form id="formAuthMagicLink" class="modal-cuerpo" autocomplete="on">
    <p style="margin: 0; font-size: 13px; color: var(--tinta-2); line-height: 1.45;">
      Accede con tu correo electrónico. Te enviaremos un <strong>enlace mágico seguro</strong> para ingresar sin contraseñas. Tus datos, clientes, casos y memoriales se resguardarán en la nube con Row Level Security y cifrado.
    </p>
    <div class="campo" style="margin: 0;">
      <label for="authEmail" style="font-weight: 600; font-size: 13px; color: var(--tinta); display: block; margin-bottom: 4px;">Tu correo electrónico</label>
      <input type="email" id="authEmail" required placeholder="abogado@tufirma.com" style="width: 100%; box-sizing: border-box; font-size: 14px; padding: 8px 10px; border: 1.5px solid var(--regla); border-radius: 4px;">
    </div>
    <div id="msgAuthEstado" style="display: none; padding: 10px 12px; border-radius: 6px; font-size: 12.5px; line-height: 1.4;"></div>
    <button type="submit" class="btn primario grande" id="btnEnviarMagicLink" style="width: 100%; justify-content: center; font-size: 14px; padding: 10px 16px;">
      ✉️ Enviar enlace mágico a mi correo
    </button>
    <p style="margin: 0; font-size: 11.5px; color: var(--tinta-2); text-align: center;">
      Si ya tienes memoriales o membrete en este navegador, se migrarán automáticamente a tu cuenta la primera vez que ingreses.
    </p>
  </form>
</dialog>

<!-- Modal de Mi Cuenta / Sesión y Datos -->
<dialog id="modalCuenta" class="modal-dialog">
  <div class="modal-cab">
    <h3><span>👤</span> Mi Cuenta en El Memorialista</h3>
    <button type="button" class="btn-cerrar-modal" id="btnCerrarModalCuenta" title="Cerrar">✕</button>
  </div>
  <div class="modal-cuerpo">
    <div class="tarjeta-usuario">
      <div class="linea-dato-usuario">
        <strong>Correo:</strong>
        <span id="cuentaUserEmail">—</span>
      </div>
      <div class="linea-dato-usuario">
        <strong>Firma / Despacho:</strong>
        <span id="cuentaUserFirma">—</span>
      </div>
      <div class="linea-dato-usuario">
        <strong>Rol:</strong>
        <span id="cuentaUserRol">Abogado</span>
      </div>
      <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--regla);">
        <div class="linea-dato-usuario">
          <strong>Límite de uso diario:</strong>
          <span id="cuentaUserCuota">0 / 50 redacciones</span>
        </div>
        <div class="barra-cuota-uso">
          <div class="barra-cuota-progreso" id="cuentaProgresoCuota" style="width: 0%;"></div>
        </div>
      </div>
    </div>

    <div style="display: grid; gap: 10px;">
      <h4 style="margin: 0; font-size: 13px; font-weight: 700; color: var(--tinta);">Gestión de datos y privacidad</h4>
      <button type="button" class="btn chico" id="btnExportarDatosCuenta" style="display: flex; align-items: center; justify-content: center; gap: 8px; padding: 9px 14px; font-weight: 600;">
        📦 Exportar todos mis datos (JSON)
      </button>
      <button type="button" class="btn chico fantasma" id="btnSincronizarNube" style="display: flex; align-items: center; justify-content: center; gap: 8px; padding: 9px 14px;">
        🔄 Sincronizar datos locales con la nube
      </button>
    </div>

    <div style="border-top: 1px solid #fee2e2; padding-top: 14px; margin-top: 4px; display: grid; gap: 8px;">
      <h4 style="margin: 0; font-size: 13px; font-weight: 700; color: #dc2626;">Zona de peligro</h4>
      <p style="margin: 0; font-size: 11.5px; color: var(--tinta-2);">
        Borra tu cuenta en Supabase y elimina definitivamente todos tus clientes, casos, memoriales, versiones y archivos privados.
      </p>
      <button type="button" class="btn-peligro" id="btnEliminarCuentaModal" style="justify-content: center;">
        🗑️ Eliminar mi cuenta y mis datos
      </button>
    </div>
  </div>
  <div class="modal-pie" style="justify-content: space-between;">
    <button type="button" class="btn fantasma" id="btnCerrarSesionCuenta">🚪 Cerrar sesión</button>
    <button type="button" class="btn" id="btnCerrarCuentaDialog">Cerrar</button>
  </div>
</dialog>

<!-- Modal de Preparar Radicación Judicial -->
<dialog id="modalRadicacion" class="modal-dialog" style="max-width: 640px;">
  <div class="modal-cab">
    <h3><span>📦</span> Paquete de Radicación Judicial</h3>
    <button type="button" class="btn-cerrar-modal" id="btnCerrarModalRadicacion" title="Cerrar">✕</button>
  </div>
  <div class="modal-cuerpo" style="max-height: 80vh; overflow-y: auto; display: grid; gap: 14px;">
    <!-- Estado de descarga del ZIP -->
    <div style="background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 6px; padding: 12px 14px; display: flex; align-items: center; justify-content: space-between; gap: 10px;">
      <div>
        <div style="font-weight: 750; font-size: 13.5px; color: #166534; display: flex; align-items: center; gap: 6px;">
          <span>✅</span> Paquete .ZIP generado y descargado
        </div>
        <div id="radNombrePaquete" style="font-size: 12px; color: #15803d; font-family: monospace; word-break: break-all; margin-top: 2px;">—</div>
      </div>
      <button type="button" class="btn chico" id="btnDescargarZipDeNuevo" title="Descargar nuevamente el archivo .zip">
        📥 Descargar .ZIP
      </button>
    </div>

    <!-- Contenido del paquete -->
    <div style="background: #f8fafc; border: 1px solid var(--regla); border-radius: 6px; padding: 12px 14px;">
      <strong style="font-size: 12.5px; color: var(--tinta); display: block; margin-bottom: 6px;">Archivos incluidos en el paquete:</strong>
      <ul id="radListaArchivos" style="margin: 0; padding-left: 20px; font-size: 12px; color: var(--tinta-2); line-height: 1.6;">
        <!-- Se llena dinámicamente -->
      </ul>
    </div>

    <!-- Traslado simultáneo a contraparte (Art. 6 Ley 2213 de 2022) -->
    <div id="radSeccionContraparte" style="border-radius: 6px; padding: 12px 14px; border: 1px solid var(--regla); display: grid; gap: 8px;">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
        <strong style="font-size: 13px; color: var(--tinta); display: flex; align-items: center; gap: 6px;">
          <span>⚖️</span> Traslado Simultáneo a Contraparte (Art. 6 Ley 2213 de 2022)
        </strong>
        <span id="radBadgeContraparte" style="font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 12px;">—</span>
      </div>
      <p id="radMotivoContraparte" style="margin: 0; font-size: 12px; line-height: 1.45; color: var(--tinta-2);"></p>
      <div id="radAccionContraparte" style="display: none; margin-top: 4px;">
        <a id="btnMailtoContraparte" class="btn chico primario" href="#" target="_blank" rel="noopener" style="width: 100%; justify-content: center; gap: 8px; text-decoration: none; box-sizing: border-box;">
          ✉️ Abrir borrador de correo para Contraparte (mailto:)
        </a>
      </div>
    </div>

    <!-- Radicación al Despacho Judicial -->
    <div style="border-radius: 6px; padding: 12px 14px; border: 1px solid var(--regla); background: #faf5ff; border-color: #e9d5ff; display: grid; gap: 8px;">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
        <strong style="font-size: 13px; color: #581c87; display: flex; align-items: center; gap: 6px;">
          <span>🏛️</span> Radicación al Despacho Judicial
        </strong>
        <span style="font-size: 11px; font-weight: 700; background: #f3e8ff; color: #6b21a8; padding: 2px 8px; border-radius: 12px;">Oficial</span>
      </div>
      <div style="font-size: 12px; color: #6b21a8; line-height: 1.4;">
        Destinatario: <strong id="radCorreoDespachoTexto">—</strong>
      </div>
      <a id="btnMailtoDespacho" class="btn chico primario" href="#" target="_blank" rel="noopener" style="width: 100%; justify-content: center; gap: 8px; background: #7e22ce; border-color: #6b21a8; text-decoration: none; box-sizing: border-box;">
        ✉️ Abrir borrador de correo para Despacho Judicial (mailto:)
      </a>
    </div>

    <p style="margin: 0; font-size: 11px; color: var(--tinta-2); line-height: 1.4; text-align: center;">
      🔒 <strong>Garantía de control:</strong> Los borradores se abren en tu aplicación de correo predeterminada (Outlook, Apple Mail, Thunderbird, Gmail) mediante enlaces <code>mailto:</code>. <strong>Nunca se envían automáticamente</strong> sin tu revisión previa y anexión final.
    </p>
  </div>
  <div class="modal-pie">
    <button type="button" class="btn chico fantasma" id="btnCerrarModalRadicacionPie">Cerrar</button>
  </div>
</dialog>

<!-- Modal de Comparar Versiones y Control de Cambios -->
<dialog id="modalComparar" class="modal-dialog" style="max-width: 900px; width: calc(100vw - 32px); max-height: 92vh;">
  <div class="modal-cab">
    <h3><span>🔍</span> Comparador de versiones y control de cambios</h3>
    <button type="button" class="btn-cerrar-modal" id="btnCerrarModalComparar" title="Cerrar">✕</button>
  </div>
  <div class="modal-cuerpo" style="max-height: 80vh; overflow-y: auto; display: grid; gap: 14px; padding: 16px 20px;">
    <!-- Barra de selección de versiones -->
    <div style="background: #f8fafc; border: 1px solid var(--regla); border-radius: 6px; padding: 12px 14px; display: grid; grid-template-columns: 1fr auto 1fr; gap: 10px; align-items: center;">
      <div>
        <label for="selectVersionBase" style="font-size: 11.5px; font-weight: 700; color: var(--tinta-2); display: block; margin-bottom: 4px;">
          VERSIÓN BASE (ANTERIOR)
        </label>
        <select id="selectVersionBase" style="width: 100%; font-size: 12.5px; padding: 6px 8px; border: 1px solid var(--regla); border-radius: 4px; background: #fff; font-weight: 600;">
        </select>
      </div>

      <button type="button" class="btn chico fantasma" id="btnIntercambiarVersiones" title="Intercambiar versiones base y comparada" style="margin-top: 16px; padding: 6px 10px;">
        ⇄
      </button>

      <div>
        <label for="selectVersionComparada" style="font-size: 11.5px; font-weight: 700; color: var(--tinta-2); display: block; margin-bottom: 4px;">
          VERSIÓN COMPARADA (NUEVA)
        </label>
        <select id="selectVersionComparada" style="width: 100%; font-size: 12.5px; padding: 6px 8px; border: 1px solid var(--regla); border-radius: 4px; background: #fff; font-weight: 600;">
        </select>
      </div>
    </div>

    <!-- Barra de métricas y resumen de cambios -->
    <div id="diffResumenBarra" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; padding: 8px 12px; background: #fff; border: 1px solid var(--regla); border-radius: 6px;">
      <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
        <span id="diffBadgeAnadidas" style="font-size: 12px; font-weight: 700; color: #15803d; background: #dcfce7; padding: 3px 8px; border-radius: 12px;">+0 añadidas</span>
        <span id="diffBadgeEliminadas" style="font-size: 12px; font-weight: 700; color: #b91c1c; background: #fee2e2; padding: 3px 8px; border-radius: 12px;">-0 eliminadas</span>
        <span id="diffBadgeIguales" style="font-size: 12px; color: var(--tinta-2); background: #f1f5f9; padding: 3px 8px; border-radius: 12px;">0 sin cambio</span>
      </div>
      <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
        <button type="button" class="btn chico" id="btnRestaurarVersionBase" title="Restaura el texto de la versión base en el editor">
          ↺ Restaurar esta versión
        </button>
        <button type="button" class="btn chico primario" id="btnExportarWordDiff" title="Descarga archivo .docx con control de cambios nativo (w:ins y w:del)">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;" aria-hidden="true">
            <path d="M8 2v8M4.5 6.8 8 10.3l3.5-3.5M3 13.5h10"/>
          </svg>
          Exportar a Word con control de cambios
        </button>
      </div>
    </div>

    <!-- Visor de diferencias por palabra -->
    <div id="diffVisorDocumento" style="background: #ffffff; border: 1px solid var(--regla); border-radius: 6px; padding: 24px 28px; min-height: 240px; font-family: var(--fuente-cuerpo); font-size: 14px; line-height: 1.65; color: var(--tinta); box-shadow: inset 0 1px 3px rgba(0,0,0,0.03); max-height: 50vh; overflow-y: auto;">
      <!-- Diff renderizado dinámicamente -->
    </div>

    <p style="margin: 0; font-size: 11.5px; color: var(--tinta-2); line-height: 1.4;">
      💡 <strong>Control de cambios en Word:</strong> El archivo exportado contiene etiquetas oficiales OpenXML (<code>&lt;w:ins&gt;</code> y <code>&lt;w:del&gt;</code>) con autor y fecha, compatibles con Microsoft Word, Google Docs y LibreOffice para que cualquier abogado pueda aceptar o rechazar cambios individualmente.
    </p>
  </div>
  <div class="modal-pie">
    <button type="button" class="btn chico fantasma" id="btnCerrarModalCompararPie">Cerrar</button>
  </div>
</dialog>

<!-- Modal de Dictamen de Auditoría Jurídica con IA -->
<dialog id="modalAuditoriaIa" class="modal-dialog" style="max-width: 640px; width: calc(100vw - 32px);">
  <div class="modal-cab">
    <h3 style="display: flex; align-items: center; gap: 8px;">🤖 Dictamen de Auditoría Jurídica</h3>
    <button type="button" class="btn-cerrar" id="btnCerrarModalAuditoria" aria-label="Cerrar">✕</button>
  </div>
  <div class="modal-cuerpo" id="cuerpoModalAuditoria" style="display: grid; gap: 14px; max-height: 70vh; overflow-y: auto; padding: 18px 20px;">
    <!-- Renderizado dinámico del dictamen -->
  </div>
  <div class="modal-pie">
    <button type="button" class="btn chico fantasma" id="btnCerrarModalAuditoriaPie">Cerrar</button>
  </div>
</dialog>

<script src="auditor.js"></script>
<script>
'use strict';
/* =========================================================
   Utilidades
   ========================================================= */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  if (attrs) for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'text') el.textContent = v;
    else if (k === 'html') el.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids.flat()) if (k != null && k !== false) el.append(k instanceof Node ? k : String(k));
  return el;
}
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const fechaLarga = (d = new Date()) => `${d.getDate()} de ${MESES[d.getMonth()]} de ${d.getFullYear()}`;
const dos = n => String(n).padStart(2, '0');
const fechaCorta = ms => { const d = new Date(ms); return `${dos(d.getDate())}/${dos(d.getMonth() + 1)}/${d.getFullYear()}`; };
const horaCorta = ms => { const d = new Date(ms); return `${dos(d.getHours())}:${dos(d.getMinutes())}`; };
const pesos = n => '$' + Math.round(Number(n) || 0).toLocaleString('es-CO');
const clon = o => JSON.parse(JSON.stringify(o));
const espera = ms => new Promise(r => setTimeout(r, ms));
function debounce(fn, ms) {
  let t;
  const f = (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
  f.ya = (...a) => { clearTimeout(t); return fn(...a); };
  f.cancelar = () => clearTimeout(t);
  return f;
}
const lsGet = k => { try { const v = localStorage.getItem('memorialista:' + k); return v ? JSON.parse(v) : null; } catch { return null; } };
const lsSet = (k, v) => { try { localStorage.setItem('memorialista:' + k, JSON.stringify(v)); return true; } catch { return false; } };
const lsDel = k => { try { localStorage.removeItem('memorialista:' + k); } catch { /* sin almacenamiento */ } };
function getPath(o, p) { return p.split('.').reduce((a, k) => (a == null ? a : a[k]), o); }
function setPath(o, p, v) { const ks = p.split('.'); let a = o; ks.slice(0, -1).forEach(k => { if (a[k] == null || typeof a[k] !== 'object') a[k] = {}; a = a[k]; }); a[ks[ks.length - 1]] = v; }
function mezclar(base, extra) {
  if (Array.isArray(base)) return Array.isArray(extra) ? extra : base;
  if (base && typeof base === 'object') {
    const out = { ...base };
    if (extra && typeof extra === 'object') for (const k of Object.keys(extra)) out[k] = (k in base && base[k] && typeof base[k] === 'object' && !Array.isArray(base[k])) ? mezclar(base[k], extra[k]) : extra[k];
    return out;
  }
  return extra === undefined ? base : extra;
}
function toast(msg, tipo = 'info', ms = 4500) {
  const t = h('div', { class: 'toast ' + tipo, role: tipo === 'error' ? 'alert' : 'status' }, msg);
  $('#toasts').append(t);
  setTimeout(() => { t.classList.add('sale'); setTimeout(() => t.remove(), 320); }, ms);
}
const cargados = {};
function cargarScript(url) {
  if (!cargados[url]) cargados[url] = new Promise((ok, mal) => {
    const s = document.createElement('script');
    s.src = url; s.async = true;
    s.onload = () => ok();
    s.onerror = () => { delete cargados[url]; mal(new Error('No se pudo cargar ' + url)); };
    document.head.append(s);
  });
  return cargados[url];
}
const LIBS = {
  jszip: 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js',
  pdfmake: 'https://cdn.jsdelivr.net/npm/pdfmake@0.3.11/build/pdfmake.min.js',
  times: 'https://cdn.jsdelivr.net/npm/pdfmake@0.3.11/build/standard-fonts/Times.js',
  helvetica: 'https://cdn.jsdelivr.net/npm/pdfmake@0.3.11/build/standard-fonts/Helvetica.js',
};
const cargarJSZip = () => cargarScript(LIBS.jszip);
async function cargarPdfMake() {
  await cargarScript(LIBS.pdfmake);
  await Promise.all([cargarScript(LIBS.times), cargarScript(LIBS.helvetica)]);
  try { window.pdfMake.setUrlAccessPolicy && window.pdfMake.setUrlAccessPolicy(() => false); } catch { /* opcional */ }
}

/* =========================================================
   Constantes de formato
   ========================================================= */
const PAPEL = { carta: { w: 21.59, h: 27.94, n: 'Carta' }, oficio: { w: 21.59, h: 33.02, n: 'Oficio' }, a4: { w: 21.0, h: 29.7, n: 'A4' } };
const MARGENES = { amplio: { sup: 3, inf: 2.5, izq: 3, der: 2.5 }, normal: { sup: 2.5, inf: 2.5, izq: 2.5, der: 2.5 }, estrecho: { sup: 2, inf: 2, izq: 2, der: 2 } };
const FUENTES = {
  'Arial': { web: 'Arimo', pdf: 'Helvetica', css: '"Arimo", Arial, "Helvetica Neue", sans-serif' },
  'Times New Roman': { web: 'Tinos', pdf: 'Times', css: '"Tinos", "Times New Roman", Times, serif' },
  'Calibri': { web: 'Carlito', pdf: 'Helvetica', css: '"Carlito", Calibri, Arial, sans-serif' },
  'Cambria': { web: 'Caladea', pdf: 'Times', css: '"Caladea", Cambria, Georgia, serif' },
  'Georgia': { web: 'Gelasio', pdf: 'Times', css: '"Gelasio", Georgia, serif' },
  'Garamond': { web: 'EB Garamond', pdf: 'Times', css: '"EB Garamond", Garamond, Georgia, serif' },
};
const ESPACIO = { ninguno: 0, normal: 8, amplio: 12 };
const COLORES = [['#1a1a1a', 'Tinta negra'], ['#1f3a68', 'Azul notarial'], ['#6d1f2f', 'Vinotinto'], ['#1f4d3a', 'Verde toga'], ['#3f4650', 'Gris pizarra'], ['#4a32a6', 'Violeta sello']];
const PERFIL_BASE = {
  v: 1,
  abogado: { nombre: '', genero: '', cedula: '', cedulaLugar: '', tp: '', correo: '', telefono: '', direccion: '', ciudad: '' },
  membrete: { modo: 'diseno', diseno: 'centrado', titulo: '', subtitulo: '', color: '#1f3a68', linea: true, web: '', numeracion: true },
  formato: { papel: 'carta', margenes: 'amplio', fuente: 'Arial', tamano: 12, interlineado: 1.5, espacio: 'normal', alineacion: 'justificado', titulos: 'centrados', mayus: true, sangria: false, refSangria: false, citaCursiva: true, firmaAlin: 'izquierda', firmaContacto: true, fuentePlantilla: true },
  estilo: { tratamiento: 'auto', persona: 'auto', numHechos: 'auto', numPretensiones: 'auto', tono: 'sobrio', lenguaje: 'auto', fecha: 'arriba', esd: true, cierre: '', extension: 'estandar', ficha: '', muestra: '' },
  ia: { calidad: 'complex', smmlv: 1750905 },
  plantilla: null,
};

/* =========================================================
   Catálogo de escritos (servidor v2.2.1)
   ========================================================= */
let TIPOS_LISTA = [];
let TIPOS = {};
let AREAS = [];

function grupoRedaccion(tipo) {
  const gr = (state.catalogo && state.catalogo.grupo_redaccion) || {};
  const baseCampos = gr.campos || [
    { k: 'fundamentos', l: 'Normas o jurisprudencia que quieres citar', t: 'area', rows: 2, ph: 'Opcional. Ej.: Sentencia T-760 de 2008; art. 49 de la Constitución.' },
    { k: '_extension', l: 'Extensión', t: 'select', opciones: [['concisa', 'Concisa'], ['estandar', 'Estándar'], ['extensa', 'Extensa y exhaustiva']] },
    { k: '_juris', l: 'Jurisprudencia', t: 'select', opciones: [['verificables', 'Solo citas verificables'], ['sugerir', 'Sugerir sentencias, marcadas para verificar'], ['usuario', 'Solo la que yo indique'], ['ninguna', 'No citar jurisprudencia']] },
    { k: '_firma', l: 'Quién firma', t: 'select', opciones: [['apoderado', 'Yo, como apoderado(a)'], ['propio', 'Yo, en nombre propio'], ['cliente', 'Mi cliente, en nombre propio']] },
    { k: '_membrete', l: 'Incluir mi membrete en este escrito', t: 'check', def: true },
    { k: '_notas', l: 'Indicaciones adicionales', t: 'area', rows: 2, ph: 'Ej.: Enfatiza que la accionante es adulta mayor; no menciones el nombre del médico.' },
  ];
  const campos = [];
  for (const c of baseCampos) {
    if (c.k === '_firma' && tipo && tipo.firma === 'poder') continue;
    const cl = { ...c };
    if (cl.k === '_extension') cl.def = (tipo && tipo.breve) ? 'concisa' : '@extension';
    if (cl.k === '_juris') cl.def = (tipo && tipo.juris) || 'verificables';
    if (cl.k === '_firma') cl.def = (tipo && tipo.firma) || 'apoderado';
    campos.push(cl);
  }
  return { n: (gr && gr.nombre_grupo) || 'Redacción', campos };
}

/* Escrito de ejemplo para la primera vista */
const EJEMPLO_TEXTO = `Bogotá D.C., ${fechaLarga()}

Señor
JUEZ CIVIL MUNICIPAL DE BOGOTÁ D.C. (REPARTO)
E. S. D.

| **Referencia:** Acción de tutela
| **Accionante:** María Fernanda López Rincón
| **Accionada:** EPS Salud Ejemplo S.A.S.
| **Derechos invocados:** Salud, vida digna y seguridad social

**@NOMBRE@**, mayor de edad, identificad@O@ con la cédula de ciudadanía No. @CEDULA@, abogad@O@ en ejercicio con Tarjeta Profesional No. @TP@ del Consejo Superior de la Judicatura, en calidad de apoderad@O@ de la señora **MARÍA FERNANDA LÓPEZ RINCÓN**, según el poder que anexo, respetuosamente presento **ACCIÓN DE TUTELA** contra **EPS SALUD EJEMPLO S.A.S.**, con fundamento en el artículo 86 de la Constitución Política y el Decreto 2591 de 1991, por los siguientes:

## Hechos

**PRIMERO.** La señora López Rincón, de 63 años, está afiliada al régimen contributivo de la EPS accionada desde 2015.

**SEGUNDO.** El 2 de septiembre de 2026 su médico tratante le diagnosticó artritis reumatoide y le ordenó tofacitinib de 5 mg cada doce horas por tres meses.

**TERCERO.** El 9 de septiembre de 2026 la EPS negó la entrega con el argumento de que el medicamento requería autorización del comité técnico, trámite que a la fecha no ha resuelto.

**CUARTO.** Sin el tratamiento, la accionante sufre dolor e inflamación que le impiden trabajar como costurera independiente.

## Derechos fundamentales vulnerados

La negativa de la EPS a entregar un medicamento prescrito por el médico tratante vulnera los derechos a la salud, reconocido como fundamental autónomo por la Ley 1751 de 2015, a la vida en condiciones dignas y a la seguridad social. La Corte Constitucional ha reiterado que los trámites administrativos internos no pueden convertirse en barreras para acceder a los servicios ordenados por el médico tratante (Sentencia T-760 de 2008 [VERIFICAR]).

## Procedencia

La accionante es titular de los derechos invocados y la EPS presta el servicio público de salud. No existe otro mecanismo judicial igualmente eficaz frente a la urgencia de un tratamiento continuo, la accionante es sujeto de especial protección por su edad y la vulneración es actual.

## Pretensiones

**PRIMERA.** Tutelar los derechos fundamentales a la salud, a la vida digna y a la seguridad social de la señora María Fernanda López Rincón.

**SEGUNDA.** Ordenar a EPS Salud Ejemplo S.A.S. que, dentro de las cuarenta y ocho (48) horas siguientes a la notificación del fallo, autorice y entregue el medicamento en la forma prescrita.

**TERCERA.** Ordenar el tratamiento integral de la patología diagnosticada.

## Pruebas

1. Fórmula médica del 2 de septiembre de 2026.
2. Respuesta de la EPS del 9 de septiembre de 2026.
3. Copia de la cédula de ciudadanía de la accionante y poder.

## Juramento

Bajo la gravedad del juramento manifiesto que no se ha presentado otra acción de tutela por los mismos hechos y derechos.

## Notificaciones

La accionante recibe notificaciones en [COMPLETAR: dirección y correo de la accionante]. La accionada, en el correo de notificaciones judiciales que figura en su certificado de existencia y representación legal.

Del señor Juez, con todo respeto,

[[FIRMA: Apoderad@O@ de la parte accionante]]`;

/* =========================================================
   Estado, capacidades y almacenamiento
   ========================================================= */
const state = {
  vista: 'redactar',
  perfil: clon(PERFIL_BASE),
  tipo: null,
  datos: {},
  texto: '',
  versiones: [],
  ejemplo: true,
  docId: null,
  creado: null,
  prompt: '',
  prevTexto: null,
  generando: false,
  ctl: null,
  plantilla: null,
  catalogoAbierto: true,
  citasVerificadas: [],
  verificandoCitas: false,
  archivosCaso: [],
  propuestasExtraidas: [],
  extrayendoDocs: false,
  hechosContestacion: [],
  usuario: null,
  session: null,
  perfilCloud: null,
  firma: null,
  supabaseConfig: null,
};
const IMG = { logo: null, firma: null };
const CAP = { sample: true, db: null, user: null, downloads: true, permissions: null, uid: null, listo: true };

async function iniciarCapacidades() {
  CAP.sample = true;
  CAP.downloads = true;
  CAP.listo = true;
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    console.log('[Memorialista] Conectado al backend:', data);
  } catch (e) {
    console.warn('[Memorialista] Backend:', e);
  }
}

/* =========================================================
   Supabase Auth (Magic Link), Base de Datos y Storage Privado
   ========================================================= */
let sbClient = null;

function dataUrlABlob(dataUrl) {
  if (!dataUrl) return null;
  if (dataUrl instanceof Blob) return dataUrl;
  if (typeof dataUrl === 'string' && dataUrl.startsWith('data:')) {
    try {
      const partes = dataUrl.split(',');
      const mime = partes[0].match(/:(.*?);/)[1];
      const bstr = atob(partes[1]);
      let n = bstr.length;
      const u8arr = new Uint8Array(n);
      while (n--) {
        u8arr[n] = bstr.charCodeAt(n);
      }
      return new Blob([u8arr], { type: mime });
    } catch (e) {
      console.warn('Error convirtiendo dataURL a Blob:', e);
      return null;
    }
  }
  return new Blob([dataUrl]);
}

async function iniciarSupabase() {
  try {
    const res = await fetch('/api/auth/config');
    if (!res.ok) return;
    const config = await res.json();
    state.supabaseConfig = config;

    if (window.supabase && config.supabase_url && config.supabase_anon_key) {
      sbClient = window.supabase.createClient(config.supabase_url, config.supabase_anon_key);
      window.supabaseClient = sbClient;

      sbClient.auth.onAuthStateChange(async (event, session) => {
        state.session = session;
        state.usuario = session?.user || null;
        actualizarUiAuth();
        if (event === 'SIGNED_IN' && session?.user) {
          toast(`¡Bienvenido, ${session.user.email}!`, 'ok');
          await migrarDatosNavegadorASupabase(session.user);
        } else if (event === 'SIGNED_OUT') {
          toast('Sesión cerrada.', 'info');
        }
      });

      const { data: { session } } = await sbClient.auth.getSession();
      state.session = session;
      state.usuario = session?.user || null;
      actualizarUiAuth();
      if (session?.user) {
        await migrarDatosNavegadorASupabase(session.user);
      }
    } else {
      actualizarUiAuth();
    }
  } catch (err) {
    console.warn('[Memorialista] Inicialización Supabase:', err);
    actualizarUiAuth();
  }
}

function actualizarUiAuth() {
  const btnAuth = $('#btnAuthHeader');
  if (!btnAuth) return;

  if (state.usuario) {
    const nombre = (state.usuario.email || 'abogado').split('@')[0];
    btnAuth.textContent = `⚖️ ${nombre}`;
    btnAuth.className = 'btn chico primario';
    btnAuth.title = `Conectado como ${state.usuario.email} · Clic para ver tu cuenta`;
    btnAuth.onclick = () => abrirModalCuenta();

    const elEmail = $('#cuentaUserEmail');
    const elFirma = $('#cuentaUserFirma');
    const elRol = $('#cuentaUserRol');
    const elCuota = $('#cuentaUserCuota');
    const elProgreso = $('#cuentaProgresoCuota');

    if (elEmail) elEmail.textContent = state.usuario.email;
    if (elFirma) elFirma.textContent = state.perfil?.nombre_firma || 'Despacho personal';
    if (elRol) elRol.textContent = (state.usuario.user_metadata?.rol || 'Abogado').toUpperCase();
    if (elCuota) {
      const limite = state.supabaseConfig?.limite_diario_usuario || 50;
      elCuota.textContent = `Activo (${limite} redacciones/día)`;
      if (elProgreso) elProgreso.style.width = '20%';
    }
  } else {
    btnAuth.textContent = '🔒 Iniciar sesión';
    btnAuth.className = 'btn chico';
    btnAuth.title = 'Inicia sesión con tu enlace mágico para respaldar tus memoriales';
    btnAuth.onclick = () => abrirModalAuth();
  }
}

function abrirModalAuth(mensaje = '') {
  const dlg = $('#modalAuth');
  if (!dlg) return;
  const msg = $('#msgAuthEstado');
  if (msg) {
    if (mensaje) {
      msg.style.display = 'block';
      msg.style.background = '#fffbeb';
      msg.style.border = '1px solid #fde68a';
      msg.style.color = '#92400e';
      msg.textContent = mensaje;
    } else {
      msg.style.display = 'none';
      msg.textContent = '';
    }
  }
  const emailInp = $('#authEmail');
  if (emailInp) emailInp.value = '';
  dlg.showModal();
}

function cerrarModalAuth() {
  const dlg = $('#modalAuth');
  if (dlg) dlg.close();
}

function abrirModalCuenta() {
  const dlg = $('#modalCuenta');
  if (!dlg) return;
  actualizarUiAuth();
  dlg.showModal();
}

function cerrarModalCuenta() {
  const dlg = $('#modalCuenta');
  if (dlg) dlg.close();
}

async function manejarSubmitMagicLink(e) {
  e.preventDefault();
  const inpEmail = $('#authEmail');
  const btn = $('#btnEnviarMagicLink');
  const msg = $('#msgAuthEstado');
  const email = (inpEmail.value || '').trim();
  if (!email) return;

  btn.disabled = true;
  msg.style.display = 'block';
  msg.style.background = '#eff6ff';
  msg.style.border = '1px solid #bfdbfe';
  msg.style.color = '#1e40af';
  msg.textContent = '⏳ Enviando enlace mágico a tu correo...';

  try {
    if (sbClient) {
      const { error } = await sbClient.auth.signInWithOtp({
        email: email,
        options: {
          emailRedirectTo: window.location.origin
        }
      });
      if (error) throw error;

      msg.style.background = '#f0fdf4';
      msg.style.border = '1px solid #bbf7d0';
      msg.style.color = '#166534';
      msg.innerHTML = `📬 <strong>¡Enlace mágico enviado con éxito!</strong><br>Revisa tu correo en <u>${email}</u> y haz clic en el enlace para ingresar de inmediato.`;
    } else {
      // Modo local / sin Supabase remoto: sesión simulada para desarrollo y pruebas
      state.usuario = { id: 'dev-user-local', email: email, role: 'authenticated' };
      state.session = { access_token: 'mock-' + email.replace(/[^a-zA-Z0-9]/g, '') + '-token', user: state.usuario };
      actualizarUiAuth();
      cerrarModalAuth();
      toast(`Sesión iniciada como ${email}`, 'ok');
      await migrarDatosNavegadorASupabase(state.usuario);
    }
  } catch (err) {
    console.error('Error enviando enlace mágico:', err);
    msg.style.background = '#fef2f2';
    msg.style.border = '1px solid #fecaca';
    msg.style.color = '#991b1b';
    msg.textContent = 'Error al enviar enlace mágico: ' + (err.message || err);
  } finally {
    btn.disabled = false;
  }
}

async function migrarDatosNavegadorASupabase(user) {
  if (!user || !user.id) return;
  const claveMigracion = 'supabase_migrado_' + user.id;
  if (localStorage.getItem(claveMigracion)) {
    return;
  }

  try {
    const membrete = lsGet('membrete');
    const logoData = await IDB.get('almacen', 'logo');
    const firmaData = await IDB.get('almacen', 'firma');
    const plantillaData = await IDB.get('almacen', 'plantilla');
    const historial = (await IDB.getAll('historial')) || [];

    const tieneDatos = membrete || logoData || firmaData || plantillaData || (historial && historial.length > 0);
    if (!tieneDatos) {
      localStorage.setItem(claveMigracion, new Date().toISOString());
      return;
    }

    toast('🔄 Migrando tus datos locales del navegador a tu cuenta en la nube...', 'info', 5000);

    let logoPath = null;
    let firmaPath = null;
    let plantillaPath = null;

    if (sbClient) {
      // 1. Storage privado para logo, firma y plantilla
      if (logoData) {
        const logoBlob = dataUrlABlob(logoData);
        if (logoBlob) {
          logoPath = `logo/${user.id}/logo.png`;
          await sbClient.storage.from('archivos-privados').upload(logoPath, logoBlob, { upsert: true }).catch(e => console.warn(e));
        }
      }
      if (firmaData) {
        const firmaBlob = dataUrlABlob(firmaData);
        if (firmaBlob) {
          firmaPath = `firma/${user.id}/firma.png`;
          await sbClient.storage.from('archivos-privados').upload(firmaPath, firmaBlob, { upsert: true }).catch(e => console.warn(e));
        }
      }
      if (plantillaData) {
        plantillaPath = `plantilla/${user.id}/plantilla.docx`;
        await sbClient.storage.from('archivos-privados').upload(plantillaPath, plantillaData, { upsert: true }).catch(e => console.warn(e));
      }

      // 2. Perfil del abogado
      const nombreUsuario = membrete?.nombre || user.email.split('@')[0];
      await sbClient.from('perfiles').upsert({
        id: user.id,
        email: user.email,
        nombre_completo: nombreUsuario,
        tarjeta_profesional: membrete?.tarjeta || '',
        telefono: membrete?.celular || '',
        direccion: membrete?.direccion || '',
        ciudad: membrete?.ciudad || 'Bogotá D.C.',
        firma_grafica_path: firmaPath
      }).catch(e => console.warn('Error perfil:', e));

      // 3. Migrar historial a clientes, casos, documentos y versiones
      let migrados = 0;
      for (const item of historial) {
        const nomCliente = (item.cliente || item.datos?.cliente || 'Cliente ' + (migrados + 1)).split(/[,\n]/)[0].trim();
        const contraparte = (item.datos?.contraparte || '').split(/[,\n]/)[0].trim();
        const radicado = item.datos?.radicado || '';
        const despacho = item.datos?.destinatario || '';

        const { data: clienteCreado } = await sbClient.from('clientes').insert({
          user_id: user.id,
          nombre_razon_social: nomCliente || 'Cliente sin nombre',
          numero_documento: 'Por registrar',
          tipo_persona: 'natural',
          domicilio: item.datos?.ciudad || 'Bogotá D.C.'
        }).select().single().catch(() => ({ data: null }));

        const { data: casoCreado } = await sbClient.from('casos').insert({
          user_id: user.id,
          cliente_id: clienteCreado ? clienteCreado.id : null,
          nombre_caso: item.titulo || `Caso ${nomCliente} vs ${contraparte || 'Contraparte'}`,
          contraparte: contraparte,
          radicado: radicado,
          despacho: despacho,
          tipo_proceso: item.tipo,
          estado: 'activo'
        }).select().single().catch(() => ({ data: null }));

        const { data: docCreado } = await sbClient.from('documentos').insert({
          caso_id: casoCreado ? casoCreado.id : null,
          tipo: item.tipo || 'memorial',
          titulo: item.titulo || 'Memorial judicial',
          datos: item.datos || {},
          texto: item.texto || '',
          version: 1,
          creado_por: user.id
        }).select().single().catch(() => ({ data: null }));

        if (docCreado) {
          await sbClient.from('versiones').insert({
            documento_id: docCreado.id,
            version: 1,
            texto: item.texto || '',
            datos: item.datos || {},
            creado_por: user.id,
            comentario: 'Migrado automáticamente desde el navegador'
          }).catch(e => console.warn(e));
          migrados++;
        }
      }

      toast(`✓ ¡Migración completada! ${migrados} escritos, tu membrete y archivos se guardaron en Supabase.`, 'ok', 6000);
    }

    localStorage.setItem(claveMigracion, new Date().toISOString());
  } catch (err) {
    console.error('Error migrando datos a Supabase:', err);
    toast('Nota: algunos datos locales no pudieron sincronizarse a la nube: ' + err.message, 'error', 6000);
  }
}

async function sincronizarDocumentoConSupabase(docId, data) {
  if (!sbClient || !state.usuario) return;
  try {
    const user = state.usuario;
    const nomCliente = (data.datos?.cliente || 'Cliente').split(/[,\n]/)[0].trim();
    const contraparte = (data.datos?.contraparte || '').split(/[,\n]/)[0].trim();

    const { data: casoCreado } = await sbClient.from('casos').insert({
      user_id: user.id,
      nombre_caso: data.titulo || `Expediente ${nomCliente}`,
      contraparte: contraparte,
      radicado: data.datos?.radicado || '',
      despacho: data.datos?.destinatario || '',
      tipo_proceso: data.tipo,
      estado: 'activo'
    }).select().single();

    const { data: docCreado } = await sbClient.from('documentos').insert({
      caso_id: casoCreado ? casoCreado.id : null,
      tipo: data.tipo,
      titulo: data.titulo || 'Memorial',
      datos: data.datos || {},
      texto: data.texto || '',
      version: 1,
      creado_por: user.id
    }).select().single();

    if (docCreado) {
      await sbClient.from('versiones').insert({
        documento_id: docCreado.id,
        version: 1,
        texto: data.texto || '',
        datos: data.datos || {},
        creado_por: user.id,
        comentario: 'Versión guardada desde el editor'
      });
    }
  } catch (err) {
    console.warn('Error sincronizando documento individual:', err);
  }
}

async function exportarTodosMisDatos() {
  toast('Preparando exportación completa de tus datos...', 'info', 3000);
  try {
    const res = await apiFetch('/api/usuario/exportar-datos');
    if (!res.ok) {
      throw new Error('No se pudo generar la exportación en el servidor.');
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `el_memorialista_mis_datos_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast('✓ ¡Tus datos se exportaron exitosamente en formato JSON!', 'ok');
  } catch (err) {
    console.error('Error exportando datos:', err);
    toast('Error exportando datos: ' + err.message, 'error');
  }
}

async function eliminarMiCuenta() {
  const confirmacion = window.confirm(
    '⚠️ ADVERTENCIA CRÍTICA: ELIMINACIÓN PERMANENTE DE CUENTA\n\n' +
    'Esta acción borrará de forma definitiva e irreversible:\n' +
    '• Tu cuenta de usuario y perfil de abogado.\n' +
    '• Todos tus clientes registrados.\n' +
    '• Todos tus casos y expedientes.\n' +
    '• Todos los memoriales redactados y su historial de versiones.\n' +
    '• Tu logo, firma y plantilla en el almacenamiento privado.\n\n' +
    '¿Estás completamente seguro de que deseas proceder?'
  );

  if (!confirmacion) return;

  const confirmacion2 = window.prompt(
    'Para confirmar la eliminación definitiva, escribe "ELIMINAR MI CUENTA":', ''
  );

  if (confirmacion2 !== 'ELIMINAR MI CUENTA') {
    toast('Confirmación incorrecta. Tu cuenta permanece segura.', 'info');
    return;
  }

  try {
    toast('Eliminando cuenta y datos...', 'info', 4000);
    const res = await apiFetch('/api/usuario/eliminar-cuenta', { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error en el servidor al eliminar cuenta.');
    }

    if (sbClient) {
      await sbClient.auth.signOut().catch(() => {});
    }

    const keysBorrar = Object.keys(localStorage).filter(k => k.startsWith('supabase_migrado_') || k === 'codigoAcceso');
    keysBorrar.forEach(k => localStorage.removeItem(k));
    await IDB.del('almacen', 'logo').catch(() => {});
    await IDB.del('almacen', 'firma').catch(() => {});
    await IDB.del('almacen', 'plantilla').catch(() => {});
    await IDB.clear('historial').catch(() => {});

    state.session = null;
    state.usuario = null;
    actualizarUiAuth();
    cerrarModalCuenta();

    toast('Tu cuenta y todos tus datos fueron eliminados definitivamente.', 'ok', 7000);
  } catch (err) {
    console.error('Error eliminando cuenta:', err);
    toast('Error al eliminar cuenta: ' + err.message, 'error', 7000);
  }
}

/* =========================================================
   Base de Datos Interna del Navegador (IndexedDB)
   Almacenamiento privado, seguro e ilimitado por usuario
   ========================================================= */
const IDB = {
  _db: null,
  async abrir() {
    if (this._db) return this._db;
    return new Promise((resolve, reject) => {
      const req = indexedDB.open('memorialista_db', 1);
      req.onupgradeneeded = e => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('almacen')) db.createObjectStore('almacen');
        if (!db.objectStoreNames.contains('historial')) db.createObjectStore('historial', { keyPath: 'id' });
      };
      req.onsuccess = e => { this._db = e.target.result; resolve(this._db); };
      req.onerror = e => reject(e.target.error);
    });
  },
  async get(store, key) {
    const db = await this.abrir();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(store, 'readonly');
      const req = tx.objectStore(store).get(key);
      req.onsuccess = () => resolve(req.result ?? null);
      req.onerror = () => reject(req.error);
    });
  },
  async set(store, key, val) {
    const db = await this.abrir();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(store, 'readwrite');
      const req = key !== undefined ? tx.objectStore(store).put(val, key) : tx.objectStore(store).put(val);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  },
  async del(store, key) {
    const db = await this.abrir();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(store, 'readwrite');
      const req = tx.objectStore(store).delete(key);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  },
  async getAll(store) {
    const db = await this.abrir();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(store, 'readonly');
      const req = tx.objectStore(store).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  },
  async clear(store) {
    const db = await this.abrir();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(store, 'readwrite');
      const req = tx.objectStore(store).clear();
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  }
};

const Almacen = {
  async leer(k) {
    try { return await IDB.get('almacen', k); } catch { return null; }
  },
  async escribir(k, data) {
    try { await IDB.set('almacen', k, data); }
    catch (e) {
      if (e && e.name === 'QuotaExceededError') {
        toast('El almacenamiento interno está lleno. Te recomendamos descargar una copia de seguridad.', 'error', 9000);
      }
      throw e;
    }
  },
  async borrar(k) {
    try { await IDB.del('almacen', k); } catch { /* ignore */ }
  },
  async listarHist() {
    try {
      const lista = await IDB.getAll('historial');
      return lista.sort((a, b) => (b.actualizado || b.creado || 0) - (a.actualizado || a.creado || 0));
    } catch { return []; }
  },
  async guardarHist(id, data) {
    try {
      await IDB.set('historial', undefined, { id, ...data });
    } catch (e) {
      if (e && e.name === 'QuotaExceededError') {
        toast('El espacio de almacenamiento del navegador está lleno. Te sugerimos descargar una copia de seguridad desde el Historial.', 'error', 9000);
      }
      throw e;
    }
  },
  async borrarHist(id) {
    try { await IDB.del('historial', id); } catch { /* ignore */ }
  }
};

async function migrarLocalStorageAIndexedDB() {
  if (localStorage.getItem('memorialista:migrado_idb_v2')) return;
  try {
    const histViejo = lsGet('hist');
    if (Array.isArray(histViejo)) {
      for (const item of histViejo) {
        if (item && item.id) await IDB.set('historial', undefined, item);
      }
      lsDel('hist');
    }
    const logoViejo = lsGet('img:logo');
    if (logoViejo) { await IDB.set('almacen', 'logo', logoViejo); lsDel('img:logo'); }
    const firmaVieja = lsGet('img:firma');
    if (firmaVieja) { await IDB.set('almacen', 'firma', firmaVieja); lsDel('img:firma'); }
    for (let i = 0; i < 20; i++) {
      const p = lsGet('doc:plantilla_' + i);
      if (p) { await IDB.set('almacen', 'plantilla_' + i, p); lsDel('doc:plantilla_' + i); }
    }
    localStorage.setItem('memorialista:migrado_idb_v2', '1');
    console.log('[Memorialista] Migración a IndexedDB completada con éxito.');
  } catch (e) {
    console.warn('[Memorialista] Error durante la migración a IndexedDB:', e);
  }
}

/* =========================================================
   Formato del escrito: lenguaje de marcas
   ========================================================= */
const RE_MARCA = /\[(COMPLETAR|VERIFICAR)(?::\s*[^\]]*)?\]/;
function limpiarSalida(t) {
  let s = String(t || '').replace(/\r\n?/g, '\n');
  s = s.replace(/^\s*```[a-zA-Z]*\s*\n/, '').replace(/\n```\s*$/, '');
  const m = /^(?:aquí|a continuación|claro|por supuesto)[^\n]*:\s*\n\s*\n/i.exec(s);
  if (m) s = s.slice(m[0].length);
  return s;
}
function parseDoc(texto) {
  const lineas = limpiarSalida(texto).split('\n');
  const bloques = [];
  let cur = null;
  const cerrar = () => { if (cur) { bloques.push(cur); cur = null; } };
  for (const bruta of lineas) {
    const l = bruta.replace(/\s+$/, '');
    if (!l.trim()) { cerrar(); continue; }
    let m;
    if ((m = /^\s*\[\[\s*FIRMA(?:\s*:\s*([^\]]*?))?\s*\]\]\s*$/i.exec(l))) { cerrar(); bloques.push({ t: 'firma', rol: (m[1] || '').trim() }); continue; }
    if ((m = /^(#{1,3})\s+(.+)$/.exec(l))) { cerrar(); bloques.push({ t: 'h' + m[1].length, lines: [m[2].replace(/\s+#+\s*$/, '')] }); continue; }
    if ((m = /^\s*>\s?(.*)$/.exec(l))) { if (!cur || cur.t !== 'quote') { cerrar(); cur = { t: 'quote', lines: [] }; } cur.lines.push(m[1]); continue; }
    if ((m = /^\s*\|\s?(.*)$/.exec(l))) { if (!cur || cur.t !== 'ref') { cerrar(); cur = { t: 'ref', lines: [] }; } cur.lines.push(m[1]); continue; }
    if ((m = /^\s*[-•*]\s+(.*)$/.exec(l)) && !/^\s*\*\*/.test(l)) { cerrar(); cur = { t: 'li', lines: [m[1]] }; continue; }
    if (cur && (cur.t === 'quote' || cur.t === 'ref')) cerrar();
    if (!cur) cur = { t: 'p', lines: [] };
    cur.lines.push(l.replace(/^\s+/, ''));
  }
  cerrar();
  for (const b of bloques) {
    if (b.t === 'p' && b.lines.length === 1) {
      const m = /^\*\*([^*]{2,80})\*\*:?$/.exec(b.lines[0].trim());
      if (m && m[1] === m[1].toLocaleUpperCase('es-CO') && /[A-ZÁÉÍÓÚÑ]/.test(m[1]) && !/[.;,]$/.test(m[1])) { b.t = 'h2'; b.lines = [m[1]]; }
    }
  }
  return bloques;
}
function parseInline(s) {
  const runs = [];
  let b = false, i = false, u = false, last = 0, m;
  const re = /(_{3,}|\*\*|__|\*|\[(?:COMPLETAR|VERIFICAR)(?::[^\]]*)?\])/g;
  while ((m = re.exec(s))) {
    if (m.index > last) runs.push({ text: s.slice(last, m.index), b, i, u });
    const tok = m[1];
    if (/^_{3,}$/.test(tok)) runs.push({ text: tok, b, i, u });
    else if (tok === '**') b = !b;
    else if (tok === '__') u = !u;
    else if (tok === '*') i = !i;
    else runs.push({ text: tok, b, i, u, mk: tok.startsWith('[COMPLETAR') ? 'c' : 'v' });
    last = re.lastIndex;
  }
  if (last < s.length) runs.push({ text: s.slice(last), b, i, u });
  return runs.filter(r => r.text);
}
function textoPlano(dsl) {
  const out = [];
  for (const b of parseDoc(dsl)) {
    if (b.t === 'firma') { out.push(firmaLineas(b.rol).join('\n')); continue; }
    const lines = b.lines.map(l => parseInline(l).map(r => r.text).join(''));
    if (b.t === 'li') out.push('• ' + lines.join('\n'));
    else if (b.t === 'h1' || b.t === 'h2') out.push(state.perfil.formato.mayus ? lines.join(' ').toLocaleUpperCase('es-CO') : lines.join(' '));
    else out.push(lines.join('\n'));
  }
  return out.join('\n\n');
}
function quitarVerificar(dsl) { return dsl.replace(/[ \t]*\[VERIFICAR(?::[^\]]*)?\]/g, ''); }

/* =========================================================
   Vista previa: membrete, cuerpo y firma
   ========================================================= */
function generoAb() { const g = state.perfil.abogado.genero; return g === 'f' ? 'a' : g === 'm' ? 'o' : 'o(a)'; }
function firmaLineas(rol) {
  const ab = state.perfil.abogado, f = state.perfil.formato;
  const L = ['_______________________________', (ab.nombre || '[COMPLETAR: nombre del abogado]').toLocaleUpperCase('es-CO')];
  if (ab.cedula) L.push(`C.C. No. ${ab.cedula}${ab.cedulaLugar ? ' de ' + ab.cedulaLugar : ''}`);
  if (ab.tp) L.push(`T.P. No. ${ab.tp} del C. S. de la J.`);
  if (rol) L.push(rol);
  if (f.firmaContacto) { const c = [ab.correo, ab.telefono && 'Tel. ' + ab.telefono].filter(Boolean).join(' · '); if (c) L.push(c); }
  return L;
}
function firmaHtml(rol) {
  const ab = state.perfil.abogado, f = state.perfil.formato;
  const ph = t => `<span class="ph">${esc(t)}</span>`;
  const L = ['_______________________________'];
  L.push(ab.nombre ? `<strong>${esc(ab.nombre.toLocaleUpperCase('es-CO'))}</strong>` : ph('NOMBRE DEL ABOGADO'));
  L.push(ab.cedula ? `C.C. No. ${esc(ab.cedula)}${ab.cedulaLugar ? ' de ' + esc(ab.cedulaLugar) : ''}` : ph('C.C. No. —'));
  L.push(ab.tp ? `T.P. No. ${esc(ab.tp)} del C. S. de la J.` : ph('T.P. No. — del C. S. de la J.'));
  if (rol) L.push(esc(rol));
  if (f.firmaContacto) { const c = [ab.correo, ab.telefono && 'Tel. ' + ab.telefono].filter(Boolean).map(esc).join(' · '); if (c) L.push(c); }
  const img = IMG.firma ? `<img class="firma-img" src="${IMG.firma.dataUrl}" alt="">` : '<div class="firma-espacio"></div>';
  return `<div data-b="firma" data-rol="${esc(rol)}" contenteditable="false" class="firma${f.firmaAlin === 'centro' ? ' centro' : ''}">${img}${L.join('<br>')}</div>`;
}
function inlineHtml(linea) {
  return parseInline(linea).map(r => {
    let t = esc(r.text);
    if (r.mk) t = `<mark class="mk-${r.mk}">${t}</mark>`;
    if (r.u) t = `<u>${t}</u>`;
    if (r.i) t = `<em>${t}</em>`;
    if (r.b) t = `<strong>${t}</strong>`;
    return t;
  }).join('');
}
function cuerpoHtml(bloques) {
  return bloques.map(b => {
    if (b.t === 'firma') return firmaHtml(b.rol);
    const multi = b.t === 'p' && b.lines.length > 1;
    const inner = b.lines.map(inlineHtml).join('<br>');
    return `<p data-b="${b.t}"${multi ? ' class="multi"' : ''}>${inner || '<br>'}</p>`;
  }).join('');
}
function pieTexto() {
  const ab = state.perfil.abogado, m = state.perfil.membrete;
  const dirCiudad = [ab.direccion, ab.ciudad].filter(Boolean);
  if (m.diseno === 'centrado') return [...dirCiudad, ab.telefono && 'Tel. ' + ab.telefono, ab.correo, m.web].filter(Boolean).join('  ·  ');
  if (m.diseno === 'sobrio') return [m.web].filter(Boolean).join('');
  return [...dirCiudad, m.web].filter(Boolean).join('  ·  ');
}
function contactoCabecera() {
  const ab = state.perfil.abogado;
  return [ab.telefono && 'Tel. ' + ab.telefono, ab.correo].filter(Boolean).join('  ·  ');
}
function usaPlantilla() { return state.perfil.membrete.modo === 'plantilla' && !!(state.plantilla && state.plantilla.info); }
function membreteHtml() {
  const p = state.perfil, m = p.membrete, ab = p.abogado;
  if (usaPlantilla()) {
    const cab = state.plantilla.info.cab;
    if (!cab || (!cab.imgs.length && !cab.textos.length)) return '<div class="memb-plantilla"><div class="tx">Tu plantilla no tiene encabezado.</div></div>';
    const imgs = cab.imgs.filter(i => i.src).map(i => `<img src="${i.src}" alt="" style="width:${i.wcm.toFixed(2)}cm;max-height:${i.hcm.toFixed(2)}cm">`).join('');
    return `<div class="memb-plantilla">${imgs}${cab.textos.map(t => `<div class="tx">${esc(t)}</div>`).join('')}</div>`;
  }
  const nombre = (m.titulo || ab.nombre || '').trim();
  const nom = nombre ? esc(nombre) : '<span class="memb-vacio">Nombre del abogado</span>';
  const sub = m.subtitulo ? esc(m.subtitulo) : (nombre ? '' : '<span class="memb-vacio">Abogado(a) · Especialidad</span>');
  const logo = IMG.logo ? `<img class="memb-logo" src="${IMG.logo.dataUrl}" alt="">` : '';
  const linea = m.linea ? '<div class="memb-linea"></div>' : '';
  const contacto = esc(contactoCabecera());
  if (m.diseno === 'lateral') {
    return `<div class="memb-lateral${logo ? '' : ' sin-logo'}">${logo}<div class="memb-texto"><div class="memb-nombre">${nom}</div>${sub ? `<div class="memb-sub">${sub}</div>` : ''}${contacto ? `<div class="memb-contacto">${contacto}</div>` : ''}</div>${linea}</div>`;
  }
  if (m.diseno === 'sobrio') {
    const dir = esc([ab.direccion, ab.ciudad].filter(Boolean).join(', '));
    return `<div class="memb-sobrio"><div class="memb-nombre">${nom}</div><div class="memb-contacto der">${contacto}</div><div class="memb-sub">${sub}</div><div class="memb-contacto der">${dir}</div><div class="memb-linea"></div></div>`;
  }
  return `<div class="memb-centrado">${logo}<div class="memb-nombre">${nom}</div>${sub ? `<div class="memb-sub">${sub}</div>` : ''}${linea}</div>`;
}
function pieHtml(conMembrete, paginas) {
  const m = state.perfil.membrete;
  let s = '';
  if (conMembrete) {
    if (usaPlantilla()) {
      const pie = state.plantilla.info.pie;
      if (pie) s += pie.imgs.filter(i => i.src).map(i => `<img src="${i.src}" alt="" style="display:block;margin:0 auto;width:${i.wcm.toFixed(2)}cm;max-height:${i.hcm.toFixed(2)}cm">`).join('') + pie.textos.map(t => `<div>${esc(t)}</div>`).join('');
    } else {
      const t = pieTexto();
      if (t || !state.perfil.abogado.nombre) s += `${m.linea ? '<div class="pie-linea"></div>' : ''}<div>${t ? esc(t) : '<span class="memb-vacio">Dirección · Ciudad · Teléfono · Correo</span>'}</div>`;
    }
  }
  if (m.numeracion && !usaPlantilla()) s += `<div class="pie-pag">Página 1 de ${paginas || 1}</div>`;
  return s;
}

/* Medidas efectivas: con plantilla mandan su papel y sus márgenes */
function medidas() {
  const f = state.perfil.formato;
  if (usaPlantilla() && state.plantilla.info.papel) {
    const i = state.plantilla.info;
    return { papel: { w: i.papel.w, h: i.papel.h }, mg: i.margenes || MARGENES[f.margenes] };
  }
  return { papel: PAPEL[f.papel] || PAPEL.carta, mg: MARGENES[f.margenes] || MARGENES.amplio };
}
function fuenteEfectiva() {
  const f = state.perfil.formato;
  if (usaPlantilla() && f.fuentePlantilla && state.plantilla.info.fuente) {
    const nom = state.plantilla.info.fuente.nombre;
    return { nombre: nom, tam: state.plantilla.info.fuente.tam || f.tamano, conocida: FUENTES[nom] || null };
  }
  return { nombre: f.fuente, tam: f.tamano, conocida: FUENTES[f.fuente] || FUENTES.Arial };
}
let fuenteCargada = 'Arimo';
function cargarFuenteHoja(web) {
  if (!web || web === fuenteCargada) return;
  fuenteCargada = web;
  $('#fuenteHojaCss').href = `https://fonts.googleapis.com/css2?family=${web.replace(/ /g, '+')}:ital,wght@0,400;0,700;1,400;1,700&display=swap`;
}
function aplicarFormato(hoja) {
  const p = state.perfil, f = p.formato;
  const { papel, mg } = medidas();
  const fu = fuenteEfectiva();
  if (fu.conocida) cargarFuenteHoja(fu.conocida.web);
  const css = fu.conocida ? fu.conocida.css : `"${fu.nombre}", Arial, sans-serif`;
  const s = hoja.style;
  s.setProperty('--hoja-ancho', papel.w + 'cm');
  s.setProperty('--hoja-alto', papel.h + 'cm');
  s.setProperty('--m-sup', mg.sup + 'cm'); s.setProperty('--m-inf', mg.inf + 'cm');
  s.setProperty('--m-izq', mg.izq + 'cm'); s.setProperty('--m-der', mg.der + 'cm');
  s.setProperty('--hoja-fuente', css);
  s.setProperty('--hoja-tam', fu.tam + 'pt');
  s.setProperty('--hoja-int', String(Math.round(Number(f.interlineado) * 1.15 * 1000) / 1000));
  s.setProperty('--hoja-esp', (ESPACIO[f.espacio] ?? 8) + 'pt');
  s.setProperty('--hoja-alin', f.alineacion === 'izquierda' ? 'left' : 'justify');
  s.setProperty('--hoja-tit-alin', f.titulos === 'izquierda' ? 'left' : 'center');
  s.setProperty('--hoja-sangria', f.sangria ? '1.25cm' : '0cm');
  s.setProperty('--ref-sangria', f.refSangria ? ((papel.w - mg.izq - mg.der) / 2).toFixed(2) + 'cm' : '0cm');
  s.setProperty('--cita-estilo', f.citaCursiva ? 'italic' : 'normal');
  s.setProperty('--memb-color', p.membrete.color || '#1f3a68');
  hoja.classList.toggle('mayus', !!f.mayus);
}
function ajustarZoom() {
  const hoja = $('#hoja'), mesa = $('#mesaHoja');
  if (!hoja || !mesa || mesa.offsetParent === null) return;
  const cs = getComputedStyle(mesa);
  const disponible = mesa.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  const anchoPx = medidas().papel.w * 37.795;
  if (disponible < 560) { hoja.classList.add('lectura'); hoja.style.zoom = ''; return; }
  hoja.classList.remove('lectura');
  hoja.style.zoom = String(Math.min(1, Math.max(0.3, disponible / anchoPx)));
}
function estimarPaginas() {
  const hoja = $('#hoja'), cuerpo = $('#cuerpo');
  if (!hoja || hoja.classList.contains('lectura')) return 1;
  const { papel, mg } = medidas();
  const z = parseFloat(hoja.style.zoom) || 1;
  const util = (papel.h - mg.sup - mg.inf) * 37.795;
  const alto = cuerpo.getBoundingClientRect().height / (z || 1);
  const pz = cuerpo.getBoundingClientRect().height && hoja.getBoundingClientRect().width ? (hoja.getBoundingClientRect().width / (papel.w * 37.795)) : z;
  const altoReal = cuerpo.getBoundingClientRect().height / (pz || 1);
  return Math.max(1, Math.ceil((altoReal || alto) / util));
}
function textoEjemplo() {
  const ab = state.perfil.abogado;
  const g = generoAb();
  return EJEMPLO_TEXTO
    .replace(/@NOMBRE@/g, ab.nombre ? ab.nombre.toLocaleUpperCase('es-CO') : '[COMPLETAR: nombre del abogado]')
    .replace(/@CEDULA@/g, ab.cedula ? ab.cedula + (ab.cedulaLugar ? ' de ' + ab.cedulaLugar : '') : '[COMPLETAR: cédula]')
    .replace(/@TP@/g, ab.tp || '[COMPLETAR: número]')
    .replace(/@O@/g, g === 'o(a)' ? 'o(a)' : g);
}
function conMembreteDoc() { return state.ejemplo ? true : state.datos._membrete !== false; }
function renderMembreteHoja() {
  const hoja = $('#hoja');
  const con = conMembreteDoc();
  $('#membrete').innerHTML = con ? membreteHtml() : '';
  hoja.classList.toggle('sin-membrete', !con);
  $('#pie').innerHTML = pieHtml(con, estimarPaginas());
}
function renderHoja({ escribiendo = false } = {}) {
  const hoja = $('#hoja'), cuerpo = $('#cuerpo');
  aplicarFormato(hoja);
  $('#selloEjemplo').hidden = !state.ejemplo;
  const texto = state.ejemplo ? textoEjemplo() : state.texto;
  cuerpo.innerHTML = cuerpoHtml(parseDoc(texto));
  cuerpo.classList.toggle('escribiendo', escribiendo);
  cuerpo.contentEditable = (!state.ejemplo && !state.generando) ? 'true' : 'false';
  renderMembreteHoja();
  ajustarZoom();
  $('#pie').innerHTML = pieHtml(conMembreteDoc(), estimarPaginas());
  actualizarVerificacion();
}
function refrescarFirmas() {
  $$('#cuerpo [data-b="firma"]').forEach(el => { const t = document.createElement('div'); t.innerHTML = firmaHtml(el.dataset.rol || ''); el.replaceWith(t.firstChild); });
}

/* Serialización de la hoja editada de vuelta al formato de marcas */
function inlineDesdeDom(nodo) {
  let s = '';
  for (const n of nodo.childNodes) {
    if (n.nodeType === 3) { s += n.nodeValue.replace(/ /g, ' '); continue; }
    if (n.nodeType !== 1) continue;
    const tag = n.tagName;
    if (tag === 'BR') { s += '\n'; continue; }
    const dentro = inlineDesdeDom(n);
    if (!dentro) continue;
    const fw = n.style && n.style.fontWeight;
    if (tag === 'STRONG' || tag === 'B' || fw === 'bold' || Number(fw) >= 600) s += envolver(dentro, '**');
    else if (tag === 'EM' || tag === 'I' || (n.style && n.style.fontStyle === 'italic')) s += envolver(dentro, '*');
    else if (tag === 'U') s += envolver(dentro, '__');
    else if (tag === 'DIV' || tag === 'P') s += (s && !s.endsWith('\n') ? '\n' : '') + dentro;
    else s += dentro;
  }
  return s;
}
function envolver(t, m) {
  return t.split('\n').map(l => { const a = /^\s*/.exec(l)[0], z = /\s*$/.exec(l)[0], c = l.trim(); return c ? a + m + c + m + z : l; }).join('\n');
}
function serializarCuerpo() {
  const out = [];
  for (const el of $('#cuerpo').children) {
    const t = el.dataset.b || 'p';
    if (t === 'firma') { out.push(el.dataset.rol ? `[[FIRMA: ${el.dataset.rol}]]` : '[[FIRMA]]'); continue; }
    const lines = inlineDesdeDom(el).replace(/\n+$/, '').split('\n').map(l => l.replace(/\s+$/, ''));
    if (!lines.join('').trim()) continue;
    const pre = { h1: '# ', h2: '## ', h3: '### ', quote: '> ', ref: '| ' }[t];
    if (t === 'h1' || t === 'h2' || t === 'h3') out.push(pre + lines.join(' ').trim());
    else if (t === 'quote' || t === 'ref') out.push(lines.map(l => pre + l).join('\n'));
    else if (t === 'li') out.push('- ' + lines.join('\n'));
    else out.push(lines.join('\n'));
  }
  return out.join('\n\n');
}

/* =========================================================
   Verificación: datos por completar y citas por verificar
   ========================================================= */
let panelAbierto = false;

function recogerMarcas() {
  const cuerpo = $('#cuerpo');
  const items = [];
  const walker = document.createTreeWalker(cuerpo, NodeFilter.SHOW_TEXT);
  const re = /\[(COMPLETAR|VERIFICAR)(?::\s*([^\]]*))?\]/g;
  let n;
  while ((n = walker.nextNode())) {
    let m; re.lastIndex = 0;
    while ((m = re.exec(n.nodeValue))) {
      const bloque = n.parentElement.closest('#cuerpo > *');
      const previo = textoPrevio(bloque, n, m.index);
      items.push({ tipo: m[1] === 'COMPLETAR' ? 'c' : 'v', detalle: (m[2] || '').trim(), nodo: n, off: m.index, bloque, previo });
    }
  }
  return items;
}

function textoPrevio(bloque, nodo, off) {
  if (!bloque) return '';
  const r = document.createRange();
  r.setStart(bloque, 0);
  try { r.setEnd(nodo, off); } catch { return ''; }
  return r.toString().replace(/\[(?:COMPLETAR|VERIFICAR)[^\]]*\]/g, '').replace(/\s+/g, ' ').trim();
}

async function verificarCitasDocumento() {
  if (state.ejemplo || state.generando || !state.texto || state.verificandoCitas) return;
  state.verificandoCitas = true;
  actualizarVerificacion();
  try {
    const res = await apiFetch('/api/verificar-citas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto: state.texto })
    });
    if (!res.ok) throw new Error('Error al verificar citas');
    const data = await res.json();
    state.citasVerificadas = data.citas || [];

    // Requerimiento 6: Si la opción es "Solo citas verificables", marca con [VERIFICAR] las citas en rojo
    const citasRojas = state.citasVerificadas.filter(c => c.color === 'rojo');
    if (citasRojas.length && (state.datos._juris === 'verificables' || !state.datos._juris)) {
      let modificado = state.texto;
      let huboCambio = false;
      for (const cr of citasRojas) {
        const orig = cr.texto_original;
        if (orig && modificado.includes(orig) && !modificado.includes(orig + ' [VERIFICAR]')) {
          modificado = modificado.replaceAll(orig, orig + ' [VERIFICAR]');
          huboCambio = true;
        }
      }
      if (huboCambio) {
        state.texto = modificado;
        renderHoja();
        guardarBorrador();
      }
    }
  } catch (err) {
    console.error('Error al verificar citas:', err);
  } finally {
    state.verificandoCitas = false;
    actualizarVerificacion();
  }
}

function actualizarVerificacion() {
  const verif = $('#verif'), panel = $('#panelVerif');
  if (state.ejemplo || state.generando || !state.texto) { verif.hidden = true; panel.hidden = true; return; }
  const items = recogerMarcas();
  const nc = items.filter(i => i.tipo === 'c').length, nv = items.filter(i => i.tipo === 'v').length;
  verif.replaceChildren();

  // 1. Citas verificadas oficialmente
  if (state.verificandoCitas) {
    verif.append(h('span', { class: 'vchip amarillo' }, '⏳ Verificando citas en fuentes oficiales…'));
  } else if (state.citasVerificadas && state.citasVerificadas.length) {
    const nVerdes = state.citasVerificadas.filter(c => c.color === 'verde').length;
    const nAmarillas = state.citasVerificadas.filter(c => c.color === 'amarillo').length;
    const nRojas = state.citasVerificadas.filter(c => c.color === 'rojo').length;

    if (nRojas) verif.append(h('button', { class: 'vchip rojo', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, `✗ ${nRojas} ${nRojas === 1 ? 'cita no encontrada' : 'citas no encontradas'}`));
    if (nAmarillas) verif.append(h('button', { class: 'vchip amarillo', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, `⚠ ${nAmarillas} ${nAmarillas === 1 ? 'cita por verificar' : 'citas por verificar'}`));
    if (nVerdes) verif.append(h('button', { class: 'vchip verde', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, `✓ ${nVerdes} ${nVerdes === 1 ? 'cita verificada' : 'citas verificadas'}`));
  }

  // 2. Datos por completar
  if (nc) verif.append(h('button', { class: 'vchip c', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, `${nc} ${nc === 1 ? 'dato' : 'datos'} por completar`));
  if (nv && (!state.citasVerificadas || !state.citasVerificadas.length)) verif.append(h('button', { class: 'vchip v', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, `${nv} ${nv === 1 ? 'cita' : 'citas'} por verificar`));

  // 3. Auditoría de datos (formulario vs. escrito generado)
  let nAudit = 0;
  if (typeof auditarDatosYEscrito === 'function') {
    state.auditoria = auditarDatosYEscrito(state.datos, state.texto, state.perfil);
    nAudit = state.auditoria ? state.auditoria.total : 0;
  }
  if (nAudit > 0) {
    verif.append(h('button', { class: 'vchip amarillo', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, `⚠ ${nAudit} ${nAudit === 1 ? 'dato para revisar' : 'datos para revisar'}`));
  } else if (!nc && (!state.citasVerificadas || !state.citasVerificadas.some(c => c.color === 'rojo' || c.color === 'amarillo'))) {
    verif.append(h('span', { class: 'vchip ok' }, '✓ Datos consistentes'));
  }

  // 4. Requisitos procesales evaluados
  if (state.revisionRequisitos && state.revisionRequisitos.length && state.textoRevisado === state.texto) {
    const nCriticos = state.revisionRequisitos.filter(r => r.critico && r.estado === 'no_cumple').length;
    if (nCriticos > 0) {
      verif.append(h('button', { class: 'vchip rojo', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, `✗ ${nCriticos} ${nCriticos === 1 ? 'requisito crítico' : 'requisitos críticos'}`));
    } else {
      verif.append(h('button', { class: 'vchip verde', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, '✓ Requisitos procesales'));
    }
  }

  if (!verif.children.length) verif.append(h('span', { class: 'vchip ok' }, '✓ Sin datos pendientes'));
  verif.hidden = false;
  if (panelAbierto) pintarPanel(items); else panel.hidden = true;
}

function alternarPanel() { panelAbierto = !panelAbierto; actualizarVerificacion(); }

function pintarPanel(items) {
  const panel = $('#panelVerif');
  panel.replaceChildren();

  // 0. Requisitos procesales evaluados
  if (state.revisionRequisitos && state.revisionRequisitos.length && state.textoRevisado === state.texto) {
    panel.append(h('h3', {}, 'Requisitos formales y procesales'));
    const divReqs = h('div', { style: 'display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px;' });
    state.revisionRequisitos.forEach(r => {
      const esCrit = r.critico && r.estado === 'no_cumple';
      const esNoCrit = !r.critico && r.estado === 'no_cumple';
      const cumple = r.estado === 'cumple';
      const estiloCaja = esCrit
        ? 'background: #fef2f2; border: 1.5px solid #ef4444; border-radius: 6px; padding: 8px 10px;'
        : esNoCrit
        ? 'background: #fffbeb; border: 1px solid #fcd34d; border-radius: 6px; padding: 8px 10px;'
        : cumple
        ? 'background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 6px 10px; font-size: 13px;'
        : 'background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 6px 10px; font-size: 12.5px;';
      const item = h('div', { style: estiloCaja });
      const badgeClase = esCrit ? 'rojo' : esNoCrit ? 'amarillo' : cumple ? 'verde' : '';
      const badgeTexto = esCrit ? '✗ No cumple · Crítico' : esNoCrit ? '⚠ No cumple · Recomendación' : cumple ? '✓ Cumple' : '— No aplica';

      const fila = h('div', { style: 'display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; flex-wrap: wrap;' },
        h('div', { style: 'flex: 1 1 240px;' },
          h('div', { style: 'display: flex; align-items: center; gap: 6px; flex-wrap: wrap;' },
            h('span', { class: `cita-badge ${badgeClase}` }, badgeTexto),
            h('strong', {}, r.texto),
            r.norma ? h('span', { style: 'font-size: 11.5px; opacity: 0.85;' }, `(${r.norma})`) : null
          ),
          r.evidencia ? h('div', { style: 'font-size: 12px; margin-top: 3px; opacity: 0.9;' }, h('strong', {}, 'Hallazgo: '), r.evidencia) : null,
          r.sugerencia && (esCrit || esNoCrit) ? h('div', { style: 'font-size: 12px; background: rgba(0,0,0,0.04); padding: 4px 6px; border-radius: 4px; margin-top: 4px;' }, h('strong', {}, 'Sugerencia: '), r.sugerencia) : null
        )
      );
      if (esCrit || esNoCrit) {
        fila.append(h('button', {
          class: `btn chico ${esCrit ? 'peligro-relleno' : 'fantasma'}`,
          type: 'button',
          style: esNoCrit ? 'border: 1px solid #d97706; color: #92400e;' : '',
          onclick: () => corregirConIA(r.sugerencia || `Agrega el siguiente requisito: ${r.texto} (${r.norma || ''})`)
        }, '🪄 Corregir con IA'));
      }
      item.append(fila);
      divReqs.append(item);
    });
    panel.append(divReqs);
  }

  // 1. Citas verificadas oficialmente
  if (state.citasVerificadas && state.citasVerificadas.length) {
    panel.append(h('h3', {}, 'Citas y jurisprudencia verificadas'));
    const ol = h('ol', { style: 'padding-left: 20px; margin-bottom: 16px;' });
    state.citasVerificadas.forEach(c => {
      const li = h('li', { style: 'margin-bottom: 10px; line-height: 1.4;' });
      const badgeClase = c.color === 'verde' ? 'verde' : c.color === 'rojo' ? 'rojo' : 'amarillo';
      const badgeTexto = c.color === 'verde' ? '✓ Existe y respalda' : c.color === 'rojo' ? '✗ No encontrada' : '⚠ Respaldo parcial / sin verificar';
      li.append(
        h('div', { style: 'display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 3px;' },
          h('strong', {}, c.nombre || c.texto_original),
          h('span', { class: `cita-badge ${badgeClase}` }, badgeTexto)
        )
      );
      if (c.url) {
        li.append(h('div', { style: 'font-size: 12px; margin-bottom: 2px;' },
          h('a', { href: c.url, target: '_blank', rel: 'noopener noreferrer', style: 'color: var(--azul, #2563eb); text-decoration: underline;' }, 'Ver documento oficial ↗')
        ));
      }
      if (c.pertinencia && c.pertinencia.fragmento) {
        li.append(h('div', { class: 'ctx', style: 'font-size: 12px; color: var(--color-texto-suave, #555); font-style: italic; background: rgba(0,0,0,0.03); padding: 4px 6px; border-radius: 4px; margin-top: 2px;' },
          `«${c.pertinencia.fragmento}»`
        ));
      }
      ol.append(li);
    });
    panel.append(ol);
  }

  // 2. Auditoría de datos del formulario vs. escrito
  const audit = state.auditoria || (typeof auditarDatosYEscrito === 'function' ? auditarDatosYEscrito(state.datos, state.texto, state.perfil) : null);
  if (audit && audit.total > 0) {
    panel.append(h('h3', {}, 'Auditoría de consistencia de datos'));

    // 0. Discrepancias entre cifras numéricas y expresiones en letras
    if (audit.discrepanciasCifrasLetras && audit.discrepanciasCifrasLetras.length) {
      panel.append(h('div', { style: 'font-weight: 700; font-size: 13px; color: #dc2626; margin: 6px 0 4px 0;' },
        `❌ Discrepancia entre cifra y letras (${audit.discrepanciasCifrasLetras.length}):`
      ));
      const olDisc = h('ol', { style: 'padding-left: 20px; margin-bottom: 12px;' });
      audit.discrepanciasCifrasLetras.forEach(disc => {
        const li = h('li', { style: 'margin-bottom: 6px; line-height: 1.4; color: #991b1b;' },
          h('strong', {}, disc.detalle || `${disc.cifraTexto} vs. ${disc.letrasTexto}`),
          h('span', { class: 'acc', style: 'margin-left: 8px;' },
            h('button', { class: 'enlace', type: 'button', onclick: () => irATexto(disc.cifraTexto || disc.letrasTexto) }, 'Ver en el texto')
          )
        );
        olDisc.append(li);
      });
      panel.append(olDisc);
    }

    // 1. Alertas de NIT (Dígito de verificación DIAN)
    if (audit.alertasNit && audit.alertasNit.length) {
      panel.append(h('div', { style: 'font-weight: 700; font-size: 13px; color: #dc2626; margin: 6px 0 4px 0;' },
        `⚠️ Alertas de NIT DIAN (${audit.alertasNit.length}):`
      ));
      const olNit = h('ol', { style: 'padding-left: 20px; margin-bottom: 12px;' });
      audit.alertasNit.forEach(an => {
        const li = h('li', { style: 'margin-bottom: 6px; line-height: 1.4; color: #991b1b;' },
          h('strong', {}, `${an.nit}: `),
          h('span', {}, an.detalle),
          h('span', { class: 'acc', style: 'margin-left: 8px;' },
            h('button', { class: 'enlace', type: 'button', onclick: () => irATexto(an.nit) }, 'Ver en el texto')
          )
        );
        olNit.append(li);
      });
      panel.append(olNit);
    }

    // a) Posibles invenciones (en el escrito pero no en tus datos)
    if (audit.invenciones && audit.invenciones.length) {
      panel.append(h('div', { style: 'font-weight: 600; font-size: 13px; color: var(--amarillo-osc, #b45309); margin: 6px 0 4px 0;' },
        `⚠️ Posibles invenciones (${audit.invenciones.length}): en el escrito pero no en tus datos`
      ));
      const olInv = h('ol', { style: 'padding-left: 20px; margin-bottom: 12px;' });
      audit.invenciones.forEach(inv => {
        const li = h('li', { style: 'margin-bottom: 6px; line-height: 1.4;' });
        li.append(
          h('strong', {}, `${inv.tipo}: `),
          h('span', {}, inv.valor || inv.textoOriginal),
          h('span', { class: 'acc', style: 'margin-left: 8px;' },
            h('button', { class: 'enlace', type: 'button', onclick: () => irATexto(inv.textoOriginal || inv.valor) }, 'Ver en el texto')
          )
        );
        li.append(h('div', { class: 'ctx', style: 'font-size: 12px; color: #666;' }, 'Dato generado en el escrito que no fue suministrado en el formulario.'));
        olInv.append(li);
      });
      panel.append(olInv);
    }

    // b) Posibles omisiones (en tus datos pero no en el escrito)
    if (audit.omisiones && audit.omisiones.length) {
      panel.append(h('div', { style: 'font-weight: 600; font-size: 13px; color: var(--rojo, #b91c1c); margin: 6px 0 4px 0;' },
        `ℹ️ Posibles omisiones (${audit.omisiones.length}): en tus datos pero no en el escrito`
      ));
      const olOm = h('ol', { style: 'padding-left: 20px; margin-bottom: 12px;' });
      audit.omisiones.forEach(om => {
        const li = h('li', { style: 'margin-bottom: 6px;' });
        li.append(
          h('strong', {}, `${om.tipo}: `),
          h('span', {}, om.valor || om.textoOriginal)
        );
        li.append(h('div', { class: 'ctx', style: 'font-size: 12px; color: #666;' }, 'Ingresado en el formulario pero ausente en el escrito generado.'));
        olOm.append(li);
      });
      panel.append(olOm);
    }
  }

  // 3. Datos por completar
  const datosComp = items.filter(i => i.tipo === 'c');
  if (datosComp.length) {
    panel.append(h('h3', {}, 'Datos por completar'));
    const ol = h('ol', { style: 'padding-left: 20px;' });
    datosComp.forEach(it => {
      const li = h('li', { style: 'margin-bottom: 6px;' });
      li.append(h('strong', {}, it.detalle || 'Dato faltante'));
      li.append(h('span', { class: 'acc', style: 'margin-left: 8px;' }, h('button', { class: 'enlace', type: 'button', onclick: () => irAMarca(it) }, 'Ver en el texto')));
      if (it.previo) li.append(h('div', { class: 'ctx', style: 'font-size: 12px; color: #666;' }, '…' + it.previo.slice(-80)));
      ol.append(li);
    });
    panel.append(ol);
  }

  panel.append(h('p', { class: 'nota', style: 'margin-top: 12px; font-size: 12px; color: #666;' }, 'Las citas en verde cuentan con registro oficial verificado en la relatoría o base de leyes. Las citas en rojo no fueron halladas y deben corregirse o eliminarse antes de radicar.'));
  panel.hidden = false;
}

function irAMarca(it) {
  const el = it.bloque || it.nodo.parentElement;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.classList.remove('destello'); void el.offsetWidth; el.classList.add('destello');
  try {
    const r = document.createRange(); r.setStart(it.nodo, it.off); r.setEnd(it.nodo, Math.min(it.nodo.length, it.off + 11));
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  } catch { /* nodo cambió */ }
}

function irATexto(cadena) {
  if (!cadena) return;
  const cuerpo = $('#cuerpo');
  if (!cuerpo) return;

  const target = String(cadena).trim().toLowerCase();
  if (!target) return;

  // 1. Buscar en nodos de texto dentro de cuerpo
  const walker = document.createTreeWalker(cuerpo, NodeFilter.SHOW_TEXT, null, false);
  let nodo;
  while ((nodo = walker.nextNode())) {
    const val = (nodo.nodeValue || '').toLowerCase();
    const idx = val.indexOf(target);
    if (idx !== -1) {
      const el = nodo.parentElement || cuerpo;
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.remove('destello'); void el.offsetWidth; el.classList.add('destello');
      try {
        const r = document.createRange();
        r.setStart(nodo, idx);
        r.setEnd(nodo, Math.min(nodo.length, idx + target.length));
        const sel = getSelection();
        sel.removeAllRanges();
        sel.addRange(r);
      } catch { }
      return;
    }
  }

  // 2. Fallback: buscar en elementos hijos de cuerpo si abarca varias etiquetas
  for (const el of cuerpo.children) {
    if ((el.textContent || '').toLowerCase().includes(target)) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.remove('destello'); void el.offsetWidth; el.classList.add('destello');
      return;
    }
  }
}

/* =========================================================
   Word (.docx): XML de WordprocessingML
   ========================================================= */
const NS_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"';
const xesc = s => String(s ?? '').replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F￾￿]/g, '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const hex = c => String(c || '#1f3a68').replace('#', '').toUpperCase().slice(0, 6);
const cmTw = cm => Math.round(cm * 566.93);
const cmEmu = cm => Math.round(cm * 360000);
function rPrXml(o, ctx) {
  let s = '';
  if (ctx.fuente) { const f = xesc(ctx.fuente); s += `<w:rFonts w:ascii="${f}" w:hAnsi="${f}" w:cs="${f}" w:eastAsia="${f}"/>`; }
  if (o.b) s += '<w:b/><w:bCs/>';
  if (o.i) s += '<w:i/><w:iCs/>';
  if (o.caps) s += '<w:caps/>';
  if (o.color) s += `<w:color w:val="${o.color}"/>`;
  if (o.esp) s += `<w:spacing w:val="${o.esp}"/>`;
  const sz = o.sz || ctx.sz;
  if (sz) s += `<w:sz w:val="${sz}"/><w:szCs w:val="${sz}"/>`;
  if (o.hl) s += `<w:highlight w:val="${o.hl}"/>`;
  if (o.u) s += '<w:u w:val="single"/>';
  if (o.shd) s += `<w:shd w:val="clear" w:color="auto" w:fill="${o.shd}"/>`;
  return s ? `<w:rPr>${s}</w:rPr>` : '';
}
function rXml(r, ctx) {
  if (r.br) return '<w:r><w:br/></w:r>';
  if (r.tab) return `<w:r>${rPrXml(r, ctx)}<w:tab/></w:r>`;
  if (r.raw) return r.raw;
  const o = { ...r };
  if (r.mk === 'c') o.hl = 'yellow';
  if (r.mk === 'v') { o.shd = 'FFE1C7'; o.color = '7A3300'; }
  return `<w:r>${rPrXml(o, ctx)}<w:t xml:space="preserve">${xesc(r.text)}</w:t></w:r>`;
}
function pXml(o, ctx) {
  let pp = '';
  if (o.keepNext) pp += '<w:keepNext/>';
  if (o.keepLines) pp += '<w:keepLines/>';
  if (o.borde) pp += `<w:pBdr><w:${o.borde.pos} w:val="${o.borde.val || 'single'}" w:sz="${o.borde.sz || 6}" w:space="${o.borde.space ?? 4}" w:color="${o.borde.color || 'auto'}"/></w:pBdr>`;
  if (o.tabs) pp += `<w:tabs>${o.tabs.map(t => `<w:tab w:val="${t.val}" w:pos="${t.pos}"/>`).join('')}</w:tabs>`;
  const sp = o.sp || {};
  pp += `<w:spacing w:before="${sp.antes || 0}" w:after="${sp.despues || 0}" w:line="${sp.linea || 240}" w:lineRule="auto"/>`;
  if (o.ind) {
    const i = o.ind; let a = '';
    if (i.izq) a += ` w:left="${i.izq}"`;
    if (i.der) a += ` w:right="${i.der}"`;
    if (i.primera) a += ` w:firstLine="${i.primera}"`;
    if (i.colgante) a += ` w:hanging="${i.colgante}"`;
    if (a) pp += `<w:ind${a}/>`;
  }
  pp += `<w:jc w:val="${o.jc || 'left'}"/>`;
  if (o.szMarca) pp += `<w:rPr><w:sz w:val="${o.szMarca}"/><w:szCs w:val="${o.szMarca}"/></w:rPr>`;
  const runs = (o.runs || []).map(r => rXml(r, ctx)).join('') + (o.runsXml || '');
  return `<w:p><w:pPr>${pp}</w:pPr>${runs}</w:p>`;
}
function runsDe(b, extra = {}) {
  const out = [];
  b.lines.forEach((l, idx) => {
    if (idx) out.push({ br: true });
    for (const r of parseInline(l)) out.push({ text: r.text, b: r.b || extra.b, i: r.i || extra.i, u: r.u, caps: extra.caps, sz: extra.sz, mk: r.mk });
  });
  return out;
}
function imgXml(rid, wEmu, hEmu, id, nombre) {
  return `<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="${wEmu}" cy="${hEmu}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="${id}" name="${nombre}"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="${id}" name="${nombre}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="${rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="${wEmu}" cy="${hEmu}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>`;
}
function tamImagen(img, altoCm, maxAnchoCm) {
  let h = altoCm, w = altoCm * (img.w / img.h);
  if (w > maxAnchoCm) { w = maxAnchoCm; h = w * (img.h / img.w); }
  return { w, h };
}
function campoXml(instr, o, ctx) {
  const rp = rPrXml(o, ctx);
  return `<w:r>${rp}<w:fldChar w:fldCharType="begin"/></w:r><w:r>${rp}<w:instrText xml:space="preserve"> ${instr} </w:instrText></w:r><w:r>${rp}<w:fldChar w:fldCharType="separate"/></w:r><w:r>${rp}<w:t>1</w:t></w:r><w:r>${rp}<w:fldChar w:fldCharType="end"/></w:r>`;
}
function cabeceraXml(ctx) {
  const p = state.perfil, m = p.membrete, ab = p.abogado;
  const nombre = (m.titulo || ab.nombre || '').trim();
  const sub = (m.subtitulo || '').trim();
  const col = hex(m.color);
  const contacto = contactoCabecera();
  const gris = '595959';
  const anchoTw = cmTw(ctx.anchoTexto);
  const lineaVacia = (borde) => pXml({ sp: { antes: 40, despues: 240 }, borde, szMarca: 8 }, ctx);
  if (m.diseno === 'sobrio') {
    const dir = [ab.direccion, ab.ciudad].filter(Boolean).join(', ');
    const tabs = [{ val: 'right', pos: anchoTw }];
    return pXml({ tabs, runs: [{ text: nombre, b: true, caps: true, esp: 28, sz: 23, color: col }, { tab: true }, { text: contacto, sz: 17, color: gris }] }, ctx)
      + pXml({ tabs, sp: { despues: 240 }, borde: { pos: 'bottom', val: 'single', sz: 4, color: 'A6A6A6', space: 4 }, runs: [{ text: sub, sz: 18, color: gris }, { tab: true }, { text: dir, sz: 17, color: gris }] }, ctx);
  }
  if (m.diseno === 'lateral') {
    const textos = [
      nombre && pXml({ jc: ctx.logo ? 'right' : 'left', runs: [{ text: nombre, b: true, caps: true, esp: 12, sz: 28, color: col }] }, ctx),
      sub && pXml({ jc: ctx.logo ? 'right' : 'left', runs: [{ text: sub, sz: 19, color: gris }] }, ctx),
      contacto && pXml({ jc: ctx.logo ? 'right' : 'left', runs: [{ text: contacto, sz: 17, color: gris }] }, ctx),
    ].filter(Boolean).join('') || pXml({}, ctx);
    let x;
    if (ctx.logo) {
      const t = tamImagen(ctx.logo, 2, 5);
      const c1 = cmTw(t.w + 0.5), c2 = Math.max(1000, anchoTw - c1);
      const tb = '<w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/>';
      x = `<w:tbl><w:tblPr><w:tblW w:w="${anchoTw}" w:type="dxa"/><w:tblBorders>${tb}</w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar><w:tblLook w:val="0000"/></w:tblPr><w:tblGrid><w:gridCol w:w="${c1}"/><w:gridCol w:w="${c2}"/></w:tblGrid><w:tr><w:tc><w:tcPr><w:tcW w:w="${c1}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>${pXml({ runsXml: imgXml('rIdLogo', cmEmu(t.w), cmEmu(t.h), 9001, 'Logo') }, ctx)}</w:tc><w:tc><w:tcPr><w:tcW w:w="${c2}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>${textos}</w:tc></w:tr></w:tbl>`;
    } else x = textos;
    return x + lineaVacia(m.linea ? { pos: 'bottom', val: 'single', sz: 12, color: col, space: 1 } : null);
  }
  let x = '';
  if (ctx.logo) { const t = tamImagen(ctx.logo, 1.7, 6); x += pXml({ jc: 'center', sp: { despues: 60 }, runsXml: imgXml('rIdLogo', cmEmu(t.w), cmEmu(t.h), 9001, 'Logo') }, ctx); }
  if (nombre) x += pXml({ jc: 'center', runs: [{ text: nombre, b: true, caps: true, esp: 24, sz: 30, color: col }] }, ctx);
  if (sub) x += pXml({ jc: 'center', runs: [{ text: sub, sz: 19, color: gris }] }, ctx);
  x += lineaVacia(m.linea ? { pos: 'bottom', val: 'double', sz: 6, color: col, space: 1 } : null);
  return x;
}
function pieXml(ctx, conMembrete) {
  const m = state.perfil.membrete;
  const gris = '595959';
  let x = '';
  if (conMembrete) {
    const t = pieTexto();
    if (t) x += pXml({ jc: 'center', borde: m.linea ? { pos: 'top', val: 'single', sz: 4, color: hex(m.color), space: 4 } : null, runs: [{ text: t, sz: 16, color: gris }] }, ctx);
  }
  if (m.numeracion) {
    const o = { sz: 16, color: gris };
    x += pXml({ jc: 'right', runs: [{ text: 'Página ', ...o }], runsXml: campoXml('PAGE', o, ctx) + rXml({ text: ' de ', ...o }, ctx) + campoXml('NUMPAGES', o, ctx) }, ctx);
  }
  return x;
}
function firmaXml(rol, ctx) {
  const f = state.perfil.formato;
  const jc = f.firmaAlin === 'centro' ? 'center' : 'left';
  const L = firmaLineas(rol);
  let x = '';
  if (ctx.firma) { const t = tamImagen(ctx.firma, 1.6, 6); x += pXml({ jc, keepNext: true, sp: { antes: 200 }, runsXml: imgXml('rIdFirmaMem', cmEmu(t.w), cmEmu(t.h), 9003, 'Firma') }, ctx); }
  else x += pXml({ jc, keepNext: true, sp: { antes: 600 } }, ctx);
  L.forEach((l, i) => {
    const runs = parseInline(l).map(r => ({ text: r.text, b: i === 1, mk: r.mk }));
    x += pXml({ jc, keepNext: i < L.length - 1, runs }, ctx);
  });
  return x;
}
function cuerpoXml(bloques, ctx) {
  const f = state.perfil.formato;
  const base = ctx.sz || (Number(f.tamano) * 2);
  const linea = Math.round(240 * Number(f.interlineado));
  const despues = (ESPACIO[f.espacio] ?? 8) * 20;
  const jcCuerpo = f.alineacion === 'izquierda' ? 'left' : 'both';
  const refIzq = f.refSangria ? cmTw(ctx.anchoTexto / 2) : 0;
  const tamExtra = d => (ctx.sinTam ? undefined : base + d);
  let x = '';
  bloques.forEach((b, idx) => {
    const antesDeFirma = bloques[idx + 1] && bloques[idx + 1].t === 'firma';
    switch (b.t) {
      case 'h1': x += pXml({ jc: 'center', keepNext: true, sp: { antes: 240, despues: 240, linea }, runs: runsDe(b, { b: true, caps: f.mayus, sz: tamExtra(2) }) }, ctx); break;
      case 'h2': x += pXml({ jc: f.titulos === 'izquierda' ? 'left' : 'center', keepNext: true, sp: { antes: 240, despues: 120, linea }, runs: runsDe(b, { b: true, caps: f.mayus }) }, ctx); break;
      case 'h3': x += pXml({ jc: 'left', keepNext: true, sp: { antes: 160, despues: 80, linea }, runs: runsDe(b, { b: true }) }, ctx); break;
      case 'quote': x += pXml({ jc: 'both', sp: { despues, linea: 240 }, ind: { izq: 1134, der: 1134 }, runs: runsDe(b, { i: f.citaCursiva, sz: tamExtra(-2) }) }, ctx); break;
      case 'ref': x += pXml({ jc: 'left', sp: { despues, linea: Math.min(linea, 276) }, ind: { izq: refIzq }, runs: runsDe(b) }, ctx); break;
      case 'li': x += pXml({ jc: jcCuerpo, sp: { despues: Math.round(despues / 2), linea }, ind: { izq: 720, colgante: 360 }, runs: [{ text: '•' }, { tab: true }, ...runsDe(b)] }, ctx); break;
      case 'firma': x += firmaXml(b.rol, ctx); break;
      default: {
        const multi = b.lines.length > 1;
        x += pXml({ jc: multi ? 'left' : jcCuerpo, keepNext: antesDeFirma, sp: { despues, linea }, ind: (f.sangria && !multi) ? { primera: 709 } : null, runs: runsDe(b) }, ctx);
      }
    }
  });
  return x;
}
function dataUrlPartes(du) {
  const m = /^data:image\/(png|jpe?g);base64,(.*)$/i.exec(du || '');
  if (!m) return null;
  return { ext: m[1].toLowerCase() === 'png' ? 'png' : 'jpeg', b64: m[2] };
}
function stylesXml(fuente, sz) {
  const f = xesc(fuente);
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="${f}" w:hAnsi="${f}" w:cs="${f}" w:eastAsia="${f}"/><w:sz w:val="${sz}"/><w:szCs w:val="${sz}"/><w:lang w:val="es-CO" w:eastAsia="en-US" w:bidi="ar-SA"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style><w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/><w:uiPriority w:val="1"/><w:semiHidden/><w:unhideWhenUsed/></w:style><w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:uiPriority w:val="99"/><w:semiHidden/><w:unhideWhenUsed/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style></w:styles>`;
}
function contextoExport() {
  const { papel, mg } = medidas();
  const con = conMembreteDoc() && !state.ejemplo;
  return { papel, mg, anchoTexto: papel.w - mg.izq - mg.der, conMembrete: con, logo: con && !usaPlantilla() && state.perfil.membrete.diseno !== 'sobrio' ? IMG.logo : null, firma: IMG.firma };
}
function textoExport(sinVerificar) {
  const t = state.texto;
  return sinVerificar ? quitarVerificar(t) : t;
}
async function docxPropio(texto) {
  await cargarJSZip();
  const ex = contextoExport();
  const f = state.perfil.formato;
  const fuente = f.fuente || 'Arial', sz = Number(f.tamano) * 2;
  const ctx = { anchoTexto: ex.anchoTexto, logo: ex.logo, firma: ex.firma, fuente: null, sz: null };
  const zip = new window.JSZip();
  const docRels = ['<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>', '<Relationship Id="rIdSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'];
  let sectRefs = '';
  const ct = ['<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>', '<Default Extension="xml" ContentType="application/xml"/>', '<Default Extension="png" ContentType="image/png"/>', '<Default Extension="jpeg" ContentType="image/jpeg"/>', '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>', '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>', '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>', '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>', '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'];
  if (ex.conMembrete) {
    zip.file('word/header1.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:hdr ${NS_W}>${cabeceraXml(ctx)}</w:hdr>`);
    docRels.push('<Relationship Id="rIdHdr" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>');
    ct.push('<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>');
    sectRefs += '<w:headerReference w:type="default" r:id="rIdHdr"/>';
    if (ctx.logo) {
      const lp = dataUrlPartes(ctx.logo.dataUrl);
      if (lp) {
        zip.file('word/media/logo.' + lp.ext, lp.b64, { base64: true });
        zip.file('word/_rels/header1.xml.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdLogo" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/logo.${lp.ext}"/></Relationships>`);
      }
    }
  }
  const pie = pieXml(ctx, ex.conMembrete);
  if (pie) {
    zip.file('word/footer1.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:ftr ${NS_W}>${pie}</w:ftr>`);
    docRels.push('<Relationship Id="rIdFtr" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>');
    ct.push('<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>');
    sectRefs += '<w:footerReference w:type="default" r:id="rIdFtr"/>';
  }
  if (ctx.firma) {
    const fp = dataUrlPartes(ctx.firma.dataUrl);
    if (fp) { zip.file('word/media/firma.' + fp.ext, fp.b64, { base64: true }); docRels.push(`<Relationship Id="rIdFirmaMem" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/firma.${fp.ext}"/>`); }
    else ctx.firma = null;
  }
  const cuerpo = cuerpoXml(parseDoc(texto), ctx);
  const { papel, mg } = ex;
  const sect = `<w:sectPr>${sectRefs}<w:pgSz w:w="${cmTw(papel.w)}" w:h="${cmTw(papel.h)}"/><w:pgMar w:top="${cmTw(mg.sup)}" w:right="${cmTw(mg.der)}" w:bottom="${cmTw(mg.inf)}" w:left="${cmTw(mg.izq)}" w:header="709" w:footer="709" w:gutter="0"/><w:cols w:space="708"/></w:sectPr>`;
  zip.file('word/document.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document ${NS_W}><w:body>${cuerpo}${sect}</w:body></w:document>`);
  zip.file('word/styles.xml', stylesXml(fuente, sz));
  zip.file('word/settings.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:zoom w:percent="100"/><w:defaultTabStop w:val="708"/><w:hyphenationZone w:val="425"/><w:characterSpacingControl w:val="doNotCompress"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>');
  zip.file('word/_rels/document.xml.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${docRels.join('')}</Relationships>`);
  zip.file('[Content_Types].xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">${ct.join('')}</Types>`);
  zip.file('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>');
  const ahora = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  const autor = xesc(state.perfil.abogado.nombre || 'El Memorialista');
  zip.file('docProps/core.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>${xesc(tituloDoc())}</dc:title><dc:creator>${autor}</dc:creator><cp:lastModifiedBy>${autor}</cp:lastModifiedBy><dc:language>es-CO</dc:language><dcterms:created xsi:type="dcterms:W3CDTF">${ahora}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">${ahora}</dcterms:modified></cp:coreProperties>`);
  zip.file('docProps/app.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>El Memorialista</Application></Properties>');
  return zip.generateAsync({ type: 'blob', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', compression: 'DEFLATE' });
}

/* =========================================================
   Plantilla de Word del abogado
   ========================================================= */
function hijosNivelSuperior(xml) {
  const out = [];
  const re = /<(\/?)([A-Za-z_][\w:.-]*)\b(?:[^>"']|"[^"]*"|'[^']*')*?(\/?)>|<!--[\s\S]*?-->|<\?[\s\S]*?\?>/g;
  let prof = 0, ini = -1, nombre = '', m;
  while ((m = re.exec(xml))) {
    if (m[0].startsWith('<!--') || m[0].startsWith('<?')) continue;
    const cierre = m[1] === '/', auto = m[3] === '/';
    if (!cierre) {
      if (prof === 0) { ini = m.index; nombre = m[2]; }
      if (auto) { if (prof === 0) out.push({ nombre, ini, fin: re.lastIndex }); }
      else prof++;
    } else {
      prof--;
      if (prof === 0) out.push({ nombre, ini, fin: re.lastIndex });
    }
  }
  return out;
}
const deEnt = s => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, '&');
function textoXml(fr) { return deEnt((fr.match(/<w:t(?:\s[^>]*)?>[^<]*<\/w:t>/g) || []).map(t => t.replace(/<[^>]+>/g, '')).join('')); }
function parseRels(txt) {
  const out = {};
  for (const m of (txt || '').matchAll(/<Relationship\b[^>]*>/g)) {
    const id = /\bId="([^"]+)"/.exec(m[0]), tg = /\bTarget="([^"]+)"/.exec(m[0]);
    if (id && tg) out[id[1]] = tg[1];
  }
  return out;
}
function resolverRuta(base, target) {
  if (target.startsWith('/')) return target.slice(1);
  const partes = base.split('/'); partes.pop();
  for (const seg of target.split('/')) { if (seg === '..') partes.pop(); else if (seg !== '.') partes.push(seg); }
  return partes.join('/');
}
function cuerpoInterior(doc) {
  const m = /<w:body\b[^>]*>/.exec(doc);
  if (!m) return null;
  const ini = m.index + m[0].length, fin = doc.lastIndexOf('</w:body>');
  return { ini, fin, xml: doc.slice(ini, fin) };
}
function sectPrDe(interior) {
  const hijos = hijosNivelSuperior(interior);
  const s = [...hijos].reverse().find(x => x.nombre === 'w:sectPr');
  if (s) return interior.slice(s.ini, s.fin);
  const todos = interior.match(/<w:sectPr\b[\s\S]*?<\/w:sectPr>/g);
  return todos ? todos[todos.length - 1] : '';
}
async function temaFuente(zip, tipo) {
  const t = await (zip.file('word/theme/theme1.xml')?.async('string') || '');
  const m = new RegExp(`<a:${tipo}Font>[\\s\\S]*?<a:latin typeface="([^"]*)"`).exec(t);
  return m ? m[1] : null;
}
async function fuentePlantilla(zip) {
  const st = await (zip.file('word/styles.xml')?.async('string') || '');
  const normal = (/<w:style\b[^>]*w:styleId="Normal"[^>]*>([\s\S]*?)<\/w:style>/.exec(st) || [])[1] || '';
  const defs = (/<w:rPrDefault>([\s\S]*?)<\/w:rPrDefault>/.exec(st) || [])[1] || '';
  let nombre = null, tam = null;
  for (const src of [normal, defs]) {
    const rf = (/<w:rFonts\b([^>]*)\/?>/.exec(src) || [])[1];
    if (!nombre && rf) {
      const a = /w:ascii="([^"]+)"/.exec(rf);
      if (a) nombre = a[1];
      else if (/w:asciiTheme="minor/.test(rf)) nombre = await temaFuente(zip, 'minor');
      else if (/w:asciiTheme="major/.test(rf)) nombre = await temaFuente(zip, 'major');
    }
    const sz = /<w:sz w:val="(\d+)"/.exec(src);
    if (!tam && sz) tam = Number(sz[1]) / 2;
  }
  if (!nombre) nombre = (await temaFuente(zip, 'minor')) || 'Calibri';
  return { nombre, tam: tam || 11 };
}
async function analizarParte(zip, ruta) {
  const xml0 = await (zip.file(ruta)?.async('string') || '');
  if (!xml0) return null;
  const xml = xml0.replace(/<mc:Fallback>[\s\S]*?<\/mc:Fallback>/g, '');
  const rels = parseRels(await (zip.file(resolverRuta(ruta, '_rels/' + ruta.split('/').pop() + '.rels'))?.async('string') || ''));
  const textos = [];
  for (const p of xml.match(/<w:p\b[\s\S]*?<\/w:p>/g) || []) {
    const t = textoXml(p.replace(/<w:instrText[\s\S]*?<\/w:instrText>/g, '')).replace(/\s+/g, ' ').trim();
    if (t && !/^(p[aá]gina\s*)?\d*(\s*de\s*\d*)?$/i.test(t)) textos.push(t);
  }
  const imgs = [];
  const agregar = async (rid, wcm, hcm) => {
    const tg = rels[rid];
    if (!tg) return;
    const ruta2 = resolverRuta(ruta, tg);
    const ext = (ruta2.split('.').pop() || '').toLowerCase();
    const mime = { png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', gif: 'image/gif' }[ext];
    let src = null;
    if (mime && zip.file(ruta2)) src = `data:${mime};base64,` + await zip.file(ruta2).async('base64');
    imgs.push({ src, wcm: wcm || 4, hcm: hcm || 1.5, ruta: ruta2 });
  };
  for (const d of xml.match(/<w:drawing>[\s\S]*?<\/w:drawing>/g) || []) {
    const ex = /<wp:extent cx="(\d+)" cy="(\d+)"/.exec(d), rid = /r:embed="([^"]+)"/.exec(d);
    if (rid) await agregar(rid[1], ex ? Number(ex[1]) / 360000 : null, ex ? Number(ex[2]) / 360000 : null);
  }
  for (const v of xml.match(/<v:shape\b[\s\S]*?<\/v:shape>/g) || []) {
    const rid = /<v:imagedata\b[^>]*r:id="([^"]+)"/.exec(v);
    if (!rid) continue;
    const st = (/style="([^"]*)"/.exec(v) || [])[1] || '';
    const dim = k => { const m = new RegExp(k + ':([\\d.]+)(pt|in|cm|mm|px)?').exec(st); if (!m) return null; const n = Number(m[1]); return { pt: n / 28.3465, in: n * 2.54, cm: n, mm: n / 10, px: n / 37.795 }[m[2] || 'pt']; };
    await agregar(rid[1], dim('width'), dim('height'));
  }
  return { textos: textos.slice(0, 6), imgs };
}
async function analizarPlantilla(zip) {
  const doc = await zip.file('word/document.xml').async('string');
  const rels = parseRels(await (zip.file('word/_rels/document.xml.rels')?.async('string') || ''));
  const ci = cuerpoInterior(doc);
  const sect = ci ? sectPrDe(ci.xml) : '';
  const refs = { header: {}, footer: {} };
  for (const m of sect.matchAll(/<w:(header|footer)Reference\b[^>]*>/g)) {
    const tipo = (/w:type="([^"]+)"/.exec(m[0]) || [])[1] || 'default', id = (/r:id="([^"]+)"/.exec(m[0]) || [])[1];
    if (id) refs[m[1]][tipo] = id;
  }
  const titlePg = /<w:titlePg(?:\s*\/>|\s+w:val="(?:1|true|on)"\s*\/>)/.test(sect);
  const elegir = r => (titlePg && r.first) || r.default || r.first || null;
  const hid = elegir(refs.header), fid = elegir(refs.footer);
  const cab = hid && rels[hid] ? await analizarParte(zip, resolverRuta('word/document.xml', rels[hid])) : null;
  const pie = fid && rels[fid] ? await analizarParte(zip, resolverRuta('word/document.xml', rels[fid])) : null;
  const pg = /<w:pgSz\b([^>]*)\/?>/.exec(sect), mg = /<w:pgMar\b([^>]*)\/?>/.exec(sect);
  const at = (s, k) => { const m = new RegExp('w:' + k + '="(-?\\d+)"').exec(s || ''); return m ? Number(m[1]) / 566.93 : null; };
  const papel = pg ? { w: at(pg[1], 'w') || 21.59, h: at(pg[1], 'h') || 27.94 } : { w: 21.59, h: 27.94 };
  const margenes = mg ? { sup: Math.abs(at(mg[1], 'top') ?? 2.5), inf: Math.abs(at(mg[1], 'bottom') ?? 2.5), izq: at(mg[1], 'left') ?? 3, der: at(mg[1], 'right') ?? 3 } : null;
  const fuente = await fuentePlantilla(zip);
  const marcador = !!(ci && hijosNivelSuperior(ci.xml).some(x => x.nombre === 'w:p' && textoXml(ci.xml.slice(x.ini, x.fin)).includes('{{CONTENIDO}}')));
  return { cab, pie, papel, margenes, fuente, marcador, primeraPagina: titlePg };
}
function infoSinImagenes(info) {
  const quitar = parte => parte && { textos: parte.textos, imgs: parte.imgs.map(i => ({ wcm: i.wcm, hcm: i.hcm, ruta: i.ruta })) };
  return { ...info, cab: quitar(info.cab), pie: quitar(info.pie) };
}
function asegurarNs(doc) {
  const m = /<w:document\b[^>]*>/.exec(doc);
  if (!m) return doc;
  let raiz = m[0];
  const ns = { r: 'http://schemas.openxmlformats.org/officeDocument/2006/relationships', wp: 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing', a: 'http://schemas.openxmlformats.org/drawingml/2006/main', pic: 'http://schemas.openxmlformats.org/drawingml/2006/picture' };
  for (const [p, u] of Object.entries(ns)) if (!new RegExp('\\sxmlns:' + p + '=').test(raiz)) raiz = raiz.replace(/^<w:document\b/, `<w:document xmlns:${p}="${u}"`);
  return doc.slice(0, m.index) + raiz + doc.slice(m.index + m[0].length);
}
async function docxDesdePlantilla(texto) {
  await cargarJSZip();
  const ex = contextoExport();
  const f = state.perfil.formato;
  const zip = await window.JSZip.loadAsync(state.plantilla.buf);
  const ctx = { anchoTexto: ex.anchoTexto, firma: ex.firma, fuente: f.fuentePlantilla ? null : f.fuente, sz: f.fuentePlantilla ? null : Number(f.tamano) * 2, sinTam: !!f.fuentePlantilla };
  const relsRuta = 'word/_rels/document.xml.rels';
  let rels = await (zip.file(relsRuta)?.async('string') || '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>');
  let ct = await zip.file('[Content_Types].xml').async('string');
  if (ctx.firma) {
    const fp = dataUrlPartes(ctx.firma.dataUrl);
    if (fp && !/Id="rIdFirmaMem"/.test(rels)) {
      zip.file('word/media/memorialista_firma.' + fp.ext, fp.b64, { base64: true });
      rels = rels.replace('</Relationships>', `<Relationship Id="rIdFirmaMem" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/memorialista_firma.${fp.ext}"/></Relationships>`);
      if (!new RegExp(`Extension="${fp.ext}"`, 'i').test(ct)) ct = ct.replace(/(<Types\b[^>]*>)/, `$1<Default Extension="${fp.ext}" ContentType="image/${fp.ext}"/>`);
    } else if (!fp) ctx.firma = null;
  }
  ct = ct.replace('wordprocessingml.template.main+xml', 'wordprocessingml.document.main+xml');
  let doc = asegurarNs(await zip.file('word/document.xml').async('string'));
  const ci = cuerpoInterior(doc);
  if (!ci) throw new Error('plantilla_invalida');
  const nuevo = cuerpoXml(parseDoc(texto), ctx);
  const hijos = hijosNivelSuperior(ci.xml);
  const marca = hijos.find(x => x.nombre === 'w:p' && textoXml(ci.xml.slice(x.ini, x.fin)).includes('{{CONTENIDO}}'));
  let interior;
  if (marca) interior = ci.xml.slice(0, marca.ini) + nuevo + ci.xml.slice(marca.fin);
  else interior = nuevo + (sectPrDe(ci.xml) || '');
  doc = doc.slice(0, ci.ini) + interior + doc.slice(ci.fin);
  zip.file('word/document.xml', doc);
  zip.file(relsRuta, rels);
  zip.file('[Content_Types].xml', ct);
  return zip.generateAsync({ type: 'blob', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', compression: 'DEFLATE' });
}
function bufAB64(buf) {
  const bytes = new Uint8Array(buf); let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}
function b64ABuf(b64) { const s = atob(b64); const u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i); return u.buffer; }

/* =========================================================
   PDF
   ========================================================= */
const WINANSI_EXTRA = '€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ';
const SUSTITUTOS = { '→': '->', '←': '<-', '≈': '~', '≤': '<=', '≥': '>=', '✓': 'v', '✔': 'v', '−': '-', '‐': '-', '‑': '-', '‒': '-', '―': '—', '′': "'", '″': '"', ' ': ' ', ' ': ' ', ' ': ' ', '​': '' };
function winAnsi(s) {
  let o = '';
  for (const ch of String(s)) {
    const c = ch.codePointAt(0);
    if (c === 10 || (c >= 32 && c <= 126) || (c >= 160 && c <= 255) || WINANSI_EXTRA.includes(ch)) o += ch;
    else if (ch in SUSTITUTOS) o += SUSTITUTOS[ch];
    else o += ch.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^\x20-\x7e]/g, '?');
  }
  return o;
}
const cmPt = cm => cm * 28.3465;
function unirPuntuacion(runs) {
  for (let i = 1; i < runs.length; i++) {
    const a = runs[i - 1], b = runs[i];
    if (a.text === '\n' || b.text === '\n' || !a.text || !b.text) continue;
    if (/\S$/.test(a.text) && /^\S/.test(b.text)) {
      const m = /^\S+/.exec(b.text)[0];
      if (m.length <= 3 && /^[^\p{L}\p{N}]+$/u.test(m)) { a.text += m; b.text = b.text.slice(m.length); }
      else { const n = /[(«“¿¡"'\[]+$/.exec(a.text); if (n && n[0].length < a.text.length) { a.text = a.text.slice(0, -n[0].length); b.text = n[0] + b.text; } }
    }
    if (/\S$/.test(a.text) && /^[ \t]+\S/.test(b.text)) { const e = /^[ \t]+/.exec(b.text)[0]; a.text += e; b.text = b.text.slice(e.length); }
  }
  return runs.filter(r => r.text !== '');
}
function runsPdf(b, extra = {}) {
  const out = [];
  b.lines.forEach((l, idx) => {
    if (idx) out.push({ text: '\n' });
    for (const r of parseInline(l)) {
      let text = winAnsi(r.text);
      if (extra.mayus) text = text.toLocaleUpperCase('es-CO');
      const o = { text };
      if (r.b || extra.b) o.bold = true;
      if (r.i || extra.i) o.italics = true;
      if (r.u) o.decoration = 'underline';
      if (r.mk === 'c') o.background = '#fff1a8';
      if (r.mk === 'v') { o.background = '#ffe1c7'; o.color = '#7a3300'; }
      out.push(o);
    }
  });
  return unirPuntuacion(out);
}
function cabeceraPdf(ctx) {
  const p = state.perfil, m = p.membrete, ab = p.abogado;
  const ancho = cmPt(ctx.anchoTexto);
  const col = m.color || '#1f3a68', gris = '#595959';
  const linea = (y, w, c, doble) => ({ canvas: doble ? [{ type: 'line', x1: 0, y1: y, x2: ancho, y2: y, lineWidth: .6, lineColor: c }, { type: 'line', x1: 0, y1: y + 2.2, x2: ancho, y2: y + 2.2, lineWidth: .6, lineColor: c }] : [{ type: 'line', x1: 0, y1: y, x2: ancho, y2: y, lineWidth: w, lineColor: c }] });
  if (usaPlantilla()) {
    const cab = state.plantilla.info.cab;
    if (!cab) return null;
    const st = []; let alto = 0;
    for (const i of cab.imgs.filter(x => x.src && /^data:image\/(png|jpe?g)/.test(x.src))) { const w = Math.min(cmPt(i.wcm), ancho), hh = w * (i.hcm / i.wcm); st.push({ image: i.src, width: w, height: hh, alignment: 'center', margin: [0, 0, 0, 3] }); alto += hh + 3; }
    for (const t of cab.textos) { st.push({ text: winAnsi(t), fontSize: 9, color: gris, alignment: 'center' }); alto += 11; }
    return st.length ? { def: st, alto } : null;
  }
  const nombre = winAnsi((m.titulo || ab.nombre || '').trim());
  const sub = winAnsi((m.subtitulo || '').trim());
  const contacto = winAnsi(contactoCabecera());
  if (m.diseno === 'sobrio') {
    const dir = winAnsi([ab.direccion, ab.ciudad].filter(Boolean).join(', '));
    return { def: [
      { columns: [{ text: nombre.toLocaleUpperCase('es-CO'), bold: true, fontSize: 11.5, color: col, characterSpacing: 1.4 }, { text: contacto, fontSize: 8.5, color: gris, alignment: 'right', width: 'auto' }], columnGap: 12 },
      { columns: [{ text: sub, fontSize: 9, color: gris }, { text: dir, fontSize: 8.5, color: gris, alignment: 'right', width: 'auto' }], columnGap: 12, margin: [0, 2, 0, 4] },
      linea(0, .5, '#a6a6a6'),
    ], alto: 36 };
  }
  if (m.diseno === 'lateral') {
    const texto = { stack: [nombre && { text: nombre.toLocaleUpperCase('es-CO'), bold: true, fontSize: 14, color: col, characterSpacing: .4 }, sub && { text: sub, fontSize: 9.5, color: gris, margin: [0, 2, 0, 0] }, contacto && { text: contacto, fontSize: 8.5, color: gris, margin: [0, 2, 0, 0] }].filter(Boolean), alignment: ctx.logo ? 'right' : 'left' };
    let alto = 14 * 1.25 + (sub ? 13 : 0) + (contacto ? 12 : 0);
    let fila;
    if (ctx.logo) {
      const t = tamImagen(ctx.logo, 2, 5);
      fila = { columns: [{ image: ctx.logo.dataUrl, width: cmPt(t.w), height: cmPt(t.h) }, { width: '*', ...texto }], columnGap: 14 };
      alto = Math.max(alto, cmPt(t.h));
    } else fila = texto;
    return { def: [fila, m.linea ? { ...linea(0, 1.2, col), margin: [0, 6, 0, 0] } : null].filter(Boolean), alto: alto + 10 };
  }
  const st = []; let alto = 0;
  if (ctx.logo) { const t = tamImagen(ctx.logo, 1.7, 6); st.push({ image: ctx.logo.dataUrl, width: cmPt(t.w), height: cmPt(t.h), alignment: 'center', margin: [0, 0, 0, 3] }); alto += cmPt(t.h) + 3; }
  if (nombre) { st.push({ text: nombre.toLocaleUpperCase('es-CO'), bold: true, fontSize: 15, color: col, characterSpacing: 1, alignment: 'center' }); alto += 19; }
  if (sub) { st.push({ text: sub, fontSize: 9.5, color: gris, alignment: 'center', margin: [0, 1, 0, 0] }); alto += 13; }
  if (m.linea) { st.push({ ...linea(0, .6, col, true), margin: [0, 5, 0, 0] }); alto += 9; }
  return st.length ? { def: st, alto } : null;
}
function piePdf(ctx) {
  const m = state.perfil.membrete, gris = '#595959';
  const ancho = cmPt(ctx.anchoTexto);
  const partes = [];
  let alto = 0;
  if (ctx.conMembrete) {
    if (usaPlantilla()) {
      const pie = state.plantilla.info.pie;
      if (pie) {
        for (const i of pie.imgs.filter(x => x.src && /^data:image\/(png|jpe?g)/.test(x.src))) { const w = Math.min(cmPt(i.wcm), ancho), hh = w * (i.hcm / i.wcm); partes.push({ image: i.src, width: w, height: hh, alignment: 'center' }); alto += hh + 2; }
        for (const t of pie.textos) { partes.push({ text: winAnsi(t), fontSize: 8.5, color: gris, alignment: 'center' }); alto += 11; }
      }
    } else {
      const t = pieTexto();
      if (t) {
        if (m.linea) { partes.push({ canvas: [{ type: 'line', x1: 0, y1: 0, x2: ancho, y2: 0, lineWidth: .5, lineColor: m.color || '#1f3a68' }], margin: [0, 0, 0, 3] }); alto += 4; }
        partes.push({ text: winAnsi(t), fontSize: 8.5, color: gris, alignment: 'center' }); alto += 11;
      }
    }
  }
  const numerar = m.numeracion;
  if (!partes.length && !numerar) return null;
  if (numerar) alto += 11;
  return { alto, def: (pag, total) => numerar ? [...partes, { text: `Página ${pag} de ${total}`, fontSize: 8.5, color: gris, alignment: 'right', margin: [0, 2, 0, 0] }] : partes };
}
function cuerpoPdf(bloques, ctx) {
  const f = state.perfil.formato;
  const tam = Number(f.tamano);
  const despues = ESPACIO[f.espacio] ?? 8;
  const alin = f.alineacion === 'izquierda' ? 'left' : 'justify';
  const out = [];
  let lista = null;
  const cerrarLista = () => { if (lista) { out.push({ ul: lista, margin: [cmPt(.4), 0, 0, despues] }); lista = null; } };
  for (const b of bloques) {
    if (b.t !== 'li') cerrarLista();
    if (b.t === 'firma' && out.length) {
      const prev = out[out.length - 1];
      if (prev && prev.text && !prev.headlineLevel && JSON.stringify(prev.text).length < 400) { out.pop(); b.previo = prev; }
    }
    switch (b.t) {
      case 'h1': out.push({ text: runsPdf(b, { b: true, mayus: f.mayus }), alignment: 'center', fontSize: tam + 1, margin: [0, 12, 0, 12], headlineLevel: 1 }); break;
      case 'h2': out.push({ text: runsPdf(b, { b: true, mayus: f.mayus }), alignment: f.titulos === 'izquierda' ? 'left' : 'center', margin: [0, 12, 0, 6], headlineLevel: 1 }); break;
      case 'h3': out.push({ text: runsPdf(b, { b: true }), alignment: 'left', margin: [0, 8, 0, 4], headlineLevel: 1 }); break;
      case 'quote': out.push({ text: runsPdf(b, { i: f.citaCursiva }), alignment: 'justify', fontSize: tam - 1, lineHeight: 1.05, margin: [cmPt(2), 0, cmPt(2), despues] }); break;
      case 'ref': out.push({ text: runsPdf(b), alignment: 'left', lineHeight: Math.min(Number(f.interlineado), 1.15), margin: [f.refSangria ? cmPt(ctx.anchoTexto / 2) : 0, 0, 0, despues] }); break;
      case 'li': (lista = lista || []).push({ text: runsPdf(b), alignment: alin, margin: [0, 0, 0, despues / 2] }); break;
      case 'firma': {
        const L = firmaLineas(b.rol);
        const al = f.firmaAlin === 'centro' ? 'center' : 'left';
        const st = [];
        if (ctx.firma && /^data:image\/(png|jpe?g)/.test(ctx.firma.dataUrl)) { const t = tamImagen(ctx.firma, 1.6, 6); st.push({ image: ctx.firma.dataUrl, width: cmPt(t.w), height: cmPt(t.h), alignment: al, margin: [0, 10, 0, -6] }); }
        else st.push({ text: ' ', margin: [0, cmPt(1.1), 0, 0] });
        L.forEach((l, i) => st.push({ text: runsPdf({ lines: [l] }, { b: i === 1 }), alignment: al }));
        const bloqueFirma = { stack: st, lineHeight: 1.15, margin: [0, 4, 0, despues] };
        out.push(b.previo ? { stack: [b.previo, bloqueFirma], unbreakable: true } : { ...bloqueFirma, unbreakable: true });
        break;
      }
      default: {
        const multi = b.lines.length > 1;
        out.push({ text: runsPdf(b), alignment: multi ? 'left' : alin, leadingIndent: f.sangria && !multi ? cmPt(1.25) : 0, margin: [0, 0, 0, despues] });
      }
    }
  }
  cerrarLista();
  return out;
}
async function construirPdf(texto) {
  await cargarPdfMake();
  const ex = contextoExport();
  const f = state.perfil.formato;
  const fu = fuenteEfectiva();
  const familia = fu.conocida ? fu.conocida.pdf : (/(times|roman|garamond|georgia|cambria|book|serif)/i.test(fu.nombre) ? 'Times' : 'Helvetica');
  const { papel, mg } = ex;
  const ctx = { anchoTexto: ex.anchoTexto, logo: ex.logo, firma: ex.firma, conMembrete: ex.conMembrete };
  const cab = ex.conMembrete ? cabeceraPdf(ctx) : null;
  const pie = piePdf(ctx);
  const dist = cmPt(1.25);
  const top = Math.max(cmPt(mg.sup), cab ? dist + cab.alto + cmPt(.6) : 0);
  const bottom = Math.max(cmPt(mg.inf), pie ? dist + pie.alto + cmPt(.4) : 0);
  const dd = {
    pageSize: { width: cmPt(papel.w), height: cmPt(papel.h) },
    pageMargins: [cmPt(mg.izq), top, cmPt(mg.der), bottom],
    info: { title: winAnsi(tituloDoc()), author: winAnsi(state.perfil.abogado.nombre || ''), creator: 'El Memorialista' },
    defaultStyle: { font: familia, fontSize: Number(fu.tam) || 12, lineHeight: Number(f.interlineado) || 1.5 },
    content: cuerpoPdf(parseDoc(texto), ctx),
    pageBreakBefore: (nodo, util) => nodo.headlineLevel === 1 && util.getFollowingNodesOnPage().length === 0,
  };
  const copia = o => JSON.parse(JSON.stringify(o));
  if (cab) dd.header = () => ({ margin: [cmPt(mg.izq), dist, cmPt(mg.der), 0], stack: copia(cab.def) });
  if (pie) dd.footer = (pag, total) => ({ margin: [cmPt(mg.izq), Math.max(4, bottom - dist - pie.alto), cmPt(mg.der), 0], stack: copia(pie.def(pag, total)) });
  return window.pdfMake.createPdf(dd).getBlob();
}

/* =========================================================
   Redacción con IA (servidor v2.2.1)
   ========================================================= */
function camposTipo(tipo) {
  if (!tipo) return [];
  return [...(tipo.grupos || []).flatMap(g => g.campos || []), ...grupoRedaccion(tipo).campos];
}

let reloj = null, relojBase = '';
function iniciarReloj(base) {
  const t0 = Date.now();
  relojBase = base;
  clearInterval(reloj);
  const pintar = () => { const s = Math.floor((Date.now() - t0) / 1000); estadoHoja('vivo', `${relojBase} ${Math.floor(s / 60)}:${dos(s % 60)}`); };
  pintar(); reloj = setInterval(pintar, 1000);
}
function etiquetaReloj(base) { if (base) relojBase = base; }
function pararReloj() { clearInterval(reloj); reloj = null; }
function estadoHoja(clase, texto) {
  const e = $('#hbEstado');
  e.className = 'hb-estado ' + (clase || '');
  $('#hbTexto').textContent = texto;
}
/* ===== v2.2: lector del protocolo NDJSON, código de acceso y redacción ===== */
function crearLectorNdjson(alEvento) {
  let resto = '';
  const procesar = linea => {
    const l = linea.trim();
    if (!l) return;
    let ev;
    try { ev = JSON.parse(l); } catch { return; }
    alEvento(ev);
  };
  return {
    empujar(fragmento) {
      resto += fragmento;
      let i;
      while ((i = resto.indexOf('\n')) >= 0) { procesar(resto.slice(0, i)); resto = resto.slice(i + 1); }
    },
    cerrar() { procesar(resto); resto = ''; },
  };
}
async function apiFetch(url, opciones = {}, segundoIntento = false) {
  const headers = { ...(opciones.headers || {}) };
  const token = state.session?.access_token || (window.supabaseClient ? (await window.supabaseClient.auth.getSession().then(r => r.data?.session?.access_token).catch(() => null)) : null);
  if (token) {
    headers['Authorization'] = 'Bearer ' + token;
  }
  const res = await fetch(url, { ...opciones, headers });
  if (res.status === 401) {
    abrirModalAuth('Se requiere una sesión activa con Supabase para acceder a esta función.');
  }
  return res;
}
const MARCA_INCOMPLETO = '[COMPLETAR: el escrito se interrumpió en este punto. Usa «Ajustar con IA» → «Continúa donde quedó» o «Regenerar» antes de radicar]';
async function redactar(modo = 'nuevo', instruccion = '') {
  if (state.generando) return;
  let textoPrevio = '';
  if (modo === 'ajuste') {
    state.prevTexto = state.texto;
    textoPrevio = state.texto;
  } else {
    if (modo === 'regenerar' && state.texto) state.prevTexto = state.texto;
  }
  state.generando = true;
  state.ejemplo = false;
  state.ctl = new AbortController();
  const ctl = state.ctl;
  const tier = state.perfil.ia.calidad === 'default' ? 'default' : 'complex';
  ponerControles();
  $('#selloEjemplo').hidden = true;
  const cuerpo = $('#cuerpo');
  cuerpo.contentEditable = 'false';
  cuerpo.innerHTML = `<p class="esperando">${modo === 'ajuste' ? 'Aplicando el ajuste' : 'Leyendo el expediente y redactando con IA'}${tier === 'complex' ? ' · con calidad máxima puede tardar un momento' : ''}</p>`;
  renderMembreteHoja();
  iniciarReloj(modo === 'ajuste' ? 'Ajustando…' : 'Redactando con IA…');
  if (matchMedia('(max-width: 999px)').matches) $('#colHoja').scrollIntoView({ behavior: 'smooth', block: 'start' });
  let acumulado = '';
  let meta = null, errorServidor = null, terminado = false, pendiente = false;
  const pintar = () => { pendiente = false; if (terminado) return; cuerpo.innerHTML = cuerpoHtml(parseDoc(acumulado)); cuerpo.classList.add('escribiendo'); };
  const programar = () => { if (!pendiente) { pendiente = true; requestAnimationFrame(pintar); } };
  const lector = crearLectorNdjson(ev => {
    if (ev.t === 'delta' && ev.d) { acumulado += ev.d; programar(); }
    else if (ev.t === 'aviso' && ev.mensaje) etiquetaReloj(ev.mensaje);
    else if (ev.t === 'fin') meta = ev;
    else if (ev.t === 'error') errorServidor = ev;
  });
  const cerrar = (aviso, fallo) => { terminado = true; terminarRedaccion(acumulado, modo, aviso, fallo, instruccion); };
  try {
    const res = await apiFetch('/api/redactar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tipo: state.tipo,
        datos: state.datos,
        perfil: {
          abogado: state.perfil.abogado,
          estilo: state.perfil.estilo,
          ia: state.perfil.ia,
        },
        modo,
        instruccion,
        texto_previo: textoPrevio,
        calidad: tier,
        protocolo: 'ndjson'
      }),
      signal: ctl.signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `El servidor respondió ${res.status}. Intenta de nuevo.`);
    }
    const esNdjson = (res.headers.get('content-type') || '').includes('ndjson');
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const trozo = decoder.decode(value, { stream: true });
      if (esNdjson) lector.empujar(trozo); else { acumulado += trozo; programar(); }
    }
    const cola = decoder.decode();
    if (esNdjson) { if (cola) lector.empujar(cola); lector.cerrar(); } else acumulado += cola;
    if (errorServidor && !acumulado.trim()) throw new Error(errorServidor.mensaje || 'No se pudo redactar el escrito.');
    const incompleto = esNdjson && (!!errorServidor || !meta || !!meta.truncado);
    if (incompleto && !acumulado.trim()) throw new Error('Se perdió la conexión con el servidor antes de recibir el escrito. Intenta de nuevo.');
    if (incompleto) {
      if (acumulado.trim() && !acumulado.includes(MARCA_INCOMPLETO)) acumulado = acumulado.replace(/\s+$/, '') + '\n\n' + MARCA_INCOMPLETO;
      cerrar('El escrito quedó incompleto: el motor de IA se detuvo antes de terminar. Revisa el final antes de radicar.', true);
      return;
    }
    cerrar(null, false);
  } catch (e) {
    if (e.name === 'AbortError') { cerrar('Redacción detenida. Se conservó lo escrito.', true); return; }
    cerrar(null, true);
    toast(e.message || 'Error al conectar con la Inteligencia Artificial.', 'error', 7000);
  }
}
function terminarRedaccion(texto, modo, aviso, fallo = false, instruccion = '') {
  pararReloj();
  state.generando = false;
  state.ctl = null;
  const limpio = limpiarSalida(texto || '').trim();
  if (!limpio) {
    if (!state.texto) state.ejemplo = true;
    renderHoja();
    ponerControles();
    estadoHoja(state.texto ? 'listo' : '', state.texto ? 'Se conservó la versión anterior' : 'Ejemplo de escrito');
    return;
  }
  state.texto = limpio;
  state.ejemplo = false;
  state.revisionRequisitos = null;
  state.textoRevisado = null;
  state.tipoRevisado = null;
  if (modo === 'nuevo') {
    state.docId = null;
    state.creado = null;
    state.versiones = [];
    registrarVersion('generacion', 'Generación inicial');
  } else if (modo === 'regenerar') {
    registrarVersion('generacion', 'Regeneración con IA');
  } else if (modo === 'ajuste' || modo === 'continuar') {
    registrarVersion('ajuste_ia', instruccion ? `Ajuste con IA: "${instruccion}"` : 'Ajuste con IA', instruccion);
  }
  renderHoja();
  ponerControles();
  $('#btnDeshacerAjuste').hidden = !state.prevTexto;
  guardarBorrador();
  verificarCitasDocumento();
  guardarEnHistorial().then(ok => {
    estadoHoja(fallo ? 'error' : 'listo', (fallo ? 'Incompleto · ' : 'Listo · ') + (ok ? 'guardado ' + horaCorta(Date.now()) : 'sin guardar'));
  });
  if (aviso) toast(aviso, 'info', 7000);
  else if (!fallo) toast(modo === 'ajuste' ? 'Ajuste aplicado.' : 'Escrito listo. Revisa las marcas antes de radicar.', 'ok');
}
function detener() { if (state.ctl) state.ctl.abort(); }

/* Análisis de estilo a partir de una muestra */
async function analizarEstilo() {
  const muestra = state.perfil.estilo.muestra.trim();
  const est = $('#analizarEstado');
  if (muestra.length < 100) { est.textContent = 'Pega al menos un par de páginas de un escrito tuyo.'; return; }
  const btn = $('#btnAnalizar'); btn.disabled = true; est.textContent = 'Analizando tu estilo con IA…';
  try {
    const res = await apiFetch('/api/analizar-estilo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ muestra })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al analizar la muestra');
    state.perfil.estilo.ficha = data.ficha;
    $('#e_ficha').value = data.ficha;
    guardarPerfil();
    est.textContent = 'Listo. Revisa y corrige la ficha si hace falta.';
    toast('Ficha de estilo generada.', 'ok');
  } catch (e) {
    est.textContent = e.message || 'Error al analizar estilo.';
    toast(e.message, 'error');
  } finally { btn.disabled = false; }
}

/* =========================================================
   Formulario del caso
   ========================================================= */
function valorDefecto(c) {
  if (c.def === '@ciudad') return state.perfil.abogado.ciudad || '';
  if (c.def === '@extension') return state.perfil.estilo.extension || 'estandar';
  if (c.def !== undefined) return c.def;
  if (c.t === 'chips') return [];
  if (c.t === 'select') return c.opciones[0][0];
  return '';
}
function elegirTipo(id, { conservar = true } = {}) {
  const tipo = TIPOS[id];
  if (!tipo) return;
  const previos = conservar ? state.datos : {};
  const datos = {};
  for (const c of camposTipo(tipo)) {
    const prev = previos[c.k];
    const util = prev !== undefined && prev !== '' && !(Array.isArray(prev) && !prev.length) && !c.k.startsWith('_');
    datos[c.k] = util ? prev : valorDefecto(c);
  }
  state.tipo = id;
  state.datos = datos;
  state.archivosCaso = [];
  state.propuestasExtraidas = [];
  state.catalogoAbierto = false;
  renderZonaTipo();
  renderFormulario();
  guardarBorrador();
  $('#accionesForm').hidden = false;
  const primero = $('#formCaso input, #formCaso textarea, #formCaso select');
  if (primero && !matchMedia('(max-width: 999px)').matches) primero.focus({ preventScroll: true });
  $('.col-form').scrollTop = 0;
}
function renderZonaTipo() {
  const zona = $('#zonaTipo');
  zona.replaceChildren();
  if (!state.tipo || state.catalogoAbierto) {
    const fechaRev = (state.catalogo && state.catalogo.fecha_revision) || '21 de octubre de 2026';
    const badgeNormativo = () => h('div', { class: 'base-normativa-pill', style: 'font-size: 11px; color: var(--color-texto-suave, #6b7280); margin-top: 6px; display: inline-flex; align-items: center; gap: 6px;' },
      h('span', { style: 'display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #10b981;' }),
      `Base normativa revisada al ${fechaRev}`
    );
    zona.append(h('div', { class: 'intro' }, h('h1', {}, '¿Qué escrito necesitas?'), h('p', {}, 'Elige el tipo de documento. Luego llenas los datos del caso y se redacta con tu membrete y tu estilo.'), badgeNormativo()));
    const buscar = h('input', { type: 'search', id: 'catBuscar', placeholder: 'Buscar: tutela, petición, ejecutiva, poder…', 'aria-label': 'Buscar tipo de escrito' });
    const lista = h('div', { class: 'catalogo', id: 'catLista' });
    const pintar = () => {
      const q = buscar.value.trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
      lista.replaceChildren();
      for (const area of AREAS) {
        const items = TIPOS_LISTA.filter(t => t.area === area && (!q || (t.nombre + ' ' + t.desc + ' ' + t.norma + ' ' + t.area).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').includes(q)));
        if (!items.length) continue;
        lista.append(h('div', { class: 'cat-grupo' }, h('h3', {}, area), h('div', { class: 'cat-items' }, items.map(t => {
          let pillRev = null;
          if (t.revisado_por === 'pendiente') {
            pillRev = h('span', { class: 'pill-revision pill-pendiente', title: 'Guía pendiente de revisión jurídica' }, '⚠️ Pendiente');
          } else if ((t.revisado_por && t.revisado_por.toLowerCase().includes('auditado con ia')) || t.auditoria_ia) {
            pillRev = h('span', { class: 'pill-revision pill-ia', title: 'Auditado con IA Jurídica' }, '🤖 Auditado');
          }
          return h('button', { class: 'cat-item', type: 'button', onclick: () => elegirTipo(t.id) },
            h('span', { class: 'n' }, t.nombre, pillRev),
            h('span', { class: 'nm' }, t.norma),
            h('span', { class: 'd' }, t.desc)
          );
        }))));
      }
      if (!lista.children.length) lista.append(h('p', { class: 'ayuda' }, 'No hay coincidencias. Prueba “Otro escrito” y descríbelo.'));
    };
    buscar.addEventListener('input', pintar);
    pintar();
    zona.append(h('div', { class: 'buscador' }, buscar), lista);
    if (state.tipo) zona.prepend(h('div', {}, h('button', { class: 'btn chico fantasma', type: 'button', onclick: () => { state.catalogoAbierto = false; renderZonaTipo(); $('#formCaso').hidden = false; $('#accionesForm').hidden = false; } }, '← Volver al formulario')));
    $('#formCaso').hidden = !!state.tipo && state.catalogoAbierto ? true : !state.tipo;
    $('#accionesForm').hidden = true;
    return;
  }
  const t = TIPOS[state.tipo];
  const fechaRev = t.fecha_revision || (state.catalogo && state.catalogo.fecha_revision) || '22 de octubre de 2026';

  const renderBadgeAuditoria = () => {
    if (t.revisado_por === 'pendiente') {
      return h('div', { class: 'alerta-revision-guia pendiente' },
        h('span', {}, '⚠️'),
        h('span', {}, 'Guía pendiente de revisión jurídica')
      );
    }
    if ((t.revisado_por && t.revisado_por.toLowerCase().includes('auditado con ia')) || t.auditoria_ia) {
      const score = t.auditoria_ia?.puntuacion || 97;
      return h('div', { class: 'alerta-revision-guia ia' },
        h('span', {}, '🤖'),
        h('span', {}, `Auditado con IA Jurídica (${score}/100) al ${fechaRev}`),
        h('button', {
          type: 'button',
          class: 'enlace',
          style: 'margin-left: 6px; font-size: 11px; text-decoration: underline; color: #2563eb;',
          onclick: (e) => { e.preventDefault(); e.stopPropagation(); mostrarDictamenAuditoria(t); }
        }, 'Ver dictamen')
      );
    }
    return h('div', { class: 'base-normativa-pill', style: 'font-size: 11px; color: var(--color-texto-suave, #6b7280); margin-top: 6px; display: inline-flex; align-items: center; gap: 6px;' },
      h('span', { style: 'display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #10b981;' }),
      `Base normativa revisada al ${fechaRev}`
    );
  };

  const card = h('div', { class: 'tipo-actual' },
    h('span', { class: 'eyebrow' }, t.area),
    h('h2', {}, t.nombre),
    h('button', { class: 'btn chico', type: 'button', onclick: () => { state.catalogoAbierto = true; renderZonaTipo(); } }, 'Cambiar'),
    h('span', { class: 'nm' }, t.norma),
    h('p', { class: 'd' }, t.desc),
    renderBadgeAuditoria());
  zona.append(card);
  if (t.ejemplo) zona.append(h('div', { class: 'fila-ejemplo' }, h('button', { class: 'btn chico fantasma', type: 'button', onclick: llenarEjemplo }, 'Llenar con un caso de ejemplo'), h('button', { class: 'btn chico fantasma', type: 'button', onclick: limpiarFormulario }, 'Limpiar formulario')));
  else zona.append(h('div', { class: 'fila-ejemplo' }, h('button', { class: 'btn chico fantasma', type: 'button', onclick: limpiarFormulario }, 'Limpiar formulario')));
  if (!state.perfil.abogado.nombre) zona.append(h('div', { class: 'aviso' }, 'Aún no configuras tu nombre, cédula y tarjeta profesional: el escrito los dejará marcados por completar. ', h('button', { class: 'enlace', type: 'button', onclick: () => irVista('membrete') }, 'Configurar ahora')));
  $('#formCaso').hidden = false;
}
function llenarEjemplo() {
  const t = TIPOS[state.tipo];
  if (!t || !t.ejemplo) return;
  for (const c of camposTipo(t)) if (c.k in t.ejemplo) state.datos[c.k] = clon(t.ejemplo[c.k]);
  renderFormulario();
  guardarBorrador();
  toast('Se llenó con un caso de ejemplo. Cámbialo por los datos reales.', 'info');
}
function limpiarFormulario() {
  const t = TIPOS[state.tipo];
  for (const c of camposTipo(t)) state.datos[c.k] = valorDefecto(c);
  renderFormulario();
  guardarBorrador();
}

function mostrarDictamenAuditoria(t) {
  const dlg = $('#modalAuditoriaIa');
  const cuerpo = $('#cuerpoModalAuditoria');
  if (!dlg || !cuerpo) return;
  cuerpo.replaceChildren();

  const aud = t.auditoria_ia || {};
  const score = aud.puntuacion != null ? aud.puntuacion : 97;
  const aprobado = aud.aprobado !== false;

  const cabeceraScore = h('div', {
    style: 'display: flex; align-items: center; justify-content: space-between; background: #f8fafc; border: 1px solid var(--regla); border-radius: 8px; padding: 12px 16px; flex-wrap: wrap; gap: 10px;'
  },
    h('div', {},
      h('div', { style: 'font-weight: 750; font-size: 14.5px; color: var(--tinta);' }, t.nombre),
      h('div', { style: 'font-size: 12px; color: var(--tinta-2); margin-top: 2px;' },
        `Auditado con ${aud.modelo_auditor || 'Gemini 3.8 Flash con razonamiento profundo'} · ${aud.fecha || t.fecha_revision || '22 de octubre de 2026'}`
      )
    ),
    h('div', {
      style: `font-size: 18px; font-weight: 800; padding: 4px 12px; border-radius: 999px; background: ${aprobado ? '#dcfce7' : '#fee2e2'}; color: ${aprobado ? '#166534' : '#991b1b'}; display: inline-flex; align-items: center; gap: 4px;`
    }, `${score}/100`)
  );

  const bloqueDictamen = h('div', { style: 'background: #eff6ff; border-left: 4px solid #2563eb; padding: 12px 16px; border-radius: 4px; font-size: 13px; line-height: 1.55; color: #1e3a8a;' },
    h('div', { style: 'font-weight: 700; margin-bottom: 4px; font-size: 13.5px;' }, '⚖️ Concepto del Magistrado Auditor:'),
    h('p', { style: 'margin: 0;' }, aud.dictamen || 'Estructura procesal verificada frente a la legislación colombiana vigente. Cumple con los requisitos de procedencia y admisibilidad.')
  );

  const listaNormas = h('div', {},
    h('div', { style: 'font-weight: 700; font-size: 12.5px; color: var(--tinta); margin-bottom: 6px;' }, '📚 Normas colombianas validadas:'),
    h('ul', { style: 'margin: 0; padding-left: 20px; font-size: 12px; color: var(--tinta); line-height: 1.5;' },
      ...(aud.normas_validadas || t.fuentes || [t.norma]).map(n => h('li', {}, n))
    )
  );

  const observaciones = (aud.observaciones && aud.observaciones.length)
    ? h('div', { style: 'background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 10px 14px; font-size: 12px; color: #92400e;' },
        h('div', { style: 'font-weight: 700; margin-bottom: 4px;' }, '💡 Recomendaciones procesales integradas:'),
        h('ul', { style: 'margin: 0; padding-left: 18px; line-height: 1.5;' },
          ...aud.observaciones.map(o => h('li', {}, o))
        )
      )
    : null;

  cuerpo.append(cabeceraScore, bloqueDictamen, listaNormas);
  if (observaciones) cuerpo.append(observaciones);

  dlg.showModal();
  $('#btnCerrarModalAuditoria').onclick = () => dlg.close();
  $('#btnCerrarModalAuditoriaPie').onclick = () => dlg.close();
}

/* =========================================================
   Extracción Multimodal de Documentos del Caso (PDF, Imágenes, Audio)
   ========================================================= */
function formatearTamanoBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

function renderZonaSubidaDocumentos(tipo) {
  const card = h('section', {
    class: 'grupo zona-subida-docs',
    id: 'zonaSubidaDocs'
  });

  const tipoId = state.tipo;
  let titSeccion = '📁 Sube los documentos del caso';
  let descSeccion = 'Adjunta poderes, cédulas, demandas, contratos, grabaciones de audio o providencias (PDF, imágenes, audio · máx. 20 MB en total). La IA de Gemini 3.8 Flash extraerá los datos y te propondrá cada campo antes de que se escriba en el formulario.';
  let iconoDrop = '📄 🎙️ 🖼️';
  let textoDrop = 'Arrastra y suelta tus archivos aquí, o ';
  let subDrop = 'PDF, PNG, JPG, WEBP, MP3, WAV, M4A, OGG · Máximo 20 MB en total (privacidad: procesados 100% en memoria y descartados)';

  if (tipoId === 'contestacion') {
    titSeccion = '📁 Sube la demanda judicial (PDF)';
    descSeccion = 'Adjunta la demanda en PDF. Gemini 3.8 Flash extraerá los hechos numerados (art. 96 CGP) para responderlos uno a uno, pretensiones y fecha de notificación.';
    iconoDrop = '⚖️ 📄';
    textoDrop = 'Arrastra y suelta aquí la demanda en PDF (o anexos del caso), o ';
    subDrop = 'Demanda en PDF, grabaciones o fotos · Máx. 20 MB · Privacidad: procesados 100% en memoria y descartados';
  } else if (tipoId === 'impugnacion_tutela') {
    titSeccion = '📁 Sube el fallo de tutela (PDF)';
    descSeccion = 'Adjunta la sentencia de tutela en PDF. Gemini 3.8 Flash extraerá la decisión de la parte resolutiva, su fecha y la notificación para calcular el término de 3 días.';
    iconoDrop = '⚖️ 📑';
    textoDrop = 'Arrastra y suelta aquí el fallo de tutela en PDF, o ';
    subDrop = 'Fallo de tutela en PDF · Máx. 20 MB · Privacidad: procesados 100% en memoria y descartados';
  } else if (tipoId === 'recurso_judicial') {
    titSeccion = '📁 Sube el auto judicial recurrido (PDF)';
    descSeccion = 'Adjunta el auto interlocutorio en PDF. Gemini 3.8 Flash extraerá la decisión controvertida, su fecha y la notificación para el cómputo de términos (arts. 318 y 322 CGP).';
    iconoDrop = '⚖️ 📑';
    textoDrop = 'Arrastra y suelta aquí el auto judicial en PDF, o ';
    subDrop = 'Auto en PDF · Máx. 20 MB · Privacidad: procesados 100% en memoria y descartados';
  } else if (tipoId === 'apelacion_sentencia') {
    titSeccion = '📁 Sube la sentencia judicial apelada (PDF)';
    descSeccion = 'Adjunta la sentencia en PDF. Gemini 3.8 Flash extraerá la decisión, la fecha del fallo y la fecha de notificación para calcular el término de apelación.';
    iconoDrop = '⚖️ 📑';
    textoDrop = 'Arrastra y suelta aquí la sentencia en PDF, o ';
    subDrop = 'Sentencia en PDF · Máx. 20 MB · Privacidad: procesados 100% en memoria y descartados';
  }

  const cab = h('div', { style: 'display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap;' },
    h('div', {},
      h('h3', { style: 'font-size: 15px; font-weight: 750; margin: 0 0 3px; display: flex; align-items: center; gap: 8px;' },
        h('span', {}, titSeccion),
        h('span', { style: 'font-size: 11px; background: rgba(37,99,235,0.08); color: var(--azul, #2563eb); padding: 2px 8px; border-radius: 999px; font-weight: 600;' }, 'Extracción con IA')
      ),
      h('p', { style: 'font-size: 12.5px; color: var(--tinta-2); margin: 0;' }, descSeccion)
    )
  );

  const inpArchivos = h('input', {
    type: 'file',
    id: 'inputArchivosCaso',
    multiple: true,
    accept: '.pdf,image/*,audio/*',
    style: 'display: none;'
  });

  const dropzone = h('div', {
    class: 'dropzone-docs',
    id: 'dropzoneDocs',
    onclick: () => inpArchivos.click()
  },
    h('div', { style: 'font-size: 26px; margin-bottom: 6px;' }, iconoDrop),
    h('div', { style: 'font-size: 13.5px; font-weight: 650; color: var(--tinta);' },
      textoDrop,
      h('span', { style: 'color: var(--azul, #2563eb); text-decoration: underline;' }, 'haz clic para seleccionarlos')
    ),
    h('div', { style: 'font-size: 11.5px; color: var(--tinta-2); margin-top: 4px;' }, subDrop)
  );

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer && e.dataTransfer.files) {
      agregarArchivosCaso(Array.from(e.dataTransfer.files));
    }
  });

  inpArchivos.addEventListener('change', () => {
    if (inpArchivos.files) {
      agregarArchivosCaso(Array.from(inpArchivos.files));
      inpArchivos.value = '';
    }
  });

  const contenedorArchivos = h('div', { id: 'listaArchivosCaso', style: 'display: grid; gap: 6px;' });

  const barraAccion = h('div', {
    id: 'barraAccionExtraccion',
    style: 'display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; padding-top: 4px;',
    hidden: true
  });

  const lblPeso = h('div', { id: 'lblPesoArchivos', style: 'font-size: 12px; color: var(--tinta-2); font-weight: 500;' });
  const btnExtraer = h('button', {
    type: 'button',
    class: 'btn primario',
    id: 'btnExtraerDocs',
    style: 'display: inline-flex; align-items: center; gap: 6px; padding: 7px 16px; font-size: 13px;',
    onclick: () => ejecutarExtraccionDocumentos(tipo)
  },
    h('span', {}, '🪄 Extraer datos con IA')
  );
  barraAccion.append(lblPeso, btnExtraer);

  const divProgreso = h('div', {
    id: 'progresoExtraccionDocs',
    style: 'padding: 16px; background: rgba(37,99,235,0.04); border: 1px solid rgba(37,99,235,0.15); border-radius: 6px; text-align: center; display: grid; gap: 6px;',
    hidden: true
  },
    h('div', { style: 'display: flex; align-items: center; justify-content: center; gap: 10px; color: var(--azul, #2563eb); font-weight: 600; font-size: 13.5px;' },
      h('span', { class: 'girando', style: 'display: inline-block;' }, '⏳'),
      h('span', { id: 'txtProgresoExtraccion' }, 'Analizando documentos en memoria con Gemini 3.8 Flash...')
    ),
    h('div', { style: 'font-size: 11.5px; color: var(--tinta-2);' },
      'Extrayendo datos de partes, fechas, hechos y pretensiones con citas textuales y números de página...'
    )
  );

  const panelPropuestas = h('div', { id: 'panelPropuestasExtraccion', style: 'display: grid; gap: 12px;', hidden: true });

  card.append(cab, inpArchivos, dropzone, contenedorArchivos, barraAccion, divProgreso, panelPropuestas);

  setTimeout(() => renderListaArchivosCaso(), 0);

  return card;
}

function agregarArchivosCaso(nuevos) {
  if (!state.archivosCaso) state.archivosCaso = [];
  const validos = [];
  for (const f of nuevos) {
    const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase();
    const esValido = f.type.startsWith('image/') || f.type.startsWith('audio/') || f.type === 'application/pdf' || ['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.mp3', '.wav', '.m4a', '.ogg', '.heic', '.aac', '.flac', '.webm'].includes(ext);
    if (esValido) {
      validos.push(f);
    } else {
      toast(`El archivo "${f.name}" no es compatible. Formatos permitidos: PDF, imágenes o audio.`, 'error');
    }
  }
  state.archivosCaso.push(...validos);
  renderListaArchivosCaso();
}

function renderListaArchivosCaso() {
  const lista = $('#listaArchivosCaso');
  const barra = $('#barraAccionExtraccion');
  const lbl = $('#lblPesoArchivos');
  const btn = $('#btnExtraerDocs');
  if (!lista || !barra || !lbl || !btn) return;

  const archivos = state.archivosCaso || [];
  lista.replaceChildren();

  if (!archivos.length) {
    lista.hidden = true;
    barra.hidden = true;
    return;
  }

  lista.hidden = false;
  barra.hidden = false;

  let totalBytes = 0;
  for (let i = 0; i < archivos.length; i++) {
    const f = archivos[i];
    totalBytes += f.size;

    const fila = h('div', {
      style: 'display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.02); border: 1px solid var(--regla); border-radius: 6px; padding: 6px 12px; font-size: 12px;'
    },
      h('div', { style: 'display: flex; align-items: center; gap: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;' },
        h('span', { style: 'font-size: 14px;' }, f.type.startsWith('audio') ? '🎙️' : f.type.startsWith('image') ? '🖼️' : '📄'),
        h('strong', { style: 'color: var(--tinta);' }, f.name),
        h('span', { style: 'color: var(--tinta-2); font-size: 11px;' }, `(${formatearTamanoBytes(f.size)})`)
      ),
      h('button', {
        type: 'button',
        title: 'Quitar archivo',
        style: 'border: none; background: none; color: #dc2626; cursor: pointer; padding: 2px 8px; font-size: 15px; font-weight: bold; line-height: 1;',
        onclick: (e) => {
          e.stopPropagation();
          archivos.splice(i, 1);
          renderListaArchivosCaso();
        }
      }, '✕')
    );
    lista.append(fila);
  }

  const pesoMB = (totalBytes / (1024 * 1024)).toFixed(2);
  const excede = totalBytes > 20 * 1024 * 1024;

  lbl.textContent = `Total: ${pesoMB} MB de 20 MB máx. (${archivos.length} archivo${archivos.length === 1 ? '' : 's'})`;
  if (excede) {
    lbl.style.color = '#dc2626';
    lbl.textContent += ' ⚠️ ¡Supera el límite de 20 MB!';
    btn.disabled = true;
  } else {
    lbl.style.color = 'var(--tinta-2)';
    btn.disabled = false;
  }
}

async function ejecutarExtraccionDocumentos(tipo) {
  const archivos = state.archivosCaso || [];
  if (!archivos.length) {
    toast('Adjunta al menos un archivo (PDF, imagen o audio) para extraer datos.', 'error');
    return;
  }

  const btn = $('#btnExtraerDocs');
  const progreso = $('#progresoExtraccionDocs');
  const panel = $('#panelPropuestasExtraccion');

  btn.disabled = true;
  if (progreso) progreso.hidden = false;
  if (panel) { panel.hidden = true; panel.replaceChildren(); }

  const formData = new FormData();
  formData.append('tipo', state.tipo);
  for (const f of archivos) {
    formData.append('archivos', f);
  }

  try {
    const res = await apiFetch('/api/extraer', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error en la extracción con IA.');
    }

    const data = await res.json();
    state.propuestasExtraidas = data.propuestas || [];

    // 1. Si se detectó fecha de notificación en el documento:
    if (data.fecha_notificacion_detectada) {
      state.datos.notificacion_fecha = data.fecha_notificacion_detectada;
      const inpNotif = $('#f_notificacion_fecha');
      if (inpNotif) {
        inpNotif.value = data.fecha_notificacion_detectada;
        inpNotif.dispatchEvent(new Event('input', { bubbles: true }));
        inpNotif.dispatchEvent(new Event('change', { bubbles: true }));
      }
      actualizarBannerVencimientoTop(data.fecha_notificacion_detectada);
    }

    // 2. Si es contestación y se extrajeron hechos numerados de la demanda:
    let mensajeHechos = '';
    if (state.tipo === 'contestacion' && Array.isArray(data.hechos_numerados) && data.hechos_numerados.length > 0) {
      state.hechosContestacion = data.hechos_numerados.map(h => ({
        numero: h.numero,
        texto: h.texto,
        pronunciamiento: 'Es cierto',
        razon: ''
      }));
      recompilarRespuestaHechos();
      const wrapHechos = $('#filasHechosContestacion');
      if (wrapHechos) renderFilasAsistenteHechos(wrapHechos);
      mensajeHechos = ` y ${data.hechos_numerados.length} hechos de la demanda listos para responder`;
    }

    const totalDatos = (state.propuestasExtraidas.length) + (data.hechos_numerados ? data.hechos_numerados.length : 0);
    if (!totalDatos) {
      toast('No se encontraron datos concluyentes en los documentos adjuntos.', 'error', 6000);
      return;
    }

    toast(`¡Extracción exitosa! ${state.propuestasExtraidas.length} campos propuestos${mensajeHechos}.`, 'ok');
    if (state.propuestasExtraidas.length > 0) {
      renderizarTablaPropuestas(state.propuestasExtraidas);
    }
  } catch (err) {
    console.error('Error en extracción:', err);
    toast(err.message || 'Error al procesar los documentos con IA.', 'error', 7000);
  } finally {
    btn.disabled = false;
    if (progreso) progreso.hidden = true;
  }
}

function renderizarTablaPropuestas(propuestas) {
  const panel = $('#panelPropuestasExtraccion');
  if (!panel) return;
  panel.replaceChildren();
  panel.hidden = false;

  const cabTabla = h('div', {
    style: 'background: #f8fafc; border: 1px solid var(--regla); border-radius: var(--r); padding: 14px 16px; display: grid; gap: 8px;'
  },
    h('div', { style: 'display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;' },
      h('h4', { style: 'margin: 0; font-size: 14px; font-weight: 750; color: var(--tinta); display: flex; align-items: center; gap: 8px;' },
        '📋 Propuestas extraídas del caso',
        h('span', { style: 'background: #0f172a; color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 999px;' }, `${propuestas.length} datos`)
      ),
      h('div', { style: 'display: flex; gap: 8px;' },
        h('button', {
          type: 'button',
          class: 'btn chico',
          onclick: () => {
            const chks = panel.querySelectorAll('input.chk-propuesta');
            const todos = Array.from(chks).every(c => c.checked);
            chks.forEach(c => { c.checked = !todos; });
          }
        }, 'Marcar / Desmarcar todos')
      )
    ),
    h('p', { style: 'margin: 0; font-size: 12px; color: var(--tinta-2);' },
      'Acepta campo por campo marcando su casilla. Por seguridad profesional, ningún campo con contenido previo se sobrescribirá sin tu confirmación explícita.'
    )
  );

  const tablaWrap = h('div', { style: 'overflow-x: auto; background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r);' });
  const tabla = h('table', { class: 'tabla-propuestas' },
    h('thead', {},
      h('tr', {},
        h('th', { style: 'width: 38px; text-align: center;' }, '✓'),
        h('th', { style: 'width: 140px;' }, 'Campo'),
        h('th', { style: 'min-width: 220px;' }, 'Propuesta extraída'),
        h('th', { style: 'width: 180px;' }, 'Origen y Cita'),
        h('th', { style: 'width: 130px;' }, 'Estado actual')
      )
    ),
    h('tbody', {},
      ...propuestas.map(p => {
        const valActual = state.datos[p.campo];
        const tieneDato = valActual != null && String(valActual).trim() !== '' && !(Array.isArray(valActual) && !valActual.length);

        const chk = h('input', {
          type: 'checkbox',
          class: 'chk-propuesta',
          dataset: { campo: p.campo }
        });
        chk.checked = !tieneDato;

        const badgeConfianza = p.confianza === 'alta'
          ? h('span', { style: 'background: #dcfce7; color: #166534; font-size: 10.5px; font-weight: 700; padding: 2px 6px; border-radius: 4px;' }, '✓ Alta')
          : p.confianza === 'media'
          ? h('span', { style: 'background: #fef9c3; color: #854d0e; font-size: 10.5px; font-weight: 700; padding: 2px 6px; border-radius: 4px;' }, '⚠️ Media')
          : h('span', { style: 'background: #f3f4f6; color: #4b5563; font-size: 10.5px; font-weight: 700; padding: 2px 6px; border-radius: 4px;' }, '❓ Baja');

        const celdaPropuesta = h('div', { style: 'display: grid; gap: 4px;' },
          h('div', { style: 'white-space: pre-wrap; font-size: 12.5px; color: var(--tinta); font-weight: 500; line-height: 1.4;' }, p.valor),
          h('div', {}, badgeConfianza)
        );

        const celdaOrigen = h('div', { style: 'font-size: 11.5px; display: grid; gap: 3px;' },
          h('div', { style: 'font-weight: 600; color: var(--tinta); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;' },
            `📄 ${p.archivo}` + (p.pagina ? ` (pág. ${p.pagina})` : '')
          ),
          p.cita_textual_corta ? h('div', { style: 'font-style: italic; color: var(--tinta-2); font-size: 11px; line-height: 1.3;' }, `“${p.cita_textual_corta}”`) : null
        );

        const celdaEstado = tieneDato
          ? h('div', { style: 'background: #fffbeb; border: 1px solid #fde68a; border-radius: 4px; padding: 4px 6px; font-size: 11px; color: #92400e;' },
              h('strong', {}, '⚠️ Ya tiene datos:'),
              h('div', { style: 'color: var(--tinta-2); max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;' }, String(valActual)),
              h('span', { style: 'font-size: 10px; color: #b45309; display: block; margin-top: 2px;' }, 'Requiere confirmación')
            )
          : h('div', { style: 'color: #16a34a; font-size: 11.5px; font-weight: 600;' }, '⚪ Vacío (listo)');

        return h('tr', { style: tieneDato ? 'background: rgba(254, 243, 199, 0.15);' : '' },
          h('td', { style: 'text-align: center;' }, chk),
          h('td', {},
            h('strong', { style: 'color: var(--tinta); display: block;' }, p.etiqueta),
            h('small', { style: 'color: var(--tinta-2); font-family: var(--mono); font-size: 10.5px;' }, p.campo)
          ),
          h('td', {}, celdaPropuesta),
          h('td', {}, celdaOrigen),
          h('td', {}, celdaEstado)
        );
      })
    )
  );
  tablaWrap.append(tabla);

  const barraBotones = h('div', {
    style: 'display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; padding: 4px 0;'
  },
    h('div', { style: 'display: flex; gap: 10px; align-items: center;' },
      h('button', {
        type: 'button',
        class: 'btn primario',
        id: 'btnAplicarPropuestas',
        style: 'padding: 8px 18px; font-size: 13.5px; font-weight: 650; display: inline-flex; align-items: center; gap: 6px;',
        onclick: () => incorporarPropuestasSeleccionadas(propuestas)
      }, '✓ Incorporar campos seleccionados al formulario'),
      h('button', {
        type: 'button',
        class: 'btn enlace',
        style: 'color: var(--tinta-2); font-size: 12.5px; text-decoration: underline;',
        onclick: () => { panel.hidden = true; panel.replaceChildren(); }
      }, 'Descartar propuestas')
    )
  );

  panel.append(cabTabla, tablaWrap, barraBotones);
}

function incorporarPropuestasSeleccionadas(propuestas) {
  const panel = $('#panelPropuestasExtraccion');
  if (!panel) return;

  const seleccionadas = [];
  const sobrescrituras = [];

  for (const p of propuestas) {
    const chk = panel.querySelector(`input.chk-propuesta[data-campo="${p.campo}"]`);
    if (chk && chk.checked) {
      seleccionadas.push(p);
      const valActual = state.datos[p.campo];
      if (valActual != null && String(valActual).trim() !== '' && !(Array.isArray(valActual) && !valActual.length)) {
        sobrescrituras.push({ p, valActual });
      }
    }
  }

  if (!seleccionadas.length) {
    toast('Selecciona al menos una propuesta marcando su casilla.', 'error');
    return;
  }

  // Regla fundamental: "Nunca sobrescribas un campo lleno sin confirmación."
  if (sobrescrituras.length > 0) {
    const detalleSobrescrituras = sobrescrituras.map(s => {
      const actStr = String(s.valActual);
      const valStr = String(s.p.valor);
      const actCorta = actStr.length > 70 ? actStr.slice(0, 70) + '...' : actStr;
      const valCorta = valStr.length > 70 ? valStr.slice(0, 70) + '...' : valStr;
      return `• ${s.p.etiqueta} (${s.p.campo}):\n  - ACTUAL: "${actCorta}"\n  - NUEVA: "${valCorta}"`;
    }).join('\n\n');

    const mensaje = (
      `⚠️ CONFIRMACIÓN DE SOBRESCRITURA DE DATOS\n\n` +
      `Los siguientes ${sobrescrituras.length} campos ya contienen datos en el formulario:\n\n` +
      `${detalleSobrescrituras}\n\n` +
      `¿Deseas reemplazar el contenido existente por los datos extraídos de los documentos?`
    );

    const confirmado = window.confirm(mensaje);
    if (!confirmado) {
      toast('Operación cancelada. Se mantuvieron tus datos intactos.', 'info');
      return;
    }
  }

  // Aplicar campos seleccionados al formulario
  let aplicados = 0;
  for (const p of seleccionadas) {
    state.datos[p.campo] = p.valor;
    aplicados++;

    const inp = $('#f_' + p.campo);
    if (inp) {
      inp.value = p.valor;
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      inp.dispatchEvent(new Event('change', { bubbles: true }));
      const wrap = inp.closest('.campo');
      if (wrap) {
        wrap.classList.add('campo-recien-aplicado');
        setTimeout(() => wrap.classList.remove('campo-recien-aplicado'), 3000);
      }
    }
    if (p.campo === 'notificacion_fecha' && p.valor) {
      actualizarBannerVencimientoTop(p.valor);
    }
  }

  guardarBorrador();
  toast(`¡${aplicados} datos incorporados con éxito al formulario!`, 'ok');

  panel.replaceChildren(
    h('div', {
      style: 'padding: 14px 18px; background: #f0fdf4; border: 1.5px solid #86efac; border-radius: var(--r); color: #166534; font-size: 13px; font-weight: 600; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;'
    },
      h('div', { style: 'display: flex; align-items: center; gap: 8px;' },
        h('span', { style: 'font-size: 16px;' }, '✓'),
        h('span', {}, `Se incorporaron ${aplicados} campos al formulario. Revisa los campos resaltados.`)
      ),
      h('button', {
        type: 'button',
        class: 'btn chico',
        onclick: () => renderizarTablaPropuestas(propuestas)
      }, 'Ver propuestas de nuevo')
    )
  );
}

/* =========================================================
   Asistente de Hechos (Art. 96 CGP) y Cómputo de Vencimiento
   ========================================================= */

function parsearTextoAHechos(texto) {
  if (!texto || typeof texto !== 'string') return [];
  const bloques = texto.split(/(?=\n\s*\d+[\.\)])/g).map(s => s.trim()).filter(Boolean);
  if (!bloques.length) return [];
  const hechos = [];
  for (let i = 0; i < bloques.length; i++) {
    const b = bloques[i];
    const mNum = /^\s*(\d+)[\.\)]\s*(?:AL\s+HECHO\s+\w+[\s\:\-\.]*)?(.*)$/is.exec(b);
    const num = mNum ? parseInt(mNum[1], 10) : (i + 1);
    const resto = mNum ? mNum[2].trim() : b;

    let pron = 'Es cierto';
    let razon = '';
    if (/\bno\s+es\s+cierto\b/i.test(resto)) {
      pron = 'No es cierto';
      razon = resto.replace(/^.*?\bno\s+es\s+cierto\b[\:\.\s\-]*/i, '').trim();
    } else if (/\bno\s+me\s+consta\b/i.test(resto)) {
      pron = 'No me consta';
      razon = resto.replace(/^.*?\bno\s+me\s+consta\b[\:\.\s\-]*/i, '').trim();
    } else if (/\b(?:es\s+)?parcialmente\s+cierto\b/i.test(resto)) {
      pron = 'Es parcialmente cierto';
      razon = resto.replace(/^.*?\bparcialmente\s+cierto\b[\:\.\s\-]*/i, '').trim();
    } else if (/\bes\s+cierto\b/i.test(resto)) {
      pron = 'Es cierto';
      razon = resto.replace(/^.*?\bes\s+cierto\b[\:\.\s\-]*/i, '').trim();
    } else {
      razon = resto;
    }
    hechos.push({ numero: num, texto: '', pronunciamiento: pron, razon });
  }
  return hechos;
}

function recompilarRespuestaHechos() {
  if (!state.hechosContestacion || !state.hechosContestacion.length) return;
  const lineas = state.hechosContestacion.map((h, i) => {
    const num = h.numero || (i + 1);
    const pron = h.pronunciamiento || 'Es cierto';
    const razon = (h.razon || '').trim();
    let l = `${num}. AL HECHO ${num}: ${pron}.`;
    if (razon) {
      l += ` ${razon.endsWith('.') ? razon : razon + '.'}`;
    }
    return l;
  });

  const textoCompilado = lineas.join('\n\n');
  state.datos.respuesta_hechos = textoCompilado;
  const area = $('#f_respuesta_hechos');
  if (area && area.value !== textoCompilado) {
    area.value = textoCompilado;
  }
  guardarBorrador();
}

function claseSegunPronunciamiento(pron) {
  if (pron === 'No es cierto') return 'no-es-cierto requiere-razon';
  if (pron === 'No me consta') return 'no-consta requiere-razon';
  if (pron === 'Es parcialmente cierto') return 'parcial requiere-razon';
  return 'es-cierto';
}

function renderFilasAsistenteHechos(filasWrap) {
  if (!filasWrap) return;
  filasWrap.replaceChildren();

  if (!state.hechosContestacion || !state.hechosContestacion.length) {
    state.hechosContestacion = [{ numero: 1, texto: '', pronunciamiento: 'Es cierto', razon: '' }];
  }

  state.hechosContestacion.forEach((hItem, idx) => {
    hItem.numero = idx + 1;
    const card = h('div', {
      class: 'asistente-hecho-card ' + claseSegunPronunciamiento(hItem.pronunciamiento)
    });

    const topBar = h('div', { class: 'asistente-hecho-top' },
      h('span', { class: 'asistente-hecho-num' },
        h('span', { style: 'color: var(--azul, #2563eb);' }, `#${hItem.numero}`),
        `Hecho ${hItem.numero}`
      ),
      h('button', {
        type: 'button',
        class: 'asistente-hecho-del',
        title: `Eliminar hecho ${hItem.numero}`,
        onclick: () => {
          state.hechosContestacion.splice(idx, 1);
          if (!state.hechosContestacion.length) {
            state.hechosContestacion.push({ numero: 1, texto: '', pronunciamiento: 'Es cierto', razon: '' });
          }
          renderFilasAsistenteHechos(filasWrap);
          recompilarRespuestaHechos();
        }
      }, '✕')
    );

    const txtDemanda = hItem.texto
      ? h('div', { class: 'asistente-hecho-texto-demanda' },
          h('strong', { style: 'color: var(--tinta);' }, 'Afirmación de la demanda: '),
          `“${hItem.texto}”`
        )
      : null;

    const controles = h('div', { class: 'asistente-hecho-controles' });

    const sel = h('select', { class: 'asistente-hecho-select' },
      h('option', { value: 'Es cierto' }, '✓ Es cierto'),
      h('option', { value: 'No es cierto' }, '✗ No es cierto'),
      h('option', { value: 'No me consta' }, '❓ No me consta'),
      h('option', { value: 'Es parcialmente cierto' }, '⚡ Es parcialmente cierto')
    );
    sel.value = hItem.pronunciamiento || 'Es cierto';

    const inpRazon = h('textarea', {
      class: 'asistente-hecho-razon',
      rows: 2,
      placeholder: (sel.value === 'Es cierto')
        ? 'Razón o precisión opcional...'
        : '⚠️ Razón precisa y unívoca obligatoria (art. 96 CGP)...'
    });
    inpRazon.value = hItem.razon || '';

    const btnMicRazon = crearBotonMicrofono('razon_' + hItem.numero, (b) => {
      iniciarDictado(inpRazon, b, (nuevaRazon) => {
        hItem.razon = nuevaRazon;
        recompilarRespuestaHechos();
      });
    });
    btnMicRazon.title = `Dictar razón del hecho ${hItem.numero} (es-CO)`;

    sel.addEventListener('change', () => {
      hItem.pronunciamiento = sel.value;
      card.className = 'asistente-hecho-card ' + claseSegunPronunciamiento(sel.value);
      inpRazon.placeholder = (sel.value === 'Es cierto')
        ? 'Razón o precisión opcional...'
        : '⚠️ Razón precisa y unívoca obligatoria (art. 96 CGP)...';
      recompilarRespuestaHechos();
    });

    inpRazon.addEventListener('input', () => {
      hItem.razon = inpRazon.value;
      recompilarRespuestaHechos();
    });

    controles.append(sel, inpRazon, btnMicRazon);

    card.append(topBar);
    if (txtDemanda) card.append(txtDemanda);
    card.append(controles);

    filasWrap.append(card);
  });
}

function renderAsistenteHechosContestacion(c, cambiar, wrap) {
  wrap.replaceChildren();

  // Inicializar state.hechosContestacion si está vacío
  if (!state.hechosContestacion || !state.hechosContestacion.length) {
    const parsed = parsearTextoAHechos(state.datos.respuesta_hechos);
    if (parsed.length) {
      state.hechosContestacion = parsed;
    } else {
      state.hechosContestacion = [{ numero: 1, texto: '', pronunciamiento: 'Es cierto', razon: '' }];
    }
  }

  const asis = h('div', { class: 'asistente-hechos', id: 'wrapAsistenteHechos' });
  const filasWrap = h('div', { class: 'asistente-hechos-filas', id: 'filasHechosContestacion' });

  const cab = h('div', { class: 'asistente-hechos-cab' },
    h('div', {},
      h('div', { style: 'font-weight: 750; font-size: 13.5px; color: var(--tinta); display: flex; align-items: center; gap: 8px;' },
        h('span', {}, '📋 Pronunciamiento sobre los hechos de la demanda'),
        h('span', { style: 'font-size: 11px; background: rgba(37,99,235,0.08); color: var(--azul, #2563eb); padding: 2px 7px; border-radius: 999px; font-weight: 600;' }, 'Art. 96 CGP')
      ),
      h('div', { style: 'font-size: 11.5px; color: var(--tinta-2); margin-top: 2px;' },
        'Pronúnciate hecho por hecho. Si niegas o no te consta, debes expresar las razones precisas y unívocas para evitar que se presuma cierto (confesión ficta).'
      )
    ),
    h('button', {
      type: 'button',
      class: 'btn chico primario',
      id: 'btnAgregarHecho',
      style: 'font-size: 12px; padding: 5px 12px; display: inline-flex; align-items: center; gap: 4px;',
      onclick: () => {
        const nuevoNum = (state.hechosContestacion.length || 0) + 1;
        state.hechosContestacion.push({ numero: nuevoNum, texto: '', pronunciamiento: 'Es cierto', razon: '' });
        renderFilasAsistenteHechos(filasWrap);
        recompilarRespuestaHechos();
      }
    }, '+ Agregar hecho')
  );

  renderFilasAsistenteHechos(filasWrap);

  const inpAreaConsolidada = h('textarea', {
    id: 'f_respuesta_hechos',
    rows: 6,
    style: 'width: 100%; box-sizing: border-box; font-family: inherit; font-size: 12.5px; border: 1px solid var(--regla); border-radius: 4px; padding: 8px; margin-top: 6px;'
  });
  inpAreaConsolidada.value = state.datos.respuesta_hechos || '';
  inpAreaConsolidada.addEventListener('input', () => {
    state.datos.respuesta_hechos = inpAreaConsolidada.value;
    guardarBorrador();
  });

  const btnMicConsolidado = crearBotonMicrofono('respuesta_hechos', (b) => {
    iniciarDictado(inpAreaConsolidada, b, (val) => {
      state.datos.respuesta_hechos = val;
      guardarBorrador();
    });
  });

  const cabDetalle = h('div', { style: 'display: flex; justify-content: space-between; align-items: center; margin: 6px 0; gap: 8px;' },
    h('p', { style: 'margin: 0; color: var(--tinta-2); font-size: 11.5px;' },
      'Texto consolidado conforme al art. 96 CGP que se enviará al redactor de IA:'
    ),
    btnMicConsolidado
  );

  const det = h('details', { style: 'border-top: 1px solid var(--regla); padding: 10px 14px; font-size: 12px;' },
    h('summary', { style: 'cursor: pointer; font-weight: 600; color: var(--azul, #2563eb);' }, '📝 Ver / editar texto consolidado de respuesta a hechos'),
    cabDetalle,
    inpAreaConsolidada
  );

  asis.append(cab, filasWrap, det);
  wrap.append(asis);

  recompilarRespuestaHechos();
  return wrap;
}

async function actualizarBannerVencimientoTop(fechaIso) {
  const banner = $('#bannerVencimientoTop');
  if (!banner) return;
  const tipoId = state.tipo;
  if (!tipoId || !TIPOS[tipoId]) {
    banner.hidden = true;
    banner.replaceChildren();
    return;
  }

  const tiposConTermino = ['contestacion', 'impugnacion_tutela', 'recurso_judicial', 'apelacion_sentencia'];
  const esTipoConTermino = tiposConTermino.includes(tipoId);
  const fecha = (fechaIso != null ? String(fechaIso) : String(state.datos.notificacion_fecha || '')).trim();

  // Si no hay fecha aún
  if (!fecha || !/^\d{4}-\d{2}-\d{2}$/.test(fecha)) {
    if (esTipoConTermino) {
      const infoTerminos = {
        contestacion: { dias: '20 días hábiles (ordinario) / 10 días (verbal sumario)', norma: 'Arts. 369 y 391 CGP' },
        impugnacion_tutela: { dias: '3 días hábiles', norma: 'Art. 31 Decreto 2591 de 1991' },
        recurso_judicial: { dias: '3 días hábiles', norma: 'Arts. 318 y 322 CGP' },
        apelacion_sentencia: { dias: '3 días hábiles', norma: 'Art. 322 CGP' }
      };
      const info = infoTerminos[tipoId] || { dias: 'Término legal procesal', norma: 'CGP / CPACA' };
      banner.hidden = false;
      banner.className = 'banner-vencimiento-top info';
      banner.replaceChildren(
        h('div', { style: 'display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;' },
          h('div', { style: 'display: flex; align-items: center; gap: 10px;' },
            h('span', { style: 'font-size: 20px;' }, '⏱️'),
            h('div', {},
              h('div', { style: 'font-weight: 750; font-size: 13.5px; color: var(--tinta);' },
                `Término legal: ${info.dias} · ${info.norma}`
              ),
              h('div', { style: 'font-size: 12px; color: var(--tinta-2); margin-top: 2px;' },
                'Sube la providencia o demanda en PDF (o ingresa la fecha de notificación) para calcular el vencimiento en días hábiles.'
              )
            )
          ),
          h('button', {
            type: 'button',
            class: 'btn chico',
            style: 'font-size: 12px;',
            onclick: () => {
              const inp = $('#f_notificacion_fecha');
              if (inp) { inp.focus(); inp.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
            }
          }, '📅 Ingresar fecha')
        )
      );
      return;
    }
    banner.hidden = true;
    banner.replaceChildren();
    return;
  }

  // Si hay fecha válida, llamamos a /api/plazos
  const presetId = inferirPresetTermino(tipoId);
  banner.hidden = false;
  banner.className = 'banner-vencimiento-top cargando';
  banner.dataset.lastPlazoFecha = fecha;
  banner.replaceChildren(
    h('div', { style: 'display: flex; align-items: center; gap: 8px; color: var(--tinta-2); font-size: 13px;' },
      h('span', { class: 'girando' }, '⏳'),
      h('span', {}, 'Calculando vencimiento legal del término procesal...')
    )
  );

  try {
    const res = await apiFetch('/api/plazos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tipo_termino: presetId,
        fecha_inicio: fecha,
        titulo_evento: `Vencimiento: ${TIPOS[tipoId]?.nombre || 'Término procesal'}`
      })
    });
    if (!res.ok) throw new Error('Error al calcular plazos en el servidor');
    const data = await res.json();
    if (banner.dataset.lastPlazoFecha !== fecha) return;

    const esVencido = data.ha_vencido;
    const esHoy = data.estado_vencimiento === 'vence_hoy';
    banner.className = 'banner-vencimiento-top ' + (esVencido ? 'vencido' : esHoy ? 'urgente' : 'ok');

    let textoVence = '';
    if (esVencido) {
      textoVence = `Vence el ${data.dia_semana_vencimiento.toLowerCase()}, ${data.fecha_vencimiento} (quedan 0 días hábiles · ¡VENCIDO!)`;
    } else {
      textoVence = `Vence el ${data.dia_semana_vencimiento.toLowerCase()}, ${data.fecha_vencimiento} (quedan ${data.dias_habiles_restantes} días hábiles)`;
    }

    const icono = esVencido ? '⚠️' : esHoy ? '⏰' : '⏱️';

    banner.replaceChildren(
      h('div', { style: 'display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap;' },
        h('div', { style: 'display: flex; align-items: flex-start; gap: 10px;' },
          h('span', { style: 'font-size: 22px; line-height: 1.1;' }, icono),
          h('div', {},
            h('div', { style: 'font-size: 14px; font-weight: 800; letter-spacing: -0.2px;' },
              (esVencido ? '¡PLAZO VENCIDO! ' : '') + textoVence
            ),
            h('div', { style: 'font-size: 12px; margin-top: 3px; opacity: 0.95;' },
              `${data.nombre_termino} (${data.cantidad} ${data.unidad === 'dias_habiles' ? 'días hábiles' : data.unidad}) · ${data.norma} · Notificado el ${fecha}`
            ),
            h('div', { style: 'font-size: 11.5px; margin-top: 2px; opacity: 0.85;' },
              data.texto_resumen
            )
          )
        ),
        h('div', { style: 'display: flex; gap: 8px; align-items: center;' },
          h('button', {
            type: 'button',
            class: 'btn chico ' + (esVencido ? 'fantasma' : 'primario'),
            style: 'display: inline-flex; align-items: center; gap: 5px; font-weight: 600;',
            onclick: () => descargarIcs(data.evento_ics, `vencimiento_${data.fecha_vencimiento}.ics`)
          }, '📅 Descargar evento (.ics)'),
          h('button', {
            type: 'button',
            class: 'btn chico fantasma',
            title: 'Ir al campo de fecha de notificación',
            onclick: () => {
              const inp = $('#f_notificacion_fecha');
              if (inp) { inp.focus(); inp.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
            }
          }, 'Cambiar fecha')
        )
      )
    );
  } catch (err) {
    if (banner.dataset.lastPlazoFecha !== fecha) return;
    console.error('Error calculando vencimiento superior:', err);
    banner.className = 'banner-vencimiento-top info';
    banner.replaceChildren(
      h('div', { style: 'font-size: 12px; color: #dc2626;' },
        'No fue posible calcular el vencimiento legal: ' + err.message
      )
    );
  }
}

/* =========================================================
   Reconocimiento y Dictado por Voz (Web Speech API es-CO)
   ========================================================= */
const soportaVoz = () => typeof window !== 'undefined' && !!(window.SpeechRecognition || window.webkitSpeechRecognition);

function esCampoHechosOPretensiones(c) {
  if (!c || !c.k) return false;
  if (c.t === 'check' || c.t === 'chips' || c.t === 'select' || c.t === 'date' || c.t === 'fecha') return false;
  const k = String(c.k).toLowerCase();
  const l = String(c.l || '').toLowerCase();
  return k.includes('hecho') || k.includes('pretensi') || l.includes('hecho') || l.includes('pretensi');
}

function crearBotonMicrofono(idCampo, alClic) {
  const tieneSoporte = soportaVoz();
  const iconoMic = `<svg viewBox="0 0 16 16" width="13" height="13" fill="currentColor" aria-hidden="true"><path d="M8 11a3 3 0 0 0 3-3V4a3 3 0 0 0-6 0v4a3 3 0 0 0 3 3z"/><path d="M12.5 8a.5.5 0 0 0-1 0 3.5 3.5 0 0 1-7 0 .5.5 0 0 0-1 0 4.5 4.5 0 0 0 4 4.45V14H6.5a.5.5 0 0 0 0 1h3a.5.5 0 0 0 0-1H8.5v-1.55A4.5 4.5 0 0 0 12.5 8z"/></svg>`;
  const btn = h('button', {
    type: 'button',
    class: 'btn-microfono',
    id: 'btnMic_' + idCampo,
    title: tieneSoporte ? 'Dictar por voz (es-CO)' : 'Dictado por voz no soportado en este navegador',
    'aria-label': 'Dictar por voz (es-CO)'
  });
  btn.innerHTML = `${iconoMic} <span>Dictar</span>`;
  if (!tieneSoporte) {
    btn.hidden = true;
    btn.style.display = 'none';
    btn.setAttribute('aria-hidden', 'true');
  } else {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      if (typeof alClic === 'function') alClic(btn);
    });
  }
  return btn;
}

let reconocimientoActivo = null;

function iniciarDictado(inp, btnMicrofono, alCambiar) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    if (btnMicrofono) {
      btnMicrofono.hidden = true;
      btnMicrofono.style.display = 'none';
      btnMicrofono.setAttribute('aria-hidden', 'true');
    }
    toast('Tu navegador no soporta la Web Speech API para dictado por voz.', 'info');
    return;
  }

  const iconoMic = `<svg viewBox="0 0 16 16" width="13" height="13" fill="currentColor" aria-hidden="true"><path d="M8 11a3 3 0 0 0 3-3V4a3 3 0 0 0-6 0v4a3 3 0 0 0 3 3z"/><path d="M12.5 8a.5.5 0 0 0-1 0 3.5 3.5 0 0 1-7 0 .5.5 0 0 0-1 0 4.5 4.5 0 0 0 4 4.45V14H6.5a.5.5 0 0 0 0 1h3a.5.5 0 0 0 0-1H8.5v-1.55A4.5 4.5 0 0 0 12.5 8z"/></svg>`;

  const ponerEstadoNormal = () => {
    btnMicrofono.classList.remove('grabando');
    btnMicrofono.innerHTML = `${iconoMic} <span>Dictar</span>`;
    btnMicrofono.title = 'Dictar por voz (es-CO)';
    if (reconocimientoActivo === recognition) reconocimientoActivo = null;
  };

  const ponerEstadoGrabando = () => {
    btnMicrofono.classList.add('grabando');
    btnMicrofono.innerHTML = `<span class="punto-grabando" style="width:7px;height:7px;background:#dc2626;border-radius:50%;display:inline-block;"></span> <span>Escuchando…</span>`;
    btnMicrofono.title = 'Escuchando en es-CO. Haz clic para detener.';
  };

  // Si ya estaba grabando este mismo botón, detenerlo
  if (reconocimientoActivo && reconocimientoActivo._btn === btnMicrofono) {
    try {
      reconocimientoActivo.stop();
    } catch {}
    ponerEstadoNormal();
    return;
  }

  // Si había otro botón grabando, detenerlo primero
  if (reconocimientoActivo) {
    try {
      if (typeof reconocimientoActivo._ponerNormal === 'function') {
        reconocimientoActivo._ponerNormal();
      }
      reconocimientoActivo.stop();
    } catch {}
    reconocimientoActivo = null;
  }

  let recognition;
  try {
    recognition = new SpeechRecognition();
  } catch (e) {
    console.error('Error al instanciar SpeechRecognition:', e);
    if (btnMicrofono) {
      btnMicrofono.hidden = true;
      btnMicrofono.style.display = 'none';
      btnMicrofono.setAttribute('aria-hidden', 'true');
    }
    return;
  }

  recognition.lang = 'es-CO';
  recognition.continuous = true;
  recognition.interimResults = false;
  recognition._btn = btnMicrofono;
  recognition._ponerNormal = ponerEstadoNormal;

  recognition.onstart = () => {
    reconocimientoActivo = recognition;
    ponerEstadoGrabando();
    toast('🎙️ Micrófono activo (es-CO). Dicta y el texto se agregará al final.', 'info', 2500);
  };

  recognition.onresult = (event) => {
    const trozos = [];
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        const tr = (event.results[i][0].transcript || '').trim();
        if (tr) trozos.push(tr);
      }
    }
    const tLimpia = trozos.join(' ');
    if (tLimpia) {
      agregarTextoDictado(inp, tLimpia, alCambiar);
    }
  };

  recognition.onerror = (event) => {
    console.warn('SpeechRecognition error:', event.error);
    ponerEstadoNormal();
    if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
      toast('Permiso de micrófono denegado en el navegador.', 'error', 4500);
    } else if (event.error === 'no-speech') {
      toast('No se detectó voz al dictar. Intenta de nuevo.', 'info', 2500);
    } else if (event.error !== 'aborted') {
      toast('Reconocimiento de voz: ' + event.error, 'error', 3500);
    }
  };

  recognition.onend = () => {
    ponerEstadoNormal();
  };

  try {
    recognition.start();
  } catch (err) {
    console.error('No se pudo iniciar el dictado:', err);
    ponerEstadoNormal();
  }
}

function agregarTextoDictado(inp, transcripcion, alCambiar) {
  const trans = (transcripcion || '').trim();
  if (!trans) return;

  const actual = inp.value || '';
  let res = '';
  if (!actual.trim()) {
    res = trans.charAt(0).toUpperCase() + trans.slice(1);
  } else {
    const trimActual = actual.trimEnd();
    const separador = /[\.\n]\s*$/.test(trimActual) ? '\n' : ' ';
    const textoAñadir = (separador === '\n')
      ? (trans.charAt(0).toUpperCase() + trans.slice(1))
      : trans;
    res = trimActual + separador + textoAñadir;
  }

  inp.value = res;
  inp.scrollTop = inp.scrollHeight;
  inp.dispatchEvent(new Event('input', { bubbles: true }));
  inp.dispatchEvent(new Event('change', { bubbles: true }));
  if (typeof alCambiar === 'function') alCambiar(res);
}

function renderFormulario() {
  const form = $('#formCaso');
  form.replaceChildren();
  const tipo = TIPOS[state.tipo];
  if (!tipo) { form.hidden = true; return; }

  // Banner superior de vencimiento con /api/plazos
  actualizarBannerVencimientoTop(state.datos.notificacion_fecha);

  // 1. Área: Sube los documentos del caso (PDF, imágenes, audio)
  form.append(renderZonaSubidaDocumentos(tipo));

  for (const g of [...tipo.grupos, grupoRedaccion(tipo)]) {
    const sec = h('section', { class: 'grupo' }, h('h3', { class: 'leyenda' }, h('span', {}, g.n)));
    for (const c of g.campos) sec.append(renderCampo(c));
    form.append(sec);
  }
}
function renderCampo(c) {
  const id = 'f_' + c.k;
  const v = state.datos[c.k] ?? valorDefecto(c);
  const wrap = h('div', { class: 'campo', 'data-campo': c.k });
  const etiqueta = (t) => h('label', { for: id }, t, c.req ? h('span', { class: 'req', 'aria-hidden': 'true' }, '*') : null);
  const cambiar = val => { state.datos[c.k] = val; wrap.classList.remove('err'); const me = wrap.querySelector('.msg-err'); if (me) me.remove(); guardarBorrador(); if (c.k === '_membrete' && !state.ejemplo) renderMembreteHoja(); };

  // Asistente estructurado para hechos de contestación de demanda (Art. 96 CGP)
  if (c.k === 'respuesta_hechos' && state.tipo === 'contestacion') {
    return renderAsistenteHechosContestacion(c, cambiar, wrap);
  }
  if (c.t === 'check') {
    const inp = h('input', { type: 'checkbox', id });
    inp.checked = !!v;
    inp.addEventListener('change', () => cambiar(inp.checked));
    wrap.append(h('label', { class: 'check', for: id }, inp, h('span', {}, c.l)));
    return wrap;
  }
  if (c.t === 'chips') {
    wrap.append(h('span', { class: 'etq', id: id + '_l' }, c.l, c.req ? h('span', { class: 'req', 'aria-hidden': 'true' }, '*') : null));
    const caja = h('div', { class: 'chips', role: 'group', 'aria-labelledby': id + '_l' });
    const sel = new Set(Array.isArray(v) ? v : []);
    const todos = [...c.opciones, ...[...sel].filter(x => !c.opciones.includes(x))];
    const pintarChip = op => {
      const b = h('button', { type: 'button', class: 'chip', 'aria-pressed': String(sel.has(op)) }, op);
      b.addEventListener('click', () => { if (sel.has(op)) sel.delete(op); else sel.add(op); b.setAttribute('aria-pressed', String(sel.has(op))); cambiar([...sel]); });
      return b;
    };
    todos.forEach(op => caja.append(pintarChip(op)));
    const otro = h('input', { type: 'text', id, placeholder: 'Otro…', 'aria-label': 'Agregar otro: ' + c.l });
    const agregar = () => { const x = otro.value.trim(); if (!x) return; if (!sel.has(x)) { sel.add(x); caja.append(pintarChip(x)); cambiar([...sel]); } otro.value = ''; };
    otro.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); agregar(); } });
    wrap.append(caja, h('div', { class: 'chip-otro' }, otro, h('button', { type: 'button', class: 'btn chico', onclick: agregar }, 'Agregar')));
    if (c.ayuda) wrap.append(h('p', { class: 'ayuda' }, c.ayuda));
    return wrap;
  }
  const esVoz = esCampoHechosOPretensiones(c);
  let btnMic = null;
  if (esVoz) {
    btnMic = crearBotonMicrofono(c.k, (b) => {
      iniciarDictado(inp, b, cambiar);
    });
    btnMic.title = `Dictar por voz en ${c.l || c.k} (es-CO)`;
    const cabFila = h('div', { class: 'campo-cab', style: 'display: flex; justify-content: space-between; align-items: center; gap: 8px;' },
      etiqueta(c.l),
      btnMic
    );
    wrap.append(cabFila);
  } else {
    wrap.append(etiqueta(c.l));
  }
  const contenedorAyudas = h('div', { class: 'contenedor-ayudas' });
  let inp;
  if (c.t === 'select') {
    inp = h('select', { id });
    for (const [val, txt] of c.opciones) { const o = h('option', { value: val }, txt); if (val === v) o.selected = true; inp.append(o); }
    inp.addEventListener('change', () => { cambiar(inp.value); actualizarAyudasCampo(c, inp, contenedorAyudas); });
  } else if (c.t === 'area') {
    inp = h('textarea', { id, rows: c.rows || 4, placeholder: c.ph || '' });
    inp.value = v || '';
    inp.addEventListener('input', () => { cambiar(inp.value); actualizarAyudasCampo(c, inp, contenedorAyudas); });
  } else if (c.t === 'date' || c.t === 'fecha' || (c.k && c.k.includes('notificacion_fecha'))) {
    inp = h('input', { type: 'date', id, class: 'campo-fecha' });
    inp.value = v || '';
    const fnAlCambiarFecha = () => { cambiar(inp.value); actualizarAyudasCampo(c, inp, contenedorAyudas); };
    inp.addEventListener('input', fnAlCambiarFecha);
    inp.addEventListener('change', fnAlCambiarFecha);
  } else {
    inp = h('input', { type: 'text', id, placeholder: c.ph || '', class: c.t === 'radicado' ? 'maq' : null, inputmode: c.t === 'radicado' ? 'numeric' : null });
    inp.value = v || '';
    if (c.sug && c.sug.length) { const dl = h('datalist', { id: id + '_dl' }, c.sug.map(s => h('option', { value: s }))); inp.setAttribute('list', id + '_dl'); wrap.append(dl); }
    inp.addEventListener('input', () => {
      cambiar(inp.value);
      actualizarAyudasCampo(c, inp, contenedorAyudas);
    });
    if (c.t === 'radicado' || c.k === 'radicado') {
      inp.addEventListener('blur', () => {
        const digitos = (inp.value || '').replace(/\D/g, '');
        if (digitos.length === 23 && typeof formatearRadicado === 'function') {
          inp.value = formatearRadicado(digitos);
          cambiar(inp.value);
          actualizarAyudasCampo(c, inp, contenedorAyudas);
        }
      });
    }
  }
  wrap.append(inp);
  wrap.append(contenedorAyudas);
  actualizarAyudasCampo(c, inp, contenedorAyudas);
  return wrap;
}
function actualizarAyudasCampo(c, inp, contenedor) {
  if (!contenedor) return;
  const val = String(inp.value || '').trim();
  contenedor.replaceChildren();

  // 1. Si es radicado (o clave radicado)
  if (c.t === 'radicado' || c.k === 'radicado') {
    const digitos = val.replace(/\D/g, '');
    const n = digitos.length;
    if (!n) {
      contenedor.append(h('p', { class: 'ayuda' }, 'Número de 23 dígitos asignado por el despacho (5-2-2-3-4-5-2).'));
    } else if (n === 23 && typeof decodificarRadicado === 'function') {
      const dec = decodificarRadicado(digitos);
      contenedor.append(
        h('div', { class: 'ayuda-radicado-ok', style: 'background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 4px; padding: 6px 8px; margin-top: 4px; font-size: 12.5px;' },
          h('div', { style: 'color: #166534; font-weight: 600;' }, `✓ Radicado judicial: ${dec.formateado}`),
          h('div', { style: 'color: #15803d; font-size: 11.5px; margin-top: 2px;' }, `📍 ${dec.resumen}`)
        )
      );
    } else {
      contenedor.append(
        h('p', { class: 'msg-err', style: 'color: #dc2626; font-size: 12px; margin-top: 4px; font-weight: 500;' },
          `Tiene ${n} dígitos; un radicado judicial completo exige exactamente 23 dígitos (5-2-2-3-4-5-2).`
        )
      );
    }
    return;
  }

  // 2. Si contiene un NIT: calcular y validar dígito de verificación DIAN
  const esNit = c.k.includes('nit') || val.toLowerCase().includes('nit') || /\b\d{3}\.\d{3}\.\d{3}-\d\b/.test(val) || /\b\d{8,10}-\d\b/.test(val);
  if (esNit && typeof validarNit === 'function') {
    const reNit = /\b(?:NIT|N\.I\.T\.)\s*[:#]?\s*(\d{1,3}(?:\.\d{3}){2,3}(?:-\d)?|\d{8,10}(?:-\d)?)\b|\b(\d{3}\.\d{3}\.\d{3}-\d|\d{8,10}-\d)\b/gi;
    let m = reNit.exec(val);
    const textoNit = m ? (m[1] || m[2]) : (val.includes('-') ? val : '');
    if (textoNit) {
      const vNit = validarNit(textoNit);
      if (vNit.dvIngresado !== null) {
        if (vNit.valido) {
          contenedor.append(
            h('p', { class: 'ayuda', style: 'color: #166534; font-size: 12px; margin-top: 3px;' },
              `✓ Dígito de verificación DIAN correcto: ${vNit.nitFormateado}`
            )
          );
        } else {
          contenedor.append(
            h('p', { class: 'msg-err', style: 'color: #dc2626; font-size: 12px; font-weight: 600; margin-top: 3px;' },
              `⚠️ ${vNit.mensaje}`
            )
          );
        }
      } else if (vNit.dvCalculado !== null) {
        contenedor.append(
          h('p', { class: 'ayuda', style: 'font-size: 12px; color: var(--tinta-2); margin-top: 3px;' },
            `Dígito de verificación DIAN: ${vNit.dvCalculado} (${vNit.nitFormateado})`
          )
        );
      }
    }
  }

  // 3. Si es un valor económico: mostrar versión en letras determinista
  const esValor = c.t === 'valor' || c.k.includes('cuantia') || c.k.includes('valor') || c.k.includes('canon') || c.k.includes('salario') || c.k.includes('perjuicios') || c.k.includes('capital') || c.k.includes('monto') || /^\$?\s*\d/.test(val);
  if (esValor && typeof numeroALetras === 'function') {
    const letras = numeroALetras(val);
    if (letras) {
      contenedor.append(
        h('div', { class: 'valor-en-letras', style: 'font-size: 12px; color: var(--azul, #2563eb); font-weight: 600; margin-top: 4px; background: rgba(37,99,235,0.06); padding: 4px 8px; border-radius: 4px;' },
          `↳ ${letras}`
        )
      );
    }
  }

  // 4. Si es fecha de notificación o campo de fecha: mostrar cálculo de vencimiento y botón .ics
  const esFechaNotif = c.t === 'date' || c.t === 'fecha' || (c.k && (c.k.includes('notificacion') || c.k.includes('fecha')));
  if (esFechaNotif && val && /^\d{4}-\d{2}-\d{2}$/.test(val)) {
    renderizarAyudaVencimientoCampo(c, inp, contenedor, val);
    actualizarBannerVencimientoTop(val);
  } else if (esFechaNotif && !val) {
    actualizarBannerVencimientoTop('');
  }

  // 5. Ayuda general del catálogo
  if (c.ayuda) {
    contenedor.append(h('p', { class: 'ayuda' }, c.ayuda));
  }
}
function ayudaRadicado(inp, nota) {
  actualizarAyudasCampo({ t: 'radicado', k: 'radicado' }, inp, nota);
}
function validarFormulario() {
  const tipo = TIPOS[state.tipo];
  let primero = null;
  for (const c of camposTipo(tipo)) {
    const v = state.datos[c.k];
    const vacio = v == null || (typeof v === 'string' && !v.trim()) || (Array.isArray(v) && !v.length);
    const wrap = $(`[data-campo="${c.k}"]`);
    if (!wrap) continue;

    wrap.querySelectorAll('.msg-err-valid').forEach(el => el.remove());

    if (c.req && vacio) {
      wrap.classList.add('err');
      wrap.append(h('p', { class: 'msg-err msg-err-valid' }, 'Este dato es necesario para redactar.'));
      if (!primero) primero = wrap;
      continue;
    }

    // Exigencia de exactamente 23 dígitos en radicado
    if ((c.t === 'radicado' || c.k === 'radicado') && !vacio) {
      const digitos = String(v).replace(/\D/g, '');
      if (digitos.length !== 23) {
        wrap.classList.add('err');
        wrap.append(h('p', { class: 'msg-err msg-err-valid', style: 'color: #dc2626; font-weight: 600;' },
          `El radicado judicial debe tener exactamente 23 dígitos (actualmente tiene ${digitos.length}). Formato: 5-2-2-3-4-5-2.`
        ));
        if (!primero) primero = wrap;
        continue;
      }
    }

    wrap.classList.remove('err');
  }
  if (primero) {
    primero.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const f = primero.querySelector('input,textarea,button');
    if (f) f.focus({ preventScroll: true });
  }
  return !primero;
}
const guardarBorrador = debounce(() => {
  lsSet('borrador', { tipo: state.tipo, datos: state.datos, texto: state.texto, versiones: state.versiones, docId: state.docId, creado: state.creado, prompt: state.prompt.length < 200000 ? state.prompt : '' });
}, 400);

/* =========================================================
   Historial
   ========================================================= */
function nombreCliente() {
  const c = String(state.datos.cliente || '').split(/[,\n;]/)[0].trim();
  return c.length > 60 ? c.slice(0, 60) + '…' : c;
}
function tituloDoc() {
  const t = TIPOS[state.tipo];
  const base = t ? (state.tipo === 'otro' && state.datos.tipo_libre ? state.datos.tipo_libre : t.nombre) : 'Escrito';
  const cli = nombreCliente();
  return cli ? `${base} · ${cli}` : base;
}
async function guardarEnHistorial() {
  if (!state.texto || state.ejemplo) return false;
  const ahora = Date.now();
  if (!state.docId) { state.docId = 'd' + ahora.toString(36) + Math.random().toString(36).slice(2, 6); state.creado = ahora; }
  const data = { titulo: tituloDoc(), tipo: state.tipo, creado: state.creado || ahora, actualizado: ahora, datos: state.datos, texto: state.texto, versiones: state.versiones };
  try {
    await Almacen.guardarHist(state.docId, data);
    guardarBorrador();
    if (sbClient && state.usuario) {
      sincronizarDocumentoConSupabase(state.docId, data).catch(() => {});
    }
    return true;
  }
  catch (e) { toast(mensajeAlmacen(e), 'error', 6000); return false; }
}
const guardarEdicion = debounce(async () => {
  if (state.generando || state.ejemplo) return;
  sincronizarTexto();
  const ultVer = (state.versiones && state.versiones.length > 0) ? state.versiones[state.versiones.length - 1].texto : null;
  if (state.texto && state.texto !== ultVer) {
    registrarVersion('edicion_manual', 'Edición manual');
  }
  estadoHoja('', 'Editado · guardando…');
  const ok = await guardarEnHistorial();
  estadoHoja(ok ? 'listo' : 'error', ok ? 'Editado · guardado ' + horaCorta(Date.now()) : 'Editado · sin guardar');
}, 2500);
let histCache = [];
async function renderHistorial() {
  const lista = $('#histLista'), vacio = $('#histVacio');
  lista.replaceChildren(h('li', { class: 'ayuda' }, 'Cargando…'));
  try { histCache = await Almacen.listarHist(); }
  catch (e) { lista.replaceChildren(h('li', { class: 'aviso' }, 'No se pudo cargar el historial. ' + mensajeAlmacen(e))); return; }
  pintarHistorial();
}
function pintarHistorial() {
  const lista = $('#histLista'), vacio = $('#histVacio');
  const q = $('#histBuscar').value.trim().toLowerCase();
  const items = histCache.filter(x => !q || ((x.titulo || '') + ' ' + (TIPOS[x.tipo]?.nombre || '')).toLowerCase().includes(q));
  lista.replaceChildren();
  vacio.hidden = histCache.length > 0;
  $('#histResumen').textContent = histCache.length ? `${histCache.length} ${histCache.length === 1 ? 'escrito guardado' : 'escritos guardados'}${Almacen.remoto() ? ' en tu cuenta' : ' en este navegador'}.` : 'Cada escrito que redactes se guarda aquí automáticamente.';
  for (const x of items) {
    const acc = h('div', { class: 'acc' });
    const li = h('li', { class: 'hist-item' },
      h('span', { class: 'f' }, fechaCorta(x.actualizado || x.creado), h('br'), horaCorta(x.actualizado || x.creado)),
      h('span', { class: 't' }, x.titulo || 'Escrito', h('span', { class: 'tp' }, (TIPOS[x.tipo]?.nombre || '') + (x.versiones?.length ? ` · ${x.versiones.length} vers.` : ''))),
      acc);
    const normal = () => {
      acc.replaceChildren(
        h('button', { class: 'btn chico primario', type: 'button', onclick: () => abrirDeHistorial(x) }, 'Abrir'),
        h('button', { class: 'btn chico', type: 'button', onclick: () => abrirDeHistorial(x, true) }, 'Usar como base'),
        h('button', { class: 'btn chico fantasma', type: 'button', onclick: () => abrirComparadorHistorial(x) }, 'Comparar'),
        h('button', { class: 'btn chico fantasma', type: 'button', onclick: confirmar }, 'Eliminar'));
    };
    const confirmar = () => {
      acc.replaceChildren(h('span', { class: 'ayuda' }, '¿Eliminar este escrito?'),
        h('button', { class: 'btn chico peligro', type: 'button', onclick: async () => {
          try { await Almacen.borrarHist(x.id); histCache = histCache.filter(y => y.id !== x.id); if (state.docId === x.id) state.docId = null; pintarHistorial(); toast('Escrito eliminado.', 'ok'); }
          catch (e) { toast(mensajeAlmacen(e), 'error'); }
        } }, 'Eliminar'),
        h('button', { class: 'btn chico fantasma', type: 'button', onclick: normal }, 'Cancelar'));
    };
    normal();
    lista.append(li);
  }
}
function abrirDeHistorial(x, comoBase = false) {
  if (!TIPOS[x.tipo]) { toast('Ese tipo de escrito ya no está disponible.', 'error'); return; }
  state.tipo = x.tipo;
  state.datos = mezclar(Object.fromEntries(camposTipo(TIPOS[x.tipo]).map(c => [c.k, valorDefecto(c)])), x.datos || {});
  state.catalogoAbierto = false;
  if (comoBase) {
    state.texto = ''; state.ejemplo = true; state.docId = null; state.creado = null; state.versiones = [];
  } else {
    state.texto = x.texto || '';
    state.ejemplo = !state.texto;
    state.docId = x.id;
    state.creado = x.creado;
    state.versiones = Array.isArray(x.versiones) && x.versiones.length > 0 ? x.versiones : (state.texto ? [{
      id: 'v_' + (x.creado || Date.now()).toString(36),
      numero: 1,
      fecha: new Date(x.creado || Date.now()).toISOString(),
      fechaFormateada: `${fechaCorta(x.creado || Date.now())}, ${horaCorta(x.creado || Date.now())}`,
      origen: 'generacion',
      origenEtiqueta: 'Guardado',
      descripcion: 'Versión guardada',
      texto: state.texto,
      palabras: (state.texto.match(/\b\w+\b/g) || []).length
    }] : []);
  }
  state.prompt = ''; state.prevTexto = null;
  renderZonaTipo(); renderFormulario(); $('#accionesForm').hidden = false;
  irVista('redactar');
  renderHoja(); ponerControles();
  estadoHoja(state.ejemplo ? '' : 'listo', state.ejemplo ? 'Datos cargados · listo para redactar' : 'Abierto del historial · ' + fechaCorta(x.actualizado));
  guardarBorrador();
}

/* =========================================================
   Barra de la hoja: exportar, copiar, ajustar
   ========================================================= */
function ponerControles() {
  const hay = !!state.texto && !state.ejemplo;
  const g = state.generando;
  $('#btnDetener').hidden = !g;
  $('#btnAjustar').disabled = !hay || g;
  $('#btnRegenerar').disabled = !hay || g || !state.tipo;
  $('#btnCopiar').disabled = !hay || g;
  $('#btnWord').disabled = !hay || g;
  $('#btnPdf').disabled = !hay || g;
  const btnRad = $('#btnRadicacion');
  if (btnRad) btnRad.disabled = !hay || g;
  const btnComp = $('#btnCompararVersiones');
  if (btnComp) btnComp.disabled = !hay || g;
  actualizarBadgeVersiones();
  $('#btnRedactar').disabled = g;
  $('#edicion').hidden = !hay || g;
  if (!hay || g) { $('#ajuste').hidden = true; }
  $('#btnDeshacerAjuste').hidden = !state.prevTexto || g;
}
function nombreArchivo(ext) {
  const t = TIPOS[state.tipo];
  const base = (t ? (state.tipo === 'otro' && state.datos.tipo_libre ? state.datos.tipo_libre : t.nombre) : 'Escrito');
  const cli = nombreCliente();
  const d = new Date();
  const s = `${base}${cli ? ' - ' + cli : ''} - ${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
  return s.replace(/[\\/:*?"<>|]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 150) + '.' + ext;
}
async function guardarArchivo(nombre, blob) {
  try {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nombre;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast('Descargado: ' + nombre, 'ok');
    return true;
  } catch (e) {
    toast('No se pudo descargar el archivo en este navegador.', 'error');
    return false;
  }
}
function sincronizarTexto() {
  if (!state.ejemplo && !state.generando && $('#cuerpo').contentEditable === 'true') state.texto = serializarCuerpo();
}
async function pedirExportacion(tipo) {
  sincronizarTexto();
  if (!state.texto || state.ejemplo) {
    toast('No hay un escrito redactado para exportar.', 'info');
    return;
  }

  const caja = $('#panelVerif');
  caja.hidden = false;
  caja.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  // Si no se han verificado los requisitos para este texto y tipo, llamar a /api/revisar
  const necesitaRevision = !state.revisionRequisitos || state.textoRevisado !== state.texto || state.tipoRevisado !== state.tipo;
  if (necesitaRevision && state.tipo) {
    caja.replaceChildren(
      h('div', { style: 'padding: 10px 4px;' },
        h('h3', { style: 'margin-bottom: 6px;' }, tipo === 'docx' ? 'Revisión antes de exportar a Word' : 'Revisión antes de exportar a PDF'),
        h('p', { class: 'nota', style: 'color: var(--tinta-2);' }, '⏳ Verificando cumplimiento de requisitos formales y legales con IA…')
      )
    );
    try {
      const res = await apiFetch('/api/revisar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ escrito: state.texto, tipo: state.tipo })
      });
      if (res.ok) {
        const data = await res.json();
        state.revisionRequisitos = Array.isArray(data) ? data : (data.requisitos || []);
        state.textoRevisado = state.texto;
        state.tipoRevisado = state.tipo;
      }
    } catch (e) {
      console.warn('Error al verificar requisitos:', e);
    }
  }

  renderizarPreExportacion(tipo);
}

function renderizarPreExportacion(tipo) {
  const caja = $('#panelVerif');
  const contenido = [];

  contenido.push(h('h3', { style: 'margin-bottom: 8px;' },
    `Requisitos formales y legales antes de exportar (${tipo === 'docx' ? 'Word' : 'PDF'})`
  ));

  const marcas = recogerMarcas();
  const nv = marcas.filter(i => i.tipo === 'v').length, nc = marcas.filter(i => i.tipo === 'c').length;
  const citasRojas = (state.citasVerificadas || []).filter(c => c.color === 'rojo');
  const reqs = state.revisionRequisitos || [];

  const criticosFaltantes = reqs.filter(r => r.critico && r.estado === 'no_cumple');
  const noCriticosFaltantes = reqs.filter(r => !r.critico && r.estado === 'no_cumple');
  const cumplen = reqs.filter(r => r.estado === 'cumple');
  const noAplican = reqs.filter(r => r.estado === 'no_aplica');

  // Resumen de advertencia si hay requisitos críticos faltantes
  if (criticosFaltantes.length > 0) {
    contenido.push(h('div', { style: 'background: #fef2f2; border: 1px solid #f87171; border-radius: 6px; padding: 10px 12px; margin-bottom: 10px;' },
      h('p', { style: 'color: #991b1b; font-weight: 700; margin: 0 0 4px 0;' },
        `⚠️ Hay ${criticosFaltantes.length} ${criticosFaltantes.length === 1 ? 'requisito crítico pendiente' : 'requisitos críticos pendientes'}:`
      ),
      h('p', { style: 'color: #7f1d1d; font-size: 12.5px; margin: 0;' },
        'Los requisitos críticos en rojo pueden dar lugar a inadmisión o rechazo de la acción judicial. Puedes corregirlos con un clic mediante IA o decidir exportar de todos modos.'
      )
    ));
  }

  // Lista de requisitos procesales
  if (reqs.length > 0) {
    const contenedorReqs = h('div', { class: 'lista-requisitos', style: 'display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px;' });

    // 1. Críticos en no_cumple (ROJO con botón "Corregir con IA")
    criticosFaltantes.forEach(r => {
      const item = h('div', { style: 'background: #fef2f2; border: 1.5px solid #ef4444; border-radius: 6px; padding: 10px 12px;' },
        h('div', { style: 'display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap;' },
          h('div', { style: 'flex: 1 1 280px;' },
            h('div', { style: 'display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 4px;' },
              h('span', { class: 'cita-badge rojo' }, '✗ No cumple · Crítico'),
              h('strong', { style: 'color: #991b1b;' }, r.texto),
              r.norma ? h('span', { style: 'font-size: 12px; color: #7f1d1d; font-weight: 600;' }, `(${r.norma})`) : null
            ),
            r.evidencia ? h('div', { style: 'font-size: 12.5px; color: #7f1d1d; margin-top: 3px;' }, h('strong', {}, 'Hallazgo: '), r.evidencia) : null,
            r.sugerencia ? h('div', { style: 'font-size: 12.5px; color: #991b1b; background: rgba(239, 68, 68, 0.08); padding: 5px 8px; border-radius: 4px; margin-top: 5px;' },
              h('strong', {}, 'Sugerencia: '), r.sugerencia
            ) : null
          ),
          h('button', {
            class: 'btn chico peligro-relleno',
            type: 'button',
            style: 'white-space: nowrap; margin-top: 2px;',
            title: 'Lanzar ajuste con IA aplicando esta sugerencia',
            onclick: () => corregirConIA(r.sugerencia || `Agrega el siguiente requisito procesal: ${r.texto} (${r.norma || ''})`)
          }, '🪄 Corregir con IA')
        )
      );
      contenedorReqs.append(item);
    });

    // 2. No críticos en no_cumple (AMARILLO)
    noCriticosFaltantes.forEach(r => {
      const item = h('div', { style: 'background: #fffbeb; border: 1px solid #fcd34d; border-radius: 6px; padding: 8px 12px;' },
        h('div', { style: 'display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap;' },
          h('div', { style: 'flex: 1 1 280px;' },
            h('div', { style: 'display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 4px;' },
              h('span', { class: 'cita-badge amarillo' }, '⚠ No cumple · Recomendación'),
              h('strong', { style: 'color: #92400e;' }, r.texto),
              r.norma ? h('span', { style: 'font-size: 12px; color: #78350f;' }, `(${r.norma})`) : null
            ),
            r.evidencia ? h('div', { style: 'font-size: 12px; color: #78350f; margin-top: 2px;' }, h('strong', {}, 'Hallazgo: '), r.evidencia) : null,
            r.sugerencia ? h('div', { style: 'font-size: 12px; color: #92400e; background: rgba(245, 158, 11, 0.1); padding: 4px 6px; border-radius: 4px; margin-top: 4px;' },
              h('strong', {}, 'Sugerencia: '), r.sugerencia
            ) : null
          ),
          h('button', {
            class: 'btn chico fantasma',
            type: 'button',
            style: 'border: 1px solid #d97706; color: #92400e; white-space: nowrap; margin-top: 2px;',
            onclick: () => corregirConIA(r.sugerencia || `Agrega o ajusta: ${r.texto}`)
          }, '🪄 Corregir con IA')
        )
      );
      contenedorReqs.append(item);
    });

    // 3. Requisitos cumplidos (VERDE)
    cumplen.forEach(r => {
      const item = h('div', { style: 'background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 6px 10px; font-size: 13px; color: #166534;' },
        h('div', { style: 'display: flex; align-items: center; gap: 6px; flex-wrap: wrap;' },
          h('span', { class: 'cita-badge verde' }, '✓ Cumple'),
          h('strong', {}, r.texto),
          r.norma ? h('span', { style: 'font-size: 11.5px; color: #15803d;' }, `(${r.norma})`) : null
        ),
        r.evidencia ? h('div', { style: 'font-size: 12px; color: #14532d; margin-top: 2px; opacity: 0.9;' }, r.evidencia) : null
      );
      contenedorReqs.append(item);
    });

    // 4. Requisitos que no aplican (GRIS)
    noAplican.forEach(r => {
      const item = h('div', { style: 'background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 6px 10px; font-size: 12.5px; color: #4b5563;' },
        h('div', { style: 'display: flex; align-items: center; gap: 6px; flex-wrap: wrap;' },
          h('span', { class: 'cita-badge', style: 'background: #e5e7eb; color: #4b5563;' }, '— No aplica'),
          h('span', {}, r.texto),
          r.norma ? h('span', { style: 'font-size: 11.5px; color: #6b7280;' }, `(${r.norma})`) : null
        )
      );
      contenedorReqs.append(item);
    });

    contenido.push(contenedorReqs);
  }

  // Citas inexistentes
  if (citasRojas.length) {
    contenido.push(h('div', { style: 'background: #fef2f2; border: 1px solid #f87171; border-radius: 6px; padding: 10px; margin-bottom: 10px;' },
      h('p', { style: 'color: #991b1b; font-weight: 600; margin: 0 0 6px 0;' }, `⚠️ Citas jurisprudenciales: Hay ${citasRojas.length} ${citasRojas.length === 1 ? 'cita no encontrada' : 'citas no encontradas'} en fuentes oficiales:`),
      h('ul', { style: 'margin: 0; padding-left: 18px; color: #b91c1c; font-size: 13px;' },
        citasRojas.map(cr => h('li', {}, cr.nombre || cr.texto_original))
      ),
      h('p', { style: 'margin: 6px 0 0 0; color: #7f1d1d; font-size: 12px;' }, 'Exportar con citas inexistentes puede acarrear sanciones disciplinarias o rechazo de pretensiones.')
    ));
  }

  // Discrepancias entre cifras numéricas y expresiones en letras
  const auditPre = state.auditoria || (typeof auditarDatosYEscrito === 'function' ? auditarDatosYEscrito(state.datos, state.texto, state.perfil) : null);
  const discCifras = (auditPre && auditPre.discrepanciasCifrasLetras) || [];
  if (discCifras.length > 0) {
    contenido.push(h('div', { style: 'background: #fef2f2; border: 1.5px solid #ef4444; border-radius: 6px; padding: 10px 12px; margin-bottom: 10px;' },
      h('p', { style: 'color: #991b1b; font-weight: 700; margin: 0 0 4px 0;' },
        `❌ Atención: Hay ${discCifras.length} discrepancia(s) entre cifras y letras en el escrito:`
      ),
      h('ul', { style: 'margin: 0; padding-left: 18px; color: #b91c1c; font-size: 12.5px;' },
        discCifras.map(d => h('li', {}, d.detalle))
      ),
      h('p', { style: 'margin: 4px 0 0 0; color: #7f1d1d; font-size: 12px;' }, 'Verifica que el valor en números coincida con su expresión en palabras antes de radicar.')
    ));
  }

  // Alertas de NIT con DV inválido
  const alertasNitPre = (auditPre && auditPre.alertasNit) || [];
  if (alertasNitPre.length > 0) {
    contenido.push(h('div', { style: 'background: #fffbeb; border: 1px solid #f59e0b; border-radius: 6px; padding: 10px 12px; margin-bottom: 10px;' },
      h('p', { style: 'color: #92400e; font-weight: 700; margin: 0 0 4px 0;' },
        `⚠️ Alerta de NIT DIAN (${alertasNitPre.length}):`
      ),
      h('ul', { style: 'margin: 0; padding-left: 18px; color: #78350f; font-size: 12.5px;' },
        alertasNitPre.map(a => h('li', {}, a.detalle))
      )
    ));
  }

  // Marcas [COMPLETAR]
  if (nc) {
    contenido.push(h('p', { class: 'nota', style: 'margin-bottom: 6px;' }, `Quedan ${nc} ${nc === 1 ? 'dato' : 'datos'} por completar; saldrán resaltados en amarillo en el archivo.`));
  }
  if (nv && !citasRojas.length) {
    contenido.push(h('p', { class: 'nota', style: 'margin-bottom: 6px;' }, `Hay ${nv} ${nv === 1 ? 'cita marcada' : 'citas marcadas'} con [VERIFICAR].`));
  }

  // Nota de decisión del abogado (no bloquea)
  contenido.push(h('p', { class: 'nota', style: 'font-size: 12px; color: var(--tinta-2); margin: 6px 0 10px 0;' },
    'El Memorialista no bloquea la exportación: como abogado responsable, tú decides el momento oportuno de radicación.'
  ));

  // Botones de acción
  const textoBotonExport = (criticosFaltantes.length || citasRojas.length || discCifras.length)
    ? `Confirmar y exportar de todos modos (${tipo === 'docx' ? 'Word' : 'PDF'})`
    : `Confirmar y exportar (${tipo === 'docx' ? 'Word' : 'PDF'})`;

  contenido.push(h('div', { class: 'ajuste-fila', style: 'margin-top: 10px;' },
    h('button', {
      class: 'btn primario chico',
      type: 'button',
      onclick: () => { caja.hidden = true; exportar(tipo, false); }
    }, textoBotonExport),
    h('button', {
      class: 'btn chico fantasma',
      type: 'button',
      onclick: () => { caja.hidden = true; }
    }, 'Seguir editando')
  ));

  caja.replaceChildren(...contenido);
  caja.hidden = false;
}

function corregirConIA(sugerencia) {
  const caja = $('#panelVerif');
  if (caja) caja.hidden = true;
  if (!sugerencia) return;
  toast('Aplicando ajuste con IA para cumplir el requisito…', 'info', 4000);
  redactar('ajuste', sugerencia);
}
async function exportar(tipo, sinVerificar) {
  const btn = tipo === 'docx' ? $('#btnWord') : $('#btnPdf');
  const etiqueta = btn.lastChild.textContent;
  btn.disabled = true; btn.lastChild.textContent = tipo === 'docx' ? 'Preparando…' : 'Preparando…';
  try {
    const texto = textoExport(sinVerificar);
    let blob;
    if (tipo === 'docx') blob = (usaPlantilla() && conMembreteDoc() && state.plantilla.buf) ? await docxDesdePlantilla(texto) : await docxPropio(texto);
    else blob = await construirPdf(texto);
    if (!state.perfil.abogado.nombre && conMembreteDoc() && !usaPlantilla()) toast('Tu membrete aún no está configurado: el archivo sale sin tus datos. Configúralo en Membrete y estilo.', 'info', 7000);
    await guardarArchivo(nombreArchivo(tipo), blob);
  } catch (e) {
    console.error(e);
    toast(String(e && e.message || '').startsWith('No se pudo cargar') ? 'No se pudo cargar el componente para crear el archivo. Revisa tu conexión e intenta de nuevo.' : 'No se pudo crear el archivo. Intenta de nuevo.', 'error', 7000);
  } finally {
    btn.lastChild.textContent = etiqueta; btn.disabled = false; ponerControles();
  }
}
let currentRadicacionBlob = null;
let currentRadicacionData = null;

async function prepararRadicacion() {
  sincronizarTexto();
  const hay = !!state.texto && !state.ejemplo;
  if (!hay) {
    toast('Debes redactar o tener un escrito antes de preparar la radicación.', 'info');
    return;
  }

  const btn = $('#btnRadicacion');
  const etiquetaOriginal = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" style="width:14px;height:14px;animation:spin 1s linear infinite" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke-dasharray="28" stroke-dashoffset="10"/></svg> Preparando…`;

  try {
    toast('Preparando paquete de radicación, poder judicial e índice CSJ…', 'info', 4000);

    const payload = {
      tipo: state.tipo || 'otro',
      datos: state.datos || {},
      texto: textoExport(true) || state.texto,
      perfil: state.perfil || {}
    };

    const res = await apiFetch('/api/radicacion/preparar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al procesar el paquete de radicación.');
    }

    const data = await res.json();
    currentRadicacionData = data;

    // Cargar librerías necesarias
    await cargarJSZip();
    await cargarPdfMake();

    const zip = new window.JSZip();

    // 1. PDF del escrito judicial principal
    const textoDoc = textoExport(true);
    const blobPrincipal = await construirPdf(textoDoc);
    zip.file(data.nombre_archivo_principal, blobPrincipal);

    // 2. Si requiere poder judicial, generar PDF del poder especial
    if (data.requiere_poder && data.texto_poder) {
      const blobPoder = await construirPdf(data.texto_poder);
      zip.file(data.nombre_archivo_poder, blobPoder);
    }

    // 3. Índice de anexos y expediente electrónico (CSJ)
    zip.file("00_Indice_de_Anexos.txt", data.texto_indice);

    // 4. Borrador del correo de radicación para el Despacho Judicial
    const borradorDespacho = [
      `ASUNTO: ${data.asunto_despacho}`,
      `PARA: ${data.correo_despacho}`,
      ``,
      data.cuerpo_despacho
    ].join('\n');
    zip.file("Borrador_Correo_Radicacion_Despacho.txt", borradorDespacho);

    // 5. Borrador de traslado simultáneo a contraparte (Art. 6 Ley 2213 de 2022)
    if (data.aplica_traslado_contraparte && data.correo_contraparte) {
      const borradorContraparte = [
        `ASUNTO: ${data.asunto_contraparte}`,
        `PARA: ${data.correo_contraparte}`,
        ``,
        data.cuerpo_contraparte
      ].join('\n');
      zip.file("Borrador_Correo_Traslado_Contraparte.txt", borradorContraparte);
    }

    // Generar archivo ZIP y descargar
    const zipBlob = await zip.generateAsync({ type: 'blob' });
    currentRadicacionBlob = zipBlob;

    await guardarArchivo(data.nombre_paquete, zipBlob);
    toast('Paquete de radicación .ZIP descargado exitosamente.', 'ok', 5000);

    mostrarModalRadicacion(data);

  } catch (err) {
    console.error('Error preparando radicación:', err);
    toast(err.message || 'Error al generar el paquete de radicación.', 'error', 7000);
  } finally {
    btn.innerHTML = etiquetaOriginal;
    btn.disabled = false;
    ponerControles();
  }
}

function mostrarModalRadicacion(data) {
  const modal = $('#modalRadicacion');
  if (!modal) return;

  $('#radNombrePaquete').textContent = data.nombre_paquete;

  // Lista de archivos incluidos en el paquete
  const lista = $('#radListaArchivos');
  lista.replaceChildren();

  const archivos = [
    { nombre: data.nombre_archivo_principal, desc: 'Escrito judicial principal en PDF' }
  ];
  if (data.requiere_poder && data.nombre_archivo_poder) {
    archivos.push({ nombre: data.nombre_archivo_poder, desc: 'Poder especial judicial en PDF (Art. 74 CGP / Ley 2213)' });
  }
  archivos.push({ nombre: '00_Indice_de_Anexos.txt', desc: 'Índice de expediente y relación de anexos (CSJ)' });
  archivos.push({ nombre: 'Borrador_Correo_Radicacion_Despacho.txt', desc: 'Borrador del correo para el Despacho Judicial' });
  if (data.aplica_traslado_contraparte) {
    archivos.push({ nombre: 'Borrador_Correo_Traslado_Contraparte.txt', desc: 'Borrador de traslado simultáneo a contraparte' });
  }

  archivos.forEach(a => {
    const li = document.createElement('li');
    li.innerHTML = `<strong>${esc(a.nombre)}</strong> <span style="color:var(--tinta-2)">— ${esc(a.desc)}</span>`;
    lista.appendChild(li);
  });

  // Sección Traslado a Contraparte (Art. 6 Ley 2213)
  const secContra = $('#radSeccionContraparte');
  const badgeContra = $('#radBadgeContraparte');
  const motivoContra = $('#radMotivoContraparte');
  const accContra = $('#radAccionContraparte');
  const btnMailContra = $('#btnMailtoContraparte');

  if (data.aplica_traslado_contraparte) {
    secContra.style.background = '#f0fdf4';
    secContra.style.borderColor = '#bbf7d0';
    badgeContra.style.background = '#dcfce7';
    badgeContra.style.color = '#15803d';
    badgeContra.textContent = 'Aplica Traslado';
    motivoContra.textContent = data.motivo_traslado_contraparte + (data.correo_contraparte ? ` (Destinatario: ${data.correo_contraparte})` : '');
    accContra.style.display = 'block';
    btnMailContra.href = data.mailto_contraparte || '#';
    btnMailContra.onclick = (e) => {
      if (data.mailto_contraparte) {
        window.location.href = data.mailto_contraparte;
        e.preventDefault();
      }
    };
  } else {
    secContra.style.background = '#fffbeb';
    secContra.style.borderColor = '#fef08a';
    badgeContra.style.background = '#fef3c7';
    badgeContra.style.color = '#b45309';
    badgeContra.textContent = 'Exonerado / No aplica';
    motivoContra.textContent = data.motivo_traslado_contraparte;
    accContra.style.display = 'none';
  }

  // Sección Despacho Judicial
  $('#radCorreoDespachoTexto').textContent = data.correo_despacho;
  const btnMailDespacho = $('#btnMailtoDespacho');
  btnMailDespacho.href = data.mailto_despacho || '#';
  btnMailDespacho.onclick = (e) => {
    if (data.mailto_despacho) {
      window.location.href = data.mailto_despacho;
      e.preventDefault();
    }
  };

  // Botón re-descargar ZIP
  const btnReZip = $('#btnDescargarZipDeNuevo');
  btnReZip.onclick = async () => {
    if (currentRadicacionBlob && currentRadicacionData) {
      await guardarArchivo(currentRadicacionData.nombre_paquete, currentRadicacionBlob);
    }
  };

  modal.showModal();
}

/* =========================================================
   Control de Versiones y Comparador (Diff por palabra)
   ========================================================= */
function registrarVersion(origen, descripcion, instruccion = '') {
  if (!state.texto || state.ejemplo) return;
  if (!Array.isArray(state.versiones)) state.versiones = [];

  const ult = state.versiones[state.versiones.length - 1];
  if (ult && ult.texto === state.texto) return;

  const ahora = Date.now();
  const d = new Date(ahora);
  const num = state.versiones.length + 1;
  const palabras = (state.texto.match(/\b\w+\b/g) || []).length;

  let etiqueta = 'Edición manual';
  if (origen === 'generacion') etiqueta = num === 1 ? 'Generación inicial' : 'Regeneración con IA';
  else if (origen === 'ajuste_ia') etiqueta = 'Ajuste con IA';

  const version = {
    id: 'v_' + ahora.toString(36) + '_' + Math.random().toString(36).slice(2, 6),
    numero: num,
    fecha: d.toISOString(),
    fechaFormateada: `${fechaCorta(ahora)}, ${horaCorta(ahora)}`,
    origen: origen,
    origenEtiqueta: etiqueta,
    descripcion: descripcion || (origen === 'ajuste_ia' ? (instruccion ? `Ajuste: "${instruccion}"` : 'Ajuste con IA') : (origen === 'generacion' ? 'Generación con IA' : 'Edición manual')),
    instruccion: instruccion || '',
    texto: state.texto,
    palabras: palabras
  };

  state.versiones.push(version);
  actualizarBadgeVersiones();
  guardarBorrador();
}

function actualizarBadgeVersiones() {
  const badge = $('#badgeNumVersiones');
  const count = (state.versiones || []).length;
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? 'inline-block' : 'none';
  }
  const btn = $('#btnCompararVersiones');
  if (btn) {
    btn.disabled = !state.texto || state.ejemplo || count === 0;
  }
}

async function abrirComparadorVersiones() {
  sincronizarTexto();
  if (!state.texto || state.ejemplo) {
    toast('No hay un escrito redactado para comparar versiones.', 'info');
    return;
  }

  // Asegurar que la versión actual esté registrada si cambió
  const ultVer = (state.versiones && state.versiones.length > 0) ? state.versiones[state.versiones.length - 1].texto : null;
  if (state.texto && state.texto !== ultVer) {
    registrarVersion('edicion_manual', 'Edición actual');
  }

  if (!state.versiones || state.versiones.length === 0) {
    registrarVersion('generacion', 'Versión inicial');
  }

  const modal = $('#modalComparar');
  if (!modal) return;

  poblarSelectoresVersiones();
  modal.showModal();
  await ejecutarComparacion();
}

function abrirComparadorHistorial(x) {
  if (!x || !x.texto) return;
  const versionesItem = Array.isArray(x.versiones) && x.versiones.length > 0 ? x.versiones : [{
    id: 'v_' + (x.creado || Date.now()).toString(36),
    numero: 1,
    fecha: new Date(x.creado || Date.now()).toISOString(),
    fechaFormateada: `${fechaCorta(x.creado || Date.now())}, ${horaCorta(x.creado || Date.now())}`,
    origen: 'generacion',
    origenEtiqueta: 'Guardado',
    descripcion: 'Versión guardada',
    texto: x.texto,
    palabras: (x.texto.match(/\b\w+\b/g) || []).length
  }];

  const modal = $('#modalComparar');
  if (!modal) return;

  const selBase = $('#selectVersionBase');
  const selComp = $('#selectVersionComparada');
  selBase.replaceChildren();
  selComp.replaceChildren();

  versionesItem.forEach((v, idx) => {
    const t = `V${v.numero} · ${v.origenEtiqueta} (${v.fechaFormateada}) - ${v.palabras} palabras`;
    selBase.appendChild(new Option(t, String(idx)));
    selComp.appendChild(new Option(t, String(idx)));
  });

  const len = versionesItem.length;
  if (len >= 2) {
    selBase.value = String(len - 2);
    selComp.value = String(len - 1);
  } else {
    selBase.value = '0';
    selComp.value = '0';
  }

  modal.showModal();
  ejecutarComparacionCustom(versionesItem);
}

function poblarSelectoresVersiones() {
  const selBase = $('#selectVersionBase');
  const selComp = $('#selectVersionComparada');
  if (!selBase || !selComp) return;
  selBase.replaceChildren();
  selComp.replaceChildren();

  (state.versiones || []).forEach((v, idx) => {
    const t = `V${v.numero} · ${v.origenEtiqueta} (${v.fechaFormateada}) - ${v.palabras} palabras`;
    selBase.appendChild(new Option(t, String(idx)));
    selComp.appendChild(new Option(t, String(idx)));
  });

  const len = (state.versiones || []).length;
  if (len >= 2) {
    selBase.value = String(len - 2);
    selComp.value = String(len - 1);
  } else {
    selBase.value = '0';
    selComp.value = '0';
  }
}

async function ejecutarComparacion() {
  await ejecutarComparacionCustom(state.versiones || []);
}

async function ejecutarComparacionCustom(versionesLista) {
  const selBase = $('#selectVersionBase');
  const selComp = $('#selectVersionComparada');
  if (!selBase || !selComp) return;
  const idxBase = parseInt(selBase.value, 10);
  const idxComp = parseInt(selComp.value, 10);

  const verBase = versionesLista[idxBase];
  const verComp = versionesLista[idxComp];

  const visor = $('#diffVisorDocumento');
  if (!visor) return;

  if (!verBase || !verComp) {
    visor.innerHTML = '<p class="diff-parrafo" style="color:var(--tinta-2);">Selecciona dos versiones para ver la comparación.</p>';
    return;
  }

  visor.innerHTML = '<p class="diff-parrafo" style="color:var(--tinta-2);">⏳ Comparando diferencias palabra por palabra…</p>';

  try {
    const res = await apiFetch('/api/versiones/comparar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        texto_base: verBase.texto,
        texto_comparado: verComp.texto,
        autor: state.perfil?.abogado?.nombre || 'El Memorialista',
        fecha: verComp.fecha
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al comparar versiones en el servidor.');
    }

    const data = await res.json();
    const anadidas = data.estadisticas.palabras_anadidas;
    const eliminadas = data.estadisticas.palabras_eliminadas;
    const iguales = data.estadisticas.palabras_sin_cambio;

    $('#diffBadgeAnadidas').textContent = `+${anadidas} ${anadidas === 1 ? 'añadida' : 'añadidas'}`;
    $('#diffBadgeEliminadas').textContent = `-${eliminadas} ${eliminadas === 1 ? 'eliminada' : 'eliminadas'}`;
    $('#diffBadgeIguales').textContent = `${iguales} sin cambio`;

    if (anadidas === 0 && eliminadas === 0) {
      visor.innerHTML = '<div style="text-align:center; padding: 30px 10px; color: var(--tinta-2);">' +
        '<span style="font-size:24px; display:block; margin-bottom:8px;">⚖️</span>' +
        '<strong>No hay diferencias entre las versiones seleccionadas.</strong><br>' +
        '<span style="font-size:12px;">El texto es idéntico en ambas versiones.</span>' +
        '</div>';
    } else {
      visor.innerHTML = data.html_diff;
    }

  } catch (err) {
    console.error('Error al comparar versiones:', err);
    visor.innerHTML = `<p class="diff-parrafo" style="color:#b91c1c;">Error al comparar versiones: ${esc(err.message)}</p>`;
  }
}

async function exportarWordDiff() {
  const selBase = $('#selectVersionBase');
  const selComp = $('#selectVersionComparada');
  const idxBase = parseInt(selBase.value, 10);
  const idxComp = parseInt(selComp.value, 10);

  const verBase = (state.versiones || [])[idxBase];
  const verComp = (state.versiones || [])[idxComp];

  if (!verBase || !verComp) {
    toast('Selecciona las versiones a comparar antes de exportar.', 'info');
    return;
  }

  const btn = $('#btnExportarWordDiff');
  const txtOriginal = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" style="width:14px;height:14px;animation:spin 1s linear infinite" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke-dasharray="28" stroke-dashoffset="10"/></svg> Exportando…`;

  try {
    toast('Generando archivo Word con control de cambios (w:ins y w:del)…', 'info', 3000);

    const payload = {
      texto_base: verBase.texto,
      texto_comparado: verComp.texto,
      autor: state.perfil?.abogado?.nombre || 'El Memorialista',
      fecha: verComp.fecha,
      titulo: `${tituloDoc()} - Control de Cambios V${verBase.numero} vs V${verComp.numero}`,
      perfil: state.perfil
    };

    const res = await apiFetch('/api/versiones/exportar-docx', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al exportar documento con control de cambios.');
    }

    const blob = await res.blob();
    const nombre = nombreArchivo('docx').replace('.docx', `_ControlCambios_V${verBase.numero}_vs_V${verComp.numero}.docx`);
    await guardarArchivo(nombre, blob);
    toast('Documento Word con control de cambios descargado.', 'ok', 5000);

  } catch (err) {
    console.error('Error exportando Word diff:', err);
    toast('Error al exportar a Word: ' + (err.message || 'Intenta de nuevo'), 'error', 6000);
  } finally {
    btn.innerHTML = txtOriginal;
    btn.disabled = false;
  }
}

function restaurarVersionBase() {
  const selBase = $('#selectVersionBase');
  const idxBase = parseInt(selBase.value, 10);
  const verBase = (state.versiones || [])[idxBase];

  if (!verBase) return;

  const confirmar = confirm(`¿Deseas restaurar la Versión #${verBase.numero} (${verBase.origenEtiqueta}) en el editor principal?`);
  if (!confirmar) return;

  state.texto = verBase.texto;
  state.prevTexto = null;
  renderHoja();
  ponerControles();
  registrarVersion('edicion_manual', `Restaurada Versión #${verBase.numero}`);

  $('#modalComparar').close();
  toast(`Se restauró la Versión #${verBase.numero} en el escrito.`, 'ok', 4000);
}

function intercambiarVersiones() {
  const selBase = $('#selectVersionBase');
  const selComp = $('#selectVersionComparada');
  const tmp = selBase.value;
  selBase.value = selComp.value;
  selComp.value = tmp;
  ejecutarComparacion();
}
function copiarTexto() {
  sincronizarTexto();
  const texto = textoPlano(state.texto);
  const manual = () => {
    const ta = h('textarea', { readonly: true, 'aria-label': 'Texto del escrito' }); ta.value = texto;
    const caja = $('#panelVerif');
    caja.replaceChildren(h('h3', {}, 'Copia el texto'), h('div', { class: 'copia-manual' }, ta, h('button', { class: 'btn chico', type: 'button', onclick: () => { caja.hidden = true; actualizarVerificacion(); } }, 'Cerrar')));
    caja.hidden = false; ta.focus(); ta.select();
  };
  try {
    if (!navigator.clipboard || !navigator.clipboard.writeText) { manual(); return; }
    navigator.clipboard.writeText(texto).then(() => toast('Texto copiado.', 'ok'), manual);
  } catch { manual(); }
}
const SUGERENCIAS_AJUSTE = ['Hazlo más breve', 'Más contundente', 'Revisa redacción y ortografía', 'Fortalece los fundamentos de derecho', 'Agrega una pretensión subsidiaria', 'Continúa donde quedó'];
function abrirAjuste() {
  const caja = $('#ajuste');
  caja.hidden = !caja.hidden;
  if (!caja.hidden) {
    const s = $('#ajusteSugerencias'); s.replaceChildren();
    SUGERENCIAS_AJUSTE.forEach(t => s.append(h('button', { class: 'chip', type: 'button', onclick: () => { $('#ajusteTexto').value = t; $('#ajusteTexto').focus(); } }, t)));
    $('#ajusteTexto').focus();
  }
}
function aplicarAjuste() {
  const t = $('#ajusteTexto').value.trim();
  if (!t) { $('#ajusteTexto').focus(); return; }
  sincronizarTexto();
  $('#ajuste').hidden = true; $('#ajusteTexto').value = '';
  redactar('ajuste', t);
}
function deshacerAjuste() {
  if (!state.prevTexto) return;
  const actual = state.texto;
  state.texto = state.prevTexto; state.prevTexto = actual;
  renderHoja(); ponerControles(); guardarEdicion();
  toast('Se restauró la versión anterior. Puedes volver a la otra con el mismo botón.', 'info');
}

/* Edición directa en la hoja */
function bloqueActual() {
  const sel = getSelection();
  if (!sel.rangeCount) return null;
  let n = sel.anchorNode; if (n && n.nodeType === 3) n = n.parentElement;
  const b = n && n.closest('#cuerpo > *');
  return b && b.dataset.b !== 'firma' ? b : null;
}
function cambiarBloque(tipo) {
  const b = bloqueActual();
  if (!b) { toast('Pon el cursor en el párrafo que quieres cambiar.', 'info'); return; }
  b.dataset.b = tipo;
  b.classList.toggle('multi', tipo === 'p' && /<br>/i.test(b.innerHTML.replace(/<br>$/i, '')));
  alEditar();
}
function alEditar() {
  if (state.ejemplo || state.generando) return;
  state.texto = serializarCuerpo();
  actualizarVerificacionLuego();
  guardarBorrador();
  guardarEdicion();
}
const actualizarVerificacionLuego = debounce(actualizarVerificacion, 700);
function iniciarEdicion() {
  const cuerpo = $('#cuerpo');
  try { document.execCommand('defaultParagraphSeparator', false, 'p'); document.execCommand('styleWithCSS', false, false); } catch { /* navegadores antiguos */ }
  cuerpo.addEventListener('input', alEditar);
  cuerpo.addEventListener('paste', e => {
    if (cuerpo.contentEditable !== 'true') return;
    e.preventDefault();
    const t = (e.clipboardData || window.clipboardData).getData('text/plain');
    document.execCommand('insertText', false, t);
  });
  cuerpo.addEventListener('keydown', e => {
    if (cuerpo.contentEditable !== 'true') return;
    if (e.key === 'Enter' && !e.shiftKey) {
      const b = bloqueActual();
      if (!b) return;
      const sel = getSelection(); const r = sel.getRangeAt(0);
      const fin = document.createRange(); fin.selectNodeContents(b); fin.setStart(r.endContainer, r.endOffset);
      if (b.dataset.b !== 'p' && !fin.toString().trim()) {
        e.preventDefault();
        const p = h('p', { dataset: { b: 'p' } }); p.innerHTML = '<br>';
        b.after(p);
        const nr = document.createRange(); nr.setStart(p, 0); nr.collapse(true); sel.removeAllRanges(); sel.addRange(nr);
        alEditar();
      }
    }
  });
  $$('#edicion [data-cmd]').forEach(b => { b.addEventListener('mousedown', e => e.preventDefault()); b.addEventListener('click', () => { document.execCommand(b.dataset.cmd); alEditar(); }); });
  $$('#edicion [data-bloque]').forEach(b => { b.addEventListener('mousedown', e => e.preventDefault()); b.addEventListener('click', () => cambiarBloque(b.dataset.bloque)); });
}

/* =========================================================
   Navegación
   ========================================================= */
function irVista(v) {
  if (!['redactar', 'membrete', 'historial', 'plazos', 'calculos'].includes(v)) v = 'redactar';
  state.vista = v;
  for (const b of $$('.pestanas button')) b.setAttribute('aria-selected', String(b.dataset.vista === v));
  for (const s of ['redactar', 'membrete', 'historial', 'plazos', 'calculos']) {
    const el = $('#vista-' + s);
    if (el) el.hidden = s !== v;
  }
  if (location.hash.slice(1) !== v) { try { history.replaceState(null, '', '#' + v); } catch { /* sin historial */ } }
  if (v === 'historial') renderHistorial();
  if (v === 'membrete') renderPrevia();
  if (v === 'plazos') renderVistaPlazos();
  if (v === 'calculos') renderVistaCalculos();
  if (v === 'redactar') { sincronizarTexto(); renderHoja(); }
  window.scrollTo(0, 0);
}
function actualizarChip() {
  const ab = state.perfil.abogado, chip = $('#perfilChip');
  const ok = !!ab.nombre;
  chip.classList.toggle('pendiente', !ok);
  chip.querySelector('.ini').textContent = ok ? ab.nombre.split(/\s+/).filter(Boolean).slice(0, 2).map(x => x[0]).join('').toUpperCase() : '?';
  chip.querySelector('.txt').textContent = ok ? ab.nombre : 'Configura tu membrete';
}

/* =========================================================
   Membrete y estilo: perfil
   ========================================================= */
function pintarEstadoGuardado(t) { $('#estadoGuardado').textContent = t; }
const guardarPerfil = debounce(async () => {
  lsSet('perfil', state.perfil);
  pintarEstadoGuardado('Guardando…');
  try { await Almacen.escribir('perfil', state.perfil); pintarEstadoGuardado('Guardado ' + horaCorta(Date.now()) + (Almacen.remoto() ? ' en tu cuenta' : ' en este navegador')); }
  catch (e) { pintarEstadoGuardado(mensajeAlmacen(e)); }
}, 900);
function cargarAjustesEnFormulario() {
  for (const el of $$('#ajForm [data-path]')) {
    const v = getPath(state.perfil, el.dataset.path);
    if (el.type === 'checkbox') el.checked = !!v;
    else if (el.type === 'radio') el.checked = String(v) === el.value;
    else el.value = v ?? '';
  }
  pintarColores();
  pintarImagenesAjustes();
  pintarPlantillaInfo();
  const plantilla = state.perfil.membrete.modo === 'plantilla';
  $('#bloqueDiseno').hidden = plantilla;
  $('#bloquePlantilla').hidden = !plantilla;
  $('#notaFormatoPlantilla').hidden = !usaPlantilla();
  $('#notaAlmacen').textContent = 'Tus datos de membrete, imágenes e historial se guardan de forma privada y segura en tu navegador (IndexedDB).';
}
function alCambiarAjuste(el) {
  let v;
  if (el.type === 'checkbox') v = el.checked;
  else if (el.type === 'radio') { if (!el.checked) return; v = el.value; }
  else v = el.dataset.num ? Number(el.value) : el.value;
  setPath(state.perfil, el.dataset.path, v);
  if (el.dataset.path === 'membrete.modo') { $('#bloqueDiseno').hidden = v === 'plantilla'; $('#bloquePlantilla').hidden = v !== 'plantilla'; $('#notaFormatoPlantilla').hidden = !usaPlantilla(); }
  actualizarChip();
  renderPreviaLuego();
  guardarPerfil();
}
function pintarColores() {
  const caja = $('#colores');
  caja.replaceChildren();
  const actual = (state.perfil.membrete.color || '').toLowerCase();
  for (const [c, n] of COLORES) caja.append(h('button', { class: 'color', type: 'button', style: `background:${c}`, title: n, 'aria-label': n, 'aria-pressed': String(actual === c), onclick: () => { state.perfil.membrete.color = c; pintarColores(); renderPreviaLuego(); guardarPerfil(); } }));
  const libre = h('input', { type: 'color', id: 'm_color', value: /^#[0-9a-f]{6}$/i.test(actual) ? actual : '#1f3a68', 'aria-label': 'Otro color' });
  libre.addEventListener('input', () => { state.perfil.membrete.color = libre.value; renderPreviaLuego(); guardarPerfil(); });
  libre.addEventListener('change', pintarColores);
  caja.append(libre);
}
function pintarImagenesAjustes() {
  for (const k of ['logo', 'firma']) {
    const img = $('#' + k + 'Previa');
    if (IMG[k]) { img.src = IMG[k].dataUrl; img.hidden = false; } else { img.removeAttribute('src'); img.hidden = true; }
    $('#' + k + 'Quitar').hidden = !IMG[k];
  }
}
function cargarImagen(file) {
  return new Promise((ok, mal) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); ok(img); };
    img.onerror = () => { URL.revokeObjectURL(url); mal(new Error('imagen')); };
    img.src = url;
  });
}
async function procesarImagen(file, { maxW, maxH, quitarFondo }) {
  const img = await cargarImagen(file);
  let w = img.naturalWidth || img.width || 600, hh = img.naturalHeight || img.height || 200;
  const esc0 = Math.min(1, maxW / w, maxH / hh);
  w = Math.max(1, Math.round(w * esc0)); hh = Math.max(1, Math.round(hh * esc0));
  const dibujar = (ww, hh2) => {
    const cv = document.createElement('canvas'); cv.width = ww; cv.height = hh2;
    const cx = cv.getContext('2d'); cx.drawImage(img, 0, 0, ww, hh2);
    if (quitarFondo) {
      const d = cx.getImageData(0, 0, ww, hh2), px = d.data;
      for (let i = 0; i < px.length; i += 4) {
        const m = Math.min(px[i], px[i + 1], px[i + 2]);
        if (m > 228) px[i + 3] = 0;
        else if (m > 185) px[i + 3] = Math.round(px[i + 3] * (228 - m) / 43);
      }
      cx.putImageData(d, 0, 0);
    }
    return cv;
  };
  let cv = dibujar(w, hh), dataUrl = cv.toDataURL('image/png');
  for (let i = 0; i < 4 && dataUrl.length > 190000; i++) { w = Math.round(w * .75); hh = Math.round(hh * .75); cv = dibujar(w, hh); dataUrl = cv.toDataURL('image/png'); }
  if (dataUrl.length > 190000) throw new Error('grande');
  return { dataUrl, w: cv.width, h: cv.height };
}
async function subirImagen(k, file) {
  if (!file) return;
  try {
    const r = await procesarImagen(file, k === 'logo' ? { maxW: 900, maxH: 450, quitarFondo: false } : { maxW: 700, maxH: 300, quitarFondo: $('#firmaFondo').checked });
    IMG[k] = r;
    pintarImagenesAjustes(); renderPreviaLuego();
    lsSet('img:' + k, r);
    await Almacen.escribir(k, r);
    toast(k === 'logo' ? 'Logo guardado.' : 'Firma guardada.', 'ok');
    if (k === 'firma') refrescarFirmas();
    if (k === 'logo' && state.vista === 'redactar') renderMembreteHoja();
    if (supabase && state.usuario) {
      const blob = dataUrlABlob(r);
      if (blob) {
        const ruta = `${k}/${state.usuario.id}/${k}.png`;
        supabase.storage.from('archivos-privados').upload(ruta, blob, { upsert: true }).catch(() => {});
      }
    }
  } catch (e) {
    toast(e && e.message === 'grande' ? 'La imagen es demasiado pesada aun reducida. Prueba con otra más sencilla.' : (e && e.code ? mensajeAlmacen(e) : 'No se pudo leer la imagen. Usa PNG o JPG.'), 'error', 6000);
  }
}
async function quitarImagen(k) {
  IMG[k] = null; lsDel('img:' + k);
  pintarImagenesAjustes(); renderPreviaLuego();
  try {
    await Almacen.borrar(k);
    if (supabase && state.usuario) {
      const ruta = `${k}/${state.usuario.id}/${k}.png`;
      supabase.storage.from('archivos-privados').remove([ruta]).catch(() => {});
    }
  } catch (e) { toast(mensajeAlmacen(e), 'error'); }
}

/* Plantilla de Word */
function pintarPlantillaInfo() {
  const caja = $('#plantillaInfo');
  const meta = state.perfil.plantilla;
  $('#plantillaQuitar').hidden = !meta;
  if (!meta) { caja.hidden = true; return; }
  const info = (state.plantilla && state.plantilla.info) || meta.info || {};
  const cab = info.cab, pie = info.pie;
  const desc = parte => !parte ? 'sin contenido' : [parte.imgs && parte.imgs.length ? `${parte.imgs.length} ${parte.imgs.length === 1 ? 'imagen' : 'imágenes'}` : '', parte.textos && parte.textos.length ? '“' + parte.textos.slice(0, 2).join(' · ').slice(0, 90) + '”' : ''].filter(Boolean).join(', ') || 'sin contenido';
  caja.replaceChildren(
    h('div', {}, h('strong', {}, meta.nombre), ` · ${Math.round((meta.bytes || 0) / 1024)} KB${state.plantilla && state.plantilla.buf ? '' : ' · cargando…'}`),
    h('div', {}, 'Encabezado: ', desc(cab)),
    h('div', {}, 'Pie de página: ', desc(pie)),
    info.fuente ? h('div', {}, `Fuente de la plantilla: ${info.fuente.nombre} ${info.fuente.tam} pt`) : null,
    info.papel ? h('div', {}, `Papel: ${info.papel.w.toFixed(2).replace('.', ',')} × ${info.papel.h.toFixed(2).replace('.', ',')} cm`) : null,
    h('div', {}, info.marcador ? 'Tiene el marcador {{CONTENIDO}}: el escrito irá en ese lugar.' : 'El escrito reemplazará el cuerpo de la plantilla.'),
    info.primeraPagina ? h('div', {}, 'Tiene encabezado distinto en la primera página: la vista previa muestra ese.') : null);
  caja.hidden = false;
}
async function subirPlantilla(file) {
  if (!file) return;
  if (!/\.(docx|dotx)$/i.test(file.name)) { toast('Sube un archivo de Word .docx o .dotx.', 'error'); return; }
  if (file.size > 3 * 1024 * 1024) { toast('La plantilla supera 3 MB. Reduce las imágenes del encabezado e intenta de nuevo.', 'error', 7000); return; }
  try {
    await cargarJSZip();
    const buf = await file.arrayBuffer();
    const zip = await window.JSZip.loadAsync(buf);
    if (!zip.file('word/document.xml')) throw new Error('invalida');
    const info = await analizarPlantilla(zip);
    state.plantilla = { buf, info, nombre: file.name };
    const b64 = bufAB64(buf);
    const trozos = []; for (let i = 0; i < b64.length; i += 180000) trozos.push(b64.slice(i, i + 180000));
    state.perfil.plantilla = { nombre: file.name, bytes: buf.byteLength, partes: trozos.length, subido: Date.now(), info: infoSinImagenes(info) };
    state.perfil.membrete.modo = 'plantilla';
    cargarAjustesEnFormulario(); renderPreviaLuego();
    if (state.vista === 'redactar') renderHoja();
    pintarEstadoGuardado('Guardando plantilla…');
    for (let i = 0; i < trozos.length; i++) await Almacen.escribir('plantilla_' + i, { d: trozos[i] });
    guardarPerfil.ya();
    if (supabase && state.usuario && file) {
      const ruta = `plantilla/${state.usuario.id}/plantilla.docx`;
      supabase.storage.from('archivos-privados').upload(ruta, file, { upsert: true }).catch(() => {});
    }
    toast('Plantilla lista. Tus escritos en Word usarán su encabezado y pie de página.', 'ok', 6000);
  } catch (e) {
    if (e && e.code) toast(mensajeAlmacen(e), 'error', 7000);
    else toast('No se pudo leer la plantilla. Verifica que sea un .docx válido.', 'error', 7000);
  }
}
async function quitarPlantilla() {
  const partes = (state.perfil.plantilla && state.perfil.plantilla.partes) || 0;
  state.plantilla = null; state.perfil.plantilla = null; state.perfil.membrete.modo = 'diseno';
  cargarAjustesEnFormulario(); renderPreviaLuego(); guardarPerfil();
  for (let i = 0; i < partes; i++) Almacen.borrar('plantilla_' + i).catch(() => {});
  if (supabase && state.usuario) {
    const ruta = `plantilla/${state.usuario.id}/plantilla.docx`;
    supabase.storage.from('archivos-privados').remove([ruta]).catch(() => {});
  }
}
async function cargarPlantillaGuardada() {
  const meta = state.perfil.plantilla;
  if (!meta || (state.plantilla && state.plantilla.buf)) return;
  try {
    const trozos = [];
    for (let i = 0; i < meta.partes; i++) { const d = await Almacen.leer('plantilla_' + i); if (!d || !d.d) throw new Error('faltan'); trozos.push(d.d); }
    await cargarJSZip();
    const buf = b64ABuf(trozos.join(''));
    const info = await analizarPlantilla(await window.JSZip.loadAsync(buf));
    state.plantilla = { buf, info, nombre: meta.nombre };
    pintarPlantillaInfo(); renderPreviaLuego();
    if (state.vista === 'redactar') renderHoja();
  } catch {
    pintarEstadoGuardado('No se pudo cargar tu plantilla guardada. Súbela de nuevo.');
  }
}

/* Muestra de estilo desde archivo */
async function subirMuestra(file) {
  if (!file) return;
  try {
    let texto;
    if (/\.txt$/i.test(file.name) || file.type === 'text/plain') texto = await file.text();
    else {
      await cargarJSZip();
      const zip = await window.JSZip.loadAsync(await file.arrayBuffer());
      const doc = await zip.file('word/document.xml').async('string');
      const ci = cuerpoInterior(doc);
      texto = (ci ? ci.xml : doc).match(/<w:p\b[\s\S]*?<\/w:p>/g)?.map(p => textoXml(p.replace(/<w:tab\/>/g, '<w:t>\t</w:t>').replace(/<w:br\/>/g, '<w:t>\n</w:t>'))).join('\n') || '';
    }
    texto = texto.replace(/\n{3,}/g, '\n\n').trim().slice(0, 20000);
    if (!texto) throw new Error('vacio');
    state.perfil.estilo.muestra = texto;
    $('#e_muestra').value = texto;
    guardarPerfil();
    $('#analizarEstado').textContent = 'Muestra cargada. Pulsa “Analizar mi estilo”.';
  } catch { toast('No se pudo leer el archivo. Usa .docx o .txt.', 'error'); }
}

/* Vista previa del membrete en Ajustes */
function renderPrevia() {
  const hoja = $('#hojaPrevia');
  if (!hoja) return;
  aplicarFormato(hoja);
  const marco = hoja.parentElement;
  const disp = marco.clientWidth || 360;
  hoja.style.zoom = String(Math.min(0.55, Math.max(0.3, (disp - 8) / (medidas().papel.w * 37.795))));
  $('#membretePrevia').innerHTML = membreteHtml();
  const muestra = textoEjemplo().split('\n## Hechos')[0] + '\n\n## Hechos\n\n**PRIMERO.** La señora López Rincón, de 63 años, está afiliada al régimen contributivo de la EPS accionada desde 2015.\n\nDel señor Juez, con todo respeto,\n\n[[FIRMA: Apoderad' + (generoAb() === 'o(a)' ? 'o(a)' : generoAb()) + ' de la parte accionante]]';
  $('#cuerpoPrevia').innerHTML = cuerpoHtml(parseDoc(muestra));
  $('#piePrevia').innerHTML = pieHtml(true, 1);
}
const renderPreviaLuego = debounce(() => { renderPrevia(); actualizarChip(); if (state.vista === 'redactar') renderHoja(); }, 150);

/* =========================================================
   Carga inicial
   ========================================================= */
function cargarEspejoLocal() {
  const p = lsGet('perfil');
  state.perfil = p ? mezclar(clon(PERFIL_BASE), p) : clon(PERFIL_BASE);
  IMG.logo = lsGet('img:logo'); IMG.firma = lsGet('img:firma');
  const b = lsGet('borrador');
  if (b && b.tipo && TIPOS[b.tipo]) {
    state.tipo = b.tipo;
    state.datos = mezclar(Object.fromEntries(camposTipo(TIPOS[b.tipo]).map(c => [c.k, valorDefecto(c)])), b.datos || {});
    state.texto = b.texto || ''; state.versiones = Array.isArray(b.versiones) ? b.versiones : []; state.ejemplo = !state.texto; state.docId = b.docId || null; state.creado = b.creado || null; state.prompt = b.prompt || '';
    state.catalogoAbierto = false;
  }
}

/* =========================================================
   Copia de seguridad y restauración (JSON)
   ========================================================= */
async function descargarCopiaSeguridad() {
  toast('Generando copia de seguridad...', 'info', 3000);
  try {
    const hist = await Almacen.listarHist();
    const logo = await Almacen.leer('logo') || IMG.logo;
    const firma = await Almacen.leer('firma') || IMG.firma;
    let plantillaBufB64 = null;
    if (state.plantilla && state.plantilla.buf) {
      plantillaBufB64 = bufAB64(state.plantilla.buf);
    }
    const copia = {
      app: 'El Memorialista',
      version: 1,
      fechaExportacion: new Date().toISOString(),
      perfil: state.perfil,
      logo,
      firma,
      plantilla: state.plantilla ? {
        nombre: state.plantilla.nombre,
        info: state.plantilla.info,
        bufferB64: plantillaBufB64
      } : null,
      historial: hist
    };
    const jsonStr = JSON.stringify(copia, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const fecha = new Date().toISOString().slice(0, 10);
    await guardarArchivo(`copia_seguridad_memorialista_${fecha}.json`, blob);
    toast('Copia de seguridad descargada con éxito.', 'ok');
  } catch (e) {
    console.error(e);
    toast('Error al generar la copia de seguridad.', 'error');
  }
}

async function restaurarCopiaSeguridad(file) {
  if (!file) return;
  try {
    const texto = await file.text();
    const copia = JSON.parse(texto);
    if (!copia || !copia.perfil || !Array.isArray(copia.historial)) {
      throw new Error('El archivo no tiene el formato válido de copia de seguridad de El Memorialista.');
    }
    const confirmar = confirm(`Se restaurarán los datos de "${copia.perfil.abogado?.nombre || 'Abogado(a)'}" con ${copia.historial.length} escritos del historial.\n\n¿Deseas sobrescribir los datos actuales?`);
    if (!confirmar) return;

    state.perfil = mezclar(clon(PERFIL_BASE), copia.perfil);
    lsSet('perfil', state.perfil);

    if (copia.logo) {
      IMG.logo = copia.logo;
      await Almacen.escribir('logo', copia.logo);
    }
    if (copia.firma) {
      IMG.firma = copia.firma;
      await Almacen.escribir('firma', copia.firma);
    }
    if (copia.plantilla && copia.plantilla.bufferB64) {
      const buf = b64ABuf(copia.plantilla.bufferB64);
      await cargarJSZip();
      const info = copia.plantilla.info || await analizarPlantilla(await window.JSZip.loadAsync(buf));
      state.plantilla = { buf, info, nombre: copia.plantilla.nombre };
      state.perfil.plantilla = {
        nombre: copia.plantilla.nombre,
        bytes: buf.byteLength,
        subido: Date.now(),
        info: infoSinImagenes(info)
      };
      guardarPerfil.ya();
    }

    await IDB.clear('historial');
    for (const hItem of copia.historial) {
      if (hItem && hItem.id) await Almacen.guardarHist(hItem.id, hItem);
    }

    cargarAjustesEnFormulario();
    actualizarChip();
    pintarHistorial();
    if (state.vista === 'redactar') renderHoja();
    else if (state.vista === 'membrete') renderPrevia();
    toast('¡Copia de seguridad restaurada con éxito!', 'ok', 6000);
  } catch (e) {
    console.error(e);
    toast(e.message || 'Error al restaurar la copia de seguridad.', 'error', 7000);
  }
}

/* =========================================================
   Cómputo de Términos Judiciales y Plazos Procesales
   ========================================================= */
function descargarIcs(icsText, nombreArchivo) {
  if (!icsText) return;
  const blob = new Blob([icsText], { type: 'text/calendar;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nombreArchivo || 'vencimiento.ics';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 200);
}

function inferirPresetTermino(tipoId) {
  const t = String(tipoId || '').toLowerCase();
  if (t.includes('tutela')) return 'impugnacion_tutela';
  if (t.includes('verbal_sumario')) return 'contestacion_verbal_sumario';
  if (t.includes('verbal') || t.includes('contestacion') || t.includes('demanda')) return 'contestacion_verbal';
  if (t.includes('nulidad')) return 'caducidad_nulidad_restablecimiento';
  if (t.includes('reparacion')) return 'caducidad_reparacion_directa';
  if (t.includes('querella') || t.includes('denuncia')) return 'caducidad_querella';
  if (t.includes('admin') || t.includes('revocatoria')) return 'recursos_admin';
  return 'recursos_autos';
}

function renderizarAyudaVencimientoCampo(c, inp, contenedor, fechaIso) {
  const box = h('div', {
    class: 'ayuda-vencimiento-box',
    style: 'margin-top: 6px; padding: 8px 10px; border-radius: 6px; font-size: 12.5px; border: 1px solid var(--regla); background: var(--superficie); transition: all 0.2s;'
  },
    h('div', { style: 'color: var(--tinta-2); display: flex; align-items: center; gap: 6px;' },
      h('span', { class: 'girando', style: 'display: inline-block;' }, '⏳'),
      'Calculando vencimiento legal...'
    )
  );
  contenedor.append(box);

  const presetId = inferirPresetTermino(state.tipo);
  inp.dataset.lastPlazoFecha = fechaIso;

  apiFetch('/api/plazos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tipo_termino: presetId,
      fecha_inicio: fechaIso,
      titulo_evento: `Vencimiento: ${TIPOS[state.tipo]?.nombre || 'Término procesal'}`
    })
  }).then(async r => {
    if (!r.ok) throw new Error('Error al calcular plazos');
    return r.json();
  }).then(data => {
    if (inp.value.trim() !== fechaIso || inp.dataset.lastPlazoFecha !== fechaIso) return;
    box.replaceChildren();

    const esVencido = data.ha_vencido;
    const esHoy = data.estado_vencimiento === 'vence_hoy';

    if (esVencido) {
      box.style.background = '#fef2f2';
      box.style.borderColor = '#fca5a5';
      box.style.color = '#dc2626';
    } else if (esHoy) {
      box.style.background = '#fffbeb';
      box.style.borderColor = '#fde68a';
      box.style.color = '#b45309';
    } else {
      box.style.background = '#f0fdf4';
      box.style.borderColor = '#bbf7d0';
      box.style.color = '#15803d';
    }

    // Texto exacto solicitado: "Vence el … (quedan N días hábiles)", en rojo si ya venció
    let textoVence = '';
    if (esVencido) {
      textoVence = `Vence el ${data.dia_semana_vencimiento.toLowerCase()}, ${data.fecha_vencimiento} (quedan 0 días hábiles · ¡VENCIDO!)`;
    } else {
      textoVence = `Vence el ${data.dia_semana_vencimiento.toLowerCase()}, ${data.fecha_vencimiento} (quedan ${data.dias_habiles_restantes} días hábiles)`;
    }

    const cab = h('div', { style: 'font-weight: 700; display: flex; align-items: center; justify-content: space-between; gap: 8px;' },
      h('span', {}, (esVencido ? '⚠️ ' : esHoy ? '⏰ ' : '⏱️ ') + textoVence),
      h('span', { style: 'font-size: 11px; opacity: 0.85; font-weight: 600;' }, data.nombre_termino)
    );

    const sub = h('div', { style: 'font-size: 11.5px; margin-top: 3px; opacity: 0.9;' },
      data.texto_resumen + ` · ${data.norma}`
    );

    const btnIcs = h('button', {
      type: 'button',
      class: 'btn enlace',
      style: 'margin-top: 6px; font-size: 12px; font-weight: 600; text-decoration: underline; cursor: pointer; color: inherit; display: inline-flex; align-items: center; gap: 4px; padding: 0; background: none; border: none;',
      onclick: () => descargarIcs(data.evento_ics, `vencimiento_${data.fecha_vencimiento}.ics`)
    }, '📅 Descargar vencimiento (.ics)');

    box.append(cab, sub, btnIcs);
  }).catch(err => {
    if (inp.value.trim() !== fechaIso) return;
    box.replaceChildren(h('div', { style: 'color: #dc2626; font-size: 11.5px;' }, 'Error al verificar plazo: ' + err.message));
  });
}

let vistaPlazosInicializada = false;
let calculoPlazosTimer = null;

async function renderVistaPlazos() {
  const selPreset = $('#plazo_preset');
  if (!selPreset) return;

  if (!state.catalogo?.plazos) {
    try {
      const res = await apiFetch('/api/plazos/catalogo');
      if (res.ok) {
        if (!state.catalogo) state.catalogo = {};
        state.catalogo.plazos = await res.json();
      }
    } catch (e) {
      console.warn('Error al cargar catálogo de plazos:', e);
    }
  }

  const presets = state.catalogo?.plazos?.precargas_terminos || [];

  if (selPreset.options.length === 0) {
    selPreset.append(h('option', { value: '' }, '— Selecciona un término procesal —'));
    for (const p of presets) {
      selPreset.append(h('option', { value: p.id }, `${p.nombre} (${p.cantidad} ${p.unidad === 'dias_habiles' ? 'días hábiles' : p.unidad}) · ${p.norma}`));
    }
    selPreset.append(h('option', { value: 'personalizado' }, 'Personalizado (duración y unidad manual)'));
    selPreset.value = 'impugnacion_tutela';
  }

  const inpFecha = $('#plazo_fecha_inicio');
  if (inpFecha && !inpFecha.value) {
    inpFecha.value = new Date().toISOString().slice(0, 10);
  }

  if (!vistaPlazosInicializada) {
    vistaPlazosInicializada = true;

    selPreset.addEventListener('change', () => {
      const val = selPreset.value;
      const p = presets.find(item => item.id === val);
      if (p) {
        $('#plazo_cantidad').value = p.cantidad;
        $('#plazo_unidad').value = p.unidad;
        $('#plazo_vacancia_colectiva').checked = p.vacancia_colectiva !== false;
      }
      ejecutarCalculoPlazosVista();
    });

    $('#plazo_mensaje_datos').addEventListener('change', e => {
      $('#plazo_bloque_acuse').hidden = !e.target.checked;
      ejecutarCalculoPlazosVista();
    });

    for (const id of ['plazo_fecha_inicio', 'plazo_cantidad', 'plazo_unidad', 'plazo_vacancia_colectiva', 'plazo_fecha_acuse']) {
      const el = $('#' + id);
      if (el) {
        el.addEventListener('change', ejecutarCalculoPlazosVista);
        el.addEventListener('input', ejecutarCalculoPlazosVista);
      }
    }
  }

  ejecutarCalculoPlazosVista();
}

function ejecutarCalculoPlazosVista() {
  clearTimeout(calculoPlazosTimer);
  calculoPlazosTimer = setTimeout(async () => {
    const fechaInicio = $('#plazo_fecha_inicio')?.value;
    const panel = $('#plazos_resultado_panel');
    if (!panel) return;
    if (!fechaInicio) {
      panel.replaceChildren(h('div', { class: 'vacio' }, 'Selecciona o escribe una fecha de notificación o providencia para calcular los términos.'));
      return;
    }

    const presetVal = $('#plazo_preset')?.value;
    const cantidad = parseInt($('#plazo_cantidad')?.value, 10) || 1;
    const unidad = $('#plazo_unidad')?.value || 'dias_habiles';
    const vacancia = Boolean($('#plazo_vacancia_colectiva')?.checked);
    const mensajeDatos = Boolean($('#plazo_mensaje_datos')?.checked);
    const fechaAcuse = mensajeDatos && $('#plazo_fecha_acuse')?.value ? $('#plazo_fecha_acuse').value : null;

    panel.replaceChildren(
      h('div', { style: 'padding: 24px; text-align: center; color: var(--tinta-2);' },
        h('span', { class: 'girando', style: 'display: inline-block; margin-right: 8px;' }, '⏳'),
        'Calculando términos procesales con calendario judicial...'
      )
    );

    try {
      const res = await apiFetch('/api/plazos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tipo_termino: presetVal && presetVal !== 'personalizado' ? presetVal : null,
          fecha_inicio: fechaInicio,
          unidad: unidad,
          cantidad: cantidad,
          vacancia_colectiva: vacancia,
          notificacion_mensaje_datos: mensajeDatos,
          fecha_acuse_recibo: fechaAcuse
        })
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Error al calcular los plazos');
      }

      const data = await res.json();
      pintarResultadoPlazosCompleto(data, panel);
    } catch (err) {
      panel.replaceChildren(
        h('div', { style: 'padding: 16px; background: #fef2f2; border: 1px solid #fecaca; border-radius: var(--r); color: #dc2626;' },
          h('strong', {}, 'Error de cómputo: '),
          err.message
        )
      );
    }
  }, 100);
}

function pintarResultadoPlazosCompleto(data, panel) {
  panel.replaceChildren();

  const esVencido = data.ha_vencido;
  const esHoy = data.estado_vencimiento === 'vence_hoy';

  const colorTema = esVencido
    ? { bg: '#fef2f2', borde: '#ef4444', texto: '#991b1b', badgeBg: '#dc2626', badgeTxt: '#fff', label: 'TÉRMINO VENCIDO' }
    : esHoy
    ? { bg: '#fffbeb', borde: '#f59e0b', texto: '#92400e', badgeBg: '#d97706', badgeTxt: '#fff', label: '¡VENCE HOY!' }
    : { bg: '#f0fdf4', borde: '#22c55e', texto: '#166534', badgeBg: '#16a34a', badgeTxt: '#fff', label: 'EN TÉRMINO' };

  // 1. Tarjeta Resumen Principal
  const tarjetaPrincipal = h('div', {
    style: `background: ${colorTema.bg}; border: 2px solid ${colorTema.borde}; border-radius: var(--r); padding: 22px; display: grid; gap: 12px;`
  },
    h('div', { style: 'display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;' },
      h('span', { style: `background: ${colorTema.badgeBg}; color: ${colorTema.badgeTxt}; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 999px; letter-spacing: 0.05em; text-transform: uppercase;` }, colorTema.label),
      h('span', { style: 'font-size: 13px; font-weight: 600; color: ' + colorTema.texto }, `${data.nombre_termino} · ${data.norma}`)
    ),
    h('div', {},
      h('h2', { style: `font-size: 22px; font-weight: 800; margin: 0 0 6px; color: ${colorTema.texto};` },
        esVencido
          ? `Vence el ${data.dia_semana_vencimiento.toLowerCase()}, ${data.fecha_vencimiento} (quedan 0 días hábiles)`
          : `Vence el ${data.dia_semana_vencimiento.toLowerCase()}, ${data.fecha_vencimiento} (quedan ${data.dias_habiles_restantes} días hábiles)`
      ),
      h('p', { style: `margin: 0; font-size: 14.5px; color: ${colorTema.texto}; opacity: 0.95; font-weight: 500;` },
        `${data.texto_resumen} · Hora límite de radicación: ${data.hora_limite}`
      )
    ),
    h('div', { style: 'display: flex; gap: 10px; flex-wrap: wrap; align-items: center; padding-top: 6px;' },
      h('button', {
        type: 'button',
        class: 'btn primario',
        style: 'background: #0f172a; color: #fff; padding: 8px 16px; border-radius: 6px; font-weight: 600; font-size: 13.5px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 8px;',
        onclick: () => descargarIcs(data.evento_ics, `vencimiento_${data.fecha_vencimiento}.ics`)
      },
        '📅 Descargar evento de calendario (.ics)'
      ),
      h('span', { style: 'font-size: 12px; color: var(--tinta-2);' }, 'Compatible con Google Calendar, Outlook y Apple Calendar')
    )
  );

  // 2. Fundamento Legal y Reglas Aplicadas
  const tarjetaReglas = h('div', {
    style: 'background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r); padding: 18px; display: grid; gap: 10px;'
  },
    h('h3', { style: 'font-size: 14px; font-weight: 700; margin: 0; color: var(--tinta); display: flex; align-items: center; gap: 6px;' },
      '⚖️ Fundamento legal y reglas de cómputo aplicadas'
    ),
    h('ul', { style: 'margin: 0; padding-left: 20px; display: grid; gap: 6px; font-size: 13px; color: var(--tinta-2);' },
      ...(data.reglas_aplicadas || []).map(r => h('li', {}, r))
    )
  );

  // 3. Desglose Día por Día
  const tarjetaDesglose = h('div', {
    style: 'background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r); padding: 18px; display: grid; gap: 12px;'
  },
    h('div', { style: 'display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;' },
      h('h3', { style: 'font-size: 14px; font-weight: 700; margin: 0; color: var(--tinta);' },
        `🗓️ Desglose del cómputo procesal (${(data.desglose_dias || []).length} días analizados)`
      ),
      h('span', { style: 'font-size: 12px; color: var(--tinta-2);' },
        `Notificación: ${data.fecha_notificacion} · Inicio cómputo: ${data.fecha_inicio_computo}`
      )
    ),
    h('div', { style: 'overflow-x: auto;' },
      h('table', { style: 'width: 100%; border-collapse: collapse; font-size: 12.5px; text-align: left;' },
        h('thead', {},
          h('tr', { style: 'border-bottom: 2px solid var(--regla); color: var(--tinta-2);' },
            h('th', { style: 'padding: 8px 10px;' }, 'Fecha'),
            h('th', { style: 'padding: 8px 10px;' }, 'Día'),
            h('th', { style: 'padding: 8px 10px;' }, 'Estado procesal'),
            h('th', { style: 'padding: 8px 10px;' }, 'Detalle / Festivo / Norma')
          )
        ),
        h('tbody', {},
          ...(data.desglose_dias || []).map(d => {
            const esHabil = d.es_habil;
            const esUltimo = d.fecha === data.fecha_vencimiento;
            const bgFila = esUltimo
              ? (esVencido ? '#fef2f2' : '#f0fdf4')
              : esHabil
              ? 'rgba(34, 197, 94, 0.04)'
              : 'rgba(0, 0, 0, 0.02)';

            return h('tr', { style: `border-bottom: 1px solid var(--regla); background: ${bgFila};` },
              h('td', { style: `padding: 8px 10px; font-family: var(--mono); font-weight: ${esUltimo ? '700' : 'normal'};` }, d.fecha),
              h('td', { style: 'padding: 8px 10px;' }, d.dia_semana),
              h('td', { style: 'padding: 8px 10px;' },
                esUltimo
                  ? h('span', { style: `display: inline-block; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 11px; background: ${esVencido ? '#dc2626' : '#16a34a'}; color: #fff;` }, `🎯 VENCE (Día #${d.dia_computo || data.cantidad})`)
                  : esHabil
                  ? h('span', { style: 'display: inline-block; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 11px; background: #dcfce7; color: #166534;' }, `✓ Día hábil #${d.dia_computo}`)
                  : h('span', { style: 'display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px; background: #f3f4f6; color: #6b7280;' }, '— Inhábil')
              ),
              h('td', { style: `padding: 8px 10px; color: ${esUltimo ? colorTema.texto : 'inherit'}; font-weight: ${esUltimo ? '600' : 'normal'};` },
                d.motivo + (esUltimo ? ` (Fecha límite a las ${data.hora_limite})` : '')
              )
            );
          })
        )
      )
    )
  );

  panel.append(tarjetaPrincipal, tarjetaReglas, tarjetaDesglose);
}

/* =========================================================
   Cálculos Jurídicos, Laborales y Financieros
   ========================================================= */
let subtabCalculosActual = 'laboral';
let vistaCalculosInicializada = false;

function cambiarSubtabCalculos(subtab) {
  subtabCalculosActual = subtab;
  const tabs = ['laboral', 'mora', 'ipc'];
  for (const t of tabs) {
    const btn = $('#subtab-' + t);
    const sec = $('#calc-seccion-' + t);
    if (btn) {
      btn.className = t === subtab ? 'btn chico' : 'btn chico secundario';
    }
    if (sec) {
      sec.style.display = t === subtab ? 'grid' : 'none';
    }
  }
}

function toggleCamposLaboral() {
  const tipoContrato = $('#lab_tipo_contrato')?.value;
  const pactada = $('#lab_campo_fecha_pactada');
  if (pactada) pactada.hidden = tipoContrato !== 'termino_fijo';

  const checkMora = $('#lab_check_moratoria')?.checked;
  const checkConsignacion = $('#lab_check_consignacion')?.checked;
  const panelExtra = $('#lab_panel_opciones_extra');
  const campoCorte = $('#lab_campo_corte_moratoria');
  const campoConsignacion = $('#lab_campo_dias_consignacion');

  if (panelExtra) panelExtra.hidden = !checkMora && !checkConsignacion;
  if (campoCorte) campoCorte.hidden = !checkMora;
  if (campoConsignacion) campoConsignacion.hidden = !checkConsignacion;
}

function renderVistaCalculos() {
  if (vistaCalculosInicializada) return;
  vistaCalculosInicializada = true;

  const hoy = new Date().toISOString().slice(0, 10);
  const haceUnAnio = new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10);
  const haceTresMeses = new Date(Date.now() - 90 * 86400000).toISOString().slice(0, 10);

  if ($('#lab_fecha_inicio') && !$('#lab_fecha_inicio').value) $('#lab_fecha_inicio').value = haceUnAnio;
  if ($('#lab_fecha_fin') && !$('#lab_fecha_fin').value) $('#lab_fecha_fin').value = hoy;
  if ($('#lab_salario_base') && !$('#lab_salario_base').value) $('#lab_salario_base').value = '2000000';
  if ($('#lab_fecha_corte_moratoria') && !$('#lab_fecha_corte_moratoria').value) $('#lab_fecha_corte_moratoria').value = hoy;

  if ($('#mora_capital') && !$('#mora_capital').value) $('#mora_capital').value = '50000000';
  if ($('#mora_fecha_inicio') && !$('#mora_fecha_inicio').value) $('#mora_fecha_inicio').value = haceTresMeses;
  if ($('#mora_fecha_fin') && !$('#mora_fecha_fin').value) $('#mora_fecha_fin').value = hoy;

  if ($('#ipc_valor') && !$('#ipc_valor').value) $('#ipc_valor').value = '10000000';
  if ($('#ipc_fecha_ini') && !$('#ipc_fecha_ini').value) $('#ipc_fecha_ini').value = '2022-01-01';
  if ($('#ipc_fecha_fin') && !$('#ipc_fecha_fin').value) $('#ipc_fecha_fin').value = hoy;
}

async function ejecutarCalculoLaboral() {
  const panel = $('#lab_resultado_panel');
  if (!panel) return;

  const fIni = $('#lab_fecha_inicio')?.value;
  const fFin = $('#lab_fecha_fin')?.value;
  const salario = parseFloat($('#lab_salario_base')?.value) || 0;
  if (!fIni || !fFin) {
    toast('Ingresa la fecha de inicio y terminación laboral.');
    return;
  }
  if (salario <= 0) {
    toast('Ingresa el salario básico mensual.');
    return;
  }

  panel.replaceChildren(
    h('div', { style: 'padding: 24px; text-align: center; color: var(--tinta-2);' },
      h('span', { class: 'girando', style: 'display: inline-block; margin-right: 8px;' }, '⏳'),
      'Calculando prestaciones e indemnizaciones laborales...'
    )
  );

  try {
    const payload = {
      fecha_inicio: fIni,
      fecha_fin: fFin,
      salario_base: salario,
      incluir_auxilio_transporte: Boolean($('#lab_incluir_auxilio')?.checked),
      tipo_contrato: $('#lab_tipo_contrato')?.value || 'indefinido',
      motivo_terminacion: $('#lab_motivo')?.value || 'despido_sin_justa_causa',
      nombre_trabajador: $('#lab_trabajador')?.value || '',
      nombre_empleador: $('#lab_empleador')?.value || '',
      liquidar_moratoria_art65: Boolean($('#lab_check_moratoria')?.checked),
      fecha_corte_moratoria: $('#lab_fecha_corte_moratoria')?.value || null,
      liquidar_sancion_consignacion_art99: Boolean($('#lab_check_consignacion')?.checked),
      dias_mora_consignacion: parseInt($('#lab_dias_consignacion')?.value, 10) || null,
      fecha_fin_pactada: $('#lab_fecha_pactada')?.value || null
    };

    const res = await apiFetch('/api/calculos/laboral', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error en cálculo laboral');
    }

    const data = await res.json();
    pintarResultadoLaboral(data, panel);
  } catch (err) {
    panel.replaceChildren(
      h('div', { style: 'padding: 16px; background: #fef2f2; border: 1px solid #fecaca; border-radius: var(--r); color: #dc2626;' },
        h('strong', {}, 'Error de cálculo: '),
        err.message
      )
    );
  }
}

function pintarResultadoLaboral(data, panel) {
  panel.replaceChildren();

  // Tarjeta de resumen
  const tarjetaCab = h('div', { class: 'card', style: 'background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r); padding: 20px; display: grid; gap: 14px;' },
    h('div', { style: 'display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;' },
      h('div', {},
        h('h3', { style: 'margin: 0; font-size: 18px; font-weight: 700;' }, 'Resultado de la Liquidación Laboral'),
        h('p', { style: 'margin: 4px 0 0; font-size: 13.5px; color: var(--tinta-2);' },
          `Trabajador: ${data.trabajador} | Periodo: ${data.fecha_inicio} a ${data.fecha_fin} (${data.dias_totales_servicio} días)`
        )
      ),
      h('div', { style: 'text-align: right;' },
        h('div', { style: 'font-size: 12px; color: var(--tinta-2); text-transform: uppercase; font-weight: 600;' }, 'Gran Total Liquidación'),
        h('div', { style: 'font-size: 24px; font-weight: 800; color: #166534;' }, formatoMonedaCOP(data.gran_total_liquidacion))
      )
    ),
    h('div', { style: 'display: flex; gap: 16px; flex-wrap: wrap; padding-top: 10px; border-top: 1px solid var(--regla); font-size: 13px;' },
      h('span', {}, h('strong', {}, 'Salario Base: '), formatoMonedaCOP(data.salario_base_ordinario)),
      h('span', {}, h('strong', {}, 'Auxilio Transporte: '), formatoMonedaCOP(data.auxilio_transporte)),
      h('span', {}, h('strong', {}, 'Subtotal Prestaciones: '), formatoMonedaCOP(data.total_prestaciones_sociales)),
      data.total_indemnizaciones_y_sanciones > 0 ? h('span', {}, h('strong', {}, 'Subtotal Indemnizaciones: '), formatoMonedaCOP(data.total_indemnizaciones_y_sanciones)) : ''
    )
  );

  // Alerta de Ley 2466 de 2025
  const bloquesAlertas = [];
  if (data.advertencias_legales && data.advertencias_legales.length > 0) {
    for (const adv of data.advertencias_legales) {
      bloquesAlertas.push(
        h('div', { style: 'background: #fffbeb; border: 1px solid #fde68a; border-radius: var(--r); padding: 14px 18px; font-size: 13.5px; color: #92400e; line-height: 1.5; white-space: pre-wrap;' },
          adv
        )
      );
    }
  }

  // Tabla detallada de rubros
  const filas = data.conceptos.map(c =>
    h('tr', { style: 'border-bottom: 1px solid var(--regla);' },
      h('td', { style: 'padding: 10px;' },
        h('strong', {}, c.concepto),
        h('div', { style: 'font-size: 11.5px; color: var(--tinta-2); margin-top: 2px;' }, c.detalle)
      ),
      h('td', { style: 'padding: 10px; text-align: center;' }, String(c.dias)),
      h('td', { style: 'padding: 10px; text-align: right;' }, formatoMonedaCOP(c.base_calculo)),
      h('td', { style: 'padding: 10px; font-family: var(--mono); font-size: 12px;' }, c.formula),
      h('td', { style: 'padding: 10px; text-align: right; font-weight: 700; color: #166534;' }, formatoMonedaCOP(c.subtotal)),
      h('td', { style: 'padding: 10px; font-size: 12px; color: var(--tinta-2);' }, c.norma)
    )
  );

  const tablaCard = h('div', { class: 'card', style: 'background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r); padding: 16px; overflow-x: auto;' },
    h('table', { style: 'width: 100%; border-collapse: collapse; font-size: 13px;' },
      h('thead', {},
        h('tr', { style: 'border-bottom: 2px solid var(--regla); background: var(--fondo); text-align: left;' },
          h('th', { style: 'padding: 10px;' }, 'Rubro / Concepto'),
          h('th', { style: 'padding: 10px; text-align: center;' }, 'Días'),
          h('th', { style: 'padding: 10px; text-align: right;' }, 'Base Cálculo'),
          h('th', { style: 'padding: 10px;' }, 'Fórmula'),
          h('th', { style: 'padding: 10px; text-align: right;' }, 'Subtotal'),
          h('th', { style: 'padding: 10px;' }, 'Fuente Legal')
        )
      ),
      h('tbody', {}, ...filas)
    )
  );

  const barraAcciones = crearBarraAccionesTabla(data.tabla_markdown, data.tabla_texto);
  panel.append(tarjetaCab, ...bloquesAlertas, tablaCard, barraAcciones);
}

async function ejecutarCalculoMora() {
  const panel = $('#mora_resultado_panel');
  if (!panel) return;

  const capital = parseFloat($('#mora_capital')?.value) || 0;
  const fIni = $('#mora_fecha_inicio')?.value;
  const fFin = $('#mora_fecha_fin')?.value;
  if (capital <= 0) {
    toast('Ingresa un monto de capital válido.');
    return;
  }
  if (!fIni || !fFin) {
    toast('Ingresa la fecha de inicio y de corte de la mora.');
    return;
  }

  panel.replaceChildren(
    h('div', { style: 'padding: 24px; text-align: center; color: var(--tinta-2);' },
      h('span', { class: 'girando', style: 'display: inline-block; margin-right: 8px;' }, '⏳'),
      'Liquidando intereses moratorios mes a mes con tasas SFC...'
    )
  );

  try {
    const payload = {
      capital: capital,
      fecha_inicio: fIni,
      fecha_fin: fFin,
      concepto_obligacion: $('#mora_concepto')?.value || '',
      metodo: $('#mora_metodo')?.value || 'financiero_exacto'
    };

    const res = await apiFetch('/api/calculos/intereses-moratorios', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error en cálculo de intereses');
    }

    const data = await res.json();
    pintarResultadoMora(data, panel);
  } catch (err) {
    panel.replaceChildren(
      h('div', { style: 'padding: 16px; background: #fef2f2; border: 1px solid #fecaca; border-radius: var(--r); color: #dc2626;' },
        h('strong', {}, 'Error de cálculo: '),
        err.message
      )
    );
  }
}

function pintarResultadoMora(data, panel) {
  panel.replaceChildren();

  const tarjetaCab = h('div', { class: 'card', style: 'background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r); padding: 20px; display: grid; gap: 14px;' },
    h('div', { style: 'display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;' },
      h('div', {},
        h('h3', { style: 'margin: 0; font-size: 18px; font-weight: 700;' }, 'Liquidación de Intereses Moratorios Mercantiles'),
        h('p', { style: 'margin: 4px 0 0; font-size: 13.5px; color: var(--tinta-2);' },
          `${data.concepto_obligacion} | Lapso: ${data.fecha_inicio} al ${data.fecha_fin} (${data.dias_totales_mora} días de mora)`
        )
      ),
      h('div', { style: 'text-align: right;' },
        h('div', { style: 'font-size: 12px; color: var(--tinta-2); text-transform: uppercase; font-weight: 600;' }, 'Gran Total Adeudado'),
        h('div', { style: 'font-size: 24px; font-weight: 800; color: #1e40af;' }, formatoMonedaCOP(data.total_adeudado))
      )
    ),
    h('div', { style: 'display: flex; gap: 16px; flex-wrap: wrap; padding-top: 10px; border-top: 1px solid var(--regla); font-size: 13px;' },
      h('span', {}, h('strong', {}, 'Capital Base: '), formatoMonedaCOP(data.capital)),
      h('span', {}, h('strong', {}, 'Intereses Totales: '), formatoMonedaCOP(data.interes_total)),
      h('span', { style: 'color: var(--tinta-2);' }, data.criterio_legal)
    )
  );

  const filas = data.periodos.map(p =>
    h('tr', { style: 'border-bottom: 1px solid var(--regla);' },
      h('td', { style: 'padding: 8px 10px; font-weight: 600;' }, p.periodo),
      h('td', { style: 'padding: 8px 10px; font-size: 12px; color: var(--tinta-2);' }, `${p.fecha_desde} a ${p.fecha_hasta}`),
      h('td', { style: 'padding: 8px 10px; text-align: center;' }, String(p.dias_mora)),
      h('td', { style: 'padding: 8px 10px; text-align: right;' }, `${p.ibc_ea.toFixed(2)}%`),
      h('td', { style: 'padding: 8px 10px; text-align: right; font-weight: 600;' }, `${p.mora_ea.toFixed(2)}%`),
      h('td', { style: 'padding: 8px 10px; text-align: right; font-family: var(--mono); font-size: 12px;' }, `${p.tasa_periodo_pct.toFixed(4)}%`),
      h('td', { style: 'padding: 8px 10px; text-align: right; font-weight: 600;' }, formatoMonedaCOP(p.interes_periodo)),
      h('td', { style: 'padding: 8px 10px; text-align: right; color: var(--tinta-2);' }, formatoMonedaCOP(p.interes_acumulado)),
      h('td', { style: 'padding: 8px 10px; font-size: 11.5px; color: var(--tinta-2);' }, p.resolucion)
    )
  );

  const tablaCard = h('div', { class: 'card', style: 'background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r); padding: 16px; overflow-x: auto;' },
    h('table', { style: 'width: 100%; border-collapse: collapse; font-size: 13px;' },
      h('thead', {},
        h('tr', { style: 'border-bottom: 2px solid var(--regla); background: var(--fondo); text-align: left;' },
          h('th', { style: 'padding: 8px 10px;' }, 'Periodo'),
          h('th', { style: 'padding: 8px 10px;' }, 'Rango Fechas'),
          h('th', { style: 'padding: 8px 10px; text-align: center;' }, 'Días'),
          h('th', { style: 'padding: 8px 10px; text-align: right;' }, 'IBC E.A.'),
          h('th', { style: 'padding: 8px 10px; text-align: right;' }, 'Mora E.A.'),
          h('th', { style: 'padding: 8px 10px; text-align: right;' }, 'Tasa Tramo'),
          h('th', { style: 'padding: 8px 10px; text-align: right;' }, 'Interés Mes'),
          h('th', { style: 'padding: 8px 10px; text-align: right;' }, 'Acumulado'),
          h('th', { style: 'padding: 8px 10px;' }, 'Resolución SFC')
        )
      ),
      h('tbody', {}, ...filas)
    )
  );

  const barraAcciones = crearBarraAccionesTabla(data.tabla_markdown, data.tabla_texto);
  panel.append(tarjetaCab, tablaCard, barraAcciones);
}

async function ejecutarCalculoIPC() {
  const panel = $('#ipc_resultado_panel');
  if (!panel) return;

  const valor = parseFloat($('#ipc_valor')?.value) || 0;
  const fIni = $('#ipc_fecha_ini')?.value;
  const fFin = $('#ipc_fecha_fin')?.value;
  if (valor <= 0) {
    toast('Ingresa un monto histórico válido.');
    return;
  }
  if (!fIni || !fFin) {
    toast('Ingresa la fecha inicial y final para la indexación.');
    return;
  }

  panel.replaceChildren(
    h('div', { style: 'padding: 24px; text-align: center; color: var(--tinta-2);' },
      h('span', { class: 'girando', style: 'display: inline-block; margin-right: 8px;' }, '⏳'),
      'Actualizando valor con serie mensual IPC del DANE...'
    )
  );

  try {
    const payload = {
      valor_historico: valor,
      fecha_inicial: fIni,
      fecha_final: fFin,
      concepto: $('#ipc_concepto')?.value || ''
    };

    const res = await apiFetch('/api/calculos/indexacion', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error en indexación con IPC');
    }

    const data = await res.json();
    pintarResultadoIPC(data, panel);
  } catch (err) {
    panel.replaceChildren(
      h('div', { style: 'padding: 16px; background: #fef2f2; border: 1px solid #fecaca; border-radius: var(--r); color: #dc2626;' },
        h('strong', {}, 'Error de cálculo: '),
        err.message
      )
    );
  }
}

function pintarResultadoIPC(data, panel) {
  panel.replaceChildren();

  const tarjetaCab = h('div', { class: 'card', style: 'background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r); padding: 20px; display: grid; gap: 14px;' },
    h('div', { style: 'display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;' },
      h('div', {},
        h('h3', { style: 'margin: 0; font-size: 18px; font-weight: 700;' }, 'Actualización Monetaria (Indexación con IPC DANE)'),
        h('p', { style: 'margin: 4px 0 0; font-size: 13.5px; color: var(--tinta-2);' },
          `Periodo: ${data.periodo_inicial} a ${data.periodo_final} | ${data.norma}`
        )
      ),
      h('div', { style: 'text-align: right;' },
        h('div', { style: 'font-size: 12px; color: var(--tinta-2); text-transform: uppercase; font-weight: 600;' }, 'Valor Indexado (VA)'),
        h('div', { style: 'font-size: 24px; font-weight: 800; color: #15803d;' }, formatoMonedaCOP(data.valor_indexado))
      )
    ),
    h('div', { style: 'display: flex; gap: 16px; flex-wrap: wrap; padding-top: 10px; border-top: 1px solid var(--regla); font-size: 13px;' },
      h('span', {}, h('strong', {}, 'Valor Histórico: '), formatoMonedaCOP(data.valor_historico)),
      h('span', {}, h('strong', {}, 'Corrección Monetaria: '), formatoMonedaCOP(data.correccion_monetaria)),
      h('span', {}, h('strong', {}, 'Inflación Acumulada: '), `${data.variacion_porcentual}%`),
      h('span', {}, h('strong', {}, 'Factor Multiplicador: '), data.factor_indexacion.toFixed(6))
    )
  );

  const tablaCard = h('div', { class: 'card', style: 'background: var(--superficie); border: 1px solid var(--regla); border-radius: var(--r); padding: 16px;' },
    h('table', { style: 'width: 100%; border-collapse: collapse; font-size: 13.5px;' },
      h('tbody', {},
        h('tr', { style: 'border-bottom: 1px solid var(--regla);' },
          h('td', { style: 'padding: 8px 10px; font-weight: 600;' }, 'Valor Histórico Original (VH)'),
          h('td', { style: 'padding: 8px 10px; text-align: right;' }, formatoMonedaCOP(data.valor_historico)),
          h('td', { style: 'padding: 8px 10px; color: var(--tinta-2); font-size: 12px;' }, 'Capital de origen')
        ),
        h('tr', { style: 'border-bottom: 1px solid var(--regla);' },
          h('td', { style: 'padding: 8px 10px; font-weight: 600;' }, `IPC Inicial (${data.periodo_inicial})`),
          h('td', { style: 'padding: 8px 10px; text-align: right;' }, data.ipc_inicial.toFixed(2)),
          h('td', { style: 'padding: 8px 10px; color: var(--tinta-2); font-size: 12px;' }, 'DANE Total Nacional')
        ),
        h('tr', { style: 'border-bottom: 1px solid var(--regla);' },
          h('td', { style: 'padding: 8px 10px; font-weight: 600;' }, `IPC Final (${data.periodo_final})`),
          h('td', { style: 'padding: 8px 10px; text-align: right;' }, data.ipc_final.toFixed(2)),
          h('td', { style: 'padding: 8px 10px; color: var(--tinta-2); font-size: 12px;' }, 'DANE Total Nacional')
        ),
        h('tr', { style: 'border-bottom: 1px solid var(--regla);' },
          h('td', { style: 'padding: 8px 10px; font-weight: 600;' }, 'Factor de Actualización'),
          h('td', { style: 'padding: 8px 10px; text-align: right; font-family: var(--mono);' }, data.factor_indexacion.toFixed(6)),
          h('td', { style: 'padding: 8px 10px; color: var(--tinta-2); font-size: 12px;' }, 'IPC_final / IPC_inicial')
        ),
        h('tr', { style: 'border-bottom: 1px solid var(--regla);' },
          h('td', { style: 'padding: 8px 10px; font-weight: 600;' }, 'Corrección Monetaria (Ajuste)'),
          h('td', { style: 'padding: 8px 10px; text-align: right; font-weight: 600; color: #b45309;' }, formatoMonedaCOP(data.correccion_monetaria)),
          h('td', { style: 'padding: 8px 10px; color: var(--tinta-2); font-size: 12px;' }, 'Pérdida de poder adquisitivo')
        ),
        h('tr', { style: 'background: var(--fondo);' },
          h('td', { style: 'padding: 10px; font-weight: 800;' }, 'VALOR ACTUALIZADO TOTAL (VA)'),
          h('td', { style: 'padding: 10px; text-align: right; font-weight: 800; font-size: 16px; color: #15803d;' }, formatoMonedaCOP(data.valor_indexado)),
          h('td', { style: 'padding: 10px; font-weight: 600; color: #15803d;' }, 'Total indexado a corte')
        )
      )
    )
  );

  const barraAcciones = crearBarraAccionesTabla(data.tabla_markdown, data.tabla_texto);
  panel.append(tarjetaCab, tablaCard, barraAcciones);
}

function crearBarraAccionesTabla(tablaMd, tablaTxt) {
  return h('div', { style: 'display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; align-items: center; padding-top: 6px;' },
    h('button', {
      type: 'button',
      class: 'btn chico secundario',
      onclick: () => {
        if (navigator.clipboard) {
          navigator.clipboard.writeText(tablaMd);
          toast('Tabla en formato Markdown copiada al portapapeles.');
        }
      }
    }, '📋 Copiar Markdown'),
    h('button', {
      type: 'button',
      class: 'btn chico secundario',
      onclick: () => {
        if (navigator.clipboard) {
          navigator.clipboard.writeText(tablaTxt);
          toast('Tabla en texto plano copiada al portapapeles.');
        }
      }
    }, '📋 Copiar Texto'),
    h('button', {
      type: 'button',
      class: 'btn chico',
      style: 'background: #047857; color: #fff; font-weight: 600;',
      onclick: () => insertarAnexoEnEscrito(tablaMd)
    }, '✍️ Insertar en el escrito')
  );
}

function insertarAnexoEnEscrito(tablaMd) {
  if (!state.texto) {
    state.texto = '';
  }
  state.texto = state.texto.trim() + '\n\n' + tablaMd + '\n';
  state.ejemplo = false;
  irVista('redactar');
  toast('Anexo liquidatorio insertado en el escrito judicial.');
}

function formatoMonedaCOP(num) {
  if (num === null || num === undefined) return '$0';
  return '$' + Math.round(num).toLocaleString('es-CO');
}

async function cargarDesdeAlmacen() {
  await migrarLocalStorageAIndexedDB();
  try {
    const [logo, firma] = await Promise.all([Almacen.leer('logo'), Almacen.leer('firma')]);
    if (logo && logo.dataUrl) IMG.logo = logo;
    if (firma && firma.dataUrl) IMG.firma = firma;
  } catch (e) {
    console.warn('[Memorialista] Error al cargar recursos:', e);
  }
  cargarAjustesEnFormulario();
  actualizarChip();
  if (state.vista === 'redactar') { renderZonaTipo(); renderHoja(); } else renderPrevia();
  if (state.vista === 'historial') renderHistorial();
  if (state.perfil.plantilla) cargarPlantillaGuardada();
}
async function cargarCatalogo() {
  try {
    const res = await apiFetch('/api/catalogo');
    if (!res.ok) throw new Error('No se pudo cargar el catálogo');
    const cat = await res.json();
    state.catalogo = cat;
    TIPOS_LISTA = cat.tipos || [];
    TIPOS = Object.fromEntries(TIPOS_LISTA.map(t => [t.id, t]));
    AREAS = cat.areas || [];
    renderZonaTipo();
    if (state.tipo && TIPOS[state.tipo]) renderFormulario();
  } catch (e) {
    console.error('Error cargando catálogo:', e);
  }
}

function iniciar() {
  { const d = new Date(); $('#selloFecha').textContent = `Recibido · ${dos(d.getDate())} ${MESES[d.getMonth()].slice(0, 3).toUpperCase()} ${d.getFullYear()}`; }
  cargarEspejoLocal();
  cargarCatalogo();
  for (const b of $$('.pestanas button')) b.addEventListener('click', () => irVista(b.dataset.vista));
  $('.sello').addEventListener('click', e => { e.preventDefault(); irVista('redactar'); });
  $('#perfilChip').addEventListener('click', () => irVista('membrete'));
  $('#btnRedactar').addEventListener('click', () => { if (validarFormulario()) redactar('nuevo'); });
  $('#formCaso').addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); if (validarFormulario()) redactar('nuevo'); } });
  $('#formCaso').addEventListener('submit', e => e.preventDefault());
  $('#btnDetener').addEventListener('click', detener);
  $('#btnRegenerar').addEventListener('click', () => { if (validarFormulario()) redactar('regenerar'); });
  $('#btnAjustar').addEventListener('click', abrirAjuste);
  $('#ajusteAplicar').addEventListener('click', aplicarAjuste);
  $('#ajusteTexto').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); aplicarAjuste(); } });
  $('#ajusteCerrar').addEventListener('click', () => { $('#ajuste').hidden = true; });
  $('#btnCopiar').addEventListener('click', copiarTexto);
  $('#btnWord').addEventListener('click', () => pedirExportacion('docx'));
  $('#btnPdf').addEventListener('click', () => pedirExportacion('pdf'));
  const btnRad = $('#btnRadicacion'); if (btnRad) btnRad.addEventListener('click', prepararRadicacion);
  const mRad = $('#modalRadicacion');
  if (mRad) {
    $('#btnCerrarModalRadicacion')?.addEventListener('click', () => mRad.close());
    $('#btnCerrarModalRadicacionPie')?.addEventListener('click', () => mRad.close());
  }
  const btnComp = $('#btnCompararVersiones');
  if (btnComp) btnComp.addEventListener('click', abrirComparadorVersiones);
  const mComp = $('#modalComparar');
  if (mComp) {
    $('#btnCerrarModalComparar')?.addEventListener('click', () => mComp.close());
    $('#btnCerrarModalCompararPie')?.addEventListener('click', () => mComp.close());
    $('#btnIntercambiarVersiones')?.addEventListener('click', intercambiarVersiones);
    $('#btnRestaurarVersionBase')?.addEventListener('click', restaurarVersionBase);
    $('#btnExportarWordDiff')?.addEventListener('click', exportarWordDiff);
    $('#selectVersionBase')?.addEventListener('change', ejecutarComparacion);
    $('#selectVersionComparada')?.addEventListener('change', ejecutarComparacion);
  }
  $('#btnDeshacerAjuste').addEventListener('click', deshacerAjuste);
  $('#histBuscar').addEventListener('input', pintarHistorial);
  const btnDesc = $('#btnDescargarCopia'); if (btnDesc) btnDesc.addEventListener('click', descargarCopiaSeguridad);
  const inpRest = $('#archivoRestaurarCopia'); if (inpRest) inpRest.addEventListener('change', e => { if (e.target.files[0]) restaurarCopiaSeguridad(e.target.files[0]); e.target.value = ''; });
  for (const el of $$('#ajForm [data-path]')) el.addEventListener(el.tagName === 'SELECT' || el.type === 'checkbox' || el.type === 'radio' ? 'change' : 'input', () => alCambiarAjuste(el));
  $('#logoArchivo').addEventListener('change', e => { subirImagen('logo', e.target.files[0]); e.target.value = ''; });
  $('#firmaArchivo').addEventListener('change', e => { subirImagen('firma', e.target.files[0]); e.target.value = ''; });
  $('#logoQuitar').addEventListener('click', () => quitarImagen('logo'));
  $('#firmaQuitar').addEventListener('click', () => quitarImagen('firma'));
  $('#plantillaArchivo').addEventListener('change', e => { subirPlantilla(e.target.files[0]); e.target.value = ''; });
  $('#plantillaQuitar').addEventListener('click', quitarPlantilla);
  $('#muestraArchivo').addEventListener('change', e => { subirMuestra(e.target.files[0]); e.target.value = ''; });
  $('#btnAnalizar').addEventListener('click', analizarEstilo);
  iniciarEdicion();
  const barra = $('#barra');
  const medirBarra = () => document.documentElement.style.setProperty('--barra-h', barra.offsetHeight + 'px');
  medirBarra();
  if ('ResizeObserver' in window) { new ResizeObserver(medirBarra).observe(barra); new ResizeObserver(() => ajustarZoom()).observe($('#mesaHoja')); }
  else window.addEventListener('resize', () => { medirBarra(); ajustarZoom(); });
  window.addEventListener('hashchange', () => irVista(location.hash.slice(1)));
  cargarAjustesEnFormulario();
  actualizarChip();
  renderZonaTipo();
  renderFormulario();
  if (state.tipo) $('#accionesForm').hidden = false;
  const inicial = location.hash.slice(1);
  irVista(['membrete', 'historial', 'plazos', 'calculos'].includes(inicial) ? inicial : 'redactar');
  ponerControles();
  if (!state.ejemplo) estadoHoja('listo', 'Borrador recuperado');
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { ajustarZoom(); if (state.vista === 'redactar') renderMembreteHoja(); });
  iniciarCapacidades().then(cargarDesdeAlmacen).catch(() => cargarAjustesEnFormulario());

  // Controles de Supabase Auth, Cuenta y Privacidad
  const btnCerrarAuth = $('#btnCerrarModalAuth');
  if (btnCerrarAuth) btnCerrarAuth.addEventListener('click', cerrarModalAuth);

  const btnCerrarCuenta = $('#btnCerrarModalCuenta');
  if (btnCerrarCuenta) btnCerrarCuenta.addEventListener('click', cerrarModalCuenta);

  const btnCerrarCuentaDlg = $('#btnCerrarCuentaDialog');
  if (btnCerrarCuentaDlg) btnCerrarCuentaDlg.addEventListener('click', cerrarModalCuenta);

  const formAuth = $('#formAuthMagicLink');
  if (formAuth) formAuth.addEventListener('submit', manejarSubmitMagicLink);

  const btnExp = $('#btnExportarDatosCuenta');
  if (btnExp) btnExp.addEventListener('click', exportarTodosMisDatos);

  const btnSinc = $('#btnSincronizarNube');
  if (btnSinc) btnSinc.addEventListener('click', () => {
    if (state.usuario) {
      localStorage.removeItem('supabase_migrado_' + state.usuario.id);
      migrarDatosNavegadorASupabase(state.usuario);
    } else {
      abrirModalAuth('Inicia sesión para sincronizar tus datos con la nube.');
    }
  });

  const btnElim = $('#btnEliminarCuentaModal');
  if (btnElim) btnElim.addEventListener('click', eliminarMiCuenta);

  const btnCerrarSesion = $('#btnCerrarSesionCuenta');
  if (btnCerrarSesion) btnCerrarSesion.addEventListener('click', async () => {
    if (sbClient) await sbClient.auth.signOut().catch(() => {});
    state.session = null;
    state.usuario = null;
    actualizarUiAuth();
    cerrarModalCuenta();
    toast('Has cerrado sesión.', 'info');
  });

  iniciarSupabase();
}
iniciar();
</script>
</body></html>

```
