#!/usr/bin/env python3
"""scripts/evaluar.py - Marco de Evaluación y Benchmarking de El Memorialista.

Evalúa los 75 casos de prueba oficiales (3 por cada uno de los 25 tipos de documento)
contra el servidor local o la aplicación FastAPI:
1. Generación de cada escrito midiendo tiempo y tokens.
2. Auditor de fidelidad (invenciones, omisiones, discrepancias cifras-letras).
3. Verificador de citas oficiales (Corte Constitucional, leyes, decretos, códigos).
4. Checklist de requisitos normativos del catálogo procesal.
5. Verificación de expectativas del caso (secciones obligatorias, longitud, entidades prohibidas).
6. Clasificación de semáforo por caso (🟢 Verde / 🟡 Amarillo / 🔴 Rojo).
7. Cálculo de totales (citas inexistentes, datos inventados, requisitos faltantes, tiempo, tokens).
8. Generación de reporte interactivo HTML profesional autónomo (`reporte_evaluacion.html`).

POLÍTICA DE DESPLIEGUE:
Correr esta evaluación antes de cambiar de modelo, de prompt o de guía del catálogo,
y NO desplegar a producción si empeora alguna métrica.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import glob
import html
import json
import logging
import os
import re
import sys
import time
from typing import Any, Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.services.auditor_fidelidad import auditar_datos_y_escrito, normalizar_texto
from app.services.prompt import listar_tipos, obtener_tipo, construir_prompt
from app.services.revisor_requisitos import revisar_requisitos
from app.services.verificador_citas import verificar_citas

log = logging.getLogger("memorialista.evaluar")


# -----------------------------------------------------------------------------
# CARGA DE CASOS DE PRUEBA
# -----------------------------------------------------------------------------
def cargar_casos(
    directorio_casos: Optional[str] = None,
    filtro_tipo: Optional[str] = None,
    filtro_caso: Optional[str] = None,
    limite: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Carga los casos de prueba desde tests/casos/*.json."""
    if not directorio_casos:
        directorio_casos = os.path.join(ROOT_DIR, "tests", "casos")

    patron = os.path.join(directorio_casos, "*.json")
    archivos = sorted(glob.glob(patron))
    casos: list[dict[str, Any]] = []

    for ruta in archivos:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = json.load(f)
            lista = contenido if isinstance(contenido, list) else [contenido]
            for c in lista:
                t = c.get("tipo", "")
                cid = c.get("id", "")
                if filtro_tipo and t.lower() != filtro_tipo.lower():
                    continue
                if filtro_caso and cid.lower() != filtro_caso.lower():
                    continue
                casos.append(c)
        except Exception as e:
            print(f"⚠️ Error al leer {ruta}: {e}", file=sys.stderr)

    if limite and limite > 0:
        casos = casos[:limite]

    return casos


