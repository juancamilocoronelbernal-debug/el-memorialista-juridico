const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const fechaLarga = (d = new Date()) => `${d.getDate()} de ${MESES[d.getMonth()]} de ${d.getFullYear()}`;
const dos = n => String(n).padStart(2, '0');
const fechaCorta = ms => { const d = new Date(ms); return `${dos(d.getDate())}/${dos(d.getMonth() + 1)}/${d.getFullYear()}`; };
const horaCorta = ms => { const d = new Date(ms); return `${dos(d.getHours())}:${dos(d.getMinutes())}`; };
const pesos = n => '$' + Math.round(Number(n) || 0).toLocaleString('es-CO');
const clon = o => JSON.parse(JSON.stringify(o));

const AYUDA_HECHOS = 'Escríbelos como te salgan: en borrador, en viñetas o en desorden. Se redactan con lenguaje jurídico y en orden cronológico, sin agregar hechos.';
const DESP = {
  tutela: ['Juez Civil Municipal de Bogotá D.C. (Reparto)', 'Juez Penal Municipal de Medellín con Función de Control de Garantías (Reparto)', 'Juez Laboral del Circuito de Cali (Reparto)', 'Juez de la República (Reparto)'],
  civil: ['Juez Civil Municipal de Bogotá D.C. (Reparto)', 'Juez Civil del Circuito de Medellín (Reparto)', 'Juez de Pequeñas Causas y Competencia Múltiple de Cali (Reparto)'],
  familia: ['Juez de Familia de Bogotá D.C. (Reparto)', 'Juez Promiscuo de Familia de Zipaquirá (Reparto)'],
  laboral: ['Juez Laboral Municipal de Bogotá D.C. (Reparto)', 'Juez Laboral del Circuito de Barranquilla (Reparto)'],
  admin: ['Juez Administrativo del Circuito de Bogotá D.C. (Reparto)', 'Tribunal Administrativo de Antioquia (Reparto)'],
  penal: ['Fiscalía General de la Nación, Fiscal Seccional (Reparto)', 'Fiscalía General de la Nación, Fiscal Local (Reparto)'],
  conciliacion: ['Procuraduría Judicial para Asuntos Administrativos (Reparto)', 'Centro de Conciliación de la Cámara de Comercio de Bogotá', 'Comisaría de Familia de Suba', 'Notaría 20 del Círculo de Bogotá'],
  disciplinario: ['Procuraduría General de la Nación', 'Personería de Bogotá D.C.', 'Comisión Seccional de Disciplina Judicial de Antioquia'],
  entidad: ['Señores Administradora Colombiana de Pensiones, Colpensiones', 'Señores Alcaldía de Medellín, Secretaría de Movilidad', 'Señores Banco de Ejemplo S.A., Servicio al Cliente'],
};
const C = {
  dest: (ph, sug, l = 'Juez o despacho', ayuda) => ({ k: 'destinatario', l, t: 'texto', req: true, ph, sug, ayuda }),
  ciudad: () => ({ k: 'ciudad', l: 'Ciudad', t: 'texto', ph: 'Bogotá D.C.', def: '@ciudad', ayuda: 'Donde se radica el escrito.' }),
  radicado: req => ({ k: 'radicado', l: 'Radicado del proceso', t: 'radicado', req: !!req, ph: '11001-40-03-012-2026-00345-00' }),
  parte: (k, l, ph, req = true) => ({ k, l, t: 'area', rows: 3, req, ph }),
  area: (k, l, ph, o = {}) => ({ k, l, t: 'area', rows: o.rows || 4, req: !!o.req, ph, ayuda: o.ayuda }),
  texto: (k, l, ph, o = {}) => ({ k, l, t: 'texto', req: !!o.req, ph, ayuda: o.ayuda }),
  select: (k, l, opciones, o = {}) => ({ k, l, t: 'select', opciones, req: !!o.req, def: o.def, ayuda: o.ayuda }),
  chips: (k, l, opciones, o = {}) => ({ k, l, t: 'chips', opciones, req: !!o.req, ayuda: o.ayuda }),
  check: (k, l, def = true) => ({ k, l, t: 'check', def }),
  hechos: (ph, o = {}) => ({ k: 'hechos', l: o.l || 'Hechos', t: 'area', rows: o.rows || 8, req: o.req !== false, ph, ayuda: AYUDA_HECHOS }),
  pruebas: ph => ({ k: 'pruebas', l: 'Pruebas y anexos', t: 'area', rows: 3, ph }),
  notif: ph => ({ k: 'notificaciones', l: 'Direcciones de notificación', t: 'area', rows: 2, ph: ph || 'Tu cliente: dirección y correo. La contraparte: dirección, correo y cómo lo obtuviste.' }),
};
const PH_PERSONA = 'Nombre completo, cédula, ciudad de domicilio, dirección, correo y teléfono.';
const PH_ENTIDAD = 'Entidad o persona, NIT si lo conoces, representante legal y correo de notificaciones judiciales.';
const JURIS_PROC = [['civil', 'Civil, comercial o familia (CGP)'], ['laboral', 'Laboral (Ley 2452 de 2025)'], ['admin', 'Contencioso administrativo (CPACA)'], ['penal', 'Penal (Ley 906 de 2004)']];

