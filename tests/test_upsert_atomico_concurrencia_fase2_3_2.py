# -*- coding: utf-8 -*-
"""
Pruebas obligatorias de concurrencia, idempotencia y atomicidad (Fase 2.3.2)
Verifica que el nuevo mecanismo de UPSERT en PostgreSQL y normalización canónica
garantice unicidad, prevenga condiciones de carrera y mantenga consistencia
entre despacho_conector_descubrimientos y despacho_corpus_documentos.
"""

import asyncio
import hashlib
import json
import uuid
import pytest
import pytest_asyncio
from app.config import get_settings
from app.services import despacho_store as store
from app.services.conector_corte_constitucional import canonicalize_sentencia

TEST_SENTENCIA = "T-888/26"
TEST_CANON = "constitucional:T-888-2026"
TEST_URL = "https://www.corteconstitucional.gov.co/relatoria/2026/T-888-26.htm"
TEST_HASH = hashlib.sha256(b"Texto oficial de prueba de providencia T-888/26").hexdigest()

TEST_CHUNKS = [
    {
        "ordinal": 0,
        "segment": 1,
        "content": "Fragmento oficial de prueba de providencia T-888/26 sobre derecho a la salud.",
        "section": "resuelve",
        "embedding": [0.01] * 768,
        "embedding_model": "gemini-embedding-001",
    }
]


async def _clean_all_test_canons():
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        return
    for c in ["constitucional:T-888-2026", "constitucional:T-999-2026"]:
        docs = await store.db_request(
            "GET",
            f"despacho_corpus_documentos?identificador_canonico=eq.{c}&select=id",
            key,
            service=True,
        ) or []
        for d in docs:
            await store.db_request("DELETE", f"despacho_corpus_documentos?id=eq.{d['id']}", key, service=True)
        await store.db_request(
            "DELETE",
            f"despacho_conector_descubrimientos?identificador_canonico=eq.{c}",
            key,
            service=True,
        )


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data():
    """Limpia los registros de prueba antes y después de cada prueba de concurrencia."""
    await _clean_all_test_canons()
    try:
        yield
    finally:
        await _clean_all_test_canons()


# ---------------------------------------------------------------------------
# PRUEBA A — INSERCIÓN ÚNICA
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_prueba_a_insercion_unica():
    """Intenta incorporar por primera vez una providencia de prueba.
    Comprueba que se crea exactamente un registro en ambas tablas."""
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        pytest.skip("Requiere SUPABASE_SERVICE_ROLE_KEY")

    # Ingesta inicial
    res = await store.db_request(
        "POST",
        "rpc/despacho_upsert_providencia_corpus_atomico",
        key,
        service=True,
        json={
            "p_source_id": "constitucional",
            "p_source_url": TEST_URL,
            "p_title": "Sentencia T-888/26 - Corte Constitucional",
            "p_sentencia": TEST_SENTENCIA,
            "p_hash": TEST_HASH,
            "p_chunks": TEST_CHUNKS,
            "p_metadata": {"magistrado": "Dra. Magistrada Test", "tema": "Salud"},
            "p_workflow_status": "technically_validated",
            "p_published": False,
            "p_finalize": False,
        },
    )

    assert isinstance(res, dict)
    assert res.get("operation") == "created"
    assert res.get("unchanged") is False
    assert res.get("identificador_canonico") == TEST_CANON
    doc_id = res.get("id")
    assert doc_id is not None

    # Verificar que existe exactamente un registro en despacho_corpus_documentos
    docs = await store.db_request(
        "GET",
        f"despacho_corpus_documentos?identificador_canonico=eq.{TEST_CANON}&select=id,version,published",
        key,
        service=True,
    )
    assert len(docs) == 1
    assert docs[0]["id"] == doc_id
    assert docs[0]["version"] == 1

    # Verificar que existe exactamente un registro sincronizado en despacho_conector_descubrimientos
    desc = await store.db_request(
        "GET",
        f"despacho_conector_descubrimientos?identificador_canonico=eq.{TEST_CANON}&select=id,document_id,source_status",
        key,
        service=True,
    )
    assert len(desc) == 1
    assert desc[0]["document_id"] == doc_id
    assert desc[0]["source_status"] == "technically_validated"