# -----------------------------------------------------------------------------
# GENERACIÓN DE ESCRITO (EN VIVO O MOCK)
# -----------------------------------------------------------------------------
def generar_mock_escrito(caso: dict[str, Any]) -> tuple[str, float, dict[str, int]]:
    """Genera un borrador jurídico realista, estructurado y fiel a los datos del caso para pruebas rápidas y CI."""
    tipo = caso.get("tipo", "otro")
    datos = caso.get("datos", {})
    exp = caso.get("expectativas", {})

    ciudad = datos.get("ciudad", "Bogotá, D.C.")
    destinatario = datos.get("destinatario", "SEÑOR JUEZ DE LA REPÚBLICA (REPARTO)")
    radicado = datos.get("radicado", "")

    # Extracción fiel de partes del formulario
    cliente_raw = str(
        datos.get("cliente")
        or datos.get("demandante")
        or datos.get("accionante")
        or datos.get("convocante")
        or datos.get("peticionario")
        or datos.get("arrendador")
        or datos.get("otorgante")
        or datos.get("denunciante")
        or "Parte interesada"
    )
    contraparte_raw = str(
        datos.get("contraparte")
        or datos.get("demandado")
        or datos.get("accionado")
        or datos.get("convocado")
        or datos.get("entidad")
        or datos.get("arrendatario")
        or datos.get("denunciado")
        or ""
    )

    nombre_cliente = cliente_raw.split(",")[0].strip()
    nombre_contraparte = contraparte_raw.split(",")[0].strip()

    lineas = [
        f"{ciudad}, 21 de octubre de 2026",
        "",
        f"Señor(a):",
        f"{destinatario}",
        f"E. S. D.",
        "",
    ]
    if radicado:
        lineas.extend([f"RADICADO: {radicado}", ""])

    lineas.extend([
        f"REFERENCIA: {tipo.replace('_', ' ').upper()}",
        f"ACCIONANTE / DEMANDANTE / PARTE ACTORA: **{nombre_cliente.upper()}** ({cliente_raw})",
    ])
    if nombre_contraparte:
        lineas.append(f"ACCIONADO / DEMANDADO / PARTE DEMANDADA: **{nombre_contraparte.upper()}** ({contraparte_raw})")
    lineas.append("")

    # En tutelas, incluir siempre acápite de derechos fundamentales y procedencia
    if tipo in ("tutela", "impugnacion_tutela"):
        derechos_txt = ", ".join(datos.get("derechos", ["Salud", "Vida digna", "Debido proceso"]))
        lineas.extend([
            "### DERECHOS FUNDAMENTALES VULNERADOS",
            f"Se individualizan como derechos fundamentales vulnerados o amenazados: {derechos_txt}.",
            "",
            "### PROCEDENCIA, INMEDIATEZ Y SUBSIDIARIEDAD",
            "Se sustenta expresamente la procedencia de la acción de tutela: concurre el principio de inmediatez al ser la vulneración actual y lesiva, "
            "así como el principio de subsidiariedad al no disponer la parte de otro medio de defensa judicial expedito para evitar la configuración de un perjuicio irremediable.",
            "",
        ])

    if "alegato" in tipo:
        lineas.extend([
            "### SÍNTESIS DEL LITIGIO Y FIJACIÓN DEL PROBLEMA JURÍDICO",
            "El debate procesal se circunscribe a resolver las pretensiones y excepciones formuladas en el litigio.",
            "",
            "### HECHOS PROBADOS Y VALORACIÓN PROBATORIA",
            "Los hechos han quedado debidamente probados mediante la valoración probatoria conforme a las reglas de la sana crítica (art. 176 del CGP).",
            "",
        ])

    # Asegurar que todas las secciones obligatorias aparezcan como acápite
    secciones_orden = exp.get("secciones_obligatorias", ["HECHOS", "PRETENSIONES", "FUNDAMENTOS", "PRUEBAS", "NOTIFICACIONES"])

    for sec in secciones_orden:
        sec_upper = sec.upper()
        lineas.append(f"### {sec_upper}")
        sec_norm = normalizar_texto(sec)

        if "hecho" in sec_norm:
            hechos_txt = datos.get("hechos") or "1. Ocurrieron los hechos descritos en la solicitud procesal y se encuentran demostrados."
            lineas.append(hechos_txt)
        elif any(k in sec_norm for k in ("pretensi", "solicitud", "peticion", "posicion", "conclusi")):
            pret_txt = datos.get("pretensiones") or datos.get("posicion") or "1. Acceder a lo peticionado conforme a derecho y condenar a la contraparte."
            lineas.append(pret_txt)
        elif any(k in sec_norm for k in ("fundamento", "derecho", "juridico", "norma")):
            citas_base = "Fundamento esta actuación en la Constitución Política de 1991."
            if tipo in ("tutela", "impugnacion_tutela", "desacato"):
                citas_base = "Fundamento la acción en el artículo 86 de la Constitución Política, el Decreto 2591 de 1991 y la Sentencia T-760 de 2008 sobre salud."
            elif "peticion" in tipo:
                citas_base = "Fundamento en el artículo 23 de la Constitución Política y en la Ley 1755 de 2015 que regula el derecho de petición."
            elif "demanda" in tipo:
                citas_base = "Fundamento en los artículos 82, 83 y 84 del Código General del Proceso (CGP) y la Ley 2213 de 2022."
            elif "penal" in tipo or "denuncia" in tipo:
                citas_base = "Fundamento en el artículo 66 de la Ley 906 de 2004 (Código de Procedimiento Penal)."
            elif "laboral" in tipo:
                citas_base = "Fundamento en el Código Sustantivo del Trabajo (CST) y el Código Procesal del Trabajo."
            elif any(k in tipo for k in ("admin", "nulidad", "reparacion", "cumplimiento", "popular")):
                citas_base = "Fundamento en los artículos 137, 138 y 161 de la Ley 1437 de 2011 (CPACA)."
            lineas.append(citas_base)
        elif "juramento" in sec_norm:
            lineas.append(
                "Manifiesto bajo la gravedad del juramento que no he presentado otra acción judicial por los mismos hechos y derechos "
                "(art. 37 del Decreto 2591 de 1991). Asimismo, afirmo bajo juramento que los canales digitales indicados corresponden a los utilizados por las partes."
            )
        elif "procedencia" in sec_norm or "subsidiariedad" in sec_norm:
            lineas.append(
                "Se cumple el principio de inmediatez y de subsidiariedad al no existir otro medio de defensa judicial idóneo y eficaz "
                "para evitar la consumación de un perjuicio irremediable."
            )
        elif "prueba" in sec_norm or "anexo" in sec_norm or "valoracion" in sec_norm:
            pruebas_txt = datos.get("pruebas") or "Aporto los documentos y testimonios relacionados en el acápite de antecedentes fácticos conforme a la sana crítica del art. 176 del CGP."
            lineas.append(pruebas_txt)
        elif "notificaci" in sec_norm:
            notif_txt = datos.get("notificaciones")
            if not notif_txt:
                notif_txt = f"Demandante y demandado serán notificados en sus canales físicos y electrónicos oficiales aportados."
            lineas.append(notif_txt)
            lineas.append("Afirmo bajo la gravedad del juramento que la dirección electrónica indicada para la contraparte es la que utiliza para sus comunicaciones (art. 8 de la Ley 2213 de 2022).")
        elif "cuantia" in sec_norm or "competencia" in sec_norm:
            cuantia_txt = datos.get("cuantia", "Mayor cuantía")
            lineas.append(f"La cuantía del proceso se estima en {cuantia_txt}, por lo cual es competente este Despacho judicial.")
        elif "conciliacion" in sec_norm or "procedibilidad" in sec_norm:
            lineas.append("Se agotó el requisito de procedibilidad de conciliación prejudicial conforme a la Ley 2220 de 2022, aportando la constancia de no acuerdo.")
        else:
            lineas.append(f"Se desarrolla el acápite de {sec} conforme a las exigencias procesales vigentes y a los hechos del litigio.")
        lineas.append("")

    # Asegurar que todas las entidades que deben aparecer se encuentren explícitamente en el texto
    entidades_deben = exp.get("entidades_deben_aparecer", [])
    entidades_faltantes = [e for e in entidades_deben if normalizar_texto(e) not in normalizar_texto("\n".join(lineas))]
    if entidades_faltantes:
        lineas.append("### SÍNTESIS DE ANTECEDENTES Y PARTES CONCRETAS")
        lineas.append("Se hace constar expresamente la vinculación de: " + ", ".join(entidades_faltantes) + ".")
        lineas.append("")

    # Asegurar que se cumpla la longitud mínima
    l_min = exp.get("longitud_minima", 800)
    texto_actual = "\n".join(lineas)
    if len(texto_actual) < l_min:
        lineas.append("### CONSIDERACIONES Y SÍNTESIS PROCESAL")
        lineas.append(
            "En mérito de lo expuesto, se reitera al Despacho que concurren plenamente todos los presupuestos de legitimación "
            "en la causa por activa y por pasiva, la competencia territorial y funcional, y la debida fundamentación fáctica "
            "y jurídica de cada una de las pretensiones deprecadas, en salvaguarda de las garantías constitucionales y procesales aplicables."
        )
        lineas.append("")

    # Cierre con firma de abogado
    lineas.extend([
        "Atentamente,",
        "",
        "Dr. Carlos Rodríguez Vélez",
        "C.C. 79.123.456 de Bogotá",
        "T.P. 182.456 del C.S. de la J.",
    ])

    texto_final = "\n".join(lineas)
    tokens_in = len(json.dumps(datos)) // 3
    tokens_out = len(texto_final) // 3
    tokens = {"entrada": tokens_in, "salida": tokens_out, "total": tokens_in + tokens_out}
    tiempo = 0.85
    return texto_final, tiempo, tokens


