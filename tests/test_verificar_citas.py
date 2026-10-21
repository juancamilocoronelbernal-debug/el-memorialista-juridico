"""Pruebas de extracción y verificación de citas jurídicas (v2.2.1).

Verifica:
1. Extracción por expresiones regulares sin IA para sentencias (varios formatos), leyes, decretos y códigos.
2. Comportamiento ante respuestas HTTP simuladas (Corte Constitucional y Secretaría del Senado).
3. Clasificación de colores (verde, amarillo, rojo) según existencia y pertinencia.
4. Caché de 30 días.
5. Endpoint POST /api/verificar-citas.
"""
import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.verificador_citas import (
    extraer_citas,
    verificar_citas,
    _guardar_cache,
    _obtener_cache,
)


def test_extraccion_regex_sentencias():
    texto = (
        "Como se indicó en la Sentencia T-760 de 2008 y en T-760/08, la salud es fundamental. "
        "En la sentencia C-522 de 2023 se reiteró la regla. "
        "También véase la SU-012/20, el Auto 123 de 2021 y el auto A-456-19. "
        "Por último, la sentencia T-123-04."
    )
    citas = extraer_citas(texto)
    identificadores = {c["identificador"] for c in citas}

    assert "T-760-08" in identificadores
    assert "C-522-23" in identificadores
    assert "SU-12-20" in identificadores or "SU-012-20" in identificadores
    assert "A-123-21" in identificadores
    assert "A-456-19" in identificadores
    assert "T-123-04" in identificadores

    # Verificar que las URLs se formaron correctamente
    for c in citas:
        if c["identificador"] == "T-760-08":
            assert c["url"] == "https://www.corteconstitucional.gov.co/relatoria/2008/T-760-08.htm"
        elif c["identificador"] == "C-522-23":
            assert c["url"] == "https://www.corteconstitucional.gov.co/relatoria/2023/C-522-23.htm"


def test_extraccion_regex_leyes_decretos_codigos():
    texto = (
        "Conforme a la Ley 1755 de 2015 sobre derecho de petición, "
        "y al Decreto 2591 de 1991 que reglamenta la tutela. "
        "Asimismo, se cita el artículo 82 del CGP, el art. 138 del CPACA, "
        "el art. 154 del Código Civil, el artículo 64 del CST, "
        "el artículo 66 de la Ley 906 de 2004 y el artículo 86 de la Constitución Política."
    )
    citas = extraer_citas(texto)
    nombres = {c["nombre"] for c in citas}

    assert "Ley 1755 de 2015" in nombres
    assert "Decreto 2591 de 1991" in nombres
    assert "Artículo 82 del Código General del Proceso" in nombres
    assert "Artículo 138 del Código de Procedimiento Administrativo y de lo Contencioso Administrativo" in nombres
    assert "Artículo 154 del Código Civil" in nombres
    assert "Artículo 64 del Código Sustantivo del Trabajo" in nombres
    assert "Artículo 66 del Código de Procedimiento Penal (Ley 906 de 2004)" in nombres
    assert "Artículo 86 de la Constitución Política de Colombia" in nombres


