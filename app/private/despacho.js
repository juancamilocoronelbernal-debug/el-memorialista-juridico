/* El Memorialista · Despacho privado. Los permisos y la persistencia residen en la API. */
(() => {
'use strict';
const $ = (selector, parent = document) => parent.querySelector(selector);
const API = '/api/despacho';
const S = { client:null,user:null,items:[],caps:null,page:'chat',matterId:'',conversationId:null,conversationVersion:null,messages:[],mode:'general',knowledgeScope:'auto',selectedDocs:new Set(),playbookId:'',chatDraft:'',chatTask:null,chatCounter:0,chatUnsaved:false,editor:null,editorDirty:false,tableResult:null,signatures:[],signatureError:'',loadError:'',loading:true,search:'',filter:'',versionTarget:null,uploadUse:'library',modalReturn:null,selectedFragmentsState:new Map(),customSelectedFragments:[] };
const icons = {
 chat:['M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8z'],
 spark:['m12 3 2.2 6.8L21 12l-6.8 2.2L12 21l-2.2-6.8L3 12l6.8-2.2Z','m20 2 .6 1.4L22 4l-1.4.6L20 6l-.6-1.4L18 4l1.4-.6Z'],
 book:['M4 4h6a3 3 0 0 1 3 3v15a4 4 0 0 0-4-3H4Z','M20 4h-4a3 3 0 0 0-3 3v15a4 4 0 0 1 4-3h3Z'],
 search:['M21 21l-5-5','M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0'],
 monitor:['M3 3h18v14H3Z','M8 21h8','M12 17v4','m6 11 3-3 3 4 3-6 3 3'],
 folder:['M3 5h6l2 3h10v12H3Z'],
 file:['M14 2H5v20h14V7Z','M14 2v5h5','M8 12h8','M8 16h8'],
 sign:['m4 16 12-12 4 4L8 20H4Z','m13 7 4 4','M12 21h9'],
 case:['M3 7h18v13H3Z','M8 7V4h8v3','M3 12h18','M10 10v4h4v-4'],
 table:['M3 4h18v16H3Z','M3 10h18','M9 4v16','M15 4v16'],
 settings:['M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8','m9 3 1-1h4l1 1v2l2 1 2-1 2 3-1 2v3l1 2-2 3-2-1-2 1v2l-1 1h-4l-1-1v-2l-2-1-2 1-2-3 1-2v-3L3 8l2-3 2 1 2-1Z'],
 arrow:['M5 12h14','m13 6 6 6-6 6'],
 up:['M12 20V4','m6 10 6-6 6 6'],
 attach:['M8 12 15 5a4 4 0 0 1 6 6L11 21a6 6 0 0 1-8-8L14 2','m7 13 9-9'],
 lock:['M5 10h14v11H5Z','M8 10V6a4 4 0 0 1 8 0v4'],
 copy:['M8 8h13v13H8Z','M4 16H2V2h14v2'],
 download:['M12 3v12','m6 9 6 6 6-6','M4 17v4h16v-4'],
 upload:['M12 17V5','m6 11 6-6 6 6','M4 17v4h16v-4'],
 plus:['M12 5v14','M5 12h14'],
 check:['m5 12 4 4L19 6'],
 clock:['M12 8v5l3 2','M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
 edit:['m16 3 5 5L8 21H3v-5Z','m14 5 5 5'],
 trash:['M3 6h18','M9 6V3h6v3','M5 6l1 15h12l1-15','M10 10v7','M14 10v7'],
 link:['M10 13a5 5 0 0 0 7 0l4-4a5 5 0 0 0-7-7l-2 2','M14 11a5 5 0 0 0-7 0l-4 4a5 5 0 0 0 7 7l2-2'],
 logout:['M9 21H3V3h6','M9 12h12','m17 8 4 4-4 4'],
 close:['M6 6l12 12','M18 6 6 18'],
 history:['M3 11a9 9 0 1 1 3 8','M3 3v8h8','M12 7v6l4 2'],
 eye:['M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z','M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0'],
 columns:['M3 3h18v18H3Z','M12 3v18'],
 calendar:['M3 5h18v16H3Z','M7 2v6','M17 2v6','M3 10h18'],
 external:['M14 3h7v7','m10 14 11-11','M10 3H3v18h18v-7']
};
function icon(name){const node=document.createElementNS('http://www.w3.org/2000/svg','svg');node.setAttribute('viewBox','0 0 24 24');node.setAttribute('class','icon');node.setAttribute('aria-hidden','true');for(const d of icons[name]||icons.file){const p=document.createElementNS(node.namespaceURI,'path');p.setAttribute('d',d);node.append(p);}return node;}
function el(tag,attrs={},...children){const n=document.createElement(tag);for(const[k,v]of Object.entries(attrs)){if(v===null||v===undefined||v===false)continue;if(k==='class')n.className=v;else if(k==='text')n.textContent=String(v);else if(k==='on')for(const[e,fn]of Object.entries(v))n.addEventListener(e,fn);else if(k==='dataset')Object.assign(n.dataset,v);else if(k in n&&!k.startsWith('aria'))n[k]=v;else n.setAttribute(k,v===true?'':String(v));}for(const c of children.flat(Infinity)){if(c!==null&&c!==undefined&&c!==false)n.append(c instanceof Node?c:document.createTextNode(String(c)));}return n;}
function text(value){return value===null||value===undefined?'':typeof value==='string'?value:JSON.stringify(value);}
function byKind(kind){return S.items.filter(i=>i.kind===kind).sort((a,b)=>String(b.updated_at||'').localeCompare(String(a.updated_at||'')));}
function item(id){return S.items.find(i=>i.id===id);}
function scoped(kind){return byKind(kind).filter(i=>!S.matterId||i.matter_id===S.matterId);}
function matterTitle(id){return item(id)?.title||'Sin asunto asignado';}
function shortDate(value,withTime=false){if(!value)return'—';const d=new Date(value);if(Number.isNaN(d.valueOf()))return String(value);return new Intl.DateTimeFormat('es-CO',{day:'2-digit',month:'short',...(withTime?{hour:'2-digit',minute:'2-digit'}:{year:'numeric'})}).format(d);}
function localDate(value){if(!value)return'';const str=String(value);return /^\d{4}-\d{2}-\d{2}/.test(str)?str.slice(0,10):'';}
function safeUrl(value){try{const u=new URL(String(value));if(u.protocol==='https:'&& !u.username&&!u.password)return u.href;}catch{}return null;}
function link(label,url,cls=''){const u=safeUrl(url);return u?el('a',{href:u,target:'_blank',rel:'noopener noreferrer',class:cls},label):el('span',{class:cls},label);}
function act(fn){return async e=>{try{await fn(e);}catch(error){if(error?.name!=='AbortError')toast(error?.message||'No se pudo completar la acción.','error');}};}
function button(label,fn,{icon:ic,class:cls='button',title,disabled=false}={}){return el('button',{type:'button',class:cls,title,disabled,on:{click:act(fn)}},ic?icon(ic):null,label);}
function badge(label,type=''){return el('span',{class:`badge ${type}`},label);}
function toast(message,type=''){const n=el('div',{class:`toast ${type}`,role:type==='error'?'alert':'status'},el('span',{},message),button('×',()=>n.remove(),{class:'',title:'Cerrar aviso'}));$('#toast-region').append(n);while($('#toast-region').children.length>2)$('#toast-region').firstElementChild.remove();setTimeout(()=>n.remove(),type==='error'?14000:6500);}
async function busy(btn,fn){const old=btn.disabled;btn.disabled=true;btn.setAttribute('aria-busy','true');try{return await fn();}finally{btn.disabled=old;btn.removeAttribute('aria-busy');}}
function downloadBlob(blob,name){const url=URL.createObjectURL(blob);const a=el('a',{href:url,download:name});document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);}
function filename(title,ext){return (String(title||'documento').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-zA-Z0-9_-]+/g,'-').replace(/^-|-$/g,'').slice(0,90)||'documento')+'.'+ext;}
async function copy(value){try{await navigator.clipboard.writeText(String(value));toast('Copiado al portapapeles.');}catch{const ta=el('textarea',{value:String(value),readOnly:true});showModal('Copiar contenido',el('div',{},el('p',{class:'inline-help'},'Selecciona y copia el contenido.'),ta),[]);ta.select();}}
async function api(path,{method='GET',body,signal,blob=false,retry=true}={}){const session=await S.client.auth.getSession();const token=session.data?.session?.access_token;if(!token)throw new Error('Tu sesión ha caducado. Inicia sesión de nuevo.');const headers={Authorization:'Bearer '+token};let payload=body;if(body!==undefined&&!(body instanceof FormData)){headers['Content-Type']='application/json';payload=JSON.stringify(body);}const r=await fetch(path.startsWith('/api/')?path:API+path,{method,headers,body:payload,signal,cache:'no-store',credentials:'same-origin'});if(r.status===401&&retry){const refreshed=await S.client.auth.refreshSession();if(refreshed.data?.session)return api(path,{method,body,signal,blob,retry:false});}if(!r.ok){const data=await r.json().catch(()=>({}));const detail=typeof data.detail==='string'?data.detail:typeof data.error==='string'?data.error:'No se pudo completar la operación (HTTP '+r.status+').';const error=new Error(detail);error.status=r.status;throw error;}if(blob)return r.blob();if(r.status===204)return{};return r.json();}

/* Streaming real: SSE POST con Bearer, sin poner la clave del proveedor en el navegador. */
async function streamChatRequest(request,signal,onEvent,retry=true){
  const session=await S.client.auth.getSession();
  const token=session.data?.session?.access_token;
  if(!token)throw new Error('Tu sesión ha caducado. Inicia sesión de nuevo.');
  const r=await fetch(API+'/chat/stream',{
    method:'POST',
    headers:{Authorization:'Bearer '+token,'Content-Type':'application/json',Accept:'text/event-stream'},
    body:JSON.stringify(request),signal,cache:'no-store',credentials:'same-origin'
  });
  if(r.status===401&&retry){
    const renewed=await S.client.auth.refreshSession();
    if(renewed.data?.session)return streamChatRequest(request,signal,onEvent,false);
  }
  if(!r.ok){
    const response=await r.json().catch(()=>({}));
    throw new Error(typeof response.detail==='string'?response.detail:'Error al iniciar la respuesta (HTTP '+r.status+').');
  }
  if(!r.headers.get('Content-Type')?.includes('text/event-stream')||!r.body)throw new Error('El servidor no entregó un flujo de texto válido.');
  const reader=r.body.getReader();
  const decoder=new TextDecoder();
  let buffer='',completed=false;
  async function consume(raw){
    const lines=raw.split('\n');
    const event=(lines.find(line=>line.startsWith('event:'))||'event: message').slice(6).trim();
    const json=lines.filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trimStart()).join('\n');
    if(!json)return;
    let data;
    try{data=JSON.parse(json);}catch{throw new Error('El servidor envió un fragmento de respuesta inválido.');}
    if(event==='error'){
      const err=new Error(data?.message||'La respuesta se interrumpió.');
      err.status=data?.status;
      throw err;
    }
    if(event==='done')completed=true;
    await onEvent(event,data);
  }
  try{
    while(true){
      const {done,value}=await reader.read();
      buffer+=(done?decoder.decode():decoder.decode(value,{stream:true}));
      buffer=buffer.replace(/\r\n/g,'\n');
      let stop;
      while((stop=buffer.indexOf('\n\n'))!==-1){
        const frame=buffer.slice(0,stop);buffer=buffer.slice(stop+2);
        await consume(frame);
      }
      if(done)break;
    }
    if(!completed)throw new Error('Se cortó la conexión antes de completar la respuesta. El texto parcial no se guardó.');
  }finally{
    reader.releaseLock();
  }
}
function mergeItem(value){const data=value?.item||value;if(!data?.id)return data;const pos=S.items.findIndex(i=>i.id===data.id);if(pos<0)S.items.push(data);else S.items[pos]=data;return data;}
async function createItem(kind,title,data,matterId=S.matterId){return mergeItem(await api('/items',{method:'POST',body:{kind,title,matter_id:matterId||null,data}}));}
async function updateItem(record,changes){if(!record?.id)throw new Error('No se encontró el elemento. Actualiza el despacho.');return mergeItem(await api('/items/'+encodeURIComponent(record.id),{method:'POST',body:{...changes,expected_version:record.version}}));}
async function removeItem(record){const result=await api('/items/'+encodeURIComponent(record.id)+'?version='+encodeURIComponent(record.version),{method:'DELETE'});S.items=S.items.filter(i=>i.id!==record.id);S.selectedDocs.delete(record.id);if(S.conversationId===record.id){S.conversationId=null;S.messages=[];}if(S.editor?.id===record.id){S.editor=null;S.editorDirty=false;}render();if(Array.isArray(result?.warnings)&&result.warnings.length)toast(result.warnings.map(text).join('\n'),'error');}
async function refresh({silent=false}={}){const all=[];let offset=0;for(let p=0;p<100;p++){const batch=await api('/items?offset='+offset+'&limit=100');all.push(...(Array.isArray(batch)?batch:batch.items||[]));if(!batch.has_more)break;offset+=100;if(p===99)throw new Error('La colección es muy grande. Utiliza la exportación para revisar todos los elementos.');}S.items=all;S.loadError='';if(!silent)toast('Despacho actualizado.');const caps=await api('/capabilities').catch(()=>null);if(caps)S.caps=caps;render();}
function pageHeader(title,description,actions=[],eyebrow='MI DESPACHO'){return el('div',{class:'page-header'},el('div',{},el('div',{class:'eyebrow'},eyebrow),el('h1',{},title),el('p',{},description)),el('div',{class:'actions'},actions));}
function empty(title,description,action,ic='folder'){return el('div',{class:'empty-state'},icon(ic),el('h2',{},title),el('p',{},description),action);}
function showModal(title,body,footer=[],wide=false){const m=$('#modal');S.modalReturn=document.activeElement;$('#modal-title').textContent=title;$('#modal-body').replaceChildren(body);$('#modal-footer').replaceChildren(...footer);m.classList.toggle('wide',wide);if(!m.open)m.showModal();return m;}
function closeModal(){const m=$('#modal');if(m.open)m.close();}
function field(label,{value='',name,type='text',required=false,placeholder='',help='',options,rows,min,max}={}){const id='f-'+(name||Math.random().toString(36).slice(2));let input;if(options){input=el('select',{id,name,required});for(const option of options){const o=typeof option==='string'?{value:option,label:option}:option;input.append(el('option',{value:o.value,selected:String(value)===String(o.value)},o.label));}}else input=el(type==='textarea'?'textarea':'input',{id,name,type:type==='textarea'?undefined:type,value,required,placeholder,rows,min,max,maxLength:type==='textarea'?1000000:500});return{wrap:el('div',{class:'field'},el('label',{htmlFor:id},label),input,help?el('span',{class:'help'},help):null),input};}
function matterOptions(includeAll=false){return[{value:'',label:includeAll?'Todos los asuntos':'Sin asunto asignado'},...byKind('matter').map(m=>({value:m.id,label:m.title}))];}
function formModal(title,fields,onSave,{label='Guardar',extra,wide=false}={}){const form=el('form',{});const error=el('div',{class:'form-error',hidden:true,role:'alert'});form.append(error,extra||[],...fields.map(f=>f.wrap));const save=button(label,()=>form.requestSubmit(),{class:'button primary',icon:'check'});form.addEventListener('submit',async e=>{e.preventDefault();error.hidden=true;await busy(save,async()=>{try{await onSave();closeModal();}catch(err){error.textContent=err.message||'No se pudo guardar.';error.hidden=false;}});});showModal(title,form,[button('Cancelar',closeModal),save],wide);return form;}
function confirmDialog(title,message,onYes,label='Eliminar'){return new Promise(resolve=>{const yes=button(label,async()=>{await busy(yes,async()=>{await onYes();closeModal();resolve(true);});},{class:'button danger'});const no=button('Cancelar',()=>{closeModal();resolve(false);});showModal(title,el('p',{class:'inline-help'},message),[no,yes]);});}
function captureDrafts(){const t=$('#chat-input');if(t)S.chatDraft=t.value;if(S.editor){const a=$('#editor-text'),b=$('#editor-title');if(a)S.editor.text=a.value;if(b)S.editor.title=b.value;}}
function setPage(page){captureDrafts();v5StopRequests();S.search='';S.filter='';S.page=page;if(page==='investigacion')S.mode='research';else if(page==='chat'&&S.mode==='research'&&!S.conversationId)S.mode='general';history.replaceState(null,'','#'+page);closeSidebar();render();if(page==='firmas'&&(!S.caps?.signatures_v5||V5.signatureView==='legacy'))loadSignatures();v5PageLoad(page);}
function renderNav(){const primary=[['chat','Agente','spark'],['investigacion','Jurisprudencia','book'],['monitores','Monitor','monitor'],['biblioteca','DMS','folder'],['firmas','Firma electrónica','sign']];const secondary=[['calidad','Centro de Calidad','shield'],['encargos','Encargos por etapas','spark'],['tareas','Tareas programadas','calendar'],['conexiones','Conexiones','link'],['salas','Salas de documentos','lock'],['asuntos','Asuntos','case'],['tablas','Revisión en tabla','table'],['documentos','Editor y versiones','file'],['ajustes','Ajustes','settings']];const nav=$('#main-nav');nav.replaceChildren(el('div',{class:'nav-label'},'PRODUCTOS'),el('div',{class:'nav-group'},primary.map(([p,t,ic])=>button(t,()=>setPage(p),{icon:ic,class:'nav-item '+(S.page===p?'active':'')}))),el('div',{class:'nav-label'},'MI TRABAJO'),el('div',{class:'nav-group'},secondary.map(([p,t,ic])=>button(t,()=>setPage(p),{icon:ic,class:'nav-item '+(S.page===p?'active':'')}))));nav.querySelectorAll('.active').forEach(n=>n.setAttribute('aria-current','page'));$('#page-name').textContent=[...primary,...secondary].find(v=>v[0]===S.page)?.[1]||'Agente';const recent=byKind('conversation').slice(0,5);$('#recent-chats').replaceChildren(...(recent.length?recent.map(c=>button(c.title,()=>openConversation(c.id),{class:'recent-chat '+(c.id===S.conversationId?'active':''),title:c.title})):[el('p',{class:'sidebar-empty'},'Tus encargos guardados aparecerán aquí.')]));}
function showNotice(){const n=$('#workspace-notice');const msg=S.loadError||(S.caps?.storage?.ready===false?S.caps.storage.message||'El almacenamiento del despacho necesita configuración.':'');n.hidden=!msg;if(msg)n.replaceChildren(el('span',{},msg),button('Reintentar',()=>refresh({silent:true}),{class:''}));}
function render(){renderNav();showNotice();if(S.loading)return;const main=$('#main');const renders={chat:renderChat,investigacion:renderChat,asuntos:renderMatters,biblioteca:renderLibrary,tablas:renderTables,documentos:renderEditor,monitores:renderMonitors,firmas:renderSigningV5,ajustes:renderSettings,encargos:renderJobsV5,tareas:renderSchedulesV5,conexiones:renderConnectionsV5,salas:renderRoomsV5,calidad:renderCalidadJuridica};main.replaceChildren(v5EnhancePage((renders[S.page]||renderChat)()));}
function closeSidebar(){$('#sidebar').classList.remove('open');$('#sidebar-scrim').hidden=true;$('#mobile-menu').setAttribute('aria-expanded','false');document.body.classList.remove('menu-open');}
function openSidebar(){$('#sidebar').classList.add('open');$('#sidebar-scrim').hidden=false;$('#mobile-menu').setAttribute('aria-expanded','true');document.body.classList.add('menu-open');}
function cancelChat(){
  const task=S.chatTask;
  if(!task)return;
  task.controller.abort();
  if(task.draft){
    if(task.draft.content){
      task.draft.incomplete=true;
      task.draft.streaming=false;
      task.draft.warnings=['Respuesta interrumpida: no es una respuesta completa y no se guardó.'];
    }else S.messages=S.messages.filter(m=>m!==task.draft);
  }
  S.chatTask=null;
  S.chatCounter++;
  toast('Respuesta detenida. El texto parcial no se guarda como documento final.');
  render();
}
async function newChat(){if(S.chatTask){await confirmDialog('Detener el encargo actual','Se detendrá la respuesta en curso antes de abrir un nuevo encargo.',async()=>cancelChat(),'Detener y continuar');if(S.chatTask)return;}S.conversationId=null;S.conversationVersion=null;S.messages=[];S.chatDraft='';S.chatUnsaved=false;S.selectedDocs.clear();S.mode='general';S.knowledgeScope='auto';S.analysisDepth='auto';setPage('chat');$('#chat-input')?.focus();}
function openConversation(id){if(S.chatTask){toast('Detén el encargo actual antes de abrir otra conversación.');return;}const c=item(id);if(!c)return;S.conversationId=id;S.conversationVersion=c.version;S.messages=Array.isArray(c.data?.messages)?c.data.messages.slice():[];S.matterId=c.matter_id||'';S.mode=c.data?.mode||'general';S.knowledgeScope=['auto','off','documents','legal','all','official'].includes(c.data?.knowledge_scope)?c.data.knowledge_scope:'auto';S.analysisDepth=['auto','quick','balanced','deep'].includes(c.data?.depth)?c.data.depth:'auto';S.chatDraft='';S.chatUnsaved=false;S.selectedDocs=new Set((c.data?.document_ids||[]).filter(id=>item(id)));setPage(S.mode==='research'?'investigacion':'chat');}
function formatSectionName(s) {
  const names = {
    encabezado: 'Encabezado',
    identificacion: 'Identificación',
    hechos: 'Hechos',
    antecedentes: 'Antecedentes',
    problema_juridico: 'Problema Jurídico',
    consideraciones: 'Consideraciones',
    fundamentos_juridicos: 'Fundamentos Jurídicos',
    ratio_decidendi: 'Ratio Decidendi',
    parte_resolutiva: 'Parte Resolutiva',
    aclaracion_voto: 'Aclaración de Voto',
    salvamento_voto: 'Salvamento de Voto',
    referencias_normativas: 'Referencias Normativas',
    seccion_desconocida: 'Sección General'
  };
  return names[s] || s;
}

function handleCitationClick(ref, m) {
  let sources = m?.sources || [];
  if (!sources.length) {
    for (const msg of S.messages.slice().reverse()) {
      if (Array.isArray(msg.sources) && msg.sources.length) {
        sources = msg.sources;
        m = msg;
        break;
      }
    }
  }
  const cleanRef = ref.replace(/\s+/g, '');
  const matchedSource = sources.find(s => (s.id || '').replace(/\s+/g, '') === cleanRef);
  const groupedDocs = groupSourcesByDocument(sources, m?.content || '', m?.coverage);
  let targetGroup = null;
  if (matchedSource) {
    targetGroup = groupedDocs.find(g => g.fragments.some(f => (f.id || '').replace(/\s+/g, '') === cleanRef));
  }
  if (!targetGroup && groupedDocs.length) targetGroup = groupedDocs[0];
  if (targetGroup) {
    openEvidenceModal(targetGroup, 'cited', cleanRef);
  } else {
    toast(`Cita ${ref}: Fuente referenciada en la respuesta.`);
  }
}