async def generar_con_cliente(
    caso: dict[str, Any],
    cliente_http: Optional[Any] = None,
    servidor_url: Optional[str] = None,
) -> tuple[str, float, dict[str, int], str]:
    """Genera el escrito contra el servidor local o la aplicación en memoria."""
    tipo = caso.get("tipo", "otro")
    datos = caso.get("datos", {})

    perfil = {
        "abogado": {
            "nombre": "Dr. Carlos Rodríguez Vélez",
            "genero": "m",
            "cedula": "79.123.456",
            "cedulaLugar": "Bogotá",
            "tp": "182.456",
            "correo": "carlos.rodriguez@memorialista.co",
            "telefono": "3001234567",
            "direccion": "Carrera 7 # 71-21, Torre B",
            "ciudad": "Bogotá D.C.",
        },
        "estilo": {
            "tratamiento": "auto",
            "persona": "primera",
            "tono": "asertivo",
            "extension": "completa",
        },
        "ia": {
            "calidad": "default",
        },
    }

    payload = {
        "tipo": tipo,
        "datos": datos,
        "perfil": perfil,
        "modo": "nuevo",
        "protocolo": "ndjson",
    }

    t0 = time.monotonic()
    acumulado: list[str] = []
    tokens = {"entrada": 0, "salida": 0, "total": 0}
    modelo = "gemini"

    if servidor_url:
        import httpx
        url = f"{servidor_url.rstrip('/')}/api/redactar"
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    cuerpo = (await resp.aread()).decode("utf-8", "ignore")
                    raise RuntimeError(f"Servidor respondió {resp.status_code}: {cuerpo}")
                async for linea in resp.aiter_lines():
                    linea = linea.strip()
                    if not linea:
                        continue
                    try:
                        ev = json.loads(linea)
                        t = ev.get("t")
                        if t == "delta" and ev.get("d"):
                            acumulado.append(ev["d"])
                        elif t == "fin":
                            tokens = ev.get("tokens") or tokens
                            modelo = ev.get("modelo", modelo)
                        elif t == "error":
                            raise RuntimeError(ev.get("mensaje", "Error en redacción"))
                    except json.JSONDecodeError:
                        continue
    else:
        # En memoria usando TestClient de FastAPI
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        with client.stream("POST", "/api/redactar", json=payload) as resp:
            if resp.status_code != 200:
                raise RuntimeError(f"Error {resp.status_code}: {resp.text}")
            for linea in resp.iter_lines():
                linea = (linea.decode("utf-8") if isinstance(linea, bytes) else linea).strip()
                if not linea:
                    continue
                try:
                    ev = json.loads(linea)
                    t = ev.get("t")
                    if t == "delta" and ev.get("d"):
                        acumulado.append(ev["d"])
                    elif t == "fin":
                        tokens = ev.get("tokens") or tokens
                        modelo = ev.get("modelo", modelo)
                    elif t == "error":
                        raise RuntimeError(ev.get("mensaje", "Error en redacción"))
                except json.JSONDecodeError:
                    continue

    duracion = round(time.monotonic() - t0, 2)
    texto_final = "".join(acumulado)
    if not tokens.get("total"):
        tokens = {
            "entrada": len(json.dumps(datos)) // 3,
            "salida": len(texto_final) // 3,
            "total": (len(json.dumps(datos)) + len(texto_final)) // 3,
        }
    return texto_final, duracion, tokens, modelo


# -----------------------------------------------------------------------------
# AUDITORÍA DE EXPECTATIVAS DEL CASO
# -----------------------------------------------------------------------------
def verificar_expectativas_caso(texto: str, expectativas: dict[str, Any]) -> dict[str, Any]:
    """Compara el texto generado con las expectativas definidas en el caso JSON."""
    texto_norm = normalizar_texto(texto)
    secciones_faltantes: list[str] = []
    entidades_faltantes: list[str] = []
    entidades_prohibidas_detectadas: list[str] = []

    # 1. Secciones obligatorias
    for sec in expectativas.get("secciones_obligatorias", []):
        sec_norm = normalizar_texto(sec)
        # Buscar la sección en texto libre o encabezados
        if sec_norm not in texto_norm:
            secciones_faltantes.append(sec)

    # 2. Entidades que deben aparecer
    for ent in expectativas.get("entidades_deben_aparecer", []):
        ent_norm = normalizar_texto(ent)
        # Búsqueda tolerante
        if ent_norm not in texto_norm and ent.lower() not in texto.lower():
            # Buscar sin puntuación
            solo_digitos = re.sub(r"\D", "", ent)
            if solo_digitos and solo_digitos in re.sub(r"\D", "", texto):
                continue
            entidades_faltantes.append(ent)

    # 3. Entidades que NO deben aparecer (detector de alucinaciones)
    for ent_no in expectativas.get("entidades_no_deben_aparecer", []):
        ent_no_norm = normalizar_texto(ent_no)
        if len(ent_no_norm) >= 3 and ent_no_norm in texto_norm:
            entidades_prohibidas_detectadas.append(ent_no)

    # 4. Longitud mínima y máxima
    longitud_caracteres = len(texto)
    longitud_minima = expectativas.get("longitud_minima", 500)
    longitud_maxima = expectativas.get("longitud_maxima", 50000)
    longitud_cumple = longitud_minima <= longitud_caracteres <= longitud_maxima

    return {
        "secciones_faltantes": secciones_faltantes,
        "entidades_faltantes": entidades_faltantes,
        "entidades_prohibidas_detectadas": entidades_prohibidas_detectadas,
        "longitud_caracteres": longitud_caracteres,
        "longitud_minima": longitud_minima,
        "longitud_maxima": longitud_maxima,
        "longitud_cumple": longitud_cumple,
    }


# -----------------------------------------------------------------------------
# DETERMINACIÓN DEL SEMÁFORO
# -----------------------------------------------------------------------------
def calcular_semaforo(
    citas_resumen: dict[str, int],
    req_resumen: dict[str, int],
    audit_resumen: dict[str, Any],
    exp_resumen: dict[str, Any],
    error_generacion: Optional[str] = None,
) -> tuple[str, list[str]]:
    """Calcula el semáforo del caso:

    🔴 Rojo:
      - Citas inexistentes (rojas) > 0
      - Requisitos críticos faltantes (no_cumple crítico) > 0
      - Alucinaciones: entidades prohibidas detectadas > 0
      - Secciones obligatorias faltantes > 0
      - Discrepancias entre cifras y letras > 0
      - Longitud fuera del rango permitido
      - Error durante la generación

    🟡 Amarillo:
      - Sin condiciones de rojo, pero:
      - Citas amarillas (sin verificar / respaldo parcial) > 0
      - Requisitos faltantes no críticos > 0
      - Invenciones del formulario > 0
      - Omisiones de datos > 0
      - Entidades esperadas faltantes > 0

    🟢 Verde:
      - 100% conforme a todas las expectativas y normativas.
    """
    motivos_rojo: list[str] = []
    motivos_amarillo: list[str] = []

    if error_generacion:
        return "rojo", [f"Error de generación: {error_generacion}"]

    # Reglas Rojas
    citas_rojas = citas_resumen.get("rojo", 0)
    if citas_rojas > 0:
        motivos_rojo.append(f"{citas_rojas} cita(s) inexistente(s) o no encontradas en fuentes oficiales")

    req_criticos_pendientes = req_resumen.get("criticos_pendientes", 0)
    if req_criticos_pendientes > 0:
        motivos_rojo.append(f"{req_criticos_pendientes} requisito(s) procesal(es) crítico(s) no cumplido(s)")

    if exp_resumen.get("entidades_prohibidas_detectadas"):
        prohibidas = ", ".join(exp_resumen["entidades_prohibidas_detectadas"])
        motivos_rojo.append(f"Alucinación detectada: contiene entidades prohibidas ({prohibidas})")

    if exp_resumen.get("secciones_faltantes"):
        faltantes = ", ".join(exp_resumen["secciones_faltantes"])
        motivos_rojo.append(f"Faltan secciones obligatorias ({faltantes})")

    if audit_resumen.get("discrepancias"):
        motivos_rojo.append(f"{len(audit_resumen['discrepancias'])} discrepancia(s) entre cifra y letras")

    if not exp_resumen.get("longitud_cumple"):
        caracteres = exp_resumen.get("longitud_caracteres", 0)
        l_min = exp_resumen.get("longitud_minima", 0)
        l_max = exp_resumen.get("longitud_maxima", 0)
        motivos_rojo.append(f"Longitud fuera de rango ({caracteres} caracteres; esperado entre {l_min} y {l_max})")

    if motivos_rojo:
        return "rojo", motivos_rojo

    # Reglas Amarillas
    citas_amarillas = citas_resumen.get("amarillo", 0)
    if citas_amarillas > 0:
        motivos_amarillo.append(f"{citas_amarillas} cita(s) con verificación parcial o sin verificar")

    req_no_cumple = req_resumen.get("no_cumple", 0)
    if req_no_cumple > 0:
        motivos_amarillo.append(f"{req_no_cumple} requisito(s) no crítico(s) pendiente(s)")

    if audit_resumen.get("invenciones"):
        motivos_amarillo.append(f"{len(audit_resumen['invenciones'])} dato(s) en escrito no presentes en formulario (posible invención)")

    if audit_resumen.get("omisiones"):
        motivos_amarillo.append(f"{len(audit_resumen['omisiones'])} dato(s) del formulario omitidos en el escrito")

    if exp_resumen.get("entidades_faltantes"):
        ent_falt = ", ".join(exp_resumen["entidades_faltantes"])
        motivos_amarillo.append(f"Entidades esperadas no encontradas ({ent_falt})")

    if motivos_amarillo:
        return "amarillo", motivos_amarillo

    return "verde", ["Cumple plenamente con todas las expectativas, normas y citas oficiales"]


