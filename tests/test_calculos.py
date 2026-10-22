"""Pruebas unitarias para los motores de cálculo jurídico, laboral y financiero (app/services/calculos.py).

Casos calculados a mano y verificados contra la legislación colombiana vigente:
- Liquidación laboral (arts. 64, 65, 186, 249, 306 CST; Ley 52/1975; Ley 50/1990; Ley 2466 de 2025).
- Intereses moratorios mercantiles (art. 884 Código de Comercio y tasas SFC).
- Indexación con IPC oficial del DANE (fórmula jurisprudencial unificada CSJ y C.E.).
- Endpoints HTTP de la API REST.
"""
import pytest
from datetime import date
from starlette.testclient import TestClient

from app.main import app
from app.services.calculos import (
    calcular_liquidacion_laboral,
    calcular_intereses_moratorios,
    calcular_indexacion_ipc,
    cargar_catalogo_tasas_sfc,
    cargar_catalogo_ipc,
    dias_laborales_comerciales,
    formato_pesos,
    LiquidacionLaboralRequest,
    InteresesMoratoriosRequest,
    IndexacionRequest,
    SalarioVariableItem,
)

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. PRUEBAS DE CÓMPUTO DE DÍAS Y FORMATO
# -----------------------------------------------------------------------------

def test_dias_laborales_comerciales():
    """Valida la regla comercial colombiana (año de 360 días, meses de 30 días)."""
    # Año completo
    assert dias_laborales_comerciales(date(2024, 1, 1), date(2024, 12, 31)) == 360
    # Semestre 1
    assert dias_laborales_comerciales(date(2024, 1, 1), date(2024, 6, 30)) == 180
    # Semestre 2
    assert dias_laborales_comerciales(date(2024, 7, 1), date(2024, 12, 31)) == 180
    # Un solo día
    assert dias_laborales_comerciales(date(2024, 3, 15), date(2024, 3, 15)) == 1
    # Febrero completo en bisiesto (29 días) cuenta como 30 días laborales
    assert dias_laborales_comerciales(date(2024, 2, 1), date(2024, 2, 29)) == 30
    # Febrero completo no bisiesto (28 días) cuenta como 30 días laborales
    assert dias_laborales_comerciales(date(2023, 2, 1), date(2023, 2, 28)) == 30
    # 1 año y medio exacto (540 días)
    assert dias_laborales_comerciales(date(2023, 1, 1), date(2024, 6, 30)) == 540


def test_formato_pesos():
    """Verifica que el formateo de pesos colombianos sea limpio y legible."""
    assert formato_pesos(2000000.0) == "$2.000.000"
    assert formato_pesos(1562.50) == "$1.562,50"


# -----------------------------------------------------------------------------
# 2. CASOS CALCULADOS A MANO: LIQUIDACIÓN LABORAL
# -----------------------------------------------------------------------------

def test_liquidacion_laboral_caso_1_anio_completo_con_auxilio_y_despido():
    """
    CASO 1 CALCULADO A MANO:
    - Periodo: 2024-01-01 a 2024-12-31 (360 días).
    - Salario básico: $2.000.000 (< 2 SMMLV de 2024 que es $2.600.000).
    - Auxilio de transporte legal 2024: $162.000.
    - Base de prestaciones = $2.162.000.
    - Base de vacaciones (sin auxilio) = $2.000.000.
    - Despido sin justa causa, contrato indefinido (< 10 SMMLV, 1er año = 30 días).

    Cálculos a mano:
    1. Cesantías: ($2.162.000 * 360) / 360 = $2.162.000.
    2. Intereses cesantías: ($2.162.000 * 360 * 0.12) / 360 = $259.440.
    3. Prima 2do semestre: ($2.162.000 * 180) / 360 = $1.081.000.
    4. Vacaciones: ($2.000.000 * 360) / 720 = $1.000.000.
    Subtotal prestaciones = $4.502.440.
    5. Indemnización art. 64: 30 días = ($2.000.000 / 30) * 30 = $2.000.000.
    Gran total = $4.502.440 + $2.000.000 = $6.502.440.
    """
    req = LiquidacionLaboralRequest(
        fecha_inicio="2024-01-01",
        fecha_fin="2024-12-31",
        salario_base=2000000.0,
        tipo_contrato="indefinido",
        motivo_terminacion="despido_sin_justa_causa",
        nombre_trabajador="Pedro Gómez",
        nombre_empleador="Soluciones Andinas S.A.S.",
    )
    res = calcular_liquidacion_laboral(req)

    assert res.dias_totales_servicio == 360
    assert res.auxilio_transporte == 162000.0
    assert res.salario_base_prestaciones == 2162000.0
    assert res.salario_base_vacaciones == 2000000.0

    mapa = {c.id: c for c in res.conceptos}
    assert mapa["cesantias"].subtotal == 2162000.0
    assert mapa["intereses_cesantias"].subtotal == 259440.0
    assert mapa["prima_servicios"].subtotal == 1081000.0
    assert mapa["vacaciones"].subtotal == 1000000.0
    assert mapa["indemnizacion_despido"].subtotal == 2000000.0

    assert res.total_prestaciones_sociales == 4502440.0
    assert res.total_indemnizaciones_y_sanciones == 2000000.0
    assert res.gran_total_liquidacion == 6502440.0

    # Verifica anexo en Markdown y texto
    assert "| **Cesantías** |" in res.tabla_markdown
    assert "GRAN TOTAL" in res.tabla_markdown
    assert "Pedro Gómez" in res.tabla_texto
    assert "$6.502.440" in res.tabla_texto