function plainRich(content, m){
  const holder=el('div',{class:'message-content'});
  const rawLines=String(content||'').split('\n');
  let inCode=false,codeLines=[];
  let i=0;

  function parseInline(str){
    const frag=document.createDocumentFragment();
    if(!str)return frag;
    const regex=/(\[(?:O\d+|D\d+|SEL\d*)\s*-\s*S\d+\]|\*\*[^*]+\*\*|`[^`]+`)/g;
    const parts=str.split(regex);
    for(const part of parts){
      if(!part)continue;
      if(part.startsWith('**')&&part.endsWith('**')){
        frag.append(el('strong',{},part.slice(2,-2)));
      }else if(part.startsWith('`')&&part.endsWith('`')){
        frag.append(el('code',{},part.slice(1,-1)));
      }else if(/^\[(?:O\d+|D\d+|SEL\d*)\s*-\s*S\d+\]$/i.test(part)){
        const ref=part.slice(1,-1).trim();
        const pill=el('button',{
          type:'button',
          class:'v5-citation-pill',
          'data-ref':ref,
          title:`Ver evidencia del fragmento ${part}`
        },part);
        pill.addEventListener('click',(e)=>{
          e.preventDefault();
          e.stopPropagation();
          handleCitationClick(ref,m);
        });
        frag.append(pill);
      }else{
        frag.append(document.createTextNode(part));
      }
    }
    return frag;
  }

  while(i<rawLines.length){
    const line=rawLines[i];
    if(line.startsWith('```')){
      if(inCode){
        holder.append(el('pre',{},codeLines.join('\n')));
        codeLines=[];
      }
      inCode=!inCode;
      i++;
      continue;
    }
    if(inCode){
      codeLines.push(line);
      i++;
      continue;
    }

    // Markdown Table Detection (| Col | Col |)
    if(line.trim().startsWith('|')&&line.trim().endsWith('|')){
      const nextLine=(i+1<rawLines.length)?rawLines[i+1].trim():'';
      if(/^\|?\s*:?-{2,}:?\s*(\|:?-{2,}:?\s*)*\|?$/.test(nextLine)){
        const headerCells=line.split('|').slice(1,-1).map(c=>c.trim());
        const table=el('table',{class:'v5-markdown-table'});
        const thead=el('thead',{},el('tr',{},headerCells.map(h=>el('th',{},parseInline(h)))));
        const tbody=el('tbody');
        i+=2;
        while(i<rawLines.length&&rawLines[i].trim().startsWith('|')&&rawLines[i].trim().endsWith('|')){
          const rowCells=rawLines[i].split('|').slice(1,-1).map(c=>c.trim());
          tbody.append(el('tr',{},rowCells.map(c=>el('td',{},parseInline(c)))));
          i++;
        }
        table.append(thead,tbody);
        holder.append(el('div',{class:'v5-table-wrapper'},table));
        continue;
      }
    }

    // Encabezados
    const hMatch=line.match(/^(#{1,4})\s+(.+)/);
    if(hMatch){
      const level=hMatch[1].length;
      const tag=level===1?'h2':level===2?'h3':level===3?'h4':'h5';
      const headingNode=el(tag);
      headingNode.append(parseInline(hMatch[2]));
      holder.append(headingNode);
      i++;
      continue;
    }

    // Citas en bloque
    if(line.startsWith('> ')){
      const bq=el('blockquote',{class:'v5-blockquote'});
      bq.append(parseInline(line.slice(2)));
      holder.append(bq);
      i++;
      continue;
    }

    // Listas con viñetas
    if(/^\s*[-*]\s+/.test(line)){
      const ul=el('ul');
      while(i<rawLines.length&&/^\s*[-*]\s+/.test(rawLines[i])){
        const li=el('li');
        li.append(parseInline(rawLines[i].replace(/^\s*[-*]\s+/,'')));
        ul.append(li);
        i++;
      }
      holder.append(ul);
      continue;
    }

    // Listas numeradas
    if(/^\s*\d+\.\s+/.test(line)){
      const ol=el('ol');
      while(i<rawLines.length&&/^\s*\d+\.\s+/.test(rawLines[i])){
        const li=el('li');
        li.append(parseInline(rawLines[i].replace(/^\s*\d+\.\s+/,'')));
        ol.append(li);
        i++;
      }
      holder.append(ol);
      continue;
    }

    if(!line.trim()){
      holder.append(el('div',{class:'spacer'}));
    }else{
      const p=el('div');
      p.append(parseInline(line));
      holder.append(p);
    }
    i++;
  }

  if(codeLines.length){
    holder.append(el('pre',{},codeLines.join('\n')));
  }
  return holder;
}

function groupSourcesByDocument(sources, content, coverage){
  if(!Array.isArray(sources)||!sources.length)return [];
  const groups=new Map();
  for(const s of sources){
    const key=s.url||s.source_url||s.document_id||s.title||s.id;
    if(!groups.has(key)){
      groups.set(key,{
        key,
        title:s.title||'Documento jurídico',
        url:s.url||s.source_url||'',
        kind:s.kind||'official',
        source_id:s.source_id||'',
        document_id:s.document_id||'',
        date:s.date||'',
        version:s.document_version||s.version||1,
        fragments:[],
        coverage:coverage||{}
      });
    }
    groups.get(key).fragments.push(s);
  }

  const result=[];
  for(const g of groups.values()){
    // Citados en la respuesta
    const citedFragments=g.fragments.filter(f=>{
      if(!f.id)return false;
      const cleanId=f.id.replace(/\s+/g,'');
      const regex=new RegExp('\\b'+cleanId.replace('-','\\s*-\\s*')+'\\b','i');
      return regex.test(content||'');
    });
    g.citedFragments=citedFragments;
    g.citadosCount=citedFragments.length;
    g.enviadosCount=g.fragments.length;
    g.seleccionadosCount=g.fragments.length;
    const totalFound=coverage?.candidates_retrieved||coverage?.available_passages||g.fragments.length;
    g.encontradosCount=Math.max(totalFound,g.fragments.length);
    result.push(g);
  }
  return result;
}

function renderFragmentItem(frag, docGroup){
  const key=frag.id||(frag.document_id?`${frag.document_id}-${frag.segment}`:`seg-${frag.segment||Math.random()}`);
  const isSelected=S.selectedFragmentsState.has(key);
  const card=el('article',{
    class:'v5-fragment-item '+(isSelected?'selected':''),
    id:'frag-'+key
  });

  const checkbox=el('input',{type:'checkbox',class:'v5-frag-checkbox',checked:isSelected});
  checkbox.addEventListener('change',()=>{
    toggleFragmentSelection(frag,docGroup,checkbox.checked);
    card.classList.toggle('selected',checkbox.checked);
  });

  const sec=frag.section||'seccion_desconocida';
  const secBadge=el('span',{class:`v5-section-badge v5-sec-${sec}`},formatSectionName(sec));
  const labelId=el('strong',{class:'v5-frag-id'},frag.id?`[${frag.id}]`:`Segmento ${frag.segment||1}`);

  const copyBtn=button('Copiar',async(e)=>{
    e.stopPropagation();
    await copy(frag.excerpt||frag.text||frag.content||'');
    toast('✓ Fragmento copiado al portapapeles');
  },{class:'button small text-button'});

  const score=frag.rerank_score||frag.score;
  const scoreBadge=score?el('small',{class:'source-meta'},`Relevancia: ${Math.round(score*100)}%`):null;

  const header=el('div',{class:'v5-frag-header'},checkbox,labelId,secBadge,scoreBadge,copyBtn);
  const textContent=frag.excerpt||frag.text||frag.content||'';
  const body=el('div',{class:'v5-frag-body'},textContent);

  card.append(header,body);
  return card;
}

function renderGroupedDocumentCard(docGroup, m, options={}){
  const card=el('article',{class:'v5-grouped-card'});
  const header=el('div',{class:'v5-grouped-header'});

  const titleRow=el('div',{},
    el('h3',{class:'v5-grouped-title'},docGroup.title),
    el('div',{class:'v5-grouped-meta'},
      [
        docGroup.kind==='official'?'Corpus Jurídico Oficial':docGroup.kind==='web'?'Fuente de búsqueda':'Documento privado DMS',
        docGroup.source_id?`Organismo: ${docGroup.source_id}`:'',
        docGroup.date?`Fecha: ${docGroup.date}`:'',
        docGroup.version?`Versión ${docGroup.version}`:''
      ].filter(Boolean).join(' · ')
    )
  );
  header.append(titleRow);

  // Barra con los 4 Contadores Verificables
  const countersBar=el('div',{class:'v5-counters-bar'},
    el('div',{class:'v5-counter-item'},el('small',{},'Encontrados'),el('strong',{},String(docGroup.encontradosCount))),
    el('div',{class:'v5-counter-item'},el('small',{},'Seleccionados RAG'),el('strong',{},String(docGroup.seleccionadosCount))),
    el('div',{class:'v5-counter-item'},el('small',{},'Enviados a Gemini'),el('strong',{},String(docGroup.enviadosCount))),
    el('div',{class:'v5-counter-item highlight-counter'},el('small',{},'Citados en respuesta'),el('strong',{},String(docGroup.citadosCount)))
  );

  // Acciones
  const actions=el('div',{class:'v5-grouped-actions'});
  const modalBtn=button('Ver evidencia completa',()=>openEvidenceModal(docGroup,'cited'),{
    icon:'search',
    class:'button small'
  });
  actions.append(modalBtn);

  if(docGroup.url&&safeUrl(docGroup.url)){
    actions.append(link('Abrir fuente original ↗',docGroup.url,'button small text-button'));
  }else if(docGroup.document_id&&item(docGroup.document_id)){
    actions.append(button('Abrir documento',()=>previewDocument(item(docGroup.document_id)),{class:'button small text-button'}));
  }

  // Botón Reportar Error en providencia
  actions.append(button('Reportar error',()=>openErrorReportModal({
    target_type:'jurisprudencia_tarjeta',
    document_id:docGroup.document_id||null,
    sentencia:docGroup.title||null
  }),{icon:'flag',class:'button small text-button report-error-btn',title:'Reportar inconsistencia o error en esta providencia'}));

  // Acordeón para Jurisprudencia
  if(options.allowAccordion&&docGroup.fragments.length){
    let accordionOpen=false;
    const accordionContent=el('div',{class:'v5-accordion-content',hidden:true});
    const accordionBtn=button(`▼ Mostrar fragmentos (${docGroup.fragments.length})`,()=>{
      accordionOpen=!accordionOpen;
      accordionBtn.textContent=accordionOpen?`▲ Ocultar fragmentos (${docGroup.fragments.length})`:`▼ Mostrar fragmentos (${docGroup.fragments.length})`;
      accordionContent.hidden=!accordionOpen;
      if(accordionOpen&&!accordionContent.children.length){
        accordionContent.append(el('div',{class:'v5-fragments-list'},docGroup.fragments.map(f=>renderFragmentItem(f,docGroup))));
      }
    },{class:'button small text-button'});
    actions.append(accordionBtn);
    card.append(header,countersBar,actions,accordionContent);
  }else{
    card.append(header,countersBar,actions);
  }

  return card;
}

function openEvidenceModal(docGroup, initialTab='cited', targetRef=null){
  let activeTab=initialTab;
  if(activeTab==='cited'&&(!docGroup.citedFragments||!docGroup.citedFragments.length)){
    activeTab='sent';
  }

  const modalContainer=el('div',{class:'v5-evidence-modal-body'});
  const tabsBar=el('div',{class:'v5-modal-tabs'});
  const contentPane=el('div',{class:'v5-modal-content-pane'});

  const tabs=[
    {id:'cited',label:`Citados en respuesta (${docGroup.citadosCount||0})`},
    {id:'sent',label:`Enviados al modelo (${docGroup.enviadosCount||0})`},
    {id:'found',label:`Encontrados (${docGroup.encontradosCount||0})`},
    {id:'all',label:`Todos los fragmentos (bajo demanda)`},
  ];

  const onDemandState={
    fragments:[],
    offset:0,
    limit:25,
    total:null,
    hasMore:false,
    loading:false,
    query:''
  };

  async function loadOnDemandFragments(reset=false){
    if(onDemandState.loading)return;
    if(reset){
      onDemandState.offset=0;
      onDemandState.fragments=[];
      onDemandState.total=null;
      onDemandState.hasMore=false;
    }
    onDemandState.loading=true;
    renderTabPane();
    try{
      const qParams=new URLSearchParams();
      if(docGroup.url)qParams.set('source_url',docGroup.url);
      if(docGroup.document_id)qParams.set('doc_id',docGroup.document_id);
      qParams.set('kind',docGroup.kind||'official');
      qParams.set('offset',String(onDemandState.offset));
      qParams.set('limit',String(onDemandState.limit));
      if(onDemandState.query)qParams.set('q',onDemandState.query);

      const res=await v5api('/official/document/fragments?'+qParams.toString());
      onDemandState.total=res.total;
      onDemandState.hasMore=res.has_more;
      onDemandState.fragments.push(...(res.fragments||[]));
      onDemandState.offset+=(res.fragments||[]).length;
    }catch(err){
      toast('Error al consultar fragmentos: '+err.message,'error');
    }finally{
      onDemandState.loading=false;
      renderTabPane();
    }
  }

  function renderTabPane(){
    tabsBar.querySelectorAll('.v5-modal-tab-btn').forEach(btn=>{
      btn.classList.toggle('active',btn.dataset.tab===activeTab);
    });

    contentPane.replaceChildren();

    if(activeTab==='cited'){
      const list=docGroup.citedFragments||[];
      if(!list.length){
        contentPane.append(el('p',{class:'inline-help'},'Esta respuesta no citó fragmentos específicos de este documento con identificador formal explícito. Consulta la pestaña "Enviados al modelo" para ver el contexto completo aportado.'));
      }else{
        const wrap=el('div',{class:'v5-fragments-list'});
        wrap.append(...list.map(f=>renderFragmentItem(f,docGroup)));
        contentPane.append(wrap);
      }
    }else if(activeTab==='sent'){
      const list=docGroup.fragments||[];
      const wrap=el('div',{class:'v5-fragments-list'});
      wrap.append(...list.map(f=>renderFragmentItem(f,docGroup)));
      contentPane.append(wrap);
    }else if(activeTab==='found'){
      const list=docGroup.fragments||[];
      const wrap=el('div',{class:'v5-fragments-list'});
      wrap.append(el('p',{class:'inline-help'},`Mostrando ${list.length} fragmentos recuperados para esta providencia.`));
      wrap.append(...list.map(f=>renderFragmentItem(f,docGroup)));
      contentPane.append(wrap);
    }else if(activeTab==='all'){
      const searchBox=el('div',{class:'v5-modal-search'});
      const searchInput=el('input',{
        type:'search',
        placeholder:'Buscar texto dentro de la totalidad de fragmentos de esta providencia…',
        value:onDemandState.query
      });
      let debounceTimer=null;
      searchInput.addEventListener('input',()=>{
        clearTimeout(debounceTimer);
        debounceTimer=setTimeout(()=>{
          onDemandState.query=searchInput.value.trim();
          loadOnDemandFragments(true);
        },400);
      });
      searchBox.append(searchInput);

      const statusInfo=el('div',{class:'v5-grouped-meta',style:'margin-bottom:10px;'},
        onDemandState.total!==null?`Total indexado en BD: ${onDemandState.total} fragmentos (${onDemandState.fragments.length} cargados)`:'Consultando base de datos…'
      );

      const wrap=el('div',{class:'v5-fragments-list'});
      if(onDemandState.fragments.length){
        wrap.append(...onDemandState.fragments.map((f,i)=>{
          const fragAdapted={
            id:`SEG-${f.segment||(i+1)}`,
            segment:f.segment,
            section:f.section,
            excerpt:f.content,
            title:docGroup.title,
            source_url:docGroup.url,
            url:docGroup.url
          };
          return renderFragmentItem(fragAdapted,docGroup);
        }));
      }

      if(onDemandState.loading){
        wrap.append(el('div',{class:'busy-indicator'},'Cargando fragmentos…'));
      }else if(onDemandState.hasMore){
        const moreBtn=button('Cargar más fragmentos',()=>loadOnDemandFragments(false),{class:'button small'});
        wrap.append(el('div',{style:'text-align:center;margin:12px 0;'},moreBtn));
      }else if(!onDemandState.fragments.length&&!onDemandState.loading&&onDemandState.total===0){
        wrap.append(el('p',{class:'inline-help'},'No se encontraron fragmentos para el término de búsqueda ingresado.'));
      }

      contentPane.append(searchBox,statusInfo,wrap);
      if(onDemandState.total===null&&!onDemandState.loading){
        loadOnDemandFragments(true);
      }
    }
  }

  for(const t of tabs){
    const btn=el('button',{
      type:'button',
      class:'v5-modal-tab-btn '+(t.id===activeTab?'active':''),
      'data-tab':t.id
    },t.label);
    btn.addEventListener('click',()=>{
      activeTab=t.id;
      renderTabPane();
    });
    tabsBar.append(btn);
  }

  modalContainer.append(tabsBar,contentPane);
  renderTabPane();

  const footerBtns=[];
  if(docGroup.url&&safeUrl(docGroup.url)){
    footerBtns.push(link('Abrir documento oficial ↗',docGroup.url,'button small'));
  }
  footerBtns.push(button('Cerrar',closeModal,{class:'button'}));

  showModal(`📋 Evidencia Jurídica · ${docGroup.title}`,modalContainer,footerBtns,true);

  if(targetRef){
    setTimeout(()=>{
      const target=document.querySelector('#frag-'+targetRef);
      if(target){
        target.scrollIntoView({behavior:'smooth',block:'center'});
        target.classList.add('v5-fragment-highlight');
        setTimeout(()=>target.classList.remove('v5-fragment-highlight'),2500);
      }
    },220);
  }
}

function toggleFragmentSelection(frag,docGroup,isSelected){
  const key=frag.id||(frag.document_id?`${frag.document_id}-${frag.segment}`:`seg-${frag.segment||Math.random()}`);
  if(isSelected){
    S.selectedFragmentsState.set(key,{
      id:key,
      title:docGroup?.title||frag.title||'Providencia judicial',
      source_url:docGroup?.url||frag.source_url||frag.url||'',
      source_id:docGroup?.source_id||frag.source_id||'',
      section:frag.section||'fundamentos_juridicos',
      segment:frag.segment||1,
      page:frag.page,
      excerpt:frag.excerpt||frag.text||frag.content||'',
      text:frag.excerpt||frag.text||frag.content||'',
      document_id:frag.document_id,
      user_selected:true
    });
  }else{
    S.selectedFragmentsState.delete(key);
  }
  document.querySelectorAll(`.v5-fragment-item[id="frag-${key}"]`).forEach(card=>{
    card.classList.toggle('selected',isSelected);
    const cb=card.querySelector('input[type="checkbox"]');
    if(cb)cb.checked=isSelected;
  });
  renderFloatingSelectionBar();
}

function renderFloatingSelectionBar(){
  let bar=document.querySelector('#v5-floating-selection-bar');
  const count=S.selectedFragmentsState.size;

  if(count===0){
    if(bar)bar.remove();
    return;
  }

  const uniqueDocs=new Set(Array.from(S.selectedFragmentsState.values()).map(f=>f.title||f.source_url)).size;

  if(!bar){
    bar=el('div',{class:'v5-selection-bar',id:'v5-floating-selection-bar'});
    document.body.append(bar);
  }

  const summary=el('div',{class:'v5-selection-summary'},
    el('span',{},'📌'),
    el('strong',{},`${count} fragmento${count>1?'s':''} seleccionado${count>1?'s':''}`),
    el('small',{style:'opacity:0.8;'},`de ${uniqueDocs} providencia${uniqueDocs>1?'s':''}`)
  );

  const clearBtn=button('Desmarcar todos',()=>{
    S.selectedFragmentsState.clear();
    document.querySelectorAll('.v5-fragment-item.selected').forEach(c=>{
      c.classList.remove('selected');
      const cb=c.querySelector('input[type="checkbox"]');
      if(cb)cb.checked=false;
    });
    renderFloatingSelectionBar();
  },{class:'v5-bar-btn text-only'});

  const sendToAgentBtn=button('Enviar al Agente',()=>{
    closeModal();
    S.customSelectedFragments=Array.from(S.selectedFragmentsState.values());
    if(S.page!=='chat')setPage('chat');
    render();
    const input=$('#chat-input');
    if(input){
      if(!input.value.trim()){
        input.value='Analiza los fragmentos jurídicos seleccionados y evalúa su aplicación al caso:\n';
        S.chatDraft=input.value;
      }
      input.focus();
    }
    toast(`✓ ${count} fragmentos incorporados al contexto del Agente`);
  },{class:'v5-bar-btn secondary'});

  const draftBtn=button('Utilizar en un escrito',()=>{
    closeModal();
    S.customSelectedFragments=Array.from(S.selectedFragmentsState.values());
    S.mode='draft';
    if(S.page!=='chat')setPage('chat');
    render();
    const input=$('#chat-input');
    if(input){
      const summaryText=S.customSelectedFragments.map((f,i)=>
        `[Fuente ${i+1}: ${f.title} · ${formatSectionName(f.section)}]\n"${(f.excerpt||'').slice(0,350)}..."`
      ).join('\n\n');
      input.value=`Redacta un escrito jurídico profesional (ej. alegato o memorial) fundamentado rigurosamente en los siguientes fragmentos jurisprudenciales seleccionados:\n\n${summaryText}\n\nEstructura el escrito con hechos, fundamentos de derecho y peticiones concretas.`;
      S.chatDraft=input.value;
      input.focus();
    }
    toast('✓ Modo redacción jurídica activado con los fundamentos seleccionados');
  },{class:'v5-bar-btn primary'});

  const actions=el('div',{class:'v5-selection-actions'},clearBtn,sendToAgentBtn,draftBtn);
  bar.replaceChildren(summary,actions);
}

function sourceCard(source){const label=source.title||source.id||'Fuente';const location=source.page?'Página '+source.page:source.location||(source.segment?'Segmento '+source.segment:'');const node=el('div',{class:'source-card'},el('strong',{},label),el('span',{class:'source-meta'},[source.id,location,source.kind==='web'?'Fuente de búsqueda':source.kind==='official'?'Corpus Jurídico Oficial':'Documento aportado'].filter(Boolean).join(' · ')));if(source.excerpt)node.append(el('p',{},source.excerpt));if(source.url&&safeUrl(source.url))node.append(link('Abrir fuente original ↗',source.url));else if(source.document_id&&item(source.document_id))node.append(button('Abrir documento',()=>previewDocument(item(source.document_id)),{class:''}));node.append(el('div',{class:'source-meta'},source.verified?'Fragmento contrastado con el documento; revisa su aplicación.':source.provenance||'Revisa el contenido y su aplicación jurídica.'));return node;}
function renderMessage(m,index){if(m.role==='user')return el('article',{class:'message user','aria-label':'Tu encargo'},plainRich(m.content,m));const n=el('article',{class:'message assistant','aria-label':'Respuesta de El Memorialista'},el('div',{class:'message-header'},el('span',{class:'avatar'},'M'),el('span',{},'El Memorialista')),plainRich(m.content,m));
  if(m.streaming){
    const content=n.querySelector('.message-content');
    content.classList.add('streaming-text');
    content.textContent=m.content||'';
    n.append(el('div',{class:'streaming-status',role:'status'},m.streamStatus||'Preparando respuesta…'));
    return n;
  }
  if(m.incomplete){
    n.append(el('div',{class:'message-note'},'Respuesta incompleta. No se ha guardado ni se puede exportar como documento final.'));
    return n;
  }
  if(Array.isArray(m.sources)&&m.sources.length){
    const groupedDocs=groupSourcesByDocument(m.sources,m.content,m.coverage);
    n.append(el('div',{class:'sources-list'},groupedDocs.map(g=>renderGroupedDocumentCard(g,m,{allowAccordion:false}))));
  }
  if(m.search_suggestions_html){const frame=el('iframe',{class:'search-attribution',title:'Sugerencias de búsqueda de Google',sandbox:'allow-popups allow-popups-to-escape-sandbox',referrerPolicy:'no-referrer'});frame.srcdoc='<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src https: data:; base-uri \'none\'; form-action \'none\'">'+m.search_suggestions_html;n.append(frame);}if(Array.isArray(m.warnings))for(const w of m.warnings)n.append(el('div',{class:'message-note'},typeof w==='string'?w:text(w)));if(m.coverage){const c=m.coverage;const covText=c.scope==='official'?('Corpus Jurídico Oficial: '+(c.official_documents||0)+' documento(s) consultado(s) · '+(c.selected_passages??'—')+' fragmento(s) utilizados de '+(c.available_passages??'—')+' disponibles'+(c.truncated?' · Selección parcial del contenido.':'.')):('Contexto utilizado: '+(c.selected_passages??'—')+' fragmentos de '+(c.available_passages??'—')+' disponibles'+(c.truncated?' · Selección parcial del contenido.':'.'));n.append(el('div',{class:'coverage'},covText));if(c.depth||c.candidates_retrieved!==undefined||m.cost_metrics){const depthLabel=c.depth_name||({quick:'Rápido',balanced:'Equilibrado',deep:'Profundo',auto:'Automático'}[c.depth]||c.depth||'Automático');const items=[];if(c.depth)items.push(el('li',{},'Profundidad: '+depthLabel));if(c.detected_intent)items.push(el('li',{},'Tipo de consulta detectada: '+c.detected_intent));if(c.candidates_retrieved!==undefined)items.push(el('li',{},'Candidatos evaluados: '+c.candidates_retrieved+' · Seleccionados: '+(c.selected_passages||0)));if(c.chars_sent!==undefined)items.push(el('li',{},'Contexto documental: '+c.chars_sent+' caracteres (~'+Math.round(c.chars_sent/4)+' tokens)'));if(c.sections_represented&&c.sections_represented.length)items.push(el('li',{},'Secciones jurídicas analizadas: '+c.sections_represented.join(', ')));if(m.model)items.push(el('li',{},'Modelo de IA: '+m.model+(m.provider?' ('+m.provider+')':'')));if(m.usage?.input_tokens)items.push(el('li',{},'Tokens consumidos: '+m.usage.input_tokens+' entrada / '+(m.usage.output_tokens||0)+' salida'));if(m.cost_metrics?.estimated_cost_usd!==undefined)items.push(el('li',{},'Coste estimado: $'+m.cost_metrics.estimated_cost_usd+' USD (estimación comercial)'));if(c.retrieval_time_seconds)items.push(el('li',{},'Tiempo de recuperación: '+c.retrieval_time_seconds+'s · Reranking: '+(c.rerank_time_seconds||0)+'s'));if(c.memory_hit)items.push(el('li',{},'Memoria documental: Contexto reutilizado de la sesión previa'));n.append(el('details',{class:'v5-rag-details'},el('summary',{},'Detalles del análisis · '+depthLabel+' ('+(c.selected_passages||0)+' fragmentos seleccionados)'),el('ul',{},items)));}}if(m.coverage?.indexed_retrieval)n.append(v5RetrievalCoverage(m.coverage.indexed_retrieval));if(Array.isArray(m.plan)&&m.plan.length)n.append(el('details',{class:'work-plan'},el('summary',{},'Trabajo realizado'),el('ul',{},m.plan.map(step=>el('li',{},typeof step==='string'?step:(step.label||'Paso')+' · '+({completed:'Completado',pending:'Pendiente de revisión',unverified:'Sin confirmar'}[step.status]||step.status||''))))));if(m.quality_audit){
  const qa=m.quality_audit;
  const isOk=qa.technical_verification==='verificado_tecnicamente';
  n.append(el('div',{class:'v5-quality-badge '+(isOk?'ok':'warn')},
    el('span',{},isOk?'✓ ':'⚠ '),
    el('span',{},qa.badge_label||(isOk?'Verificación técnica aprobada':'Advertencias en citas o cobertura')),
    button('Reportar error',()=>openErrorReportModal({target_type:'agente_respuesta',query_summary:m.content?.slice(0,120)}),{class:'button small text-button report-error-btn'})
  ));
}
n.append(el('div',{class:'message-tools'},button('Copiar',()=>copy(m.content),{icon:'copy',class:''}),button('Guardar escrito',()=>saveAnswerDocument(m),{icon:'file',class:''}),button('Word',()=>exportDocument(m.content,conversationTitle(),'docx'),{icon:'download',class:''}),button('PDF',()=>exportDocument(m.content,conversationTitle(),'pdf'),{icon:'download',class:''}),button('Reportar error',()=>openErrorReportModal({target_type:'agente_respuesta',query_summary:m.content?.slice(0,120)}),{icon:'flag',class:'report-error-btn',title:'Reportar error o inconsistencia'})));return n;}
function conversationTitle(){return item(S.conversationId)?.title||'Respuesta de El Memorialista';}
function renderChat(){const research=S.page==='investigacion';const outer=el('section',{class:'chat-layout'});const matterSelect=el('select',{class:'context-select','aria-label':'Asunto del encargo',disabled:!!S.chatTask});for(const o of matterOptions())matterSelect.append(el('option',{value:o.value,selected:S.matterId===o.value},o.label));matterSelect.addEventListener('change',()=>{S.matterId=matterSelect.value;S.selectedDocs.clear();if(S.conversationId){S.conversationId=null;S.messages=[];}render();});const knowledge=el('select',{class:'context-select v5-knowledge-select','aria-label':'Biblioteca para el agente',disabled:!!S.chatTask});for(const[value,label]of[['auto','Biblioteca: automática'],['official','Corpus Jurídico Oficial'],['off','Biblioteca: sin recuperación'],['documents','Biblioteca: documentos DMS'],['legal','Biblioteca: fuentes jurídicas'],['all','Biblioteca: documentos y fuentes']])knowledge.append(el('option',{value,selected:S.knowledgeScope===value},label));knowledge.addEventListener('change',()=>S.knowledgeScope=knowledge.value);knowledge.title='Automática: fuentes jurídicas al investigar; documentos DMS en otros encargos. Corpus Oficial: providencias y normas publicadas del corpus compartido.';const context=el('div',{class:'context-actions'},knowledge,matterSelect);if(S.conversationId)context.append(button('⋯',showConversationMenu,{class:'icon-button',title:'Opciones de conversación'}));outer.append(el('div',{class:'chat-context'},el('span',{class:'workspace-label'},icon('lock'),research?'INVESTIGACIÓN JURÍDICA':'TU ESPACIO DE TRABAJO'),context));if(!S.messages.length){outer.append(el('div',{class:'chat-welcome'},el('div',{class:'welcome-emblem'},icon(research?'book':'spark')),el('div',{class:'eyebrow'},research?'FUENTES, CONTEXTO Y CRITERIO':'EL MEMORIALISTA · AGENTE JURÍDICO'),el('h1',{},research?'Investiga con fuentes.': 'Cada asunto, ',research?el('em',{},' Decide con criterio.'):el('em',{},'con claridad.')),el('p',{},research?'Plantea el problema jurídico y revisa las fuentes que respaldan el análisis.':'Un espacio para investigar, analizar tus documentos y preparar el siguiente escrito. Tú diriges el trabajo.')));}else outer.append(el('div',{class:'chat-messages',id:'chat-messages'},S.messages.map(renderMessage)));if(S.chatTask)outer.append(el('div',{class:'thinking',role:'status'},el('span',{class:'dots'},el('i'),el('i'),el('i')),'Procesando el encargo y sus documentos…'));if(S.chatUnsaved)outer.append(el('div',{class:'callout warning'},'La respuesta está en esta pantalla y aún no se ha guardado. ',button('Reintentar guardado',persistConversation,{class:'text-button'})));const form=el('form',{class:'composer',id:'chat-form'});
if(Array.isArray(S.customSelectedFragments)&&S.customSelectedFragments.length){
  form.append(el('div',{class:'v5-composer-context-chip'},
    el('span',{},`📌 ${S.customSelectedFragments.length} fragmento(s) seleccionado(s) incorporado(s) al contexto`),
    button('×',()=>{
      S.customSelectedFragments=[];
      render();
    },{class:'chip-close',title:'Quitar fragmentos seleccionados'})
  ));
}
const input=el('textarea',{id:'chat-input',value:S.chatDraft,placeholder:research?'¿Qué problema jurídico necesitas investigar? Incluye jurisdicción, fechas y contexto…':'Describe tu encargo o adjunta un documento para empezar…','aria-label':'Describe tu encargo',maxLength:12000,disabled:!!S.chatTask});input.addEventListener('input',()=>S.chatDraft=input.value);input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();if(!S.chatTask)form.requestSubmit();}});form.append(input);if(S.selectedDocs.size)form.append(el('div',{class:'attachment-chips'},[...S.selectedDocs].filter(id=>item(id)).map(id=>el('span',{class:'attachment-chip'},icon('file'),el('span',{},item(id).title),button('×',()=>{S.selectedDocs.delete(id);render();},{class:'',title:'Quitar '+item(id).title})))));const mode=el('select',{class:'mode-select','aria-label':'Tipo de encargo',disabled:!!S.chatTask});for(const[value,label]of[['general','General'],['analyze','Analizar'],['draft','Redactar'],['timeline','Cronología'],['research','Investigar']])mode.append(el('option',{value,selected:S.mode===value},label));mode.addEventListener('change',()=>{S.mode=mode.value;});const depthSelect=el('select',{class:'depth-select','aria-label':'Profundidad del análisis',disabled:!!S.chatTask});for(const[val,lab]of[['auto','Profundidad: Automática'],['quick','Profundidad: Rápida'],['balanced','Profundidad: Equilibrada'],['deep','Profundidad: Profunda']])depthSelect.append(el('option',{value:val,selected:(S.analysisDepth||'auto')===val},lab));depthSelect.addEventListener('change',()=>{S.analysisDepth=depthSelect.value;});const send=S.chatTask?button('Detener',cancelChat,{icon:'close',class:'send-button cancel'}):el('button',{type:'submit',class:'send-button'},'Enviar encargo',icon('up'));form.append(el('div',{class:'composer-toolbar'},el('div',{class:'composer-tools'},button('Adjuntar',chooseChatDocuments,{icon:'attach',class:'tool-button',disabled:!!S.chatTask}),button('Instrucciones',choosePlaybook,{icon:'book',class:'tool-button',disabled:!!S.chatTask}),mode,depthSelect),send));form.addEventListener('submit',act(async e=>{e.preventDefault();await sendChat();}));outer.append(form,el('div',{class:'composer-note'},icon('lock'),el('span',{},'Espacio privado. Verifica los hechos, las fuentes y el escrito antes de utilizarlo.')));if(!S.messages.length){const cards=research?[['book','Comparar criterios','Contrasta decisiones y abre sus fuentes.','Investiga los criterios jurídicos aplicables a este problema en Colombia. Explica los puntos de acuerdo y las diferencias, y cita únicamente fuentes recuperadas: '],['search','Comprobar una referencia','Revisa el contenido y el contexto de una cita.','Ayúdame a investigar esta referencia. Identifica el documento original y distingue lo confirmado de lo pendiente de verificar: '],['clock','Investigar cambios','Delimita el periodo y el problema jurídico.','Investiga novedades jurídicas sobre el siguiente tema en Colombia. Indica fecha, fuente y alcance de cada hallazgo: ']]:[['file','Analizar un expediente','Hechos, pruebas y puntos por revisar.','Analiza los documentos adjuntos. Organiza los hechos, identifica las pruebas que los respaldan y señala vacíos o contradicciones. '],['book','Investigar jurisprudencia','Fuentes para fundamentar tu argumento.','Investiga jurisprudencia colombiana sobre el siguiente problema. Cita las fuentes recuperadas y explica su pertinencia: '],['sign','Preparar un escrito','Del contexto a un borrador para revisar.','Prepara un borrador jurídico a partir de este contexto. Conserva los hechos aportados y marca los datos que faltan: ']];outer.append(el('div',{class:'prompt-grid'},cards.map(([ic,title,desc,prompt])=>button('',()=>{S.chatDraft=prompt;S.mode=ic==='book'?'research':ic==='sign'?'draft':'analyze';render();$('#chat-input')?.focus();},{class:'prompt-card'}))));outer.querySelectorAll('.prompt-card').forEach((card,i)=>card.append(icon(cards[i][0]),el('strong',{},cards[i][1]),el('small',{},cards[i][2])));outer.append(el('div',{class:'section-heading'},el('h2',{},'Tus asuntos recientes'),button('Ver asuntos →',()=>setPage('asuntos'),{class:'text-button'})));const matters=byKind('matter').slice(0,2);outer.append(matters.length?el('div',{class:'recent-matters'},matters.map(matterMini)):el('div',{class:'welcome-empty'},el('span',{},'Dale un lugar a los documentos y el contexto de cada cliente.'),button('Crear asunto +',()=>matterForm(),{class:'text-button'})));}return outer;}
function matterMini(m){const b=button('',()=>matterDetail(m),{class:'matter-mini'});b.append(icon('folder'),el('span',{},el('strong',{},m.title),el('small',{},m.data?.client||'Asunto privado')),badge(m.data?.status==='closed'?'Cerrado':'En curso',m.data?.status==='closed'?'neutral':''));return b;}
async function persistConversation(){if(!S.conversationId)return;const c=item(S.conversationId);try{const saved=await updateItem({...c,version:S.conversationVersion||c.version},{data:{...c.data,messages:S.messages.filter(m=>!m.streaming&&!m.incomplete),mode:S.mode,knowledge_scope:S.knowledgeScope,depth:S.analysisDepth||'auto',document_ids:[...S.selectedDocs]},matter_id:S.matterId||null});S.conversationVersion=saved.version;S.chatUnsaved=false;render();return saved;}catch(error){S.chatUnsaved=true;throw error;}}
async function sendChat(){
  if(S.chatTask)return;
  const message=($('#chat-input')?.value||S.chatDraft).trim();
  if(!message)return;
  let totalHistory=0;
  const previous=[];
  for(const m of S.messages.filter(m=>!m.incomplete&&!m.streaming).slice().reverse()){
    if(previous.length>=24||totalHistory+String(m.content||'').length>230000)break;
    previous.unshift({role:m.role,content:m.content});
    totalHistory+=String(m.content||'').length;
  }
  const historyLimited=previous.length<S.messages.filter(m=>!m.incomplete&&!m.streaming).length;
  const request={message,history:previous,mode:S.mode,knowledge_scope:S.knowledgeScope,depth:S.analysisDepth||'auto',
    document_ids:[...S.selectedDocs],matter_id:S.matterId||null,playbook_id:S.playbookId||null};
  if(Array.isArray(S.customSelectedFragments)&&S.customSelectedFragments.length){
    request.selected_fragments=S.customSelectedFragments.map(f=>({
      id:f.id,
      document_id:f.document_id,
      segment:f.segment,
      ordinal:f.ordinal,
      section:f.section,
      kind:f.kind||(f.source_url?'official':'document'),
      source_url:f.source_url||'',
      title:f.title||''
    }));
  }
  S.messages.push({role:'user',content:message,created_at:new Date().toISOString()});
  S.chatDraft='';
  const controller=new AbortController();
  const runId=++S.chatCounter;
  S.chatTask={id:runId,controller,stage:'Preparando consulta…',draft:null};
  render();
  let draft=null;
  let completed=false;
  try{
    if(!S.conversationId){
      const c=await createItem('conversation',message.slice(0,85),{
        messages:S.messages.filter(m=>!m.incomplete&&!m.streaming),mode:request.mode,
        knowledge_scope:request.knowledge_scope,document_ids:request.document_ids},request.matter_id);
      if(S.chatTask?.id!==runId)return;
      S.conversationId=c.id;S.conversationVersion=c.version;
    }else await persistConversation();
    if(S.chatTask?.id!==runId)return;
    draft={role:'assistant',content:'',streaming:true,streamStatus:'Preparando respuesta…',created_at:new Date().toISOString()};
    S.chatTask.draft=draft;
    S.messages.push(draft);
    render();
    await streamChatRequest(request,controller.signal,async(event,data)=>{
      if(S.chatTask?.id!==runId)return;
      if(event==='status'){
        draft.streamStatus=data?.message||'Procesando consulta…';
        const status=$('#chat-messages .message.assistant:last-child .streaming-status');
        if(status)status.textContent=draft.streamStatus;
      }
      if(event==='delta'&&typeof data?.text==='string'){
        draft.content+=data.text;
        const textNode=$('#chat-messages .message.assistant:last-child .streaming-text');
        const box=$('#chat-messages');
        const follow=box&&box.scrollHeight-box.scrollTop-box.clientHeight<180;
        if(textNode)textNode.append(document.createTextNode(data.text));
        if(follow&&box)box.scrollTop=box.scrollHeight;
        const thinking=$('.thinking');if(thinking)thinking.hidden=true;
      }
      if(event==='done'){
        if(!data?.answer||data.answer!==draft.content)throw new Error('El resultado final no coincide con los fragmentos recibidos. No se guardó la respuesta.');
        Object.assign(draft,{content:data.answer,sources:data.sources||[],
          warnings:[...(data.warnings||[]),...(historyLimited?['Se utilizó el historial reciente disponible para esta consulta.']:[])],
          coverage:data.coverage,plan:data.plan,search_suggestions_html:data.search_suggestions_html,
          provider:data.provider,model:data.model,streaming:false,streamStatus:undefined});
        completed=true;
      }
    });
    if(S.chatTask?.id!==runId||!completed)throw new Error('La respuesta no terminó correctamente.');
    S.chatUnsaved=true;
    try{await persistConversation();}catch(error){toast('La respuesta se recibió, pero no se pudo guardar: '+error.message,'error');}
  }catch(error){
    if(error.name!=='AbortError'&&S.chatTask?.id===runId){
      if(draft){
        if(draft.content){draft.streaming=false;draft.incomplete=true;draft.warnings=['Respuesta incompleta: no se guardó como final.'];}
        else S.messages=S.messages.filter(m=>m!==draft);
      }
      if(!S.conversationId){S.messages.pop();S.chatDraft=message;}
      toast(error.message,'error');
    }
  }finally{
    if(S.chatTask?.id===runId){S.chatTask=null;render();$('#chat-input')?.focus();}
  }
}
function chooseChatDocuments(){const docs=byKind('document').filter(d=>!S.matterId||d.matter_id===S.matterId);const selected=new Set(S.selectedDocs);const list=el('div',{class:'checklist'});if(!docs.length)list.append(el('p',{class:'inline-help'},'Carga un documento para aportar contexto a este encargo.'));for(const d of docs){const check=el('input',{type:'checkbox',checked:selected.has(d.id)});check.addEventListener('change',()=>check.checked?selected.add(d.id):selected.delete(d.id));list.append(el('label',{class:'check-row'},check,el('span',{},d.title,el('small',{},matterTitle(d.matter_id)))));}showModal('Documentos para este encargo',el('div',{},el('p',{class:'inline-help'},'Selecciona documentos de tu biblioteca. El análisis indicará qué fragmentos utilizó.'),list),[button('Cargar archivos',()=>{S.uploadUse='chat';$('#upload-input').click();},{icon:'upload'}),button('Usar selección',()=>{if(selected.size>20)throw new Error('Selecciona como máximo 20 documentos para un encargo.');S.selectedDocs=selected;closeModal();render();},{class:'button primary'})]);}
function choosePlaybook(){const saved=byKind('playbook');const select=field('Instrucciones para este encargo',{value:S.playbookId,options:[{value:'',label:'Sin instrucciones adicionales'},...saved.map(p=>({value:p.id,label:p.title}))]});const preview=el('div',{class:'document-preview'});const update=()=>preview.textContent=item(select.input.value)?.data?.instructions||'Utiliza las instrucciones generales del agente.';select.input.addEventListener('change',update);update();showModal('Instrucciones reutilizables',el('div',{},select.wrap,preview),[button('Crear instrucciones',()=>playbookForm()),button('Aplicar',()=>{S.playbookId=select.input.value;closeModal();toast('Instrucciones seleccionadas.');},{class:'button primary'})]);}
function showConversationMenu(){const c=item(S.conversationId);if(!c)return;showModal('Opciones del encargo',el('div',{class:'stack'},button('Cambiar nombre',()=>renameItem(c),{icon:'edit'}),button('Descargar conversación',()=>downloadBlob(new Blob([S.messages.map(m=>(m.role==='user'?'TÚ':'EL MEMORIALISTA')+'\n'+m.content).join('\n\n---\n\n')],{type:'text/plain;charset=utf-8'}),filename(c.title,'txt')),{icon:'download'}),button('Eliminar conversación',()=>confirmDialog('Eliminar conversación','Se eliminará este historial de tu cuenta. Sus documentos permanecerán en la biblioteca.',()=>removeItem(c)),{icon:'trash',class:'button danger'})),[button('Cerrar',closeModal)]);}
function allConversations(){const box=el('div',{class:'search-results'});const conversations=byKind('conversation');if(!conversations.length)box.append(el('p',{class:'inline-help'},'Aún no tienes conversaciones guardadas.'));for(const c of conversations)box.append(button('',()=>{closeModal();openConversation(c.id);},{class:'result-button'}));box.querySelectorAll('button').forEach((b,i)=>b.append(el('strong',{},conversations[i].title),el('small',{},shortDate(conversations[i].updated_at)+' · '+matterTitle(conversations[i].matter_id))));showModal('Tus conversaciones',box,[button('Nuevo encargo',async()=>{closeModal();await newChat();},{class:'button primary'})]);}
function renameItem(record){const name=field('Nombre',{value:record.title,required:true});formModal('Cambiar nombre',[name],async()=>{await updateItem(record,{title:name.input.value.trim()});render();});}
async function exportDocument(content,title,format){if(!String(content).trim())throw new Error('El documento está vacío.');const data=await api('/export/document',{method:'POST',body:{title:title||'Escrito',text:content,format},blob:true});downloadBlob(data,filename(title,format));}
function saveAnswerDocument(message){const title=field('Título del escrito',{value:conversationTitle(),required:true});const matter=field('Asunto',{value:S.matterId,options:matterOptions()});formModal('Guardar respuesta como escrito',[title,matter],async()=>{const d=await createItem('document',title.input.value.trim(),{text:message.content,pages:[],versions:[],mime:'text/plain',source:'agent',sources:message.sources||[]},matter.input.value);toast('Escrito guardado en DMS.');openEditor(d);});}
function match(query,...values){const norm=v=>String(v||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase();return norm(values.join(' ')).includes(norm(query));}
function listToolbar({placeholder='Buscar…',onChange,withMatter=false}={}){const input=el('input',{type:'search',placeholder,'aria-label':placeholder,value:S.search});const bar=el('div',{class:'toolbar'},el('div',{class:'search-input'},input));input.addEventListener('input',()=>{S.search=input.value;onChange();});if(withMatter){const select=el('select',{class:'filter-select','aria-label':'Filtrar por asunto'});for(const o of matterOptions(true))select.append(el('option',{value:o.value,selected:S.filter===o.value},o.label));select.addEventListener('change',()=>{S.filter=select.value;onChange();});bar.append(select);}const count=el('span',{class:'count-label'});bar.append(count);return{bar,count};}
function renderMatters(){const page=el('section',{class:'page'});page.append(pageHeader('Asuntos','Un lugar para el contexto, los documentos y los acontecimientos de cada cliente.',[button('Nuevo asunto',()=>matterForm(),{icon:'plus',class:'button primary'})]));const grid=el('div',{class:'grid'});let count;const draw=()=>{const list=byKind('matter').filter(m=>match(S.search,m.title,m.data?.client,m.data?.reference));count.textContent=list.length+' asuntos';grid.className=list.length?'grid':'';grid.replaceChildren(...(list.length?list.map(m=>{const total=S.items.filter(i=>i.matter_id===m.id&&i.kind==='document').length;return el('article',{class:'card'},el('div',{class:'card-head'},icon('case'),badge(m.data?.status==='closed'?'Cerrado':'En curso',m.data?.status==='closed'?'neutral':'')),el('h3',{},m.title),el('p',{},m.data?.client||'Sin cliente indicado'),el('p',{},String(m.data?.description||'').slice(0,160)),el('div',{class:'card-meta'},total+' documentos',m.data?.reference||'Sin radicado'),el('div',{class:'card-actions'},button('Abrir asunto',()=>matterDetail(m),{class:'button small',icon:'folder'}),button('Editar',()=>matterForm(m),{class:'button small',icon:'edit'}),button('',()=>confirmDialog('Eliminar asunto','Sólo se podrá eliminar si no contiene documentos, conversaciones u otros elementos asociados. Trasládalos antes si necesitas conservarlos.',()=>removeItem(m)),{class:'button small',icon:'trash',title:'Eliminar '+m.title})));}):[empty('El contexto empieza aquí','Crea tu primer asunto y reúne los documentos y el trabajo jurídico de cada cliente.',button('Crear asunto',()=>matterForm(),{class:'button primary',icon:'plus'}),'case')]));};const tools=listToolbar({placeholder:'Buscar por asunto, cliente o radicado…',onChange:draw});count=tools.count;page.append(tools.bar,grid);draw();return page;}
function matterForm(record){const title=field('Nombre del asunto',{value:record?.title,required:true});const client=field('Cliente o parte principal',{value:record?.data?.client});const reference=field('Radicado o referencia',{value:record?.data?.reference,help:'Es una referencia del asunto; no activa una consulta judicial automática.'});const desc=field('Contexto y objetivo',{value:record?.data?.description,type:'textarea'});const status=field('Estado',{value:record?.data?.status||'active',options:[{value:'active',label:'En curso'},{value:'closed',label:'Cerrado'}]});formModal(record?'Editar asunto':'Nuevo asunto',[title,client,reference,desc,status],async()=>{const data={...record?.data,client:client.input.value.trim(),reference:reference.input.value.trim(),description:desc.input.value.trim(),status:status.input.value};if(record)await updateItem(item(record.id)||record,{title:title.input.value.trim(),data});else await createItem('matter',title.input.value.trim(),data,'');render();toast('Asunto guardado.');});}
function matterDetail(record){const m=item(record.id)||record;const docs=byKind('document').filter(d=>d.matter_id===m.id);const events=byKind('event').filter(e=>e.matter_id===m.id).sort((a,b)=>String(a.data?.date||'').localeCompare(String(b.data?.date||'')));const body=el('div',{},el('dl',{class:'detail-kv'},el('dt',{},'Cliente'),el('dd',{},m.data?.client||'No indicado'),el('dt',{},'Referencia'),el('dd',{},m.data?.reference||'No indicada'),el('dt',{},'Estado'),el('dd',{},m.data?.status==='closed'?'Cerrado':'En curso')),el('p',{class:'inline-help'},m.data?.description||'Añade contexto al editar el asunto.'),el('div',{class:'section-heading'},el('h2',{},'Documentos del asunto'),button('Cargar',()=>{S.matterId=m.id;S.uploadUse='library';$('#upload-input').click();},{class:'text-button',icon:'upload'})),el('div',{class:'item-list'},docs.length?docs.map(d=>el('div',{class:'list-row'},icon('file'),el('div',{class:'row-main'},el('strong',{},d.title),el('small',{},shortDate(d.updated_at))),button('Abrir',()=>previewDocument(d),{class:'button small'}))):el('p',{class:'inline-help'},'Todavía no hay documentos asociados.')),el('div',{class:'section-heading'},el('h2',{},'Acontecimientos y seguimiento'),button('Añadir',()=>eventForm(null,m.id),{class:'text-button',icon:'plus'})),el('p',{class:'inline-help'},'Registro introducido por ti. Comprueba las fechas y los términos aplicables al asunto.'),el('div',{class:'timeline'},events.length?events.map(e=>el('article',{class:'timeline-item'},el('time',{},e.data?.date+(e.data?.time?' · '+e.data.time:'')),el('h3',{},e.title),el('p',{},e.data?.description||''),el('div',{class:'actions'},badge(e.data?.status==='done'?'Completado':'Pendiente',e.data?.status==='done'?'':'pending'),button('Editar',()=>eventForm(e,m.id),{class:'text-button'}),button('Calendario',()=>eventCalendar(e),{class:'text-button'}),button('Eliminar',()=>confirmDialog('Eliminar acontecimiento','Se eliminará este registro del asunto.',async()=>{await removeItem(e);matterDetail(m);}),{class:'text-button'})))):el('p',{class:'inline-help'},'Sin acontecimientos registrados.')));showModal(m.title,body,[button('Editar asunto',()=>matterForm(m)),button('Trabajar con el agente',async()=>{closeModal();await newChat();S.matterId=m.id;S.selectedDocs=new Set(docs.slice(0,8).map(d=>d.id));render();},{class:'button primary',icon:'spark'})],true);}
function eventForm(record,matterId=S.matterId){const title=field('Acontecimiento',{value:record?.title,required:true,placeholder:'Ej. recepción de respuesta'});const date=field('Fecha',{value:record?.data?.date,type:'date',required:true});const time=field('Hora de Colombia (opcional)',{value:record?.data?.time,type:'time'});const desc=field('Descripción',{value:record?.data?.description,type:'textarea'});const status=field('Estado',{value:record?.data?.status||'pending',options:[{value:'pending',label:'Pendiente'},{value:'done',label:'Completado'}]});formModal(record?'Editar acontecimiento':'Añadir acontecimiento',[title,date,time,desc,status],async()=>{const data={...record?.data,date:date.input.value,time:time.input.value,description:desc.input.value.trim(),status:status.input.value};if(record)await updateItem(item(record.id)||record,{title:title.input.value.trim(),data});else await createItem('event',title.input.value.trim(),data,matterId);render();toast('Acontecimiento guardado.');});}
function eventCalendar(e){const esc=v=>String(v||'').replace(/\\/g,'\\\\').replace(/\r?\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,');const d=e.data||{};if(!/^\d{4}-\d{2}-\d{2}$/.test(d.date||''))throw new Error('El acontecimiento necesita una fecha válida.');let start='DTSTART;VALUE=DATE:'+d.date.replace(/-/g,'');if(d.time){const parsed=new Date(d.date+'T'+d.time+':00-05:00');if(Number.isNaN(parsed.valueOf()))throw new Error('Hora inválida.');start='DTSTART:'+parsed.toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');}const dtstamp=new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//El Memorialista//Despacho//ES','CALSCALE:GREGORIAN','BEGIN:VEVENT','UID:'+e.id+'@elmemorialista','DTSTAMP:'+dtstamp,start,'SUMMARY:'+esc(e.title),'DESCRIPTION:'+esc(d.description),'END:VEVENT','END:VCALENDAR'];downloadBlob(new Blob([lines.join('\r\n')+'\r\n'],{type:'text/calendar;charset=utf-8'}),filename(e.title,'ics'));}
function renderLibrary(){const page=el('section',{class:'page'});page.append(pageHeader('DMS · Biblioteca','Tus documentos, sus versiones y el contexto de cada asunto en un solo lugar.',[button('Nuevo escrito',()=>newEditor(),{icon:'file'}),button('Cargar documentos',()=>{S.uploadUse='library';$('#upload-input').click();},{icon:'upload',class:'button primary'})],'GESTIÓN DOCUMENTAL'));const list=el('div',{class:'item-list'});let count;const draw=()=>{const docs=byKind('document').filter(d=>(!S.filter||d.matter_id===S.filter)&&match(S.search,d.title,d.data?.filename,d.data?.text));count.textContent=docs.length+' documentos';list.replaceChildren(...(docs.length?docs.map(d=>{const versions=Array.isArray(d.data?.versions)?d.data.versions.length+1:1;const loc=d.data?.pagination==='segments'?'segmentos':'páginas';return el('article',{class:'list-row'},icon('file'),el('div',{class:'row-main'},el('strong',{},d.title),el('small',{},matterTitle(d.matter_id)+' · '+versions+' '+(versions===1?'versión':'versiones')+' · '+shortDate(d.updated_at)+(d.data?.pages?.length?' · '+d.data.pages.length+' '+loc:''))),d.data?.locked||d.data?.final?badge('Protegido','pending'):null,el('div',{class:'row-actions'},button('Abrir',()=>previewDocument(d),{class:'button small',icon:'eye'}),button('Editar',()=>openEditor(d),{class:'button small',icon:'edit'}),button('Versiones',()=>documentVersions(d),{class:'button small',icon:'history'}),button('',()=>documentMenu(d),{class:'icon-button',icon:'settings',title:'Opciones de '+d.title})));}):[empty('Tu biblioteca, organizada','Carga documentos PDF, Word o texto. Podrás consultarlos, conservar sus versiones y aportarlos al agente.',button('Cargar documentos',()=>{S.uploadUse='library';$('#upload-input').click();},{class:'button primary',icon:'upload'}),'folder')]));};const tools=listToolbar({placeholder:'Buscar en nombres y contenido…',onChange:draw,withMatter:true});count=tools.count;page.append(tools.bar,list,el('p',{class:'inline-help'},'Los documentos se guardan en tu cuenta. La carga conserva el original e informa de la extracción y del reconocimiento de texto disponible.'));draw();return page;}
async function uploadFiles(files,{documentId,expectedVersion,where='library'}={}){if(!files.length)return;if(files.length>10)throw new Error('Selecciona como máximo 10 archivos por carga.');const form=new FormData();for(const f of files)form.append('files',f);if(S.matterId)form.append('matter_id',S.matterId);if(documentId){form.append('document_id',documentId);form.append('expected_version',String(expectedVersion));}showModal('Cargando documentos',el('div',{class:'stack'},el('p',{class:'inline-help'},'Se conserva el original y se extrae el texto disponible.'),el('span',{class:'busy-indicator'},'Procesando '+files.length+' '+(files.length===1?'archivo':'archivos')+'…')),[]);try{const result=await api('/documents/upload',{method:'POST',body:form});for(const d of result.items||[]){mergeItem(d);if(where==='chat')S.selectedDocs.add(d.id);}closeModal();render();if(result.items?.length)toast(result.items.length+' '+(result.items.length===1?'documento guardado.':'documentos guardados.'));if(result.errors?.length)showModal('Resultado de la carga',el('div',{},el('p',{class:'inline-help'},'Estos archivos no se pudieron guardar:'),...result.errors.map(e=>el('div',{class:'callout error'},typeof e==='string'?e:[e.filename||e.name,e.error||e.detail||e.message].filter(Boolean).join(': ')))),[button('Cerrar',closeModal)]);}catch(error){closeModal();throw error;}}
function previewDocument(record){const d=item(record.id)||record;const warnings=(d.data?.warnings||[]).map(w=>el('div',{class:'callout warning'},text(w)));const preview=el('div',{class:'document-preview'},d.data?.text||'El archivo no tiene texto extraíble. Puedes descargar el original.');showModal(d.title,el('div',{},el('p',{class:'inline-help'},matterTitle(d.matter_id)+' · Actualizado '+shortDate(d.updated_at)),warnings,preview),[button('Usar en el agente',async()=>{closeModal();await newChat();S.matterId=d.matter_id||'';S.selectedDocs.add(d.id);S.mode='analyze';render();},{icon:'spark'}),button('Editar',()=>{closeModal();openEditor(d);},{icon:'edit'}),button('Descargar',()=>downloadOriginal(d),{icon:'download',class:'button primary'})],true);}
async function downloadOriginal(d,index){if(!d.data?.storage_path&&index===undefined)return exportDocument(d.data?.text||'',d.title,'docx');const suffix=index===undefined?'':'?version_index='+index;const blob=await api('/documents/'+d.id+'/download'+suffix,{blob:true});const version=index===undefined?d.data:d.data?.versions?.[index];downloadBlob(blob,version?.filename||d.data?.filename||filename(d.title,'bin'));}
function documentMenu(record){const d=item(record.id)||record;const locked=!!(d.data?.locked||d.data?.final);showModal('Opciones del documento',el('div',{class:'stack'},button('Cambiar nombre o asunto',()=>documentMetadata(d),{icon:'edit'}),button('Consultar actividad',()=>documentAudit(d),{icon:'history'}),button(locked?'Desbloquear para edición':'Proteger versión actual',async()=>{await updateItem(d,{data:{...d.data,locked:!locked,final:false}});closeModal();render();toast(locked?'Documento desbloqueado.':'Documento protegido contra cambios.');},{icon:'lock'}),button('Crear copia',async()=>{const clone={...d.data,storage_path:undefined,locked:false,final:false,versions:[],filename:undefined};await createItem('document',d.title+' · copia',clone,d.matter_id);closeModal();render();toast('Copia de texto creada.');},{icon:'copy'}),button('Eliminar documento',()=>confirmDialog('Eliminar documento','Se eliminarán este documento y sus referencias de almacenamiento conforme a la API. Descarga una copia si necesitas conservarla.',()=>removeItem(d)),{class:'button danger',icon:'trash'})),[button('Cerrar',closeModal)]);}
function documentMetadata(d){const name=field('Título',{value:d.title,required:true});const matter=field('Asunto',{value:d.matter_id||'',options:matterOptions()});formModal('Organizar documento',[name,matter],async()=>{await updateItem(d,{title:name.input.value.trim(),matter_id:matter.input.value||null});render();});}
async function documentAudit(d){const result=await api('/items/'+d.id+'/audit');const list=result.events||[];showModal('Actividad · '+d.title,el('div',{class:'item-list'},list.length?list.map(e=>el('div',{class:'list-row'},icon('history'),el('div',{class:'row-main'},el('strong',{},({insert:'Creación',create:'Creación',update:'Actualización',delete:'Eliminación',restore:'Restauración'}[e.operation]||e.operation)),el('small',{},shortDate(e.created_at,true)+' · versión '+e.version)))):el('p',{class:'inline-help'},'No hay actividad disponible.')),[button('Cerrar',closeModal)]);}
function documentVersions(record){const d=item(record.id)||record;const versions=Array.isArray(d.data?.versions)?d.data.versions:[];const list=el('div',{class:'item-list'},el('div',{class:'callout'},'La versión actual se conserva al restaurar una anterior. Las versiones son de este documento y de tu cuenta.'));if(!versions.length)list.append(el('p',{class:'inline-help'},'Todavía no hay versiones anteriores. Guarda cambios o carga una nueva versión del archivo.'));versions.forEach((v,i)=>list.append(el('div',{class:'list-row'},icon('history'),el('div',{class:'row-main'},el('strong',{},v.title||v.filename||'Versión '+(i+1)),el('small',{},shortDate(v.created_at||v.updated_at||v.at,true))),el('div',{class:'row-actions'},button('Comparar',()=>compareTexts(v.text||'',d.data?.text||'',d.title),{class:'button small'}),button('Restaurar',()=>confirmDialog('Restaurar versión','La versión actual se añadirá al historial antes de restaurar esta versión.',async()=>{const restored=await api('/documents/'+d.id+'/restore',{method:'POST',body:{expected_version:d.version,version_index:i}});mergeItem(restored);render();toast('Versión restaurada.');},'Restaurar'),{class:'button small'}),v.storage_path?button('Original',()=>downloadOriginal(d,i),{class:'button small'}):null))));showModal('Versiones · '+d.title,list,[button('Nueva versión del archivo',()=>{S.versionTarget=d;$('#version-input').click();},{icon:'upload',class:'button primary'}),button('Cerrar',closeModal)],true);}
function newEditor(){const launch=()=>{S.editor={id:null,title:'Nuevo escrito',text:'',baseText:'',matter_id:S.matterId||''};S.editorDirty=false;setPage('documentos');setTimeout(()=>$('#editor-title')?.select(),0);};if(S.editorDirty)return confirmDialog('Abrir un escrito nuevo','El editor tiene cambios sin guardar. Se descartarán al continuar.',launch,'Descartar y abrir');launch();}
function openEditor(d){if(S.editorDirty&&S.editor?.id===d.id){closeModal();setPage('documentos');return;}const launch=()=>{const fresh=item(d.id)||d;S.editor={id:fresh.id,recordVersion:fresh.version,title:fresh.title,text:fresh.data?.text||'',baseText:fresh.data?.text||'',matter_id:fresh.matter_id||''};S.editorDirty=false;closeModal();setPage('documentos');};if(S.editorDirty&&S.editor?.id!==d.id)return confirmDialog('Cambiar de documento','El editor tiene cambios sin guardar. Se descartarán al continuar.',launch,'Descartar y abrir');launch();}
function renderEditor(){const page=el('section',{class:'page'});page.append(pageHeader('Editor y versiones','Revisa cada escrito, conserva su historial y exporta el resultado con control sobre los cambios.',[button('Nuevo escrito',newEditor,{icon:'plus',class:'button primary'})]));const docs=byKind('document');if(!S.editor){page.append(docs.length?el('div',{class:'item-list'},docs.map(d=>el('div',{class:'list-row'},icon('file'),el('div',{class:'row-main'},el('strong',{},d.title),el('small',{},matterTitle(d.matter_id))),button('Editar escrito',()=>openEditor(d),{class:'button small'})))):empty('De borrador a escrito','Crea un documento o guarda una respuesta del agente para revisarla aquí.',button('Crear escrito',newEditor,{class:'button primary',icon:'plus'}),'file'));return page;}const ed=S.editor;const record=item(ed.id);const locked=!!(record?.data?.locked||record?.data?.final);const nav=el('div',{class:'editor-list','aria-label':'Documentos'},docs.map(d=>{const b=button('',()=>openEditor(d),{class:'editor-file '+(ed.id===d.id?'active':'')});b.append(d.title,el('small',{},shortDate(d.updated_at)));return b;}));const title=el('input',{id:'editor-title',class:'editor-title',value:ed.title,'aria-label':'Título del escrito',maxLength:200,readOnly:locked});const area=el('textarea',{id:'editor-text',class:'editor-text',value:ed.text,'aria-label':'Texto del escrito',spellcheck:true,readOnly:locked,maxLength:1000000,placeholder:'Escribe o pega el contenido que quieres trabajar…'});const status=el('div',{class:'editor-status'},locked?'Documento protegido. Desbloquéalo desde DMS para editar.':S.editorDirty?'Cambios sin guardar.':'Documento guardado en tu cuenta.');if(!ed.id)status.textContent='Borrador nuevo. Guarda para conservarlo en tu cuenta.';const changed=()=>{ed.text=area.value;ed.title=title.value;S.editorDirty=true;status.textContent='Cambios sin guardar · '+area.value.split(/\s+/).filter(Boolean).length+' palabras';};title.addEventListener('input',changed);area.addEventListener('input',changed);const save=button('Guardar versión',e=>busy(e.currentTarget,saveEditor),{icon:'check',class:'button primary',disabled:locked});const panel=el('div',{class:'editor-area'},el('div',{class:'editor-top'},title,record?badge('v'+record.version):badge('Nuevo')),area,el('div',{class:'editor-tools'},el('div',{class:'actions'},button('Comparar cambios',()=>{captureDrafts();return compareTexts(ed.baseText,ed.text,ed.title);},{icon:'columns',class:'button small'}),button('Ajustar con IA',editorAI,{icon:'spark',class:'button small',disabled:locked}),record?button('Historial',()=>documentVersions(record),{icon:'history',class:'button small'}):null),el('div',{class:'actions'},button('Word',()=>{captureDrafts();return exportDocument(ed.text,ed.title,'docx');},{icon:'download',class:'button small'}),button('PDF',()=>{captureDrafts();return exportDocument(ed.text,ed.title,'pdf');},{icon:'download',class:'button small'}),save)),status);page.append(el('div',{class:'editor-layout'},nav,panel));return page;}
async function saveEditor(){captureDrafts();const ed=S.editor;if(!ed?.title.trim())throw new Error('Escribe un título para el documento.');if(!ed.text.trim())throw new Error('El documento está vacío.');let saved;if(ed.id){const record=item(ed.id);if(ed.recordVersion&&record.version!==ed.recordVersion)throw new Error('Este documento cambió desde que lo abriste. Descarga tus cambios y abre la versión reciente para compararlos antes de guardar.');if(record.data?.locked||record.data?.final)throw new Error('Desbloquea el documento antes de editarlo.');const versions=[...(record.data?.versions||[])];if(record.data?.text!==ed.text)versions.push({title:record.title,text:record.data?.text||'',pages:record.data?.pages||[],pagination:record.data?.pagination,filename:record.data?.filename,mime:record.data?.mime,storage_path:record.data?.storage_path,created_at:record.updated_at||new Date().toISOString()});saved=await updateItem(record,{title:ed.title.trim(),data:{...record.data,text:ed.text,pages:[],pagination:'segments',versions,source:'editor'}});}else saved=await createItem('document',ed.title.trim(),{text:ed.text,pages:[],pagination:'segments',mime:'text/plain',versions:[],source:'editor'},ed.matter_id);S.editor={id:saved.id,recordVersion:saved.version,title:saved.title,text:saved.data?.text||ed.text,baseText:saved.data?.text||ed.text,matter_id:saved.matter_id};S.editorDirty=false;render();toast('Versión guardada.');return saved;}
async function compareTexts(base,updated,title){const result=await api('/api/versiones/comparar',{method:'POST',body:{texto_base:base,texto_comparado:updated,autor:S.user?.user_metadata?.name||'El Memorialista'}});const diff=el('div',{class:'diff-view'});for(const para of result.parrafos_diff||[])diff.append(el('p',{},para.length?para.map(t=>el(t.tipo==='insert'?'ins':t.tipo==='delete'?'del':'span',{},t.texto)):'\u00a0'));const stats=result.estadisticas||{};showModal('Comparar · '+title,el('div',{},el('div',{class:'diff-summary'},(stats.palabras_anadidas||0)+' palabras añadidas',(stats.palabras_eliminadas||0)+' eliminadas'),diff),[button('Cerrar',closeModal),button('Word con cambios',async()=>{const blob=await api('/api/versiones/exportar-docx',{method:'POST',body:{texto_base:base,texto_comparado:updated,titulo:title,autor:'El Memorialista'},blob:true});downloadBlob(blob,filename(title+'-cambios','docx'));},{icon:'download',class:'button primary'})],true);}
function editorAI(){captureDrafts();if(!S.editor?.text.trim())throw new Error('Añade texto antes de pedir un ajuste.');const instruction=field('Qué quieres ajustar',{type:'textarea',required:true,placeholder:'Describe el ajuste; por ejemplo, mejorar la estructura o señalar contradicciones.'});formModal('Proponer un ajuste',[instruction],async()=>{const original=S.editor.text;if(original.length+instruction.input.value.length+350>80000)throw new Error('El escrito supera el límite de 80.000 caracteres para un ajuste completo. Divide el trabajo en secciones antes de solicitar la propuesta; el texto no se ha recortado ni enviado.');const result=await api('/chat',{method:'POST',body:{mode:'draft',message:'Aplica el siguiente ajuste al escrito. Devuelve sólo el documento completo actualizado, sin comentarios previos. No inventes hechos. Ajuste: '+instruction.input.value+'\n\nDOCUMENTO A REVISAR:\n'+original,history:[],document_ids:[],matter_id:S.editor.matter_id||null}});if(!result.answer)throw new Error('No se recibió un ajuste.');setTimeout(()=>showProposedEdit(original,result.answer),0);},{label:'Preparar propuesta',extra:el('div',{class:'callout'},'La propuesta se mostrará antes de aplicar cambios al editor.')});}
async function showProposedEdit(original,proposal){const result=await api('/api/versiones/comparar',{method:'POST',body:{texto_base:original,texto_comparado:proposal}});const diff=el('div',{class:'diff-view'});for(const para of result.parrafos_diff||[])diff.append(el('p',{},para.map(t=>el(t.tipo==='insert'?'ins':t.tipo==='delete'?'del':'span',{},t.texto))));showModal('Revisar propuesta de la IA',el('div',{},el('div',{class:'callout'},'Revisa los cambios. Al aceptarlos se aplican al editor; guarda una versión para conservarlos.'),diff),[button('Descartar',closeModal),button('Aplicar al editor',()=>{S.editor.text=proposal;S.editorDirty=true;closeModal();render();},{class:'button primary',icon:'check'})],true);}
function renderTables(){const page=el('section',{class:'page'});page.append(pageHeader('Revisión en tabla','Define qué necesitas encontrar y contrasta la información de varios documentos. Cada celda conserva su referencia cuando está disponible.',[button('Tablas guardadas',savedTables,{icon:'history'})],'REVISIÓN DOCUMENTAL'));const docs=byKind('document');const checks=el('div',{class:'checklist'});const chosen=new Set();for(const d of docs){const check=el('input',{type:'checkbox',value:d.id});check.addEventListener('change',()=>check.checked?chosen.add(d.id):chosen.delete(d.id));checks.append(el('label',{class:'check-row'},check,el('span',{},d.title,el('small',{},matterTitle(d.matter_id)))));}if(!docs.length)checks.append(el('p',{class:'inline-help'},'Carga documentos en DMS antes de iniciar una revisión.'));const cols=field('Columnas a extraer',{type:'textarea',value:'Partes\nObjeto\nFechas relevantes\nObligaciones\nPuntos por revisar',help:'Una columna por línea. Hasta 8 columnas por revisión.'});const instruction=field('Criterio adicional (opcional)',{type:'textarea',placeholder:'Ej. conservar las fechas y cifras tal como aparecen.'});const resultBox=el('div',{id:'table-result'});if(S.tableResult)resultBox.append(tableResultView(S.tableResult));const run=button('Revisar documentos',async e=>{const columns=cols.input.value.split('\n').map(s=>s.trim()).filter(Boolean);if(!chosen.size)throw new Error('Selecciona al menos un documento.');if(chosen.size>10)throw new Error('Selecciona como máximo 10 documentos por revisión.');if(!columns.length||columns.length>8)throw new Error('Introduce entre 1 y 8 columnas.');await busy(e.currentTarget,async()=>{resultBox.replaceChildren(el('div',{class:'callout'},el('span',{class:'busy-indicator'},'Revisando los documentos seleccionados…')));try{const result=await api('/tables/analyze',{method:'POST',body:{document_ids:[...chosen],columns,instruction:instruction.input.value}});S.tableResult=result;resultBox.replaceChildren(tableResultView(result));}catch(error){resultBox.replaceChildren(el('div',{class:'callout error'},error.message));throw error;}});},{icon:'spark',class:'button primary',disabled:!docs.length});page.append(el('div',{class:'table-controls'},el('div',{class:'panel'},el('h2',{},'1. Selecciona los documentos'),checks),el('div',{class:'panel'},el('h2',{},'2. Define la revisión'),cols.wrap,instruction.wrap,run)),resultBox);return page;}
function tableResultView(result){const cols=result.columns||[];const rows=result.rows||[];const body=el('div',{},el('div',{class:'section-heading'},el('h2',{},'Resultado de la revisión'),el('div',{class:'actions'},button('Guardar tabla',()=>saveTable(result),{icon:'check',class:'button small'}),button('Exportar CSV',()=>exportTable(result),{icon:'download',class:'button small'}))),el('div',{class:'table-scroll'},el('table',{},el('thead',{},el('tr',{},el('th',{scope:'col'},'Documento'),cols.map(c=>el('th',{scope:'col'},text(c))))),el('tbody',{},rows.map(r=>el('tr',{},el('td',{},r.title||item(r.document_id)?.title||'Documento'),(r.cells||[]).map(c=>el('td',{},typeof c==='string'?c:text(c.value),c.source_page?el('small',{},'Página '+c.source_page):c.source_segment?el('small',{},'Segmento '+c.source_segment):null,c.verified!==undefined?el('small',{},c.verified?'Fragmento contrastado con el texto disponible.':'Dato o fragmento pendiente de verificación.'):null,c.excerpt?el('small',{},'«'+c.excerpt+'»'):null,c.warning?el('small',{class:'danger-text'},c.warning):null))))))));for(const row of rows){if(row.coverage?.truncated)body.append(el('div',{class:'callout warning'},(row.title||'Documento')+': se utilizó una selección de '+row.coverage.selected_passages+' de '+row.coverage.available_passages+' fragmentos disponibles.'));for(const warning of row.warnings||[])body.append(el('div',{class:'callout warning'},(row.title||'Documento')+': '+text(warning)));}for(const warning of result.warnings||[])body.append(el('div',{class:'callout warning'},text(warning)));return body;}
function csvCell(v){const raw=String(v??'');const safe=/^[=+\-@\t\r]/.test(raw)?"'"+raw:raw;return '"'+safe.replace(/"/g,'""')+'"';}
function exportTable(result){const lines=[['Documento',...(result.columns||[])].map(csvCell).join(',')];for(const r of result.rows||[])lines.push([r.title||item(r.document_id)?.title||'Documento',...(r.cells||[]).map(c=>typeof c==='string'?c:c.value||'')].map(csvCell).join(','));downloadBlob(new Blob(['\uFEFF'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'}),'revision-documental.csv');}
function saveTable(result){const title=field('Nombre de la revisión',{value:'Revisión documental · '+shortDate(new Date().toISOString()),required:true});const matter=field('Asunto',{value:S.matterId,options:matterOptions()});formModal('Guardar revisión',[title,matter],async()=>{await createItem('table',title.input.value.trim(),result,matter.input.value);toast('Tabla guardada.');});}
function savedTables(){const tables=byKind('table');const body=el('div',{class:'item-list'},tables.length?tables.map(t=>el('div',{class:'list-row'},icon('table'),el('div',{class:'row-main'},el('strong',{},t.title),el('small',{},shortDate(t.updated_at))),el('div',{class:'row-actions'},button('Abrir',()=>{S.tableResult=t.data;closeModal();setPage('tablas');},{class:'button small'}),button('Eliminar',()=>confirmDialog('Eliminar tabla','Se eliminará esta revisión guardada. Sus documentos se conservarán.',()=>removeItem(t)),{class:'button small',icon:'trash'})))):el('p',{class:'inline-help'},'Aún no hay tablas guardadas.'));showModal('Revisiones guardadas',body,[button('Cerrar',closeModal)]);}
function renderMonitors(){const page=el('section',{class:'page'});page.append(pageHeader('Monitor jurídico','Vigila fuentes oficiales y evalúa los cambios según tus condiciones jurídicas.',[button('Crear monitor',()=>monitorForm(),{icon:'plus',class:'button primary'})],'MONITOREO DE FUENTES'));const config=S.caps?.monitoring;page.append(el('div',{class:'callout'},config?.automatic?'La revisión automática está habilitada mientras el servicio permanezca activo. También puedes ejecutar cada monitor manualmente.':config?.message||'Puedes revisar cada monitor manualmente. La revisión automática requiere que el servicio programado esté configurado.'));page.append(el('p',{class:'inline-help'},'Selecciona evaluación con IA o coincidencias de palabras. Cada revisión muestra las fuentes y el contenido que pudo analizar; los errores se conservan para que puedas revisarlos.'));const grid=el('div',{class:'grid'});const monitors=byKind('monitor');if(!monitors.length){page.append(empty('Tus fuentes, bajo seguimiento','Selecciona una fuente oficial, define tu condición y revisa los cambios junto con sus evidencias.',button('Crear primer monitor',()=>monitorForm(),{class:'button primary',icon:'plus'}),'monitor'));return page;}const names={baseline:'Primera lectura guardada',changed:'Cambio con coincidencias',unchanged:'Sin cambios',changed_no_match:'Cambio sin coincidencias',reviewed:'Revisado sin nuevas coincidencias',partial:'Revisión parcial: contenido pendiente',error:'No se pudo comprobar'};for(const m of monitors){const d=m.data||{};grid.append(el('article',{class:'card'},el('div',{class:'card-head'},icon('monitor'),badge(d.enabled===false?'Pausado':config?.automatic?'Automático':'Manual',d.enabled===false?'neutral':config?.automatic?'':'pending')),el('h3',{},m.title),el('div',{class:'monitor-url'},link(d.url||'Sin URL',d.url)),el('p',{},d.analysis_mode==='semantic'?d.condition||'Condición pendiente':Array.isArray(d.keywords)?d.keywords.join(' · '):d.keywords||'Todos los cambios de contenido'),badge(d.analysis_mode==='semantic'?'Evaluación con IA':'Palabras clave','neutral'),el('div',{class:'monitor-meta'},'Última comprobación: '+shortDate(d.last_checked,true),el('br'),'Estado: '+(v5MonitorExtractionIncomplete(d)?'Extracción parcial: revisión incompleta':names[d.last_status]||'Sin comprobar'),el('br'),'Frecuencia solicitada: '+(d.interval_minutes||60)+' minutos'),d.last_error?el('div',{class:'callout error'},d.last_error):null,v5MonitorIssues(d),el('div',{class:'card-actions'},button('Comprobar ahora',async e=>busy(e.currentTarget,async()=>{const updated=await api('/monitors/'+m.id+'/run',{method:'POST'});mergeItem(updated);render();const fresh=item(m.id);toast(v5MonitorExtractionIncomplete(fresh?.data||{})?'Comprobación parcial: falta contenido por extraer.':names[fresh?.data?.last_status]||'Comprobación terminada.');}),{class:'button small',icon:'search'}),button('Hallazgos ('+(d.findings?.length||0)+')',()=>monitorFindings(m),{class:'button small'}),button('Editar',()=>monitorForm(m),{class:'button small',icon:'edit'}),button(d.enabled===false?'Activar':'Pausar',async()=>{await updateItem(item(m.id),{data:{...item(m.id).data,enabled:d.enabled===false}});render();},{class:'button small'}),button('',()=>confirmDialog('Eliminar monitor','Se eliminará este monitor y su historial de hallazgos.',()=>removeItem(m)),{class:'button small',icon:'trash',title:'Eliminar monitor'}))));}page.append(grid);return page;}
async function loadSignatures(){try{const result=await api('/signatures');S.signatures=Array.isArray(result)?result:result.signatures||[];S.signatureError='';if(S.page==='firmas')render();}catch(error){S.signatureError=error.message;if(S.page==='firmas')render();}}
function signatureStatus(s){if(s.status==='signed')return['Firmado',''];if(s.status==='cancelled')return['Cancelado','neutral'];if(s.expires_at&&new Date(s.expires_at)<new Date())return['Enlace vencido','error'];return['Pendiente','pending'];}
function renderSignatures(){const page=el('section',{class:'page'});page.append(pageHeader('Firma electrónica','Prepara una solicitud, comparte su enlace privado y conserva la evidencia del documento aceptado.',[button('Actualizar',loadSignatures,{icon:'history'}),button('Nueva solicitud',()=>signatureForm(),{icon:'plus',class:'button primary'})],'DOCUMENTOS Y ACEPTACIÓN'));page.append(el('div',{class:'callout'},'La firma por enlace privado registra el consentimiento y la huella del documento. La identidad es declarada por quien firma; revisa los requisitos del documento y del acto antes de utilizar este mecanismo.'));if(S.caps?.signatures?.configured===false)page.append(el('div',{class:'callout warning'},'La firma electrónica está pendiente de activar en esta instalación. Configura el servicio y aplica su migración antes de crear enlaces.'));if(S.signatureError)page.append(el('div',{class:'callout error'},S.signatureError));if(!S.signatures.length){page.append(empty('Del escrito a la aceptación','Crea una solicitud a partir de un documento revisado. Recibirás un enlace para compartir con la persona indicada.',button('Preparar solicitud',()=>signatureForm(),{class:'button primary',icon:'sign'}),'sign'));return page;}page.append(el('div',{class:'item-list'},S.signatures.map(s=>{const[label,type]=signatureStatus(s);return el('article',{class:'list-row'},icon('sign'),el('div',{class:'row-main'},el('strong',{},s.title),el('small',{},[s.signer_name,s.signer_email].filter(Boolean).join(' · ')),el('small',{},'Creada '+shortDate(s.created_at)+(s.signed_at?' · Firmada '+shortDate(s.signed_at,true):s.expires_at?' · Vence '+shortDate(s.expires_at,true):''))),badge(label,type),el('div',{class:'row-actions'},button('Ver detalle',()=>signatureDetail(s),{class:'button small'}),s.status==='signed'?button('Constancia PDF',()=>signatureReceipt(s),{class:'button small',icon:'download'}):null,s.status==='pending'?button('Renovar enlace',()=>renewSignature(s),{class:'button small',icon:'link'}):null,s.status==='pending'?button('Cancelar',()=>cancelSignature(s),{class:'button small',icon:'close'}):null));})));return page;}
function signatureForm(){const docs=byKind('document').filter(d=>d.data?.text);const documentSelect=field('Documento guardado (opcional)',{options:[{value:'',label:'Escribir o pegar contenido'},...docs.map(d=>({value:d.id,label:d.title}))]});const title=field('Título del documento',{required:true});const content=field('Contenido que se enviará a firma',{type:'textarea',required:true,help:'Se conservará esta versión del texto. Revisa su contenido antes de crear la solicitud.'});documentSelect.input.addEventListener('change',()=>{const d=item(documentSelect.input.value);if(d){title.input.value=d.title;content.input.value=d.data?.text||'';}});const name=field('Nombre de quien firma',{required:true});const email=field('Correo de referencia',{type:'email',required:true,help:'No se envía un correo automáticamente; tú compartes el enlace privado.'});const expiry=field('Vigencia del enlace (días)',{type:'number',value:7,min:1,max:30,required:true});formModal('Preparar solicitud de firma',[documentSelect,title,content,name,email,expiry],async()=>{const result=await api('/signatures',{method:'POST',body:{title:title.input.value.trim(),text:content.input.value,signer_name:name.input.value.trim(),signer_email:email.input.value.trim(),expires_days:Number(expiry.input.value)}});await loadSignatures();setTimeout(()=>showSigningLink(result),0);},{label:'Crear enlace privado',wide:true,extra:el('div',{class:'callout warning'},'Este mecanismo registra una aceptación por enlace privado, con identidad declarada. No incorpora verificación de identidad ni certificado digital de un tercero.')});}
function showSigningLink(result){const url=result.signing_url;if(!url)throw new Error('La solicitud se creó, pero no se recibió un enlace. Actualiza las solicitudes y renueva el enlace.');const body=el('div',{},el('div',{class:'callout'},result.notice||'Copia este enlace y compártelo únicamente con la persona indicada. No se enviará ningún mensaje automáticamente.'),el('div',{class:'signature-link'},url),el('p',{class:'inline-help'},'El enlace contiene un acceso privado. Se muestra ahora; si necesitas recuperarlo más adelante, usa «Renovar enlace».'));showModal('Enlace de firma preparado',body,[button('Cerrar',closeModal),button('Copiar enlace',()=>copy(url),{icon:'copy',class:'button primary'})]);}
async function signatureDetail(s){const result=await api('/signatures/'+s.id);const d=result.signature||result;const[label,type]=signatureStatus(d);const body=el('div',{},badge(label,type),el('dl',{class:'detail-kv'},el('dt',{},'Persona indicada'),el('dd',{},d.signer_name||'—'),el('dt',{},'Correo'),el('dd',{},d.signer_email||'—'),el('dt',{},'Creada'),el('dd',{},shortDate(d.created_at,true)),el('dt',{},'Firmada'),el('dd',{},shortDate(d.signed_at,true)),el('dt',{},'Vencimiento'),el('dd',{},shortDate(d.expires_at,true)),el('dt',{},'Huella del documento'),el('dd',{},d.document_hash||d.content_hash||d.sha256||'Disponible en la constancia')),(d.document_text||d.text)?el('div',{class:'document-preview'},d.document_text||d.text):null);showModal(d.title||'Solicitud de firma',body,[button('Cerrar',closeModal),d.status==='signed'?button('Constancia PDF',()=>signatureReceipt(d),{icon:'download',class:'button primary'}):null].filter(Boolean),true);}
function renewSignature(s){return confirmDialog('Renovar enlace de firma','Se invalidará el enlace anterior y se generará uno nuevo con una vigencia de 7 días. Tendrás que compartir el enlace nuevo.',async()=>{const result=await api('/signatures/'+s.id+'/link',{method:'POST'});await loadSignatures();setTimeout(()=>showSigningLink(result),0);},'Renovar enlace');}
function cancelSignature(s){return confirmDialog('Cancelar solicitud de firma','El enlace dejará de aceptar firmas para esta solicitud.',async()=>{await api('/signatures/'+s.id+'/cancel',{method:'POST'});await loadSignatures();toast('Solicitud cancelada.');},'Cancelar solicitud');}
async function signatureReceipt(s){const blob=await api('/signatures/'+s.id+'/receipt',{blob:true});downloadBlob(blob,filename('constancia-'+s.title,'pdf'));}
function renderSettings(){const page=el('section',{class:'page'});page.append(pageHeader('Ajustes del despacho','Conexiones, instrucciones de trabajo y copias de tus datos.',[button('Comprobar conexiones',async e=>busy(e.currentTarget,async()=>{S.caps=await api('/capabilities');render();toast('Estado actualizado.');}),{icon:'history'})]));const c=S.caps||{};const card=(title,ready,message)=>el('div',{class:'connection-card'},el('h3',{},title,badge(ready?'Configurado':'Por configurar',ready?'':'pending')),el('p',{},message));page.append(el('div',{class:'connection-grid'},card('Almacenamiento privado',c.storage?.ready,c.storage?.message||'El estado se comprueba con el servicio del despacho.'),card('Asistente de IA',c.ai?.configured,c.ai?.configured?'Proveedor configurado. La disponibilidad y el consumo se comprueban al ejecutar cada encargo.':'Configura un proveedor de IA en el servidor para utilizar el agente y las revisiones.'),card('Monitoreo programado',c.monitoring?.automatic,c.monitoring?.message||'Las comprobaciones manuales están disponibles cuando se habilita el almacenamiento.'),card('Firma electrónica',c.signatures?.configured,c.signatures?.configured?'Servicio por enlace privado habilitado. La solicitud comprueba sus permisos y la disponibilidad del almacenamiento.':'El servicio de firma necesita habilitación en el servidor y su migración.'),card('Sesión de usuario',!!S.user,'Conectado como '+(S.user?.email||'usuario autenticado')+'. Los permisos se comprueban en el servidor.')));const plays=byKind('playbook');page.append(el('section',{class:'settings-section'},el('div',{class:'section-heading'},el('h2',{},'Instrucciones reutilizables'),button('Crear instrucciones',()=>playbookForm(),{class:'button small',icon:'plus'})),el('p',{},'Define criterios de estilo, estructura o revisión y selecciónalos al iniciar un encargo.'),el('div',{class:'item-list'},plays.length?plays.map(p=>el('div',{class:'list-row'},icon('book'),el('div',{class:'row-main'},el('strong',{},p.title),el('small',{},String(p.data?.instructions||'').slice(0,130))),el('div',{class:'row-actions'},button('Editar',()=>playbookForm(p),{class:'button small'}),button('Eliminar',()=>confirmDialog('Eliminar instrucciones','Se eliminará este conjunto de instrucciones reutilizables.',()=>removeItem(p)),{class:'button small',icon:'trash'})))):el('p',{class:'inline-help'},'Todavía no has guardado instrucciones.'))));page.append(el('section',{class:'settings-section'},el('h2',{},'Copias y portabilidad'),el('p',{},'Exporta el contenido del despacho o importa una copia compatible. Los archivos originales deben descargarse también desde DMS si necesitas una copia independiente del almacenamiento.'),el('div',{class:'actions'},button('Exportar despacho',exportBackup,{icon:'download'}),button('Importar copia',()=>$('#backup-input').click(),{icon:'upload'}))));page.append(el('section',{class:'settings-section'},el('h2',{},'El Memorialista en Word'),el('p',{},'Utiliza el complemento para trabajar sobre el texto seleccionado y aprobar una propuesta antes de insertarla con control de cambios. Su instalación requiere Word compatible y una dirección HTTPS.'),el('div',{class:'actions'},el('a',{class:'button',href:'/word',target:'_blank',rel:'noopener'},icon('external'),'Abrir complemento'),el('a',{class:'button',href:'/word/manifest.xml',download:'el-memorialista-word.xml'},icon('download'),'Descargar manifiesto'))));page.append(el('section',{class:'settings-section'},el('h2',{},'Tu cuenta'),el('p',{},'El generador especializado sigue disponible con tus flujos de redacción. El cierre de sesión termina el acceso privado en este navegador.'),el('div',{class:'actions'},el('a',{class:'button',href:'/generador'},icon('file'),'Abrir generador'),button('Cerrar sesión',logout,{icon:'logout',class:'button danger'}))));return page;}
function playbookForm(record){const title=field('Nombre',{value:record?.title,required:true,placeholder:'Ej. criterios de revisión del despacho'});const instructions=field('Instrucciones',{value:record?.data?.instructions,type:'textarea',required:true,help:'Incluye preferencias de estilo y criterios de revisión. Los datos del caso deben aportarse en su asunto o sus documentos.'});formModal(record?'Editar instrucciones':'Instrucciones reutilizables',[title,instructions],async()=>{if(record)await updateItem(item(record.id),{title:title.input.value.trim(),data:{...record.data,instructions:instructions.input.value.trim()}});else await createItem('playbook',title.input.value.trim(),{instructions:instructions.input.value.trim()},'');render();toast('Instrucciones guardadas.');});}
async function exportBackup(){const backup=await api('/export');downloadBlob(new Blob([JSON.stringify(backup)],{type:'application/json;charset=utf-8'}),'el-memorialista-despacho-'+new Date().toISOString().slice(0,10)+'.json');}
async function importBackup(file){if(!file)return;if(file.size>26*1024*1024)throw new Error('El archivo supera 26 MiB. El respaldo admite hasta 24 MiB de contenido JSON; el margen de archivo permite espacios de formato.');let backup;try{backup=JSON.parse(await file.text());}catch{throw new Error('El archivo no contiene una copia JSON válida.');}if(!backup||backup.format!=='memorialista-despacho')throw new Error('Esta pantalla importa copias del despacho. Las copias del asesor ciudadano y del generador se importan desde sus respectivas herramientas.');if(new Blob([JSON.stringify(backup)]).size>24*1024*1024)throw new Error('El contenido del respaldo supera 24 MiB, incluso sin los espacios de formato. Solicita una exportación administrativa.');showModal('Importar copia del despacho',el('div',{},el('p',{class:'inline-help'},'Se importarán los elementos compatibles. La API valida la copia y conserva las diferencias como copias para evitar sobrescrituras silenciosas.'),el('p',{class:'inline-help'},'Archivo máximo: 26 MiB. Contenido JSON máximo: 24 MiB. El servidor realiza la validación final del contenido.'),el('p',{class:'inline-help'},'Archivo: '+file.name)),[button('Cancelar',closeModal),button('Importar',async e=>busy(e.currentTarget,async()=>{const result=await api('/import',{method:'POST',body:{backup}});await refresh({silent:true});closeModal();showModal('Resultado de la importación',el('div',{},el('p',{},'Elementos importados: '+(result.imported??0)),result.conflicts!==undefined?el('p',{class:'inline-help'},'Conflictos conservados: '+(Array.isArray(result.conflicts)?result.conflicts.length:result.conflicts)):null,...(result.warnings||[]).map(w=>el('div',{class:'callout warning'},text(w)))),[button('Cerrar',closeModal)]);}),{class:'button primary',icon:'upload'})]);}
function quickSearch(){const input=el('input',{type:'search',placeholder:'Asuntos, documentos, conversaciones…','aria-label':'Buscar en el despacho'});const result=el('div',{class:'search-results'});const kindLabels={matter:'Asunto',document:'Documento',conversation:'Conversación',monitor:'Monitor',table:'Tabla',playbook:'Instrucciones',event:'Acontecimiento',source:'Fuente'};const draw=()=>{const query=input.value.trim();const matches=query?S.items.filter(i=>match(query,i.title,i.data?.client,i.data?.reference)).slice(0,40):S.items.slice().sort((a,b)=>String(b.updated_at).localeCompare(String(a.updated_at))).slice(0,10);result.replaceChildren(...(matches.length?matches.map(i=>{const b=button('',()=>{closeModal();if(i.kind==='matter')matterDetail(i);else if(i.kind==='document')previewDocument(i);else if(i.kind==='conversation')openConversation(i.id);else if(i.kind==='monitor')setPage('monitores');else if(i.kind==='table'){S.tableResult=i.data;setPage('tablas');}else if(i.kind==='playbook')playbookForm(i);else if(i.kind==='event')eventForm(i,i.matter_id);else showModal(i.title,el('div',{class:'document-preview'},text(i.data)),[button('Cerrar',closeModal)]);},{class:'result-button'});b.append(el('strong',{},i.title),el('small',{},(kindLabels[i.kind]||i.kind)+' · '+shortDate(i.updated_at)));return b;}):[el('p',{class:'inline-help'},'No hay resultados para esa búsqueda.')]));};input.addEventListener('input',draw);draw();showModal('Buscar en mi despacho',el('div',{},el('div',{class:'field'},input),result),[button('Cerrar',closeModal)]);input.focus();}
async function logout(){if(S.editorDirty){await confirmDialog('Cerrar sesión','El editor contiene cambios sin guardar. Descárgalos o guárdalos antes de cerrar; continuar descartará esos cambios.',async()=>{S.editorDirty=false;await performLogout();},'Cerrar y descartar');return;}await performLogout();}
async function performLogout(){v5StopRequests();cancelChat();await MemAuth.clearCookie();const result=await S.client.auth.signOut({scope:'local'});if(result.error)throw result.error;S.items=[];S.messages=[];S.editor=null;S.signatures=[];location.assign('/login');}
function initEvents(){$('#new-chat').addEventListener('click',act(newChat));$('#all-conversations').addEventListener('click',allConversations);$('#account-button').addEventListener('click',()=>setPage('ajustes'));$('#quick-search').addEventListener('click',quickSearch);$('#refresh-button').addEventListener('click',act(e=>busy(e.currentTarget,()=>refresh())));$('#mobile-menu').addEventListener('click',()=>$('#sidebar').classList.contains('open')?closeSidebar():openSidebar());$('#sidebar-scrim').addEventListener('click',closeSidebar);$('#modal-close').addEventListener('click',closeModal);$('#modal').addEventListener('close',()=>{for(const url of V5.browserUrls)URL.revokeObjectURL(url);V5.browserUrls.clear();V5.resourceSequence++;if(S.modalReturn?.isConnected)S.modalReturn.focus();});$('#upload-input').addEventListener('change',act(async e=>{const files=[...e.target.files];e.target.value='';await uploadFiles(files,{where:S.uploadUse});}));$('#version-input').addEventListener('change',act(async e=>{const files=[...e.target.files];e.target.value='';const target=S.versionTarget;S.versionTarget=null;if(target&&files.length)await uploadFiles(files,{documentId:target.id,expectedVersion:target.version});}));$('#backup-input').addEventListener('change',act(async e=>{const file=e.target.files[0];e.target.value='';await importBackup(file);}));window.addEventListener('keydown',act(async e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!$('#modal').open)await newChat();}if((e.metaKey||e.ctrlKey)&&e.key==='/'){e.preventDefault();quickSearch();}if(e.key==='Escape')closeSidebar();if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='s'&&S.page==='documentos'&&S.editor){e.preventDefault();await saveEditor();}}));window.addEventListener('beforeunload',e=>{if(S.editorDirty||S.chatUnsaved){e.preventDefault();e.returnValue='';}});window.addEventListener('hashchange',()=>{const page=location.hash.slice(1);if(['chat','investigacion','monitores','biblioteca','firmas','asuntos','tablas','documentos','ajustes',...V5_PAGES].includes(page)&&S.page!==page)setPage(page);});}
async function init(){initEvents();try{const{client}=await MemAuth.init();S.client=client;const result=await client.auth.getSession();if(result.error)throw result.error;if(!result.data?.session){location.replace('/login?next=/app');return;}S.user=result.data.session.user;await MemAuth.establish(result.data.session);const name=S.user.user_metadata?.full_name||S.user.user_metadata?.name||S.user.email?.split('@')[0]||'Mi despacho';$('#user-name').textContent=name;$('#user-email').textContent=S.user.email||'Sesión autenticada';$('#avatar').textContent=name.split(/\s+/).slice(0,2).map(n=>n[0]).join('').toUpperCase();client.auth.onAuthStateChange((event,session)=>{if(event==='SIGNED_OUT'){v5StopRequests();S.items=[];S.messages=[];S.editor=null;location.replace('/login');}else if(session?.user?.id&&session.user.id!==S.user?.id){location.reload();}});const page=location.hash.slice(1);if(['chat','investigacion','monitores','biblioteca','firmas','asuntos','tablas','documentos','ajustes',...V5_PAGES].includes(page))S.page=page;if(S.page==='investigacion')S.mode='research';try{S.caps=await api('/capabilities');}catch(error){S.loadError=error.message;}try{await refresh({silent:true});}catch(error){S.loadError=error.message;}S.loading=false;render();if(S.page==='firmas'&&(!S.caps?.signatures_v5||V5.signatureView==='legacy'))loadSignatures();v5PageLoad(S.page);}catch(error){S.loading=false;$('#main').replaceChildren(el('section',{class:'boot-state'},icon('lock'),el('h1',{},'No pudimos abrir tu despacho'),el('p',{},MemAuth.message(error)),el('div',{class:'actions'},el('a',{href:'/login?next=/app',class:'button primary'},'Iniciar sesión'),button('Reintentar',()=>location.reload()))));}}
/* Despacho V5: flujos persistidos, conexiones y evidencia. Sin sesiones simuladas. */
const V5 = {
  jobs: [], job: null, schedules: [], agentStatus: null, providers: [], connections: [],
  envelopes: [], rooms: [], roomsOffset: 0, roomsHasMore: false, roomsSequence: 0, roomsCaps: null, legalTab: 'research', legalResearch: {query:'', territory:'', result:null}, signatureView: 'verified', knowledgeStatus: null, sources: [],
  results: {documents: null, legal: null}, knowledgeDraft: {documents: '', legal: ''},
  loaded: new Set(), errors: {}, controllers: new Set(), generation: 0, runningJob: null,
  browserUrls: new Set(), searchSequence: 0, resourceSequence: 0, scheduleDirty: false
};
const V5_PAGES = ['encargos', 'tareas', 'conexiones', 'salas'];
const JOB_LABELS = {draft:'Plan por revisar',approved:'Aprobado',running:'En ejecución',waiting_approval:'Requiere tu aprobación',completed:'Completado',failed:'Interrumpido',cancelled:'Cancelado'};
const JOB_TOOLS = {read_documents:'Leer documentos',research:'Investigar fuentes',analyze:'Analizar',draft:'Redactar',timeline:'Preparar cronología',fetch_source:'Consultar una fuente',save_document:'Guardar un escrito',browser_read:'Abrir navegador supervisado'};
function v5Error(key, error) { if (error?.name !== 'AbortError') V5.errors[key] = error?.message || 'No se pudo completar esta operación.'; }
function v5Notice(key) { return V5.errors[key] ? el('div', {class:'callout error',role:'alert'}, V5.errors[key]) : document.createDocumentFragment(); }
function v5Loading(text='Recuperando información…') { return el('div',{class:'v5-loading',role:'status'},el('span',{class:'busy-indicator'},text)); }
function v5StopRequests() {
  V5.generation++;
  for (const c of V5.controllers) c.abort();
  V5.controllers.clear();
  V5.runningJob = null;
}
async function v5api(path, options={}) {
  const c = new AbortController(); V5.controllers.add(c);
  try { return await api(path, {...options, signal:c.signal}); }
  finally { V5.controllers.delete(c); }
}
function v5MergeJob(job) {
  if (!job?.id) throw new Error('La API no devolvió un encargo válido. Actualiza su estado.');
  const index = V5.jobs.findIndex(x=>x.id===job.id);
  if(index<0) V5.jobs.unshift(job); else V5.jobs[index]=job;
  if (!V5.job || V5.job.id === job.id) V5.job=job;
  return job;
}
async function v5PageLoad(page) {
  const generation=V5.generation;
  const settle=async(key, fn)=>{try{await fn();if(generation===V5.generation){delete V5.errors[key];V5.loaded.add(key);}}catch(e){if(generation===V5.generation){v5Error(key,e);V5.loaded.add(key);}}};
  if(page==='encargos') await settle('agent',async()=>{
    const results=await Promise.all([v5api('/agent/jobs'),v5api('/agent/status')]);
    if(generation!==V5.generation)return;
    V5.jobs=results[0].items||[]; V5.agentStatus=results[1];
    if(V5.job)V5.job=V5.jobs.find(j=>j.id===V5.job.id)||V5.job;
  });
  if(page==='tareas') await settle('schedules',async()=>{
    const results=await Promise.all([v5api('/agent/schedules'),v5api('/agent/jobs'),v5api('/agent/status')]);
    if(generation!==V5.generation)return;
    V5.schedules=results[0].items||[];V5.jobs=results[1].items||[];V5.agentStatus=results[2];
  });
  if(page==='conexiones') await settle('connections',async()=>{const result=await v5api('/connections');if(generation!==V5.generation)return;V5.providers=result.providers||[];V5.connections=result.connections||[];});
  if(page==='salas') await settle('rooms',async()=>{const sequence=++V5.roomsSequence;const result=await v5api('/rooms?offset='+V5.roomsOffset+'&limit=20');if(generation===V5.generation&&sequence===V5.roomsSequence){V5.rooms=result.items||result.rooms||[];V5.roomsHasMore=!!result.has_more;V5.roomsCaps=result.capabilities||null;}});
  if(page==='firmas' && V5.signatureView==='verified') await settle('signing',async()=>{const result=await v5api('/signing');if(generation===V5.generation)V5.envelopes=result.envelopes||[];});
  if(['biblioteca','investigacion'].includes(page)) await settle('knowledge',async()=>{
    const result=await v5api('/knowledge/status');if(generation===V5.generation)V5.knowledgeStatus=result;
  });
  if(generation===V5.generation && S.page===page)render();
}
function v5Segment(label, body, actions=[]) { return el('section',{class:'v5-section'},el('div',{class:'section-heading'},el('h2',{},label),el('div',{class:'actions'},actions)),body); }
function v5ContextDocs(selected = new Set(S.selectedDocs)) {
  const box=el('div',{class:'checklist v5-doc-list'});
  const docs=byKind('document');
  for(const doc of docs){const input=el('input',{type:'checkbox',checked:selected.has(doc.id)});input.addEventListener('change',()=>input.checked?selected.add(doc.id):selected.delete(doc.id));box.append(el('label',{class:'check-row'},input,el('span',{},doc.title,el('small',{},matterTitle(doc.matter_id)))));}
  if(!docs.length)box.append(el('p',{class:'inline-help'},'Tu biblioteca todavía no contiene documentos. Puedes crear un encargo sin adjuntos o cargar archivos en DMS.'));
  return {box,selected};
}
function v5CreateJob() {
  captureDrafts();
  const objective=field('Objetivo del encargo',{type:'textarea',value:S.chatDraft,required:true,placeholder:'Describe el resultado que necesitas, el contexto y las restricciones.',rows:5});objective.input.maxLength=12000;
  const matter=field('Asunto del plan',{value:S.matterId,options:matterOptions()});
  const urls=field('Páginas autorizadas para este encargo',{type:'textarea',help:'Una URL HTTPS por línea. Autoriza solamente las páginas necesarias. No incluyas contraseñas ni enlaces con claves.',rows:3});
  const docs=v5ContextDocs();
  formModal('Planificar un encargo',[objective,matter,urls],async()=>{
    if(docs.selected.size>20)throw new Error('Selecciona como máximo 20 documentos.');
    const allowed_urls=urls.input.value.split('\n').map(s=>s.trim()).filter(Boolean);
    if(allowed_urls.length>8 || allowed_urls.some(url=>!safeUrl(url)))throw new Error('Indica hasta ocho páginas HTTPS válidas.');
    const job=await v5api('/agent/jobs',{method:'POST',body:{objective:objective.input.value.trim(),document_ids:[...docs.selected],matter_id:matter.input.value||null,playbook_id:S.playbookId||null,allowed_urls}});
    v5MergeJob(job);V5.job=job;V5.loaded.add('agent');setPage('encargos');toast('Plan preparado. Revisa sus pasos antes de aprobarlo.');
  },{label:'Preparar plan con IA',wide:true,extra:el('div',{},el('div',{class:'callout'},'La IA propondrá un plan. Los pasos se ejecutan después de tu aprobación; las acciones sobre páginas externas requieren aprobación adicional.'),el('h3',{},'Documentos del encargo'),docs.box)});
}
function v5JobCard(job) {
  return button('',()=>{V5.job=job;render();},{class:'v5-job-card '+(V5.job?.id===job.id?'selected':'')}).appendChild(el('div',{},
    el('div',{class:'v5-job-title'},el('strong',{},job.title||job.objective),badge(JOB_LABELS[job.state]||job.state,job.state==='completed'?'':job.state==='failed'?'error':'pending')),
    el('small',{},shortDate(job.updated_at,true)+' · '+Math.min(Number(job.cursor)||0,job.plan?.length||0)+' de '+(job.plan?.length||0)+' pasos'))).parentElement;
}
function renderJobsV5() {
  const page=el('section',{class:'page v5-workspace'});
  page.append(pageHeader('Encargos por etapas','Define el objetivo, revisa el plan y conserva el resultado de cada paso.',[button('Actualizar encargos',()=>v5PageLoad('encargos'),{icon:'history'}),button('Nuevo plan',v5CreateJob,{icon:'plus',class:'button primary'})],'AGENTE JURÍDICO'));
  page.append(v5Notice('agent'));
  if(!V5.loaded.has('agent')){page.append(v5Loading());return page;}
  if(V5.agentStatus?.configured===false)page.append(el('div',{class:'callout warning'},'El agente necesita un proveedor de IA y sus tablas configuradas en el servidor. Las operaciones comprobarán su disponibilidad al ejecutarse.'));
  const list=el('aside',{class:'v5-job-list','aria-label':'Encargos guardados'},...V5.jobs.map(v5JobCard));
  if(!V5.jobs.length){page.append(empty('Un objetivo, un plan revisable','Prepara un plan con los documentos del asunto y las fuentes autorizadas. Tendrás control sobre la ejecución.',button('Crear primer plan',v5CreateJob,{class:'button primary',icon:'spark'}),'spark'));return page;}
  const selected=V5.job||V5.jobs[0];V5.job=selected;
  page.append(el('div',{class:'v5-workgrid'},list,v5JobDetail(selected)));
  return page;
}
function v5JobDetail(job) {
  const running=V5.runningJob===job.id;
  const box=el('article',{class:'v5-job-detail','aria-label':'Detalle del encargo'});
  box.append(el('div',{class:'v5-detail-header'},el('div',{},badge(JOB_LABELS[job.state]||job.state,job.state==='completed'?'':'pending'),el('h2',{},job.title||'Encargo jurídico')),button('Actualizar estado',async()=>{v5MergeJob(await v5api('/agent/jobs/'+job.id));render();},{icon:'history',class:'button small'})),el('p',{class:'v5-objective'},job.objective));
  if(job.last_error)box.append(el('div',{class:'callout error',role:'alert'},job.last_error));
  const controls=el('div',{class:'actions v5-job-actions'});
  if(job.state==='draft')controls.append(button('Editar plan',()=>v5EditPlan(job),{icon:'edit'}),button('Aprobar plan',()=>v5ApprovePlan(job),{icon:'check',class:'button primary'}));
  if(['approved','running'].includes(job.state))controls.append(button('Ejecutar siguiente paso',()=>v5Run(job,false),{icon:'arrow',disabled:running}),button(running?'Ejecutando…':'Ejecutar plan',()=>v5Run(job,true),{icon:'spark',class:'button primary',disabled:running}));
  if(job.state==='failed')controls.append(button('Reintentar paso',async()=>{v5MergeJob(await v5api('/agent/jobs/'+job.id+'/retry',{method:'POST',body:{expected_version:job.version}}));render();},{icon:'history',class:'button primary'}));
  if(['approved','running','waiting_approval','failed','draft'].includes(job.state))controls.append(button('Cancelar encargo',()=>confirmDialog('Cancelar encargo','Los pasos ya completados y sus evidencias se conservarán. Se detendrá la continuación de este encargo.',async()=>{const latest=await v5api('/agent/jobs/'+job.id);v5MergeJob(await v5api('/agent/jobs/'+job.id+'/cancel',{method:'POST',body:{expected_version:latest.version}}));V5.runningJob=null;render();},'Cancelar encargo'),{icon:'close',class:'button danger'}));
  if(['approved','completed'].includes(job.state))controls.append(button('Programar repetición',()=>v5ScheduleForm(job),{icon:'calendar',disabled:running}));
  controls.append(button('Registro de actividad',()=>v5JobEvents(job),{icon:'history'}));
  if((job.plan||[]).some(s=>s.tool==='browser_read'))controls.append(button('Navegador del encargo',()=>v5Browser(job),{icon:'external'}));
  box.append(controls);
  if(running)box.append(v5Loading('Ejecutando el paso autorizado. El resultado se guardará en este encargo…'));
  if(job.state==='waiting_approval')box.append(el('div',{class:'callout warning'},'La ejecución necesita una decisión tuya. Abre el navegador del encargo y revisa la acción propuesta.'));
  const steps=el('ol',{class:'v5-plan-list'});
  for(const [i,step] of (job.plan||[]).entries()){
    const result=(job.results||[]).find(r=>r.step_id===step.id);
    const completed=i<(Number(job.cursor)||0);
    const node=el('li',{class:'v5-plan-step '+(completed?'done':i===job.cursor?'current':'')},el('span',{class:'v5-step-number','aria-hidden':'true'},completed?'✓':i+1),el('div',{class:'v5-step-content'},el('div',{class:'v5-step-heading'},el('h3',{},step.title||JOB_TOOLS[step.tool]||'Paso'),badge(completed?'Completado':i===job.cursor&&running?'En ejecución':'Pendiente',completed?'':'neutral')),el('span',{class:'source-meta'},JOB_TOOLS[step.tool]||step.tool),el('p',{},step.instruction),step.url?link(step.url,step.url,'v5-url'):null));
    if(result)node.lastChild.append(v5StepResult(result));
    steps.append(node);
  }
  box.append(steps);
  return box;
}
function v5StepResult(entry) {
  const result=entry.result||{}, details=el('details',{class:'v5-step-result'},el('summary',{},'Resultado y evidencias'));
  if(typeof result==='string')details.append(plainRich(result));
  else {
    const answer=result.answer||result.text||result.content||result.summary;
    if(answer)details.append(plainRich(answer));
    if(result.document_id)details.append(button('Abrir documento guardado',async()=>{const d=mergeItem(await v5api('/items/'+encodeURIComponent(result.document_id)));previewDocument(d);},{icon:'file',class:'button small'}));
    if(result.document?.id)details.append(button('Abrir documento guardado',()=>previewDocument(mergeItem(result.document)),{icon:'file',class:'button small'}));
    if(Array.isArray(result.documents))for(const doc of result.documents)details.append(el('div',{class:'v5-evidence'},el('strong',{},doc.title||'Documento'),el('p',{},doc.excerpt||doc.text||doc.summary||'')));
    if(result.url)details.append(link('Abrir fuente',result.url));
    if(result.sources?.length)details.append(el('div',{class:'sources-list'},result.sources.map(sourceCard)));
    for(const warning of result.warnings||[])details.append(el('div',{class:'message-note'},text(warning)));
    if(result.coverage)details.append(v5Coverage(result.coverage));
    if(!answer&&!result.documents?.length&&!result.document_id&&!result.document?.id&&!result.sources?.length)details.append(el('pre',{class:'v5-json-evidence'},JSON.stringify(result,null,2)));
  }
  return details;
}
function v5EditPlan(job) {
  let steps=(job.plan||[]).map(s=>({...s}));
  const container=el('div',{class:'v5-plan-editor'}), err=el('div',{class:'form-error',hidden:true,role:'alert'});
  const form=el('form',{},err,el('p',{class:'inline-help'},'Ajusta las instrucciones y el orden. Cambiar el plan exige una nueva aprobación.'),container);
  function redraw(){container.replaceChildren(...steps.map((step,i)=>{
    const title=field('Título del paso '+(i+1),{value:step.title,required:true});
    const tool=field('Operación del paso '+(i+1),{value:step.tool,options:Object.entries(JOB_TOOLS).map(([value,label])=>({value,label}))});
    const instruction=field('Instrucciones del paso '+(i+1),{value:step.instruction,type:'textarea',required:true,rows:3});
    const url=field('Fuente del paso '+(i+1),{value:step.url||'',type:'url',help:'Para consultar páginas, utiliza una URL autorizada en este encargo.'});
    title.input.addEventListener('input',()=>step.title=title.input.value);tool.input.addEventListener('change',()=>step.tool=tool.input.value);instruction.input.addEventListener('input',()=>step.instruction=instruction.input.value);url.input.addEventListener('input',()=>step.url=url.input.value);
    return el('fieldset',{class:'v5-plan-fieldset'},el('legend',{},'Paso '+(i+1)),el('div',{class:'v5-two-fields'},title.wrap,tool.wrap),instruction.wrap,url.wrap,el('div',{class:'actions'},button('Subir',()=>{[steps[i-1],steps[i]]=[steps[i],steps[i-1]];redraw();},{disabled:i===0,class:'button small'}),button('Bajar',()=>{[steps[i+1],steps[i]]=[steps[i],steps[i+1]];redraw();},{disabled:i===steps.length-1,class:'button small'}),button('Quitar paso',()=>{steps.splice(i,1);redraw();},{disabled:steps.length===1,class:'button small danger'})));
  }));}
  redraw();
  const save=button('Guardar plan',()=>form.requestSubmit(),{class:'button primary',icon:'check'});
  form.addEventListener('submit',async event=>{event.preventDefault();err.hidden=true;await busy(save,async()=>{try{const payload=steps.map(({tool,title,instruction,url})=>({tool,title,instruction,...(url?{url}:{})}));const updated=await v5api('/agent/jobs/'+job.id+'/plan',{method:'PATCH',body:{expected_version:job.version,steps:payload}});v5MergeJob(updated);closeModal();render();}catch(e){err.textContent=e.message;err.hidden=false;}});});
  showModal('Editar plan de trabajo',form,[button('Añadir paso',()=>{if(steps.length>=12)throw new Error('El plan admite hasta 12 pasos.');steps.push({tool:'analyze',title:'Nuevo paso',instruction:''});redraw();},{icon:'plus'}),button('Cancelar',closeModal),save],true);
}
function v5ApprovePlan(job) {
  return confirmDialog('Aprobar este plan','Se autorizarán los '+(job.plan?.length||0)+' pasos mostrados. Las acciones externas del navegador se revisan por separado. El consumo de IA dependerá de los pasos ejecutados.',async()=>{v5MergeJob(await v5api('/agent/jobs/'+job.id+'/approve',{method:'POST',body:{expected_version:job.version}}));render();toast('Plan aprobado. Ya puedes ejecutarlo.');},'Aprobar plan');
}
async function v5Run(initial, all) {
  if(V5.runningJob)return;
  const generation=V5.generation;V5.runningJob=initial.id;render();let job=initial;
  try{let guard=0;do{job=await v5api('/agent/jobs/'+job.id+'/step',{method:'POST',body:{expected_version:job.version}});if(generation!==V5.generation)return;v5MergeJob(job);render();guard++;}while(all&&guard<16&&['approved','running'].includes(job.state)&&job.cursor<(job.plan||[]).length);}
  catch(error){if(error?.name!=='AbortError'){toast(error.message,'error');try{v5MergeJob(await v5api('/agent/jobs/'+initial.id));}catch{}}}
  finally{if(generation===V5.generation){V5.runningJob=null;render();}}
}
async function v5JobEvents(job) {
  const result=await v5api('/agent/jobs/'+job.id+'/events');
  showModal('Actividad del encargo',el('div',{class:'timeline'},...(result.items||[]).map(event=>el('article',{class:'timeline-item'},el('time',{},shortDate(event.at,true)),el('h3',{},event.event),el('p',{},text(event.detail))))),[button('Cerrar',closeModal)],true);
}
async function v5Browser(job) {
  const data=await v5api('/agent/jobs/'+job.id+'/browser');
  const content=el('div',{class:'v5-browser-panel'},el('div',{class:'callout'},V5.agentStatus?.browser?.takeover_supported?'El agente requiere aprobación para cada acción. Para iniciar sesión o realizar una operación sensible, toma el control manual: el agente queda pausado mientras actúas.':'Revisa la página y el destino antes de actuar. Este navegador consulta fuentes públicas y no admite credenciales, CAPTCHAs, pagos ni trámites vinculantes.'),el('h3',{},data.title||'Navegador del encargo'),data.url?link(data.url,data.url,'v5-url'):null);
  if(!data.active)content.append(el('p',{class:'inline-help'},data.message||'Todavía no hay una página abierta. Ejecuta primero el paso de navegación del plan.'));
  if(data.text)content.append(el('div',{class:'document-preview v5-browser-text'},data.text));
  if(data.blocked_page)content.append(el('div',{class:'callout warning'},data.message||'Esta página requiere una operación que el navegador de fuentes públicas no admite.'));
  if(!data.active && ['approved','running','completed','waiting_approval'].includes(job.state)){for(const step of (job.plan||[]).filter(s=>s.tool==='browser_read'&&s.url))content.append(button('Abrir '+(step.title||'fuente autorizada'),async()=>{await v5api('/agent/jobs/'+job.id+'/browser/open',{method:'POST',body:{url:step.url}});await v5Browser(job);},{icon:'external'}));}
  if(data.pending_action)content.append(button('Revisar acción pendiente',()=>v5ConfirmBrowser(job,data.pending_action),{class:'button primary',icon:'check'}));
  if(data.manual)content.append(el('div',{class:'callout'},data.message||'El navegador está bajo tu control. El agente no observa ni actúa hasta que reanudes la supervisión.'),button('Cerré la ventana de control y terminé',async()=>{await v5api('/agent/jobs/'+job.id+'/browser/resume',{method:'POST',body:{}});const latest=await v5api('/agent/jobs/'+job.id);v5MergeJob(latest);render();await v5Browser(latest);},{class:'button primary',icon:'check'}));
  if(data.active&&!data.manual&&V5.agentStatus?.browser?.takeover_supported)content.append(button('Tomar control manual',()=>v5BrowserTakeover(job),{icon:'external'}));
  if(data.active)content.append(button('Descargas del navegador',()=>v5BrowserDownloads(job),{icon:'download'}));
  if(data.active&&!data.blocked_page&&!data.manual){
    const screenshot=button('Ver captura de la página',async e=>busy(e.currentTarget,async()=>{const blob=await v5api('/agent/jobs/'+job.id+'/browser/screenshot',{blob:true});const u=URL.createObjectURL(blob);V5.browserUrls.add(u);const image=el('img',{src:u,alt:'Estado del navegador del encargo',class:'v5-browser-screenshot'});content.append(image);}),{icon:'eye'});content.append(screenshot);
    const safeControls=(data.controls||[]).filter(c=>!c.blocked&&!c.disabled&&!['password','hidden'].includes(String(c.field_type).toLowerCase()));
    const target=field('Control de la página',{options:safeControls.map(c=>({value:c.ref,label:(c.name||c.role||c.tag||'Control')+' · '+c.ref}))});
    const action=field('Acción que deseas proponer',{options:[{value:'click',label:'Hacer clic'},{value:'fill',label:'Escribir en un campo'}]});
    const value=field('Texto para el campo',{type:'textarea',rows:3,help:'Se enviará exactamente este texto al destino mostrado cuando apruebes la acción.'});
    if(safeControls.length)content.append(v5Segment('Acción supervisada',el('div',{},target.wrap,action.wrap,value.wrap),[button('Revisar acción',async()=>{const proposal=await v5api('/agent/jobs/'+job.id+'/browser/propose',{method:'POST',body:{action:action.input.value,ref:target.input.value,...(action.input.value==='fill'?{value:value.input.value}:{})}});v5ConfirmBrowser(job,proposal);},{icon:'check',class:'button primary'})]));
    else content.append(el('p',{class:'inline-help'},'No se encontraron controles utilizables en esta página.'));
  }
  showModal('Navegador supervisado',content,[button('Cerrar ventana',closeModal),button('Actualizar página visible',()=>v5Browser(job),{icon:'history'}),data.active?button('Finalizar navegador',async()=>{const result=await v5api('/agent/jobs/'+job.id+'/browser/close',{method:'POST'});if(result.job)v5MergeJob(result.job);closeModal();render();toast('Navegador del encargo cerrado.');},{class:'button danger'}):null].filter(Boolean),true);
}
async function v5BrowserTakeover(job) {
  const result=await v5api('/agent/jobs/'+job.id+'/browser/takeover',{method:'POST',body:{}});
  v5MergeJob(await v5api('/agent/jobs/'+job.id));render();const url=safeUrl(result.takeover_url);if(!url)throw new Error('No se recibió una dirección válida para el control manual.');
  showModal('Control manual del navegador',el('div',{},el('div',{class:'callout'},result.message||'El agente queda pausado mientras controlas el navegador. Introduce tus credenciales y realiza las acciones sensibles directamente en la sesión remota.'),el('p',{class:'inline-help'},'El enlace es temporal y privado. Ábrelo ahora; no lo compartas.'),el('a',{href:url,target:'_blank',rel:'noopener noreferrer',referrerPolicy:'no-referrer',class:'button primary'},'Abrir navegador bajo mi control')),[button('Volver al encargo',closeModal),button('Cerré la ventana de control y terminé',async()=>{await v5api('/agent/jobs/'+job.id+'/browser/resume',{method:'POST',body:{}});const latest=await v5api('/agent/jobs/'+job.id);v5MergeJob(latest);render();await v5Browser(latest);},{icon:'check'})],true);
}
async function v5BrowserDownloads(job) {
  const result=await v5api('/agent/jobs/'+job.id+'/browser/downloads');
  const list=el('div',{class:'item-list'});
  for(const file of result.items||[])list.append(el('article',{class:'list-row'},icon('file'),el('div',{class:'row-main'},el('strong',{},file.filename),el('small',{},file.size?Math.ceil(file.size/1024)+' KB':'')),el('div',{class:'row-actions'},
    button('Descargar archivo',async()=>{const blob=await v5api('/agent/jobs/'+job.id+'/browser/downloads/'+encodeURIComponent(file.id),{blob:true});downloadBlob(blob,file.filename||'documento');},{icon:'download',class:'button small'}),
    button('Guardar en DMS',async e=>busy(e.currentTarget,async()=>{const result=await v5api('/agent/jobs/'+job.id+'/browser/downloads/'+encodeURIComponent(file.id)+'/save',{method:'POST',body:{}});if(result.item)mergeItem(result.item);else if(result.document)mergeItem(result.document);else if(result.id)mergeItem(result);toast('Copia guardada en la biblioteca.');}),{icon:'file',class:'button small'}))));
  if(!(result.items||[]).length)list.append(el('p',{class:'inline-help'},'No hay descargas disponibles en esta sesión.'));
  showModal('Descargas del navegador',list,[button('Cerrar',closeModal),button('Volver al navegador',()=>v5Browser(job))],true);
}

function v5ConfirmBrowser(job, proposal) {
  const body=el('div',{},el('div',{class:'callout warning'},'Esta acción interactuará con una página externa. Comprueba el destino y el contenido exacto.'),el('dl',{class:'detail-kv'},el('dt',{},'Destino'),el('dd',{},proposal.url||'Sin destino informado'),el('dt',{},'Acción'),el('dd',{},proposal.action==='fill'?'Escribir texto':'Hacer clic'),el('dt',{},'Control'),el('dd',{},proposal.label||proposal.ref),el('dt',{},'Texto'),el('dd',{class:'v5-prewrap'},proposal.value||'No aplica')));
  const approve=button('Aprobar esta acción',async e=>busy(e.currentTarget,async()=>{const latest=await v5api('/agent/jobs/'+job.id);const result=await v5api('/agent/jobs/'+job.id+'/browser/approve',{method:'POST',body:{action_id:proposal.action_id,expected_version:latest.version}});if(result.job)v5MergeJob(result.job);await v5Browser(result.job||latest);}),{class:'button primary',icon:'check'});
  showModal('Confirmar acción externa',body,[button('No ejecutar',closeModal),approve],true);
}
function renderSchedulesV5() {
  const page=el('section',{class:'page'});page.append(pageHeader('Tareas programadas','Repite un plan aprobado y revisa cada ejecución desde tu despacho.',[button('Actualizar tareas',()=>v5PageLoad('tareas'),{icon:'history'}),button('Programar tarea',()=>v5ScheduleForm(),{icon:'calendar',class:'button primary'})]));
  page.append(v5Notice('schedules'));
  if(!V5.loaded.has('schedules')){page.append(v5Loading());return page;}
  page.append(el('div',{class:'callout'},V5.agentStatus?.worker_enabled?'El trabajador de tareas está habilitado. Las últimas ejecuciones y sus errores se muestran en cada tarea.':'La programación necesita un trabajador activo en el servidor. Puedes guardar tareas, pero no se ejecutarán automáticamente hasta habilitarlo.'));
  if(!V5.schedules.length)page.append(empty('Trabajo recurrente, con un plan definido','Aprueba un plan en Encargos por etapas y programa su repetición.',button('Ver mis encargos',()=>setPage('encargos'),{class:'button primary'}),'calendar'));
  else page.append(el('div',{class:'grid'},V5.schedules.map(schedule=>el('article',{class:'card'},el('div',{class:'card-head'},icon('calendar'),badge(schedule.enabled?'Activa':'Pausada',schedule.enabled?'':'neutral')),el('h3',{},schedule.title||V5.jobs.find(j=>j.id===schedule.job_id)?.title||'Tarea programada'),el('p',{},'Cada '+schedule.interval_minutes+' minutos'),el('p',{class:'inline-help'},'Próxima ejecución: '+shortDate(schedule.next_run_at,true)),el('p',{class:'inline-help'},'Última ejecución: '+shortDate(schedule.last_run_at,true)),schedule.last_error?el('div',{class:'callout error'},schedule.last_error):null,el('div',{class:'actions'},button('Editar frecuencia',()=>v5ScheduleForm(null,schedule),{icon:'edit',class:'button small'}),button(schedule.enabled?'Pausar tarea':'Activar tarea',async()=>{await v5api('/agent/schedules/'+schedule.id,{method:'PATCH',body:{expected_version:schedule.version,enabled:!schedule.enabled}});await v5PageLoad('tareas');},{class:'button small'}),schedule.last_job_id?button('Ver última ejecución',async()=>{const job=await v5api('/agent/jobs/'+schedule.last_job_id);v5MergeJob(job);V5.job=job;setPage('encargos');},{class:'button small'}):null)))));
  return page;
}
function v5ScheduleForm(job, existing) {
  const candidates=V5.jobs.filter(j=>['approved','completed'].includes(j.state)&&!(j.plan||[]).some(s=>s.tool==='browser_read'));
  const select=field('Plan aprobado',{value:existing?.job_id||job?.id||'',options:[{value:'',label:'Selecciona un plan'},...candidates.map(j=>({value:j.id,label:j.title||j.objective}))],required:true});
  if(existing)select.input.disabled=true;
  const interval=field('Repetir cada (minutos)',{type:'number',value:existing?.interval_minutes||1440,min:60,max:10080,required:true,help:'Entre una hora y una semana. Se repetirá el mismo plan aprobado.'});
  const next=field('Primera ejecución (hora local)',{type:'datetime-local',help:'Déjalo vacío para utilizar la fecha calculada por el servidor.'});
  formModal(existing?'Editar tarea programada':'Programar un plan',[select,interval,next],async()=>{
    if(!existing&&!select.input.value)throw new Error('Selecciona un plan aprobado sin pasos de navegador.');
    const next_run_at=next.input.value?new Date(next.input.value).toISOString():undefined;
    const body=existing?{expected_version:existing.version,interval_minutes:Number(interval.input.value),...(next_run_at?{next_run_at}:{})}:{job_id:select.input.value,interval_minutes:Number(interval.input.value),enabled:true,...(next_run_at?{next_run_at}:{})};
    await v5api('/agent/schedules'+(existing?'/'+existing.id:''),{method:existing?'PATCH':'POST',body});setPage('tareas');toast('Programación guardada. Comprueba el estado del trabajador.');
  },{label:'Guardar programación',extra:el('div',{class:'callout'},'Las tareas programadas pueden leer, investigar, analizar y guardar resultados. Los pasos de navegador requieren supervisión y no se programan.')});
}
function renderConnectionsV5() {
  const page=el('section',{class:'page'});page.append(pageHeader('Conexiones','Importa documentos y correspondencia desde las cuentas que autorices.',[button('Actualizar conexiones',()=>v5PageLoad('conexiones'),{icon:'history'})]));
  page.append(v5Notice('connections'));
  if(!V5.loaded.has('connections')){page.append(v5Loading());return page;}
  page.append(el('div',{class:'callout'},'Cada conexión solicita permisos de lectura. Los documentos se importan a tu cuenta de El Memorialista cuando los seleccionas. Puedes desconectar una cuenta en cualquier momento.'));
  if(!V5.providers.length)page.append(el('p',{class:'inline-help'},'La API no devolvió proveedores disponibles. Revisa la configuración del servidor.'));
  const providers=el('div',{class:'connection-grid'});
  for(const provider of V5.providers){
    const connected=V5.connections.filter(c=>c.provider===provider.id);
    const connectButton=button(connected.length?'Conectar otra cuenta':'Conectar cuenta',async e=>busy(e.currentTarget,async()=>{
      const result=await v5api('/connections/'+encodeURIComponent(provider.id)+'/authorize',{method:'POST',body:{}});
      const url=safeUrl(result.authorization_url);if(!url)throw new Error('El proveedor no devolvió un enlace de autorización válido.');location.assign(url);
    }),{icon:'link',class:'button primary',disabled:!provider.configured});
    const card=el('article',{class:'connection-card'},
      el('div',{class:'v5-card-heading'},icon('link'),el('h2',{},provider.label||provider.id)),
      badge(provider.configured?'Aplicación OAuth configurada':'Configuración pendiente',provider.configured?'neutral':'pending'),
      el('p',{},provider.configured?'Autoriza una cuenta para listar e importar su contenido. La conexión se comprueba al consultar el proveedor.':provider.message||'El administrador debe configurar la aplicación OAuth y su dirección de retorno.'),
      provider.scopes?.length?el('details',{},el('summary',{},'Permisos solicitados'),el('ul',{class:'v5-scopes'},provider.scopes.map(s=>el('li',{},s)))):null,
      el('div',{class:'actions'},connectButton));
    for(const connection of connected){
      const disconnect=()=>confirmDialog('Desconectar cuenta','Se retirarán las credenciales de esta conexión. Los documentos ya importados permanecerán en tu biblioteca.',async()=>{
        const result=await v5api('/connections/'+connection.id,{method:'DELETE'});await v5PageLoad('conexiones');
        if(result.warnings?.length)toast(result.warnings.join('\n'),'error');else toast('Conexión retirada.');
      },'Desconectar');
      card.append(el('div',{class:'v5-connected-account'},el('strong',{},connection.label||'Cuenta autorizada'),el('small',{},'Conectada '+shortDate(connection.created_at)),
        el('div',{class:'actions'},button('Explorar archivos',()=>v5BrowseConnection(connection),{icon:'folder',class:'button small'}),button('Desconectar',disconnect,{class:'button small danger'}))));
    }
    providers.append(card);
  }
  page.append(providers);return page;
}
async function v5BrowseConnection(connection, resourceOptions={}) {
  const sequence=++V5.resourceSequence;
  const query=new URLSearchParams();for(const[key,value]of Object.entries(resourceOptions))if(value)query.set(key,String(value));
  const result=await v5api('/connections/'+connection.id+'/resources'+(query.size?'?'+query.toString():''));
  if(sequence!==V5.resourceSequence)return;
  const q=field('Buscar en la conexión',{type:'search',value:resourceOptions.q||'',placeholder:'Nombre o contenido admitido por el proveedor'});
  const matter=field('Asunto de destino',{value:S.matterId,options:matterOptions()});
  const resources=el('div',{class:'item-list'});
  for(const resource of result.items||[]){
    const folder=['folder','drive','site'].includes(resource.type);
    resources.append(el('article',{class:'list-row'},icon(folder?'folder':'file'),el('div',{class:'row-main'},el('strong',{},resource.name||resource.id),el('small',{},[resource.type,resource.mime,resource.size?Math.ceil(resource.size/1024)+' KB':''].filter(Boolean).join(' · '))),el('div',{class:'row-actions'},folder?button('Abrir carpeta',()=>v5BrowseConnection(connection,{...resourceOptions,folder_id:resource.type==='folder'?resource.id:undefined,drive_id:resource.type==='drive'?resource.id:resource.drive_id||resourceOptions.drive_id,site_id:resource.type==='site'?resource.id:resource.site_id||resourceOptions.site_id,cursor:undefined,q:undefined}),{class:'button small',icon:'folder'}):button('Importar a DMS',async e=>{const target=e.currentTarget;await busy(target,async()=>{const imported=await v5api('/connections/'+connection.id+'/import',{method:'POST',body:{resource_id:resource.id,...(resource.drive_id?{drive_id:resource.drive_id}:resourceOptions.drive_id?{drive_id:resourceOptions.drive_id}:{}),matter_id:matter.input.value||null}});if(imported.item)mergeItem(imported.item);toast('Documento importado a tu biblioteca.');for(const warning of imported.warnings||[])toast(text(warning),'error');});target.textContent='Importado';target.disabled=true;},{class:'button small',icon:'download'}),resource.web_url?link('Ver original ↗',resource.web_url,'text-button'):null)));
  }
  if(!(result.items||[]).length)resources.append(el('p',{class:'inline-help'},'No se encontraron elementos en esta ubicación.'));
  const search=el('form',{class:'v5-connection-search'},q.wrap,el('button',{type:'submit',class:'button'},'Buscar'));search.addEventListener('submit',act(async event=>{event.preventDefault();await v5BrowseConnection(connection,{...resourceOptions,q:q.input.value,cursor:undefined});}));
  const body=el('div',{},search,matter.wrap,el('p',{class:'inline-help'},'Importar crea una copia en tu biblioteca. No modifica el archivo de origen.'),resources);
  for(const warning of result.warnings||[])body.append(el('div',{class:'callout warning'},text(warning)));
  showModal(connection.label||'Archivos conectados',body,[button('Cerrar',closeModal),Object.keys(resourceOptions).some(k=>['folder_id','drive_id','site_id'].includes(k)&&resourceOptions[k])?button('Volver al inicio',()=>v5BrowseConnection(connection),{icon:'folder'}):null,result.next_cursor?button('Página siguiente',()=>v5BrowseConnection(connection,{...resourceOptions,cursor:result.next_cursor}),{icon:'arrow'}):null].filter(Boolean),true);
}
/* Investigación externa: separada del chat del Agente y de las búsquedas privadas. */
function v5ResearchImport(source, verified) {
  if(!verified || !source.importable)throw new Error('Comprueba primero el documento oficial antes de incorporarlo.');
  const title=field('Título de la fuente',{value:source.title||''});
  const court=field('Corporación o entidad (opcional)');
  const year=field('Año (opcional)',{type:'number',min:1800,max:2200});
  const type=field('Tipo de documento',{options:[{value:'sentencia',label:'Sentencia'},{value:'ley',label:'Ley'},{value:'decreto',label:'Decreto'},{value:'auto',label:'Auto'},{value:'resolucion',label:'Resolución'},{value:'concepto',label:'Concepto'},{value:'otro',label:'Otro'}]});
  formModal('Incorporar fuente comprobada',[title,court,year,type],async()=>{
    const body={url:source.url,title:title.input.value.trim()||source.title,document_type:type.input.value};
    if(court.input.value.trim())body.court=court.input.value.trim();
    if(year.input.value)body.year=Number(year.input.value);
    const result=await v5api('/knowledge/import',{method:'POST',body});
    if(result.item)mergeItem(result.item);
    toast(result.duplicate?'La fuente ya estaba en tu biblioteca.':'Fuente oficial incorporada.');
    for(const warning of result.warnings||[])toast(text(warning),'error');
  },{label:'Guardar en mi biblioteca',extra:el('p',{class:'inline-help'},'Se conserva una copia del original. Debes revisar su vigencia y la pertinencia jurídica; la lectura automática no las acredita.')});
}
async function v5ResearchVerify(source) {
  if(!source.importable)throw new Error('Esta URL no pertenece a los dominios oficiales permitidos en el servidor. Puedes abrirla y revisar el sitio, o incorporar manualmente una dirección oficial admitida.');
  const status=el('div',{role:'status'},v5Loading('Comprobando el documento original…'));
  showModal('Comprobar fuente oficial',status,[button('Cerrar',closeModal)],true);
  try{
    const result=await v5api('/knowledge/verify',{method:'POST',body:{url:source.url}});
    if(!status.isConnected)return;
    status.replaceChildren(el('div',{class:'callout'},result.notice||'Se recuperó texto del documento original.'),
      el('p',{class:'inline-help'},(result.title||source.title)+' · '+(result.text_length||0)+' caracteres recuperados'),
      el('pre',{class:'v5-source-preview'},result.excerpt||''));
    for(const warning of result.warnings||[])status.append(el('div',{class:'callout warning'},text(warning)));
    $('#modal-footer').replaceChildren(button('Cerrar',closeModal),button('Incorporar a mi biblioteca',()=>{closeModal();v5ResearchImport(source,true);},{class:'button primary',icon:'plus'}));
  }catch(error){if(!status.isConnected||error.name==='AbortError')return;status.replaceChildren(el('div',{class:'callout error',role:'alert'},error.message));}
}
function v5LegalResearchPanel() {
  const state=V5.legalResearch;
  const panel=el('section',{class:'v5-knowledge v5-legal-research','aria-label':'Investigar nuevas fuentes jurídicas'});
  panel.append(el('div',{class:'section-heading'},el('h2',{},'Investiga jurisprudencia con IA'),
    el('p',{class:'inline-help'},'Busca en la web con Gemini y revisa las fuentes encontradas antes de guardarlas. No necesitas una biblioteca previamente cargada.')));
  const query=field('Problema jurídico',{type:'textarea',value:state.query,placeholder:'Ej. normas, competencia municipal y jurisprudencia sobre el mantenimiento de las vías de Bucaramanga…',rows:4});
  query.input.maxLength=3000;
  const territory=field('Lugar o jurisdicción (opcional)',{value:state.territory,placeholder:'Ej. Bucaramanga, Santander, Colombia'});
  territory.input.maxLength=120;
  query.input.addEventListener('input',()=>state.query=query.input.value);
  territory.input.addEventListener('input',()=>state.territory=territory.input.value);
  const submit=el('button',{type:'submit',class:'button primary'},icon('search'),'Investigar con fuentes');
  const form=el('form',{class:'v5-knowledge-form'},query.wrap,territory.wrap,
    el('div',{class:'actions'},submit));
  const output=el('div',{class:'v5-external-results','aria-live':'polite'});
  const draw=()=>{
    const result=state.result;output.replaceChildren();if(!result)return;
    output.append(el('div',{class:'v5-search-summary'},el('strong',{},'Resultado de investigación'),badge(result.model||'Gemini','neutral')),
      el('p',{class:'inline-help'},result.coverage||'Las fuentes deben comprobarse individualmente.'),
      el('article',{class:'v5-research-answer'},plainRich(result.answer||'No se recibió un análisis.')),
      el('div',{class:'actions'},button('Copiar análisis',()=>copy(result.answer||''),{icon:'copy',class:'button small'}),
        button('Guardar informe en DMS',async()=>{
          const body=[result.query,'',result.answer,'','Fuentes sugeridas (pendientes de comprobación):',...(result.sources||[]).map(src=>src.title+' — '+src.url)].join('\n');
          const saved=await createItem('document','Investigación jurídica · '+result.query.slice(0,85),
            {text:body,mime:'text/plain',pages:[],pagination:'segments',versions:[],source:'investigacion_externa',review_required:true},'');
          toast('Informe guardado como borrador para revisar.');mergeItem(saved);
        },{icon:'file',class:'button small'})));
    for(const warning of result.warnings||[])output.append(el('div',{class:'callout warning'},text(warning)));
    output.append(el('h3',{},'Fuentes encontradas ('+(result.sources?.length||0)+')'),
      el('p',{class:'inline-help'},'Los enlaces proceden de las referencias del proveedor. Un dominio admitido no significa que el contenido o su vigencia se hayan verificado.'));
    if(!result.sources?.length)output.append(el('div',{class:'callout warning'},'El proveedor no suministró enlaces comprobables. No utilices esta respuesta como jurisprudencia confirmada.'));
    for(const source of result.sources||[]){
      output.append(el('article',{class:'v5-search-hit v5-external-source'},
        el('h3',{},source.title||source.host||'Fuente'),
        el('span',{class:'source-meta'},source.host||''),
        source.support_text?el('p',{class:'v5-excerpt'},source.support_text):null,
        el('p',{class:'inline-help'},source.status||'Documento no comprobado'),
        el('div',{class:'actions'},link('Abrir referencia ↗',source.url,'button small'),
          source.importable?button('Comprobar el original',()=>v5ResearchVerify(source),{class:'button small',icon:'check'}):null)));
    }
    if(result.search_queries?.length)output.append(el('details',{class:'v5-search-queries'},el('summary',{},'Consultas realizadas por el proveedor'),el('ul',{},result.search_queries.map(q=>el('li',{},q)))));
  };
  form.addEventListener('submit',act(async event=>{
    event.preventDefault();const q=query.input.value.trim(),t=territory.input.value.trim();
    if(q.length<12)throw new Error('Describe el problema jurídico con al menos 12 caracteres.');
    state.query=q;state.territory=t;
    await busy(submit,async()=>{output.replaceChildren(v5Loading('Consultando fuentes web con IA…'));try{
      const result=await v5api('/knowledge/research',{method:'POST',body:{query:q,territory:t}});
      state.result=result;draw();
    }catch(error){
      if(error.name!=='AbortError'){
        output.replaceChildren(
          el('div',{class:'callout error',role:'alert'},error.message),
          el('p',{class:'inline-help'},'Tu consulta permanece intacta en el formulario para reintentar cuando lo desees.')
        );
      }
    }});
  }));
  panel.append(form,output);draw();return panel;
}
/* Corpus oficial compartido: explícito, separado de la biblioteca privada. */
function v5OfficialPanel() {
  const wrap=el('section',{class:'v5-knowledge v5-official-panel','aria-label':'Corpus jurídico oficial compartido'});
  const status=el('div',{class:'v5-official-status','aria-live':'polite'},'La cobertura se comprobará al solicitarla.');
  const query=field('Buscar en la base jurídica compartida',{type:'search',placeholder:'Ej. reparación directa, confianza legítima, ambiente sano…'});
  query.input.maxLength=800;
  const results=el('div',{class:'v5-search-results','aria-live':'polite'});
  const submit=el('button',{type:'submit',class:'button primary'},icon('search'),'Buscar en corpus');
  const form=el('form',{class:'v5-knowledge-form'},query.wrap,el('div',{class:'actions'},submit));
  form.addEventListener('submit',act(async e=>{
    e.preventDefault();results.replaceChildren(v5Loading('Buscando exclusivamente en documentos publicados…'));
    await busy(submit,async()=>{try{
      const r=await v5api('/official/search',{method:'POST',body:{query:query.input.value.trim(),semantic:true,limit:15,depth:S.analysisDepth||'auto'}});
      const groupedResults=groupSourcesByDocument(r.results||[],'',{candidates_retrieved:r.results?.length||0,available_passages:r.results?.length||0});
      results.replaceChildren(el('div',{class:'v5-search-summary'},el('strong',{},(r.results?.length||0)+' fragmentos encontrados · '+groupedResults.length+' providencia(s)')),
        el('p',{class:'inline-help'},r.coverage||'La cobertura depende de los documentos realmente publicados.'));
      for(const w of r.warnings||[])results.append(el('div',{class:'callout warning'},text(w)));
      if(!groupedResults.length)results.append(el('div',{class:'callout'},'La colección compartida no contiene fragmentos que coincidan. No se atribuirán sentencias no encontradas.'));
      for(const g of groupedResults)results.append(renderGroupedDocumentCard(g,null,{allowAccordion:true}));
    }catch(error){results.replaceChildren(el('div',{class:'callout error',role:'alert'},error.message));}});
  }));
  const metadataField=field('Consultar metadatos de sentencias de la Corte Constitucional',{type:'search',placeholder:'Ej. T-100/24, ponente, sala o radicado'});
  metadataField.input.maxLength=120;
  const metaResult=el('div',{class:'v5-search-results','aria-live':'polite'});
  const metaBtn=el('button',{type:'submit',class:'button'},'Consultar índice oficial');
  const metaForm=el('form',{class:'v5-knowledge-form'},metadataField.wrap,
    el('div',{class:'actions'},metaBtn));
  metaForm.addEventListener('submit',act(async e=>{
    e.preventDefault();metaResult.replaceChildren(v5Loading('Consultando metadatos oficiales…'));
    await busy(metaBtn,async()=>{try{
      const r=await v5api('/official/constitutional-metadata',{method:'POST',body:{query:metadataField.input.value.trim(),limit:15}});
      metaResult.replaceChildren(el('div',{class:'v5-search-summary'},el('strong',{},(r.items?.length||0)+' registros encontrados')),
        el('p',{class:'inline-help'},r.notice||'Solo datos estadísticos. No es texto completo.'));
      if(!r.items?.length)metaResult.append(el('div',{class:'callout'},'No se encontraron metadatos con ese término. El índice no busca por temas del texto de las sentencias.'));
      for(const x of r.items||[])metaResult.append(el('article',{class:'v5-search-hit'},
        el('h3',{},x.citation),el('p',{class:'inline-help'},[x.date,x.judge,x.chamber].filter(Boolean).join(' · ')),
        el('p',{class:'inline-help'},'Registro oficial de metadatos, sin lectura ni verificación del texto completo.'),
        el('div',{class:'actions'},link('Abrir conjunto público ↗',x.dataset_url,'button small'))));
    }catch(error){metaResult.replaceChildren(el('div',{class:'callout error',role:'alert'},error.message));}});
  }));
  const loadStatus=async()=>{status.replaceChildren(v5Loading('Comprobando cobertura real…'));try{
    const r=await v5api('/official/status');
    status.replaceChildren(el('p',{},'Documentos publicados: '+(r.published_documents??0)+
       ' · Colecciones con documentos: '+(r.published_sources??0)+' · Fragmentos: '+(r.indexed_fragments??0)),
       el('p',{class:'inline-help'},r.note||''));}
    catch(e){status.replaceChildren(el('div',{class:'callout warning'},'La colección compartida aún no está lista: '+e.message));}
  };

  const connectorBox=el('div',{class:'v5-connector-admin'});
  const loadConnectorStatus=async()=>{
    connectorBox.replaceChildren(v5Loading('Consultando estado del conector oficial…'));
    try{
      const c=await v5api('/official/connector/status');
      const grid=el('div',{class:'v5-connector-grid'},
        el('div',{class:'v5-metric-box'},el('div',{class:'v5-metric-num'},String(c.discovered_count||'~29.500')),el('div',{class:'v5-metric-label'},'Descubiertas')),
        el('div',{class:'v5-metric-box'},el('div',{class:'v5-metric-num'},String(c.retrieved_count||0)),el('div',{class:'v5-metric-label'},'Recuperadas')),
        el('div',{class:'v5-metric-box'},el('div',{class:'v5-metric-num'},String(c.published_count||0)),el('div',{class:'v5-metric-label'},'Publicadas')),
        el('div',{class:'v5-metric-box'},el('div',{class:'v5-metric-num'},String(c.pending_review_count||0)),el('div',{class:'v5-metric-label'},'Pendientes')),
        el('div',{class:'v5-metric-box'},el('div',{class:'v5-metric-num'},String(c.rejected_count||0)),el('div',{class:'v5-metric-label'},'Rechazadas')),
        el('div',{class:'v5-metric-box'},el('div',{class:'v5-metric-num'},String(c.fragments_count||0)),el('div',{class:'v5-metric-label'},'Fragmentos')),
        el('div',{class:'v5-metric-box'},el('div',{class:'v5-metric-num'},String(c.embeddings_count||0)),el('div',{class:'v5-metric-label'},'Embeddings 768d')),
        el('div',{class:'v5-metric-box'},el('div',{class:'v5-metric-num'},'$'+(c.estimated_cost_usd||0)),el('div',{class:'v5-metric-label'},'Coste est. USD'))
      );
      const header=el('div',{class:'v5-connector-header'},
        el('div',{},
          el('strong',{},'⚙️ Conector Oficial · Corte Constitucional (v2k4-2t8s) — Actualización Incremental'),
          el('p',{class:'inline-help'},`Estado: ${(c.status||'idle').toUpperCase()} · Fuente: datos.gov.co + Relatoría · Última sinc: ${c.last_sync_at?new Date(c.last_sync_at).toLocaleString():'Pendiente'}`)
        )
      );
      const pilotBtn=button('Iniciar Piloto (20 Sentencias)',async()=>{
        await busy(pilotBtn,async()=>{
          toast('Iniciando piloto de incorporación de sentencias oficiales...');
          try{
            const res=await v5api('/official/connector/pilot',{method:'POST',body:{max_rulings:20,semantic:true}});
            toast(`✓ Piloto completado: ${res.published_count} publicadas, ${res.unchanged_count} sin cambios`);
            await loadConnectorStatus();
            await loadStatus();
          }catch(err){toast('Error ejecutando piloto: '+err.message);}
        });
      },{class:'button small primary'});
      const syncBtn=button('Sincronización incremental',async()=>{
        await busy(syncBtn,async()=>{
          toast('Verificando actualizaciones incrementales...');
          try{
            const res=await v5api('/official/connector/sync',{method:'POST',body:{max_rulings:20,semantic:true}});
            toast(`✓ Sincronización completada: ${res.published_count} nuevas, ${res.unchanged_count} idénticas`);
            await loadConnectorStatus();
            await loadStatus();
          }catch(err){toast('Error en sincronización: '+err.message);}
        });
      },{class:'button small'});
      const actions=el('div',{class:'v5-connector-actions'},pilotBtn,syncBtn);
      connectorBox.replaceChildren(header,grid,actions);
    }catch(err){
      connectorBox.replaceChildren(el('div',{class:'callout warning'},'Panel de conector no disponible: '+err.message));
    }
  };
  loadConnectorStatus();
  const showCatalog=async()=>{
    const body=el('div',{},v5Loading('Consultando el directorio de colecciones…'));
    showModal('Directorio de fuentes jurídicas',body,[button('Cerrar',closeModal)],true);
    try{const r=await v5api('/official/sources');if(!body.isConnected)return;
      body.replaceChildren(el('p',{class:'inline-help'},r.notice||'Fuentes planificadas, no corpus descargado.'),
        el('p',{},'Colecciones catalogadas: '+(r.listed??0)+' · Conectores de metadatos: '+(r.metadata_connectors??0)));
      for(const x of r.sources||[])body.append(el('article',{class:'list-row v5-official-row'},
        el('div',{class:'row-main'},el('strong',{},x.name),el('small',{},x.category+' · '+
          (x.access==='metadata_api'?'Consulta de metadatos habilitada':x.access==='portal_manual'?'Portal de referencia':'Pendiente de evaluación')),
          el('p',{class:'inline-help'},x.notice||'')),x.portal_url?link('Abrir portal ↗',x.portal_url,'button small'):null));
    }catch(e){body.replaceChildren(el('div',{class:'callout error'},e.message));}
  };
  wrap.append(el('div',{class:'section-heading'},el('h2',{},'Corpus jurídico oficial'),
    el('p',{class:'inline-help'},'Colección compartida propia, separada del DMS de cada usuario. Sólo contiene originales publicados tras revisión; no incluye bases de datos privadas de terceros.')),
    el('div',{class:'actions'},button('Actualizar cobertura',loadStatus,{class:'button small'}),button('Ver fuentes catalogadas',showCatalog,{class:'button small'})),
    status,connectorBox,form,results,el('hr'),el('h3',{},'Consultar registros de la Corte Constitucional'),
    el('p',{class:'inline-help'},'Esta búsqueda consulta directamente metadatos publicados en Datos Abiertos Colombia. No incluye hechos, asuntos, razones ni texto completo del fallo.'),
    metaForm,metaResult);
  return wrap;
}

function v5JurisprudenciaWorkspace(chatPage) {
  const container=el('section',{class:'page v5-legal-workspace'},pageHeader('Jurisprudencia',
    'Investiga nuevas fuentes en la web o consulta tu biblioteca privada. Las referencias requieren revisión.',[],'INVESTIGACIÓN JURÍDICA'));
  const choices=[['research','Investigar con IA'],['official','Corpus jurídico oficial'],['library','Mi biblioteca jurídica'],['chat','Chat jurídico']];
  const tabs=el('nav',{class:'v5-legal-tabs',role:'tablist','aria-label':'Vistas de Jurisprudencia'},choices.map(([value,label])=>{
    const selected=V5.legalTab===value;
    return el('button',{type:'button',role:'tab','aria-selected':selected?'true':'false',class:'v5-legal-tab '+(selected?'active':''),on:{click:()=>{V5.legalTab=value;render();}}},label);
  }));
  container.append(tabs);
  if(V5.legalTab==='official')container.append(v5OfficialPanel());
  else if(V5.legalTab==='library')container.append(v5KnowledgePanel('legal'));
  else if(V5.legalTab==='chat')container.append(chatPage);
  else container.append(v5LegalResearchPanel());
  return container;
}
function v5KnowledgePanel(scope) {
  const legal=scope==='legal', wrap=el('section',{class:'v5-knowledge','aria-label':legal?'Biblioteca de fuentes jurídicas':'Búsqueda documental'});
  const heading=el('div',{class:'section-heading'},el('div',{},el('h2',{},legal?'Tu biblioteca jurídica':'Encuentra el fragmento que necesitas'),el('p',{class:'inline-help'},legal?'Busca en las fuentes oficiales que hayas incorporado y conserva el documento original.':'Pregunta por conceptos, cláusulas o hechos dentro de los documentos de tu cuenta.')));
  wrap.append(heading);
  const query=field(legal?'Buscar en fuentes incorporadas':'Consulta sobre tus documentos',{type:'search',value:V5.knowledgeDraft[scope],placeholder:legal?'Ej. criterios sobre estabilidad laboral reforzada':'Ej. obligaciones de entrega y cláusulas de terminación'});
  query.input.maxLength=4000;query.input.addEventListener('input',()=>V5.knowledgeDraft[scope]=query.input.value);
  const matter=field('Limitar búsqueda al asunto',{value:S.matterId,options:matterOptions(true)});
  const court=field('Corporación o entidad',{placeholder:'Todas las entidades'});
  const year=field('Año',{type:'number',min:1800,max:2200,placeholder:'Todos'});
  const type=field('Tipo de fuente',{options:[{value:'',label:'Todos los tipos'},{value:'sentencia',label:'Sentencia'},{value:'auto',label:'Auto'},{value:'ley',label:'Ley'},{value:'decreto',label:'Decreto'},{value:'concepto',label:'Concepto'},{value:'resolucion',label:'Resolución'},{value:'otro',label:'Otro'}]});
  const form=el('form',{class:'v5-knowledge-form'},query.wrap);
  if(legal)form.append(el('div',{class:'v5-three-fields'},court.wrap,year.wrap,type.wrap));else form.append(matter.wrap);
  const submit=el('button',{type:'submit',class:'button primary'},icon('search'),'Buscar en contenido');
  form.append(el('div',{class:'actions'},submit,legal?button('Incorporar fuente oficial',v5ImportSource,{icon:'plus'}):button('Preparar índice',()=>v5Reindex(),{icon:'history'}),legal?button('Ver fuentes admitidas',v5Sources,{icon:'book'}):button('Importar desde una conexión',()=>setPage('conexiones'),{icon:'link'})));
  if(legal)form.append(el('div',{class:'actions'},button('Ver biblioteca incorporada',()=>v5LegalLibrary({court:court.input.value.trim(),year:year.input.value,document_type:type.input.value}),{icon:'folder',class:'button small'}),button('Incorporar varias fuentes',v5CrawlSources,{icon:'download',class:'button small'})));
  const results=el('div',{class:'v5-search-results','aria-live':'polite'});
  const draw=()=>{
    const result=V5.results[scope];results.replaceChildren();if(!result)return;
    const count=result.results?.length||0;
    results.append(el('div',{class:'v5-search-summary'},el('strong',{},count+' '+(count===1?'fragmento encontrado':'fragmentos encontrados')),badge(result.method==='semantic'?'Búsqueda por significado':result.method==='hybrid'?'Búsqueda combinada':'Búsqueda de contenido','neutral')));
    if(result.coverage)results.append(v5Coverage(result.coverage,'Cobertura de la biblioteca'));
    for(const warning of result.warnings||[])results.append(el('div',{class:'callout warning'},text(warning)));
    if(!count)results.append(el('p',{class:'inline-help'},legal?'No hay resultados. Incorpora fuentes oficiales o ajusta los términos y filtros.':'No se encontraron fragmentos. Comprueba que los documentos contienen texto y que su índice esté actualizado.'));
    for(const found of result.results||[]){const loc=found.page?'Página '+found.page:found.segment?'Segmento '+found.segment:'';results.append(el('article',{class:'v5-search-hit'},el('h3',{},found.title||'Documento'),el('span',{class:'source-meta'},loc),el('p',{class:'v5-excerpt'},found.excerpt||''),el('div',{class:'actions'},button('Abrir documento',async()=>{const document=mergeItem(await v5api('/items/'+encodeURIComponent(found.document_id)));previewDocument(document);},{class:'button small',icon:'file'}),button('Usar en el agente',async()=>{const document=mergeItem(await v5api('/items/'+encodeURIComponent(found.document_id)));await newChat();S.selectedDocs.add(document.id);S.mode='analyze';S.chatDraft='Analiza el siguiente punto a partir del documento seleccionado: '+query.input.value;render();},{class:'button small',icon:'spark'}),found.source_url?link('Fuente oficial ↗',found.source_url,'text-button'):null)));}
  };
  form.addEventListener('submit',act(async event=>{
    event.preventDefault();if(!query.input.value.trim())throw new Error('Escribe una consulta para buscar.');const seq=++V5.searchSequence;
    await busy(submit,async()=>{results.replaceChildren(v5Loading('Buscando en tus documentos…'));try{
      const filters={};if(legal){if(court.input.value.trim())filters.court=court.input.value.trim();if(year.input.value)filters.year=Number(year.input.value);if(type.input.value)filters.document_type=type.input.value;}
      const result=await v5api('/knowledge/search',{method:'POST',body:{query:query.input.value.trim(),scope,matter_id:legal?null:matter.input.value||null,semantic:true,limit:20,filters}});
      if(seq!==V5.searchSequence)return;V5.results[scope]=result;draw();
    }catch(error){if(error.name==='AbortError')return;results.replaceChildren(el('div',{class:'callout error',role:'alert'},error.message));}});
  }));
  wrap.append(form,results);draw();
  return wrap;
}
async function v5Sources() {
  const result=await v5api('/knowledge/sources');V5.sources=Array.isArray(result)?result:result.sources||result.items||[];
  const list=el('div',{class:'item-list'},...V5.sources.map(source=>el('article',{class:'list-row'},icon('book'),el('div',{class:'row-main'},el('strong',{},source.name||source.title||source.label||source.host),el('small',{},source.description||source.host||'')),source.url?link('Abrir sitio ↗',source.url,'text-button'):null)));
  if(!V5.sources.length)list.append(el('p',{class:'inline-help'},'El servidor no devolvió fuentes disponibles.'));
  showModal('Fuentes oficiales admitidas',el('div',{},el('p',{class:'inline-help'},'Este catálogo indica dónde puedes incorporar documentos. La biblioteca contiene únicamente las fuentes que hayas importado; no es un inventario completo de jurisprudencia.'),list),[button('Cerrar',closeModal),button('Incorporar un documento',v5ImportSource,{class:'button primary',icon:'plus'})],true);
}
function v5ImportSource() {
  const url=field('URL del documento oficial',{type:'url',required:true,placeholder:'https://…',help:'Usa el enlace directo al documento o a la página oficial que lo contiene.'});
  const title=field('Título de la fuente (opcional)');
  const court=field('Corporación o entidad (opcional)');
  const year=field('Año de la fuente (opcional)',{type:'number',min:1800,max:2200});
  const type=field('Tipo de documento',{options:[{value:'sentencia',label:'Sentencia'},{value:'auto',label:'Auto'},{value:'ley',label:'Ley'},{value:'decreto',label:'Decreto'},{value:'concepto',label:'Concepto'},{value:'resolucion',label:'Resolución'},{value:'otro',label:'Otro'}]});
  formModal('Incorporar fuente oficial',[url,title,court,year,type],async()=>{
    if(!safeUrl(url.input.value))throw new Error('Introduce una URL HTTPS válida.');
    const result=await v5api('/knowledge/import',{method:'POST',body:{url:url.input.value.trim(),...(title.input.value.trim()?{title:title.input.value.trim()}:{}),...(court.input.value.trim()?{court:court.input.value.trim()}:{}),...(year.input.value?{year:Number(year.input.value)}:{}),document_type:type.input.value}});
    if(result.item)mergeItem(result.item);else if(result.document)mergeItem(result.document);else if(result.id)mergeItem(result);
    render();toast('Fuente incorporada a tu biblioteca.');for(const warning of result.warnings||[])toast(text(warning),'error');
  },{label:'Incorporar documento',extra:el('div',{class:'callout'},'Se conservarán el origen y el contenido recuperado. Comprueba fecha, entidad y pertinencia antes de utilizar la fuente.')});
}
async function v5Reindex() {
  const status=el('p',{class:'inline-help'},'Preparando la siguiente página de documentos…'),details=el('div',{class:'stack'});let stopped=false,offset=0,total=0,failed=0;
  const stop=button('Detener después de esta página',()=>{stopped=true;stop.disabled=true;status.textContent='Se terminará la página en curso.';});
  const content=el('div',{},el('div',{class:'callout'},'La búsqueda por significado utiliza el proveedor de embeddings configurado. Esta operación puede consumir su cuota.'),status,details);
  const modal=showModal('Actualizar índice documental',content,[stop]);
  const onClose=()=>{stopped=true;};modal.addEventListener('close',onClose,{once:true});
  try{for(let page=0;page<100&&!stopped&&content.isConnected;page++){
    const result=await v5api('/knowledge/reindex',{method:'POST',body:{offset,limit:10}});total+=result.items?.length??result.indexed??result.processed??result.results?.length??0;failed+=result.errors?.length||0;status.textContent='Documentos procesados: '+total+'. Errores: '+failed+'.';
    for(const error of result.errors||[])details.append(el('div',{class:'callout warning'},(item(error.document_id)?.title||error.document_id||'Documento')+': '+(error.message||error.error||'No se pudo preparar el índice.')));
    for(const warning of result.warnings||[])details.append(el('div',{class:'callout warning'},text(warning)));
    if(!result.has_more||result.next_offset===undefined||result.next_offset===null)break;
    if(result.next_offset<=offset)throw new Error('El servidor no avanzó el índice. Actualiza la página antes de reintentar.');offset=result.next_offset;
  }status.textContent+=(stopped?' Operación detenida.':' Actualización terminada.');}
  catch(e){if(e.name!=='AbortError'){status.textContent=e.message;status.setAttribute('role','alert');}}
  finally{modal.removeEventListener('close',onClose);if(content.isConnected&&modal.open)$('#modal-footer').replaceChildren(button('Cerrar',closeModal));}
}
function v5RetrievalCoverage(value) {
  const rows=Array.isArray(value)?value:[value],names={documents:'Documentos DMS',legal:'Fuentes jurídicas',official:'Corpus Jurídico Oficial'},methods={hybrid:'búsqueda combinada',semantic:'búsqueda por significado',text:'búsqueda textual',unavailable:'índice no disponible'};
  return el('div',{class:'coverage'},el('strong',{},'Consulta de la biblioteca: '),rows.map(row=>(names[row.scope]||'Biblioteca')+' · '+(methods[row.method]||row.method||'método no indicado')+' · '+(row.results??0)+' fragmentos recuperados').join('; '));
}
function v5Coverage(value,prefix='Cobertura') {
  if(typeof value==='string')return el('p',{class:'inline-help'},prefix+': '+value);
  const labels={documents:'documentos en la cuenta',indexed_documents:'documentos indexados',semantic_documents:'documentos con índice de significado',legal_documents:'fuentes jurídicas incorporadas',selected_passages:'fragmentos utilizados',available_passages:'fragmentos disponibles',pages:'páginas',parts_total:'fragmentos totales',parts_reviewed:'fragmentos revisados',chars_total:'caracteres totales',chars_reviewed:'caracteres revisados',discovered_links:'enlaces encontrados',attempted_documents:'documentos intentados',analyzed_documents:'documentos analizados',unchanged_documents:'documentos sin cambios',matches:'coincidencias',pending_links:'enlaces pendientes',extraction_incomplete_documents:'documentos con extracción incompleta',cached_parts:'fragmentos conservados de una revisión anterior',pages_total:'páginas del original',pages_included:'páginas incluidas',pages_with_text:'páginas con texto extraído'};
  const parts=Object.entries(labels).filter(([key])=>typeof value?.[key]==='number').map(([key,label])=>value[key]+' '+label);
  if(value?.source_extraction_complete===false)parts.push('extracción parcial del original');if(value?.retrieved_text_complete===false)parts.push('análisis pendiente de parte del texto recuperado');
  if(value?.complete===false||value?.complete_within_limit===false||value?.source_extraction_complete===false||value?.retrieved_text_complete===false||value?.truncated)parts.push('lectura parcial; queda contenido por revisar');
  else if(value?.complete===true||value?.complete_within_limit===true)parts.push('completado dentro del alcance indicado');
  const box=el('div',{class:'v5-coverage'},el('p',{class:'inline-help'},prefix+': '+(parts.join(' · ')||'El servidor no indicó un recuento de cobertura.')));
  if(value?.scope)box.append(el('p',{class:'inline-help'},value.scope));
  for(const error of value?.errors||[])box.append(el('div',{class:'callout warning'},typeof error==='string'?error:[error.url,error.error||error.message].filter(Boolean).join(' · ')));
  return box;
}
function v5RoomStatus(room) {
  if(room.status==='revoked'||room.revoked_at)return ['Revocada','neutral'];
  if(room.status==='expired'||room.expires_at&&new Date(room.expires_at)<new Date())return ['Vencida','neutral'];
  return ['Activa',''];
}
function renderRoomsV5() {
  const page=el('section',{class:'page'},pageHeader('Salas de documentos','Comparte una selección del expediente y recibe archivos mediante accesos con permisos y caducidad.',[button('Actualizar salas',()=>v5PageLoad('salas'),{icon:'history'}),button('Crear sala privada',v5RoomForm,{icon:'plus',class:'button primary'})],'GESTIÓN DOCUMENTAL'));
  page.append(el('div',{class:'callout'},'Cada enlace concede los permisos que elijas a quien lo posea. Comparte el acceso por un canal adecuado y revócalo cuando termine el trabajo. Los documentos publicados son copias fijadas de la versión seleccionada.'),v5Notice('rooms'));
  if(!V5.loaded.has('rooms')){page.append(v5Loading());return page;}
  if(V5.roomsCaps?.configured===false)page.append(el('div',{class:'callout warning'},V5.roomsCaps.message||'Configura los servicios privados de salas y aplica su migración.'));
  if(!V5.rooms.length&&V5.roomsOffset){page.append(empty('No hay más salas en esta página','Regresa a la página anterior para consultar las salas existentes.',button('Volver a la página anterior',()=>{V5.roomsOffset=Math.max(0,V5.roomsOffset-20);return v5PageLoad('salas');},{class:'button primary'})));return page;}
  if(!V5.rooms.length){page.append(empty('Un espacio delimitado para cada entrega','Selecciona documentos, prepara un enlace de consulta y decide si permites descargas o recepción de archivos.',button('Preparar primera sala',v5RoomForm,{icon:'lock',class:'button primary'}),'folder'));return page;}
  page.append(el('div',{class:'item-list'},V5.rooms.map(room=>{const[label,type]=v5RoomStatus(room);return el('article',{class:'list-row'},icon('lock'),el('div',{class:'row-main'},el('strong',{},room.title),el('small',{},matterTitle(room.matter_id)+' · Vence '+shortDate(room.expires_at)),room.description?el('small',{},room.description):null),badge(label,type),button('Abrir sala',()=>v5RoomDetail(room.id),{class:'button small',icon:'eye'}));})));
  page.append(el('div',{class:'actions v5-room-pagination'},el('span',{class:'inline-help'},'Salas '+(V5.roomsOffset+1)+' a '+(V5.roomsOffset+V5.rooms.length)),V5.roomsOffset?button('Página anterior',()=>{V5.roomsOffset=Math.max(0,V5.roomsOffset-20);return v5PageLoad('salas');}):null,V5.roomsHasMore?button('Página siguiente',()=>{V5.roomsOffset+=20;return v5PageLoad('salas');}):null));
  return page;
}
function v5RoomForm() {
  const title=field('Nombre de la sala',{required:true,placeholder:'Ej. revisión documental del asunto'}),description=field('Descripción para los destinatarios',{type:'textarea',rows:3}),matter=field('Asunto de la sala',{value:S.matterId,options:matterOptions()}),expiry=field('Vigencia de la sala (días)',{type:'number',value:30,min:1,max:90,required:true});
  const docs=v5ContextDocs(new Set());title.input.maxLength=240;description.input.maxLength=4000;
  formModal('Crear una sala privada',[title,description,matter,expiry],async()=>{
    if(!docs.selected.size)throw new Error('Selecciona al menos un documento para publicar en la sala.');if(docs.selected.size>20)throw new Error('Una sala admite hasta veinte documentos.');
    const result=await v5api('/rooms',{method:'POST',body:{title:title.input.value.trim(),description:description.input.value.trim(),document_ids:[...docs.selected],matter_id:matter.input.value||null,expires_days:Number(expiry.input.value)}});
    const room=result.room||result;if(!room.id)throw new Error('El servidor no devolvió una sala válida. Actualiza el listado antes de reintentar.');
    V5.roomsOffset=0;setPage('salas');toast('Sala creada. Abre la sala para preparar los enlaces y sus permisos.');
  },{label:'Crear sala',wide:true,extra:el('div',{},el('p',{class:'inline-help'},'Se fijarán copias de hasta 20 documentos, con un máximo total de 25 MB y 500 páginas. Crear una sala no envía mensajes ni comparte enlaces automáticamente.'),el('h3',{},'Documentos que se publicarán'),docs.box)});
}
async function v5RoomDetail(id) {
  const result=await v5api('/rooms/'+id),room=result.room||result,[label,type]=v5RoomStatus(room),active=label==='Activa';
  const content=el('div',{},badge(label,type),el('p',{class:'inline-help'},room.description||'Sala privada de documentos'),el('dl',{class:'detail-kv'},el('dt',{},'Asunto'),el('dd',{},matterTitle(room.matter_id)),el('dt',{},'Vence'),el('dd',{},shortDate(room.expires_at,true))));
  content.append(el('h3',{},'Documentos publicados'),el('div',{class:'item-list'},(room.documents||[]).map(doc=>el('article',{class:'list-row'},icon('file'),el('div',{class:'row-main'},el('strong',{},doc.title||doc.filename||'Documento'),el('small',{},doc.sha256?'Huella: '+doc.sha256:'Copia fijada para la sala')),button('Descargar copia',async()=>{const blob=await v5api('/rooms/'+id+'/documents/'+encodeURIComponent(doc.id),{blob:true});downloadBlob(blob,filename(doc.title,'pdf'));},{class:'button small',icon:'download'})))));
  content.append(el('div',{class:'section-heading'},el('h3',{},'Enlaces y permisos'),active?button('Crear enlace de acceso',()=>v5RoomLinkForm(room),{icon:'plus',class:'button small'}):null));
  const links=el('div',{class:'item-list'});for(const access of room.links||[]){const p=access.permissions||access,revoked=access.revoked_at||access.status==='revoked',expired=access.expires_at&&new Date(access.expires_at)<new Date();links.append(el('article',{class:'list-row'},icon('link'),el('div',{class:'row-main'},el('strong',{},access.label||'Acceso compartido'),el('small',{},[p.can_view?'Consulta':null,p.can_download?'Descarga':null,p.can_upload?'Recepción de archivos':null].filter(Boolean).join(' · ')||'Sin permisos'),el('small',{},'Vence '+shortDate(access.expires_at,true))),badge(revoked?'Revocado':expired?'Vencido':active?'Vigente':'Sala revocada',revoked||expired||!active?'neutral':''),!revoked&&active?button('Revocar enlace',()=>confirmDialog('Revocar este enlace','El enlace dejará de abrir la sala. Los demás accesos conservarán sus propios permisos.',async()=>{await v5api('/rooms/'+id+'/links/'+encodeURIComponent(access.id),{method:'DELETE'});toast('Enlace revocado.');},'Revocar enlace').then(()=>v5RoomDetail(id)),{class:'button small danger'}):null));}
  if(!links.children.length)links.append(el('p',{class:'inline-help'},'Todavía no hay accesos. Crea un enlace y comparte únicamente con las personas previstas.'));content.append(links);
  content.append(el('h3',{},'Archivos recibidos'),el('p',{class:'inline-help'},'Los archivos recibidos se revisan antes de incorporarse a DMS. Un enlace identifica el acceso utilizado; no verifica por sí solo la identidad de quien carga un archivo.'));
  const uploads=el('div',{class:'item-list'});for(const upload of room.uploads||[]){const status=upload.status||'pending',ready=status==='received',rejectable=['pending','received','failed'].includes(status);uploads.append(el('article',{class:'list-row'},icon('attach'),el('div',{class:'row-main'},el('strong',{},upload.filename||upload.name||'Archivo recibido'),el('small',{},shortDate(upload.created_at,true)+(upload.link_label?' · '+upload.link_label:''))),badge(({pending:'Recepción sin confirmar',received:'Pendiente de revisión',importing:'Incorporación en curso',failed:'No se pudo procesar',imported:'Incorporado a DMS',rejected:'Rechazado'}[status]||status),ready?'pending':'neutral'),el('div',{class:'row-actions'},['received','imported'].includes(status)?button('Revisar archivo',async()=>{const blob=await v5api('/rooms/'+id+'/uploads/'+encodeURIComponent(upload.id),{blob:true});downloadBlob(blob,upload.filename||'archivo-recibido');},{class:'button small',icon:'download'}):null,ready?button('Incorporar a DMS',async()=>{const imported=await v5api('/rooms/'+id+'/uploads/'+encodeURIComponent(upload.id)+'/import',{method:'POST',body:{}});mergeItem(imported.item||imported);toast('Archivo incorporado a tu biblioteca.');await v5RoomDetail(id);},{class:'button small',icon:'file'}):null,rejectable?button('Rechazar archivo',()=>confirmDialog('Rechazar archivo recibido','El archivo no se incorporará a tu biblioteca. El servidor conservará la trazabilidad de esta decisión.',async()=>{await v5api('/rooms/'+id+'/uploads/'+encodeURIComponent(upload.id)+'/reject',{method:'POST',body:{}});toast('Archivo rechazado.');},'Rechazar archivo').then(()=>v5RoomDetail(id)),{class:'button small danger'}):null)));}
  if(!uploads.children.length)uploads.append(el('p',{class:'inline-help'},'No se han recibido archivos. Para habilitar esta opción, crea un enlace con permiso de recepción.'));content.append(uploads);
  const events=room.audit||room.events||[];if(events.length)content.append(el('details',{class:'v5-room-audit'},el('summary',{},'Registro de accesos y actividad'),el('div',{class:'timeline'},events.map(event=>el('article',{class:'timeline-item'},el('time',{},shortDate(event.at||event.created_at,true)),el('strong',{},event.event||event.action||event.kind||'Actividad registrada'),el('p',{},text(event.detail||event.details||'')))))));
  showModal(room.title||'Sala privada',content,[button('Cerrar',closeModal),button('Actualizar sala',()=>v5RoomDetail(id),{icon:'history'}),active?button('Revocar sala completa',()=>confirmDialog('Revocar la sala','Todos los enlaces dejarán de permitir acceso. Esta decisión afecta a los destinatarios de esta sala.',async()=>{await v5api('/rooms/'+id+'/revoke',{method:'POST',body:{}});await v5PageLoad('salas');toast('Sala revocada.');},'Revocar sala'),{class:'button danger'}):null].filter(Boolean),true);
}
function v5RoomLinkForm(room) {
  const label=field('Etiqueta del acceso',{required:true,placeholder:'Ej. cliente · revisión de documentos'}),expiry=field('Vigencia del enlace (días)',{type:'number',value:7,min:1,max:90,required:true,help:'El acceso nunca se extiende más allá de la caducidad de la sala.'});
  const view=el('input',{type:'checkbox',checked:true}),download=el('input',{type:'checkbox'}),upload=el('input',{type:'checkbox'}),error=el('div',{class:'form-error',hidden:true,role:'alert'});
  label.input.maxLength=120;view.addEventListener('change',()=>{if(!view.checked)download.checked=false;download.disabled=!view.checked;});
  const form=el('form',{},error,label.wrap,el('fieldset',{class:'v5-plan-fieldset'},el('legend',{},'Permisos del enlace'),el('label',{class:'check-row'},view,el('span',{},'Consultar documentos en la sala')),el('label',{class:'check-row'},download,el('span',{},'Descargar documentos publicados')),el('label',{class:'check-row'},upload,el('span',{},'Cargar archivos para mi revisión'))),expiry.wrap,el('p',{class:'inline-help'},'La consulta en navegador entrega una copia para visualizarla: no impide capturas o copias por otros medios. El permiso de descarga controla la opción de descarga del portal.'));
  const create=button('Crear enlace privado',()=>form.requestSubmit(),{class:'button primary',icon:'link'});
  form.addEventListener('submit',async event=>{event.preventDefault();error.hidden=true;await busy(create,async()=>{try{
    if(!view.checked&&!upload.checked)throw new Error('Permite consultar documentos o cargar archivos.');if(download.checked&&!view.checked)throw new Error('La descarga requiere permiso de consulta.');
    const result=await v5api('/rooms/'+room.id+'/links',{method:'POST',body:{label:label.input.value.trim(),can_view:view.checked,can_download:download.checked,can_upload:upload.checked,expires_days:Number(expiry.input.value)}});
    const path=result.url||result.access_url;if(!path)throw new Error('No se recibió un enlace de acceso.');const url=new URL(path,location.origin);if(url.origin!==location.origin||url.pathname!=='/sala-cliente')throw new Error('El servidor devolvió un enlace inesperado. Revisa la sala antes de compartirlo.');
    showModal('Enlace privado de la sala',el('div',{},el('p',{class:'inline-help'},'Guarda este enlace ahora. Contiene una clave de acceso y no se volverá a mostrar. Compártelo únicamente con el destinatario previsto.'),el('div',{class:'signature-link'},url.href),el('p',{class:'inline-help'},'No se ha enviado ningún mensaje. Puedes revocar este acceso desde la sala.')),[button('Volver a la sala',()=>v5RoomDetail(room.id)),button('Copiar enlace privado',()=>copy(url.href),{class:'button primary',icon:'copy'})]);
  }catch(e){if(e.name!=='AbortError'){error.textContent=e.message;error.hidden=false;}}});});
  showModal('Preparar acceso a la sala',form,[button('Cancelar',closeModal),create],true);
}
async function v5LegalLibrary(filters={},offset=0) {
  const params=new URLSearchParams({offset:String(offset),limit:'20'});for(const [key,value]of Object.entries(filters))if(value!==''&&value!==null&&value!==undefined)params.set(key,String(value));
  const result=await v5api('/knowledge/documents?'+params.toString());const docs=result.items||[];
  const content=el('div',{},el('p',{class:'inline-help'},'Documentos oficiales incorporados a tu cuenta. Cada fuente conserva su origen; la colección depende de tus importaciones.'),el('div',{class:'item-list'},docs.map(doc=>{mergeItem(doc);return el('article',{class:'list-row'},icon('book'),el('div',{class:'row-main'},el('strong',{},doc.title),el('small',{},[doc.data?.court,doc.data?.year,doc.data?.document_type].filter(Boolean).join(' · '))),button('Revisar fuente',()=>previewDocument(doc),{class:'button small',icon:'eye'}));})));
  if(!docs.length)content.append(el('p',{class:'inline-help'},'No hay fuentes incorporadas con estos filtros. Puedes añadir documentos desde los sitios oficiales admitidos.'));
  showModal('Fuentes de tu biblioteca',content,[button('Cerrar',closeModal),offset?button('Anterior',()=>v5LegalLibrary(filters,Math.max(0,offset-20))):null,result.has_more?button('Siguiente',()=>v5LegalLibrary(filters,offset+20)):null,button('Incorporar fuente',v5ImportSource,{class:'button primary',icon:'plus'})].filter(Boolean),true);
}
function v5CrawlSources() {
  const url=field('Página oficial con enlaces a documentos',{type:'url',required:true,placeholder:'https://…'}),limit=field('Máximo de documentos por lote',{type:'number',value:5,min:1,max:10,required:true});
  const error=el('div',{class:'form-error',hidden:true,role:'alert'}),resultBox=el('div',{class:'stack','aria-live':'polite'}),form=el('form',{},error,url.wrap,limit.wrap,el('p',{class:'inline-help'},'Se revisarán los enlaces oficiales admitidos de esa página. La importación conserva documentos en tu cuenta y puede consumir cuota de extracción e indexación.'),resultBox);
  const save=button('Revisar enlaces e importar',()=>form.requestSubmit(),{class:'button primary',icon:'download'});
  form.addEventListener('submit',async event=>{event.preventDefault();error.hidden=true;await busy(save,async()=>{try{
    if(!safeUrl(url.input.value))throw new Error('Introduce una dirección HTTPS oficial.');resultBox.replaceChildren(v5Loading('Revisando los enlaces y preparando los documentos…'));
    const result=await v5api('/knowledge/crawl',{method:'POST',body:{url:url.input.value.trim(),max_documents:Number(limit.input.value)}});
    for(const row of result.items||[])if(row.item)mergeItem(row.item);resultBox.replaceChildren(el('h3',{},'Resultado del lote'),el('p',{},(result.items?.length||0)+' documentos incorporados o ya existentes. '+(result.errors?.length||0)+' errores.'),el('p',{class:'inline-help'},'Enlaces encontrados: '+(result.discovered??'—')+' · Intentos: '+(result.attempted??'—')));
    for(const row of result.items||[])resultBox.append(el('div',{class:'callout'},row.item?.title||'Documento incorporado',row.duplicate?' · Ya estaba en tu biblioteca':'',...(row.warnings||[]).map(w=>el('p',{},text(w)))));
    for(const failure of result.errors||[])resultBox.append(el('div',{class:'callout warning'},el('strong',{},failure.url||'Fuente'),el('p',{},failure.message||failure.error||'No se pudo incorporar.')));
    if(result.coverage)resultBox.append(el('p',{class:'inline-help'},typeof result.coverage==='string'?result.coverage:'Cobertura: '+text(result.coverage)));
    if(result.has_more)resultBox.append(el('p',{class:'inline-help'},'La página contiene más enlaces que el límite de este lote. Incorpora las fuentes pendientes por su URL para completar la colección.'));
  }catch(e){if(e.name!=='AbortError'){error.textContent=e.message;error.hidden=false;resultBox.replaceChildren();}}});});
  showModal('Incorporar un lote de fuentes oficiales',form,[button('Cerrar',closeModal),save],true);
}
function v5EnvelopeStatus(envelope) {
  if(envelope.status==='completed')return['Completada',''];
  if(envelope.status==='cancelled')return['Cancelada','neutral'];
  if(envelope.status==='expired'||(envelope.expires_at&&new Date(envelope.expires_at)<new Date()))return['Vencida','neutral'];
  return [envelope.status==='draft'?'Preparada':'Pendiente de firmas','pending'];
}
function renderSigningV5() {
  if(!S.caps?.signatures_v5){const legacy=renderSignatures();legacy.prepend(el('div',{class:'v5-upgrade-bar'},el('p',{},'Las solicitudes con varios documentos y verificación de correo se gestionan en el nuevo flujo.'),button('Solicitud con correo verificado',v5EnvelopeForm,{icon:'sign',class:'button primary'})));return legacy;}
  if(V5.signatureView==='legacy'){const legacy=renderSignatures();legacy.prepend(el('div',{class:'v5-tabs'},button('Solicitudes verificadas',()=>{V5.signatureView='verified';render();v5PageLoad('firmas');},{class:'button'}),badge('Solicitudes anteriores','neutral')));return legacy;}
  const page=el('section',{class:'page'});page.append(pageHeader('Firma electrónica','Reúne los documentos, define los firmantes y sigue la aceptación de cada persona.',[button('Actualizar solicitudes',()=>v5PageLoad('firmas'),{icon:'history'}),button('Solicitud con correo verificado',v5EnvelopeForm,{icon:'plus',class:'button primary'})]));
  page.append(el('div',{class:'v5-tabs'},badge('Solicitudes verificadas'),button('Solicitudes anteriores',()=>{V5.signatureView='legacy';render();loadSignatures();},{class:'text-button'})));
  page.append(el('div',{class:'callout'},'Cada destinatario revisa los documentos y confirma su correo mediante un código antes de aceptar. El sistema conserva el consentimiento y la evidencia del contenido. La verificación acredita acceso al correo, no verificación documental de identidad.'));
  if(S.caps.signatures_v5.configured===false)page.append(el('div',{class:'callout warning'},S.caps.signatures_v5.message||'La firma verificada requiere su migración, un servicio de correo y las claves del servidor. Comprueba esos servicios antes de enviar una solicitud.'));
  page.append(v5Notice('signing'));
  if(!V5.loaded.has('signing')){page.append(v5Loading());return page;}
  if(!V5.envelopes.length){page.append(empty('Una solicitud, todos los documentos','Selecciona los escritos revisados, ordena los anexos y añade las personas que deben firmar.',button('Preparar solicitud verificada',v5EnvelopeForm,{class:'button primary',icon:'sign'}),'sign'));return page;}
  page.append(el('div',{class:'item-list'},V5.envelopes.map(envelope=>{const[label,type]=v5EnvelopeStatus(envelope);return el('article',{class:'list-row'},icon('sign'),el('div',{class:'row-main'},el('strong',{},envelope.title),el('small',{},(envelope.documents?.length||0)+' documentos · '+(envelope.recipients?.filter(r=>r.status==='signed').length||0)+' de '+(envelope.recipients?.length||0)+' firmas'),el('small',{},'Creada '+shortDate(envelope.created_at)+' · Vence '+shortDate(envelope.expires_at))),badge(label,type),el('div',{class:'row-actions'},button('Abrir solicitud',()=>v5EnvelopeDetail(envelope.id),{class:'button small',icon:'eye'}),envelope.status==='completed'?button('Evidencia PDF',()=>v5EnvelopePdf(envelope,'receipt'),{class:'button small',icon:'download'}):null));})));
  return page;
}
function v5EnvelopeForm() {
  const title=field('Título de la solicitud',{required:true,placeholder:'Ej. contrato y anexos del asunto'});
  const order=field('Orden de firma',{options:[{value:'parallel',label:'Todos pueden firmar en cualquier orden'},{value:'sequential',label:'Uno después de otro, en el orden indicado'}]});
  const expiry=field('Vigencia de la solicitud (días)',{type:'number',value:7,min:1,max:30,required:true});
  const selected=[],docs=byKind('document').filter(d=>d.data?.text||(d.data?.mime==='application/pdf'&&d.data?.storage_path)),selectedBox=el('div',{class:'v5-ordered-docs'}),selection=el('div',{class:'checklist v5-doc-list'});
  const redraw=()=>{selectedBox.replaceChildren(...selected.map((id,i)=>el('div',{class:'v5-order-row'},el('span',{},(i+1)+'. '+(item(id)?.title||'Documento')),button('↑',()=>{[selected[i-1],selected[i]]=[selected[i],selected[i-1]];redraw();},{class:'button small',title:'Subir documento',disabled:i===0}),button('↓',()=>{[selected[i+1],selected[i]]=[selected[i],selected[i+1]];redraw();},{class:'button small',title:'Bajar documento',disabled:i===selected.length-1}))));};
  for(const doc of docs){const input=el('input',{type:'checkbox'});input.addEventListener('change',()=>{if(input.checked){if(selected.length>=10){input.checked=false;toast('Selecciona como máximo diez documentos.','error');return;}selected.push(doc.id);}else selected.splice(selected.indexOf(doc.id),1);redraw();});selection.append(el('label',{class:'check-row'},input,el('span',{},doc.title)));}
  if(!docs.length)selection.append(el('p',{class:'inline-help'},'Guarda primero los documentos revisados en DMS. Este flujo acepta el PDF original o genera un PDF desde el texto del escrito.'));
  const signerRows=[],signerBox=el('div',{class:'v5-signers'});
  function addSigner(){if(signerRows.length>=10){toast('Una solicitud admite hasta diez firmantes.','error');return;}const row={name:'',email:''};signerRows.push(row);drawSigners();}
  function drawSigners(){signerBox.replaceChildren(...signerRows.map((signer,i)=>{const name=field('Nombre del firmante '+(i+1),{value:signer.name,required:true});name.input.maxLength=160;name.input.minLength=2;const email=field('Correo del firmante '+(i+1),{value:signer.email,type:'email',required:true});name.input.addEventListener('input',()=>signer.name=name.input.value);email.input.addEventListener('input',()=>signer.email=email.input.value);return el('fieldset',{class:'v5-signer-row'},el('legend',{},'Firmante '+(i+1)),el('div',{class:'v5-two-fields'},name.wrap,email.wrap),button('Quitar firmante',()=>{signerRows.splice(i,1);drawSigners();},{class:'button small danger',disabled:signerRows.length===1}));}));}
  addSigner();
  const form=el('form',{},title.wrap,el('h3',{},'Documentos que integran la solicitud'),selection,selectedBox,el('h3',{},'Personas que deben firmar'),signerBox,button('Añadir firmante',addSigner,{icon:'plus'}),order.wrap,expiry.wrap,el('div',{class:'callout'},'Crear la solicitud fija los PDF originales o genera un PDF desde el texto de otros escritos. Revisa el PDF resultante antes de invitar. Las invitaciones se envían únicamente cuando pulses «Enviar invitaciones».'));
  const error=el('div',{class:'form-error',hidden:true,role:'alert'});form.prepend(error);
  const submit=button('Crear solicitud',()=>form.requestSubmit(),{class:'button primary',icon:'check'});
  form.addEventListener('submit',async event=>{event.preventDefault();error.hidden=true;await busy(submit,async()=>{try{
    if(!selected.length)throw new Error('Selecciona al menos un documento revisado.');
    const signers=signerRows.map(s=>({name:s.name.trim(),email:s.email.trim()}));if(signers.some(s=>!s.name||!s.email))throw new Error('Completa los nombres y correos de todos los firmantes.');
    const result=await v5api('/signing',{method:'POST',body:{title:title.input.value.trim(),document_ids:selected,signers,signing_order:order.input.value,expires_days:Number(expiry.input.value)}});
    closeModal();V5.signatureView='verified';await v5PageLoad('firmas');if(result.envelope?.id)await v5EnvelopeDetail(result.envelope.id);toast('Solicitud creada. Revisa los destinatarios antes de enviar invitaciones.');
  }catch(e){error.textContent=e.message;error.hidden=false;}});});
  showModal('Preparar firma con correo verificado',form,[button('Cancelar',closeModal),submit],true);
}
async function v5EnvelopeDetail(id) {
  const result=await v5api('/signing/'+id),envelope=result.envelope||result,[label,type]=v5EnvelopeStatus(envelope);
  const active=!['completed','cancelled','expired'].includes(envelope.status)&&(!envelope.expires_at||new Date(envelope.expires_at)>new Date());
  const content=el('div',{},badge(label,type),el('dl',{class:'detail-kv'},el('dt',{},'Orden'),el('dd',{},envelope.signing_order==='sequential'?'Secuencial':'En paralelo'),el('dt',{},'Vence'),el('dd',{},shortDate(envelope.expires_at,true)),el('dt',{},'Huella del conjunto'),el('dd',{class:'v5-hash'},envelope.manifest_hash||'—')),el('h3',{},'Documentos fijados'),el('ol',{class:'v5-document-manifest'},(envelope.documents||[]).map(d=>el('li',{},el('strong',{},d.title),el('small',{},d.pages+' páginas'),el('code',{class:'v5-hash'},d.sha256)))));
  const pending=[];
  content.append(el('h3',{},'Destinatarios y seguimiento'),el('div',{class:'item-list'},(envelope.recipients||[]).map((recipient,i)=>{if(recipient.status!=='signed')pending.push(recipient.id);return el('article',{class:'list-row'},el('span',{class:'avatar'},i+1),el('div',{class:'row-main'},el('strong',{},recipient.name),el('small',{},recipient.email),el('small',{},recipient.status==='signed'?'Aceptó '+shortDate(recipient.signed_at,true):'Correo: '+({smtp_accepted:'Aceptado por el servidor de correo',unconfirmed:'Envío sin confirmar',sent:'Enviado',not_sent:'Sin enviar',failed:'Error de envío',pending:'Pendiente'}[recipient.delivery_status]||recipient.delivery_status||'Sin enviar'))),badge(recipient.status==='signed'?'Firmó':'Pendiente',recipient.status==='signed'?'':'pending'),active&&recipient.status!=='signed'?el('div',{class:'row-actions'},button('Enviar invitación',()=>v5Invite(envelope,[recipient.id]),{class:'button small'}),button('Obtener enlace privado',()=>v5RecipientLink(envelope,recipient),{class:'button small',icon:'link'})):null);})));
  if(envelope.events?.length)content.append(el('details',{},el('summary',{},'Registro de eventos'),el('div',{class:'timeline'},envelope.events.map(e=>el('article',{class:'timeline-item'},el('time',{},shortDate(e.at||e.created_at,true)),el('strong',{},e.event||e.kind),el('p',{},text(e.detail||'')))))));
  showModal(envelope.title,content,[button('Cerrar',closeModal),button('Documento PDF',()=>v5EnvelopePdf(envelope,'document'),{icon:'download'}),envelope.status==='completed'?button('Evidencia PDF',()=>v5EnvelopePdf(envelope,'receipt'),{icon:'download',class:'button primary'}):null,active&&pending.length?button('Enviar invitaciones',()=>v5Invite(envelope,pending),{class:'button primary',icon:'arrow'}):null,active?button('Cancelar solicitud',()=>confirmDialog('Cancelar solicitud de firma','Los enlaces dejarán de aceptar firmas nuevas. Las evidencias de aceptaciones previas se conservarán.',async()=>{await v5api('/signing/'+envelope.id+'/cancel',{method:'POST',body:{}});await v5PageLoad('firmas');},'Cancelar solicitud'),{class:'button danger'}):null].filter(Boolean),true);
}
function v5Invite(envelope, ids) {
  const recipients=(envelope.recipients||[]).filter(r=>ids.includes(r.id));
  const body=el('div',{},el('p',{class:'inline-help'},'Se enviará una invitación de firma para «'+envelope.title+'» a estas personas:'),el('ul',{},recipients.map(r=>el('li',{},r.name+' · '+r.email))),el('p',{class:'inline-help'},'Cada mensaje contiene un enlace privado. Revisa los correos antes de enviarlo.'));
  const send=button('Enviar estos correos',async e=>busy(e.currentTarget,async()=>{const result=await v5api('/signing/'+envelope.id+'/invite',{method:'POST',body:{recipient_ids:ids}});const results=el('div',{class:'item-list'},(result.results||[]).map(r=>el('div',{class:r.status==='smtp_accepted'?'callout':'callout warning'},el('strong',{},(recipients.find(p=>p.id===r.recipient_id)?.email||'Destinatario')+': '+({smtp_accepted:'Aceptado por el servidor de correo',unconfirmed:'Envío sin confirmar'}[r.status]||'No se confirmó el envío')),el('p',{},r.error||r.notice||(r.status==='smtp_accepted'?'La aceptación del servidor no garantiza la llegada a la bandeja del destinatario.':'Revisa el servicio de correo antes de reintentar.')))));showModal('Resultado del envío',results,[button('Cerrar',closeModal),button('Volver a la solicitud',()=>v5EnvelopeDetail(envelope.id),{class:'button primary'})]);await v5PageLoad('firmas');}),{class:'button primary',icon:'arrow'});
  showModal('Confirmar invitaciones de firma',body,[button('Cancelar',closeModal),send],true);
}
async function v5RecipientLink(envelope, recipient) {
  const result=await v5api('/signing/'+envelope.id+'/recipients/'+recipient.id+'/link',{method:'POST',body:{}});
  if(!result.signing_url)throw new Error('No se recibió un enlace válido.');
  showModal('Enlace privado para '+recipient.name,el('div',{},el('div',{class:'callout'},result.notice||'El enlace anterior del destinatario ha sido reemplazado. Comparte el nuevo únicamente con la persona indicada.'),el('div',{class:'signature-link'},result.signing_url),el('p',{class:'inline-help'},'La aceptación también requiere el código enviado al correo del destinatario.')),[button('Cerrar',closeModal),button('Copiar enlace privado',()=>copy(result.signing_url),{class:'button primary',icon:'copy'})]);
}
async function v5EnvelopePdf(envelope, kind) {
  const blob=await v5api('/signing/'+envelope.id+'/'+kind,{blob:true});downloadBlob(blob,filename((kind==='receipt'?'evidencia-':'documentos-')+envelope.title,'pdf'));
}
function v5EnhancePage(page) {
  if(S.page==='chat'){
    const panel=el('div',{class:'v5-agent-entry'},el('div',{},el('h2',{},'¿Necesitas varios pasos?'),el('p',{},'Prepara un plan de lectura, investigación y redacción. Revisa las etapas antes de ejecutarlas.')),el('div',{class:'actions'},button('Planificar y ejecutar',v5CreateJob,{icon:'spark',class:'button primary'}),button('Ver encargos',()=>setPage('encargos'),{class:'text-button'})));
    const composer=page.querySelector('.composer-note');if(composer)composer.after(panel);else page.append(panel);
  }
  if(S.page==='investigacion')return v5JurisprudenciaWorkspace(page);
  if(S.page==='biblioteca'){
    const heading=page.querySelector('.page-header');if(heading){heading.querySelector('.actions')?.append(button('Salas para compartir',()=>setPage('salas'),{icon:'lock'}));heading.after(v5KnowledgePanel('documents'));}
    const ocr=V5.knowledgeStatus?.ocr;
    if(ocr){const help=el('p',{class:'inline-help v5-ocr-status'},ocr.available?'OCR disponible para archivos escaneados e imágenes. Revisa siempre las fechas, nombres y cifras del texto reconocido.':'El OCR no está disponible en este servidor. Los PDF con texto pueden analizarse; los escaneados necesitan activar el motor de reconocimiento.');page.append(help);}
  }
  if(S.page==='ajustes')page.prepend(el('div',{class:'v5-upgrade-bar'},el('div',{},el('h2',{},'Herramientas conectadas'),el('p',{},'Administra las cuentas externas y el trabajo programado desde sus secciones.')),el('div',{class:'actions'},button('Abrir conexiones',()=>setPage('conexiones'),{icon:'link'}),button('Tareas programadas',()=>setPage('tareas'),{icon:'calendar'}))));
  if(S.page==='ajustes')page.append(v5AutomationSettings());
  return page;
}

function monitorForm(record){
  const title=field('Nombre del monitor',{value:record?.title,required:true,placeholder:'Ej. cambios en obligaciones de protección de datos'});
  const url=field('URL de la página oficial',{value:record?.data?.url,type:'url',required:true,placeholder:'https://…',help:'Indica una página concreta de una fuente admitida por el servidor.'});
  const mode=field('Criterio de detección',{value:record?.data?.analysis_mode||'keywords',options:[{value:'semantic',label:'Evaluar una condición con IA'},{value:'keywords',label:'Detectar cambios y palabras clave'}]});
  const condition=field('Condición jurídica para la IA',{type:'textarea',value:record?.data?.condition||'',placeholder:'Ej. detectar cambios que alteren los deberes de información de una empresa.',help:'Describe qué cambios te interesan. La IA explicará por qué un documento cumple o no tu condición.',rows:3});
  condition.input.maxLength=6000;
  const keywords=field('Palabras clave',{value:Array.isArray(record?.data?.keywords)?record.data.keywords.join(', '):record?.data?.keywords||'',help:'Separadas por comas. En el modo de palabras clave, vacío registra cualquier cambio.'});
  const follow=field('Lectura de documentos enlazados',{value:record?.data?.follow_links?'true':'false',options:[{value:'false',label:'Sólo la página indicada'},{value:'true',label:'Revisar también documentos enlazados admitidos'}]});
  const maxDocs=field('Máximo de documentos por revisión',{type:'number',value:record?.data?.max_documents||5,min:1,max:10,required:true});
  const interval=field('Frecuencia solicitada (minutos)',{value:record?.data?.interval_minutes||60,type:'number',min:15,max:10080,required:true,help:'La ejecución automática necesita un trabajador activo. Cada análisis de IA puede consumir cuota.'});
  const matter=field('Asunto',{value:record?.matter_id||S.matterId,options:matterOptions()});
  const update=()=>{condition.input.required=mode.input.value==='semantic';condition.wrap.hidden=mode.input.value!=='semantic';};mode.input.addEventListener('change',update);update();
  formModal(record?'Editar monitor':'Crear monitor',[title,url,mode,condition,keywords,follow,maxDocs,interval,matter],async()=>{
    if(!safeUrl(url.input.value))throw new Error('Usa una URL HTTPS válida sin usuario ni contraseña.');
    if(mode.input.value==='semantic'&&!condition.input.value.trim())throw new Error('Describe la condición que debe evaluar la IA.');
    const data={...record?.data,url:url.input.value.trim(),keywords:keywords.input.value.split(',').map(s=>s.trim()).filter(Boolean),condition:condition.input.value.trim(),analysis_mode:mode.input.value,follow_links:follow.input.value==='true',max_documents:Number(maxDocs.input.value),interval_minutes:Number(interval.input.value),enabled:record?.data?.enabled!==false};
    if(record)await updateItem(item(record.id),{title:title.input.value.trim(),matter_id:matter.input.value||null,data});else await createItem('monitor',title.input.value.trim(),data,matter.input.value);
    render();toast('Monitor guardado.');
  },{wide:true,extra:el('div',{class:'callout'},'Cada revisión muestra su cobertura y conserva las fuentes consultadas. Una evaluación de IA requiere revisión jurídica; un error de análisis no se presenta como ausencia de novedades.')});
}
function v5MonitorExtractionIncomplete(data) {
  return data?.extraction_coverage?.complete===false || Number(data?.coverage?.extraction_incomplete_documents)>0;
}
function v5AutomationSettings() {
  const limits=S.caps?.automation_limits;
  if(!limits)return document.createDocumentFragment();
  const display=value=>Number.isFinite(value)?new Intl.NumberFormat('es-CO').format(value):'No indicado';
  return el('section',{class:'settings-section'},el('h2',{},'Cuotas de automatización'),el('p',{},'Límites diarios configurados para los monitores automáticos y las tareas programadas. El servidor comprueba la cuota antes de cada llamada y la restablece a las 00:00 '+(limits.reset_timezone||'UTC')+'.'),el('dl',{class:'detail-kv'},el('dt',{},'Por cuenta y día'),el('dd',{},display(limits.user_daily)+' llamadas automáticas'),el('dt',{},'En todo el servicio por día'),el('dd',{},display(limits.global_daily)+' llamadas automáticas')),el('p',{class:'inline-help'},'Cada solicitud lógica al modelo o al servicio de búsqueda por significado consume una unidad, incluidos los intentos fallidos. Una tarea puede necesitar varias llamadas para completar sus pasos.'),limits.user_daily===0||limits.global_daily===0?el('div',{class:'callout warning'},'Una de las cuotas está en cero. Las nuevas llamadas automáticas permanecerán bloqueadas hasta que el administrador ajuste ese límite.'):null);
}
function v5MonitorIssues(data,expanded=false) {
  const warnings=Array.isArray(data.last_warnings)?data.last_warnings:[],partial=v5MonitorExtractionIncomplete(data);
  if(!warnings.length&&!partial)return document.createDocumentFragment();
  const block=el('div',{class:'v5-monitor-issues'});
  if(partial)block.append(el('div',{class:'callout warning'},'Extracción parcial del original. Hay páginas o texto pendientes de lectura; esta comprobación no permite descartar novedades en el contenido que falta.'));
  if(warnings.length)block.append(el('details',{class:'v5-monitor-warnings',open:expanded},el('summary',{},'Advertencias de la última comprobación ('+warnings.length+')'),warnings.map(w=>el('p',{class:'message-note'},text(w)))));
  return block;
}
function monitorFindings(record){
  const m=item(record.id)||record,findings=m.data?.findings||[],body=el('div',{class:'monitor-findings'});
  if(!findings.length)body.append(el('p',{class:'inline-help'},'No hay hallazgos registrados. Consulta el estado y la última cobertura del monitor para distinguir una revisión sin cambios de una revisión incompleta.'));
  for(const f of findings.slice().reverse()){
    const a=f.analysis||{},row=el('article',{class:'finding'},el('time',{},shortDate(f.detected_at,true)),el('strong',{},f.title||'Documento revisado'),a.relevant===true?badge('Coincide con la condición'):a.relevant===false?badge('No coincide','neutral'):f.analysis_status==='error'?badge('Análisis pendiente','pending'):null,
      el('p',{},a.summary||f.summary||f.excerpt||''),a.reason?el('div',{class:'v5-finding-reason'},el('h4',{},'Por qué se considera relevante'),el('p',{},a.reason)):null);
    if(a.evidence?.length)row.append(el('details',{},el('summary',{},'Fragmentos de apoyo'),el('div',{class:'v5-prewrap'},typeof a.evidence==='string'?a.evidence:a.evidence.map(text).join('\n\n'))));
    if(f.matched_keywords?.length)row.append(el('small',{},'Coincidencias: '+f.matched_keywords.join(', ')));
    if(a.coverage)row.append(v5Coverage(a.coverage));
    for(const warning of [...(a.warnings||[]),...(f.warnings||[])])row.append(el('div',{class:'message-note'},text(warning)));
    if(f.error||a.error)row.append(el('div',{class:'callout error'},text(f.error||a.error)));
    row.append(link('Abrir fuente original ↗',f.url||m.data?.url));body.append(row);
  }
  if(m.data?.coverage)body.prepend(v5Coverage(m.data.coverage,'Última comprobación'));
  if(m.data?.extraction_coverage&&Object.keys(m.data.extraction_coverage).length)body.prepend(v5Coverage(m.data.extraction_coverage,'Extracción del original'));
  body.prepend(v5MonitorIssues(m.data||{},true));
  showModal('Hallazgos · '+m.title,body,[button('Cerrar',closeModal)],true);
}

/* =========================================================================
   CENTRO DE CALIDAD JURÍDICA CONTINUA (FASE 2.3)
   ========================================================================= */

const calidadState = {
  activeTab: 'corpus', // 'corpus' | 'agente' | 'evolucion'
  metrics: null,
  docs: [],
  incidencias: [],
  evolucion: [],
  loading: false,
};

async function loadCalidadData(){
  try {
    const [metricsRes, docsRes, incsRes, evoRes] = await Promise.all([
      api('/despacho/calidad/metricas').catch(()=>({})),
      api('/despacho/calidad/corpus/documentos?limit=50').catch(()=>({documentos:[]})),
      api('/despacho/calidad/incidencias?limit=50').catch(()=>({incidencias:[]})),
      api('/despacho/calidad/evolucion?limit=50').catch(()=>({relaciones:[]})),
    ]);
    calidadState.metrics = metricsRes;
    calidadState.docs = docsRes.documentos || [];
    calidadState.incidencias = incsRes.incidencias || [];
    calidadState.evolucion = evoRes.relaciones || [];
  } catch (err) {
    console.error('Error cargando datos de calidad:', err);
  }
}

function openErrorReportModal(targetInfo={}){
  const body = el('div', {class: 'error-report-modal'});
  body.append(el('p', {class: 'inline-help'},
    'Tu reporte permite auditar y perfeccionar la fundamentación jurídica de El Memorialista. La información técnica se enviará de forma confidencial sin exponer datos privados de expedientes.'
  ));

  const categoryField = field('Tipo de anomalía detectada', {
    name: 'error_category',
    options: [
      {value: 'sentencia_incorrecta', label: 'Sentencia incorrecta o inexistente'},
      {value: 'referencia_equivocada', label: 'Referencia documental equivocada [O#-S#]'},
      {value: 'interpretacion_incorrecta', label: 'Interpretación jurídica o alcance incorrecto'},
      {value: 'informacion_desactualizada', label: 'Información desactualizada o precedente superado'},
      {value: 'fragmento_incompleto', label: 'Fragmento incompleto o truncado'},
      {value: 'otro', label: 'Otro problema de calidad'}
    ]
  });

  const descField = field('Observaciones o justificación jurídica (opcional)', {
    name: 'description',
    type: 'textarea',
    rows: 4,
    placeholder: 'Indica por qué consideras que la sentencia, cita o interpretación presenta una inconsistencia…'
  });

  body.append(categoryField.wrap, descField.wrap);

  const sendBtn = button('Radicar reporte de error', async () => {
    await busy(sendBtn, async () => {
      try {
        const payload = {
          target_type: targetInfo.target_type || 'agente_respuesta',
          document_id: targetInfo.document_id || null,
          document_version: targetInfo.document_version || targetInfo.version || 1,
          fragment_ordinal: targetInfo.fragment_ordinal !== undefined ? targetInfo.fragment_ordinal : (targetInfo.ordinal !== undefined ? targetInfo.ordinal : null),
          fragment_segment: targetInfo.fragment_segment !== undefined ? targetInfo.fragment_segment : (targetInfo.segment !== undefined ? targetInfo.segment : null),
          response_id: targetInfo.response_id || null,
          sentencia: targetInfo.sentencia || null,
          error_category: categoryField.input.value,
          description: descField.input.value.trim(),
          temporal_citation: targetInfo.source_fragment_id || targetInfo.citation_id || null,
          source_fragment_id: targetInfo.source_fragment_id || null,
          query_summary: targetInfo.query_summary || null
        };
        const res = await api('/despacho/calidad/reportes-error', {method: 'POST', body: payload});
        toast(res.message || 'Reporte radicado con éxito en el Centro de Calidad.');
        closeModal();
      } catch (err) {
        toast('Error al enviar reporte: ' + err.message);
      }
    });
  }, {class: 'button primary', icon: 'check'});

  showModal('⚠️ Reportar error o inconsistencia jurídica', body, [button('Cancelar', closeModal), sendBtn]);
}

function renderCalidadJuridica(){
  const container = el('section', {class: 'calidad-container'});

  const header = el('div', {class: 'calidad-header'},
    el('div', {class: 'calidad-title'},
      el('h1', {}, 'Centro de Calidad Jurídica Continua'),
      el('p', {}, 'Supervisión permanente del Corpus Oficial, verificación de respuestas del Agente y seguimiento jurisprudencial.')
    ),
    el('div', {class: 'calidad-header-actions'},
      button('↻ Actualizar', async () => {
        calidadState.loading = true;
        render();
        await loadCalidadData();
        calidadState.loading = false;
        render();
      }, {class: 'button small'}),
      button('Auditar muestra ahora', async () => {
        try {
          toast('Iniciando auditoría incremental de muestra…');
          const res = await api('/despacho/calidad/corpus/auditar', {method: 'POST', body: {sample_size: 5}});
          toast(`Muestra auditada con éxito (${res.result?.audited_count || 0} providencias).`);
          await loadCalidadData();
          render();
        } catch (err) {
          toast('Error en auditoría: ' + err.message);
        }
      }, {class: 'button small primary', icon: 'check'})
    )
  );

  const m = calidadState.metrics?.metricas_tecnicas || {};
  const j = calidadState.metrics?.evaluaciones_juridicas || {};
  const metricsBar = el('div', {class: 'v5-sync-metrics-grid'},
    el('div', {class: 'v5-metric-box'},
      el('div', {class: 'v5-metric-num'}, String(m.documentos_publicados ?? '—')),
      el('div', {class: 'v5-metric-label'}, 'Providencias Publicadas')
    ),
    el('div', {class: 'v5-metric-box'},
      el('div', {class: 'v5-metric-num'}, String(m.documentos_auditados ?? '—')),
      el('div', {class: 'v5-metric-label'}, 'Providencias Auditadas')
    ),
    el('div', {class: 'v5-metric-box'},
      el('div', {class: 'v5-metric-num'}, String(m.documentos_retirados ?? '0')),
      el('div', {class: 'v5-metric-label'}, 'Retiradas Preventivamente')
    ),
    el('div', {class: 'v5-metric-box'},
      el('div', {class: 'v5-metric-num'}, String(m.errores_criticos ?? '0')),
      el('div', {class: 'v5-metric-label'}, 'Errores Críticos')
    ),
    el('div', {class: 'v5-metric-box'},
      el('div', {class: 'v5-metric-num'}, String(j.respuestas_reportadas ?? '0')),
      el('div', {class: 'v5-metric-label'}, 'Reportes de Usuarios')
    ),
    el('div', {class: 'v5-metric-box'},
      el('div', {class: 'v5-metric-num'}, String(j.incidencias_solucionadas ?? '0')),
      el('div', {class: 'v5-metric-label'}, 'Incidencias Resueltas')
    ),
    el('div', {class: 'v5-metric-box'},
      el('div', {class: 'v5-metric-num'}, '$0.00 USD'),
      el('div', {class: 'v5-metric-label'}, 'Coste Infraestructura')
    )
  );

  const tabsBar = el('div', {class: 'calidad-tabs'});
  const tabs = [
    {id: 'corpus', label: 'A. Calidad del Corpus'},
    {id: 'agente', label: 'B. Calidad del Agente e Incidencias'},
    {id: 'evolucion', label: 'C. Seguimiento Jurisprudencial'}
  ];
  for (const t of tabs) {
    const btn = el('button', {
      type: 'button',
      class: 'calidad-tab-btn ' + (calidadState.activeTab === t.id ? 'active' : '')
    }, t.label);
    btn.addEventListener('click', () => {
      calidadState.activeTab = t.id;
      render();
    });
    tabsBar.append(btn);
  }

  let tabPane;
  if (calidadState.activeTab === 'corpus') {
    tabPane = renderTabCorpus();
  } else if (calidadState.activeTab === 'agente') {
    tabPane = renderTabAgente();
  } else {
    tabPane = renderTabEvolucion();
  }

  container.append(header, metricsBar, tabsBar, tabPane);

  if (!calidadState.metrics && !calidadState.loading) {
    calidadState.loading = true;
    loadCalidadData().then(() => {
      calidadState.loading = false;
      render();
    });
  }

  return container;
}

function renderTabCorpus(){
  const wrap = el('div', {class: 'calidad-tab-pane'});
  const docs = calidadState.docs;

  const disclaimerBox = el('div', {class: 'calidad-disclaimer-box'},
    el('strong', {}, 'Distinción obligatoria entre integridad técnica y certificación jurídica: '),
    el('span', {}, 'El Puntaje Técnico Automático refleja exclusivamente comprobaciones sistemáticas de archivos (hashes SHA-256, ausencia de duplicados, continuidad de fragmentos y formato de embeddings). Una puntuación técnica del 100 % NO constituye garantía ni certificación de exactitud o vigencia jurídica, las cuales requieren revisión jurídica humana profesional.')
  );
  wrap.append(disclaimerBox);

  if (!docs.length) {
    wrap.append(el('p', {class: 'inline-help'}, 'Cargando providencias del Corpus Oficial…'));
    return wrap;
  }

  const tableWrap = el('div', {class: 'calidad-table-wrapper'});
  const table = el('table', {class: 'calidad-table'});
  table.append(
    el('thead', {},
      el('tr', {},
        el('th', {}, 'Providencia'),
        el('th', {}, 'Puntaje Técnico Automático'),
        el('th', {}, 'Certificación Jurídica'),
        el('th', {}, 'Estado en Corpus'),
        el('th', {}, 'Última Auditoría'),
        el('th', {}, 'Acciones')
      )
    )
  );

  const tbody = el('tbody', {});
  for (const d of docs) {
    const qStatus = d.quality_status || 'sin_auditar';
    const pillClass = qStatus === 'optimo' ? 'optimo' : (qStatus === 'con_advertencias' ? 'advertencia' : (qStatus === 'critico_retirado' ? 'retirado' : 'incidencia'));
    const isWithdrawn = !!d.is_withdrawn;
    const isLegalCertified = !!d.legal_certified;
    const isPublished = !!d.published;

    const row = el('tr', {},
      el('td', {},
        el('strong', {}, d.title || 'Providencia Oficial'),
        el('div', {class: 'v5-grouped-meta'}, d.metadata?.magistrado ? `Ponente: ${d.metadata.magistrado}` : (d.metadata?.radicado ? `Exp: ${d.metadata.radicado}` : ''))
      ),
      el('td', {},
        el('div', {style: 'display:flex;align-items:center;gap:6px;'},
          el('span', {class: 'calidad-pill ' + pillClass}, `${d.technical_score ?? d.quality_score ?? 100}% Técnico`),
          el('span', {style: 'font-size:0.75rem;color:var(--text-muted);'}, `(${qStatus.replace(/_/g, ' ')})`)
        )
      ),
      el('td', {},
        isLegalCertified
          ? el('span', {class: 'calidad-pill verificado', title: d.legal_certified_by ? `Revisada por: ${d.legal_certified_by}` : 'Certificada formalmente'}, '✓ Certificada por Abogado')
          : el('span', {class: 'calidad-pill advertencia', title: 'Pendiente de revisión jurídica humana formal'}, '⏳ Pendiente Revisión Humana')
      ),
      el('td', {},
        isWithdrawn
          ? el('span', {class: 'calidad-pill retirado'}, 'Retirado')
          : (isPublished ? el('span', {class: 'calidad-pill optimo'}, 'Publicado') : el('span', {class: 'calidad-pill pendiente'}, 'En Triage'))
      ),
      el('td', {}, d.last_quality_audit_at ? shortDate(d.last_quality_audit_at, true) : 'Pendiente'),
      el('td', {style: 'display:flex;gap:6px;flex-wrap:wrap;'},
        button('Auditar', async () => {
          try {
            toast('Auditando ' + d.title + '…');
            const res = await api('/despacho/calidad/corpus/auditar', {method: 'POST', body: {document_id: d.id}});
            toast(`Auditoría técnica: score ${res.result?.quality_score}% (${res.result?.quality_status})`);
            await loadCalidadData();
            render();
          } catch (err) {
            toast('Error auditando: ' + err.message);
          }
        }, {class: 'button small'}),
        isWithdrawn ? button('Restaurar', async () => {
          const reasonPrompt = prompt('Ingresa nota de subsanación para restaurar la providencia:', 'Inconsistencia subsanada tras verificación.');
          if (!reasonPrompt) return;
          try {
            await api('/despacho/calidad/corpus/restaurar', {method: 'POST', body: {document_id: d.id, resolution_note: reasonPrompt}});
            toast('Providencia restaurada con éxito.');
            await loadCalidadData();
            render();
          } catch (err) {
            toast('Error restaurando: ' + err.message);
          }
        }, {class: 'button small primary'}) : button('Retirar', async () => {
          const reasonPrompt = prompt('Motivo del retiro preventivo de esta providencia:', 'Inconsistencia grave detectada en texto o metadatos.');
          if (!reasonPrompt) return;
          try {
            await api('/despacho/calidad/corpus/retirar', {method: 'POST', body: {document_id: d.id, reason: reasonPrompt}});
            toast('Providencia retirada temporalmente de búsquedas.');
            await loadCalidadData();
            render();
          } catch (err) {
            toast('Error retirando: ' + err.message);
          }
        }, {class: 'button small text-button report-error-btn'})
      )
    );
    tbody.append(row);
  }

  table.append(tbody);
  tableWrap.append(table);
  wrap.append(tableWrap);
  return wrap;
}

function renderTabAgente(){
  const wrap = el('div', {class: 'calidad-tab-pane'});
  const incs = calidadState.incidencias;

  if (!incs.length) {
    wrap.append(el('p', {class: 'inline-help'}, 'No hay incidencias registradas en este momento. El sistema se encuentra operando con integridad.'));
    return wrap;
  }

  const tableWrap = el('div', {class: 'calidad-table-wrapper'});
  const table = el('table', {class: 'calidad-table'});
  table.append(
    el('thead', {},
      el('tr', {},
        el('th', {}, 'Fecha'),
        el('th', {}, 'Ámbito'),
        el('th', {}, 'Tipo de Problema'),
        el('th', {}, 'Gravedad'),
        el('th', {}, 'Estado'),
        el('th', {}, 'Acciones')
      )
    )
  );

  const tbody = el('tbody', {});
  for (const inc of incs) {
    const sevPill = inc.severity === 'critica' ? 'incidencia' : (inc.severity === 'alta' ? 'advertencia' : 'optimo');
    const stPill = inc.status === 'corregido' || inc.status === 'cerrado' ? 'verificado' : (inc.status === 'en_investigacion' ? 'advertencia' : 'pendiente');

    const row = el('tr', {},
      el('td', {}, shortDate(inc.detected_at, true)),
      el('td', {}, el('strong', {}, inc.scope?.toUpperCase() || 'GENERAL')),
      el('td', {}, inc.issue_type?.replace(/_/g, ' ') || 'Anomalía'),
      el('td', {}, el('span', {class: 'calidad-pill ' + sevPill}, inc.severity)),
      el('td', {}, el('span', {class: 'calidad-pill ' + stPill}, inc.status?.replace(/_/g, ' '))),
      el('td', {style: 'display:flex;gap:6px;'},
        button('Ver expediente', () => {
          const body = el('div', {});
          body.append(el('p', {}, el('strong', {}, 'Sentencia / Afectado: '), inc.sentencia || inc.document_id || 'Respuesta Agente'));
          body.append(el('p', {}, el('strong', {}, 'Tipo: '), inc.issue_type, ' · ', el('strong', {}, 'Gravedad: '), inc.severity));
          if (inc.evidence) {
            body.append(el('h4', {}, 'Evidencia Técnica'), el('pre', {class: 'v5-prewrap'}, JSON.stringify(inc.evidence, null, 2)));
          }
          if (inc.action_history && inc.action_history.length) {
            body.append(el('h4', {}, 'Historial de Acciones Inmutables'));
            const histList = el('ul', {});
            for (const a of inc.action_history) {
              histList.append(el('li', {}, `[${shortDate(a.timestamp, true)}] ${a.actor}: ${a.action} — ${a.note || ''}`));
            }
            body.append(histList);
          }
          showModal('Expediente de Incidencia Jurídica', body, [button('Cerrar', closeModal)], true);
        }, {class: 'button small'}),
        inc.status !== 'cerrado' ? button('Resolver', async () => {
          const resNote = prompt('Indica cómo se solucionó la incidencia:', 'Verificado y corregido.');
          if (!resNote) return;
          try {
            await api('/despacho/calidad/incidencias/' + inc.id, {method: 'PATCH', body: {status: 'corregido', resolution_note: resNote}});
            toast('Incidencia resuelta.');
            await loadCalidadData();
            render();
          } catch (err) {
            toast('Error resolviendo: ' + err.message);
          }
        }, {class: 'button small primary'}) : null
      )
    );
    tbody.append(row);
  }

  table.append(tbody);
  tableWrap.append(table);
  wrap.append(tableWrap);
  return wrap;
}

function renderTabEvolucion(){
  const wrap = el('div', {class: 'calidad-tab-pane'});
  wrap.append(el('div', {class: 'evo-disclaimer-box'},
    el('span', {}, '⚖️'),
    el('span', {}, 'Las relaciones descubiertas automáticamente corresponden a evidencia textual preliminar. Se muestran como "Posible evolución jurisprudencial — pendiente de verificación" hasta que un profesional jurídico autorizado confirme su vigencia vinculante.')
  ));

  const rels = calidadState.evolucion;
  if (!rels.length) {
    wrap.append(el('p', {class: 'inline-help'}, 'No hay relaciones jurisprudenciales registradas. Haz clic en "Escanear relaciones del corpus" para iniciar el mapeo.'));
    wrap.append(button('Escanear relaciones del corpus', async () => {
      try {
        toast('Escaneando providencias del corpus en búsqueda de precedentes…');
        const res = await api('/despacho/calidad/evolucion/escanear?limit=10', {method: 'POST'});
        toast(`Escaneo finalizado: ${res.relations_found || 0} relaciones detectadas.`);
        await loadCalidadData();
        render();
      } catch (err) {
        toast('Error escaneando: ' + err.message);
      }
    }, {class: 'button primary small', icon: 'check'}));
    return wrap;
  }

  const tableWrap = el('div', {class: 'calidad-table-wrapper'});
  const table = el('table', {class: 'calidad-table'});
  table.append(
    el('thead', {},
      el('tr', {},
        el('th', {}, 'Origen'),
        el('th', {}, 'Destino'),
        el('th', {}, 'Relación'),
        el('th', {}, 'Evidencia Textual'),
        el('th', {}, 'Estado Jurídico'),
        el('th', {}, 'Acciones')
      )
    )
  );

  const tbody = el('tbody', {});
  for (const r of rels) {
    const isVerified = r.status === 'verificado_humano';
    const pillClass = isVerified ? 'verificado' : (r.status === 'descartado' ? 'descartado' : 'advertencia');
    const labelStatus = isVerified ? '✓ Precedente verificado' : (r.status === 'descartado' ? 'Descartado' : 'Posible evolución pendiente');

    const row = el('tr', {},
      el('td', {}, el('strong', {}, r.source_sentencia)),
      el('td', {}, el('strong', {}, r.target_sentencia)),
      el('td', {}, el('span', {class: 'calidad-pill pendiente'}, r.relation_type?.replace(/_/g, ' '))),
      el('td', {style: 'max-width:320px;font-size:0.78rem;color:#475569;'}, `"${r.evidence_quote}"`),
      el('td', {}, el('span', {class: 'calidad-pill ' + pillClass}, labelStatus)),
      el('td', {style: 'display:flex;gap:6px;'},
        !isVerified ? button('Certificar', async () => {
          const notes = prompt('Notas de certificación jurídica vinculante:', 'Confirmada regla de reiteración/unificación.');
          if (notes === null) return;
          try {
            await api(`/despacho/calidad/evolucion/${r.id}/verificar`, {method: 'POST', body: {verified: true, notes}});
            toast('Evolución jurisprudencial certificada por profesional jurídico.');
            await loadCalidadData();
            render();
          } catch (err) {
            toast('Error certificando: ' + err.message);
          }
        }, {class: 'button small primary'}) : null,
        !isVerified ? button('Descartar', async () => {
          const notes = prompt('Motivo del descarte:', 'Simple mención incidental sin alcance doctrinario.');
          if (notes === null) return;
          try {
            await api(`/despacho/calidad/evolucion/${r.id}/verificar`, {method: 'POST', body: {verified: false, notes}});
            toast('Relación descartada.');
            await loadCalidadData();
            render();
          } catch (err) {
            toast('Error descartando: ' + err.message);
          }
        }, {class: 'button small text-button report-error-btn'}) : null
      )
    );
    tbody.append(row);
  }

  table.append(tbody);
  tableWrap.append(table);
  wrap.append(tableWrap);
  return wrap;
}

init();
})();
