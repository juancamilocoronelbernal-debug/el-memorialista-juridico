"""Pruebas unitarias para el marco de evaluación y benchmarking (scripts/evaluar.py)."""

import os
import pytest
from app.services.prompt import listar_tipos
from scripts.evaluar import (
    cargar_casos,
    verificar_expectativas_caso,
    calcular_semaforo,
    generar_reporte_html,
    evaluar_caso,
)


def test_catalogo_casos_completo():
    """Verifica que existan 3 casos en tests/casos/ por cada tipo del catálogo."""
    tipos = listar_tipos(incluir_guia=False)
    assert len(tipos) >= 26, f"Se esperaban al menos 26 tipos en el catálogo, hay {len(tipos)}"

    casos = cargar_casos()
    assert len(casos) == len(tipos) * 3, f"Se esperaban {len(tipos) * 3} casos en total (3 por tipo), hay {len(casos)}"

    conteo_por_tipo = {}
    for c in casos:
        t = c["tipo"]
        conteo_por_tipo[t] = conteo_por_tipo.get(t, 0) + 1

        # Validar estructura requerida de cada caso
        assert "id" in c, f"Falta 'id' en caso: {c}"
        assert "tipo" in c, f"Falta 'tipo' en caso: {c}"
        assert "datos" in c, f"Faltan 'datos' en caso: {c}"
        assert isinstance(c["datos"], dict), f"'datos' debe ser dict en caso: {c}"
        assert "expectativas" in c, f"Faltan 'expectativas' en caso: {c}"

        exp = c["expectativas"]
        assert "secciones_obligatorias" in exp, f"Faltan 'secciones_obligatorias' en caso: {c['id']}"
        assert "entidades_deben_aparecer" in exp, f"Faltan 'entidades_deben_aparecer' en caso: {c['id']}"
        assert "entidades_no_deben_aparecer" in exp, f"Faltan 'entidades_no_deben_aparecer' en caso: {c['id']}"
        assert "longitud_minima" in exp, f"Falta 'longitud_minima' en caso: {c['id']}"
        assert "longitud_maxima" in exp, f"Falta 'longitud_maxima' en caso: {c['id']}"
        assert exp["longitud_minima"] < exp["longitud_maxima"]

    for t in tipos:
        tid = t["id"]
        assert tid in conteo_por_tipo, f"Tipo '{tid}' no tiene casos en tests/casos/"
        assert conteo_por_tipo[tid] == 3, f"Tipo '{tid}' debe tener exactamente 3 casos, tiene {conteo_por_tipo[tid]}"


def test_verificar_expectativas_exitoso():
    """Verifica que el comprobador de expectativas apruebe un texto conforme."""
    texto = """Bogotá, 21 de octubre de 2026
SEÑOR JUEZ CIVIL
MARÍA LÓPEZ formula tutela contra NUEVA EPS.
HECHOS:
1. Negación de Pembrolizumab.
PRETENSIONES:
1. Entrega del medicamento.
FUNDAMENTOS:
Sentencia T-760 de 2008.
PRUEBAS:
Fórmula médica.
NOTIFICACIONES:
Carrera 7 # 32-16."""

    expectativas = {
        "secciones_obligatorias": ["HECHOS", "PRETENSIONES", "FUNDAMENTOS", "PRUEBAS", "NOTIFICACIONES"],
        "entidades_deben_aparecer": ["MARÍA LÓPEZ", "NUEVA EPS", "Pembrolizumab"],
        "entidades_no_deben_aparecer": ["Sanitas", "Sura", "Bancolombia"],
        "longitud_minima": 100,
        "longitud_maxima": 5000,
    }

    res = verificar_expectativas_caso(texto, expectativas)
    assert len(res["secciones_faltantes"]) == 0
    assert len(res["entidades_faltantes"]) == 0
    assert len(res["entidades_prohibidas_detectadas"]) == 0
    assert res["longitud_cumple"] is True


