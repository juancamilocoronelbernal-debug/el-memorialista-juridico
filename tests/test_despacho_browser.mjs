/**
 * UI del despacho en Chromium: archivos de producción y respuestas HTTP controladas.
 * No utiliza Supabase, IA, correo ni personas reales. No instala modos demo en la app.
 * Verifica interacción, persistencia solicitada, estados de error, XSS, CSP y móvil.
 *
 * node --test tests/test_despacho_browser.mjs
 * Opcionales: PLAYWRIGHT_MODULE, PLAYWRIGHT_CHROMIUM_EXECUTABLE,
 * DESPACHO_BROWSER_ARTIFACTS (capturas internas; no forman parte del ZIP).
 */
import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { randomUUID } from 'node:crypto';
import { readFile, mkdir, mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const imported=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const {chromium}=imported.default||imported;
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
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
  const state={items:[],signatures:[],errors:[],csp:[],requests:[],alerts:[],chatFailure:false,malicious:false,lastSignatureToken:0};
  const stamp=()=>new Date().toISOString();
  const add=(kind,title,data={},matter_id=null)=>{const i={id:randomUUID(),kind,title,data,matter_id,version:1,created_at:stamp(),updated_at:stamp()};state.items.push(i);return i;};
  state.add=add;
  page.on('pageerror',e=>state.errors.push(e.message));
  page.on('dialog',async d=>{state.alerts.push(d.message());await d.dismiss();});
  page.on('console',m=>{if(m.type()==='error'&&/Content Security Policy|violates.*directive/i.test(m.text()))state.csp.push(m.text());});
  await page.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url()),p=url.pathname,method=request.method();
    state.requests.push({p,method});
    const json=(obj,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(obj)});
    const binary=(content='fixture bytes',mime='application/octet-stream')=>route.fulfill({status:200,contentType:mime,body:content});
    if(url.origin!==origin)return route.abort('blockedbyclient');
    if(p==='/app')return route.fulfill({contentType:'text/html',headers:{'Content-Security-Policy':csp,'Cache-Control':'no-store'},body:await readFile(root+'/app/private/despacho.html','utf8')});
    if(['/app/assets/despacho.js','/app/assets/despacho.css'].includes(p))return route.fulfill({contentType:p.endsWith('.js')?'application/javascript':'text/css',body:await readFile(root+'/app/private/'+p.split('/').pop(),'utf8')});
    if(p==='/static/vendor/supabase.js')return route.fulfill({contentType:'application/javascript',body:''});
    if(p==='/static/auth/session.js')return route.fulfill({contentType:'application/javascript',body:`window.MemAuth={init:async()=>({client:{auth:{getSession:async()=>({data:{session:{access_token:'fixture-only',user:{id:'00000000-0000-4000-8000-000000000001',email:'prueba@example.invalid',user_metadata:{name:'María Prueba'}}}}}),onAuthStateChange:()=>{},signOut:async()=>({}),refreshSession:async()=>({})}}}),establish:async()=>({}),clearCookie:async()=>{},message:e=>e.message}`});
    if(p==='/static/asesor/favicon.svg')return route.fulfill({status:204,body:''});
    if(p==='/api/despacho/capabilities')return json({storage:{ready:true,message:'Almacenamiento de prueba disponible'},ai:{configured:true},monitoring:{automatic:false,message:'Comprobación manual de prueba disponible'},signatures:{configured:true,enabled:true}});
    if(p==='/api/despacho/items'&&method==='GET')return json({items:state.items,has_more:false});
    if(p==='/api/despacho/items'&&method==='POST'){const b=request.postDataJSON();return json(add(b.kind,b.title,b.data,b.matter_id),201);}
    if(p.startsWith('/api/despacho/items/')&&p.endsWith('/audit'))return json({events:[{id:'audit',operation:'update',version:2,created_at:stamp()}]});
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
      return json({answer:state.malicious?'Texto seguro <img src=x onerror="alert(1)"> y <script>alert(2)</script>':'## Análisis\nEl documento contiene información de prueba.\n\n**Revisión requerida:** confirma la fecha.',search_suggestions_html:'<style>body{font-family:sans-serif;font-size:13px}</style><div>Google · <a href="https://www.google.com/search?q=prueba" target="_blank" rel="noopener">Consulta de prueba</a></div>',sources:state.malicious?[{id:'D1-S1',title:'<img src=x onerror="alert(3)">',kind:'document',excerpt:'<script>alert(4)</script>',url:'javascript:alert(5)',verified:false}]:[],warnings:[],coverage:{selected_passages:1,available_passages:2,truncated:true},plan:[{label:'Contexto',status:'completed'}]});
    }
    if(p==='/api/versiones/comparar')return json({estadisticas:{palabras_anadidas:2,palabras_eliminadas:1},parrafos_diff:[[{tipo:'equal',texto:'Texto '},{tipo:'insert',texto:'ajustado'}]]});
    if(p==='/api/despacho/export/document'||p==='/api/versiones/exportar-docx')return binary('Descarga controlada: la generación real se prueba en backend.');
    if(p==='/api/despacho/tables/analyze')return json({columns:['Partes'],rows:[{title:'Documento de prueba',document_id:state.items.find(x=>x.kind==='document')?.id,cells:[{value:'=1+1',source_segment:1,excerpt:'Texto fixture',verified:false}],warnings:['Revisión limitada al contenido extraído.'],coverage:{truncated:true,selected_passages:1,available_passages:2}}],warnings:[]});
    if(p.includes('/monitors/')&&p.endsWith('/run')){const i=state.items.find(x=>x.id===p.split('/')[4]);i.data.last_checked=stamp();i.data.last_status='baseline';return json(i);}
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

