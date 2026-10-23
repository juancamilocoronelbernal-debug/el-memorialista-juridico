/* Firma V5: token en fragmento, consentimiento explícito y OTP. Sin credenciales de despacho. */
(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const state={token:'',request:null,controller:null,sending:false,accepting:false,codeSent:false};
  try { state.token=decodeURIComponent(location.hash.slice(1)); } catch {}
  const text=(node,value)=>node.textContent=String(value??'');
  function make(tag,className,value){const n=document.createElement(tag);if(className)n.className=className;if(value!==undefined)n.textContent=String(value);return n;}
  function when(value){const d=new Date(value);return Number.isNaN(d.getTime())?'Fecha no disponible':new Intl.DateTimeFormat('es-CO',{dateStyle:'long',timeStyle:'short'}).format(d);}
  function message(error){return error?.message||'No se pudo completar la operación. Vuelve a intentarlo.';}
  async function api(path,payload,{blob=false,signal}={}){
    const response=await fetch('/api/firmas-v5/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:state.token,...payload}),cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',signal});
    if(!response.ok){const error=await response.json().catch(()=>({}));throw new Error(typeof error.detail==='string'?error.detail:'No se pudo completar la operación (HTTP '+response.status+').');}
    return blob?response.blob():response.json();
  }
  function busy(button,value){button.disabled=value;button.setAttribute('aria-busy',String(value));}
  function signed(result){
    $('request').hidden=true;$('loading').hidden=true;$('error').hidden=true;$('success').hidden=false;
    text($('success-message'),result.completed?'Todas las personas indicadas han completado su aceptación.':'Tu aceptación fue registrada. La solicitud puede continuar pendiente de otras personas.');
    text($('success-date'),result.signed_at?'Fecha: '+when(result.signed_at):'');
    $('success').setAttribute('tabindex','-1');$('success').focus();
  }
  function render(data){
    state.request=data;
    if(data.recipient?.status==='signed'){signed({completed:data.status==='completed',signed_at:data.recipient.signed_at});return;}
    text($('request-title'),data.title||'Solicitud de firma');text($('request-subtitle'),(data.documents?.length||0)+' '+(data.documents?.length===1?'documento para revisar':'documentos para revisar'));
    text($('request-expiry'),data.expires_at?'Vigente hasta '+when(data.expires_at):'');text($('manifest-hash'),data.manifest_hash||'');
    if(data.consent_text)text($('consent-text'),data.consent_text);
    text($('signer-label'),[data.recipient?.name,data.recipient?.email_masked].filter(Boolean).join(' · '));
    $('signer-name').value=data.recipient?.name||'';
    $('document-list').replaceChildren();$('document-hashes').replaceChildren();
    for(const [i,doc] of (data.documents||[]).entries()){
      const card=make('article','document-card'),heading=make('h3','',String(i+1).padStart(2,'0')+' · '+(doc.title||'Documento'));
      const content=make('div','document-text',doc.text||'El contenido textual no está disponible. Descarga el PDF para revisar el documento.');
      content.setAttribute('tabindex','0');content.setAttribute('role','region');content.setAttribute('aria-label','Contenido de '+(doc.title||'documento '+(i+1)));
      card.append(heading,content);$('document-list').append(card);
      const hash=make('div','document-hash');hash.append(make('strong','',doc.title||'Documento'),make('code','',doc.sha256||''));$('document-hashes').append(hash);
    }
    const enabled=data.can_sign===true;
    $('send-code').disabled=!enabled;$('accept-button').disabled=!enabled;$('otp').disabled=!enabled;$('signer-name').disabled=!enabled;$('consent').disabled=!enabled;
    text($('request-status'),enabled?'Pendiente de tu aceptación':({cancelled:'Solicitud cancelada',expired:'Solicitud vencida',completed:'Solicitud completada'}[data.status]||'Firma no disponible en este momento'));
    $('request-status').classList.toggle('inactive',!enabled);
    $('request-notice').hidden=!data.notice;if(data.notice)text($('request-notice'),data.notice);
    if(!enabled&&!data.notice){$('request-notice').hidden=false;text($('request-notice'),'Esta solicitud no admite tu firma ahora. Puede estar pendiente de un firmante anterior, vencida o cancelada. Contacta con quien la preparó.');}
    $('request').hidden=false;$('loading').hidden=true;$('error').hidden=true;$('success').hidden=true;
  }
  async function load(){
    if(state.controller)state.controller.abort();state.controller=new AbortController();state.codeSent=false;
    $('loading').hidden=false;$('error').hidden=true;$('request').hidden=true;$('success').hidden=true;
    try{
      if(!state.token||state.token.length>1000)throw new Error('El enlace no contiene un acceso válido. Abre el enlace completo que recibiste de la persona que preparó la solicitud.');
      const result=await api('view',{}, {signal:state.controller.signal});render(result);
    }catch(error){if(error.name==='AbortError')return;$('loading').hidden=true;$('error').hidden=false;text($('error-message'),message(error));}
  }
  document.querySelector('.skip-link')?.addEventListener('click',event=>{event.preventDefault();$('main').focus();$('main').scrollIntoView({block:'start'});});
  $('retry').addEventListener('click',load);
  $('send-code').addEventListener('click',async()=>{
    if(state.sending||!state.request?.can_sign)return;state.sending=true;busy($('send-code'),true);text($('code-status'),'Enviando el código…');
    try{const result=await api('otp',{});if(result.sent!==true)throw new Error('El servicio no confirmó el envío del código.');state.codeSent=true;text($('code-status'),result.notice||'Código enviado. Revisa el correo indicado, incluida la carpeta de correo no deseado.');text($('send-code'),'Solicitar otro código');$('otp').focus();}
    catch(error){text($('code-status'),message(error));}
    finally{state.sending=false;busy($('send-code'),!state.request?.can_sign);}
  });
  $('accept-form').addEventListener('submit',async event=>{
    event.preventDefault();if(state.accepting||!state.request?.can_sign)return;$('accept-error').hidden=true;
    if(!$('consent').checked){$('accept-error').hidden=false;text($('accept-error'),'Debes manifestar expresamente tu aceptación antes de firmar.');return;}
    if(!/^[0-9]{6}$/.test($('otp').value.trim())){$('accept-error').hidden=false;text($('accept-error'),'Introduce los seis dígitos del código recibido.');return;}
    state.accepting=true;busy($('accept-button'),true);
    try{const result=await api('accept',{otp:$('otp').value.trim(),name:$('signer-name').value.trim(),consent:true,manifest_hash:state.request.manifest_hash});if(result.signed!==true)throw new Error('No se confirmó la aceptación. Comprueba el estado antes de volver a firmar.');$('otp').value='';signed(result);}
    catch(error){$('accept-error').hidden=false;text($('accept-error'),message(error));}
    finally{state.accepting=false;busy($('accept-button'),!state.request?.can_sign);}
  });
  $('download').addEventListener('click',async()=>{
    busy($('download'),true);
    try{const blob=await api('document',{}, {blob:true});const url=URL.createObjectURL(blob);const a=make('a');a.href=url;a.download='documentos-para-firma.pdf';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);}
    catch(error){$('request-notice').hidden=false;text($('request-notice'),message(error));}
    finally{busy($('download'),false);}
  });
  window.addEventListener('pagehide',()=>{state.controller?.abort();state.token='';$('otp').value='';});
  window.addEventListener('pageshow',event=>{if(event.persisted){try{state.token=decodeURIComponent(location.hash.slice(1));}catch{state.token='';}load();}});
  load();
})();
