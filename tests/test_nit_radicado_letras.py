import json
import subprocess
import shutil
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.nit import calcular_dv_nit, validar_nit, formatear_nit
from app.services.radicado import (
    obtener_catalogo_radicado,
    validar_radicado,
    formatear_radicado,
    decodificar_radicado,
)
from app.services.numeros_letras import numero_a_letras
from app.services.prompt import listar_tipos, obtener_tipo, valor_legible

AUDITOR_JS_PATH = Path(__file__).resolve().parent.parent / "app" / "private" / "auditor.js"


def ejecutar_js(codigo_js: str) -> dict:
    """Evalúa los mismos cálculos JS en Node en Windows, macOS o Linux."""
    node = shutil.which("node") or os.environ.get("CODEX_PRIMARY_RUNTIME_NODE")
    if not node:
        pytest.skip("Node.js es necesario para comparar el auditor de navegador.")
    script = f"""
    const auditor = require({json.dumps(str(AUDITOR_JS_PATH))});
    const resultado = require('node:vm').runInNewContext({json.dumps(codigo_js)}, {{...auditor}});
    process.stdout.write(String(resultado));
    """
    res = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
    salida = res.stdout.strip()
    return json.loads(salida) if salida else {}


# ============================================================================
# 1. PRUEBAS PARA NIT (ALGORITMO DIAN)
# ============================================================================

def test_nit_algoritmo_dian_empresas_reales():
    """Prueba el cálculo de DV en NITs de empresas colombianas reales."""
    # Ecopetrol S.A.: 899.999.068-1
    assert calcular_dv_nit("899.999.068") == 1
    assert calcular_dv_nit("899999068") == 1

    # Bancolombia S.A.: 890.903.938-8
    assert calcular_dv_nit("890.903.938") == 8

    # Almacenes Éxito S.A.: 890.900.608-9
    assert calcular_dv_nit("890.900.608") == 9

    # Grupo Aval Acciones y Valores: 800.216.181-5
    assert calcular_dv_nit("800.216.181") == 5


def test_nit_algoritmo_dian_casos_residuo_cero_y_uno():
    """Valida la regla especial de la DIAN donde residuo 0 da DV 0 y residuo 1 da DV 1."""
    # 900000009 genera suma 396 (36 * 11, residuo 0) -> DV 0
    assert calcular_dv_nit("900000009") == 0

    # 900000002 genera suma 375 (34 * 11 + 1, residuo 1) -> DV 1
    assert calcular_dv_nit("900000002") == 1


def test_nit_validacion_con_dv_correcto_e_incorrecto():
    """Valida que validar_nit detecte discrepancias y devuelva advertencias claras."""
    # Con DV erróneo (para 900.123.456 el DV real es 8, se pasa 7)
    val_err = validar_nit("900.123.456-7")
    assert val_err["valido"] is False
    assert val_err["dv_ingresado"] == 7
    assert val_err["dv_calculado"] == 8
    assert "no coincide" in val_err["mensaje"]

    # Con DV correcto
    val_ok = validar_nit("900.123.456-8")
    assert val_ok["valido"] is True
    assert val_ok["dv_ingresado"] == 8
    assert val_ok["dv_calculado"] == 8

    # Formateo
    assert formatear_nit("900123456", incluir_dv=True) == "900.123.456-8"


def test_nit_javascript_auditor():
    """Verifica la paridad de la implementación JavaScript en auditor.js."""
    js = """
    const dvEcopetrol = calcularDvNit("899999068");
    const valErr = validarNit("900.123.456-7");
    const valOk = validarNit("900.123.456-8");
    const fmt = formatearNit("890903938");
    JSON.stringify({ dvEcopetrol, valErr, valOk, fmt });
    """
    res = ejecutar_js(js)
    assert res["dvEcopetrol"] == 1
    assert res["valErr"]["valido"] is False
    assert res["valErr"]["dvCalculado"] == 8
    assert res["valOk"]["valido"] is True
    assert res["fmt"] == "890.903.938-8"


# ============================================================================
# 2. PRUEBAS PARA RADICADO (23 DÍGITOS: 5-2-2-3-4-5-2)
# ============================================================================

def test_radicado_longitud_23_digitos():
    """Exige exactamente 23 dígitos numéricos."""
    valido, _ = validar_radicado("11001-40-03-012-2026-00345-00")
    assert valido is True

    # 21 dígitos (incompleto)
    val_incompleto, msg = validar_radicado("11001-40-03-012-2026-00345")
    assert val_incompleto is False
    assert "21" in msg

    # Vacío
    val_vacio, msg_v = validar_radicado("")
    assert val_vacio is False


def test_radicado_formato_5_2_2_3_4_5_2():
    """Formatea 23 dígitos en bloques 5-2-2-3-4-5-2."""
    entrada = "11001400301220260034500"
    esperado = "11001-40-03-012-2026-00345-00"
    assert formatear_radicado(entrada) == esperado


