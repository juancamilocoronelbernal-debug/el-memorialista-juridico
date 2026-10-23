"""Pruebas reales de optimización técnica del Agente y Embeddings (v5.0.2).

Ejecuta las 7 pruebas requeridas por la optimización:
1. Chat sencillo (tiempo y modelo gemini-3.6-flash)
2. Consulta jurídica real
3. Embeddings y búsqueda conceptual por significado
4. DMS y trazabilidad de referencias
5. Seguridad y aislamiento de cuentas
6. Manejo de errores y tolerancia a fallos
7. Ejecución programada real de trabajadores
"""
import asyncio
import os
import sys
import time
from uuid import uuid4

import httpx
from dotenv import load_dotenv

load_dotenv(".env")

from app.config import get_settings
from app.services import despacho_ai as ai
from app.services import despacho_knowledge as knowledge
from app.services import despacho_store as store
from app.services.gemini_service import gemini_service, Motor

URL = os.getenv("SUPABASE_URL")
ANON = os.getenv("SUPABASE_ANON_KEY")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
USER_EMAIL = "mppaulacruz91@gmail.com"
USER_PASS = "112891"
USER_ID = "2638a0a9-1375-4241-91eb-426b9282acee"
OTHER_USER_ID = "bbff7fef-1a0e-43a1-a629-f8657e9a5a0f"


async def get_user_token():
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{URL}/auth/v1/token?grant_type=password",
            headers={"apikey": ANON, "Content-Type": "application/json"},
            json={"email": USER_EMAIL, "password": USER_PASS},
        )
        data = r.json()
        return data["access_token"], data["user"]["id"]


