"""Pruebas unitarias e integrales para el Motor RAG Jurídico Inteligente 2.0."""
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services import despacho_rag as rag
from app.services.despacho_rag import (
    LegalSection,
    classify_legal_section,
    classify_query_intent,
    rerank_candidates,
    select_intelligent_fragments,
    document_memory,
    estimate_tokens_and_cost,
    DEPTH_PROFILES,
)


def test_classify_legal_section_identifies_all_judicial_parts():
    assert classify_legal_section("CORTE CONSTITUCIONAL DE COLOMBIA\nMagistrado Ponente: Juan Carlos Cortés") == LegalSection.ENCABEZADO
    assert classify_legal_section("I. ANTECEDENTES\nTrámite procesal en primera instancia") == LegalSection.ANTECEDENTES
    assert classify_legal_section("1. Hechos probados de la demanda de tutela. La accionante manifestó que...") == LegalSection.HECHOS
    assert classify_legal_section("Planteamiento del problema jurídico: Corresponde a la Sala determinar si...") == LegalSection.PROBLEMA_JURIDICO
    assert classify_legal_section("II. CONSIDERACIONES DE LA CORTE\nCompetencia de la Sala de Revisión") == LegalSection.CONSIDERACIONES
    assert classify_legal_section("Fundamentos jurídicos y marco normativo constitucional aplicable") == LegalSection.FUNDAMENTOS_JURIDICOS
    assert classify_legal_section("Esta Corporación fija la regla jurisprudencial vinculante y subregla...") == LegalSection.RATIO_DECIDENDI
    assert classify_legal_section("RESUELVE: Primero.- TUTELAR los derechos fundamentales de la accionante") == LegalSection.PARTE_RESOLUTIVA
    assert classify_legal_section("SALVAMENTO DE VOTO del Magistrado. Me aparto de la decisión mayoritaria...") == LegalSection.SALVAMENTO_VOTO
    assert classify_legal_section("ACLARACIÓN DE VOTO: Comparto la decisión adoptada pero aclaro mi voto...") == LegalSection.ACLARACION_VOTO
    assert classify_legal_section("Texto genérico sin términos procesales específicos.") == LegalSection.SECCION_DESCONOCIDA


def test_classify_query_intent_handles_greetings_and_ruling_entities():
    # Saludo trivial
    g = classify_query_intent("Hola, buenos días")
    assert g["intent"] == "greeting"
    assert g["skip_retrieval_safe"] is True

    # Sentencia específica y parte resolutiva
    q_ruling = classify_query_intent("¿Qué resolvió la Sentencia T-100 de 2024?")
    assert q_ruling["intent"] == "specific_ruling"
    assert q_ruling["target_ruling"] == "T-100/24"
    assert q_ruling["target_section"] == "parte_resolutiva"
    assert q_ruling["suggested_depth"] == "quick"

    # Análisis exhaustivo
    q_deep = classify_query_intent("Analiza íntegramente la Sentencia C-055/22 incluyendo hechos, fundamentos y decisión")
    assert q_deep["intent"] == "exhaustive_ruling_analysis"
    assert q_deep["target_ruling"] == "C-055/22"
    assert q_deep["suggested_depth"] == "deep"
    assert q_deep["is_exhaustive"] is True

    # Investigación general de precedentes
    q_res = classify_query_intent("responsabilidad patrimonial del Estado por accidentes en vías públicas", mode="research")
    assert q_res["intent"] == "legal_research"
    assert q_res["suggested_depth"] == "balanced"


def test_depth_profiles_enforce_boundaries():
    quick = DEPTH_PROFILES["quick"]
    balanced = DEPTH_PROFILES["balanced"]
    deep = DEPTH_PROFILES["deep"]

    assert quick["max_passages"] <= 5
    assert balanced["max_passages"] <= 10
    assert deep["max_passages"] <= 18

    assert quick["max_context_chars"] < balanced["max_context_chars"] < deep["max_context_chars"]
    assert quick["candidate_limit"] < balanced["candidate_limit"] < deep["candidate_limit"]


