/**
 * UI V5 en Chromium: archivos de producción y respuestas HTTP controladas.
 * No utiliza Supabase, IA, correo ni personas reales. No instala modos demo en la app.
 * Verifica interacción, persistencia solicitada, estados de error, XSS, CSP y móvil.
 *
 * node --test tests/test_despacho_v5_browser.mjs
 * Opcionales: PLAYWRIGHT_MODULE, PLAYWRIGHT_CHROMIUM_EXECUTABLE, PYTHON_BIN (entorno backend),
 * DESPACHO_BROWSER_ARTIFACTS (capturas internas; no forman parte del ZIP).
 */
import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFile, mkdir, mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const imported=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const {chromium}=imported.default||imported;
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const publicCsp=execFileSync(process.env.PYTHON_BIN||'python',['-c',"from app.main import csp_archivo_publico,PRIVATE_DIR; print(csp_archivo_publico(PRIVATE_DIR / 'firma-v5.html').replace(\"frame-src 'none'\", \"frame-src 'self' blob:\"))"],{cwd:root,encoding:'utf8'}).trim();
const artifacts=process.env.DESPACHO_BROWSER_ARTIFACTS||await mkdtemp(path.join(tmpdir(),'memorialista-despacho-ui-'));
await mkdir(artifacts,{recursive:true});
const origin='http://memorialista.invalid';
// Misma política de recursos que la superficie privada, sin proveedores externos en esta prueba.
const csp="default-src 'none'; script-src 'self'; script-src-attr 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; media-src 'self' blob:; object-src 'none'; frame-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; worker-src 'self'; manifest-src 'self'";
let browser;
before(async()=>{browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}:{})});});
after(async()=>{await browser?.close();});

