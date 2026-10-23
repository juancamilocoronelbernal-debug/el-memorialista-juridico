"""
Pruebas de construcción de prompts en el servidor y catálogo (v2.2.1).
Verifica:
1. Equivalencia 100% entre Python y JavaScript para 3 tipos de documentos (tutela, peticion, demanda_verbal).
2. Endpoint GET /api/catalogo sin guías internas y con fecha_revision.
3. Validación Pydantic / 422 ante campos requeridos faltantes.
4. Rechazo con HTTP 400 del campo prompt libre en producción.
"""
import datetime
import json
import os
import subprocess
import shutil
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("autenticacion_pruebas")

from app.config import get_settings
from app.main import app
from app.services.prompt import (
    construir_prompt,
    listar_tipos,
    obtener_tipo,
    validar_datos_tipo,
)


@pytest.fixture(scope="module")
def perfil_prueba():
    return {
        "abogado": {
            "nombre": "Carlos Alberto Méndez",
            "genero": "m",
            "cedula": "79.123.456",
            "cedulaLugar": "Bogotá",
            "tp": "123456",
            "correo": "carlos@mendezabogados.com",
            "telefono": "3001234567",
            "direccion": "Carrera 7 # 71-21",
            "ciudad": "Bogotá D.C."
        },
        "estilo": {
            "tratamiento": "Señor Juez",
            "persona": "primera",
            "numHechos": "ordinal",
            "numPretensiones": "ordinal",
            "tono": "sobrio",
            "lenguaje": "claro",
            "fecha": "arriba",
            "esd": True,
            "cierre": "Del señor juez, atentamente",
            "extension": "estandar",
            "ficha": "Preferir citas breves.",
            "muestra": "Señor Juez Civil Municipal..."
        },
        "ia": {
            "smmlv": 1750905
        }
    }


def _generar_prompt_en_js(tipo_id, datos, perfil):
    """Compara Python con la referencia JavaScript original, ejecutada en Node.

    El código y los datos pasan por stdin; no requiere macOS ni escribe archivos
    temporales compartidos. TZ=UTC mantiene la misma fecha que la prueba Python.
    """
    node = os.environ.get("NODE_BINARY") or shutil.which("node")
    if not node:
        pytest.skip("Node.js es necesario para verificar equivalencia Python/JavaScript")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base_dir, "tests", "reference_prompt.js"), encoding="utf-8") as source:
        reference = source.read()
    state = {"tipo": tipo_id, "datos": datos, "perfil": perfil}
    script = "const state = " + json.dumps(state, ensure_ascii=False) + ";\n"
    script += reference + "\nprocess.stdout.write(construirPrompt());\n"
    result = subprocess.run([node, "-"], input=script, capture_output=True, text=True,
                            timeout=20, env={**os.environ, "TZ": "UTC"})
    if result.returncode != 0:
        raise RuntimeError(f"Error evaluando JS en {tipo_id}: {result.stderr}")
    return result.stdout


def test_prompt_identico_tutela(perfil_prueba):
    tutela_meta = obtener_tipo("tutela")
    datos = tutela_meta["ejemplo"]
    hoy = datetime.datetime.now(datetime.timezone.utc).date()

    py_prompt = construir_prompt("tutela", datos, perfil_prueba, fecha_ref=hoy)
    js_prompt = _generar_prompt_en_js("tutela", datos, perfil_prueba)

    assert py_prompt == js_prompt, "El prompt generado en Python para 'tutela' difiere del generado en JS"


def test_prompt_identico_peticion(perfil_prueba):
    peticion_meta = obtener_tipo("peticion")
    datos = peticion_meta["ejemplo"]
    hoy = datetime.datetime.now(datetime.timezone.utc).date()

    py_prompt = construir_prompt("peticion", datos, perfil_prueba, fecha_ref=hoy)
    js_prompt = _generar_prompt_en_js("peticion", datos, perfil_prueba)

    assert py_prompt == js_prompt, "El prompt generado en Python para 'peticion' difiere del generado en JS"


def test_prompt_identico_demanda_verbal(perfil_prueba):
    datos = {
        "destinatario": "Juez Civil Municipal de Bogotá D.C. (Reparto)",
        "ciudad": "Bogotá D.C.",
        "cliente": "Inversiones del Norte S.A.S., NIT 901.234.567-8, rep. legal Juan Pérez.",
        "contraparte": "Construcciones Andinas Ltda., NIT 800.987.654-3.",
        "asunto": "Resolución de contrato de compraventa e indemnización de perjuicios.",
        "hechos": "1. El 10 de enero de 2026 se celebró contrato.\n2. Incumplimiento del plazo de entrega.",
        "pretensiones": "1. Declarar la resolución del contrato.\n2. Condenar al pago de 50 millones.",
        "cuantia": "Menor cuantía, estimada en $50.000.000 COP.",
        "juramento_estimatorio": "Bajo juramento estimo los perjuicios en $50.000.000.",
        "conciliacion": "Acta de conciliación fallida del 15 de marzo de 2026.",
        "medidas": "Embargo de cuentas bancarias.",
        "pruebas": "Copia del contrato y requerimientos.",
        "notificaciones": "Demandante: notificaciones@norte.com. Demandada: judicial@andinas.com."
    }
    hoy = datetime.datetime.now(datetime.timezone.utc).date()

    py_prompt = construir_prompt("demanda_verbal", datos, perfil_prueba, fecha_ref=hoy)
    js_prompt = _generar_prompt_en_js("demanda_verbal", datos, perfil_prueba)

    assert py_prompt == js_prompt, "El prompt generado en Python para 'demanda_verbal' difiere del generado en JS"


def test_api_catalogo():
    with TestClient(app, headers={"Authorization": "Bearer unit-test-bearer"}) as client:
        res = client.get("/api/catalogo")
        assert res.status_code == 200
        data = res.json()
        assert "tipos" in data
        assert len(data["tipos"]) >= 26
        assert "areas" in data
        assert "fecha_revision" in data
        assert "Base normativa" in "Base normativa revisada al " + data["fecha_revision"]
        # Las guías internas no deben exponerse al cliente
        for t in data["tipos"]:
            assert "guia" not in t, f"El tipo {t['id']} expone la guía interna"
            assert "fuentes" in t
            assert "version" in t


def test_validacion_campos_requeridos():
    tutela_meta = obtener_tipo("tutela")
    # Datos vacíos: faltan destinatario, cliente, contraparte, derechos, pretensiones
    errores = validar_datos_tipo(tutela_meta, {})
    assert len(errores) > 0

    with TestClient(app, headers={"Authorization": "Bearer unit-test-bearer"}) as client:
        res = client.post("/api/redactar", json={
            "tipo": "tutela",
            "datos": {},
            "perfil": {}
        })
        assert res.status_code == 422
        assert "obligatorio" in res.json()["detail"]


def test_rechazo_prompt_libre_en_produccion(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()

    with TestClient(app, headers={"Authorization": "Bearer unit-test-bearer"}) as client:
        # Intento de enviar prompt libre en producción -> debe retornar 400
        res = client.post("/api/redactar", json={
            "prompt": "Redacta una tutela libremente sin tipo ni datos validados.",
            "modo": "nuevo"
        })
        assert res.status_code == 400
        assert "producción" in res.json()["detail"].lower()

    get_settings.cache_clear()