def test_radicado_decodificacion_dane_ano_consecutivo():
    """Decodifica municipio DANE, corporación, especialidad, año y consecutivo."""
    rad = "11001-40-03-012-2026-00345-00"
    dec = decodificar_radicado(rad)
    assert dec["valido"] is True
    assert dec["municipio_codigo"] == "11001"
    assert "Bogotá" in dec["municipio_nombre"]
    assert dec["entidad_codigo"] == "40"
    assert "Municipal" in dec["entidad_nombre"]
    assert dec["especialidad_codigo"] == "03"
    assert dec["especialidad_nombre"] == "Civil"
    assert dec["despacho_numero"] == "012"
    assert dec["ano"] == 2026
    assert dec["consecutivo"] == "00345"
    assert dec["consecutivo_numero"] == 345

    # Medellín (05001), Cali (76001), Barranquilla (08001)
    dec_med = decodificar_radicado("05001-31-04-001-2025-00100-00")
    assert "Medellín" in dec_med["municipio_nombre"]
    assert dec_med["ano"] == 2025

    dec_cali = decodificar_radicado("76001-22-01-005-2024-00050-01")
    assert "Cali" in dec_cali["municipio_nombre"]
    assert dec_cali["especialidad_nombre"] == "Penal"


def test_radicado_catalogo_json():
    """Verifica que app/catalogo/radicado.json exista y contenga entidades y especialidades CSJ."""
    cat = obtener_catalogo_radicado()
    assert "entidades" in cat
    assert "especialidades" in cat
    assert "municipios_dane" in cat
    assert "40" in cat["entidades"]
    assert "03" in cat["especialidades"]
    assert "11001" in cat["municipios_dane"]


def test_radicado_javascript_auditor():
    """Verifica la decodificación de radicado en auditor.js."""
    js = """
    const dec = decodificarRadicado("11001-40-03-012-2026-00345-00");
    const fmt = formatearRadicado("11001400301220260034500");
    const valErr = validarRadicado("1100140030122026");
    JSON.stringify({ dec, fmt, valErr });
    """
    res = ejecutar_js(js)
    assert res["dec"]["valido"] is True
    assert "Bogotá" in res["dec"]["municipioNombre"]
    assert res["dec"]["ano"] == 2026
    assert res["dec"]["consecutivo"] == "00345"
    assert res["fmt"] == "11001-40-03-012-2026-00345-00"
    assert res["valErr"]["valido"] is False


# ============================================================================
# 3. PRUEBAS PARA NUMERO A LETRAS (PESOS COLOMBIANOS, "M/CTE")
# ============================================================================

def test_numero_a_letras_determinista_pesos_mcte():
    """Verifica la conversión exacta según la práctica legal colombiana."""
    casos = [
        (0, "CERO PESOS M/CTE."),
        (1, "UN PESO M/CTE."),
        (21, "VEINTIÚN PESOS M/CTE."),
        (100, "CIEN PESOS M/CTE."),
        (101, "CIENTO UN PESOS M/CTE."),
        (1000, "UN MIL PESOS M/CTE."),
        (1001, "UN MIL UN PESOS M/CTE."),
        (1000000, "UN MILLÓN DE PESOS M/CTE."),
        (2000000, "DOS MILLONES DE PESOS M/CTE."),
        (80000000, "OCHENTA MILLONES DE PESOS M/CTE."),
        (80000500, "OCHENTA MILLONES QUINIENTOS PESOS M/CTE."),
        (1000000000, "UN MIL MILLONES DE PESOS M/CTE."),
        ("80.000.000", "OCHENTA MILLONES DE PESOS M/CTE."),
        ("$ 80.000.000", "OCHENTA MILLONES DE PESOS M/CTE."),
        ("80.000.000,50", "OCHENTA MILLONES DE PESOS CON 50/100 M/CTE."),
    ]
    for valor, esperado in casos:
        assert numero_a_letras(valor) == esperado, f"Fallo en {valor}: esperado '{esperado}'"


def test_numero_a_letras_javascript():
    """Verifica la equivalencia exacta de numeroALetras() en auditor.js."""
    js = """
    const c0 = numeroALetras(0);
    const c1 = numeroALetras(1);
    const c21 = numeroALetras(21);
    const c100 = numeroALetras(100);
    const c101 = numeroALetras(101);
    const c1000 = numeroALetras(1000);
    const c1M = numeroALetras(1000000);
    const c80M = numeroALetras(80000000);
    const c80M500 = numeroALetras(80000500);
    const cStr = numeroALetras("$ 80.000.000");
    const cCent = numeroALetras("80.000.000,50");
    JSON.stringify({ c0, c1, c21, c100, c101, c1000, c1M, c80M, c80M500, cStr, cCent });
    """
    res = ejecutar_js(js)
    assert res["c0"] == "CERO PESOS M/CTE."
    assert res["c1"] == "UN PESO M/CTE."
    assert res["c21"] == "VEINTIÚN PESOS M/CTE."
    assert res["c100"] == "CIEN PESOS M/CTE."
    assert res["c101"] == "CIENTO UN PESOS M/CTE."
    assert res["c1000"] == "UN MIL PESOS M/CTE."
    assert res["c1M"] == "UN MILLÓN DE PESOS M/CTE."
    assert res["c80M"] == "OCHENTA MILLONES DE PESOS M/CTE."
    assert res["c80M500"] == "OCHENTA MILLONES QUINIENTOS PESOS M/CTE."
    assert res["cStr"] == "OCHENTA MILLONES DE PESOS M/CTE."
    assert res["cCent"] == "OCHENTA MILLONES DE PESOS CON 50/100 M/CTE."


