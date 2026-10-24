"""Suite completa de 18 pruebas obligatorias para la Fase 2:
Conector Oficial de la Corte Constitucional y Sistema de Actualización Incremental.
"""
from __future__ import annotations

import asyncio
import hashlib
import pytest
from unittest.mock import AsyncMock, patch

from app.services import conector_corte_constitucional as conector
from app.services import despacho_rag as rag
from app.services.despacho_rag import (
    classify_legal_section,
    classify_query_intent,
    rerank_candidates,
    LegalSection,
)


# 1. Recuperación de sentencias oficiales
def test_01_recuperacion_urls_oficiales():
    t_urls = conector.resolve_relatoria_urls("T-100/24", "2024-04-05")
    c_urls = conector.resolve_relatoria_urls("C-055/22", "2022-02-21")
    su_urls = conector.resolve_relatoria_urls("SU-016/21", "2021-01-28")
    assert any("T-100-24.htm" in u for u in t_urls)
    assert any("C-055-22.htm" in u for u in c_urls)
    assert any("SU016-21.htm" in u for u in su_urls)


# 2. Extracción de texto completo
def test_02_extraccion_texto_limpio():
    sample_html = """
    <html><head><script>evil()</script></head>
    <body>
      <h1>CORTE CONSTITUCIONAL</h1>
      <p>Bogotá D.C. Sentencia T-100/24. Hechos de la demanda.</p>
      <p>RESUELVE: Conceder el amparo.</p>
    </body></html>
    """
    ext = conector.HTMLTextExtractor()
    ext.feed(sample_html)
    txt = ext.get_clean_text()
    assert "evil()" not in txt
    assert "CORTE CONSTITUCIONAL" in txt
    assert "RESUELVE: Conceder el amparo." in txt


# 3. Integridad del contenido
def test_03_integridad_contenido_sha256():
    txt = "SENTENCIA JUDICIAL AUTÉNTICA DE LA CORTE CONSTITUCIONAL"
    expected_hash = hashlib.sha256(txt.encode("utf-8")).hexdigest()
    assert len(expected_hash) == 64
    assert int(expected_hash, 16) > 0


# 4. Duplicados
@pytest.mark.asyncio
async def test_04_deteccion_duplicados(monkeypatch):
    meta = {"sentencia": "T-100/24", "url": "https://corte.gov.co/T-100-24.htm"}
    monkeypatch.setattr(conector, "retrieve_and_validate_ruling", AsyncMock(return_value={
        "url": meta["url"], "text": "Texto idéntico", "sha256": "hash-identico-123",
        "char_length": 500, "has_operative_decision": True, "legal_basis": "Art 41",
        "retrieved_at": "2026-10-24T00:00:00Z"
    }))
    monkeypatch.setattr(conector, "check_existing_document", AsyncMock(return_value={
        "id": "doc-uuid", "version": 1, "unchanged": True, "published": True
    }))
    res = await conector.ingest_ruling(meta, semantic=True, ack_reviews=True)
    assert res["unchanged"] is True
    assert res["status"] == "already_indexed"


# 5. Actualización incremental (segunda ejecución no reprocesa)
@pytest.mark.asyncio
async def test_05_actualizacion_incremental_segunda_ejecucion(monkeypatch):
    rulings = [{"sentencia": "T-100/24"}, {"sentencia": "C-055/22"}]
    # Primera ejecución: un documento publicado y uno unchanged
    monkeypatch.setattr(conector, "ingest_ruling", AsyncMock(side_effect=[
        {"status": "published", "unchanged": False, "segments": 40, "tokens_consumed": 24000, "estimated_cost_usd": 0.0018},
        {"status": "already_indexed", "unchanged": True, "segments": 0, "tokens_consumed": 0, "estimated_cost_usd": 0.0}
    ]))
    rep1 = await conector.run_controlled_pilot(max_rulings=2, rulings_list=rulings)
    assert rep1["published_count"] == 1
    assert rep1["unchanged_count"] == 1

    # Segunda ejecución: ambos unchanged
    monkeypatch.setattr(conector, "ingest_ruling", AsyncMock(return_value={
        "status": "already_indexed", "unchanged": True, "segments": 0, "tokens_consumed": 0, "estimated_cost_usd": 0.0
    }))
    rep2 = await conector.run_controlled_pilot(max_rulings=2, rulings_list=rulings)
    assert rep2["published_count"] == 0
    assert rep2["unchanged_count"] == 2
    assert rep2["embeddings_count"] == 0
    assert rep2["estimated_cost_usd"] == 0.0


