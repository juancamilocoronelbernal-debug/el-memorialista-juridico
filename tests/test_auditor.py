import json
import subprocess
import shutil
import os
from pathlib import Path
import pytest

AUDITOR_JS_PATH = Path(__file__).resolve().parent.parent / "app" / "private" / "auditor.js"


def auditar_js(datos: dict, texto: str, perfil: dict, fecha_hoy: str = "2026-10-21") -> dict:
    """Ejecuta la función auditarDatosYEscrito en JavaScript usando el Node.js."""
    assert AUDITOR_JS_PATH.exists(), f"No se encontró {AUDITOR_JS_PATH}"

    payload = {
        "datos": datos,
        "texto": texto,
        "perfil": perfil,
        "opciones": {"fechaHoy": fecha_hoy},
    }

    node = shutil.which("node") or os.environ.get("CODEX_PRIMARY_RUNTIME_NODE")
    if not node:
        pytest.skip("Node.js es necesario para comparar el auditor de navegador.")
    js_code = f"""
    const auditor = require({json.dumps(str(AUDITOR_JS_PATH))});
    const params = {json.dumps(payload, ensure_ascii=False)};
    const resultado = auditor.auditarDatosYEscrito(params.datos, params.texto, params.perfil, params.opciones);
    process.stdout.write(JSON.stringify(resultado));
    """
    res = subprocess.run([node, "-e", js_code], capture_output=True, text=True, check=True)
    return json.loads(res.stdout.strip())


def test_ejemplo_1_tutela_omisiones():
    """Ejemplo 1: Acción de tutela donde el escrito omite la cédula y el correo ingresados en el formulario."""
    datos = {
        "accionante": "María Fernanda López Rincón",
        "cedula": "1.020.304.050",
        "accionado": "Nueva EPS S.A.",
        "correo": "mfernanda.lopez@email.com",
        "hechos": "El 9 de septiembre de 2026 la EPS negó la autorización del medicamento.",
    }
    texto = """Bogotá D.C., 21 de octubre de 2026.
SEÑOR JUEZ CIVIL MUNICIPAL DE BOGOTÁ

**MARÍA FERNANDA LÓPEZ RINCÓN**, mayor de edad, formulo acción de tutela contra **NUEVA EPS S.A.**

HECHOS:
1. El 9 de septiembre de 2026 la EPS negó la autorización del medicamento recetado por mi médico tratante.

PRETENSIONES:
Tutelar mis derechos fundamentales a la salud y a la vida digna.

Atentamente,
Laura Mejía Restrepo
C.C. 52.123.456 de Bogotá
T.P. 123.456 del C.S. de la J.
laura@mejiaabogados.co
Tel: 310 000 0000"""

    perfil = {
        "abogado": {
            "nombre": "Laura Mejía Restrepo",
            "cedula": "52.123.456",
            "tp": "123.456",
            "correo": "laura@mejiaabogados.co",
            "telefono": "3100000000",
            "ciudad": "Bogotá D.C.",
        }
    }

    res = auditar_js(datos, texto, perfil, fecha_hoy="2026-10-21")

    # No debe haber invenciones (la fecha de hoy 21/10/2026 y los datos de Laura Mejía están excluidos)
    assert len(res["invenciones"]) == 0, f"Invenciones inesperadas: {res['invenciones']}"

    # Debe reportar omisión de la cédula y del correo
    omisiones = res["omisiones"]
    tipos_om = [o["tipo"] for o in omisiones]
    assert "cédula / NIT" in tipos_om
    assert "correo" in tipos_om

    ced_om = next(o for o in omisiones if o["tipo"] == "cédula / NIT")
    assert ced_om["normalizado"] == "1020304050"

    mail_om = next(o for o in omisiones if o["tipo"] == "correo")
    assert mail_om["normalizado"] == "mfernanda.lopez@email.com"

    assert res["total"] == 2


def test_ejemplo_2_demanda_verbal_invenciones():
    """Ejemplo 2: Demanda verbal donde el modelo inventa una fecha y una cuantía adicional."""
    datos = {
        "demandante": "CARLOS ANDRÉS RINCÓN MORALES",
        "demandado": "CLÍNICA SAN JOSÉ S.A.",
        "cuantia": "$80.000.000",
        "fecha_contrato": "15 de mayo de 2025",
    }
    texto = """SEÑOR JUEZ CIVIL DEL CIRCUITO DE BOGOTÁ

**CARLOS ANDRÉS RINCÓN MORALES**, demandante, promuevo demanda verbal contra **CLÍNICA SAN JOSÉ S.A.**

HECHOS:
1. El 15 de mayo de 2025 se suscribió el contrato de prestación de servicios.
2. Con fecha 20 de octubre de 2024 se realizaron procedimientos no autorizados.

PRETENSIONES:
1. Declarar contractualmente responsable a la demandada.
2. Condenar al pago de OCHENTA MILLONES DE PESOS ($80.000.000) por concepto de daño emergente.
3. Condenar además al pago de $120.000.000 por concepto de lucro cesante."""

    perfil = {"abogado": {}}

    res = auditar_js(datos, texto, perfil, fecha_hoy="2026-10-21")

    # Omisiones: 0 (todos los datos del formulario están en el texto)
    assert len(res["omisiones"]) == 0, f"Omisiones inesperadas: {res['omisiones']}"

    # Invenciones: 2 (el valor de $120.000.000 y la fecha del 20 de octubre de 2024)
    invenciones = res["invenciones"]
    tipos_inv = [i["tipo"] for i in invenciones]
    assert "valor" in tipos_inv
    assert "fecha" in tipos_inv

    val_inv = next(i for i in invenciones if i["tipo"] == "valor")
    assert val_inv["normalizado"] == "120000000"

    fec_inv = next(i for i in invenciones if i["tipo"] == "fecha")
    assert fec_inv["normalizado"] == "2024-10-20"

    assert res["total"] == 2


