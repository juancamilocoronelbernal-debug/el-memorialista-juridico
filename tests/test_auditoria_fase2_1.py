"""Pruebas de auditoría de integridad, calidad y confiabilidad del Corpus Jurídico Oficial (Fase 2.1)."""
import pytest
from unittest.mock import AsyncMock

from app.services import conector_corte_constitucional as conector
from app.services import despacho_rag as rag


def test_all_20_pilot_rulings_have_verified_official_metadata():
    """Verifica que las 20 sentencias piloto tengan sus metadatos oficiales auditados y completos."""
    rulings = conector.PILOT_CURATED_RULINGS
    assert len(rulings) == 20

    by_id = {r["sentencia"]: r for r in rulings}

    # Verificaciones específicas de las sentencias auditadas en Fase 2.1
    assert by_id["T-100/24"]["magistrado"] == "Juan Carlos Cortés González"
    assert "embarazada" in by_id["T-100/24"]["materia"].lower()
    assert "servicio militar" in by_id["T-100/24"]["materia"].lower()

    assert by_id["SU-067/23"]["magistrado"] == "Paola Andrea Meneses Mosquera"
    assert by_id["SU-067/23"]["fecha"] == "2023-03-16"
    assert "trans" in by_id["SU-067/23"]["materia"].lower()
    assert "prepensionados" not in by_id["SU-067/23"]["materia"].lower()

    assert by_id["SU-016/21"]["magistrado"] == "Gloria Stella Ortiz Delgado"
    assert by_id["SU-016/21"]["fecha"] == "2021-01-21"
    assert "desalojo" in by_id["SU-016/21"]["materia"].lower() or "vivienda digna" in by_id["SU-016/21"]["materia"].lower()

    assert by_id["C-395/21"]["magistrado"] == "Jorge Enrique Ibáñez Najar"
    assert "2055 de 2020" in by_id["C-395/21"]["materia"]
    assert "personas mayores" in by_id["C-395/21"]["materia"].lower()
    assert "código de policía" not in by_id["C-395/21"]["materia"].lower()

    assert by_id["T-028/23"]["magistrado"] == "José Fernando Reyes Cuartas"
    assert "perspectiva de género" in by_id["T-028/23"]["materia"].lower()

    assert by_id["T-123/24"]["magistrado"] == "Natalia Ángel Cabo"
    assert "ambientales" in by_id["T-123/24"]["materia"].lower()

    assert by_id["T-030/20"]["magistrado"] == "Diana Constanza Fajardo Rivera"
    assert "internet" in by_id["T-030/20"]["materia"].lower()

    assert by_id["T-307/26"]["magistrado"] == "Natalia Ángel Cabo"
    assert "migrante" in by_id["T-307/26"]["materia"].lower()

    assert by_id["T-012/92"]["magistrado"] == "José Gregorio Hernández Galindo"
    assert "petición" in by_id["T-012/92"]["materia"].lower()

    assert by_id["SU-111/20"]["magistrado"] == "Gloria Stella Ortiz Delgado"
    assert "afrodescendiente" in by_id["SU-111/20"]["materia"].lower()

    assert by_id["C-266/26"]["magistrado"] == "Jorge Enrique Ibáñez Najar"
    assert "venezuela" in by_id["C-266/26"]["materia"].lower()

    assert by_id["T-416/23"]["magistrado"] == "Juan Carlos Cortés González"
    assert "salud mental" in by_id["T-416/23"]["materia"].lower()

    assert by_id["SU-388/21"]["magistrado"] == "Alejandro Linares Cantillo"
    assert "indagatoria" in by_id["SU-388/21"]["materia"].lower()

    for r in rulings:
        for required_key in (
            "sentencia", "anio", "fecha", "decision_date", "tipo",
            "corporacion", "sala", "magistrado", "expediente",
            "proceso", "url", "materia", "problema_juridico", "decision"
        ):
            assert r.get(required_key), f"Falta {required_key} en {r.get('sentencia')}"


