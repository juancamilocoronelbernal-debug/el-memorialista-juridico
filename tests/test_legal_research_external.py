"""Investigación jurídica externa: referencia del proveedor != fuente oficial verificada."""
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.routers import despacho_knowledge as router
from app.services import despacho_ai as ai
from app.services import despacho_legal_research as legal

OFFICIAL = 'https://www.corteconstitucional.gov.co/relatoria/2025/t-100-25.htm'
OUTSIDE = 'https://www.ejemplo.org/publicacion'


def test_references_are_only_importable_when_allowed_and_never_auto_verified():
    official = legal.classify_source({'id': 'W1', 'url': OFFICIAL, 'title': 'Decisión',
                                      'support_text': 'Una frase citada por la búsqueda'})
    assert official['importable'] is True
    assert official['document_verified'] is False
    assert 'no comprobado' in official['status']
    external = legal.classify_source({'id': 'W2', 'url': OUTSIDE, 'title': 'Nota'})
    assert external['importable'] is False
    assert external['document_verified'] is False
    assert legal.classify_source({'url': 'http://127.0.0.1/private'}) is None
    assert legal.classify_source({'url': 'javascript:alert(1)'}) is None


@pytest.mark.asyncio
async def test_research_uses_grounded_provider_without_private_files_or_storage(monkeypatch):
    call = AsyncMock(return_value={
        'answer': 'La competencia depende de la vía.', 'model': 'gemini-3.6-flash',
        'provider': 'gemini', 'search_performed': True,
        'sources': [
            {'id': 'W1', 'url': OFFICIAL, 'title': 'Documento oficial'},
            {'id': 'W2', 'url': OUTSIDE, 'title': 'Artículo externo'},
            {'id': 'W3', 'url': OFFICIAL, 'title': 'Duplicado'},
            {'id': 'W4', 'url': 'http://internal.local', 'title': 'Interno'},
        ], 'warnings': [], 'search_queries': ['vías Bucaramanga jurisprudencia'],
    })
    monkeypatch.setattr(ai, '_call_provider', call)
    result = await legal.investigate('competencia sobre las vías de Bucaramanga', 'Santander')
    assert result['storage_modified'] is False
    assert len(result['sources']) == 2
    assert result['sources'][0]['importable'] and not result['sources'][1]['importable']
    assert all(not x['document_verified'] for x in result['sources'])
    assert 'competencia sobre las vías' in call.await_args.args[0][0][1]
    assert call.await_args.kwargs == {'mode': 'research', 'search': True}
    assert 'Santander' in call.await_args.args[0][0][1]


@pytest.mark.asyncio
async def test_no_grounding_sources_causes_prominent_disclaimer(monkeypatch):
    monkeypatch.setattr(ai, '_call_provider', AsyncMock(return_value={
        'answer': 'Análisis sin fuentes', 'sources': [], 'warnings': [], 'search_performed': False,
    }))
    result = await legal.investigate('criterios sobre derechos de petición')
    assert result['sources'] == []
    assert any('no acredita jurisprudencia' in w for w in result['warnings'])


@pytest.mark.parametrize('query,territory', [('a', ''), ('a' * 3001, ''), ('texto de doce o más', 'x' * 121)])
@pytest.mark.asyncio
async def test_bad_query_is_rejected_before_call(monkeypatch, query, territory):
    call = AsyncMock()
    monkeypatch.setattr(ai, '_call_provider', call)
    with pytest.raises(HTTPException) as exc:
        await legal.investigate(query, territory)
    assert exc.value.status_code == 422
    call.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_checks_original_without_storing_it(monkeypatch):
    fetch = AsyncMock(return_value={'url': OFFICIAL, 'title': 'Providencia', 'mime': 'text/html',
                                    'text': 'Decisión de la Corte Constitucional', 'warnings': []})
    monkeypatch.setattr(legal, 'fetch_source', fetch)
    result = await legal.verify_source(OFFICIAL)
    assert result['document_retrieved'] is True
    assert result['legal_validity_checked'] is False
    assert result['excerpt'].startswith('Decisión')
    fetch.assert_awaited_once()
    with pytest.raises(HTTPException) as exc:
        await legal.verify_source('https://127.0.0.1/secrets')
    assert exc.value.status_code == 422
    fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_research_timeout_has_specific_message(monkeypatch):
    async def timeout(*args, **kwargs):
        raise TimeoutError()
    monkeypatch.setattr(ai, '_call_provider', timeout)
    with pytest.raises(HTTPException) as exc:
        await legal.investigate('problema jurídico largo suficiente')
    assert exc.value.status_code == 504


def test_models_validate_research_request():
    assert router.ResearchRequest(query='Investigación de vías del municipio').query
    with pytest.raises(Exception):
        router.ResearchRequest(query='hola')
    with pytest.raises(Exception):
        router.VerifySourceRequest(url='x' * 2049)

@pytest.mark.asyncio
async def test_research_route_requires_authenticated_identity(monkeypatch):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    app = FastAPI()
    app.include_router(router.router)
    research = AsyncMock(return_value={'answer': 'OK', 'sources': []})
    monkeypatch.setattr(legal, 'investigate', research)
    # Identity verification errors must prevent any call to Gemini.
    async def unauthorized(request):
        raise HTTPException(401, 'Se requiere una sesión válida.')
    monkeypatch.setattr(router, 'identity', unauthorized)
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
        response = await client.post('/api/despacho/knowledge/research', json={
            'query': 'Competencia para reparar vías municipales'})
    assert response.status_code == 401
    research.assert_not_awaited()


@pytest.mark.asyncio
async def test_authenticated_research_route_does_not_change_library(monkeypatch):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    app = FastAPI()
    app.include_router(router.router)
    monkeypatch.setattr(router, 'identity', AsyncMock(return_value=('00000000-0000-4000-8000-000000000001', 'jwt')))
    monkeypatch.setattr(router.limitador, 'verificar', lambda *a, **k: None)
    research = AsyncMock(return_value={'answer': 'Revisión requerida', 'sources': [], 'storage_modified': False})
    monkeypatch.setattr(legal, 'investigate', research)
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
        response = await client.post('/api/despacho/knowledge/research', json={
            'query': 'Competencia para reparar vías municipales', 'territory': 'Bucaramanga'})
    assert response.status_code == 200
    assert response.json()['storage_modified'] is False
    assert research.await_args.args == ('Competencia para reparar vías municipales', 'Bucaramanga')
