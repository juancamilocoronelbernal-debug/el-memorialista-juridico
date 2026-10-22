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


def construir_esquema_extraccion(campos: list[dict[str, Any]]) -> dict[str, Any]:
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

    return {
        "type": "OBJECT",
        "properties": properties,
    }


def construir_prompt_extraccion(nombre_tipo: str, campos: list[dict[str, Any]], archivos: list[dict[str, Any]]) -> str:
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

    return (
        f"Eres un asistente pericial jurídico de alta precisión especializado en derecho procesal colombiano.\n"
        f"Tu labor es examinar minuciosamente los documentos del caso adjuntos (archivos en línea: PDF, imágenes o audio)\n"
        f"y extraer de forma estructurada los datos para completar un escrito judicial de tipo: \"{nombre_tipo}\".\n\n"
        f"ARCHIVOS APORTADOS POR EL ABOGADO:\n"
        f"{lista_archivos_str}\n\n"
        f"CAMPOS DEL FORMULARIO A COMPLETAR:\n"
        f"{lista_campos_str}\n\n"
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
) -> list[dict[str, Any]]:
    """Envía los archivos como partes en línea a gemini-3.8-flash y extrae los campos."""
    s = get_settings()
    nombre_tipo = tipo_info.get("nombre", tipo_id)
    campos = extraer_campos_relevantes_tipo(tipo_info)
    campos_dict = {c["k"]: c for c in campos}
    esquema = construir_esquema_extraccion(campos)
    prompt = construir_prompt_extraccion(nombre_tipo, campos, archivos)

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
        return []

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

    return propuestas
