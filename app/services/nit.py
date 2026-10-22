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