const TIPOS_LISTA = [
  {
    id: 'tutela', nombre: 'Acción de tutela', area: 'Constitucional', norma: 'Art. 86 C.P. · D. 2591/1991', rolFirma: 'de la parte accionante', rolCliente: 'la parte accionante',
    desc: 'Protección inmediata de derechos fundamentales.',
    grupos: [
      { n: 'Despacho', campos: [C.dest('Juez Civil Municipal de Bogotá D.C. (Reparto)', DESP.tutela, 'Juez', 'Si no sabes el despacho, escribe “Juez de la República (Reparto)”.'), C.ciudad()] },
      { n: 'Partes', campos: [
        C.parte('cliente', 'Accionante', PH_PERSONA + '\nSi actúa por un menor o como agente oficioso, indícalo.'),
        C.parte('contraparte', 'Accionado(s)', PH_ENTIDAD),
        C.area('vinculados', 'Terceros a vincular (opcional)', 'Ej.: Superintendencia Nacional de Salud; ADRES.', { rows: 2 }),
      ] },
      { n: 'El caso', campos: [
        C.chips('derechos', 'Derechos fundamentales vulnerados', ['Salud', 'Vida digna', 'Seguridad social', 'Mínimo vital', 'Petición', 'Debido proceso', 'Igualdad', 'Trabajo', 'Estabilidad laboral reforzada', 'Educación', 'Vivienda digna', 'Hábeas data', 'Intimidad', 'Buen nombre', 'Dignidad humana', 'Acceso a la administración de justicia', 'Unidad familiar', 'Libre desarrollo de la personalidad'], { req: true }),
        C.hechos('Ej.: 2/09 el médico le ordenó el medicamento X. 9/09 la EPS lo negó por falta de autorización del comité técnico. Desde entonces no recibe el tratamiento…'),
        C.area('procedencia', 'Procedencia: subsidiariedad e inmediatez', 'Ej.: Pasaron 6 semanas desde la negativa; no hay otro medio igual de eficaz porque el tratamiento es continuo; es adulta mayor.', { rows: 3, ayuda: 'Por qué la tutela es el medio adecuado y cuánto tiempo ha pasado desde la vulneración.' }),
        C.area('pretensiones', 'Lo que se pide al juez', 'Ej.: Ordenar a la EPS entregar el medicamento en 48 horas y garantizar el tratamiento integral.', { req: true }),
        C.area('medida', 'Medida provisional (opcional)', 'Ej.: Entrega inmediata del medicamento mientras se decide, porque suspenderlo agrava la enfermedad.', { rows: 2 }),
      ] },
      { n: 'Pruebas y notificaciones', campos: [
        C.pruebas('Ej.: Fórmula médica del 2/09/2026; respuesta de la EPS del 9/09/2026; cédula de la accionante; poder.'),
        C.check('juramento', 'Manifestar bajo juramento que no se ha presentado otra tutela por los mismos hechos (art. 37, D. 2591 de 1991)', true),
        C.notif('Accionante: dirección y correo. Accionado: correo de notificaciones judiciales.'),
      ] },
    ],
    guia: `Fundamento: artículo 86 de la Constitución, Decreto 2591 de 1991 y Decreto 306 de 1992. Reparto: Decreto 1069 de 2015, modificado por el Decreto 333 de 2021. La tutela es informal y no requiere abogado; no le apliques las cargas de admisión de la demanda del artículo 6 de la Ley 2213 de 2022 (sentencia C-522 de 2023).
Estructura: lugar y fecha; destinatario (Juez … (Reparto)) y, si aplica, E. S. D.; bloque de referencia (Referencia: Acción de tutela; Accionante; Accionado; Derechos invocados); párrafo de presentación con identificación de quien actúa y la calidad en que lo hace; HECHOS (numerados y cronológicos, con fechas); DERECHOS FUNDAMENTALES VULNERADOS (cada derecho y cómo se vulnera); PROCEDENCIA DE LA ACCIÓN (legitimación por activa y por pasiva; subsidiariedad: inexistencia de otro medio idóneo y eficaz o perjuicio irremediable; inmediatez); FUNDAMENTOS DE DERECHO; MEDIDA PROVISIONAL solo si se pide (art. 7 del Decreto 2591 de 1991: necesidad y urgencia); PRETENSIONES (órdenes concretas y verificables, con plazo, normalmente 48 horas); PRUEBAS (enumeradas; pide que se oficie al accionado por los documentos que estén en su poder); JURAMENTO (art. 37 del Decreto 2591 de 1991); ANEXOS; NOTIFICACIONES.
Si el accionado es un particular, explica por qué procede la tutela en su contra (art. 42 del Decreto 2591 de 1991: servicio público, subordinación o indefensión).`,
    ejemplo: {
      destinatario: 'Juez Civil Municipal de Bogotá D.C. (Reparto)', ciudad: 'Bogotá D.C.',
      cliente: 'María Fernanda López Rincón, C.C. 52.123.456 de Bogotá, 63 años, domiciliada en Bogotá, Calle 45 # 13-20, maria.lopez@correo.com, 310 555 0101.',
      contraparte: 'EPS Salud Ejemplo S.A.S., NIT 900.123.456-7, notificaciones judiciales: notificaciones@epsejemplo.com',
      derechos: ['Salud', 'Vida digna', 'Seguridad social'],
      hechos: '- afiliada al régimen contributivo de la EPS desde 2015\n- 2/09/2026 el reumatólogo le diagnosticó artritis reumatoide y le ordenó tofacitinib 5 mg cada 12 horas por 3 meses\n- 9/09/2026 la EPS negó la entrega: dijo que requiere autorización del comité técnico, que no ha resuelto\n- sin el medicamento tiene dolor e inflamación y no puede trabajar (es costurera independiente)\n- presentó queja ante la EPS el 15/09/2026 y no le han respondido',
      procedencia: 'Han pasado 6 semanas desde la negativa. Es adulta mayor, sujeto de especial protección, y el tratamiento es continuo; no hay otro medio igual de eficaz.',
      pretensiones: 'Que se ordene a la EPS entregar el medicamento en 48 horas y garantizar el tratamiento integral para la artritis reumatoide.',
      pruebas: 'Fórmula médica del 2/09/2026; respuesta de la EPS del 9/09/2026; queja del 15/09/2026; cédula; poder.',
      juramento: true,
      notificaciones: 'Accionante: Calle 45 # 13-20, Bogotá; maria.lopez@correo.com. EPS: notificaciones@epsejemplo.com',
    },
  },
  {
    id: 'impugnacion_tutela', nombre: 'Impugnación de fallo de tutela', area: 'Constitucional', norma: 'Art. 31 D. 2591/1991', rolFirma: 'de la parte impugnante', rolCliente: 'la parte que impugna',
    desc: 'Recurso contra la sentencia de primera instancia, dentro de los 3 días siguientes a su notificación.',
    grupos: [
      { n: 'Despacho', campos: [C.dest('Juez Quinto Civil Municipal de Bogotá D.C.', DESP.tutela, 'Juez que dictó el fallo'), C.radicado(false), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Parte que impugna', PH_PERSONA + ' Indica si es accionante o accionado.'), C.parte('contraparte', 'Contraparte', PH_ENTIDAD)] },
      { n: 'El fallo', campos: [
        C.area('fallo', 'Fallo impugnado', 'Ej.: Sentencia del 10/10/2026 que negó la tutela por improcedente; notificada el 14/10/2026.', { rows: 3, req: true }),
        C.area('razones', 'Razones de inconformidad', 'Ej.: El juez dijo que había otro medio judicial, pero no valoró que la accionante es adulta mayor y el tratamiento es urgente…', { rows: 7, req: true }),
        C.area('pretensiones', 'Lo que se pide al superior', 'Ej.: Revocar el fallo y, en su lugar, amparar los derechos y ordenar la entrega del medicamento.', { req: true }),
        C.pruebas('Opcional: pruebas nuevas o documentos que el juez no valoró.'),
      ] },
    ],
    guia: `Fundamento: artículos 31 y 32 del Decreto 2591 de 1991. Término: dentro de los 3 días siguientes a la notificación del fallo. Se presenta ante el juez de primera instancia, que lo remite al superior jerárquico.
Estructura: destinatario (el juez que dictó el fallo); referencia (Impugnación de fallo de tutela; radicado; accionante; accionado); presentación y oportunidad (indica la fecha de notificación y que se presenta dentro del término); ANTECEDENTES (lo pedido y lo decidido, brevemente); RAZONES DE LA IMPUGNACIÓN (cargo por cargo: errores fácticos, probatorios o jurídicos del fallo, cada uno con su argumentación); SOLICITUD (revocar o modificar y, en su lugar, las órdenes concretas); PRUEBAS si hay; NOTIFICACIONES.`,
  },
  {
    id: 'desacato', nombre: 'Incidente de desacato', area: 'Constitucional', norma: 'Arts. 27 y 52 D. 2591/1991', rolFirma: 'de la parte accionante', rolCliente: 'la parte accionante',
    desc: 'Cuando el accionado no cumple el fallo de tutela.',
    grupos: [
      { n: 'Despacho', campos: [C.dest('Juez Quinto Civil Municipal de Bogotá D.C.', DESP.tutela, 'Juez que dictó el fallo'), C.radicado(false), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Accionante', PH_PERSONA), C.parte('contraparte', 'Accionado y funcionario responsable', 'Entidad, y si lo sabes, nombre y cargo del funcionario que debe cumplir y de su superior.')] },
      { n: 'El incumplimiento', campos: [
        C.area('fallo', 'Fallo y órdenes', 'Ej.: Sentencia del 5/09/2026 que ordenó entregar el medicamento en 48 horas.', { rows: 3, req: true }),
        C.area('incumplimiento', 'Qué no se ha cumplido', 'Ej.: A la fecha no han entregado el medicamento; el 20/09 radiqué solicitud de cumplimiento y respondieron que está en trámite.', { rows: 6, req: true }),
        C.area('pretensiones', 'Solicitudes', 'Si lo dejas vacío: requerir al responsable y a su superior, abrir el incidente, sancionar y ordenar el cumplimiento inmediato.', { rows: 3 }),
        C.pruebas('Ej.: Copia del fallo; solicitudes de cumplimiento; respuestas de la entidad.'),
      ] },
    ],
    guia: `Fundamento: artículos 27 (cumplimiento del fallo: el juez requiere al superior del responsable y puede sancionar a ambos) y 52 (desacato: arresto hasta de seis meses y multa hasta de veinte salarios mínimos mensuales, sin perjuicio de las sanciones penales) del Decreto 2591 de 1991. El desacato tiene carácter subjetivo: identifica al funcionario responsable de cumplir y su superior, si se conocen.
Estructura: destinatario; referencia (Incidente de desacato; radicado; accionante; accionado); presentación; ANTECEDENTES (el fallo, su fecha y las órdenes con su plazo); HECHOS DEL INCUMPLIMIENTO (fechas, requerimientos y respuestas); FUNDAMENTOS; SOLICITUDES (requerir al responsable y a su superior conforme al art. 27, abrir el incidente, imponer las sanciones del art. 52 y adoptar las medidas para el cumplimiento efectivo); PRUEBAS; NOTIFICACIONES.`,
  },
  {
    id: 'cumplimiento', nombre: 'Acción de cumplimiento', area: 'Constitucional', norma: 'Art. 87 C.P. · Ley 393/1997', rolFirma: 'de la parte accionante', rolCliente: 'la parte accionante',
    desc: 'Exige que una autoridad cumpla una norma con fuerza de ley o un acto administrativo.',
    grupos: [
      { n: 'Despacho', campos: [C.dest('Juez Administrativo del Circuito de Bogotá D.C. (Reparto)', DESP.admin), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Accionante', PH_PERSONA), C.parte('contraparte', 'Autoridad o particular incumplido', PH_ENTIDAD)] },
      { n: 'El caso', campos: [
        C.area('norma', 'Norma o acto incumplido', 'Ej.: Artículo 5 del Acuerdo 123 de 2024 del Concejo, que ordena instalar semáforos en la intersección…', { rows: 3, req: true }),
        C.area('renuencia', 'Constitución en renuencia', 'Ej.: El 1/08/2026 pedí por escrito el cumplimiento; la Secretaría no respondió en 10 días (o respondió negándolo el …).', { rows: 3, req: true, ayuda: 'Requisito de procedibilidad (art. 8, Ley 393 de 1997).' }),
        C.hechos('Ej.: La norma está vigente desde…; la autoridad no ha hecho…'),
        C.area('pretensiones', 'Lo que se pide', 'Ej.: Ordenar a la Secretaría cumplir el artículo 5 del Acuerdo 123 de 2024 dentro de un plazo razonable.', { req: true }),
        C.pruebas('Ej.: Copia del acuerdo; solicitud de cumplimiento y su constancia de radicación.'), C.notif(),
      ] },
    ],
    guia: `Fundamento: artículo 87 de la Constitución; Ley 393 de 1997: art. 8 (procedibilidad: haber reclamado antes el cumplimiento del deber y que la autoridad se ratifique en el incumplimiento o no conteste dentro de los 10 días siguientes, salvo inminente perjuicio irremediable), art. 9 (improcedencia: cuando existe otro instrumento judicial, para proteger derechos amparables por tutela o para exigir normas que establezcan gastos) y art. 10 (contenido de la solicitud); artículo 146 del CPACA.
Estructura: destinatario; referencia (Acción de cumplimiento; accionante; accionado); presentación; NORMA O ACTO INCUMPLIDO (indica el deber; transcríbelo solo si el abogado lo suministra); HECHOS; CONSTITUCIÓN EN RENUENCIA; PROCEDENCIA; PRETENSIONES (ordenar el cumplimiento dentro de un plazo); PRUEBAS; JURAMENTO (manifestar bajo la gravedad del juramento que no se ha presentado otra solicitud respecto de los mismos hechos o derechos ante otra autoridad, art. 10 num. 7); NOTIFICACIONES.`,
  },
  {
    id: 'popular', nombre: 'Acción popular', area: 'Constitucional', norma: 'Art. 88 C.P. · Ley 472/1998', rolFirma: 'de la parte actora', rolCliente: 'el actor popular',
    desc: 'Protección de derechos e intereses colectivos.',
    grupos: [
      { n: 'Despacho', campos: [C.dest('Juez Administrativo del Circuito de Bogotá D.C. (Reparto)', DESP.admin, 'Juez', 'Administrativo si el demandado es una autoridad o un particular con funciones administrativas; civil del circuito en los demás casos.'), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Actor popular', PH_PERSONA), C.parte('contraparte', 'Demandado(s)', PH_ENTIDAD)] },
      { n: 'El caso', campos: [
        C.chips('colectivos', 'Derechos colectivos amenazados', ['Goce de un ambiente sano', 'Moralidad administrativa', 'Goce del espacio público', 'Defensa del patrimonio público', 'Seguridad y salubridad públicas', 'Servicios públicos eficientes y oportunos', 'Prevención de desastres técnicamente previsibles', 'Derechos de los consumidores y usuarios', 'Acceso a la infraestructura de servicios', 'Realización de construcciones respetando las normas urbanísticas'], { req: true }),
        C.area('requisito', 'Solicitud previa a la autoridad (art. 144 CPACA)', 'Ej.: El 1/07/2026 pedí a la Alcaldía adoptar medidas; no respondió en 15 días.', { rows: 3, ayuda: 'Solo puede omitirse si hay inminente peligro de perjuicio irremediable, que debe sustentarse.' }),
        C.hechos('Ej.: Desde marzo la quebrada recibe vertimientos de la empresa X…'),
        C.area('pretensiones', 'Lo que se pide', 'Ej.: Ordenar el cierre de los vertimientos, la recuperación de la quebrada y medidas cautelares inmediatas.', { req: true }),
        C.pruebas('Ej.: Fotografías, informes técnicos, derechos de petición.'), C.notif(),
      ] },
    ],
    guia: `Fundamento: artículo 88 de la Constitución; Ley 472 de 1998: art. 4 (derechos e intereses colectivos), art. 9 (procedencia), art. 18 (requisitos de la demanda: derecho o interés colectivo, hechos, pretensiones, responsable, pruebas, direcciones y datos del actor), art. 25 (medidas cautelares), arts. 15 y 16 (jurisdicción y competencia); artículo 144 del CPACA (requisito previo: solicitar a la autoridad o al particular que adopte las medidas; si no atiende en 15 días o se niega, se puede demandar; excepcionalmente se omite ante perjuicio irremediable inminente, que debe sustentarse). El incentivo económico fue derogado por la Ley 1425 de 2010: no lo pidas.
Estructura: destinatario; referencia (Acción popular; actor; demandado); presentación; DERECHOS E INTERESES COLECTIVOS AMENAZADOS O VULNERADOS; HECHOS; REQUISITO DE PROCEDIBILIDAD; FUNDAMENTOS; PRETENSIONES (órdenes de hacer o no hacer); MEDIDAS CAUTELARES si se piden; PRUEBAS; NOTIFICACIONES.`,
  },
  {
    id: 'peticion', nombre: 'Derecho de petición', area: 'Peticiones y actuaciones administrativas', norma: 'Art. 23 C.P. · Ley 1755/2015', rolFirma: 'del peticionario', rolCliente: 'el peticionario', juris: 'ninguna',
    desc: 'Solicitud respetuosa a una entidad pública o a un particular.',
    grupos: [
      { n: 'Destinatario', campos: [C.dest('Administradora Colombiana de Pensiones, Colpensiones', DESP.entidad, 'Entidad o empresa destinataria', 'Incluye la dependencia si la conoces.'), C.texto('dir_destinatario', 'Dirección o correo de radicación', 'Ej.: notificacionesjudiciales@entidad.gov.co'), C.ciudad()] },
      { n: 'Peticionario', campos: [C.parte('cliente', 'Peticionario(a)', PH_PERSONA)] },
      { n: 'La petición', campos: [
        C.select('modalidad', 'Modalidad', [['particular', 'Interés particular · 15 días'], ['documentos', 'Información o copias · 10 días'], ['consulta', 'Consulta · 30 días'], ['general', 'Interés general · 15 días'], ['privado', 'Ante una empresa privada · 15 días']], { def: 'particular' }),
        C.hechos('Ej.: Radiqué la solicitud de pensión de vejez el 3/03/2026 con el número…', { req: false, l: 'Contexto y hechos' }),
        C.area('pretensiones', 'Lo que se solicita', 'Ej.: Que se informe el estado de la solicitud y se expida copia del expediente administrativo.', { req: true, rows: 4 }),
        { k: 'anexos', l: 'Anexos', t: 'area', rows: 2, ph: 'Ej.: Cédula; constancia de radicación.' }, C.notif('Dirección física y correo donde recibirás la respuesta.'),
      ] },
    ],
    guia: `Fundamento: artículo 23 de la Constitución; Ley 1437 de 2011 (CPACA), arts. 13 y siguientes, sustituidos por la Ley 1755 de 2015. Términos (art. 14): 15 días hábiles por regla general; 10 días para documentos e información; 30 días para consultas. Ante organizaciones privadas: arts. 32 y 33 del CPACA (sustituidos por la Ley 1755 de 2015). Si es pertinente, recuerda que la respuesta debe ser oportuna, de fondo, clara, precisa y congruente con lo pedido.
Estructura: lugar y fecha; destinatario (Señores, entidad, dependencia, dirección o correo); ASUNTO o referencia (Derecho de petición en interés particular, general, de información o de consulta); presentación del peticionario con fundamento en el art. 23 C.P.; HECHOS si los hay; PETICIONES (numeradas, claras y precisas, cada una independiente); FUNDAMENTOS DE DERECHO (breves); ANEXOS; NOTIFICACIONES (dirección física y correo para la respuesta). No uses “E. S. D.”: no es un despacho judicial. Tono respetuoso y firme.`,
    ejemplo: {
      destinatario: 'Fondo de Pensiones Ejemplo S.A., Dirección de Prestaciones Económicas', dir_destinatario: 'servicioalcliente@pensionesejemplo.com', ciudad: 'Bogotá D.C.',
      cliente: 'Jorge Iván Restrepo Gómez, C.C. 79.456.123 de Bogotá, domiciliado en Bogotá, Carrera 30 # 45-10, jorge.restrepo@correo.com, 311 555 0202.',
      modalidad: 'particular',
      hechos: 'radicó solicitud de pensión de vejez el 3/03/2026 (radicado 2026-PV-00123). Han pasado más de 7 meses sin respuesta de fondo. Llamó a la línea dos veces y le dijeron que está en estudio.',
      pretensiones: '1) que resuelvan de fondo la solicitud de pensión; 2) que le informen en qué etapa está y qué documentos faltan, si falta alguno; 3) copia completa del expediente administrativo.',
      anexos: 'Cédula; constancia de radicación del 3/03/2026.',
      notificaciones: 'Carrera 30 # 45-10, Bogotá; jorge.restrepo@correo.com',
    },
  },
  {
    id: 'recurso_admin', nombre: 'Recursos en vía administrativa', area: 'Peticiones y actuaciones administrativas', norma: 'Arts. 74 a 82 CPACA', rolFirma: 'de la parte recurrente', rolCliente: 'el recurrente',
    desc: 'Reposición, apelación o queja contra un acto administrativo, dentro de los 10 días siguientes a su notificación.',
    grupos: [
      { n: 'Autoridad', campos: [C.dest('Secretaría Distrital de Movilidad de Bogotá', null, 'Autoridad que expidió el acto'), C.ciudad()] },
      { n: 'Recurrente', campos: [C.parte('cliente', 'Recurrente', PH_PERSONA)] },
      { n: 'El acto', campos: [
        C.area('acto', 'Acto administrativo recurrido', 'Ej.: Resolución 4567 del 1/10/2026 de la Secretaría de Movilidad, que impuso multa por…', { rows: 3, req: true }),
        C.texto('notificacion_fecha', 'Fecha de notificación', 'Ej.: 6 de octubre de 2026', { req: true }),
        C.select('recurso', 'Recurso', [['reposicion_apelacion', 'Reposición y en subsidio apelación'], ['reposicion', 'Reposición'], ['apelacion', 'Apelación'], ['queja', 'Queja']], { def: 'reposicion_apelacion' }),
        C.area('razones', 'Motivos de inconformidad', 'Ej.: La notificación del comparendo no se hizo dentro de los 3 días hábiles; la foto no permite identificar al conductor…', { rows: 7, req: true }),
        C.area('pretensiones', 'Lo que se pide', 'Ej.: Revocar la Resolución 4567 de 2026 y archivar la actuación.', { req: true, rows: 3 }),
        C.pruebas('Pruebas que aportas o pides que se practiquen.'), C.notif('Tu dirección y el correo donde quieres ser notificado.'),
      ] },
    ],
    guia: `Fundamento: artículos 74 a 82 de la Ley 1437 de 2011 (CPACA). Oportunidad (art. 76): por escrito dentro de los 10 días siguientes a la notificación personal o por aviso, o al vencimiento del término de publicación. Requisitos (art. 77): presentarse dentro del plazo por el interesado o su representante o apoderado; sustentarse con expresión concreta de los motivos de inconformidad; solicitar y aportar las pruebas; indicar nombre y dirección del recurrente y el correo si desea ser notificado por ese medio. La apelación puede interponerse directamente o como subsidiaria de la reposición; la queja procede cuando se rechace la apelación.
Estructura: destinatario; referencia (Recurso de … contra la Resolución No. … del …); identificación del recurrente; OPORTUNIDAD; ANTECEDENTES; MOTIVOS DE INCONFORMIDAD (cargo por cargo); PRUEBAS; PETICIÓN (revocar, modificar o aclarar y, en subsidio, conceder la apelación ante el superior); NOTIFICACIONES.`,
  },
  {
    id: 'revocatoria', nombre: 'Revocatoria directa', area: 'Peticiones y actuaciones administrativas', norma: 'Arts. 93 a 97 CPACA', rolFirma: 'del solicitante', rolCliente: 'el solicitante',
    desc: 'Solicitud para que la administración revoque su propio acto.',
    grupos: [
      { n: 'Autoridad', campos: [C.dest('Alcaldía de Medellín, Secretaría de Hacienda', null, 'Autoridad que expidió el acto'), C.ciudad()] },
      { n: 'Solicitante', campos: [C.parte('cliente', 'Solicitante', PH_PERSONA)] },
      { n: 'El acto', campos: [
        C.area('acto', 'Acto cuya revocatoria se pide', 'Ej.: Resolución 890 del 12/05/2026, que liquidó el impuesto predial…', { rows: 3, req: true }),
        C.select('causal', 'Causal (art. 93 CPACA)', [['1', 'Es manifiestamente contrario a la Constitución o a la ley'], ['2', 'No está conforme con el interés público o social, o atenta contra él'], ['3', 'Causa un agravio injustificado a una persona']], { def: '1' }),
        C.area('razones', 'Razones', 'Ej.: El acto aplicó una tarifa que no corresponde al uso del predio…', { rows: 6, req: true }),
        C.area('pretensiones', 'Lo que se pide', 'Ej.: Revocar la Resolución 890 de 2026 y expedir una nueva liquidación.', { rows: 3, req: true }),
        C.pruebas(''), C.notif(),
      ] },
    ],
    guia: `Fundamento: artículos 93 a 97 del CPACA. Causales del art. 93 (1: oposición manifiesta a la Constitución o a la ley; 2: no conformidad con el interés público o social; 3: agravio injustificado). Art. 94: no procede por la causal 1 cuando el peticionario interpuso los recursos procedentes, ni respecto de actos sobre los que haya operado la caducidad del medio de control. Art. 95: puede pedirse aun si se acudió a la jurisdicción, siempre que no se haya notificado el auto admisorio. Art. 96: la solicitud y su decisión no reviven términos para demandar. Art. 97: la revocatoria de actos particulares y concretos requiere el consentimiento previo, expreso y escrito del titular.
Estructura: destinatario; referencia (Solicitud de revocatoria directa de la Resolución …); identificación; HECHOS; CAUSAL INVOCADA Y FUNDAMENTOS; PROCEDENCIA (no se interpusieron recursos, si aplica la causal 1); PRUEBAS; PETICIÓN; NOTIFICACIONES.`,
  },
  {
    id: 'queja_disciplinaria', nombre: 'Queja disciplinaria', area: 'Peticiones y actuaciones administrativas', norma: 'Ley 1952/2019 · Ley 1123/2007', rolFirma: 'del quejoso', rolCliente: 'el quejoso',
    desc: 'Contra un servidor público, un funcionario judicial o un abogado.',
    grupos: [
      { n: 'Destinatario', campos: [C.select('contra', 'Contra quién', [['servidor', 'Servidor público'], ['judicial', 'Funcionario o empleado judicial'], ['abogado', 'Abogado en ejercicio']], { def: 'servidor' }), C.dest('Procuraduría General de la Nación', DESP.disciplinario, 'Autoridad disciplinaria'), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Quejoso(a)', PH_PERSONA), C.parte('contraparte', 'Disciplinable', 'Nombre, cargo y entidad (o tarjeta profesional, si es abogado), si los conoces.')] },
      { n: 'Los hechos', campos: [
        C.hechos('Circunstancias de tiempo, modo y lugar. Ej.: El 12/08/2026, en la ventanilla de la Secretaría, el funcionario X exigió…'),
        C.area('pretensiones', 'Lo que se pide', 'Si lo dejas vacío: iniciar la actuación disciplinaria que corresponda.', { rows: 2 }),
        C.pruebas('Ej.: Correos, grabaciones, testigos (nombre y correo).'), C.notif('Tu dirección y correo.'),
      ] },
    ],
    guia: `Servidores públicos: Ley 1952 de 2019 (Código General Disciplinario), modificada por la Ley 2094 de 2021; competencia de la oficina de control disciplinario interno, la personería o la Procuraduría General de la Nación. Funcionarios y empleados judiciales y abogados: Comisión Nacional y Comisiones Seccionales de Disciplina Judicial; para abogados aplica la Ley 1123 de 2007 (Código Disciplinario del Abogado).
La queja narra hechos concretos con circunstancias de tiempo, modo y lugar, identifica al disciplinable si se conoce y aporta pruebas; evita calificativos y juicios no soportados. Menciona las posibles faltas con prudencia (“podrían constituir”) y marca [VERIFICAR] el artículo si no tienes certeza.
Estructura: destinatario; referencia (Queja disciplinaria contra …); identificación del quejoso; IDENTIFICACIÓN DEL DISCIPLINABLE; HECHOS; POSIBLES FALTAS; PRUEBAS; SOLICITUD; NOTIFICACIONES.`,
  },
  {
    id: 'demanda_verbal', nombre: 'Demanda declarativa (verbal o verbal sumario)', area: 'Civil y comercial', norma: 'Arts. 82 y ss., 368 y 390 CGP', rolFirma: 'de la parte demandante', rolCliente: 'la parte demandante',
    desc: 'Responsabilidad civil, restitución de inmueble, resolución de contrato, pertenencia y demás procesos declarativos.',
    grupos: [
      { n: 'Despacho', campos: [C.dest('Juez Civil Municipal de Bogotá D.C. (Reparto)', DESP.civil), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Demandante', PH_PERSONA), C.parte('contraparte', 'Demandado(s)', PH_PERSONA + ' Si es empresa: NIT y representante legal. Indica cómo obtuviste su correo.')] },
      { n: 'El caso', campos: [
        C.texto('asunto', 'Pretensión principal', 'Ej.: Responsabilidad civil extracontractual por accidente de tránsito', { req: true }),
        C.hechos('Ej.: El 4/05/2026 el vehículo de placa ABC123 conducido por el demandado chocó…'),
        C.area('pretensiones', 'Pretensiones', 'Ej.: Declarar responsable al demandado y condenarlo a pagar daño emergente de $8.500.000 y lucro cesante de $3.000.000.', { req: true }),
        C.texto('cuantia', 'Valor estimado de las pretensiones', 'Ej.: $11.500.000'),
        C.area('juramento_estimatorio', 'Juramento estimatorio (art. 206 CGP)', 'Concepto por concepto, con su valor. Ej.: Reparación del vehículo $8.500.000 (factura); ingresos dejados de percibir $3.000.000.', { rows: 3 }),
        C.select('conciliacion', 'Conciliación previa', [['agotada', 'Se agotó: adjunto constancia de no acuerdo'], ['cautelares', 'No se exige: pido medidas cautelares'], ['no_exige', 'No se exige por el tipo de asunto'], ['nose', 'No sé / revísalo tú']], { def: 'agotada' }),
        C.area('medidas', 'Medidas cautelares (opcional)', 'Ej.: Inscripción de la demanda en el folio de matrícula 50C-123456.', { rows: 2 }),
      ] },
      { n: 'Pruebas y notificaciones', campos: [C.pruebas('Documentales; testigos (nombre, correo y qué hechos declaran); dictamen pericial; interrogatorio de parte.'), C.notif()] },
    ],
    guia: `Requisitos de la demanda: art. 82 del CGP (designación del juez; nombre, domicilio e identificación de las partes y sus representantes; lo que se pretenda, expresado con precisión y claridad; hechos determinados, clasificados y numerados; pruebas; juramento estimatorio cuando sea necesario; fundamentos de derecho; cuantía cuando se requiera para la competencia o el trámite; dirección física y electrónica de notificaciones), arts. 83 (requisitos adicionales), 84 (anexos), 88 (acumulación de pretensiones), 206 (juramento estimatorio, discriminando cada concepto) y 212 (en la petición de testimonios se indica nombre, domicilio o lugar de citación de cada testigo y se enuncian concretamente los hechos objeto de la prueba). Ley 2213 de 2022: art. 6 (indicar el canal digital de partes, testigos y peritos; enviar simultáneamente por medio electrónico copia de la demanda y anexos al demandado, salvo cuando se pidan medidas cautelares previas o se desconozca su dirección) y art. 8 (afirmación bajo juramento de que la dirección electrónica del demandado es la que utiliza, cómo se obtuvo y evidencias). Conciliación extrajudicial como requisito de procedibilidad en asuntos conciliables (Ley 2220 de 2022), salvo cuando se pidan medidas cautelares. Cuantía (art. 25 CGP): mínima hasta 40 smmlv, menor de más de 40 y hasta 150 smmlv, mayor de más de 150 smmlv; los de mínima cuantía se tramitan como verbal sumario en única instancia (arts. 17 y 390).
Estructura: destinatario; referencia (Proceso verbal o verbal sumario de …; demandante; demandado); presentación (apoderado y poder); PARTES; PRETENSIONES (principales y, si hay, subsidiarias, numeradas); HECHOS; FUNDAMENTOS DE DERECHO; JURAMENTO ESTIMATORIO si se reclaman perjuicios, frutos o mejoras; CUANTÍA Y COMPETENCIA; PROCEDIMIENTO; REQUISITO DE PROCEDIBILIDAD; MEDIDAS CAUTELARES si se piden; PRUEBAS (documentales; testimoniales con el objeto de cada testimonio y su canal digital; interrogatorio; dictamen); ANEXOS; NOTIFICACIONES (con la manifestación bajo juramento del art. 8 de la Ley 2213 de 2022). Si el abogado indicó que la conciliación se agotó, anuncia la constancia en anexos; si se piden medidas cautelares, no anuncies el envío simultáneo de la demanda.`,
  },
  {
    id: 'demanda_ejecutiva', nombre: 'Demanda ejecutiva', area: 'Civil y comercial', norma: 'Arts. 422 y ss. CGP', rolFirma: 'de la parte ejecutante', rolCliente: 'la parte ejecutante',
    desc: 'Cobro judicial de una obligación clara, expresa y exigible: pagarés, letras, facturas, contratos, actas.',
    grupos: [
      { n: 'Despacho', campos: [C.dest('Juez Civil Municipal de Bogotá D.C. (Reparto)', DESP.civil), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Ejecutante (acreedor)', PH_PERSONA), C.parte('contraparte', 'Ejecutado(s) (deudor)', PH_PERSONA)] },
      { n: 'La obligación', campos: [
        C.area('titulo', 'Título ejecutivo', 'Ej.: Pagaré No. 001 suscrito el 10/01/2026 por $20.000.000, con vencimiento el 10/07/2026.', { rows: 3, req: true }),
        C.area('valores', 'Valores adeudados', 'Ej.: Capital $20.000.000; intereses de plazo al 1,5 % mensual hasta el 10/07/2026; moratorios desde el 11/07/2026.', { rows: 3, req: true }),
        C.hechos('Ej.: El deudor no pagó en la fecha de vencimiento; se le requirió el 1/08/2026…', { req: false }),
        C.area('pretensiones', 'Pretensiones (opcional)', 'Si lo dejas vacío: mandamiento de pago por capital, intereses de plazo y moratorios a la tasa máxima legal, y costas.', { rows: 3 }),
        C.area('medidas', 'Medidas cautelares', 'Ej.: Embargo y secuestro del inmueble con matrícula 50N-998877; embargo de las cuentas del deudor en el Banco X.', { rows: 3 }),
      ] },
      { n: 'Pruebas y notificaciones', campos: [C.pruebas('Ej.: Pagaré original (o certificado de depósito si es desmaterializado); certificado de tradición.'), C.notif()] },
    ],
    guia: `Fundamento: CGP arts. 422 (título ejecutivo: obligación clara, expresa y exigible, que conste en documento que provenga del deudor y constituya plena prueba contra él), 424 (sumas de dinero), 430 y 431 (mandamiento de pago), 599 (embargo y secuestro); Código de Comercio arts. 619 y siguientes (títulos valores), 671 y siguientes (letra de cambio), 709 y siguientes (pagaré); art. 884 del Código de Comercio (intereses moratorios: una y media veces el interés bancario corriente certificado por la Superintendencia Financiera, sin exceder la tasa de usura).
Estructura: destinatario; referencia (Proceso ejecutivo singular de mínima, menor o mayor cuantía; ejecutante; ejecutado); presentación; HECHOS (creación del título, vencimiento, incumplimiento, saldo); PRETENSIONES (librar mandamiento de pago por el capital, los intereses de plazo y los moratorios desde la exigibilidad hasta el pago total, y condenar en costas); FUNDAMENTOS DE DERECHO; CUANTÍA Y COMPETENCIA; PRUEBAS (el título ejecutivo); MEDIDAS CAUTELARES (si el abogado las indica, inclúyelas en un capítulo propio o como solicitud separada al final); ANEXOS; NOTIFICACIONES. Con medidas cautelares previas no se envía copia de la demanda al demandado (art. 6 de la Ley 2213 de 2022). Si el título es desmaterializado o una factura electrónica, menciona el certificado o registro correspondiente con [VERIFICAR].`,
  },
  {
    id: 'contestacion', nombre: 'Contestación de demanda', area: 'Civil y comercial', norma: 'Art. 96 CGP · Ley 2452/2025', rolFirma: 'de la parte demandada', rolCliente: 'la parte demandada',
    desc: 'Pronunciamiento sobre hechos y pretensiones, excepciones y pruebas. Sirve para procesos civiles, laborales y administrativos.',
    grupos: [
      { n: 'Proceso', campos: [C.select('jurisdiccion', 'Jurisdicción', JURIS_PROC.slice(0, 3), { def: 'civil' }), C.dest('Juez Doce Civil Municipal de Bogotá D.C.', DESP.civil, 'Juez que conoce del proceso'), C.radicado(true), C.texto('proceso', 'Clase de proceso', 'Ej.: Verbal de responsabilidad civil contractual'), C.texto('notificacion_fecha', 'Fecha de notificación del auto admisorio', 'Ej.: 1 de octubre de 2026'), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Demandado que representas', PH_PERSONA), C.parte('contraparte', 'Demandante', 'Nombre e identificación.')] },
      { n: 'Contestación', campos: [
        C.area('respuesta_hechos', 'Respuesta a cada hecho', 'Ej.:\n1. Es cierto.\n2. No es cierto: el contrato se terminó el 3/02 por mutuo acuerdo (acta).\n3. No me consta: no participé en esa reunión.', { rows: 8, req: true, ayuda: 'Usa la numeración de la demanda. Si niegas un hecho o no te consta, di por qué.' }),
        C.area('respuesta_pretensiones', 'Posición frente a las pretensiones', 'Ej.: Me opongo a todas; la segunda carece de fundamento porque…', { rows: 3, req: true }),
        C.area('excepciones', 'Excepciones', 'Ej.: Inexistencia de la obligación; pago; prescripción; cobro de lo no debido. Explica el fundamento de cada una.', { rows: 5 }),
        C.area('objecion', 'Objeción al juramento estimatorio (opcional)', 'Ej.: Los perjuicios están sobreestimados porque…', { rows: 2 }),
      ] },
      { n: 'Pruebas y notificaciones', campos: [C.pruebas('Documentales, testimonios (nombre, correo y objeto), interrogatorio, dictamen.'), C.notif('Tu dirección y el canal digital de tu cliente y el tuyo.')] },
    ],
    guia: `Civil (CGP): traslado de 20 días en el verbal (art. 369) y de 10 días en el verbal sumario (art. 391). Contenido (art. 96): nombre del demandado y domicilio, y los de su representante o apoderado; pronunciamiento expreso y concreto sobre las pretensiones y sobre cada hecho, indicando si se admite, se niega o no le consta, con las razones precisas y unívocas de la negativa o de la falta de conocimiento (si no se dan, se presume cierto el hecho); excepciones de mérito con su fundamento; pruebas; dirección física y electrónica para notificaciones. Las excepciones previas (art. 100) van en escrito separado (art. 101). La objeción al juramento estimatorio especifica razonadamente la inexactitud (art. 206).
Laboral: para procesos iniciados desde el 6 de abril de 2026 rige la Ley 2452 de 2025 (traslado de 10 días; pronunciarse sobre cada hecho dando las razones de la negativa o de por qué no le consta, so pena de tenerlo por probado; aportar los documentos y registros que el empleador deba llevar; excepciones previas en el mismo escrito; indicar correo y canal digital) [VERIFICAR artículos]; para procesos anteriores, art. 31 del Decreto-Ley 2158 de 1948.
Contencioso administrativo: traslado de 30 días (art. 172 CPACA) y contenido del art. 175 CPACA.
Estructura: destinatario; referencia (proceso, radicado, demandante, demandado); presentación y oportunidad; PRONUNCIAMIENTO SOBRE LOS HECHOS (uno por uno, con la numeración de la demanda); PRONUNCIAMIENTO SOBRE LAS PRETENSIONES; EXCEPCIONES DE MÉRITO (cada una con nombre en mayúsculas y fundamento fáctico y jurídico); OBJECIÓN AL JURAMENTO ESTIMATORIO si aplica; FUNDAMENTOS DE DERECHO; PRUEBAS; ANEXOS; NOTIFICACIONES.`,
  },
  {
    id: 'conciliacion', nombre: 'Solicitud de conciliación extrajudicial', area: 'Civil y comercial', norma: 'Ley 2220/2022', rolFirma: 'de la parte convocante', rolCliente: 'la parte convocante',
    desc: 'Ante centro de conciliación, notaría, Procuraduría o comisaría de familia.',
    grupos: [
      { n: 'Conciliador', campos: [C.select('area_conc', 'Materia', [['civil', 'Civil o comercial'], ['familia', 'Familia'], ['admin', 'Contencioso administrativa (Procuraduría)'], ['laboral', 'Laboral']], { def: 'civil' }), C.dest('Centro de Conciliación de la Cámara de Comercio de Bogotá', DESP.conciliacion, 'Centro o autoridad'), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Convocante', PH_PERSONA), C.parte('contraparte', 'Convocado(s)', PH_PERSONA + ' Incluye su correo para la citación.')] },
      { n: 'El conflicto', campos: [
        C.hechos('Ej.: El 1/02/2026 firmamos contrato de arrendamiento; el arrendatario no paga desde junio…'),
        C.area('pretensiones', 'Pretensiones', 'Ej.: Que el convocado pague los cánones adeudados ($6.000.000) y restituya el inmueble.', { req: true }),
        C.texto('cuantia', 'Cuantía', 'Ej.: $6.000.000'),
        C.area('admin_detalle', 'Solo si es contencioso: medio de control, acto o hecho y fecha', 'Ej.: Nulidad y restablecimiento contra la Resolución 12 del 3/08/2026, notificada el 5/08/2026.', { rows: 2 }),
        C.pruebas(''), C.notif(),
      ] },
    ],
    guia: `Fundamento: Ley 2220 de 2022 (Estatuto de Conciliación), vigente desde el 30 de diciembre de 2022. La solicitud incluye: identificación de las partes y sus representantes con dirección física y electrónica; hechos; pretensiones; cuantía; relación de pruebas y anexos; y la manifestación de no haber presentado demanda ni otra solicitud de conciliación sobre los mismos aspectos [VERIFICAR artículo]. En lo contencioso administrativo se presenta ante la Procuraduría y debe precisar el medio de control que se ejercería, el acto o hecho, la estimación razonada de la cuantía y la fecha de notificación del acto o de ocurrencia del hecho. En asuntos laborales la conciliación no es requisito de procedibilidad. La presentación de la solicitud suspende la prescripción o la caducidad en los términos de la ley.
Estructura: destinatario; referencia (Solicitud de conciliación extrajudicial en derecho; convocante; convocado); presentación; PARTES; HECHOS; PRETENSIONES; CUANTÍA; FUNDAMENTOS DE DERECHO (breves); PRUEBAS Y ANEXOS; MANIFESTACIONES; NOTIFICACIONES.`,
  },
  {
    id: 'divorcio', nombre: 'Divorcio o cesación de efectos civiles', area: 'Familia', norma: 'Art. 154 C.C. · Art. 388 CGP · Ley 2442/2024', rolFirma: 'de la parte demandante', rolCliente: 'la parte demandante',
    desc: 'Proceso contencioso ante juez de familia, incluido el divorcio por voluntad unilateral.',
    grupos: [
      { n: 'Despacho', campos: [C.dest('Juez de Familia de Bogotá D.C. (Reparto)', DESP.familia), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Demandante (cónyuge)', PH_PERSONA), C.parte('contraparte', 'Demandado (cónyuge)', PH_PERSONA)] },
      { n: 'El matrimonio', campos: [
        C.area('matrimonio', 'Datos del matrimonio', 'Ej.: Matrimonio religioso en la Parroquia San José de Bogotá el 12/06/2010, registrado en la Notaría 5, indicativo serial 0123456.', { rows: 3, req: true }),
        C.chips('causales', 'Causales (art. 154 C.C.)', ['Sola voluntad de cualquiera de los cónyuges', 'Relaciones sexuales extramatrimoniales', 'Incumplimiento grave de los deberes de esposo o de padre', 'Ultrajes, trato cruel y maltratamientos de obra', 'Embriaguez habitual', 'Uso habitual de sustancias alucinógenas o estupefacientes', 'Enfermedad grave e incurable', 'Conducta tendiente a corromper o pervertir', 'Separación de cuerpos de más de dos años', 'Mutuo acuerdo'], { req: true }),
        C.area('hijos', 'Hijos', 'Nombres, fechas de nacimiento y propuesta de custodia, cuota alimentaria y visitas. Ej.: Sofía (8 años): custodia de la madre; cuota de $900.000 mensuales…', { rows: 3 }),
        C.hechos('Ej.: Conviven separados desde enero de 2023; desde entonces el demandado no aporta para los gastos del hogar…'),
        C.area('pretensiones', 'Pretensiones', 'Ej.: Decretar la cesación de efectos civiles del matrimonio religioso; disolver la sociedad conyugal; fijar custodia, alimentos y visitas; inscribir la sentencia.', { req: true }),
        C.area('bienes', 'Bienes y deudas de la sociedad conyugal (opcional)', 'Ej.: Apartamento en Bogotá, matrícula 50C-112233; crédito hipotecario con el Banco X.', { rows: 2 }),
      ] },
      { n: 'Pruebas y notificaciones', campos: [C.pruebas('Registro civil de matrimonio; registros civiles de nacimiento de los hijos; testigos (nombre, correo y objeto).'), C.notif()] },
    ],
    guia: `Fundamento: art. 154 del Código Civil (causales, modificado por la Ley 25 de 1992); la Ley 2442 de 2024 agregó como causal la sola voluntad de cualquiera de los cónyuges [VERIFICAR numeral] y, cuando hay hijos menores, exige proponer la forma en que cada padre contribuirá a su crianza, educación, alimentos y custodia, y el juez revisa de oficio la obligación alimentaria. Arts. 156 (oportunidad para alegar ciertas causales) [VERIFICAR], 160 (efectos del divorcio) y 1820 (disolución de la sociedad conyugal) del Código Civil; art. 388 del CGP (proceso verbal de divorcio y cesación de efectos civiles del matrimonio religioso, art. 152 C.C.); arts. 82 y siguientes del CGP; Ley 2213 de 2022 para canal digital y notificaciones. Si se invoca la causal de mutuo acuerdo, advierte que puede tramitarse ante notario o por jurisdicción voluntaria.
Estructura: destinatario; referencia (Proceso verbal de divorcio o de cesación de efectos civiles de matrimonio religioso; demandante; demandado); presentación; HECHOS (matrimonio, hijos, bienes, hechos que configuran cada causal); PRETENSIONES (decretar el divorcio o la cesación; disolución y liquidación de la sociedad conyugal; custodia, alimentos y visitas de los hijos menores; inscripción en el registro civil; costas si aplica); FUNDAMENTOS DE DERECHO; PRUEBAS; COMPETENCIA Y PROCEDIMIENTO; ANEXOS; NOTIFICACIONES.`,
  },
  {
    id: 'alimentos', nombre: 'Fijación de cuota alimentaria', area: 'Familia', norma: 'Art. 411 C.C. · Ley 1098/2006 · Art. 397 CGP', rolFirma: 'de la parte demandante', rolCliente: 'la parte demandante',
    desc: 'Alimentos para hijos menores u otros alimentarios, con medidas para asegurar el pago.',
    grupos: [
      { n: 'Despacho', campos: [C.dest('Juez de Familia de Bogotá D.C. (Reparto)', DESP.familia), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Demandante (representante del menor)', PH_PERSONA), C.area('alimentarios', 'Alimentario(s)', 'Ej.: Tomás Pérez Gómez, 6 años, NUIP 1.012.345.678.', { rows: 2, req: true }), C.parte('contraparte', 'Demandado (alimentante)', PH_PERSONA + ' Ocupación, ingresos y empleador si los conoces.')] },
      { n: 'El caso', campos: [
        C.area('necesidades', 'Gastos mensuales del alimentario', 'Ej.: Colegio $450.000; alimentación $600.000; salud y transporte $200.000.', { rows: 3, req: true }),
        C.area('capacidad', 'Capacidad económica del demandado', 'Ej.: Trabaja como supervisor en la empresa X; gana alrededor de $4.000.000.', { rows: 2 }),
        C.hechos('Ej.: Desde marzo de 2026 el demandado dejó de aportar…'),
        C.area('pretensiones', 'Pretensiones', 'Ej.: Cuota mensual de $1.000.000, reajustada cada año con el salario mínimo; mitad de gastos de educación y salud; cuotas extra en junio y diciembre.', { req: true }),
        C.select('conciliacion', 'Conciliación previa', [['agotada', 'Se agotó: adjunto constancia'], ['cautelares', 'No se agotó: pido medidas cautelares'], ['nose', 'No sé / revísalo tú']], { def: 'agotada' }),
        C.area('medidas', 'Medidas cautelares (opcional)', 'Ej.: Embargo del 30 % del salario; impedimento de salida del país.', { rows: 2 }),
      ] },
      { n: 'Pruebas y notificaciones', campos: [C.pruebas('Registro civil de nacimiento; soportes de gastos; certificado laboral o solicitud de oficiar al empleador.'), C.notif()] },
    ],
    guia: `Fundamento: arts. 411 y siguientes del Código Civil; Código de la Infancia y la Adolescencia (Ley 1098 de 2006), arts. 24 (derecho a los alimentos), 129 (fijación, alimentos provisionales, impedimento de salida del país y reporte) y 130 (medidas para el cumplimiento, como el embargo de hasta el 50 % del salario); art. 397 del CGP (alimentos, proceso verbal sumario, alimentos provisionales); Ley 2097 de 2021 (Registro de Deudores Alimentarios Morosos, REDAM). Verifica si se agotó la conciliación previa como requisito de procedibilidad (Ley 2220 de 2022) [VERIFICAR], sin perjuicio de que se pidan medidas cautelares. Competencia: juez del domicilio del menor.
Estructura: destinatario; referencia (Proceso verbal sumario de fijación de cuota alimentaria; demandante en representación del menor; demandado); presentación; HECHOS (filiación, necesidades, capacidad del obligado, incumplimientos); PRETENSIONES (cuota mensual, reajuste anual con el incremento del salario mínimo, cuotas adicionales, gastos de educación, salud y vestuario, alimentos provisionales); FUNDAMENTOS DE DERECHO; PRUEBAS (pide oficiar al empleador, a la DIAN o a entidades financieras si no hay prueba de ingresos); MEDIDAS CAUTELARES; COMPETENCIA; ANEXOS; NOTIFICACIONES.`,
  },
  {
    id: 'laboral_demanda', nombre: 'Demanda ordinaria laboral', area: 'Laboral', norma: 'Ley 2452/2025 · CST', rolFirma: 'de la parte demandante', rolCliente: 'la parte demandante',
    desc: 'Reclamación de salarios, prestaciones, indemnizaciones o reintegro ante juez laboral.',
    grupos: [
      { n: 'Despacho', campos: [C.dest('Juez Laboral del Circuito de Bogotá D.C. (Reparto)', DESP.laboral, 'Juez', 'Laboral municipal hasta 40 smmlv; del circuito por encima de 40 smmlv o en estabilidad laboral reforzada.'), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Demandante (trabajador)', PH_PERSONA), C.parte('contraparte', 'Demandado (empleador)', 'Razón social, NIT, representante legal, dirección y correo de notificaciones judiciales.')] },
      { n: 'La relación laboral', campos: [
        C.area('relacion', 'Datos de la relación laboral', 'Ej.: Contrato a término indefinido del 1/02/2021 al 30/06/2026; cargo: auxiliar de bodega; salario $2.100.000; despido sin justa causa por carta del 30/06/2026.', { rows: 4, req: true }),
        C.hechos('Ej.: Trabajaba de lunes a sábado de 6 a. m. a 6 p. m.; nunca le pagaron horas extra; no le consignaron las cesantías de 2025…'),
        C.area('pretensiones', 'Pretensiones', 'Ej.: Indemnización por despido sin justa causa; horas extra; sanción por no consignación de cesantías; indemnización moratoria; indexación; costas.', { req: true }),
        C.texto('cuantia', 'Cuantía estimada', 'Ej.: $48.000.000'),
        C.area('reclamacion', 'Reclamación previa (si el empleador es entidad pública)', 'Ej.: Reclamación radicada el 15/07/2026, sin respuesta.', { rows: 2 }),
      ] },
      { n: 'Pruebas y notificaciones', campos: [C.pruebas('Contrato, desprendibles de pago, carta de despido; testigos (nombre, correo y objeto); documentos en poder del empleador que pides exhibir.'), C.notif()] },
    ],
    guia: `Régimen procesal: Ley 2452 de 2025 (nuevo Código Procesal del Trabajo y de la Seguridad Social), aplicable a los procesos iniciados desde el 6 de abril de 2026; los anteriores siguen con el Decreto-Ley 2158 de 1948. No cites números de artículo de la Ley 2452 de 2025 salvo que el abogado los dé; si los mencionas, márcalos [VERIFICAR].
Requisitos de la demanda según la Ley 2452 de 2025: se presenta como mensaje de datos con sus anexos; nombre de las partes y de sus representantes; identificación (cédula; NIT para personas jurídicas); domicilio, dirección física y correo o canal digital de partes, apoderados, testigos y peritos (si se desconoce, se manifiesta bajo juramento); pretensiones precisas y separadas; hechos numerados; fundamentos de derecho; pruebas (aportar las que se tengan y señalar las que estén en poder del demandado); cuantía cuando defina la competencia (jueces laborales municipales hasta 40 smmlv; jueces del circuito por encima de 40 smmlv; estabilidad laboral reforzada: circuito). Anexos: copia del documento de identidad del demandante y pruebas. No se exige enviar copia simultánea de la demanda al demandado y la conciliación no es requisito de procedibilidad. Si el demandado es una entidad pública, indica si se agotó la reclamación de derechos.
Derecho sustancial: Código Sustantivo del Trabajo con las modificaciones de la Ley 2466 de 2025; aplica la norma vigente en la fecha de los hechos y marca [VERIFICAR] cuando un cálculo dependa de la reforma (jornada, recargos, dominicales). Referencias usuales: art. 64 CST (despido sin justa causa), art. 65 CST (indemnización moratoria), art. 99 de la Ley 50 de 1990 (no consignación de cesantías), Ley 52 de 1975 (intereses a las cesantías), arts. 249 y siguientes (cesantías), 306 (prima de servicios) y 186 y siguientes (vacaciones) del CST.
Estructura: destinatario; referencia (Demanda ordinaria laboral de primera instancia; demandante; demandado); presentación y poder; PARTES; HECHOS; PRETENSIONES (declarativas y de condena separadas, con indexación y costas); FUNDAMENTOS DE DERECHO; PRUEBAS (documentales, testimoniales con canal digital, interrogatorio de parte, exhibición de documentos en poder del demandado, inspección judicial); CUANTÍA Y COMPETENCIA; ANEXOS; NOTIFICACIONES (con la manifestación bajo juramento sobre el canal digital).`,
  },
  {
    id: 'nulidad_restablecimiento', nombre: 'Nulidad y restablecimiento del derecho', area: 'Contencioso administrativo', norma: 'Art. 138 CPACA', rolFirma: 'de la parte demandante', rolCliente: 'la parte demandante',
    desc: 'Contra actos administrativos particulares, dentro de los 4 meses siguientes a su notificación.',
    grupos: [
      { n: 'Despacho', campos: [C.dest('Juez Administrativo del Circuito de Bogotá D.C. (Reparto)', DESP.admin), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Demandante', PH_PERSONA), C.parte('contraparte', 'Entidad demandada', 'Entidad, representante legal y correo de notificaciones judiciales.')] },
      { n: 'Los actos', campos: [
        C.area('acto', 'Actos demandados', 'Ej.: Resolución 2345 del 3/06/2026 de la UGPP y Resolución 3456 del 1/08/2026 que resolvió la apelación.', { rows: 3, req: true }),
        C.texto('notificacion_fecha', 'Fecha de notificación del último acto', 'Ej.: 5 de agosto de 2026', { req: true, ayuda: 'Para la caducidad de 4 meses. Las prestaciones periódicas pueden demandarse en cualquier tiempo.' }),
        C.area('normas_violadas', 'Normas violadas y concepto de la violación', 'Ej.: Falsa motivación: el acto afirma que no cotizó 1.300 semanas, pero la historia laboral muestra 1.350…', { rows: 6, req: true }),
        C.hechos('Ej.: El demandante solicitó la reliquidación el…'),
        C.area('pretensiones', 'Pretensiones', 'Ej.: Declarar la nulidad de las resoluciones; a título de restablecimiento, ordenar reliquidar la pensión y pagar las diferencias indexadas.', { req: true }),
        C.texto('cuantia', 'Estimación razonada de la cuantía', 'Ej.: $36.000.000 (diferencias de 36 meses × $1.000.000)'),
        C.select('conciliacion', 'Conciliación prejudicial', [['agotada', 'Se agotó ante la Procuraduría (adjunto constancia)'], ['no_exige', 'No se exige (asunto pensional o laboral, u otro)'], ['cautelares', 'Pido medidas cautelares previas'], ['nose', 'No sé / revísalo tú']], { def: 'agotada' }),
        C.area('medidas', 'Medida cautelar (opcional)', 'Ej.: Suspensión provisional de la Resolución 2345 de 2026.', { rows: 2 }),
      ] },
      { n: 'Pruebas y notificaciones', campos: [C.pruebas('Copia de los actos con constancia de notificación; expediente administrativo; historia laboral.'), C.notif()] },
    ],
    guia: `Fundamento: Ley 1437 de 2011 (CPACA), modificada por la Ley 2080 de 2021: arts. 137 (causales: infracción de las normas en que debía fundarse, falta de competencia, expedición irregular, desconocimiento del derecho de audiencia y defensa, falsa motivación y desviación de las atribuciones de quien lo profirió), 138 (nulidad y restablecimiento del derecho), 161 (requisitos previos: conciliación extrajudicial cuando el asunto sea conciliable y ejercicio de los recursos obligatorios), 162 (contenido de la demanda: partes y representantes; pretensiones precisas y claras; hechos y omisiones determinados, clasificados y numerados; fundamentos de derecho y, contra actos administrativos, las normas violadas y el concepto de su violación; pruebas; estimación razonada de la cuantía; lugar y dirección de notificaciones con canal digital; y, según el numeral 8 adicionado por la Ley 2080 de 2021, envío simultáneo por medio electrónico de la demanda y anexos a los demandados, salvo cuando se pidan medidas cautelares previas o se desconozca su dirección), 163 (individualizar los actos; si hubo recursos, se demandan también los actos que los resolvieron), 164 num. 2 lit. d (caducidad de 4 meses desde el día siguiente a la comunicación, notificación, ejecución o publicación; las prestaciones periódicas pueden demandarse en cualquier tiempo, num. 1 lit. c), 166 (anexos: copia del acto con sus constancias de publicación, comunicación, notificación o ejecución), 187 (ajuste de las condenas con el IPC), 192 (cumplimiento de sentencias) y 229 y siguientes (medidas cautelares; suspensión provisional, art. 231). Competencia: arts. 152, 155, 156 y 157 del CPACA [VERIFICAR cuantías]. Conciliación ante la Procuraduría: Ley 2220 de 2022.
Estructura: destinatario; referencia (Medio de control de nulidad y restablecimiento del derecho; demandante; demandado); presentación; PARTES Y REPRESENTANTES; PRETENSIONES; HECHOS Y OMISIONES; NORMAS VIOLADAS Y CONCEPTO DE LA VIOLACIÓN (por cargos); ESTIMACIÓN RAZONADA DE LA CUANTÍA; COMPETENCIA; OPORTUNIDAD (caducidad); REQUISITO DE PROCEDIBILIDAD; MEDIDA CAUTELAR si se pide (capítulo aparte); PRUEBAS; ANEXOS; NOTIFICACIONES (con canal digital).`,
  },
  {
    id: 'reparacion_directa', nombre: 'Reparación directa', area: 'Contencioso administrativo', norma: 'Art. 90 C.P. · Art. 140 CPACA', rolFirma: 'de la parte demandante', rolCliente: 'la parte demandante',
    desc: 'Daño antijurídico causado por una acción u omisión del Estado, dentro de los 2 años siguientes.',
    grupos: [
      { n: 'Despacho', campos: [C.dest('Juez Administrativo del Circuito de Medellín (Reparto)', DESP.admin), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Demandantes', 'Víctima directa y familiares, con su parentesco e identificación. Ej.: Pedro Gómez (víctima); Ana Ruiz (esposa)…'), C.parte('contraparte', 'Entidades demandadas', 'Ej.: Nación, Ministerio de Defensa, Policía Nacional; Municipio de Medellín.')] },
      { n: 'El daño', campos: [
        C.area('hecho_danoso', 'Hecho, omisión u operación administrativa', 'Ej.: El 14/03/2025 cayó en una excavación de la empresa de acueducto sin señalizar, en la Carrera 50 con Calle 10.', { rows: 3, req: true }),
        C.hechos('Ej.: Fue llevado al hospital…; sufrió fractura de tibia…; estuvo incapacitado 120 días…'),
        C.area('perjuicios', 'Perjuicios por demandante', 'Ej.: Pedro: daño emergente $5.000.000, lucro cesante $9.000.000, morales 50 smmlv, daño a la salud 30 smmlv. Ana: morales 50 smmlv.', { rows: 4, req: true }),
        C.area('pretensiones', 'Pretensiones (opcional)', 'Si lo dejas vacío: declarar la responsabilidad y condenar al pago de los perjuicios indicados.', { rows: 2 }),
        C.texto('cuantia', 'Estimación razonada de la cuantía', 'Ej.: Pretensión mayor: $14.000.000 de perjuicios materiales'),
        C.select('conciliacion', 'Conciliación prejudicial', [['agotada', 'Se agotó ante la Procuraduría (adjunto constancia)'], ['nose', 'No sé / revísalo tú']], { def: 'agotada' }),
      ] },
      { n: 'Pruebas y notificaciones', campos: [C.pruebas('Historia clínica, informes, registros civiles para el parentesco, testigos, dictamen de pérdida de capacidad laboral.'), C.notif()] },
    ],
    guia: `Fundamento: art. 90 de la Constitución (responsabilidad patrimonial del Estado por el daño antijurídico que le sea imputable); art. 140 del CPACA (reparación directa); art. 164 num. 2 lit. i (caducidad: 2 años desde el día siguiente al de la acción u omisión causante del daño, o desde que el demandante tuvo o debió tener conocimiento, si fue posterior y prueba la imposibilidad de conocerlo antes); arts. 161 y 162 del CPACA (requisitos; conciliación prejudicial); Ley 2220 de 2022. Títulos de imputación desarrollados por el Consejo de Estado: falla del servicio, daño especial y riesgo excepcional. Los topes de perjuicios inmateriales (morales y daño a la salud) los unificó la Sección Tercera del Consejo de Estado en 2014 [VERIFICAR]; exprésalos en salarios mínimos.
Estructura: destinatario; referencia (Medio de control de reparación directa; demandantes; demandados); presentación; PARTES (cada demandante con su calidad: víctima directa, cónyuge, hijo, padre, hermano); PRETENSIONES (declarar administrativa y patrimonialmente responsables a las entidades; condenar por cada demandante y cada perjuicio: materiales en pesos e inmateriales en smmlv); HECHOS; FUNDAMENTOS DE LA RESPONSABILIDAD (daño antijurídico, imputación y título de imputación); ESTIMACIÓN RAZONADA DE LA CUANTÍA; OPORTUNIDAD (caducidad); REQUISITO DE PROCEDIBILIDAD; PRUEBAS; ANEXOS; NOTIFICACIONES.`,
  },
  {
    id: 'denuncia', nombre: 'Denuncia penal o querella', area: 'Penal', norma: 'Arts. 66 a 74 Ley 906/2004', rolFirma: 'de la víctima', rolCliente: 'el denunciante',
    desc: 'Puesta en conocimiento de un posible delito ante la Fiscalía General de la Nación.',
    grupos: [
      { n: 'Destinatario', campos: [C.select('clase', 'Clase', [['denuncia', 'Denuncia'], ['querella', 'Querella (delito querellable)']], { def: 'denuncia' }), C.dest('Fiscalía General de la Nación, Fiscal Seccional (Reparto)', DESP.penal, 'Destinatario'), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Denunciante o víctima', PH_PERSONA), C.parte('contraparte', 'Denunciado(s)', 'Nombre, identificación y ubicación si se conocen. Si no, escribe “en averiguación de responsables”.', false)] },
      { n: 'Los hechos', campos: [
        C.hechos('Circunstancias de tiempo, modo y lugar. Ej.: El 2/10/2026 recibí una llamada de alguien que dijo ser del banco…'),
        C.texto('delito', 'Posible(s) delito(s) (opcional)', 'Ej.: Estafa; hurto por medios informáticos'),
        C.area('danos', 'Perjuicios sufridos (opcional)', 'Ej.: Transferencias por $7.800.000 desde mi cuenta de ahorros.', { rows: 2 }),
        C.area('pretensiones', 'Solicitudes', 'Si lo dejas vacío: investigar, reconocer la calidad de víctima y adoptar medidas de protección si proceden.', { rows: 2 }),
        C.pruebas('Ej.: Extractos bancarios, capturas de chats, números telefónicos, testigos.'), C.notif('Tu dirección, correo y teléfono.'),
      ] },
    ],
    guia: `Fundamento: Ley 906 de 2004: arts. 66 (titularidad de la acción penal), 67 (deber de denunciar), 69 (requisitos: verbalmente, por escrito o por medio técnico que permita identificar al autor, con relación detallada de los hechos; manifestar si los mismos hechos ya se pusieron en conocimiento de otro funcionario; advertencia sobre la responsabilidad penal por falsa denuncia), 70 a 74 (querella; caducidad de 6 meses, art. 73; delitos querellables, art. 74), y 11 y 132 y siguientes (derechos de las víctimas). Para delitos querellables del procedimiento abreviado aplica la Ley 1826 de 2017. Adecuación típica con el Código Penal (Ley 599 de 2000): menciona los tipos penales con prudencia (“podrían configurar”) y marca [VERIFICAR] el artículo.
Estructura: destinatario; referencia (Denuncia penal o Querella; denunciante; denunciado o “en averiguación de responsables”); presentación; HECHOS (cronológicos, con tiempo, modo y lugar); POSIBLE CALIFICACIÓN JURÍDICA; PERJUICIOS si los hay; ELEMENTOS MATERIALES PROBATORIOS (enumerados y descritos); JURAMENTO (bajo la gravedad del juramento, que los hechos son ciertos y que no se ha presentado otra denuncia por los mismos hechos ante otra autoridad); SOLICITUDES (reconocimiento de la calidad de víctima, medidas de protección, actos urgentes); ANEXOS; NOTIFICACIONES.`,
  },
  {
    id: 'recurso_judicial', nombre: 'Recurso de reposición o apelación (autos)', area: 'Procesos en curso', norma: 'Arts. 318 y 320 a 322 CGP', rolFirma: 'de la parte recurrente', rolCliente: 'la parte que represento',
    desc: 'Contra autos judiciales, dentro de los 3 días siguientes a su notificación por estado.',
    grupos: [
      { n: 'Proceso', campos: [C.select('jurisdiccion', 'Jurisdicción', JURIS_PROC, { def: 'civil' }), C.dest('Juez Doce Civil Municipal de Bogotá D.C.', DESP.civil, 'Juez que dictó la providencia'), C.radicado(true), C.texto('proceso', 'Clase de proceso', 'Ej.: Ejecutivo singular de menor cuantía'), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Parte que recurre', 'Nombre y calidad (demandante, demandado…).'), C.parte('contraparte', 'Contraparte', 'Nombre y calidad.', false)] },
      { n: 'La providencia', campos: [
        C.area('providencia', 'Providencia recurrida', 'Ej.: Auto del 9/10/2026 que rechazó la demanda por no aportar el certificado de existencia.', { rows: 3, req: true }),
        C.texto('notificacion_fecha', 'Fecha de notificación', 'Ej.: Estado del 10 de octubre de 2026', { req: true }),
        C.select('recurso', 'Recurso', [['reposicion_apelacion', 'Reposición y en subsidio apelación'], ['reposicion', 'Reposición'], ['apelacion', 'Apelación'], ['queja', 'Reposición y en subsidio queja (contra el auto que negó la apelación)'], ['suplica', 'Súplica']], { def: 'reposicion_apelacion' }),
        C.area('razones', 'Razones del recurso', 'Ej.: El certificado sí se aportó como anexo 4 del correo de radicación…', { rows: 7, req: true }),
        C.area('pretensiones', 'Lo que se pide', 'Ej.: Revocar el auto y, en su lugar, admitir la demanda.', { rows: 2, req: true }),
      ] },
    ],
    guia: `CGP: reposición (art. 318: procede contra los autos que dicte el juez, salvo norma en contrario; si el auto se dicta fuera de audiencia, se interpone por escrito dentro de los 3 días siguientes a su notificación, con expresión de las razones que lo sustenten; en audiencia, verbalmente y de inmediato); apelación de autos (art. 321: autos apelables y los demás señalados expresamente en el CGP; art. 322: puede interponerse directamente o en subsidio de la reposición, dentro de los 3 días siguientes a la notificación, y el apelante debe sustentarlo ante el juez que dictó la providencia dentro de ese término o de los 3 días siguientes a la notificación del auto que niega la reposición); queja (arts. 352 y 353: en subsidio de la reposición contra el auto que negó la apelación o la casación); súplica (art. 331).
Laboral: para procesos iniciados desde el 6 de abril de 2026, Ley 2452 de 2025 (reposición de autos dictados fuera de audiencia y queja: 3 días; autos apelables en el art. 228) [VERIFICAR]. Contencioso administrativo: arts. 242 a 247 del CPACA, modificados por la Ley 2080 de 2021. Penal: arts. 176 a 179 de la Ley 906 de 2004.
Estructura: destinatario; referencia (proceso, radicado, partes); identificación de quien recurre y oportunidad; PROVIDENCIA RECURRIDA (fecha y decisión); FUNDAMENTOS DEL RECURSO (razones, cargo por cargo, con las normas aplicables); SOLICITUD (revocar o modificar y, en subsidio, conceder la apelación o expedir las copias para la queja); si hay apelación, sus reparos concretos.`,
  },
  {
    id: 'apelacion_sentencia', nombre: 'Apelación de sentencia', area: 'Procesos en curso', norma: 'Art. 322 CGP · Art. 12 Ley 2213/2022', rolFirma: 'de la parte apelante', rolCliente: 'la parte apelante',
    desc: 'Reparos concretos ante el juez de primera instancia o sustentación ante el superior.',
    grupos: [
      { n: 'Proceso', campos: [C.select('jurisdiccion', 'Jurisdicción', JURIS_PROC.slice(0, 3), { def: 'civil' }), C.select('momento', 'Momento procesal', [['reparos', 'Reparos concretos ante el juez de primera instancia'], ['sustentacion', 'Sustentación ante el superior (segunda instancia)']], { def: 'reparos' }), C.dest('Juez Tercero Civil del Circuito de Cali', DESP.civil, 'Despacho'), C.radicado(true), C.texto('proceso', 'Clase de proceso', 'Ej.: Verbal de responsabilidad civil'), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Parte apelante', 'Nombre y calidad.'), C.parte('contraparte', 'Contraparte', 'Nombre y calidad.', false)] },
      { n: 'La sentencia', campos: [
        C.area('sentencia', 'Sentencia apelada', 'Ej.: Sentencia del 2/10/2026 que negó las pretensiones; notificada por estado el 3/10/2026.', { rows: 3, req: true }),
        C.area('reparos', 'Reparos concretos', 'Ej.: 1) El juez no valoró el dictamen pericial; 2) aplicó mal la carga de la prueba (art. 167 CGP)…', { rows: 8, req: true }),
        C.area('pretensiones', 'Lo que se pide al superior', 'Ej.: Revocar la sentencia y, en su lugar, acceder a las pretensiones.', { rows: 2, req: true }),
      ] },
    ],
    guia: `CGP art. 322: la apelación contra la sentencia se interpone en la audiencia en que se dicta o, si se dictó por fuera de audiencia, por escrito dentro de los 3 días siguientes a su notificación por estado; el apelante precisa, de manera breve, los reparos concretos que hace a la decisión, sobre los cuales versará la sustentación ante el superior. Ley 2213 de 2022, art. 12 (civil y familia): ejecutoriado el auto que admite la apelación, el apelante sustenta por escrito a más tardar dentro de los 5 días siguientes; si no lo hace, se declara desierto. Contencioso administrativo: art. 247 del CPACA (10 días siguientes a la notificación). Laboral: Ley 2452 de 2025 [VERIFICAR término y forma].
Si el momento procesal es “reparos”, redacta reparos concretos, breves y numerados, dirigidos al juez de primera instancia, pidiendo que se conceda el recurso. Si es “sustentación”, dirígelo al superior (Tribunal o juez del circuito) y desarrolla a fondo cada reparo.
Estructura: destinatario; referencia; oportunidad; SENTENCIA APELADA (fecha y decisión); REPAROS CONCRETOS o SUSTENTACIÓN (numerados, cada uno con título, el error del juez y la argumentación); SOLICITUD (conceder el recurso o revocar o modificar la sentencia y, en su lugar, …).`,
  },
  {
    id: 'alegatos', nombre: 'Alegatos de conclusión', area: 'Procesos en curso', norma: 'Art. 373 CGP · Art. 181 CPACA', rolFirma: 'de la parte que represento', rolCliente: 'la parte que represento',
    desc: 'Argumentación final sobre los hechos probados y el derecho aplicable.',
    grupos: [
      { n: 'Proceso', campos: [C.select('jurisdiccion', 'Jurisdicción', JURIS_PROC.slice(0, 3), { def: 'admin' }), C.dest('Juez Cuarto Administrativo del Circuito de Bogotá D.C.', DESP.admin, 'Despacho'), C.radicado(true), C.texto('proceso', 'Clase de proceso', 'Ej.: Nulidad y restablecimiento del derecho'), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Parte que represento', 'Nombre y calidad.'), C.parte('contraparte', 'Contraparte', 'Nombre y calidad.', false)] },
      { n: 'Argumentos', campos: [
        C.area('posicion', 'Tu posición y lo que se busca', 'Ej.: Que se acceda a las pretensiones: la resolución se expidió con falsa motivación.', { rows: 3, req: true }),
        C.area('hechos_probados', 'Hechos probados y con qué prueba', 'Ej.: La historia laboral (folio 45) acredita 1.350 semanas; el testigo Juan Ruiz declaró que…', { rows: 7, req: true }),
        C.area('argumentos', 'Argumentos jurídicos clave', 'Ej.: Aplica el régimen de transición porque…', { rows: 4 }),
        C.area('replica', 'Argumentos de la contraparte que debes rebatir (opcional)', 'Ej.: La entidad alega prescripción, pero…', { rows: 3 }),
        C.area('pretensiones', 'Solicitud final', 'Ej.: Declarar la nulidad y condenar en costas.', { rows: 2 }),
      ] },
    ],
    guia: `Alegatos finales. CGP: art. 373 (alegatos en la audiencia de instrucción y juzgamiento; por escrito solo cuando el juez lo permite); CPACA: art. 181 (alegatos por escrito dentro de los 10 días siguientes cuando el juez prescinde de la audiencia de alegaciones y juzgamiento); segunda instancia civil y de familia: art. 12 de la Ley 2213 de 2022.
Estructura: destinatario; referencia; oportunidad; SÍNTESIS DEL LITIGIO (pretensiones y problema jurídico); HECHOS PROBADOS (cada hecho con la prueba que lo demuestra: documento con su folio, testimonio con el nombre del testigo y lo que declaró, dictamen); VALORACIÓN PROBATORIA (sana crítica, art. 176 CGP; carga de la prueba, art. 167 CGP); ARGUMENTOS JURÍDICOS; RÉPLICA a la contraparte; SOLICITUD. Persuasivo y sobrio. Nunca inventes pruebas, folios ni declaraciones que el abogado no haya indicado.`,
  },
  {
    id: 'poder', nombre: 'Poder especial', area: 'Procesos en curso', norma: 'Arts. 74 a 77 CGP · Art. 5 Ley 2213/2022', rolFirma: '', rolCliente: 'el poderdante', juris: 'ninguna', firma: 'poder', breve: true,
    desc: 'Mandato para representar a tu cliente en un proceso o trámite.',
    grupos: [
      { n: 'Destinatario', campos: [C.dest('Juez Civil Municipal de Bogotá D.C. (Reparto)', [...DESP.civil, ...DESP.admin], 'Juez o entidad ante quien se presenta'), C.radicado(false), C.ciudad()] },
      { n: 'Poderdante', campos: [C.parte('cliente', 'Poderdante', PH_PERSONA + ' Si es empresa: NIT, representante legal y correo inscrito en el registro mercantil.')] },
      { n: 'El encargo', campos: [
        C.area('asunto', 'Para qué se otorga', 'Ej.: Iniciar y llevar hasta su terminación proceso verbal de restitución de inmueble arrendado contra Pedro Gómez, respecto del apartamento de la Calle 10 # 20-30.', { rows: 3, req: true }),
        C.parte('contraparte', 'Contra quién (si aplica)', 'Nombre e identificación.', false),
        C.chips('facultades', 'Facultades expresas', ['Recibir', 'Conciliar', 'Transigir', 'Desistir', 'Sustituir', 'Reasumir', 'Renunciar', 'Allanarse', 'Interponer recursos', 'Tachar documentos de falsos', 'Cobrar y recibir títulos judiciales', 'Presentar acción de tutela']),
      ] },
    ],
    guia: `Fundamento: arts. 73 a 77 del CGP (derecho de postulación; el poder especial puede conferirse por documento privado y los asuntos deben estar determinados y claramente identificados, art. 74; facultades del apoderado y actos que requieren autorización expresa, como recibir, allanarse o disponer del derecho en litigio, art. 77); art. 5 de la Ley 2213 de 2022 (el poder especial puede conferirse por mensaje de datos, sin firma manuscrita o digital, con la sola antefirma; se presume auténtico y no requiere presentación personal; debe indicar expresamente el correo del apoderado, que debe coincidir con el inscrito en el Registro Nacional de Abogados; los poderdantes inscritos en el registro mercantil lo remiten desde su correo de notificaciones judiciales).
Redacta en primera persona del poderdante: “[Nombre], mayor de edad, identificado(a) con …, por medio del presente escrito confiero poder especial, amplio y suficiente a [abogado], identificado(a) con …, abogado(a) en ejercicio, portador(a) de la Tarjeta Profesional No. … del Consejo Superior de la Judicatura, con correo electrónico … inscrito en el Registro Nacional de Abogados, para que …”. Luego, las facultades del art. 77 del CGP y las expresas indicadas. Breve: una página. Sin capítulos de hechos ni fundamentos.
Estructura: lugar y fecha; destinatario; referencia (Poder especial; asunto); texto del poder; facultades; bloque de firma del poderdante; “Acepto,”; firma del apoderado.`,
  },
  {
    id: 'memorial', nombre: 'Memorial o solicitud al despacho', area: 'Procesos en curso', norma: 'CGP', rolFirma: 'de la parte que represento', rolCliente: 'la parte que represento', juris: 'ninguna', breve: true,
    desc: 'Impulso procesal, copias, aplazamientos, desistimientos, renuncia o sustitución de poder y otras solicitudes.',
    grupos: [
      { n: 'Proceso', campos: [C.dest('Juez Doce Civil Municipal de Bogotá D.C.', [...DESP.civil, ...DESP.laboral, ...DESP.admin], 'Despacho'), C.radicado(true), C.texto('proceso', 'Clase de proceso', 'Ej.: Ejecutivo singular'), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Parte que represento', 'Nombre y calidad.'), C.parte('contraparte', 'Contraparte', 'Nombre y calidad.', false)] },
      { n: 'La solicitud', campos: [
        C.select('asunto_memorial', 'Asunto', [['impulso', 'Impulso procesal'], ['copias', 'Acceso al expediente o copias'], ['aplazamiento', 'Aplazamiento de audiencia'], ['medida', 'Solicitud de medida cautelar'], ['aportar', 'Aportar documentos o pruebas'], ['desistimiento', 'Desistimiento'], ['renuncia', 'Renuncia de poder (art. 76 CGP)'], ['sustitucion', 'Sustitución de poder (art. 75 CGP)'], ['pago', 'Terminación por pago (art. 461 CGP)'], ['titulos', 'Entrega de títulos judiciales'], ['aclaracion', 'Aclaración, corrección o adición de providencia'], ['otro', 'Otro']], { def: 'impulso' }),
        C.area('solicitud', 'Qué solicitas y por qué', 'Ej.: Han pasado 4 meses desde la radicación de la demanda sin auto admisorio; solicito darle trámite.', { rows: 5, req: true }),
        C.area('hechos', 'Antecedentes (opcional)', 'Fechas y actuaciones relevantes.', { rows: 3 }),
        { k: 'anexos', l: 'Anexos', t: 'area', rows: 2, ph: 'Ej.: Comunicación de la renuncia enviada al poderdante el 15/10/2026.' },
      ] },
    ],
    guia: `Escrito breve y directo al despacho que conoce del proceso. Normas según el asunto: impulso (arts. 8 y 42 num. 1 del CGP); acceso al expediente y copias (art. 114 del CGP; Ley 2213 de 2022 para el expediente digital); aplazamiento (según la audiencia, p. ej. art. 372 del CGP) [VERIFICAR]; medidas cautelares (arts. 588 y siguientes del CGP); desistimiento (arts. 314 a 316 del CGP); renuncia de poder (art. 76 del CGP: no pone fin al poder sino 5 días después de presentado el memorial, acompañado de la comunicación enviada al poderdante); sustitución (art. 75 del CGP); terminación por pago (art. 461 del CGP); aclaración, corrección y adición (arts. 285 a 287 del CGP).
Estructura: destinatario; referencia (proceso, radicado, partes); presentación (calidad en que se actúa); ASUNTO; SOLICITUD con su fundamento; ANEXOS si los hay. Sin capítulos innecesarios.`,
  },
  {
    id: 'otro', nombre: 'Otro escrito', area: 'Otro', norma: 'Tú lo describes', rolFirma: 'de la parte que represento', rolCliente: 'la parte que represento',
    desc: 'Describe el documento que necesitas y se redacta con tu membrete y tu estilo.',
    grupos: [
      { n: 'El documento', campos: [C.texto('tipo_libre', '¿Qué documento necesitas?', 'Ej.: Solicitud de amparo de pobreza; habeas data ante central de riesgo; contrato de transacción', { req: true }), C.dest('Juez, entidad o persona destinataria', null, 'Destinatario'), C.radicado(false), C.ciudad()] },
      { n: 'Partes', campos: [C.parte('cliente', 'Tu cliente', PH_PERSONA), C.parte('contraparte', 'Contraparte (si aplica)', PH_ENTIDAD, false)] },
      { n: 'El caso', campos: [C.hechos('Todo lo que el documento debe contar.'), C.area('pretensiones', 'Lo que se pide o se pacta', '', { rows: 4 }), C.pruebas(''), C.notif()] },
    ],
    guia: `Identifica el tipo de escrito descrito por el abogado y aplica la estructura y las normas colombianas vigentes que le correspondan. Si no estás seguro de un requisito, de un término o de un artículo, márcalo [VERIFICAR].`,
  },
];
const TIPOS = Object.fromEntries(TIPOS_LISTA.map(t => [t.id, t]));
const AREAS = ['Constitucional', 'Peticiones y actuaciones administrativas', 'Civil y comercial', 'Familia', 'Laboral', 'Contencioso administrativo', 'Penal', 'Procesos en curso', 'Otro'];

function grupoRedaccion(tipo) {
  const campos = [
    { k: 'fundamentos', l: 'Normas o jurisprudencia que quieres citar', t: 'area', rows: 2, ph: 'Opcional. Ej.: Sentencia T-760 de 2008; art. 49 de la Constitución.' },
    { k: '_extension', l: 'Extensión', t: 'select', opciones: [['concisa', 'Concisa'], ['estandar', 'Estándar'], ['extensa', 'Extensa y exhaustiva']], def: tipo.breve ? 'concisa' : '@extension' },
    { k: '_juris', l: 'Jurisprudencia', t: 'select', opciones: [['sugerir', 'Sugerir sentencias, marcadas para verificar'], ['usuario', 'Solo la que yo indique'], ['ninguna', 'No citar jurisprudencia']], def: tipo.juris || 'sugerir' },
  ];
  if (tipo.firma !== 'poder') campos.push({ k: '_firma', l: 'Quién firma', t: 'select', opciones: [['apoderado', 'Yo, como apoderado(a)'], ['propio', 'Yo, en nombre propio'], ['cliente', 'Mi cliente, en nombre propio']], def: tipo.firma || 'apoderado' });
  campos.push({ k: '_membrete', l: 'Incluir mi membrete en este escrito', t: 'check', def: true });
  campos.push({ k: '_notas', l: 'Indicaciones adicionales', t: 'area', rows: 2, ph: 'Ej.: Enfatiza que la accionante es adulta mayor; no menciones el nombre del médico.' });
  return { n: 'Redacción', campos };
}

/* Contexto normativo verificado (octubre de 2026) que se le da a Claude en cada redacción */
function contextoNormativo() {
  return [
    'Ley 2213 de 2022: la virtualidad en los procesos judiciales es permanente (canal digital de partes, testigos y peritos; envío simultáneo de la demanda; notificación personal por mensaje de datos; poderes por mensaje de datos). Según la sentencia C-522 de 2023, las cargas de admisión del inciso 5 del artículo 6 no se aplican a la acción de tutela.',
    'Ley 2452 de 2025: nuevo Código Procesal del Trabajo y de la Seguridad Social, aplicable a los procesos laborales iniciados desde el 6 de abril de 2026; los iniciados antes siguen con el Decreto-Ley 2158 de 1948. Los antiguos jueces de pequeñas causas laborales pasaron a ser jueces laborales municipales.',
    'Ley 2466 de 2025: reforma laboral que modificó el Código Sustantivo del Trabajo; algunas medidas son de aplicación gradual.',
    'Ley 2220 de 2022: Estatuto de Conciliación, vigente desde el 30 de diciembre de 2022. En asuntos laborales la conciliación no es requisito de procedibilidad.',
    'Ley 2442 de 2024: agregó al artículo 154 del Código Civil la causal de divorcio por la sola voluntad de cualquiera de los cónyuges.',
    `Salario mínimo mensual legal vigente en 2026: ${pesos(state.perfil.ia.smmlv || 1750905)} (dato configurado por el abogado).`,
    'Si una regla procesal cambió recientemente y no tienes certeza del artículo exacto, describe la regla sin número de artículo o marca [VERIFICAR].',
  ];
}

function generoAb() { const g = state.perfil.abogado.genero; return g === 'f' ? 'a' : g === 'm' ? 'o' : 'o(a)'; }

const FORMATO_SALIDA = `FORMATO DE SALIDA (obligatorio; texto plano con estas marcas y ninguna otra):
- Separa los párrafos con una línea en blanco. Dentro de un párrafo, un salto de línea simple es un cambio de línea forzado: úsalo solo en el destinatario, en la referencia y en los bloques de firma.
- Título del escrito, si lo lleva: una línea que empiece con "# ".
- Títulos de capítulo (HECHOS, PRETENSIONES, PRUEBAS…): una línea que empiece con "## ".
- Subtítulos dentro de un capítulo: una línea que empiece con "### ".
- Bloque de referencia (referencia, radicado, partes): cada línea empieza con "| ", por ejemplo: | **Referencia:** Acción de tutela
- Transcripción textual de una norma: cada línea empieza con "> ".
- Viñetas: líneas que empiezan con "- ".
- Negrilla con **dos asteriscos**, cursiva con *un asterisco*, subrayado con __dos guiones bajos__.
- Cada hecho y cada pretensión va en su propio párrafo.
- La firma del abogado se indica solo con la marca [[FIRMA]] o [[FIRMA: rol]] en una línea sola.
- No uses tablas, código, enlaces ni otras marcas.`;
function valorLegible(c, v) {
  if (c.t === 'check') return v ? 'Sí' : 'No';
  if (c.t === 'select') { const o = (c.opciones || []).find(x => x[0] === v); return o ? o[1] : v; }
  if (c.t === 'chips') return (v || []).join(', ');
  return String(v || '').trim();
}
function camposTipo(tipo) { return [...tipo.grupos.flatMap(g => g.campos), ...grupoRedaccion(tipo).campos]; }
function instruccionFirma(tipo) {
  const ab = state.perfil.abogado, g = generoAb();
  const nombre = ab.nombre || 'el abogado';
  const modo = tipo.firma === 'poder' ? 'poder' : (state.datos._firma || 'apoderado');
  if (modo === 'poder') return `El poder lo otorga ${tipo.rolCliente} y lo acepta ${nombre}. Al final escribe el bloque de firma del poderdante (una línea de guiones bajos, su nombre en mayúsculas y su documento; si es persona jurídica, el nombre del representante legal y el NIT), luego «Acepto,» en su propio párrafo y, en una línea sola, [[FIRMA: Apoderad${g}]].`;
  if (modo === 'cliente') return `El escrito lo firma directamente ${tipo.rolCliente} en nombre propio; el abogado solo lo redacta y no se menciona en el documento. No uses [[FIRMA]]. Al final, después de la despedida, escribe el bloque de firma del firmante: una línea de guiones bajos, su nombre en mayúsculas y su documento de identidad, cada dato en su propia línea dentro del mismo párrafo.`;
  if (modo === 'propio') return `${nombre} actúa en nombre propio. Preséntalo con su nombre, cédula y tarjeta profesional. Termina con [[FIRMA]] en una línea sola.`;
  return `El escrito lo presenta ${nombre} como apoderad${g} ${tipo.rolFirma || 'de su cliente'}. En el párrafo de presentación identifícal${g === 'o(a)' ? 'o(a)' : g} con su nombre, cédula y tarjeta profesional e indica que actúa según el poder que se anexa (inclúyelo en los anexos). Al final, después de la fórmula de despedida, escribe en una línea sola: [[FIRMA: Apoderad${g} ${tipo.rolFirma || ''}]].`;
}
function lineasEstilo() {
  const e = state.perfil.estilo, L = [];
  if (e.tratamiento !== 'auto') L.push(`Dirígete al despacho como «${e.tratamiento}».`);
  if (e.persona === 'primera') L.push('Escribe en primera persona («me permito», «solicito», «manifiesto»).');
  if (e.persona === 'tercera') L.push('Escribe en tercera persona («el suscrito apoderado», «la parte que represento»).');
  if (e.numHechos === 'ordinal') L.push('Numera los hechos con ordinales en mayúscula y negrilla: **PRIMERO.**, **SEGUNDO.**');
  if (e.numHechos === 'numero') L.push('Numera los hechos con números arábigos: 1., 2., 3.');
  if (e.numHechos === 'hecho') L.push('Numera los hechos así: **Hecho 1.**, **Hecho 2.**');
  if (e.numPretensiones === 'ordinal') L.push('Numera las pretensiones con ordinales femeninos en mayúscula y negrilla: **PRIMERA.**, **SEGUNDA.**');
  if (e.numPretensiones === 'numero') L.push('Numera las pretensiones con números arábigos: 1., 2., 3.');
  L.push({ sobrio: 'Tono sobrio, técnico y respetuoso.', contundente: 'Tono firme y contundente, sin perder el respeto por el despacho ni por la contraparte.', sencillo: 'Lenguaje claro y sencillo, comprensible para el cliente, sin perder rigor.' }[e.tono] || 'Tono sobrio y técnico.');
  if (e.lenguaje === 'claro') L.push('Lenguaje claro y moderno: evita latinismos innecesarios, fórmulas arcaicas y oraciones demasiado largas.');
  if (e.lenguaje === 'tradicional') L.push('Estilo forense tradicional colombiano, con sus fórmulas clásicas («respetuosamente me permito», «con todo respeto»).');
  if (e.fecha === 'arriba') L.push('Escribe el lugar y la fecha al inicio, antes del destinatario.');
  if (e.fecha === 'final') L.push('Escribe el lugar y la fecha al final, antes de la firma.');
  if (e.fecha === 'no') L.push('No escribas lugar ni fecha.');
  L.push(e.esd ? 'En los escritos dirigidos a un despacho judicial, cierra el destinatario con «E. S. D.».' : 'No uses «E. S. D.» en el destinatario.');
  if (e.cierre) L.push(`Fórmula de despedida antes de la firma: «${e.cierre}».`);
  return L;
}
function construirPrompt() {
  const tipo = TIPOS[state.tipo];
  const p = state.perfil, ab = p.abogado, d = state.datos;
  const L = [];
  L.push('Eres un abogado litigante colombiano con amplia experiencia. Redactas escritos jurídicos impecables, listos para radicar. Redacta completo el documento descrito abajo.');
  L.push('');
  L.push(`FECHA DE HOY: ${fechaLarga()}. Úsala si el escrito lleva fecha.`);
  L.push(`DOCUMENTO: ${tipo.nombre}${d.tipo_libre ? ' (' + d.tipo_libre + ')' : ''}`);
  L.push('');
  L.push('CONTEXTO NORMATIVO VIGENTE (octubre de 2026; prevalece sobre lo que recuerdes):');
  contextoNormativo().forEach(x => L.push('- ' + x));
  L.push('');
  L.push('GUÍA JURÍDICA Y ESTRUCTURA PARA ESTE ESCRITO:');
  L.push(tipo.guia);
  L.push('');
  L.push('ABOGADO(A) QUE REDACTA:');
  if (ab.nombre) {
    L.push(`- Nombre: ${ab.nombre} (${ab.genero === 'f' ? 'abogada; trátala en femenino: la suscrita, apoderada' : ab.genero === 'm' ? 'abogado; trátalo en masculino: el suscrito, apoderado' : 'usa la forma «apoderado(a)» si necesitas nombrarlo'})`);
    L.push(`- Cédula: ${ab.cedula ? ab.cedula + (ab.cedulaLugar ? ' de ' + ab.cedulaLugar : '') : '[COMPLETAR]'}`);
    L.push(`- Tarjeta profesional: ${ab.tp ? ab.tp + ' del Consejo Superior de la Judicatura' : '[COMPLETAR]'}`);
    if (ab.correo) L.push(`- Correo de notificaciones (inscrito en el Registro Nacional de Abogados): ${ab.correo}`);
    if (ab.telefono) L.push(`- Teléfono: ${ab.telefono}`);
    if (ab.direccion) L.push(`- Dirección: ${ab.direccion}${ab.ciudad ? ', ' + ab.ciudad : ''}`);
  } else L.push('- Sus datos no están configurados: donde debas mencionarlos escribe [COMPLETAR: nombre del abogado], [COMPLETAR: cédula] y [COMPLETAR: tarjeta profesional].');
  L.push('');
  L.push('QUIÉN FIRMA:');
  L.push(instruccionFirma(tipo));
  L.push('');
  L.push('ESTILO DEL ABOGADO (síguelo):');
  lineasEstilo().forEach(x => L.push('- ' + x));
  if (p.estilo.ficha.trim()) { L.push(''); L.push('FICHA DE ESTILO DEL ABOGADO (prevalecen las preferencias anteriores si chocan):'); L.push(p.estilo.ficha.trim().slice(0, 4000)); }
  if (p.estilo.muestra.trim()) {
    L.push('');
    L.push('MUESTRA DE UN ESCRITO DEL ABOGADO. Imita su voz, sus fórmulas, el orden de sus capítulos y su nivel de formalidad. No copies sus hechos, nombres ni datos:');
    L.push('<<<'); L.push(p.estilo.muestra.trim().slice(0, 9000)); L.push('>>>');
  }
  L.push('');
  L.push('DATOS DEL CASO (los escribió el abogado; pueden estar en borrador o con errores de digitación: corrígelos al redactar sin cambiar su sentido):');
  for (const c of camposTipo(tipo)) {
    if (c.k.startsWith('_') && c.k !== '_notas') continue;
    const v = d[c.k];
    if (v == null || v === '' || (Array.isArray(v) && !v.length)) continue;
    if (c.t === 'check' && c.k === 'juramento') { L.push(`### ${c.l}`); L.push(v ? 'Sí, inclúyelo.' : 'No lo incluyas.'); continue; }
    L.push(`### ${c.k === '_notas' ? 'Indicaciones adicionales del abogado' : c.l}`);
    L.push(valorLegible(c, v));
  }
  L.push('');
  const ext = d._extension || p.estilo.extension;
  const juris = d._juris || 'sugerir';
  const nSent = ext === 'concisa' ? 2 : ext === 'extensa' ? 6 : 4;
  L.push('REGLAS OBLIGATORIAS:');
  L.push('1. Usa únicamente los hechos, nombres, cifras, fechas y documentos que aparecen en los datos del caso. No inventes nada. Si falta un dato necesario, escribe en su lugar [COMPLETAR: descripción breve del dato].');
  L.push('2. Puedes ordenar, depurar y redactar con lenguaje jurídico los hechos y las pretensiones, sin alterar su sentido ni agregar hechos nuevos.');
  L.push('3. Cita solo normas colombianas que existan y estén vigentes. Si dudas del número de un artículo o de su vigencia, escribe [VERIFICAR] inmediatamente después de la cita.');
  if (juris === 'sugerir') L.push(`4. Jurisprudencia: además de la que indique el abogado, puedes citar hasta ${nSent} pronunciamientos de la Corte Constitucional, la Corte Suprema de Justicia o el Consejo de Estado que conozcas con certeza y que sean pertinentes; prefiere sentencias de unificación y precedentes muy reconocidos. Escribe [VERIFICAR] inmediatamente después de cada sentencia que cites y que no haya suministrado el abogado. Nunca inventes números de sentencia, radicados, fechas ni magistrados ponentes.`);
  else if (juris === 'usuario') L.push('4. Jurisprudencia: cita únicamente la que indicó el abogado en los datos del caso; no agregues otras sentencias.');
  else L.push('4. Jurisprudencia: no cites sentencias. Funda el escrito en la Constitución, la ley y los hechos.');
  L.push('5. Nunca pongas entre comillas un texto atribuido a una sentencia, a una norma o a un autor, salvo que el abogado lo haya suministrado textualmente o estés seguro de su texto exacto; en caso contrario, parafrasea.');
  L.push('6. No escribas el membrete ni el encabezado o pie de página con los datos de contacto del abogado: se agregan automáticamente. Sí escribe el destinatario y la referencia.');
  L.push(`7. Extensión: ${{ concisa: 'concisa y directa, solo lo esencial de cada capítulo.', estandar: 'completa pero sin relleno ni repeticiones.', extensa: 'exhaustiva: desarrolla a fondo cada argumento.' }[ext] || 'completa pero sin relleno.'}`);
  L.push('8. Escribe solo el documento: sin comentarios, notas, advertencias ni explicaciones antes o después.');
  L.push('');
  L.push(FORMATO_SALIDA);
  return L.join('\n');
}
