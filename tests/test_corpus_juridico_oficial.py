"""Contrato del directorio, conexión de metadatos y búsqueda compartida."""
import json
import httpx
import pytest
from fastapi import HTTPException

from app.services import despacho_corpus_fuentes as c
from scripts.ingestar_corpus_juridico import _host_allowed_for_source, make_chunks


def test_catalogo_identifica_realmente_cobertura():
    data=c.catalog()
    ids=[x['id'] for x in data]
    assert len(ids)==len(set(ids))
    assert len(data)==43       # 41 propuestas + SUIN y Función Pública
    assert sum(x['access']=='metadata_api' for x in data)==1
    assert all(x['indexed'] is False for x in data)
    assert next(s for s in data if s['id']=='juzgados_municipales')['portal_url'] is None
    assert next(s for s in data if s['id']=='constitucional')['access']=='metadata_api'


def test_consulta_socrata_no_acepta_where_libre():
    q=c._soda_where("T-100/24")
    assert "upper(sentencia)" in q
    with pytest.raises(HTTPException): c._soda_where("Judicial') OR 1=1 --")
    with pytest.raises(HTTPException): c._soda_where("%")
    with pytest.raises(HTTPException): c._soda_where("x")
    with pytest.raises(HTTPException): c._soda_where("sentencia",1991)


@pytest.mark.asyncio
async def test_metadatos_officiales_sin_asegurar_texto(monkeypatch):
    params_seen=[]
    class Client:
        def __init__(self, **kwargs):
            assert kwargs['follow_redirects'] is False
            assert kwargs['trust_env'] is False
        async def __aenter__(self): return self
        async def __aexit__(self,*args): return None
        async def get(self,url,*,params,headers):
            params_seen.append((url,params))
            request=httpx.Request('GET',url)
            return httpx.Response(200, request=request, json=[{'sentencia':'T-100/24',
                'fecha_sentencia':'2024-01-01T00:00:00','magistrado_a':'Ponente ficticio'}])
    monkeypatch.setattr(c.httpx,'AsyncClient',Client)
    result=await c.constitutional_metadata('T-100/24')
    assert result['items'][0]['citation']=='T-100/24'
    assert result['items'][0]['metadata_confirmed'] is True
    assert result['items'][0]['full_text_retrieved'] is False
    assert 'www.datos.gov.co' in params_seen[0][0]
    assert '$where' in params_seen[0][1]


@pytest.mark.asyncio
async def test_corpus_consulta_solo_rpc_compartida(monkeypatch):
    capture=[]
    async def db(method,path,token,**kwargs):
        capture.append((method,path,token,kwargs))
        if path.endswith('estado_corpus_publicado'):
            return {'published_documents':0,'published_sources':0,'indexed_fragments':0}
        return [{'title':'Decisión ficticia','excerpt':'Fuente revisada','source_url':'https://www.corteconstitucional.gov.co/relatoria/2024/T-100-24.htm',
                 'source_id':'constitucional','method':'text','document_version':1,'segment':1}]
    monkeypatch.setattr(c.store,'db_request',db)
    monkeypatch.setattr(c,'embedding_status',lambda: {'configured':False})
    result=await c.search_corpus('jwt-de-usuario','reparación directa',semantic=False)
    assert result['scope']=='shared_official'
    assert len(result['results'])==1
    assert capture[0][1]=='rpc/despacho_consultar_corpus_publicado'
    assert capture[0][2]=='jwt-de-usuario'
    assert c.DATASET_URL not in str(capture)
    status=await c.corpus_status('jwt-de-usuario')
    assert status['published_documents']==0


def test_ingestor_solo_fuente_revisada_y_pdf_extenso():
    sources={x['id']:x for x in c.catalog()}
    assert _host_allowed_for_source(sources['constitucional'],'https://www.corteconstitucional.gov.co/relatoria/2024/T-100-24.htm')
    assert not _host_allowed_for_source(sources['constitucional'],'https://www.dian.gov.co/fake')
    assert not _host_allowed_for_source(sources['unat'],'https://example.org/documento')
    assert len(make_chunks('ABC. '*200))>=1
    with pytest.raises(ValueError): make_chunks('hola')


def test_sql_no_publica_sin_revision_y_rls():
    from pathlib import Path
    migration=(Path(__file__).parents[1]/'supabase/migrations/20261023130000_corpus_juridico_compartido.sql').read_text()
    assert 'ENABLE ROW LEVEL SECURITY' in migration
    assert 'published = true' in migration
    assert 'TO service_role' in migration
    assert 'REVOKE ALL ON FUNCTION public.despacho_publicar_documento_corpus' in migration
    assert 'GRANT EXECUTE ON FUNCTION public.despacho_publicar_documento_corpus' in migration
    assert 'TO authenticated' not in migration.split('GRANT EXECUTE ON FUNCTION public.despacho_publicar_documento_corpus')[1].split(';')[0]


def test_rutas_corpus_rechazan_visitas_sin_sesion():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        assert client.get('/api/despacho/official/sources').status_code in (401, 403)
        assert client.get('/api/despacho/official/status').status_code in (401, 403)
        assert client.post('/api/despacho/official/search',json={'query':'reparación directa'}).status_code in (401, 403)
        assert client.post('/api/despacho/official/constitutional-metadata',json={'query':'T-100/24'}).status_code in (401, 403)


@pytest.mark.asyncio
async def test_agente_recupera_contexto_corpus_oficial(monkeypatch):
    from app.services import despacho_ai as ai
    from app.services import despacho_corpus_fuentes as official

    async def fake_search(token, query, limit=16, semantic=True):
        return {
            'results': [
                {'title': 'Sentencia T-100/24', 'excerpt': 'Protección a la maternidad en servicio militar.',
                 'source_url': 'https://www.corteconstitucional.gov.co/relatoria/2024/T-100-24.htm',
                 'source_id': 'constitucional', 'date': '2024-04-05', 'version': 1, 'segment': 3,
                 'score': 0.03, 'method': 'hybrid'}
            ],
            'method': 'hybrid',
            'warnings': []
        }

    async def fake_status(token):
        return {'published_documents': 1, 'published_sources': 1, 'indexed_fragments': 41}

    monkeypatch.setattr(official, 'search_corpus', fake_search)
    monkeypatch.setattr(official, 'corpus_status', fake_status)

    context = {'payload': [], 'passages': [], 'sources': [], 'coverage': {'document_ids': []}, 'warnings': []}
    res_ctx = await ai.augment_indexed_context('user-1', 'jwt-test', {'message': 'T-100/24 maternidad', 'knowledge_scope': 'official'}, context)

    assert len(res_ctx['passages']) == 1
    assert res_ctx['passages'][0]['id'] == 'O1-S3'
    assert res_ctx['passages'][0]['kind'] == 'official'
    assert len(res_ctx['sources']) == 1
    assert res_ctx['sources'][0]['id'] == 'O1-S3'
    assert res_ctx['sources'][0]['kind'] == 'official'
    assert res_ctx['coverage']['scope'] == 'official'
    assert res_ctx['coverage']['official_documents'] == 1
    assert res_ctx['coverage']['retrieved_passages'] == 1
    assert res_ctx['coverage']['selected_passages'] == 1


def test_esquema_chat_admite_official_scope():
    from app.routers.despacho_ai import ChatRequest
    req = ChatRequest(message="Consulta oficial", knowledge_scope="official")
    assert req.knowledge_scope == "official"

