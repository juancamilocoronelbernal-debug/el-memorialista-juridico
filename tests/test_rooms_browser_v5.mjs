/** Public room UI with production assets, real Chromium and controlled HTTP.
 * No external accounts, emails, storage buckets or private user data are used.
 */
import assert from 'node:assert/strict';
import {test,before,after} from 'node:test';
import {readFile,mkdir,mkdtemp} from 'node:fs/promises';
import {randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {tmpdir} from 'node:os';
import {execFileSync} from 'node:child_process';

const module=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const {chromium}=module.default||module;
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const artifacts=process.env.ROOMS_BROWSER_ARTIFACTS||await mkdtemp(path.join(tmpdir(),'memorialista-rooms-ui-'));
await mkdir(artifacts,{recursive:true});
const origin='https://memorialista.invalid',secret='A'.repeat(43);
const csp=execFileSync(process.env.PYTHON_BIN||'python',['-c',"from app.main import csp_archivo_publico,PRIVATE_DIR; print(csp_archivo_publico(PRIVATE_DIR / 'sala-cliente.html').replace(\"frame-src 'none'\", \"frame-src 'self' blob:\"))"],{cwd:root,encoding:'utf8'}).trim();
let browser;
before(async()=>{browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}:{})});});
after(async()=>{await browser?.close();});

function fixturePdf(){
  const stream='BT /F1 12 Tf 50 730 Td (Copia controlada de prueba - El Memorialista) Tj ET';
  const objects=['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Kids [3 0 R] /Count 1 >>','<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>','<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`];
  let pdf='%PDF-1.4\n';const offsets=[0];
  objects.forEach((o,i)=>{offsets.push(Buffer.byteLength(pdf));pdf+=(i+1)+' 0 obj\n'+o+'\nendobj\n';});
  const xref=Buffer.byteLength(pdf);pdf+='xref\n0 6\n0000000000 65535 f \n'+offsets.slice(1).map(n=>String(n).padStart(10,'0')+' 00000 n \n').join('')+'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+xref+'\n%%EOF';return Buffer.from(pdf);
}
async function fixture(t,{permissions={can_view:true,can_download:true,can_upload:true},expired=false,missing=false,mobile=false,malicious=false,failUpload=false}={}){
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:1000},locale:'es-CO',timezoneId:'America/Bogota',acceptDownloads:true});t.after(()=>context.close());
  const page=await context.newPage(),state={requests:[],errors:[],csp:[],alerts:[],expired,uploads:[],failUpload};
  page.on('pageerror',e=>state.errors.push(e.message));page.on('dialog',async d=>{state.alerts.push(d.message());await d.dismiss();});
  page.on('console',m=>{if(m.type()==='error'&&/Content Security Policy|violates.*directive/i.test(m.text()))state.csp.push(m.text());});
  const docs=[{id:randomUUID(),title:malicious?'<img src=x onerror=alert(1)>':'Contrato de prestación de servicios',source_version:3,pages:4,bytes:184500,sha256:'a'.repeat(64),representation:'pdf_original'},
    {id:randomUUID(),title:'Anexo de obligaciones y cronograma',source_version:1,pages:2,bytes:82500,sha256:'b'.repeat(64),representation:'pdf_original'}];
  const room={id:randomUUID(),title:malicious?'<script>alert(2)</script>':'Revisión del contrato · Estudio Ríos',description:malicious?'<img src=x onerror=alert(3)>':'Consulta las versiones preparadas para esta revisión y aporta los soportes que acordamos. Cada envío queda pendiente de incorporación al expediente.',expires_at:'2035-10-30T23:59:00Z',documents:permissions.can_view?docs:[],link:{id:randomUUID(),label:'Equipo del cliente',...permissions},notice:'El enlace permite acceso a quien lo posea; no verifica su identidad. Las aperturas y descargas se registran.',max_upload_bytes:10485760};
  await page.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url()),p=url.pathname;state.requests.push({url:url.href,path:p,method:request.method(),body:request.postData()});
    const json=(data,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
    if(url.origin!==origin)return route.abort('blockedbyclient');
    if(p==='/sala-cliente')return route.fulfill({contentType:'text/html',headers:{'Content-Security-Policy':csp,'Referrer-Policy':'no-referrer','Cache-Control':'private, no-store'},body:await readFile(root+'/app/private/sala-cliente.html','utf8')});
    if(p.startsWith('/static/sala-cliente/'))return route.fulfill({contentType:p.endsWith('.js')?'application/javascript':'text/css',body:await readFile(root+'/app'+p,'utf8')});
    if(p==='/static/asesor/favicon.svg')return route.fulfill({status:204,body:''});
    if(state.expired&&p.startsWith('/api/salas-v5/'))return json({detail:'El enlace de la sala caducó o fue revocado.'},404);
    if(p==='/api/salas-v5/view')return json(room);
    if(p==='/api/salas-v5/document'){
      const body=request.postDataJSON();if(body.mode==='download'&&!permissions.can_download)return json({detail:'Este enlace no permite descargar.'},403);
      return route.fulfill({contentType:'application/pdf',body:fixturePdf()});
    }
    if(p==='/api/salas-v5/upload'){
      const body=request.postData()||'';state.uploads.push(/name="request_id"\r\n\r\n([^\r]+)/.exec(body)?.[1]);
      if(state.failUpload){state.failUpload=false;return json({detail:'No se confirmó la recepción. Reintenta este mismo envío.'},502);}
      return json({received:true,id:randomUUID(),filename:'Soporte del cliente.txt'});
    }
    return json({detail:'Ruta no prevista'},404);
  });
  await page.goto(origin+'/sala-cliente'+(missing?'':'#'+secret));
  await page.locator(expired||missing?'#error':'#room').waitFor({state:'visible'});
  return {page,state,room,clean:()=>{assert.deepEqual(state.errors,[]);assert.deepEqual(state.csp,[]);assert.deepEqual(state.alerts,[]);}};
}