def test_detector_alucinaciones_entidades_prohibidas():
    """Verifica que se detecten entidades prohibidas (detector de alucinaciones del modelo)."""
    texto = """Bogotá, 21 de octubre de 2026.
Se interpone demanda contra NUEVA EPS y se cita como referencia a Sanitas S.A. y Bancolombia."""

    expectativas = {
        "secciones_obligatorias": [],
        "entidades_deben_aparecer": ["NUEVA EPS"],
        "entidades_no_deben_aparecer": ["Sanitas", "Bancolombia"],
        "longitud_minima": 50,
        "longitud_maxima": 1000,
    }

    res = verificar_expectativas_caso(texto, expectativas)
    assert "Sanitas" in res["entidades_prohibidas_detectadas"]
    assert "Bancolombia" in res["entidades_prohibidas_detectadas"]


def test_calculo_semaforo_rojo_amarillo_verde():
    """Verifica las reglas de clasificación del semáforo."""
    # 1. Caso Rojo por citas inexistentes
    sem, motivos = calcular_semaforo(
        citas_resumen={"rojo": 1, "amarillo": 0, "verde": 2},
        req_resumen={"criticos_pendientes": 0, "cumple": 5, "no_cumple": 0},
        audit_resumen={"discrepancias": [], "invenciones": [], "omisiones": []},
        exp_resumen={"secciones_faltantes": [], "entidades_prohibidas_detectadas": [], "longitud_cumple": True},
    )
    assert sem == "rojo"
    assert any("cita(s) inexistente(s)" in m for m in motivos)

    # 2. Caso Rojo por requisitos críticos no cumplidos
    sem, motivos = calcular_semaforo(
        citas_resumen={"rojo": 0, "amarillo": 0, "verde": 2},
        req_resumen={"criticos_pendientes": 2, "cumple": 3, "no_cumple": 2},
        audit_resumen={"discrepancias": [], "invenciones": [], "omisiones": []},
        exp_resumen={"secciones_faltantes": [], "entidades_prohibidas_detectadas": [], "longitud_cumple": True},
    )
    assert sem == "rojo"
    assert any("crítico(s) no cumplido(s)" in m for m in motivos)

    # 3. Caso Amarillo por citas sin verificar o invenciones menores
    sem, motivos = calcular_semaforo(
        citas_resumen={"rojo": 0, "amarillo": 1, "verde": 2},
        req_resumen={"criticos_pendientes": 0, "cumple": 5, "no_cumple": 0},
        audit_resumen={"discrepancias": [], "invenciones": [{"tipo": "correo", "valor": "otro@email.com"}], "omisiones": []},
        exp_resumen={"secciones_faltantes": [], "entidades_prohibidas_detectadas": [], "longitud_cumple": True},
    )
    assert sem == "amarillo"

    # 4. Caso Verde cuando todo está en orden
    sem, motivos = calcular_semaforo(
        citas_resumen={"rojo": 0, "amarillo": 0, "verde": 2},
        req_resumen={"criticos_pendientes": 0, "cumple": 5, "no_cumple": 0},
        audit_resumen={"discrepancias": [], "invenciones": [], "omisiones": []},
        exp_resumen={"secciones_faltantes": [], "entidades_prohibidas_detectadas": [], "longitud_cumple": True},
    )
    assert sem == "verde"