# ---------------------------------------------------------------------------
# PRUEBA B — REPETICIÓN (IDEMPOTENCIA)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_prueba_b_repeticion_idempotencia():
    """Ejecuta nuevamente la misma operación con variantes tipográficas.
    Comprueba que no aparecen duplicados y que la operación es estrictamente idempotente."""
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        pytest.skip("Requiere SUPABASE_SERVICE_ROLE_KEY")

    # Inserción inicial con formato estándar
    res1 = await store.db_request(
        "POST",
        "rpc/despacho_upsert_providencia_corpus_atomico",
        key,
        service=True,
        json={
            "p_source_id": "constitucional",
            "p_source_url": TEST_URL,
            "p_title": "Sentencia T-888/26 - Corte Constitucional",
            "p_sentencia": "T-888/26",
            "p_hash": TEST_HASH,
            "p_chunks": TEST_CHUNKS,
            "p_metadata": {"magistrado": "Dra. Magistrada Test", "tema": "Salud"},
            "p_workflow_status": "technically_validated",
            "p_published": False,
            "p_finalize": False,
        },
    )
    doc_id = res1["id"]

    # Segunda ejecución con variante de formato: 'T-888-26'
    res2 = await store.db_request(
        "POST",
        "rpc/despacho_upsert_providencia_corpus_atomico",
        key,
        service=True,
        json={
            "p_source_id": "constitucional",
            "p_source_url": TEST_URL,
            "p_title": "Sentencia T-888-26 - Corte Constitucional",
            "p_sentencia": "T-888-26",
            "p_hash": TEST_HASH,
            "p_chunks": TEST_CHUNKS,
            "p_metadata": {"magistrado": "Dra. Magistrada Test", "tema": "Salud"},
            "p_workflow_status": "technically_validated",
            "p_published": False,
            "p_finalize": False,
        },
    )

    # Debe ser reconocido como idéntico (metadata_synced), mismo id, version 1
    assert res2["id"] == doc_id
    assert res2["operation"] == "metadata_synced"
    assert res2["unchanged"] is True
    assert res2["version"] == 1

    # Comprobar que en la base de datos sigue existiendo un único registro
    docs = await store.db_request("GET", f"despacho_corpus_documentos?identificador_canonico=eq.{TEST_CANON}&select=id", key, service=True)
    assert len(docs) == 1

    desc = await store.db_request("GET", f"despacho_conector_descubrimientos?identificador_canonico=eq.{TEST_CANON}&select=id", key, service=True)
    assert len(desc) == 1


