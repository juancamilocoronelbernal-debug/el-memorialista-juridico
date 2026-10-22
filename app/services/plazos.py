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
