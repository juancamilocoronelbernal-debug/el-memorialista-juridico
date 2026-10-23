/* El Memorialista · integración ciudadana. No envía respuestas a servidores. */
(function () {
  'use strict';
  window.AJ = window.AJ || {};
  const normalize = s => String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const stop = new Set('que con para por una uno los las del mis sus tengo quiero necesito como hacer poner puedo ayuda ayudar porque pero desde hace esta este esto ese esa unos unas alguien'.split(' '));
  const reasons = new Map();
  function buscar(q, tipo, categoria) {
    const modulo = tipo && tipo.startsWith('modulo-') ? tipo.slice(7) : '';
    if (modulo) tipo = '';
    const query = normalize(q).slice(0, 500);
    if (AJ.buscador && AJ.buscador.buscar) {
      reasons.clear();
      const found = AJ.buscador.buscar(query, { tipo: tipo || '', categoria: categoria || '', modulo });
      return found;
    }
    const terms = [...new Set(query.split(/[^a-z0-9]+/).filter(t => t.length > 2 && !stop.has(t)))];
    reasons.clear();
    return AJ.casos.filter(c => !c.retirado && (!tipo || tipo === c.tipo) && (!categoria || categoria === c.categoria) && (!modulo || modulo === c.modulo)).map(c => {
      const title = normalize(c.titulo);
      const keywords = normalize([...(c.palabras || []), ...((AJ.sinonimos || {})[c.id] || [])].join(' '));
      const description = normalize(c.resumen);
      const entity = normalize(AJ.entidades.categoria(c.categoria).nombre);
      const label = normalize(AJ.tipos[c.tipo].nombre);
      const found = [];
      let score = 0;
      for (const t of terms) {
        let points = title.includes(t) ? 8 : keywords.includes(t) ? 5 : description.includes(t) ? 3 : entity.includes(t) || label.includes(t) ? 2 : 0;
        if (!points && t.length >= 6 && (title + ' ' + keywords).includes(t.slice(0, -2))) points = 1;
        if (points) { score += points; found.push(t); }
      }
      if (terms.length && !found.length) return null;
      if (found.length === terms.length && terms.length > 1) score += 8;
      if (query.length > 5 && title.includes(query)) score += 20;
      // Prefer the specific procedural stage explicitly described by the person.
      if (/no (me )?(responden|contestan)|sin respuesta/.test(query) && c.id === 'tut_peticion') score += 20;
      if (/gan[eé].*tutela|no cumple.*(fallo|tutela)|incumpl.*(fallo|tutela)/.test(query) && c.id === 'desacato') score += 25;
      if (/medicamento|cita|cirugia/.test(query) && ['pet_eps_servicio', 'tut_salud_servicio'].includes(c.id)) score += 8;
      if (/no .*pag.*salario|salario.*no.*pag/.test(query) && ['pet_empleador', 'tut_salarios'].includes(c.id)) score += 10;
      reasons.set(c.id, found.slice(0, 3));
      return { c, score };
    }).filter(Boolean).sort((a, b) => b.score - a.score || a.c.titulo.localeCompare(b.c.titulo, 'es')).map(x => x.c);
  }
  function datosSeguros(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Datos no válidos.');
    const out = Object.create(null);
    const entries = Object.entries(input);
    if (entries.length > 250) throw new Error('Demasiados campos.');
    for (const [key, value] of entries) {
      if (!/^[a-zA-Z][a-zA-Z0-9_]{0,69}$/.test(key) || ['__proto__', 'prototype', 'constructor'].includes(key)) throw new Error('Campo no válido.');
      if (typeof value === 'string') { if (value.length > 40000) throw new Error('Texto demasiado largo.'); out[key] = value; }
      else if (typeof value === 'number' && Number.isFinite(value)) out[key] = String(value);
      else if (Array.isArray(value) && value.length <= 150 && value.every(v => typeof v === 'string' && v.length < 2000)) out[key] = [...value];
      else if (value === null) out[key] = '';
      else throw new Error('Tipo de dato no admitido.');
    }
    return out;
  }
  const ID_SEGURO = /^[a-zA-Z0-9_-]{1,100}$/;
  function objetoPlano(value, etiqueta) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${etiqueta}: formato no válido.`);
    if (Object.keys(value).some(k => ['__proto__', 'prototype', 'constructor'].includes(k))) throw new Error(`${etiqueta}: clave no válida.`);
  }
  function fechaCalendario(value, etiqueta) {
    if (typeof value !== 'string' || !AJ.festivos.parseISO(value)) throw new Error(`${etiqueta}: fecha no válida.`);
    return value;
  }
  function fechaRegistro(value, etiqueta) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2}))?$/.test(value) || !AJ.festivos.parseISO(value.slice(0, 10)) || !Number.isFinite(Date.parse(value))) throw new Error(`${etiqueta}: fecha no válida.`);
    return new Date(value).toISOString();
  }
  function origenSeguro(value) {
    if (value === null || value === undefined) return null;
    objetoPlano(value, 'Documento de origen');
    if (Object.keys(value).some(k => !['id', 'casoId', 'titulo', 'fecha'].includes(k))) throw new Error('El origen tiene campos de otra versión. No se ha modificado la copia.');
    if (typeof value.id !== 'string' || !ID_SEGURO.test(value.id || '') || !AJ.casos.some(c => c.id === value.casoId) || typeof value.titulo !== 'string' || value.titulo.length > 350) throw new Error('Documento de origen no válido.');
    const out = { id: value.id, casoId: value.casoId, titulo: value.titulo };
    if (value.fecha) out.fecha = fechaCalendario(value.fecha, 'Fecha del documento de origen');
    return out;
  }
  function seguimientoSeguro(value) {
    if (value === null || value === undefined) return null;
    objetoPlano(value, 'Seguimiento');
    const fechas = new Set(['fecha', 'fechaRespuesta', 'fechaNotificacion', 'fechaInicioCumplimiento', 'fechaApertura', 'fechaRecepcionExpediente']);
    const textos = { numero: 300, juzgado: 500, numeroRespuesta: 300, nota: 10000 };
    const opciones = {
      canal: ['', 'ventanilla', 'correo', 'web', 'tutela_linea', 'reparto', 'otro', 'personal', 'certificado'],
      decision: ['', 'concedio', 'nego', 'parcial', 'improcedente', 'pendiente'],
      cumple: ['', 'si', 'no'],
      respuesta: ['', 'no', 'si', 'positiva', 'negativa', 'incompleta', 'prorroga', 'sin_respuesta', 'favorable', 'desfavorable'],
      unidadCumplimiento: ['', 'horas', 'dias_calendario']
    };
    // Los valores del módulo son la autoridad para formatos heredados válidos.
    if (AJ.seguimiento) {
      for (const [key, list] of [['canal', 'CANALES'], ['decision', 'DECISIONES'], ['respuesta', 'RESPUESTAS']]) {
        opciones[key] = ['', ...new Set([...(opciones[key] || []), ...(AJ.seguimiento[list] || []).map(x => x.v)])];
      }
    }
    const out = {};
    for (const [key, raw] of Object.entries(value)) {
      const v = raw === null ? '' : String(raw);
      if (typeof raw === 'object' && raw !== null) throw new Error('Seguimiento: dato no válido.');
      if (fechas.has(key)) out[key] = v ? fechaCalendario(v, 'Seguimiento') : '';
      else if (Object.hasOwn(textos, key)) { if (v.length > textos[key]) throw new Error('Un texto del seguimiento es demasiado largo.'); out[key] = v; }
      else if (Object.hasOwn(opciones, key)) { if (!opciones[key].includes(v)) throw new Error(`Seguimiento: opción no válida en ${key}.`); out[key] = v; }
      else if (key === 'actualizado') out[key] = fechaRegistro(v, 'Actualización del seguimiento');
      else if (key === 'horaNotificacion' || key === 'horaInicioCumplimiento') { if (v && !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(v)) throw new Error('La hora del seguimiento no es válida.'); out[key] = v; }
      else if (key === 'plazoCumplimiento') { if (v && (!/^\d+(?:\.\d{1,2})?$/.test(v) || +v <= 0 || +v > 3650)) throw new Error('Revisa el plazo que indica el fallo.'); out[key] = v; }
      else throw new Error(`El seguimiento contiene un campo de otra versión (${key}). Conserva el archivo original; no se ha modificado.`);
    }
    for (const key of ['fechaRespuesta', 'fechaNotificacion', 'fechaInicioCumplimiento', 'fechaApertura', 'fechaRecepcionExpediente']) {
      if (out.fecha && out[key] && out[key] < out.fecha) throw new Error('Una respuesta o notificación no puede ser anterior a la radicación registrada.');
    }
    if (out.fechaRespuesta && out.fechaNotificacion && out.fechaNotificacion < out.fechaRespuesta) throw new Error('La notificación del fallo no puede ser anterior al fallo registrado.');
    if (out.fechaRespuesta && out.fechaInicioCumplimiento && out.fechaInicioCumplimiento < out.fechaRespuesta) throw new Error('El inicio del cumplimiento no puede ser anterior al fallo registrado.');
    if (out.unidadCumplimiento === 'dias_calendario' && out.plazoCumplimiento && !Number.isInteger(+out.plazoCumplimiento)) throw new Error('El plazo en días calendario debe ser un número entero.');
    return out;
  }
  function validarRespaldo(raw) {
    const list = Array.isArray(raw) ? raw : raw && [1, 2].includes(raw.version) && Array.isArray(raw.documentos) ? raw.documentos : null;
    if (!list || list.length > 200) throw new Error('La copia debe contener hasta 200 documentos.');
    const seen = new Set();
    return list.map(item => {
      objetoPlano(item, 'Documento');
      if (Object.keys(item).some(k => !['id', 'casoId', 'titulo', 'fecha', 'datos', 'seguimiento', 'origen'].includes(k))) throw new Error('La copia tiene campos de otra versión. Conserva el original: no se ha modificado.');
      if (typeof item.id !== 'string' || !ID_SEGURO.test(item.id || '') || seen.has(item.id)) throw new Error('Identificador de documento no válido o repetido.');
      if (!AJ.casos.some(c => !c.retirado && c.id === item.casoId)) throw new Error('La copia contiene un caso no disponible.');
      if (typeof item.titulo !== 'string' || item.titulo.length > 350 || typeof item.fecha !== 'string' || !Number.isFinite(Date.parse(item.fecha))) throw new Error('Datos del documento incompletos.');
      seen.add(item.id);
      const out = { id: item.id, casoId: item.casoId, titulo: item.titulo, fecha: fechaRegistro(item.fecha, 'Documento'), datos: datosSeguros(item.datos) };
      if ('seguimiento' in item) out.seguimiento = seguimientoSeguro(item.seguimiento);
      if ('origen' in item) out.origen = origenSeguro(item.origen);
      return out;
    });
  }
  function serializarRespaldo(records) {
    return JSON.stringify({ version: 2, aplicacion: 'El Memorialista · orientación ciudadana', exportado: new Date().toISOString(), documentos: validarRespaldo(records) }, null, 2);
  }
  function fusionarRespaldo(actual, nuevos) {
    const lista = validarRespaldo(actual), entrada = validarRespaldo(nuevos);
    const canonical = value => {
      if (Array.isArray(value)) return value.map(canonical);
      if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])]));
      return value;
    };
    const iguales = (a, b) => JSON.stringify(canonical({ ...a, seguimiento: a.seguimiento || null, origen: a.origen || null })) === JSON.stringify(canonical({ ...b, seguimiento: b.seguimiento || null, origen: b.origen || null }));
    const existentes = new Map(lista.map(x => [x.id, x]));
    const conflictos = new Set(entrada.filter(reg => existentes.has(reg.id) && !iguales(existentes.get(reg.id), reg)).map(reg => reg.id));
    // If a parent receives a new id, an otherwise identical child also needs
    // its own copy. Propagate through the full imported chain before deduping.
    let cambio = true;
    while (cambio) {
      cambio = false;
      for (const reg of entrada) if (existentes.has(reg.id) && !conflictos.has(reg.id) && reg.origen && conflictos.has(reg.origen.id)) { conflictos.add(reg.id); cambio = true; }
    }
    const ids = new Set([...lista, ...entrada].map(x => x.id)), renombrados = new Map();
    for (const id of conflictos) {
      let nuevo, n = 1;
      do { nuevo = `${id.slice(0, 75)}_importado_${n++}`; } while (ids.has(nuevo));
      renombrados.set(id, nuevo); ids.add(nuevo);
    }
    let duplicados = 0, importados = 0;
    for (const reg of entrada) {
      if (existentes.has(reg.id) && !conflictos.has(reg.id)) { duplicados++; continue; }
      const copia = { ...reg, id: renombrados.get(reg.id) || reg.id };
      if (copia.origen && renombrados.has(copia.origen.id)) copia.origen = { ...copia.origen, id: renombrados.get(copia.origen.id) };
      lista.push(copia); importados++;
    }
    return { documentos: validarRespaldo(lista), importados, duplicados, conflictos: conflictos.size };
  }
  function guardarHistorial(records) {
    if (records.length > 200) throw new Error('Puedes guardar hasta 200 borradores. Exporta una copia y elimina algunos.');
    const normalized = validarRespaldo(records);
    // Medir la copia que se exportará, incluido su sobre e indentación, en bytes
    // UTF-8. Contar caracteres del almacenamiento compacto rompe la reimportación.
    if (new TextEncoder().encode(serializarRespaldo(normalized)).byteLength > 5000000) throw new Error('La copia supera el límite de 5 MB. Exporta una copia y reduce el contenido antes de guardar.');
    localStorage.setItem('aj_documentos', JSON.stringify(normalized));
  }
  function leerHistorial() {
    let raw;
    try { raw = localStorage.getItem('aj_documentos'); }
    catch (_) { throw new Error('El navegador no permite leer el historial. No se ha modificado ningún borrador.'); }
    if (raw === null) return [];
    try { return validarRespaldo(JSON.parse(raw)); }
    catch (_) { throw new Error('No se puede abrir el historial existente. Tus datos siguen intactos: descarga el historial original desde Mis borradores antes de repararlo o borrarlo.'); }
  }
  function guardarBorrador(record) {
    // Nunca interpretar un historial ilegible como uno vacío: lo sobrescribiría.
    const list = leerHistorial();
    const normalized = validarRespaldo([record])[0];
    const index = list.findIndex(item => item.id === normalized.id);
    if (index >= 0) list[index] = normalized; else list.unshift(normalized);
    guardarHistorial(list);
    return normalized;
  }
  function afterRender(main) {
    const nav = document.getElementById('nav-principal');
    const menu = document.getElementById('menu-movil');
    nav?.classList.remove('abierto');
    if (menu) menu.setAttribute('aria-expanded', 'false');
    const current = location.hash.split('/')[0];
    document.querySelectorAll('.nav a').forEach(a => { if (a.getAttribute('href') === current) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    const title = main.querySelector('h1');
    document.title = !location.hash || location.hash === '#inicio' ? 'Orientación ciudadana · El Memorialista' : (title ? title.innerText.replace(/\s+/g, ' ').trim() + ' · ' : '') + 'El Memorialista';
    if (title) { title.tabIndex = -1; title.focus({ preventScroll: true }); }
    main.querySelectorAll('a[target="_blank"]').forEach(a => a.setAttribute('rel', 'noopener noreferrer'));
    if (window.AJ_SIN_INTERNET) document.querySelectorAll('[data-online-only]').forEach(el => el.remove());
    const form = main.querySelector('#formulario');
    if (form && AJ.ui) enhanceForm(form);
    if (location.hash.startsWith('#documento')) {
      const heading = main.querySelector('h1');
      if (heading) heading.textContent = 'Tu borrador, listo para revisar';
      const note = document.createElement('p');
      note.className = 'revision-note';
      note.textContent = 'Revisa los hechos, fechas, destinatario y normas citadas. La descarga no presenta el documento ante ninguna entidad.';
      main.querySelector('.doc-cab')?.append(note);
    }
  }
  function enhanceForm(form) {
    const ui = AJ.ui;
    const required = () => ui.camposDelCaso(ui.estado.caso).flatMap(s => s.campos).filter(c => c.requerido && c.tipo !== 'info' && ui.visible(c, ui.estado.datos));
    const progress = document.createElement('div');
    progress.className = 'form-progress';
    progress.innerHTML = '<div><strong>Tu documento, paso a paso</strong><span id="progreso-texto-mejora"></span></div><progress id="progreso-caso" max="100" value="0" aria-label="Campos obligatorios completados"></progress><p>La pestaña recupera automáticamente lo que escribes. Usa Guardar borrador para conservarlo en este navegador. En un equipo compartido, borra tus datos al terminar.</p>';
    form.prepend(progress);
    const sections = [...form.querySelectorAll('fieldset.bloque')];
    const navigation = document.createElement('nav');
    navigation.className = 'section-nav'; navigation.setAttribute('aria-label', 'Secciones del formulario');
    for (const [i, section] of sections.entries()) {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'section-step';
      button.textContent = `${i + 1}. ${section.querySelector('legend')?.textContent.replace(/^\d+/, '').trim() || 'Sección'}`;
      button.addEventListener('click', () => { section.scrollIntoView({ behavior: 'smooth', block: 'start' }); const target = section.querySelector('input:not([type="hidden"]),select,textarea'); target?.focus({ preventScroll: true }); });
      navigation.append(button);
    }
    progress.append(navigation);
    const update = () => {
      if (!form.isConnected || !progress.isConnected) return;
      const all = required(); const complete = all.filter(c => { const v = ui.estado.datos[c.id]; return Array.isArray(v) ? v.length : String(v || '').trim(); }).length;
      const percent = all.length ? Math.round(complete / all.length * 100) : 100;
      document.getElementById('progreso-caso').value = percent;
      document.getElementById('progreso-texto-mejora').textContent = `${complete} de ${all.length} respuestas necesarias · ${percent}%`;
      form.querySelectorAll('.campo').forEach(el => { const input = el.querySelector('input,textarea,select'); if (input) { input.setAttribute('aria-invalid', el.classList.contains('invalido') ? 'true' : 'false'); const error = el.querySelector('.error'); if (error) { error.id = 'error-' + el.dataset.id; input.setAttribute('aria-describedby', error.id); } } });
    };
    form.addEventListener('input', update); form.addEventListener('change', update); form.addEventListener('submit', () => setTimeout(update, 0)); update();
    const save = document.createElement('button'); save.type = 'button'; save.className = 'btn'; save.textContent = 'Guardar borrador en este navegador';
    save.addEventListener('click', () => {
      try {
        const record = ui.guardarActual();
        if (!record) return;
        save.textContent = 'Borrador guardado · actualizar'; ui.aviso('Guardado solo en este navegador. Puedes retomarlo en Mis borradores.', 'ok');
      } catch (error) { ui.aviso(error.message || 'El navegador no permite guardar. Descarga tu documento.', 'error'); }
    });
    form.querySelector('.acciones-form')?.append(save);
    const preview = document.getElementById('previa');
    if (preview) { const toggle = document.createElement('button'); toggle.className = 'btn preview-toggle'; toggle.type = 'button'; toggle.textContent = 'Ver vista previa del borrador'; toggle.setAttribute('aria-expanded', 'false'); toggle.setAttribute('aria-controls', 'previa'); toggle.addEventListener('click', () => { const open = preview.classList.toggle('mostrar-previa'); toggle.setAttribute('aria-expanded', String(open)); toggle.textContent = open ? 'Ocultar vista previa' : 'Ver vista previa del borrador'; if (open) preview.scrollIntoView({ behavior: 'smooth', block: 'start' }); }); progress.append(toggle); }
  }
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('.skip-link')?.addEventListener('click', event => { event.preventDefault(); document.getElementById('app')?.focus(); });
    const menu = document.getElementById('menu-movil');
    menu?.addEventListener('click', () => { const expanded = menu.getAttribute('aria-expanded') === 'true'; menu.setAttribute('aria-expanded', String(!expanded)); document.getElementById('nav-principal')?.classList.toggle('abierto', !expanded); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') { document.getElementById('nav-principal')?.classList.remove('abierto'); menu?.setAttribute('aria-expanded', 'false'); } });
  });
  AJ.mejoras = { buscar, reasons, datosSeguros, validarRespaldo, leerHistorial, serializarRespaldo, fusionarRespaldo, guardarHistorial, guardarBorrador, seguimientoSeguro, origenSeguro, afterRender };
})();