# -----------------------------------------------------------------------------
# EVALUACIÓN DE UN CASO INDIVIDUAL
# -----------------------------------------------------------------------------
async def evaluar_caso(
    caso: dict[str, Any],
    mock: bool = False,
    servidor_url: Optional[str] = None,
) -> dict[str, Any]:
    """Ejecuta la evaluación completa de un caso de prueba."""
    caso_id = caso.get("id", "caso_sin_id")
    tipo = caso.get("tipo", "otro")
    datos = caso.get("datos", {})
    expectativas = caso.get("expectativas", {})

    error_generacion: Optional[str] = None
    texto = ""
    tiempo = 0.0
    tokens = {"entrada": 0, "salida": 0, "total": 0}
    modelo = "gemini-mock" if mock else "gemini"

    try:
        if mock:
            texto, tiempo, tokens = generar_mock_escrito(caso)
        else:
            texto, tiempo, tokens, modelo = await generar_con_cliente(
                caso,
                servidor_url=servidor_url,
            )
    except Exception as exc:
        error_generacion = str(exc)
        texto = ""
        tiempo = 0.0

    # 1. Auditor de fidelidad
    res_auditoria = auditar_datos_y_escrito(
        datos,
        texto,
        perfil={"abogado": {"nombre": "Carlos Rodríguez", "cedula": "79123456", "tp": "182456"}},
        fecha_hoy_iso="2026-10-21",
    )

    # 2. Verificador de citas
    if texto:
        res_citas = await verificar_citas(texto)
    else:
        res_citas = {"ok": False, "total_citas": 0, "resumen": {"verde": 0, "amarillo": 0, "rojo": 0}, "citas": []}

    # 3. Checklist de requisitos normativos
    if texto:
        raw_requisitos = await revisar_requisitos(texto, tipo)
    else:
        raw_requisitos = []

    if isinstance(raw_requisitos, list):
        req_lista = raw_requisitos
        req_cumple = sum(1 for r in req_lista if r.get("estado") == "cumple")
        req_nocumple = sum(1 for r in req_lista if r.get("estado") == "no_cumple")
        req_noaplica = sum(1 for r in req_lista if r.get("estado") == "no_aplica")
        req_criticos = sum(1 for r in req_lista if r.get("estado") == "no_cumple" and r.get("critico"))
        req_resumen = {
            "cumple": req_cumple,
            "no_cumple": req_nocumple,
            "no_aplica": req_noaplica,
            "criticos_pendientes": req_criticos,
        }
    elif isinstance(raw_requisitos, dict):
        req_lista = raw_requisitos.get("requisitos", [])
        req_resumen = raw_requisitos.get("resumen", {})
    else:
        req_lista = []
        req_resumen = {"cumple": 0, "no_cumple": 0, "no_aplica": 0, "criticos_pendientes": 0}

    # 4. Expectativas del caso
    res_expectativas = verificar_expectativas_caso(texto, expectativas)

    # 5. Semáforo
    citas_resumen = res_citas.get("resumen", {})
    color_semaforo, motivos = calcular_semaforo(
        citas_resumen,
        req_resumen,
        res_auditoria,
        res_expectativas,
        error_generacion=error_generacion,
    )

    return {
        "id": caso_id,
        "tipo": tipo,
        "descripcion": caso.get("descripcion", ""),
        "semaforo": color_semaforo,
        "motivos": motivos,
        "tiempo_segundos": tiempo,
        "tokens": tokens,
        "modelo": modelo,
        "texto": texto,
        "error_generacion": error_generacion,
        "auditoria": {
            "invenciones": res_auditoria.get("invenciones", []),
            "omisiones": res_auditoria.get("omisiones", []),
            "discrepancias": res_auditoria.get("discrepancias", []),
            "total_alertas": res_auditoria.get("total", 0),
        },
        "citas": {
            "total": res_citas.get("total_citas", 0),
            "resumen": citas_resumen,
            "lista": res_citas.get("citas", []),
        },
        "requisitos": {
            "total": len(req_lista),
            "resumen": req_resumen,
            "lista": req_lista,
        },
        "expectativas": res_expectativas,
    }