# ---------------------------------------------------------------------------
# PRUEBA C — CONCURRENCIA REAL (30 SOLICITUDES SIMULTÁNEAS)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_prueba_c_concurrencia_solicitudes_simultaneas():
    """Simula 30 solicitudes concurrentes intentando incorporar la misma providencia
    con distintas variantes de formato y espaciado.
    Comprueba que:
    - Solo existe una identidad documental.
    - Los registros permanecen consistentes.
    - No se duplican fragmentos.
    - No se generan embeddings innecesarios.
    - No se pierde información."""
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        pytest.skip("Requiere SUPABASE_SERVICE_ROLE_KEY")

    # Generar 30 variantes de llamada concurrente
    variantes = [
        "T-888/26", "T-888-26", "T 888/26", "t-888-26", "T-888/2026",
        "T 888/2026", "T-0888/26", "t-0888-2026", "T-888-2026", "T-888/26"
    ] * 3

    async def _worker_task(worker_idx: int, sentencia_var: str):
        return await store.db_request(
            "POST",
            "rpc/despacho_upsert_providencia_corpus_atomico",
            key,
            service=True,
            json={
                "p_source_id": "constitucional",
                "p_source_url": TEST_URL,
                "p_title": f"Sentencia {sentencia_var} - Concurrente {worker_idx}",
                "p_sentencia": sentencia_var,
                "p_hash": TEST_HASH,
                "p_chunks": TEST_CHUNKS,
                "p_metadata": {"worker_idx": worker_idx, "magistrado": "Dra. Concurrente", "tema": "Salud"},
                "p_workflow_status": "technically_validated",
                "p_published": False,
                "p_finalize": False,
            },
        )

    tasks = [_worker_task(i, var) for i, var in enumerate(variantes)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Ninguna llamada debe haber fallado con excepción no controlada
    valid_results = [r for r in results if isinstance(r, dict)]
    assert len(valid_results) == 30

    # Todos los resultados deben reportar exactamente el mismo UUID e identificador canónico
    first_id = valid_results[0]["id"]
    for r in valid_results:
        assert r["id"] == first_id
        assert r["identificador_canonico"] == TEST_CANON

    # Exactamente una operación debe ser 'created' y las restantes 29 'metadata_synced'
    created_ops = [r for r in valid_results if r.get("operation") == "created"]
    synced_ops = [r for r in valid_results if r.get("operation") == "metadata_synced"]
    assert len(created_ops) == 1
    assert len(synced_ops) == 29

    # Verificar en la base de datos: CERO DUPLICADOS en ambas tablas
    docs = await store.db_request("GET", f"despacho_corpus_documentos?identificador_canonico=eq.{TEST_CANON}&select=id,version", key, service=True)
    assert len(docs) == 1
    assert docs[0]["id"] == first_id
    assert docs[0]["version"] == 1

    desc = await store.db_request("GET", f"despacho_conector_descubrimientos?identificador_canonico=eq.{TEST_CANON}&select=id,document_id", key, service=True)
    assert len(desc) == 1
    assert desc[0]["document_id"] == first_id

    # Fragmentos: exactamente 1 fragmento (sin duplicación por concurrencia)
    fragments = await store.db_request("GET", f"despacho_corpus_fragmentos?document_id=eq.{first_id}&select=ordinal", key, service=True)
    assert len(fragments) == 1


# ---------------------------------------------------------------------------
# PRUEBA D — ERROR INTERMEDIO Y ROLLBACK TRANSACCIONAL
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_prueba_d_error_intermedio_rollback():
    """Simula una llamada con datos inválidos (hash malformado que viola el CHECK de PostgreSQL).
    Comprueba que la transacción se revierte al 100% y que no quedan registros huérfanos."""
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        pytest.skip("Requiere SUPABASE_SERVICE_ROLE_KEY")

    fail_sent = "T-999/26"
    fail_canon = "constitucional:T-999-2026"
    fail_url = "https://www.corteconstitucional.gov.co/relatoria/2026/T-999-26.htm"

    # Asegurar limpieza previa
    await store.db_request("DELETE", f"despacho_corpus_documentos?identificador_canonico=eq.{fail_canon}", key, service=True)
    await store.db_request("DELETE", f"despacho_conector_descubrimientos?identificador_canonico=eq.{fail_canon}", key, service=True)

    with pytest.raises(Exception):
        await store.db_request(
            "POST",
            "rpc/despacho_upsert_providencia_corpus_atomico",
            key,
            service=True,
            json={
                "p_source_id": "constitucional",
                "p_source_url": fail_url,
                "p_title": "Sentencia Invalida",
                "p_sentencia": fail_sent,
                "p_hash": "hash_invalido_demasiado_corto",  # Viola CHECK (content_hash ~ '^[0-9a-f]{64}$')
                "p_chunks": TEST_CHUNKS,
                "p_metadata": {},
            },
        )

    # Verificar que NINGUNA de las dos tablas guardó estados huérfanos
    docs = await store.db_request("GET", f"despacho_corpus_documentos?identificador_canonico=eq.{fail_canon}&select=id", key, service=True)
    assert len(docs) == 0

    desc = await store.db_request("GET", f"despacho_conector_descubrimientos?identificador_canonico=eq.{fail_canon}&select=id", key, service=True)
    assert len(desc) == 0


# ---------------------------------------------------------------------------
# PRUEBA E — ACTUALIZACIÓN DE METADATOS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_prueba_e_actualizacion_metadatos_preserva_uuid_fragmentos():
    """Actualiza el magistrado y tema de un documento de prueba sin alterar el hash del texto.
    Comprueba que se conservan UUID, fragmentos, versión y embeddings."""
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        pytest.skip("Requiere SUPABASE_SERVICE_ROLE_KEY")

    # Ingesta inicial
    res1 = await store.db_request(
        "POST",
        "rpc/despacho_upsert_providencia_corpus_atomico",
        key,
        service=True,
        json={
            "p_source_id": "constitucional",
            "p_source_url": TEST_URL,
            "p_title": "Sentencia T-888/26 - Corte Constitucional",
            "p_sentencia": TEST_SENTENCIA,
            "p_hash": TEST_HASH,
            "p_chunks": TEST_CHUNKS,
            "p_metadata": {"magistrado": "Dr. Original", "fecha": "2026-03-01"},
            "p_workflow_status": "technically_validated",
            "p_published": False,
        },
    )
    doc_id = res1["id"]

    # Actualizar metadatos (magistrado y fecha corregidos)
    res2 = await store.db_request(
        "POST",
        "rpc/despacho_upsert_providencia_corpus_atomico",
        key,
        service=True,
        json={
            "p_source_id": "constitucional",
            "p_source_url": TEST_URL,
            "p_title": "Sentencia T-888/26 - Corte Constitucional (Metadatos actualizados)",
            "p_sentencia": TEST_SENTENCIA,
            "p_hash": TEST_HASH,  # Mismo hash
            "p_chunks": TEST_CHUNKS,
            "p_metadata": {"magistrado": "Dra. Corregida Titular", "fecha": "2026-03-02", "tema": "Seguridad Social"},
            "p_workflow_status": "technically_validated",
            "p_published": False,
        },
    )

    assert res2["id"] == doc_id
    assert res2["operation"] == "metadata_synced"
    assert res2["version"] == 1
    assert res2["unchanged"] is True

    # Verificar metadatos actualizados en el corpus
    doc = (await store.db_request("GET", f"despacho_corpus_documentos?id=eq.{doc_id}&select=metadata,version", key, service=True))[0]
    assert doc["metadata"]["magistrado"] == "Dra. Corregida Titular"
    assert doc["version"] == 1

    # Verificar que los fragmentos y embeddings no fueron borrados ni duplicados
    frags = await store.db_request("GET", f"despacho_corpus_fragmentos?document_id=eq.{doc_id}&select=ordinal,embedding_model", key, service=True)
    assert len(frags) == 1
    assert frags[0]["embedding_model"] == "gemini-embedding-001"


# ---------------------------------------------------------------------------
# PRUEBA F — VERSIONAMIENTO ESTRICTO POR CAMBIO DE CONTENIDO
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_prueba_f_modificacion_contenido_versionamiento_estricto():
    """Simula una modificación auténtica del contenido documental (nuevo hash).
    Comprueba que se incrementa la versión (v2), se conserva el UUID, se reemplazan fragmentos
    y se genera registro de auditoría inmutable sin alterar referencias históricas."""
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        pytest.skip("Requiere SUPABASE_SERVICE_ROLE_KEY")

    # Ingesta inicial v1 (publicada oficialmente)
    res1 = await store.db_request(
        "POST",
        "rpc/despacho_upsert_providencia_corpus_atomico",
        key,
        service=True,
        json={
            "p_source_id": "constitucional",
            "p_source_url": TEST_URL,
            "p_title": "Sentencia T-888/26 - Corte Constitucional",
            "p_sentencia": TEST_SENTENCIA,
            "p_hash": TEST_HASH,
            "p_chunks": TEST_CHUNKS,
            "p_metadata": {"magistrado": "Magistrado Ponente"},
            "p_workflow_status": "published",
            "p_published": True,
            "p_finalize": True,
        },
    )
    doc_id = res1["id"]
    assert res1["version"] == 1
    assert res1["published"] is True

    # Simular nueva versión v2 con texto oficial modificado y hash distinto
    new_hash = hashlib.sha256(b"Texto oficial corregido con aclaracion de voto v2").hexdigest()
    new_chunks = [
        {
            "ordinal": 0,
            "segment": 1,
            "content": "Fragmento oficial corregido v2 con aclaración de voto.",
            "section": "resuelve",
            "embedding": [0.02] * 768,
            "embedding_model": "gemini-embedding-001",
        }
    ]

    res2 = await store.db_request(
        "POST",
        "rpc/despacho_upsert_providencia_corpus_atomico",
        key,
        service=True,
        json={
            "p_source_id": "constitucional",
            "p_source_url": TEST_URL,
            "p_title": "Sentencia T-888/26 - Corte Constitucional (v2)",
            "p_sentencia": TEST_SENTENCIA,
            "p_hash": new_hash,
            "p_chunks": new_chunks,
            "p_metadata": {"magistrado": "Magistrado Ponente", "version_note": "Aclaración incorporada"},
            "p_workflow_status": "pending_legal_review",
            "p_published": False,
        },
    )

    assert res2["id"] == doc_id
    assert res2["version"] == 2
    assert res2["operation"] == "version_bumped"
    assert res2["unchanged"] is False

    # Comprobar trazabilidad en auditoría
    audit = await store.db_request(
        "GET",
        f"despacho_corpus_auditoria_revisiones?document_id=eq.{doc_id}&document_version=eq.2&select=decision,reason",
        key,
        service=True,
    )
    assert len(audit) >= 1
    assert audit[0]["decision"] == "reopen"

    # =========================================================================
    # VERIFICACIÓN DE PRESERVACIÓN HISTÓRICA INMUTABLE DE CITAS
    # =========================================================================
    # 1. Comprobar que la versión anterior (v1) quedó archivada en despacho_corpus_documentos_historicos
    hist_docs = await store.db_request(
        "GET",
        f"despacho_corpus_documentos_historicos?document_id=eq.{doc_id}&document_version=eq.1&select=document_version,content_hash",
        key,
        service=True,
    )
    assert len(hist_docs) == 1
    assert hist_docs[0]["document_version"] == 1
    assert hist_docs[0]["content_hash"] == TEST_HASH

    # 2. Comprobar que los fragmentos de la versión 1 se preservaron íntegros en despacho_corpus_fragmentos_historicos
    hist_frags = await store.db_request(
        "GET",
        f"despacho_corpus_fragmentos_historicos?document_id=eq.{doc_id}&document_version=eq.1&select=document_version,ordinal,content",
        key,
        service=True,
    )
    assert len(hist_frags) == 1
    assert hist_frags[0]["document_version"] == 1
    assert "sobre derecho a la salud" in hist_frags[0]["content"]

    # 3. Comprobar que la versión activa (v2) en despacho_corpus_fragmentos tiene el nuevo contenido
    active_frags = await store.db_request(
        "GET",
        f"despacho_corpus_fragmentos?document_id=eq.{doc_id}&select=document_version,ordinal,content",
        key,
        service=True,
    )
    assert len(active_frags) == 1
    assert active_frags[0]["document_version"] == 2
    assert "con aclaración de voto" in active_frags[0]["content"]

    # 4. Probar recuperación a través del servicio de fuentes con version=1 (Visor de Evidencia Histórica)
    from app.services.despacho_corpus_fuentes import get_document_fragments
    # Simular consulta histórica del Visor sobre v1 mientras v2 está en revisión
    hist_view = await get_document_fragments(
        key,
        doc_id=doc_id,
        kind="official",
        version=1,
    )
    assert hist_view["document"]["is_historical_version"] is True
    assert hist_view["document"]["version"] == 1
    assert len(hist_view["fragments"]) == 1
    assert "sobre derecho a la salud" in hist_view["fragments"][0]["content"]

    # Publicar v2 formalmente
    await store.db_request(
        "POST",
        "rpc/despacho_actualizar_validacion_documento",
        key,
        service=True,
        json={
            "p_document_id": doc_id,
            "p_validation_status": "technically_validated",
            "p_validation_details": {"approved": True},
            "p_workflow_status": "published",
            "p_published": True,
        },
    )

    # Simular consulta activa del Visor (sin versión o versión 2)
    active_view = await get_document_fragments(
        key,
        doc_id=doc_id,
        kind="official",
    )
    assert active_view["document"]["is_historical_version"] is False
    assert active_view["document"]["version"] == 2
    assert len(active_view["fragments"]) == 1
    assert "con aclaración de voto" in active_view["fragments"][0]["content"]

    # 5. Probar recuperación en RAG: citas históricas (v1) vs citas contemporáneas (v2)
    from app.services.despacho_rag import verify_and_resolve_selected_fragments
    evidence_payload = [
        {"document_id": doc_id, "segment": 1, "version": 1, "kind": "official", "id": "CITA-HIST-1"},
        {"document_id": doc_id, "segment": 1, "version": 2, "kind": "official", "id": "CITA-ACTUAL-2"},
    ]
    verified = await verify_and_resolve_selected_fragments("test_user_id", key, evidence_payload)
    assert len(verified) == 2
    c_hist = next(c for c in verified if c["id"] == "CITA-HIST-1")
    c_act = next(c for c in verified if c["id"] == "CITA-ACTUAL-2")

    assert c_hist["version"] == 1
    assert "sobre derecho a la salud" in c_hist["excerpt"]

    assert c_act["version"] == 2
    assert "con aclaración de voto" in c_act["excerpt"]


# ---------------------------------------------------------------------------
# PRUEBA G — SEGURIDAD Y RESTRICCIÓN SERVICE_ROLE
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_prueba_g_seguridad_restriccion_service_role():
    """Verifica que las funciones administrativas de UPSERT no puedan ser invocadas
    por usuarios anónimos ni usuarios autenticados sin rol de servicio."""
    settings = get_settings()
    anon_key = settings.SUPABASE_ANON_KEY
    if not anon_key:
        pytest.skip("Requiere SUPABASE_ANON_KEY")

    # Invocación con clave anon -> DEBE RECHAZARSE (401 o 403 / 42501 No autorizado)
    with pytest.raises(Exception):
        await store.db_request(
            "POST",
            "rpc/despacho_upsert_providencia_corpus_atomico",
            anon_key,
            service=False,
            json={
                "p_source_id": "constitucional",
                "p_source_url": TEST_URL,
                "p_title": "Intento no autorizado",
                "p_sentencia": TEST_SENTENCIA,
                "p_hash": TEST_HASH,
                "p_chunks": TEST_CHUNKS,
                "p_metadata": {},
            },
        )

    with pytest.raises(Exception):
        await store.db_request(
            "POST",
            "rpc/despacho_upsert_descubrimiento",
            anon_key,
            service=False,
            json={
                "p_data": {"sentencia": TEST_SENTENCIA}
            },
        )


# ---------------------------------------------------------------------------
# PRUEBA H — CONCILIACIÓN FINAL
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_prueba_h_conciliacion_cero_duplicados():
    """Comprueba que no existan documentos duplicados, ni canónicos colisionados,
    ni estados contradictorios en la totalidad de las tablas en Supabase."""
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        pytest.skip("Requiere SUPABASE_SERVICE_ROLE_KEY")

    desc_rows = await store.db_request("GET", "despacho_conector_descubrimientos?select=id,sentencia,identificador_canonico,source_status,document_id", key, service=True) or []
    doc_rows = await store.db_request("GET", "despacho_corpus_documentos?select=id,title,identificador_canonico,published,workflow_status", key, service=True) or []

    # 1. Total exacto
    assert len(desc_rows) == 57
    assert len(doc_rows) == 46

    # 2. Cero duplicados canónicos en descubrimientos
    desc_canons = [d["identificador_canonico"] for d in desc_rows]
    assert len(desc_canons) == len(set(desc_canons)), "Existen duplicados canónicos en descubrimientos"

    # 3. Cero duplicados canónicos en corpus
    doc_canons = [d["identificador_canonico"] for d in doc_rows]
    assert len(doc_canons) == len(set(doc_canons)), "Existen duplicados canónicos en corpus"

    # 4. Todos los documentos del corpus tienen su contraparte vinculada en descubrimientos
    desc_by_canon = {d["identificador_canonico"]: d for d in desc_rows}
    for doc in doc_rows:
        canon = doc["identificador_canonico"]
        assert canon in desc_by_canon, f"Documento del corpus {canon} no tiene registro en descubrimientos"
        desc_entry = desc_by_canon[canon]
        assert str(desc_entry["document_id"]) == str(doc["id"]), f"Desincronización de document_id para {canon}"

        # Consistencia de estado publicado
        if doc["published"]:
            assert desc_entry["source_status"] == "published"
        else:
            assert desc_entry["source_status"] in ("technically_validated", "pending_legal_review")
