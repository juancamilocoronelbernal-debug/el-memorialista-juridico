"""Pruebas unitarias e integrales para el cómputo de términos y plazos procesales en Colombia.

Verifica:
- Festivos de Colombia bajo la Ley 51 de 1983 (Ley Emiliani) y algoritmo de Pascua Meeus/Butcher.
- Cruce de festivos ordinarios.
- Cruce de Semana Santa judicial (lunes a viernes santos inhábiles).
- Cruce de fin de año y vacancia judicial colectiva (20 de diciembre a 10 de enero, art. 146 Ley 270/96).
- Cómputo de meses y años con traslado de inhábil a primer día hábil siguiente (art. 118 CGP).
- Notificación por mensaje de datos (art. 8 Ley 2213 de 2022: 2 días hábiles de gracia).
- Precargas normativas del catálogo judicial.
- Generación de archivos iCalendar (.ics RFC 5545).
- Endpoints HTTP: POST /api/plazos, GET /api/plazos/catalogo, POST /api/plazos/ics.
"""

import datetime
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.plazos import (
    calcular_domingo_pascua,
    obtener_festivos_colombia,
    trasladar_al_siguiente_lunes,
    es_dia_habil,
    dia_habil_siguiente,
    sumar_meses_calendario,
    sumar_anios_calendario,
    procesar_notificacion_mensaje_datos,
    calcular_plazo,
    generar_evento_ics,
    obtener_precargas_terminos,
    buscar_precarga,
)

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. ALGORITMO DE PASCUA Y FESTIVOS LEY 51 DE 1983
# -----------------------------------------------------------------------------
def test_algoritmo_pascua_meeus_butcher():
    """Verifica las fechas del Domingo de Pascua para varios años astronómicamente confirmados."""
    assert calcular_domingo_pascua(2024) == datetime.date(2024, 3, 31)
    assert calcular_domingo_pascua(2025) == datetime.date(2025, 4, 20)
    assert calcular_domingo_pascua(2026) == datetime.date(2026, 4, 5)
    assert calcular_domingo_pascua(2027) == datetime.date(2027, 3, 28)


def test_festivos_colombia_ley_emiliani():
    """Verifica los festivos oficiales de Colombia en 2026."""
    festivos_2026 = obtener_festivos_colombia(2026)
    assert len(festivos_2026) == 18

    # Festivos fijos
    assert datetime.date(2026, 1, 1) in festivos_2026  # Año nuevo
    assert datetime.date(2026, 5, 1) in festivos_2026  # Trabajo
    assert datetime.date(2026, 7, 20) in festivos_2026  # Independencia
    assert datetime.date(2026, 8, 7) in festivos_2026  # Batalla de Boyacá
    assert datetime.date(2026, 12, 8) in festivos_2026  # Inmaculada Concepción
    assert datetime.date(2026, 12, 25) in festivos_2026  # Navidad

    # Festivos de Semana Santa 2026 (Pascua = 5 de abril)
    assert datetime.date(2026, 4, 2) in festivos_2026  # Jueves Santo
    assert datetime.date(2026, 4, 3) in festivos_2026  # Viernes Santo

    # Festivos trasladados al lunes
    # Reyes Magos (6 enero cae martes -> lunes 12 enero)
    assert datetime.date(2026, 1, 12) in festivos_2026
    # San José (19 marzo cae jueves -> lunes 23 marzo)
    assert datetime.date(2026, 3, 23) in festivos_2026
    # San Pedro y San Pablo (29 junio ya es lunes)
    assert datetime.date(2026, 6, 29) in festivos_2026
    # Asunción de la Virgen (15 agosto sábado -> lunes 17 agosto)
    assert datetime.date(2026, 8, 17) in festivos_2026
    # Todos los Santos (1 nov domingo -> lunes 2 nov)
    assert datetime.date(2026, 11, 2) in festivos_2026
    # Independencia de Cartagena (11 nov miércoles -> lunes 16 nov)
    assert datetime.date(2026, 11, 16) in festivos_2026

    # Móviles de Pascua
    # Ascensión del Señor: lunes 18 de mayo de 2026
    assert datetime.date(2026, 5, 18) in festivos_2026
    # Corpus Christi: lunes 8 de junio de 2026
    assert datetime.date(2026, 6, 8) in festivos_2026
    # Sagrado Corazón: lunes 15 de junio de 2026
    assert datetime.date(2026, 6, 15) in festivos_2026


