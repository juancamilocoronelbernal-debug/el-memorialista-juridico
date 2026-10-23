/* ============================================================
   mujer.js — Módulo de protección de la mujer y de las madres
   cabeza de familia: denuncia penal por violencia, tutela por
   falta de protección, declaración de madre cabeza de familia,
   petición de beneficios, licencia de maternidad, acoso laboral,
   salud sexual y reproductiva, y custodia de los hijos.

   Los casos llevan `modulo: 'mujer'` para agruparse en el catálogo
   (también lo llevan fam_alimentos, fam_proteccion y tut_estabilidad).
   ============================================================ */
window.AJ = window.AJ || {};
AJ.casos = AJ.casos || [];

(function () {
  const R = AJ.red;
  const C = AJ.campos;
  const cd = (c, f) => AJ.camposDe(c, f);
  const SI_NO = [ { v: 'si', t: 'Sí' }, { v: 'no', t: 'No' } ];
  const RELACION = [
    { v: 'pareja', t: 'Es mi esposo, compañero o novio', legal: 'su cónyuge, compañero permanente o pareja' },
    { v: 'ex', t: 'Es mi expareja', legal: 'su expareja' },
    { v: 'familiar', t: 'Es un familiar (padre, hermano, hijo, tío…)', legal: 'un integrante de su familia' },
    { v: 'trabajo', t: 'Es mi jefe o un compañero de trabajo', legal: 'su superior o compañero de trabajo' },
    { v: 'conocido', t: 'Es un vecino o conocido', legal: 'una persona conocida' },
    { v: 'desconocido', t: 'No lo conozco', legal: 'una persona desconocida' }
  ];
  const esFamiliar = d => ['pareja', 'ex', 'familiar'].includes(d.relacion);
  const marco = (d, campo, lista) => (d[campo] || []).map(v => R.opcionTexto(cd(lista[0], lista[1]), v));

  AJ.casos.push(
  /* ---------------- DENUNCIA PENAL POR VIOLENCIA CONTRA LA MUJER ---------------- */
  {
    id: 'muj_denuncia', tipo: 'denuncia', categoria: 'nacional', modulo: 'mujer',
    titulo: 'Denuncia penal por violencia contra la mujer o violencia intrafamiliar (Fiscalía)',
    resumen: 'Golpes, amenazas, maltrato, violencia sexual, acoso o intento de matarte, por parte de tu pareja, expareja, un familiar o cualquier persona. La Fiscalía debe recibirla, investigar y pedir medidas de protección. Si estás en peligro ahora, llama al 123 o al 155.',
    palabras: ['denuncia', 'Fiscalía', 'violencia', 'mujer', 'golpes', 'me pega', 'amenazas', 'violación', 'abuso sexual', 'acoso', 'feminicidio', 'pareja', 'expareja', 'esposo', 'intrafamiliar', 'URI', 'noticia criminal', 'Medicina Legal', 'medida de protección', 'Línea 155'],
    destinatario: { categoria: 'nacional', nombre: 'Fiscalía General de la Nación', cargo: 'Fiscal de la Unidad de Reacción Inmediata (URI)' },
    campos: [
      { id: 'infoEmergencia', tipo: 'info', texto: 'Si estás en peligro en este momento, llama al 123 (Policía) o al 155 (orientación a mujeres, gratis, 24 horas). Si hubo violencia sexual, ve a urgencias de cualquier hospital, mejor en las primeras 72 horas: deben atenderte gratis, sin denuncia previa y sin autorización de la EPS.' },
      { id: 'denunciado', tipo: 'texto', etiqueta: 'Nombre completo del agresor (y apodo, si lo conoces)', requerido: true, ancho: 'media' },
      { id: 'denunciadoDoc', tipo: 'texto', etiqueta: 'Cédula del agresor (si la sabes)', ancho: 'media' },
      { id: 'relacion', tipo: 'select', etiqueta: '¿Qué relación tienes con él?', requerido: true, opciones: RELACION, ancho: 'media' },
      { id: 'denunciadoDireccion', tipo: 'texto', etiqueta: 'Dónde vive o trabaja (para ubicarlo)', requerido: true, ancho: 'media' },
      { id: 'delitos', tipo: 'checks', etiqueta: '¿Qué te hizo? (marca todo lo que aplique)', requerido: true, opciones: [
        { v: 'golpes', t: 'Me golpeó o me causó lesiones', legal: 'lesiones personales' },
        { v: 'maltrato', t: 'Me maltrata física o psicológicamente (insultos, humillaciones, control, encierro)', legal: 'maltrato físico y psicológico' },
        { v: 'amenazas', t: 'Me amenazó de muerte o con hacerme daño (a mí o a mis hijos)', legal: 'amenazas contra la vida y la integridad' },
        { v: 'sexual', t: 'Me obligó a tener relaciones o actos sexuales', legal: 'violencia sexual' },
        { v: 'acoso', t: 'Me acosa con fines sexuales (insinuaciones, persecución, tocamientos)', legal: 'acoso sexual' },
        { v: 'intento', t: 'Intentó matarme', legal: 'tentativa de feminicidio' },
        { v: 'economica', t: 'Me quita el dinero, me impide trabajar o destruye mis cosas', legal: 'violencia económica y patrimonial' }
      ] },
      { id: 'ultimoHecho', tipo: 'fecha', etiqueta: 'Fecha del último hecho', requerido: true, ancho: 'media' },
      { id: 'lugar', tipo: 'texto', etiqueta: '¿Dónde ocurrió?', requerido: true, ancho: 'media' },
      { id: 'desde', tipo: 'texto', etiqueta: '¿Desde cuándo ocurre?', ejemplo: 'Ej.: desde 2023 / desde que nos separamos en marzo', ancho: 'media' },
      { id: 'convive', tipo: 'radio', etiqueta: '¿Vive contigo actualmente?', opciones: SI_NO, requerido: true, ancho: 'media' },
      { id: 'relatoHechos', tipo: 'textarea', etiqueta: 'Cuenta qué pasó, con tus palabras (qué hizo, cuándo, dónde, quién vio o escuchó)', ayuda: 'Escribe cada hecho en una línea aparte y en orden de fechas. No necesitas lenguaje legal: el documento lo convertirá en hechos numerados.', requerido: true, filas: 7, ejemplo: 'Ej.:\nEl 5 de octubre de 2026, a las 10 de la noche, llegó borracho y me golpeó en la cara y en los brazos.\nMe dijo que si lo denunciaba me mataba.\nMi hija de 9 años lo vio todo; la vecina del 3-47 escuchó los gritos.' },
      { id: 'lesiones', tipo: 'radio', etiqueta: '¿Tienes lesiones físicas?', requerido: true, opciones: [ { v: 'si_atendida', t: 'Sí, y ya me atendieron en un hospital o en Medicina Legal' }, { v: 'si', t: 'Sí, pero nadie me ha atendido ni valorado' }, { v: 'no', t: 'No tengo lesiones visibles' } ] },
      { id: 'hijos', tipo: 'radio', etiqueta: '¿Hay niños, niñas o adolescentes que presenciaron o sufrieron los hechos?', requerido: true, opciones: SI_NO, ancho: 'media' },
      { id: 'hijosDatos', tipo: 'texto', etiqueta: 'Nombres y edades de los niños', mostrarSi: { campo: 'hijos', valor: 'si' }, ancho: 'media' },
      { id: 'riesgo', tipo: 'checks', etiqueta: 'Señales de peligro (marca las que apliquen: ayudan a que la Fiscalía actúe rápido)', opciones: [
        { v: 'armas', t: 'Tiene armas o acceso a ellas', legal: 'el agresor tiene armas o acceso a ellas' },
        { v: 'incumple', t: 'Ya tenía una medida de protección y la incumplió', legal: 'el agresor ha incumplido medidas de protección anteriores' },
        { v: 'alcohol', t: 'Consume alcohol o drogas', legal: 'el agresor consume alcohol o sustancias psicoactivas' },
        { v: 'persigue', t: 'Me persigue, me vigila o me controla el celular', legal: 'el agresor la persigue, la vigila y la controla' },
        { v: 'aumenta', t: 'La violencia es cada vez más frecuente o más grave', legal: 'la violencia ha aumentado en frecuencia y gravedad' },
        { v: 'celos', t: 'Celos extremos; no acepta la separación', legal: 'el agresor manifiesta celos extremos y no acepta la separación' },
        { v: 'denuncias', t: 'Ya lo había denunciado antes', legal: 'existen denuncias anteriores contra el agresor' }
      ] },
      { id: 'previas', tipo: 'texto', etiqueta: 'Denuncias o medidas de protección anteriores (número de noticia criminal, Comisaría, fecha)', ancho: 'completa' },
      { id: 'testigosDatos', tipo: 'texto', etiqueta: 'Testigos (nombre y teléfono, si los hay)', ancho: 'completa' }
    ],
    asunto: d => `Denuncia penal por ${R.lista(marco(d, 'delitos', ['muj_denuncia', 'delitos']))} – Violencia contra la mujer${esFamiliar(d) ? ' e intrafamiliar' : ''}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} es víctima de ${R.lista(marco(d, 'delitos', ['muj_denuncia', 'delitos']))} por parte de ${R.mayus(d.denunciado) || '[NOMBRE DEL AGRESOR]'}${d.denunciadoDoc ? `, identificado con cédula No. ${d.denunciadoDoc}` : ''}, ${R.opcionTexto(cd('muj_denuncia', 'relacion'), d.relacion)}, quien ${d.convive === 'si' ? 'convive con la víctima' : 'reside o puede ser ubicado'} en ${d.denunciadoDireccion || '[dirección]'}.`);
      const desde = (d.desde || '').trim().replace(/^desde\s+/i, '');
      const lugar = (d.lugar || '').trim().replace(/^en\s+/i, '');
      h.push(`Los hechos ${desde ? `ocurren desde ${desde} y el último de ellos sucedió` : 'ocurrieron'} ${R.elDia(d.ultimoHecho)} en ${lugar || '[lugar]'}.`);
      h.push(...R.relatoAHechos(d.relatoHechos));
      if (d.lesiones === 'si_atendida') h.push('La víctima fue atendida por las lesiones sufridas, como consta en la historia clínica o en el dictamen que se anexa.');
      if (d.lesiones === 'si') h.push('La víctima presenta lesiones que aún no han sido valoradas por Medicina Legal ni atendidas por un servicio de salud.');
      if (d.hijos === 'si') h.push(`Los hechos fueron presenciados o sufridos también por ${d.hijosDatos || 'los niños del hogar'}, menores de edad.`);
      const riesgos = marco(d, 'riesgo', ['muj_denuncia', 'riesgo']);
      if (riesgos.length) h.push(`Existen señales de riesgo grave para la vida y la integridad de la víctima: ${R.lista(riesgos)}.`);
      if (d.previas && /^(ninguna|ninguno|no|nada)\b/i.test(d.previas.trim())) h.push('No se han presentado denuncias ni solicitudes de protección anteriores por estos hechos.');
      else if (d.previas) h.push(`Con anterioridad se han presentado las siguientes denuncias o solicitudes de protección: ${R.oracion(d.previas)}`);
      if (d.testigosDatos) h.push(`Pueden declarar sobre los hechos: ${R.oracion(d.testigosDatos)}`);
      h.push(`${a.Nom} teme por su vida y su integridad${d.hijos === 'si' ? ' y por las de sus hijos' : ''}, y requiere protección inmediata.`);
      return h;
    },
    normas: d => {
      const del = d.delitos || [];
      return ['cp11', 'cp12', 'cp13', 'cp42', 'cp43', 'l1257_2', 'l1257_7', 'l906_11', 'belem',
        esFamiliar(d) ? 'cpen_vif' : null, del.includes('golpes') ? 'cpen_les' : null, del.includes('amenazas') ? 'cpen_347' : null,
        del.includes('sexual') ? 'cpen_sex' : null, del.includes('acoso') ? 'cpen_210a' : null, del.includes('intento') ? 'cpen_104a' : null,
        'l1257_16', 'l1257_19', 't735'].filter(Boolean);
    },
    fundamentos: d => ['Conforme a la Ley 1542 de 2012, la violencia intrafamiliar y los delitos sexuales se investigan de oficio, no son querellables ni desistibles y su trámite no puede condicionarse a una conciliación. La víctima no está obligada a ser confrontada con el agresor (artículo 8, literal k, de la Ley 1257 de 2008) y tiene derecho a que su relato se valore sin estereotipos y a que se evalúe el riesgo con debida diligencia.'],
    peticiones: [
      { v: 'investigar', inicial: true, fijo: true, t: 'Que reciban la denuncia e inicien la investigación', legal: d => `Recibir esta denuncia, asignarle número de noticia criminal e iniciar la investigación penal contra ${R.mayus(d.denunciado) || '[NOMBRE DEL AGRESOR]'} por ${R.lista(marco(d, 'delitos', ['muj_denuncia', 'delitos']))}, con enfoque de género y debida diligencia.` },
      { v: 'proteccion', inicial: true, t: 'Que pidan medidas de protección urgentes (alejamiento, no contacto, vigilancia policial)', legal: 'Solicitar al juez de control de garantías, de manera inmediata, las medidas de protección y atención necesarias para la víctima y sus hijos (artículo 134 de la Ley 906 de 2004 y artículos 17 y 18 de la Ley 1257 de 2008): orden al agresor de abstenerse de acercarse a la víctima, a su vivienda, su trabajo o su lugar de estudio y de contactarla por cualquier medio, y protección de la Policía Nacional.' },
      { v: 'aseguramiento', inicial: d => (d.delitos || []).includes('intento') || (d.riesgo || []).some(v => ['armas', 'incumple'].includes(v)), t: 'Que pidan al juez una medida de aseguramiento contra el agresor (detención o prohibición de acercarse)', legal: 'Solicitar al juez de control de garantías la imposición de medida de aseguramiento contra el agresor (artículos 306 a 308 de la Ley 906 de 2004), dada la gravedad de los hechos y el peligro que representa para la víctima.' },
      { v: 'medicina', inicial: d => d.lesiones !== 'no' || (d.delitos || []).includes('sexual'), t: 'Que me remitan a Medicina Legal para valoración física y psicológica', legal: 'Remitir a la víctima de inmediato al Instituto Nacional de Medicina Legal y Ciencias Forenses para la valoración de las lesiones físicas, del daño psicológico y del riesgo.' },
      { v: 'salud', inicial: true, t: 'Que ordenen atención médica y psicológica para mí y mis hijos', legal: 'Gestionar la atención integral en salud física y psicológica de la víctima y de sus hijos a cargo de la EPS o de la entidad territorial, conforme a los artículos 13 y 19 de la Ley 1257 de 2008.' },
      { v: 'refugio', t: 'Que me remitan a una casa refugio o me garanticen un lugar seguro', legal: 'Remitir a la víctima y a sus hijos a una casa de refugio o garantizar las medidas de atención de habitación, alimentación y transporte (artículo 18, literal a, y artículo 19 de la Ley 1257 de 2008; Ley 2215 de 2022).' },
      { v: 'comisaria', inicial: d => esFamiliar(d), t: 'Que remitan copia a la Comisaría de Familia para la medida de protección', legal: 'Remitir copia de esta denuncia a la Comisaría de Familia competente para que adopte las medidas de protección de la Ley 294 de 1996, sin perjuicio de la investigación penal.' },
      { v: 'noconciliar', inicial: true, t: 'Que no me obliguen a conciliar ni a enfrentarme con el agresor', legal: 'Abstenerse de citar a la víctima a conciliación o a cualquier diligencia que implique confrontarla con el agresor sin su consentimiento (artículo 8, literal k, de la Ley 1257 de 2008 y Ley 1542 de 2012).' },
      { v: 'ninos', inicial: d => d.hijos === 'si', t: 'Que mis hijos sean reconocidos como víctimas y protegidos', legal: 'Reconocer a los niños, niñas y adolescentes afectados como víctimas, garantizarles atención psicológica y dar aviso a la Comisaría de Familia o al ICBF para su protección (artículo 44 de la Constitución y Ley 1098 de 2006).' },
      { v: 'abogado', t: 'Que me asignen asesoría jurídica gratuita', legal: 'Garantizar a la víctima asesoría y representación jurídica gratuita a través de la Defensoría del Pueblo (artículo 8, literal b, de la Ley 1257 de 2008 y artículo 11 de la Ley 906 de 2004).' },
      { v: 'informar', inicial: true, t: 'Que me informen el número de noticia criminal y el fiscal del caso', legal: 'Informar a la víctima el número de noticia criminal, el fiscal asignado y los avances de la investigación, y notificarle cualquier decisión de archivo (artículo 11 de la Ley 906 de 2004).' }
    ],
    anexos: [
      { v: 'cedula', t: 'Copia de la cédula' },
      { v: 'medicina', t: 'Dictamen de Medicina Legal o historia clínica de urgencias' },
      { v: 'fotos', t: 'Fotos de las lesiones o de los daños' },
      { v: 'mensajes', t: 'Pantallazos de mensajes, audios, correos o llamadas' },
      { v: 'previas', t: 'Denuncias o medidas de protección anteriores' },
      { v: 'registros', t: 'Registros civiles de los hijos', si: d => d.hijos === 'si' },
      { v: 'testigos', t: 'Nombres y teléfonos de los testigos' }
    ],
    guia: { nota: 'No hay plazo para denunciar la violencia intrafamiliar ni los delitos sexuales, y la Fiscalía no puede negarse a recibir la denuncia ni pedirte que vuelvas "con pruebas". Pide siempre el número de noticia criminal. Puedes pedir, además y al mismo tiempo, la medida de protección en la Comisaría de Familia: es más rápida (medidas provisionales en 4 horas).', siNoResponden: 'Si la Fiscalía no actúa o te trata mal: queja ante la Procuraduría o la Dirección Seccional de Fiscalías, acompañamiento de la Personería o la Defensoría del Pueblo, y tutela por los derechos a la vida, la integridad y el acceso a la justicia (en esta plataforma: "Tutela por falta de protección frente a la violencia").' }
  },

  /* ---------------- TUTELA: FALTA DE PROTECCIÓN FRENTE A LA VIOLENCIA ---------------- */
  {
    id: 'muj_tutela_proteccion', tipo: 'tutela', categoria: 'municipio', modulo: 'mujer',
    titulo: 'Tutela por falta de protección frente a la violencia contra la mujer (Comisaría, Fiscalía, Policía, EPS o Alcaldía no actúan)',
    resumen: 'Pediste protección o denunciaste y la entidad no hace nada, demora, te obligó a conciliar, no hace cumplir la medida o no te da atención. La tutela ordena actuar en días.',
    palabras: ['tutela', 'violencia', 'mujer', 'comisaría no hace nada', 'fiscalía no avanza', 'policía no viene', 'medida de protección', 'incumple la medida', 'casa refugio', 'revictimización', 'debida diligencia', 'perspectiva de género', 'vida', 'integridad'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Comisaría Primera de Familia de Soacha / Fiscalía Local de Rionegro / Policía Metropolitana / EPS Sanitas', cargo: 'Comisario(a) de Familia / Fiscal / Comandante / Representante legal' },
    campos: [
      { id: 'quienFalla', tipo: 'select', etiqueta: '¿Qué entidad no te está protegiendo?', ayuda: 'Arriba, en "¿A qué entidad le pones la tutela?", escribe su nombre y elige el tipo: Comisaría o Alcaldía = "Alcaldía o entidad del municipio"; Fiscalía o Policía = "Entidad del Gobierno nacional"; EPS u hospital = "EPS".', requerido: true, opciones: [
        { v: 'comisaria', t: 'La Comisaría de Familia (no dicta la medida, la demora o no hace cumplir la que dictó)', legal: 'la Comisaría de Familia' },
        { v: 'fiscalia', t: 'La Fiscalía (no avanza la denuncia, no pide medidas, archivó)', legal: 'la Fiscalía General de la Nación' },
        { v: 'policia', t: 'La Policía (no atiende mis llamados ni hace cumplir la medida)', legal: 'la Policía Nacional' },
        { v: 'salud', t: 'La EPS o el hospital (no me da atención médica o psicológica, ni a mis hijos)', legal: 'la entidad de salud' },
        { v: 'alcaldia', t: 'La Alcaldía o la Gobernación (no me da casa refugio ni las medidas de atención)', legal: 'la entidad territorial' },
        { v: 'otra', t: 'Otra entidad', legal: 'la entidad accionada' }
      ], ancho: 'completa' },
      { id: 'agresor', tipo: 'texto', etiqueta: 'Nombre del agresor', requerido: true, ancho: 'media' },
      { id: 'relacion', tipo: 'select', etiqueta: '¿Qué relación tienes con él?', requerido: true, opciones: RELACION, ancho: 'media' },
      { id: 'violencia', tipo: 'checks', etiqueta: '¿Qué tipo de violencia sufres?', requerido: true, opciones: [
        { v: 'fisica', t: 'Física', legal: 'violencia física' }, { v: 'psicologica', t: 'Psicológica', legal: 'violencia psicológica' }, { v: 'sexual', t: 'Sexual', legal: 'violencia sexual' }, { v: 'economica', t: 'Económica', legal: 'violencia económica' }, { v: 'amenazas', t: 'Amenazas', legal: 'amenazas contra su vida e integridad' }
      ] },
      { id: 'fechaSolicitud', tipo: 'fecha', etiqueta: '¿Cuándo pediste ayuda a esa entidad (denuncia, solicitud de medida, cita)?', requerido: true, ancho: 'media' },
      { id: 'radicado', tipo: 'texto', etiqueta: 'Radicado, noticia criminal o número del expediente', ancho: 'media' },
      { id: 'queHizo', tipo: 'checks', etiqueta: '¿Qué ha pasado con tu solicitud?', requerido: true, opciones: [
        { v: 'nada', t: 'No han hecho nada / no responden', legal: 'no ha adoptado ninguna actuación ni ha dado respuesta' },
        { v: 'demora', t: 'Pasaron los plazos legales sin decisión', legal: 'ha dejado vencer los términos legales sin decidir' },
        { v: 'negaron', t: 'Negaron la medida o archivaron sin razones válidas', legal: 'negó la protección o archivó la actuación sin fundamento' },
        { v: 'incumple', t: 'Dictaron la medida, el agresor la incumple y no hacen nada', legal: 'no ha hecho cumplir la medida de protección que el agresor viola' },
        { v: 'conciliar', t: 'Me obligaron a conciliar o a enfrentarme con el agresor', legal: 'la obligó a conciliar o a confrontarse con el agresor' },
        { v: 'maltrato', t: 'Me trataron mal, dudaron de mí o me culparon', legal: 'la revictimizó, puso en duda su relato y la responsabilizó de la violencia' },
        { v: 'sinatencion', t: 'No me dan atención médica o psicológica', legal: 'no le ha brindado la atención médica y psicológica requerida' }
      ] },
      { id: 'relatoHechos', tipo: 'textarea', etiqueta: 'Cuenta qué pasó: la violencia que sufres y lo que hizo (o no hizo) la entidad', ayuda: 'Una línea por hecho, en orden de fechas. Incluye fechas, nombres de funcionarios y números de radicado si los tienes.', requerido: true, filas: 7, ejemplo: 'Ej.:\nEl 2 de septiembre de 2026 pedí medida de protección en la Comisaría contra mi expareja por golpes y amenazas.\nMe dijeron que volviera con fotos y testigos; no me recibieron la solicitud.\nEl 20 de septiembre él volvió a amenazarme en la puerta de mi casa; llamé al 123 y nadie llegó.' },
      { id: 'riesgoActual', tipo: 'textarea', etiqueta: '¿Qué peligro corres hoy? (amenazas recientes, si el agresor sabe dónde vives, si tiene armas)', requerido: true, filas: 3 },
      { id: 'hijos', tipo: 'radio', etiqueta: '¿Tienes hijos menores afectados?', requerido: true, opciones: SI_NO, ancho: 'media' },
      { id: 'hijosDatos', tipo: 'texto', etiqueta: 'Nombres y edades', mostrarSi: { campo: 'hijos', valor: 'si' }, ancho: 'media' }
    ],
    asunto: d => 'Acción de tutela – Derecho de las mujeres a una vida libre de violencia – Falta de protección',
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} es víctima de ${R.lista(marco(d, 'violencia', ['muj_tutela_proteccion', 'violencia']))} por parte de ${d.agresor || '[NOMBRE DEL AGRESOR]'}, ${R.opcionTexto(cd('muj_tutela_proteccion', 'relacion'), d.relacion)}.`);
      h.push(`${R.capital(R.elDia(d.fechaSolicitud))} ${a.nom} acudió a ${R.entidad(d)} en busca de protección${d.radicado ? ` (radicado o noticia criminal ${d.radicado})` : ''}.`);
      h.push(`A pesar de ello, ${R.entidad(d)} ${R.lista(marco(d, 'queHizo', ['muj_tutela_proteccion', 'queHizo']))}.`);
      h.push(...R.relatoAHechos(d.relatoHechos));
      h.push(`La situación de riesgo persiste: ${R.oracion(d.riesgoActual)}`);
      if (d.hijos === 'si') h.push(`Los hechos afectan también a ${d.hijosDatos || 'los hijos menores de edad de la accionante'}.`);
      return h;
    },
    derechos: [
      { v: 'vida', inicial: true, t: 'Vida e integridad personal', legal: 'derechos a la vida y a la integridad personal (artículos 11 y 12 de la Constitución)' },
      { v: 'libre', inicial: true, t: 'Vivir una vida libre de violencias', legal: 'derecho de las mujeres a una vida libre de violencias (artículos 13, 42 y 43 de la Constitución, Ley 1257 de 2008 y Convención de Belém do Pará)' },
      { v: 'justicia', inicial: true, t: 'Acceso a la justicia y debido proceso', legal: 'derechos al acceso a la administración de justicia y al debido proceso (artículos 29 y 229 de la Constitución)' },
      { v: 'salud', t: 'Salud', legal: 'derecho a la salud (artículo 49 de la Constitución)' },
      { v: 'ninos', t: 'Derechos de los niños', legal: 'derechos prevalentes de los niños, niñas y adolescentes (artículo 44 de la Constitución)' }
    ],
    normas: ['cp86', 'cp11', 'cp12', 'cp13', 'cp43', 'l1257_7', 'l1257_16', 'l1257_19', 'l294_4', 'l294_9', 'belem', 't735'],
    procedencia: d => [
      'Subsidiariedad: aunque existen los trámites ante la Comisaría de Familia y la Fiscalía, no han sido eficaces para proteger a la accionante. La Corte Constitucional ha señalado que la tutela procede cuando las autoridades omiten actuar con la debida diligencia frente a la violencia contra la mujer, lo hacen con dilación o revictimizan a la víctima, pues están en riesgo su vida y su integridad (sentencias T-735 de 2017, T-338 de 2018 y T-462 de 2018).',
      'Inmediatez: la vulneración es actual y continúa, pues el riesgo para la accionante persiste.'
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja los derechos', legal: d => `TUTELAR los derechos fundamentales a la vida, la integridad personal, a una vida libre de violencias y al acceso a la justicia de ${R.actor(d).nom}${d.hijos === 'si' ? ' y de sus hijos' : ''}.` },
      { v: 'actuar', inicial: true, t: 'Que ordene a la entidad actuar de inmediato (dictar o hacer cumplir la medida, impulsar la investigación, atender)', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes a la notificación del fallo, ${d.quienFalla === 'comisaria' ? 'avoque conocimiento, dicte las medidas de protección provisionales y definitivas que la situación exige y adelante el incidente de incumplimiento contra el agresor' : d.quienFalla === 'fiscalia' ? 'impulse la investigación, practique las pruebas pendientes y solicite al juez de control de garantías las medidas de protección y de aseguramiento necesarias' : d.quienFalla === 'policia' ? 'disponga la protección efectiva de la accionante (rondas, acompañamiento y atención prioritaria de sus llamados) y haga cumplir la medida de protección vigente' : d.quienFalla === 'salud' ? 'garantice la atención médica y psicológica integral de la accionante y de sus hijos' : d.quienFalla === 'alcaldia' ? 'garantice a la accionante y a sus hijos las medidas de atención (casa de refugio o subsidio de habitación, alimentación y transporte)' : 'adopte las medidas de protección y atención que la situación exige'}, con enfoque de género y debida diligencia.` },
      { v: 'genero', inicial: true, t: 'Que ordene tratarme con respeto, sin revictimizarme ni obligarme a conciliar', legal: d => `ORDENAR a ${R.entidad(d)} abstenerse de revictimizar a la accionante, de poner en duda su relato sin fundamento y de citarla a conciliación o confrontarla con el agresor sin su consentimiento (artículo 8 de la Ley 1257 de 2008).` },
      { v: 'atencion', inicial: d => d.quienFalla !== 'salud', t: 'Que ordene atención médica y psicológica', legal: 'ORDENAR a la EPS o a la Secretaría de Salud competente brindar atención médica y psicológica inmediata a la accionante y a sus hijos (artículos 13 y 19 de la Ley 1257 de 2008).' },
      { v: 'copias', t: 'Que compulse copias a la Procuraduría por la omisión de los funcionarios', legal: 'COMPULSAR copias a la Procuraduría General de la Nación para que investigue disciplinariamente a los funcionarios responsables de la omisión.' },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` }
    ],
    medida: d => `Solicito como MEDIDA PROVISIONAL (artículo 7 del Decreto 2591 de 1991) que se ordene a ${R.entidad(d)} adoptar de inmediato las medidas de protección necesarias (orden de alejamiento y de no contacto al agresor, vigilancia policial y atención en salud), pues esperar el fallo puede costar la vida o la integridad de la accionante: ${R.oracion(d.medidaTexto || d.riesgoActual)}`,
    anexos: [
      { v: 'cedula', t: 'Copia de la cédula' },
      { v: 'solicitudes', t: 'Denuncias o solicitudes de protección radicadas (con sello o número)' },
      { v: 'medida', t: 'Medida de protección dictada (si existe) y pruebas de que el agresor la incumple' },
      { v: 'medicina', t: 'Dictámenes de Medicina Legal o historia clínica' },
      { v: 'mensajes', t: 'Mensajes, audios, fotos, llamadas al 123' },
      { v: 'registros', t: 'Registros civiles de los hijos', si: d => d.hijos === 'si' }
    ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'Marca "la situación es urgente" en la sección de medidas provisionales: el juez puede ordenar protección el mismo día. Lleva copia de todo lo que radicaste antes. La Personería o la Defensoría del Pueblo pueden presentar la tutela contigo.', siNoResponden: 'Incidente de desacato ante el mismo juez si la entidad no cumple; impugnación en 3 días si niegan la tutela.' }
  },

  /* ---------------- DECLARACIÓN JURAMENTADA DE MADRE CABEZA DE FAMILIA ---------------- */
  {
    id: 'muj_declaracion_cabeza', tipo: 'contrato', categoria: 'particular', modulo: 'mujer', unilateral: true,
    titulo: 'Declaración juramentada de madre (o padre) cabeza de familia',
    resumen: 'Documento para acreditar que eres madre cabeza de familia ante programas de vivienda, educación, empleo, subsidios o tu empleador. Se firma ante notario sin costo (Ley 1232 de 2008).',
    palabras: ['madre cabeza de familia', 'madre cabeza de hogar', 'padre cabeza de familia', 'declaración juramentada', 'declaración extrajuicio', 'notaría', 'jefe de hogar', 'sola con mis hijos', 'subsidio', 'vivienda', 'retén social'],
    tituloDoc: (d, P) => d.genero === 'm' ? 'DECLARACIÓN JURAMENTADA DE PADRE CABEZA DE FAMILIA' : 'DECLARACIÓN JURAMENTADA DE MADRE CABEZA DE FAMILIA',
    nombreContrato: 'declaración', tituloClausulas: 'DECLARACIONES',
    roles: d => ({ a: d.genero === 'm' ? 'EL DECLARANTE' : 'LA DECLARANTE', b: '' }),
    campos: [
      { id: 'infoDecl', tipo: 'info', texto: 'La ley (Ley 82 de 1993, modificada por la Ley 1232 de 2008) dice que eres madre cabeza de familia si tienes a tu cargo, de forma permanente, hijos menores u otras personas que no pueden trabajar, y no cuentas con la ayuda del padre ni de otros familiares. La declaración se presenta ante notario, que no puede cobrarte por ella. Si eres padre en la misma situación, también puedes usarla.' },
      { id: 'dependientes', tipo: 'textarea', etiqueta: 'Personas que dependen de ti (nombre, edad, parentesco y documento)', requerido: true, filas: 3, ejemplo: 'Ej.:\nSara Valentina Gómez Ruiz, 8 años, mi hija, TI 1.030.456.789\nJuan David Gómez Ruiz, 4 años, mi hijo, RC 123456' },
      { id: 'razon', tipo: 'select', etiqueta: '¿Por qué no cuentas con el apoyo del padre (o madre) de tus hijos?', requerido: true, opciones: [
        { v: 'abandono', t: 'Se fue y no responde económicamente', legal: 'su ausencia permanente, pues abandonó el hogar y no cumple sus obligaciones' },
        { v: 'fallecio', t: 'Falleció', legal: 'su fallecimiento' },
        { v: 'desconocido', t: 'Nunca reconoció ni se hizo cargo', legal: 'que nunca reconoció a los hijos ni asumió obligación alguna' },
        { v: 'incapacidad', t: 'Tiene una incapacidad física o mental que le impide trabajar', legal: 'su incapacidad física o mental para trabajar' },
        { v: 'carcel', t: 'Está privado de la libertad', legal: 'su privación de la libertad' },
        { v: 'separados', t: 'Estamos separados y no cumple con la cuota', legal: 'la separación y su sustracción de la obligación alimentaria' },
        { v: 'otra', t: 'Otra razón (explícala abajo)', legal: 'su ausencia permanente' }
      ], ancho: 'completa' },
      { id: 'razonDetalle', tipo: 'textarea', etiqueta: 'Detalles (opcional): desde cuándo, qué ha pasado', filas: 2 },
      { id: 'otrosApoyos', tipo: 'radio', etiqueta: '¿Algún otro familiar (abuelos, hermanos) aporta de forma importante al sostenimiento del hogar?', requerido: true, opciones: [ { v: 'no', t: 'No, el sostenimiento depende de mí' }, { v: 'poco', t: 'Ayudan de vez en cuando, pero no alcanza' } ] },
      { id: 'estadoCivil', tipo: 'select', etiqueta: 'Estado civil', opciones: [ { v: 'soltera', t: 'Soltera / soltero', legal: 'soy soltero(a)' }, { v: 'casada', t: 'Casada / casado', legal: 'soy casado(a)' }, { v: 'union', t: 'Unión libre (compañero permanente)', legal: 'vivo en unión marital de hecho' }, { v: 'separada', t: 'Separada / separado', legal: 'estoy separado(a)' }, { v: 'divorciada', t: 'Divorciada / divorciado', legal: 'soy divorciado(a)' }, { v: 'viuda', t: 'Viuda / viudo', legal: 'soy viudo(a)' } ], valorInicial: 'soltera', ancho: 'media' },
      { id: 'ingresos', tipo: 'texto', etiqueta: '¿De qué vives y cuánto ganas al mes, aproximadamente?', ejemplo: 'Ej.: Vendo arepas, unos 600.000 al mes', ancho: 'media' },
      { id: 'vivienda', tipo: 'select', etiqueta: '¿Dónde vives?', opciones: [ { v: 'arriendo', t: 'En arriendo', legal: 'en una vivienda arrendada' }, { v: 'familiar', t: 'En casa de un familiar', legal: 'en la vivienda de un familiar' }, { v: 'propia', t: 'En casa propia', legal: 'en vivienda propia' }, { v: 'posesion', t: 'En un lote o casa sin escrituras', legal: 'en una vivienda sin título de propiedad' }, { v: 'otro', t: 'Otra situación', legal: 'en la vivienda que ocupa actualmente' } ], valorInicial: 'arriendo', ancho: 'media' },
      { id: 'paraQue', tipo: 'texto', etiqueta: '¿Ante quién o para qué la vas a presentar?', ejemplo: 'Ej.: Subsidio de vivienda de la Alcaldía / Universidad / ICETEX / mi empleador / Prosperidad Social', ancho: 'media' }
    ],
    intro: (d, P) => `Yo, ${P.A.ident}, bajo la gravedad del juramento y con pleno conocimiento de las consecuencias penales de faltar a la verdad (artículo 442 del Código Penal), DECLARO:`,
    clausulas: (d, P) => {
      const f = d.genero === 'm';
      const rol = f ? 'padre' : 'madre';
      const otro = f ? 'la madre' : 'el padre';
      return [
        { t: 'Condición', c: `Soy ${f ? 'padre' : 'mujer'} cabeza de familia en los términos del artículo 2 de la Ley 82 de 1993, modificado por el artículo 1 de la Ley 1232 de 2008: ejerzo la jefatura de mi hogar y tengo bajo mi cargo, afectiva, económica y socialmente y de forma permanente, a las personas que se relacionan a continuación.` },
        { t: 'Personas a mi cargo', c: R.relatoAHechos(d.dependientes).join(' ') || '[Personas a cargo]' },
        { t: 'Ausencia de apoyo', c: `No cuento con el apoyo de ${otro} de mis hijos por ${R.opcionTexto(cd('muj_declaracion_cabeza', 'razon'), d.razon)}${d.razonDetalle ? `: ${R.oracion(d.razonDetalle)}` : '.'} ${d.otrosApoyos === 'poco' ? 'La ayuda de otros miembros de mi familia es ocasional y sustancialmente insuficiente para el sostenimiento del hogar.' : 'Ningún otro miembro de mi núcleo familiar aporta al sostenimiento del hogar, que depende exclusivamente de mí.'}` },
        { t: 'Situación personal y económica', c: `${R.capital(R.generizar(R.opcionTexto(cd('muj_declaracion_cabeza', 'estadoCivil'), d.estadoCivil), d.genero))}. ${d.ingresos ? `Mis ingresos provienen de: ${R.oracion(d.ingresos)} ` : ''}Vivo con las personas a mi cargo ${R.opcionTexto(cd('muj_declaracion_cabeza', 'vivienda'), d.vivienda)}.` },
        { t: 'Destino de la declaración', c: `Esta declaración se destina a: ${d.paraQue || 'las entidades que la requieran'}. Tiene por objeto acreditar mi condición de ${rol} cabeza de familia y acceder a los derechos y beneficios que la ley reconoce a esta población. Me comprometo a informar cualquier cambio en las circunstancias aquí declaradas, conforme al artículo 1 de la Ley 1232 de 2008.` }
      ];
    },
    cierre: (d, P) => `Para constancia firmo en ${d.ciudad || '[ciudad]'}, el ${R.fechaLarga(d.fechaFirma) || R.fechaLarga(R.hoy())}.`,
    firmas: (d, P) => [{ rol: P.A.rol, lines: P.A.firma }],
    guia: { nota: 'La condición de madre cabeza de familia se declara ante notario y, por el artículo 1 de la Ley 1232 de 2008, ese trámite no causa emolumentos notariales: es gratis. Si te cobran, muéstrales la ley. Muchas entidades aceptan también la declaración firmada con copia de la cédula, sin notaría: pregunta antes.', pasos: ['Imprime la declaración y llévala a cualquier notaría con tu cédula y los registros civiles de tus hijos; firma frente al notario.', 'Entrega la declaración autenticada a la entidad junto con los registros civiles.', 'Guarda copias: te sirven para otros trámites (vivienda, educación, retén social, créditos, Prosperidad Social, ICBF).'] }
  },

  /* ---------------- PETICIÓN: PRIORIDAD COMO MADRE CABEZA DE FAMILIA ---------------- */
  {
    id: 'muj_cabeza_familia', tipo: 'peticion', categoria: 'municipio', modulo: 'mujer',
    titulo: 'Petición para que reconozcan tu condición de madre cabeza de familia (vivienda, educación, empleo, subsidios, trabajo)',
    resumen: 'Para que una entidad, un programa o tu empleador apliquen la protección y la prioridad que la ley da a las madres (y padres) cabeza de familia: inscripción, priorización, revisión de una negativa o información.',
    palabras: ['madre cabeza de familia', 'cabeza de hogar', 'prioridad', 'subsidio de vivienda', 'Mi Casa Ya', 'ICETEX', 'universidad', 'SENA', 'empleo', 'Renta Ciudadana', 'retén social', 'reestructuración', 'no me priorizan', 'me excluyeron'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Alcaldía de Soacha – Secretaría de Vivienda / ICETEX / Prosperidad Social / Empresa donde trabajo' },
    campos: [
      { id: 'programa', tipo: 'select', etiqueta: '¿Para qué trámite o programa?', requerido: true, opciones: [
        { v: 'vivienda', t: 'Subsidio o programa de vivienda', legal: 'el programa de vivienda' },
        { v: 'educacion', t: 'Cupo, beca, crédito educativo o condonación (para mí o para mis hijos)', legal: 'el acceso a la educación (cupo, beca, crédito o condonación)' },
        { v: 'empleo', t: 'Empleo, capacitación o proyecto productivo', legal: 'el programa de empleo, capacitación o emprendimiento' },
        { v: 'subsidio', t: 'Subsidio o transferencia (Renta Ciudadana, Colombia Mayor, ICBF, Alcaldía)', legal: 'el programa social o subsidio' },
        { v: 'laboral', t: 'Protección en mi trabajo (retén social, reestructuración, horario compatible con el cuidado)', legal: 'la protección laboral reforzada como madre cabeza de familia' },
        { v: 'otro', t: 'Otro trámite', legal: 'el trámite' }
      ], ancho: 'completa' },
      { id: 'tramite', tipo: 'select', etiqueta: '¿Qué pides?', requerido: true, opciones: [
        { v: 'inscribir', t: 'Que me inscriban o me incluyan', legal: 'la inscripción o inclusión' },
        { v: 'priorizar', t: 'Que me den la prioridad que la ley ordena', legal: 'la aplicación de la prioridad legal' },
        { v: 'estado', t: 'Que me informen el estado de mi solicitud', legal: 'información sobre el estado de la solicitud' },
        { v: 'revisar', t: 'Que revisen la negativa o mi exclusión', legal: 'la revisión de la negativa o exclusión' }
      ], ancho: 'media' },
      { id: 'declaracion', tipo: 'radio', etiqueta: '¿Tienes la declaración juramentada de madre cabeza de familia?', requerido: true, ancho: 'media', opciones: [ { v: 'si', t: 'Sí, la anexo' }, { v: 'no', t: 'Todavía no' } ] },
      { id: 'infoDecl', tipo: 'info', mostrarSi: { campo: 'declaracion', valor: 'no' }, texto: 'Crea primero la "Declaración juramentada de madre cabeza de familia" (está en este mismo módulo), fírmala ante notario (gratis) y anéxala a esta petición: es la prueba que las entidades piden.' },
      { id: 'dependientes', tipo: 'textarea', etiqueta: 'Personas a tu cargo (nombre, edad, parentesco)', requerido: true, filas: 2 },
      { id: 'detalle', tipo: 'textarea', etiqueta: 'Explica tu caso: programa o convocatoria, radicado, qué te dijeron y qué necesitas', requerido: true, filas: 4, ejemplo: 'Ej.:\nMe inscribí en la convocatoria de vivienda de 2026 (radicado 4455).\nEn la lista de priorizados quedé de 320, sin tener en cuenta que soy madre cabeza de familia.\nTengo dos hijos y vivo en arriendo con Sisbén A3.' },
      ...C.previo()
    ],
    asunto: d => `Solicitud de ${R.opcionTexto(cd('muj_cabeza_familia', 'tramite'), d.tramite)} en ${R.opcionTexto(cd('muj_cabeza_familia', 'programa'), d.programa)} – Condición de madre cabeza de familia (Ley 82 de 1993)`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} es ${R.terminacion(a.g, 'padre', 'madre')} cabeza de familia en los términos de la Ley 82 de 1993, modificada por la Ley 1232 de 2008: tiene a su cargo, de forma permanente y sin apoyo del otro progenitor, a ${R.relatoAHechos(d.dependientes).join(' ') || '[personas a cargo]'}${d.declaracion === 'si' ? ', condición que acredita con la declaración juramentada que se anexa' : ''}.`);
      h.push(...R.relatoAHechos(d.detalle));
      h.push(...R.hechosPrevio(d, R.opcionTexto(cd('muj_cabeza_familia', 'tramite'), d.tramite)));
      return h;
    },
    normas: d => ['cp13', 'cp42', 'cp43', 'l82', d.programa === 'vivienda' ? 'l1537_12' : null, 'cp23', 'l1755_14'].filter(Boolean),
    fundamentos: d => d.programa === 'laboral' ? ['La Corte Constitucional ha reconocido que las madres y los padres cabeza de familia gozan de estabilidad laboral reforzada en los procesos de reestructuración, liquidación o supresión de cargos de las entidades públicas ("retén social", sentencias SU-388 y SU-389 de 2005), y que los empleadores deben tener en cuenta sus responsabilidades de cuidado al fijar turnos y condiciones de trabajo, en desarrollo de los artículos 42, 43 y 53 de la Constitución.'] : [],
    peticiones: [
      { v: 'reconocer', inicial: true, fijo: true, t: 'Que reconozcan mi condición de madre cabeza de familia en este trámite', legal: d => `Reconocer y aplicar en ${R.opcionTexto(cd('muj_cabeza_familia', 'programa'), d.programa)} la condición de ${R.terminacion(R.actor(d).g, 'padre', 'madre')} cabeza de familia de ${R.actor(d).nom}, con la especial protección y la prioridad que ordenan la Ley 82 de 1993 y la Ley 1232 de 2008.` },
      { v: 'tramite', inicial: true, t: 'Lo que pediste arriba', legal: d => `Resolver de fondo ${R.opcionTexto(cd('muj_cabeza_familia', 'tramite'), d.tramite)} solicitada, con decisión motivada y por escrito.` },
      { v: 'requisitos', inicial: true, t: 'Que me informen por escrito los requisitos, los plazos y el estado de mi solicitud', legal: 'Informar por escrito los requisitos, los plazos, los criterios de priorización aplicados y el estado actual de la solicitud.' },
      { v: 'diferencial', t: 'Que apliquen enfoque diferencial de género en la decisión', legal: 'Aplicar el enfoque diferencial de género y la protección reforzada de las mujeres cabeza de familia en la valoración de la solicitud, conforme al artículo 43 de la Constitución.' }
    ],
    anexos: [ { v: 'declaracion', t: 'Declaración juramentada de madre cabeza de familia' }, { v: 'registros', t: 'Registros civiles de los hijos o personas a cargo' }, { v: 'cedula', t: 'Copia de la cédula' }, { v: 'sisben', t: 'Consulta del Sisbén' }, { v: 'radicados', t: 'Radicados, cartas o respuestas anteriores de la entidad' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Anexa siempre la declaración juramentada. Si la entidad niega la prioridad, pide la respuesta por escrito: con ella puedes presentar recurso o tutela.', siNoResponden: 'Tutela por derecho de petición si no responden en 15 días hábiles; recurso de reposición si responden negando.' }
  },

  /* ---------------- PETICIÓN: LICENCIA DE MATERNIDAD ---------------- */
  {
    id: 'muj_licencia_maternidad', tipo: 'peticion', categoria: 'eps', modulo: 'mujer',
    titulo: 'Petición a la EPS o al empleador por la licencia de maternidad no pagada',
    resumen: 'Tuviste a tu bebé y la EPS no paga la licencia (18 semanas), la negó por "semanas de cotización" o por mora del empleador, o el empleador no la tramita ni te la paga.',
    palabras: ['licencia de maternidad', 'no me pagan la licencia', 'parto', 'bebé', 'recién nacido', 'EPS', 'empleador', '18 semanas', 'incapacidad de maternidad', 'cotización', 'mora del empleador', 'independiente', 'licencia de paternidad'],
    destinatario: { categoria: 'eps', ejemploNombre: 'Ej.: EPS Sanitas / Confecciones del Norte S.A.S. (empleador)' },
    campos: [
      { id: 'quien', tipo: 'select', etiqueta: '¿A quién le reclamas?', ayuda: 'Si reclamas al empleador, arriba en "¿A quién va dirigido?" elige "Empleador o empresa privada" y escribe su nombre.', requerido: true, opciones: [
        { v: 'eps_no_paga', t: 'A la EPS: no ha pagado la licencia o la demora', legal: 'la EPS no ha reconocido ni pagado la licencia de maternidad' },
        { v: 'eps_nego', t: 'A la EPS: la negó (por semanas de cotización, mora del empleador u otro motivo)', legal: 'la EPS negó la licencia de maternidad' },
        { v: 'empleador_no_paga', t: 'Al empleador: no me ha pagado la licencia ni la ha tramitado', legal: 'el empleador no ha pagado ni tramitado la licencia de maternidad' },
        { v: 'empleador_no_afilio', t: 'Al empleador: no me afilió o no pagó los aportes a la EPS', legal: 'el empleador no realizó la afiliación ni los aportes al sistema de salud' }
      ], ancho: 'completa' },
      { id: 'infoQuien', tipo: 'info', texto: 'Si tu empleador no te afilió o no pagó los aportes, él debe pagarte la licencia completa. Si la EPS la negó por "mora del empleador" pero venía recibiendo los pagos atrasados sin reclamar, no puede negarla. Si cotizaste solo una parte del embarazo, deben pagarla en proporción, no negarla.' },
      { id: 'vinculo', tipo: 'select', etiqueta: 'Tu vinculación', opciones: [ { v: 'dependiente', t: 'Empleada (con contrato o sin él)', legal: 'trabajadora dependiente' }, { v: 'independiente', t: 'Independiente que cotiza por su cuenta', legal: 'trabajadora independiente cotizante' }, { v: 'domestica', t: 'Empleada doméstica', legal: 'trabajadora del servicio doméstico' } ], valorInicial: 'dependiente', ancho: 'media' },
      { id: 'empleador', tipo: 'texto', etiqueta: 'Nombre de tu empleador', mostrarSi: { campo: 'vinculo', valores: ['dependiente', 'domestica'] }, ancho: 'media' },
      { id: 'fechaParto', tipo: 'fecha', etiqueta: 'Fecha del parto', requerido: true, ancho: 'media' },
      { id: 'inicioLicencia', tipo: 'fecha', etiqueta: 'Fecha de inicio de la licencia (según la incapacidad médica)', ancho: 'media' },
      { id: 'tipoParto', tipo: 'select', etiqueta: 'Tipo de parto', opciones: [ { v: 'unico', t: 'Un bebé, a término', legal: 'parto único a término' }, { v: 'multiple', t: 'Parto múltiple (gemelos, trillizos)', legal: 'parto múltiple' }, { v: 'prematuro', t: 'Bebé prematuro', legal: 'parto prematuro' } ], valorInicial: 'unico', ancho: 'media' },
      { id: 'salario', tipo: 'texto', etiqueta: 'Tu salario o ingreso base de cotización mensual', requerido: true, ancho: 'media' },
      { id: 'tiempoCotizado', tipo: 'texto', etiqueta: '¿Cuánto tiempo llevas cotizando a esa EPS?', ejemplo: 'Ej.: 14 meses / solo 5 meses del embarazo', ancho: 'media' },
      { id: 'respuesta', tipo: 'texto', etiqueta: '¿Qué te han dicho? (razón de la negativa o de la demora)', ancho: 'completa' },
      { id: 'afectacion', tipo: 'textarea', etiqueta: '¿Cómo te afecta no recibir el pago? (único ingreso, gastos del bebé, arriendo)', requerido: true, filas: 3 },
      ...C.previo({ etiqueta: '¿Ya habías reclamado la licencia por escrito?' })
    ],
    asunto: d => 'Solicitud de reconocimiento y pago de la licencia de maternidad – Artículo 236 del Código Sustantivo del Trabajo',
    hechos: d => {
      const a = R.actor(d);
      const esEps = (d.quien || '').startsWith('eps');
      const h = [];
      h.push(`${a.Nom} es ${R.opcionTexto(cd('muj_licencia_maternidad', 'vinculo'), d.vinculo)}${d.empleador && d.vinculo !== 'independiente' ? `, vinculada a ${R.mayus(d.empleador)}` : ''}, ${esEps ? `afiliada al sistema de salud a través de ${R.entidad(d)}` : 'afiliada (o que debió estar afiliada) al sistema de salud'}, con un ingreso base de cotización de ${R.moneda(d.salario) || d.salario || '[salario]'} mensuales.`);
      h.push(`${R.capital(R.elDia(d.fechaParto))} tuvo lugar el parto (${R.opcionTexto(cd('muj_licencia_maternidad', 'tipoParto'), d.tipoParto)})${d.inicioLicencia ? `, y la licencia de maternidad inició ${R.elDia(d.inicioLicencia)}` : ', con la correspondiente incapacidad médica de maternidad'}.`);
      if (d.tiempoCotizado) h.push(`${a.Nom} ha cotizado al sistema durante ${d.tiempoCotizado}.`);
      h.push(`${R.capital(R.opcionTexto(cd('muj_licencia_maternidad', 'quien'), d.quien))}${d.respuesta ? `, con el siguiente argumento: ${R.oracion(d.respuesta)}` : '.'}`);
      h.push(`La falta de pago afecta gravemente a la madre y al recién nacido: ${R.oracion(d.afectacion)}`);
      h.push(...R.hechosPrevio(d, 'el pago de la licencia de maternidad'));
      return h;
    },
    normas: ['cp43', 'cp44', 'cp53', 'cst_236', 'lic_pago', 'cp23'],
    fundamentos: d => {
      const f = [];
      if (d.quien === 'empleador_no_afilio') f.push('Cuando el empleador no afilia a la trabajadora al sistema de salud o no paga los aportes, asume directamente el pago de la licencia de maternidad y de las demás prestaciones que el sistema habría reconocido, sin perjuicio de las sanciones por evasión (Ley 100 de 1993 y Decreto 780 de 2016).');
      if (d.quien === 'eps_nego') f.push('La EPS no puede negar la licencia en su totalidad por una cotización incompleta durante el embarazo: debe reconocerla en proporción al tiempo cotizado (artículo 2.1.13.1 del Decreto 780 de 2016). Tampoco puede negarla por mora del empleador cuando recibió los aportes extemporáneos sin objetarlos ("allanamiento a la mora"), según jurisprudencia reiterada de la Corte Constitucional.');
      f.push('La licencia de maternidad protege el mínimo vital de la madre y del recién nacido y el derecho de este a recibir cuidado y amor en sus primeros meses de vida (artículos 43 y 44 de la Constitución). La Corte Constitucional ha reiterado que su pago es exigible por tutela cuando la madre carece de otros ingresos, siempre que se reclame dentro del año siguiente al nacimiento.');
      return f;
    },
    peticiones: [
      { v: 'pagar', inicial: true, fijo: true, t: 'Que reconozcan y paguen la licencia completa', legal: d => `Reconocer y pagar de inmediato la licencia de maternidad de ${d.tipoParto === 'multiple' ? 'veinte (20)' : 'dieciocho (18)'} semanas${d.tipoParto === 'prematuro' ? ', más la diferencia entre la fecha del parto prematuro y la fecha probable de parto' : ''}, liquidada sobre el ingreso base de cotización de ${R.moneda(d.salario) || d.salario || '[salario]'} mensuales.` },
      { v: 'tramitar', inicial: d => (d.quien || '').startsWith('empleador'), t: 'Que el empleador haga el trámite ante la EPS y me pague sin esperar el reembolso', legal: 'Adelantar directamente ante la EPS el trámite de reconocimiento de la licencia (artículo 121 del Decreto Ley 019 de 2012) y pagarla a la trabajadora en las fechas habituales de pago del salario, sin trasladarle la carga del trámite ni esperar el reembolso.' },
      { v: 'proporcional', inicial: d => d.quien === 'eps_nego', t: 'En subsidio, que la paguen en proporción al tiempo cotizado', legal: 'En subsidio, reconocer la licencia en forma proporcional al tiempo cotizado durante la gestación, conforme al artículo 2.1.13.1 del Decreto 780 de 2016.' },
      { v: 'afiliar', inicial: d => d.quien === 'empleador_no_afilio', t: 'Que me afilien a salud, pensión y riesgos y paguen los aportes atrasados', legal: 'Afiliar a la trabajadora al Sistema de Seguridad Social Integral y pagar los aportes adeudados con los intereses de mora, conforme a la Ley 100 de 1993.' },
      { v: 'liquidacion', inicial: true, t: 'Que me entreguen por escrito la liquidación y la fecha de pago', legal: 'Informar por escrito la liquidación de la licencia, el valor reconocido y la fecha de pago.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'registro', t: 'Registro civil de nacimiento del bebé' }, { v: 'incapacidad', t: 'Incapacidad o licencia de maternidad expedida por el médico' }, { v: 'afiliacion', t: 'Certificado de afiliación y planilla de pagos (PILA)' }, { v: 'contrato', t: 'Contrato de trabajo o desprendibles de pago' }, { v: 'respuesta', t: 'Respuesta de la EPS o del empleador (si la hay)' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Reclama por escrito y guarda el radicado. Si la EPS no paga, presenta la tutela antes de que el bebé cumpla un año. El padre tiene derecho a dos semanas de licencia de paternidad (Ley 2114 de 2021): se reclaman igual.', siNoResponden: 'Tutela por el mínimo vital de la madre y del bebé (en esta plataforma: "Tutela por salud" o "Tutela por derecho de petición") y queja ante la Supersalud (EPS) o el Ministerio del Trabajo (empleador).' }
  },

  /* ---------------- QUEJA: ACOSO LABORAL O ACOSO SEXUAL EN EL TRABAJO ---------------- */
  {
    id: 'muj_acoso_laboral', tipo: 'queja', categoria: 'empleador', modulo: 'mujer', rolQueja: 'trabajador(a) (Ley 1010 de 2006, Ley 1257 de 2008 y Ley 2365 de 2024)',
    titulo: 'Queja por acoso laboral o acoso sexual en el trabajo (Comité de Convivencia, empleador o Ministerio del Trabajo)',
    resumen: 'Tu jefe, un compañero o un cliente te acosa sexualmente, te maltrata, te persigue o te discrimina por ser mujer, estar embarazada o tener hijos. La queja obliga a la empresa a actuar y te protege contra represalias.',
    palabras: ['acoso laboral', 'acoso sexual', 'jefe', 'compañero de trabajo', 'me acosa', 'insinuaciones', 'tocamientos', 'gritos', 'humillaciones', 'persecución', 'discriminación', 'embarazo', 'comité de convivencia', 'Ministerio del Trabajo', 'represalias', 'Ley 1010'],
    destinatario: { categoria: 'empleador', ejemploNombre: 'Ej.: Comité de Convivencia Laboral de Confecciones del Norte S.A.S. / Ministerio del Trabajo – Dirección Territorial Antioquia', cargo: 'Comité de Convivencia Laboral / Gerencia / Talento Humano' },
    campos: [
      { id: 'aQuien', tipo: 'select', etiqueta: '¿Ante quién presentas la queja?', ayuda: 'Si la presentas al Ministerio del Trabajo o a la Procuraduría, arriba elige "Entidad del Gobierno nacional" y escribe su nombre.', requerido: true, opciones: [
        { v: 'comite', t: 'Al Comité de Convivencia Laboral de la empresa (primer paso recomendado)', legal: 'el Comité de Convivencia Laboral' },
        { v: 'empleador', t: 'Al empleador (gerencia o talento humano): no hay comité o el acosador es el dueño', legal: 'el empleador' },
        { v: 'mintrabajo', t: 'Al Ministerio del Trabajo (inspector): la empresa no actuó o el acoso continúa', legal: 'el inspector de trabajo' },
        { v: 'procuraduria', t: 'A la Procuraduría o a control interno disciplinario (soy servidora pública)', legal: 'la Procuraduría General de la Nación' }
      ], ancho: 'completa' },
      { id: 'empresa', tipo: 'texto', etiqueta: 'Empresa o entidad donde trabajas', requerido: true, ancho: 'media' },
      { id: 'cargo', tipo: 'texto', etiqueta: 'Tu cargo', ancho: 'media' },
      { id: 'fechaIngreso', tipo: 'fecha', etiqueta: 'Fecha de ingreso', ancho: 'media' },
      { id: 'acosador', tipo: 'texto', etiqueta: 'Nombre y cargo de quien te acosa', requerido: true, ancho: 'media' },
      { id: 'jerarquia', tipo: 'select', etiqueta: '¿Qué es esa persona respecto a ti?', requerido: true, opciones: [ { v: 'jefe', t: 'Mi jefe o superior', legal: 'su superior jerárquico' }, { v: 'companero', t: 'Un compañero de trabajo', legal: 'su compañero de trabajo' }, { v: 'dueno', t: 'El dueño o representante de la empresa', legal: 'el empleador o su representante' }, { v: 'subalterno', t: 'Un subalterno', legal: 'su subalterno' }, { v: 'cliente', t: 'Un cliente, proveedor o contratista', legal: 'un cliente, proveedor o contratista de la empresa' } ], ancho: 'media' },
      { id: 'conductas', tipo: 'checks', etiqueta: '¿Qué conductas sufres?', requerido: true, opciones: [
        { v: 'sexual', t: 'Acoso sexual: insinuaciones, propuestas, tocamientos, mensajes o fotos de contenido sexual', legal: 'acoso sexual (insinuaciones, propuestas, tocamientos y mensajes de contenido sexual no consentidos)' },
        { v: 'chantaje', t: 'Me condicionan el trabajo, el ascenso o el contrato a favores sexuales', legal: 'condicionamiento de beneficios laborales a favores sexuales' },
        { v: 'maltrato', t: 'Gritos, insultos, humillaciones delante de otros', legal: 'maltrato laboral (gritos, insultos y humillaciones)' },
        { v: 'persecucion', t: 'Persecución: cargas excesivas, cambios de turno arbitrarios, vigilancia, llamados de atención injustificados', legal: 'persecución laboral' },
        { v: 'discriminacion', t: 'Discriminación por ser mujer, estar embarazada o tener hijos', legal: 'discriminación laboral por razón de género, embarazo o maternidad' },
        { v: 'entorpecimiento', t: 'Me quitan herramientas, información o funciones para que no pueda trabajar', legal: 'entorpecimiento laboral' },
        { v: 'inequidad', t: 'Me asignan funciones o salario inferiores a los de otros con el mismo cargo', legal: 'inequidad laboral' },
        { v: 'represalias', t: 'Represalias por haber denunciado o por no aceptar propuestas', legal: 'represalias por haberse negado a las propuestas o por haber denunciado' }
      ] },
      { id: 'desde', tipo: 'fecha', etiqueta: '¿Desde cuándo?', ancho: 'media' },
      { id: 'ultimoHecho', tipo: 'fecha', etiqueta: 'Fecha del último hecho', requerido: true, ancho: 'media' },
      { id: 'relatoHechos', tipo: 'textarea', etiqueta: 'Describe los hechos: fechas, lugares, palabras exactas, qué hiciste tú', ayuda: 'Una línea por hecho, en orden de fechas. Sé concreta: la ley exige que las conductas sean "demostrables".', requerido: true, filas: 6, ejemplo: 'Ej.:\nEl 12 de agosto de 2026 el supervisor me dijo en la bodega que "si quería el turno de día tenía que ser más cariñosa".\nEl 3 de septiembre me tocó la cintura delante de dos compañeras.\nDesde que le dije que no, me cambió al turno de la noche y me grita por todo.' },
      { id: 'testigosDatos', tipo: 'texto', etiqueta: 'Testigos (nombres y cargos)', ancho: 'completa' },
      { id: 'pruebas', tipo: 'texto', etiqueta: 'Pruebas que tienes (chats, correos, audios, incapacidades, quejas anteriores)', ancho: 'completa' },
      { id: 'afectacion', tipo: 'textarea', etiqueta: '¿Cómo te ha afectado? (salud, ansiedad, incapacidades, miedo a ir a trabajar)', filas: 3 },
      { id: 'quejaPrevia', tipo: 'radio', etiqueta: '¿Ya lo habías informado a alguien en la empresa?', requerido: true, opciones: SI_NO, ancho: 'media' },
      { id: 'quejaPreviaDetalle', tipo: 'texto', etiqueta: '¿A quién, cuándo y qué pasó?', mostrarSi: { campo: 'quejaPrevia', valor: 'si' }, ancho: 'media' }
    ],
    asunto: d => { const s = (d.conductas || []).some(v => ['sexual', 'chantaje'].includes(v)); return `Queja por ${s ? 'acoso sexual en el contexto laboral' : 'acoso laboral'} – Ley 1010 de 2006${s ? ', Ley 1257 de 2008 y Ley 2365 de 2024' : ''}`; },
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} trabaja en ${R.mayus(d.empresa) || '[EMPRESA]'}${d.fechaIngreso ? ` desde ${R.fechaLarga(d.fechaIngreso)}` : ''}${d.cargo ? `, en el cargo de ${d.cargo}` : ''}.`);
      h.push(`${d.acosador || '[NOMBRE]'}, ${R.opcionTexto(cd('muj_acoso_laboral', 'jerarquia'), d.jerarquia)}, ha ejercido contra ${a.nom} las siguientes conductas: ${R.lista(marco(d, 'conductas', ['muj_acoso_laboral', 'conductas']))}${d.desde ? `, desde ${R.fechaLarga(d.desde)}` : ''}; el último hecho ocurrió ${R.elDia(d.ultimoHecho)}.`);
      h.push(...R.relatoAHechos(d.relatoHechos));
      if (d.testigosDatos) h.push(`Presenciaron los hechos: ${R.oracion(d.testigosDatos)}`);
      if (d.pruebas) h.push(`Se cuenta con las siguientes pruebas: ${R.oracion(d.pruebas)}`);
      if (d.afectacion) h.push(`Estas conductas han afectado a ${a.nom}: ${R.oracion(d.afectacion)}`);
      if (d.quejaPrevia === 'si') h.push(`Los hechos ya habían sido puestos en conocimiento de la empresa: ${R.oracion(d.quejaPreviaDetalle)}`);
      return h;
    },
    normas: d => { const s = (d.conductas || []).some(v => ['sexual', 'chantaje'].includes(v)); return ['cp25', 'cp13', 'cp43', 'l1010', s ? 'cpen_210a' : null, s || (d.conductas || []).includes('discriminacion') ? 'l1257_2' : null, s ? 'l1257_7' : null, 'cp23'].filter(Boolean); },
    fundamentos: d => ['El empleador está obligado a prevenir y corregir el acoso laboral, a tramitar la queja con confidencialidad y a proteger a la trabajadora frente a represalias (artículos 9 y 11 de la Ley 1010 de 2006). Conforme al artículo 12 de la Ley 1257 de 2008 y a la Ley 2365 de 2024, el acoso sexual en el trabajo es una forma de violencia contra la mujer que el empleador debe atender con enfoque de género, protegiendo a la víctima y remitiendo el caso a la Fiscalía cuando constituya delito.', d.aQuien === 'mintrabajo' ? 'El inspector de trabajo puede conminar preventivamente al empleador para que ponga en marcha los procedimientos de prevención y corrección, e imponer las sanciones del artículo 10 de la Ley 1010 de 2006 (multas, y la obligación de pagar a la trabajadora las atenciones en salud derivadas del acoso).' : ''].filter(Boolean),
    peticiones: [
      { v: 'tramitar', inicial: true, fijo: true, t: 'Que abran el trámite de la queja', legal: d => `Recibir y tramitar esta queja por ${(d.conductas || []).some(v => ['sexual', 'chantaje'].includes(v)) ? 'acoso sexual y acoso laboral' : 'acoso laboral'} conforme a la Ley 1010 de 2006${d.aQuien === 'comite' || d.aQuien === 'empleador' ? ' y a la Resolución 652 de 2012, con confidencialidad y escuchando a la trabajadora' : ''}.` },
      { v: 'separar', inicial: true, t: 'Que me separen del acosador sin perjudicarme (que lo muevan a él, no a mí)', legal: 'Adoptar de inmediato medidas que impidan el contacto entre la víctima y el presunto acosador, sin desmejorar las condiciones laborales de la víctima (sin cambiarle sede, turno, funciones o salario en su contra).' },
      { v: 'investigar', inicial: true, t: 'Que investiguen y sancionen', legal: d => d.aQuien === 'mintrabajo' ? 'Practicar visita de inspección, conminar al empleador y, de comprobarse el acoso, imponer las sanciones del artículo 10 de la Ley 1010 de 2006.' : 'Investigar los hechos, escuchar a los testigos, aplicar las medidas correctivas y sanciones del reglamento interno y de la Ley 1010 de 2006, e informar por escrito el resultado.' },
      { v: 'represalias', inicial: true, fijo: true, t: 'Garantía de no represalias', legal: 'Garantizar que no se tomen represalias contra la trabajadora: conforme al artículo 11 de la Ley 1010 de 2006, la terminación del contrato o la desmejora de sus condiciones dentro de los seis (6) meses siguientes a esta queja carecerá de efecto.' },
      { v: 'fiscalia', inicial: d => (d.conductas || []).some(v => ['sexual', 'chantaje'].includes(v)), t: 'Que remitan el caso a la Fiscalía (acoso sexual es delito)', legal: 'Remitir los hechos a la Fiscalía General de la Nación por el delito de acoso sexual (artículo 210A del Código Penal), sin perjuicio del trámite interno.' },
      { v: 'salud', t: 'Que reporten el caso a la ARL y me den atención psicológica', legal: 'Reportar la situación a la Administradora de Riesgos Laborales (ARL) como riesgo psicosocial y garantizar la atención psicológica de la trabajadora.' },
      { v: 'informar', inicial: true, t: 'Que me informen por escrito el resultado', legal: 'Informar por escrito a la trabajadora las decisiones adoptadas y las medidas de protección implementadas.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'mensajes', t: 'Pantallazos de chats, correos o mensajes' }, { v: 'audios', t: 'Audios o videos' }, { v: 'incapacidades', t: 'Incapacidades o constancias médicas o psicológicas' }, { v: 'previas', t: 'Quejas o comunicaciones anteriores' }, { v: 'contrato', t: 'Contrato de trabajo o certificación laboral' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Las acciones derivadas del acoso laboral tienen un término de caducidad de tres (3) años desde las conductas, conforme al artículo 18 de la Ley 1010, modificado por la Ley 2209 de 2022. Otros mecanismos pueden tener términos distintos; busca orientación para tu caso. Si fue acoso sexual, denuncia también en la Fiscalía (en esta plataforma: "Denuncia penal por violencia contra la mujer"). Guarda copia de la queja con sello de recibido.', siNoResponden: 'Queja ante el Ministerio del Trabajo (inspección laboral, línea 120) o demanda ante el juez laboral. Si hay represalias, solicita orientación para valorar las garantías del artículo 11 de la Ley 1010 y la vía adecuada; su aplicación exige los presupuestos legales.' }
  },

  /* ---------------- PETICIÓN: SALUD SEXUAL Y REPRODUCTIVA ---------------- */
  {
    id: 'muj_salud_sexual', tipo: 'peticion', categoria: 'eps', modulo: 'mujer',
    titulo: 'Petición a la EPS por servicios de salud sexual y reproductiva (control prenatal, parto, anticoncepción, IVE, atención por violencia sexual)',
    resumen: 'La EPS o el hospital no te da el control prenatal, la atención del parto, el método anticonceptivo, la interrupción voluntaria del embarazo o la atención tras una violencia sexual, o te pone requisitos que no existen.',
    palabras: ['embarazo', 'control prenatal', 'ecografía', 'parto', 'posparto', 'anticonceptivos', 'planificación', 'ligadura', 'pomeroy', 'implante', 'DIU', 'IVE', 'aborto', 'interrupción del embarazo', 'violencia sexual', 'citología', 'mamografía', 'EPS', 'salud sexual'],
    destinatario: { categoria: 'eps', ejemploNombre: 'Ej.: Nueva EPS / Hospital San Vicente de Paúl' },
    campos: [
      { id: 'servicio', tipo: 'select', etiqueta: '¿Qué servicio necesitas?', requerido: true, opciones: [
        { v: 'prenatal', t: 'Control prenatal, ecografías, exámenes o medicamentos del embarazo', legal: 'la atención prenatal (controles, ecografías, exámenes y medicamentos)' },
        { v: 'parto', t: 'Atención del parto o del posparto', legal: 'la atención del parto y del posparto' },
        { v: 'anticoncepcion', t: 'Método anticonceptivo (pastillas, inyección, implante, DIU, ligadura de trompas)', legal: 'el método anticonceptivo elegido' },
        { v: 'ive', t: 'Interrupción voluntaria del embarazo (IVE)', legal: 'la interrupción voluntaria del embarazo (IVE)' },
        { v: 'violencia', t: 'Atención integral por violencia sexual', legal: 'la atención integral en salud por violencia sexual' },
        { v: 'tamizaje', t: 'Citología, mamografía o seguimiento de un resultado anormal', legal: 'los exámenes de tamizaje (citología, mamografía) y el seguimiento de sus resultados' },
        { v: 'otro', t: 'Otro servicio de salud sexual y reproductiva', legal: 'el servicio de salud sexual y reproductiva requerido' }
      ], ancho: 'completa' },
      { id: 'infoIve', tipo: 'info', mostrarSi: { campo: 'servicio', valor: 'ive' }, texto: 'La IVE es un servicio de salud al que tienes derecho sin dar explicaciones hasta la semana 24 (sentencia C-055 de 2022) y, después, por las tres causales de la sentencia C-355 de 2006. La EPS debe prestarlo en máximo 5 días. Nadie puede exigirte permiso de tu pareja ni de tus padres, ni juzgarte. Orientación gratuita: Profamilia 018000 110 900.' },
      { id: 'infoViolencia', tipo: 'info', mostrarSi: { campo: 'servicio', valor: 'violencia' }, texto: 'Si sufriste violencia sexual, busca atención en salud lo antes posible, aunque hayan pasado más de 72 horas. No esperes a presentar esta petición ni una denuncia para acudir. El equipo de salud debe valorar la atención integral y las medidas que correspondan según el tiempo transcurrido.' },
      { id: 'detalle', tipo: 'texto', etiqueta: 'Detalle del servicio (lo que ordenó el médico o lo que pides)', requerido: true, ancho: 'completa', ejemplo: 'Ej.: Implante subdérmico / ecografía de detalle anatómico ordenada el 2 de octubre' },
      { id: 'semanas', tipo: 'texto', etiqueta: 'Semanas de embarazo', ancho: 'media', mostrarSi: { campo: 'servicio', valores: ['prenatal', 'parto', 'ive'] } },
      { id: 'fechaSolicitud', tipo: 'fecha', etiqueta: '¿Cuándo lo pediste o cuándo lo ordenó el médico?', ancho: 'media' },
      { id: 'respuesta', tipo: 'select', etiqueta: '¿Qué pasó?', requerido: true, opciones: [
        { v: 'nego', t: 'Me lo negaron', legal: 'negó el servicio' },
        { v: 'cita', t: 'No hay cita o la dan muy lejos (en tiempo o en distancia)', legal: 'no ha asignado la cita o la programó en un plazo o en un lugar que hace inviable la atención' },
        { v: 'requisitos', t: 'Me exigen requisitos que no están en la ley (autorización de la pareja, dictámenes, pagos)', legal: 'exigió requisitos no previstos en la ley' },
        { v: 'objecion', t: 'El médico se negó por "objeción de conciencia" y no me remitieron a otro', legal: 'el profesional alegó objeción de conciencia sin que la entidad garantizara la remisión inmediata a otro profesional' },
        { v: 'maltrato', t: 'Me juzgaron o me trataron mal', legal: 'prestó la atención con juicios y maltrato' },
        { v: 'demora', t: 'Lo autorizaron pero no lo prestan', legal: 'autorizó el servicio pero no lo ha prestado' }
      ], ancho: 'completa' },
      { id: 'afectacion', tipo: 'textarea', etiqueta: '¿Cómo te afecta la demora o la negativa?', requerido: true, filas: 3 },
      ...C.previo()
    ],
    asunto: d => `Solicitud de ${R.opcionTexto(cd('muj_salud_sexual', 'servicio'), d.servicio)} – Derechos sexuales y reproductivos`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} está afiliada a ${R.entidad(d)}${d.semanas ? ` y cursa un embarazo de ${d.semanas} semanas` : ''}.`);
      h.push(`${d.fechaSolicitud ? `${R.capital(R.elDia(d.fechaSolicitud))} ` : ''}${a.Nom} solicitó ${R.opcionTexto(cd('muj_salud_sexual', 'servicio'), d.servicio)}: ${R.oracion(d.detalle)}`);
      h.push(`${R.entidad(d)} ${R.opcionTexto(cd('muj_salud_sexual', 'respuesta'), d.respuesta)}.`);
      h.push(`La negativa o la demora afecta a ${a.nom}: ${R.oracion(d.afectacion)}`);
      h.push(...R.hechosPrevio(d, 'este servicio'));
      return h;
    },
    normas: d => ['cp49', 'cp43', 'cp13', 'l1751_6', 'salud_sr', d.servicio === 'ive' ? 'ive' : null, d.servicio === 'violencia' ? 'res459' : null, 'cp23'].filter(Boolean),
    fundamentos: d => {
      const f = ['Los derechos sexuales y reproductivos son derechos fundamentales, y las EPS deben garantizar los servicios que los hacen efectivos sin barreras administrativas, sin exigir la autorización de terceros y con respeto por la autonomía y la dignidad de la mujer (artículos 13, 16, 42, 43 y 49 de la Constitución, Ley 1751 de 2015 y artículo 7 de la Ley 1257 de 2008).'];
      if (d.servicio === 'ive') f.push('La objeción de conciencia solo puede ser ejercida individualmente por el profesional de la salud, nunca por la EPS o la IPS, y obliga a remitir de inmediato a otro profesional; exigir autorización de terceros, juntas médicas, dictámenes adicionales o pagos, o demorar la atención más de cinco (5) días, constituye una barrera ilegítima que vulnera los derechos fundamentales de la mujer (sentencia SU-096 de 2018).');
      return f;
    },
    peticiones: [
      { v: 'prestar', inicial: true, fijo: true, t: 'Que presten el servicio de inmediato', legal: d => `Autorizar y prestar ${R.opcionTexto(cd('muj_salud_sexual', 'servicio'), d.servicio)} (${d.detalle || '[detalle]'}) ${d.servicio === 'ive' ? 'dentro de los cinco (5) días siguientes a la solicitud, conforme a la sentencia SU-096 de 2018' : d.servicio === 'violencia' ? 'de manera inmediata, conforme a la Resolución 459 de 2012' : 'de manera inmediata y oportuna'}, sin requisitos adicionales a los previstos en la ley.` },
      { v: 'remitir', inicial: d => d.respuesta === 'objecion', t: 'Que me remitan a otro profesional que sí preste el servicio', legal: 'Garantizar la remisión inmediata a un profesional o a una institución que preste el servicio, pues la objeción de conciencia es personal y no puede ser institucional ni dilatar la atención.' },
      { v: 'cerca', inicial: d => d.respuesta === 'cita', t: 'Que lo presten en un lugar cercano o cubran el transporte', legal: 'Prestar el servicio en una institución cercana al lugar de residencia o, de no ser posible, cubrir los gastos de transporte y alojamiento de la usuaria y de un acompañante.' },
      { v: 'integral', inicial: d => ['prenatal', 'parto', 'violencia'].includes(d.servicio), t: 'Que garanticen la atención integral (exámenes, medicamentos, psicología)', legal: 'Garantizar la atención integral: consultas, exámenes, medicamentos, atención psicológica y los demás servicios que el caso requiera, sin fraccionar la atención.' },
      { v: 'escrito', inicial: true, t: 'Que me respondan por escrito con fecha y lugar de la atención', legal: 'Responder por escrito indicando la fecha, el lugar y el profesional asignado para la atención.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'orden', t: 'Orden médica, ecografía o historia clínica' }, { v: 'respuesta', t: 'Respuesta o negativa de la EPS (si la hay)' }, { v: 'radicados', t: 'Radicados de solicitudes anteriores' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'En el embarazo, en la IVE y tras una violencia sexual el tiempo cuenta: si la EPS no responde en pocos días, no esperes los 15 días hábiles y presenta la tutela (marca "urgente"). Puedes quejarte también ante la Supersalud (línea 01 8000 513 700).', siNoResponden: 'Tutela por salud con medida provisional (en esta plataforma: "Tutela por salud: la EPS no autoriza, no entrega o demora un servicio") y queja ante la Supersalud.' }
  },

  /* ---------------- FAMILIA: CUSTODIA Y VISITAS ---------------- */
  {
    id: 'fam_custodia', tipo: 'familia', categoria: 'municipio', modulo: 'mujer',
    titulo: 'Solicitud de conciliación de custodia y visitas de los hijos (Comisaría o Defensoría de Familia)',
    resumen: 'Para definir con quién viven los niños y cómo los ve el otro padre o madre, hacer cumplir las visitas acordadas o cambiarlas. Hay opciones gratuitas ante entidades habilitadas; los centros privados y notarías pueden cobrar. La autoridad competente y los pasos dependen del beneficiario y del caso.',
    palabras: ['custodia', 'visitas', 'régimen de visitas', 'hijos', 'niños', 'no me deja ver a mis hijos', 'me quiere quitar a los niños', 'se llevó a los niños', 'separación', 'divorcio', 'comisaría de familia', 'ICBF', 'defensoría de familia', 'conciliación', 'cuidado personal'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Comisaría de Familia de Rionegro / ICBF Centro Zonal Oriente', cargo: 'Comisario(a) de Familia / Defensor(a) de Familia' },
    campos: [
      { id: 'menores', tipo: 'textarea', etiqueta: 'Nombre, edad y documento de cada hijo o hija', requerido: true, filas: 2, ejemplo: 'Ej.:\nSara Valentina Gómez Ruiz, 8 años, TI 1.030.456.789' },
      { id: 'otroProgenitor', tipo: 'texto', etiqueta: 'Nombre y documento del otro padre o madre', requerido: true, ancho: 'media' },
      { id: 'otroDireccion', tipo: 'texto', etiqueta: 'Dirección, teléfono o lugar de trabajo del otro padre o madre (para citarlo)', requerido: true, ancho: 'media' },
      { id: 'situacion', tipo: 'select', etiqueta: '¿Cuál es la situación?', requerido: true, opciones: [
        { v: 'conmigo', t: 'Los niños viven conmigo y el otro quiere llevárselos o los retiene en las visitas', legal: 'los menores viven con quien suscribe y el otro progenitor pretende llevárselos o los retiene indebidamente' },
        { v: 'conotro', t: 'Los niños viven con el otro y no me deja verlos', legal: 'los menores viven con el otro progenitor, quien impide el contacto con quien suscribe' },
        { v: 'definir', t: 'Nos separamos y hay que definir la custodia y las visitas', legal: 'los progenitores se separaron y es necesario definir la custodia y el régimen de visitas' },
        { v: 'incumple', t: 'Hay un acuerdo de visitas y el otro no lo cumple', legal: 'existe un acuerdo o decisión sobre visitas que el otro progenitor incumple' }
      ], ancho: 'completa' },
      { id: 'pide', tipo: 'select', etiqueta: '¿Qué pides?', requerido: true, opciones: [
        { v: 'custodia', t: 'Que la custodia quede conmigo y se fijen las visitas del otro', legal: 'la asignación de la custodia y el cuidado personal a quien suscribe y la fijación del régimen de visitas del otro progenitor' },
        { v: 'visitas', t: 'Que se fije un régimen de visitas para que yo pueda ver a mis hijos', legal: 'la fijación de un régimen de visitas a favor de quien suscribe' },
        { v: 'cumplir', t: 'Que se haga cumplir el régimen de visitas acordado', legal: 'el cumplimiento del régimen de visitas acordado' },
        { v: 'modificar', t: 'Que se modifique la custodia o las visitas', legal: 'la modificación de la custodia o del régimen de visitas' }
      ], ancho: 'completa' },
      { id: 'propuesta', tipo: 'textarea', etiqueta: 'Tu propuesta de visitas (días, horarios, vacaciones, festividades)', requerido: true, filas: 3, ejemplo: 'Ej.: Fines de semana cada 15 días de sábado 9 a. m. a domingo 6 p. m.; la mitad de las vacaciones; Navidad y Año Nuevo alternados.' },
      { id: 'razones', tipo: 'textarea', etiqueta: '¿Por qué es lo mejor para los niños? (con quién han vivido, colegio, cuidado, estabilidad)', requerido: true, filas: 3 },
      { id: 'riesgo', tipo: 'radio', etiqueta: '¿Hay violencia, consumo de drogas o algún riesgo para los niños con el otro padre o madre?', requerido: true, opciones: SI_NO },
      { id: 'riesgoDetalle', tipo: 'textarea', etiqueta: 'Explica el riesgo', mostrarSi: { campo: 'riesgo', valor: 'si' }, filas: 2 },
      { id: 'infoRiesgo', tipo: 'info', mostrarSi: { campo: 'riesgo', valor: 'si' }, texto: 'Si hay violencia, pide también la "Medida de protección por violencia intrafamiliar" (en este módulo): la Comisaría puede ordenar que las visitas sean supervisadas o suspenderlas.' },
      C.relato({ requerido: false, etiqueta: 'Contexto adicional (opcional)' })
    ],
    asunto: d => `Solicitud de audiencia de conciliación – ${R.opcionTexto(cd('fam_custodia', 'pide'), d.pide)}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom}, en calidad de ${R.terminacion(a.g, 'padre', 'madre')}, tiene ${['conmigo', 'definir', 'incumple'].includes(d.situacion) ? 'a su cargo o comparte' : 'derecho a mantener contacto con'} ${R.relatoAHechos(d.menores).join(' ')}`);
      h.push(`El otro progenitor es ${d.otroProgenitor || '[NOMBRE]'}, quien puede ser citado en ${d.otroDireccion || '[dirección]'}.`);
      h.push(`Situación actual: ${R.opcionTexto(cd('fam_custodia', 'situacion'), d.situacion)}.`);
      h.push(`El bienestar de los menores exige ${R.opcionTexto(cd('fam_custodia', 'pide'), d.pide)}: ${R.oracion(d.razones)}`);
      h.push(`Se propone el siguiente régimen de visitas: ${R.oracion(d.propuesta)}`);
      if (d.riesgo === 'si') h.push(`Existe riesgo para los menores en el contacto sin supervisión con el otro progenitor: ${R.oracion(d.riesgoDetalle)}`);
      return h;
    },
    normas: ['cp44', 'cp42', 'l1098_23', 'l1098_111'],
    fundamentos: d => ['El interés superior de los niños, niñas y adolescentes (artículo 44 de la Constitución y artículos 8 y 9 de la Ley 1098 de 2006) obliga a decidir la custodia y las visitas con base en su bienestar, estabilidad, cuidado efectivo y continuidad escolar, y no en los conflictos entre los adultos. Los niños tienen derecho a mantener relaciones con ambos padres (artículo 22 de la Ley 1098 de 2006 y artículo 256 del Código Civil), salvo cuando ello ponga en riesgo su integridad. Si no hay acuerdo en la conciliación, el Comisario o Defensor de Familia puede fijar provisionalmente la custodia y las visitas (artículos 82 y 86 de la Ley 1098 de 2006) y el asunto se decide ante el juez de familia mediante proceso verbal sumario (artículo 390 del Código General del Proceso).'],
    peticiones: [
      { v: 'citar', inicial: true, fijo: true, t: 'Que citen al otro padre o madre a audiencia de conciliación', legal: d => `Citar a ${d.otroProgenitor || '[NOMBRE]'} a audiencia de conciliación para ${R.opcionTexto(cd('fam_custodia', 'pide'), d.pide)} respecto de los menores relacionados.` },
      { v: 'fijar', inicial: true, t: 'Que aprueben mi propuesta (y la fijen provisionalmente si no hay acuerdo)', legal: d => `Aprobar ${R.opcionTexto(cd('fam_custodia', 'pide'), d.pide)} en los términos propuestos y, en caso de inasistencia o falta de acuerdo, fijarla provisionalmente conforme a los artículos 82 y 86 de la Ley 1098 de 2006.` },
      { v: 'supervisadas', inicial: d => d.riesgo === 'si', t: 'Que las visitas sean supervisadas mientras se verifica el riesgo', legal: 'Disponer que las visitas del otro progenitor se realicen de forma supervisada, en un lugar seguro, mientras el equipo psicosocial verifica la situación de riesgo descrita.' },
      { v: 'psicosocial', t: 'Que el equipo psicosocial evalúe la situación de los niños', legal: 'Ordenar la valoración de los menores por el equipo psicosocial de la Comisaría o del ICBF para orientar la decisión.' },
      { v: 'judicial', t: 'Si no hay acuerdo, que remitan al juez de familia', legal: 'En caso de no lograrse acuerdo, expedir la constancia correspondiente y orientar sobre el proceso ante el juez de familia.' }
    ],
    anexos: [ { v: 'registros', t: 'Registros civiles de nacimiento de los hijos' }, { v: 'cedula', t: 'Copia de la cédula' }, { v: 'colegio', t: 'Constancias del colegio, la EPS o el pediatra' }, { v: 'acuerdo', t: 'Acuerdo o acta de visitas anterior (si existe)' }, { v: 'pruebas', t: 'Mensajes, fotos o denuncias relacionadas con el riesgo', si: d => d.riesgo === 'si' } ],
    guia: { plazo: null, nota: 'La conciliación tiene un trámite propio y no debe confundirse con el término de respuesta a una petición. Consulta la programación, competencia y requisitos del operador. Lleva los registros civiles y los acuerdos existentes. Si hay riesgo o violencia, busca protección inmediata y orientación sobre las medidas aplicables.', siNoResponden: 'Si el otro padre o madre incumple lo acordado: incidente ante la misma Comisaría y proceso ante el juez de familia (consultorio jurídico gratuito). Si hay violencia: medida de protección.' }
  }
  );
})();