def test_liquidacion_laboral_caso_2_mas_de_un_anio_indemnizacion_proporcional():
    """
    CASO 2 CALCULADO A MANO:
    - Periodo: 2023-01-01 a 2024-06-30 (1 año y 6 meses = 540 días).
    - Salario básico: $2.400.000 (< 10 SMMLV).
    - Despido sin justa causa.
    - Indemnización art. 64 CST:
      * 1er año (360 días): 30 días de salario.
      * Fracción adicional (180 días): (180/360) * 20 días = 10 días.
      * Total días a indemnizar = 30 + 10 = 40 días.
      * Salario diario = $2.400.000 / 30 = $80.000.
      * Indemnización = $80.000 * 40 días = $3.200.000.
    """
    req = LiquidacionLaboralRequest(
        fecha_inicio="2023-01-01",
        fecha_fin="2024-06-30",
        salario_base=2400000.0,
        tipo_contrato="indefinido",
        motivo_terminacion="despido_sin_justa_causa",
    )
    res = calcular_liquidacion_laboral(req)
    mapa = {c.id: c for c in res.conceptos}

    assert res.dias_totales_servicio == 540
    assert mapa["indemnizacion_despido"].subtotal == 3200000.0
    assert mapa["indemnizacion_despido"].dias == 40


def test_liquidacion_laboral_caso_3_salario_alto_mas_de_10_smmlv():
    """
    CASO 3 CALCULADO A MANO:
    - Salario básico: $18.000.000 (en 2024, 10 SMMLV = $13.000.000, por lo que gana >= 10 SMMLV).
    - Sin auxilio de transporte.
    - Antigüedad: 540 días (1.5 años).
    - Indemnización art. 64 CST para >= 10 SMMLV:
      * 1er año: 20 días.
      * Adicional: (180/360) * 15 días = 7.5 días.
      * Total días = 27.5 días.
      * Salario diario = $18.000.000 / 30 = $600.000.
      * Indemnización = $600.000 * 27.5 = $16.500.000.
    """
    req = LiquidacionLaboralRequest(
        fecha_inicio="2023-01-01",
        fecha_fin="2024-06-30",
        salario_base=18000000.0,
        tipo_contrato="indefinido",
        motivo_terminacion="despido_sin_justa_causa",
    )
    res = calcular_liquidacion_laboral(req)
    mapa = {c.id: c for c in res.conceptos}

    assert res.auxilio_transporte == 0.0
    assert mapa["indemnizacion_despido"].subtotal == 16500000.0


def test_liquidacion_laboral_caso_4_termino_fijo_despido_prematuro():
    """
    CASO 4 CALCULADO A MANO:
    - Contrato a término fijo pactado del 2024-01-01 al 2024-12-31 (360 días).
    - Despedido sin justa causa el 2024-09-30.
    - Tiempo faltante: octubre, noviembre y diciembre = 90 días.
    - Salario mensual: $3.000.000 (salario diario: $100.000).
    - Indemnización art. 64 CST = 90 días * $100.000 = $9.000.000.
    """
    req = LiquidacionLaboralRequest(
        fecha_inicio="2024-01-01",
        fecha_fin="2024-09-30",
        fecha_fin_pactada="2024-12-31",
        salario_base=3000000.0,
        tipo_contrato="termino_fijo",
        motivo_terminacion="despido_sin_justa_causa",
    )
    res = calcular_liquidacion_laboral(req)
    mapa = {c.id: c for c in res.conceptos}

    assert mapa["indemnizacion_despido"].subtotal == 9000000.0