test('Cinco productos privados: conversación, asunto, DMS/versiones, tabla, monitor y firma',async t=>{
  const{page,state,nav,close,clean}=await fixture(t);
  await page.screenshot({path:path.join(artifacts,'despacho-escritorio.png'),fullPage:true});
  for(const name of ['Agente','Jurisprudencia','Monitor','DMS','Firma electrónica'])assert.equal(await page.getByRole('navigation',{name:'Productos'}).getByRole('button',{name,exact:true}).count(),1);
  await nav('Asuntos');await page.getByRole('button',{name:'Nuevo asunto',exact:true}).click();await page.getByLabel('Nombre del asunto').fill('Asunto ficticio');await page.getByLabel('Cliente o parte principal').fill('Cliente de prueba');await page.getByRole('dialog').getByRole('button',{name:'Guardar',exact:true}).click();await page.getByRole('heading',{name:'Asunto ficticio',exact:true}).waitFor();
  await nav('DMS');await page.locator('#upload-input').setInputFiles({name:'archivo-prueba.txt',mimeType:'text/plain',buffer:Buffer.from('Texto ficticio de prueba.')});await page.getByText('archivo-prueba.txt',{exact:true}).first().waitFor();
  await nav('Editor y versiones');await page.getByRole('button',{name:'Nuevo escrito',exact:true}).click();await page.getByLabel('Título del escrito').fill('Documento prueba');await page.getByLabel('Texto del escrito').fill('Primera versión.');await page.getByRole('button',{name:'Guardar versión'}).click();await page.getByText('Versión guardada.',{exact:true}).waitFor();
  await page.getByLabel('Texto del escrito').fill('Segunda versión.');await page.getByRole('button',{name:'Guardar versión'}).click();await page.getByRole('button',{name:'Historial',exact:true}).click();await page.getByRole('button',{name:'Restaurar',exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:'Restaurar',exact:true}).click();assert.equal(state.items.find(i=>i.title==='Documento prueba').data.text,'Primera versión.');
  await nav('DMS');const row=page.locator('.list-row').filter({has:page.getByText('Documento prueba',{exact:true})});await row.getByRole('button',{name:'Opciones de Documento prueba'}).click();await page.getByRole('button',{name:'Proteger versión actual',exact:true}).click();assert.equal(state.items.find(i=>i.title==='Documento prueba').data.locked,true);await row.getByRole('button',{name:'Editar',exact:true}).click();assert.equal(await page.getByLabel('Texto del escrito').getAttribute('readonly'),'');
  await nav('Agente');await page.getByLabel('Describe tu encargo').fill('Analiza este problema de prueba.');await page.getByRole('button',{name:'Enviar encargo'}).click();await page.getByRole('heading',{name:'Análisis',exact:true}).waitFor();assert.equal(state.items.find(i=>i.kind==='conversation').data.messages.length,2);await page.frameLocator('.search-attribution').getByRole('link',{name:'Consulta de prueba'}).waitFor();assert.equal((await page.locator('.search-attribution').getAttribute('sandbox')).includes('allow-scripts'),false);assert.equal((await page.locator('.search-attribution').getAttribute('sandbox')).includes('allow-same-origin'),false);
  await page.reload();await page.getByRole('button',{name:'Analiza este problema de prueba.',exact:true}).click();await page.getByRole('heading',{name:'Análisis',exact:true}).waitFor();
  await nav('Jurisprudencia');await page.getByRole('tab',{name:'Chat jurídico'}).click();assert.equal(await page.getByLabel('Tipo de encargo').inputValue(),'research');
  await nav('Revisión en tabla');await page.locator('.check-row input').first().check();await page.getByRole('button',{name:'Revisar documentos',exact:true}).click();await page.getByText('Segmento 1',{exact:true}).waitFor();await page.getByText('Dato o fragmento pendiente de verificación.',{exact:true}).waitFor();const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar CSV',exact:true}).click();const download=await downloadPromise;const downloaded=await download.path();const csv=await readFile(downloaded,'utf8');assert.ok(csv.includes("'=1+1"),'CSV neutraliza fórmulas al abrir en hojas de cálculo');
  await nav('Monitor');await page.getByRole('button',{name:'Crear monitor',exact:true}).click();await page.getByLabel('Nombre del monitor').fill('Monitor de prueba');await page.getByLabel('URL de la página oficial').fill('https://www.corteconstitucional.gov.co/');await page.getByRole('dialog').getByRole('button',{name:'Guardar',exact:true}).click();await page.getByRole('button',{name:'Comprobar ahora',exact:true}).click();await page.getByText('Estado: Primera lectura guardada',{exact:false}).waitFor();
  await nav('Firma electrónica');await page.getByRole('button',{name:'Nueva solicitud',exact:true}).click();await page.getByLabel('Título del documento',{exact:true}).fill('Solicitud de prueba');await page.getByLabel('Contenido que se enviará a firma').fill('Contenido congelado de prueba.');await page.getByLabel('Nombre de quien firma').fill('Persona ficticia');await page.getByLabel('Correo de referencia').fill('persona@example.invalid');await page.getByRole('button',{name:'Crear enlace privado',exact:true}).click();await page.getByRole('heading',{name:'Enlace de firma preparado'}).waitFor();await close();await page.getByRole('button',{name:'Ver detalle',exact:true}).click();await page.getByText('Contenido congelado de prueba.',{exact:true}).waitFor();await close();
  await page.getByRole('button',{name:'Renovar enlace',exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:'Renovar enlace',exact:true}).click();await page.getByText('Enlace anterior invalidado.',{exact:true}).waitFor();assert.equal(state.lastSignatureToken,2);await close();await page.getByRole('button',{name:'Cancelar',exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:'Cancelar solicitud',exact:true}).click();assert.equal(state.signatures[0].status,'cancelled');
  await nav('Ajustes');await page.getByRole('heading',{name:'Ajustes del despacho'}).waitFor();clean();
},{timeout:60000});

