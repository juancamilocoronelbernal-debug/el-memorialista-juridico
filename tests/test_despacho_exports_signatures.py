"""Contratos reales de exportación, enlaces y permisos. Sin cuentas externas."""
import hashlib
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock
from xml.etree import ElementTree

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.config import get_settings
from app.main import app
from app.routers import despacho_signatures as signatures
from app.services import supabase_service
from app.services.despacho_export import make_docx, make_pdf

OWNER = '11111111-1111-4111-8111-111111111111'
DOC = '22222222-2222-4222-8222-222222222222'
TOKEN = 'private-test-access'
BASE = Path(__file__).resolve().parents[1]


@pytest.fixture
def signed_client(monkeypatch):
    async def validate(token):
        return {'id': OWNER, 'email':'abogada@example.test'} if token == TOKEN else None
    monkeypatch.setattr(supabase_service,'validar_token_supabase',validate)
    settings=get_settings()
    for key,value in {'SUPABASE_URL':'https://project.supabase.test','SUPABASE_ANON_KEY':'public-key',
                      'SUPABASE_SERVICE_ROLE_KEY':'server-only-secret','APP_BASE_URL':'https://memorialista.example',
                      'DESPACHO_SIGNING_ENABLED':True}.items():
        monkeypatch.setattr(settings,key,value)
    signatures._attempts.clear()
    return TestClient(app,headers={'Authorization':'Bearer '+TOKEN})


def test_docx_is_editable_safe_xml_and_preserves_characters():
    text='MARÍA ÑANDÚ & ASOCIADOS\n<prueba> & "contrato"\nÁÉÍÓÚ ¿Qué?\nFIN DEL DOCUMENTO'
    blob=make_docx('Revisión jurídica',text)
    with zipfile.ZipFile(io.BytesIO(blob)) as package:
        assert set(package.namelist()) == {'[Content_Types].xml','_rels/.rels','word/document.xml','word/styles.xml','word/_rels/document.xml.rels'}
        root=ElementTree.fromstring(package.read('word/document.xml'))
        actual='\n'.join(root.itertext())
        for line in text.splitlines(): assert line in actual
        assert not root.findall('.//prueba')


def test_pdf_multpage_unicode_and_end_marker():
    text='MARÍA ÑANDÚ & CÍA\n'+('\n'.join('Hecho %s. La comunicación contiene información jurídica íntegra.'%i for i in range(160)))+'\nÚLTIMA LÍNEA: devolución y comprobación.'
    reader=PdfReader(io.BytesIO(make_pdf('Escrito de prueba',text)))
    assert len(reader.pages)>=3
    actual='\n'.join(page.extract_text() for page in reader.pages)
    assert 'MARÍA ÑANDÚ' in actual and 'ÚLTIMA LÍNEA' in actual and 'Hecho 159' in actual
    assert '\ufffd' not in actual


def test_pdf_rejects_unsupported_script_instead_of_corrupting():
    with pytest.raises(HTTPException) as exc:
        make_pdf('Documento','Prueba con escritura 中文')
    assert exc.value.status_code==422
    assert 'DOCX' in exc.value.detail


@pytest.mark.parametrize('method,path',[
    ('GET','/api/despacho/items'),('POST','/api/despacho/chat'),('POST','/api/despacho/tables/analyze'),
    ('GET','/api/despacho/signatures'),('POST','/api/despacho/signatures'),('GET','/api/despacho/export'),
    ('POST','/api/despacho/export/document'),('POST','/api/despacho/documents/upload'),
])
def test_new_modules_are_private_before_parsing(method,path):
    response=TestClient(app).request(method,path,json={})
    assert response.status_code==401
    assert 'no-store' in response.headers['cache-control']


@pytest.mark.parametrize('path',['/app/assets/despacho.js','/app/assets/despacho.css'])
def test_private_assets_need_session(path):
    assert TestClient(app).get(path).status_code==401


