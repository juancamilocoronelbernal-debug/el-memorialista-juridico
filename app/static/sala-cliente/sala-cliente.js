(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const token = location.hash.slice(1);
  history.replaceState(null, '', location.pathname);
  let room = null, uploadRequest = null, objectUrl = null;
  const date = value => new Intl.DateTimeFormat('es-CO', {dateStyle:'medium',timeStyle:'short'}).format(new Date(value));
  const size = n => n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.ceil(n / 1024) + ' KB';
  function el(tag, text, className) { const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node; }
  function status(id, message, type='') { $(id).textContent=message;$(id).className='status '+type; }
  async function api(path, body, binary=false) {
    const options = {method:'POST',credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer'};
    if(body instanceof FormData)options.body=body;
    else{options.headers={'Content-Type':'application/json'};options.body=JSON.stringify(body);}
    const response=await fetch('/api/salas-v5/'+path,options);
    if(!response.ok){let detail;try{const data=await response.json();detail=typeof data.detail==='string'?data.detail:null;}catch{}throw new Error(detail||'No se pudo completar la operación. Vuelve a comprobar el acceso.');}
    if(binary){if(!(response.headers.get('Content-Type')||'').includes('application/pdf'))throw new Error('El servidor no devolvió un PDF válido.');return response.blob();}
    return response.json();
  }
  function closeViewer(){if(objectUrl){URL.revokeObjectURL(objectUrl);objectUrl=null;}$('pdf-frame').removeAttribute('src');if($('viewer').open)$('viewer').close();}
  async function documentAction(doc, mode, button){
    button.disabled=true;status('document-status','Preparando y comprobando la copia…');
    try{
      const blob=await api('document',{token,document_id:doc.id,mode},true);
      const url=URL.createObjectURL(blob);
      if(mode==='download'){
        const a=el('a');a.href=url;a.download=(doc.title||'documento').replace(/[^\p{L}\p{N} ._-]/gu,'').slice(0,100)+'.pdf';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
        status('document-status','La descarga de la copia marcada se inició.','success');
      }else{
        closeViewer();objectUrl=url;$('viewer-title').textContent=doc.title;$('pdf-frame').src=url;$('viewer').showModal();status('document-status','Copia abierta para revisión.','success');
      }
    }catch(error){status('document-status',error.message,'error');}
    finally{button.disabled=false;}
  }
  function render(data){
    room=data;$('room-title').textContent=data.title;$('description').textContent=data.description||'';$('link-label').textContent=data.link.label;
    $('expiry').textContent='Acceso hasta '+date(data.expires_at);$('access-note').textContent=data.notice;
    const list=$('document-list');list.replaceChildren();
    if(!data.documents.length)list.append(el('p','Este enlace permite aportar archivos. No tiene documentos habilitados para visualizar.','empty'));
    for(const doc of data.documents){
      const card=el('article',undefined,'document'),top=el('div',undefined,'document-top'),text=el('div');
      top.append(el('span','PDF','file-icon'));text.append(el('h3',doc.title),el('small',doc.pages+' página'+(doc.pages===1?'':'s')+' · '+size(doc.bytes)+' · Versión '+doc.source_version));top.append(text);card.append(top);
      const actions=el('div',undefined,'actions');
      if(data.link.can_view){const view=el('button','Ver documento','button secondary');view.type='button';view.addEventListener('click',()=>documentAction(doc,'view',view));actions.append(view);}
      if(data.link.can_download){const download=el('button','Descargar PDF','button');download.type='button';download.addEventListener('click',()=>documentAction(doc,'download',download));actions.append(download);}
      card.append(actions);const details=el('details');details.append(el('summary','Huella del original compartido'),el('code',doc.sha256));card.append(details);list.append(card);
    }
    $('upload-form').hidden=!data.link.can_upload;
    $('upload-permission').textContent=data.link.can_upload?'Puedes aportar documentos para que el responsable los revise. Ningún aporte reemplaza las copias de esta sala.':'Este enlace no permite aportar archivos. Pide al responsable de la sala un enlace con ese permiso.';
  }
  async function load(){
    $('loading').hidden=false;$('error').hidden=true;$('room').hidden=true;closeViewer();
    try{
      if(!/^[A-Za-z0-9_-]{43}$/.test(token))throw new Error('Abre el enlace privado completo que te compartió el responsable de la sala. El código sólo se conserva durante esta visita.');
      render(await api('view',{token}));$('room').hidden=false;
    }catch(error){$('error-message').textContent=error.message;$('error').hidden=false;}
    finally{$('loading').hidden=true;}
  }
  $('upload-file').addEventListener('change',()=>{uploadRequest=null;$('upload-submit').textContent='Enviar este archivo';status('upload-status','');});
  $('upload-form').addEventListener('submit',async event=>{
    event.preventDefault();if(!room?.link.can_upload)return;
    const file=$('upload-file').files[0];if(!file)return;
    if(!/\.(pdf|docx|txt)$/i.test(file.name)||file.size<1||file.size>10485760){status('upload-status','Selecciona un PDF, DOCX o TXT de hasta 10 MB.','error');return;}
    uploadRequest ||= crypto.randomUUID();const body=new FormData();body.set('token',token);body.set('request_id',uploadRequest);body.set('file',file);
    $('upload-submit').disabled=true;$('upload-file').disabled=true;status('upload-status','Enviando el archivo y confirmando su recepción…');
    try{
      const result=await api('upload',body);if(result.received!==true)throw new Error('La recepción del archivo no se confirmó.');
      status('upload-status','Archivo recibido para revisión.','success');$('received-list').prepend(el('p','Recibido: '+result.filename));$('upload-file').value='';uploadRequest=null;$('upload-submit').textContent='Enviar este archivo';
    }catch(error){status('upload-status',error.message,'error');$('upload-submit').textContent='Reintentar este envío';}
    finally{$('upload-submit').disabled=false;$('upload-file').disabled=false;}
  });
  $('viewer-close').addEventListener('click',closeViewer);$('viewer').addEventListener('close',()=>{if(objectUrl){URL.revokeObjectURL(objectUrl);objectUrl=null;}$('pdf-frame').removeAttribute('src');});
  $('retry').addEventListener('click',load);$('refresh').addEventListener('click',load);window.addEventListener('pagehide',closeViewer);load();
})();
