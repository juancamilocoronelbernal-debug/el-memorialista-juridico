/* ============================================================
   accesibilidad.js — Letra más grande, alto contraste y lectura
   en voz alta (con las voces que trae el propio dispositivo, para
   que el texto no salga a internet).
   ============================================================ */
window.AJ = window.AJ || {};

AJ.a11y = (function () {
  'use strict';
  const CLAVE = 'aj_accesibilidad';
  const ESCALAS = [1, 1.12, 1.25, 1.4];
  let pref = { escala: 0, contraste: false };

  function cargar() {
    try {
      const v = JSON.parse(localStorage.getItem(CLAVE) || 'null');
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        pref = { escala: Number.isInteger(v.escala) ? Math.max(0, Math.min(ESCALAS.length - 1, v.escala)) : 0, contraste: v.contraste === true };
      }
    } catch (e) { /* sin almacenamiento */ }
    aplicar();
  }
  function guardar() { try { localStorage.setItem(CLAVE, JSON.stringify(pref)); } catch (e) { /* sin almacenamiento */ } }
  function aplicar() {
    const raiz = document.documentElement;
    raiz.style.setProperty('--escala', String(ESCALAS[pref.escala]));
    if (pref.contraste) raiz.dataset.contraste = 'alto'; else delete raiz.dataset.contraste;
  }
  function letra(delta) {
    pref.escala = Math.max(0, Math.min(ESCALAS.length - 1, pref.escala + (Number.isInteger(delta) ? delta : 0)));
    aplicar(); guardar();
    return pref.escala;
  }
  function contraste(valor) {
    pref.contraste = valor === undefined ? !pref.contraste : !!valor;
    aplicar(); guardar();
    return pref.contraste;
  }
  return { cargar, letra, contraste, estado: () => Object.assign({}, pref, { maximo: ESCALAS.length - 1 }) };
})();

AJ.voz = (function () {
  'use strict';
  const sintesis = typeof window !== 'undefined' ? window.speechSynthesis : null;
  let voz = null;
  let cola = [];
  let activa = false;
  let alTerminar = null;
  let generacion = 0;
  const oyentes = [];

  // Solo voces en español instaladas en el dispositivo (localService): así el texto no se envía a ningún servidor
  function vocesLocales() {
    if (!sintesis || !sintesis.getVoices) return [];
    try { return sintesis.getVoices().filter(v => /^es([-_]|$)/i.test(v.lang || '') && v.localService); } catch (e) { return []; }
  }
  function elegir() {
    const vs = vocesLocales();
    return vs.find(v => /es[-_]CO/i.test(v.lang)) || vs.find(v => /es[-_](419|MX|US|AR|CL|PE|VE)/i.test(v.lang)) || vs.find(v => /es[-_]ES/i.test(v.lang)) || vs[0] || null;
  }
  function disponible() { return !!(sintesis && typeof window.SpeechSynthesisUtterance === 'function' && (voz || (voz = elegir()))); }
  function alCambiar(fn) { oyentes.push(fn); }
  function olvidarOyentes() { oyentes.length = 0; }
  if (sintesis) {
    const actualizar = () => { voz = elegir(); oyentes.forEach(fn => { try { fn(disponible()); } catch (e) { /* nada */ } }); };
    try { if ('onvoiceschanged' in sintesis) sintesis.addEventListener('voiceschanged', actualizar); } catch (e) { /* nada */ }
    setTimeout(actualizar, 300);
  }

  // Frases cortas: algunos navegadores cortan la lectura de textos largos
  function trozos(texto) {
    const limpio = String(texto || '').replace(/\[\[?[^\]]*\]\]?/g, ' ').replace(/_{3,}/g, ' ').replace(/\s+/g, ' ').trim();
    const frases = limpio.match(/[^.!?;:]+[.!?;:]*/g) || [];
    const out = [];
    frases.forEach(f => {
      f = f.trim();
      while (f.length > 220) { let corte = f.lastIndexOf(',', 220); if (corte < 80) corte = f.lastIndexOf(' ', 220); if (corte < 40) corte = 220; out.push(f.slice(0, corte + 1)); f = f.slice(corte + 1).trim(); }
      if (f) out.push(f);
    });
    return out;
  }
  function siguiente(turno = generacion) {
    if (!activa || turno !== generacion) return;
    const t = cola.shift();
    if (!t) { terminar(); return; }
    const u = new window.SpeechSynthesisUtterance(t);
    u.lang = (voz && voz.lang) || 'es-CO';
    if (voz) u.voice = voz;
    u.rate = 0.95;
    u.onend = () => { if (turno === generacion) siguiente(turno); };
    u.onerror = () => { if (turno === generacion) terminar(); };
    sintesis.speak(u);
  }
  function terminar() {
    const fn = alTerminar;
    activa = false; cola = []; alTerminar = null;
    if (fn) { try { fn(); } catch (e) { /* nada */ } }
  }
  function leer(texto, opciones) {
    if (!disponible()) return false;
    detener();
    cola = trozos(texto);
    activa = true;
    alTerminar = opciones && opciones.alTerminar;
    siguiente();
    return true;
  }
  function detener() {
    generacion++;
    const fn = alTerminar;
    activa = false; cola = []; alTerminar = null;
    if (sintesis) { try { sintesis.cancel(); } catch (e) { /* nada */ } }
    if (fn) { try { fn(); } catch (e) { /* nada */ } }
  }
  return { disponible, leer, detener, hablando: () => activa, alCambiar, olvidarOyentes, trozos };
})();