def test_private_ui_not_mounted_as_static():
    client=TestClient(app)
    for path in ['/static/despacho.html','/static/despacho.js','/private/despacho.html']:
        assert client.get(path).status_code==404


def test_pdf_endpoint_requires_real_body_and_returns_binary(signed_client):
    result=signed_client.post('/api/despacho/export/document',json={'title':'Prueba','text':'El documento solicitado.','format':'pdf'})
    assert result.status_code==200 and result.content.startswith(b'%PDF')
    assert 'attachment' in result.headers['content-disposition']
    assert 'El documento solicitado' in PdfReader(io.BytesIO(result.content)).pages[0].extract_text()


def test_create_link_uses_hash_and_fragment_not_token_in_database(signed_client,monkeypatch):
    rpc=AsyncMock(return_value={'id':DOC,'title':'Contrato','status':'pending'})
    monkeypatch.setattr(signatures,'_rpc',rpc)
    result=signed_client.post('/api/despacho/signatures',json={'title':'Contrato','text':'Texto aprobado','signer_name':'Persona Prueba','signer_email':'PERSONA@example.test'})
    assert result.status_code==200
    link=result.json()['signing_url']
    assert link.startswith('https://memorialista.example/firmar#')
    secret=link.split('#')[1]
    assert len(secret)==43
    payload=rpc.call_args.args[1]
    assert payload['p_token_hash']==hashlib.sha256(secret.encode()).hexdigest()
    assert secret not in json.dumps(payload)
    assert payload['p_email']=='persona@example.test'
    assert rpc.call_args.args[2]==TOKEN


def test_unconfigured_signature_does_not_create_record(signed_client,monkeypatch):
    monkeypatch.setattr(get_settings(),'SUPABASE_SERVICE_ROLE_KEY','')
    rpc=AsyncMock();monkeypatch.setattr(signatures,'_rpc',rpc)
    result=signed_client.post('/api/despacho/signatures',json={'title':'Contrato','text':'Texto','signer_name':'Persona','signer_email':'persona@example.test'})
    assert result.status_code==503
    rpc.assert_not_called()


def test_signature_domain_validated_before_write(signed_client,monkeypatch):
    monkeypatch.setattr(get_settings(),'APP_BASE_URL','https://attacker.example/?x=1')
    rpc=AsyncMock();monkeypatch.setattr(signatures,'_rpc',rpc)
    result=signed_client.post('/api/despacho/signatures',json={'title':'Contrato','text':'Texto','signer_name':'Persona','signer_email':'persona@example.test'})
    assert result.status_code==503;rpc.assert_not_called()


def test_public_signature_without_valid_token_has_no_rpc(monkeypatch):
    rpc=AsyncMock();monkeypatch.setattr(signatures,'_rpc',rpc)
    client=TestClient(app)
    assert client.post('/api/firmas-publicas/ver',json={'token':'guess'}).status_code==422
    assert client.get('/api/firmas-publicas/ver').status_code==401
    rpc.assert_not_called()


def test_public_acceptance_requires_consent_and_records_server_ip(signed_client,monkeypatch):
    rpc=AsyncMock(return_value={'id':DOC,'status':'signed'});monkeypatch.setattr(signatures,'_rpc',rpc)
    client=TestClient(app)
    body={'token':'A'*43,'name':'Persona Prueba','email':'persona@example.test','consent':False}
    assert client.post('/api/firmas-publicas/aceptar',json=body).status_code==422
    rpc.assert_not_called()
    body['consent']=True
    response=client.post('/api/firmas-publicas/aceptar',json=body,headers={'X-Forwarded-For':'1.2.3.4','User-Agent':'test-agent'})
    assert response.status_code==200
    payload=rpc.call_args.args[1]
    assert payload['p_ip']!='1.2.3.4'
    assert payload['p_agent']=='test-agent'
    assert rpc.call_args.kwargs['admin'] is True
    assert 'A'*43 not in json.dumps(payload)


