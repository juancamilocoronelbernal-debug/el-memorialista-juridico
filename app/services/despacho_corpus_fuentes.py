"""Fuentes oficiales: catálogo HONESTO, metadatos públicos y corpus global revisado.

No contiene material de Magnar ni afirma que sus colecciones estén indexadas.
Las consultas a datos.gov.co recuperan metadatos, NO el texto de las sentencias.
El corpus compartido sólo incluye originales seleccionados y aprobados por un
administrador, con separación total de los documentos privados del despacho.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from app.services import despacho_store as store
from app.services.despacho_knowledge import embed_texts, embedding_status
from app.config import get_settings

# Catálogo derivado de los nombres de colecciones facilitados por el propietario.
# Los portales enlazados son referencias públicas; no equivalen a conectores activos.
# TODO: revisión individual de acceso automatizado, licencias, privacidad y cobertura.
_C = [
 ('anla','ANLA','ambiental',None),
 ('anla_eureka','ANLA · EUREKA','ambiental','https://www.anla.gov.co/wanla/eureka/'),
 ('ant_conceptos','ANT · Conceptos','tierras',None),
 ('contraloria','Contraloría General de la República','control',None),
 ('ciadi','CIADI','internacional','https://icsid.worldbank.org/cases'),
 ('cndj','Comisión Nacional de Disciplina Judicial','disciplinario',None),
 ('ancp_cce','ANCP · Colombia Compra Eficiente','contratacion','https://www.colombiacompra.gov.co/normativa-y-relatoria/conoce-la-relatoria'),
 ('consejo_historico','Consejo de Estado · anterior a 2021','jurisprudencia','https://consejodeestado.gov.co/buscador-de-jurisprudencia2/'),
 ('constitucional','Corte Constitucional','jurisprudencia','https://www.corteconstitucional.gov.co/'),
 ('corte_idh','Corte Interamericana de Derechos Humanos','internacional',None),
 ('consejo_estado','Consejo de Estado','jurisprudencia','https://consejodeestado.gov.co/buscador-de-jurisprudencia2/'),
 ('cpa','Tribunal Permanente de Arbitraje','internacional',None),
 ('dian','DIAN','tributario','https://www.dian.gov.co/'),
 ('defensoria','Defensoría del Pueblo','control',None),
 ('fgn','Fiscalía General de la Nación','penal',None),
 ('cij','Corte Internacional de Justicia','internacional',None),
 ('jep','Jurisdicción Especial para la Paz','justicia_transicional',None),
 ('juzgados_administrativos','Juzgados Administrativos','procesal',None),
 ('juzgados_circuito','Juzgados de Circuito','procesal',None),
 ('juzgados_circuito_ejecucion','Juzgados de Circuito de Ejecución','procesal',None),
 ('juzgados_municipales','Juzgados Municipales','procesal',None),
 ('oma','Organización Mundial de Aduanas · Convenciones y recomendaciones','internacional',None),
 ('omc','OMC · Solución de Diferencias','internacional','https://data.wto.org/en/dataset/ds_db'),
 ('pgn','Procuraduría General de la Nación','control',None),
 ('pgn_normativa','PGN · Normativa','control',None),
 ('samai','Consejo de Estado · SAMAI','jurisprudencia','https://samaijca.consejodeestado.gov.co/TitulacionRelatoria/BuscadorProvidenciasTituladas.aspx'),
 ('sic','Superintendencia de Industria y Comercio','superintendencias','https://www.sic.gov.co/'),
 ('sspd_servicios','SSPD · Servicios','superintendencias',None),
 ('sspd','Superintendencia de Servicios Públicos Domiciliarios','superintendencias','https://www.superservicios.gov.co/Normativa/Resoluciones-y-circulares-Superservicios'),
 ('sfc','Superintendencia Financiera de Colombia','superintendencias',None),
 ('sfc_circulares','SFC · Circulares','superintendencias',None),
 ('supersalud_conceptos','Supersalud · Conceptos','superintendencias',None),
 ('supersociedades','Superintendencia de Sociedades','superintendencias',None),
 ('suprema','Corte Suprema de Justicia','jurisprudencia','https://cortesuprema.gov.co/'),
 ('tjca','Tribunal de Justicia de la Comunidad Andina','internacional',None),
 ('tratados','Tratados internacionales de Colombia','internacional',None),
 ('tribunales_superiores','Tribunales Superiores','procesal',None),
 ('tribunales_administrativos','Tribunales Administrativos','procesal',None),
 ('ugpp','Unidad de Gestión Pensional y Parafiscales','seguridad_social',None),
 ('unat','Tribunal de Apelaciones de Naciones Unidas · UNAT','internacional',None),
 ('undt','Tribunal Contencioso-Administrativo de Naciones Unidas · UNDT','internacional',None),
]
# Se añade SUIN, que no estaba entre los nombres compartidos y es una fuente normativa clave.
_C.append(('suin','SUIN-Juriscol · normativa nacional','normativa','https://www.suin-juriscol.gov.co/'))
_C.append(('funcion_publica','Función Pública · Gestor Normativo','normativa','https://www.funcionpublica.gov.co/eva/gestornormativo/consulta_avanzada.php'))

DATASET_URL = 'https://www.datos.gov.co/Justicia-y-Derecho/Sentencias-proferidas-por-la-Corte-Constitucional/v2k4-2t8s'
SODA_URL = 'https://www.datos.gov.co/resource/v2k4-2t8s.json'


def catalog() -> list[dict]:
    """Fuente nombrada != fuente conectada != fuente indexada."""
    return [{"id": id_, "name": name, "category": cat, "portal_url": url,
             "access": "metadata_api" if id_ == 'constitucional' else 'portal_manual' if url else 'pending_review',
             "indexed": False,
             "notice": "Metadatos estadísticos, no texto de providencias." if id_ == 'constitucional'
                  else "Requiere evaluación de acceso, licencia y un conector individual."}
            for id_, name, cat, url in _C]


def _soda_where(query: str, year: int | None = None) -> str:
    """Construye solo expresiones predefinidas; jamás acepta cláusulas SQL del cliente."""
    q = query.strip()
    if not (2 <= len(q) <= 120) or not re.fullmatch(r'[\w\s./-]+', q, flags=re.UNICODE) or '_' in q or '\\' in q or any(ord(x) < 32 for x in q):
        raise HTTPException(422, "Usa entre 2 y 120 caracteres para buscar metadatos de sentencias.")
    # Socrata SoQL quoted literal; escapar comillas simples y metacaracteres LIKE.
    term = q.strip()
    if len(term) < 2:
        raise HTTPException(422, "La búsqueda no contiene suficientes caracteres.")
    if re.fullmatch(r'(?i)(?:T|C|SU)[- ]?\d{1,5}[/-]\d{2,4}', term):
        expr = "upper(sentencia)=upper('" + term + "')"
    else:
        expr = "(" + " OR ".join(
            "upper(" + field + ") like upper('%" + term + "%')"
            for field in ('sentencia', 'magistrado_a', 'sala', 'proceso')) + ")"
    if year is not None:
        if not (1992 <= year <= 2100):
            raise HTTPException(422, "El año debe ser posterior a 1991.")
        expr += f" AND fecha_sentencia between '{year}-01-01T00:00:00' and '{year}-12-31T23:59:59'"
    return expr


async def constitutional_metadata(query: str, *, year: int | None = None, limit: int = 10, offset: int = 0) -> dict:
    """Consulta un dataset oficial publicado; no extrae sentencias completas ni documentos personales."""
    if not (1 <= limit <= 25 and 0 <= offset <= 10000):
        raise HTTPException(422, "Paginación fuera de los límites permitidos.")
    where = _soda_where(query, year)
    params = {'$select': 'sentencia,fecha_sentencia,magistrado_a,sala,proceso,expediente_tipo,expediente_numero',
              '$where': where, '$limit': str(limit), '$offset': str(offset), '$order': 'fecha_sentencia DESC'}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(18, connect=6), follow_redirects=False, trust_env=False) as client:
            response = await client.get(SODA_URL, params=params, headers={'Accept': 'application/json', 'User-Agent':'ElMemorialista-FuentesOficiales/1.0'})
        if response.status_code == 429:
            raise HTTPException(429, "El portal de datos abiertos limitó temporalmente las consultas. Intenta más tarde.")
        if response.status_code != 200:
            raise HTTPException(502, f"El dataset oficial no respondió correctamente (HTTP {response.status_code}).")
        data = response.json()
        if not isinstance(data, list):
            raise ValueError('La API no devolvió una lista')
    except (httpx.HTTPError, ValueError, TypeError):
        raise HTTPException(502, "No fue posible consultar o interpretar los metadatos oficiales.") from None
    rows = []
    for item in data[:limit]:
        if not isinstance(item, dict):
            continue
        cite = str(item.get('sentencia') or '').strip()[:60]
        if not cite:
            continue
        rows.append({"citation": cite, "date": str(item.get('fecha_sentencia') or '')[:28],
                     "judge": str(item.get('magistrado_a') or '')[:160], "chamber": str(item.get('sala') or '')[:160],
                     "process": str(item.get('proceso') or '')[:160],
                     "case_number": str(item.get('expediente_numero') or '')[:45],
                     "dataset_url": DATASET_URL,
                     "metadata_source": "Datos Abiertos Colombia · Corte Constitucional",
                     "metadata_confirmed": True, "full_text_retrieved": False,
                     "legal_validity_checked": False})
    return {"items": rows, "query": query, "limit": limit, "offset": offset,
            "more_possible": len(data) == limit,
            "source_id": 'constitucional', "dataset_url": DATASET_URL,
            "coverage": "Registros estadísticos publicados por la Corte Constitucional; sin contenido de fallos, temas ni citas textuales.",
            "notice": "Un registro demuestra metadatos de la sentencia, no su ratio decidendi ni la vigencia de la regla jurídica."}


async def _fetch_target_ruling_structural_rows(
    token: str,
    target_ruling: str,
    target_section: str | None = None,
) -> list[dict]:
    """Recupera los fragmentos estructurales clave (encabezado con ponente, problema jurídico y parte resolutiva)
    cuando la consulta identifica explícitamente una sentencia del Corpus Oficial.
    """
    try:
        base, headers = store.connection(token)
        if not base:
            return []
        async with httpx.AsyncClient(timeout=12) as client:
            d_res = await client.get(
                f"{base}/rest/v1/despacho_corpus_documentos?published=eq.true&title=ilike.*{target_ruling}*&limit=1",
                headers=headers,
            )
            if d_res.status_code >= 400 or not isinstance(d_res.json(), list) or not d_res.json():
                return []
            doc = d_res.json()[0]
            if doc.get("integrity_status") == "partial" or doc.get("workflow_status") == "withdrawn":
                return []
            doc_id = doc["id"]
            doc_url = str(doc.get("source_url") or "")
            if urlsplit(doc_url).scheme != "https":
                return []
            meta = doc.get("metadata") or {}
            decision_date = meta.get("decision_date") or meta.get("fecha")
            ficha_parts = []
            if meta.get("sentencia"):
                ficha_parts.append(f"Providencia: Sentencia {meta['sentencia']}")
            if meta.get("magistrado"):
                ficha_parts.append(f"Magistrado(a) Ponente: {meta['magistrado']}")
            if meta.get("sala"):
                ficha_parts.append(f"Sala: {meta['sala']}")
            if meta.get("expediente"):
                ficha_parts.append(f"Expediente: {meta['expediente']}")
            if decision_date:
                ficha_parts.append(f"Fecha: {decision_date}")
            if meta.get("materia"):
                ficha_parts.append(f"Materia oficial verificada: {meta['materia']}")
            ficha_prefix = ("[" + " | ".join(ficha_parts) + "]\n\n") if ficha_parts else ""

            sections_wanted = ["encabezado", "problema_juridico", "parte_resolutiva"]
            if target_section and target_section not in sections_wanted:
                sections_wanted.append(target_section)
            sec_in = ",".join(sections_wanted)

            f_res = await client.get(
                f"{base}/rest/v1/despacho_corpus_fragmentos?document_id=eq.{doc_id}"
                f"&section=in.({sec_in})&order=ordinal.asc&select=segment,content,section,document_version&limit=8",
                headers=headers,
            )
            if f_res.status_code >= 400 or not isinstance(f_res.json(), list):
                return []

            extra_rows = []
            for idx, fr in enumerate(f_res.json()):
                raw_txt = str(fr.get("content") or "")
                excerpt = (ficha_prefix + raw_txt)[:4000] if idx == 0 else raw_txt[:4000]
                extra_rows.append({
                    "title": doc.get("title"),
                    "excerpt": excerpt,
                    "source_url": doc_url,
                    "source_id": doc.get("source_id"),
                    "date": decision_date,
                    "version": fr.get("document_version") or doc.get("version", 1),
                    "segment": fr.get("segment") or 1,
                    "section": fr.get("section") or "encabezado",
                    "score": 0.032,
                    "method": "hybrid",
                    "provenance": "Documento publicado en corpus revisado. Comprobar vigencia y pertinencia.",
                })
            return extra_rows
    except Exception:
        return []


async def search_corpus(token: str, query: str, *, limit: int = 12, semantic: bool = True, depth: str = "auto") -> dict:
    """Busca únicamente un corpus global expresamente aprobado; no lee DMS privado."""
    query = query.strip()
    if not (2 <= len(query) <= 800 and 1 <= limit <= 50):
        raise HTTPException(422, "Escribe entre 2 y 800 caracteres y selecciona un límite válido (1 a 50).")
    vector, warnings = None, []
    if semantic and embedding_status()['configured']:
        try:
            vector = (await embed_texts([query], query=True))[0]
        except HTTPException as exc:
            warnings.append('Búsqueda conceptual no disponible: ' + str(exc.detail) + '. Se consultó el índice textual.')
    elif semantic:
        warnings.append('Se consultó el índice textual. Los embeddings no están activos.')
    data = await store.db_request('POST', 'rpc/despacho_consultar_corpus_publicado', token, json={
        'p_query': query, 'p_vector': json.dumps(vector) if vector else None,
        'p_model': get_settings().DESPACHO_EMBEDDING_MODEL if vector else None,
        'p_limit': limit})
    if not isinstance(data, list):
        raise HTTPException(502, 'La base jurídica compartida no devolvió resultados válidos.')
    rows = []
    for item in data:
        if not isinstance(item, dict):
            continue
        url = str(item.get('source_url') or '')
        if urlsplit(url).scheme != 'https':
            continue
        rows.append({"title": item.get('title'), "excerpt": str(item.get('excerpt') or '')[:4000],
                     "source_url": url, "source_id": item.get('source_id'),
                     "date": item.get('decision_date'), "version": item.get('document_version'),
                     "segment": item.get('segment'), "score": item.get('score'), "method": item.get('method'),
                     "provenance": "Documento publicado en corpus revisado. Comprobar vigencia y pertinencia."})

    # RAG 2.0: Clasificación de secciones, reranking jurídico y filtrado de umbral mínimo
    if getattr(get_settings(), "DESPACHO_RAG_V2_ENABLED", True):
        try:
            from app.services import despacho_rag
            intent_info = despacho_rag.classify_query_intent(query)
            if intent_info.get("target_ruling") and semantic:
                structural_rows = await _fetch_target_ruling_structural_rows(
                    token,
                    intent_info["target_ruling"],
                    intent_info.get("target_section"),
                )
                seen_seg = {(r.get("source_url"), r.get("segment")) for r in rows}
                for sr in structural_rows:
                    key_seg = (sr.get("source_url"), sr.get("segment"))
                    if key_seg not in seen_seg:
                        rows.append(sr)
                        seen_seg.add(key_seg)
                    elif sr.get("segment") == 1:
                        for existing_r in rows:
                            if (existing_r.get("source_url"), existing_r.get("segment")) == key_seg:
                                existing_r["excerpt"] = sr["excerpt"]

            if rows:
                for row in rows:
                    if not row.get("section") or row.get("section") == "seccion_desconocida":
                        row["section"] = despacho_rag.classify_legal_section(row["excerpt"], row.get("title") or "").value
                d_key = depth if depth in despacho_rag.DEPTH_PROFILES else intent_info["suggested_depth"]
                profile = despacho_rag.DEPTH_PROFILES[d_key]
                rows = despacho_rag.rerank_candidates(rows, query, intent_info, profile)
                min_thresh = profile.get("min_score_threshold", 0.30)
                rows = [
                    r for r in rows
                    if r.get("score") is None or r.get("rerank_score", 0.0) >= min_thresh
                ]
        except Exception as e:
            warnings.append(f"Reranking no aplicado: {e}")

    return {"results": rows, "query": query, "scope": "shared_official",
            "semantic_query": bool(vector), "warnings": warnings,
            "coverage": "Exclusivamente documentos autorizados e incorporados por un administrador. No es exhaustiva.",
            "source": "Corpus propio de El Memorialista, separado de cada DMS privado."}


async def corpus_status(token: str) -> dict:
    result = await store.db_request('POST', 'rpc/despacho_estado_corpus_publicado', token, json={})
    if not isinstance(result, dict):
        raise HTTPException(502, 'La cobertura del corpus no está disponible.')
    return {**result, 'note': 'Sólo se contabilizan documentos revisados y publicados; el catálogo de portales es independiente.'}


async def get_document_fragments(
    token: str,
    *,
    doc_id: str | None = None,
    source_url: str | None = None,
    source_id: str | None = None,
    kind: str = "official",
    user_id: str | None = None,
    offset: int = 0,
    limit: int = 50,
    q: str | None = None,
    version: int | None = None,
) -> dict:
    """Recupera la totalidad de los fragmentos indexados de un documento bajo demanda
    con paginación y búsqueda textual interna sin sobrecargar el contexto.
    """
    limit = min(max(int(limit), 1), 100)
    offset = max(int(offset), 0)
    base, base_headers = store.connection(token)
    headers = {
        **base_headers,
        "Range": f"{offset}-{offset + limit - 1}",
        "Prefer": "count=exact"
    }

    async with httpx.AsyncClient(timeout=35) as client:
        if kind == "official" or source_url or (doc_id and not user_id):
            doc_query = "limit=1"
            if doc_id:
                doc_query += f"&id=eq.{doc_id}"
            elif source_url:
                doc_query += f"&source_url=eq.{source_url}"
            elif source_id:
                doc_query += f"&source_id=eq.{source_id}"

            doc_res = await client.get(
                f"{base}/rest/v1/despacho_corpus_documentos?{doc_query}",
                headers=base_headers
            )
            if doc_res.status_code >= 400 or not doc_res.json():
                raise HTTPException(404, "Documento oficial no encontrado en el corpus compartido.")

            doc_data = doc_res.json()[0]
            is_historical = bool(version and int(version) < int(doc_data.get("version", 1)))

            if doc_data.get("is_withdrawn") or doc_data.get("workflow_status") in ("withdrawn", "retirado_temporalmente"):
                reason = doc_data.get("withdrawn_reason") or "Providencia retirada preventivamente por control de calidad"
                status_wf = doc_data.get("workflow_status") or "retirado_temporalmente"
                raise HTTPException(
                    410,
                    f"Providencia no disponible: {reason}. Estado actual: {status_wf}."
                )

            if not is_historical and (doc_data.get("published") is False):
                reason = doc_data.get("withdrawn_reason") or "Providencia en proceso de revisión editorial no publicada"
                status_wf = doc_data.get("workflow_status") or "pending_legal_review"
                raise HTTPException(
                    410,
                    f"Providencia no disponible: {reason}. Estado actual: {status_wf}."
                )

            if doc_data.get("integrity_status") == "partial":
                raise HTTPException(
                    404,
                    "Documento oficial con indexación parcial en curso; no disponible como providencia íntegra."
                )
            actual_doc_id = doc_data["id"]

            target_table = "despacho_corpus_fragmentos_historicos" if is_historical else "despacho_corpus_fragmentos"
            
            frag_query = f"document_id=eq.{actual_doc_id}&order=ordinal.asc&select=document_id,document_version,ordinal,segment,content,section"
            if is_historical:
                frag_query += f"&document_version=eq.{version}"
            if q and q.strip():
                clean_q = re.sub(r"[^\w\s\-\.]", "", q.strip())
                if clean_q:
                    frag_query += f"&content=ilike.*{clean_q}*"

            frags_res = await client.get(
                f"{base}/rest/v1/{target_table}?{frag_query}",
                headers=headers
            )
            if frags_res.status_code >= 400:
                raise HTTPException(502, f"Error consultando fragmentos: {frags_res.text}")

            crange = frags_res.headers.get("content-range")
            total = int(crange.split("/")[1]) if (crange and "/" in crange) else len(frags_res.json())
            raw_items = frags_res.json()
            items = []
            for it in raw_items:
                c = it.get("content", "")
                items.append({
                    "ordinal": it.get("ordinal"),
                    "segment": it.get("segment"),
                    "content": c,
                    "section": it.get("section") or "seccion_desconocida",
                    "char_length": len(c),
                    "document_version": it.get("document_version", 1),
                })

            doc_meta = doc_data.get("metadata") or {}
            return {
                "document": {
                    "id": actual_doc_id,
                    "title": doc_data.get("title"),
                    "source_url": doc_data.get("source_url"),
                    "source_id": doc_data.get("source_id"),
                    "version": version if is_historical else doc_data.get("version", 1),
                    "is_historical_version": is_historical,
                    "active_version": doc_data.get("version", 1),
                    "workflow_status": doc_data.get("workflow_status", "published"),
                    "integrity_status": doc_data.get("integrity_status", "complete"),
                    "coverage_pct": doc_meta.get("coverage_pct", 100.0),
                    "classification_method": doc_meta.get("classification_method", "automatic_structural_heuristic"),
                    "metadata": doc_meta,
                    "kind": "official"
                },
                "fragments": items,
                "total": total,
                "offset": offset,
                "limit": limit,
                "has_more": (offset + len(items)) < total
            }

        else:
            if not doc_id:
                raise HTTPException(422, "Se requiere document_id para consultar fragmentos del DMS.")
            doc = await store.fetch_item(user_id, token, doc_id, kind="document")
            frag_query = f"document_id=eq.{doc_id}&owner_id=eq.{user_id}&order=ordinal.asc&select=document_id,document_version,ordinal,segment,page,content"
            if q and q.strip():
                clean_q = re.sub(r"[^\w\s\-\.]", "", q.strip())
                if clean_q:
                    frag_query += f"&content=ilike.*{clean_q}*"

            frags_res = await client.get(
                f"{base}/rest/v1/despacho_indice?{frag_query}",
                headers=headers
            )
            if frags_res.status_code >= 400:
                raise HTTPException(502, f"Error consultando índice DMS: {frags_res.text}")

            crange = frags_res.headers.get("content-range")
            total = int(crange.split("/")[1]) if (crange and "/" in crange) else len(frags_res.json())
            raw_items = frags_res.json()

            from app.services.despacho_rag import classify_legal_section
            items = []
            for it in raw_items:
                c = it.get("content", "")
                items.append({
                    "ordinal": it.get("ordinal"),
                    "segment": it.get("segment"),
                    "page": it.get("page"),
                    "content": c,
                    "section": classify_legal_section(c, doc.get("title", "")).value,
                    "char_length": len(c),
                    "document_version": it.get("document_version", 1),
                })

            return {
                "document": {
                    "id": doc_id,
                    "title": doc.get("title"),
                    "version": doc.get("version", 1),
                    "kind": "document"
                },
                "fragments": items,
                "total": total,
                "offset": offset,
                "limit": limit,
                "has_more": (offset + len(items)) < total
            }