test('Error real de API, texto no confiable y rechazo de ajustes mayores de80k',async t=>{
  const{page,state,nav,clean}=await fixture(t);state.chatFailure=true;
  await page.getByLabel('Describe tu encargo').fill('Consulta cuyo proveedor no está configurado.');await page.getByRole('button',{name:'Enviar encargo'}).click();await page.getByRole('alert').filter({hasText:'Proveedor de IA no configurado.'}).waitFor();assert.equal(await page.locator('.message.assistant').count(),0);
  state.chatFailure=false;state.malicious=true;await page.getByLabel('Describe tu encargo').fill('Comprueba contenido no confiable.');await page.getByRole('button',{name:'Enviar encargo'}).click();await page.getByText('Texto seguro <img src=x onerror="alert(1)"> y <script>alert(2)</script>',{exact:true}).waitFor();assert.equal(await page.locator('.message img,.message script,.source-card a[href^="javascript:"]').count(),0);
  await nav('Editor y versiones');await page.getByRole('button',{name:'Nuevo escrito',exact:true}).click();await page.getByLabel('Texto del escrito').fill('A'.repeat(80001));await page.getByRole('button',{name:'Ajustar con IA',exact:true}).click();await page.getByLabel('Qué quieres ajustar').fill('Mejorar estructura.');const beforeCalls=state.requests.filter(r=>r.p==='/api/despacho/chat').length;await page.getByRole('button',{name:'Preparar propuesta',exact:true}).click();await page.locator('.form-error').filter({hasText:'supera el límite'}).waitFor();assert.equal(state.requests.filter(r=>r.p==='/api/despacho/chat').length,beforeCalls);clean();
},{timeout:30000});