def test_ejemplo_3_derecho_peticion_totalmente_consistente():
    """Ejemplo 3: Derecho de petición donde todos los datos coinciden exactamente (0 discrepancias)."""
    datos = {
        "peticionario": "GLORIA ESPERANZA PATIÑO",
        "cedula": "52.345.678",
        "entidad": "SECRETARÍA DE MOVILIDAD DE BOGOTÁ",
        "telefono": "3105550101",
        "correo": "gloria.patino@correo.co",
        "fecha_comparendo": "14 de junio de 2026",
    }
    texto = """Bogotá D.C., 21 de octubre de 2026.
Señores
SECRETARÍA DE MOVILIDAD DE BOGOTÁ
Ciudad

Referencia: DERECHO DE PETICIÓN EN INTERÉS PARTICULAR

Yo, **GLORIA ESPERANZA PATIÑO**, identificada con C.C. 52.345.678, con número de contacto 310 555 0101 y correo gloria.patino@correo.co, formulo respetuosa solicitud respecto al comparendo del 14 de junio de 2026.

Cordialmente,
Laura Mejía Restrepo
C.C. 52.123.456
T.P. 123.456
laura@mejiaabogados.co
Tel: 3100000000"""

    perfil = {
        "abogado": {
            "nombre": "Laura Mejía Restrepo",
            "cedula": "52.123.456",
            "tp": "123.456",
            "correo": "laura@mejiaabogados.co",
            "telefono": "3100000000",
        }
    }

    res = auditar_js(datos, texto, perfil, fecha_hoy="2026-10-21")

    assert len(res["invenciones"]) == 0
    assert len(res["omisiones"]) == 0
    assert res["total"] == 0


def test_ejemplo_4_demanda_ejecutiva_radicado_23_digitos_y_cuantia_en_letras():
    """Ejemplo 4: Demanda ejecutiva con radicado de 23 dígitos normalizado y cuantía en letras coincidentes, con cédula inventada."""
    datos = {
        "radicado": "11001-31-03-001-2023-00123-00",
        "cuantia": "cincuenta millones de pesos",
        "demandante": "BANCO DAVIVIENDA S.A.",
        "demandado": "JORGE ENRIQUE TASCON",
    }
    texto = """SEÑOR JUEZ CIVIL MUNICIPAL DE EJECUCIÓN DE SENTENCIAS

Radicado: 11001310300120230012300

**BANCO DAVIVIENDA S.A.** contra **JORGE ENRIQUE TASCON**, identificado con cédula 1.098.765.432.

PRETENSIONES:
Librar mandamiento ejecutivo de pago por la suma de CINCUENTA MILLONES DE PESOS ($50.000.000) por concepto de capital insoluto."""

    perfil = {"abogado": {}}

    res = auditar_js(datos, texto, perfil, fecha_hoy="2026-10-21")

    # Omisiones: 0 (el radicado de 23 dígitos y la cuantía en letras coinciden plenamente)
    assert len(res["omisiones"]) == 0, f"Omisiones inesperadas: {res['omisiones']}"

    # Invención: La cédula 1.098.765.432 que no venía en los datos
    assert len(res["invenciones"]) == 1
    inv = res["invenciones"][0]
    assert inv["tipo"] == "cédula / NIT"
    assert inv["normalizado"] == "1098765432"
    assert res["total"] == 1


def test_ejemplo_5_contrato_arrendamiento_matricula_nit_telefono():
    """Ejemplo 5: Contrato con matrícula inmobiliaria, NIT y teléfono. Reporta omisión de matrícula y teléfono, e invención de nuevo teléfono."""
    datos = {
        "arrendador": "INVERSIONES Y CONSTRUCCIONES LTDA.",
        "nit": "900.123.456-7",
        "arrendatario": "PEDRO ALONSO MONTOYA",
        "cedula": "79.876.543",
        "matricula": "50C-123456",
        "telefono": "320 123 4567",
        "canon": "$2.500.000",
    }
    texto = """CONTRATO DE ARRENDAMIENTO DE VIVIENDA URBANA

Entre los suscritos, **INVERSIONES Y CONSTRUCCIONES LTDA.**, con NIT 900.123.456-7, como arrendador; y **PEDRO ALONSO MONTOYA**, con cédula 79.876.543, como arrendatario, se acuerda:

CLÁUSULA PRIMERA: CANON. El canon mensual será de DOS MILLONES QUINIENTOS MIL PESOS ($2.500.000).
CLÁUSULA SEGUNDA: NOTIFICACIONES. Para cualquier efecto se señala el teléfono 300 987 6543."""

    perfil = {"abogado": {}}

    res = auditar_js(datos, texto, perfil, fecha_hoy="2026-10-21")

    # Omisiones: Matrícula inmobiliaria 50C-123456 y Teléfono 320 123 4567
    om_tipos = [o["tipo"] for o in res["omisiones"]]
    assert "matrícula" in om_tipos
    assert "teléfono" in om_tipos

    # Invenciones: El teléfono inventado 300 987 6543
    inv_tipos = [i["tipo"] for i in res["invenciones"]]
    assert "teléfono" in inv_tipos
    inv_tel = next(i for i in res["invenciones"] if i["tipo"] == "teléfono")
    assert inv_tel["normalizado"] == "3009876543"