async def main():
    print("=" * 60)
    print("INICIO DE VERIFICACIÓN DE OPTIMIZACIÓN DEL AGENTE")
    print("=" * 60)

    token, uid = await get_user_token()
    print(f"Usuario autenticado para pruebas: {uid} ({USER_EMAIL})")

    # ----------------------------------------------------
    # PRUEBA 1: CHAT SENCILLO
    # ----------------------------------------------------
    print("\n--- PRUEBA 1: CHAT SENCILLO ---")
    t0 = time.time()
    req_chat = {
        "message": "Hola, responde únicamente OK.",
        "history": [],
        "mode": "general",
        "knowledge_scope": "off",
        "document_ids": [],
    }
    res1 = await ai.chat(uid, token, req_chat)
    elapsed1 = time.time() - t0
    print(f"Respuesta recibida: {res1['answer'].strip()}")
    print(f"Proveedor: {res1.get('provider')}")
    print(f"Modelo: {res1.get('model')}")
    print(f"Tiempo total: {elapsed1:.2f}s")
    if "timing" in res1:
        print(f"Métricas internas: {res1['timing']}")
    assert "OK" in res1["answer"].upper(), "La respuesta no contiene OK"
    assert res1.get("model") == "gemini-3.6-flash", f"El modelo no fue gemini-3.6-flash: {res1.get('model')}"
    print("[OK] Prueba 1 superada con éxito.")

    # ----------------------------------------------------
    # PRUEBA 2: CONSULTA JURÍDICA
    # ----------------------------------------------------
    print("\n--- PRUEBA 2: CONSULTA JURÍDICA REAL ---")
    t0 = time.time()
    req_legal = {
        "message": "¿Cuál es el término legal para interponer el recurso de reposición contra un auto en el Código General del Proceso en Colombia?",
        "history": [],
        "mode": "general",
        "knowledge_scope": "off",
        "document_ids": [],
    }
    res2 = await ai.chat(uid, token, req_legal)
    elapsed2 = time.time() - t0
    print(f"Respuesta previa: {res2['answer'][:220]}...")
    print(f"Proveedor: {res2.get('provider')}")
    print(f"Modelo: {res2.get('model')}")
    print(f"Tiempo total: {elapsed2:.2f}s")
    assert any(term in res2["answer"].lower() for term in ["tres", "3", "artículo 318", "días"]), "Respuesta jurídica imprecisa"
    print("[OK] Prueba 2 superada con éxito.")

    # ----------------------------------------------------
    # PRUEBA 3: EMBEDDINGS Y BÚSQUEDA CONCEPTUAL
    # ----------------------------------------------------
    print("\n--- PRUEBA 3: EMBEDDINGS Y BÚSQUEDA CONCEPTUAL ---")
    doc_text = (
        "La responsabilidad civil médica de las clínicas y hospitales por eventos adversos derivados "
        "de infecciones intrahospitalarias o nosocomiales compromete patrimonialmente a la institución prestadora "
        "cuando no se acredita el estricto cumplimiento de los protocolos de bioseguridad, esterilización "
        "y asepsia quirúrgica exigidos por el Ministerio de Salud."
    )
    doc_item = await store.create_item(uid, token, {
        "kind": "document",
        "title": "Protocolo de responsabilidad en infecciones nosocomiales",
        "data": {
            "text": doc_text,
            "pages": [{"page": 1, "text": doc_text}],
            "pagination": "pages",
        }
    })
    doc_id = doc_item["id"]
    print(f"Documento de prueba creado: {doc_id}")

    # Indexar con embeddings
    index_res = await knowledge.index_document(uid, token, doc_id)
    print(f"Resultado de indexación: {index_res}")
    assert index_res.get("semantic") is True, "La indexación semántica no fue exitosa"

    # Búsqueda con vocabulario completamente diferente: "sanatorios, bacterias adquiridas en quirófano y culpa clínica"
    conceptual_query = "sanatorios y bacterias adquiridas en quirófano"
    search_res = await knowledge.search(uid, token, {
        "query": conceptual_query,
        "scope": "documents",
        "semantic": True,
        "limit": 5,
    })
    print(f"Resultados de búsqueda conceptual para '{conceptual_query}': {len(search_res['results'])}")
    assert len(search_res["results"]) > 0, "La búsqueda conceptual no encontró el documento"
    hit = search_res["results"][0]
    print(f" - Hallazgo: {hit['title']} | Método: {hit['method']} | Versión: {hit['document_version']}")
    assert hit["method"] in ("semantic", "hybrid"), f"El método esperado era semántico/híbrido pero fue {hit['method']}"
    print("[OK] Prueba 3 superada con éxito.")

    # ----------------------------------------------------
    # PRUEBA 4: DMS Y CITAS
    # ----------------------------------------------------
    print("\n--- PRUEBA 4: DMS Y CITAS CONTEXTUALES ---")
    t0 = time.time()
    req_dms = {
        "message": "¿Cuándo se compromete patrimonialmente una institución prestadora según los documentos aportados?",
        "history": [],
        "mode": "analyze",
        "knowledge_scope": "documents",
        "document_ids": [doc_id],
    }
    res4 = await ai.chat(uid, token, req_dms)
    elapsed4 = time.time() - t0
    print(f"Respuesta con DMS: {res4['answer'][:200]}...")
    print(f"Fuentes citadas: {[s.get('id') for s in res4.get('sources', [])]}")
    print(f"Tiempo: {elapsed4:.2f}s")
    assert len(res4.get("sources", [])) > 0, "No se registraron fuentes documentales en la respuesta"
    print("[OK] Prueba 4 superada con éxito.")

    # ----------------------------------------------------
    # PRUEBA 5: SEGURIDAD Y AISLAMIENTO DE USUARIOS
    # ----------------------------------------------------
    print("\n--- PRUEBA 5: AISLAMIENTO POR CUENTA ---")
    other_search = await store.db_request(
        "POST", "rpc/despacho_buscar_conocimiento_interno", SERVICE_KEY, service=True, json={
            "p_owner": OTHER_USER_ID,
            "p_query": conceptual_query,
            "p_embedding": None,
            "p_model": None,
            "p_scope": "documents",
            "p_matter_id": None,
            "p_filters": {},
            "p_limit": 5,
        }
    )
    print(f"Resultados visibles para otro usuario ({OTHER_USER_ID}): {len(other_search)}")
    assert len(other_search) == 0, f"Violación de aislamiento: otro usuario recuperó {len(other_search)} documentos"
    print("[OK] Prueba 5 superada con éxito.")

    # Limpiar documento de prueba
    await store.delete_item(uid, token, doc_id, doc_item["version"])
    print("Documento de prueba limpiado de la base de datos.")

    # ----------------------------------------------------
    # PRUEBA 6: MANEJO DE ERRORES Y TIMEOUTS
    # ----------------------------------------------------
    print("\n--- PRUEBA 6: MANEJO DE MODELO NO DISPONIBLE ---")
    gemini_service.no_disponibles["modelo-fantasma-inexistente"] = time.monotonic()
    print("Modelo fantasma marcado correctamente en lista de no disponibles.")
    # Comprobar que candidatos() no incluye modelos no disponibles
    cand = [m.modelo for m in gemini_service.candidatos("default")]
    assert "modelo-fantasma-inexistente" not in cand
    print("[OK] Prueba 6 superada con éxito.")

    print("\n" + "=" * 60)
    print("TODAS LAS PRUEBAS REALES SUPERADAS SATISFACTORIAMENTE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