def test_public_form_contains_no_document_or_private_navigation():
    result=TestClient(app).get('/firmar')
    assert result.status_code==200
    assert "script-src 'self'" in result.headers['content-security-policy']
    assert 'no-store' in result.headers['cache-control']
    assert '/api/despacho/items' not in result.text


def test_signature_receipt_contains_exact_document_and_identification_method(signed_client,monkeypatch):
    record={'id':DOC,'title':'Acuerdo','document_text':'MARÍA acepta un acuerdo.','document_hash':'f'*64,
            'status':'signed','signed_at':'2026-10-23T04:00:00Z','signed_name':'María','signed_email':'m@example.test',
            'consent_text':'He leído y acepto.','signer_ip':'203.0.113.4'}
    monkeypatch.setattr(signatures,'_owned',AsyncMock(return_value=record))
    result=signed_client.get('/api/despacho/signatures/'+DOC+'/receipt')
    assert result.status_code==200
    text=''.join(page.extract_text() for page in PdfReader(io.BytesIO(result.content)).pages)
    assert 'MARÍA acepta un acuerdo.' in text
    assert 'identidad declarada' in text
    assert 'SHA-256' in text and 'no comparte la misma huella' in ' '.join(text.split())


def test_word_manifest_and_embed_boundary(signed_client):
    response=signed_client.get('/word/manifest.xml')
    assert response.status_code==200
    root=ElementTree.fromstring(response.content)
    assert 'https://memorialista.example/word' in response.text
    assert 'ReadWriteDocument' in response.text and 'MinVersion="1.4"' in response.text
    response=signed_client.get('/word')
    assert 'x-frame-options' not in response.headers
    assert "https://*.officeapps.live.com" in response.headers['content-security-policy']
    assert 'server-only-secret' not in response.text


def test_sql_signature_transition_permissions_and_immutable_hash():
    sql=(BASE/'supabase/migrations/20261023020000_firma_electronica.sql').read_text()
    assert 'enable row level security' in sql
    assert 'grant select on public.despacho_firmas to authenticated' in sql
    assert 'grant insert' not in sql and 'grant update' not in sql
    assert 'for update' in sql
    assert 'sha256(convert_to(p_text' in sql
    assert 'public.despacho_aceptar_firma(text,text,text,text,text,boolean) to service_role' in sql
    assert 'p_token_hash text)' in sql


def test_request_size_rejected_before_large_parse():
    response=TestClient(app).post('/api/despacho/chat',headers={'Content-Length':str(32*1024*1024)},content=b'{}')
    assert response.status_code==413


@pytest.mark.parametrize('origin',[
    'https://memorialista.example:invalid','https://memorialista.example:99999',
    'https://[invalid','https://memorialista.example\n.evil.example',
    'https://user@memorialista.example','https://memorialista.example/otro',
    'https://bad<host>.example','https://memorialista.example:0',
])
def test_malformed_canonical_origin_is_rejected_without_writing(signed_client,monkeypatch,origin):
    monkeypatch.setattr(get_settings(),'APP_BASE_URL',origin)
    rpc=AsyncMock();monkeypatch.setattr(signatures,'_rpc',rpc)
    response=signed_client.post('/api/despacho/signatures',json={
        'title':'Contrato','text':'Documento','signer_name':'Persona','signer_email':'p@example.test'})
    assert response.status_code==503
    rpc.assert_not_called()


def test_host_header_cannot_replace_configured_origin_even_in_development(signed_client,monkeypatch):
    monkeypatch.setattr(get_settings(),'APP_BASE_URL','')
    monkeypatch.setattr(get_settings(),'ENVIRONMENT','development')
    response=signed_client.get('https://attacker.example/word/manifest.xml')
    assert response.status_code==503
    local=signed_client.get('/word/manifest.xml')
    assert local.status_code==200 and 'http://testserver/word' in local.text


