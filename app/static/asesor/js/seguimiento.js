/* ============================================================
   seguimiento.js — "Mis trámites": después de entregar (radicar)
   un documento, calcula hasta cuándo tienen para responder con
   los festivos de Colombia, avisa cuando se vence y propone el
   siguiente documento YA PRELLENADO con los datos del anterior
   (petición → tutela → desacato o impugnación, reclamo → recurso…).
   Todo queda en el navegador de la persona.
   ============================================================ */
window.AJ = window.AJ || {};

AJ.seguimiento = (function () {
  'use strict';
  const F = () => AJ.festivos;
  const R = () => AJ.red;

  const IDENTIDAD = ['modo', 'nombre', 'genero', 'tipoDoc', 'numDoc', 'expedidaEn', 'ciudad', 'direccion', 'telefono', 'correo', 'condicion', 'afectadoNombre', 'afectadoGenero', 'afectadoTipoDoc', 'afectadoNumDoc', 'parentesco', 'afectadoRazon'];
  const ENTIDAD = ['categoria', 'entidadNombre', 'entidadCargo', 'entidadCiudad', 'entidadDireccion'];
  const NO_COPIAR = new Set(['peticiones', 'peticionOtra', 'anexos', 'anexosOtros', 'derechos', 'urgente', 'medidaTexto', 'otraTutela', 'yaPedi', 'fechaPrevia', 'radicadoPrevio', 'medioPrevio', 'respuestaPrevia']);

  const CANALES = [
    { v: 'ventanilla', t: 'En la ventanilla, con sello de recibido' },
    { v: 'correo', t: 'Por correo electrónico' },
    { v: 'web', t: 'Por la página web o la aplicación' },
    { v: 'tutela_linea', t: 'Por Tutela en Línea (Rama Judicial)' },
    { v: 'reparto', t: 'En la Oficina de Reparto o en el juzgado' },
    { v: 'otro', t: 'Otro medio' }
  ];
  const RESPUESTAS = [
    { v: '', t: 'Todavía no me responden' },
    { v: 'favorable', t: 'Me respondieron a favor (resolvieron lo que pedí)' },
    { v: 'parcial', t: 'Respondieron algo, pero no resuelve lo que pedí' },
    { v: 'tramite', t: 'Solo dijeron que "está en trámite"' },
    { v: 'negativa', t: 'Me lo negaron' }
  ];
  const DECISIONES = [
    { v: '', t: 'El juez todavía no ha decidido' },
    { v: 'concedio', t: 'El juez concedió la tutela' },
    { v: 'parcial', t: 'La concedió solo en parte' },
    { v: 'nego', t: 'La negó o la declaró improcedente' }
  ];

  /* Siguiente documento según cómo va el trámite. Por tipo y, cuando hace falta, por caso. */
  const SIGUIENTES = {
    tipo: {
      peticion: { vencido: ['tut_peticion'], noResuelve: ['tut_peticion'] },
      queja: { vencido: ['tut_peticion'], noResuelve: [] },
      habeas: { vencido: ['tut_habeas_data'], noResuelve: ['tut_habeas_data'] },
      recurso: { vencido: ['tut_debido_proceso'], noResuelve: ['tut_debido_proceso'] },
      familia: { vencido: ['tut_peticion'], noResuelve: [] }
    },
    caso: {
      pet_eps_servicio: { vencido: ['tut_salud_servicio', 'tut_peticion'], noResuelve: ['tut_salud_servicio', 'queja_supersalud'] },
      pet_eps_historia: { vencido: ['tut_peticion'], noResuelve: ['tut_peticion', 'queja_supersalud'] },
      pet_pension: { vencido: ['tut_pension', 'tut_peticion'], noResuelve: ['tut_pension'] },
      pet_empleador: { vencido: ['tut_salario', 'tut_peticion'], noResuelve: ['tut_salario'] },
      pet_incapacidades: { vencido: ['tut_incapacidades', 'tut_peticion'], noResuelve: ['tut_incapacidades'] },
      pet_colegio: { vencido: ['tut_educacion', 'tut_peticion'], noResuelve: ['tut_educacion'] },
      pet_victimas: { vencido: ['tut_victimas', 'tut_peticion'], noResuelve: ['tut_victimas'] },
      pet_migracion: { vencido: ['tut_peticion'], noResuelve: ['tut_migrantes', 'tut_peticion'] },
      pet_spd: { vencido: [], noResuelve: ['rec_spd'] },
      rec_spd: { vencido: [], noResuelve: [] },
      pet_municipio_transito: { vencido: ['tut_peticion'], noResuelve: ['rec_reposicion', 'tut_peticion'] },
      pet_municipio_predial: { vencido: ['tut_peticion'], noResuelve: ['rec_reposicion', 'tut_peticion'] },
      pet_prosperidad: { vencido: ['tut_peticion'], noResuelve: ['rec_reposicion', 'tut_peticion'] },
      queja_supersalud: { vencido: ['tut_salud_servicio'], noResuelve: ['tut_salud_servicio'] },
      queja_consumidor: { vencido: [], noResuelve: [] },
      queja_financiera: { vencido: [], noResuelve: [] },
      hd_supresion: { vencido: ['tut_habeas_data'], noResuelve: [] },
      muj_licencia_maternidad: { vencido: ['tut_peticion', 'queja_supersalud'], noResuelve: ['tut_general', 'queja_supersalud'] },
      muj_salud_sexual: { vencido: ['tut_salud_servicio', 'queja_supersalud'], noResuelve: ['tut_salud_servicio', 'queja_supersalud'] },
      muj_cabeza_familia: { vencido: ['tut_peticion'], noResuelve: ['tut_peticion'] },
      muj_acoso_laboral: { vencido: ['tut_peticion'], noResuelve: ['muj_denuncia'] },
      fam_proteccion: { vencido: ['muj_tutela_proteccion', 'muj_denuncia'], noResuelve: ['muj_tutela_proteccion', 'muj_denuncia'] },
      fam_alimentos: { vencido: ['tut_peticion'], noResuelve: [] },
      fam_custodia: { vencido: ['tut_peticion'], noResuelve: [] }
    }
  };
  function siguientesDe(caso, clave) {
    const c = SIGUIENTES.caso[caso.id];
    if (c && c[clave]) return c[clave].filter(id => (AJ.casos || []).some(x => x.id === id && !x.retirado));
    const t = SIGUIENTES.tipo[caso.tipo];
    return ((t && t[clave]) || []).filter(id => (AJ.casos || []).some(x => x.id === id && !x.retirado));
  }

  // Fuentes primarias revisadas el 22-10-2026. El cómputo es orientativo:
  // no conoce cierres extraordinarios, suspensiones, pruebas, prórrogas ni la
  // fecha efectiva de notificación. La providencia y su constancia prevalecen.
  const FUENTES = Object.freeze({
    revision: '2026-10-22',
    peticion: 'https://cancilleria.gov.co/normograma/compilacion/docs/ley_1755_2015.htm',
    tutela: 'https://cancilleria.gov.co/normograma/compilacion/docs/decreto_2591_1991.htm',
    desacato: 'https://www.corteconstitucional.gov.co/relatoria/2014/c-367-14.htm',
    comunicaciones: 'https://normograma.crcom.gov.co/crc/compilacion/docs/resolucion_crc_8171_2026.htm',
    servicios: 'https://cancilleria.gov.co/normograma/compilacion/docs/ley_0142_1994.htm',
    habeas: 'https://www.cancilleria.gov.co/normograma/compilacion/docs/ley_1581_2012.htm',
    habeasFinanciero: 'https://cancilleria.gov.co/normograma/compilacion/docs/ley_1266_2008.htm',
    recurso: 'https://cancilleria.gov.co/normograma/compilacion/docs/ley_1437_2011.htm',
    computo: 'https://www.cancilleria.gov.co/normograma/compilacion/docs/ley_0004_1913.htm'
  });
  const ADVERTENCIA = 'Cálculo orientativo con fines de seguimiento. Verifica la fecha efectiva, las prórrogas, suspensiones y reglas especiales; la aplicación no determina el resultado del trámite.';
  const esComunicaciones = datos => ['internet', 'telefonia', 'celular', 'television'].includes((datos || {}).servicio);
  const diasRecursoServicios = datos => esComunicaciones(datos) ? 10 : 5;
  const consultaDatos = (caso, datos) => caso.id === 'hd_supresion' && Array.isArray(datos.tramite)
    && datos.tramite.length > 0 && datos.tramite.every(v => ['acceso', 'origen'].includes(v));

  /* Término de referencia y hecho desde el que empieza a contarse. */
  function plazoRespuesta(caso, datos) {
    datos = datos || {};
    const comun = { base: 'fecha', baseTexto: 'recepción de la solicitud', nota: ADVERTENCIA };
    switch (caso.tipo) {
      case 'tutela': return { ...comun, dias: 10, tipo: 'habiles', baseTexto: 'presentación de la tutela', quien: 'El juzgado', que: 'decidir la tutela', fuente: FUENTES.tutela };
      case 'impugnacion': return { ...comun, dias: 20, tipo: 'habiles', base: 'fechaRecepcionExpediente', baseTexto: 'recepción del expediente por el superior', quien: 'El juez de segunda instancia', que: 'decidir la impugnación', fuente: FUENTES.tutela };
      case 'desacato': return { ...comun, dias: 10, tipo: 'habiles', base: 'fechaApertura', baseTexto: 'apertura del incidente por el juzgado', quien: 'El juzgado', que: 'resolver el incidente de desacato; pueden existir excepciones justificadas por el juez', fuente: FUENTES.desacato };
      case 'recurso':
        if (caso.id === 'rec_spd') return { ...comun, dias: 15, tipo: 'habiles', quien: esComunicaciones(datos) ? 'El operador' : 'La empresa', que: 'responder el recurso', fuente: esComunicaciones(datos) ? FUENTES.comunicaciones : FUENTES.servicios,
          nota: esComunicaciones(datos) ? 'Plazo ordinario: puede ampliarse por pruebas en los términos del régimen de comunicaciones. No se declara automáticamente un resultado favorable.' : 'Plazo ordinario. Verifica las excepciones por pruebas o demora atribuible al usuario antes de solicitar el reconocimiento del silencio administrativo positivo.' };
        return { ...comun, meses: 2, tipo: 'calendario', quien: 'La entidad', que: 'revisar la falta de decisión del recurso (referencia para silencio administrativo negativo)', fuente: FUENTES.recurso,
          nota: 'Los dos meses son una referencia para el silencio del artículo 86 del CPACA, no un plazo universal de respuesta. El período de pruebas suspende el cómputo; consulta las reglas especiales del recurso.' };
      case 'habeas': {
        const consulta = consultaDatos(caso, datos);
        return { ...comun, dias: consulta ? 10 : 15, tipo: 'habiles', quien: 'El responsable de los datos', que: consulta ? 'atender la consulta de datos personales' : 'responder el reclamo de datos personales',
          fuente: caso.id === 'hd_reclamo' ? FUENTES.habeasFinanciero : FUENTES.habeas,
          nota: `Plazo ordinario. Si se informa una prórroga motivada, puede haber hasta ${consulta ? 5 : 8} días hábiles adicionales. Verifica el aviso y si la solicitud estaba completa.` };
      }
      case 'denuncia':
      case 'contrato': return null;
      default: {
        const p = caso.guia && caso.guia.plazo;
        if (!p || !Number.isFinite(p.dias) || p.dias <= 0) return null;
        let dias = p.dias;
        if (caso.id === 'pet_general') dias = datos.modalidad === 'informacion' ? 10 : datos.modalidad === 'consulta' ? 30 : 15;
        const quien = caso.tipo === 'familia' ? 'La autoridad competente' : 'La entidad';
        const que = caso.id === 'fam_proteccion' ? 'realizar la actuación indicada en la guía; las medidas urgentes tienen su propio término' : 'responder o realizar la actuación indicada en la guía';
        return { ...comun, dias, tipo: p.tipo === 'habiles' ? 'habiles' : 'calendario', quien, que, fuente: caso.tipo === 'peticion' ? FUENTES.peticion : undefined,
          nota: caso.tipo === 'peticion' ? 'Término ordinario. Puede variar por norma especial, petición incompleta o prórroga debidamente informada antes del vencimiento.' : ADVERTENCIA };
      }
    }
  }

  /* Fecha efectiva de notificación/comunicación: debe tomarla la persona de su constancia. */
  function plazoPresentar(caso, datos) {
    datos = datos || {};
    const f = F().parseISO(datos.fechaNotif);
    if (!f) return null;
    if (caso.tipo === 'impugnacion') return { dias: 3, vence: F().sumarDiasHabiles(f, 3), texto: '3 días hábiles desde la notificación efectiva del fallo', fuente: FUENTES.tutela };
    if (caso.id === 'rec_spd') {
      const dias = diasRecursoServicios(datos);
      return { dias, vence: F().sumarDiasHabiles(f, dias), texto: `${dias} días hábiles desde ${esComunicaciones(datos) ? 'la comunicación de la decisión del operador' : 'el conocimiento de la decisión de la empresa'}`, fuente: esComunicaciones(datos) ? FUENTES.comunicaciones : FUENTES.servicios };
    }
    if (caso.tipo === 'recurso') return { dias: 10, vence: F().sumarDiasHabiles(f, 10), texto: '10 días hábiles desde la notificación efectiva, salvo regla especial', fuente: FUENTES.recurso };
    return null;
  }

  function sumarPlazo(desde, p) {
    if (p.meses) {
      let limite = F().sumarMeses(desde, p.meses);
      while (!F().esHabil(limite)) limite = F().sumarDias(limite, 1);
      return limite;
    }
    return p.tipo === 'habiles' ? F().sumarDiasHabiles(desde, p.dias) : F().sumarDias(desde, p.dias);
  }
  function diaBogota(instante) {
    const local = new Date(instante.getTime() - 5 * 3600000);
    return new Date(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate());
  }
  function horaBogota(instante) {
    const local = new Date(instante.getTime() - 5 * 3600000);
    const d2 = n => String(n).padStart(2, '0');
    return `${d2(local.getUTCDate())}/${d2(local.getUTCMonth() + 1)}/${local.getUTCFullYear()} a las ${d2(local.getUTCHours())}:${d2(local.getUTCMinutes())} (hora de Colombia)`;
  }
  /* Horas continuas/días calendario del fallo. Nunca transforma 48 h en 2 hábiles. */
  function plazoCumplimiento(seg) {
    seg = seg || {};
    const fecha = F().parseISO(seg.fechaInicioCumplimiento);
    const valor = String(seg.plazoCumplimiento || '');
    if (!fecha || !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(seg.horaInicioCumplimiento || '')
      || !/^\d+(?:\.\d{1,2})?$/.test(valor) || +valor <= 0 || +valor > 3650
      || !['horas', 'dias_calendario'].includes(seg.unidadCumplimiento)
      || (seg.unidadCumplimiento === 'dias_calendario' && !Number.isInteger(+valor))) return null;
    // La notificación al solicitante se usa para impugnar; no prueba cuándo nació
    // la obligación del destinatario. El inicio se toma por separado de la orden.
    const desde = new Date(`${seg.fechaInicioCumplimiento}T${seg.horaInicioCumplimiento}:00-05:00`);
    const enDias = seg.unidadCumplimiento === 'dias_calendario';
    const ultimoDia = enDias ? F().clave(F().sumarDias(fecha, +valor)) : null;
    const vence = enDias ? new Date(`${ultimoDia}T23:59:59.999-05:00`) : new Date(desde.getTime() + +valor * 3600000);
    if (!Number.isFinite(vence.getTime())) return null;
    return { desde, vence, precision: 'hora', horas: (vence - desde) / 3600000,
      texto: `${valor} ${enDias ? 'días calendario, hasta finalizar el último día' : 'horas continuas'} según la orden registrada` };
  }
  const textoPlazo = p => p.meses ? `${p.meses} meses` : `${p.dias} días${p.tipo === 'habiles' ? ' hábiles' : ' calendario'}`;
  const faltan = (hoy, vence, p) => p.tipo === 'habiles' ? F().diasHabilesEntre(hoy, vence) : Math.round((vence - hoy) / 86400000);

  /** El cuarto argumento es un instante real, no una fecha truncada a medianoche. */
  function estado(caso, datos, seg, instante) {
    datos = datos || {}; seg = seg || {};
    const ahora = instante || new Date(), hoy = diaBogota(ahora);
    const fl = d => R().fechaLarga(d);
    const r = { fase: 'borrador', nivel: 'neutro', titulo: '', detalle: '', vence: null, restantes: null, siguientes: [], evento: null };
    if (AJ.tipos[caso.tipo] && AJ.tipos[caso.tipo].contrato) {
      r.fase = 'sin_plazo'; r.titulo = seg.fecha ? `Firmado el ${fl(seg.fecha)}` : 'Documento para firmar';
      r.detalle = 'Conserva la copia firmada y las pruebas de cumplimiento. Si hay un conflicto, verifica los requisitos y la vía apropiada para reclamar.';
      return r;
    }
    const fRad = F().parseISO(seg.fecha);
    if (!fRad) {
      r.titulo = 'Todavía no lo has entregado';
      r.detalle = 'Cuando lo entregues, registra la fecha efectiva de recepción y el radicado para consultar el seguimiento al abrir la aplicación.';
      const pp = plazoPresentar(caso, datos);
      if (pp) {
        r.vence = pp.vence;
        const n = F().diasHabilesEntre(hoy, pp.vence);
        r.nivel = pp.vence < hoy || n <= 1 ? 'peligro' : 'alerta';
        r.titulo = pp.vence < hoy ? `El plazo orientativo terminó el ${fl(pp.vence)}` : `Fecha orientativa para presentarlo: ${fl(pp.vence)}`;
        r.detalle = `Plazo de referencia: ${pp.texto}. ${ADVERTENCIA}`;
        if (pp.vence >= hoy) { r.restantes = n; r.evento = { fecha: pp.vence, titulo: `Revisar plazo para presentar: ${caso.titulo}`, descripcion: r.detalle }; }
      }
      return r;
    }
    if (caso.tipo === 'denuncia') {
      r.fase = 'sin_plazo'; r.titulo = `Presentada el ${fl(fRad)}`;
      r.detalle = `Consulta el avance con la noticia criminal${seg.numero ? ` (${seg.numero})` : ''}. Esta herramienta no calcula un término de investigación. Si sigues en riesgo, busca protección inmediata.`;
      r.siguientes = caso.id === 'muj_denuncia' ? ['muj_tutela_proteccion', 'fam_proteccion'] : ['pet_juzgado'];
      return r;
    }
    if (caso.tipo === 'tutela' || caso.tipo === 'impugnacion') {
      // El día del fallo no equivale al de su notificación efectiva.
      const fNot = F().parseISO(seg.fechaNotificacion);
      const decision = seg.decision === 'improcedente' ? 'nego' : seg.decision;
      if (decision === 'concedio' || decision === 'parcial') {
        r.fase = seg.cumple === 'si' ? 'cerrado' : 'fallo'; r.nivel = 'ok';
        if (seg.cumple === 'si') { r.titulo = 'Registraste el cumplimiento de la orden'; r.detalle = 'Conserva el fallo y las pruebas de cumplimiento.'; }
        else {
          const p = plazoCumplimiento(seg);
          r.titulo = 'Hay una orden judicial por verificar';
          r.detalle = 'Revisa la conducta ordenada, a quién se dirige y desde qué hecho se cuenta el plazo. Registra por separado la fecha y hora de inicio del cumplimiento según la orden y la constancia del obligado, la cantidad y la unidad. La notificación al solicitante no reemplaza ese inicio. No se presume un plazo de 48 horas.';
          if (p) {
            r.vence = p.vence;
            const vencido = ahora >= p.vence;
            r.nivel = vencido ? 'alerta' : 'neutro';
            r.titulo = vencido ? 'Se cumplió el plazo que registraste del fallo' : `Plazo registrado: ${horaBogota(p.vence)}`;
            r.detalle = `${p.texto}, contado desde ${horaBogota(p.desde)}: ${horaBogota(p.vence)}. Verifica que el inicio y la duración coincidan con la orden; si falta cumplimiento, informa al juez y consulta las vías de cumplimiento e incidente de desacato.`;
            r.evento = { fecha: p.vence, precision: 'hora', titulo: `Revisar cumplimiento: ${datos.entidadNombre || caso.titulo}`, descripcion: r.detalle };
            if (vencido) r.siguientes = ['desacato'];
          } else if (seg.cumple === 'no') {
            r.nivel = 'alerta'; r.detalle += ' Registraste que no se ha cumplido: informa al juzgado y verifica si procede el escrito de cumplimiento o desacato.'; r.siguientes = ['desacato'];
          }
        }
        if (decision === 'parcial' && caso.tipo === 'tutela') {
          const limite = fNot && F().sumarDiasHabiles(fNot, 3);
          if (!limite || hoy <= limite) {
            r.siguientes.push('impugnacion');
            r.detalle += limite ? ` Para impugnar lo no concedido, la fecha orientativa es el ${fl(limite)}; verifica la notificación efectiva.` : ' La parte no concedida puede impugnarse en el término legal; falta la fecha efectiva de notificación para estimarlo.';
          }
        }
        return r;
      }
      if (decision === 'nego') {
        r.fase = 'fallo'; r.nivel = 'alerta';
        if (caso.tipo === 'impugnacion') { r.titulo = 'Registraste una decisión negativa de segunda instancia'; r.detalle = 'Consulta las razones del fallo y, si necesitas orientación, las opciones de eventual revisión constitucional; no existe una tercera instancia ordinaria de tutela.'; return r; }
        r.siguientes = ['impugnacion'];
        if (!fNot) { r.titulo = 'Verifica el término para impugnar'; r.detalle = 'Son 3 días hábiles desde la notificación efectiva. Registra esa fecha según la constancia; la fecha del fallo no la reemplaza.'; return r; }
        const limite = F().sumarDiasHabiles(fNot, 3);
        r.vence = limite;
        if (hoy <= limite) {
          r.nivel = 'peligro'; r.restantes = F().diasHabilesEntre(hoy, limite); r.titulo = `Fecha orientativa para impugnar: ${fl(limite)}`;
          r.detalle = `Verifica la notificación efectiva y presenta el escrito ante el juzgado que decidió. ${ADVERTENCIA}`;
          r.evento = { fecha: limite, titulo: 'Revisar término de impugnación de tutela', descripcion: r.detalle };
        } else { r.titulo = `La fecha orientativa de impugnación fue el ${fl(limite)}`; r.detalle = 'Consulta de inmediato la notificación y las opciones con la Personería, Defensoría del Pueblo o un consultorio jurídico.'; r.siguientes = []; }
        return r;
      }
    }
    const respuesta = ({ positiva: 'favorable', desfavorable: 'negativa', incompleta: 'parcial', si: 'tramite', prorroga: 'tramite' })[seg.respuesta] || seg.respuesta;
    if (respuesta === 'favorable') { r.fase = 'cerrado'; r.nivel = 'ok'; r.titulo = 'Registraste una respuesta favorable'; r.detalle = 'Conserva la respuesta y verifica que se cumpla lo ofrecido. Si hay incumplimiento, consulta la vía adecuada para reclamar.'; return r; }
    if (['parcial', 'tramite', 'negativa'].includes(respuesta)) {
      r.fase = 'respondido'; r.nivel = 'alerta'; r.siguientes = siguientesDe(caso, 'noResuelve');
      if (caso.id === 'pet_spd' && ['negativa', 'parcial'].includes(respuesta)) {
        const dias = diasRecursoServicios(datos);
        const fResp = F().parseISO(seg.fechaNotificacion);
        const autoridad = esComunicaciones(datos) ? 'Superintendencia de Industria y Comercio (SIC)' : 'Superintendencia de Servicios Públicos';
        r.titulo = 'Verifica si corresponde recurso contra la respuesta';
        r.detalle = `Referencia: ${dias} días hábiles desde ${esComunicaciones(datos) ? 'la comunicación' : 'el conocimiento'} de la decisión. La apelación, si procede, corresponde a la ${autoridad}.`;
        if (fResp) {
          const lim = F().sumarDiasHabiles(fResp, dias); r.vence = lim;
          r.detalle += ` Fecha orientativa: ${fl(lim)}. ${ADVERTENCIA}`;
          if (lim >= hoy) r.evento = { fecha: lim, titulo: 'Revisar término de recurso contra la empresa', descripcion: r.detalle };
          else { r.siguientes = []; r.detalle += ' Busca orientación sobre las opciones disponibles.'; }
        } else r.detalle += ' Registra la fecha efectiva en que te comunicaron o conociste la respuesta para estimar el vencimiento.';
        return r;
      }
      r.titulo = respuesta === 'negativa' ? 'Registraste una respuesta negativa' : 'Revisa el alcance de la respuesta';
      r.detalle = respuesta === 'negativa'
        ? 'Una respuesta de fondo puede ser negativa sin vulnerar por ello el derecho de petición. Revisa los fundamentos, los recursos y las condiciones de cualquier otra acción.'
        : 'Distingue una respuesta incompleta de un aviso de prórroga motivada. Comprueba el plazo comunicado y, si no hay respuesta de fondo o persiste la afectación, revisa las opciones con orientación jurídica.';
      return r;
    }
    const p = plazoRespuesta(caso, datos);
    if (!p) { r.fase = 'sin_plazo'; r.titulo = `Entregado el ${fl(fRad)}`; r.detalle = caso.guia && caso.guia.nota || 'Consulta el estado y las reglas del trámite con la entidad competente.'; return r; }
    const desde = F().parseISO(seg[p.base || 'fecha']);
    if (!desde || desde < fRad) {
      r.fase = 'sin_plazo'; r.titulo = `Falta confirmar la ${p.baseTexto}`;
      r.detalle = `El término de referencia es ${textoPlazo(p)} desde la ${p.baseTexto}. La radicación del escrito no reemplaza ese hecho. Consulta la constancia del juzgado y registra la fecha para calcularlo.`;
      return r;
    }
    const vence = sumarPlazo(desde, p); r.vence = vence;
    if (hoy <= vence) {
      const n = faltan(hoy, vence, p); r.fase = 'esperando'; r.restantes = n; r.nivel = n <= 2 ? 'alerta' : 'neutro';
      r.titulo = `Fecha orientativa de seguimiento: ${fl(vence)}`;
      r.detalle = `${textoPlazo(p)} desde la ${p.baseTexto} (${fl(desde)}) para ${p.que}. ${p.nota || ADVERTENCIA}`;
      r.evento = { fecha: vence, titulo: `Revisar trámite: ${caso.titulo}`, descripcion: r.detalle };
      return r;
    }
    r.fase = 'vencido'; r.nivel = 'alerta'; r.titulo = `Pasó la fecha de referencia: ${fl(vence)}`;
    if (['tutela', 'impugnacion', 'desacato'].includes(caso.tipo)) {
      r.detalle = `Consulta el proceso o el despacho para confirmar la decisión y las notificaciones. ${p.nota || ADVERTENCIA}`;
      r.siguientes = ['pet_juzgado']; return r;
    }
    if (caso.id === 'pet_spd' || caso.id === 'rec_spd') {
      r.detalle = esComunicaciones(datos)
        ? 'Verifica si hubo respuesta o ampliación válida por pruebas. Puede corresponder silencio administrativo positivo bajo el régimen de comunicaciones; consulta su reconocimiento ante el operador y, según el caso, la SIC. Este contador no lo declara.'
        : 'Verifica si hubo respuesta, práctica de pruebas o demora atribuible al usuario. Cuando se cumplen los requisitos puede proceder el silencio administrativo positivo; solicita su reconocimiento y consulta a la Superintendencia de Servicios Públicos. Este contador no lo declara.';
      return r;
    }
    if (caso.tipo === 'recurso') { r.detalle = p.nota; r.siguientes = siguientesDe(caso, 'vencido'); return r; }
    r.detalle = `${p.nota || ADVERTENCIA} Si no hay respuesta de fondo, revisa la alternativa adecuada; que venza el contador no garantiza que una tutela proceda ni que se conceda.`;
    r.siguientes = siguientesDe(caso, 'vencido');
    return r;
  }

  /* ---------- Encadenamiento: prellenar el siguiente documento ---------- */
  function definiciones(caso) {
    const defs = {};
    const sol = AJ.campos.solicitante({ permiteAnonimo: true });
    const dest = AJ.campos.destinatario(caso.destinatario || {});
    const extra = caso.tipo === 'tutela' && AJ.campos.tutelaExtra ? AJ.campos.tutelaExtra() : [];
    [...sol, ...dest, ...extra, ...(caso.campos || [])].forEach(c => { if (c.id && c.tipo !== 'info') defs[c.id] = c; });
    return defs;
  }
  function valido(def, v) {
    if (v == null || v === '') return undefined;
    if (def.tipo === 'select' || def.tipo === 'radio') return (def.opciones || []).some(o => o.v === v) ? v : undefined;
    if (def.tipo === 'checks') { const ok = (Array.isArray(v) ? v : []).filter(x => (def.opciones || []).some(o => o.v === x)); return ok.length ? ok : undefined; }
    return typeof v === 'string' || typeof v === 'number' ? String(v) : undefined;
  }
  const canalAMedio = c => ({ ventanilla: 'escrito', correo: 'correo', web: 'web' }[c] || 'escrito');
  const respuestaAPrevia = r => ({ parcial: 'parcial', tramite: 'parcial', negativa: 'negaron' }[r] || 'nada');

  /** Datos iniciales del documento "destino" a partir de un documento ya presentado */
  function prellenar(origen, datosO, seg, destino) {
    seg = seg || {};
    datosO = datosO || {};
    const defs = definiciones(destino);
    const out = {};
    const poner = (id, v) => { if (!defs[id]) return; const ok = valido(defs[id], v); if (ok !== undefined) out[id] = ok; };
    const permiteAnonimo = destino.tipo === 'peticion' || destino.tipo === 'queja';
    IDENTIDAD.forEach(id => poner(id, datosO[id]));
    if (datosO.modo === 'anonimo' && !permiteAnonimo) { out.modo = 'propio'; }
    if (destino.tipo !== 'denuncia') ENTIDAD.forEach(id => poner(id, datosO[id]));
    // Mismos campos con el mismo significado (diagnóstico, servicio, radicado, salario…)
    Object.keys(datosO).forEach(id => { if (!NO_COPIAR.has(id) && !IDENTIDAD.includes(id) && !ENTIDAD.includes(id) && out[id] === undefined) poner(id, datosO[id]); });
    // La solicitud anterior pasa a ser un hecho del nuevo documento
    if (seg.fecha && defs.yaPedi) {
      poner('yaPedi', 'si'); poner('fechaPrevia', seg.fecha); poner('radicadoPrevio', seg.numero); poner('medioPrevio', canalAMedio(seg.canal)); poner('respuestaPrevia', respuestaAPrevia(seg.respuesta));
    }
    const pedido = () => {
      const marcadas = (origen.peticiones || []).filter(o => (datosO.peticiones || []).includes(o.v)).map(o => R().capital(o.t.replace(/^Que /, '')));
      const otras = R().relatoAHechos(datosO.peticionOtra);
      return [...marcadas, ...otras].join(' ').trim();
    };
    const quitar = (...ids) => ids.forEach(id => { delete out[id]; });
    switch (destino.id) {
      case 'tut_peticion': {
        quitar('radicado', 'objeto', 'respuesta');
        poner('fechaPeticion', seg.fecha || datosO.fechaPrevia);
        poner('radicado', seg.numero || datosO.radicadoPrevio);
        poner('medio', seg.fecha ? canalAMedio(seg.canal) : 'escrito');
        const p = plazoRespuesta(origen, datosO);
        poner('tipoPeticion', p && p.dias === 10 ? 'documentos' : p && p.dias === 30 ? 'consulta' : 'general');
        poner('objeto', pedido() || datosO.tema || datosO.objeto);
        poner('respuesta', { parcial: 'parcial', tramite: 'tramite', negativa: 'parcial' }[seg.respuesta] || 'nada');
        break;
      }
      case 'desacato':
      case 'impugnacion':
        quitar('radicado', 'decision', 'fechaFallo', 'fechaNotif', 'fechaNotificacion', 'juzgado');
        poner('juzgado', seg.juzgado);
        poner('radicado', seg.numero);
        poner('fechaFallo', seg.fechaRespuesta);
        // La fecha en que se notificó al solicitante solo sirve para su impugnación.
        // Para desacato debe verificarse la notificación al obligado; un inicio de
        // cumplimiento genérico puede ser otro hito y tampoco la acredita.
        if (destino.id === 'impugnacion') { poner('fechaNotificacion', seg.fechaNotificacion); poner('fechaNotif', seg.fechaNotificacion); }
        if (destino.id === 'impugnacion') poner('decision', seg.decision === 'parcial' ? 'parcial' : 'nego');
        break;
      case 'tut_habeas_data':
        poner('reclamo', 'si'); poner('fechaReclamo', seg.fecha);
        break;
      case 'rec_spd':
        quitar('fechaNotif', 'respuesta');
        poner('fechaNotif', seg.fechaNotificacion);
        poner('respuesta', seg.numeroRespuesta);
        break;
      case 'tut_debido_proceso':
        quitar('decision', 'fechaConocio', 'fechaRecurso');
        poner('decision', datosO.acto || datosO.respuesta);
        poner('fechaConocio', datosO.fechaNotif);
        poner('fechaRecurso', seg.fecha);
        break;
      case 'tut_salud_servicio':
        if (origen.id === 'queja_supersalud') { quitar('entidadNombre', 'entidadCargo', 'entidadDireccion', 'entidadCiudad'); poner('categoria', 'eps'); poner('entidadNombre', datosO.eps); }
        break;
      case 'tut_salario':
        if (!out.periodos) poner('periodos', datosO.periodoDeuda);
        if (datosO.vinculo === 'domestico') poner('vinculo', 'laboral');
        break;
      case 'muj_tutela_proteccion':
        quitar('radicado', 'fechaSolicitud', 'relacion');
        poner('agresor', datosO.agresor || datosO.denunciado);
        poner('relacion', datosO.relacion || ({ conyuge: 'pareja', ex: 'ex', padre: 'familiar', hijo: 'familiar', hermano: 'familiar' }[datosO.relacionAgresor]));
        poner('fechaSolicitud', seg.fecha);
        poner('radicado', seg.numero);
        poner('quienFalla', origen.id === 'muj_denuncia' ? 'fiscalia' : origen.tipo === 'familia' ? 'comisaria' : undefined);
        if (origen.id === 'fam_proteccion') poner('violencia', (datosO.tipoViolencia || []).filter(v => v !== 'ninos'));
        if (origen.id === 'muj_denuncia') poner('violencia', (datosO.delitos || []).map(v => ({ golpes: 'fisica', maltrato: 'psicologica', amenazas: 'amenazas', sexual: 'sexual', acoso: 'sexual', intento: 'fisica', economica: 'economica' }[v])).filter(Boolean));
        poner('relatoHechos', datosO.relatoHechos || datosO.hechos);
        break;
      case 'fam_proteccion':
        if (origen.id === 'muj_denuncia') { poner('agresor', datosO.denunciado); poner('direccionAgresor', datosO.denunciadoDireccion); poner('hechos', datosO.relatoHechos); poner('ultimoHecho', datosO.ultimoHecho); poner('convive', datosO.convive); }
        break;
    }
    if (out.categoria === undefined && destino.destinatario && destino.destinatario.categoria) out.categoria = destino.destinatario.categoria;
    return out;
  }

  return { CANALES, RESPUESTAS, DECISIONES, SIGUIENTES, FUENTES, plazoRespuesta, plazoPresentar, plazoCumplimiento, sumarPlazo, diaBogota, horaBogota, estado, prellenar, siguientesDe, definiciones };
})();
