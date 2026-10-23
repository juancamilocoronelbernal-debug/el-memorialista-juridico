"""Carga administrativa EXPLÍCITA de UN original jurídico oficial al corpus compartido.

Ejemplo (sólo después de revisar permisos y datos):
 python scripts/ingestar_corpus_juridico.py --source-id constitucional \
   --url 'https://www.corteconstitucional.gov.co/relatoria/2024/T-100-24.htm' \
   --title 'Sentencia T-100/24' \
   --ack-rights-review --ack-privacy-review --ack-content-review

NO realiza crawling masivo, NO acepta contenido privado y NO usa Google Search.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services import despacho_corpus_fuentes as official
from app.services import despacho_store as store
from app.services.despacho_fetch import fetch_source, validate_url
from app.services.despacho_knowledge import CHUNK_SIZE, CHUNK_OVERLAP, embed_texts, embedding_status


def _host_allowed_for_source(source: dict, url: str) -> bool:
    host = (urlsplit(url).hostname or '').lower()
    source_host = (urlsplit(source.get('portal_url') or '').hostname or '').lower()
    if not source_host:
        return False
    def origin_domain(hostname):
        return hostname.removeprefix('www.')
    # La lista se limita al dominio del organismo declarado para impedir
    # etiquetar materiales de un sitio ajeno con la autoridad de otra fuente.
    source_base = origin_domain(source_host)
    allowed_extra = {'constitucional': ('corteconstitucional.gov.co',),
                     'consejo_estado': ('consejodeestado.gov.co',),
                     'consejo_historico': ('consejodeestado.gov.co',)}
    domains = allowed_extra.get(source['id'], (source_base,))
    return any(host == domain or host.endswith('.' + domain) for domain in domains)


def make_chunks(text: str) -> list[dict]:
    text = text.replace('\x00', '').strip()
    if not 450 <= len(text) <= 300_000:
        raise ValueError('El original debe tener entre 450 y 300.000 caracteres; no se admiten fichas vacías o portadas.')
    parts = []
    for i in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP):
        chunk = text[i:i + CHUNK_SIZE].strip()
        if chunk:
            parts.append({'content': chunk, 'embedding': None, 'embedding_model': None})
        if i + CHUNK_SIZE >= len(text):
            break
    if len(parts) > 200:
        raise ValueError('Demasiados fragmentos; divide el documento antes de publicar.')
    return parts


async def ingest(source_id: str, url: str, title: str, *, semantic: bool = False) -> dict:
    source = next((x for x in official.catalog() if x['id'] == source_id), None)
    if not source:
        raise ValueError('Identificador de colección desconocido.')
    validated = validate_url(url)
    if not _host_allowed_for_source(source, validated):
        raise ValueError('La URL no corresponde al dominio del organismo seleccionado.')
    # Impedir importar portada genérica como una sentencia/jurisprudencia.
    if urlsplit(validated).path.strip('/') in ('', 'index.html', 'index.php'):
        raise ValueError('Selecciona un documento concreto, no la portada de una institución.')
    data = await fetch_source(validated)
    chunks = make_chunks(data['text'])
    if data.get('extraction_coverage', {}).get('complete') is False or data.get('warnings'):
        raise ValueError('La extracción es incompleta o advierte errores. Revisa el original y prepara una copia legible.')
    if semantic:
        if not embedding_status()['configured']:
            raise ValueError('Embeddings no configurados. Ejecuta sin --semantic o habilita una clave válida.')
        for i in range(0, len(chunks), 24):
            batch = chunks[i:i+24]
            vectors = await embed_texts([c['content'] for c in batch])
            for c, vec in zip(batch, vectors):
                c.update(embedding=vec, embedding_model=get_settings().DESPACHO_EMBEDDING_MODEL)
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY.strip()
    if not key:
        raise ValueError('Falta la clave de servicio en el entorno del servidor (nunca en el navegador).')
    sha = hashlib.sha256(data['text'].encode('utf-8')).hexdigest()
    result = await store.db_request('POST', 'rpc/despacho_publicar_documento_corpus', key, service=True, json={
        'p_source_id': source_id, 'p_source_url': data['url'], 'p_title': title.strip()[:240],
        'p_hash': sha, 'p_chunks': chunks,
        'p_metadata': {'retrieved_url': data['url'], 'original_mime': data.get('mime'),
                       'origin': source['name'], 'rights_review': 'aprobada_por_administrador',
                       'personal_data_review': 'aprobada_por_administrador', 'coverage': 'documento_individual'}})
    if not isinstance(result, dict):
        raise RuntimeError('La base no confirmó la operación de publicación.')
    return {**result, 'source_id': source_id, 'sha256': sha, 'title': title[:240],
            'semantic': semantic, 'note': 'Publicación puntual y revisada; no implica cobertura integral del organismo.'}


def main():
    parser = argparse.ArgumentParser(description='Publicación puntual y revisada de un documento oficial')
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--title', required=True)
    parser.add_argument('--semantic', action='store_true', help='Usa cuota de Gemini para indexar por significado')
    parser.add_argument('--ack-rights-review', action='store_true', help='He revisado condiciones y permisos de reutilización')
    parser.add_argument('--ack-privacy-review', action='store_true', help='He revisado datos personales/sensibles')
    parser.add_argument('--ack-content-review', action='store_true', help='He comprobado que es un documento público relevante y legible')
    args = parser.parse_args()
    if not (args.ack_rights_review and args.ack_privacy_review and args.ack_content_review):
        parser.error('Se requieren las tres revisiones expresas antes de publicar contenido global.')
    try:
        print(json.dumps(asyncio.run(ingest(args.source_id, args.url, args.title, semantic=args.semantic)), ensure_ascii=False))
    except Exception as exc:
        print('Error de carga: ' + type(exc).__name__ + ': ' + str(exc)[:400], file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