async function fixture(t,{viewport={width:1440,height:1000}}={}){
  const context=await browser.newContext({viewport,locale:'es-CO',timezoneId:'America/Bogota',acceptDownloads:true});
  t.after(()=>context.close());
  const page=await context.newPage();
  const state={items:[],signatures:[],errors:[],csp:[],requests:[],alerts:[],chatFailure:false,malicious:false,lastSignatureToken:0,jobs:[],schedules:[],connections:[{id:'connection-fixture',provider:'google_drive',label:'Cuenta ficticia',created_at:new Date().toISOString()}],envelopes:[],rooms:[],browserManual:false,browserApprovals:0};
  const stamp=()=>new Date().toISOString();
  const add=(kind,title,data={},matter_id=null)=>{const i={id:randomUUID(),kind,title,data,matter_id,version:1,created_at:stamp(),updated_at:stamp()};state.items.push(i);return i;};
  state.add=add;
  page.on('pageerror',e=>state.errors.push(e.message));
  page.on('dialog',async d=>{state.alerts.push(d.message());await d.dismiss();});
  page.on('console',m=>{if(m.type()==='error'&&/Content Security Policy|violates.*directive/i.test(m.text()))state.csp.push(m.text());});
  await page.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url()),p=url.pathname,method=request.method();
    let body;try{body=request.postDataJSON();}catch{}state.requests.push({p,method,body,headers:request.headers()});
    const json=(obj,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(obj)});
    const binary=(content='fixture bytes',mime='application/octet-stream')=>route.fulfill({status:200,contentType:mime,body:content});
    if(url.origin!==origin)return route.abort('blockedbyclient');
    if(p==='/app')return route.fulfill({contentType:'text/html',headers:{'Content-Security-Policy':csp,'Cache-Control':'no-store'},body:await readFile(root+'/app/private/despacho.html','utf8')});
    if(['/app/assets/despacho.js','/app/assets/despacho.css'].includes(p))return route.fulfill({contentType:p.endsWith('.js')?'application/javascript':'text/css',body:await readFile(root+'/app/private/'+p.split('/').pop(),'utf8')});
    if(p==='/static/vendor/supabase.js')return route.fulfill({contentType:'application/javascript',body:''});
    if(p==='/static/auth/session.js')return route.fulfill({contentType:'application/javascript',body:`window.MemAuth={init:async()=>({client:{auth:{getSession:async()=>({data:{session:{access_token:'fixture-only',user:{id:'00000000-0000-4000-8000-000000000001',email:'prueba@example.invalid',user_metadata:{name:'Cuenta ficticia de prueba'}}}}}),onAuthStateChange:()=>{},signOut:async()=>({}),refreshSession:async()=>({})}}}),establish:async()=>({}),clearCookie:async()=>{},message:e=>e.message}`});
    if(p==='/static/asesor/favicon.svg')return route.fulfill({status:204,body:''});
    if(p==='/api/despacho/capabilities')return json({storage:{ready:true,message:'Almacenamiento de prueba disponible'},ai:{configured:true},monitoring:{automatic:false,message:'Comprobación manual de prueba disponible'},signatures:{configured:true,enabled:true},signatures_v5:{supported:true,configured:true},automation_limits:{user_daily:100,global_daily:1000,reset_timezone:'UTC',unit:'logical_call'}});
    if(p==='/api/despacho/agent/status')return json({configured:!state.agentFailure,worker_enabled:false,browser:{configured:true,enabled:true,takeover_supported:true},tools:[]});
    if(p==='/api/despacho/agent/jobs'&&method==='GET')return json({items:state.jobs});
    if(p==='/api/despacho/agent/jobs'&&method==='POST'){
      if(state.agentFailure)return json({detail:'Configura un proveedor de IA y las tablas del agente.'},503);
      const b=request.postDataJSON();const j={id:randomUUID(),title:b.objective.slice(0,70),...b,state:'draft',version:1,cursor:0,results:[],plan:[{id:'s1',tool:'analyze',title:'Analizar contexto',instruction:'Revisar el texto aportado.'},{id:'s2',tool:'draft',title:'Preparar borrador',instruction:'Preparar texto para revisión.'}],created_at:stamp(),updated_at:stamp()};state.jobs.push(j);return json(j,201);
    }
    if(p.startsWith('/api/despacho/agent/jobs/')&&p.endsWith('/browser'))return json({active:true,manual:state.browserManual,url:'https://www.corteconstitucional.gov.co/',title:'Fuente de prueba',text:'Contenido de prueba <img src=x onerror=alert(1)>',controls:[{ref:'c1',name:'Buscar',role:'button',tag:'button',field_type:'',blocked:false},{ref:'c2',name:'Contraseña',role:'textbox',field_type:'password',blocked:true}],pending_action:state.proposal||null});
    if(p.endsWith('/browser/propose')){const j=state.jobs.find(j=>p.includes(j.id));j.version++;j.state='waiting_approval';state.proposal={...request.postDataJSON(),action_id:randomUUID(),label:'Buscar',url:'https://www.corteconstitucional.gov.co/',requires_approval:true};return json(state.proposal);}
    if(p.endsWith('/browser/approve')){const j=state.jobs.find(j=>p.includes(j.id)),b=request.postDataJSON();if(b.expected_version!==j.version)return json({detail:'Versión cambió'},409);state.browserApprovals++;state.proposal=null;j.version++;j.state='approved';return json({job:j,browser:{active:true}});}
    if(p.endsWith('/browser/close'))return json({closed:true});
    if(p.endsWith('/browser/takeover')){state.browserManual=true;const j=state.jobs.find(j=>p.includes(j.id));j.version++;j.state='waiting_approval';return json({manual:true,takeover_url:'https://www.browserbase.com/devtools/fixture',expires_in:60,message:'Control de prueba; el agente está pausado.'});}
    if(p.endsWith('/browser/resume')){state.browserManual=false;const j=state.jobs.find(j=>p.includes(j.id));j.version++;j.state='approved';return json({active:true,manual:false,controls:[]});}
    if(p.endsWith('/browser/downloads'))return json({items:[{id:'download-1',filename:'descarga-ficticia.txt',size:30,mime:'text/plain'}]});
    if(p.endsWith('/browser/downloads/download-1/save'))return json(add('document','descarga-ficticia.txt',{text:'Documento ficticio descargado.',versions:[]}));
    if(p.endsWith('/browser/downloads/download-1'))return binary('Documento ficticio descargado.','text/plain');
    if(p.startsWith('/api/despacho/agent/jobs/')&&p.endsWith('/events'))return json({items:[{at:stamp(),event:'plan_created',detail:'Plan de prueba preparado'}]});
    if(p.startsWith('/api/despacho/agent/jobs/')){
      const j=state.jobs.find(j=>j.id===p.split('/')[5]);if(!j)return json({detail:'Encargo no encontrado'},404);
      if(method==='GET')return json(j);const b=request.postDataJSON();if(b.expected_version!==j.version)return json({detail:'La versión del encargo cambió.'},409);
      if(p.endsWith('/plan')){j.plan=b.steps.map((s,i)=>({...s,id:'s'+(i+1)}));j.version++;return json(j);}
      if(p.endsWith('/approve')){j.state='approved';j.version++;return json(j);}
      if(p.endsWith('/cancel')){j.state='cancelled';j.version++;return json(j);}
      if(p.endsWith('/retry')){j.state='approved';j.version++;return json(j);}
      if(p.endsWith('/step')){if(state.stepFailure){j.state='failed';j.last_error='Proveedor temporalmente no disponible.';j.version++;return json(j);}const step=j.plan[j.cursor];j.results.push({step_id:step.id,tool:step.tool,title:step.title,result:{answer:'Resultado controlado del paso '+(j.cursor+1),warnings:[]}});j.cursor++;j.state=j.cursor>=j.plan.length?'completed':'running';j.version++;return json(j);}
    }
    if(p==='/api/despacho/agent/schedules'&&method==='GET')return json({items:state.schedules});
    if(p==='/api/despacho/agent/schedules'&&method==='POST'){const b=request.postDataJSON();const item={id:randomUUID(),version:1,title:state.jobs.find(j=>j.id===b.job_id)?.title,...b,next_run_at:b.next_run_at||stamp()};state.schedules.push(item);return json(item,201);}
    if(p.startsWith('/api/despacho/agent/schedules/')&&method==='PATCH'){const item=state.schedules.find(s=>s.id===p.split('/').pop());Object.assign(item,request.postDataJSON(),{version:item.version+1});return json(item);}
    if(p==='/api/despacho/connections')return json({providers:[{id:'google_drive',label:'Google Drive',configured:true,scopes:['drive.readonly']},{id:'microsoft_onedrive',label:'Microsoft OneDrive',configured:false,scopes:[]}],connections:state.connections});
    if(p.endsWith('/resources'))return json({items:[{id:'file-a',name:'Contrato de conexión.txt',type:'file',mime:'text/plain',size:123}],next_cursor:null});
    if(p.startsWith('/api/despacho/connections/')&&p.endsWith('/import'))return json({item:add('document','Contrato de conexión.txt',{text:'Contenido importado de prueba.',versions:[]}),warnings:[]});
    if(p.startsWith('/api/despacho/connections/')&&method==='DELETE'){state.connections=[];return json({disconnected:true,warnings:[]});}
    if(p==='/api/despacho/knowledge/status')return json({ocr:{available:true,languages:['spa'],engine:'controlled'},embeddings:{configured:true,model:'fixture'}});
    if(p==='/api/despacho/knowledge/research')return json({answer:'## Análisis jurídico de prueba\nCriterios y fuentes <img src=x onerror=alert(1)>',query:'vías',model:'gemini-3.6-flash',provider:'gemini',search_performed:true,coverage:'Investigación externa no exhaustiva.',warnings:[],search_queries:['vías jurisprudencia'],sources:[{title:'Providencia <script>alert(1)</script>',url:'https://www.corteconstitucional.gov.co/relatoria/2025/t-100-25.htm',host:'www.corteconstitucional.gov.co',importable:true,status:'Contenido no comprobado',support_text:'Referencia del proveedor, no revisión del original.'},{title:'Referencia externa',url:'https://www.ejemplo.org/fuente',host:'ejemplo.org',importable:false,status:'Fuente externa',support_text:''}]});
    if(p==='/api/despacho/knowledge/verify')return json({title:'Providencia comprobada',excerpt:'Texto ficticio recuperado en la fuente oficial.',text_length:80,document_retrieved:true,legal_validity_checked:false,notice:'Lectura del original, no vigencia.'});
    if(p==='/api/despacho/knowledge/search'){const b=request.postDataJSON();return json({results:state.items.filter(i=>i.kind==='document').slice(0,1).map(i=>({document_id:i.id,title:i.title,excerpt:'Cláusula de prueba <img src=x onerror=alert(1)>',page:2,source_url:'https://www.corteconstitucional.gov.co/',method:'semantic'})),method:'semantic',coverage:'Un documento de prueba',warnings:['Resultado controlado: requiere revisión.']});}
    if(p==='/api/despacho/knowledge/reindex')return json({items:state.items.filter(i=>i.kind==='document').map(i=>({document_id:i.id,indexed:true})),errors:[{document_id:'no-text-fixture',message:'Documento de prueba sin texto extraíble.'}],next_offset:null,has_more:false});
    if(p==='/api/despacho/knowledge/documents')return json({items:state.items.filter(i=>i.data?.source_url),has_more:false});
    if(p==='/api/despacho/knowledge/crawl')return json({items:[{item:add('document','Fuente oficial de prueba',{text:'Texto de fuente ficticia.',source_url:'https://www.corteconstitucional.gov.co/fixture',versions:[]}),warnings:[]}],errors:[{url:'https://www.corteconstitucional.gov.co/no-disponible',message:'Fuente de prueba no disponible.'}],discovered:2,attempted:2,coverage:'Contenido de prueba limitado a dos enlaces.',has_more:false});
    if(p==='/api/despacho/knowledge/sources')return json({sources:[{name:'Corte Constitucional',url:'https://www.corteconstitucional.gov.co/',description:'Fuente oficial'}]});
    if(p==='/api/despacho/knowledge/import'){const b=request.postDataJSON();return json({item:add('document',b.title||'Fuente incorporada',{text:'Texto público de prueba.',source_url:b.url,versions:[]}),warnings:[]});}
    if(p==='/api/despacho/rooms'&&method==='GET')return json({rooms:state.rooms});
    if(p==='/api/despacho/rooms'&&method==='POST'){const b=request.postDataJSON();const room={id:randomUUID(),...b,status:'active',expires_at:new Date(Date.now()+864e5*30).toISOString(),created_at:stamp(),links:[],uploads:[],audit:[],documents:b.document_ids.map(id=>({id,title:state.items.find(i=>i.id===id)?.title,sha256:'a'.repeat(64)}))};state.rooms.push(room);return json(room,201);}
    if(p.startsWith('/api/despacho/rooms/')){const room=state.rooms.find(r=>r.id===p.split('/')[4]);if(!room)return json({detail:'Sala no encontrada'},404);
      if(p.endsWith('/links')&&method==='POST'){const b=request.postDataJSON(),access={id:randomUUID(),...b,expires_at:room.expires_at};room.links.push(access);return json({link:access,url:'/sala-cliente#token-ficticio-privado'});}
      if(p.includes('/links/')&&method==='DELETE'){room.links.find(a=>a.id===p.split('/').pop()).revoked_at=stamp();return json({revoked:true});}
      if(p.endsWith('/revoke')){room.status='revoked';return json(room);}
      if(p.includes('/uploads/')&&p.endsWith('/import')){const u=room.uploads.find(u=>u.id===p.split('/')[6]);u.status='imported';return json({item:add('document',u.filename,{text:'Documento recibido ficticio.',versions:[]}),upload:u});}
      if(p.includes('/uploads/')&&p.endsWith('/reject')){const u=room.uploads.find(u=>u.id===p.split('/')[6]);u.status='rejected';return json({rejected:true});}
      if(p.includes('/documents/')||p.includes('/uploads/'))return binary('PDF o archivo de prueba','application/pdf');
      return json(room);
    }
    if(p==='/api/despacho/signing'&&method==='GET')return json({envelopes:state.envelopes});
    if(p==='/api/despacho/signing'&&method==='POST'){const b=request.postDataJSON();const env={id:randomUUID(),title:b.title,status:'pending',signing_order:b.signing_order,manifest_hash:'d'.repeat(64),created_at:stamp(),expires_at:new Date(Date.now()+864e5).toISOString(),documents:b.document_ids.map(id=>({id,title:state.items.find(i=>i.id===id)?.title,pages:1,sha256:'a'.repeat(64)})),recipients:b.signers.map((r,i)=>({...r,id:randomUUID(),position:i,status:'pending',delivery_status:'not_sent'}))};state.envelopes.push(env);return json({envelope:env,notice:'No se enviaron invitaciones.'},201);}
    if(p.startsWith('/api/despacho/signing/')){
      const env=state.envelopes.find(e=>e.id===p.split('/')[4]);if(!env)return json({detail:'Solicitud no encontrada'},404);
      if(p.endsWith('/invite')){const b=request.postDataJSON();return json({results:b.recipient_ids.map(id=>{env.recipients.find(r=>r.id===id).delivery_status='smtp_accepted';return{recipient_id:id,status:'smtp_accepted',notice:'Aceptado por el servidor; la llegada no está confirmada.'};}),envelope:env});}
      if(p.endsWith('/cancel')){env.status='cancelled';return json({envelope:env});}
      if(p.endsWith('/link'))return json({signing_url:origin+'/firmar-v5#fixture-private-token',notice:'El enlace anterior se invalidó.'});
      if(p.endsWith('/document')||p.endsWith('/receipt'))return binary('PDF de prueba','application/pdf');
      return json(env);
    }

    if(p==='/api/despacho/items'&&method==='GET')return json({items:state.items,has_more:false});
    if(p==='/api/despacho/items'&&method==='POST'){const b=request.postDataJSON();return json(add(b.kind,b.title,b.data,b.matter_id),201);}
    if(p.startsWith('/api/despacho/items/')&&p.endsWith('/audit'))return json({events:[{id:'audit',operation:'update',version:2,created_at:stamp()}]});
    if(p.startsWith('/api/despacho/items/')&&method==='GET')return json(state.items.find(x=>x.id===p.split('/').pop()));
    if(p.startsWith('/api/despacho/items/')&&method==='POST'){
      const i=state.items.find(x=>x.id===p.split('/').pop()),b=request.postDataJSON();
      if(!i)return json({detail:'No existe'},404);
      if(i.version!==b.expected_version)return json({detail:'La versión cambió. Recarga antes de guardar.'},409);
      if((i.data.locked||i.data.final)&&b.data?.locked!==false)return json({detail:'Documento protegido'},409);
      if(i.kind==='document'&&b.data?.text!==undefined&&b.data.text!==i.data.text)b.data.versions=[...(i.data.versions||[]),{title:i.title,text:i.data.text,pages:i.data.pages||[],created_at:i.updated_at}];
      Object.assign(i,b,{version:i.version+1,updated_at:stamp()});delete i.expected_version;return json(i);
    }
    if(p.startsWith('/api/despacho/items/')&&method==='DELETE'){const index=state.items.findIndex(x=>x.id===p.split('/').pop());if(index>=0)state.items.splice(index,1);return json({deleted:true,warnings:state.deleteWarnings||[]});}
    if(p==='/api/despacho/documents/upload'){
      const raw=request.postData()||'';const name=/filename="([^"]+)"/.exec(raw)?.[1]||'archivo.txt';
      return json({items:[add('document',name,{text:'Texto extraíble de prueba.',pages:[{page:1,text:'Texto extraíble de prueba.'}],filename:name,mime:'text/plain',storage_path:'fixture/original',versions:[]})],errors:[]});
    }
    if(p.includes('/documents/')&&p.endsWith('/download'))return binary('Original de prueba.','text/plain');
    if(p.includes('/documents/')&&p.endsWith('/restore')){
      const i=state.items.find(x=>x.id===p.split('/')[4]);const b=request.postDataJSON();if(i.version!==b.expected_version)return json({detail:'Conflicto'},409);
      const v=i.data.versions[b.version_index];i.data.versions.push({title:i.title,text:i.data.text,created_at:stamp()});i.data.text=v.text;i.version++;return json(i);
    }
    if(p==='/api/despacho/chat'){
      if(state.chatFailure)return json({detail:'Proveedor de IA no configurado.'},503);
      return json({answer:state.malicious?'Texto seguro <img src=x onerror="alert(1)"> y <script>alert(2)</script>':'## Análisis\nEl documento contiene información de prueba.\n\n**Revisión requerida:** confirma la fecha.',search_suggestions_html:'<style>body{font-family:sans-serif;font-size:13px}</style><div>Google · <a href="https://www.google.com/search?q=prueba" target="_blank" rel="noopener">Consulta de prueba</a></div>',sources:state.malicious?[{id:'D1-S1',title:'<img src=x onerror="alert(3)">',kind:'document',excerpt:'<script>alert(4)</script>',url:'javascript:alert(5)',verified:false}]:[],warnings:[],coverage:{selected_passages:1,available_passages:2,truncated:true,indexed_retrieval:[{scope:'documents',method:'hybrid',results:1}]},plan:[{label:'Contexto',status:'completed'}]});
    }
    if(p==='/api/versiones/comparar')return json({estadisticas:{palabras_anadidas:2,palabras_eliminadas:1},parrafos_diff:[[{tipo:'equal',texto:'Texto '},{tipo:'insert',texto:'ajustado'}]]});
    if(p==='/api/despacho/export/document'||p==='/api/versiones/exportar-docx')return binary('Descarga controlada: la generación real se prueba en backend.');
    if(p==='/api/despacho/tables/analyze')return json({columns:['Partes'],rows:[{title:'Documento de prueba',document_id:state.items.find(x=>x.kind==='document')?.id,cells:[{value:'=1+1',source_segment:1,excerpt:'Texto fixture',verified:false}],warnings:['Revisión limitada al contenido extraído.'],coverage:{truncated:true,selected_passages:1,available_passages:2}}],warnings:[]});
    if(p.includes('/monitors/')&&p.endsWith('/run')){const i=state.items.find(x=>x.id===p.split('/')[4]);i.data.last_checked=stamp();i.data.last_status='baseline';i.data.findings=[{detected_at:stamp(),title:'Hallazgo de prueba',url:i.data.url,analysis:{summary:'Una obligación cambió.',relevant:true,reason:'Cumple la condición indicada.',evidence:['Fragmento de prueba'],coverage:{pages:1},warnings:[]}}];return json(i);}
    if(p==='/api/despacho/signatures'&&method==='GET')return json({signatures:state.signatures});
    if(p==='/api/despacho/signatures'&&method==='POST'){
      const b=request.postDataJSON();const s={...b,document_text:b.text,id:randomUUID(),status:'pending',created_at:stamp(),expires_at:new Date(Date.now()+7*864e5).toISOString()};delete s.text;state.signatures.push(s);return json({signature:s,signing_url:origin+'/firmar#fixture-'+(++state.lastSignatureToken)});
    }
    if(p.includes('/signatures/')&&p.endsWith('/link'))return json({signature:state.signatures[0],signing_url:origin+'/firmar#fixture-'+(++state.lastSignatureToken),notice:'Enlace anterior invalidado.'});
    if(p.includes('/signatures/')&&p.endsWith('/cancel')){state.signatures[0].status='cancelled';return json(state.signatures[0]);}
    if(p.includes('/signatures/')&&p.endsWith('/receipt'))return binary('PDF fixture','application/pdf');
    if(p.startsWith('/api/despacho/signatures/'))return json(state.signatures.find(s=>s.id===p.split('/').pop()));
    if(p==='/api/despacho/export')return json({format:'memorialista-despacho',version:1,items:state.items});
    if(p==='/api/despacho/import'){const b=request.postDataJSON();return json({imported:b.backup.items?.length||0,conflicts:0});}
    return json({detail:'Ruta no prevista en la prueba: '+p},404);
  });
  await page.goto(origin+'/app');await page.getByRole('heading',{name:'Cada asunto, con claridad.'}).waitFor();
  const nav=async name=>{if(await page.getByRole('button',{name:'Abrir navegación'}).isVisible())await page.getByRole('button',{name:'Abrir navegación'}).click();await page.getByRole('navigation',{name:'Productos'}).getByRole('button',{name,exact:true}).click();};
  const close=()=>page.getByRole('dialog').getByRole('button',{name:'Cerrar',exact:true}).click();
  const clean=()=>{assert.deepEqual(state.errors,[]);assert.deepEqual(state.csp,[]);assert.deepEqual(state.alerts,[]);};
  return{page,state,nav,close,clean};
}

