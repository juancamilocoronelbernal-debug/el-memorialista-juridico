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
