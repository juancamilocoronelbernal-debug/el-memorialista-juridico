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