# -----------------------------------------------------------------------------
# 2. CRUCE DE FESTIVOS ORDINARIOS
# -----------------------------------------------------------------------------
def test_computo_cruza_puente_festivo():
    """Término de 3 días notificado el viernes antes de un puente festivo (San José).

    Notificación: viernes 20 de marzo de 2026.
    Sábado 21 y domingo 22: inhábiles.
    Lunes 23 de marzo de 2026: Festivo San José.
    Día 1 hábil: martes 24 de marzo de 2026.
    Día 2 hábil: miércoles 25 de marzo de 2026.
    Día 3 hábil (Vencimiento): jueves 26 de marzo de 2026.
    """
    res = calcular_plazo(
        fecha_inicio="2026-03-20",
        unidad="dias_habiles",
        cantidad=3,
        vacancia_colectiva=False,
    )
    assert res["fecha_inicio_computo"] == "2026-03-24"
    assert res["fecha_vencimiento"] == "2026-03-26"
    assert res["dia_semana_vencimiento"] == "Jueves"


# -----------------------------------------------------------------------------
# 3. CRUCE DE SEMANA SANTA JUDICIAL
# -----------------------------------------------------------------------------
def test_computo_cruza_semana_santa_judicial():
    """Término de 3 días de impugnación de tutela notificado el viernes previo a Semana Santa.

    Fecha notificación: viernes 27 de marzo de 2026.
    Sábado 28 y domingo 29: fin de semana inhábil.
    Lunes Santo 30 de marzo: sin despacho judicial.
    Martes Santo 31 de marzo: sin despacho judicial.
    Miércoles Santo 1 de abril: sin despacho judicial.
    Jueves Santo 2 de abril: festivo nacional.
    Viernes Santo 3 de abril: festivo nacional.
    Sábado 4 y domingo 5 de abril (Pascua): fin de semana inhábil.
    Día 1 hábil: lunes 6 de abril de 2026.
    Día 2 hábil: martes 7 de abril de 2026.
    Día 3 hábil (Vencimiento): miércoles 8 de abril de 2026.
    """
    res = calcular_plazo(
        fecha_inicio="2026-03-27",
        unidad="dias_habiles",
        cantidad=3,
        tipo_termino="impugnacion_tutela",
        vacancia_colectiva=False,
    )
    assert res["fecha_inicio_computo"] == "2026-04-06"
    assert res["fecha_vencimiento"] == "2026-04-08"
    assert res["dia_semana_vencimiento"] == "Miércoles"


# -----------------------------------------------------------------------------
# 4. CRUCE DE FIN DE AÑO Y VACANCIA JUDICIAL COLECTIVA
# -----------------------------------------------------------------------------
def test_computo_cruza_vacancia_judicial_fin_de_ano():
    """Término de 3 días con vacancia judicial colectiva de fin de año (20 dic a 10 ene).

    Notificación: viernes 18 de diciembre de 2026.
    Sábado 19 de diciembre: inhábil.
    Del 20 de diciembre de 2026 al 10 de enero de 2027: Vacancia judicial colectiva (art. 146 Ley 270/96).
    Domingo 10 de enero de 2027: inhábil.
    Lunes 11 de enero de 2027: Festivo Reyes Magos (trasladado del 6 de enero).
    Día 1 hábil: martes 12 de enero de 2027.
    Día 2 hábil: miércoles 13 de enero de 2027.
    Día 3 hábil (Vencimiento): jueves 14 de enero de 2027.
    """
    res = calcular_plazo(
        fecha_inicio="2026-12-18",
        unidad="dias_habiles",
        cantidad=3,
        vacancia_colectiva=True,
    )
    assert res["fecha_inicio_computo"] == "2027-01-12"
    assert res["fecha_vencimiento"] == "2027-01-14"
    assert res["dia_semana_vencimiento"] == "Jueves"


def test_computo_fin_de_ano_sin_vacancia_colectiva():
    """Término de tutela o administrativo donde NO aplica vacancia colectiva.

    Notificación: viernes 18 de diciembre de 2026.
    Vacancia colectiva = False (tutela / control de garantías).
    Sábado 19 y domingo 20: fin de semana inhábil.
    Día 1 hábil: lunes 21 de diciembre de 2026.
    Día 2 hábil: martes 22 de diciembre de 2026.
    Día 3 hábil (Vencimiento): miércoles 23 de diciembre de 2026.
    """
    res = calcular_plazo(
        fecha_inicio="2026-12-18",
        unidad="dias_habiles",
        cantidad=3,
        vacancia_colectiva=False,
    )
    assert res["fecha_inicio_computo"] == "2026-12-21"
    assert res["fecha_vencimiento"] == "2026-12-23"


