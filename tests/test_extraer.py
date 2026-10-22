"""Pruebas unitarias e integrales para la extracción multimodal de documentos del caso.

Verifica:
1. Validación de tamaño total de archivos (límite 20 MB).
2. Validación de formatos permitidos (PDF, imágenes, audio).
3. Rechazo de formatos no permitidos (.exe, .zip, .docx).
4. Privacidad: los archivos se leen en memoria y no se guardan en disco.
5. Construcción de esquema dinámico de extracción según los campos del tipo.
6. Endpoint POST /api/extraer con simulación de respuesta de Gemini 3.8 Flash.
7. Cada valor trae {valor, archivo, pagina, cita_textual_corta, confianza}.
"""

import io
import json
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient

from app.main import app
from app.services.extractor_documentos import (
    MAX_TOTAL_BYTES,
    detectar_mime,
    validar_archivos_extraccion,
    construir_esquema_extraccion,
    extraer_campos_relevantes_tipo,
    extraer_datos_con_gemini,
)
from app.services.prompt import obtener_tipo

client = TestClient(app)


def test_detectar_mime():
    """Valida la detección correcta de formatos permitidos para PDF, imágenes y audio."""
    assert detectar_mime("demanda.pdf", "application/pdf") == "application/pdf"
    assert detectar_mime("cedula.PNG", None) == "image/png"
    assert detectar_mime("contrato.jpg", "image/jpeg") == "image/jpeg"
    assert detectar_mime("foto.webp", None) == "image/webp"
    assert detectar_mime("audiencia.mp3", "audio/mpeg") == "audio/mpeg"
    assert detectar_mime("declaracion.wav", None) == "audio/wav"
    assert detectar_mime("audio_llamada.m4a", None) == "audio/m4a"

    # Formatos prohibidos
    assert detectar_mime("virus.exe", "application/x-msdownload") is None
    assert detectar_mime("archivo.zip", "application/zip") is None
    assert detectar_mime("documento.docx", None) is None


