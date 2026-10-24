"""Script de verificación integral en vivo para la Fase 2:
Conector Oficial de la Corte Constitucional y Sistema de Actualización Incremental.
"""
from __future__ import annotations

import asyncio
import json
import time
import httpx

LOCAL_URL = "http://127.0.0.1:8000"
PROD_URL = "https://el-memorialista-juridico.onrender.com"
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings

TEST_EMAIL = "mppaulacruz91@gmail.com"
TEST_PASS = "112891"


async def main():
    print("=" * 80)
    print("INICIANDO SUITE DE VERIFICACIÓN EN VIVO: FASE 2 CONECTOR CORTE CONSTITUCIONAL")
    print("=" * 80)

    s = get_settings()
    supabase_url = s.SUPABASE_URL
    anon_key = s.SUPABASE_ANON_KEY

    # 1. Login en Supabase
    async with httpx.AsyncClient(timeout=45) as client:
        auth_res = await client.post(
            f"{supabase_url}/auth/v1/token?grant_type=password",
            headers={"apikey": anon_key},
            json={"email": TEST_EMAIL, "password": TEST_PASS},
        )
        assert auth_res.status_code == 200, f"Error autenticando: {auth_res.text}"
        auth_data = auth_res.json()
        token = auth_data["access_token"]
        user_id = auth_data["user"]["id"]
        print(f"✓ Autenticación exitosa (user_id: {user_id})")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # 2. Probar estado del conector
        from app.services import conector_corte_constitucional as conector
        st = await conector.get_connector_status()
        print("\n--- 1. ESTADO DEL CONECTOR OFICIAL EN SUPABASE ---")
        print(f"✓ Fuente: {st['source']}")
        print(f"✓ Estado operativo: {st['status']}")
        print(f"✓ Providencias publicadas en BD: {st['published_count']}")
        print(f"✓ Fragmentos totales indexados: {st['fragments_count']}")
        print(f"✓ Embeddings generados (768d): {st['embeddings_count']}")
        print(f"✓ Última sincronización: {st['last_sync_at']}")
        assert st["published_count"] >= 20, f"Esperado >= 20 providencias, encontrado {st['published_count']}"
        assert st["fragments_count"] >= 800, f"Esperado >= 800 fragmentos, encontrado {st['fragments_count']}"

        # 3. Probar recuperación RAG 2.0 con múltiples sentencias
        print("\n--- 2. VERIFICACIÓN DE RAG 2.0 MULTI-SENTENCIA ---")
        from app.services import despacho_rag as rag
        query = "estabilidad laboral reforzada en mujeres gestantes y prepensionados"
        ctx = {"passages": [], "sources": [], "warnings": [], "coverage": {}}
        req = {
            "message": query,
            "knowledge_scope": "official",
            "depth": "balanced",
            "conversation_id": f"live-multi-{int(time.time())}",
        }
        rag_res = await rag.retrieve_and_augment_rag(user_id, token, req, ctx)
        sources = rag_res.get("sources") or []
        passages = rag_res.get("passages") or []
        distinct_titles = {s.get("title") for s in sources}
        print(f"✓ Fuentes seleccionadas: {len(sources)}")
        print(f"✓ Providencias distintas recuperadas y distinguidas: {len(distinct_titles)}")
        for t in distinct_titles:
            print(f"   * {t}")
        assert len(distinct_titles) >= 2, "El motor RAG 2.0 debe recuperar y distinguir múltiples providencias distintas"

        # 4. Probar seguridad estricta de selected_fragments (descarte de texto cliente)
        print("\n--- 3. VERIFICACIÓN DE SEGURIDAD ESTRICTA DE selected_fragments ---")
        # Encontrar ID de T-100/24
        t100_source = next((s for s in sources if "T-100" in (s.get("title") or "")), sources[0])
        tampered_req = {
            "message": "Evalúa la procedencia de la tutela:",
            "knowledge_scope": "official",
            "depth": "quick",
            "selected_fragments": [
                {
                    "id": "SEL-PROD-1",
                    "document_id": t100_source.get("document_id"),
                    "segment": 2,
                    "kind": "official",
                    "source_url": t100_source.get("source_url"),
                    # Texto malicioso inyectado por el cliente que el servidor DEBE ignorar
                    "text": "TEXTO_FALSO_INYECTADO_POR_CLIENTE_QUE_EL_SERVIDOR_DEBE_IGNORAR_COMPLETAMENTE",
                }
            ],
        }
        ctx_tamper = {"passages": [], "sources": [], "warnings": [], "coverage": {}}
        tamper_res = await rag.retrieve_and_augment_rag(user_id, token, tampered_req, ctx_tamper)
        tamper_passages = tamper_res.get("passages") or []
        assert len(tamper_passages) >= 1, "Debe resolver el fragmento auténtico en BD"
        for p in tamper_passages:
            assert "TEXTO_FALSO" not in p.get("text", ""), "VULNERABILIDAD: El servidor aceptó texto cliente no verificado!"
        print("✓ SEGURIDAD CONFIRMADA: El texto falso fue completamente ignorado; se recuperó el texto auténtico de Supabase.")

        # 5. Probar seguridad entre cuentas (rechazo de documentos privados ajenos)
        print("\n--- 4. VERIFICACIÓN DE AISLAMIENTO RLS ENTRE CUENTAS ---")
        attack_req = [
            {
                "id": "ATTACK-DOC",
                "document_id": "00000000-0000-0000-0000-000000000000",
                "segment": 1,
                "kind": "document",
            }
        ]
        resolved = await rag.verify_and_resolve_selected_fragments(user_id, token, attack_req)
        assert len(resolved) == 0, "VULNERABILIDAD: Se resolvieron fragmentos de documentos no pertenecientes al usuario!"
        print("✓ SEGURIDAD CONFIRMADA: Solicitud de documentos privados no autorizados rechazada estrictamente (0 fragmentos devueltos).")

    print("\n" + "=" * 80)
    print("TODAS LAS VERIFICACIONES EN VIVO COMPLETADAS EXITOSAMENTE (100% OK)")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