# -----------------------------------------------------------------------------
# 5. CÓMPUTO DE MESES Y AÑOS (ART. 118 CGP)
# -----------------------------------------------------------------------------
def test_computo_meses_calendario_con_ultimo_dia_inhabiles():
    """Término de 1 mes donde el último día cae en fin de semana y festivo.

    Fecha de inicio: 18 de junio de 2026.
    1 mes calendario: 18 de julio de 2026 (sábado inhábil).
    Domingo 19 de julio: inhábil.
    Lunes 20 de julio de 2026: Festivo nacional Día de la Independencia.
    Conforme al art. 118 CGP, se extiende automáticamente hasta el primer día hábil siguiente:
    Martes 21 de julio de 2026.
    """
    res = calcular_plazo(
        fecha_inicio="2026-06-18",
        unidad="meses",
        cantidad=1,
    )
    assert res["fecha_vencimiento"] == "2026-07-21"
    assert res["dia_semana_vencimiento"] == "Martes"


def test_computo_meses_ajuste_fin_de_mes():
    """Término de 1 mes que inicia el 31 de enero en año no bisiesto (2026).

    El mes de febrero no tiene día 31, por lo cual vence el último día de febrero (28 de febrero de 2026, sábado).
    Domingo 1 de marzo: inhábil.
    Se extiende al primer día hábil siguiente: lunes 2 de marzo de 2026.
    """
    res = calcular_plazo(
        fecha_inicio="2026-01-31",
        unidad="meses",
        cantidad=1,
    )
    assert res["fecha_vencimiento"] == "2026-03-02"
    assert res["dia_semana_vencimiento"] == "Lunes"


def test_computo_anios_caducidad_reparacion_directa():
    """Caducidad de 2 años de reparación directa (art. 164 numeral 2 lit. i CPACA).

    Hecho: 21 de octubre de 2026 (miércoles).
    2 años calendario: 21 de octubre de 2028 (sábado inhábil).
    Domingo 22 de octubre de 2028: inhábil.
    Primer día hábil siguiente: lunes 23 de octubre de 2028.
    """
    res = calcular_plazo(
        fecha_inicio="2026-10-21",
        unidad="anios",
        cantidad=2,
        tipo_termino="caducidad_reparacion_directa",
    )
    assert res["fecha_vencimiento"] == "2028-10-23"
    assert res["dia_semana_vencimiento"] == "Lunes"


# -----------------------------------------------------------------------------
# 6. NOTIFICACIÓN POR MENSAJE DE DATOS (LEY 2213 DE 2022, ART. 8)
# -----------------------------------------------------------------------------
def test_notificacion_mensaje_datos_sin_acuse():
    """Envío de mensaje de datos sin acuse de recibo: 2 días hábiles de gracia.

    Envío: miércoles 14 de octubre de 2026.
    Día 1 de gracia hábil: jueves 15 de octubre.
    Día 2 de gracia hábil: viernes 16 de octubre -> notificación surtida.
    Inicio del cómputo de términos: lunes 19 de octubre de 2026.
    Término de 3 días hábiles:
      Día 1: lunes 19 oct
      Día 2: martes 20 oct
      Día 3: miércoles 21 oct (Vencimiento).
    """
    res = calcular_plazo(
        fecha_inicio="2026-10-14",
        unidad="dias_habiles",
        cantidad=3,
        notificacion_mensaje_datos=True,
    )
    assert res["fecha_notificacion"] == "2026-10-16"
    assert res["fecha_inicio_computo"] == "2026-10-19"
    assert res["fecha_vencimiento"] == "2026-10-21"


def test_notificacion_mensaje_datos_con_acuse_recibo():
    """Envío de mensaje de datos donde el destinatario emite acuse de recibo.

    Envío: lunes 19 de octubre de 2026.
    Acuse de recibo: martes 20 de octubre de 2026.
    El término corre al día hábil siguiente al acuse: miércoles 21 de octubre de 2026.
    Término de 3 días:
      Día 1: miércoles 21 oct
      Día 2: jueves 22 oct
      Día 3: viernes 23 oct (Vencimiento).
    """
    res = calcular_plazo(
        fecha_inicio="2026-10-19",
        unidad="dias_habiles",
        cantidad=3,
        notificacion_mensaje_datos=True,
        fecha_acuse_recibo="2026-10-20",
    )
    assert res["fecha_notificacion"] == "2026-10-20"
    assert res["fecha_inicio_computo"] == "2026-10-21"
    assert res["fecha_vencimiento"] == "2026-10-23"