test('Plan dinámico: editar, aprobar, ejecutar dos pasos y programar sin ejecuciones anticipadas',async t=>{
  const {page,state,nav,clean}=await fixture(t);
  await page.getByLabel('Describe tu encargo').fill('Revisar y preparar escrito de prueba');
  await page.getByRole('button',{name:'Planificar y ejecutar',exact:true}).click();
  assert.equal(await page.getByLabel('Objetivo del encargo').inputValue(),'Revisar y preparar escrito de prueba');
  await page.getByRole('button',{name:'Preparar plan con IA',exact:true}).click();
  await page.getByRole('heading',{name:'Encargos por etapas',exact:true}).waitFor();
  await page.getByRole('button',{name:'Editar plan',exact:true}).click();
  await page.getByLabel('Instrucciones del paso 1',{exact:true}).fill('Revisar <img src=x onerror=alert(1)> como texto.');
  await page.getByRole('button',{name:'Guardar plan',exact:true}).click();
  await page.getByText('Revisar <img src=x onerror=alert(1)> como texto.',{exact:true}).waitFor();
  assert.equal(state.requests.filter(r=>r.p.endsWith('/step')).length,0);
  await page.getByRole('button',{name:'Aprobar plan',exact:true}).click();
  assert.equal(state.jobs[0].state,'draft');
  await page.getByRole('dialog').getByRole('button',{name:'Aprobar plan',exact:true}).click();
  await page.getByRole('button',{name:'Ejecutar plan',exact:true}).waitFor();
  assert.equal(state.jobs[0].state,'approved');
  await page.getByRole('button',{name:'Ejecutar plan',exact:true}).click();
  await page.locator('.v5-detail-header .badge').filter({hasText:'Completado'}).waitFor();
  assert.equal(state.jobs[0].state,'completed');assert.equal(state.jobs[0].results.length,2);
  assert.equal(await page.locator('.v5-job-detail img').count(),0);
  await page.getByRole('button',{name:'Programar repetición',exact:true}).click();
  await page.getByLabel('Repetir cada (minutos)').fill('1440');
  await page.getByRole('button',{name:'Guardar programación',exact:true}).click();
  await page.getByRole('heading',{name:'Tareas programadas',exact:true}).waitFor();
  await page.getByRole('button',{name:'Pausar tarea',exact:true}).click();
  await page.getByRole('button',{name:'Activar tarea',exact:true}).waitFor();
  assert.equal(state.schedules[0].enabled,false);
  assert.equal(state.requests.filter(r=>r.p.endsWith('/step')).length,2);
  clean();
},{timeout:45000});