def test_generador_reporte_html():
    """Verifica que el reporte HTML contenga los elementos visuales y métricas clave."""
    resultados = [
        {
            "id": "tutela_01_salud_medicamentos",
            "tipo": "tutela",
            "descripcion": "Tutela por medicamento oncológico",
            "semaforo": "verde",
            "motivos": ["Cumple plenamente"],
            "tiempo_segundos": 1.2,
            "tokens": {"entrada": 400, "salida": 1200, "total": 1600},
            "texto": "Texto de prueba del memorial...",
            "citas": {"total": 1, "resumen": {"verde": 1, "amarillo": 0, "rojo": 0}, "lista": []},
            "requisitos": {"total": 6, "resumen": {"cumple": 6, "no_cumple": 0, "criticos_pendientes": 0}, "lista": []},
            "auditoria": {"invenciones": [], "omisiones": [], "discrepancias": [], "total_alertas": 0},
            "expectativas": {"secciones_faltantes": [], "entidades_faltantes": [], "entidades_prohibidas_detectadas": [], "longitud_cumple": True, "longitud_caracteres": 1500, "longitud_minima": 1000, "longitud_maxima": 10000},
        }
    ]

    totales = {
        "total_casos": 1,
        "total_verdes": 1,
        "total_amarillos": 0,
        "total_rojos": 0,
        "porcentaje_verdes": 100.0,
        "total_citas_inexistentes": 0,
        "total_datos_inventados": 0,
        "total_requisitos_faltantes": 0,
        "tiempo_total_s": 1.2,
        "tiempo_promedio_s": 1.2,
        "tokens_total": 1600,
        "tokens_promedio": 1600,
    }

    metadata = {"fecha": "21/10/2026 22:00:00", "modelo": "Gemini 2.5 Pro", "entorno": "Pruebas"}

    html = generar_reporte_html(resultados, totales, metadata)
    assert "<!DOCTYPE html>" in html
    assert "El Memorialista · Reporte de Evaluación de Modelos y Prompts" in html
    assert "Política Obligatoria de Despliegue" in html
    assert "Semáforos Verdes (Aprobados)" in html
    assert "Citas Inexistentes (Rojas)" in html
    assert "Datos Inventados (Fidelidad)" in html
    assert "Requisitos Faltantes" in html
    assert "tutela_01_salud_medicamentos" in html


@pytest.mark.asyncio
async def test_evaluar_caso_mock_tutela():
    """Ejecuta una evaluación mock end-to-end de un caso de tutela."""
    casos = cargar_casos(filtro_caso="tutela_02_debido_proceso_universidad")
    assert len(casos) == 1
    res = await evaluar_caso(casos[0], mock=True)

    assert res["id"] == "tutela_02_debido_proceso_universidad"
    assert res["tipo"] == "tutela"
    assert res["semaforo"] in ("verde", "amarillo")  # No debe ser rojo
    assert res["citas"]["resumen"]["rojo"] == 0
    assert len(res["auditoria"]["discrepancias"]) == 0
    assert len(res["expectativas"]["entidades_prohibidas_detectadas"]) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("servidor", [None, "https://memorialista.example.test"])
async def test_generacion_real_exige_token_antes_de_crear_cliente(monkeypatch, servidor):
    from scripts import evaluar
    import httpx
    import fastapi.testclient
    monkeypatch.delenv("MEMORIALISTA_ACCESS_TOKEN", raising=False)
    def prohibido(*args, **kwargs):
        pytest.fail("No se debe iniciar un cliente sin un token explícito.")
    monkeypatch.setattr(httpx, "AsyncClient", prohibido)
    monkeypatch.setattr(fastapi.testclient, "TestClient", prohibido)
    with pytest.raises(RuntimeError, match="Falta MEMORIALISTA_ACCESS_TOKEN"):
        await evaluar.generar_con_cliente({"tipo": "peticion", "datos": {}}, servidor_url=servidor)


@pytest.mark.asyncio
async def test_cli_real_falla_antes_de_cargar_casos_si_falta_token(monkeypatch, capsys, tmp_path):
    from scripts import evaluar
    monkeypatch.delenv("MEMORIALISTA_ACCESS_TOKEN", raising=False)
    salida = tmp_path / "no-debe-existir.html"
    monkeypatch.setattr("sys.argv", ["evaluar.py", "--limite", "1", "--salida", str(salida)])
    def prohibido(**kwargs):
        pytest.fail("El CLI debe fallar antes de cargar y procesar los casos.")
    monkeypatch.setattr(evaluar, "cargar_casos", prohibido)
    assert await evaluar.main_async() == 2
    assert "MEMORIALISTA_ACCESS_TOKEN" in capsys.readouterr().err
    assert not salida.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("servidor", [None, "https://memorialista.example.test"])