test('Room portal reviews PDF, downloads and rechecks revoked access without URL secrets',async t=>{
  const {page,state,clean}=await fixture(t);
  assert.equal(await page.evaluate(()=>location.hash),'');
  await page.getByRole('button',{name:'Ver documento',exact:true}).first().click();
  await page.getByRole('dialog').waitFor({state:'visible'});assert.match(await page.locator('#pdf-frame').getAttribute('src'),/^blob:/);
  await page.getByRole('button',{name:'Cerrar',exact:true}).click();
  const downloaded=page.waitForEvent('download');await page.getByRole('button',{name:'Descargar PDF',exact:true}).first().click();assert.match((await downloaded).suggestedFilename(),/\.pdf$/);
  assert.ok(state.requests.filter(r=>r.path.startsWith('/api/')).every(r=>r.method==='POST'&&!r.url.includes(secret)));
  assert.deepEqual(await page.evaluate(()=>({local:localStorage.length,session:sessionStorage.length})),{local:0,session:0});
  await page.screenshot({path:path.join(artifacts,'sala-cliente-escritorio.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.screenshot({path:path.join(artifacts,'sala-cliente-movil.png'),fullPage:true});
  state.expired=true;await page.getByRole('button',{name:'Actualizar acceso'}).click();await page.locator('#error').waitFor({state:'visible'});assert.equal(await page.locator('#room').isVisible(),false);clean();
});

test('Room upload retry keeps the same idempotency key and confirms receipt',async t=>{
  const {page,state,clean}=await fixture(t,{failUpload:true});
  await page.locator('#upload-file').setInputFiles({name:'Soporte del cliente.txt',mimeType:'text/plain',buffer:Buffer.from('Aporte controlado.')});
  await page.getByRole('button',{name:'Enviar este archivo',exact:true}).click();
  await page.getByRole('button',{name:'Reintentar este envío',exact:true}).waitFor();
  await page.getByRole('button',{name:'Reintentar este envío',exact:true}).click();
  await page.getByText('Archivo recibido para revisión.',{exact:true}).waitFor();assert.equal(state.uploads.length,2);assert.ok(state.uploads[0]);assert.equal(state.uploads[0],state.uploads[1]);
  assert.equal(await page.locator('#upload-file').inputValue(),'');clean();
});

test('An upload-only link does not expose shared document metadata or viewer controls',async t=>{
  const {page,state,clean}=await fixture(t,{permissions:{can_view:false,can_download:false,can_upload:true}});
  assert.equal(await page.getByRole('button',{name:'Ver documento',exact:true}).count(),0);assert.equal(await page.getByRole('button',{name:'Descargar PDF',exact:true}).count(),0);
  assert.equal(await page.locator('#upload-form').isVisible(),true);assert.equal(state.requests.some(r=>r.path==='/api/salas-v5/document'),false);clean();
});

test('A view-only link does not offer download or upload actions',async t=>{
  const {page,clean}=await fixture(t,{permissions:{can_view:true,can_download:false,can_upload:false}});
  assert.equal(await page.getByRole('button',{name:'Ver documento',exact:true}).count(),2);assert.equal(await page.getByRole('button',{name:'Descargar PDF',exact:true}).count(),0);assert.equal(await page.locator('#upload-form').isVisible(),false);clean();
});

test('Expired and missing room links fail visibly before exposing content',async t=>{
  const a=await fixture(t,{expired:true});assert.match(await a.page.locator('#error-message').textContent(),/caducó|revocado/);a.clean();
  const b=await fixture(t,{missing:true});assert.equal(b.state.requests.filter(r=>r.path.startsWith('/api/')).length,0);b.clean();
});

test('Room metadata renders as text under CSP and remains usable on mobile',async t=>{
  const {page,clean}=await fixture(t,{mobile:true,malicious:true});
  assert.equal(await page.locator('#room-title').textContent(),'<script>alert(2)</script>');assert.equal(await page.locator('#document-list img').count(),0);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.screenshot({path:path.join(artifacts,'sala-cliente-movil-xss-prueba.png'),fullPage:true});clean();
});