def test_prepare_ruling_chunks_preserves_100_percent_without_60_chunk_truncation():
    """Verifica que por defecto prepare_ruling_chunks no trunque en 60 fragmentos."""
    # Generar un texto de ~200.000 caracteres (~91 fragmentos)
    full_text = (
        "REPÚBLICA DE COLOMBIA\nCORTE CONSTITUCIONAL\nSentencia C-055 de 2022\n"
        "Referencia: Expediente D-13.956\nMagistrados Ponentes: Antonio José Lizarazo Ocampo y Alberto Rojas Ríos\n\n"
        "I. ANTECEDENTES\n"
        + ("Relato detallado de la demanda ciudadana y las intervenciones recibidas en el proceso. " * 400)
        + "\n\nII. CONSIDERACIONES DE LA CORTE CONSTITUCIONAL\n"
        "Problema jurídico: Le corresponde a la Sala Plena determinar si la norma demandada vulnera la Constitución.\n"
        + ("Análisis constitucional y fundamentos jurídicos de la Sala Plena sobre derechos fundamentales. " * 1800)
        + "\n\nIII. DECISIÓN\nEn mérito de lo expuesto, la Sala Plena de la Corte Constitucional,\n"
        "RESUELVE\nPrimero.- Declarar EXEQUIBLE condicionadamente la disposición acusada.\n"
        "Notifíquese, comuníquese y cúmplase.\n\n"
        "SALVAMENTO DE VOTO DEL MAGISTRADO JORGE ENRIQUE IBÁÑEZ NAJAR\n"
        + ("Con el acostumbrado respeto por las decisiones de la mayoría, me aparto de la decisión adoptada. " * 200)
    )

    chunks = conector.prepare_ruling_chunks(full_text)
    assert len(chunks) > 80  # Supera ampliamente el antiguo límite de 60
    assert chunks[0]["section"] == "encabezado"
    assert any(c["section"] == "antecedentes" for c in chunks)
    assert any(c["section"] in ("consideraciones", "fundamentos_juridicos", "problema_juridico") for c in chunks)
    assert any(c["section"] == "parte_resolutiva" for c in chunks)
    assert chunks[-1]["section"] == "salvamento_voto"


def test_section_classifier_does_not_confuse_majority_vote_with_salvamento_or_aclaracion():
    """Verifica que notas de relatoría o firmas al pie del RESUELVE no etiqueten el fallo mayoritario como voto disidente."""
    # Caso 1: Nota de relatoría sobre reserva de aclaración de voto (como en SU-388/21)
    relatoria_note = (
        "[Nota de Relatoría: La magistrada Paola Andrea Meneses Mosquera comunicó a la Secretaría General "
        "su decisión de no presentar la aclaración de voto que había anunciado en relación con esta providencia.]\n"
        "I. ANTECEDENTES\nHechos de la demanda de tutela interpuesta por el accionante."
    )
    sec1 = rag.classify_legal_section(relatoria_note)
    assert sec1 != rag.LegalSection.ACLARACION_VOTO
    assert sec1 in (rag.LegalSection.ANTECEDENTES, rag.LegalSection.HECHOS)

    # Caso 2: Parte resolutiva con firma "Con salvamento de voto" al pie (como en T-063/15)
    resuelve_with_sig = (
        "III. DECISIÓN\nEn mérito de lo expuesto, la Sala Primera de Revisión de la Corte Constitucional,\n"
        "R E S U E L V E\n"
        "Primero.- REVOCAR la sentencia de instancia y TUTELAR los derechos fundamentales.\n"
        "Notifíquese, comuníquese y cúmplase.\n"
        "MARÍA VICTORIA CALLE CORREA\nMagistrada\n"
        "LUIS GUILLERMO GUERRERO PÉREZ\nMagistrado\nCon salvamento de voto"
    )
    sec2 = rag.classify_legal_section(resuelve_with_sig)
    assert sec2 == rag.LegalSection.PARTE_RESOLUTIVA