test('Plan falla sin respuesta ficticia y acciones del navegador exigen aprobación concreta',async t=>{
  const {page,state,nav,clean}=await fixture(t);state.agentFailure=true;
  await page.getByRole('button',{name:'Planificar y ejecutar',exact:true}).click();
  await page.getByLabel('Objetivo del encargo').fill('Prueba de ausencia de proveedor.');
  await page.getByRole('button',{name:'Preparar plan con IA',exact:true}).click();
  await page.locator('.form-error').filter({hasText:'Configura un proveedor de IA'}).waitFor();
  assert.equal(state.jobs.length,0);
  await page.getByRole('dialog').getByRole('button',{name:'Cancelar',exact:true}).click();state.agentFailure=false;
  state.jobs.push({id:randomUUID(),title:'Navegación de prueba',objective:'Consultar fuente oficial.',state:'approved',version:1,cursor:0,results:[],allowed_urls:['https://www.corteconstitucional.gov.co/'],plan:[{id:'s1',tool:'browser_read',title:'Leer fuente',instruction:'Leer página',url:'https://www.corteconstitucional.gov.co/'}],created_at:new Date().toISOString(),updated_at:new Date().toISOString()});
  await nav('Encargos por etapas');
  await page.getByRole('button',{name:'Navegador del encargo',exact:true}).click();
  await page.getByLabel('Control de la página').waitFor();assert.equal(await page.getByLabel('Control de la página').locator('option').count(),1);
  await page.getByRole('button',{name:'Revisar acción',exact:true}).click();
  await page.getByRole('heading',{name:'Confirmar acción externa',exact:true}).waitFor();assert.equal(state.browserApprovals,0);
  await page.getByRole('button',{name:'Aprobar esta acción',exact:true}).click();
  await page.getByRole('heading',{name:'Navegador supervisado',exact:true}).waitFor();assert.equal(state.browserApprovals,1);
  assert.equal(await page.locator('.v5-browser-panel img').count(),0);
  await page.getByRole('button',{name:'Tomar control manual',exact:true}).click();
  const privateLink=page.getByRole('link',{name:'Abrir navegador bajo mi control',exact:true});await privateLink.waitFor();
  assert.equal(await privateLink.getAttribute('rel'),'noopener noreferrer');assert.equal(state.browserManual,true);
  assert.equal(await page.evaluate(()=>JSON.stringify(localStorage).includes('browserbase')),false);
  await page.getByRole('button',{name:'Cerré la ventana de control y terminé',exact:true}).click();
  await page.getByRole('heading',{name:'Navegador supervisado',exact:true}).waitFor();assert.equal(state.browserManual,false);
  await page.getByRole('button',{name:'Descargas del navegador',exact:true}).click();
  await page.getByRole('button',{name:'Guardar en DMS',exact:true}).click();
  await page.getByText('Copia guardada en la biblioteca.',{exact:true}).waitFor();assert.equal(state.items.some(i=>i.title==='descarga-ficticia.txt'),true);
  clean();
},{timeout:30000});

