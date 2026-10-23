(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const token = location.hash.slice(1);
  const notice = (text, error = false) => { $('message').textContent = text; $('message').classList.toggle('error', error); };
  const date = value => value ? new Date(value).toLocaleString('es-CO', {timeZone:'America/Bogota'}) + ' (Colombia)' : '';
  let record;
  async function call(path, body) {
    const response = await fetch('/api/firmas-publicas/' + path, {method:'POST', cache:'no-store', credentials:'omit', headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'No fue posible completar la solicitud.');
    return result;
  }
  async function load() {
    if (!/^[A-Za-z0-9_-]{43}$/.test(token)) { notice('Abre el enlace privado completo que te compartió el solicitante.', true); return; }
    try {
      record = await call('ver', {token});
      $('title').textContent = record.title;
      $('recipient').textContent = 'Solicitud dirigida a ' + record.signer_name;
      $('expiry').textContent = 'Enlace disponible hasta ' + date(record.expires_at);
      $('document').textContent = record.document_text;
      $('hash').textContent = record.document_hash;
      $('document-section').hidden = false;
      $('sign-form').hidden = record.status !== 'pending';
      if (record.status === 'signed') showSuccess(record);
      else notice('Revisa el documento completo antes de registrar tu aceptación.');
    } catch (error) { notice(error.message,true); }
  }
  function showSuccess(result) {
    $('sign-form').hidden = true;
    $('success').hidden = false;
    $('success-text').textContent = 'Aceptación registrada el ' + date(result.signed_at) + '. Identificador: ' + result.id + '.';
    notice('El documento fue aceptado.');
  }
  $('sign-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    const fields = new FormData(event.currentTarget);
    const button = event.currentTarget.querySelector('button');button.disabled = true;
    try {
      notice('Registrando tu aceptación…');
      const result = await call('aceptar', {token,name:String(fields.get('name')).trim(),email:String(fields.get('email')).trim(),consent:fields.get('consent') === 'on'});
      showSuccess(result);$('success').scrollIntoView({behavior:'smooth'});
    } catch(error) {notice(error.message,true);button.disabled=false;}
  });
  $('print').addEventListener('click', () => window.print());
  load();
})();
