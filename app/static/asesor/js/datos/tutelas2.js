/* ============================================================
   tutelas2.js — Casos de ACCIÓN DE TUTELA (parte 2):
   educación, debido proceso, hábeas data, servicios públicos,
   víctimas, vida y seguridad, migrantes y tutela general.
   ============================================================ */
window.AJ = window.AJ || {};
AJ.casos = AJ.casos || [];

(function () {
  const R = AJ.red;
  const C = AJ.campos;
  const cd = (c, f) => AJ.camposDe(c, f);

  AJ.casos.push(
  /* ---------------- TUTELA EDUCACIÓN ---------------- */
  {
    id: 'tut_educacion', tipo: 'tutela', categoria: 'educacion',
    titulo: 'Tutela por el derecho a la educación (cupo, certificados, expulsión, discapacidad)',
    resumen: 'Un niño sin cupo escolar, certificados retenidos que impiden matricularse en otro colegio, expulsión sin debido proceso o negación de apoyos a un estudiante con discapacidad.',
    palabras: ['tutela', 'educación', 'cupo', 'colegio', 'certificados', 'expulsión', 'matrícula', 'discapacidad', 'universidad', 'secretaría de educación', 'niño', 'estudiante', 'grado', 'bullying'],
    destinatario: { categoria: 'educacion', ejemploNombre: 'Ej.: Institución Educativa La Esperanza / Secretaría de Educación de Cúcuta' },
    campos: [
      { id: 'estudiante', tipo: 'texto', etiqueta: 'Nombre, edad y grado del estudiante', requerido: true, ancho: 'completa' },
      { id: 'problema', tipo: 'select', etiqueta: '¿Qué está pasando?', requerido: true, opciones: [
        { v: 'cupo', t: 'No le dan cupo en ningún colegio público', legal: 'la negación de cupo escolar' },
        { v: 'certificados', t: 'No entregan certificados y no puede matricularse en otro colegio', legal: 'la retención de los certificados de estudio' },
        { v: 'expulsion', t: 'Lo expulsaron o cancelaron la matrícula sin debido proceso', legal: 'la exclusión del estudiante sin el debido proceso' },
        { v: 'discapacidad', t: 'Niegan el cupo o los apoyos por su discapacidad', legal: 'la negación del cupo o de los ajustes razonables por su condición de discapacidad' },
        { v: 'pago', t: 'No lo dejan entrar a clase o presentar exámenes por deudas', legal: 'la exclusión de clases o evaluaciones por deudas económicas de los padres' },
        { v: 'acoso', t: 'Sufre acoso escolar y el colegio no actúa', legal: 'la omisión del colegio frente al acoso escolar que sufre' },
        { v: 'transporte', t: 'No hay transporte ni alimentación escolar en zona rural', legal: 'la falta de transporte o alimentación escolar que impide su asistencia' }
      ], ancho: 'completa' },
      { id: 'desde', tipo: 'fecha', etiqueta: '¿Desde cuándo está sin estudiar o afectado?', ancho: 'media' },
      { id: 'diasSinClase', tipo: 'texto', etiqueta: 'Días o semanas de clase perdidos (aproximado)', ancho: 'media' },
      ...C.previo({ etiqueta: '¿Ya pediste solución al colegio o a la Secretaría de Educación?' }),
      C.relato({ ejemplo: 'Ej.:\nMi hija de 9 años terminó 3° en el colegio Santa Rosa.\nNos mudamos y el colegio no entrega los certificados por una deuda de 400.000 pesos.\nEl nuevo colegio no la recibe sin certificados y lleva 5 semanas sin estudiar.' })
    ],
    asunto: d => `Acción de tutela – Derecho fundamental a la educación – ${d.estudiante || 'estudiante'}`,
    hechos: d => {
      const h = [];
      h.push(`${d.estudiante || 'El estudiante'} tiene derecho a acceder y permanecer en el sistema educativo, y se ve afectado por ${R.opcionTexto(cd('tut_educacion', 'problema'), d.problema)} por parte de ${R.entidad(d)}.`);
      if (d.desde) h.push(`La situación se presenta desde ${R.fechaLarga(d.desde)}${d.diasSinClase ? `, con una pérdida aproximada de ${d.diasSinClase} de clase` : ''}.`);
      h.push(...R.hechosPrevio(d, 'la solución de esta situación'));
      return h;
    },
    derechos: [
      { v: 'educacion', inicial: true, t: 'Educación', legal: 'derecho fundamental a la educación (artículos 44 y 67 de la Constitución)' },
      { v: 'ninos', inicial: true, t: 'Derechos de los niños (prevalentes)', legal: 'derechos fundamentales y prevalentes de los niños, niñas y adolescentes (artículo 44 de la Constitución)' },
      { v: 'igualdad', t: 'Igualdad y no discriminación', legal: 'derecho a la igualdad (artículo 13 de la Constitución)' },
      { v: 'debido', t: 'Debido proceso', legal: 'derecho al debido proceso (artículo 29 de la Constitución)' },
      { v: 'dignidad', t: 'Dignidad e integridad', legal: 'derechos a la dignidad humana y a la integridad personal (artículos 1 y 12 de la Constitución)' }
    ],
    normas: ['cp86', 'cp67', 'cp44', 'cp13', 'l115_4', 'l1098_28', 'd2591_42'],
    fundamentos: d => {
      const f = [];
      if (d.problema === 'certificados' || d.problema === 'pago') f.push(AJ.normas.su624.texto + ` (${AJ.normas.su624.cita}).`, AJ.normas.t_cert.texto + ` (${AJ.normas.t_cert.cita}).`);
      if (d.problema === 'expulsion') f.push(AJ.normas.cp29.texto + ` (${AJ.normas.cp29.cita}).`, 'La Corte Constitucional (sentencias T-390 de 2011, T-478 de 2015 y T-240 de 2018) ha reiterado que las sanciones escolares exigen un debido proceso con comunicación de cargos, defensa, pruebas, decisión motivada y recursos, y que la exclusión es la última medida, nunca procedente por bajo rendimiento, embarazo, orientación sexual o apariencia.');
      if (d.problema === 'discapacidad') f.push(AJ.normas.l1618.texto + ` (${AJ.normas.l1618.cita}).`, 'El Decreto 1421 de 2017 obliga a las instituciones a garantizar la educación inclusiva, elaborar el Plan Individual de Ajustes Razonables (PIAR) y no negar el cupo por razón de la discapacidad.');
      if (d.problema === 'acoso') f.push('La Ley 1620 de 2013 obliga a las instituciones a activar la Ruta de Atención Integral frente al acoso escolar y a proteger a la víctima; su omisión compromete la integridad y la dignidad del estudiante (Sentencia T-478 de 2015).');
      if (d.problema === 'cupo' || d.problema === 'transporte') f.push('La Corte Constitucional (sentencias T-779 de 2011, T-008 de 2016 y T-434 de 2018) ha señalado que las entidades territoriales deben garantizar cupos en instituciones cercanas a la residencia y, cuando la distancia lo exige, el transporte escolar, pues la accesibilidad material es componente del derecho a la educación.');
      return f;
    },
    procedencia: d => [
      'Subsidiariedad: no existe otro medio judicial idóneo y eficaz para garantizar de manera inmediata la continuidad del proceso educativo de un menor; cada día sin clases produce un perjuicio irremediable, por lo que la tutela es procedente.',
      'Inmediatez: la vulneración es actual, pues el estudiante continúa afectado.'
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja el derecho a la educación', legal: d => `TUTELAR el derecho fundamental a la educación de ${d.estudiante || 'el estudiante'}.` },
      { v: 'cupo', inicial: d => ['cupo', 'transporte'].includes(d.problema), t: 'Que ordene asignar el cupo escolar de inmediato', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes, asigne cupo escolar al estudiante en una institución oficial cercana a su residencia y garantice su matrícula.` },
      { v: 'certificados', inicial: d => ['certificados', 'pago'].includes(d.problema), t: 'Que ordene entregar los certificados', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes, expida y entregue los certificados de estudio y demás documentos requeridos, sin condicionarlos al pago de obligaciones económicas.` },
      { v: 'reintegro', inicial: d => ['expulsion', 'pago'].includes(d.problema), t: 'Que ordene reintegrar al estudiante y dejar sin efectos la sanción', legal: d => `ORDENAR a ${R.entidad(d)} dejar sin efectos la sanción impuesta y reintegrar de inmediato al estudiante, garantizando la recuperación de las actividades académicas perdidas.` },
      { v: 'ajustes', inicial: d => d.problema === 'discapacidad', t: 'Que ordene los apoyos para el estudiante con discapacidad', legal: d => `ORDENAR a ${R.entidad(d)} garantizar la matrícula y elaborar en diez (10) días el Plan Individual de Ajustes Razonables (PIAR), con los apoyos pedagógicos y personales que requiera.` },
      { v: 'ruta', inicial: d => d.problema === 'acoso', t: 'Que ordene activar la ruta contra el acoso escolar', legal: d => `ORDENAR a ${R.entidad(d)} activar de inmediato la Ruta de Atención Integral para la Convivencia Escolar, adoptar medidas de protección al estudiante y reportar al comité de convivencia.` },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` }
    ],
    medida: d => `Solicito como MEDIDA PROVISIONAL (artículo 7 del Decreto 2591 de 1991) que se ordene a ${R.entidad(d)} permitir de inmediato la asistencia del estudiante a clases mientras se decide la tutela, pues la espera del fallo puede causar un daño irreversible: ${R.oracion(d.medidaTexto || 'cada día sin estudiar causa un perjuicio irremediable al menor')}`,
    anexos: [ { v: 'cedula', t: 'Cédula del padre o madre y registro civil o tarjeta del estudiante' }, { v: 'boletines', t: 'Boletines, certificados o constancia del último grado' }, { v: 'negativa', t: 'Comunicación del colegio o de la Secretaría (negativa, sanción, cobro)' }, { v: 'peticion', t: 'Copia de la petición previa' }, { v: 'medicos', t: 'Certificado de discapacidad o diagnóstico (si aplica)' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'La presenta el padre, la madre o el acudiente en representación del menor (el documento ya lo indica).', siNoResponden: 'Incidente de desacato. También queja ante la Secretaría de Educación y, si hay maltrato, ICBF (línea 141).' }
  },

  /* ---------------- TUTELA DEBIDO PROCESO ADMINISTRATIVO ---------------- */
  {
    id: 'tut_debido_proceso', tipo: 'tutela', categoria: 'municipio',
    titulo: 'Tutela por violación del debido proceso (sanción, cobro o decisión sin notificarte ni dejarte defender)',
    resumen: 'Te sancionaron, te embargaron, te quitaron un subsidio o tomaron una decisión en tu contra sin notificarte, sin escucharte o sin resolver tus recursos.',
    palabras: ['tutela', 'debido proceso', 'notificación', 'sanción', 'multa', 'embargo', 'cobro coactivo', 'recurso', 'subsidio', 'retiraron', 'decisión', 'resolución', 'defensa', 'proceso disciplinario'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Secretaría de Tránsito de Barranquilla / Prosperidad Social / Alcaldía de Pasto' },
    campos: [
      { id: 'decision', tipo: 'texto', etiqueta: '¿Qué decisión tomaron en tu contra? (número y fecha si la conoces)', ejemplo: 'Ej.: Resolución 0789 del 3 de julio de 2026 que me impuso una multa / Retiro del programa Renta Ciudadana', requerido: true, ancho: 'completa' },
      { id: 'falla', tipo: 'checks', etiqueta: '¿Qué hicieron mal?', requerido: true, opciones: [
        { v: 'no_notificaron', t: 'Nunca me notificaron la decisión ni el proceso', legal: 'no se notificó en debida forma el inicio de la actuación ni la decisión' },
        { v: 'sin_defensa', t: 'No me dejaron presentar pruebas ni explicar mi versión', legal: 'no se brindó la oportunidad de ejercer la defensa, presentar pruebas y controvertir las existentes' },
        { v: 'recursos', t: 'Presenté recursos y no los han resuelto', legal: 'los recursos interpuestos no han sido resueltos' },
        { v: 'sin_motivos', t: 'La decisión no explica las razones', legal: 'la decisión carece de motivación' },
        { v: 'ejecucion', t: 'Me embargaron o ejecutaron la decisión sin estar en firme', legal: 'se ejecutó la decisión (embargo, descuento, retiro) sin que estuviera en firme' },
        { v: 'incompetente', t: 'La tomó un funcionario que no era el competente', legal: 'la decisión fue adoptada por un funcionario sin competencia' }
      ] },
      { id: 'fechaConocio', tipo: 'fecha', etiqueta: '¿Cuándo te enteraste de la decisión?', requerido: true, ancho: 'media' },
      { id: 'fechaRecurso', tipo: 'fecha', etiqueta: 'Fecha en que presentaste recursos (si lo hiciste)', ancho: 'media' },
      { id: 'afectacion', tipo: 'textarea', etiqueta: '¿Qué consecuencias tiene la decisión para ti? (embargo de salario, pérdida de subsidio, no poder trabajar)', requerido: true, filas: 3 },
      C.relato({ ejemplo: 'Ej.:\nEn agosto de 2026 me descontaron 400.000 pesos del salario por un embargo de la Secretaría de Tránsito.\nNunca recibí ninguna carta ni notificación del comparendo ni de la resolución.\nPresenté recurso el 20 de agosto y no me han respondido.' })
    ],
    asunto: d => `Acción de tutela – Debido proceso administrativo – ${d.decision || ''}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${R.entidad(d)} adoptó en contra de ${a.nom} la siguiente decisión: ${R.oracion(d.decision)}`);
      h.push(`En esa actuación ${R.lista((d.falla || []).map(v => R.opcionTexto(cd('tut_debido_proceso', 'falla'), v)))}.`);
      h.push(`${a.Nom} solo tuvo conocimiento de la decisión ${R.elDia(d.fechaConocio)}${d.fechaRecurso ? `, e interpuso los recursos de ley el ${R.fechaLarga(d.fechaRecurso)} sin que hayan sido resueltos` : ''}.`);
      h.push(`Consecuencias de la decisión: ${R.oracion(d.afectacion)}`);
      return h;
    },
    derechos: [
      { v: 'debido', inicial: true, t: 'Debido proceso', legal: 'derecho fundamental al debido proceso administrativo (artículo 29 de la Constitución)' },
      { v: 'defensa', inicial: true, t: 'Defensa y contradicción', legal: 'derechos de defensa y contradicción (artículo 29 de la Constitución)' },
      { v: 'minimo', t: 'Mínimo vital (si hay embargo o pérdida de ingresos)', legal: 'derecho al mínimo vital (artículos 1 y 53 de la Constitución)' },
      { v: 'peticion', t: 'Derecho de petición (recursos sin resolver)', legal: 'derecho fundamental de petición (artículo 23 de la Constitución)' }
    ],
    normas: ['cp86', 'cp29', 'l1437_3', 'l1437_66', 'l1437_74', 'l1437_79', 'l1437_87', 'cp209'],
    procedencia: d => [
      'Subsidiariedad: si bien existe el medio de control de nulidad y restablecimiento del derecho ante la jurisdicción contencioso administrativa, la Corte Constitucional ha admitido la tutela contra actos administrativos cuando la vulneración del debido proceso es evidente (falta de notificación, ausencia de defensa) y el acto produce un perjuicio irremediable sobre el mínimo vital u otros derechos fundamentales, o cuando se usa como mecanismo transitorio (artículo 8 del Decreto 2591 de 1991; sentencias T-956 de 2011 y SU-355 de 2015).',
      `Inmediatez: la parte accionante conoció la decisión ${R.elDia(d.fechaConocio)} y acude a la tutela dentro de un término razonable, mientras los efectos de la decisión continúan.`
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja el debido proceso', legal: d => `TUTELAR el derecho fundamental al debido proceso administrativo de ${R.actor(d).nom}.` },
      { v: 'dejar_sin_efecto', inicial: true, t: 'Que deje sin efectos la decisión y ordene rehacer el proceso con notificación', legal: d => `DEJAR SIN EFECTOS la decisión descrita y ORDENAR a ${R.entidad(d)} que, de persistir en la actuación, la adelante desde el inicio con notificación en debida forma y plena garantía del derecho de defensa.` },
      { v: 'resolver', t: 'Que ordene resolver mis recursos en 48 horas', legal: d => `ORDENAR a ${R.entidad(d)} resolver de fondo, dentro de las cuarenta y ocho (48) horas siguientes, los recursos interpuestos por la parte accionante.` },
      { v: 'suspender', inicial: true, t: 'Que suspenda el embargo, descuento o ejecución', legal: d => `ORDENAR a ${R.entidad(d)} suspender de inmediato la ejecución de la decisión (embargos, descuentos, retiros o cobros) hasta que la actuación se surta con las garantías del debido proceso y quede en firme.` },
      { v: 'devolver', t: 'Que devuelva lo descontado', legal: d => `ORDENAR a ${R.entidad(d)} devolver las sumas descontadas o cobradas con fundamento en la decisión viciada.` },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` }
    ],
    medida: d => `Solicito como MEDIDA PROVISIONAL (artículo 7 del Decreto 2591 de 1991) la suspensión inmediata de la ejecución de la decisión (embargo, descuento o retiro), pues la espera del fallo puede causar un daño irreversible: ${R.oracion(d.medidaTexto || d.afectacion)}`,
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'decision', t: 'Copia de la decisión (resolución, oficio, comparendo) si la tienes' }, { v: 'recursos', t: 'Copia de los recursos presentados con radicado' }, { v: 'descuentos', t: 'Desprendibles o extractos que muestren el embargo o descuento' }, { v: 'direccion', t: 'Prueba de tu dirección registrada (para demostrar que no te notificaron)' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'Antes de la tutela, lo normal es presentar recurso de reposición y apelación (10 días hábiles desde que conociste la decisión). Si ya pasó ese plazo porque nunca te notificaron, explícalo: el término corre desde la notificación en debida forma.', siNoResponden: 'Si el juez niega la tutela por existir la vía contenciosa, acude a un consultorio jurídico para la demanda de nulidad y restablecimiento del derecho (4 meses desde la notificación).' }
  },

  /* ---------------- TUTELA HÁBEAS DATA ---------------- */
  {
    id: 'tut_habeas_data', tipo: 'tutela', categoria: 'financiera',
    titulo: 'Tutela por hábeas data: reporte negativo ilegal en Datacrédito o TransUnion',
    resumen: 'Te reportaron sin avisarte, el dato ya caducó, ya pagaste y siguen reportándote, o la deuda no es tuya. Requisito: haber presentado antes el reclamo a la entidad o la central.',
    palabras: ['tutela', 'hábeas data', 'habeas data', 'Datacrédito', 'TransUnion', 'CIFIN', 'reporte', 'reportado', 'central de riesgo', 'deuda', 'caducidad', 'pagué', 'buen nombre', 'crédito negado'],
    destinatario: { categoria: 'financiera', ejemploNombre: 'Ej.: Banco Davivienda / Claro / Datacrédito Experian' },
    campos: [
      { id: 'quienReporta', tipo: 'texto', etiqueta: '¿Qué entidad te reportó (la fuente)?', ejemplo: 'Ej.: Banco de Bogotá / Movistar / Cooperativa XYZ', requerido: true, ancho: 'media' },
      { id: 'central', tipo: 'select', etiqueta: '¿En qué central aparece el reporte?', opciones: [ { v: 'datacredito', t: 'Datacrédito Experian' }, { v: 'transunion', t: 'TransUnion (CIFIN)' }, { v: 'ambas', t: 'En ambas' }, { v: 'procredito', t: 'Procrédito' } ], valorInicial: 'datacredito', ancho: 'media' },
      { id: 'motivo', tipo: 'select', etiqueta: '¿Por qué el reporte es ilegal?', requerido: true, opciones: [
        { v: 'sin_aviso', t: 'Nunca me avisaron antes de reportarme', legal: 'la fuente no envió la comunicación previa que exige el artículo 12 de la Ley 1266 de 2008' },
        { v: 'pague', t: 'Ya pagué y siguen reportándome o no actualizan', legal: 'la obligación fue pagada y la fuente no actualizó el dato ni reportó el pago' },
        { v: 'caduco', t: 'El dato ya cumplió el tiempo máximo (doble de la mora, máximo 4 años / 8 años sin pagar)', legal: 'el dato negativo superó el término máximo de permanencia previsto en el artículo 13 de la Ley 1266 de 2008' },
        { v: 'no_mia', t: 'La deuda no es mía (suplantación o error)', legal: 'la obligación reportada no corresponde al titular, por error o suplantación de identidad' },
        { v: 'prescrita', t: 'La deuda está prescrita y me reportan de todas formas', legal: 'se reporta una obligación prescrita o inexistente' },
        { v: 'monto', t: 'El monto o la fecha reportada son incorrectos', legal: 'la información reportada es inexacta en cuanto al monto o las fechas' }
      ], ancho: 'completa' },
      { id: 'obligacion', tipo: 'texto', etiqueta: 'Obligación reportada (producto, número, valor)', ancho: 'completa' },
      { id: 'fechaMora', tipo: 'fecha', etiqueta: 'Fecha en que entró en mora (si la sabes)', ancho: 'media' },
      { id: 'fechaPago', tipo: 'fecha', etiqueta: 'Fecha de pago (si pagaste)', ancho: 'media' },
      { id: 'reclamo', tipo: 'radio', etiqueta: '¿Ya presentaste el reclamo escrito a la entidad o a la central? (es obligatorio antes de la tutela)', requerido: true, opciones: [ { v: 'si', t: 'Sí, y no respondieron en 15 días hábiles o respondieron negando' }, { v: 'no', t: 'No todavía' } ] },
      { id: 'infoReclamo', tipo: 'info', mostrarSi: { campo: 'reclamo', valor: 'no' }, texto: 'La ley exige presentar primero el reclamo ante la entidad que reporta o la central de riesgo (artículo 16 de la Ley 1266 de 2008). Genera primero el "Reclamo de hábeas data" de esta plataforma, espera 15 días hábiles y luego vuelve a esta tutela.' },
      { id: 'fechaReclamo', tipo: 'fecha', etiqueta: 'Fecha del reclamo', mostrarSi: { campo: 'reclamo', valor: 'si' }, ancho: 'media' },
      { id: 'afectacion', tipo: 'textarea', etiqueta: '¿Qué consecuencias te ha traído el reporte? (crédito negado, empleo, vivienda)', requerido: true, filas: 2 },
      C.relato({ requerido: false, etiqueta: '¿Algo más que el juez deba saber? (opcional)' })
    ],
    asunto: d => 'Acción de tutela – Hábeas data y buen nombre – Reporte negativo en centrales de riesgo',
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${d.quienReporta || 'La entidad fuente'} reportó negativamente a ${a.nom} en ${R.opcionTexto(cd('tut_habeas_data', 'central'), d.central, 't')}${d.obligacion ? `, por la obligación ${d.obligacion}` : ''}${d.fechaMora ? `, con fecha de mora ${R.fechaLarga(d.fechaMora)}` : ''}.`);
      h.push(`El reporte es ilegal porque ${R.opcionTexto(cd('tut_habeas_data', 'motivo'), d.motivo)}${d.fechaPago ? `. La obligación fue pagada el ${R.fechaLarga(d.fechaPago)}` : ''}.`);
      if (d.motivo === 'caduco' && d.fechaPago) {
        const fp = AJ.festivos.parseISO(d.fechaPago);
        const fm = AJ.festivos.parseISO(d.fechaMora);
        if (fp && fm) { const mesesMora = Math.max(1, Math.round((fp - fm) / (30.44 * 24 * 3600 * 1000))); const permanencia = Math.min(mesesMora * 2, 48); const limite = AJ.festivos.sumarMeses(fp, permanencia); h.push(`La mora fue de aproximadamente ${mesesMora} meses, de modo que el dato negativo podía permanecer máximo ${permanencia} meses desde el pago, es decir, hasta el ${R.fechaLarga(limite)}, fecha ya superada.`); }
      }
      if (d.reclamo === 'si') h.push(`${R.capital(R.elDia(d.fechaReclamo, 'Con anterioridad'))}, ${a.nom} presentó reclamo escrito ante la fuente y/o el operador, conforme al artículo 16 de la Ley 1266 de 2008, sin obtener la corrección o eliminación del dato dentro del término legal.`);
      h.push(`Consecuencias del reporte: ${R.oracion(d.afectacion)}`);
      return h;
    },
    derechos: [
      { v: 'habeas', inicial: true, t: 'Hábeas data', legal: 'derecho fundamental al hábeas data (artículo 15 de la Constitución)' },
      { v: 'buen_nombre', inicial: true, t: 'Buen nombre y honra', legal: 'derechos al buen nombre y a la honra (artículos 15 y 21 de la Constitución)' },
      { v: 'debido', t: 'Debido proceso', legal: 'derecho al debido proceso (artículo 29 de la Constitución)' },
      { v: 'minimo', t: 'Mínimo vital (si impide trabajar o acceder a crédito esencial)', legal: 'derecho al mínimo vital' }
    ],
    normas: ['cp86', 'cp15', 'l1266_6', 'l1266_8', 'l1266_12', 'l1266_13', 'l1266_16', 'l2157', 'sic_hd', 'd2591_42'],
    fundamentos: d => {
      const f = ['La Corte Constitucional (sentencias SU-082 de 1995, C-1011 de 2008, T-168 de 2010, T-017 de 2011 y T-167 de 2015, entre otras) ha señalado que el reporte de datos negativos exige que la información sea veraz y esté soportada, que exista autorización del titular y que se le haya comunicado previamente, de modo que el reporte efectuado sin ese aviso o sin prueba de la obligación es ilegal y debe eliminarse; que la permanencia del dato está limitada por el principio de caducidad; y que la fuente responde por el reporte inexacto y el operador por no corregirlo.'];
      if (d.motivo === 'no_mia') f.push('La Ley Estatutaria 2573 de 2026 (revisada en la Sentencia C-413 de 2025) obliga a las entidades financieras, operadores y comercios a suspender los cobros, los intereses y los reportes negativos mientras se verifica una suplantación de identidad denunciada por el titular, quien debe presentar la denuncia ante la Fiscalía dentro de los veinte (20) días hábiles siguientes.');
      return f;
    },
    procedencia: d => [
      'Subsidiariedad: conforme al artículo 16 de la Ley 1266 de 2008, el titular agotó el reclamo previo ante la fuente y/o el operador sin obtener la corrección, de manera que se cumple el requisito de procedibilidad y la tutela es el mecanismo idóneo para la protección del hábeas data.',
      'Inmediatez: el reporte continúa publicado y produce efectos actuales.'
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja el hábeas data y el buen nombre', legal: d => `TUTELAR los derechos fundamentales al hábeas data y al buen nombre de ${R.actor(d).nom}.` },
      { v: 'eliminar', inicial: true, t: 'Que ordene eliminar o corregir el reporte en 48 horas', legal: d => `ORDENAR a ${R.entidad(d)} ${d.quienReporta && !R.entidad(d).includes(R.mayus(d.quienReporta)) ? `y a ${R.mayus(d.quienReporta)} ` : ''}que, dentro de las cuarenta y ocho (48) horas siguientes a la notificación del fallo, eliminen o corrijan el dato negativo reportado y actualicen la información en todas las centrales de riesgo.` },
      { v: 'abstener', t: 'Que no vuelvan a reportar esa obligación', legal: d => `ORDENAR a la fuente abstenerse de reportar nuevamente la obligación sin cumplir los requisitos legales.` },
      { v: 'certificar', t: 'Que certifiquen la eliminación', legal: 'ORDENAR a las entidades accionadas expedir certificación de la eliminación o corrección del dato y entregarla a la parte accionante.' },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: d => `ADVERTIR a las accionadas que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'historial', t: 'Historial de crédito descargado (Datacrédito / TransUnion, gratis una vez al mes)' }, { v: 'reclamo', t: 'Copia del reclamo previo y la respuesta (INDISPENSABLE)' }, { v: 'pago', t: 'Paz y salvo o comprobante de pago' }, { v: 'negacion', t: 'Prueba del crédito o empleo negado' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'Puedes dirigir la tutela contra la fuente (quien reportó) y la central de riesgo al mismo tiempo. Pon ambas en el nombre de la entidad accionada.', siNoResponden: 'Incidente de desacato. También puedes quejarte ante la Superintendencia de Industria y Comercio.' }
  },

  /* ---------------- TUTELA SERVICIOS PÚBLICOS ---------------- */
  {
    id: 'tut_servicios_publicos', tipo: 'tutela', categoria: 'spd',
    titulo: 'Tutela por corte de agua o energía en una vivienda con niños, enfermos o personas mayores',
    resumen: 'La empresa suspendió el agua o la luz y en la casa viven personas que dependen del servicio (niños, adultos mayores, enfermos con oxígeno o diálisis), o cortaron sin aviso ni causa.',
    palabras: ['tutela', 'agua', 'luz', 'energía', 'corte', 'suspensión', 'reconexión', 'servicios públicos', 'mínimo vital de agua', 'niños', 'enfermo', 'oxígeno', 'EPM', 'acueducto'],
    destinatario: { categoria: 'spd', ejemploNombre: 'Ej.: Aguas de Bogotá / Air-e' },
    campos: [
      { id: 'servicio', tipo: 'select', etiqueta: 'Servicio suspendido', requerido: true, opciones: [ { v: 'agua', t: 'Agua (acueducto)' }, { v: 'energia', t: 'Energía eléctrica' }, { v: 'gas', t: 'Gas' }, { v: 'varios', t: 'Varios servicios' } ], ancho: 'media' },
      { id: 'fechaCorte', tipo: 'fecha', etiqueta: 'Fecha del corte', requerido: true, ancho: 'media' },
      { id: 'direccionServicio', tipo: 'texto', etiqueta: 'Dirección de la vivienda', requerido: true, ancho: 'completa' },
      { id: 'causa', tipo: 'select', etiqueta: '¿Por qué cortaron?', opciones: [
        { v: 'deuda', t: 'Por deuda que no he podido pagar', legal: 'por una deuda que el hogar no ha podido pagar debido a su situación económica' },
        { v: 'sin_aviso', t: 'Sin aviso y sin deuda (error o reclamo pendiente)', legal: 'sin previo aviso y sin causa legal, pues el hogar está al día o existe un reclamo pendiente' },
        { v: 'fraude', t: 'Dicen que hubo "fraude" o "manipulación del medidor" sin pruebas', legal: 'alegando una supuesta irregularidad en el medidor, sin un procedimiento previo con garantías' }
      ], valorInicial: 'deuda', ancho: 'completa' },
      { id: 'habitantes', tipo: 'checks', etiqueta: '¿Quiénes viven en la casa?', requerido: true, opciones: [ { v: 'ninos', t: 'Niños o niñas', legal: 'niños' }, { v: 'mayores', t: 'Personas mayores', legal: 'personas adultas mayores' }, { v: 'enfermos', t: 'Personas enfermas o con discapacidad', legal: 'personas enfermas o con discapacidad' }, { v: 'equipos', t: 'Alguien que depende de equipos eléctricos (oxígeno, diálisis, nebulizador)', legal: 'una persona que depende de equipos médicos eléctricos' }, { v: 'embarazo', t: 'Mujer embarazada', legal: 'una mujer embarazada' } ] },
      { id: 'detalleHabitantes', tipo: 'texto', etiqueta: 'Detalle (edades, enfermedades)', ejemplo: 'Ej.: Mi madre de 82 años con EPOC usa oxígeno; dos niños de 4 y 7 años', ancho: 'completa' },
      { id: 'deuda', tipo: 'texto', etiqueta: 'Valor de la deuda (si hay)', ancho: 'media' },
      { id: 'economia', tipo: 'textarea', etiqueta: 'Situación económica del hogar (ingresos, Sisbén, empleo)', requerido: true, filas: 2 },
      { id: 'acuerdo', tipo: 'radio', etiqueta: '¿Has intentado un acuerdo de pago con la empresa?', opciones: [ { v: 'si', t: 'Sí, pero no lo aceptaron o no puedo cumplir la cuota' }, { v: 'no', t: 'No' } ], requerido: true },
      C.relato({ requerido: false, etiqueta: '¿Algo más que el juez deba saber? (opcional)' })
    ],
    asunto: d => `Acción de tutela – Vida digna, salud y mínimo vital – Suspensión del servicio de ${R.opcionTexto(cd('tut_servicios_publicos', 'servicio'), d.servicio, 't').toLowerCase()}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} reside con su familia en ${d.direccionServicio}, vivienda a la que ${R.entidad(d)} presta el servicio de ${R.opcionTexto(cd('tut_servicios_publicos', 'servicio'), d.servicio, 't').toLowerCase()}.`);
      h.push(`${R.capital(R.elDia(d.fechaCorte))}, la empresa suspendió el servicio ${R.opcionTexto(cd('tut_servicios_publicos', 'causa'), d.causa)}${d.deuda ? ` (deuda aproximada: ${R.moneda(d.deuda) || d.deuda})` : ''}.`);
      h.push(`En la vivienda habitan ${R.lista((d.habitantes || []).map(v => R.opcionTexto(cd('tut_servicios_publicos', 'habitantes'), v)))}${d.detalleHabitantes ? `: ${d.detalleHabitantes}` : ''}, para quienes el servicio es indispensable para la vida, la salud y la dignidad.`);
      h.push(`Situación económica del hogar: ${R.oracion(d.economia)}`);
      if (d.acuerdo === 'si') h.push('Se intentó un acuerdo de pago con la empresa, sin que fuera posible en condiciones acordes con la capacidad económica del hogar.');
      return h;
    },
    derechos: [
      { v: 'vida', inicial: true, t: 'Vida digna', legal: 'derecho a la vida en condiciones dignas (artículos 1 y 11 de la Constitución)' },
      { v: 'minimo', inicial: true, t: 'Mínimo vital y servicios públicos esenciales', legal: 'derecho al mínimo vital y a la prestación de los servicios públicos esenciales (artículos 1, 11, 365 y 366 de la Constitución)' },
      { v: 'agua', inicial: d => d.servicio === 'agua' || d.servicio === 'varios', t: 'Agua potable (si el corte es de acueducto)', legal: 'derecho fundamental al agua potable (artículos 11 y 366 de la Constitución; Sentencia T-740 de 2011)' },
      { v: 'salud', inicial: true, t: 'Salud', legal: 'derecho fundamental a la salud (artículo 49 de la Constitución)' },
      { v: 'ninos', t: 'Derechos de los niños', legal: 'derechos prevalentes de los niños (artículo 44 de la Constitución)' },
      { v: 'vivienda', t: 'Vivienda digna', legal: 'derecho a la vivienda digna (artículo 51 de la Constitución)' }
    ],
    normas: ['cp86', 'cp365', 'cp13', 't740', 'l142_140', 'l142_152', 'd2591_42'],
    fundamentos: d => d.servicio !== 'agua' ? ['La Corte Constitucional ha extendido la protección a la energía eléctrica cuando de ella depende la vida o la salud de un miembro del hogar (equipos médicos como concentradores de oxígeno, refrigeración de medicamentos) o cuando habitan sujetos de especial protección (sentencias T-761 de 2015 y T-436 de 2024, entre otras), ordenando la reconexión, la suscripción de acuerdos de pago razonables y, cuando el equipo eléctrico es la alternativa médica idónea, la asunción de su costo energético por la EPS.'] : [],
    procedencia: d => [
      'Subsidiariedad: aunque existen los recursos ante la empresa y la Superintendencia de Servicios Públicos, estos no son eficaces frente a la urgencia de un hogar con sujetos de especial protección privado de un servicio esencial, por lo que la tutela procede de manera directa (Sentencia T-740 de 2011 y jurisprudencia posterior).',
      'Inmediatez: la suspensión es actual y sus efectos sobre la salud y la vida de los habitantes son inmediatos.'
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja los derechos', legal: d => `TUTELAR los derechos fundamentales a la vida digna, a la salud, al agua y al mínimo vital de ${R.actor(d).nom} y de su núcleo familiar.` },
      { v: 'reconectar', inicial: true, t: 'Que ordene reconectar el servicio en 48 horas', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes a la notificación del fallo, restablezca el servicio en la vivienda ubicada en ${d.direccionServicio}.` },
      { v: 'minimo', inicial: d => d.servicio === 'agua' || d.servicio === 'varios', t: 'Que garantice el mínimo vital de agua (50 litros por persona al día) mientras se paga', legal: d => `ORDENAR a ${R.entidad(d)} garantizar el suministro de un mínimo vital de agua de cincuenta (50) litros diarios por persona, sin interrupción, mientras subsista la situación de vulnerabilidad.` },
      { v: 'acuerdo', inicial: true, t: 'Que ordene un acuerdo de pago acorde con mi capacidad', legal: d => `ORDENAR a ${R.entidad(d)} suscribir con la parte accionante un acuerdo de pago de la deuda en cuotas acordes con la capacidad económica del hogar, sin que ello condicione la reconexión.` },
      { v: 'abstener', t: 'Que no vuelvan a cortar mientras haya personas vulnerables', legal: d => `ORDENAR a ${R.entidad(d)} abstenerse de suspender nuevamente el servicio mientras habiten en la vivienda sujetos de especial protección y la parte accionante cumpla el acuerdo de pago.` },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` }
    ],
    medida: d => `Solicito como MEDIDA PROVISIONAL (artículo 7 del Decreto 2591 de 1991) que se ordene a ${R.entidad(d)} la reconexión inmediata del servicio, pues la espera del fallo puede causar un daño irreversible: ${R.oracion(d.medidaTexto || 'los habitantes de la vivienda no pueden esperar el fallo sin grave riesgo para su salud y su vida')}`,
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'factura', t: 'Última factura y constancia del corte' }, { v: 'registros', t: 'Registros civiles de los niños o cédulas de los adultos mayores' }, { v: 'medicos', t: 'Historias clínicas o certificados de las personas enfermas' }, { v: 'sisben', t: 'Sisbén o prueba de la situación económica' }, { v: 'reclamo', t: 'Reclamo o solicitud de acuerdo de pago presentada' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, siNoResponden: 'Si no cumplen dentro del plazo ordenado en el fallo, informa al juzgado y solicita el cumplimiento; según el caso, puede proceder el incidente de desacato.' }
  },

  /* ---------------- TUTELA VÍCTIMAS ---------------- */
  {
    id: 'tut_victimas', tipo: 'tutela', categoria: 'nacional',
    titulo: 'Tutela de víctimas del conflicto (ayuda humanitaria, registro, indemnización)',
    resumen: 'La Unidad para las Víctimas no responde, no entrega la ayuda humanitaria, no decide tu inclusión en el registro en 60 días hábiles o no te informa sobre la indemnización.',
    palabras: ['tutela', 'víctima', 'desplazado', 'desplazamiento', 'ayuda humanitaria', 'RUV', 'registro', 'indemnización', 'Unidad de Víctimas', 'conflicto'],
    destinatario: { categoria: 'nacional', nombre: 'Unidad para la Atención y Reparación Integral a las Víctimas', cargo: 'Director(a) General' },
    campos: [
      { id: 'tramite', tipo: 'select', etiqueta: '¿Cuál es el problema?', requerido: true, opciones: cd('pet_victimas', 'tramite').opciones, ancho: 'completa' },
      { id: 'hecho', tipo: 'select', etiqueta: 'Hecho victimizante', opciones: cd('pet_victimas', 'hecho').opciones, valorInicial: 'desplazamiento', ancho: 'media' },
      { id: 'fechaDeclaracion', tipo: 'fecha', etiqueta: 'Fecha de la declaración', ancho: 'media' },
      { id: 'codigo', tipo: 'texto', etiqueta: 'Código FUD o radicado', ancho: 'media' },
      { id: 'nucleo', tipo: 'texto', etiqueta: 'Integrantes del hogar (número y edades)', ancho: 'media' },
      { id: 'situacion', tipo: 'textarea', etiqueta: 'Situación actual del hogar (vivienda, alimentación, salud, ingresos)', requerido: true, filas: 3 },
      ...C.previo({ etiqueta: '¿Ya presentaste derecho de petición a la Unidad?' }),
      C.relato({ requerido: false, etiqueta: '¿Algo más que el juez deba saber? (opcional)' })
    ],
    asunto: d => `Acción de tutela – Derechos de las víctimas – ${R.opcionTexto(cd('tut_victimas', 'tramite'), d.tramite)}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} es víctima del conflicto armado por el hecho de ${R.opcionTexto(cd('tut_victimas', 'hecho'), d.hecho, 't').toLowerCase()}${d.fechaDeclaracion ? `, y rindió declaración ${R.elDia(d.fechaDeclaracion)}` : ''}${d.codigo ? ` (código ${d.codigo})` : ''}.`);
      if (d.nucleo) h.push(`Su hogar está conformado por ${d.nucleo}.`);
      h.push(`La Unidad para las Víctimas no ha garantizado ${R.opcionTexto(cd('tut_victimas', 'tramite'), d.tramite)}, pese a los términos legales.`);
      h.push(`Situación actual: ${R.oracion(d.situacion)}`);
      h.push(...R.hechosPrevio(d, 'la atención solicitada'));
      return h;
    },
    derechos: [
      { v: 'minimo', inicial: true, t: 'Mínimo vital y vida digna', legal: 'derechos al mínimo vital y a la vida digna (artículos 1 y 11 de la Constitución)' },
      { v: 'victimas', inicial: true, t: 'Derechos de las víctimas (atención y reparación)', legal: 'derechos de las víctimas a la atención humanitaria, a la verdad, la justicia y la reparación (Ley 1448 de 2011)' },
      { v: 'peticion', inicial: true, t: 'Derecho de petición', legal: 'derecho fundamental de petición (artículo 23 de la Constitución)' },
      { v: 'igualdad', t: 'Igualdad y protección especial', legal: 'derecho a la igualdad y a la protección especial de la población desplazada (artículo 13 de la Constitución)' }
    ],
    normas: ['cp86', 'cp13', 'cp23', 'l1448', 't025', 'l1755_14', 'l1755_20'],
    procedencia: d => [
      'Subsidiariedad: la Corte Constitucional, desde la Sentencia T-025 de 2004, ha establecido que la población víctima del conflicto, en especial la desplazada, goza de protección constitucional reforzada y que la tutela es el mecanismo idóneo para exigir la atención humanitaria, la inclusión en el registro y la respuesta a sus solicitudes, dada su extrema vulnerabilidad.',
      'Inmediatez: la omisión de la entidad es actual y continúa afectando la subsistencia del hogar.'
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja los derechos', legal: d => `TUTELAR los derechos fundamentales al mínimo vital, a la vida digna, de petición y los derechos como víctima de ${R.actor(d).nom} y de su núcleo familiar.` },
      { v: 'ayuda', inicial: d => d.tramite === 'ayuda', t: 'Que ordene entregar la ayuda humanitaria en 48 horas', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes, entregue la atención humanitaria que corresponda al hogar y, si es necesario, realice la medición de carencias dentro de los diez (10) días siguientes.` },
      { v: 'registro', inicial: d => ['registro', 'recurso', 'novedad'].includes(d.tramite), t: 'Que ordene decidir la inclusión en el RUV', legal: d => `ORDENAR a ${R.entidad(d)} decidir de fondo, dentro de los diez (10) días siguientes, la solicitud de inclusión en el Registro Único de Víctimas y notificarla.` },
      { v: 'indemnizacion', inicial: d => d.tramite === 'indemnizacion', t: 'Que ordene informar el turno y la fecha de la indemnización', legal: d => `ORDENAR a ${R.entidad(d)} informar de manera clara, dentro de las cuarenta y ocho (48) horas siguientes, el estado de la indemnización administrativa, el método de priorización, el turno asignado y la fecha estimada de pago.` },
      { v: 'responder', inicial: true, t: 'Que ordene responder de fondo la petición', legal: d => `ORDENAR a ${R.entidad(d)} responder de fondo, dentro de las cuarenta y ocho (48) horas siguientes, las solicitudes presentadas por la parte accionante.` },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'declaracion', t: 'Constancia de la declaración (FUD)' }, { v: 'registros', t: 'Registros civiles del hogar' }, { v: 'peticion', t: 'Derecho de petición previo' }, { v: 'resolucion', t: 'Resoluciones de la Unidad (si existen)' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'La Unidad es entidad nacional: la tutela se reparte a un juez del circuito. La Personería y la Defensoría te acompañan gratis.', siNoResponden: 'Incidente de desacato.' }
  },

  /* ---------------- TUTELA VIDA Y SEGURIDAD ---------------- */
  {
    id: 'tut_vida_seguridad', tipo: 'tutela', categoria: 'nacional',
    titulo: 'Tutela por amenazas contra la vida (protección de la UNP o la Policía)',
    resumen: 'Recibes amenazas por tu trabajo como líder social, periodista, defensor de derechos, testigo o víctima, y la Unidad Nacional de Protección o la Policía no te protegen o demoran la evaluación del riesgo.',
    palabras: ['tutela', 'amenazas', 'vida', 'seguridad', 'protección', 'UNP', 'líder social', 'Policía', 'riesgo', 'esquema', 'desplazamiento', 'intimidación'],
    destinatario: { categoria: 'nacional', nombre: 'Unidad Nacional de Protección (UNP)', cargo: 'Director(a) General' },
    campos: [
      { id: 'perfil', tipo: 'select', etiqueta: '¿Por qué te amenazan?', requerido: true, opciones: [
        { v: 'lider', t: 'Soy líder social, comunal o defensor(a) de derechos humanos', legal: 'su labor como líder social, comunal o defensor(a) de derechos humanos' },
        { v: 'periodista', t: 'Soy periodista o comunicador(a)', legal: 'su ejercicio periodístico' },
        { v: 'testigo', t: 'Soy testigo o denunciante en un proceso', legal: 'su condición de testigo o denunciante' },
        { v: 'victima', t: 'Soy víctima del conflicto o reclamante de tierras', legal: 'su condición de víctima del conflicto o reclamante de tierras' },
        { v: 'funcionario', t: 'Soy servidor público o sindicalista', legal: 'su condición de servidor público o dirigente sindical' },
        { v: 'otro', t: 'Otra razón', legal: 'las circunstancias que se describen en los hechos' }
      ], ancho: 'completa' },
      { id: 'amenazas', tipo: 'textarea', etiqueta: 'Describe las amenazas (fechas, medio, contenido, autores si se conocen)', requerido: true, filas: 4 },
      { id: 'denuncia', tipo: 'radio', etiqueta: '¿Denunciaste ante la Fiscalía?', opciones: [ { v: 'si', t: 'Sí' }, { v: 'no', t: 'No todavía' } ], requerido: true, ancho: 'media' },
      { id: 'noticiaCriminal', tipo: 'texto', etiqueta: 'Número de noticia criminal (si denunciaste)', ancho: 'media' },
      { id: 'solicitudUNP', tipo: 'radio', etiqueta: '¿Pediste protección a la UNP o a la Policía?', opciones: [ { v: 'si', t: 'Sí, y no han respondido o negaron las medidas' }, { v: 'no', t: 'No todavía' } ], requerido: true, ancho: 'media' },
      { id: 'fechaSolicitud', tipo: 'fecha', etiqueta: 'Fecha de la solicitud de protección', ancho: 'media' },
      { id: 'situacionActual', tipo: 'textarea', etiqueta: 'Situación actual (¿tuviste que desplazarte? ¿hay familia en riesgo?)', requerido: true, filas: 2 }
    ],
    asunto: d => 'Acción de tutela – Derechos a la vida, la integridad y la seguridad personal – Medidas de protección',
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} se encuentra en situación de riesgo extraordinario debido a ${R.opcionTexto(cd('tut_vida_seguridad', 'perfil'), d.perfil)}.`);
      h.push(...R.relatoAHechos(d.amenazas));
      if (d.denuncia === 'si') h.push(`Los hechos fueron denunciados ante la Fiscalía General de la Nación${d.noticiaCriminal ? ` (noticia criminal No. ${d.noticiaCriminal})` : ''}.`);
      if (d.solicitudUNP === 'si') h.push(`${d.fechaSolicitud ? `${R.capital(R.elDia(d.fechaSolicitud))}, ` : ''}${a.nom} solicitó medidas de protección a ${R.entidad(d)}, sin que a la fecha se hayan implementado medidas efectivas ni se haya concluido la evaluación del riesgo.`);
      h.push(`Situación actual: ${R.oracion(d.situacionActual)}`);
      return h;
    },
    derechos: [
      { v: 'vida', inicial: true, t: 'Vida', legal: 'derecho a la vida (artículo 11 de la Constitución)' },
      { v: 'integridad', inicial: true, t: 'Integridad y seguridad personal', legal: 'derechos a la integridad y a la seguridad personal (artículos 2 y 12 de la Constitución)' },
      { v: 'peticion', t: 'Derecho de petición', legal: 'derecho fundamental de petición (artículo 23 de la Constitución)' },
      { v: 'familia', t: 'Protección de la familia', legal: 'derecho a la protección de la familia (artículo 42 de la Constitución)' }
    ],
    normas: ['cp86', 'cp2', 'cp11', 'cp12', 'unp', 'l1755_20'],
    fundamentos: d => ['La Corte Constitucional (sentencias T-719 de 2003, T-078 de 2013 y T-473 de 2018) ha definido el derecho a la seguridad personal como el derecho a recibir protección estatal frente a riesgos extraordinarios que la persona no está obligada a soportar, y ha señalado que las autoridades deben actuar con urgencia, adoptar medidas de emergencia mientras se evalúa el riesgo y no pueden demorar injustificadamente la evaluación ni la implementación de las medidas.'],
    procedencia: d => [
      'Subsidiariedad: no existe otro medio judicial eficaz para obtener protección inmediata frente a una amenaza contra la vida; la tutela es el mecanismo idóneo y procede incluso como mecanismo transitorio para evitar un perjuicio irremediable.',
      'Inmediatez: la amenaza es actual y persistente.'
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja la vida y la seguridad', legal: d => `TUTELAR los derechos fundamentales a la vida, a la integridad y a la seguridad personal de ${R.actor(d).nom} y de su núcleo familiar.` },
      { v: 'emergencia', inicial: true, t: 'Que ordene medidas de protección de emergencia de inmediato', legal: d => `ORDENAR a ${R.entidad(d)}${/POLIC/i.test(R.entidad(d)) ? '' : ' y a la Policía Nacional'} que, dentro de las cuarenta y ocho (48) horas siguientes, adopten medidas de protección de emergencia (rondas policiales, medio de comunicación, chaleco, apoyo de reubicación o las que correspondan) mientras se concluye la evaluación del riesgo.` },
      { v: 'evaluacion', inicial: true, t: 'Que ordene evaluar el riesgo y decidir las medidas en un plazo corto', legal: d => `ORDENAR a ${R.entidad(d)} realizar la evaluación del riesgo y decidir las medidas definitivas de protección dentro de los veinte (20) días siguientes, notificando la decisión motivada.` },
      { v: 'fiscalia', t: 'Que ordene a la Fiscalía impulsar la investigación', legal: 'ORDENAR a la Fiscalía General de la Nación impulsar la investigación por las amenazas e informar su estado a la parte accionante.' },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: 'ADVERTIR a las entidades accionadas que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.' }
    ],
    medida: d => `Solicito como MEDIDA PROVISIONAL (artículo 7 del Decreto 2591 de 1991) que se ordene a ${R.entidad(d)}${/POLIC/i.test(R.entidad(d)) ? '' : ' y a la Policía Nacional'} implementar de inmediato medidas de protección de emergencia, pues la espera del fallo puede causar un daño irreversible: ${R.oracion(d.medidaTexto || 'la amenaza es inminente y puede costar la vida de la parte accionante')}`,
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'denuncia', t: 'Copia de la denuncia ante la Fiscalía' }, { v: 'amenazas', t: 'Pantallazos, panfletos, audios o cartas de amenaza' }, { v: 'solicitud', t: 'Solicitud de protección a la UNP o la Policía y respuesta' }, { v: 'perfil', t: 'Prueba de tu labor (certificado de la organización, credencial de periodista)' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'Dirige la tutela contra la UNP y la Policía Nacional (Ministerio de Defensa). Pide medida provisional. La Defensoría del Pueblo puede acompañarte.', siNoResponden: 'Incidente de desacato.' }
  },

  /* ---------------- TUTELA MIGRANTES ---------------- */
  {
    id: 'tut_migrantes', tipo: 'tutela', categoria: 'eps',
    titulo: 'Tutela por salud o educación de personas migrantes',
    resumen: 'Te niegan la atención de urgencias, el tratamiento de una enfermedad grave, el control prenatal o el cupo escolar de tus hijos por tu situación migratoria o por falta de documentos.',
    palabras: ['tutela', 'migrante', 'venezolano', 'extranjero', 'urgencias', 'salud', 'PPT', 'sin documentos', 'embarazo', 'niños', 'educación', 'hospital', 'afiliación'],
    destinatario: { categoria: 'eps', ejemploNombre: 'Ej.: Hospital Universitario del Valle / Secretaría de Salud de Cúcuta / Nueva EPS' },
    campos: [
      { id: 'situacionMig', tipo: 'select', etiqueta: 'Situación migratoria', opciones: [ { v: 'ppt', t: 'Tengo PPT o cédula de extranjería', legal: 'cuenta con Permiso por Protección Temporal o cédula de extranjería' }, { v: 'tramite', t: 'Estoy en trámite de regularización', legal: 'se encuentra en trámite de regularización migratoria' }, { v: 'irregular', t: 'No tengo documentos colombianos', legal: 'no cuenta aún con documento migratorio vigente' } ], valorInicial: 'ppt', ancho: 'completa' },
      { id: 'problema', tipo: 'select', etiqueta: '¿Qué te niegan?', requerido: true, opciones: [
        { v: 'urgencias', t: 'Atención de urgencias', legal: 'la atención de urgencias' },
        { v: 'tratamiento', t: 'Tratamiento de una enfermedad grave (cáncer, VIH, diálisis, cirugía)', legal: 'el tratamiento de una enfermedad grave' },
        { v: 'prenatal', t: 'Control prenatal o atención del parto', legal: 'la atención prenatal y del parto' },
        { v: 'afiliacion', t: 'Afiliación a salud (teniendo PPT y Sisbén)', legal: 'la afiliación al sistema de salud pese a cumplir los requisitos' },
        { v: 'educacion', t: 'Cupo escolar para mis hijos', legal: 'el cupo escolar de los niños' },
        { v: 'ninos_salud', t: 'Atención en salud de un niño', legal: 'la atención en salud de un menor de edad' }
      ], ancho: 'completa' },
      { id: 'diagnostico', tipo: 'texto', etiqueta: 'Diagnóstico o condición (si aplica)', ancho: 'completa' },
      { id: 'detalle', tipo: 'textarea', etiqueta: '¿Qué pasó? (fechas, qué te dijeron, estado actual)', requerido: true, filas: 4 }
    ],
    asunto: d => `Acción de tutela – ${d.problema === 'educacion' ? 'Derecho a la educación' : 'Derecho fundamental a la salud'} – Persona migrante`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} es una persona migrante que ${R.opcionTexto(cd('tut_migrantes', 'situacionMig'), d.situacionMig)} y reside en ${d.ciudad || 'Colombia'}.`);
      h.push(`${R.entidad(d)} le ha negado ${R.opcionTexto(cd('tut_migrantes', 'problema'), d.problema)}${d.diagnostico ? `, en relación con ${d.diagnostico}` : ''}, aduciendo su situación migratoria o la falta de documentos.`);
      h.push(...R.relatoAHechos(d.detalle));
      return h;
    },
    derechos: [
      { v: 'salud', inicial: true, t: 'Salud', legal: 'derecho fundamental a la salud (artículo 49 de la Constitución y Ley 1751 de 2015)' },
      { v: 'vida', inicial: true, t: 'Vida y dignidad', legal: 'derechos a la vida y a la dignidad humana (artículos 1 y 11 de la Constitución)' },
      { v: 'igualdad', inicial: true, t: 'Igualdad', legal: 'derecho a la igualdad (artículos 13 y 100 de la Constitución)' },
      { v: 'ninos', t: 'Derechos de los niños', legal: 'derechos prevalentes de los niños (artículo 44 de la Constitución)' },
      { v: 'educacion', t: 'Educación', legal: 'derecho a la educación (artículo 67 de la Constitución)' }
    ],
    normas: ['cp86', 'cp13', 'cp49', 'l1751_10', 'l1751_14', 'su677', 'migr', 'cp44', 'd2591_42'],
    fundamentos: d => d.problema === 'educacion' ? ['La Corte Constitucional (sentencias T-185 de 2021 y T-255 de 2021) y la Circular Conjunta 16 de 2018 del Ministerio de Educación Nacional y Migración Colombia establecen que los niños, niñas y adolescentes migrantes tienen derecho a ser matriculados en el sistema educativo con o sin documento de identidad, sin que pueda exigirse afiliación previa a salud ni certificados convalidados, y que los requisitos documentales de imposible cumplimiento deben inaplicarse.'] : ['La Corte Constitucional ha señalado (sentencias SU-677 de 2017, T-210 de 2018, T-178 de 2019, T-452 de 2019 y T-274 de 2021) que la atención de urgencias debe prestarse a toda persona sin consideración a su situación migratoria; que, en casos excepcionales, esa atención comprende el tratamiento de enfermedades graves o catastróficas; que los niños migrantes tienen protección reforzada y no puede negárseles la encuesta Sisbén ni la afiliación al régimen subsidiado; y que, cuando la persona cumple los requisitos para afiliarse (PPT y Sisbén), la negativa de afiliación vulnera el derecho a la salud.'],
    procedencia: d => ['Subsidiariedad: no existe otro mecanismo judicial eficaz para garantizar de inmediato la atención en salud o la educación de una persona migrante en situación de vulnerabilidad; la tutela procede de manera directa.', 'Inmediatez: la negativa es actual y el riesgo para la vida, la salud o la educación persiste.'],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja los derechos', legal: d => `TUTELAR los derechos fundamentales a la salud, a la vida digna${d.problema === 'educacion' ? ', a la igualdad y a la educación' : ' y a la igualdad'} de ${R.actor(d).nom}.` },
      { v: 'atender', inicial: true, t: 'Que ordene prestar la atención o el cupo de inmediato', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes, garantice ${R.opcionTexto(cd('tut_migrantes', 'problema'), d.problema)} sin exigir requisitos relacionados con la situación migratoria.` },
      { v: 'afiliar', t: 'Que ordene la afiliación a salud', legal: d => `ORDENAR a ${R.entidad(d)} y a la Secretaría de Salud municipal adelantar la afiliación de la parte accionante al régimen subsidiado de salud, si cumple los requisitos, y mientras tanto garantizar la atención a través de la red pública.` },
      { v: 'migracion', t: 'Que ordene a Migración Colombia resolver el trámite de regularización', legal: 'ORDENAR a Migración Colombia resolver de fondo, en un término no superior a quince (15) días, el trámite de regularización pendiente de la parte accionante.' },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: 'ADVERTIR a las entidades accionadas que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.' }
    ],
    medida: d => `Solicito como MEDIDA PROVISIONAL (artículo 7 del Decreto 2591 de 1991) que se ordene a ${R.entidad(d)} prestar de inmediato la atención requerida, pues la espera del fallo puede causar un daño irreversible: ${R.oracion(d.medidaTexto || d.detalle)}`,
    anexos: [ { v: 'documento', t: 'Copia del documento que tengas (pasaporte, cédula venezolana, PPT)' }, { v: 'medicos', t: 'Historia clínica, orden médica o negativa escrita' }, { v: 'sisben', t: 'Sisbén o constancia del trámite' }, { v: 'registros', t: 'Documentos de los niños' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'No necesitas documento colombiano para presentar una tutela: basta el pasaporte, la cédula de tu país o cualquier identificación. Si pides una orden contra Migración Colombia, inclúyela también como accionada (es entidad nacional y la tutela se reparte a un juez del circuito).', siNoResponden: 'Incidente de desacato.' }
  },

  /* ---------------- TUTELA GENERAL ---------------- */
  {
    id: 'tut_general', tipo: 'tutela', categoria: 'municipio',
    titulo: 'Acción de tutela general (cualquier derecho fundamental)',
    resumen: 'Plantilla libre: tú describes qué pasó, qué derecho te vulneran y qué quieres que ordene el juez. La herramienta pone la estructura y las normas básicas de la tutela.',
    palabras: ['tutela', 'general', 'otro', 'derecho fundamental', 'cualquier', 'libre'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Nombre de la entidad o persona' },
    campos: [
      { id: 'derechoLibre', tipo: 'checks', etiqueta: '¿Qué derechos te están vulnerando?', requerido: true, opciones: [
        { v: 'vida', t: 'Vida e integridad', legal: 'derecho a la vida y a la integridad personal (artículos 11 y 12 de la Constitución)' },
        { v: 'dignidad', t: 'Dignidad humana', legal: 'derecho a la dignidad humana (artículo 1 de la Constitución)' },
        { v: 'igualdad', t: 'Igualdad / no discriminación', legal: 'derecho a la igualdad y a no ser discriminado (artículo 13 de la Constitución)' },
        { v: 'intimidad', t: 'Intimidad, buen nombre o datos personales', legal: 'derechos a la intimidad, al buen nombre y al hábeas data (artículo 15 de la Constitución)' },
        { v: 'libertad', t: 'Libertad de expresión, conciencia, culto o locomoción', legal: 'libertades fundamentales (artículos 16, 18, 19, 20 y 24 de la Constitución)' },
        { v: 'peticion', t: 'Derecho de petición', legal: 'derecho fundamental de petición (artículo 23 de la Constitución)' },
        { v: 'trabajo', t: 'Trabajo y mínimo vital', legal: 'derechos al trabajo y al mínimo vital (artículos 25 y 53 de la Constitución)' },
        { v: 'debido', t: 'Debido proceso', legal: 'derecho al debido proceso (artículo 29 de la Constitución)' },
        { v: 'familia', t: 'Familia, niños, adulto mayor', legal: 'derechos de la familia, de los niños y de las personas mayores (artículos 42, 44 y 46 de la Constitución)' },
        { v: 'salud', t: 'Salud y seguridad social', legal: 'derechos a la salud y a la seguridad social (artículos 48 y 49 de la Constitución)' },
        { v: 'vivienda', t: 'Vivienda digna', legal: 'derecho a la vivienda digna (artículo 51 de la Constitución)' },
        { v: 'educacion', t: 'Educación', legal: 'derecho a la educación (artículo 67 de la Constitución)' },
        { v: 'ambiente', t: 'Ambiente sano / agua', legal: 'derecho al ambiente sano y al agua (artículos 79 y 366 de la Constitución)' }
      ] },
      C.relato({ etiqueta: 'Cuéntale al juez qué pasó (un hecho por línea, con fechas)' }),
      { id: 'porque', tipo: 'textarea', etiqueta: '¿Por qué eso viola tus derechos y por qué no puedes esperar otro proceso?', requerido: true, filas: 3 },
      { id: 'ordenes', tipo: 'textarea', etiqueta: '¿Qué quieres que el juez le ordene a la entidad? (una orden por línea)', requerido: true, filas: 3, ejemplo: 'Ej.:\nQue me entreguen el certificado de residencia.\nQue dejen de publicar mi fotografía en la cartelera del conjunto.' },
      ...C.previo({ etiqueta: '¿Ya reclamaste directamente a la entidad?' })
    ],
    asunto: d => `Acción de tutela – ${R.lista((d.derechoLibre || []).slice(0, 2).map(v => R.opcionTexto(cd('tut_general', 'derechoLibre'), v, 't')))}`,
    hechos: d => R.hechosPrevio(d, 'la solución de esta situación'),
    derechos: [],
    normas: ['cp86', 'cp2', 'd2591_1', 'd2591_5', 'd2591_6', 'd2591_8', 'd2591_14', 'd2591_42'],
    fundamentos: d => [`Los hechos descritos vulneran ${R.lista((d.derechoLibre || []).map(v => R.opcionTexto(cd('tut_general', 'derechoLibre'), v)))}, por las siguientes razones: ${R.oracion(d.porque)}`],
    procedencia: d => ['Subsidiariedad: la parte accionante no cuenta con otro medio de defensa judicial idóneo y eficaz para obtener la protección inmediata de sus derechos, o, de existir, este no es eficaz frente a la urgencia de la situación, por lo que la tutela procede, al menos como mecanismo transitorio para evitar un perjuicio irremediable.', 'Inmediatez: la acción se presenta dentro de un término razonable, pues la vulneración es actual.'],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja los derechos', legal: d => `TUTELAR los derechos fundamentales de ${R.actor(d).nom} a ${R.lista((d.derechoLibre || []).map(v => R.opcionTexto(cd('tut_general', 'derechoLibre'), v).replace(/^derechos? (fundamentales? )?(a |al )?/, '').replace(/^libertades fundamentales/, 'las libertades fundamentales'))) || 'los derechos indicados'}, vulnerados por ${R.entidad(d)}.` },
      { v: 'propias', inicial: true, fijo: true, t: 'Mis órdenes (las que escribiste arriba)', legal: d => R.relatoAHechos(d.ordenes).map(o => `ORDENAR a ${R.entidad(d)}: ${o}`) },
      { v: 'plazo', inicial: true, t: 'Que fije un plazo de 48 horas para cumplir', legal: d => `ORDENAR que el cumplimiento se realice dentro de las cuarenta y ocho (48) horas siguientes a la notificación del fallo.` },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` }
    ],
    medida: d => `Solicito como MEDIDA PROVISIONAL (artículo 7 del Decreto 2591 de 1991) que, desde la admisión, se ordene lo siguiente: ${R.oracion(d.medidaTexto || R.relatoAHechos(d.ordenes)[0] || '')}`,
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'pruebas', t: 'Todas las pruebas de lo que cuento (documentos, fotos, chats, radicados)' }, { v: 'reclamo', t: 'Reclamo previo a la entidad' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'Si tu caso encaja en una de las tutelas específicas de la plataforma, úsala: tendrá mejores fundamentos.', siNoResponden: 'Incidente de desacato si no cumplen; impugnación (3 días) si la niegan.' }
  }
  );
})();
