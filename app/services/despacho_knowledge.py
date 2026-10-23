"""Biblioteca propia: indexación, búsqueda híbrida y fuentes oficiales trazables.

No incluye ni anuncia un corpus comercial. La cobertura corresponde únicamente
a los documentos que el titular incorporó. Cada consulta conserva RLS y versión.
"""
from __future__ import annotations

import asyncio
try:
    from asyncio import timeout as async_timeout
except ImportError:
    from async_timeout import timeout as async_timeout
import hashlib
import json
import math
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.services import despacho_store as store
from app.services.despacho_fetch import fetch_source, validate_url

DIMENSIONS = 768
CHUNK_SIZE = 2400
CHUNK_OVERLAP = 240
SOURCES = [
    {"id": "constitucional", "name": "Corte Constitucional", "url": "https://www.corteconstitucional.gov.co/", "type": "jurisprudencia"},
    {"id": "suprema", "name": "Corte Suprema de Justicia", "url": "https://cortesuprema.gov.co/", "type": "jurisprudencia"},
    {"id": "consejo", "name": "Consejo de Estado", "url": "https://www.consejodeestado.gov.co/", "type": "jurisprudencia"},
    {"id": "suin", "name": "SUIN-Juriscol", "url": "https://www.suin-juriscol.gov.co/", "type": "normativa"},
    {"id": "funcionpublica", "name": "Función Pública", "url": "https://www.funcionpublica.gov.co/", "type": "normativa"},
    {"id": "senado", "name": "Secretaría del Senado", "url": "https://www.secretariasenado.gov.co/", "type": "normativa"},
    {"id": "dian", "name": "DIAN", "url": "https://www.dian.gov.co/", "type": "doctrina"},
    {"id": "sic", "name": "Superintendencia de Industria y Comercio", "url": "https://www.sic.gov.co/", "type": "resoluciones"},
]


def embedding_status() -> dict:
    s = get_settings()
    enabled = bool(s.DESPACHO_EMBEDDINGS_ENABLED)
    return {"enabled": enabled, "configured": bool(enabled and s.GEMINI_API_KEY.strip()),
            "model": s.DESPACHO_EMBEDDING_MODEL, "dimensions": DIMENSIONS,
            "message": "La disponibilidad del modelo se comprueba al indexar o buscar." if enabled else
                       "Búsqueda textual activa. Habilita embeddings para buscar por significado."}


def document_chunks(document: dict) -> list[dict]:
    data = document.get("data") or {}
    pages = data.get("pages") or [{"page": 1, "text": str(data.get("text") or "")}]
    physical = data.get("pagination") == "pages"
    chunks = []
    total = 0
    for page in pages:
        text = str(page.get("text") or "").replace("\x00", "")
        for start in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP):
            content = text[start:start + CHUNK_SIZE].strip()
            if not content:
                continue
            total += len(content)
            if len(chunks) >= 500 or total > 700_000:
                raise HTTPException(413, "El documento supera el presupuesto del índice. Divídelo antes de indexar.")
            chunks.append({"content": content, "page": page.get("page") if physical else None,
                           "segment": None if physical else page.get("page", 1),
                           "embedding": None, "embedding_model": None})
            if start + CHUNK_SIZE >= len(text):
                break
    return chunks


def _vector(value) -> list[float]:
    if not isinstance(value, list) or len(value) != DIMENSIONS:
        raise HTTPException(502, "El proveedor devolvió un vector de tamaño incompatible con el índice.")
    try:
        if any(isinstance(n, bool) for n in value):
            raise ValueError()
        floats = [float(n) for n in value]
        if any(not math.isfinite(n) for n in floats):
            raise ValueError()
        norm = math.sqrt(sum(n * n for n in floats))
        if not math.isfinite(norm) or norm <= 0:
            raise ValueError()
        return [n / norm for n in floats]
    except (ValueError, TypeError, OverflowError):
        raise HTTPException(502, "El proveedor devolvió un vector no válido.") from None


async def embed_texts(texts: list[str], *, query: bool = False) -> list[list[float]]:
    s = get_settings()
    if not embedding_status()["configured"]:
        raise HTTPException(503, "Habilita embeddings y configura Gemini en el servidor para utilizar búsqueda conceptual.")
    if not texts or len(texts) > 24 or any(not x or len(x) > 8000 for x in texts):
        raise HTTPException(422, "El lote de indexación no es válido.")
    model = s.DESPACHO_EMBEDDING_MODEL.strip()
    if not model or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for c in model):
        raise HTTPException(503, "El modelo de embeddings configurado no es válido.")
    from app.services.despacho_quotas import reserve_for_call
    await reserve_for_call()
    payload = {"requests": [{"model": "models/" + model, "content": {"parts": [{"text": text}]},
                             "taskType": "RETRIEVAL_QUERY" if query else "RETRIEVAL_DOCUMENT",
                             "outputDimensionality": DIMENSIONS} for text in texts]}
    try:
        async with httpx.AsyncClient(timeout=70, follow_redirects=False) as client:
            response = await client.post(s.GEMINI_API_BASE.rstrip("/") + f"/v1beta/models/{model}:batchEmbedContents",
                headers={"x-goog-api-key": s.GEMINI_API_KEY.strip(), "Content-Type": "application/json"}, json=payload)
        if response.status_code == 429:
            raise HTTPException(429, "La cuota de embeddings está temporalmente agotada.")
        if response.status_code != 200:
            raise HTTPException(503, "El proveedor no pudo generar embeddings. Comprueba clave, modelo y cuota.")
        embeddings = response.json().get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise ValueError()
        return [_vector(e.get("values")) for e in embeddings]
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        raise HTTPException(502, "La respuesta del proveedor de embeddings no fue utilizable.") from None