test('Conexión: importar documento no modifica origen y desconectar necesita confirmación',async t=>{
  const {page,state,nav,clean}=await fixture(t);
  await nav('Conexiones');
  await page.getByRole('heading',{name:'Google Drive',exact:true}).waitFor();
  const unconfigured=page.locator('.connection-card').filter({has:page.getByRole('heading',{name:'Microsoft OneDrive',exact:true})});
  assert.equal(await unconfigured.getByRole('button',{name:'Conectar cuenta',exact:true}).isDisabled(),true);
  await page.getByRole('button',{name:'Explorar archivos',exact:true}).click();
  await page.getByRole('button',{name:'Importar a DMS',exact:true}).click();
  await page.getByText('Documento importado a tu biblioteca.',{exact:true}).waitFor();
  assert.equal(state.items.filter(i=>i.title==='Contrato de conexión.txt').length,1);
  assert.equal(await page.getByRole('button',{name:'Importado',exact:true}).isDisabled(),true);assert.equal(await page.locator('.toast.error').count(),0);
  await page.getByRole('dialog').getByRole('button',{name:'Cerrar',exact:true}).click();
  await page.getByRole('button',{name:'Desconectar',exact:true}).click();assert.equal(state.connections.length,1);
  await page.getByRole('dialog').getByRole('button',{name:'Desconectar',exact:true}).click();
  await page.getByText('Conexión retirada.',{exact:true}).waitFor();assert.equal(state.connections.length,0);
  assert.equal(state.requests.some(r=>r.p.includes('/resources')&&r.method!=='GET'),false);
  clean();
},{timeout:30000});

test('Búsqueda conceptual y monitor semántico muestran evidencia sin ejecutar HTML',async t=>{
  const {page,state,nav,clean}=await fixture(t);state.add('document','Contrato de prueba',{text:'Una cláusula de prueba.',versions:[]});
  await page.getByRole('button',{name:'Actualizar despacho'}).click();
  await nav('DMS');await page.getByLabel('Consulta sobre tus documentos').fill('Obligaciones de entrega');
  await page.getByRole('button',{name:'Buscar en contenido',exact:true}).click();
  await page.getByText('Cláusula de prueba <img src=x onerror=alert(1)>',{exact:true}).waitFor();
  assert.equal(await page.locator('.v5-search-hit img').count(),0);
  const search=state.requests.find(r=>r.p==='/api/despacho/knowledge/search');assert.equal(search.body.scope,'documents');assert.equal(search.body.semantic,true);
  await nav('Monitor');await page.getByRole('button',{name:'Crear monitor',exact:true}).click();
  await page.getByLabel('Nombre del monitor').fill('Monitor con condición');
  await page.getByLabel('URL de la página oficial').fill('https://www.corteconstitucional.gov.co/');
  await page.getByLabel('Criterio de detección').selectOption('semantic');
  await page.getByLabel('Condición jurídica para la IA').fill('Cambios en obligaciones de entrega.');
  await page.getByRole('dialog').getByRole('button',{name:'Guardar',exact:true}).click();
  assert.equal(state.items.find(i=>i.kind==='monitor').data.analysis_mode,'semantic');
  await page.getByRole('button',{name:'Comprobar ahora',exact:true}).click();
  await page.getByRole('button',{name:'Hallazgos (1)',exact:true}).click();
  await page.getByText('Una obligación cambió.',{exact:true}).waitFor();
  await page.getByText('Cumple la condición indicada.',{exact:true}).waitFor();
  clean();
},{timeout:30000});