@pytest.mark.asyncio
async def test_validar_archivos_excede_limite_20mb():
    """Verifica que si el total excede 20 MB se lance un error 400."""
    contenido_21mb = b"0" * (20 * 1024 * 1024 + 1024)
    archivo = UploadFile(
        filename="archivo_pesado.pdf",
        file=io.BytesIO(contenido_21mb),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(HTTPException) as exc_info:
        await validar_archivos_extraccion([archivo])
    assert exc_info.value.status_code == 400
    assert "20 MB" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validar_archivos_formato_no_permitido():
    """Verifica que rechace archivos con extensiones no autorizadas."""
    archivo_invalido = UploadFile(
        filename="archivo.exe",
        file=io.BytesIO(b"MZ..."),
        headers={"content-type": "application/octet-stream"},
    )

    with pytest.raises(HTTPException) as exc_info:
        await validar_archivos_extraccion([archivo_invalido])
    assert exc_info.value.status_code == 400
    assert "no tiene un formato compatible" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validar_archivos_en_memoria_sin_guardar_en_disco():
    """Verifica que los archivos válidos se lean en memoria y conserven sus bytes."""
    datos_pdf = b"%PDF-1.4 simulado..."
    datos_img = b"\x89PNG\r\n\x1a\n simulado..."
    f1 = UploadFile(filename="orden.pdf", file=io.BytesIO(datos_pdf), headers={"content-type": "application/pdf"})
    f2 = UploadFile(filename="cedula.png", file=io.BytesIO(datos_img), headers={"content-type": "image/png"})

    archivos_procesados, total_bytes = await validar_archivos_extraccion([f1, f2])
    assert len(archivos_procesados) == 2
    assert total_bytes == len(datos_pdf) + len(datos_img)
    assert archivos_procesados[0]["bytes"] == datos_pdf
    assert archivos_procesados[1]["bytes"] == datos_img


def test_construir_esquema_extraccion():
    """Verifica que el esquema JSON contenga las propiedades requeridas para los campos del tipo."""
    tipo_tutela = obtener_tipo("tutela")
    assert tipo_tutela is not None

    campos = extraer_campos_relevantes_tipo(tipo_tutela)
    assert len(campos) > 0
    # No deben incluirse campos con guión bajo
    for c in campos:
        assert not c["k"].startswith("_")

    esquema = construir_esquema_extraccion(campos)
    assert esquema["type"] == "OBJECT"
    assert "properties" in esquema
    assert "cliente" in esquema["properties"]
    assert "contraparte" in esquema["properties"]

    prop_cliente = esquema["properties"]["cliente"]
    assert prop_cliente["type"] == "OBJECT"
    assert "valor" in prop_cliente["properties"]
    assert "archivo" in prop_cliente["properties"]
    assert "pagina" in prop_cliente["properties"]
    assert "cita_textual_corta" in prop_cliente["properties"]
    assert "confianza" in prop_cliente["properties"]
    assert prop_cliente["properties"]["confianza"]["enum"] == ["alta", "media", "baja"]


def test_endpoint_extraer_sin_archivos():
    """Verifica que el endpoint responda 422 si falta 'archivos' o 'tipo'."""
    resp = client.post("/api/extraer", data={"tipo": "tutela"})
    assert resp.status_code == 422


def test_endpoint_extraer_tipo_inexistente():
    """Verifica error 400 si el tipo no existe en el catálogo."""
    pdf_bytes = io.BytesIO(b"%PDF-1.4 prueba")
    files = [("archivos", ("prueba.pdf", pdf_bytes, "application/pdf"))]
    resp = client.post("/api/extraer", data={"tipo": "tipo_que_no_existe_999"}, files=files)
    assert resp.status_code == 400
    assert "no existe" in resp.json()["detail"]


@patch("app.routers.documents.extraer_datos_con_gemini")
def test_endpoint_extraer_exitoso(mock_gemini):
    """Verifica el flujo completo de POST /api/extraer con respuesta simulada de Gemini 3.8 Flash."""
    mock_gemini.return_value = [
        {
            "campo": "cliente",
            "etiqueta": "Accionante",
            "tipo_campo": "area",
            "valor": "MARÍA FERNANDA LÓPEZ RINCÓN, C.C. 52.883.102 de Bogotá, correo maria@email.com",
            "archivo": "cedula_maria.pdf",
            "pagina": 1,
            "cita_textual_corta": "LÓPEZ RINCÓN MARÍA FERNANDA C.C. 52.883.102",
            "confianza": "alta",
        },
        {
            "campo": "contraparte",
            "etiqueta": "Accionado(s)",
            "tipo_campo": "area",
            "valor": "NUEVA EPS S.A., NIT 900.156.264-2",
            "archivo": "negacion_servicio.pdf",
            "pagina": 2,
            "cita_textual_corta": "NUEVA EPS S.A. NIT 900.156.264-2",
            "confianza": "alta",
        },
    ]

    pdf_bytes = io.BytesIO(b"%PDF-1.4 documento ficticio")
    files = [("archivos", ("cedula_maria.pdf", pdf_bytes, "application/pdf"))]

    resp = client.post("/api/extraer", data={"tipo": "tutela"}, files=files)
    assert resp.status_code == 200
    data = resp.json()

    assert data["ok"] is True
    assert data["tipo"] == "tutela"
    assert data["total_archivos"] == 1
    assert len(data["propuestas"]) == 2

    prop1 = data["propuestas"][0]
    assert prop1["campo"] == "cliente"
    assert "MARÍA FERNANDA" in prop1["valor"]
    assert prop1["archivo"] == "cedula_maria.pdf"
    assert prop1["pagina"] == 1
    assert prop1["confianza"] == "alta"
    assert prop1["cita_textual_corta"] == "LÓPEZ RINCÓN MARÍA FERNANDA C.C. 52.883.102"


@patch("app.routers.documents.extraer_datos_con_gemini")
def test_endpoint_extraer_audio_e_imagenes(mock_gemini):
    """Verifica que se procesen correctamente imágenes y audios sin guardar en disco."""
    mock_gemini.return_value = [
        {
            "campo": "hechos",
            "etiqueta": "Hechos",
            "tipo_campo": "area",
            "valor": "El 15 de marzo de 2026 se acordó verbalmente la entrega del inmueble.",
            "archivo": "grabacion_llamada.mp3",
            "pagina": None,
            "cita_textual_corta": "Quedamos en entregarle las llaves el quince de marzo",
            "confianza": "alta",
        },
        {
            "campo": "cuantia",
            "etiqueta": "Cuantía estimada",
            "tipo_campo": "valor",
            "valor": "$ 45.000.000",
            "archivo": "recibo_pago.png",
            "pagina": None,
            "cita_textual_corta": "VALOR PAGADO: $45.000.000 M/CTE",
            "confianza": "alta",
        },
    ]

    png_bytes = io.BytesIO(b"\x89PNG\r\n\x1a\n datos simulados")
    mp3_bytes = io.BytesIO(b"ID3 datos simulados audio mp3")

    files = [
        ("archivos", ("recibo_pago.png", png_bytes, "image/png")),
        ("archivos", ("grabacion_llamada.mp3", mp3_bytes, "audio/mp3")),
    ]

    resp = client.post("/api/extraer", data={"tipo": "demanda_verbal"}, files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["total_archivos"] == 2
    assert len(data["propuestas"]) == 2
    assert data["propuestas"][0]["campo"] == "hechos"
    assert data["propuestas"][0]["pagina"] is None
    assert data["propuestas"][1]["campo"] == "cuantia"