test('Concurrencia: una actualización remota no se pisa desde el editor abierto',async t=>{
  const{page,state,nav,clean}=await fixture(t);const doc=state.add('document','Documento concurrente',{text:'Versión inicial.',versions:[]});await page.getByRole('button',{name:'Actualizar despacho'}).click();await nav('Editor y versiones');await page.getByRole('button',{name:'Editar escrito',exact:true}).click();await page.getByLabel('Texto del escrito').fill('Mi modificación sin guardar.');doc.data.text='Cambio remoto de otra sesión.';doc.version=2;await page.getByRole('button',{name:'Actualizar despacho'}).click();await page.getByRole('button',{name:'Guardar versión',exact:true}).click();await page.getByRole('alert').filter({hasText:'cambió desde que lo abriste'}).waitFor();assert.equal(doc.data.text,'Cambio remoto de otra sesión.');assert.equal(await page.getByLabel('Texto del escrito').inputValue(),'Mi modificación sin guardar.');clean();
},{timeout:30000});

test('Respaldo compacto, importación con margen de formato y advertencia de limpieza parcial',async t=>{
  const{page,state,nav,close,clean}=await fixture(t);
  const doc=state.add('document','Documento para respaldo',{text:'Texto de prueba.\nPárrafo con tildes: jurídica.',versions:[]});
  await page.getByRole('button',{name:'Actualizar despacho'}).click();await nav('Ajustes');
  const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar despacho',exact:true}).click();const download=await downloadPromise;const exported=await readFile(await download.path(),'utf8');assert.equal(exported,JSON.stringify(JSON.parse(exported)));assert.equal(JSON.parse(exported).items[0].data.text,doc.data.text);
  // Un JSON válido de25MiB con espacios externos debe caber: su contenido real es menor de24MiB.
  const formatted=Buffer.concat([Buffer.from(exported),Buffer.alloc(25*1024*1024-Buffer.byteLength(exported),32)]);
  await page.locator('#backup-input').setInputFiles({name:'respaldo-con-espacios.json',mimeType:'application/json',buffer:formatted});await page.getByRole('heading',{name:'Importar copia del despacho',exact:true}).waitFor();await page.getByRole('dialog').getByRole('button',{name:'Importar',exact:true}).click();await page.getByText('Elementos importados: 1',{exact:true}).waitFor();await close();
  state.deleteWarnings=['El registro se eliminó, pero algún archivo original puede seguir almacenado. Contacta con el administrador para completar la limpieza.'];await nav('DMS');await page.getByRole('button',{name:'Opciones de Documento para respaldo',exact:true}).click();await page.getByRole('button',{name:'Eliminar documento',exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:'Eliminar',exact:true}).click();await page.getByRole('alert').filter({hasText:state.deleteWarnings[0]}).waitFor();assert.equal(state.items.some(i=>i.id===doc.id),false);clean();
},{timeout:30000});

test('Móvil350px/390px: menú accesible, cinco productos y ausencia de desbordamiento',async t=>{
  const{page,nav,clean}=await fixture(t,{viewport:{width:390,height:844}});
  await page.getByRole('button',{name:'Abrir navegación'}).click();await page.getByRole('navigation',{name:'Productos'}).getByRole('button',{name:'DMS',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#sidebar').getBoundingClientRect().right<=0);
  await nav('Agente');await page.waitForFunction(()=>document.querySelector('#sidebar').getBoundingClientRect().right<=0);await page.screenshot({path:path.join(artifacts,'despacho-movil.png'),fullPage:true});
  for(const width of [390,350]){await page.setViewportSize({width,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);for(const name of ['Asuntos','DMS','Revisión en tabla','Monitor','Firma electrónica','Ajustes']){await nav(name);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,name+' a'+width+'px');}}
  clean();
},{timeout:45000});
