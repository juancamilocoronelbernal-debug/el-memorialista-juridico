import json
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.prompt import listar_tipos, obtener_tipo
from app.services.revisor_requisitos import revisar_requisitos


def test_catalogo_todos_tipos_tienen_requisitos():
    """Verifica que todos los tipos del catálogo incluyan 'requisitos' con id, texto, norma y critico."""
    with TestClient(app) as client:
        res = client.get("/api/catalogo")
        assert res.status_code == 200
        data = res.json()
        tipos = data["tipos"]
        assert len(tipos) >= 26

        for t in tipos:
            tid = t["id"]
            assert "requisitos" in t, f"El tipo {tid} no tiene el campo 'requisitos'"
            reqs = t["requisitos"]
            assert isinstance(reqs, list) and len(reqs) > 0, f"El tipo {tid} tiene 'requisitos' vacío"
            for r in reqs:
                assert "id" in r and isinstance(r["id"], str)
                assert "texto" in r and isinstance(r["texto"], str)
                assert "norma" in r and isinstance(r["norma"], str)
                assert "critico" in r and isinstance(r["critico"], bool)


@pytest.mark.asyncio
async def test_revisar_tutela_omision_juramento_art37():
    """En tutela, si se omite el juramento del art. 37 del D. 2591/1991, debe marcarse 'no_cumple' y crítico."""
    texto_sin_juramento = """Bogotá D.C., 21 de octubre de 2026.
SEÑOR JUEZ CIVIL MUNICIPAL DE BOGOTÁ (REPARTO)

Referencia: ACCIÓN DE TUTELA
Accionante: MARÍA FERNANDA LÓPEZ RINCÓN
Accionado: NUEVA EPS S.A.

HECHOS:
1. El 9 de septiembre de 2026 me negaron el medicamento.
2. No tengo otro medio de defensa judicial eficaz y oportuno (subsidiariedad e inmediatez).

PRETENSIONES:
Ordenar a NUEVA EPS S.A. suministrar el tratamiento integral.

NOTIFICACIONES:
Accionante: calle 10 # 4-20, correo maria@email.com.
Accionado: notificaciones@nuevaeps.com.co."""

    resultado = await revisar_requisitos(texto_sin_juramento, "tutela")
    assert isinstance(resultado, list) and len(resultado) > 0

    req_jur = next((r for r in resultado if r["id"] == "juramento_no_otra_tutela"), None)
    assert req_jur is not None
    assert req_jur["critico"] is True
    assert req_jur["estado"] == "no_cumple"
    assert "juramento" in req_jur["sugerencia"].lower() or "tutela" in req_jur["sugerencia"].lower()

    # Ahora con el juramento incluido
    texto_con_juramento = texto_sin_juramento + "\n\nJURAMENTO:\nManifiesto bajo la gravedad del juramento que no he interpuesto otra acción de tutela por los mismos hechos y derechos (art. 37 del Decreto 2591 de 1991)."
    resultado_con = await revisar_requisitos(texto_con_juramento, "tutela")
    req_jur_con = next((r for r in resultado_con if r["id"] == "juramento_no_otra_tutela"), None)
    assert req_jur_con["estado"] == "cumple"