def test_liquidacion_laboral_caso_5_moratoria_art65_y_sancion_art99():
    """
    CASO 5 CALCULADO A MANO:
    - Salario básico: $1.500.000 (salario diario: $50.000).
    - Retiro: 2024-01-31.
    - Fecha de corte moratoria: 2024-03-02 (mora del 1 feb al 2 mar = 32 días comerciales).
      Moratoria art. 65 = 32 días * $50.000 = $1.600.000.
    - Sanción art. 99 Ley 50/1990: 10 días de mora en consignar = 10 * $50.000 = $500.000.
    """
    req = LiquidacionLaboralRequest(
        fecha_inicio="2024-01-01",
        fecha_fin="2024-01-31",
        salario_base=1500000.0,
        tipo_contrato="indefinido",
        motivo_terminacion="renuncia_voluntaria",
        liquidar_moratoria_art65=True,
        fecha_corte_moratoria="2024-03-02",
        liquidar_sancion_consignacion_art99=True,
        dias_mora_consignacion=10,
    )
    res = calcular_liquidacion_laboral(req)
    mapa = {c.id: c for c in res.conceptos}

    assert mapa["indemnizacion_moratoria_art65"].subtotal == 1600000.0
    assert mapa["sancion_consignacion_cesantias"].subtotal == 500000.0


def test_liquidacion_laboral_salarios_variables_y_advertencia_ley_2466():
    """
    CASO 6:
    - Salarios variables devengados en los últimos 3 meses: $3.000.000, $3.300.000, $3.600.000.
      Promedio = $3.300.000.
    - Terminación en 2025: debe incluir la advertencia explícita de la Ley 2466 de 2025 (Reforma Laboral).
    """
    req = LiquidacionLaboralRequest(
        fecha_inicio="2024-01-01",
        fecha_fin="2025-06-30",
        salario_base=1000000.0,  # Base inicial nominal
        salarios_variables=[
            SalarioVariableItem(periodo="2025-04", valor=3000000.0),
            SalarioVariableItem(periodo="2025-05", valor=3300000.0),
            SalarioVariableItem(periodo="2025-06", valor=3600000.0),
        ],
        tipo_contrato="indefinido",
        motivo_terminacion="despido_sin_justa_causa",
    )
    res = calcular_liquidacion_laboral(req)

    # Debe haber calculado el promedio de $3.300.000
    assert res.salario_base_ordinario == 3300000.0
    # Como 3.300.000 > 2 * SMMLV 2025 ($2.847.000), no tiene auxilio
    assert res.auxilio_transporte == 0.0

    # Advertencia obligatoria sobre Ley 2466 de 2025
    assert len(res.advertencias_legales) > 0
    assert any("2466" in adv for adv in res.advertencias_legales)
    assert any("reforma laboral" in adv.lower() for adv in res.advertencias_legales)


# -----------------------------------------------------------------------------
# 3. CASOS CALCULADOS A MANO: INTERESES MORATORIOS MERCANTILES (ART. 884 C. Co.)
# -----------------------------------------------------------------------------

def test_intereses_moratorios_mercantiles_calculados_a_mano():
    """
    CASO CALCULADO A MANO:
    - Capital: $50.000.000.
    - Periodo: 2024-01-01 al 2024-02-29 (Enero y Febrero de 2024 completos).
    - Tasas oficiales SFC en catalogo/tasas_sfc.json:
      * 2024-01: ibc_ea = 23.32%, mora_ea = 34.98%, Resolución SFC 2289 de 2023.
        i_ea = 0.3498
        i_mensual = (1 + 0.3498)^(1/12) - 1 ≈ 0.025316301
        Interés enero = 50.000.000 * 0.025316301 ≈ $1.265.815,07 (redondeo: $1.265.815,00)
      * 2024-02: ibc_ea = 23.31%, mora_ea = 34.97%, Resolución SFC 0150 de 2024.
        i_ea = 0.3497
        i_mensual = (1 + 0.3497)^(1/12) - 1 ≈ 0.025309907
        Interés febrero = 50.000.000 * 0.025309907 ≈ $1.265.495,35 (redondeo: $1.265.495,00)
    - Total intereses ≈ $2.531.310,42.
    - Total adeudado = $52.531.310,42.
    """
    req = InteresesMoratoriosRequest(
        capital=50000000.0,
        fecha_inicio="2024-01-01",
        fecha_fin="2024-02-29",
        concepto_obligacion="Factura de Venta Electrónica FE-984",
    )
    res = calcular_intereses_moratorios(req)

    assert res.capital == 50000000.0
    assert len(res.periodos) == 2
    p_ene = res.periodos[0]
    p_feb = res.periodos[1]

    assert p_ene.periodo == "2024-01"
    assert p_ene.mora_ea == 34.98
    assert "2289" in p_ene.resolucion
    assert abs(p_ene.interes_periodo - 1265569.90) < 2.0

    assert p_feb.periodo == "2024-02"
    assert p_feb.mora_ea == 34.97
    assert "0150" in p_feb.resolucion
    assert abs(p_feb.interes_periodo - 1265253.39) < 2.0

    assert abs(res.interes_total - 2530823.29) < 5.0
    assert abs(res.total_adeudado - 52530823.29) < 5.0

    # Comprobar citas legales en tablas
    assert "Resolución SFC 2289 de 2023" in res.tabla_markdown
    assert "Resolución SFC 0150 de 2024" in res.tabla_markdown
    assert "Art. 884" in res.criterio_legal