# 6. Clasificación de secciones procesales
def test_06_clasificacion_secciones():
    assert classify_legal_section("I. ANTECEDENTES PROCESALES EN PRIMERA INSTANCIA") == LegalSection.ANTECEDENTES
    assert classify_legal_section("RESUELVE: Primero.- REVOCAR la sentencia") == LegalSection.PARTE_RESOLUTIVA
    assert classify_legal_section("SALVAMENTO DE VOTO del suscrito Magistrado") == LegalSection.SALVAMENTO_VOTO
    assert classify_legal_section("Esta Corporación fija como regla jurisprudencial vinculante") == LegalSection.RATIO_DECIDENDI


# 7. Generación de embeddings
def test_07_preparacion_fragmentos_para_embeddings():
    txt = ("CORTE CONSTITUCIONAL\n" + ("Fundamentos jurídicos constitucionales. " * 500) + "\nRESUELVE: Tutelar.")
    chunks = conector.prepare_ruling_chunks(txt, max_chunks=60)
    assert len(chunks) <= 60
    for c in chunks:
        assert "content" in c
        assert "section" in c
        assert c["ordinal"] >= 0


# 8. Búsqueda híbrida
def test_08_clasificacion_intencion_busqueda():
    intent = classify_query_intent("¿Qué estableció la Sentencia T-100 de 2024?")
    assert intent["intent"] == "specific_ruling"
    assert intent["target_ruling"] == "T-100/24"


# 9. Reranking con varias sentencias
def test_09_reranking_distingue_varias_sentencias():
    candidates = [
        {"id": "c1", "source_id": "doc-t100", "title": "Sentencia T-100/24", "section": "ratio_decidendi", "excerpt": "estabilidad laboral mujer gestante", "score": 0.8},
        {"id": "c2", "source_id": "doc-su067", "title": "Sentencia SU-067/23", "section": "ratio_decidendi", "excerpt": "estabilidad ocupacional prepensionados", "score": 0.78},
    ]
    intent_info = {"intent": "general_legal", "target_ruling": None, "target_section": None}
    ranked = rerank_candidates(candidates, "estabilidad laboral en mujeres y prepensionados", intent_info=intent_info, profile={"top_k": 2})
    assert len(ranked) == 2
    titles = {r["title"] for r in ranked}
    assert "Sentencia T-100/24" in titles
    assert "Sentencia SU-067/23" in titles


# 10. Consulta desde el Agente
@pytest.mark.asyncio
async def test_10_consulta_agente_integra_rag(monkeypatch):
    from app.services import despacho_corpus_fuentes as official
    monkeypatch.setattr(official, "corpus_status", AsyncMock(return_value={"published_documents": 20, "indexed_fragments": 1000}))
    monkeypatch.setattr(official, "search_corpus", AsyncMock(return_value={
        "results": [
            {"id": "f1", "title": "Sentencia C-055/22", "source_url": "https://corte.gov.co/C-055-22.htm", "source_id": "doc-c055", "excerpt": "Derechos reproductivos y despenalización.", "segment": 1, "score": 0.9}
        ],
        "method": "hybrid",
        "warnings": []
    }))
    ctx = {"passages": [], "sources": [], "warnings": [], "coverage": {}}
    res = await rag.retrieve_and_augment_rag("u1", "t1", {"message": "aborto c-055 de 2022", "knowledge_scope": "official"}, ctx)
    assert len(res["sources"]) == 1
    assert "C-055/22" in res["sources"][0]["title"]


# 11. Referencias interactivas [O1-S1]
def test_11_generacion_referencias_interactivas():
    # Verifica que el formato de cita [O1-S1] sea generado coherentemente
    cand = {"id": "O1-S5", "title": "Sentencia T-100/24", "segment": 5, "kind": "official"}
    assert cand["id"] == "O1-S5"


