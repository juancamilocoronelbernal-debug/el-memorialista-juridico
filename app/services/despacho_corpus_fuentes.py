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

    # RAG 2.0: Clasificación de secciones y reranking jurídico opcional
    if getattr(get_settings(), "DESPACHO_RAG_V2_ENABLED", True) and rows:
        try:
            from app.services import despacho_rag
            for row in rows:
                row["section"] = despacho_rag.classify_legal_section(row["excerpt"], row.get("title") or "").value
            intent_info = despacho_rag.classify_query_intent(query)
            d_key = depth if depth in despacho_rag.DEPTH_PROFILES else intent_info["suggested_depth"]
            profile = despacho_rag.DEPTH_PROFILES[d_key]
            rows = despacho_rag.rerank_candidates(rows, query, intent_info, profile)
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
