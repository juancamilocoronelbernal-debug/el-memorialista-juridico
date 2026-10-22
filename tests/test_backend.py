"""
Pruebas del backend v2.2 con un Gemini simulado: no gastan tokens ni necesitan internet.
Desde la raíz del proyecto:
    pip install -r requirements-dev.txt
    pytest -q
"""
import json
import os

os.environ.update({
    "ENVIRONMENT": "test",
    "GEMINI_API_KEY": "clave-de-prueba",
    "GROQ_API_KEY": "",
    "GEMINI_MODEL": "modelo-a",
    "GEMINI_MODEL_PRO": "modelo-pro",
    "GEMINI_FALLBACK_MODELS": "modelo-b",
    "GEMINI_MAX_OUTPUT_TOKENS": "65536",
    "GEMINI_THINKING_DEFAULT": "",
    "GEMINI_THINKING_COMPLEX": "",
    "GEMINI_SAFETY": "",
    "MAX_CONTINUACIONES": "3",
    "INTENTOS_POR_MODELO": "2",
    "ESPERA_REINTENTO_S": "0",
    "KEEP_ALIVE": "false",
    "APP_ACCESS_CODE": "",
    "LIMITE_POR_VENTANA": "1000",
    "LIMITE_DIA_IP": "1000",
    "LIMITE_DIA_GLOBAL": "1000",
})

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.main import app  # noqa: E402
from app.services.gemini_service import RecortadorSolape, gemini_service  # noqa: E402
from app.services.limites import limitador  # noqa: E402

PROMPT = "Redacta una acción de tutela de prueba con los datos del caso. " * 3


def _sse(*eventos) -> bytes:
    return "".join("data: " + json.dumps(e, ensure_ascii=False) + "\r\n\r\n" for e in eventos).encode("utf-8")


