import pytest
"""
Pruebas unitarias para el comparador de versiones y exportación a Word
con control de cambios (w:ins y w:del) en El Memorialista.
"""
import io
import zipfile
from fastapi.testclient import TestClient

from app.main import app
from app.services.comparador_versiones import (
    tokenizar_texto,
    comparar_versiones,
    generar_docx_con_control_de_cambios,
    CompararVersionesRequest,
)

client = TestClient(app, headers={"Authorization": "Bearer unit-test-bearer"})


def test_tokenizar_texto():
    texto = "Señor Juez, el demandado adeuda $15.000.000 m/cte.\nNuevo hecho."
    tokens = tokenizar_texto(texto)
    assert "Señor" in tokens
    assert "Juez" in tokens
    assert "," in tokens
    assert "demandado" in tokens
    assert "15" in tokens or "$15" in tokens or "15000000" in "".join(tokens)
    assert "\n" in tokens
    assert "".join(tokens) == texto


def test_comparar_versiones_estadisticas_y_html():
    texto_base = """SEÑOR JUEZ CIVIL MUNICIPAL
El demandado no ha pagado la suma de 10 millones de pesos.
Solicito pruebas documentales."""

    texto_comparado = """SEÑOR JUEZ CIVIL DEL CIRCUITO
El demandado adeuda la suma de 25 millones de pesos m/cte.
Solicito pruebas documentales y testimoniales."""

    req = CompararVersionesRequest(
        texto_base=texto_base,
        texto_comparado=texto_comparado,
        autor="Dra. Laura Camila Martínez",
    )
    resp = comparar_versiones(req)

    # Verificación de estadísticas
    assert resp.estadisticas.palabras_anadidas > 0
    assert resp.estadisticas.palabras_eliminadas > 0
    assert resp.estadisticas.palabras_sin_cambio > 0
    assert resp.estadisticas.total_palabras_base > 0
    assert resp.estadisticas.total_palabras_comparado > 0

    # Verificación de HTML
    assert '<ins class="diff-ins"' in resp.html_diff
    assert '<del class="diff-del"' in resp.html_diff
    assert "DEL CIRCUITO" in resp.html_diff
    assert "MUNICIPAL" in resp.html_diff


def test_generar_docx_con_control_de_cambios_openxml():
    texto_base = "El contrato fue firmado el 10 de enero de 2024."
    texto_comparado = "El contrato fue suscrito válidamente el 15 de marzo de 2024."

    docx_bytes = generar_docx_con_control_de_cambios(
        texto_base=texto_base,
        texto_comparado=texto_comparado,
        autor="Carlos Abogado",
        titulo="Demanda con Control de Cambios",
    )

    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 1000

    # Abrir como ZIP y verificar estructura de OpenXML
    with zipfile.ZipFile(io.BytesIO(docx_bytes), "r") as z:
        archivos = z.namelist()
        assert "[Content_Types].xml" in archivos
        assert "word/document.xml" in archivos
        assert "word/settings.xml" in archivos
        assert "word/styles.xml" in archivos
        assert "docProps/core.xml" in archivos

        doc_xml = z.read("word/document.xml").decode("utf-8")
        settings_xml = z.read("word/settings.xml").decode("utf-8")

        # Verificar w:ins y w:del nativos
        assert "<w:ins" in doc_xml
        assert 'w:author="Carlos Abogado"' in doc_xml
        assert "<w:del" in doc_xml
        assert "<w:delText" in doc_xml
        assert "firmado" in doc_xml
        assert "suscrito" in doc_xml

        # Verificar activación de control de revisiones en Word
        assert "<w:trackRevisions/>" in settings_xml


def test_endpoint_api_versiones_comparar():
    payload = {
        "texto_base": "Primera pretensión: que se declare la resolución del contrato.",
        "texto_comparado": "Primera pretensión: que se declare la nulidad absoluta del contrato de compraventa.",
        "autor": "Andrés Felipe",
    }
    resp = client.post("/api/versiones/comparar", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "estadisticas" in data
    assert data["estadisticas"]["palabras_anadidas"] >= 2
    assert data["estadisticas"]["palabras_eliminadas"] >= 1
    assert "html_diff" in data
    assert '<ins class="diff-ins"' in data["html_diff"]
    assert '<del class="diff-del"' in data["html_diff"]


def test_endpoint_api_versiones_exportar_docx():
    payload = {
        "texto_base": "Cláusula primera: el valor es de diez millones.",
        "texto_comparado": "Cláusula primera: el valor total es de quince millones m/cte.",
        "autor": "Abogado Titular",
        "titulo": "Contrato Comparado",
    }
    resp = client.post("/api/versiones/exportar-docx", json=payload)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert "attachment;" in resp.headers["content-disposition"]
    assert ".docx" in resp.headers["content-disposition"]

    # Verificar que el contenido devuelto es un ZIP válido
    with zipfile.ZipFile(io.BytesIO(resp.content), "r") as z:
        assert "word/document.xml" in z.namelist()
        doc_xml = z.read("word/document.xml").decode("utf-8")
        assert "<w:ins" in doc_xml
        assert "<w:del" in doc_xml

pytestmark = pytest.mark.usefixtures("autenticacion_pruebas")
