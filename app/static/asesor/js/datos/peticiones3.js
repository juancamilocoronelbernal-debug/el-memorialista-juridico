/* ============================================================
   peticiones3.js — Casos de DERECHO DE PETICIÓN (parte 3):
   quejas, víctimas, migración, juzgados, ICBF, arrendador y
   petición general.
   ============================================================ */
window.AJ = window.AJ || {};
AJ.casos = AJ.casos || [];

(function () {
  const R = AJ.red;
  const C = AJ.campos;
  const cd = (c, f) => AJ.camposDe(c, f);

  AJ.casos.push(
  /* ---------------- QUEJA CONTRA FUNCIONARIO ---------------- */
  {
    id: 'pet_queja_funcionario', tipo: 'peticion', categoria: 'municipio',
    titulo: 'Queja por mala atención o conducta indebida de un funcionario',
    resumen: 'Denunciar maltrato, negligencia, cobros indebidos, discriminación o abuso de un servidor público. Puede ser anónima si aportas pruebas. Se dirige a la entidad, la Personería o la Procuraduría.',
    palabras: ['queja', 'funcionario', 'mala atención', 'maltrato', 'abuso', 'negligencia', 'corrupción', 'cobro', 'discriminación', 'procuraduría', 'personería', 'control interno disciplinario', 'denuncia', 'policía'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Personería de Medellín / Oficina de Control Interno Disciplinario de la Alcaldía / Procuraduría Provincial', cargo: 'Oficina de Control Interno Disciplinario / Personero(a)' },
    campos: [
      { id: 'funcionario', tipo: 'texto', etiqueta: 'Nombre o descripción del funcionario y entidad donde trabaja', ejemplo: 'Ej.: Funcionaria de la ventanilla 3 de la Secretaría de Tránsito, de apellido Gómez', requerido: true, ancho: 'completa' },
      { id: 'conducta', tipo: 'checks', etiqueta: '¿Qué hizo?', requerido: true, opciones: [
        { v: 'maltrato', t: 'Me trató mal, me gritó o me humilló', legal: 'trato irrespetuoso, humillante o degradante' },
        { v: 'negligencia', t: 'No me atendió o no hizo su trabajo', legal: 'omisión injustificada de sus funciones y negación del servicio' },
        { v: 'cobro', t: 'Me pidió dinero o favores para hacer el trámite', legal: 'exigencia de dinero o dádivas para realizar un trámite' },
        { v: 'discriminacion', t: 'Me discriminó (por mi condición, origen, género, discapacidad)', legal: 'actos de discriminación' },
        { v: 'informacion', t: 'Me dio información falsa o me hizo perder el trámite', legal: 'suministro de información falsa o inducción a error en el trámite' },
        { v: 'abuso', t: 'Abusó de su autoridad o me amenazó', legal: 'abuso de autoridad y amenazas' },
        { v: 'peticion', t: 'No respondió mi derecho de petición', legal: 'omisión de respuesta a un derecho de petición' }
      ] },
      { id: 'fechaHechos', tipo: 'fecha', etiqueta: 'Fecha de los hechos', requerido: true, ancho: 'media' },
      { id: 'lugar', tipo: 'texto', etiqueta: 'Lugar (oficina, ventanilla, dirección)', requerido: true, ancho: 'media' },
      { id: 'testigos', tipo: 'texto', etiqueta: 'Testigos (nombres y teléfonos, si los hay)', ancho: 'completa' },
      C.relato({ ejemplo: 'Ej.:\nEl 5 de septiembre de 2026 a las 10 a. m. fui a la ventanilla 3 a radicar mi petición.\nLa funcionaria se negó a recibirla, me dijo que "no tenía tiempo para eso" y me pidió que volviera otro día.\nCuando insistí, me gritó delante de las demás personas.' })
    ],
    asunto: d => `Queja contra servidor público – ${d.funcionario || 'funcionario'}`,
    hechos: d => {
      const h = [];
      h.push(`${R.capital(R.elDia(d.fechaHechos))}, en ${d.lugar || 'las instalaciones de la entidad'}, el servidor público que se identifica como "${d.funcionario || 'funcionario descrito en el relato'}" incurrió en ${R.lista((d.conducta || []).map(v => R.opcionTexto(cd('pet_queja_funcionario', 'conducta'), v)))}.`);
      if (d.testigos) h.push(`Presenciaron los hechos: ${d.testigos}.`);
      h.push('La conducta descrita desconoce los principios de la función administrativa, los derechos de las personas ante las autoridades (artículo 5 de la Ley 1437 de 2011: recibir trato respetuoso y considerado, obtener información y orientación, y ser atendidas con prioridad en caso de condición de vulnerabilidad) y puede constituir falta disciplinaria.');
      return h;
    },
    normas: ['cp2', 'cp23', 'cp209', 'l1755_13', 'l1755_31', 'l190_38'],
    fundamentos: d => ['De acuerdo con los artículos 2, 86 y 129 de la Ley 1952 de 2019 (Código General Disciplinario, modificado por la Ley 2094 de 2021), cualquier persona puede presentar queja contra un servidor público; la oficina de control interno disciplinario de la entidad, la Personería o la Procuraduría deben iniciar la indagación o investigación correspondiente, y al quejoso se le comunican la decisión de archivo y el fallo absolutorio.'],
    peticiones: [
      { v: 'investigar', inicial: true, t: 'Que investiguen disciplinariamente la conducta', legal: 'Iniciar la indagación o investigación disciplinaria contra el servidor público por los hechos descritos y adoptar las sanciones que correspondan.' },
      { v: 'informar', inicial: true, t: 'Que me informen el radicado y las decisiones', legal: 'Informarme el número de radicado asignado a la queja y comunicarme las decisiones de fondo que se adopten, conforme al artículo 129 de la Ley 1952 de 2019.' },
      { v: 'tramite', t: 'Que ordenen atender el trámite que me negaron', legal: 'Ordenar que se me atienda y se dé trámite inmediato a la solicitud o servicio que me fue negado.' },
      { v: 'garantias', t: 'Que garanticen que no habrá represalias', legal: 'Garantizar que no se adoptarán represalias en mi contra por la presentación de esta queja.' }
    ],
    anexos: [ { v: 'pruebas', t: 'Audios, videos, fotos o pantallazos' }, { v: 'radicados', t: 'Radicados o turnos de atención' }, { v: 'testigos', t: 'Declaraciones de testigos' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Si la presentas de forma anónima, anexa pruebas concretas (audios, documentos) para que deban tramitarla.', siNoResponden: 'Puedes presentar la misma queja ante la Procuraduría (www.procuraduria.gov.co) o la Personería. Si hubo exigencia de dinero, denuncia penal ante la Fiscalía (concusión o cohecho).' }
  },

  /* ---------------- VÍCTIMAS ---------------- */
  {
    id: 'pet_victimas', tipo: 'peticion', categoria: 'nacional',
    titulo: 'Petición a la Unidad para las Víctimas (registro, ayuda humanitaria, indemnización)',
    resumen: 'Preguntar por el estado de tu inclusión en el Registro Único de Víctimas, pedir ayuda humanitaria, reclamar la indemnización administrativa o actualizar tus datos.',
    palabras: ['víctima', 'víctimas', 'desplazamiento', 'desplazado', 'conflicto armado', 'RUV', 'registro', 'ayuda humanitaria', 'indemnización', 'reparación', 'Unidad de Víctimas', 'declaración', 'retorno'],
    destinatario: { categoria: 'nacional', nombre: 'Unidad para la Atención y Reparación Integral a las Víctimas', cargo: 'Dirección de Registro y Gestión de la Información / Subdirección de Asistencia y Atención Humanitaria' },
    campos: [
      { id: 'tramite', tipo: 'select', etiqueta: '¿Qué necesitas?', requerido: true, opciones: [
        { v: 'registro', t: 'Saber si fui incluido(a) en el Registro Único de Víctimas (RUV)', legal: 'la decisión sobre la inclusión en el Registro Único de Víctimas' },
        { v: 'ayuda', t: 'Ayuda humanitaria (no me la han entregado o la suspendieron)', legal: 'la entrega de la atención humanitaria' },
        { v: 'indemnizacion', t: 'Indemnización administrativa (estado, turno o pago)', legal: 'la información y el pago de la indemnización administrativa' },
        { v: 'novedad', t: 'Actualizar mis datos o incluir a mi familia', legal: 'la actualización de datos y la inclusión del núcleo familiar' },
        { v: 'recurso', t: 'Me negaron la inclusión y quiero que la revisen', legal: 'la revisión de la decisión que negó la inclusión' },
        { v: 'retorno', t: 'Apoyo para retorno, reubicación o vivienda', legal: 'las medidas de retorno, reubicación o acceso a vivienda' }
      ], ancho: 'completa' },
      { id: 'hecho', tipo: 'select', etiqueta: 'Hecho victimizante', opciones: [ { v: 'desplazamiento', t: 'Desplazamiento forzado' }, { v: 'homicidio', t: 'Homicidio de un familiar' }, { v: 'desaparicion', t: 'Desaparición forzada' }, { v: 'amenaza', t: 'Amenaza' }, { v: 'despojo', t: 'Despojo de tierras' }, { v: 'otro', t: 'Otro' } ], valorInicial: 'desplazamiento', ancho: 'media' },
      { id: 'fechaDeclaracion', tipo: 'fecha', etiqueta: 'Fecha de la declaración ante Personería o Defensoría', ancho: 'media' },
      { id: 'codigo', tipo: 'texto', etiqueta: 'Código o radicado de la declaración (FUD) o del caso', ancho: 'media' },
      { id: 'nucleo', tipo: 'texto', etiqueta: 'Personas de tu hogar (número y edades)', ejemplo: 'Ej.: 5 personas: 2 adultos, 3 niños de 3, 7 y 12 años', ancho: 'media' },
      { id: 'situacion', tipo: 'textarea', etiqueta: '¿Cuál es tu situación actual? (vivienda, alimentación, salud, trabajo)', requerido: true, filas: 3 },
      C.relato({ requerido: false, etiqueta: '¿Algo más que debamos contar? (opcional)' })
    ],
    asunto: d => `Derecho de petición – ${R.capital(R.opcionTexto(cd('pet_victimas', 'tramite'), d.tramite))}${d.codigo ? ` (${d.codigo})` : ''}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} es víctima del conflicto armado por el hecho de ${R.opcionTexto(cd('pet_victimas', 'hecho'), d.hecho, 't').toLowerCase()}${d.fechaDeclaracion ? `, y rindió declaración ${R.elDia(d.fechaDeclaracion)}` : ''}${d.codigo ? `, bajo el código o radicado ${d.codigo}` : ''}.`);
      if (d.nucleo) h.push(`Su núcleo familiar está conformado por ${d.nucleo}.`);
      if (d.situacion) h.push(`Situación actual del hogar: ${R.oracion(d.situacion)}`);
      h.push(`Hasta la fecha, la Unidad no ha garantizado ${R.opcionTexto(cd('pet_victimas', 'tramite'), d.tramite)}, pese a los términos legales.`);
      return h;
    },
    normas: ['cp13', 'cp23', 'l1448', 't025', 'l1755_14', 'l1755_20'],
    peticiones: [
      { v: 'resolver', inicial: true, t: 'Que resuelvan de fondo mi solicitud', legal: d => `Resolver de fondo ${R.opcionTexto(cd('pet_victimas', 'tramite'), d.tramite)}, mediante acto administrativo motivado, dentro de los términos legales, y notificármelo.` },
      { v: 'ayuda', inicial: d => d.tramite === 'ayuda', t: 'Que entreguen la ayuda humanitaria de inmediato', legal: 'Realizar la medición de carencias y entregar de inmediato la atención humanitaria que corresponda a la situación del hogar, informando fecha y lugar de cobro.' },
      { v: 'turno', inicial: d => d.tramite === 'indemnizacion', t: 'Que me informen el turno y la fecha estimada de la indemnización', legal: 'Informar el estado del trámite de indemnización administrativa, el método de priorización aplicado, el turno asignado y la fecha estimada de pago.' },
      { v: 'copia', t: 'Que me entreguen copia de mi expediente y de la resolución', legal: 'Expedir copia del expediente, de la resolución de inclusión o no inclusión y de las constancias de notificación.' },
      { v: 'enlace', t: 'Que me remitan a los programas de salud, educación y vivienda', legal: 'Orientar y remitir al hogar a las entidades competentes para el acceso a salud, educación, vivienda y generación de ingresos, en el marco del Plan de Atención, Asistencia y Reparación Integral.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'declaracion', t: 'Constancia de la declaración (FUD)' }, { v: 'registros', t: 'Registros civiles del núcleo familiar' }, { v: 'resolucion', t: 'Resolución de inclusión o negación (si existe)' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'La Unidad tiene 60 días hábiles desde la declaración para decidir la inclusión en el RUV. Si te niegan, tienes 10 días hábiles para recurso de reposición y apelación.', siNoResponden: 'Sin respuesta, presenta la "Tutela de víctimas (ayuda humanitaria o registro)". La Personería y la Defensoría te acompañan gratis.' }
  },

  /* ---------------- MIGRACIÓN ---------------- */
  {
    id: 'pet_migracion', tipo: 'peticion', categoria: 'nacional',
    titulo: 'Petición a Migración Colombia (PPT, cita, salvoconducto, visa, estado del trámite)',
    resumen: 'Pedir respuesta sobre el Permiso por Protección Temporal, cédula de extranjería, salvoconducto, cita o corrección de datos.',
    palabras: ['migración', 'migrante', 'venezolano', 'PPT', 'permiso', 'salvoconducto', 'cédula de extranjería', 'visa', 'cita', 'regularización', 'refugio', 'pasaporte'],
    destinatario: { categoria: 'nacional', nombre: 'Migración Colombia (Unidad Administrativa Especial)', cargo: 'Dirección Regional / Grupo de Extranjería' },
    campos: [
      { id: 'tramite', tipo: 'select', etiqueta: '¿Qué necesitas?', requerido: true, opciones: [
        { v: 'ppt', t: 'Estado o entrega de mi Permiso por Protección Temporal (PPT)', legal: 'la decisión y entrega del Permiso por Protección Temporal' },
        { v: 'cita', t: 'Una cita que no logro agendar', legal: 'la asignación de cita para el trámite' },
        { v: 'salvoconducto', t: 'Salvoconducto de permanencia', legal: 'la expedición del salvoconducto de permanencia' },
        { v: 'cedula', t: 'Cédula de extranjería (expedición o renovación)', legal: 'la expedición o renovación de la cédula de extranjería' },
        { v: 'correccion', t: 'Corregir mis datos en el sistema', legal: 'la corrección de los datos registrados' },
        { v: 'refugio', t: 'Estado de mi solicitud de refugio', legal: 'la información sobre el estado de la solicitud de reconocimiento de la condición de refugiado' },
        { v: 'otro', t: 'Otro trámite migratorio', legal: 'el trámite migratorio descrito' }
      ], ancho: 'completa' },
      { id: 'nacionalidad', tipo: 'texto', etiqueta: 'Nacionalidad', ejemplo: 'Ej.: venezolana', ancho: 'media' },
      { id: 'fechaSolicitud', tipo: 'fecha', etiqueta: 'Fecha en que iniciaste el trámite', ancho: 'media' },
      { id: 'radicado', tipo: 'texto', etiqueta: 'Número de radicado, RUMV o referencia', ancho: 'media' },
      { id: 'afectacion', tipo: 'textarea', etiqueta: '¿Qué no puedes hacer por falta del documento? (trabajar, afiliarte a salud, matricular a tus hijos, abrir cuenta)', requerido: true, filas: 3 },
      C.relato({ requerido: false, etiqueta: '¿Algo más que debamos contar? (opcional)' })
    ],
    asunto: d => `Derecho de petición – ${R.capital(R.opcionTexto(cd('pet_migracion', 'tramite'), d.tramite))}${d.radicado ? ` (${d.radicado})` : ''}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom}, de nacionalidad ${d.nacionalidad || 'extranjera'}, reside en Colombia${d.fechaSolicitud ? ` y ${R.elDia(d.fechaSolicitud)} inició ante Migración Colombia el trámite correspondiente a ${R.opcionTexto(cd('pet_migracion', 'tramite'), d.tramite)}` : ''}${d.radicado ? `, con radicado o referencia ${d.radicado}` : ''}.`);
      h.push(`Hasta la fecha no ha obtenido respuesta de fondo ni el documento requerido.`);
      if (d.afectacion) h.push(`La falta del documento le impide el ejercicio de derechos básicos: ${R.oracion(d.afectacion)}`);
      return h;
    },
    normas: ['cp13', 'cp23', 'l1755_14', 'l1755_20', 'migr', 'cp209'],
    fundamentos: d => ['El artículo 100 de la Constitución Política garantiza a los extranjeros en Colombia los mismos derechos civiles que a los nacionales, y el artículo 13 de la Ley 1437 de 2011 reconoce el derecho de petición a toda persona, sin distinción de nacionalidad o situación migratoria.'],
    peticiones: [
      { v: 'resolver', inicial: true, t: 'Que resuelvan y entreguen el documento o me den la cita', legal: d => `Resolver de fondo ${R.opcionTexto(cd('pet_migracion', 'tramite'), d.tramite)} y, según corresponda, expedir el documento o asignar la cita, informando por escrito la fecha, el lugar y los requisitos.` },
      { v: 'estado', inicial: true, t: 'Que me informen el estado del trámite y qué falta', legal: 'Informar el estado del trámite, los documentos o requisitos que eventualmente falten y el término en que se decidirá.' },
      { v: 'constancia', t: 'Que me den una constancia del trámite para acceder a salud y educación', legal: 'Expedir constancia del trámite en curso que permita acreditar la situación migratoria ante entidades de salud, educación y empleadores.' }
    ],
    anexos: [ { v: 'documento', t: 'Copia del pasaporte, cédula venezolana, PPT o documento que tengas' }, { v: 'rumv', t: 'Constancia del Registro Único de Migrantes (RUMV) o del trámite' }, { v: 'soportes', t: 'Soportes de la afectación (negativa de afiliación, carta de empleador, colegio)' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, siNoResponden: 'Tutela por violación del derecho de petición. Si hay una urgencia de salud, la atención de urgencias no puede negarse por tu situación migratoria: presenta la "Tutela por salud de personas migrantes".' }
  },

  /* ---------------- JUZGADO ---------------- */
  {
    id: 'pet_juzgado', tipo: 'peticion', categoria: 'judicial',
    titulo: 'Petición a un juzgado o fiscalía (información del proceso, copias, impulso, estado de una denuncia)',
    resumen: 'Preguntar por el estado de tu proceso o denuncia, pedir copias del expediente, solicitar que se decida una petición pendiente o que se fije fecha de audiencia.',
    palabras: ['juzgado', 'proceso', 'expediente', 'fiscalía', 'denuncia', 'audiencia', 'copias', 'impulso', 'radicado', 'demanda', 'sentencia', 'noticia criminal', 'abogado'],
    destinatario: { categoria: 'judicial', ejemploNombre: 'Ej.: Juzgado 5 Civil Municipal de Cali / Fiscalía 23 Local de Bogotá', cargo: 'Juez / Fiscal / Secretaría' },
    campos: [
      { id: 'radicado', tipo: 'texto', etiqueta: 'Número de radicado del proceso o de la noticia criminal', ejemplo: 'Ej.: 76001-40-03-005-2025-00123-00 / 110016000050202512345', requerido: true, ancho: 'completa' },
      { id: 'calidad', tipo: 'select', etiqueta: '¿Qué eres en ese proceso?', opciones: [ { v: 'demandante', t: 'Demandante o accionante', legal: 'parte demandante' }, { v: 'demandado', t: 'Demandado(a)', legal: 'parte demandada' }, { v: 'victima', t: 'Víctima o denunciante', legal: 'víctima o denunciante' }, { v: 'denunciado', t: 'Denunciado(a) o indiciado(a)', legal: 'persona denunciada o indiciada' }, { v: 'tercero', t: 'Tercero interesado', legal: 'tercero con interés legítimo' } ], valorInicial: 'demandante', ancho: 'media' },
      { id: 'tramite', tipo: 'checks', etiqueta: '¿Qué necesitas?', requerido: true, opciones: [
        { v: 'estado', t: 'Saber en qué estado va el proceso o la denuncia', legal: 'la información sobre el estado actual de la actuación' },
        { v: 'copias', t: 'Copias del expediente o de una decisión', legal: 'copia del expediente o de la decisión' },
        { v: 'impulso', t: 'Que decidan una solicitud que lleva mucho tiempo sin respuesta', legal: 'el impulso y decisión de la solicitud pendiente' },
        { v: 'audiencia', t: 'Que fijen fecha de audiencia', legal: 'la programación de la audiencia' },
        { v: 'archivo', t: 'Saber por qué archivaron o no avanzan en mi denuncia', legal: 'la explicación sobre el archivo o la inactividad de la investigación' },
        { v: 'entrega', t: 'Que me entreguen un dinero, título o bien que está en el juzgado', legal: 'la entrega de los títulos, dineros o bienes a disposición del despacho' }
      ] },
      { id: 'fechaPendiente', tipo: 'fecha', etiqueta: 'Fecha de la solicitud o actuación que está pendiente (si aplica)', ancho: 'media' },
      C.relato({ ejemplo: 'Ej.:\nPresenté la denuncia por hurto el 2 de febrero de 2026.\nDesde entonces no me han citado ni informado nada.\nLlamo y no contestan el teléfono del despacho.' })
    ],
    asunto: d => `Derecho de petición – Proceso o noticia criminal ${d.radicado || ''}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} actúa como ${R.opcionTexto(cd('pet_juzgado', 'calidad'), d.calidad)} dentro de la actuación radicada bajo el número ${d.radicado || '[radicado]'}, que cursa en ${R.entidad(d)}.`);
      h.push(`Requiere ${R.lista((d.tramite || []).map(v => R.opcionTexto(cd('pet_juzgado', 'tramite'), v)))}${d.fechaPendiente ? `, en relación con la solicitud o actuación de ${R.fechaLarga(d.fechaPendiente)}` : ''}.`);
      return h;
    },
    normas: ['cp23', 'cp29', 'l1755_13', 'l1755_14', 'cp228'],
    fundamentos: d => {
      const f = ['El artículo 228 de la Constitución Política dispone que los términos procesales se observarán con diligencia y su incumplimiento será sancionado, y el artículo 7 de la Ley 270 de 1996 (Estatutaria de la Administración de Justicia) consagra el principio de eficiencia. El derecho de petición ante autoridades judiciales procede respecto de actuaciones administrativas y de la información sobre el estado de los procesos, y el acceso al expediente por las partes está garantizado por el artículo 123 del Código General del Proceso.'];
      if (['victima', 'denunciado'].includes(d.calidad) || /FISCAL/i.test(R.entidad(d))) f.push('Conforme a los artículos 11 y 136 de la Ley 906 de 2004, las víctimas tienen derecho a recibir información sobre el estado de la investigación, a ser oídas y a que se les comunique la decisión de archivo, la cual pueden solicitar que se revise.');
      return f;
    },
    peticiones: [
      { v: 'informar', inicial: true, t: 'Que me informen por escrito el estado del proceso y la próxima actuación', legal: 'Informar por escrito el estado actual de la actuación, la última decisión adoptada, las actuaciones pendientes y la fecha estimada de la próxima.' },
      { v: 'copias', t: 'Que me entreguen copia del expediente (digital)', legal: 'Expedir copia del expediente o de las piezas procesales solicitadas, preferiblemente en formato digital al correo indicado.' },
      { v: 'impulso', t: 'Que decidan la solicitud pendiente', legal: 'Impulsar la actuación y decidir la solicitud pendiente dentro de los términos legales.' },
      { v: 'entrega', t: 'Que ordenen la entrega de títulos o dineros', legal: 'Ordenar la entrega de los títulos judiciales, dineros o bienes a disposición del despacho que correspondan al peticionario.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'radicado', t: 'Constancia de la denuncia o del proceso' }, { v: 'memoriales', t: 'Copia de solicitudes anteriores' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Envía la petición al correo institucional del despacho (lo encuentras en www.ramajudicial.gov.co) y guarda el correo enviado.', siNoResponden: 'Tutela por violación del derecho de petición (contra juzgados se reparte a los tribunales superiores). Si la demora es injustificada, queja ante la Comisión Seccional de Disciplina Judicial.' }
  },

  /* ---------------- ICBF / COMISARÍA: INFORMACIÓN ---------------- */
  {
    id: 'pet_icbf', tipo: 'peticion', categoria: 'nacional',
    titulo: 'Petición al ICBF o a la Comisaría de Familia (proceso de un menor, cita, custodia, visitas)',
    resumen: 'Pedir información sobre un proceso de restablecimiento de derechos, pedir cita de conciliación, revisar una medida sobre un niño o pedir copia de un expediente.',
    palabras: ['ICBF', 'bienestar familiar', 'comisaría de familia', 'niño', 'niña', 'custodia', 'visitas', 'restablecimiento de derechos', 'defensor de familia', 'conciliación', 'hogar sustituto', 'adopción'],
    destinatario: { categoria: 'nacional', ejemploNombre: 'Ej.: ICBF Centro Zonal Nororiental / Comisaría Primera de Familia de Bucaramanga', cargo: 'Defensor(a) de Familia / Comisario(a) de Familia' },
    campos: [
      { id: 'menor', tipo: 'texto', etiqueta: 'Nombre y edad del niño, niña o adolescente', requerido: true, ancho: 'media' },
      { id: 'relacion', tipo: 'select', etiqueta: '¿Qué eres del menor?', opciones: [ { v: 'madre', t: 'Madre', legal: 'madre' }, { v: 'padre', t: 'Padre', legal: 'padre' }, { v: 'abuelo', t: 'Abuelo(a)', legal: 'abuelo(a)' }, { v: 'tio', t: 'Tío(a)', legal: 'tío(a)' }, { v: 'hermano', t: 'Hermano(a) mayor', legal: 'hermano(a)' }, { v: 'otro', t: 'Otro familiar o cuidador', legal: 'familiar o cuidador(a)' } ], valorInicial: 'madre', ancho: 'media' },
      { id: 'tramite', tipo: 'select', etiqueta: '¿Qué necesitas?', requerido: true, opciones: [
        { v: 'estado', t: 'Información sobre un proceso de restablecimiento de derechos', legal: 'la información sobre el estado del proceso administrativo de restablecimiento de derechos' },
        { v: 'visitas', t: 'Que me permitan ver al niño o regulen las visitas', legal: 'la regulación del régimen de visitas y el contacto con el menor' },
        { v: 'custodia', t: 'Cita de conciliación sobre custodia o alimentos', legal: 'la citación a audiencia de conciliación sobre custodia, cuidado personal o alimentos' },
        { v: 'reintegro', t: 'Que el niño regrese con su familia', legal: 'el reintegro del menor a su familia' },
        { v: 'copias', t: 'Copia del expediente o de la decisión', legal: 'copia del expediente y de las decisiones adoptadas' },
        { v: 'denuncia', t: 'Que actúen porque un niño está en riesgo', legal: 'la verificación de derechos de un menor en situación de riesgo' }
      ], ancho: 'completa' },
      { id: 'radicado', tipo: 'texto', etiqueta: 'Número del proceso o del caso (si lo sabes)', ancho: 'media' },
      C.relato({ ejemplo: 'Ej.:\nEl 15 de agosto de 2026 el ICBF se llevó a mi nieto a un hogar sustituto.\nNo me han informado por qué ni me han dejado visitarlo.\nYo lo cuidé desde que nació y puedo hacerme cargo de él.' })
    ],
    asunto: d => `Derecho de petición – ${R.opcionTexto(cd('pet_icbf', 'tramite'), d.tramite)} – ${d.menor || 'menor'}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} es ${R.generizar(R.opcionTexto(cd('pet_icbf', 'relacion'), d.relacion), a.g)} de ${d.menor || 'el menor'}${d.radicado ? `, respecto de quien cursa la actuación No. ${d.radicado}` : ''} en ${R.entidad(d)}.`);
      h.push(`Requiere ${R.opcionTexto(cd('pet_icbf', 'tramite'), d.tramite)}.`);
      return h;
    },
    normas: ['cp44', 'cp42', 'cp23', 'l1755_14', 'l1755_20'],
    fundamentos: d => ['Conforme a los artículos 22, 23, 52 y 96 a 103 de la Ley 1098 de 2006 (modificados por la Ley 1878 de 2018), los niños tienen derecho a tener una familia y a no ser separados de ella, y los procesos administrativos de restablecimiento de derechos deben garantizar la participación de la familia, resolverse dentro de los seis (6) meses siguientes al conocimiento de la presunta amenaza o vulneración (término improrrogable cuyo vencimiento hace perder la competencia a la autoridad administrativa, que debe remitir el expediente al juez de familia, artículo 100) y notificarse a los interesados, quienes pueden recurrir las decisiones. El interés superior del menor y la prevalencia de sus derechos (artículo 44 de la Constitución) obligan a las autoridades a actuar con celeridad.'],
    peticiones: [
      { v: 'informar', inicial: true, t: 'Que me informen el estado del proceso y las decisiones', legal: 'Informar por escrito el estado del proceso, las medidas adoptadas, sus fundamentos y las actuaciones pendientes, y notificarme en adelante las decisiones.' },
      { v: 'cita', t: 'Que me citen a audiencia o conciliación', legal: 'Citar a audiencia o diligencia de conciliación en la fecha más próxima posible, informándome el día, la hora y los documentos que debo aportar.' },
      { v: 'visitas', t: 'Que autoricen las visitas al niño', legal: 'Autorizar y regular las visitas y el contacto con el menor, salvo que exista una razón grave y motivada para restringirlas.' },
      { v: 'copias', t: 'Que me entreguen copia del expediente', legal: 'Expedir copia del expediente y de las resoluciones o autos proferidos.' },
      { v: 'verificar', t: 'Que verifiquen la situación del niño y actúen', legal: 'Realizar la verificación de garantía de derechos del menor y adoptar las medidas de protección que correspondan.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de mi cédula' }, { v: 'registro', t: 'Registro civil del menor' }, { v: 'pruebas', t: 'Pruebas de la relación y del cuidado (fotos, constancias, testigos)' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, siNoResponden: 'Tutela invocando los derechos del menor (prevalecen sobre los demás). También puedes acudir a la Procuraduría de Familia o a la Personería.' }
  },

  /* ---------------- ARRENDADOR / PARTICULAR ---------------- */
  {
    id: 'pet_arrendador', tipo: 'peticion', categoria: 'particular',
    tituloDoc: 'RECLAMACIÓN Y REQUERIMIENTO',
    titulo: 'Reclamación al arrendador o arrendatario (depósito, reparaciones, servicios cortados, entrega del inmueble)',
    resumen: 'Pedir por escrito a un arrendador que repare daños, devuelva un depósito, reconecte servicios o deje de hostigarte; o al inquilino que pague o entregue.',
    palabras: ['arriendo', 'arrendador', 'arrendatario', 'inquilino', 'casa', 'apartamento', 'depósito', 'reparaciones', 'humedad', 'servicios', 'desalojo', 'contrato de arrendamiento', 'canon', 'devolución'],
    destinatario: { categoria: 'particular', ejemploNombre: 'Ej.: Señor Carlos Restrepo (arrendador) / Inmobiliaria Su Casa S.A.S.', cargo: 'Arrendador(a) / Representante legal de la inmobiliaria' },
    campos: [
      { id: 'rol', tipo: 'select', etiqueta: '¿Tú eres…?', opciones: [ { v: 'arrendatario', t: 'Arrendatario(a) (vivo en arriendo)', legal: 'arrendatari{o}' }, { v: 'arrendador', t: 'Arrendador(a) (soy el dueño)', legal: 'arrendador{a}' } ], valorInicial: 'arrendatario', ancho: 'media' },
      { id: 'inmueble', tipo: 'texto', etiqueta: 'Dirección del inmueble', requerido: true, ancho: 'media' },
      { id: 'canon', tipo: 'texto', etiqueta: 'Valor del arriendo mensual', ejemplo: 'Ej.: 950.000', ancho: 'media' },
      { id: 'fechaInicio', tipo: 'fecha', etiqueta: 'Fecha de inicio del contrato', ancho: 'media' },
      { id: 'problema', tipo: 'checks', etiqueta: '¿Qué está pasando?', requerido: true, opciones: [
        { v: 'reparaciones', t: 'No hacen reparaciones necesarias (humedad, techo, tuberías, eléctrico)', legal: 'la falta de reparaciones necesarias que afectan la habitabilidad' },
        { v: 'deposito', t: 'No me devuelven el depósito o me cobraron uno ilegal', legal: 'la retención o exigencia de un depósito prohibido por la ley' },
        { v: 'servicios', t: 'Me cortaron los servicios o cambiaron la cerradura para presionarme', legal: 'el corte de servicios públicos o la obstrucción del acceso como medida de presión' },
        { v: 'aumento', t: 'Aumentaron el arriendo por encima de lo legal', legal: 'un incremento del canon superior al permitido' },
        { v: 'hostigamiento', t: 'Me hostigan, amenazan o entran sin permiso', legal: 'actos de hostigamiento, amenazas o ingreso no autorizado al inmueble' },
        { v: 'pago', t: 'El inquilino no paga el arriendo o los servicios', legal: 'el incumplimiento en el pago del canon o de los servicios públicos' },
        { v: 'entrega', t: 'Entrega o recibo del inmueble (inventario, daños)', legal: 'la entrega y recibo del inmueble con su inventario' }
      ] },
      { id: 'valor', tipo: 'texto', etiqueta: 'Valor en discusión (depósito, deuda, reparación)', ancho: 'media' },
      C.relato({ ejemplo: 'Ej.:\nDesde junio el techo de la habitación gotea y la pared tiene humedad.\nLe he avisado al arrendador por WhatsApp cuatro veces.\nMi hijo de 3 años se ha enfermado de los bronquios.' })
    ],
    asunto: d => `Reclamación – Contrato de arrendamiento del inmueble ${d.inmueble || ''}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} es ${R.opcionTexto(cd('pet_arrendador', 'rol'), d.rol).replace('{o}', a.o).replace('{a}', a.g === 'f' ? 'a' : '')} del inmueble ubicado en ${d.inmueble || '[dirección]'}${d.fechaInicio ? `, en virtud de contrato de arrendamiento vigente desde ${R.fechaLarga(d.fechaInicio)}` : ''}${d.canon ? `, con un canon mensual de ${R.moneda(d.canon) || d.canon}` : ''}.`);
      h.push(`Se presenta ${R.lista((d.problema || []).map(v => R.opcionTexto(cd('pet_arrendador', 'problema'), v)))}${R.moneda(d.valor) ? `, con un valor en discusión de ${R.moneda(d.valor)}` : ''}.`);
      return h;
    },
    normas: ['cp51', 'cp83', 'l820', 'cp23', 'l1755_32'],
    fundamentos: d => {
      const f = ['Conforme al artículo 2 de la Ley 820 de 2003 y a los artículos 1973 y siguientes del Código Civil, el contrato de arrendamiento obliga a las partes a cumplir de buena fe: el arrendador debe entregar y mantener el inmueble en estado de servir, y el arrendatario debe pagar el precio y cuidar la cosa. Este escrito constituye además requerimiento para la constitución en mora (artículo 1608 del Código Civil) y prueba de la reclamación previa; de persistir el incumplimiento se acudirá a la conciliación extrajudicial (Ley 2220 de 2022) y a las acciones judiciales y policivas que correspondan.'];
      if ((d.problema || []).includes('aumento')) f.push('El artículo 20 de la Ley 820 de 2003 limita el incremento anual del canon de vivienda urbana a un porcentaje que no puede superar el 100 % del incremento del índice de precios al consumidor (IPC) del año anterior, y solo cada doce meses.');
      if ((d.problema || []).includes('servicios') || (d.problema || []).includes('hostigamiento')) f.push('El Código Nacional de Seguridad y Convivencia Ciudadana (Ley 1801 de 2016, artículos 77 y siguientes) y el Código General del Proceso (artículo 384) establecen que el arrendador solo puede obtener la restitución del inmueble mediante proceso judicial; las vías de hecho (corte de servicios, cambio de guardas, ingreso sin autorización) constituyen perturbación de la tenencia, sancionable por el inspector de policía, y pueden configurar el delito de constreñimiento ilegal.');
      return f;
    },
    peticiones: [
      { v: 'cumplir', inicial: true, t: 'Que cumplan sus obligaciones en un plazo corto', legal: d => `Cumplir dentro de los diez (10) días siguientes las obligaciones derivadas del contrato en relación con ${R.lista((d.problema || []).map(v => R.opcionTexto(cd('pet_arrendador', 'problema'), v))) || 'lo descrito'}.` },
      { v: 'reparar', t: 'Que hagan las reparaciones', legal: 'Realizar las reparaciones necesarias para la habitabilidad del inmueble, informando fecha de inicio, o autorizar que las haga el arrendatario con cargo al canon conforme al artículo 1993 del Código Civil.' },
      { v: 'devolver', t: 'Que devuelvan el depósito o lo cobrado de más', legal: 'Devolver el depósito exigido en contravención del artículo 16 de la Ley 820 de 2003 o las sumas cobradas en exceso.' },
      { v: 'cesar', t: 'Que cesen los cortes, cambios de cerradura o el hostigamiento', legal: 'Cesar de inmediato las vías de hecho (corte de servicios, cambio de guardas, ingreso no autorizado, amenazas), restablecer los servicios y respetar la tenencia pacífica del inmueble.' },
      { v: 'pagar', t: 'Que paguen lo adeudado o entreguen el inmueble', legal: 'Pagar los cánones y servicios adeudados o, en su defecto, hacer entrega del inmueble con inventario, so pena de iniciar el proceso de restitución.' },
      { v: 'acta', t: 'Que firmemos un acta de entrega con inventario', legal: 'Acordar fecha para la entrega del inmueble con acta de inventario y estado, y expedir el paz y salvo correspondiente.' }
    ],
    anexos: [ { v: 'contrato', t: 'Copia del contrato de arrendamiento' }, { v: 'pagos', t: 'Recibos de pago del arriendo y depósito' }, { v: 'fotos', t: 'Fotos de los daños o de los servicios cortados' }, { v: 'chats', t: 'Mensajes o correos cruzados' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Como es un particular, el plazo de 15 días aplica si hay subordinación o indefensión (lo habitual en arriendo). Este escrito sirve como requerimiento previo y prueba.', siNoResponden: 'Conciliación en una Casa de Justicia o centro de conciliación (Ley 2220 de 2022; gratis en consultorios jurídicos); querella ante la Inspección de Policía si hay vías de hecho; demanda ante el juez civil. Si cortaron servicios y hay niños o personas enfermas, puede proceder la tutela.' }
  },

  /* ---------------- PROSPERIDAD SOCIAL: SUBSIDIOS ---------------- */
  {
    id: 'pet_prosperidad', tipo: 'peticion', categoria: 'nacional',
    titulo: 'Petición a Prosperidad Social por un subsidio (Renta Ciudadana, Colombia Mayor, Familias en Acción)',
    resumen: 'Te sacaron del programa, suspendieron el pago, no te ha llegado el giro o no te han dicho si quedaste inscrito. Pide por escrito que te expliquen y te reintegren.',
    palabras: ['subsidio', 'Prosperidad Social', 'DPS', 'Renta Ciudadana', 'Colombia Mayor', 'Familias en Acción', 'Jóvenes en Acción', 'giro', 'me quitaron el subsidio', 'suspendieron', 'programa', 'enlace'],
    destinatario: { categoria: 'nacional', nombre: 'Prosperidad Social (Departamento Administrativo para la Prosperidad Social)', cargo: 'Dirección de Transferencias Monetarias / Oficina de atención al ciudadano' },
    campos: [
      { id: 'programa', tipo: 'select', etiqueta: '¿De qué programa se trata?', requerido: true, opciones: [
        { v: 'renta', t: 'Renta Ciudadana (antes Ingreso Solidario / Familias en Acción)', legal: 'el programa Renta Ciudadana' },
        { v: 'mayor', t: 'Colombia Mayor (subsidio para personas mayores)', legal: 'el programa Colombia Mayor' },
        { v: 'jovenes', t: 'Jóvenes en Acción', legal: 'el programa Jóvenes en Acción' },
        { v: 'iva', t: 'Devolución del IVA', legal: 'el programa de Devolución del IVA' },
        { v: 'otro', t: 'Otro subsidio o programa social', legal: 'el programa social que se describe en los hechos' }
      ], ancho: 'completa' },
      { id: 'problema', tipo: 'select', etiqueta: '¿Qué pasó?', requerido: true, opciones: [
        { v: 'retiro', t: 'Me sacaron o suspendieron del programa sin explicación', legal: 'el retiro o la suspensión del hogar del programa sin notificación ni explicación' },
        { v: 'giro', t: 'No me ha llegado el giro o pago', legal: 'la falta de pago de los giros causados' },
        { v: 'inscripcion', t: 'Me inscribí y no me dicen si quedé', legal: 'la ausencia de respuesta sobre la inscripción o focalización del hogar' },
        { v: 'datos', t: 'Mis datos están mal (documento, hijos, municipio, banco)', legal: 'la corrección de los datos del hogar en el sistema del programa' },
        { v: 'cobro', t: 'Me cobran o me piden devolver dinero', legal: 'el cobro o la solicitud de devolución de dineros del programa' }
      ], ancho: 'completa' },
      { id: 'fechaUltimoPago', tipo: 'fecha', etiqueta: 'Fecha del último pago recibido (si aplica)', ancho: 'media' },
      { id: 'valorGiro', tipo: 'texto', etiqueta: 'Valor del giro o subsidio', ejemplo: 'Ej.: 80.000 cada dos meses', ancho: 'media' },
      { id: 'hogar', tipo: 'texto', etiqueta: 'Personas del hogar (número, edades, condiciones)', ejemplo: 'Ej.: 4 personas: yo (34), mi madre (72) y dos niños de 5 y 9 años', ancho: 'completa' },
      { id: 'situacion', tipo: 'textarea', etiqueta: '¿Cómo afecta a tu hogar quedarse sin el subsidio?', requerido: true, filas: 2 },
      ...C.previo({ etiqueta: '¿Ya reclamaste a Prosperidad Social o al enlace municipal?' }),
      C.relato({ requerido: false, etiqueta: '¿Algo más que debamos contar? (opcional)' })
    ],
    asunto: d => `Derecho de petición – ${R.capital(R.opcionTexto(cd('pet_prosperidad', 'problema'), d.problema))} – ${R.opcionTexto(cd('pet_prosperidad', 'programa'), d.programa)}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} ${d.problema === 'inscripcion' ? 'se inscribió en' : 'es beneficiari' + a.o + ' de'} ${R.opcionTexto(cd('pet_prosperidad', 'programa'), d.programa)}${d.valorGiro ? `, con un subsidio de ${d.valorGiro}` : ''}${d.fechaUltimoPago ? `, cuyo último pago recibió el ${R.fechaLarga(d.fechaUltimoPago)}` : ''}.`);
      if (d.hogar) h.push(`Su hogar está conformado por ${d.hogar}.`);
      h.push(`Se presenta la siguiente situación: ${R.opcionTexto(cd('pet_prosperidad', 'problema'), d.problema)}.`);
      h.push(`El subsidio es esencial para la subsistencia del hogar: ${R.oracion(d.situacion)}`);
      h.push(...R.hechosPrevio(d, 'la solución de esta situación'));
      return h;
    },
    normas: ['cp13', 'cp23', 'cp29', 'l1755_14', 'l1755_20', 'l1437_66', 'l1437_74'],
    fundamentos: d => ['La Ley 2294 de 2023 (Plan Nacional de Desarrollo) y los manuales operativos de los programas de transferencias monetarias de Prosperidad Social establecen que las novedades, suspensiones y retiros de hogares deben estar motivados, comunicarse al beneficiario y admitir reclamación. Conforme a la jurisprudencia constitucional (entre otras, sentencias T-025 de 2004 y T-149 de 2019), los subsidios dirigidos a población vulnerable son parte de la garantía del mínimo vital y no pueden retirarse sin un procedimiento que respete el debido proceso.'],
    peticiones: [
      { v: 'explicar', inicial: true, t: 'Que me expliquen por escrito la razón del retiro, la suspensión o el no pago', legal: 'Informar por escrito, de manera clara y completa, la razón exacta del retiro, la suspensión o la falta de pago, la fecha y el acto en que se decidió, y la fuente de la información utilizada (cruce de bases de datos, Sisbén, etc.).' },
      { v: 'reintegrar', inicial: d => ['retiro', 'cobro'].includes(d.problema), t: 'Que me reintegren al programa y paguen lo que dejaron de girar', legal: 'Revocar la suspensión o el retiro, reintegrar al hogar al programa y pagar los giros dejados de cancelar desde la fecha de la suspensión.' },
      { v: 'pagar', inicial: d => d.problema === 'giro', t: 'Que paguen el giro pendiente y me digan dónde y cuándo cobrar', legal: 'Realizar el pago de los giros causados y pendientes, informando el medio, la fecha y el lugar de cobro.' },
      { v: 'estado', inicial: d => d.problema === 'inscripcion', t: 'Que me digan si quedé inscrito y, si no, por qué', legal: 'Informar el estado de la inscripción o focalización del hogar, los criterios aplicados y, en caso de no selección, las razones y la forma de reclamar.' },
      { v: 'corregir', inicial: d => d.problema === 'datos', t: 'Que corrijan mis datos', legal: 'Corregir los datos del hogar en el sistema del programa conforme a los documentos anexos.' },
      { v: 'recursos', inicial: true, t: 'Si la decisión fue mediante resolución, que me la entreguen y me informen los recursos', legal: 'Entregar copia del acto administrativo que adoptó la decisión, con su constancia de notificación, e indicar los recursos que proceden y su término, o, de no existir acto notificado, tener esta petición como reclamación oportuna.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'sisben', t: 'Consulta del Sisbén' }, { v: 'pagos', t: 'Comprobantes de giros anteriores' }, { v: 'registros', t: 'Registros civiles de los niños o cédula del adulto mayor' }, { v: 'mensajes', t: 'Mensajes o pantallazos de la app o del enlace municipal' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Puedes radicarla en www.prosperidadsocial.gov.co (PQRS), en el enlace municipal del programa (alcaldía) o en la Personería. Si te sacaron mediante resolución y te la notificaron hace menos de 10 días hábiles, usa además el "Recurso contra una decisión".', siNoResponden: 'Sin respuesta en 15 días hábiles: tutela por derecho de petición. Si el retiro fue sin notificación ni oportunidad de defensa y afecta tu sustento: "Tutela por violación del debido proceso".' }
  },

  /* ---------------- PETICIÓN GENERAL ---------------- */
  {
    id: 'pet_general', tipo: 'peticion', categoria: 'municipio',
    titulo: 'Derecho de petición general (cualquier entidad, cualquier asunto)',
    resumen: 'Plantilla libre para cualquier solicitud, queja, reclamo o consulta a una entidad pública o privada. Tú describes el problema y lo que pides; el documento pone el lenguaje legal.',
    palabras: ['petición', 'general', 'otro', 'cualquier', 'solicitud', 'reclamo', 'consulta', 'queja', 'entidad'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Nombre de la entidad' },
    campos: [
      { id: 'modalidad', tipo: 'select', etiqueta: '¿Qué tipo de petición es?', requerido: true, opciones: [
        { v: 'interes_particular', t: 'Pedir algo para mí (un derecho, un servicio, una decisión)', legal: 'petición de interés particular' },
        { v: 'interes_general', t: 'Pedir algo para la comunidad', legal: 'petición de interés general' },
        { v: 'informacion', t: 'Pedir información o documentos', legal: 'petición de información y documentos' },
        { v: 'consulta', t: 'Hacer una consulta (que me expliquen cómo funciona algo)', legal: 'consulta' },
        { v: 'queja', t: 'Presentar una queja o reclamo', legal: 'queja o reclamo' }
      ], ancho: 'completa' },
      { id: 'tema', tipo: 'texto', etiqueta: 'Resume el tema en una frase', ejemplo: 'Ej.: Devolución de un pago doble en el impuesto de industria y comercio', requerido: true, ancho: 'completa' },
      ...C.previo(),
      C.relato(),
      { id: 'pide', tipo: 'textarea', etiqueta: '¿Qué quieres exactamente que la entidad haga? (una petición por línea)', ejemplo: 'Ej.:\nQue me devuelvan el pago doble de 320.000 pesos.\nQue me expliquen por qué se generó el cobro dos veces.', requerido: true, filas: 4 }
    ],
    asunto: d => `Derecho de petición (${R.opcionTexto(cd('pet_general', 'modalidad'), d.modalidad)}) – ${d.tema || ''}`,
    hechos: d => R.hechosPrevio(d, 'lo que aquí se solicita'),
    normas: ['cp23', 'l1755_13', 'l1755_14', 'l1755_16', 'l1755_32', 't377'],
    fundamentos: d => d.modalidad === 'informacion' ? [AJ.normas.l1712_25.texto + ` (${AJ.normas.l1712_25.cita}).`] : [],
    peticiones: [
      { v: 'propias', inicial: true, fijo: true, t: 'Mis peticiones (las que escribiste arriba)', legal: d => R.relatoAHechos(d.pide) },
      { v: 'plazo', inicial: true, t: 'Que respondan de fondo dentro del plazo legal', legal: 'Resolver de fondo, de manera clara, completa y congruente, dentro del término legal, y notificarme la respuesta en la dirección y el correo indicados.' },
      { v: 'motivar', t: 'Si niegan algo, que expliquen las razones y las normas', legal: 'En caso de respuesta negativa, exponer de manera motivada las razones de hecho y de derecho e indicar los recursos que proceden.' },
      { v: 'competente', t: 'Si no son competentes, que remitan a quien sí lo sea', legal: 'Si la entidad no es competente, remitir la petición a la autoridad competente dentro de los cinco (5) días siguientes e informármelo.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'soportes', t: 'Documentos que prueban lo que cuento' }, { v: 'radicados', t: 'Copia de solicitudes anteriores' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Información y documentos: 10 días hábiles. Consultas: 30 días hábiles.', siNoResponden: 'Tutela por violación del derecho de petición (en esta plataforma).' }
  }
  );
})();