@pytest.mark.asyncio
async def test_ingest_ruling_multi_batch_incremental_publication(monkeypatch):
    """Verifica que sentencias con más de 50 fragmentos se publiquen incrementalmente sin perder fragmentos."""
    long_text = (
        "CORTE CONSTITUCIONAL DE COLOMBIA\nSENTENCIA C-141 DE 2010\n"
        "I. ANTECEDENTES\n" + ("Antecedentes procesales del control automático. " * 500)
        + "\nII. CONSIDERACIONES\n" + ("Fundamentos constitucionales sobre límites al poder de reforma. " * 2500)
        + "\nIII. DECISIÓN\nRESUELVE\nDeclarar INEXEQUIBLE la Ley 1354 de 2009.\nNotifíquese y cúmplase."
    )
    mock_extracted = {
        "url": "https://www.corteconstitucional.gov.co/relatoria/2010/C-141-10.htm",
        "raw_html_bytes": len(long_text),
        "text": long_text,
        "char_length": len(long_text),
        "sha256": "1" * 64,
        "has_operative_decision": True,
        "retrieved_at": "2026-10-24T22:00:00Z",
        "legal_basis": "Art. 41 Ley 23 de 1982",
    }
    monkeypatch.setattr(conector, "retrieve_and_validate_ruling", AsyncMock(return_value=mock_extracted))
    monkeypatch.setattr(conector, "check_existing_document", AsyncMock(return_value=None))

    rpc_calls = []

    async def fake_db_request(method, path, token, *, json=None, service=False):
        rpc_calls.append((method, path, json))
        if path == "rpc/despacho_publicar_documento_corpus":
            return {
                "id": "doc-c141",
                "version": 1,
                "unchanged": False,
                "segments": len(json["p_chunks"]),
                "finalized": json.get("p_finalize", True),
            }
        if path == "rpc/despacho_anexar_fragmentos_corpus":
            return {
                "id": json["p_document_id"],
                "version": json["p_version"],
                "appended": len(json["p_chunks"]),
                "finalized": json.get("p_finalize", True),
            }
        return {}

    monkeypatch.setattr(conector.store, "db_request", fake_db_request)
    res = await conector.ingest_ruling({"sentencia": "C-141/10"}, semantic=False, ack_reviews=True)

    assert res["status"] == "published"
    assert res["integrity_status"] == "complete"
    assert res["coverage_pct"] == 100.0
    assert res["segments"] > 50

    pub_calls = [c for c in rpc_calls if c[1] == "rpc/despacho_publicar_documento_corpus"]
    annex_calls = [c for c in rpc_calls if c[1] == "rpc/despacho_anexar_fragmentos_corpus"]
    assert len(pub_calls) == 1
    assert pub_calls[0][2]["p_finalize"] is False
    assert len(annex_calls) >= 1
    assert annex_calls[-1][2]["p_finalize"] is True

    total_sent_chunks = len(pub_calls[0][2]["p_chunks"]) + sum(len(c[2]["p_chunks"]) for c in annex_calls)
    assert total_sent_chunks == res["segments"]


@pytest.mark.asyncio
async def test_withdraw_and_restore_ruling_workflow_status(monkeypatch):
    """Verifica el retiro reversible ('withdrawn') y cambio de estado de ciclo de vida documental."""
    recorded = []

    async def fake_db_request(method, path, token, *, json=None, service=False):
        recorded.append((method, path, json))
        return {
            "id": json["p_document_id"],
            "workflow_status": json["p_workflow_status"],
            "published": False if json["p_workflow_status"] == "withdrawn" else bool(json.get("p_published")),
        }

    monkeypatch.setattr(conector.store, "db_request", fake_db_request)

    w_res = await conector.withdraw_ruling_from_corpus("doc-123", "Inconsistencia detectada en revisión")
    assert w_res["workflow_status"] == "withdrawn"
    assert w_res["published"] is False

    r_res = await conector.change_document_workflow_status("doc-123", "published", published=True, reason="Verificado")
    assert r_res["workflow_status"] == "published"
    assert r_res["published"] is True


def test_negative_query_semantic_fallback_blocks_single_generic_word_false_positive():
    """Verifica que una consulta negativa con solo 1 palabra genérica coincidente en fallback semántico no supere el umbral."""
    query = "libertad de expresión en redes sociales y difamación digital"
    intent_info = rag.classify_query_intent(query, mode="research")
    profile = rag.DEPTH_PROFILES["balanced"]

    candidates = [
        {
            "id": "frag-1",
            "title": "Sentencia SU-067/23 - Corte Constitucional",
            "source_id": "constitucional",
            "section": "consideraciones",
            "method": "semantic",  # Sin coincidencia FTS, solo similitud vectorial débil
            "score": 0.48,
            "excerpt": "La Corte ha señalado que la libertad humana y el libre desarrollo de la personalidad protegen la identidad de género.",
        }
    ]
    ranked = rag.rerank_candidates(candidates, query, intent_info, profile)
    selected, dropped = rag.select_intelligent_fragments(ranked, profile, intent_info)
    assert len(selected) == 0
    assert len(dropped) == 1