test('Monitor sin hallazgos conserva advertencias de OCR y no presenta extracción parcial como ausencia de cambios',async t=>{
  const{page,state,nav,close,clean}=await fixture(t);
  state.add('monitor','Monitor de extracción parcial',{url:'https://www.corteconstitucional.gov.co/',analysis_mode:'keywords',last_status:'unchanged',findings:[],last_warnings:['OCR de prueba: no se pudo leer una página.'],extraction_coverage:{pages_total:8,pages_included:3,pages_with_text:2,complete:false}});
  state.add('monitor','Monitor semántico parcial',{url:'https://www.funcionpublica.gov.co/',analysis_mode:'semantic',condition:'Detectar obligaciones nuevas.',last_status:'partial',findings:[],last_warnings:['Extracción de prueba incompleta.'],coverage:{extraction_incomplete_documents:1,complete_within_limit:false,analyzed_documents:1,errors:[]}});
  await page.getByRole('button',{name:'Actualizar despacho'}).click();await nav('Monitor');
  const card=page.locator('.card').filter({has:page.getByRole('heading',{name:'Monitor de extracción parcial',exact:true})});
  await card.getByText('Extracción parcial del original.',{exact:false}).waitFor();
  assert.equal((await card.textContent()).includes('Estado: Sin cambios'),false);
  await card.getByRole('button',{name:'Hallazgos (0)',exact:true}).click();
  await page.getByRole('dialog').getByText('OCR de prueba: no se pudo leer una página.',{exact:true}).waitFor();
  await page.getByRole('dialog').getByText('8 páginas del original · 3 páginas incluidas · 2 páginas con texto extraído',{exact:false}).waitFor();await close();
  const semantic=page.locator('.card').filter({has:page.getByRole('heading',{name:'Monitor semántico parcial',exact:true})});
  await semantic.getByRole('button',{name:'Hallazgos (0)',exact:true}).click();
  await page.getByRole('dialog').getByText('1 documentos con extracción incompleta',{exact:false}).waitFor();
  await page.getByRole('dialog').getByText('Extracción de prueba incompleta.',{exact:true}).waitFor();clean();
},{timeout:30000});

test('Firma con varios documentos: crear no envía correo, invitaciones explícitas y evidencias',async t=>{
  const {page,state,nav,clean}=await fixture(t);
  state.add('document','Contrato A',{text:'Contrato ficticio.',versions:[]});state.add('document','Anexo B',{text:'Anexo ficticio.',versions:[]});
  await page.getByRole('button',{name:'Actualizar despacho'}).click();await nav('Firma electrónica');
  await page.getByRole('button',{name:'Solicitud con correo verificado',exact:true}).click();
  await page.getByLabel('Título de la solicitud').fill('Contrato y anexo de prueba');
  await page.getByRole('dialog').getByLabel('Contrato A',{exact:true}).check();await page.getByRole('dialog').getByLabel('Anexo B',{exact:true}).check();
  await page.getByLabel('Nombre del firmante 1',{exact:true}).fill('Persona de prueba');await page.getByLabel('Correo del firmante 1',{exact:true}).fill('persona@example.invalid');
  await page.getByRole('button',{name:'Añadir firmante',exact:true}).click();await page.getByLabel('Nombre del firmante 2',{exact:true}).fill('Segunda persona');await page.getByLabel('Correo del firmante 2',{exact:true}).fill('segunda@example.invalid');
  await page.getByLabel('Orden de firma').selectOption('sequential');
  await page.getByRole('button',{name:'Crear solicitud',exact:true}).click();
  await page.getByRole('heading',{name:'Contrato y anexo de prueba',exact:true}).waitFor();
  assert.equal(state.envelopes[0].documents.length,2);assert.equal(state.envelopes[0].recipients.length,2);assert.equal(state.requests.filter(r=>r.p.endsWith('/invite')).length,0);
  await page.getByRole('button',{name:'Enviar invitaciones',exact:true}).click();
  await page.getByRole('heading',{name:'Confirmar invitaciones de firma',exact:true}).waitFor();assert.equal(state.requests.filter(r=>r.p.endsWith('/invite')).length,0);
  await page.getByRole('button',{name:'Enviar estos correos',exact:true}).click();
  await page.getByRole('heading',{name:'Resultado del envío',exact:true}).waitFor();assert.equal(state.requests.filter(r=>r.p.endsWith('/invite')).length,1);
  assert.equal(state.envelopes[0].recipients.every(r=>r.delivery_status==='smtp_accepted'),true);
  clean();
},{timeout:30000});

test('V5 móvil: encargos, conexiones, búsqueda y firma a350px sin desbordamiento',async t=>{
  const {page,nav,clean}=await fixture(t,{viewport:{width:350,height:844}});
  for(const name of ['Agente','Encargos por etapas','Tareas programadas','Conexiones','Salas de documentos','DMS','Jurisprudencia','Firma electrónica']){
    await nav(name);await page.waitForTimeout(100);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,name);
  }
  clean();
},{timeout:30000});

test('Chat consulta el ámbito elegido y conserva la cobertura y la selección guardadas',async t=>{
  const{page,state,nav,clean}=await fixture(t);
  await page.getByLabel('Biblioteca para el agente').selectOption('all');
  await page.getByLabel('Describe tu encargo').fill('Consulta documental y jurídica de prueba.');
  await page.getByRole('button',{name:'Enviar encargo',exact:true}).click();
  await page.getByText('Consulta de la biblioteca:',{exact:true}).waitFor();
  const request=state.requests.find(r=>r.p==='/api/despacho/chat');assert.equal(request.body.knowledge_scope,'all');
  assert.equal(state.items.find(i=>i.kind==='conversation').data.knowledge_scope,'all');
  await page.getByText('Documentos DMS · búsqueda combinada · 1 fragmentos recuperados',{exact:false}).waitFor();
  await nav('Ajustes');await page.getByRole('heading',{name:'Cuotas de automatización',exact:true}).waitFor();
  await page.getByText('100 llamadas automáticas',{exact:true}).waitFor();await page.getByText(/1[.,]?000 llamadas automáticas/).waitFor();
  clean();
},{timeout:30000});

test('Índice y lote oficial conservan los errores parciales y cuentan los resultados reales',async t=>{
  const{page,state,nav,close,clean}=await fixture(t);state.add('document','Documento indexable de prueba',{text:'Contenido ficticio.',versions:[]});
  await page.getByRole('button',{name:'Actualizar despacho'}).click();await nav('DMS');
  await page.getByRole('button',{name:'Preparar índice',exact:true}).click();
  await page.getByText('Documentos procesados: 1. Errores: 1. Actualización terminada.',{exact:true}).waitFor();
  await page.getByText('no-text-fixture: Documento de prueba sin texto extraíble.',{exact:true}).waitFor();await close();
  await nav('Jurisprudencia');await page.getByRole('tab',{name:'Mi biblioteca jurídica'}).click();await page.getByRole('button',{name:'Incorporar varias fuentes',exact:true}).click();
  await page.getByLabel('Página oficial con enlaces a documentos').fill('https://www.corteconstitucional.gov.co/');
  await page.getByRole('button',{name:'Revisar enlaces e importar',exact:true}).click();
  await page.getByText('1 documentos incorporados o ya existentes. 1 errores.',{exact:true}).waitFor();
  await page.getByText('Fuente de prueba no disponible.',{exact:true}).waitFor();await close();
  await page.getByRole('button',{name:'Ver biblioteca incorporada',exact:true}).click();
  await page.getByText('Fuente oficial de prueba',{exact:true}).waitFor();
  assert.equal(state.requests.find(r=>r.p.endsWith('/knowledge/crawl')).body.max_documents,5);clean();
},{timeout:30000});

