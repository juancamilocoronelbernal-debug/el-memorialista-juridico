/* ============================================================
   app.js — Interfaz: navegación, formularios en lenguaje común,
   vista previa, exportación, documentos guardados y guía.
   ============================================================ */
window.AJ = window.AJ || {};

(function () {
  'use strict';
  const S = { nombre: 'El Memorialista' };
  const R = AJ.red;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = s => AJ.motor.esc(s);

  const estado = { caso: null, datos: {}, generado: null, idGuardado: null, origen: null, filtros: { tipo: '', categoria: '', q: '' } };
  let temporizador = null;

  /* ---------- Iconos (SVG en línea) ---------- */
  const ICONOS = {
    carta: '<path d="M3 6h18v12H3z"/><path d="m3 7 9 6 9-6"/>',
    balanza: '<path d="M12 3v18M5 21h14M3 8l9-2 9 2"/><path d="M3 8l3 7a3 3 0 0 0 6 0L9 8M15 8l3 7a3 3 0 0 0 6 0l-3-7" transform="translate(-3 0)"/>',
    martillo: '<path d="m14 4 6 6-4 4-6-6zM11 11l-8 8 2 2 8-8M4 21h8"/>',
    flecha: '<path d="M7 17 17 7M8 7h9v9"/>',
    derecha: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    documento: '<path d="M6 2h8l5 5v15H6z"/><path d="M14 2v5h5M9 13h7M9 17h7"/>',
    alerta: '<path d="M12 3 2 21h20zM12 10v5M12 18v.5"/>',
    escudo: '<path d="M12 2 4 5v6c0 5 3.5 9 8 11 4.5-2 8-6 8-11V5z"/><path d="m9 12 2 2 4-4"/>',
    familia: '<circle cx="8" cy="7" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M2 21v-2a5 5 0 0 1 5-5h2a5 5 0 0 1 5 5v2M14 21v-1a4 4 0 0 1 4-4h1a3 3 0 0 1 3 3v2"/>',
    edificio: '<path d="M4 21V5l8-3 8 3v16M9 21v-5h6v5M8 9h2M14 9h2M8 13h2M14 13h2"/>',
    bandera: '<path d="M5 22V3M5 3h13l-3 4 3 4H5"/>',
    salud: '<path d="M12 5v14M5 12h14"/><rect x="3" y="3" width="18" height="18" rx="3"/>',
    pension: '<circle cx="9" cy="9" r="6"/><path d="M15 9a6 6 0 1 1-6 6M7 9h4M9 7v4"/>',
    trabajo: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V4h6v3M3 12h18"/>',
    servicios: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    banco: '<path d="M3 10h18L12 3zM5 10v8M9 10v8M15 10v8M19 10v8M3 21h18"/>',
    educacion: '<path d="M2 7 12 3l10 4-10 4z"/><path d="M6 9v5c0 2 3 3 6 3s6-1 6-3V9M22 7v6"/>',
    persona: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    buscar: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
    check: '<path d="m5 12 5 5 9-10"/>',
    imprimir: '<path d="M6 9V3h12v6M6 17H3v-6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6h-3M6 14h12v7H6z"/>',
    copiar: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
    descargar: '<path d="M12 3v12M6 10l6 6 6-6M4 21h16"/>',
    guardar: '<path d="M5 3h11l3 3v15H5z"/><path d="M8 3v6h7V3M8 21v-7h8v7"/>',
    editar: '<path d="M4 20h4L19 9l-4-4L4 16z"/>',
    volver: '<path d="m11 5-7 7 7 7M4 12h16"/>',
    calendario: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.5"/>',
    carpeta: '<path d="M3 6h6l2 2h10v12H3z"/>',
    libro: '<path d="M4 4h7a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H4zM20 4h-7a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h8z"/>',
    estrella: '<path d="m12 3 2.8 6 6.2.8-4.5 4.3 1.2 6.4L12 17.5 6.3 20.5l1.2-6.4L3 9.8 9.2 9z"/>',
    volumen: '<path d="M4 9v6h4l5 4V5L8 9z"/><path d="M16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12"/>',
    detener: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    brujula: '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2.2 4.8-4.8 2.2 2.2-4.8z"/>',
    campana: '<path d="M6 16v-5a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    reloj: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    candado: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    letra: '<path d="M3 19 8 5l5 14M4.5 15h7M14 19l3.5-9 3.5 9M15 16.5h5"/>',
    contraste: '<circle cx="12" cy="12" r="9"/><path d="M12 3v18a9 9 0 0 0 0-18z" fill="currentColor"/>',
    compartir: '<circle cx="18" cy="5" r="2.5"/><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="19" r="2.5"/><path d="m8.2 10.8 7.6-4.4M8.2 13.2l7.6 4.4"/>',
    pasos: '<path d="M4 6h16M4 12h10M4 18h6"/>'
  };
  function icono(n, cls) { return `<svg class="ico ${cls || ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONOS[n] || ICONOS.documento}</svg>`; }

  /* ---------- Utilidades ---------- */
  function normalizar(s) { return (s || '').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }
  function hoyISO() { const d = R.hoy(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }

  const almacen = {
    leer(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (_) { return def; } },
    guardar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (_) { return false; } },
    borrar(k) { localStorage.removeItem(k); }
  };
  const sesion = {
    leer(k) {
      try {
        const raw = sessionStorage.getItem(k);
        if (!raw) return null;
        if (raw.length > 5000000) return null;
        const b = JSON.parse(raw);
        if (!b || !AJ.casos.some(c => !c.retirado && c.id === b.casoId)) return null;
        if (b.idGuardado && !/^[a-zA-Z0-9_-]{1,100}$/.test(b.idGuardado)) return null;
        return { casoId: b.casoId, datos: AJ.mejoras.datosSeguros(b.datos), idGuardado: b.idGuardado || null, origen: AJ.mejoras.origenSeguro(b.origen), ts: b.ts };
      } catch (_) { return null; }
    },
    guardar(k, v) {
      try { sessionStorage.setItem(k, JSON.stringify(v)); return true; }
      catch (_) { const el = document.getElementById('estado-autoguardado'); if (el) el.textContent = 'La recuperación automática no está disponible. Guarda o descarga el borrador antes de salir.'; return false; }
    },
    borrar(k) { sessionStorage.removeItem(k); }
  };
  const docs = {
    lista() { return AJ.mejoras.leerHistorial(); },
    guardarLista(l) { AJ.mejoras.guardarHistorial(l); return true; },
    buscar(id) { return this.lista().find(x => x.id === id) || null; },
    poner(reg) { AJ.mejoras.guardarBorrador(reg); return true; }
  };
  const MIME_DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  const CORREOS = new Set(['correo', 'cpCorreo', 'afectadoCorreo', 'entidadCorreo']);
  const SOLO_NUMEROS_DOC = new Set(['CC', 'TI', 'RC', 'NUIP']);
  const FECHAS_PASADAS = new Set(['fechaPeticion', 'fechaNotif', 'fechaFallo', 'fechaHechos', 'fechaSolicitud', 'fechaReclamo']);
  const vacio = v => Array.isArray(v) ? !v.length : !(v && String(v).trim());
  const oscuroSistema = () => !!(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
  const temaOscuro = () => { const t = document.documentElement.dataset.theme; return t ? t === 'dark' : oscuroSistema(); };


  function aviso(msg, tipo) {
    const el = $('#aviso');
    el.textContent = msg; el.className = `aviso visible ${tipo || ''}`;
    clearTimeout(el._t); el._t = setTimeout(() => { el.className = 'aviso'; }, 3500);
  }

  function descargar(nombre, contenido, mime) {
    const blob = contenido instanceof Blob ? contenido : new Blob([contenido], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = nombre; a.rel = 'noopener'; document.body.appendChild(a); a.click();
    setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 1500);
  }

  function nombreArchivo(ext, caso, datos) {
    caso = caso || estado.caso; datos = datos || estado.datos;
    const base = `${AJ.tipos[caso.tipo].nombre} - ${datos.entidadNombre || datos.denunciado || caso.titulo}`.replace(/[^\w\sáéíóúñÁÉÍÓÚÑüÜ-]/g, '').replace(/\s+/g, ' ').trim().slice(0, 70);
    return `${base}.${ext}`;
  }

  function archivoPdf(g) { return AJ.exportar.pdf(g.bloques, g.titulo, { autor: S.nombre }); }

  function archivoDocx(g) { return AJ.exportar.docx(g.bloques, g.titulo, { autor: S.nombre }); }

  function registroActual(extra) {
    const caso = estado.caso, tipo = AJ.tipos[caso.tipo], d = estado.datos;
    const previo = estado.idGuardado ? docs.buscar(estado.idGuardado) : null;
    return Object.assign({
      id: estado.idGuardado || `doc_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`, casoId: caso.id,
      titulo: `${tipo.nombre} – ${d.entidadNombre || d.denunciado || caso.titulo}`.slice(0, 350),
      fecha: new Date().toISOString(), datos: d,
      seguimiento: (previo && previo.seguimiento) || null,
      origen: (previo && previo.origen) || (estado.origen ? { id: estado.origen.id, casoId: estado.origen.casoId, titulo: estado.origen.titulo, fecha: estado.origen.fecha } : null)
    }, extra || {});
  }

  function guardarActual(extra) {
    try {
      const reg = registroActual(extra);
      docs.poner(reg);
      estado.idGuardado = reg.id;
      actualizarInsignia();
      return reg;
    } catch (error) { aviso(error.message || 'No se pudo guardar el borrador. Tus datos anteriores no se han sustituido.', 'error'); return null; }
  }
  function pendientes() {
    const hoy = new Date();
    let lista; try { lista = docs.lista(); } catch (_) { return []; }
    return lista.map(reg => {
      const caso = AJ.casos.find(c => c.id === reg.casoId);
      if (!caso || !reg.seguimiento || !reg.seguimiento.fecha) return null;
      const st = AJ.seguimiento.estado(caso, reg.datos, reg.seguimiento, hoy);
      const urgente = st.nivel === 'peligro' || (st.fase === 'esperando' && st.restantes !== null && st.restantes <= 2) || (st.nivel === 'alerta' && st.siguientes.length);
      return urgente ? { reg, caso, st } : null;
    }).filter(Boolean);
  }

  function actualizarInsignia() {
    const enlace = $('.nav a[href="#mis-documentos"]');
    if (!enlace) return;
    const n = pendientes().length;
    let b = $('.insignia', enlace);
    if (!n) { if (b) b.remove(); return; }
    if (!b) { b = document.createElement('span'); b.className = 'insignia'; enlace.appendChild(b); }
    b.textContent = n; b.title = `${n} ${n === 1 ? 'trámite necesita' : 'trámites necesitan'} tu atención`;
  }


  function botonEscuchar(id, etiqueta) {
    return `<button type="button" class="btn btn-mini btn-escuchar" id="${id}" data-etiqueta="${esc(etiqueta)}" hidden>${icono('volumen')} <span>${esc(etiqueta)}</span></button>`;
  }

  function activarEscuchar(id, obtenerTexto) {
    const b = document.getElementById(id);
    if (!b || !AJ.voz) return;
    const mostrar = () => { b.hidden = !AJ.voz.disponible(); };
    mostrar();
    AJ.voz.alCambiar(mostrar);
    const reiniciar = () => { b.innerHTML = `${icono('volumen')} <span>${esc(b.dataset.etiqueta)}</span>`; b.classList.remove('activo'); b.setAttribute('aria-pressed', 'false'); };
    b.setAttribute('aria-pressed', 'false');
    b.addEventListener('click', () => {
      if (b.classList.contains('activo')) { AJ.voz.detener(); reiniciar(); return; }
      if (AJ.voz.leer(obtenerTexto(), { alTerminar: reiniciar })) { b.classList.add('activo'); b.setAttribute('aria-pressed', 'true'); b.innerHTML = `${icono('detener')} <span>Detener lectura</span>`; }
    });
  }


  function panelPendientes() {
    const p = pendientes();
    if (!p.length) return '';
    return `<section class="seccion pendientes" aria-labelledby="t-pendientes">
      <div class="pendientes-cab">${icono('campana')}<h2 id="t-pendientes">${p.length === 1 ? 'Un trámite necesita tu atención' : `${p.length} trámites necesitan tu atención`}</h2></div>
      <ul class="pendientes-lista">${p.slice(0, 3).map(({ reg, st }) => `<li class="nivel-${st.nivel}"><a href="#mis-documentos/${reg.id}"><strong>${esc(reg.titulo)}</strong><span>${esc(st.titulo)}</span></a></li>`).join('')}</ul>
      <p class="ayuda">Esta información solo existe en este navegador. <a href="#mis-documentos">Ver todos mis documentos</a>.</p>
    </section>`;
  }


  function vistaOrientador(main, arg) {
    const O = AJ.orientador;
    const elecciones = (arg || '').split('/').filter(x => /^\d+$/.test(x)).map(Number);
    let nodoId = 'inicio';
    const camino = [];
    let fin = null;
    for (let i = 0; i < elecciones.length; i++) {
      const nodo = O.nodos[nodoId];
      const op = nodo && nodo.opciones[elecciones[i]];
      if (!op) break;
      camino.push({ pregunta: nodo.pregunta, respuesta: op.t, hash: `#orientador${elecciones.slice(0, i).map(n => '/' + n).join('')}` });
      if (op.fin) { fin = op.fin; break; }
      nodoId = op.ir;
    }
    const base = `#orientador${elecciones.slice(0, camino.length).map(n => '/' + n).join('')}`;
    const migas = camino.length ? `<ol class="orientador-migas" aria-label="Tus respuestas">${camino.map(c => `<li><a href="${c.hash}" title="Cambiar esta respuesta"><span>${esc(c.pregunta)}</span> ${esc(c.respuesta)}</a></li>`).join('')}</ol>` : '';
    const atras = camino.length ? camino[camino.length - 1].hash : '#inicio';
    if (!fin) {
      const nodo = O.nodos[nodoId] || O.nodos.inicio;
      main.innerHTML = `
        <section class="seccion orientador">
          <a class="volver" href="${atras}">${icono('volver')} ${camino.length ? 'Volver a la pregunta anterior' : 'Volver al inicio'}</a>
          <p class="eyebrow">${icono('brujula')} Pregunta ${camino.length + 1}</p>
          <h1>${esc(nodo.pregunta)}</h1>
          ${nodo.ayuda ? `<p class="orientador-ayuda">${esc(nodo.ayuda)}</p>` : ''}
          ${botonEscuchar('b-escuchar-pregunta', 'Escuchar la pregunta y las opciones')}
          <div class="orientador-opciones">${nodo.opciones.map((o, i) => `<a class="orientador-opcion" href="${base}/${i}">${o.icono ? icono(o.icono) : ''}<span>${esc(o.t)}</span>${icono('derecha', 'ico-final')}</a>`).join('')}</div>
          ${migas}
          <p class="ayuda">¿Prefieres buscar tú? <a href="#catalogo">Ver todos los casos</a>.</p>
        </section>`;
      activarEscuchar('b-escuchar-pregunta', () => `${nodo.pregunta} ${nodo.ayuda || ''} Opciones: ${nodo.opciones.map((o, i) => `${i + 1}: ${o.t}.`).join(' ')}`);
      return;
    }
    const casos = (fin.casos || []).map(id => AJ.casos.find(c => c.id === id)).filter(Boolean);
    const [principal, ...otros] = casos;
    main.innerHTML = `
      <section class="seccion orientador">
        <a class="volver" href="${atras}">${icono('volver')} Cambiar mi última respuesta</a>
        <p class="eyebrow">${icono('brujula')} Tu resultado</p>
        <h1>${principal ? `Te recomendamos: ${esc(principal.titulo)}` : 'Busca ayuda gratuita'}</h1>
        ${fin.urgente ? `<div class="nota peligro" role="alert">${icono('alerta')}<p><strong>${esc(fin.urgente)}</strong></p></div>` : ''}
        ${fin.plazo ? `<div class="nota alerta">${icono('reloj')}<p><strong>Ojo con el plazo:</strong> ${esc(fin.plazo)}</p></div>` : ''}
        <p class="orientador-porque">${esc(fin.porque)}</p>
        ${botonEscuchar('b-escuchar-resultado', 'Escuchar la recomendación')}
        ${principal ? `<h2 class="sr">Documento recomendado</h2><div class="orientador-principal">${tarjetaCaso(principal)}<a class="btn btn-primario btn-grande" href="#caso/${principal.id}">${icono('documento')} Empezar este documento</a></div>` : ''}
        ${fin.ruta && fin.ruta.length ? `<h2>${icono('pasos')} La ruta completa</h2><ol class="pasos ruta">${fin.ruta.map(p => `<li>${esc(p)}</li>`).join('')}</ol>` : ''}
        ${otros.length ? `<h2>También te puede servir</h2><div class="grid-casos">${otros.map(tarjetaCaso).join('')}</div>` : ''}
        ${fin.ayuda ? `<div class="nota">${icono('persona')}<p>${esc(O.AYUDA_GRATIS)} <a href="#guia/directorio">Ver el directorio de ayuda gratuita</a>.</p></div>` : ''}
        ${migas}
        <p class="acciones"><a class="btn" href="#orientador">${icono('brujula')} Empezar de nuevo</a><a class="btn" href="#catalogo">${icono('buscar')} Ver todos los casos</a></p>
      </section>`;
    activarEscuchar('b-escuchar-resultado', () => `${principal ? 'Te recomendamos: ' + principal.titulo + '.' : ''} ${fin.urgente || ''} ${fin.plazo || ''} ${fin.porque} ${(fin.ruta || []).map((p, i) => `Paso ${i + 1}: ${p}`).join(' ')}`);
  }


  function errorCampo(c, datos) {
    if (c.tipo === 'info' || !visible(c, datos)) return '';
    const v = datos[c.id];
    if (c.requerido && vacio(v)) return 'Este dato es necesario.';
    if (vacio(v)) return '';
    const s = String(v).trim();
    if (CORREOS.has(c.id) && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(s)) return 'Revisa el correo: debe tener la forma nombre@correo.com.';
    if (c.id === 'numDoc' && SOLO_NUMEROS_DOC.has(datos.tipoDoc || 'CC') && !/^[\d.\s-]+$/.test(s)) return 'Escribe solo los números del documento (puedes usar puntos).';
    if (c.id === 'telefono' && /[a-zA-Z]/.test(s)) return 'Escribe solo números (puedes usar espacios).';
    if (c.tipo === 'fecha') {
      const f = AJ.festivos.parseISO(s);
      if (!f || isNaN(f) || f.getFullYear() < 1900) return 'Revisa la fecha.';
      if (FECHAS_PASADAS.has(c.id) && f > R.hoy()) return 'Esta fecha no puede ser posterior a hoy.';
    }
    return '';
  }


  function bloquePlazo(caso, d) {
    if (caso.tipo === 'denuncia') return `<div class="guia-bloque"><h3>3. Después de presentarla</h3><p>La Fiscalía no tiene un plazo fijo para responder. Pide el <strong>número de noticia criminal</strong>: con él consultas el avance. Si sigues en riesgo, pide la medida de protección en la Comisaría de Familia.</p></div>`;
    const pp = (caso.tipo === 'impugnacion' || caso.tipo === 'recurso') ? `<div id="plazo-presentar" class="plazo plazo-presentar">${d.fechaNotif ? '' : `<p>Escribe en el formulario la fecha en que te notificaron para calcular el último día para presentarlo (${caso.tipo === 'impugnacion' ? '3 días hábiles' : caso.id === 'rec_spd' && d.servicio !== 'internet' ? '5 días hábiles' : '10 días hábiles'}).</p>`}</div>` : '';
    const titulo = caso.tipo === 'tutela' || caso.tipo === 'impugnacion' || caso.tipo === 'desacato' ? '3. Hasta cuándo tiene el juez para decidir' : caso.tipo === 'recurso' ? '3. Plazos del recurso' : '3. Hasta cuándo tienen para responder';
    return `<div class="guia-bloque">
      <h3>${titulo}</h3>
      ${pp}
      <label class="etiqueta" for="fecha-radicacion">${caso.tipo === 'desacato' ? 'Fecha de apertura del incidente por el juzgado' : caso.tipo === 'impugnacion' ? 'Fecha de recepción del expediente por el superior' : 'Fecha en que lo entregas (radicas)'}</label>
      <input type="date" id="fecha-radicacion" value="${['desacato', 'impugnacion'].includes(caso.tipo) ? '' : hoyISO()}">
      <div id="plazo-resultado" class="plazo"></div>
    </div>`;
  }


  function bloqueEntregado(caso, seg) {
    if (caso.tipo === 'denuncia' || AJ.tipos[caso.tipo].contrato) return '';
    const n = 4;
    if (seg && seg.fecha) {
      return `<div class="guia-bloque entregado"><h3>${n}. Seguimiento</h3><p>Registraste que lo entregaste el <strong>${esc(R.fechaLarga(seg.fecha))}</strong>${seg.numero ? ` (radicado ${esc(seg.numero)})` : ''}.</p><p><a class="btn btn-mini" href="#mis-documentos/${esc(estado.idGuardado)}">${icono('calendario')} Ver el seguimiento</a></p></div>`;
    }
    const judicial = esJudicialCaso(caso);
    return `<div class="guia-bloque entregado">
      <h3>${n}. ¿Ya lo entregaste?</h3>
      <p>Registra la fecha y el número de radicado: verás el plazo orientativo al abrir la aplicación y podrás preparar el siguiente documento con los datos pertinentes. Se guarda solo en este navegador.</p>
      <form id="form-entregado" class="form-entregado">
        <label class="etiqueta" for="ent-fecha">Fecha en que lo entregaste</label>
        <input type="date" id="ent-fecha" value="${hoyISO()}" max="${hoyISO()}" required>
        <label class="etiqueta" for="ent-numero">${judicial ? 'Número de radicado o del proceso (si ya lo tienes)' : 'Número de radicado (si te lo dieron)'}</label>
        <input type="text" id="ent-numero" maxlength="300" autocomplete="off" placeholder="${judicial ? 'Ej.: 05001400300120260045600' : 'Ej.: 2026-RAD-004512'}">
        <label class="etiqueta" for="ent-canal">¿Cómo lo entregaste?</label>
        <select id="ent-canal">${AJ.seguimiento.CANALES.filter(c => judicial ? !['ventanilla', 'web'].includes(c.v) : !['tutela_linea', 'reparto'].includes(c.v)).map(c => `<option value="${c.v}">${esc(c.t)}</option>`).join('')}</select>
        <button type="submit" class="btn btn-primario">${icono('campana')} Guardar seguimiento</button>
      </form>
    </div>`;
  }

  function activarEntregado(caso) {
    const f = $('#form-entregado');
    if (!f) return;
    f.addEventListener('submit', e => {
      e.preventDefault();
      const fecha = $('#ent-fecha').value;
      const fd = AJ.festivos.parseISO(fecha);
      if (!fd || fd > R.hoy()) { aviso('Revisa la fecha: no puede ser posterior a hoy.', 'error'); return; }
      const seg = { fecha, numero: $('#ent-numero').value.trim(), canal: $('#ent-canal').value, actualizado: new Date().toISOString() };
      const reg = guardarActual({ seguimiento: seg });
      if (!reg) return;
      sesion.guardar('aj_borrador', { casoId: caso.id, datos: estado.datos, idGuardado: estado.idGuardado, origen: estado.origen, ts: Date.now() });
      const st = AJ.seguimiento.estado(caso, estado.datos, seg);
      aviso(st.vence ? `Listo. ${st.titulo}.` : 'Seguimiento guardado.', 'ok');
      ir(`mis-documentos/${reg.id}`);
    });
  }


  function chipEstado(st) {
    const txt = st.fase === 'borrador' ? 'Sin entregar' : st.fase === 'esperando' ? (st.restantes === 0 ? 'Vence hoy' : `${st.restantes} ${st.restantes === 1 ? 'día' : 'días'} para el plazo`) : st.fase === 'vencido' ? 'Plazo vencido' : st.fase === 'cerrado' ? 'Resuelto' : st.fase === 'respondido' ? 'Respondieron' : st.fase === 'fallo' ? 'Hay fallo' : 'Registrado';
    return `<span class="chip chip-estado nivel-${st.nivel}">${esc(txt)}</span>`;
  }


  function formularioSeguimiento(caso, seg, idDoc) {
    idDoc = esc(idDoc);
    seg = seg || {};
    const judicial = caso.tipo === 'tutela' || caso.tipo === 'impugnacion';
    const desacatoOdenuncia = caso.tipo === 'desacato' || caso.tipo === 'denuncia';
    const contrato = !!AJ.tipos[caso.tipo].contrato;
    const opt = (lista, v) => lista.map(o => `<option value="${esc(o.v)}" ${o.v === (v || '') ? 'selected' : ''}>${esc(o.t)}</option>`).join('');
    const canales = AJ.seguimiento.CANALES;
    const campo = (id, etq, ctl, cls) => `<div class="campo ${cls || 'media'}"><label class="etiqueta" for="${id}-${idDoc}">${etq}</label>${ctl}</div>`;
    const fecha = (id, v) => `<input type="date" id="${id}-${idDoc}" name="${id}" value="${esc(v || '')}" max="${hoyISO()}">`;
    let h = campo('fecha', contrato ? 'Fecha en que se firmó' : caso.tipo === 'denuncia' ? 'Fecha en que la presentaste' : 'Fecha en que lo entregaste (radicaste)', fecha('fecha', seg.fecha));
    if (!contrato) {
      h += campo('numero', judicial || caso.tipo === 'desacato' ? 'Número del proceso o radicado' : caso.tipo === 'denuncia' ? 'Número de noticia criminal' : 'Número de radicado', `<input type="text" id="numero-${idDoc}" name="numero" maxlength="300" value="${esc(seg.numero || '')}" autocomplete="off">`);
      h += campo('canal', '¿Cómo lo entregaste?', `<select id="canal-${idDoc}" name="canal">${opt([{ v: '', t: 'Escoge una opción' }, ...canales], seg.canal)}</select>`);
    }
    if (judicial) {
      h += campo('juzgado', 'Juzgado que la tiene (llega por correo)', `<input type="text" id="juzgado-${idDoc}" name="juzgado" maxlength="500" value="${esc(seg.juzgado || '')}" autocomplete="off" placeholder="Ej.: Juzgado 3 Civil Municipal de Medellín">`);
      h += campo('decision', '¿Qué decidió el juez?', `<select id="decision-${idDoc}" name="decision">${opt(AJ.seguimiento.DECISIONES, seg.decision)}</select>`);
      h += campo('fechaRespuesta', 'Fecha del fallo', fecha('fechaRespuesta', seg.fechaRespuesta));
      h += campo('fechaNotificacion', 'Fecha en que te notificaron el fallo', fecha('fechaNotificacion', seg.fechaNotificacion));
      h += campo('fechaInicioCumplimiento', 'Fecha desde la que cuenta la orden de cumplimiento', fecha('fechaInicioCumplimiento', seg.fechaInicioCumplimiento));
      h += campo('horaInicioCumplimiento', 'Hora de inicio de la orden (hora de Colombia)', `<input type="time" id="horaInicioCumplimiento-${idDoc}" name="horaInicioCumplimiento" value="${esc(seg.horaInicioCumplimiento || '')}">`);
      h += campo('plazoCumplimiento', 'Plazo exacto que ordena el fallo', `<input type="number" id="plazoCumplimiento-${idDoc}" name="plazoCumplimiento" min="0.01" max="3650" step="0.01" value="${esc(seg.plazoCumplimiento || '')}" placeholder="Solo si aparece en la orden">`);
      h += campo('unidadCumplimiento', 'Unidad del plazo de cumplimiento', `<select id="unidadCumplimiento-${idDoc}" name="unidadCumplimiento">${opt([{v:'',t:'Selecciona según el fallo'},{v:'horas',t:'Horas continuas'},{v:'dias_calendario',t:'Días calendario'}], seg.unidadCumplimiento)}</select>`);
      h += '<p class="ayuda campo completa">Copia el plazo y el hecho de inicio de la orden, según el fallo y la constancia correspondiente. La notificación que recibiste tú sirve para impugnar; no se usa automáticamente para calcular el cumplimiento de la entidad. No se presume un plazo de 48 horas. Los días calendario deben ser enteros; las horas son continuas. Si hay otra regla o condición, verifica el vencimiento con el despacho.</p>';
      h += campo('cumple', 'Si ganaste: ¿ya cumplieron?', `<select id="cumple-${idDoc}" name="cumple">${opt([{ v: '', t: 'Todavía no lo sé' }, { v: 'si', t: 'Sí, ya cumplieron' }, { v: 'no', t: 'No, no han cumplido' }], seg.cumple)}</select>`);
    } else if (!desacatoOdenuncia && !contrato) {
      h += campo('respuesta', '¿Te respondieron?', `<select id="respuesta-${idDoc}" name="respuesta">${opt(AJ.seguimiento.RESPUESTAS, seg.respuesta)}</select>`);
      h += campo('fechaRespuesta', 'Fecha de la respuesta', fecha('fechaRespuesta', seg.fechaRespuesta));
      if (caso.id === 'pet_spd') {
        h += campo('fechaNotificacion', 'Fecha en que te comunicaron o conociste la decisión', fecha('fechaNotificacion', seg.fechaNotificacion));
        h += '<p class="ayuda campo completa">Para estimar el recurso se usa la comunicación o conocimiento efectivo de la decisión, según la constancia. La fecha escrita en la carta puede ser distinta. Si importaste una copia anterior, confirma este dato antes de usar el contador.</p>';
      }
      if (caso.id === 'pet_spd') h += campo('numeroRespuesta', 'Número de la respuesta de la empresa (si la hay)', `<input type="text" id="numeroRespuesta-${idDoc}" name="numeroRespuesta" maxlength="300" value="${esc(seg.numeroRespuesta || '')}" autocomplete="off">`);
    }
    if (caso.tipo === 'desacato') h += campo('fechaApertura', 'Fecha de apertura del incidente por el juzgado (si la conoces)', fecha('fechaApertura', seg.fechaApertura));
    if (caso.tipo === 'impugnacion') h += campo('fechaRecepcionExpediente', 'Fecha en que el superior recibió el expediente (si la conoces)', fecha('fechaRecepcionExpediente', seg.fechaRecepcionExpediente));
    h += campo('nota', 'Notas para ti (opcional)', `<textarea id="nota-${idDoc}" name="nota" rows="2" maxlength="10000">${esc(seg.nota || '')}</textarea>`, 'completa');
    return `<form class="form-seguimiento campos" data-id="${esc(idDoc)}">${h}<div class="campo completa acciones-seg"><button type="submit" class="btn btn-primario">${icono('guardar')} Guardar seguimiento</button>${seg.fecha ? '<button type="button" class="btn btn-mini peligro" data-accion="quitar-seguimiento">Quitar el seguimiento</button>' : ''}</div></form>`;
  }


  function tarjetaDocumento(reg, abierto) {
    const caso = AJ.casos.find(k => k.id === reg.casoId);
    if (!caso) return `<div class="doc-item" data-id="${esc(reg.id)}"><div class="doc-item-cab"><div><strong>${esc(reg.titulo)}</strong><span>Este caso ya no existe en la plataforma.</span></div><div class="doc-botones"><button type="button" class="btn btn-mini peligro" data-accion="eliminar">Eliminar</button></div></div></div>`;
    const st = AJ.seguimiento.estado(caso, reg.datos, reg.seguimiento || {});
    const siguientes = (st.siguientes || []).map(id => AJ.casos.find(c => c.id === id)).filter(Boolean);
    return `<article class="doc-item nivel-${st.nivel}" data-id="${esc(reg.id)}" id="doc-${esc(reg.id)}">
      <div class="doc-item-cab">
        <div><strong>${esc(reg.titulo)}</strong><span>${esc(caso.titulo)} · guardado el ${esc(R.fechaLarga(new Date(reg.fecha)))}${reg.origen ? ` · sigue a "${esc(reg.origen.titulo)}"` : ''}</span></div>
        ${chipEstado(st)}
      </div>
      <div class="doc-estado">
        <p class="doc-estado-titulo">${icono(st.nivel === 'peligro' ? 'alerta' : st.nivel === 'ok' ? 'check' : 'reloj')} <strong>${esc(st.titulo)}</strong></p>
        ${st.detalle ? `<p>${esc(st.detalle)}</p>` : ''}
        ${siguientes.length ? `<div class="doc-siguientes"><p class="etiqueta">Siguiente paso, con tus datos ya llenos:</p>${siguientes.map(c => `<button type="button" class="btn btn-mini btn-siguiente" data-accion="siguiente" data-caso="${c.id}">${icono('derecha')} ${esc(c.titulo)}</button>`).join('')}</div>` : ''}
      </div>
      <div class="doc-botones">
        <button type="button" class="btn btn-mini" data-accion="abrir">${icono('editar')} Abrir</button>
        <button type="button" class="btn btn-mini" data-accion="pdf">${icono('descargar')} PDF</button>
        <button type="button" class="btn btn-mini" data-accion="word">${icono('descargar')} Word</button>
        <button type="button" class="btn btn-mini" data-accion="duplicar">${icono('copiar')} Duplicar</button>
        <button type="button" class="btn btn-mini" data-accion="seguimiento" aria-expanded="${abierto ? 'true' : 'false'}">${icono('calendario')} ${reg.seguimiento && reg.seguimiento.fecha ? 'Actualizar seguimiento' : 'Ya lo entregué'}</button>
        ${st.evento ? `<button type="button" class="btn btn-mini" data-accion="calendario">${icono('campana')} Recordatorio en mi calendario</button>` : ''}
        <button type="button" class="btn btn-mini peligro" data-accion="eliminar">Eliminar</button>
      </div>
      <div class="doc-seguimiento" ${abierto ? '' : 'hidden'}>${formularioSeguimiento(caso, reg.seguimiento, reg.id)}</div>
    </article>`;
  }


  function menuAccesibilidad() {
    const b = $('#b-accesibilidad'), panel = $('#panel-accesibilidad');
    const tema = $('#tema');
    aplicarTema(almacen.leer('aj_tema', ''));
    const pintarTema = () => { if (tema) tema.setAttribute('aria-pressed', String(temaOscuro())); };
    if (tema) {
      tema.addEventListener('click', () => { const nuevo = temaOscuro() ? 'light' : 'dark'; aplicarTema(nuevo); almacen.guardar('aj_tema', nuevo); pintarTema(); });
      pintarTema();
    }
    if (!b || !panel || !AJ.a11y) return;
    const pintar = () => {
      const st = AJ.a11y.estado();
      $('#a11y-menos').disabled = st.escala <= 0;
      $('#a11y-mas').disabled = st.escala >= st.maximo;
      $('#a11y-nivel').textContent = ['Normal', 'Grande', 'Más grande', 'Máxima'][st.escala] || '';
      $('#a11y-contraste').setAttribute('aria-pressed', String(!!st.contraste));
      pintarTema();
    };
    const cerrar = () => { panel.hidden = true; b.setAttribute('aria-expanded', 'false'); };
    b.addEventListener('click', e => { e.stopPropagation(); panel.hidden = !panel.hidden; b.setAttribute('aria-expanded', String(!panel.hidden)); if (!panel.hidden) { pintar(); $('#a11y-mas').focus(); } });
    $('#a11y-menos').addEventListener('click', () => { AJ.a11y.letra(-1); pintar(); });
    $('#a11y-mas').addEventListener('click', () => { AJ.a11y.letra(1); pintar(); });
    $('#a11y-contraste').addEventListener('click', () => { AJ.a11y.contraste(); pintar(); });
    document.addEventListener('click', e => { if (!panel.hidden && !panel.contains(e.target) && !b.contains(e.target)) cerrar(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) { cerrar(); b.focus(); } });
  }


  function aplicarTema(v) { if (v) document.documentElement.dataset.theme = v; else delete document.documentElement.dataset.theme; }

  /* ---------- Búsqueda de casos ---------- */
  /* Módulos: agrupan casos de distintos tipos alrededor de una población */
  AJ.modulos = {
    mujer: { id: 'mujer', nombre: 'Mujeres y madres cabeza de familia', icono: 'familia', descripcion: 'Violencia de pareja o intrafamiliar, acoso en el trabajo, despido en embarazo, licencia de maternidad, cuota alimentaria, declaración de madre cabeza de familia y subsidios. Documentos pensados para que ninguna mujer tenga que soportar un abuso por no saber cómo defenderse.' }
  };

  function buscarCasos(q, tipo, categoria) { return AJ.mejoras.buscar(q, tipo, categoria); }

  /* ---------- Navegación ---------- */
  function ir(hash) { location.hash = hash; }
  function ruta() {
    const h = location.hash.replace(/^#\/?/, '');
    const [vista, ...resto] = h.split('/');
    return { vista: vista || 'inicio', arg: resto.join('/') };
  }

  function render() {
    clearTimeout(temporizador);
    if (AJ.voz) { AJ.voz.detener(); AJ.voz.olvidarOyentes(); }
    const { vista, arg } = ruta();
    const main = $('#app');
    window.scrollTo({ top: 0 });
    $$('.nav a').forEach(a => a.classList.toggle('activo', a.getAttribute('href') === `#${vista}`));
    try { switch (vista) {
      case 'catalogo': vistaCatalogo(main, arg); break;
      case 'orientador': vistaOrientador(main, arg); break;
      case 'caso': vistaCaso(main, arg); break;
      case 'documento': vistaDocumento(main); break;
      case 'mis-documentos': vistaMisDocumentos(main, arg); break;
      case 'guia': vistaGuia(main, arg); break;
      case 'acerca': vistaAcerca(main, arg); break;
      default: vistaInicio(main);
    } } catch (error) {
      console.error(error);
      main.innerHTML = `<section class="seccion"><h1>No pudimos abrir esta vista</h1><p>${esc(error.message || 'Inténtalo de nuevo.')}</p><a class="btn" href="#mis-documentos">Revisar mis borradores y recuperar el historial</a><a class="btn" href="#catalogo">Volver a los casos</a></section>`;
    }
    AJ.mejoras.afterRender(main);
    actualizarInsignia();
  }

  /* ---------- Vista: inicio ---------- */
  function tarjetaCaso(c) {
    const t = AJ.tipos[c.tipo];
    return `<a class="tarjeta caso" href="#caso/${c.id}">
      <div class="tarjeta-tipo tipo-${c.tipo}">${icono(t.icono)}<span>${esc(t.nombre)}</span></div>
      <h3>${esc(c.titulo)}</h3>
      <p>${esc(c.resumen)}</p>
      ${AJ.mejoras.reasons.get(c.id)?.length ? `<span class="search-reason">Relacionado con: ${AJ.mejoras.reasons.get(c.id).map(esc).join(" · ")}</span>` : ""}
      <div class="tarjeta-pie"><span class="chip">${esc(AJ.entidades.categoria(c.categoria).nombre)}</span>${c.guia && c.guia.plazo ? `<span class="chip chip-plazo">${icono('calendario')} ${esc(plazoCorto(c))}</span>` : ''}</div>
    </a>`;
  }
  function plazoCorto(c) {
    if (c.id === 'hd_supresion') return '10 o 15 días hábiles, según solicitud';
    if (c.id === 'rec_spd') return 'Presentar: 5 o 10 días hábiles';
    const p = c.guia.plazo;
    if (p.meses) return `${p.meses} meses`;
    if (c.tipo === 'tutela') return 'Referencia: 10 días hábiles';
    return `${p.dias} días ${p.tipo === 'habiles' ? 'hábiles' : ''}`.trim();
  }

  function vistaInicio(main) {
    AJ.mejoras.reasons.clear();
    const populares = ['pet_eps_servicio', 'tut_peticion', 'pet_empleador', 'hd_reclamo', 'fam_alimentos', 'pet_spd'].map(id => AJ.casos.find(c => c.id === id)).filter(Boolean);
    const areas = [
      { t: 'Salud y EPS', s: 'Citas, medicamentos y tratamientos', ico: 'salud', href: '#catalogo/todos/eps', n: AJ.casos.filter(c => c.categoria === 'eps').length },
      { t: 'Trabajo y pensión', s: 'Salarios, prestaciones y estabilidad', ico: 'trabajo', href: '#catalogo/todos/todos/salario%20pension', n: AJ.casos.filter(c => ['empleador', 'pensiones'].includes(c.categoria)).length },
      { t: 'Familia y protección', s: 'Cuidado, alimentos y vida sin violencia', ico: 'familia', href: '#catalogo/modulo-mujer', n: AJ.casos.filter(c => c.modulo === 'mujer').length },
      { t: 'Servicios y consumo', s: 'Facturas, garantías y reclamaciones', ico: 'servicios', href: '#catalogo/todos/todos/servicios%20garantia', n: AJ.casos.filter(c => ['spd', 'financiera'].includes(c.categoria)).length }
    ];
    main.innerHTML = `
      <section class="em-hero">
        <div class="em-hero-copy"><p class="em-eyebrow"><span class="status-dot"></span> UNA PUERTA ABIERTA A TUS DERECHOS</p>
          <h1>Entiende tus derechos.<br>Da el <em>siguiente paso.</em></h1>
          <p class="em-lead">No necesitas conocer el lenguaje jurídico para empezar. Encuentra orientación para tu situación y prepara un documento, paso a paso.</p>
          <div class="hero-acciones"><a class="btn btn-primario btn-grande" href="#catalogo">Consultar mi caso <span aria-hidden="true">↗</span></a><a class="em-text-link" href="#orientador">No sé por dónde empezar <span aria-hidden="true">→</span></a></div>
          <div class="em-trust"><span>${icono('check')} Gratuito y sin registro</span><span>${icono('escudo')} Respuestas en tu navegador</span></div>
        </div>
        <div class="em-visual" aria-label="Ejemplo del recorrido: tu situación, orientación y borrador">
          <div class="em-orbit" aria-hidden="true"></div><span class="em-star" aria-hidden="true">✳</span>
          <div class="em-note em-note-back"><span>EL MEMORIALISTA / 01</span><i></i><i></i><i></i><i></i><div class="em-signature">Tu voz cuenta.</div></div>
          <div class="em-case-card"><div class="em-case-head"><span class="em-mini-mark">m·</span><span>EMPIEZA CON TUS PALABRAS</span><span aria-hidden="true">↗</span></div><p>“La EPS no me entrega<br>mis medicamentos.”</p><div class="em-case-rule"></div><div class="em-case-result"><span class="em-icon-box">${icono('documento')}</span><div><small>EXPLORA UNA RUTA</small><strong>Petición a la EPS</strong><span>Preguntas claras. Un borrador para revisar.</span></div></div><a href="#caso/pet_eps_servicio">Explorar este ejemplo <span aria-hidden="true">→</span></a></div>
          <div class="em-local-label">${icono('escudo')} Tú decides qué guardar.</div>
        </div>
      </section>
      ${panelPendientes()}
      <section class="em-search-section" aria-labelledby="titulo-busqueda"><div><p class="em-eyebrow">TU SITUACIÓN ES EL PUNTO DE PARTIDA</p><h2 id="titulo-busqueda">¿Qué está pasando?</h2></div><form class="buscador" id="buscador-inicio" role="search"><label class="sr-only" for="q-inicio">Describe tu problema, sin nombres ni números de identificación</label>${icono('buscar')}<input type="search" id="q-inicio" maxlength="500" placeholder="Ej. No me responden un derecho de petición" autocomplete="off"><button type="submit" class="btn btn-primario">Encontrar orientación <span aria-hidden="true">→</span></button></form><p class="search-help">Usa palabras cotidianas. No hace falta escribir nombres ni datos personales.</p><div class="em-examples"><span>Prueba con:</span><button type="button" data-ejemplo="no me pagan el salario">No me pagan el salario</button><button type="button" data-ejemplo="medicamento EPS">Medicamentos de la EPS</button><button type="button" data-ejemplo="reporte Datacredito">Reporte en Datacrédito</button></div><div id="resultados-inicio" class="resultados-inicio" aria-live="polite" aria-atomic="false"></div></section>
      <section class="seccion em-areas"><div class="em-section-heading"><div><p class="em-eyebrow">ORIENTACIÓN PARA LA VIDA DIARIA</p><h2>Un lugar para cada situación.</h2></div><a class="em-text-link" href="#catalogo">Explorar los ${AJ.casos.length} casos <span aria-hidden="true">↗</span></a></div><div class="em-area-grid">${areas.map((a, i) => `<a class="em-area" href="${a.href}"><span class="em-area-icon tone-${i}">${icono(a.ico)}</span><h3>${esc(a.t)}</h3><p>${esc(a.s)}</p><span class="em-area-footer">Explorar orientación <span aria-hidden="true">↗</span></span></a>`).join('')}</div></section>
      <section class="em-how seccion"><div><p class="em-eyebrow">DEL PROBLEMA AL SIGUIENTE PASO</p><h2>Más claridad.<br>Menos vueltas.</h2><p>Conserva el control de tu información y de cada decisión.</p><a class="em-text-link" href="#guia/pasos">Ver la guía completa <span aria-hidden="true">→</span></a></div><ol><li><span>01</span><div><h3>Encuentra tu situación</h3><p>Busca en tus palabras o explora el catálogo y sus guías.</p></div></li><li><span>02</span><div><h3>Responde a tu ritmo</h3><p>Preguntas sencillas construyen los hechos y las solicitudes.</p></div></li><li><span>03</span><div><h3>Revisa, descarga y actúa</h3><p>Descarga en Word, PDF o texto. Registra el trámite y prepara el siguiente paso. Tú presentas el documento.</p></div></li></ol></section>
      <section class="seccion"><div class="em-section-heading"><div><p class="em-eyebrow">RUTAS PARA EMPEZAR</p><h2>Puede que tu caso esté aquí.</h2></div><a class="em-text-link" href="#catalogo">Ver todos <span aria-hidden="true">↗</span></a></div><div class="grid-casos">${populares.map(tarjetaCaso).join('')}</div></section>
      <section class="em-help-band seccion"><span class="em-help-symbol" aria-hidden="true">↗</span><div><p class="em-eyebrow">NO TIENES QUE HACERLO A SOLAS</p><h2>Hay personas que pueden ayudarte.</h2><p>Encuentra orientación en personerías, consultorios jurídicos y entidades de atención.</p></div><a class="btn" href="#guia/directorio">Encontrar ayuda gratuita <span aria-hidden="true">→</span></a></section>
      <section class="em-scope"><span>${icono('info')}</span><p><strong>Orientación con límites claros.</strong> Esta herramienta prepara borradores y no sustituye la valoración de un abogado. Verifica los hechos y las normas aplicables antes de presentar tu documento. <a href="#acerca">Conocer el alcance</a>.</p></section>`;
    const form = $('#buscador-inicio');
    const caja = $('#resultados-inicio');
    const buscar = () => {
      const q = $('#q-inicio').value.trim();
      if (q.length < 3) { caja.innerHTML = q ? '<p class="sin-resultados">Escribe al menos tres letras para buscar tu situación.</p>' : ''; return; }
      const all = buscarCasos(q), res = all.slice(0, 6);
      caja.innerHTML = res.length ? `<p class="search-result-count">${all.length} rutas relacionadas. Elige la que coincida con tus hechos.</p><div class="grid-casos">${res.map(tarjetaCaso).join('')}</div><p class="ver-mas"><a class="btn" href="#catalogo/todos/todos/${encodeURIComponent(q)}">Ver todos los resultados</a></p>` : '<div class="sin-resultados"><h3>No encontramos una coincidencia clara.</h3><p>Prueba una entidad, un servicio o una palabra más corta. También puedes consultar la <a href="#guia/decidir">guía para elegir un documento</a> o explorar el <a href="#catalogo">catálogo completo</a>.</p></div>';
    };
    form.addEventListener('submit', e => { e.preventDefault(); buscar(); caja.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); });
    $('#q-inicio').addEventListener('input', () => { clearTimeout(temporizador); temporizador = setTimeout(buscar, 220); });
    $$('[data-ejemplo]', main).forEach(button => button.addEventListener('click', () => { $('#q-inicio').value = button.dataset.ejemplo; buscar(); $('#q-inicio').focus(); }));
  }

  /* ---------- Vista: catálogo ---------- */
  function vistaCatalogo(main, arg) {
    const [tipo = '', categoria = '', q = ''] = arg.split('/');
    estado.filtros = { tipo: tipo === 'todos' ? '' : tipo, categoria: categoria === 'todos' ? '' : categoria, q: (() => { try { return decodeURIComponent(q || '').slice(0, 500); } catch (_) { return ''; } })() };
    const dibujar = () => {
      const f = estado.filtros;
      const res = buscarCasos(f.q, f.tipo, f.categoria);
      $('#lista-casos').innerHTML = res.length ? res.map(tarjetaCaso).join('') : `<p class="sin-resultados">No hay casos con esos filtros. Prueba quitando alguno o usa la <a href="#caso/pet_general">petición general</a>.</p>`;
      $('#conteo').textContent = `${res.length} ${res.length === 1 ? 'caso' : 'casos'}`;
      $$('.chips .chip').forEach(ch => { const active = ch.dataset.tipo === f.tipo; ch.classList.toggle('activo', active); ch.setAttribute('aria-pressed', String(active)); });
    };
    main.innerHTML = `
      <section class="seccion">
        <div class="seccion-cab"><p class="em-eyebrow">ENCUENTRA UNA RUTA PARA TU SITUACIÓN</p><h1>Explora tus opciones.</h1><p>Busca un problema, una entidad o un documento. Cada caso incluye preguntas sencillas, un borrador y una guía para el siguiente paso.</p></div>
        <div class="filtros">
          <div class="buscador compacto">${icono('buscar')}<input type="search" id="q-cat" maxlength="500" value="${esc(estado.filtros.q)}" placeholder="Buscar por problema, entidad o palabra clave" aria-label="Buscar"></div>
          <select id="cat-cat" aria-label="Tipo de entidad"><option value="">Todas las entidades</option>${AJ.entidades.categorias.map(c => `<option value="${c.id}" ${c.id === estado.filtros.categoria ? 'selected' : ''}>${esc(c.nombre)}</option>`).join('')}</select>
        </div>
        <div class="chips" role="group" aria-label="Tipo de documento">
          <button class="chip" data-tipo="">Todos</button>
          ${Object.values(AJ.modulos).map(m => `<button class="chip chip-modulo" data-tipo="modulo-${m.id}">${icono(m.icono)} ${esc(m.nombre)}</button>`).join('')}
          ${Object.values(AJ.tipos).filter(t => AJ.casos.some(c => c.tipo === t.id)).map(t => `<button class="chip" data-tipo="${t.id}">${esc(t.nombre)}</button>`).join('')}
        </div>
        <p class="conteo" id="conteo" aria-live="polite"></p>
        <div class="grid-casos" id="lista-casos"></div>
      </section>`;
    $('#q-cat').addEventListener('input', e => { estado.filtros.q = e.target.value; clearTimeout(temporizador); temporizador = setTimeout(dibujar, 200); });
    $('#cat-cat').addEventListener('change', e => { estado.filtros.categoria = e.target.value; dibujar(); });
    $$('.chips .chip').forEach(ch => ch.addEventListener('click', () => { estado.filtros.tipo = ch.dataset.tipo; dibujar(); }));
    dibujar();
  }

  /* ---------- Formulario ---------- */
  // Casos en los que tiene sentido presentar sin nombre (interés general, quejas y denuncias)
  const ANONIMO_OK = new Set(['pet_municipio_servicios', 'pet_info_publica', 'pet_queja_funcionario', 'pet_municipio_policia', 'pet_general']);
  // Campos cuyo cambio redefine las peticiones marcadas por defecto
  const CAMPOS_DECIDEN = new Set(['tramite', 'problema', 'tipoServicio', 'servicio', 'quien', 'motivo', 'queQuiere', 'delitos', 'riesgo', 'lesiones', 'hijos', 'relacion', 'quienFalla', 'beneficiario', 'conductas', 'aQuien', 'respuesta']);

  function peticionesAuto(caso, d) {
    return (caso.peticiones || []).filter(o => o.fijo || (typeof o.inicial === 'function' ? !!o.inicial(d || {}) : !!o.inicial)).map(o => o.v);
  }

  function camposContrato(caso) {
    const fecha = { id: 'fechaFirma', tipo: 'fecha', etiqueta: 'Fecha en que se firma', valorInicial: hoyISO(), ancho: 'media' };
    if (caso.unilateral) {
      return [
        { id: 'quien', titulo: 'Tus datos', ayuda: 'Escribe tus datos como aparecen en la cédula: así quedarán en el documento y en la firma.', campos: AJ.campos.solicitante({ contrato: true }) },
        { id: 'situacion', titulo: 'Lo que vas a declarar', ayuda: 'Responde con tus palabras; el documento lo convierte en una declaración con el lenguaje y las normas correctas.', campos: [...caso.campos, fecha] },
        { id: 'testigos', titulo: 'Testigos (opcional)', ayuda: 'Dos personas que conozcan tu situación y firmen contigo refuerzan la declaración; no son obligatorias.', campos: AJ.campos.testigos() }
      ];
    }
    const rolCampo = { id: 'miRol', tipo: 'radio', etiqueta: '¿Cuál es tu papel en este documento?', opciones: caso.rolCampo.opciones, requerido: true, valorInicial: 'a' };
    return [
      { id: 'quien', titulo: 'Tus datos', ayuda: 'Tú eres una de las partes. Escribe tus datos como aparecen en la cédula: así quedarán en el documento y en la firma.', campos: AJ.campos.solicitante({ contrato: true }) },
      { id: 'rol', titulo: 'Tu papel y la fecha', ayuda: 'Según tu papel, el documento pondrá tus datos y los de la otra persona en el lugar correcto.', campos: [rolCampo, fecha] },
      { id: 'contraparte', titulo: 'Datos de la otra parte', ayuda: 'La persona o empresa con la que firmas. Pide su cédula (o el certificado de Cámara de Comercio si es empresa) para copiar bien los datos.', campos: AJ.campos.contraparte('la otra parte') },
      { id: 'situacion', titulo: 'Detalles del acuerdo', ayuda: 'Responde con tus palabras; el documento los convierte en cláusulas con el lenguaje y las normas correctas.', campos: caso.campos },
      { id: 'opcionales', titulo: 'Cláusulas adicionales (opcional)', ayuda: 'Marca solo las que las dos partes hayan acordado. Puedes escribir otras con tus palabras.', campos: [ { id: 'opcionales', tipo: 'checks', etiqueta: 'Cláusulas que quieres incluir', opciones: caso.opcionales || [] }, { id: 'clausulaOtra', tipo: 'textarea', etiqueta: '¿Algo más que hayan acordado? (una cláusula por línea)', ejemplo: 'Ej.: El arrendatario puede usar el parqueadero número 12.', filas: 2 } ] },
      { id: 'testigos', titulo: 'Testigos (opcional)', ayuda: 'Dos personas que vean firmar ayudan como prueba; no son obligatorias.', campos: AJ.campos.testigos() }
    ];
  }

  function camposDelCaso(caso) {
    const tipo = AJ.tipos[caso.tipo];
    if (tipo.contrato) return camposContrato(caso);
    const permiteAnonimo = tipo.permiteAnonimo && ANONIMO_OK.has(caso.id);
    const soloPropio = (caso.tipo === 'familia' || caso.tipo === 'denuncia') && !caso.permiteRepresentante;
    const secciones = [
      { id: 'quien', titulo: '¿Quién presenta el documento?', ayuda: soloPropio ? 'Este trámite lo presenta directamente la persona afectada (la madre, el padre o la víctima). Si alguien te ayuda a escribir, igual pon tus datos: tú firmas.' : permiteAnonimo ? 'A tu nombre, por otra persona que no pueda hacerlo por sí misma, o sin dar tu nombre (anónimo).' : 'A tu nombre, o por otra persona que no pueda hacerlo por sí misma.', campos: AJ.campos.solicitante({ permiteAnonimo, soloPropio }) },
      { id: 'situacion', titulo: 'Tu situación', ayuda: 'Responde con tus palabras. Lo que escribas se convertirá en hechos numerados dentro del documento.', campos: caso.campos }
    ];
    // La denuncia siempre va a la Fiscalía: no se pregunta el destinatario
    if (caso.tipo !== 'denuncia') secciones.splice(1, 0, { id: 'destino', titulo: ['tutela'].includes(caso.tipo) ? '¿A qué entidad o empresa le pones la tutela?' : ['desacato', 'impugnacion'].includes(caso.tipo) ? '¿Contra qué entidad fue la tutela?' : '¿A quién va dirigido?', ayuda: 'Escribe el nombre como aparece en sus documentos o su página web. Empieza a escribir y te sugerimos entidades conocidas.', campos: AJ.campos.destinatario(caso.destinatario || {}) });
    if (caso.tipo === 'tutela') {
      const der = { id: 'derechos', tipo: 'checks', etiqueta: 'Derechos que te están afectando (ya marcamos los normales para este caso)', opciones: caso.derechos || [] };
      const extra = [];
      if ((caso.derechos || []).length) extra.push(der);
      extra.push(...AJ.campos.tutelaExtra());
      secciones.push({ id: 'tutela', titulo: 'Derechos, urgencia y una declaración', ayuda: 'Aquí dices qué derechos te están afectando y si el juez debe ordenar algo de inmediato. La "declaración bajo juramento" solo es afirmar por escrito que no has puesto otra tutela igual; no tienes que ir a jurar a ninguna parte.', campos: extra });
    }
    secciones.push({ id: 'pide', titulo: caso.tipo === 'tutela' ? '¿Qué quieres que ordene el juez?' : '¿Qué pides?', ayuda: 'Ya marcamos lo que corresponde a lo que elegiste arriba. Revisa la lista: puedes quitar o agregar. Las que están bloqueadas son necesarias para este tipo de documento.', campos: [
      { id: 'peticiones', tipo: 'checks', etiqueta: 'Peticiones', opciones: caso.peticiones || [] },
      { id: 'peticionOtra', tipo: 'textarea', etiqueta: '¿Algo más que quieras pedir? (opcional, una petición por línea)', filas: 2 }
    ] });
    secciones.push({ id: 'anexos', titulo: 'Papeles que vas a entregar junto con el documento (anexos)', ayuda: 'Marca lo que tengas. No necesitas tenerlo todo: entrega lo que puedas y explica lo demás en el relato.', campos: [
      { id: 'anexos', tipo: 'checks', etiqueta: 'Anexos', opciones: caso.anexos || [] },
      { id: 'anexosOtros', tipo: 'textarea', etiqueta: 'Otros documentos (opcional, uno por línea)', filas: 2 }
    ] });
    return secciones;
  }

  function valorInicialCampo(c, datos) {
    if (c.tipo === 'checks') return (c.opciones || []).filter(o => o.fijo || (typeof o.inicial === 'function' ? !!o.inicial(datos || {}) : !!o.inicial)).map(o => o.v);
    if (c.valorInicial !== undefined) return c.valorInicial;
    return ''; // las preguntas de opción única sin valor inicial obligan a elegir
  }

  function inicializarDatos(caso, previos) {
    const datos = {};
    camposDelCaso(caso).forEach(s => s.campos.forEach(c => { if (c.tipo !== 'info') datos[c.id] = valorInicialCampo(c, datos); }));
    if (caso.destinatario) {
      if (caso.destinatario.nombre) datos.entidadNombre = caso.destinatario.nombre;
      if (caso.destinatario.cargo) datos.entidadCargo = caso.destinatario.cargo;
      datos.categoria = caso.destinatario.categoria || caso.categoria;
    }
    let mios = null; try { const saved = almacen.leer('aj_misdatos', null); if (saved) mios = AJ.mejoras.datosSeguros(saved); } catch (_) {}
    if (mios && !previos) ['nombre', 'genero', 'tipoDoc', 'numDoc', 'expedidaEn', 'ciudad', 'direccion', 'telefono', 'correo'].forEach(k => { if (mios[k]) datos[k] = mios[k]; });
    if (previos) Object.assign(datos, AJ.mejoras.datosSeguros(previos));
    if (!previos || !previos.peticiones) datos.peticiones = peticionesAuto(caso, datos);
    return datos;
  }

  function coincide(cond, datos) {
    const v = datos[cond.campo];
    const vals = cond.valores || [cond.valor];
    return Array.isArray(v) ? vals.some(x => v.includes(x)) : vals.includes(v);
  }
  function visible(c, datos) {
    if (c.mostrarSi && !coincide(c.mostrarSi, datos)) return false;
    if (c.ocultarSi && coincide(c.ocultarSi, datos)) return false;
    return true;
  }

  function renderCampo(c, datos) {
    const v = datos[c.id];
    const req = c.requerido ? '<span class="req" title="Obligatorio">*</span>' : '';
    const ayuda = c.ayuda ? `<p class="ayuda">${esc(c.ayuda)}</p>` : '';
    let control = '';
    switch (c.tipo) {
      case 'info': return `<div class="campo info" data-id="${c.id}" ${visible(c, datos) ? '' : 'hidden'}>${icono('info')}<p>${esc(c.texto)}</p></div>`;
      case 'textarea': control = `<textarea id="f-${c.id}" name="${c.id}" rows="${c.filas || 4}" maxlength="40000" placeholder="${esc(c.ejemplo || '')}">${esc(v || '')}</textarea>`; break;
      case 'select': control = `<select id="f-${c.id}" name="${c.id}"><option value="" ${!v ? "selected" : ""}>Selecciona una opción</option>${(c.opciones || []).map(o => `<option value="${esc(o.v)}" ${o.v === v ? 'selected' : ''}>${esc(o.t)}</option>`).join('')}</select>`; break;
      case 'radio': control = `<div class="opciones" role="group" aria-label="${esc(c.etiqueta)}">${(c.opciones || []).map(o => `<label class="opcion"><input type="radio" name="${c.id}" value="${esc(o.v)}" ${o.v === v ? 'checked' : ''}><span>${esc(o.t)}</span></label>`).join('')}</div>`; break;
      case 'checks': control = `<div class="opciones" role="group" aria-label="${esc(c.etiqueta)}">${(c.opciones || []).map(o => `<label class="opcion ${o.fijo ? 'fijo' : ''}"><input type="checkbox" name="${c.id}" value="${esc(o.v)}" ${(v || []).includes(o.v) ? 'checked' : ''} ${o.fijo ? 'disabled' : ''}><span>${esc(o.t)}</span></label>`).join('')}</div>`; break;
      case 'fecha': control = `<input type="date" id="f-${c.id}" name="${c.id}" value="${esc(v || '')}" max="2100-12-31">`; break;
      default: control = `<input type="${/correo|email/i.test(c.id) ? "email" : /telefono/i.test(c.id) ? "tel" : "text"}" maxlength="2000" id="f-${c.id}" name="${c.id}" value="${esc(v || '')}" placeholder="${esc(c.ejemplo || '')}" ${c.lista ? `list="lista-${c.lista}"` : ''} autocomplete="off">`;
    }
    const etiqueta = c.tipo === 'radio' || c.tipo === 'checks' ? `<span class="etiqueta">${esc(c.etiqueta)}${req}</span>` : `<label class="etiqueta" for="f-${c.id}">${esc(c.etiqueta)}${req}</label>`;
    return `<div class="campo ${c.ancho === 'media' ? 'media' : 'completa'}" data-id="${c.id}" ${visible(c, datos) ? '' : 'hidden'}>${etiqueta}${control}${ayuda}<p class="error" hidden>Este dato es necesario.</p></div>`;
  }

  function vistaCaso(main, id) {
    const caso = AJ.casos.find(c => c.id === id);
    if (!caso) { main.innerHTML = `<section class="seccion"><h1>No encontramos ese caso</h1><p><a href="#catalogo">Volver al catálogo</a> o <a href="#orientador">usar el orientador</a>.</p></section>`; return; }
    const tipo = AJ.tipos[caso.tipo];
    let recuperado = false;
    if (!estado.caso || estado.caso.id !== caso.id) {
      const b = sesion.leer('aj_borrador');
      if (b && b.casoId === caso.id && b.datos) {
        estado.caso = caso; estado.datos = inicializarDatos(caso, b.datos); estado.idGuardado = b.idGuardado || null; estado.origen = b.origen || null; estado.generado = null;
        recuperado = true;
      } else {
        estado.caso = caso; estado.datos = inicializarDatos(caso); estado.idGuardado = null; estado.origen = null; estado.generado = null;
      }
    }
    const secciones = camposDelCaso(caso);
    const todosCampos = secciones.flatMap(s => s.campos);
    const origenTxt = estado.origen ? `<div class="nota prellenado">${icono('check')}<p><strong>Ya llenamos parte del formulario</strong> con los datos de tu documento "${esc(estado.origen.titulo)}"${estado.origen.fecha ? `, entregado el ${esc(R.fechaLarga(estado.origen.fecha))}` : ''}. Revisa cada respuesta y completa lo que falta antes de crear el documento.</p></div>` : '';
    main.innerHTML = `
      <section class="seccion caso-cab">
        <a class="volver" href="#catalogo/${caso.tipo}">${icono('volver')} Volver a ${esc(tipo.plural.toLowerCase())}</a>
        <div class="tarjeta-tipo tipo-${caso.tipo}">${icono(tipo.icono)}<span>${esc(tipo.nombre)}</span></div>
        <h1>${esc(caso.titulo)}</h1>
        <p class="resumen">${esc(caso.resumen)}</p>
        ${caso.guia && caso.guia.nota ? `<div class="nota">${icono('info')}<p>${esc(caso.guia.nota)}</p></div>` : ''}
        ${origenTxt}
        ${recuperado ? `<div class="nota recuperado" id="nota-recuperado">${icono('guardar')}<p>Recuperamos lo que estabas escribiendo en esta pestaña. <button type="button" class="enlace" id="b-empezar-nuevo">Empezar de nuevo</button></p></div>` : ''}
      </section>
      <div class="layout-form">
        <form id="formulario" class="formulario" novalidate>
          <p class="leyenda-req">Las preguntas con <span class="req" aria-hidden="true">*</span> son obligatorias. Las demás, solo si sabes la respuesta. Al final presiona <strong>"Crear mi documento"</strong>. Lo que escribes se guarda solo en esta pestaña mientras trabajas.</p>
          ${secciones.map((s, i) => `<fieldset class="bloque" id="sec-${s.id}"><legend><span class="num" aria-hidden="true">${i + 1}</span><span class="leyenda-texto">${esc(s.titulo)}</span><span class="estado-bloque" aria-hidden="true"></span></legend><div class="bloque-ayuda-fila"><p class="bloque-ayuda">${esc(s.ayuda)}</p>${botonEscuchar(`b-escuchar-sec-${s.id}`, 'Escuchar')}</div><div class="campos">${s.campos.map(c => renderCampo(c, estado.datos)).join('')}</div></fieldset>`).join('')}
          <label class="opcion recordar"><input type="checkbox" id="recordar" ${almacen.leer('aj_misdatos', null) ? 'checked' : ''}><span>Recordar mis datos en este computador para la próxima vez (no lo marques si el computador es de una biblioteca, un colegio o un café internet)</span></label>
          <div class="acciones-form">
            <p id="estado-autoguardado" class="acciones-ayuda" role="status">Recuperación automática en esta pestaña. Puedes borrar todos tus datos en Mis borradores.</p>
            <button type="submit" class="btn btn-primario btn-grande">${icono('documento')} Crear mi documento</button>
          </div>
        </form>
        <aside class="previa" id="previa" aria-label="Vista previa del documento" tabindex="0"><div class="previa-cab"><strong>Así va quedando tu documento</strong><span>Cambia mientras respondes. Para terminar, presiona "Crear mi documento".</span></div><div class="hoja" id="hoja-previa"></div></aside>
      </div>`;

    const form = $('#formulario');
    secciones.forEach(s => activarEscuchar(`b-escuchar-sec-${s.id}`, () => `${s.titulo}. ${s.ayuda}`));
    const actualizarVisibilidad = () => { todosCampos.forEach(c => { const el = form.querySelector(`.campo[data-id="${c.id}"]`); if (el) el.hidden = !visible(c, estado.datos); }); };
    const previa = () => { clearTimeout(temporizador); temporizador = setTimeout(() => { const hoja = $('#hoja-previa'); if (!hoja || !hoja.isConnected) return; /* ya se salió del formulario */ try { estado.generado = AJ.motor.generar(caso, estado.datos); hoja.innerHTML = estado.generado.html; } catch (e) { console.error(e); } }, 350); };
    const guardarBorrador = () => sesion.guardar('aj_borrador', { casoId: caso.id, datos: estado.datos, idGuardado: estado.idGuardado, origen: estado.origen, ts: Date.now() });
    const progreso = () => {
      secciones.forEach(s => {
        const r = s.campos.filter(c => c.requerido && c.tipo !== 'info' && visible(c, estado.datos));
        const fs = document.getElementById(`sec-${s.id}`);
        if (fs) fs.classList.toggle('completo', !!r.length && r.every(c => !errorCampo(c, estado.datos)));
      });
    };
    const marcarError = (c, msg) => {
      const el = form.querySelector(`.campo[data-id="${c.id}"]`);
      if (!el) return;
      const err = $('.error', el);
      el.classList.toggle('invalido', !!msg);
      if (err) { err.hidden = !msg; if (msg) err.textContent = msg; }
      $$('input, select, textarea', el).forEach(x => { if (msg) x.setAttribute('aria-invalid', 'true'); else x.removeAttribute('aria-invalid'); });
    };

    form.addEventListener('input', e => leer(e.target));
    form.addEventListener('change', e => leer(e.target));
    form.addEventListener('focusout', e => {
      const t = e.target;
      if (!t.name) return;
      const c = todosCampos.find(x => x.id === t.name);
      if (c && !vacio(estado.datos[c.id])) marcarError(c, errorCampo(c, estado.datos));
    });
    function leer(t) {
      if (!t.name) return;
      const c = todosCampos.find(x => x.id === t.name);
      if (!c) return;
      if (c.tipo === 'checks') estado.datos[t.name] = $$(`input[name="${t.name}"]`, form).filter(i => i.checked).map(i => i.value);
      else if (c.tipo === 'radio') { if (t.checked) estado.datos[t.name] = t.value; }
      else estado.datos[t.name] = t.value;
      if (t.name === 'entidadNombre') { const cat = AJ.entidades.categoriaDeNombre(t.value); if (cat) { estado.datos.categoria = cat; const sel = $('#f-categoria', form); if (sel) sel.value = cat; } }
      if (CAMPOS_DECIDEN.has(t.name)) {
        estado.datos.peticiones = peticionesAuto(caso, estado.datos);
        $$('input[name="peticiones"]', form).forEach(i => { i.checked = estado.datos.peticiones.includes(i.value); });
      }
      const wrap = t.closest('.campo'); if (wrap && wrap.classList.contains('invalido')) marcarError(c, errorCampo(c, estado.datos));
      actualizarVisibilidad(); previa(); progreso(); guardarBorrador();
    }

    const bNuevo = $('#b-empezar-nuevo');
    if (bNuevo) bNuevo.addEventListener('click', () => {
      try { sesion.borrar('aj_borrador'); }
      catch (_) { aviso('El navegador no permitió borrar la recuperación de esta pestaña. Revisa el almacenamiento antes de empezar de nuevo.', 'error'); return; }
      estado.caso = null; estado.origen = null;
      vistaCaso(main, id);
      AJ.mejoras.afterRender(main);
      aviso('Empezamos de nuevo con el formulario vacío.', 'ok');
    });

    form.addEventListener('submit', e => {
      e.preventDefault();
      $$('.campo.invalido', form).forEach(el => { el.classList.remove('invalido'); const er = $('.error', el); if (er) er.hidden = true; });
      const fallos = todosCampos.map(c => ({ c, msg: errorCampo(c, estado.datos) })).filter(x => x.msg);
      if (fallos.length) {
        fallos.forEach(({ c, msg }) => marcarError(c, msg));
        const primero = form.querySelector('.campo.invalido');
        if (primero) { primero.scrollIntoView({ behavior: 'smooth', block: 'center' }); const ctl = $('input:not([type=hidden]), select, textarea', primero); if (ctl) setTimeout(() => ctl.focus({ preventScroll: true }), 300); }
        const faltan = fallos.filter(x => x.msg === 'Este dato es necesario.').length;
        aviso(faltan === fallos.length ? `${faltan === 1 ? 'Falta 1 dato obligatorio' : `Faltan ${faltan} datos obligatorios`} (marcados en rojo).` : `Revisa ${fallos.length} ${fallos.length === 1 ? 'respuesta marcada' : 'respuestas marcadas'} en rojo.`, 'error');
        return;
      }
      if ($('#recordar').checked) {
        const m = {}; ['nombre', 'genero', 'tipoDoc', 'numDoc', 'expedidaEn', 'ciudad', 'direccion', 'telefono', 'correo'].forEach(k => { if (estado.datos[k]) m[k] = estado.datos[k]; });
        if (!almacen.guardar('aj_misdatos', m)) aviso('No se pudieron recordar tus datos en este navegador. Puedes continuar y descargar el documento.', 'error');
      } else {
        try { almacen.borrar('aj_misdatos'); }
        catch (_) { aviso('El navegador no permitió eliminar los datos recordados. Revisa su almacenamiento al terminar.', 'error'); }
      }
      try { estado.generado = AJ.motor.generar(caso, estado.datos); }
      catch (_) { aviso('No se pudo preparar el documento. Tus respuestas siguen en el formulario; revísalas antes de intentar de nuevo.', 'error'); return; }
      guardarBorrador();
      // Si el documento ya estaba guardado, se actualiza con los cambios
      if (estado.idGuardado && !guardarActual()) return;
      ir('documento');
    });
    previa(); progreso();
  }

  /* ---------- Vista: documento ---------- */
  function calcularPlazo(caso, desdeISO, datos) {
    const p = AJ.seguimiento.plazoRespuesta(caso, datos);
    if (!p) return null;
    const desde = AJ.festivos.parseISO(desdeISO);
    if (!desde) return null;
    const vence = AJ.seguimiento.sumarPlazo(desde, p);
    const texto = p.meses ? `${p.meses} meses` : `${p.dias} días ${p.tipo === 'habiles' ? 'hábiles' : 'calendario'}`;
    const festivos = [];
    let f = new Date(desde); while (f < vence) { f = AJ.festivos.sumarDias(f, 1); const n = AJ.festivos.nombreFestivo(f); if (n && p.tipo === 'habiles') festivos.push(`${R.fechaLarga(f)} (${n})`); }
    return { vence, texto, festivos, p };
  }

  function advertenciasDe(caso, d) {
    const hoy = R.hoy();
    const advertencias = [];
    if (d.modo === 'anonimo') advertencias.push('Presentaste el documento de forma anónima: la entidad puede pedir identificación para resolver asuntos personales. Para quejas de interés general el anonimato es válido si aportas pruebas.');
    if (caso.tipo === 'tutela' && d.otraTutela === 'si') advertencias.push('Indicaste que ya presentaste otra tutela por los mismos hechos. Si ganaste y no cumplen, usa el incidente de desacato; si la perdiste, solo puedes volver a presentarla con hechos nuevos.');
    if (caso.id === 'tut_peticion') {
      if (d.medio === 'sin_prueba') advertencias.push('No indicaste una constancia de entrega de la petición (sello, radicado o correo). Aporta las pruebas disponibles y explica cómo la presentaste. Si tienes dudas sobre cómo acreditar la solicitud o existe urgencia, busca orientación jurídica; no se puede anticipar la decisión del juez.');
      const op = (AJ.camposDe('tut_peticion', 'tipoPeticion').opciones.find(o => o.v === d.tipoPeticion) || { dias: 15 });
      const f = AJ.festivos.parseISO(d.fechaPeticion);
      if (f) { const venc = AJ.festivos.sumarDiasHabiles(f, op.dias); if (venc >= hoy) advertencias.push(`Todavía no se vence el plazo de la entidad: tienen hasta el ${R.fechaLarga(venc)} para responder. Presentarla antes puede afectar su procedencia; consulta la urgencia y las circunstancias con orientación jurídica. Guarda este borrador en "Mis documentos" y preséntala a partir del día siguiente a esa fecha.`); }
    }
    if (caso.id === 'impugnacion' && d.fechaNotif) { const f = AJ.festivos.parseISO(d.fechaNotif); if (f && AJ.festivos.diasHabilesEntre(f, hoy) > 3) advertencias.push('Ya pasaron más de 3 días hábiles desde que te notificaron el fallo. Es probable que el juez rechace la impugnación por tardía. Acude hoy mismo a la Personería o la Defensoría para que te orienten.'); }
    if (caso.id === 'rec_reposicion' && d.fechaNotif) { const f = AJ.festivos.parseISO(d.fechaNotif); if (f && AJ.festivos.diasHabilesEntre(f, hoy) > 10) advertencias.push('Ya pasaron más de 10 días hábiles desde la notificación: la entidad puede rechazar el recurso por extemporáneo. Si nunca te notificaron en debida forma, dilo expresamente en el recurso (el plazo solo corre desde la notificación correcta).'); }
    if (caso.id === 'rec_spd' && d.fechaNotif) { const pp = AJ.seguimiento.plazoPresentar(caso, d); if (pp && hoy > pp.vence) advertencias.push(`El plazo orientativo de ${pp.dias} días hábiles puede haber vencido. Verifica la notificación, las circunstancias y las opciones con orientación jurídica; la aplicación no decide la admisibilidad del recurso.`); }
    if (caso.id === 'tut_habeas_data' && d.reclamo === 'no') advertencias.push('Antes de la tutela por hábeas data debes presentar el reclamo a la entidad y esperar 15 días hábiles.');
    return advertencias;
  }

  function vistaDocumento(main) {
    if (!estado.caso) {
      // Tras recargar la página: se recupera el borrador de la pestaña
      const b = sesion.leer('aj_borrador');
      const caso = b && AJ.casos.find(c => c.id === b.casoId);
      if (!caso) { ir('catalogo'); return; }
      estado.caso = caso; estado.datos = inicializarDatos(caso, b.datos); estado.idGuardado = b.idGuardado || null; estado.origen = b.origen || null;
    }
    if (!estado.generado) estado.generado = AJ.motor.generar(estado.caso, estado.datos);
    const caso = estado.caso, tipo = AJ.tipos[caso.tipo], d = estado.datos;
    const cat = AJ.entidades.categoria(d.categoria);
    const advertencias = advertenciasDe(caso, d);
    const esContrato = !!tipo.contrato;
    const primera = (caso.peticiones || []).find(o => (d.peticiones || []).includes(o.v) && !o.fijo) || (caso.peticiones || []).find(o => (d.peticiones || []).includes(o.v));
    let simple;
    if (esContrato && caso.unilateral) {
      const P = R.partesContrato(caso, d);
      simple = `Este documento es una declaración que firma <strong>${esc(P.A.nombreFirma)}</strong> bajo juramento. Léela completa y revisa que todo sea cierto antes de firmarla: abajo te decimos dónde presentarla.`;
    } else if (esContrato) {
      const P = R.partesContrato(caso, d);
      simple = `Este documento deja por escrito el acuerdo entre <strong>${esc(P.A.nombreFirma)}</strong> (${esc(P.A.rol.toLowerCase())}) y <strong>${esc(P.B.nombreFirma)}</strong> (${esc(P.B.rol.toLowerCase())}). ${caso.firmas ? 'Léelo completo y revisa que diga exactamente lo acordado antes de firmar.' : 'Las dos partes deben leerlo completo y firmarlo, y cada una se queda con una copia.'}`;
    } else if (caso.tipo === 'denuncia') {
      simple = `Este documento denuncia ante la <strong>Fiscalía</strong> a <strong>${esc(d.denunciado || 'la persona que indicaste')}</strong> y pide que te protejan. Tú solo tienes que firmarlo y entregarlo (abajo te decimos dónde). Si estás en peligro ahora, llama al 123 o al 155.`;
    } else {
      const presentacion = AJ.seguimiento.plazoPresentar(caso, d);
      const respuesta = AJ.seguimiento.plazoRespuesta(caso, d);
      const referencia = presentacion ? ` Plazo orientativo para presentarlo: ${esc(presentacion.texto)}.` : respuesta ? ` Referencia de seguimiento: ${respuesta.meses ? `${respuesta.meses} meses` : `${respuesta.dias} días ${respuesta.tipo === 'habiles' ? 'hábiles' : 'calendario'}`} desde la ${esc(respuesta.baseTexto)} para ${esc(respuesta.que)}.` : '';
      simple = `Este documento le pide a <strong>${esc(d.entidadNombre || 'la entidad')}</strong> ${primera ? esc(primera.t.replace(/^Que /, 'que ').replace(/^Mis /, 'lo que escribiste: ')) : 'lo que escribiste en el formulario'}.${referencia} Revisa el contenido y las instrucciones de firma y entrega que aparecen abajo.`;
    }
    let reg = null;
    if (estado.idGuardado) { try { reg = docs.buscar(estado.idGuardado); } catch (error) { aviso(error.message, 'error'); } }
    const seg = (reg && reg.seguimiento) || null;

    main.innerHTML = `
      <section class="seccion doc-cab">
        <a class="volver" href="#caso/${caso.id}">${icono('volver')} Volver a editar</a>
        <h1>Tu documento está listo</h1>
        <div class="simple">${icono('check')}<p id="texto-simple">${simple}</p></div>
        <div class="acciones acciones-doc">
          <button type="button" class="btn btn-primario" id="b-pdf">${icono('descargar')} Descargar PDF</button>
          <button type="button" class="btn" id="b-word">${icono('descargar')} Descargar en Word</button>
          <button type="button" class="btn" id="b-imprimir">${icono('imprimir')} Imprimir</button>
          <button type="button" class="btn" id="b-compartir" hidden>${icono('compartir')} Compartir</button>
          <button type="button" class="btn" id="b-copiar">${icono('copiar')} Copiar texto</button>
          <button type="button" class="btn" id="b-guardar">${icono('guardar')} ${reg ? 'Actualizar en Mis documentos' : 'Guardar en Mis documentos'}</button>
          <button type="button" class="btn btn-mini" id="b-txt">${icono('descargar')} Texto simple (.txt)</button>
          ${botonEscuchar('b-escuchar-doc', 'Escuchar el documento')}
        </div>
        <p class="ayuda">El PDF y el Word se crean aquí mismo, en tu dispositivo, sin enviarlos a ningún servidor. "Guardar en Mis documentos" lo guarda solo en este navegador.</p>
        ${advertencias.map(a => `<div class="nota alerta">${icono('alerta')}<p>${esc(a)}</p></div>`).join('')}
      </section>
      <div class="layout-doc">
        <div>
          <div class="hoja hoja-final" id="hoja">${estado.generado.html}</div>
          <p class="ayuda doc-pie-ayuda">${esContrato ? 'Las "cláusulas" son los puntos del acuerdo, numerados. Si algo no corresponde a lo que pactaron, vuelve a editar antes de firmar. El recuadro "Huella" es opcional: se usa cuando una de las partes no sabe firmar o para mayor seguridad.' : `${esJudicialCaso(caso) ? '"E. S. D." significa "En su despacho" (fórmula de cortesía al juez). "(REPARTO)" significa que el sistema escoge el juzgado. ' : ''}"${d.genero === 'm' ? 'El suscrito' : d.genero === 'f' ? 'La suscrita' : 'El(la) suscrito(a)'}" es la persona que firma. Las normas citadas son las que obligan a la entidad; no tienes que entenderlas todas.`}</p>
        </div>
        <aside class="guia-lateral" aria-label="Qué sigue">
          <h2>${icono('estrella')} ¿Qué sigue?</h2>
          <div class="guia-bloque">
            <h3>1. Firma y prepara</h3>
            <ul>
              <li>${['tutela', 'desacato', 'impugnacion'].includes(caso.tipo) ? 'Revisa las instrucciones del despacho o del canal judicial. Para actuaciones digitales dentro del ámbito de la Ley 2213 de 2022 no se exigen firmas manuscritas ni autenticaciones adicionales; identifica claramente a quien presenta y conserva la constancia de envío. Si lo presentas en papel, revisa los requisitos del canal.' : caso.tipo === 'denuncia' ? 'Revisa las instrucciones del canal oficial de la Fiscalía para formular la denuncia, identificarte y confirmar la información. Una denuncia puede tener requisitos distintos de los escritos judiciales civiles.' : 'Revisa las instrucciones del canal de la entidad para identificarte y presentar la solicitud. No apliques automáticamente a una petición administrativa las reglas de firma de los procesos judiciales. Conserva la constancia de recepción.'}</li>
              <li>Adjunta únicamente los documentos relacionados que realmente vayas a aportar. No se adjunta ningún archivo automáticamente.</li>
              <li>Guarda una copia completa para ti.</li>
            </ul>
          </div>
          <div class="guia-bloque">
            <h3>2. Dónde entregarlo (a eso se le dice "radicar")</h3>
            ${dondeRadicar(caso, d, cat)}
          </div>
          ${bloquePlazo(caso, d)}
          ${bloqueEntregado(caso, seg)}
          <div class="guia-bloque">
            <h3>${caso.tipo === 'denuncia' ? '4' : '5'}. Si no responden o no cumplen</h3>
            <p>${esc(caso.guia && caso.guia.siNoResponden || 'Puedes presentar una acción de tutela por violación del derecho de petición.')}</p>
            ${enlacesSiguientes(caso)}
          </div>
          <div class="guia-bloque">
            <h3>Checklist de anexos</h3>
            <ul class="checklist">${(d.anexos || []).map(v => { const o = (caso.anexos || []).find(x => x.v === v); return o ? `<li><label class="opcion"><input type="checkbox"><span>${esc(o.t)}</span></label></li>` : ''; }).join('')}${R.relatoAHechos(d.anexosOtros).map(t => `<li><label class="opcion"><input type="checkbox"><span>${esc(t)}</span></label></li>`).join('')}</ul>
          </div>
        </aside>
      </div>`;

    if (esContrato) $('.guia-lateral').innerHTML = guiaContrato(caso, d);
    const pintarPlazo = () => {
      const inp = $('#fecha-radicacion');
      if (!inp) return;
      const r = calcularPlazo(caso, inp.value, d);
      if (!r) { $('#plazo-resultado').textContent = 'Introduce la fecha de inicio indicada. Si no la conoces o existe un término especial, consulta al despacho o a la entidad.'; return; }
      $('#plazo-resultado').innerHTML = `<p><strong>${esc(r.p.quien)} tiene ${esc(r.texto)}</strong> para ${esc(r.p.que)} → vence el <strong>${esc(R.fechaLarga(r.vence))}</strong>.</p>${r.festivos.length ? `<p class="ayuda">No se cuentan sábados, domingos ni festivos: ${esc(r.festivos.join('; '))}.</p>` : ''}${caso.tipo === 'tutela' ? '<p class="ayuda">El plazo de cumplimiento es el que determine el juez. Registra la fecha, hora de notificación y el plazo exacto de la orden para hacerle seguimiento.</p>' : ''}`;
    };
    if ($('#fecha-radicacion')) { $('#fecha-radicacion').addEventListener('change', pintarPlazo); pintarPlazo(); }
    const pp = AJ.seguimiento.plazoPresentar(caso, d);
    if (pp && $('#plazo-presentar')) $('#plazo-presentar').innerHTML = `<p><strong>Último día para presentarlo: ${esc(R.fechaLarga(pp.vence))}</strong> (${esc(pp.texto)}).</p>`;

    const g = () => estado.generado;
    $('#b-pdf').addEventListener('click', () => {
      try { descargar(nombreArchivo('pdf'), archivoPdf(g()), 'application/pdf'); aviso('PDF descargado. Búscalo en la carpeta "Descargas".', 'ok'); }
      catch (e) { console.error(e); aviso(e.message || 'No se pudo crear el PDF. Usa Imprimir o descarga Word.', 'error'); }
    });
    $('#b-word').addEventListener('click', () => {
      try { descargar(nombreArchivo('docx'), archivoDocx(g()), MIME_DOCX); aviso('Documento de Word descargado.', 'ok'); }
      catch (e) { console.error(e); aviso('No se pudo crear el archivo de Word. Usa "Copiar texto" y pégalo en Word.', 'error'); }
    });
    $('#b-imprimir').addEventListener('click', () => window.print());
    if (navigator.share) {
      const bc = $('#b-compartir'); bc.hidden = false;
      bc.addEventListener('click', async () => {
        try {
          let archivo = null;
          try { archivo = new File([archivoPdf(g())], nombreArchivo('pdf'), { type: 'application/pdf' }); } catch (x) { archivo = null; }
          if (archivo && navigator.canShare && navigator.canShare({ files: [archivo] })) await navigator.share({ title: tipo.titulo, files: [archivo] });
          else await navigator.share({ title: tipo.titulo, text: g().texto });
        } catch (e) { if (e && e.name !== 'AbortError') aviso('No se pudo compartir. Descarga el PDF y envíalo como archivo.', 'error'); }
      });
    }
    $('#b-txt').addEventListener('click', () => descargar(nombreArchivo('txt'), '﻿' + g().texto, 'text/plain;charset=utf-8'));
    $('#b-copiar').addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(g().texto); aviso('Texto copiado. Pégalo en un correo o en Word.', 'ok'); }
      catch (e) { const r = document.createRange(); r.selectNodeContents($('#hoja')); const s = getSelection(); s.removeAllRanges(); s.addRange(r); aviso('Selecciona y copia el texto con Ctrl+C.', ''); }
    });
    $('#b-guardar').addEventListener('click', () => {
      if (guardarActual()) { $('#b-guardar').innerHTML = `${icono('guardar')} Actualizar en Mis documentos`; aviso('Guardado en "Mis documentos" (solo en este navegador).', 'ok'); sesion.guardar('aj_borrador', { casoId: caso.id, datos: estado.datos, idGuardado: estado.idGuardado, origen: estado.origen, ts: Date.now() }); }

    });
    activarEscuchar('b-escuchar-doc', () => `${$('#texto-simple').textContent} El documento dice: ${g().texto}`);
    activarEntregado(caso);
  }

  function esJudicialCaso(caso) { return ['tutela', 'desacato', 'impugnacion', 'denuncia'].includes(caso.tipo); }

  function guiaContrato(caso, d) {
    const g = caso.guia || {};
    if (caso.unilateral) return `<h2>${icono('estrella')} ¿Qué sigue?</h2>
      <div class="guia-bloque"><h3>1. Revisa y firma</h3><ul>
        <li>Léela completa: todo lo que dice debe ser cierto, porque la firmas bajo juramento.</li>
        <li>Imprímela (una copia por cada entidad donde la vayas a presentar, más una para ti) y fírmala en la línea de firma. La huella es opcional.</li>
        <li>Si tienes testigos, que firmen en el mismo momento.</li></ul></div>
      <div class="guia-bloque"><h3>2. Qué hacer después</h3><ul>${(g.pasos || []).map(p => `<li>${esc(p)}</li>`).join('')}</ul></div>
      ${g.nota ? `<div class="guia-bloque"><h3>3. Ten en cuenta</h3><p>${esc(g.nota)}</p></div>` : ''}
      ${enlacesSiguientes(caso)}`;
    return `<h2>${icono('estrella')} ¿Qué sigue?</h2>
      <div class="guia-bloque"><h3>1. Revisa y firma</h3><ul>
        <li>Léelo completo con la otra parte. Si algo no es lo acordado, vuelve a editar.</li>
        <li>Imprime <strong>dos copias</strong> (una para cada parte) y fírmenlas al final, en las líneas de firma. La huella es opcional.</li>
        <li>Si hay testigos, que firmen en el mismo momento.</li>
        <li>Guarda tu copia firmada y los comprobantes de pago.</li></ul></div>
      <div class="guia-bloque"><h3>2. Qué hacer después</h3><ul>${(g.pasos || []).map(p => `<li>${esc(p)}</li>`).join('')}</ul></div>
      ${g.nota ? `<div class="guia-bloque"><h3>3. Ten en cuenta</h3><p>${esc(g.nota)}</p></div>` : ''}
      <div class="guia-bloque"><h3>Si la otra parte incumple</h3><p>Primero reclama por escrito (en esta plataforma: "Reclamación al arrendador o arrendatario", "Petición al empleador" o "Reclamación directa a un vendedor", según el caso). Si no hay solución, acude a conciliación en una Casa de Justicia o centro de conciliación y, con el contrato firmado, a un consultorio jurídico universitario para la demanda.</p></div>`;
  }

  function dondeRadicar(caso, d, cat) {
    const E = esc(d.entidadNombre || 'la entidad');
    const ciudad = esc(d.ciudad || d.entidadCiudad || 'tu municipio');
    if (caso.tipo === 'tutela') {
      const juez = AJ.entidades.categoria(d.categoria).juez;
      const quien = juez === 'circuito' ? 'un juez del circuito' : juez === 'tribunal' ? 'un magistrado del tribunal' : 'un juez municipal';
      return `<ul>
      <li><strong>Por internet:</strong> <a href="https://procesojudicial.ramajudicial.gov.co/TutelaEnLinea" target="_blank" rel="noopener">Tutela en Línea</a> (Rama Judicial), gratis, las 24 horas, también desde el celular. Guarda este documento como PDF y súbelo con las fotos de la cédula y de los papeles. No necesitas firma a mano: basta con tu nombre escrito (Ley 2213 de 2022). Te llegará un correo con el juzgado asignado: revisa también la carpeta de spam.</li>
      <li><strong>En persona:</strong> Oficina Judicial de Reparto de ${ciudad} (en el palacio de justicia o en el juzgado del pueblo). La tutela se presenta donde vives tú, aunque la entidad quede en otra ciudad. Lleva el original y una copia.</li>
      <li>Como la tutela es contra ${esc(cat.nombre.split(' (')[0].toLowerCase().replace(/^eps,/, 'una EPS,').replace(/^una persona/, 'una persona'))}, la decide <strong>${quien} de ${ciudad}</strong>. El sistema escoge cuál; ningún juzgado puede negarse a recibirla.</li>
      <li>Si necesitas ayuda, la <strong>Personería</strong> de tu municipio la presenta contigo, gratis.</li></ul>`;
    }
    if (caso.tipo === 'denuncia') return `<ul><li>En cualquier <strong>Fiscalía</strong>: Unidad de Reacción Inmediata (URI, atiende 24 horas), Casa de Justicia, Centro de Atención a Víctimas (CAIVAS o CAVIF) o la Policía (también recibe denuncias). Lleva el documento impreso, tu cédula y las pruebas.</li><li><strong>Por internet:</strong> <a href="https://www.fiscalia.gov.co" target="_blank" rel="noopener">www.fiscalia.gov.co</a>, opción "Denuncia virtual (ADenunciar)".</li><li>Pide el <strong>número de noticia criminal</strong>: con él consultas el avance. Si hay peligro inmediato, llama al 123 o al 155.</li><li>Puedes pedir que un(a) funcionario(a) te reciba en privado y, si eres mujer, que te atienda personal especializado (Ley 1257 de 2008).</li></ul>`;
    if (caso.tipo === 'desacato' || caso.tipo === 'impugnacion') return `<ul><li>Ante el <strong>mismo juzgado</strong> que falló la tutela: ${esc(d.juzgado || '')}. Envíalo al correo institucional del despacho (búscalo en www.ramajudicial.gov.co) citando el radicado, o entrégalo en la secretaría del juzgado.</li>${caso.tipo === 'impugnacion' ? '<li>Recuerda: solo tienes <strong>3 días hábiles</strong> desde que te notificaron.</li>' : ''}</ul>`;
    if (caso.tipo === 'familia') return `<ul><li>En la <strong>Comisaría de Familia</strong> de tu municipio o localidad (también en Casas de Justicia) o en el Centro Zonal del ICBF. Atienden sin cita en la mayoría de casos.</li><li>Si hay peligro inmediato: Policía 123, Línea 155 (mujeres), Línea 141 (niños).</li></ul>`;
    return `<ul>
      <li><strong>En la ventanilla</strong> de ${E}: lleva dos copias y pide que le pongan sello con la fecha a la tuya. Ese sello es tu prueba de que lo entregaste.</li>
      <li><strong>Por correo electrónico</strong> al correo de PQRS o de notificaciones de la entidad (está en su página web, sección "Atención al ciudadano"). Guarda el correo enviado como prueba.</li>
      <li><strong>Por la página web</strong>: muchas entidades tienen formulario de PQRS; anota el número de radicado que te dan.</li>
      ${cat.naturaleza !== 'publica' ? '<li>Las empresas privadas también están obligadas a responder (artículos 32 y 33 de la Ley 1755 de 2015).</li>' : ''}</ul>`;
  }

  function enlacesSiguientes(caso) {
    const mapa = { peticion: ['tut_peticion'], queja: ['tut_salud_servicio', 'tut_peticion'], habeas: ['tut_habeas_data'], tutela: ['desacato', 'impugnacion'], desacato: [], impugnacion: [], recurso: ['tut_debido_proceso'], familia: ['tut_general'], contrato: [], denuncia: ['fam_proteccion', 'muj_tutela_proteccion'] };
    const porCaso = { fam_proteccion: ['muj_denuncia', 'muj_tutela_proteccion'], muj_acoso_laboral: ['muj_denuncia', 'tut_estabilidad'], muj_licencia_maternidad: ['tut_estabilidad', 'queja_supersalud'], muj_salud_sexual: ['tut_salud_servicio', 'queja_supersalud'], muj_cabeza_familia: ['tut_peticion', 'muj_declaracion_cabeza'], muj_declaracion_cabeza: ['muj_cabeza_familia'], fam_alimentos: ['fam_custodia', 'tut_general'], fam_custodia: ['fam_alimentos', 'fam_proteccion'], muj_tutela_proteccion: ['desacato', 'impugnacion'] };
    const ids = (porCaso[caso.id] || mapa[caso.tipo] || []).filter(id => id !== caso.id);
    if (!ids.length) return '';
    return `<ul class="enlaces">${ids.map(id => { const c = AJ.casos.find(x => x.id === id); return c ? `<li><a href="#caso/${c.id}">${icono('flecha')} ${esc(c.titulo)}</a></li>` : ''; }).join('')}</ul>`;
  }

  /* ---------- Vista: mis documentos ---------- */
  function vistaMisDocumentos(main, arg) {
    let lista = [], original = null, errorHistorial = '';
    try { original = localStorage.getItem('aj_documentos'); lista = docs.lista(); }
    catch (error) { errorHistorial = error.message || 'No se pudo leer el historial; tus datos siguen intactos.'; }
    const hoy = new Date(), orden = { peligro: 0, alerta: 1, neutro: 2, ok: 3 };
    const conEstado = lista.map(reg => { const caso = AJ.casos.find(c => c.id === reg.casoId); return { reg, st: caso ? AJ.seguimiento.estado(caso, reg.datos, reg.seguimiento || {}, hoy) : { nivel: 'neutro' } }; });
    conEstado.sort((a, b) => (orden[a.st.nivel] - orden[b.st.nivel]) || (new Date(b.reg.fecha) - new Date(a.reg.fecha)));
    main.innerHTML = `
      <section class="seccion">
        <div class="seccion-cab"><p class="em-eyebrow">TU ESPACIO EN ESTE DISPOSITIVO</p><h1>Mis borradores y trámites</h1><p>Conserva documentos, registra respuestas y consulta el siguiente paso. Todo queda en este navegador: otras personas que lo utilicen podrían abrirlo. Exporta una copia para conservarlo y borra tus datos al terminar en un equipo compartido.</p><p class="ayuda">El seguimiento utiliza las fechas que tú registras; no consulta expedientes ni recibe respuestas automáticamente. Los avisos se muestran al abrir la aplicación. Para un recordatorio externo, descarga el calendario e impórtalo.</p></div>
        <div class="acciones">
          <button type="button" class="btn" id="b-exportar" ${lista.length || (errorHistorial && original !== null) ? '' : 'disabled'}>${icono('descargar')} ${errorHistorial ? 'Descargar historial original' : 'Exportar copia de seguridad'}</button>
          <button type="button" class="btn" id="b-importar">${icono('carpeta')} Importar copia</button><input type="file" id="i-importar" accept="application/json,.json" hidden>
          <button type="button" class="btn peligro" id="b-borrar-todo">Borrar todos mis datos de este computador</button>
        </div>
        ${errorHistorial ? `<div class="nota-legal" role="alert"><h2>Conserva tu historial antes de continuar</h2><p>${esc(errorHistorial)}</p><p>Puedes descargar el archivo original sin cambios. No se sobrescribe al guardar o importar. Conserva esa copia antes de reparar o borrar tus datos.</p></div>` : ''}
        ${lista.length > 3 ? `<div class="buscador compacto filtro-docs">${icono('buscar')}<input type="search" id="q-docs" maxlength="500" placeholder="Filtrar por entidad, tipo o nombre" aria-label="Filtrar mis documentos" autocomplete="off"></div>` : ''}
        ${lista.length ? `<div class="lista-docs" id="lista-docs">${conEstado.map(x => tarjetaDocumento(x.reg, x.reg.id === arg)).join('')}</div>` : errorHistorial ? '' : `<p class="sin-resultados">Aún no has guardado borradores. Puedes guardar uno mientras respondes o después de generarlo, y añadir su seguimiento cuando lo presentes.</p>`}
      </section>`;
    const seguro = fn => ev => { try { return fn(ev); } catch (error) { aviso(error.message || 'No se pudo completar la operación. Conserva una copia de tus documentos.', 'error'); } };
    if (arg && /^[a-zA-Z0-9_-]{1,100}$/.test(arg)) { const el = document.getElementById(`doc-${arg}`); if (el) setTimeout(() => el.isConnected && el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60); }
    $('#b-exportar').addEventListener('click', seguro(() => {
      if (errorHistorial) { if (original !== null) descargar(`el-memorialista-historial-original-${hoyISO()}.json`, original, 'application/json'); return; }
      descargar(`el-memorialista-documentos-${hoyISO()}.json`, AJ.mejoras.serializarRespaldo(docs.lista()), 'application/json');
    }));
    $('#b-importar').addEventListener('click', () => $('#i-importar').click());
    $('#b-borrar-todo').addEventListener('click', seguro(e => {
      const b = e.currentTarget;
      if (!b.dataset.confirmar) { b.dataset.confirmar = '1'; b.textContent = '¿Seguro? Se borran documentos, seguimientos y datos guardados. Clic de nuevo'; return; }
      // Clear recovery first; never report success if any operation is refused.
      sesion.borrar('aj_borrador');
      localStorage.removeItem('aj_documentos'); localStorage.removeItem('aj_misdatos');
      estado.caso = null; estado.datos = {}; estado.idGuardado = null; estado.origen = null; estado.generado = null;
      aviso('Documentos, seguimientos y datos personales borrados de este navegador.', 'ok'); render();
    }));
    const filtro = $('#q-docs');
    if (filtro) filtro.addEventListener('input', () => {
      const q = normalizar(filtro.value);
      $$('.doc-item', main).forEach(el => { el.hidden = !!(q && !normalizar(el.textContent).includes(q)); });
    });
    $('#i-importar').addEventListener('change', e => {
      const input = e.target, f = input.files[0]; if (!f) return;
      if (f.size > 5000000) { aviso('La copia supera el límite de 5 MB.', 'error'); input.value = ''; return; }
      const r = new FileReader();
      r.onload = () => {
        try {
          const nuevos = AJ.mejoras.validarRespaldo(JSON.parse(r.result));
          const mezcla = AJ.mejoras.fusionarRespaldo(docs.lista(), nuevos);
          docs.guardarLista(mezcla.documentos);
          aviso(`${mezcla.importados} borradores importados con su seguimiento; ${mezcla.duplicados} copias idénticas omitidas.${mezcla.conflictos ? ` Se conservaron ambas versiones en ${mezcla.conflictos} coincidencias de identificador.` : ''}`, 'ok'); render();
        } catch (error) { aviso(error.message || 'El archivo no es una copia válida. No se ha modificado el historial.', 'error'); }
        finally { input.value = ''; }
      };
      r.onerror = () => { aviso('No se pudo leer el archivo; vuelve a seleccionarlo.', 'error'); input.value = ''; };
      r.readAsText(f);
    });
    $$('.doc-item', main).forEach(item => {
      item.addEventListener('click', seguro(ev => {
        const b = ev.target.closest('button[data-accion]');
        if (!b || !item.contains(b)) return;
        const id = item.dataset.id, reg = docs.buscar(id);
        if (!reg) return;
        const caso = AJ.casos.find(c => c.id === reg.casoId), accion = b.dataset.accion;
        if (accion === 'eliminar') {
          if (!b.dataset.confirmar) { b.dataset.confirmar = '1'; b.textContent = '¿Seguro? Clic de nuevo'; return; }
          docs.guardarLista(docs.lista().filter(x => x.id !== id));
          if (estado.idGuardado === id) { estado.idGuardado = null; sesion.borrar('aj_borrador'); }
          aviso('Borrador eliminado.', 'ok'); render(); return;
        }
        if (!caso) throw new Error('Ese caso no está disponible. Exporta tu copia para conservarlo.');
        if (accion === 'seguimiento') {
          const panel = $('.doc-seguimiento', item); panel.hidden = !panel.hidden;
          b.setAttribute('aria-expanded', String(!panel.hidden));
          if (!panel.hidden) $('input, select', panel)?.focus(); return;
        }
        if (accion === 'quitar-seguimiento') {
          if (!b.dataset.confirmar) { b.dataset.confirmar = '1'; b.textContent = '¿Quitar seguimiento? Clic de nuevo'; return; }
          docs.poner({ ...reg, seguimiento: null }); aviso('Seguimiento quitado; el documento se conserva.', 'ok'); render(); return;
        }
        if (accion === 'pdf' || accion === 'word') {
          const g = AJ.motor.generar(caso, inicializarDatos(caso, reg.datos));
          descargar(nombreArchivo(accion === 'pdf' ? 'pdf' : 'docx', caso, reg.datos), accion === 'pdf' ? archivoPdf(g) : archivoDocx(g), accion === 'pdf' ? 'application/pdf' : MIME_DOCX);
          return;
        }
        if (accion === 'calendario') {
          const st = AJ.seguimiento.estado(caso, reg.datos, reg.seguimiento || {});
          if (!st.evento) throw new Error('No hay un vencimiento calculable para este trámite. Revisa el seguimiento.');
          descargar(`recordatorio-${hoyISO()}.ics`, AJ.exportar.ics({ ...st.evento, descripcion: `${st.evento.descripcion}\n\nDocumento: ${reg.titulo}. El Memorialista. Comprueba el plazo en la fuente oficial.` }), 'text/calendar;charset=utf-8');
          aviso('Abre el archivo descargado para agregar el recordatorio a tu calendario.', 'ok'); return;
        }
        if (accion === 'siguiente') {
          const destino = AJ.casos.find(c => c.id === b.dataset.caso);
          if (!destino) return;
          const datos = AJ.seguimiento.prellenar(caso, reg.datos, reg.seguimiento || {}, destino);
          sesion.borrar('aj_borrador');
          estado.caso = destino; estado.datos = inicializarDatos(destino, datos); estado.idGuardado = null; estado.generado = null;
          estado.origen = { id: reg.id, casoId: reg.casoId, titulo: reg.titulo, fecha: reg.seguimiento?.fecha || '' };
          sesion.guardar('aj_borrador', { casoId: destino.id, datos: estado.datos, origen: estado.origen, ts: Date.now() });
          ir(`caso/${destino.id}`); return;
        }
        if (!['abrir', 'duplicar'].includes(accion)) return;
        sesion.borrar('aj_borrador');
        estado.caso = caso; estado.datos = inicializarDatos(caso, reg.datos); estado.idGuardado = accion === 'abrir' ? id : null;
        estado.origen = accion === 'abrir' ? (reg.origen || null) : null; estado.generado = null;
        sesion.guardar('aj_borrador', { casoId: caso.id, datos: estado.datos, idGuardado: estado.idGuardado, origen: estado.origen, ts: Date.now() });
        ir(`caso/${caso.id}`);
      }));
      const f = $('.form-seguimiento', item);
      if (f) f.addEventListener('submit', seguro(ev => {
        ev.preventDefault();
        const id = item.dataset.id, reg = docs.buscar(id); if (!reg) return;
        const seg = { ...(reg.seguimiento || {}) };
        $$('input, select, textarea', f).forEach(x => { if (x.name) seg[x.name] = x.value.trim(); });
        const fechas = ['fecha', 'fechaRespuesta', 'fechaNotificacion', 'fechaInicioCumplimiento', 'fechaApertura', 'fechaRecepcionExpediente'];
        if (fechas.some(k => seg[k] && (!AJ.festivos.parseISO(seg[k]) || AJ.festivos.parseISO(seg[k]) > R.hoy()))) throw new Error('Revisa las fechas: deben existir y no pueden ser posteriores a hoy.');
        if (!seg.fecha) throw new Error('Escribe la fecha en que entregaste el documento.');
        seg.actualizado = new Date().toISOString();
        docs.poner({ ...reg, seguimiento: AJ.mejoras.seguimientoSeguro(seg) });
        aviso('Seguimiento guardado.', 'ok');
        vistaMisDocumentos(main, ''); actualizarInsignia();
        document.getElementById(`doc-${id}`)?.scrollIntoView({ block: 'start' });
      }));
    });
  }

  /* ---------- Vista: guía ---------- */
  function vistaGuia(main, arg) {
    const decidir = [
      { q: 'Necesito que una entidad me responda, me dé información, copias o un servicio', id: 'pet_general', t: 'Derecho de petición' },
      { q: 'Ya presenté un derecho de petición y no me respondieron en 15 días hábiles', id: 'tut_peticion', t: 'Tutela por derecho de petición' },
      { q: 'La EPS no me da un medicamento, cita, cirugía o examen que ordenó el médico', id: 'tut_salud_servicio', t: 'Tutela por salud (o primero la petición a la EPS)' },
      { q: 'Gané una tutela y la entidad no cumple lo que ordenó el juez', id: 'desacato', t: 'Incidente de desacato' },
      { q: 'Me negaron la tutela y han pasado menos de 3 días', id: 'impugnacion', t: 'Impugnación' },
      { q: 'Me llegó una resolución, multa o decisión en mi contra (menos de 10 días hábiles)', id: 'rec_reposicion', t: 'Recurso de reposición y apelación' },
      { q: 'La factura de agua, luz o gas llegó altísima o me cortaron el servicio', id: 'pet_spd', t: 'Reclamo a la empresa de servicios públicos' },
      { q: 'Me reportaron en Datacrédito o TransUnion injustamente', id: 'hd_reclamo', t: 'Reclamo de hábeas data (y luego tutela)' },
      { q: 'Me despidieron estando embarazada, enferma o con discapacidad', id: 'tut_estabilidad', t: 'Tutela por estabilidad laboral reforzada' },
      { q: 'No me pagan el salario, la liquidación o las incapacidades', id: 'pet_empleador', t: 'Petición al empleador (y luego tutela por mínimo vital)' },
      { q: 'Colpensiones o el fondo no resuelve mi pensión', id: 'pet_pension', t: 'Petición a pensiones (y luego tutela)' },
      { q: 'Un almacén no me responde por la garantía de un producto', id: 'queja_consumidor', t: 'Reclamación directa al vendedor' },
      { q: 'Sufro violencia en mi familia', id: 'fam_proteccion', t: 'Medida de protección' },
      { q: 'Mi pareja, expareja u otra persona me maltrata, me amenaza o abusó de mí y quiero denunciarlo', id: 'muj_denuncia', t: 'Denuncia penal (y medida de protección)' },
      { q: 'Pedí protección y la Comisaría, la Fiscalía, la Policía o la EPS no hacen nada', id: 'muj_tutela_proteccion', t: 'Tutela por falta de protección' },
      { q: 'El padre o madre de mis hijos no da para su sostenimiento', id: 'fam_alimentos', t: 'Conciliación de cuota alimentaria' },
      { q: 'Soy una persona mayor y mis hijos no me ayudan, o mi pareja no me da para vivir', id: 'fam_alimentos', t: 'Conciliación de cuota alimentaria (personas mayores, padres, cónyuge)' },
      { q: 'Mi expareja no me deja ver a mis hijos o quiere quitármelos', id: 'fam_custodia', t: 'Conciliación de custodia y visitas' },
      { q: 'Necesito acreditar que soy madre (o padre) cabeza de familia', id: 'muj_declaracion_cabeza', t: 'Declaración juramentada de madre cabeza de familia' },
      { q: 'Soy madre cabeza de familia y no me dan la prioridad en vivienda, educación, empleo o subsidios', id: 'muj_cabeza_familia', t: 'Petición como madre cabeza de familia' },
      { q: 'No me pagan la licencia de maternidad', id: 'muj_licencia_maternidad', t: 'Petición por la licencia de maternidad' },
      { q: 'Mi jefe o un compañero me acosa en el trabajo (sexual o laboralmente)', id: 'muj_acoso_laboral', t: 'Queja por acoso laboral o sexual' },
      { q: 'La EPS no me da el control prenatal, el método anticonceptivo, la IVE o la atención por violencia sexual', id: 'muj_salud_sexual', t: 'Petición a la EPS por salud sexual y reproductiva' },
      { q: 'Tengo un problema del barrio con la alcaldía (vías, basuras, ruido)', id: 'pet_municipio_servicios', t: 'Petición a la alcaldía o querella policiva' },
      { q: 'Me quitaron el subsidio (Renta Ciudadana, Colombia Mayor, Familias en Acción) o no me ha llegado el giro', id: 'pet_prosperidad', t: 'Petición a Prosperidad Social (y recurso si hubo resolución)' },
      { q: 'Mi hijo no tiene cupo en el colegio o lo expulsaron', id: 'tut_educacion', t: 'Tutela por el derecho a la educación' },
      { q: 'No me entregan la historia clínica', id: 'pet_eps_historia', t: 'Petición de copia de la historia clínica' },
      { q: 'Me cortaron el agua o la luz y en la casa hay niños, enfermos o personas mayores', id: 'tut_servicios_publicos', t: 'Tutela por corte de servicios públicos' },
      { q: 'Migración no me da el PPT, la cita o el documento', id: 'pet_migracion', t: 'Petición a Migración Colombia' },
      { q: 'Me llaman a cobrar todo el día, a mí o a mi familia', id: 'hd_supresion', t: 'Solicitud para que dejen de usar tus datos' },
      { q: 'La Unidad de Víctimas no me da la ayuda ni me responde', id: 'pet_victimas', t: 'Petición a la Unidad para las Víctimas' }
    ];
    const glosario = [
      ['Accionante / accionado', 'Quien presenta la tutela / la entidad contra la que se presenta.'],
      ['Agente oficioso', 'Persona que presenta la tutela en nombre de otra que no puede hacerlo (enfermo, adulto mayor). Debe decirlo en el escrito.'],
      ['Días hábiles', 'Lunes a viernes, sin festivos. Los plazos de la ley se cuentan así, desde el día siguiente a la radicación.'],
      ['Desacato', 'Trámite para que el juez sancione a quien no cumple una orden de tutela (arresto hasta 6 meses y multa hasta 20 salarios mínimos).'],
      ['Impugnar', 'Pedir que un juez superior revise el fallo. En tutela, 3 días hábiles.'],
      ['Mínimo vital', 'Lo que una persona necesita para vivir dignamente (comida, vivienda, salud). Si te lo quitan, la tutela puede proceder aunque exista otro proceso.'],
      ['Medida provisional', 'Orden urgente que el juez puede dar apenas recibe la tutela, antes de fallar, para evitar un daño grave.'],
      ['Perjuicio irremediable', 'Daño grave e inminente que no se puede reparar después. Permite usar la tutela aunque haya otro camino legal.'],
      ['PQRS', 'Peticiones, quejas, reclamos y sugerencias: la ventanilla por donde las entidades reciben los derechos de petición.'],
      ['Radicar', 'Entregar oficialmente un documento y obtener constancia (sello o número de radicado). Esa constancia es tu prueba.'],
      ['Recurso de reposición / apelación', 'Pedir a la misma entidad que cambie su decisión (reposición) o que la revise el superior (apelación). 10 días hábiles.'],
      ['Silencio administrativo positivo', 'En ciertos trámites de servicios públicos domiciliarios, la falta de respuesta dentro del término puede producir efectos favorables. Hay requisitos y excepciones, como práctica de pruebas o demora atribuible al usuario; verifica si procede solicitar su reconocimiento.'],
      ['Subsidiariedad', 'Regla según la cual la tutela solo procede si no hay otro mecanismo judicial eficaz, o si lo hay pero no sirve frente a la urgencia.'],
      ['Sujeto de especial protección', 'Niños, mujeres embarazadas, adultos mayores, personas con discapacidad o enfermedad grave, víctimas, desplazados. Tienen prioridad y protección reforzada.'],
      ['Tutela', 'Acción rápida ante cualquier juez para proteger derechos fundamentales. Sin abogado, sin costo, fallo en 10 días.']
    ];
    main.innerHTML = `
      <section class="seccion">
        <div class="seccion-cab"><h1>Guía práctica</h1><p>Lo que necesitas saber para usar bien estos documentos.</p></div>
        <nav class="subnav"><a href="#guia/decidir">¿Qué documento necesito?</a><a href="#guia/pasos">Cómo entregarlo (radicar)</a><a href="#guia/plazos">Calculadora de plazos</a><a href="#guia/glosario">Glosario</a><a href="#guia/directorio">Dónde pedir ayuda</a></nav>
      </section>
      <section class="seccion" id="decidir"><h2>¿Qué documento necesito?</h2><p>Busca tu situación:</p>
        <div class="decidir">${decidir.map(x => `<a class="decidir-item" href="#caso/${x.id}"><span>${esc(x.q)}</span><strong>${icono('flecha')} ${esc(x.t)}</strong></a>`).join('')}</div>
        <p class="ayuda">El <strong>derecho de petición</strong> permite solicitar una respuesta y conservar constancia. No es un requisito universal antes de la tutela: frente a una amenaza urgente para la salud o la vida, busca atención y orientación de inmediato. El juez evalúa la procedencia de la <strong>tutela</strong>; si se incumple su fallo, puedes solicitar el cumplimiento y consultar si procede el <strong>desacato</strong>.</p>
      </section>
      <section class="seccion" id="pasos"><h2>Cómo entregarlo (radicar) y qué guardar</h2>
        <ol class="pasos">
          <li><strong>Imprime dos copias</strong> (o guarda el PDF). Firma con tu nombre y número de cédula.</li>
          <li><strong>Entrégalo</strong> en la ventanilla de la entidad (eso es "radicar") y pide que le pongan sello con la fecha y un número a tu copia: ese sello es tu prueba. O envíalo al correo de PQRS o de notificaciones de la entidad (lo encuentras en su página web) y guarda el correo enviado.</li>
          <li><strong>Tutelas:</strong> por internet en <a href="https://procesojudicial.ramajudicial.gov.co/TutelaEnLinea" target="_blank" rel="noopener">Tutela en Línea</a> o en la Oficina de Reparto. Te llegará un correo con el juzgado asignado y el radicado; revisa tu correo a diario, incluido el spam.</li>
          <li><strong>Cuenta el plazo</strong> con la calculadora de abajo. Anota la fecha de vencimiento.</li>
          <li><strong>Si no responden</strong>, genera la tutela por derecho de petición anexando tu copia radicada. Si no cumplen un fallo, el incidente de desacato.</li>
          <li><strong>Nunca pagues</strong> por un derecho de petición o una tutela: son gratuitos y no necesitan abogado. La Personería y los consultorios jurídicos te ayudan sin costo.</li>
        </ol>
      </section>
      <section class="seccion" id="plazos"><h2>Calculadora de plazos</h2><p class="revision-note">Cálculo orientativo con festivos nacionales de Colombia. Verifica el término aplicable, la fecha de notificación, las suspensiones y las reglas del despacho o entidad. No contempla cierres extraordinarios ni todos los regímenes especiales.</p>
        <div class="calculadora">
          <div class="campo media"><label class="etiqueta" for="c-fecha">Fecha de radicación</label><input type="date" id="c-fecha" value="${hoyISO()}"></div>
          <div class="campo media"><label class="etiqueta" for="c-plazo">Plazo</label><select id="c-plazo">
            <option value="15h-pet">15 días hábiles: derecho de petición normal</option><option value="10h-doc">10 días hábiles: copias o información</option><option value="30h-con">30 días hábiles: consultas</option>
            <option value="10h-tut">10 días hábiles: el juez decide la tutela</option><option value="3h-imp">3 días hábiles: para impugnar un fallo de tutela</option><option value="10h-rec">10 días hábiles: para presentar recursos contra una resolución</option><option value="5h-spd">5 días hábiles: recurso contra la respuesta de servicios públicos</option>
            <option value="15h-rec">15 días hábiles: reclamo a servicios públicos, Datacrédito, un banco o un almacén</option><option value="2m-sob">2 meses: pensión de sobrevivientes</option><option value="4m-vej">4 meses: pensión de vejez o invalidez</option><option value="60h-ruv">60 días hábiles: la Unidad de Víctimas decide si te incluye en el registro</option>
          </select></div>
          <div class="campo completa plazo" id="c-resultado"></div>
        </div>
        <details><summary>Festivos de ${new Date().getFullYear()} que se tienen en cuenta</summary><ul class="festivos">${AJ.festivos.listaAnio(new Date().getFullYear()).lista.map(f => `<li>${esc(R.fechaLarga(f.fecha))} – ${esc(f.nombre)}</li>`).join('')}</ul></details>
      </section>
      <section class="seccion" id="glosario"><h2>Glosario en lenguaje común</h2><dl class="glosario">${glosario.map(([t, d]) => `<div><dt>${esc(t)}</dt><dd>${esc(d)}</dd></div>`).join('')}</dl></section>
      <section class="seccion" id="directorio"><h2>Dónde pedir ayuda gratuita</h2>
        <div class="directorio">${AJ.entidades.directorio.map(x => `<div class="dir-item"><strong>${esc(x.nombre)}</strong><p>${esc(x.queHace)}</p><span>${esc(x.canal)}</span></div>`).join('')}</div>
      </section>
      <section class="seccion nota-legal"><h2>Fuentes</h2><p>Constitución Política de 1991; Ley 1755 de 2015; Decreto 2591 de 1991; Decreto 1069 de 2015 (reparto de tutelas, modificado por el Decreto 333 de 2021); Ley 1751 de 2015; Ley 100 de 1993; Ley 1266 de 2008 y Ley 2157 de 2021; Ley 142 de 1994; Ley 1437 de 2011; Ley 1480 de 2011; Ley 1328 de 2009; Ley 1098 de 2006; Ley 294 de 1996; Ley 1448 de 2011; Ley 1801 de 2016; Código Sustantivo del Trabajo; sentencias de la Corte Constitucional citadas en cada documento. Cifras de tutelas: Consejo Superior de la Judicatura y Defensoría del Pueblo (2023-2025).</p></section>`;
    const calc = () => {
      const [, n, u] = $('#c-plazo').value.match(/^(\d+)([hm])/);
      const desde = AJ.festivos.parseISO($('#c-fecha').value); if (!desde) { $('#c-resultado').textContent = 'Selecciona una fecha válida para calcular el plazo.'; return; }
      const vence = u === 'm' ? AJ.festivos.sumarMeses(desde, +n) : AJ.festivos.sumarDiasHabiles(desde, +n);
      $('#c-resultado').innerHTML = `<p>Vence el <strong>${esc(R.fechaLarga(vence))}</strong>. El plazo se cuenta desde el día siguiente a la radicación${u === 'h' ? ', sin sábados, domingos ni festivos' : ''}.</p>`;
    };
    $('#c-fecha').addEventListener('change', calc); $('#c-plazo').addEventListener('change', calc); calc();
    if (arg) { const el = document.getElementById(arg); if (el) setTimeout(() => el.scrollIntoView({ behavior: 'smooth' }), 50); }
  }

  /* ---------- Vista: acerca de ---------- */
  const FECHA_AVISO = '22 de octubre de 2026';
  function avisoLegalHTML() {
    return `
      <section class="seccion legal" id="legal">
        <div class="seccion-cab"><h2>Información legal, uso y privacidad</h2><p>Cómo funciona la orientación ciudadana de El Memorialista y qué debes revisar antes de utilizar un documento. Actualización: ${FECHA_AVISO}.</p></div>

        <details open id="legal-naturaleza"><summary>1. Alcance de la orientación ciudadana</summary>
          <p><strong>El Memorialista</strong> ofrece información general y formularios gratuitos para preparar borradores de documentos en Colombia. El contenido se construye a partir de las respuestas que escribes.</p>
          <p>Un formulario no sustituye el análisis individual de un caso ni crea por sí solo una relación profesional. Si necesitas apoyo para tomar una decisión jurídica, consulta la <a href="#guia/directorio">guía de ayuda</a> o a un profesional de confianza.</p>
        </details>

        <details id="legal-verificacion"><summary>2. Revisión del documento</summary>
          <p>Antes de firmar o presentar un escrito, comprueba los hechos, los nombres, las fechas, las solicitudes, los anexos y la aplicación de las referencias citadas. Las normas y los procedimientos pueden cambiar.</p>
          <p>Los plazos calculados son orientativos. Revisa las notificaciones, las reglas del trámite y las circunstancias del despacho o entidad. La preparación de un borrador no garantiza su aceptación ni un resultado determinado.</p>
        </details>

        <details id="legal-usuario"><summary>3. Uso de los formularios</summary>
          <p>Utiliza información verdadera y relaciona únicamente los documentos que realmente aportarás. Comprueba que puedes actuar por las personas que identifiques y que las solicitudes corresponden a tu situación.</p>
          <p>La decisión de editar, firmar, compartir o presentar el borrador te corresponde. Revisa con especial cuidado las declaraciones y los datos personales que contenga.</p>
        </details>

        <details id="legal-responsabilidad"><summary>4. Disponibilidad y conservación del trabajo</summary>
          <p>La aplicación puede experimentar interrupciones o limitaciones del navegador. Guarda una copia de los documentos que quieras conservar y verifica que la descarga se haya completado.</p>
          <p>El almacenamiento local puede borrarse al limpiar los datos del navegador o cambiar de dispositivo. Exportar una copia de seguridad permite conservar los borradores fuera de este navegador.</p>
        </details>

        <details id="legal-privacidad"><summary>5. Privacidad y almacenamiento</summary>
          <p>Las respuestas del módulo ciudadano se procesan en tu navegador para generar el borrador; no se envían a un modelo de IA ni al servidor para esa generación. Los borradores se guardan localmente cuando eliges guardarlos. “Recordar mis datos” también es opcional.</p>
          <p>Los datos locales no están cifrados por esta aplicación. Otra persona que utilice el mismo perfil del navegador podría acceder a ellos. Puedes eliminar los documentos y datos recordados desde <a href="#mis-documentos">Mis borradores</a>.</p>
          <p>El tema y el cierre de avisos pueden recordarse como preferencias. La aplicación instalable almacena recursos públicos para abrir sin conexión; esa caché no incluye los documentos personales ni el espacio privado.</p>
          <p>El alojamiento puede registrar datos técnicos de las solicitudes. El espacio privado utiliza sesión y servicios configurados para sus funciones; su tratamiento es distinto del procesamiento local de esta sección.</p>
        </details>

        <details id="legal-propiedad"><summary>6. Descargas y copias de seguridad</summary>
          <p>Puedes descargar, copiar o compartir los borradores que prepares, revisando antes su contenido y el destino de la información. La descarga no adjunta archivos de prueba ni presenta el documento ante ninguna entidad.</p>
          <p>Las copias de seguridad admitidas contienen hasta 200 documentos y 5 MB. Si un historial no puede abrirse, se conserva sin sobrescribirlo y puedes descargar el original desde Mis borradores para recuperarlo.</p>
        </details>

        <details id="legal-independencia"><summary>7. Entidades y presentación de documentos</summary>
          <p>Los nombres de entidades y los enlaces oficiales ayudan a identificar posibles destinatarios y canales de atención. Su inclusión no representa un aval o una afiliación institucional.</p>
          <p>Esta sección no presenta documentos automáticamente ni atiende emergencias. Para presentar un escrito, utiliza el canal que corresponda y conserva la constancia de recepción. Ante un peligro inmediato, contacta a los servicios de emergencia de tu localidad.</p>
        </details>

        <details id="legal-enlaces"><summary>8. Sitios externos</summary>
          <p>Los enlaces externos abren servicios de otras entidades. Revisa sus instrucciones, disponibilidad y políticas de privacidad antes de enviar información o realizar un trámite.</p>
        </details>

        <details id="legal-menores"><summary>9. Acompañamiento al preparar un documento</summary>
          <p>Si necesitas apoyo para comprender las preguntas o completar un escrito, pide ayuda a una persona de confianza o consulta el directorio de orientación. Evita compartir datos personales que no sean necesarios para el trámite.</p>
        </details>

        <details id="legal-ley"><summary>10. Actualizaciones</summary>
          <p>Esta información describe la versión disponible de El Memorialista. Las funciones y las orientaciones pueden actualizarse; revisa la fecha de esta sección y las indicaciones del modelo que utilices.</p>
          <p>Si utilizas el archivo autónomo, descarga una versión nueva para recibir cambios. Los enlaces a entidades y las funciones del espacio privado requieren conexión a internet.</p>
        </details>
      </section>`;
  }

  function vistaAcerca(main, arg) {
    main.innerHTML = `
      <section class="seccion"><p class="em-eyebrow">SOBRE EL MEMORIALISTA</p><h1>La claridad también empieza aquí.</h1><p class="em-lead">Orientación ciudadana gratuita para ayudarte a preparar borradores de documentos en Colombia.</p></section>
      <section class="seccion"><h2>Tus derechos, en palabras claras.</h2><p>Explora ${AJ.casos.length} casos, elige el que corresponda a tu situación y responde las preguntas del formulario. Puedes revisar el borrador, editarlo y descargarlo cuando esté listo.</p><p>La guía ciudadana reúne indicaciones para preparar documentos, un glosario, un directorio de ayuda y una calculadora orientativa de plazos. Comprueba siempre los datos y las referencias aplicables antes de presentar un escrito.</p></section>
      <section class="seccion" id="privacidad-integracion"><h2>Qué ocurre con tus datos en esta sección</h2><div class="grid-principios"><div class="principio">${icono('escudo')}<h3>Procesamiento en tu navegador</h3><p>Las respuestas y los documentos de la sección ciudadana se construyen localmente. No se envían a un modelo de IA ni al servidor para generar el borrador.</p></div><div class="principio">${icono('guardar')}<h3>Recuperación y guardado local</h3><p>La pestaña guarda automáticamente el formulario para recuperarlo al recargar. El navegador puede restaurarlo al reabrir una sesión. Los botones de guardado conservan borradores y seguimientos de forma persistente; “Recordar mis datos” conserva tus datos de identificación. Otras personas que usen este navegador podrían acceder a ellos. Borra todos tus datos en Mis borradores al terminar en un equipo compartido.</p></div><div class="principio">${icono('info')}<h3>Tu espacio privado</h3><p>El acceso mediante cuenta corresponde al generador privado. La sección ciudadana puede utilizarse sin iniciar sesión. La preferencia de tema y el cierre de avisos pueden recordarse localmente.</p></div><div class="principio">${icono('documento')}<h3>Tú controlas las descargas</h3><p>Al exportar, copiar o compartir, decides el destino de la información. El alojamiento puede registrar datos técnicos de las solicitudes web. Los enlaces externos tienen sus propias políticas.</p></div></div></section>
      <section class="seccion" id="sin-internet"><h2>La orientación también puede acompañarte sin conexión.</h2>${window.AJ_SIN_INTERNET ? '<p>Estás usando el archivo autónomo. Todos los casos, formularios, normas y exportaciones están incluidos. Los enlaces a entidades requieren internet.</p>' : '<p>Descarga una copia autónoma que reúne los casos, formularios, calendario y guías en un solo archivo. Ábrela en tu navegador, sin instalar nada.</p><a class="btn btn-primario" href="/static/asesor/descargas/el-memorialista-ciudadano-sin-internet.html" download="el-memorialista-ciudadano-sin-internet.html">Descargar orientación sin conexión</a>'}<p class="ayuda">La versión autónoma contiene únicamente la orientación ciudadana. Para actualizarla, descarga de nuevo el archivo. El guardado puede estar limitado por el navegador al abrir archivos locales; exporta una copia si necesitas conservar los borradores.</p></section>
      <section class="seccion nota-legal"><h2>Antes de presentar un documento</h2><p>Lee el borrador completo, comprueba los datos y la aplicabilidad de las normas citadas. Esta herramienta no radica escritos, representa a usuarios ni garantiza resultados. Para orientación sobre las particularidades de tu caso consulta la <a href="#guia/directorio">ayuda gratuita</a>.</p></section>
      ${avisoLegalHTML()}`;
    if (arg) { const el = document.getElementById(arg); if (el) { if (el.tagName === 'DETAILS') el.open = true; setTimeout(() => el.scrollIntoView({ behavior: 'auto', block: 'start' }), 80); } }
  }


  /* La PWA pública se gestiona en pwa.js con alcance /asesor/. */
  /* Franja de aceptación de condiciones (se muestra hasta que la persona la cierra) */
  function barraLegal() {
    const barra = $('#barra-legal');
    if (!barra) return;
    if (almacen.leer('aj_aviso', '')) return;
    barra.hidden = false;
    $('#b-aceptar-aviso').addEventListener('click', () => { almacen.guardar('aj_aviso', FECHA_AVISO); barra.hidden = true; });
  }

  AJ.ui = { estado, camposDelCaso, inicializarDatos, visible, buscarCasos, aviso, render, errorCampo, guardarActual, registroActual, docs, pendientes, formularioSeguimiento };
  AJ.app = AJ.ui;

  /* ---------- Arranque ---------- */
  function construirDatalist() {
    const dl = document.createElement('datalist'); dl.id = 'lista-entidades';
    dl.innerHTML = AJ.entidades.lista.map(e => `<option value="${esc(e.nombre)}"></option>`).join('') + AJ.entidades.dependenciasMunicipio.map(e => `<option value="${esc(e.nombre)}"></option>`).join('');
    document.body.appendChild(dl);
  }

  document.addEventListener('DOMContentLoaded', () => {
    AJ.casos = AJ.casos.filter(c => !c.retirado); // casos conservados en el código pero no ofrecidos al público
    construirDatalist();
    barraLegal();
    $('#total-casos').textContent = AJ.casos.length;
    if (AJ.buscador) AJ.buscador.construir(AJ.casos, AJ.tipos, AJ.entidades, AJ.sinonimos);
    if (AJ.a11y) AJ.a11y.cargar();
    menuAccesibilidad();
    const cabecera = document.querySelector('.cabecera');
    if (cabecera && typeof ResizeObserver !== 'undefined') { const medir = () => cabecera.classList.toggle('suelta', cabecera.getBoundingClientRect().height > window.innerHeight * 0.2); new ResizeObserver(medir).observe(cabecera); window.addEventListener('resize', medir); medir(); }
    window.addEventListener('hashchange', render);
    render();

  });
})();