@pytest.mark.parametrize('fields',[
    {'title':'   '},{'text':'\n\t '},{'signer_name':'\x00Persona'},
    {'signer_email':'p\x00@example.test'},
])
def test_invalid_signature_text_is_rejected_before_rpc(signed_client,monkeypatch,fields):
    rpc=AsyncMock();monkeypatch.setattr(signatures,'_rpc',rpc)
    body={'title':'Contrato','text':'Documento','signer_name':'Persona','signer_email':'p@example.test'}
    body.update(fields)
    assert signed_client.post('/api/despacho/signatures',json=body).status_code==422
    rpc.assert_not_called()


def test_signature_sql_quota_and_expiration_are_serialized():
    # Contrato estático complementario: la ejecución de PostgreSQL/RLS en la
    # instalación de destino sigue siendo una comprobación independiente.
    sql=(BASE/'supabase/migrations/20261023020000_firma_electronica.sql').read_text()
    assert "pg_advisory_xact_lock(hashtextextended('despacho_firmas:'" in sql
    assert sql.index('pg_advisory_xact_lock') < sql.index('if (select count(*)')
    assert sql.count("r.expires_at<=clock_timestamp()") == 2
    assert 'p_name is null or p_email is null' in sql


def test_word_limits_failure_restoration_and_logout_race():
    import shutil
    import subprocess
    node=shutil.which('node')
    if not node:
        pytest.skip('Node no está disponible para verificar el complemento Word.')
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const elements=new Map();
function element(id){if(!elements.has(id))elements.set(id,{value:'',textContent:'',hidden:false,disabled:false,handlers:{},classList:{toggle(){}},addEventListener(event,callback){this.handlers[event]=callback;}});return elements.get(id);}
let selectionText='Original de prueba', pending=null, failWrite=false, lastPayload, deferred=null;
let account={user:{id:'owner'},access_token:'test-jwt'};
const client={auth:{getSession:async()=>({data:{session:account}}),onAuthStateChange(){},signOut:async()=>{account=null;return{};}}};
const documentModel={changeTrackingMode:'off',load(){},getSelection(){return range;}};
const range={get text(){return selectionText;},load(){},insertText(value){pending=value;}};
const context={document:documentModel,trackedObjects:{add(){},remove(){}},async sync(){if(pending!==null){if(failWrite){pending=null;failWrite=false;throw new Error('Fallo controlado de inserción');}selectionText=pending;pending=null;}}};
const Word={run:async(...args)=>args.at(-1)(context),ChangeTrackingMode:{trackAll:'trackAll'},InsertLocation:{replace:'replace'}};
const Office={HostType:{Word:'Word'},context:{requirements:{isSetSupported:()=>true}},onReady:async()=>({host:'Word'})};
const sandbox={document:{getElementById:element},Word,Office,MemAuth:{init:async()=>({client}),establish:async()=>({}),clearCookie:async()=>{},message:e=>e.message},AbortController,FormData,console,
fetch:async(_url,options)=>{lastPayload=JSON.parse(options.body);if(deferred)return deferred.promise;return {ok:true,json:async()=>({answer:'Propuesta revisada'})};}};
sandbox.window=sandbox;vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const click=id=>element(id).handlers.click();
(async()=>{
 await tick();selectionText='x'.repeat(70001);await click('read');assert.match(element('status').textContent,/70\.000/);
 selectionText='x'.repeat(70000);await click('read');element('instruction').value='i'.repeat(6000);await click('analyze');assert.ok(lastPayload.message.length<=80000);
 failWrite=true;await click('apply');assert.equal(documentModel.changeTrackingMode,'off');assert.match(element('status').textContent,/Fallo controlado/);
 selectionText='Contenido privado';await click('read');element('instruction').value='Mejora el texto';
 let resolve;deferred={promise:new Promise(r=>resolve=r)};const running=click('analyze');await tick();await click('logout');
 resolve({ok:true,json:async()=>({answer:'RESPUESTA PRIVADA TARDÍA'})});await running;
 assert.equal(element('proposal').value,'');assert.equal(element('selection').value,'');assert.equal(element('work').hidden,true);
 console.log('Word: límites, restauración y cierre verificados');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result=subprocess.run([node,'-e',script,str(BASE/'app/static/word/word.js')],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