async def test_generacion_envia_bearer_en_cliente_local_y_remoto(monkeypatch, capsys, servidor):
    """Se sustituye solo el transporte del script; no el validador de producción."""
    from scripts import evaluar
    import fastapi.testclient
    import httpx
    import json
    token = "access-token-exclusivo-de-esta-prueba"
    monkeypatch.setenv("MEMORIALISTA_ACCESS_TOKEN", token)
    llamadas = []
    eventos = [json.dumps({"t": "delta", "d": "Documento simulado por el transporte de prueba."}),
               json.dumps({"t": "fin", "modelo": "provider-test", "tokens": {"entrada": 2, "salida": 3, "total": 5}})]
    class Respuesta:
        status_code = 200
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        def __enter__(self): return self
        def __exit__(self, *args): return False
        async def aiter_lines(self):
            for line in eventos: yield line
        def iter_lines(self): return iter(eventos)
    class Cliente:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def stream(self, metodo, url, **kwargs):
            llamadas.append((metodo, url, kwargs))
            return Respuesta()
    monkeypatch.setattr(httpx, "AsyncClient", Cliente)
    monkeypatch.setattr(fastapi.testclient, "TestClient", Cliente)
    texto, _, tokens, modelo = await evaluar.generar_con_cliente({"tipo": "peticion", "datos": {}}, servidor_url=servidor)
    assert texto == "Documento simulado por el transporte de prueba."
    assert tokens["total"] == 5 and modelo == "provider-test"
    assert llamadas[0][0] == "POST"
    assert llamadas[0][1] == (servidor or "") + "/api/redactar"
    assert llamadas[0][2]["headers"]["Authorization"] == "Bearer " + token
    output = capsys.readouterr()
    assert token not in output.out + output.err


@pytest.mark.asyncio
async def test_mock_no_necesita_token_y_no_invoca_ia_ni_fuentes_remotas(monkeypatch):
    from scripts import evaluar
    import httpx
    from unittest.mock import AsyncMock
    monkeypatch.delenv("MEMORIALISTA_ACCESS_TOKEN", raising=False)
    no_red = AsyncMock(side_effect=AssertionError("Una simulación no puede acceder a red ni IA."))
    monkeypatch.setattr(evaluar, "generar_con_cliente", no_red)
    monkeypatch.setattr(evaluar, "verificar_citas", no_red)
    monkeypatch.setattr(evaluar, "revisar_requisitos", no_red)
    def cliente_prohibido(*args, **kwargs):
        pytest.fail("--mock no debe abrir clientes HTTP.")
    monkeypatch.setattr(httpx, "AsyncClient", cliente_prohibido)
    caso = evaluar.cargar_casos(filtro_caso="tutela_02_debido_proceso_universidad")[0]
    resultado = await evaluar.evaluar_caso(caso, mock=True)
    assert resultado["simulacion"] is True
    assert resultado["texto"]
    assert resultado["error_generacion"] is None
    assert resultado["citas"]["resumen"]["verde"] == 0
    assert all(cita["estado"] == "sin_verificar" for cita in resultado["citas"]["lista"])
    no_red.assert_not_awaited()


@pytest.mark.asyncio
async def test_cli_mock_identifica_reporte_como_simulacion_sin_habilitar_despliegue(monkeypatch, capsys, tmp_path):
    from scripts import evaluar
    monkeypatch.delenv("MEMORIALISTA_ACCESS_TOKEN", raising=False)
    salida = tmp_path / "simulacion.html"
    monkeypatch.setattr("sys.argv", ["evaluar.py", "--mock", "--caso", "tutela_02_debido_proceso_universidad", "--salida", str(salida)])
    assert await evaluar.main_async() == 0
    contenido = salida.read_text(encoding="utf-8")
    assert "SIMULACIÓN LOCAL" in contenido
    assert "no autoriza un despliegue" in contenido
    output = capsys.readouterr().out
    assert "SIMULACIÓN LOCAL COMPLETADA" in output
    assert "APTO PARA DESPLIEGUE" not in output