# -----------------------------------------------------------------------------
# 7. ESTADO DE VENCIMIENTO Y DÍAS RESTANTES (TEXTO AMIGABLE)
# -----------------------------------------------------------------------------
def test_estado_vencido_vs_vigente():
    """Comprueba el reporte de días restantes o alerta roja si ya venció."""
    # Caso 1: Término futuro vigente
    res_vigente = calcular_plazo(
        fecha_inicio="2026-10-21",
        unidad="dias_habiles",
        cantidad=10,
        fecha_referencia_hoy=datetime.date(2026, 10, 21),
    )
    assert res_vigente["ha_vencido"] is False
    assert res_vigente["dias_habiles_restantes"] == 10
    assert "Vence el" in res_vigente["texto_resumen"]
    assert "quedan 10 días hábiles" in res_vigente["texto_resumen"]

    # Caso 2: Término ya vencido en el pasado
    res_vencido = calcular_plazo(
        fecha_inicio="2026-09-01",
        unidad="dias_habiles",
        cantidad=3,
        fecha_referencia_hoy=datetime.date(2026, 10, 21),
    )
    assert res_vencido["ha_vencido"] is True
    assert res_vencido["dias_habiles_restantes"] < 0
    assert res_vencido["estado_vencimiento"] == "vencido"
    assert "Venció el" in res_vencido["texto_resumen"]


# -----------------------------------------------------------------------------
# 8. GENERADOR DE EVENTOS .ICS (RFC 5545)
# -----------------------------------------------------------------------------
def test_generador_evento_ics_valido():
    """Verifica que el contenido del archivo .ics cumpla el estándar RFC 5545."""
    ics = generar_evento_ics(
        titulo="Vencimiento contestación demanda verbal",
        fecha_vencimiento=datetime.date(2026, 11, 20),
        descripcion="Radicar memorial ante el Juzgado 15 Civil Municipal",
        hora_vencimiento="17:00",
    )
    assert "BEGIN:VCALENDAR" in ics
    assert "VERSION:2.0" in ics
    assert "BEGIN:VEVENT" in ics
    assert "SUMMARY:Vencimiento contestación demanda verbal" in ics
    assert "DTSTART:20261120T170000" in ics
    assert "BEGIN:VALARM" in ics
    assert "END:VEVENT" in ics
    assert "END:VCALENDAR" in ics


# -----------------------------------------------------------------------------
# 9. INTEGRACIÓN HTTP ENDPOINTS
# -----------------------------------------------------------------------------
def test_endpoint_plazos_catalogo():
    """Verifica que GET /api/plazos/catalogo retorne las precargas completas."""
    resp = client.get("/api/plazos/catalogo")
    assert resp.status_code == 200
    data = resp.json()
    assert "precargas_terminos" in data
    ids = [p["id"] for p in data["precargas_terminos"]]
    assert "impugnacion_tutela" in ids
    assert "recursos_autos" in ids
    assert "recursos_admin" in ids
    assert "contestacion_verbal" in ids
    assert "contestacion_verbal_sumario" in ids
    assert "contestacion_cpaca" in ids
    assert "caducidad_nulidad_restablecimiento" in ids
    assert "caducidad_reparacion_directa" in ids
    assert "caducidad_querella" in ids


def test_endpoint_post_plazos():
    """Verifica que POST /api/plazos responda con el cálculo completo y evento .ics."""
    payload = {
        "tipo_termino": "contestacion_verbal",
        "fecha_inicio": "2026-10-21",
        "unidad": "dias_habiles",
        "cantidad": 20,
        "vacancia_colectiva": True,
        "notificacion_mensaje_datos": True,
    }
    resp = client.post("/api/plazos", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "fecha_vencimiento" in data
    assert "texto_resumen" in data
    assert "evento_ics" in data
    assert "BEGIN:VCALENDAR" in data["evento_ics"]


def test_endpoint_post_plazos_con_preset_sin_cantidad():
    """Verifica que POST /api/plazos funcione enviando solo tipo_termino y fecha_inicio."""
    payload = {
        "tipo_termino": "contestacion_verbal",
        "fecha_inicio": "2026-10-21",
    }
    resp = client.post("/api/plazos", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["cantidad"] == 20
    assert data["unidad"] == "dias_habiles"
    assert "Art. 369" in data["norma"]


def test_endpoint_post_plazos_ics_download():
    """Verifica que POST /api/plazos/ics retorne el archivo .ics con cabeceras de descarga."""
    payload = {
        "tipo_termino": "impugnacion_tutela",
        "fecha_inicio": "2026-10-21",
        "unidad": "dias_habiles",
        "cantidad": 3,
        "vacancia_colectiva": False,
    }
    resp = client.post("/api/plazos/ics", json=payload)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/calendar")
    assert "attachment" in resp.headers["content-disposition"]
    assert "BEGIN:VCALENDAR" in resp.text