test('Investigación jurídica: consulta web, referencias no verificadas y guardado explícito',async t=>{
  const{page,state,nav,clean}=await fixture(t);
  await nav('Jurisprudencia');
  assert.equal(await page.getByRole('tab',{name:'Investigar con IA'}).count(),1);
  await page.getByLabel('Problema jurídico').fill('Competencia y reparación vial en Bucaramanga');
  await page.getByLabel('Lugar o jurisdicción (opcional)').fill('Bucaramanga');
  await page.getByRole('button',{name:'Investigar con fuentes'}).click();
  await page.getByText('Investigación externa no exhaustiva.',{exact:true}).waitFor();
  assert.equal(await page.locator('.v5-external-source').count(),2);
  assert.equal(await page.locator('.v5-external-source button').count(),1);
  assert.equal(await page.locator('.v5-external-source img,.v5-external-source script').count(),0);
  const request=state.requests.find(r=>r.p==='/api/despacho/knowledge/research');
  assert.equal(request.body.territory,'Bucaramanga');
  assert.equal(state.requests.filter(r=>r.p==='/api/despacho/knowledge/import').length,0);
  await page.getByRole('button',{name:'Comprobar el original'}).click();
  await page.getByText('Texto ficticio recuperado en la fuente oficial.',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Incorporar a mi biblioteca'}).click();
  await page.getByRole('dialog').getByRole('button',{name:'Guardar en mi biblioteca'}).click();
  await page.getByText('Fuente oficial incorporada.',{exact:true}).waitFor();
  assert.equal(state.requests.filter(r=>r.p==='/api/despacho/knowledge/import').length,1);
  await page.getByRole('tab',{name:'Mi biblioteca jurídica'}).click();
  await page.getByRole('button',{name:'Ver biblioteca incorporada'}).waitFor();
  clean();
},{timeout:30000});

test('Capturas de UI V5 con datos ficticios y sin conexiones a servicios reales',async t=>{
  const{page,state,nav,clean}=await fixture(t);
  const matter=state.add('matter','Caso de demostración · datos ficticios',{client:'Cliente ficticio',description:'Expediente creado únicamente para mostrar la interfaz.'});
  const doc=state.add('document','Contrato de muestra · sin validez jurídica',{text:'Documento ficticio para revisión de interfaz.',versions:[]},matter.id);
  const stamp=new Date().toISOString();
  state.jobs.push({id:randomUUID(),title:'Revisar contrato y preparar observaciones',objective:'DEMOSTRACIÓN · DATOS FICTICIOS. Revisar el contrato de muestra, contrastar sus obligaciones y preparar un borrador para revisión profesional. Los resultados de esta captura están controlados por la prueba de interfaz.',state:'approved',version:4,cursor:1,document_ids:[doc.id],matter_id:matter.id,allowed_urls:[],created_at:stamp,updated_at:stamp,
    plan:[{id:'s1',tool:'read_documents',title:'Leer los documentos del asunto',instruction:'Identificar partes, fechas y obligaciones del contrato aportado.'},{id:'s2',tool:'analyze',title:'Evaluar obligaciones y puntos pendientes',instruction:'Contrastar las obligaciones con el contexto del asunto y señalar lo que requiere verificación.'},{id:'s3',tool:'draft',title:'Preparar el escrito para revisión',instruction:'Redactar observaciones claras y conservar las referencias del documento.'},{id:'s4',tool:'save_document',title:'Guardar el borrador en DMS',instruction:'Conservar el resultado para editarlo y revisarlo antes de utilizarlo.'}],results:[{step_id:'s1',tool:'read_documents',title:'Leer los documentos del asunto',result:{answer:'Lectura de muestra: una obligación de entrega y un plazo por confirmar. Este resultado es ficticio y solo muestra la interfaz.',sources:[{id:'D1-S1',kind:'document',document_id:doc.id,title:doc.title,excerpt:'Contenido ficticio para demostrar la lectura de evidencias.',page:1,verified:false}]}}]});
  state.jobs.push({id:randomUUID(),title:'Investigación jurídica de muestra',objective:'Demostración con fuentes ficticias.',state:'draft',version:1,cursor:0,plan:[{id:'s1',tool:'research',title:'Delimitar problema jurídico',instruction:'Definir el alcance.'}],results:[],created_at:stamp,updated_at:stamp});
  await page.getByRole('button',{name:'Actualizar despacho'}).click();await nav('Encargos por etapas');
  await page.getByRole('heading',{name:'Revisar contrato y preparar observaciones',exact:true}).waitFor();
  await page.locator('.toast button').first().click();
  await page.screenshot({path:path.join(artifacts,'memorialista-v5-encargos.png'),fullPage:false});
  await nav('Agente');await page.getByLabel('Asunto del encargo').selectOption(matter.id);
  await page.getByLabel('Describe tu encargo').fill('DEMOSTRACIÓN · DATOS FICTICIOS\nRevisa el contrato de muestra, señala las obligaciones y ayúdame a preparar el siguiente escrito.');
  await page.screenshot({path:path.join(artifacts,'memorialista-v5-agente.png'),fullPage:false});
  clean();
},{timeout:30000});

test('Sala privada: permisos explícitos, recepción revisable y revocación de acceso',async t=>{
  const{page,state,nav,close,clean}=await fixture(t);state.add('document','Documento para sala de prueba',{text:'Contenido ficticio para compartir.',versions:[]});
  await page.getByRole('button',{name:'Actualizar despacho'}).click();await nav('DMS');await page.getByRole('button',{name:'Salas para compartir',exact:true}).click();
  await page.getByRole('button',{name:'Crear sala privada',exact:true}).click();
  await page.getByRole('dialog').getByLabel('Documento para sala de prueba',{exact:false}).check();
  await page.getByLabel('Nombre de la sala').fill('Sala de prueba · datos ficticios');await page.getByLabel('Descripción para los destinatarios').fill('Entrega de prueba.');
  await page.getByRole('button',{name:'Crear sala',exact:true}).click();await page.getByRole('button',{name:'Abrir sala',exact:true}).click();
  assert.equal(state.rooms[0].links.length,0);
  await page.getByRole('button',{name:'Crear enlace de acceso',exact:true}).click();
  await page.getByLabel('Etiqueta del acceso').fill('Acceso ficticio');await page.getByLabel('Cargar archivos para mi revisión',{exact:true}).check();
  assert.equal(await page.getByLabel('Descargar documentos publicados',{exact:true}).isChecked(),false);
  await page.getByRole('button',{name:'Crear enlace privado',exact:true}).click();
  await page.getByRole('heading',{name:'Enlace privado de la sala',exact:true}).waitFor();
  assert.equal(state.rooms[0].links[0].can_view,true);assert.equal(state.rooms[0].links[0].can_download,false);assert.equal(state.rooms[0].links[0].can_upload,true);
  state.rooms[0].uploads.push({id:randomUUID(),filename:'carga-sin-confirmar.txt',status:'pending',created_at:new Date().toISOString()});
  state.rooms[0].uploads.push({id:randomUUID(),filename:'recibido-de-prueba.txt',status:'received',created_at:new Date().toISOString()});
  await page.getByRole('button',{name:'Volver a la sala',exact:true}).click();
  if(await page.locator('.toast').count())await page.locator('.toast').last().waitFor({state:'hidden',timeout:15000});
  await page.screenshot({path:path.join(artifacts,'memorialista-v5-sala-privada.png'),fullPage:false});
  const unconfirmed=page.locator('.list-row').filter({hasText:'carga-sin-confirmar.txt'});assert.equal(await unconfirmed.getByRole('button',{name:'Incorporar a DMS',exact:true}).count(),0);assert.equal(await unconfirmed.getByRole('button',{name:'Revisar archivo',exact:true}).count(),0);
  await page.getByRole('button',{name:'Incorporar a DMS',exact:true}).click();
  await page.getByRole('dialog').getByText('Incorporado a DMS',{exact:true}).waitFor();assert.equal(state.items.some(i=>i.title==='recibido-de-prueba.txt'),true);
  await page.getByRole('button',{name:'Revocar enlace',exact:true}).click();assert.equal(state.rooms[0].links[0].revoked_at,undefined);
  await page.getByRole('dialog').getByRole('button',{name:'Revocar enlace',exact:true}).click();
  await page.getByRole('dialog').getByText('Revocado',{exact:true}).waitFor();assert.ok(state.rooms[0].links[0].revoked_at);
  await page.getByRole('button',{name:'Revocar sala completa',exact:true}).click();await page.getByRole('button',{name:'Revocar sala',exact:true}).click();
  await page.getByText('Sala revocada.',{exact:true}).waitFor();assert.equal(state.rooms[0].status,'revoked');clean();
},{timeout:30000});

async function signingFixture(t){
  const context=await browser.newContext({viewport:{width:390,height:844},locale:'es-CO',acceptDownloads:true});t.after(()=>context.close());const page=await context.newPage();
  const state={requests:[],errors:[],csp:[],otpError:true,signed:false,canSign:true};page.on('pageerror',e=>state.errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/Content Security Policy/.test(m.text()))state.csp.push(m.text());});
  await page.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url()),p=url.pathname;let body;try{body=request.postDataJSON();}catch{}state.requests.push({p,body,url:request.url(),headers:request.headers()});const json=(obj,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(obj)});
    if(url.origin!==origin)return route.abort();
    if(p==='/firmar-v5')return route.fulfill({contentType:'text/html',headers:{'Content-Security-Policy':publicCsp,'Referrer-Policy':'no-referrer'},body:await readFile(root+'/app/private/firma-v5.html','utf8')});
    if(p.startsWith('/static/firma-v5/'))return route.fulfill({contentType:p.endsWith('.js')?'application/javascript':'text/css',body:await readFile(root+'/app'+p,'utf8')});
    if(p==='/static/asesor/favicon.svg')return route.fulfill({status:204,body:''});
    if(p==='/api/firmas-v5/view')return json({id:'envelope-fixture',title:'Contrato de prueba <script>alert(1)</script>',status:'pending',manifest_hash:'f'.repeat(64),expires_at:new Date(Date.now()+864e5).toISOString(),documents:[{title:'Documento ficticio',text:'Texto seguro <img src=x onerror=alert(1)>',pages:1,sha256:'a'.repeat(64)}],recipient:{name:'Persona de prueba',email_masked:'p***@example.invalid',status:'pending'},can_sign:state.canSign,consent_text:'Consentimiento exacto del servidor de prueba.',notice:state.canSign?'':'Pendiente de otro firmante.'});
    if(p==='/api/firmas-v5/otp')return json({sent:true,expires_seconds:600,notice:'Código de prueba enviado.'});
    if(p==='/api/firmas-v5/accept'){if(state.otpError)return json({detail:'El código no es válido o ha caducado.'},422);state.signed=true;return json({signed:true,completed:false,signed_at:new Date().toISOString()});}
    if(p==='/api/firmas-v5/document')return route.fulfill({contentType:'application/pdf',body:'%PDF-1.7 Fixture de transporte'});
    return json({detail:'No existe'},404);
  });
  await page.goto(origin+'/firmar-v5#token-secreto-de-prueba');await page.getByRole('heading',{name:'Lee el contenido completo'}).waitFor();return{page,state};
}
test('Destinatario: OTP inválido no confirma, consentimiento obligatorio y secreto fuera de URL HTTP',async t=>{
  const{page,state}=await signingFixture(t);
  assert.equal(await page.locator('.document-text img, #request-title script').count(),0);
  assert.equal(await page.locator('#consent-text').textContent(),'Consentimiento exacto del servidor de prueba.');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.getByRole('button',{name:'Enviar código a mi correo',exact:true}).click();await page.getByText('Código de prueba enviado.',{exact:true}).waitFor();
  await page.getByLabel('Código recibido por correo').fill('123456');
  await page.getByRole('button',{name:'Aceptar y firmar estos documentos',exact:true}).click();assert.equal(state.requests.filter(r=>r.p.endsWith('/accept')).length,0);
  await page.locator('#consent').check();await page.getByRole('button',{name:'Aceptar y firmar estos documentos',exact:true}).click();
  await page.getByText('El código no es válido o ha caducado.',{exact:true}).waitFor();assert.equal(await page.locator('#success').isVisible(),false);assert.equal(state.signed,false);
  state.otpError=false;await page.getByRole('button',{name:'Aceptar y firmar estos documentos',exact:true}).click();
  await page.getByRole('heading',{name:'Tu firma quedó registrada',exact:true}).waitFor();assert.equal(state.signed,true);
  const acceptance=state.requests.filter(r=>r.p.endsWith('/accept')).at(-1);assert.equal(acceptance.body.manifest_hash,'f'.repeat(64));assert.equal(acceptance.body.consent,true);
  for(const request of state.requests){assert.equal(request.url.includes('token-secreto'),false);assert.equal(String(request.headers.referer||'').includes('token-secreto'),false);}
  assert.deepEqual(state.errors,[]);assert.deepEqual(state.csp,[]);
},{timeout:30000});