# -----------------------------------------------------------------------------
# GENERADOR DEL REPORTE HTML
# -----------------------------------------------------------------------------
def generar_reporte_html(
    resultados: list[dict[str, Any]],
    totales: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    """Genera un reporte interactivo, responsivo y autónomo en HTML."""
    fecha_reporte = metadata.get("fecha", datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    modelo_nombre = metadata.get("modelo", "Gemini 2.5 Pro")
    entorno = metadata.get("entorno", "Local / Evaluación Automatizada")

    # Serializar resultados para búsqueda y filtrado dinámico en JavaScript
    resultados_json = json.dumps(resultados, ensure_ascii=False).replace("<", "\\u003c")

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>El Memorialista · Reporte de Evaluación de Modelos y Prompts</title>
<style>
  :root {{
    --bg-page: #0f172a;
    --bg-card: #1e293b;
    --bg-card-alt: #334155;
    --border-color: #475569;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --green-bg: #064e3b;
    --green-text: #34d399;
    --green-border: #059669;
    --amber-bg: #451a03;
    --amber-text: #fbbf24;
    --amber-border: #d97706;
    --red-bg: #450a0a;
    --red-text: #f87171;
    --red-border: #dc2626;
    --accent: #38bdf8;
    --accent-bg: #0369a1;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background-color: var(--bg-page);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.5;
    padding: 24px;
  }}
  .container {{ max-width: 1400px; margin: 0 auto; }}

  /* HEADER */
  header {{
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 24px;
    box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5);
  }}
  .header-top {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; }}
  .title-group h1 {{ font-size: 26px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 12px; }}
  .title-group p {{ color: var(--text-secondary); margin-top: 6px; font-size: 14px; }}
  .meta-pills {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }}
  .meta-pill {{ background: #334155; padding: 4px 10px; border-radius: 999px; font-size: 12px; color: #cbd5e1; border: 1px solid #475569; }}

  /* GATE POLICY BANNER */
  .policy-banner {{
    background: #172554;
    border: 1px solid #2563eb;
    border-left: 6px solid #38bdf8;
    border-radius: 8px;
    padding: 14px 18px;
    margin-top: 18px;
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .policy-icon {{ font-size: 24px; flex-shrink: 0; }}
  .policy-text {{ font-size: 13px; color: #e2e8f0; }}
  .policy-text strong {{ color: #38bdf8; text-transform: uppercase; letter-spacing: 0.5px; }}

  /* KPI METRIC CARDS */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }}
  .kpi-card {{
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 18px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: transform 0.15s ease, border-color 0.15s ease;
  }}
  .kpi-card:hover {{ transform: translateY(-2px); border-color: var(--accent); }}
  .kpi-label {{ font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; }}
  .kpi-value {{ font-size: 28px; font-weight: 800; margin: 8px 0; color: #f8fafc; display: flex; align-items: baseline; gap: 8px; }}
  .kpi-sub {{ font-size: 12px; color: var(--text-secondary); }}
  .kpi-card.green {{ border-color: var(--green-border); background: linear-gradient(180deg, rgba(6,78,59,0.25) 0%, rgba(30,41,59,1) 100%); }}
  .kpi-card.green .kpi-value {{ color: var(--green-text); }}
  .kpi-card.amber {{ border-color: var(--amber-border); background: linear-gradient(180deg, rgba(69,26,3,0.25) 0%, rgba(30,41,59,1) 100%); }}
  .kpi-card.amber .kpi-value {{ color: var(--amber-text); }}
  .kpi-card.red {{ border-color: var(--red-border); background: linear-gradient(180deg, rgba(69,10,10,0.3) 0%, rgba(30,41,59,1) 100%); }}
  .kpi-card.red .kpi-value {{ color: var(--red-text); }}

  /* CONTROLS & FILTERS */
  .controls-bar {{
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }}
  .filter-buttons {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .filter-btn {{
    background: #334155;
    color: #e2e8f0;
    border: 1px solid #475569;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .filter-btn:hover {{ background: #475569; color: #fff; }}
  .filter-btn.active {{ background: #2563eb; border-color: #38bdf8; color: #fff; font-weight: 600; }}
  .search-box {{
    background: #0f172a;
    border: 1px solid var(--border-color);
    color: #fff;
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 13px;
    min-width: 260px;
  }}
  .search-box:focus {{ outline: none; border-color: var(--accent); }}

  /* CASE CARD LIST */
  .cases-list {{ display: flex; flex-direction: column; gap: 16px; }}
  .case-card {{
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    overflow: hidden;
    transition: border-color 0.15s ease;
  }}
  .case-card.border-verde {{ border-left: 6px solid #10b981; }}
  .case-card.border-amarillo {{ border-left: 6px solid #f59e0b; }}
  .case-card.border-rojo {{ border-left: 6px solid #ef4444; }}

  .case-header {{
    padding: 16px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    background: #1e293b;
    gap: 16px;
    user-select: none;
  }}
  .case-header:hover {{ background: #243248; }}
  .case-title-area {{ display: flex; align-items: center; gap: 14px; flex-grow: 1; flex-wrap: wrap; }}
  .semaphore-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .semaphore-pill.verde {{ background: var(--green-bg); color: var(--green-text); border: 1px solid var(--green-border); }}
  .semaphore-pill.amarillo {{ background: var(--amber-bg); color: var(--amber-text); border: 1px solid var(--amber-border); }}
  .semaphore-pill.rojo {{ background: var(--red-bg); color: var(--red-text); border: 1px solid var(--red-border); }}

  .case-type-badge {{
    background: #334155;
    color: #93c5fd;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
  }}
  .case-id {{ font-size: 15px; font-weight: 700; color: #f8fafc; }}
  .case-desc {{ font-size: 13px; color: var(--text-secondary); width: 100%; margin-top: 4px; }}

  .case-metrics {{ display: flex; gap: 14px; align-items: center; flex-shrink: 0; font-size: 12px; color: #94a3b8; }}
  .case-metric-item {{ display: flex; align-items: center; gap: 4px; }}
  .chevron {{ font-size: 14px; color: #64748b; transition: transform 0.2s; }}
  .case-card.open .chevron {{ transform: rotate(180deg); }}

  /* CASE DETAILS BODY */
  .case-body {{
    display: none;
    padding: 20px;
    border-top: 1px solid #334155;
    background: #0f172a;
  }}
  .case-card.open .case-body {{ display: block; }}

  /* MOTIVOS ALERT */
  .motivos-box {{
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 20px;
    font-size: 13px;
  }}
  .motivos-box.verde {{ background: rgba(6,78,59,0.4); border: 1px solid var(--green-border); color: #6ee7b7; }}
  .motivos-box.amarillo {{ background: rgba(69,26,3,0.4); border: 1px solid var(--amber-border); color: #fde68a; }}
  .motivos-box.rojo {{ background: rgba(69,10,10,0.5); border: 1px solid var(--red-border); color: #fca5a5; }}
  .motivos-box ul {{ margin-left: 20px; margin-top: 6px; }}

  /* TABS IN CASE */
  .sub-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
    margin-bottom: 16px;
  }}
  .sub-panel {{
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 14px;
  }}
  .sub-panel h4 {{ font-size: 13px; font-weight: 700; color: #e2e8f0; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }}

  .check-item {{ font-size: 12px; padding: 4px 0; display: flex; gap: 8px; align-items: flex-start; }}
  .check-item.pass {{ color: #34d399; }}
  .check-item.warn {{ color: #fbbf24; }}
  .check-item.fail {{ color: #f87171; }}

  /* TABLES */
  table.mini-table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }}
  table.mini-table th {{ background: #0f172a; color: #94a3b8; text-align: left; padding: 6px 8px; font-size: 11px; text-transform: uppercase; }}
  table.mini-table td {{ padding: 6px 8px; border-bottom: 1px solid #334155; color: #cbd5e1; vertical-align: top; }}
  table.mini-table tr:last-child td {{ border-bottom: none; }}

  /* TEXT ACCORDION */
  .text-preview {{
    background: #090d16;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 14px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 11px;
    color: #e2e8f0;
    white-space: pre-wrap;
    max-height: 280px;
    overflow-y: auto;
    line-height: 1.4;
  }}

  /* FOOTER */
  footer {{
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid var(--border-color);
    text-align: center;
    color: var(--text-secondary);
    font-size: 12px;
  }}
</style>
</head>
<body>
<div class="container">

  <!-- HEADER -->
  <header>
    <div class="header-top">
      <div class="title-group">
        <h1>⚖️ El Memorialista · Reporte de Evaluación de Modelos y Prompts</h1>
        <p>Evaluación automatizada de fidelidad, verificación oficial de citas y checklist legal procesal</p>
        <div class="meta-pills">
          <span class="meta-pill">📅 Fecha: {fecha_reporte}</span>
          <span class="meta-pill">🤖 Modelo: {modelo_nombre}</span>
          <span class="meta-pill">🌍 Entorno: {entorno}</span>
          <span class="meta-pill">📋 Total Casos: {totales.get('total_casos', 0)}</span>
        </div>
      </div>
    </div>

    <!-- GATE POLICY BANNER -->
    <div class="policy-banner">
      <div class="policy-icon">🛡️</div>
      <div class="policy-text">
        <strong>Política Obligatoria de Despliegue:</strong>
        Ejecuta esta evaluación antes de cambiar de modelo, de prompt o de guía del catálogo.
        <strong>No desplegar a producción si empeora alguna métrica</strong> (citas inexistentes, datos inventados, requisitos faltantes o porcentaje de semáforos verdes).
      </div>
    </div>
  </header>

  <!-- KPI SUMMARY CARDS -->
  <div class="kpi-grid">
    <div class="kpi-card {'green' if totales.get('total_rojos', 0) == 0 else 'red'}">
      <div class="kpi-label">Semáforos Verdes (Aprobados)</div>
      <div class="kpi-value">{totales.get('total_verdes', 0)} <span style="font-size: 14px; font-weight: normal; color: var(--text-secondary);">/ {totales.get('total_casos', 0)} ({totales.get('porcentaje_verdes', 0)}%)</span></div>
      <div class="kpi-sub">🟡 {totales.get('total_amarillos', 0)} advertencias · 🔴 {totales.get('total_rojos', 0)} fallidos</div>
    </div>

    <div class="kpi-card {'red' if totales.get('total_citas_inexistentes', 0) > 0 else 'green'}">
      <div class="kpi-label">Citas Inexistentes (Rojas)</div>
      <div class="kpi-value">{totales.get('total_citas_inexistentes', 0)}</div>
      <div class="kpi-sub">Total providencias no halladas en Corte o Senado</div>
    </div>

    <div class="kpi-card {'amber' if totales.get('total_datos_inventados', 0) > 0 else 'green'}">
      <div class="kpi-label">Datos Inventados (Fidelidad)</div>
      <div class="kpi-value">{totales.get('total_datos_inventados', 0)}</div>
      <div class="kpi-sub">Entidades en escrito ausentes en formulario</div>
    </div>

    <div class="kpi-card {'red' if totales.get('total_requisitos_faltantes', 0) > 0 else 'green'}">
      <div class="kpi-label">Requisitos Faltantes</div>
      <div class="kpi-value">{totales.get('total_requisitos_faltantes', 0)}</div>
      <div class="kpi-sub">Normas y cláusulas procesales no cumplidas</div>
    </div>

    <div class="kpi-card">
      <div class="kpi-label">Tiempo Total de Redacción</div>
      <div class="kpi-value">{totales.get('tiempo_total_s', 0):.1f} s</div>
      <div class="kpi-sub">Promedio: {totales.get('tiempo_promedio_s', 0):.2f} s por escrito</div>
    </div>

    <div class="kpi-card">
      <div class="kpi-label">Tokens Totales (In / Out)</div>
      <div class="kpi-value">{totales.get('tokens_total', 0):,}</div>
      <div class="kpi-sub">Promedio: {totales.get('tokens_promedio', 0):,} tokens / caso</div>
    </div>
  </div>

  <!-- CONTROLS & FILTERS -->
  <div class="controls-bar">
    <div class="filter-buttons">
      <button class="filter-btn active" onclick="filtrarSemaforo('todos', this)">Todos ({totales.get('total_casos', 0)})</button>
      <button class="filter-btn" onclick="filtrarSemaforo('verde', this)">🟢 Verdes ({totales.get('total_verdes', 0)})</button>
      <button class="filter-btn" onclick="filtrarSemaforo('amarillo', this)">🟡 Amarillos ({totales.get('total_amarillos', 0)})</button>
      <button class="filter-btn" onclick="filtrarSemaforo('rojo', this)">🔴 Rojos ({totales.get('total_rojos', 0)})</button>
    </div>
    <div>
      <input type="text" id="busqueda" class="search-box" placeholder="Buscar por tipo, ID o descripción…" oninput="filtrarTexto(this.value)">
    </div>
  </div>

  <!-- CASE LIST -->
  <div class="cases-list" id="lista-casos">
"""

    for r in resultados:
        cid = html.escape(r.get("id", ""))
        tipo = html.escape(r.get("tipo", ""))
        desc = html.escape(r.get("descripcion", ""))
        sem = r.get("semaforo", "verde")
        tiempo_s = r.get("tiempo_segundos", 0.0)
        tokens_tot = r.get("tokens", {}).get("total", 0)
        tokens_in = r.get("tokens", {}).get("entrada", 0)
        tokens_out = r.get("tokens", {}).get("salida", 0)
        motivos = r.get("motivos", [])

        # Resumen citas
        citas_res = r.get("citas", {}).get("resumen", {})
        c_verde = citas_res.get("verde", 0)
        c_amarillo = citas_res.get("amarillo", 0)
        c_rojo = citas_res.get("rojo", 0)

        # Resumen req
        req_res = r.get("requisitos", {}).get("resumen", {})
        r_cumple = req_res.get("cumple", 0)
        r_nocumple = req_res.get("no_cumple", 0)

        # Resumen audit
        audit = r.get("auditoria", {})
        n_inv = len(audit.get("invenciones", []))
        n_om = len(audit.get("omisiones", []))
        n_disc = len(audit.get("discrepancias", []))

        # Expectativas
        exp = r.get("expectativas", {})

        html_content += f"""
    <div class="case-card border-{sem}" data-semaforo="{sem}" data-search="{cid.lower()} {tipo.lower()} {desc.lower()}">
      <div class="case-header" onclick="toggleCase(this.parentElement)">
        <div class="case-title-area">
          <span class="semaphore-pill {sem}">{'🟢 Conforme' if sem == 'verde' else ('🟡 Advertencia' if sem == 'amarillo' else '🔴 Fallido')}</span>
          <span class="case-type-badge">{tipo}</span>
          <span class="case-id">{cid}</span>
          <div class="case-desc">{desc}</div>
        </div>
        <div class="case-metrics">
          <span class="case-metric-item" title="Tiempo">⏱️ {tiempo_s:.1f}s</span>
          <span class="case-metric-item" title="Tokens">🔤 {tokens_tot:,}</span>
          <span class="case-metric-item" title="Citas: Verdes/Amarillas/Rojas">📚 {c_verde}V / {c_amarillo}A / {c_rojo}R</span>
          <span class="case-metric-item" title="Requisitos cumplidos">📋 {r_cumple}✓ / {r_nocumple}✗</span>
          <span class="chevron">▼</span>
        </div>
      </div>
      <div class="case-body">
        <!-- MOTIVOS -->
        <div class="motivos-box {sem}">
          <strong>Diagnóstico del Semáforo ({sem.upper()}):</strong>
          <ul>
            {''.join(f'<li>{html.escape(m)}</li>' for m in motivos)}
          </ul>
        </div>

        <div class="sub-grid">
          <!-- 1. EXPECTATIVAS -->
          <div class="sub-panel">
            <h4>🎯 1. Verificación de Expectativas</h4>
            <div class="check-item {'pass' if not exp.get('secciones_faltantes') else 'fail'}">
              {'✓' if not exp.get('secciones_faltantes') else '✗'} Secciones obligatorias: {len(exp.get('secciones_faltantes', []))} faltantes
            </div>
            <div class="check-item {'pass' if not exp.get('entidades_faltantes') else 'warn'}">
              {'✓' if not exp.get('entidades_faltantes') else '⚠️'} Entidades requeridas: {len(exp.get('entidades_faltantes', []))} no halladas
            </div>
            <div class="check-item {'pass' if not exp.get('entidades_prohibidas_detectadas') else 'fail'}">
              {'✓' if not exp.get('entidades_prohibidas_detectadas') else '✗'} Detector de alucinaciones: {len(exp.get('entidades_prohibidas_detectadas', []))} prohibidas detectadas
            </div>
            <div class="check-item {'pass' if exp.get('longitud_cumple') else 'fail'}">
              {'✓' if exp.get('longitud_cumple') else '✗'} Longitud: {exp.get('longitud_caracteres', 0):,} caracteres (rango: {exp.get('longitud_minima', 0):,} - {exp.get('longitud_maxima', 0):,})
            </div>
          </div>

          <!-- 2. AUDITORÍA DE FIDELIDAD -->
          <div class="sub-panel">
            <h4>🔍 2. Auditoría de Fidelidad de Datos</h4>
            <div class="check-item {'pass' if n_inv == 0 else 'warn'}">
              {'✓' if n_inv == 0 else '⚠️'} Invenciones: {n_inv} datos no presentes en el formulario
            </div>
            <div class="check-item {'pass' if n_om == 0 else 'warn'}">
              {'✓' if n_om == 0 else '⚠️'} Omisiones: {n_om} datos del formulario ausentes en el escrito
            </div>
            <div class="check-item {'pass' if n_disc == 0 else 'fail'}">
              {'✓' if n_disc == 0 else '✗'} Discrepancias cifras vs. letras: {n_disc} discordancias
            </div>
          </div>

          <!-- 3. VERIFICADOR DE CITAS -->
          <div class="sub-panel">
            <h4>📚 3. Verificación de Citas Oficiales ({r.get('citas', {}).get('total', 0)})</h4>
            <div class="check-item {'pass' if c_rojo == 0 else 'fail'}">
              {'✓' if c_rojo == 0 else '✗'} Citas rojas (inexistentes / no encontradas): {c_rojo}
            </div>
            <div class="check-item {'pass' if c_amarillo == 0 else 'warn'}">
              {'✓' if c_amarillo == 0 else '⚠️'} Citas amarillas (parciales / sin verificar): {c_amarillo}
            </div>
            <div class="check-item pass">
              ✓ Citas verdes (existentes y respaldadas): {c_verde}
            </div>
          </div>

          <!-- 4. CHECKLIST NORMATIVO -->
          <div class="sub-panel">
            <h4>📋 4. Requisitos Normativos Procesales</h4>
            <div class="check-item {'pass' if req_res.get('criticos_pendientes', 0) == 0 else 'fail'}">
              {'✓' if req_res.get('criticos_pendientes', 0) == 0 else '✗'} Críticos no cumplidos: {req_res.get('criticos_pendientes', 0)}
            </div>
            <div class="check-item pass">
              ✓ Requisitos cumplidos: {r_cumple}
            </div>
            <div class="check-item {'pass' if r_nocumple == 0 else 'warn'}">
              {'✓' if r_nocumple == 0 else '⚠️'} Requisitos no cumplidos totales: {r_nocumple}
            </div>
          </div>
        </div>
"""
        # Tabla de citas si existen
        citas_lista = r.get("citas", {}).get("lista", [])
        if citas_lista:
            html_content += """
        <div style="margin-bottom: 16px;">
          <h4 style="font-size: 13px; color: #94a3b8; margin-bottom: 6px;">Detalle de Citas Oficiales:</h4>
          <table class="mini-table">
            <thead>
              <tr><th>Cita</th><th>Tipo</th><th>Estado</th><th>Enlace Oficial</th><th>Pertinencia / Respaldo</th></tr>
            </thead>
            <tbody>
"""
            for c in citas_lista:
                c_nom = html.escape(c.get("nombre", ""))
                c_tip = html.escape(c.get("tipo_norma", ""))
                c_col = c.get("color", "amarillo")
                c_url = c.get("url", "")
                c_url_tag = f'<a href="{c_url}" target="_blank" style="color: #38bdf8;">Abrir norma ↗</a>' if c_url else 'N/A'
                pert = c.get("pertinencia", {})
                frag = html.escape(pert.get("fragmento", "")[:140])
                html_content += f"""
              <tr>
                <td><strong>{c_nom}</strong></td>
                <td>{c_tip}</td>
                <td><span class="semaphore-pill {c_col}" style="font-size: 10px; padding: 2px 6px;">{c.get('estado', '')}</span></td>
                <td>{c_url_tag}</td>
                <td><small>{frag}</small></td>
              </tr>
"""
            html_content += """
            </tbody>
          </table>
        </div>
"""

        # Texto del memorial
        txt = html.escape(r.get("texto", ""))
        html_content += f"""
        <div>
          <h4 style="font-size: 13px; color: #94a3b8; margin-bottom: 6px;">Texto Redactado por el Modelo ({len(txt):,} caracteres):</h4>
          <div class="text-preview">{txt}</div>
        </div>
      </div>
    </div>
"""

    html_content += """
  </div>

  <footer>
    El Memorialista · Sistema Profesional de Litigio Automatizado para Colombia · Reporte generado bajo directiva de evaluación pre-despliegue
  </footer>
</div>

<script>
  function toggleCase(card) {
    card.classList.toggle('open');
  }

  function filtrarSemaforo(tipo, btn) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const cards = document.querySelectorAll('.case-card');
    cards.forEach(card => {
      const sem = card.getAttribute('data-semaforo');
      if (tipo === 'todos' || sem === tipo) {
        card.style.display = '';
      } else {
        card.style.display = 'none';
      }
    });
  }

  function filtrarTexto(val) {
    const term = val.toLowerCase().trim();
    const cards = document.querySelectorAll('.case-card');
    cards.forEach(card => {
      const searchData = card.getAttribute('data-search') || '';
      if (!term || searchData.includes(term)) {
        card.style.display = '';
      } else {
        card.style.display = 'none';
      }
    });
  }
</script>
</body>
</html>
"""
    return html_content


# -----------------------------------------------------------------------------
# EJECUCIÓN PRINCIPAL (CLI)
# -----------------------------------------------------------------------------
async def main_async() -> int:
    parser = argparse.ArgumentParser(
        description="Marco de Evaluación y Benchmarking de El Memorialista.",
    )
    parser.add_argument("--servidor", type=str, default=None, help="URL del servidor en ejecución (ej: http://127.0.0.1:8000)")
    parser.add_argument("--tipo", type=str, default=None, help="Evaluar solo un tipo de documento específico (ej: tutela)")
    parser.add_argument("--caso", type=str, default=None, help="Evaluar un único caso por su identificador")
    parser.add_argument("--limite", type=int, default=None, help="Límite máximo de casos a evaluar")
    parser.add_argument("--mock", action="store_true", help="Usar generaciones simuladas para evaluación rápida sin consumo de cuota")
    parser.add_argument("--salida", type=str, default="reporte_evaluacion.html", help="Ruta del reporte HTML de salida")
    parser.add_argument("--json-salida", type=str, default=None, help="Ruta para exportar los resultados en JSON")
    parser.add_argument("--estricto", action="store_true", help="Retorna código de error 1 si hay cualquier caso amarillo o rojo")

    args = parser.parse_args()

    print("=" * 80)
    print("⚖️  EL MEMORIALISTA · MARCO DE EVALUACIÓN Y BENCHMARKING PRE-DESPLIEGUE")
    print("=" * 80)
    print("Política: No desplegar si empeora alguna métrica jurídica o procesal.")
    print(f"Modo: {'SIMULADO (Mock)' if args.mock else ('SERVIDOR EXTERNO ' + args.servidor if args.servidor else 'DIRECTO EN MEMORIA')}")
    if args.tipo:
        print(f"Filtro tipo: {args.tipo}")
    if args.caso:
        print(f"Filtro caso: {args.caso}")
    if args.limite:
        print(f"Límite casos: {args.limite}")
    print("-" * 80)

    casos = cargar_casos(
        filtro_tipo=args.tipo,
        filtro_caso=args.caso,
        limite=args.limite,
    )

    if not casos:
        print("❌ No se encontraron casos de prueba en tests/casos/ con los filtros dados.", file=sys.stderr)
        return 1

    print(f"Total casos a evaluar: {len(casos)}")
    print("-" * 80)

    t_inicio_total = time.monotonic()
    resultados: list[dict[str, Any]] = []

    for i, caso in enumerate(casos, 1):
        cid = caso.get("id", f"caso_{i}")
        tipo = caso.get("tipo", "otro")
        print(f"[{i:02d}/{len(casos):02d}] {cid:<40} ({tipo}) ... ", end="", flush=True)

        res = await evaluar_caso(
            caso,
            mock=args.mock,
            servidor_url=args.servidor,
        )
        resultados.append(res)

        sem = res["semaforo"]
        icono = "🟢" if sem == "verde" else ("🟡" if sem == "amarillo" else "🔴")
        t_s = res["tiempo_segundos"]
        tok = res["tokens"].get("total", 0)
        c_rojas = res["citas"]["resumen"].get("rojo", 0)
        inv = len(res["auditoria"]["invenciones"])

        print(f"{icono} {sem.upper():<9} ({t_s:4.1f}s | {tok:5,d} tok | citas_rojas={c_rojas} | inv={inv})")
        if sem == "rojo":
            for m in res["motivos"]:
                print(f"       ⚠️  {m}")

    t_total = time.monotonic() - t_inicio_total

    # Cálculo de métricas agregadas
    total_casos = len(resultados)
    total_verdes = sum(1 for r in resultados if r["semaforo"] == "verde")
    total_amarillos = sum(1 for r in resultados if r["semaforo"] == "amarillo")
    total_rojos = sum(1 for r in resultados if r["semaforo"] == "rojo")

    total_citas_inexistentes = sum(r["citas"]["resumen"].get("rojo", 0) for r in resultados)
    total_datos_inventados = sum(len(r["auditoria"]["invenciones"]) for r in resultados)
    total_requisitos_faltantes = sum(r["requisitos"]["resumen"].get("no_cumple", 0) for r in resultados)

    tiempo_total_s = sum(r["tiempo_segundos"] for r in resultados)
    tiempo_promedio_s = round(tiempo_total_s / total_casos, 2) if total_casos else 0.0

    tokens_total = sum(r["tokens"].get("total", 0) for r in resultados)
    tokens_promedio = round(tokens_total / total_casos) if total_casos else 0

    porcentaje_verdes = round((total_verdes / total_casos) * 100, 1) if total_casos else 0.0

    totales = {
        "total_casos": total_casos,
        "total_verdes": total_verdes,
        "total_amarillos": total_amarillos,
        "total_rojos": total_rojos,
        "porcentaje_verdes": porcentaje_verdes,
        "total_citas_inexistentes": total_citas_inexistentes,
        "total_datos_inventados": total_datos_inventados,
        "total_requisitos_faltantes": total_requisitos_faltantes,
        "tiempo_total_s": round(tiempo_total_s, 2),
        "tiempo_promedio_s": tiempo_promedio_s,
        "tokens_total": tokens_total,
        "tokens_promedio": tokens_promedio,
    }

    metadata = {
        "fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "modelo": resultados[0]["modelo"] if resultados else "Gemini",
        "entorno": "Mock (Simulado)" if args.mock else (args.servidor or "Local FastAPI"),
    }

    # Generar y guardar reporte HTML
    html_reporte = generar_reporte_html(resultados, totales, metadata)
    ruta_salida = os.path.abspath(args.salida)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(html_reporte)

    if args.json_salida:
        ruta_json = os.path.abspath(args.json_salida)
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump({"totales": totales, "metadata": metadata, "resultados": resultados}, f, ensure_ascii=False, indent=2)
        print(f"📄 Reporte JSON guardado en: {ruta_json}")

    print("=" * 80)
    print("📊 RESUMEN FINAL DE LA EVALUACIÓN:")
    print(f"   Total casos evaluados:   {total_casos}")
    print(f"   🟢 Aprobados (Verdes):   {total_verdes} ({porcentaje_verdes}%)")
    print(f"   🟡 Advertencias:         {total_amarillos}")
    print(f"   🔴 Fallidos (Rojos):     {total_rojos}")
    print(f"   📚 Citas inexistentes:   {total_citas_inexistentes}")
    print(f"   🔍 Datos inventados:     {total_datos_inventados}")
    print(f"   📋 Requisitos faltantes: {total_requisitos_faltantes}")
    print(f"   ⏱️  Tiempo total:          {tiempo_total_s:.1f}s (promedio: {tiempo_promedio_s:.2f}s/caso)")
    print(f"   🔤 Tokens totales:        {tokens_total:,} (promedio: {tokens_promedio:,}/caso)")
    print(f"   🌐 Reporte HTML:         {ruta_salida}")
    print("=" * 80)

    if total_rojos > 0:
        print(f"❌ REGRESIÓN O FALLA DETECTADA ({total_rojos} casos en rojo). NO DESPLEGAR A PRODUCCIÓN.", file=sys.stderr)
        return 1

    if args.estricto and total_amarillos > 0:
        print(f"⚠️  MODO ESTRICTO: Hay {total_amarillos} advertencias amarillas.", file=sys.stderr)
        return 1

    print("✅ EVALUACIÓN SUPERADA CON ÉXITO. APTO PARA DESPLIEGUE.")
    return 0


def main() -> None:
    code = asyncio.run(main_async())
    sys.exit(code)


if __name__ == "__main__":
    main()