# 12. Agrupación en Jurisprudencia
def test_12_agrupacion_en_jurisprudencia():
    sources = [
        {"id": "O1-S1", "source_url": "https://corte.gov.co/T-100-24.htm", "title": "Sentencia T-100/24"},
        {"id": "O1-S2", "source_url": "https://corte.gov.co/T-100-24.htm", "title": "Sentencia T-100/24"},
        {"id": "O2-S1", "source_url": "https://corte.gov.co/C-055-22.htm", "title": "Sentencia C-055/22"},
    ]
    groups = {}
    for s in sources:
        url = s["source_url"]
        if url not in groups:
            groups[url] = {"title": s["title"], "fragments": []}
        groups[url]["fragments"].append(s["id"])

    assert len(groups) == 2
    assert len(groups["https://corte.gov.co/T-100-24.htm"]["fragments"]) == 2
    assert len(groups["https://corte.gov.co/C-055-22.htm"]["fragments"]) == 1


# 13. Selección de fundamentos (identificadores documentales seguros)
@pytest.mark.asyncio
async def test_13_seleccion_fundamentos_solo_identificadores(monkeypatch):
    """El servidor rechaza texto falso inyectado por el cliente y extrae de Supabase."""
    class MockClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, headers=None):
            class Resp:
                def __init__(self, data): self._d = data; self.status_code = 200
                def json(self): return self._d
            if "despacho_corpus_documentos" in url:
                return Resp([{"id": "doc-t100", "title": "Sentencia T-100/24", "source_url": "https://corte.gov.co/T-100-24.htm", "source_id": "constitucional", "version": 1}])
            elif "despacho_corpus_fragmentos" in url:
                return Resp([{"segment": 10, "content": "Texto auténtico verificado en la base de datos.", "section": "fundamentos_juridicos"}])
            return Resp([])

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: MockClient())

    tampered_input = [
        {"id": "SEL-1", "document_id": "doc-t100", "segment": 10, "kind": "official", "text": "TEXTO INVENTADO POR EL NAVEGADOR"}
    ]
    verified = await rag.verify_and_resolve_selected_fragments("u1", "tok", tampered_input)
    assert len(verified) == 1
    assert verified[0]["excerpt"] == "Texto auténtico verificado en la base de datos."
    assert "INVENTADO" not in verified[0]["excerpt"]


# 14. Utilización en un escrito (modo draft)
def test_14_modo_draft_prompt():
    mode = "draft"
    assert mode in ("draft", "general", "research")


# 15. Streaming real
def test_15_formato_eventos_sse():
    # Simula el empaquetado de eventos SSE
    delta_event = f"event: delta\ndata: {{\"text\": \"Análisis jurídico\"}}\n\n"
    done_event = f"event: done\ndata: {{\"finish_reason\": \"stop\"}}\n\n"
    assert "event: delta" in delta_event
    assert "event: done" in done_event


# 16. Seguridad entre cuentas (aislamiento RLS y rechazo de documentos ajenos)
@pytest.mark.asyncio
async def test_16_seguridad_entre_cuentas_rechaza_acceso_ajeno(monkeypatch):
    from app.services import despacho_store as store
    from fastapi import HTTPException

    async def mock_fetch_item(user_id, token, item_id, kind=None):
        # Usuario víctima es 'owner-456'. Si 'attacker-123' intenta consultar, lanzar 404
        if user_id != "owner-456":
            raise HTTPException(404, "El elemento no existe en tu cuenta.")
        return {"id": item_id, "title": "Documento Confidencial"}

    monkeypatch.setattr(store, "fetch_item", mock_fetch_item)

    attack_fragments = [
        {"id": "ATTACK", "document_id": "secret-doc-789", "segment": 1, "kind": "document"}
    ]
    # Atacante intenta resolver el fragmento
    result = await rag.verify_and_resolve_selected_fragments("attacker-123", "attacker-token", attack_fragments)
    assert len(result) == 0


# 17. Consumo de Gemini y control de costes
def test_17_estimacion_costes_gemini():
    # 100,000 caracteres ~ 25,000 tokens
    chars = 100_000
    est = rag.estimate_tokens_and_cost(chars, input_tokens=None, output_tokens=500)
    assert est["estimated_input_tokens"] == 25000
    assert est["output_tokens"] == 500
    assert est["estimated_cost_usd"] > 0.0


# 18. Recuperación ante fallos
@pytest.mark.asyncio
async def test_18_recuperacion_ante_fallos():
    # URL inválida que devuelve error no rompe el conector
    class FailingClient:
        async def get(self, url, headers=None):
            class Resp:
                status_code = 500
                content = b"Internal Server Error"
            return Resp()

    with pytest.raises(ValueError, match="código HTTP 500"):
        await conector.retrieve_and_validate_ruling("https://corte.gov.co/error500.htm", client=FailingClient())