def _trozo(texto, motivo=None):
    candidato = {"content": {"role": "model", "parts": [{"text": texto}]}}
    if motivo:
        candidato["finishReason"] = motivo
    return {"candidates": [candidato], "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5}}


def ok(*textos, motivo="STOP"):
    eventos = [_trozo(t) for t in textos[:-1]] + [_trozo(textos[-1], motivo)]
    return lambda req: httpx.Response(200, content=_sse(*eventos), headers={"content-type": "text/event-stream"})


def falla(status):
    return lambda req: httpx.Response(status, json={"error": {"code": status, "message": "falla simulada"}})


class _StreamCortado(httpx.AsyncByteStream):
    def __init__(self, partes):
        self.partes = partes

    async def __aiter__(self):
        for parte in self.partes:
            yield parte
        raise httpx.ReadError("conexión cortada")

    async def aclose(self):
        return None


def corte(*textos):
    return lambda req: httpx.Response(
        200, stream=_StreamCortado([_sse(_trozo(t)) for t in textos]), headers={"content-type": "text/event-stream"}
    )


class GeminiFalso:
    def __init__(self, guion, modelos=("modelo-a", "modelo-b", "modelo-pro")):
        self.guion = list(guion)
        self.modelos = modelos
        self.llamadas = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            if self.modelos is None:
                return httpx.Response(500, json={"error": {"message": "lista no disponible"}})
            return httpx.Response(200, json={"models": [{"name": f"models/{m}"} for m in self.modelos]})
        self.llamadas.append({
            "url": str(request.url),
            "cuerpo": json.loads(request.content or b"{}"),
            "cabeceras": request.headers,
        })
        if not self.guion:
            return httpx.Response(500, json={"error": {"message": "sin guion"}})
        return self.guion.pop(0)(request)


@pytest.fixture
def preparar(monkeypatch):
    def _preparar(guion, modelos=("modelo-a", "modelo-b", "modelo-pro"), **entorno):
        for clave, valor in entorno.items():
            monkeypatch.setenv(clave, str(valor))
        get_settings.cache_clear()
        limitador.reiniciar()
        gemini_service.disponibles = None
        gemini_service.no_disponibles.clear()
        falso = GeminiFalso(guion, modelos)
        gemini_service.http = httpx.AsyncClient(transport=httpx.MockTransport(falso))
        return falso

    yield _preparar
    get_settings.cache_clear()


def _redactar(cliente, **extra):
    return cliente.post("/api/redactar", json={"prompt": PROMPT, **extra})


def test_flujo_normal(preparar):
    falso = preparar([ok("**PRIMERO.** Hecho uno. ", "Fin del escrito.")])
    with TestClient(app) as c:
        r = _redactar(c)
    assert r.status_code == 200
    assert r.text == "**PRIMERO.** Hecho uno. Fin del escrito."
    llamada = falso.llamadas[0]
    assert "key=" not in llamada["url"]
    assert llamada["cabeceras"].get("x-goog-api-key") == "clave-de-prueba"
    config = llamada["cuerpo"]["generationConfig"]
    assert "temperature" not in config and "topP" not in config
    assert config["maxOutputTokens"] == 65536
    assert llamada["cuerpo"]["contents"][-1]["role"] == "user"
    assert "systemInstruction" in llamada["cuerpo"]


def test_continua_si_se_corta_por_tokens(preparar):
    falso = preparar([
        ok("Primera parte del escrito que se corta en la pala", motivo="MAX_TOKENS"),
        ok("palabra siguiente y final."),
    ])
    with TestClient(app) as c:
        r = _redactar(c)
    assert r.status_code == 200
    assert r.text == "Primera parte del escrito que se corta en la palabra siguiente y final."
    roles = [x["role"] for x in falso.llamadas[1]["cuerpo"]["contents"]]
    assert roles == ["user", "model", "user"]


def test_fallo_a_mitad_continua_sin_duplicar(preparar):
    falso = preparar([
        corte("Inicio del escrito. ", "Segundo párrafo incompleto"),
        ok(" que continúa sin repetir. Fin."),
    ])
    with TestClient(app) as c:
        r = _redactar(c)
    assert r.status_code == 200
    assert r.text == "Inicio del escrito. Segundo párrafo incompleto que continúa sin repetir. Fin."
    texto_previo = falso.llamadas[1]["cuerpo"]["contents"][1]["parts"][0]["text"]
    assert texto_previo == "Inicio del escrito. Segundo párrafo incompleto"


def test_salta_modelo_que_no_existe(preparar):
    falso = preparar([falla(404), ok("Escrito del modelo b.")])
    with TestClient(app) as c:
        r = _redactar(c)
    assert r.status_code == 200
    assert r.text == "Escrito del modelo b."
    assert "modelo-a" in falso.llamadas[0]["url"]
    assert "modelo-b" in falso.llamadas[1]["url"]


def test_si_todo_falla_responde_error_http_y_no_texto(preparar):
    preparar([falla(500)] * 4)
    with TestClient(app) as c:
        r = _redactar(c)
    assert r.status_code == 503
    assert "detail" in r.json()


def test_reintenta_sin_parametros_opcionales_si_hay_400(preparar):
    falso = preparar([falla(400), ok("Texto.")], GEMINI_THINKING_DEFAULT="low")
    with TestClient(app) as c:
        r = _redactar(c)
    assert r.text == "Texto."
    assert falso.llamadas[0]["cuerpo"]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low"}
    assert "thinkingConfig" not in falso.llamadas[1]["cuerpo"]["generationConfig"]


def test_protocolo_ndjson(preparar):
    preparar([ok("Hola ", "mundo.")])
    with TestClient(app) as c:
        r = _redactar(c, protocolo="ndjson")
    eventos = [json.loads(linea) for linea in r.text.splitlines() if linea.strip()]
    tipos = [e["t"] for e in eventos]
    assert tipos[0] == "inicio" and tipos[-1] == "fin"
    assert "".join(e.get("d", "") for e in eventos if e["t"] == "delta") == "Hola mundo."
    assert eventos[-1]["truncado"] is False


def test_marca_incompleto_si_no_logra_terminar(preparar):
    guion = [ok("Parte uno. ", motivo="MAX_TOKENS")] + [
        ok(texto, motivo="MAX_TOKENS") for texto in ("Parte dos. ", "Parte tres. ", "Parte cuatro. ")
    ]
    preparar(guion)
    with TestClient(app) as c:
        r = _redactar(c)
    assert r.status_code == 200
    assert r.text.startswith("Parte uno. Parte dos. ")
    assert "[COMPLETAR: el escrito se interrumpió" in r.text


def test_codigo_de_acceso(preparar):
    preparar([ok("Texto.")], APP_ACCESS_CODE="secreto")
    with TestClient(app) as c:
        sin_codigo = _redactar(c)
        con_codigo = c.post("/api/redactar", json={"prompt": PROMPT}, headers={"X-Codigo-Acceso": "secreto"})
    assert sin_codigo.status_code == 401
    assert con_codigo.status_code == 200 and con_codigo.text == "Texto."


def test_limite_de_uso(preparar):
    preparar([ok("Uno."), ok("Dos.")], LIMITE_POR_VENTANA=1)
    with TestClient(app) as c:
        primero = _redactar(c)
        segundo = _redactar(c)
    assert primero.status_code == 200
    assert segundo.status_code == 429


def test_recortador_quita_repeticion():
    recorte = RecortadorSolape("La EPS negó la entrega del medicamento")
    assert recorte.filtrar("negó la entrega del medicamento el 9 de septiembre.") == ""
    assert recorte.vaciar() == " el 9 de septiembre."


def test_recortador_no_toca_continuacion_correcta():
    recorte = RecortadorSolape("Ordenar a la EPS que en cuarenta y ocho")
    recorte.filtrar(" (48) horas entregue el medicamento.")
    assert recorte.vaciar() == " (48) horas entregue el medicamento."


def test_analizar_estilo(preparar):
    ficha = {"encabezado": "Señor Juez", "cierre": "Atentamente,"}
    respuesta = {"candidates": [{"content": {"parts": [{"text": json.dumps(ficha, ensure_ascii=False)}]}}]}
    preparar([lambda req: httpx.Response(200, json=respuesta)])
    with TestClient(app) as c:
        r = c.post("/api/analizar-estilo", json={"muestra": "Señor Juez, respetuosamente me permito presentar. " * 5})
    assert r.status_code == 200
    assert "Encabezado: Señor Juez" in r.json()["ficha"]


def test_modelo_fuera_del_plan_se_salta_sin_reintentar(preparar):
    mensaje = (
        "You exceeded your current quota, please check your plan and billing details. For more information on "
        "this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. * Quota exceeded for metric: "
        "generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 0, model: modelo-pro"
    )
    sin_plan = lambda req: httpx.Response(429, json={"error": {"code": 429, "message": mensaje}})  # noqa: E731
    falso = preparar([sin_plan, ok("Escrito con el modelo equilibrado.")])
    with TestClient(app) as c:
        r = _redactar(c, calidad="complex")
    assert r.status_code == 200
    assert r.text == "Escrito con el modelo equilibrado."
    assert len(falso.llamadas) == 2
    assert "modelo-pro" in falso.llamadas[0]["url"] and "modelo-a" in falso.llamadas[1]["url"]
    assert "modelo-pro" in gemini_service.no_disponibles


def test_variables_viejas_en_render_usan_respaldo_vigente(preparar):
    falso = preparar(
        [falla(404), falla(404), ok("Escrito con el respaldo vigente.")],
        modelos=None,
        GEMINI_MODEL="gemini-1.5-flash",
        GEMINI_FALLBACK_MODELS="gemini-2.0-flash",
    )
    with TestClient(app) as c:
        r = _redactar(c)
    assert r.status_code == 200
    assert r.text == "Escrito con el respaldo vigente."
    assert "gemini-3.8-flash" in falso.llamadas[2]["url"]


def test_health_no_expone_la_clave(preparar):
    preparar([])
    with TestClient(app) as c:
        r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json()["gemini_configured"] is True
    assert "clave-de-prueba" not in r.text


def test_endpoint_auditor_js():
    with TestClient(app) as c:
        r = c.get("/auditor.js")
    assert r.status_code == 200
    assert "application/javascript" in r.headers["content-type"]
    assert "auditarDatosYEscrito" in r.text