@pytest.mark.asyncio
async def test_revisar_demanda_verbal_requisitos():
    """Demanda verbal: evalúa art. 82 CGP, juramento estimatorio art. 206 y Ley 2213 de 2022."""
    texto_demanda = """SEÑOR JUEZ CIVIL DEL CIRCUITO DE BOGOTÁ

DEMANDANTE: CARLOS ANDRÉS RINCÓN MORALES, C.C. 1.020.304.050
DEMANDADO: CLÍNICA SAN JOSÉ S.A., NIT 900.123.456-7

PRETENSIONES:
1. Declarar responsable a la demandada.
2. Condenar al pago de perjuicios materiales por $80.000.000.

HECHOS:
1. El 15 de mayo de 2025 se celebró el contrato.
2. Hubo incumplimiento grave.

CUANTÍA Y COMPETENCIA:
Por la cuantía de $80.000.000 es usted competente.

NOTIFICACIONES:
Demandante: carrera 7 # 32-16, correo carlos@email.com.
Demandado: calle 100 # 15-20, correo notificaciones@clinicasanjose.com."""

    resultado = await revisar_requisitos(texto_demanda, "demanda_verbal")
    assert isinstance(resultado, list)

    mapa = {r["id"]: r for r in resultado}

    # Juramento estimatorio: se reclaman perjuicios pero no hay acápite de juramento estimatorio
    assert "juramento_estimatorio" in mapa
    assert mapa["juramento_estimatorio"]["critico"] is True
    assert mapa["juramento_estimatorio"]["estado"] == "no_cumple"
    assert "206" in mapa["juramento_estimatorio"]["sugerencia"] or "JURAMENTO ESTIMATORIO" in mapa["juramento_estimatorio"]["sugerencia"]

    # Afirmación jurada del canal digital del demandado (art. 8 Ley 2213)
    assert "juramento_canal_demandado" in mapa
    assert mapa["juramento_canal_demandado"]["critico"] is True
    assert mapa["juramento_canal_demandado"]["estado"] == "no_cumple"


def test_endpoint_revisar_http():
    """Prueba el endpoint HTTP POST /api/revisar."""
    with TestClient(app) as client:
        # 1. Error con escrito vacío
        r_vacio = client.post("/api/revisar", json={"escrito": "   ", "tipo": "tutela"})
        assert r_vacio.status_code == 400

        # 2. Tipo inexistente devuelve lista vacía
        r_tipo_invalido = client.post("/api/revisar", json={"escrito": "Texto cualquiera", "tipo": "tipo_inexistente"})
        assert r_tipo_invalido.status_code == 200
        assert r_tipo_invalido.json() == []

        # 3. Llamada normal con tutela
        escrito = "Señor Juez Civil Municipal. Interpongo tutela contra EPS por negación de medicamentos."
        res = client.post("/api/revisar", json={"escrito": escrito, "tipo": "tutela"})
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 5

        # Esquema esperado: id, estado, evidencia, sugerencia
        for item in data:
            assert "id" in item
            assert item["estado"] in ("cumple", "no_cumple", "no_aplica")
            assert "evidencia" in item
            assert "sugerencia" in item
            assert "critico" in item
            assert "norma" in item


def test_revisar_con_salida_simulada_ia(monkeypatch):
    """Verifica que el endpoint incorpore adecuadamente la respuesta JSON de un modelo económico de IA."""
    simulacion_ia = [
        {"id": "designacion_juez", "estado": "cumple", "evidencia": "Dirigido a Juez Civil Municipal", "sugerencia": ""},
        {"id": "juramento_no_otra_tutela", "estado": "no_cumple", "evidencia": "Omitido en el memorial", "sugerencia": "Agregar juramento del art. 37 del D. 2591/1991"}
    ]

    async def mock_evaluar(prompt):
        return simulacion_ia

    from app.services.gemini_service import gemini_service
    monkeypatch.setattr(gemini_service, "evaluar_requisitos_json", mock_evaluar)

    with TestClient(app) as client:
        res = client.post("/api/revisar", json={"escrito": "Texto del escrito", "tipo": "tutela"})
        assert res.status_code == 200
        items = res.json()
        mapa = {it["id"]: it for it in items}

        assert mapa["designacion_juez"]["estado"] == "cumple"
        assert mapa["designacion_juez"]["evidencia"] == "Dirigido a Juez Civil Municipal"

        assert mapa["juramento_no_otra_tutela"]["estado"] == "no_cumple"
        assert mapa["juramento_no_otra_tutela"]["critico"] is True
        assert "art. 37" in mapa["juramento_no_otra_tutela"]["sugerencia"]
