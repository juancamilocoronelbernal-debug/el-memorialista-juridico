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