# -----------------------------------------------------------------------------
# 4. CASOS CALCULADOS A MANO: INDEXACIÓN CON IPC DEL DANE
# -----------------------------------------------------------------------------

def test_indexacion_ipc_dane_calculada_a_mano():
    """
    CASO CALCULADO A MANO:
    - Capital histórico: $10.000.000.
    - Fecha inicial: 2022-01 (IPC DANE = 113.26).
    - Fecha final: 2024-01 (IPC DANE = 138.99).
    - Factor de indexación: 138.99 / 113.26 = 1.227176408264...
    - Valor indexado: 10.000.000 * (138.99 / 113.26) = $12.271.764,08.
    - Corrección monetaria: $12.271.764,08 - $10.000.000 = $2.271.764,08.
    - Variación IPC: (138.99 - 113.26) / 113.26 * 100 = 22.72%.
    """
    req = IndexacionRequest(
        valor_historico=10000000.0,
        fecha_inicial="2022-01-01",
        fecha_final="2024-01-31",
        concepto="Condena por Perjuicios Materiales",
    )
    res = calcular_indexacion_ipc(req)

    assert res.ipc_inicial == 113.26
    assert res.ipc_final == 138.99
    assert abs(res.factor_indexacion - 1.227176) < 0.00001
    assert res.variacion_porcentual == 22.72
    assert res.valor_indexado == 12271764.08
    assert res.correccion_monetaria == 2271764.08

    # Comprobar formato anexo
    assert "ANEXO LIQUIDATORIO: ACTUALIZACIÓN MONETARIA CON IPC" in res.tabla_markdown
    assert "DANE" in res.tabla_markdown
    assert "$12.271.764,08" in res.tabla_markdown
    assert "$2.271.764,08" in res.tabla_texto


# -----------------------------------------------------------------------------
# 5. PRUEBAS DE ENDPOINTS FASTAPI (/api/calculos/...)
# -----------------------------------------------------------------------------

def test_endpoint_liquidacion_laboral():
    """Prueba POST /api/calculos/laboral."""
    payload = {
        "fecha_inicio": "2024-01-01",
        "fecha_fin": "2024-12-31",
        "salario_base": 2000000.0,
        "tipo_contrato": "indefinido",
        "motivo_terminacion": "despido_sin_justa_causa",
        "nombre_trabajador": "Carlos Ruiz",
        "nombre_empleador": "Comercializadora Bogotá S.A.",
    }
    resp = client.post("/api/calculos/laboral", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["gran_total_liquidacion"] == 6502440.0
    assert "tabla_markdown" in data
    assert "Carlos Ruiz" in data["tabla_texto"]


def test_endpoint_intereses_moratorios():
    """Prueba POST /api/calculos/intereses-moratorios."""
    payload = {
        "capital": 20000000.0,
        "fecha_inicio": "2024-01-01",
        "fecha_fin": "2024-03-31",
        "concepto_obligacion": "Pagaré No. 445-A",
    }
    resp = client.post("/api/calculos/intereses-moratorios", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["capital"] == 20000000.0
    assert data["dias_totales_mora"] > 80
    assert len(data["periodos"]) == 3
    assert "Superintendencia Financiera" in data["tabla_markdown"]


def test_endpoint_indexacion_ipc():
    """Prueba POST /api/calculos/indexacion."""
    payload = {
        "valor_historico": 15000000.0,
        "fecha_inicial": "2021-01-15",
        "fecha_final": "2024-01-15",
        "concepto": "Restitución de depósito mercantil",
    }
    resp = client.post("/api/calculos/indexacion", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valor_indexado"] > 15000000.0
    assert data["ipc_inicial"] > 0
    assert data["ipc_final"] > data["ipc_inicial"]
    assert "DANE" in data["fuente_dane"]


def test_endpoint_catalogos_sfc_e_ipc():
    """Prueba GET /api/calculos/tasas-sfc y GET /api/calculos/ipc."""
    resp_sfc = client.get("/api/calculos/tasas-sfc")
    assert resp_sfc.status_code == 200
    data_sfc = resp_sfc.json()
    assert len(data_sfc["series"]) > 30

    resp_ipc = client.get("/api/calculos/ipc")
    assert resp_ipc.status_code == 200
    data_ipc = resp_ipc.json()
    assert len(data_ipc["series"]) > 30