def test_reranking_prioritizes_legal_relevance_over_distractor():
    query = "Sentencia T-100/24 amparo de maternidad"
    intent = classify_query_intent(query)
    profile = DEPTH_PROFILES["quick"]

    candidates = [
        {
            "id": "c1",
            "title": "Sentencia C-200/10",
            "excerpt": "La carretera principal y el servicio voluntario militar...",
            "score": 0.85,  # Score léxico artificialmente alto
            "section": "consideraciones",
        },
        {
            "id": "c2",
            "title": "Sentencia T-100/24",
            "excerpt": "Se concede el amparo del derecho a la maternidad durante el servicio militar voluntario. RESUELVE: Primero.- Amparar...",
            "score": 0.65,  # Score léxico algo menor, pero pertinencia jurídica exacta
            "section": "parte_resolutiva",
        }
    ]

    reranked = rerank_candidates(candidates, query, intent, profile)
    # El candidato con la Sentencia T-100/24 y amparo debe quedar en primer lugar
    assert reranked[0]["id"] == "c2"
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]
    assert reranked[0]["ranking_factors"]["ruling_match"] > 0


def test_smart_deduplication_removes_redundant_passages():
    profile = DEPTH_PROFILES["quick"]
    intent = {"target_section": None, "is_exhaustive": False}

    candidates = [
        {"id": "p1", "excerpt": "La Corte Constitucional protegió los derechos de la accionante.", "rerank_score": 0.90, "section": "parte_resolutiva"},
        {"id": "p2", "excerpt": "la corte constitucional protegió los derechos de la accionante.", "rerank_score": 0.88, "section": "parte_resolutiva"}, # Duplicado léxico
        {"id": "p3", "excerpt": "Antecedentes del caso y hechos de la tutela presentada.", "rerank_score": 0.70, "section": "hechos"},
    ]

    selected, dropped = select_intelligent_fragments(candidates, profile, intent)
    assert len(selected) == 2
    assert selected[0]["id"] == "p1"
    assert selected[1]["id"] == "p3"
    assert any(d["id"] == "p2" for d in dropped)


def test_document_memory_caches_and_invalidates():
    memory = document_memory
    user_id = "user-123"
    conv_id = "conv-abc"
    query = "Sentencia T-100/24 hechos principales"
    intent = classify_query_intent(query)
    data = {"passages": [{"id": "O1-S1", "text": "Hechos..."}], "coverage": {"scope": "official"}}

    # Guardar en memoria
    memory.store(user_id, conv_id, query, "official", "quick", [], data, intent)

    # Consulta subsiguiente dentro de la misma conversación sobre la misma sentencia
    cached = memory.get(user_id, conv_id, "Explícame los fundamentos de la Sentencia T-100/24", "official", "quick", [])
    assert cached is not None
    assert cached["passages"][0]["id"] == "O1-S1"

    # Conversación diferente debe dar None
    assert memory.get(user_id, "conv-otra", query, "official", "quick", []) is None

    # Invalidación manual
    memory.invalidate(user_id, conv_id)
    assert memory.get(user_id, conv_id, query, "official", "quick", []) is None


def test_cost_estimator_computes_usd():
    est = estimate_tokens_and_cost(prompt_chars=4000, input_tokens=1000, output_tokens=500, model="gemini-3.6-flash")
    assert est["total_tokens"] == 1500
    assert est["is_token_count_estimated"] is False
    assert est["estimated_cost_usd"] > 0
    assert est["cost_model"] == "gemini-3.6-flash"


@pytest.mark.asyncio
async def test_retrieve_and_augment_rag_official_scope(monkeypatch):
    from app.services import despacho_corpus_fuentes as official

    monkeypatch.setattr(official, "corpus_status", AsyncMock(return_value={"published_documents": 1, "indexed_fragments": 41}))
    fake_results = [
        {"title": "Sentencia T-100/24", "excerpt": "RESUELVE: Primero.- Amparar los derechos fundamentales.",
         "source_url": "https://corte.gov.co/T-100-24.htm", "source_id": "corte_constitucional",
         "segment": 2, "score": 0.75, "method": "hybrid", "decision_date": "2024-04-05", "document_version": 1}
    ]
    monkeypatch.setattr(official, "search_corpus", AsyncMock(return_value={"results": fake_results, "method": "hybrid", "warnings": []}))

    context = {"passages": [], "sources": [], "warnings": [], "coverage": {}}
    request = {
        "message": "¿Qué resolvió la Sentencia T-100/24?",
        "knowledge_scope": "official",
        "depth": "quick"
    }

    result = await rag.retrieve_and_augment_rag("user-1", "token-1", request, context)
    assert len(result["passages"]) == 1
    assert result["passages"][0]["id"] == "O1-S2"
    assert result["passages"][0]["section"] == "parte_resolutiva"
    assert result["coverage"]["scope"] == "official"
    assert result["coverage"]["depth"] == "quick"
    assert result["coverage"]["detected_intent"] == "specific_ruling"
    assert result["coverage"]["official_documents"] == 1
