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
