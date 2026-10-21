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
RESPALDO_SEGURO = ("gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite")

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
    inicio, fin = texto.find("{"), texto.rfind("}")
    return texto[inicio:fin + 1] if inicio >= 0 and fin > inicio else ""


def extraer_json(texto: str) -> Optional[dict]:
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
        if isinstance(datos, dict):
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
            await self.http.aclose()
            self.http = None

    async def _cliente(self) -> httpx.AsyncClient:
        if self.http is None:
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
            pensamiento = (s.GEMINI_THINKING_COMPLEX if calidad == "complex" else s.GEMINI_THINKING_DEFAULT).strip()
            for nombre in filtrados or unicos:
                motores.append(Motor("gemini", nombre, pensamiento))
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
    def _payload_gemini(self, motor: Motor, mensajes: list, degradado: bool) -> dict:
        s = self.s
        legado = motor.modelo.startswith(("gemini-1", "gemini-2"))
        config = {
            "maxOutputTokens": min(s.GEMINI_MAX_OUTPUT_TOKENS, 32768) if degradado else s.GEMINI_MAX_OUTPUT_TOKENS
        }
        if not degradado:
            if legado:
                config["temperature"] = 0.3
            elif motor.pensamiento:
                config["thinkingConfig"] = {"thinkingLevel": motor.pensamiento}
        payload = {
            "systemInstruction": {"parts": [{"text": INSTRUCCION_SISTEMA}]},
            "contents": [{"role": rol, "parts": [{"text": texto}]} for rol, texto in mensajes],
            "generationConfig": config,
        }
        umbral = s.GEMINI_SAFETY.strip()
        if umbral and not degradado:
            payload["safetySettings"] = [{"category": c, "threshold": umbral} for c in CATEGORIAS_SEGURIDAD]
        return payload

    async def _stream_gemini(self, motor: Motor, mensajes: list, degradado: bool):
        s = self.s
        cliente = await self._cliente()
        url = f"{s.GEMINI_API_BASE.rstrip('/')}/v1beta/models/{motor.modelo}:streamGenerateContent"
        payload = self._payload_gemini(motor, mensajes, degradado)
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

    async def _completar_json(self, motor: Motor, prompt: str, degradado: bool) -> str:
        s = self.s
        cliente = await self._cliente()
        if motor.proveedor == "gemini":
            config = {"maxOutputTokens": 8192}
            if not degradado:
                config["responseMimeType"] = "application/json"
                config["responseSchema"] = ESQUEMA_ESTILO
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
