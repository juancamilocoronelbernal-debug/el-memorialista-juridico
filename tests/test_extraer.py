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


@patch("app.routers.documents.extraer_datos_con_gemini")
def test_endpoint_extraer_contestacion_hechos_numerados(mock_gemini):
    """En contestación, verifica la extracción de hechos numerados, pretensiones y fecha de notificación."""
    mock_gemini.return_value = {
        "propuestas": [
            {
                "campo": "respuesta_pretensiones",
                "etiqueta": "Posición frente a las pretensiones",
                "tipo_campo": "area",
                "valor": "Me opongo a todas las pretensiones de la demanda por inexistencia de la obligación.",
                "archivo": "demanda_civil.pdf",
                "pagina": 4,
                "cita_textual_corta": "PRIMERA: Se declare que el demandado incumplió el contrato",
                "confianza": "alta",
            },
            {
                "campo": "notificacion_fecha",
                "etiqueta": "Fecha de notificación del auto admisorio",
                "tipo_campo": "date",
                "valor": "2026-10-15",
                "archivo": "demanda_civil.pdf",
                "pagina": 1,
                "cita_textual_corta": "Notificado personalmente el 15 de octubre de 2026",
                "confianza": "alta",
            },
        ],
        "hechos_numerados": [
            {"numero": 1, "texto": "El 15 de enero de 2025 se suscribió contrato de promesa de compraventa."},
            {"numero": 2, "texto": "El precio acordado fue de $120.000.000 pagaderos en tres cuotas."},
            {"numero": 3, "texto": "La parte demandada incurrió en mora en el pago de la segunda cuota."},
        ],
        "decision_providencia": None,
        "fecha_notificacion_detectada": "2026-10-15",
    }

    pdf_bytes = io.BytesIO(b"%PDF-1.4 demanda simulada")
    files = [("archivos", ("demanda_civil.pdf", pdf_bytes, "application/pdf"))]

    resp = client.post("/api/extraer", data={"tipo": "contestacion"}, files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["tipo"] == "contestacion"
    assert len(data["hechos_numerados"]) == 3
    assert data["hechos_numerados"][0]["numero"] == 1
    assert "promesa de compraventa" in data["hechos_numerados"][0]["texto"]
    assert data["fecha_notificacion_detectada"] == "2026-10-15"


@patch("app.routers.documents.extraer_datos_con_gemini")
def test_endpoint_extraer_fallo_tutela_y_notificacion(mock_gemini):
    """En impugnación de tutela, auto y apelación, verifica extracción de decisión, fecha y notificación."""
    mock_gemini.return_value = {
        "propuestas": [
            {
                "campo": "fallo",
                "etiqueta": "Fallo impugnado",
                "tipo_campo": "area",
                "valor": "Sentencia del 10 de octubre de 2026 que negó la acción de tutela por improcedente.",
                "archivo": "sentencia_primera_instancia.pdf",
                "pagina": 3,
                "cita_textual_corta": "PRIMERO: NEGAR por improcedente el amparo solicitado",
                "confianza": "alta",
            },
            {
                "campo": "notificacion_fecha",
                "etiqueta": "Fecha de notificación del fallo",
                "tipo_campo": "date",
                "valor": "2026-10-21",
                "archivo": "sentencia_primera_instancia.pdf",
                "pagina": 4,
                "cita_textual_corta": "Enviado por correo electrónico el 21 de octubre de 2026",
                "confianza": "alta",
            },
        ],
        "hechos_numerados": [],
        "decision_providencia": {
            "decision": "Negar por improcedente el amparo solicitado.",
            "fecha": "2026-10-10",
            "archivo": "sentencia_primera_instancia.pdf",
            "pagina": 3,
            "cita_textual_corta": "NEGAR por improcedente el amparo",
            "confianza": "alta",
        },
        "fecha_notificacion_detectada": "2026-10-21",
    }

    pdf_bytes = io.BytesIO(b"%PDF-1.4 sentencia tutela")
    files = [("archivos", ("sentencia_primera_instancia.pdf", pdf_bytes, "application/pdf"))]

    resp = client.post("/api/extraer", data={"tipo": "impugnacion_tutela"}, files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["decision_providencia"] is not None
    assert "Negar por improcedente" in data["decision_providencia"]["decision"]
    assert data["fecha_notificacion_detectada"] == "2026-10-21"
    assert any(p["campo"] == "fallo" for p in data["propuestas"])


def test_prompt_instrucciones_especiales_providencias_y_contestacion():
    """Verifica que el prompt de extracción incluya las instrucciones legales para contestación y providencias."""
    from app.services.extractor_documentos import construir_prompt_extraccion

    archivos = [{"nombre": "demanda.pdf", "mime": "application/pdf", "tamano": 50000}]
    campos = [{"k": "respuesta_hechos", "l": "Respuesta a cada hecho"}, {"k": "respuesta_pretensiones", "l": "Pretensiones"}]

    prompt_contestacion = construir_prompt_extraccion("contestacion", "Contestación de demanda", campos, archivos)
    assert "hechos_numerados" in prompt_contestacion
    assert "art. 96 CGP" in prompt_contestacion
    assert "respuesta_pretensiones" in prompt_contestacion

    prompt_tutela = construir_prompt_extraccion("impugnacion_tutela", "Impugnación de tutela", campos, archivos)
    assert "decision_providencia" in prompt_tutela
    assert "notificacion_fecha" in prompt_tutela


def test_frontend_asistente_hechos_y_banner_plazos():
    """Verifica que el HTML del frontend contenga el banner superior de plazos y el asistente de hechos art. 96 CGP."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # 1. Banner superior de vencimiento
    assert 'id="bannerVencimientoTop"' in html
    assert 'class="banner-vencimiento-top"' in html
    assert "actualizarBannerVencimientoTop" in html

    # 2. Asistente interactivo de hechos de la contestación (art. 96 CGP)
    assert "renderAsistenteHechosContestacion" in html
    assert "recompilarRespuestaHechos" in html
    assert "parsearTextoAHechos" in html

    # 3. Opciones del selector de hechos
    assert "Es cierto" in html
    assert "No es cierto" in html
    assert "No me consta" in html
    assert "Es parcialmente cierto" in html
    assert "asistente-hecho-razon" in html



