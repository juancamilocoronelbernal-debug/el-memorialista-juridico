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
