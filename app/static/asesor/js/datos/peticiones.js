/* ============================================================
   peticiones.js — Casos de DERECHO DE PETICIÓN (parte 1):
   municipio / alcaldía y salud.
   ============================================================ */
window.AJ = window.AJ || {};
AJ.casos = AJ.casos || [];

(function () {
  const R = AJ.red;
  const C = AJ.campos;

  AJ.casos.push(
  /* ---------------- MUNICIPIO: PLANEACIÓN ---------------- */
  {
    id: 'pet_municipio_planeacion', tipo: 'peticion', categoria: 'municipio',
    titulo: 'Petición a la Secretaría de Planeación del municipio',
    resumen: 'Licencias, uso del suelo, certificado de estratificación, nomenclatura, POT, información sobre una obra o un predio.',
    palabras: ['planeación', 'licencia', 'construcción', 'uso del suelo', 'estrato', 'nomenclatura', 'POT', 'predio', 'obra', 'alcaldía', 'municipio', 'curaduría'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Alcaldía Municipal de La Ceja', cargo: 'Secretaría de Planeación', ejemploCargo: 'Ej.: Secretario(a) de Planeación' },
    campos: [
      { id: 'tramite', tipo: 'select', etiqueta: '¿Sobre qué necesitas que Planeación actúe o te informe?', requerido: true, opciones: [
        { v: 'licencia', t: 'Una licencia de construcción, ampliación o reforma', legal: 'la licencia urbanística' },
        { v: 'uso_suelo', t: 'El uso del suelo permitido en un predio (certificado o concepto)', legal: 'el concepto o certificado de uso del suelo' },
        { v: 'estrato', t: 'El estrato de mi vivienda (certificado o revisión)', legal: 'la certificación o revisión de la estratificación socioeconómica' },
        { v: 'nomenclatura', t: 'La nomenclatura o dirección oficial de un predio', legal: 'la asignación o certificación de nomenclatura' },
        { v: 'pot', t: 'Información del Plan de Ordenamiento Territorial (POT) sobre una zona', legal: 'la información sobre las normas del Plan de Ordenamiento Territorial aplicables' },
        { v: 'obra', t: 'Información o intervención sobre una obra (pública o de un vecino)', legal: 'la información y la intervención de la autoridad frente a una obra' },
        { v: 'riesgo', t: 'Un concepto de riesgo (inundación, deslizamiento) sobre mi predio', legal: 'el concepto técnico sobre la condición de riesgo del predio' },
        { v: 'otro', t: 'Otro asunto de Planeación', legal: 'el asunto que se describe en los hechos' }
      ] },
      { id: 'predio', tipo: 'texto', etiqueta: 'Dirección o identificación del predio o lugar', ejemplo: 'Ej.: Carrera 20 # 15-30, barrio San José; matrícula inmobiliaria 020-12345', ancho: 'completa' },
      { id: 'calidad', tipo: 'select', etiqueta: '¿Qué relación tienes con el predio?', opciones: [
        { v: 'propietario', t: 'Soy propietario(a)', legal: 'propietari{o} del inmueble' }, { v: 'poseedor', t: 'Vivo allí / lo poseo sin escritura', legal: 'poseedor{o} del inmueble' },
        { v: 'arrendatario', t: 'Soy arrendatario(a)', legal: 'arrendatari{o} del inmueble' }, { v: 'vecino', t: 'Soy vecino(a) afectado(a)', legal: 'vecin{o} directamente afectad{o} por el predio' }, { v: 'ciudadano', t: 'Ciudadano(a) interesado(a)', legal: 'ciudadan{o} interesad{o} en el predio' }
      ], valorInicial: 'propietario', ancho: 'media' },
      ...C.previo(),
      C.relato({ ejemplo: 'Ej.:\nEl 10 de febrero de 2026 radiqué los planos y documentos para la licencia de ampliación de mi casa.\nHan pasado tres meses y no me han dado respuesta ni me han pedido documentos adicionales.\nNecesito la licencia para iniciar la obra antes del invierno.' })
    ],
    asunto: d => `Derecho de petición – ${R.capital(R.opcionTexto(camposDe('pet_municipio_planeacion', 'tramite'), d.tramite))}${d.predio ? ` (${d.predio})` : ''}`,
    hechos: d => {
      const a = R.actor(d);
      const cal = R.opcionTexto(camposDe('pet_municipio_planeacion', 'calidad'), d.calidad).replace(/\{o\}/g, a.o);
      const h = [];
      if (d.predio) h.push(`${a.Nom} actúa en calidad de ${cal} ubicado en ${d.predio}, en jurisdicción de ${d.entidadCiudad || 'este municipio'}.`);
      h.push(...R.hechosPrevio(d, R.opcionTexto(camposDe('pet_municipio_planeacion', 'tramite'), d.tramite)));
      return h;
    },
    normas: ['cp23', 'l1755_13', 'l1755_14', 'l1755_16', 'l136', 'cp209'],
    fundamentos: d => {
      const f = [];
      if (d.tramite === 'licencia') f.push(AJ.normas.l388.texto + ` (${AJ.normas.l388.cita}).`);
      if (d.tramite === 'estrato') f.push(AJ.normas.l142_104.texto + ` (${AJ.normas.l142_104.cita}).`);
      if (['uso_suelo', 'pot', 'nomenclatura', 'riesgo', 'obra'].includes(d.tramite)) f.push(AJ.normas.l1712_25.texto + ` (${AJ.normas.l1712_25.cita}).`);
      return f;
    },
    peticiones: [
      { v: 'resolver', inicial: true, t: 'Que resuelvan de fondo mi solicitud dentro del plazo legal', legal: d => d.tramite === 'licencia' ? 'Resolver de fondo la solicitud de licencia urbanística dentro del término de cuarenta y cinco (45) días hábiles previsto en el artículo 99 de la Ley 388 de 1997 y, si dicho término ya venció sin pronunciamiento, reconocer el silencio administrativo positivo previsto en el numeral 3 del mismo artículo, expidiendo el acto que lo declare.' : `Resolver de fondo, de manera clara, completa y congruente, lo relativo a ${R.opcionTexto(camposDe('pet_municipio_planeacion', 'tramite'), d.tramite)} descrita en los hechos, dentro del término legal de quince (15) días hábiles.` },
      { v: 'estado', t: 'Que me informen en qué estado está el trámite y qué falta', legal: 'Informar el estado actual del trámite, el funcionario responsable, los requisitos o documentos que eventualmente falten y la fecha estimada de decisión.' },
      { v: 'copias', t: 'Que me entreguen copia de los documentos, conceptos o normas que apliquen', legal: 'Expedir y entregar copia de los documentos, conceptos técnicos, actos administrativos y normas urbanísticas aplicables al predio o al asunto descrito.' },
      { v: 'visita', t: 'Que hagan una visita técnica al lugar', legal: 'Ordenar y practicar una visita técnica al predio o lugar descrito, con participación del peticionario, y comunicar sus resultados por escrito.' },
      { v: 'medidas', t: 'Que tomen medidas frente a una obra irregular o un riesgo', legal: 'Adoptar las medidas administrativas y de policía que correspondan frente a la situación descrita (obra sin licencia, invasión del espacio público, condición de riesgo), e informar las actuaciones adelantadas.' },
      { v: 'competente', t: 'Si no son los competentes, que remitan mi petición a quien sí lo sea', legal: 'En caso de no ser la dependencia competente, remitir la petición a la autoridad competente dentro de los cinco (5) días siguientes e informármelo, conforme al artículo 21 de la Ley 1437 de 2011.' }
    ],
    anexos: [
      { v: 'cedula', t: 'Copia de mi cédula' }, { v: 'escritura', t: 'Copia de la escritura, certificado de libertad o recibo del predial' },
      { v: 'radicado', t: 'Copia del radicado o solicitud anterior' }, { v: 'fotos', t: 'Fotografías del predio, la obra o el problema' }, { v: 'planos', t: 'Planos o documentos técnicos' }
    ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Si pides solo copias o información, el plazo es de 10 días hábiles. Para licencias urbanísticas la autoridad tiene 45 días hábiles desde la radicación completa.', siNoResponden: 'Si pasan los 15 días hábiles sin respuesta de fondo, puedes presentar una acción de tutela por violación del derecho de petición (en esta plataforma: "Tutela porque no respondieron mi derecho de petición").' }
  },

  /* ---------------- MUNICIPIO: SERVICIOS Y OBRAS (INTERÉS GENERAL) ---------------- */
  {
    id: 'pet_municipio_servicios', tipo: 'peticion', categoria: 'municipio',
    titulo: 'Petición a la Alcaldía por problemas del barrio o la vereda',
    resumen: 'Vías dañadas, alumbrado, basuras, alcantarillado, parques, seguridad, árboles en riesgo, obras inconclusas. Puede presentarse en nombre de la comunidad.',
    palabras: ['hueco', 'vía', 'carretera', 'alumbrado', 'basura', 'alcantarillado', 'parque', 'árbol', 'comunidad', 'barrio', 'vereda', 'obra', 'inundación', 'seguridad', 'alcaldía'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Alcaldía Municipal de Sabaneta', cargo: 'Despacho del Alcalde – Secretaría de Infraestructura', ejemploCargo: 'Ej.: Secretaría de Infraestructura / Secretaría de Gobierno' },
    campos: [
      { id: 'problema', tipo: 'select', etiqueta: '¿Cuál es el problema principal?', requerido: true, opciones: [
        { v: 'vias', t: 'Vías, andenes o puentes en mal estado', legal: 'el deterioro de la malla vial, los andenes o puentes' },
        { v: 'alumbrado', t: 'Alumbrado público dañado o inexistente', legal: 'la falta o el mal estado del alumbrado público' },
        { v: 'basuras', t: 'Basuras, escombros o puntos críticos de residuos', legal: 'la acumulación de residuos sólidos y la deficiente recolección' },
        { v: 'alcantarillado', t: 'Alcantarillado, aguas residuales o inundaciones', legal: 'las fallas del sistema de alcantarillado y el manejo de aguas lluvias y residuales' },
        { v: 'parques', t: 'Parques, zonas verdes o escenarios deportivos abandonados', legal: 'el abandono de parques, zonas verdes o escenarios deportivos' },
        { v: 'arboles', t: 'Árboles en riesgo de caída o poda necesaria', legal: 'el riesgo generado por árboles que requieren poda o tala técnica' },
        { v: 'seguridad', t: 'Inseguridad, falta de presencia policial o cámaras', legal: 'las condiciones de inseguridad del sector' },
        { v: 'obra', t: 'Una obra pública inconclusa o mal hecha', legal: 'la ejecución deficiente o la paralización de una obra pública' },
        { v: 'otro', t: 'Otro problema comunitario', legal: 'la problemática comunitaria descrita en los hechos' }
      ] },
      { id: 'lugar', tipo: 'texto', etiqueta: '¿Dónde exactamente? (barrio, vereda, dirección o punto de referencia)', ejemplo: 'Ej.: Calle 45 entre carreras 30 y 32, barrio La Floresta, frente a la escuela', requerido: true, ancho: 'completa' },
      { id: 'afectados', tipo: 'texto', etiqueta: '¿A cuántas personas o familias afecta? (aproximado)', ejemplo: 'Ej.: unas 80 familias y los niños de la escuela', ancho: 'media' },
      { id: 'tiempo', tipo: 'texto', etiqueta: '¿Desde cuándo existe el problema?', ejemplo: 'Ej.: desde el invierno de 2025', ancho: 'media' },
      { id: 'comunidad', tipo: 'radio', etiqueta: '¿Lo presentas en nombre de la comunidad?', opciones: [ { v: 'no', t: 'No, solo en mi nombre' }, { v: 'si', t: 'Sí, en nombre de la comunidad (puedes anexar firmas)' } ], valorInicial: 'no' },
      ...C.previo({ etiqueta: '¿Ya habían pedido antes a la alcaldía que solucionara esto?' }),
      C.relato({ ejemplo: 'Ej.:\nLa vía principal de la vereda tiene huecos de más de medio metro desde el invierno pasado.\nEl bus escolar ya no sube y los niños deben caminar 2 kilómetros.\nEn julio se accidentó una motocicleta por el estado de la vía.' })
    ],
    asunto: d => `Derecho de petición de interés general – ${R.opcionTexto(camposDe('pet_municipio_servicios', 'problema'), d.problema)} en ${d.lugar || 'el sector'}`,
    hechos: d => {
      const h = [];
      h.push(`En ${d.lugar || 'el sector descrito'}, jurisdicción de ${d.entidadCiudad || 'este municipio'}, se presenta ${R.opcionTexto(camposDe('pet_municipio_servicios', 'problema'), d.problema)}${d.tiempo ? `, situación que persiste ${/^desde/i.test(d.tiempo) ? d.tiempo : 'desde ' + d.tiempo}` : ''}.`);
      if (d.afectados) h.push(`La situación afecta directamente a ${d.afectados}, y compromete la seguridad, la salubridad y la calidad de vida de los habitantes del sector.`);
      if (d.comunidad === 'si') h.push('Esta petición se presenta en nombre de la comunidad afectada, en ejercicio del derecho de petición por motivos de interés general, y se acompaña de las firmas de los vecinos que la respaldan.');
      h.push(...R.hechosPrevio(d, 'la solución de esta problemática'));
      return h;
    },
    normas: ['cp23', 'cp2', 'l1755_13', 'l1755_14', 'l136', 'cp365', 'cp209'],
    fundamentos: d => {
      const f = ['El artículo 311 de la Constitución Política asigna al municipio, como entidad fundamental de la división político-administrativa, la prestación de los servicios públicos que determine la ley, la construcción de las obras que demande el progreso local y el ordenamiento del desarrollo de su territorio. Estas competencias son obligaciones exigibles por los ciudadanos, no simples facultades discrecionales.'];
      if (d.problema === 'basuras' || d.problema === 'alcantarillado') f.push('Conforme a los artículos 5 y 6 de la Ley 142 de 1994, es competencia de los municipios asegurar la prestación eficiente de los servicios de acueducto, alcantarillado y aseo, directamente o a través de empresas, y la Ley 9 de 1979 (Código Sanitario) les impone velar por las condiciones de salubridad pública.');
      if (d.problema === 'arboles' || d.problema === 'alcantarillado') f.push('La Ley 1523 de 2012 (gestión del riesgo de desastres) obliga a las autoridades municipales a identificar, reducir y manejar los riesgos que amenacen a la población, y a adoptar medidas preventivas oportunas.');
      return f;
    },
    peticiones: [
      { v: 'solucionar', inicial: true, t: 'Que solucionen el problema y me digan en qué fecha lo harán', legal: d => `Adoptar las medidas necesarias para solucionar ${R.opcionTexto(camposDe('pet_municipio_servicios', 'problema'), d.problema)} en ${d.lugar || 'el sector descrito'}, e informar por escrito el cronograma, el presupuesto asignado y la dependencia responsable.` },
      { v: 'visita', inicial: true, t: 'Que visiten el lugar para verificar el problema', legal: 'Realizar una visita técnica al lugar, con participación de la comunidad, para verificar la situación y levantar un informe que se me entregue en copia.' },
      { v: 'plan', t: 'Que me informen si el arreglo está incluido en el plan de desarrollo o el presupuesto', legal: 'Informar si la intervención requerida está incluida en el Plan de Desarrollo Municipal, el plan de acción o el presupuesto de la vigencia, indicando el rubro y el monto, y en caso negativo, las razones y la fecha en que será incluida.' },
      { v: 'medidas_urgentes', t: 'Que mientras tanto tomen medidas urgentes para evitar accidentes', legal: 'Adoptar de inmediato medidas provisionales de mitigación (señalización, cerramiento, limpieza, poda, reparcheo) para evitar accidentes o daños mientras se ejecuta la solución definitiva.' },
      { v: 'competente', t: 'Si no son los competentes, que remitan mi petición a quien sí lo sea', legal: 'En caso de que la competencia corresponda a otra entidad (empresa de servicios públicos, departamento o nación), remitir la petición dentro de los cinco (5) días siguientes e informármelo, conforme al artículo 21 de la Ley 1437 de 2011.' }
    ],
    anexos: [ { v: 'fotos', t: 'Fotografías o videos del problema' }, { v: 'firmas', t: 'Listado de firmas de la comunidad' }, { v: 'radicado', t: 'Copia de solicitudes anteriores' }, { v: 'prensa', t: 'Noticias, denuncias o informes previos' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, siNoResponden: 'Sin respuesta en 15 días hábiles, procede la tutela por violación del derecho de petición. Si el problema afecta derechos colectivos (salubridad, espacio público, seguridad), también puede presentarse una acción popular (artículo 88 de la Constitución, Ley 472 de 1998), para la cual puedes pedir ayuda a la Personería.' }
  },

  /* ---------------- MUNICIPIO: SISBÉN ---------------- */
  {
    id: 'pet_municipio_sisben', tipo: 'peticion', categoria: 'municipio',
    titulo: 'Petición a la oficina del Sisbén (encuesta, actualización o corrección)',
    resumen: 'Pedir la encuesta Sisbén, actualizarla porque cambió tu situación, corregir datos o pedir que te expliquen tu grupo.',
    palabras: ['sisbén', 'sisben', 'encuesta', 'puntaje', 'grupo', 'subsidio', 'actualizar', 'visita', 'ficha'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Alcaldía de Itagüí', cargo: 'Oficina del Sisbén – Secretaría de Planeación', ejemploCargo: 'Ej.: Administrador(a) municipal del Sisbén' },
    campos: [
      { id: 'tramite', tipo: 'select', etiqueta: '¿Qué necesitas del Sisbén?', requerido: true, opciones: [
        { v: 'encuesta', t: 'Que me hagan la encuesta por primera vez', legal: 'la aplicación de la encuesta Sisbén por primera vez' },
        { v: 'actualizar', t: 'Que actualicen mi encuesta porque mi situación cambió', legal: 'la actualización de la encuesta por cambio en las condiciones del hogar' },
        { v: 'corregir', t: 'Que corrijan datos errados (integrantes, dirección, documento)', legal: 'la corrección de la información registrada en la ficha' },
        { v: 'explicar', t: 'Que me expliquen por qué quedé en ese grupo', legal: 'la explicación de las variables que determinaron la clasificación asignada' },
        { v: 'visita', t: 'Que programen la visita que nunca llegó', legal: 'la programación de la visita domiciliaria pendiente' }
      ] },
      { id: 'grupoActual', tipo: 'texto', etiqueta: 'Grupo o puntaje actual (si lo sabes)', ejemplo: 'Ej.: Grupo C1', ancho: 'media' },
      { id: 'cambio', tipo: 'textarea', etiqueta: '¿Qué cambió en tu hogar o qué dato está mal?', ejemplo: 'Ej.: Perdí el empleo en enero; mi madre, que tiene 78 años, se vino a vivir con nosotros; en la ficha aparece un integrante que ya no vive aquí.', filas: 3 },
      ...C.previo({ etiqueta: '¿Ya habías solicitado la encuesta o la actualización?' }),
      C.relato({ requerido: false, etiqueta: '¿Algo más que debamos contar? (opcional)' })
    ],
    asunto: d => `Derecho de petición – ${R.capital(R.opcionTexto(camposDe('pet_municipio_sisben', 'tramite'), d.tramite))}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} y su hogar residen en ${d.direccion || 'la dirección indicada al final de este escrito'}, en ${d.ciudad || 'este municipio'}${d.grupoActual ? `, y actualmente figuran clasificados en el Sisbén en el grupo ${d.grupoActual}` : ''}.`);
      if (d.cambio) h.push(`Las condiciones del hogar son las siguientes: ${R.oracion(d.cambio)}`);
      h.push(...R.hechosPrevio(d, R.opcionTexto(camposDe('pet_municipio_sisben', 'tramite'), d.tramite)));
      h.push('La clasificación del Sisbén determina el acceso del hogar a programas sociales esenciales (régimen subsidiado de salud, Renta Ciudadana, Colombia Mayor, subsidios de vivienda y educación), de modo que la demora en la encuesta o la información errada causa un perjuicio directo y grave.');
      return h;
    },
    normas: ['cp23', 'cp13', 'l1755_14', 'sisben', 'cp209'],
    peticiones: [
      { v: 'programar', inicial: d => ['encuesta', 'actualizar', 'visita'].includes(d.tramite), t: 'Que programen la encuesta o visita y me digan la fecha', legal: 'Programar y practicar la encuesta o visita domiciliaria solicitada, informándome por escrito la fecha y hora en que se realizará.' },
      { v: 'corregir', inicial: d => d.tramite === 'corregir', t: 'Que corrijan los datos errados', legal: 'Corregir la información errada de la ficha del hogar conforme a los documentos que se anexan y remitir la novedad al Departamento Nacional de Planeación.' },
      { v: 'explicar', inicial: d => d.tramite === 'explicar', t: 'Que me expliquen cómo se calculó mi grupo', legal: 'Explicar de manera clara las variables y la metodología que determinaron la clasificación del hogar, y entregar copia de la ficha de caracterización.' },
      { v: 'tiempo', inicial: true, t: 'Que me digan cuánto tarda en reflejarse el cambio', legal: 'Informar el término en que la actualización quedará publicada en la base nacional del Sisbén y será visible para las entidades que administran programas sociales.' }
    ],
    anexos: [ { v: 'cedulas', t: 'Copia de los documentos de identidad del hogar' }, { v: 'servicios', t: 'Recibo de servicios públicos reciente' }, { v: 'soportes', t: 'Soportes del cambio (carta de despido, historia clínica, registro civil)' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, siNoResponden: 'Sin respuesta en 15 días hábiles, procede la tutela por violación del derecho de petición. Si un programa social depende de la actualización y estás en riesgo (salud, alimentación), la tutela también puede invocar el mínimo vital.' }
  },

  /* ---------------- MUNICIPIO: TRÁNSITO ---------------- */
  {
    id: 'pet_municipio_transito', tipo: 'peticion', categoria: 'municipio',
    titulo: 'Petición a Tránsito: prescripción de comparendo, fotomulta mal notificada o paz y salvo',
    resumen: 'Pedir que declaren la prescripción de multas de más de 3 años, anular fotomultas notificadas fuera de tiempo, corregir el RUNT o expedir paz y salvo.',
    palabras: ['comparendo', 'multa', 'fotomulta', 'tránsito', 'prescripción', 'SIMIT', 'RUNT', 'licencia de conducción', 'paz y salvo', 'embargo', 'cobro coactivo'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Secretaría de Movilidad de Medellín', cargo: 'Secretaría de Tránsito y Transporte – Oficina de Cobro Coactivo', ejemploCargo: 'Ej.: Secretario(a) de Movilidad' },
    campos: [
      { id: 'tramite', tipo: 'select', etiqueta: '¿Qué necesitas?', requerido: true, opciones: [
        { v: 'prescripcion', t: 'Que declaren prescrita una multa de hace más de 3 años', legal: 'la declaratoria de prescripción de la acción de cobro de la multa' },
        { v: 'fotomulta', t: 'Que anulen una fotomulta que no me notificaron a tiempo', legal: 'la revocatoria del comparendo electrónico por indebida notificación' },
        { v: 'no_fui', t: 'Que revisen un comparendo porque yo no cometí la infracción', legal: 'la revisión y revocatoria del comparendo' },
        { v: 'pazysalvo', t: 'Un paz y salvo o certificado', legal: 'la expedición del paz y salvo o certificado' },
        { v: 'acuerdo', t: 'Un acuerdo de pago o información de la deuda', legal: 'la información detallada de la deuda y la suscripción de un acuerdo de pago' },
        { v: 'embargo', t: 'Que levanten un embargo o me expliquen un cobro coactivo', legal: 'la información del proceso de cobro coactivo y el levantamiento de las medidas cautelares' }
      ] },
      { id: 'comparendo', tipo: 'texto', etiqueta: 'Número del comparendo o de la resolución (si lo tienes)', ejemplo: 'Ej.: 05001000000012345678', ancho: 'media' },
      { id: 'fechaInfraccion', tipo: 'fecha', etiqueta: 'Fecha de la supuesta infracción', ancho: 'media' },
      { id: 'placa', tipo: 'texto', etiqueta: 'Placa del vehículo', ejemplo: 'Ej.: ABC123', ancho: 'media' },
      { id: 'valor', tipo: 'texto', etiqueta: 'Valor que cobran (aproximado)', ejemplo: 'Ej.: 1.200.000', ancho: 'media' },
      { id: 'notificacion', tipo: 'select', etiqueta: '¿Cómo te enteraste del comparendo?', opciones: [
        { v: 'nunca', t: 'Nunca me notificaron; lo vi en el SIMIT o al renovar la licencia', legal: 'nunca fue notificado y solo se enteró al consultar el SIMIT o al realizar otro trámite' },
        { v: 'tarde', t: 'Me llegó una carta pero mucho después de la fecha', legal: 'fue notificado por correo mucho después de los tres días hábiles que exige la ley' },
        { v: 'personal', t: 'Me lo entregaron en el momento (comparendo en vía)', legal: 'le fue impuesto personalmente en la vía' },
        { v: 'cobro', t: 'Me llegó directamente un mandamiento de pago o embargo', legal: 'solo tuvo conocimiento al recibir el mandamiento de pago o la medida de embargo' }
      ], valorInicial: 'nunca', ancho: 'completa' },
      C.relato({ requerido: false, etiqueta: 'Cuéntanos más detalles (opcional)' })
    ],
    asunto: d => `Derecho de petición – ${R.capital(R.opcionTexto(camposDe('pet_municipio_transito', 'tramite'), d.tramite))}${d.comparendo ? ` No. ${d.comparendo}` : ''}${d.placa ? ` – placa ${R.mayus(d.placa)}` : ''}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`En el sistema de la autoridad de tránsito figura a nombre de ${a.nom} ${d.comparendo ? `el comparendo No. ${d.comparendo}` : 'un comparendo'}${d.placa ? `, asociado al vehículo de placa ${R.mayus(d.placa)}` : ''}${d.fechaInfraccion ? `, por una presunta infracción ocurrida ${R.elDia(d.fechaInfraccion)}` : ''}${d.valor ? `, por un valor aproximado de ${R.moneda(d.valor) || d.valor}` : ''}.`);
      h.push(`${a.Nom} ${R.opcionTexto(camposDe('pet_municipio_transito', 'notificacion'), d.notificacion)}.`);
      if (d.tramite === 'prescripcion' && d.fechaInfraccion) {
        const f = AJ.festivos.parseISO(d.fechaInfraccion);
        const anios = f ? Math.floor((R.hoy() - f) / (365.25 * 24 * 3600 * 1000)) : null;
        if (anios !== null) h.push(`Desde la fecha de la presunta infracción han transcurrido más de ${anios} años sin que ${a.nom} haya sido notificad${a.o} de un mandamiento de pago, único acto que interrumpe la prescripción.`);
      }
      if (d.tramite === 'embargo' || d.notificacion === 'cobro') h.push('El proceso de cobro coactivo se adelantó sin que el comparendo y la resolución sancionatoria hubieran sido notificados en debida forma, lo que impidió ejercer el derecho de defensa.');
      return h;
    },
    normas: ['cp23', 'cp29', 'l1755_14', 'l769_159', 'l1843', 'l1437_66', 'l1066'],
    peticiones: [
      { v: 'prescripcion', inicial: d => d.tramite === 'prescripcion', t: 'Que declaren la prescripción y eliminen la multa del SIMIT y el RUNT', legal: d => `Declarar la prescripción de la acción de cobro ${d.comparendo ? `del comparendo No. ${d.comparendo}` : 'del comparendo descrito'}, conforme al artículo 159 de la Ley 769 de 2002, y ordenar su eliminación de los registros del SIMIT, del RUNT y de la cartera de la entidad.` },
      { v: 'revocar', inicial: d => ['fotomulta', 'no_fui'].includes(d.tramite), t: 'Que revoquen el comparendo por no haberme notificado en tiempo', legal: 'Revocar la orden de comparendo y la resolución sancionatoria por indebida notificación, pues no se cumplió el término de tres (3) días hábiles del artículo 8 de la Ley 1843 de 2017, y archivar la actuación.' },
      { v: 'copias', inicial: true, t: 'Que me entreguen copia del comparendo, la resolución y las pruebas de notificación', legal: 'Expedir copia íntegra del comparendo, de la resolución sancionatoria, de las constancias de envío y notificación (guías de correo certificado) y, si existe, del mandamiento de pago.' },
      { v: 'levantar', inicial: d => d.tramite === 'embargo', t: 'Que levanten el embargo', legal: 'Levantar las medidas cautelares decretadas dentro del proceso de cobro coactivo y abstenerse de continuar el cobro hasta que se resuelva de fondo esta petición.' },
      { v: 'pazysalvo', inicial: d => d.tramite === 'pazysalvo', t: 'Que expidan el paz y salvo', legal: 'Expedir el paz y salvo o certificado de no tener obligaciones pendientes por infracciones de tránsito.' },
      { v: 'acuerdo', inicial: d => d.tramite === 'acuerdo', t: 'Que me informen la deuda detallada y me permitan un acuerdo de pago', legal: 'Informar de manera detallada las obligaciones pendientes (capital, intereses, descuentos aplicables) y permitir la suscripción de un acuerdo de pago en condiciones que se ajusten a mi capacidad económica.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de mi cédula' }, { v: 'simit', t: 'Pantallazo de la consulta en el SIMIT o RUNT' }, { v: 'cartas', t: 'Copia de las cartas o notificaciones recibidas (con el sobre y la fecha)' }, { v: 'tarjeta', t: 'Copia de la tarjeta de propiedad o la licencia' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Si te niegan la prescripción o la revocatoria mediante resolución, tienes 10 días hábiles para presentar recurso de reposición y apelación (ver "Recurso contra una decisión de una entidad").', siNoResponden: 'Sin respuesta en 15 días hábiles, procede la tutela por violación del derecho de petición. Si hay embargo de tu salario o cuenta y afecta tu sustento, la tutela puede invocar también el mínimo vital y el debido proceso.' }
  },

  /* ---------------- MUNICIPIO: PREDIAL / HACIENDA ---------------- */
  {
    id: 'pet_municipio_predial', tipo: 'peticion', categoria: 'municipio',
    titulo: 'Petición a Hacienda municipal: predial, prescripción de deudas, avalúo o paz y salvo',
    resumen: 'Pedir la prescripción de impuesto predial o de vehículos de más de 5 años, corregir el avalúo o el propietario, pedir un acuerdo de pago o un paz y salvo.',
    palabras: ['predial', 'impuesto', 'hacienda', 'prescripción', 'avalúo', 'catastro', 'paz y salvo', 'cobro coactivo', 'embargo', 'vehículos', 'industria y comercio'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Alcaldía de Bello', cargo: 'Secretaría de Hacienda – Oficina de Impuestos y Cobro Coactivo', ejemploCargo: 'Ej.: Secretario(a) de Hacienda / Tesorero(a)' },
    campos: [
      { id: 'tramite', tipo: 'select', etiqueta: '¿Qué necesitas?', requerido: true, opciones: [
        { v: 'prescripcion', t: 'Que declaren prescritas deudas de impuestos de más de 5 años', legal: 'la declaratoria de prescripción de las obligaciones tributarias con más de cinco años de exigibilidad' },
        { v: 'avaluo', t: 'Que revisen el avalúo o el valor que me cobran', legal: 'la revisión del avalúo catastral y de la liquidación del impuesto' },
        { v: 'propietario', t: 'Que corrijan el nombre del propietario o los datos del predio', legal: 'la corrección de la información del propietario o del predio' },
        { v: 'acuerdo', t: 'Un acuerdo de pago o información de la deuda', legal: 'la información detallada de la deuda y un acuerdo de pago' },
        { v: 'pazysalvo', t: 'Un paz y salvo o certificado', legal: 'la expedición del paz y salvo o certificado' },
        { v: 'exencion', t: 'Que apliquen una exención o descuento al que tengo derecho', legal: 'la aplicación del beneficio tributario al que tiene derecho' }
      ] },
      { id: 'predio', tipo: 'texto', etiqueta: 'Dirección y matrícula o referencia catastral del predio (o placa del vehículo)', ejemplo: 'Ej.: Calle 50 # 20-10; referencia catastral 0101000100230005', ancho: 'completa' },
      { id: 'anios', tipo: 'texto', etiqueta: 'Años o períodos que te cobran', ejemplo: 'Ej.: 2015 a 2019', ancho: 'media' },
      { id: 'valor', tipo: 'texto', etiqueta: 'Valor total que te cobran (aproximado)', ejemplo: 'Ej.: 4.500.000', ancho: 'media' },
      C.relato({ requerido: false, etiqueta: 'Cuéntanos más detalles (opcional)', ejemplo: 'Ej.:\nHeredé la casa de mi madre en 2020 y solo ahora me enteré de la deuda.\nNunca me notificaron ningún cobro.\nSoy pensionado con una mesada de un salario mínimo.' })
    ],
    asunto: d => `Derecho de petición – ${R.capital(R.opcionTexto(camposDe('pet_municipio_predial', 'tramite'), d.tramite))}${d.predio ? ` (${d.predio})` : ''}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} figura como responsable ${d.predio ? `del predio o bien identificado así: ${d.predio}` : 'del bien descrito'}, sobre el cual la entidad cobra ${d.anios ? `los períodos ${d.anios}` : 'varios períodos'}${d.valor ? `, por un valor aproximado de ${R.moneda(d.valor) || d.valor}` : ''}.`);
      if (d.tramite === 'prescripcion') h.push(`Respecto de los períodos con más de cinco (5) años de exigibilidad, ${a.nom} no ha sido notificad${a.o} de ningún mandamiento de pago, por lo que la acción de cobro se encuentra prescrita.`);
      return h;
    },
    normas: ['cp23', 'cp29', 'l1755_14', 'l1066', 'l1437_66'],
    fundamentos: d => d.tramite === 'prescripcion' ? ['La prescripción de la acción de cobro de los impuestos territoriales se rige por el artículo 817 del Estatuto Tributario, aplicable a los municipios por remisión del artículo 59 de la Ley 788 de 2002: cinco (5) años contados desde la fecha de exigibilidad, y debe ser decretada de oficio o a petición de parte. El cobro de obligaciones prescritas constituye un enriquecimiento sin causa y vulnera el debido proceso.'] : [],
    peticiones: [
      { v: 'prescripcion', inicial: d => d.tramite === 'prescripcion', t: 'Que declaren la prescripción y eliminen la deuda', legal: d => `Declarar la prescripción de la acción de cobro de los períodos ${d.anios || 'con más de cinco años de exigibilidad'}, conforme al artículo 817 del Estatuto Tributario, y eliminar esas sumas, sus intereses y sanciones de la cuenta corriente del contribuyente.` },
      { v: 'estado', inicial: true, t: 'Que me entreguen el estado de cuenta detallado por año', legal: 'Expedir un estado de cuenta detallado por período, discriminando capital, intereses y sanciones, con indicación de la fecha de exigibilidad de cada obligación y de los actos de cobro notificados.' },
      { v: 'copias', t: 'Que me entreguen copia de las notificaciones y del mandamiento de pago', legal: 'Expedir copia de los actos de liquidación, de las constancias de notificación y, si existe, del mandamiento de pago y de las medidas cautelares.' },
      { v: 'revisar', inicial: d => ['avaluo', 'propietario', 'exencion'].includes(d.tramite), t: 'Que revisen el avalúo o corrijan los datos', legal: 'Revisar la liquidación del impuesto y corregir la información catastral o del propietario conforme a los documentos que se anexan, coordinando con la autoridad catastral lo que corresponda.' },
      { v: 'acuerdo', inicial: d => d.tramite === 'acuerdo', t: 'Que me permitan un acuerdo de pago', legal: 'Permitir la suscripción de un acuerdo de pago sobre las sumas efectivamente debidas, en condiciones acordes con mi capacidad económica.' },
      { v: 'pazysalvo', inicial: d => d.tramite === 'pazysalvo', t: 'Que expidan el paz y salvo', legal: 'Expedir el paz y salvo correspondiente una vez aplicadas las correcciones solicitadas.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de mi cédula' }, { v: 'predial', t: 'Última factura del predial o estado de cuenta' }, { v: 'escritura', t: 'Escritura o certificado de libertad y tradición' }, { v: 'soportes', t: 'Soportes de la exención (discapacidad, pensión, estrato)' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Si responden con una resolución negativa, tienes 10 días hábiles para presentar recurso de reposición (y apelación si procede).', siNoResponden: 'Sin respuesta en 15 días hábiles, procede la tutela por violación del derecho de petición.' }
  },

  /* ---------------- MUNICIPIO: INSPECCIÓN DE POLICÍA ---------------- */
  {
    id: 'pet_municipio_policia', tipo: 'peticion', categoria: 'municipio',
    tituloDoc: 'QUERELLA POLICIVA (artículo 223 de la Ley 1801 de 2016)', saludoDoc: 'Respetado(a) señor(a) Inspector(a) de Policía:',
    titulo: 'Querella ante la Inspección de Policía (ruido, vecinos, perturbación, invasión)',
    resumen: 'Pedir al inspector de policía que intervenga por ruido excesivo, mascotas, basuras, construcciones que afectan tu casa, invasión de un predio o conflictos de convivencia.',
    palabras: ['ruido', 'vecino', 'inspección de policía', 'querella', 'perturbación', 'invasión', 'convivencia', 'mascota', 'perro', 'humedad', 'muro', 'fiesta', 'bar', 'código de policía'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Inspección de Policía de la Comuna 10 de Medellín', cargo: 'Inspector(a) de Policía', ejemploCargo: 'Ej.: Inspección Municipal de Policía' },
    campos: [
      { id: 'tipo', tipo: 'select', etiqueta: '¿Qué está pasando?', requerido: true, opciones: [
        { v: 'ruido', t: 'Ruido excesivo (música, fiestas, maquinaria, bar)', legal: 'ruidos excesivos que afectan la tranquilidad' },
        { v: 'construccion', t: 'Una construcción que daña mi casa o invade mi predio', legal: 'una construcción que afecta la integridad de mi inmueble o invade mi predio' },
        { v: 'invasion', t: 'Invadieron mi predio o no me dejan entrar', legal: 'la perturbación de la posesión o tenencia de mi inmueble' },
        { v: 'animales', t: 'Animales que causan daño, agresión o insalubridad', legal: 'la tenencia irresponsable de animales' },
        { v: 'basuras', t: 'Basuras, aguas o malos olores que provienen de un vecino', legal: 'la disposición inadecuada de residuos o aguas que afecta la salubridad' },
        { v: 'espacio', t: 'Ocupación del espacio público (andén, vía) frente a mi casa', legal: 'la ocupación indebida del espacio público' },
        { v: 'agresion', t: 'Agresiones, amenazas o riñas de un vecino', legal: 'comportamientos agresivos que ponen en riesgo mi integridad' }
      ] },
      { id: 'querellado', tipo: 'texto', etiqueta: 'Nombre o descripción de la persona o establecimiento responsable', ejemplo: 'Ej.: Bar "El Rincón", carrera 40 # 10-20 / el vecino del segundo piso, señor Pedro', requerido: true, ancho: 'completa' },
      { id: 'lugar', tipo: 'texto', etiqueta: 'Dirección donde ocurren los hechos', requerido: true, ancho: 'media' },
      { id: 'frecuencia', tipo: 'texto', etiqueta: '¿Con qué frecuencia y en qué horarios?', ejemplo: 'Ej.: todos los fines de semana desde las 10 p. m. hasta las 4 a. m.', ancho: 'media' },
      { id: 'hablaron', tipo: 'radio', etiqueta: '¿Ya intentaste hablar con el responsable o llamaste a la Policía?', opciones: [ { v: 'no', t: 'No' }, { v: 'si', t: 'Sí, pero no se solucionó' } ], requerido: true },
      C.relato({ ejemplo: 'Ej.:\nDesde marzo de 2026 el bar del primer piso pone música a todo volumen hasta la madrugada.\nEn mi casa viven dos niños y mi madre de 80 años que no pueden dormir.\nHe llamado al cuadrante tres veces; llegan, bajan el volumen y a la media hora vuelve igual.' })
    ],
    asunto: d => `Querella policiva – ${R.opcionTexto(camposDe('pet_municipio_policia', 'tipo'), d.tipo)} en ${d.lugar || 'el lugar descrito'}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} reside en ${d.direccion || d.ciudad || 'el sector'}, y desde allí viene siendo afectad${a.o} por ${R.opcionTexto(camposDe('pet_municipio_policia', 'tipo'), d.tipo)}, provenientes de ${d.querellado || 'la persona querellada'}, en ${d.lugar || 'el lugar indicado'}${d.frecuencia ? `, con la siguiente frecuencia: ${d.frecuencia}` : ''}.`);
      if (d.hablaron === 'si') h.push('Se intentó una solución directa con el responsable y se acudió a la Policía Nacional (cuadrante), sin que la situación se haya corregido de manera definitiva.');
      return h;
    },
    normas: ['cp2', 'cp23', 'l1801', 'l1755_14'],
    fundamentos: d => {
      const f = ['De acuerdo con el artículo 206 de la Ley 1801 de 2016, los inspectores de policía conocen de los comportamientos contrarios a la convivencia en materia de tranquilidad, relaciones respetuosas, protección de bienes inmuebles, actividad económica y urbanismo, mediante el proceso verbal abreviado del artículo 223, que puede iniciarse a petición de cualquier persona afectada.'];
      if (d.tipo === 'ruido') f.push('El artículo 33 de la Ley 1801 de 2016 califica como comportamiento contrario a la tranquilidad "sonidos o ruidos en actividades, fiestas, reuniones o eventos similares que afecten la convivencia del vecindario", y la Resolución 627 de 2006 del Ministerio de Ambiente fija los niveles máximos de ruido permitidos en zonas residenciales (65 decibeles en el día y 55 en la noche).');
      if (d.tipo === 'invasion' || d.tipo === 'construccion') f.push('Los artículos 77 a 81 de la Ley 1801 de 2016 protegen la posesión y la mera tenencia de los inmuebles frente a perturbaciones, y facultan al inspector para ordenar el restablecimiento de la situación anterior y la suspensión de obras que afecten predios vecinos.');
      if (d.tipo === 'animales') f.push('Los artículos 116 a 134 de la Ley 1801 de 2016 regulan la tenencia responsable de animales, incluidas las obligaciones frente a animales potencialmente peligrosos y la prohibición de permitir que causen daño o molestias a terceros.');
      return f;
    },
    peticiones: [
      { v: 'proceso', inicial: true, t: 'Que inicien el proceso policivo y citen al responsable a audiencia', legal: 'Iniciar el proceso verbal abreviado previsto en el artículo 223 de la Ley 1801 de 2016, citar a la persona querellada a audiencia pública y practicar las pruebas necesarias, incluida la visita al lugar.' },
      { v: 'medida', inicial: true, t: 'Que ordenen cesar la conducta y apliquen las medidas correctivas', legal: 'Ordenar el cese inmediato del comportamiento contrario a la convivencia e imponer las medidas correctivas que correspondan (multa, suspensión temporal de actividad, restablecimiento del derecho, reparación de daños).' },
      { v: 'medicion', t: 'Que midan el ruido con la autoridad ambiental', legal: 'Solicitar a la autoridad ambiental competente la medición técnica de los niveles de ruido en el lugar y horarios indicados.' },
      { v: 'policia', t: 'Que la Policía haga rondas y acuda cuando se llame', legal: 'Requerir a la Policía Nacional para que ejerza vigilancia sobre el lugar y atienda oportunamente los llamados de la comunidad.' },
      { v: 'informar', t: 'Que me informen el número del proceso y las decisiones', legal: 'Informarme el número de radicado de la querella, la fecha de la audiencia y las decisiones que se adopten, en la dirección y correo indicados.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de mi cédula' }, { v: 'videos', t: 'Videos, audios o fotografías de los hechos' }, { v: 'testigos', t: 'Nombres y teléfonos de testigos o vecinos afectados' }, { v: 'denuncias', t: 'Constancias de llamadas a la Policía o quejas anteriores' }, { v: 'medicas', t: 'Constancias médicas de afectación (insomnio, estrés)' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'La querella no es exactamente un derecho de petición, pero la Inspección debe darle trámite y citar a audiencia. Lleva pruebas (videos con fecha, testigos).', siNoResponden: 'Si la Inspección no actúa, puedes presentar queja ante la Personería y la Secretaría de Gobierno, o una tutela si la situación afecta tu salud, tranquilidad o integridad de manera grave.' }
  },

  /* ---------------- SALUD: EPS SERVICIO ---------------- */
  {
    id: 'pet_eps_servicio', tipo: 'peticion', categoria: 'eps',
    titulo: 'Petición a la EPS: autorizar cita, medicamento, cirugía, examen o remisión',
    resumen: 'Para pedir por escrito a la EPS el servicio ordenado y conservar constancia. Si hay riesgo para la salud o la vida, no esperes a terminar una petición para buscar atención y orientación sobre tutela.',
    palabras: ['EPS', 'medicamento', 'cita', 'especialista', 'cirugía', 'procedimiento', 'examen', 'resonancia', 'autorización', 'remisión', 'salud', 'MIPRES', 'droguería', 'silla de ruedas', 'pañales', 'oxígeno'],
    destinatario: { categoria: 'eps', ejemploNombre: 'Ej.: Nueva EPS', cargo: 'Representante legal / Oficina de atención al usuario', ejemploCargo: 'Ej.: Gerente regional' },
    campos: [
      { id: 'regimen', tipo: 'select', etiqueta: '¿Cómo estás en la EPS?', ayuda: 'Si no sabes, mira el carné o la app de la EPS. Si entraste por el Sisbén y no pagas: subsidiado. Si te descuentan del sueldo, pagas tú o estás por tu esposo(a) o un familiar que paga: contributivo.', opciones: [ { v: 'contributivo', t: 'Contributivo: me descuentan del sueldo, pago yo, o soy beneficiario(a) de alguien que paga', legal: 'régimen contributivo' }, { v: 'subsidiado', t: 'Subsidiado: entré por el Sisbén y no pago', legal: 'régimen subsidiado' }, { v: 'especial', t: 'Especial: soy o fui maestro(a) (Fomag), policía, militar o de Ecopetrol', legal: 'régimen especial o de excepción' } ], valorInicial: 'contributivo', ancho: 'completa' },
      { id: 'tipoServicio', tipo: 'select', etiqueta: '¿Qué te ordenaron y no te han dado?', requerido: true, opciones: [
        { v: 'medicamento', t: 'Un medicamento', legal: 'el medicamento' }, { v: 'cita', t: 'Una cita con especialista', legal: 'la consulta con medicina especializada' },
        { v: 'cirugia', t: 'Una cirugía o procedimiento', legal: 'el procedimiento quirúrgico' }, { v: 'examen', t: 'Un examen o imagen diagnóstica', legal: 'el examen o ayuda diagnóstica' },
        { v: 'terapias', t: 'Terapias (física, ocupacional, lenguaje, psicología)', legal: 'las sesiones de terapia' }, { v: 'insumos', t: 'Insumos o dispositivos (pañales, oxígeno, silla de ruedas, glucómetro)', legal: 'los insumos o dispositivos médicos' },
        { v: 'remision', t: 'Una remisión a otra ciudad o IPS', legal: 'la remisión al prestador indicado' }, { v: 'hospitalizacion', t: 'Hospitalización, cuidado en casa o UCI', legal: 'la atención hospitalaria o domiciliaria' }
      ], ancho: 'media' },
      { id: 'servicio', tipo: 'texto', etiqueta: 'Nombre exacto de lo que ordenó el médico (cópialo de la fórmula u orden)', ejemplo: 'Ej.: Resonancia magnética de columna lumbar con contraste / Insulina glargina 100 UI/ml', requerido: true, ancho: 'completa' },
      { id: 'diagnostico', tipo: 'texto', etiqueta: 'Diagnóstico o enfermedad (como aparece en la historia clínica, si lo sabes)', ejemplo: 'Ej.: Hernia discal L4-L5 / Diabetes mellitus tipo 2', ancho: 'media' },
      { id: 'fechaOrden', tipo: 'fecha', etiqueta: '¿Cuándo te lo ordenó el médico?', ancho: 'media' },
      { id: 'medico', tipo: 'texto', etiqueta: 'Médico y clínica u hospital (IPS) donde lo ordenaron', ejemplo: 'Ej.: Dr. Juan Gómez, ortopedista, Clínica Las Américas', ancho: 'completa' },
      { id: 'respuestaEps', tipo: 'select', etiqueta: '¿Qué te ha dicho la EPS?', opciones: [
        { v: 'nada', t: 'Nada, solo "está en trámite" o "no hay agenda"', legal: 'se ha limitado a indicar que el servicio está "en trámite" o que "no hay agenda disponible"' },
        { v: 'autorizo_sin_cita', t: 'Lo autorizó pero no hay cita ni IPS que lo preste', legal: 'expidió la autorización pero no ha asignado la cita ni cuenta con un prestador que preste efectivamente el servicio' },
        { v: 'nego', t: 'Lo negó (dice que no está cubierto o que necesita más trámites)', legal: 'negó el servicio argumentando que no está cubierto o que requiere trámites administrativos adicionales' },
        { v: 'incompleto', t: 'Me entregan solo una parte (medicamentos incompletos)', legal: 'realiza entregas parciales o incompletas' },
        { v: 'lejos', t: 'Me mandan a otra ciudad sin ayudarme con el transporte', legal: 'asignó el servicio en una ciudad distinta sin garantizar el transporte y el alojamiento' }
      ], valorInicial: 'nada', ancho: 'completa' },
      { id: 'riesgo', tipo: 'textarea', etiqueta: '¿Cómo te afecta la demora? (dolor, empeoramiento, no poder trabajar, riesgo de vida)', ejemplo: 'Ej.: El dolor no me deja caminar ni trabajar; el médico dijo que sin la cirugía puedo perder la movilidad de la pierna.', filas: 3, requerido: true },
      ...C.previo({ etiqueta: '¿Ya habías reclamado por escrito o por la línea de atención?' }),
      C.relato({ requerido: false, etiqueta: '¿Algo más que debamos contar? (opcional)' })
    ],
    asunto: d => `Derecho de petición – Autorización y prestación efectiva de ${d.servicio || R.opcionTexto(camposDe('pet_eps_servicio', 'tipoServicio'), d.tipoServicio)}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} se encuentra afiliad${a.o} a ${R.entidad(d)} en el ${R.opcionTexto(camposDe('pet_eps_servicio', 'regimen'), d.regimen)}${a.doc ? `, identificad${a.o} con ${a.doc}` : ''}.`);
      h.push(`${d.fechaOrden ? `${R.capital(R.elDia(d.fechaOrden))}, ` : ''}${d.medico ? `el médico tratante ${d.medico}` : 'el médico tratante adscrito a la red de la EPS'} le ordenó ${R.opcionTexto(camposDe('pet_eps_servicio', 'tipoServicio'), d.tipoServicio)} "${d.servicio || '[servicio ordenado]'}"${d.diagnostico ? `, con ocasión del diagnóstico de ${d.diagnostico}` : ''}.`);
      h.push(`Hasta la fecha, la EPS no ha garantizado la prestación efectiva del servicio: ${R.opcionTexto(camposDe('pet_eps_servicio', 'respuestaEps'), d.respuestaEps)}.`);
      if (d.riesgo) h.push(`La demora está causando un perjuicio grave: ${R.oracion(d.riesgo)}`);
      h.push(...R.hechosPrevio(d, 'la autorización y prestación del servicio'));
      return h;
    },
    normas: ['cp49', 'l1751_2', 'l1751_6', 'l1751_8', 'l1751_17', 'l1751_14', 'cp23', 'l1755_33', 'l1755_14', 'l1755_20', 't760'],
    fundamentos: d => {
      const f = [];
      if (d.tipoServicio === 'medicamento' || d.tipoServicio === 'insumos') f.push(AJ.normas.res1604.texto + ` (${AJ.normas.res1604.cita}).`);
      if (d.tipoServicio === 'cita') f.push(AJ.normas.res1552.texto + ` (${AJ.normas.res1552.cita}).`);
      if (d.respuestaEps === 'nego') f.push(AJ.normas.mipres.texto + ` (${AJ.normas.mipres.cita}).`, AJ.normas.l1751_15.texto + ` (${AJ.normas.l1751_15.cita}).`);
      if (d.respuestaEps === 'lejos') f.push(AJ.normas.integral.texto + ` (${AJ.normas.integral.cita}).`);
      return f;
    },
    peticiones: [
      { v: 'autorizar', inicial: true, t: 'Que autoricen y me presten el servicio de inmediato, con fecha, hora y lugar', legal: d => `Autorizar y garantizar la prestación efectiva de ${R.opcionTexto(camposDe('pet_eps_servicio', 'tipoServicio'), d.tipoServicio)} "${d.servicio || '[servicio]'}" que ordenó el médico tratante, informando por escrito la fecha, hora e IPS donde se prestará, en un plazo que no supere los cinco (5) días hábiles dada la urgencia descrita.` },
      { v: 'razones', inicial: true, t: 'Si lo niegan, que me digan por escrito la razón y la norma', legal: 'En caso de negativa, informar por escrito, de manera clara y motivada, las razones y las normas en que se funda, indicando los recursos y mecanismos que proceden.' },
      { v: 'integral', t: 'Que me garanticen el tratamiento completo que ordene el médico', legal: 'Garantizar la atención integral de la enfermedad diagnosticada, suministrando sin dilaciones los demás servicios, medicamentos, insumos y controles que ordene el médico tratante, conforme al artículo 8 de la Ley 1751 de 2015.' },
      { v: 'transporte', t: 'Que cubran transporte y alojamiento si el servicio es en otra ciudad', legal: 'Cubrir los gastos de transporte, alojamiento y alimentación del paciente y de un acompañante cuando el servicio deba prestarse en un municipio distinto al de residencia, dada la carencia de recursos económicos.' },
      { v: 'copia', t: 'Que me entreguen copia de la historia clínica y las autorizaciones', legal: 'Expedir copia de la historia clínica, de las órdenes médicas y de las autorizaciones expedidas, dentro de los diez (10) días hábiles siguientes.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula del paciente' }, { v: 'orden', t: 'Copia de la orden o fórmula médica' }, { v: 'historia', t: 'Copia de la historia clínica o epicrisis' }, { v: 'autorizacion', t: 'Autorizaciones o negaciones anteriores' }, { v: 'pantallazos', t: 'Pantallazos o radicados de llamadas y reclamos' }, { v: 'sisben', t: 'Certificado del Sisbén o prueba de falta de recursos' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'En salud no tienes que esperar los 15 días si hay urgencia: la tutela procede directamente cuando está en riesgo la vida o la salud. Este escrito sirve como prueba de que la EPS conocía tu necesidad.', siNoResponden: 'Si la EPS no cumple, presenta la "Tutela por salud: la EPS no autoriza o no entrega" y una queja ante la Supersalud. Ambas están en esta plataforma.' }
  },

  /* ---------------- SALUD: HISTORIA CLÍNICA ---------------- */
  {
    id: 'pet_eps_historia', tipo: 'peticion', categoria: 'eps',
    titulo: 'Petición de copia de la historia clínica o de documentos médicos',
    resumen: 'Pedir a una clínica, hospital o EPS la copia completa de la historia clínica, epicrisis, resultados o certificados. Plazo: 10 días hábiles.',
    palabras: ['historia clínica', 'copia', 'epicrisis', 'resultados', 'exámenes', 'certificado médico', 'clínica', 'hospital', 'IPS', 'incapacidad', 'fallecido'],
    destinatario: { categoria: 'eps', ejemploNombre: 'Ej.: Hospital General de Medellín', cargo: 'Oficina de Archivo Clínico / Atención al usuario', ejemploCargo: 'Ej.: Coordinador(a) de archivo clínico' },
    campos: [
      { id: 'documentos', tipo: 'checks', etiqueta: '¿Qué documentos necesitas?', requerido: true, opciones: [
        { v: 'completa', t: 'Historia clínica completa', legal: 'la historia clínica completa' }, { v: 'epicrisis', t: 'Epicrisis o resumen de hospitalización', legal: 'la epicrisis o resumen de atención' },
        { v: 'resultados', t: 'Resultados de exámenes, imágenes o biopsias', legal: 'los resultados de exámenes de laboratorio, imágenes diagnósticas y estudios' }, { v: 'ordenes', t: 'Órdenes médicas y fórmulas', legal: 'las órdenes médicas y fórmulas expedidas' },
        { v: 'incapacidades', t: 'Certificados de incapacidad', legal: 'los certificados de incapacidad expedidos' }, { v: 'certificado', t: 'Certificado médico del diagnóstico o la discapacidad', legal: 'la certificación médica del diagnóstico o condición de salud' },
        { v: 'facturas', t: 'Facturas o detalle de cobros', legal: 'la facturación y el detalle de los cobros realizados' }
      ] },
      { id: 'periodo', tipo: 'texto', etiqueta: 'Período o fechas de atención', ejemplo: 'Ej.: Hospitalización del 2 al 10 de mayo de 2026 / Toda la historia desde 2020', ancho: 'media' },
      { id: 'paraQue', tipo: 'select', etiqueta: '¿Para qué la necesitas? (opcional, ayuda a priorizar)', opciones: [ { v: 'tratamiento', t: 'Continuar un tratamiento o pedir segunda opinión', legal: 'continuar su tratamiento y obtener una segunda opinión médica' }, { v: 'pension', t: 'Trámite de pensión de invalidez o calificación', legal: 'adelantar el trámite de calificación de pérdida de capacidad laboral o de pensión' }, { v: 'tutela', t: 'Presentar una tutela o una queja', legal: 'ejercer acciones legales en defensa de sus derechos' }, { v: 'laboral', t: 'Trámite laboral o de incapacidades', legal: 'adelantar trámites laborales y de reconocimiento de incapacidades' }, { v: 'otro', t: 'Otro', legal: 'fines personales legítimos' } ], valorInicial: 'tratamiento', ancho: 'media' },
      { id: 'fallecido', tipo: 'radio', etiqueta: '¿La historia es de un familiar fallecido?', opciones: [ { v: 'no', t: 'No' }, { v: 'si', t: 'Sí (anexa registro civil de defunción y prueba del parentesco)' } ], valorInicial: 'no' },
      C.relato({ requerido: false, etiqueta: 'Detalles adicionales (opcional)' })
    ],
    asunto: d => 'Derecho de petición – Solicitud de copia de historia clínica y documentos médicos',
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} ${d.fallecido === 'si' ? 'es familiar de una persona que ' : ''}ha recibido atención en salud en ${R.entidad(d)}${d.periodo ? `, durante el período ${d.periodo}` : ''}.`);
      h.push(`Requiere ${R.lista((d.documentos || []).map(v => R.opcionTexto(camposDe('pet_eps_historia', 'documentos'), v)))} para ${R.opcionTexto(camposDe('pet_eps_historia', 'paraQue'), d.paraQue)}.`);
      if (d.fallecido === 'si') h.push('El titular de la historia clínica falleció, y quien suscribe acredita el parentesco con los documentos anexos, conforme a la jurisprudencia constitucional que reconoce a los familiares cercanos el derecho a acceder a la historia clínica del fallecido (entre otras, Sentencia T-158A de 2008).');
      return h;
    },
    normas: ['cp23', 'cp15', 'hc', 'l1755_14', 'l1755_33', 'l1751_10'],
    peticiones: [
      { v: 'copia', inicial: true, t: 'Que me entreguen copia completa, legible y sin costo, en 10 días hábiles', legal: d => `Expedir y entregar copia íntegra y legible de ${R.lista((d.documentos || []).map(v => R.opcionTexto(camposDe('pet_eps_historia', 'documentos'), v))) || 'los documentos solicitados'}${d.periodo ? ` correspondientes al período ${d.periodo}` : ''}, dentro de los diez (10) días hábiles siguientes, preferiblemente en formato digital al correo indicado.` },
      { v: 'gratis', inicial: true, t: 'Que no me cobren por la primera copia', legal: 'Abstenerse de cobrar por la expedición de la primera copia, por tratarse del ejercicio de un derecho fundamental sobre información propia del paciente, o informar previamente el costo de reproducción cuando legalmente proceda.' },
      { v: 'certificar', t: 'Que certifiquen si hay documentos faltantes', legal: 'Certificar si existen documentos faltantes o ilegibles en la historia clínica e indicar las razones.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula del paciente' }, { v: 'defuncion', t: 'Registro civil de defunción (si el paciente falleció)', si: d => d.fallecido === 'si' }, { v: 'parentesco', t: 'Registro civil que pruebe el parentesco (si el paciente falleció o pides la de un familiar)', si: d => d.fallecido === 'si' || R.esRepresentante(d) }, { v: 'autorizacion', t: 'Autorización firmada por el paciente (si pides la de otra persona)', si: d => R.esRepresentante(d) } ],
    guia: { plazo: { dias: 10, tipo: 'habiles' }, nota: 'Si en 10 días hábiles no responden, la ley entiende que la petición fue aceptada y deben entregar las copias en los 3 días siguientes (artículo 14 de la Ley 1755 de 2015).', siNoResponden: 'Sin respuesta en 10 días hábiles: tutela por violación del derecho de petición y del hábeas data. Puedes también quejarte ante la Supersalud.' }
  }
  );

  /* Utilidad local: obtener la definición de un campo de un caso ya registrado */
  function camposDe(idCaso, idCampo) {
    const c = AJ.casos.find(x => x.id === idCaso);
    return c ? c.campos.find(f => f.id === idCampo) : null;
  }
  AJ.camposDe = camposDe;
})();