async def index_document(user_id: str, token: str, document_id: str) -> dict:
    document = await store.fetch_item(user_id, token, document_id, kind="document")
    chunks = document_chunks(document)
    warnings = list((document.get("data") or {}).get("warnings") or [])
    semantic = embedding_status()["configured"] and bool(chunks)
    if semantic:
        try:
            # El reemplazo se hace sólo después de preparar el lote completo.
            async with async_timeout(180):
                for offset in range(0, len(chunks), 24):
                    batch = chunks[offset:offset + 24]
                    vectors = await embed_texts([c["content"] for c in batch])
                    if len(batch) != len(vectors):
                        raise ValueError("Mismatch in vectors length")
                    for chunk, vector in zip(batch, vectors):
                        chunk.update(embedding=vector, embedding_model=get_settings().DESPACHO_EMBEDDING_MODEL)
        except (HTTPException, TimeoutError) as exc:
            semantic = False
            warnings.append(str(exc.detail) if isinstance(exc, HTTPException) else "La indexación conceptual alcanzó el límite de tiempo.")
            warnings.append("Se guardó únicamente un índice textual; no se anuncia disponibilidad semántica.")
            for chunk in chunks:
                chunk.update(embedding=None, embedding_model=None)
    result = await store.db_request("POST", "rpc/despacho_indexar_documento", token, json={
        "p_document_id": document["id"], "p_version": document["version"], "p_chunks": chunks})
    if not isinstance(result, dict):
        raise HTTPException(502, "El almacenamiento no confirmó la indexación.")
    return {**result, "semantic": bool(semantic), "method": "hybrid" if semantic else "text", "warnings": warnings}


async def reindex(user_id: str, token: str, offset: int, limit: int) -> dict:
    page = await store.list_items(user_id, token, kind="document", offset=offset, limit=limit)
    results, errors = [], []
    for item in page["items"]:
        try:
            results.append(await index_document(user_id, token, item["id"]))
        except HTTPException as exc:
            errors.append({"document_id": item["id"], "message": str(exc.detail), "status": exc.status_code})
    return {"items": results, "errors": errors, "has_more": page["has_more"],
            "next_offset": offset + len(page["items"]) if page["has_more"] else None}


async def search(user_id: str, token: str, request: dict) -> dict:
    store.uuid_text(user_id)
    query = str(request.get("query") or "").strip()
    scope = request.get("scope", "documents")
    if not query or len(query) > 4000 or scope not in {"documents", "legal"}:
        raise HTTPException(422, "Escribe una consulta de hasta 4.000 caracteres y un ámbito válido.")
    matter_id = request.get("matter_id")
    if matter_id:
        await store.fetch_item(user_id, token, matter_id, kind="matter")
    filters = dict(request.get("filters") or {})
    if set(filters) - {"court", "year", "document_type"}:
        raise HTTPException(422, "Los filtros permitidos son tribunal, año y tipo de documento.")
    selected = request.get("document_ids") or []
    if not isinstance(selected, list) or len(selected) > 20:
        raise HTTPException(422, "Selecciona hasta veinte documentos para limitar la búsqueda.")
    if selected:
        selected = list(dict.fromkeys(store.uuid_text(value) for value in selected))
        for doc_id in selected:
            await store.fetch_item(user_id, token, doc_id, kind="document")
        filters["document_ids"] = selected
    vector, warnings = None, []
    if request.get("semantic", True):
        try:
            vector = (await embed_texts([query], query=True))[0]
        except HTTPException as exc:
            warnings.append(str(exc.detail) + " Se ejecutó la búsqueda textual.")
    internal = store.is_service_token(token)
    rows = await store.db_request("POST", "rpc/despacho_buscar_conocimiento_interno" if internal else "rpc/despacho_buscar_conocimiento", token, service=internal, json={
        **({"p_owner": user_id} if internal else {}),
        "p_query": query, "p_embedding": json.dumps(vector) if vector else None,
        "p_model": get_settings().DESPACHO_EMBEDDING_MODEL if vector else None,
        "p_scope": scope, "p_matter_id": matter_id, "p_filters": filters,
        "p_limit": min(max(int(request.get("limit", 20)), 1), 50)})
    if not isinstance(rows, list):
        raise HTTPException(502, "El índice devolvió una respuesta no válida.")
    # La RPC aplica RLS, pero volvemos a resolver cada documento antes de divulgarlo.
    checked = {}
    results = []
    for row in rows:
        doc_id = store.uuid_text(row.get("document_id"))
        if doc_id not in checked:
            checked[doc_id] = await store.fetch_item(user_id, token, doc_id, kind="document")
        document = checked[doc_id]
        if document["version"] != row.get("document_version"):
            warnings.append("Un resultado cambió durante la consulta y se omitió. Vuelve a indexarlo.")
            continue
        results.append({**{k: row.get(k) for k in ("document_id", "title", "excerpt", "page", "segment", "score", "method")},
                        "id": doc_id, "source_url": (document.get("data") or {}).get("source_url"),
                        "document_version": document["version"]})
    coverage = await store.db_request("POST", "rpc/despacho_cobertura_indice_interna" if internal else "rpc/despacho_cobertura_indice", token,
                                      service=internal, json={"p_model": get_settings().DESPACHO_EMBEDDING_MODEL,
                                                             **({"p_owner": user_id} if internal else {})})
    methods = {row.get("method") for row in results}
    method = "hybrid" if "hybrid" in methods or {"semantic", "text"} <= methods else "semantic" if methods == {"semantic"} else "text"
    return {"results": results, "method": method, "semantic_query": bool(vector), "coverage": coverage,
            "warnings": list(dict.fromkeys(warnings)), "query": query,
            "scope": scope, "exhaustive": False}