# ============================================================================
# 4. VERIFICACIÓN DE CONCORDANCIA CIFRA Y LETRAS EN EL ESCRITO
# ============================================================================

def test_verificacion_discrepancia_cifra_y_letras():
    """Verifica que el auditor detecte cuando una cifra numérica no coincide con su texto en letras."""
    # Escrito con error evidente: $80.000.000 pero en letras dice ocho millones de pesos
    texto_error = """
    PRETENSIONES:
    Condenar a la demandada a pagar la suma de $80.000.000 (ocho millones de pesos).
    """
    js_error = f"""
    const res = auditarDatosYEscrito({{"cuantia": "80000000"}}, {json.dumps(texto_error)}, {{}});
    JSON.stringify(res);
    """
    res = ejecutar_js(js_error)
    assert len(res["discrepanciasCifrasLetras"]) >= 1
    assert "Discrepancia" in res["discrepanciasCifrasLetras"][0]["detalle"]

    # Escrito correcto: $80.000.000 (ochenta millones de pesos)
    texto_correcto = """
    PRETENSIONES:
    Condenar a la demandada a pagar la suma de $80.000.000 (ochenta millones de pesos).
    """
    js_ok = f"""
    const res = auditarDatosYEscrito({{"cuantia": "80000000"}}, {json.dumps(texto_correcto)}, {{}});
    JSON.stringify(res);
    """
    res_ok = ejecutar_js(js_ok)
    assert len(res_ok["discrepanciasCifrasLetras"]) == 0


# ============================================================================
# 5. CAMPOS DE FECHA DE NOTIFICACIÓN A <input type="date"> Y FORMATO ISO
# ============================================================================

def test_campos_notificacion_fecha_son_date_en_catalogo():
    """Verifica que los tipos procesales que piden fecha de notificación tengan tipo 'date'."""
    tipos_con_fecha = ["contestacion", "recurso_admin", "nulidad_restablecimiento", "recurso_judicial", "impugnacion_tutela", "apelacion_sentencia"]
    for tid in tipos_con_fecha:
        tipo = obtener_tipo(tid)
        assert tipo is not None
        campo_notif = None
        for g in tipo.get("grupos", []):
            for c in g.get("campos", []):
                if c.get("k") == "notificacion_fecha":
                    campo_notif = c
                    break
        assert campo_notif is not None, f"Tipo {tid} no tiene el campo 'notificacion_fecha'"
        assert campo_notif.get("t") == "date", f"Tipo {tid} tiene campo 'notificacion_fecha' con t='{campo_notif.get('t')}' en vez de 'date'"


def test_formateo_iso_fecha_en_prompt():
    """Verifica que fechas en ISO como '2026-10-01' se formateen de manera legible en el prompt del servidor."""
    c = {"k": "notificacion_fecha", "t": "date", "l": "Fecha de notificación"}
    legible = valor_legible(c, "2026-10-01")
    assert "1 de octubre de 2026" in legible


# ============================================================================
# 6. ENDPOINTS HTTP DE LA API
# ============================================================================

def test_endpoints_api_nuevos():
    """Prueba los endpoints HTTP para validación de NIT, radicado y número a letras."""
    with TestClient(app, headers={"Authorization": "Bearer unit-test-bearer"}) as client:
        # 1. /api/catalogo incluye radicado
        r_cat = client.get("/api/catalogo")
        assert r_cat.status_code == 200
        data_cat = r_cat.json()
        assert "radicado" in data_cat
        assert "entidades" in data_cat["radicado"]

        # 2. /api/radicado/decodificar
        r_rad = client.get("/api/radicado/decodificar", params={"radicado": "11001-40-03-012-2026-00345-00"})
        assert r_rad.status_code == 200
        data_rad = r_rad.json()
        assert data_rad["valido"] is True
        assert data_rad["ano"] == 2026
        assert "Bogotá" in data_rad["municipio_nombre"]

        # 3. /api/nit/validar
        r_nit = client.get("/api/nit/validar", params={"nit": "899.999.068-1"})
        assert r_nit.status_code == 200
        assert r_nit.json()["valido"] is True

        r_nit_err = client.get("/api/nit/validar", params={"nit": "900.123.456-7"})
        assert r_nit_err.status_code == 200
        assert r_nit_err.json()["valido"] is False

        # 4. /api/numero-a-letras
        r_nl = client.get("/api/numero-a-letras", params={"valor": "80000000"})
        assert r_nl.status_code == 200
        assert r_nl.json()["letras"] == "OCHENTA MILLONES DE PESOS M/CTE."

pytestmark = pytest.mark.usefixtures("autenticacion_pruebas")