@pytest.mark.asyncio
async def test_verificacion_simulada_corte_constitucional():
    texto = (
        "La Sentencia T-760 de 2008 amparó el derecho a la salud. "
        "En contraste, la Sentencia T-9999 de 1999 no existe. "
        "Y la Sentencia C-999 de 2021 fallará por timeout."
    )

    def fake_transport(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "T-760-08.htm" in url_str:
            return httpx.Response(
                200,
                text="<html><body><h1>Sentencia T-760/08</h1><p>El derecho a la salud es fundamental autónomo.</p></body></html>"
            )
        elif "T-9999-99.htm" in url_str:
            # La Corte suele retornar 404 o su home page sin el número
            return httpx.Response(200, text="<html><body>Página no encontrada</body></html>")
        elif "C-999-21.htm" in url_str:
            raise httpx.ConnectTimeout("Timeout de prueba")
        return httpx.Response(404, text="Not found")

    async with httpx.AsyncClient(transport=httpx.MockTransport(fake_transport)) as cliente:
        resultado = await verificar_citas(texto, cliente_http=cliente)

    assert resultado["ok"] is True
    assert resultado["total_citas"] >= 3

    citas_por_id = {c["identificador"]: c for c in resultado["citas"]}

    # T-760-08 debe existir y ser verde o amarillo si respaldo es parcial
    assert "T-760-08" in citas_por_id
    assert citas_por_id["T-760-08"]["estado"] == "existe"
    assert citas_por_id["T-760-08"]["color"] in ("verde", "amarillo")
    assert citas_por_id["T-760-08"]["pertinencia"]["respalda"] in ("si", "parcial")

    # T-9999-99 debe ser no encontrada y roja
    assert "T-9999-99" in citas_por_id
    assert citas_por_id["T-9999-99"]["estado"] == "no_encontrada"
    assert citas_por_id["T-9999-99"]["color"] == "rojo"

    # C-999-21 debe ser sin verificar y amarilla
    assert "C-999-21" in citas_por_id
    assert citas_por_id["C-999-21"]["estado"] == "sin_verificar"
    assert citas_por_id["C-999-21"]["color"] == "amarillo"


@pytest.mark.asyncio
async def test_verificacion_simulada_leyes_y_decretos():
    texto = "Se fundamenta en la Ley 1755 de 2015 y en la Ley 9999 de 2099."

    def fake_transport(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "ley_1755_2015.html" in url_str:
            return httpx.Response(200, text="<html><head><title>LEY 1755 DE 2015</title></head></html>")
        return httpx.Response(404, text="Categoría no encontrada")

    async with httpx.AsyncClient(transport=httpx.MockTransport(fake_transport)) as cliente:
        resultado = await verificar_citas(texto, cliente_http=cliente)

    citas_por_nombre = {c["nombre"]: c for c in resultado["citas"]}
    assert citas_por_nombre["Ley 1755 de 2015"]["color"] == "verde"
    assert citas_por_nombre["Ley 9999 de 2099"]["color"] == "rojo"


def test_cache_30_dias():
    test_url = "https://www.corteconstitucional.gov.co/relatoria/2000/T-100-00.htm"
    _guardar_cache(test_url, "existe", "Fragmento de prueba en cache")
    cached = _obtener_cache(test_url)
    assert cached is not None
    estado, frag = cached
    assert estado == "existe"
    assert "Fragmento de prueba" in frag


def test_endpoint_api_verificar_citas():
    with TestClient(app) as client:
        res = client.post("/api/verificar-citas", json={
            "texto": "Según el artículo 86 de la Constitución y el artículo 82 del CGP..."
        })
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["total_citas"] == 2
        assert data["resumen"]["verde"] == 2
        for c in data["citas"]:
            assert c["color"] == "verde"
            assert "url" in c
            assert "pertinencia" in c


@pytest.mark.asyncio
async def test_pertinencia_colores_segun_respaldo(monkeypatch):
    from app.services.gemini_service import gemini_service

    texto = "Sentencia T-760 de 2008 sobre salud."

    def fake_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body><h1>Sentencia T-760/08</h1><p>Salud</p></body></html>")

    # Caso 1: Respalda sí -> verde
    async def fake_ia_si(prompt):
        return {"respalda": "si", "fragmento": "Cita pertinente"}
    monkeypatch.setattr(gemini_service, "evaluar_pertinencia_json", fake_ia_si)

    async with httpx.AsyncClient(transport=httpx.MockTransport(fake_transport)) as cliente:
        res_si = await verificar_citas(texto, cliente_http=cliente)
        assert res_si["citas"][0]["color"] == "verde"

    # Caso 2: Respalda parcial -> amarillo
    async def fake_ia_parcial(prompt):
        return {"respalda": "parcial", "fragmento": "Respaldo parcial"}
    monkeypatch.setattr(gemini_service, "evaluar_pertinencia_json", fake_ia_parcial)

    async with httpx.AsyncClient(transport=httpx.MockTransport(fake_transport)) as cliente:
        res_parcial = await verificar_citas(texto, cliente_http=cliente)
        assert res_parcial["citas"][0]["color"] == "amarillo"

    # Caso 3: Respalda no -> rojo
    async def fake_ia_no(prompt):
        return {"respalda": "no", "fragmento": "No respalda"}
    monkeypatch.setattr(gemini_service, "evaluar_pertinencia_json", fake_ia_no)

    async with httpx.AsyncClient(transport=httpx.MockTransport(fake_transport)) as cliente:
        res_no = await verificar_citas(texto, cliente_http=cliente)
        assert res_no["citas"][0]["color"] == "rojo"


def test_opcion_jurisprudencia_verificables_en_prompt():
    from app.services.prompt import construir_prompt, obtener_tipo
    meta = obtener_tipo("tutela")
    datos = dict(meta["ejemplo"])
    datos["_juris"] = "verificables"
    prompt = construir_prompt("tutela", datos, {})
    assert "el sistema verificará automáticamente su existencia en relatoría oficial" in prompt