async def list_legal_documents(user_id: str, token: str, *, offset: int = 0, limit: int = 50, filters: dict | None = None) -> dict:
    params = {"select": "*", "owner_id": "eq." + store.uuid_text(user_id), "kind": "eq.document",
              "data->>legal_source": "eq.true", "order": "updated_at.desc,id.asc", "offset": offset, "limit": limit + 1}
    for key, value in (filters or {}).items():
        if key in {"court", "year", "document_type"} and value:
            params[f"data->legal_metadata->>{key}"] = "eq." + str(value)
    rows = await store.db_request("GET", store.TABLE, token, params=params)
    if not isinstance(rows, list):
        raise HTTPException(502, "No se pudo leer la biblioteca jurídica.")
    return {"items": [store.public_item(row, user_id) for row in rows[:limit]], "has_more": len(rows) > limit}


async def import_source(user_id: str, token: str, request: dict) -> dict:
    url = validate_url(request.get("url", ""))
    source = await fetch_source(url)
    title = str(request.get("title") or source.get("title") or urlsplit(url).hostname).strip()[:240]
    source_hash = hashlib.sha256(source["text"].encode("utf-8")).hexdigest()
    params = {"select": "*", "owner_id": "eq." + store.uuid_text(user_id), "kind": "eq.document",
              "data->>source_url": "eq." + source["url"], "data->>source_hash": "eq." + source_hash, "limit": 1}
    existing = await store.db_request("GET", store.TABLE, token, params=params)
    if isinstance(existing, list) and existing:
        return {"item": store.public_item(existing[0], user_id), "duplicate": True, "warnings": []}
    metadata = {k: str(request[k]).strip()[:160] for k in ("court", "year", "document_type") if request.get(k) is not None}
    data = {"text": source["text"], "pages": source.get("pages") or [{"page": 1, "text": source["text"]}],
            "pagination": source.get("pagination", "segments"), "mime": source["mime"], "versions": [],
            "legal_source": True, "legal_metadata": metadata, "source_url": source["url"], "source_hash": source_hash,
            "retrieved_at": store.utcnow(), "warnings": source.get("warnings", []),
            "extraction_coverage": source.get("extraction_coverage", {}),
            "source_provenance": "Texto obtenido de una URL oficial permitida. No acredita vigencia ni exhaustividad."}
    item = await store.create_item(user_id, token, {"kind": "document", "title": title, "data": data})
    warnings = []
    try:
        index = await index_document(user_id, token, item["id"])
        warnings += index.get("warnings", [])
    except HTTPException as exc:
        index = None
        warnings.append("La fuente se guardó, pero falta indexarla: " + str(exc.detail))
    return {"item": item, "index": index, "duplicate": False, "warnings": warnings}


async def crawl_sources(user_id: str, token: str, request: dict) -> dict:
    source = await fetch_source(validate_url(request.get("url", "")))
    maximum = min(max(int(request.get("max_documents", 5)), 1), 10)
    links = source.get("links", [])[:maximum]
    results, errors = [], []
    for link in links:
        try:
            results.append(await import_source(user_id, token, {"url": link["url"], "title": link.get("title")}))
        except HTTPException as exc:
            errors.append({"url": link["url"], "message": str(exc.detail)})
    return {"items": results, "errors": errors, "discovered": len(source.get("links", [])), "attempted": len(links),
            "coverage": "Sólo enlaces descubiertos en la página o feed indicado, dentro del límite elegido.",
            "has_more": len(source.get("links", [])) > len(links)}
