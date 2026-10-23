/* ============================================================
   tutelas.js — Casos de ACCIÓN DE TUTELA (parte 1):
   salud, derecho de petición, mínimo vital, incapacidades,
   pensiones y estabilidad laboral reforzada.
   ============================================================ */
window.AJ = window.AJ || {};
AJ.casos = AJ.casos || [];

(function () {
  const R = AJ.red;
  const C = AJ.campos;
  const cd = (c, f) => AJ.camposDe(c, f);

  /* Campos adicionales que el formulario agrega a toda tutela */
  C.tutelaExtra = function () {
    return [
      { id: 'urgente', tipo: 'radio', etiqueta: '¿Necesitas que el juez ordene algo de inmediato, antes de decidir la tutela (medida provisional)?', ayuda: 'Se pide cuando esperar los 10 días del fallo causaría un daño grave: una cirugía urgente, un corte de agua con niños, un desalojo.', opciones: [ { v: 'no', t: 'No, puedo esperar el fallo (máximo 10 días)' }, { v: 'si', t: 'Sí, la situación es urgente' } ], valorInicial: 'no' },
      { id: 'medidaTexto', tipo: 'textarea', etiqueta: '¿Qué debe ordenar el juez de inmediato y qué pasaría si espera los 10 días?', ejemplo: 'Ej.: Que la EPS entregue el oxígeno hoy mismo, porque sin él mi padre no puede respirar.', mostrarSi: { campo: 'urgente', valor: 'si' }, filas: 3 },
      { id: 'otraTutela', tipo: 'radio', etiqueta: '¿Has presentado antes otra tutela por estos mismos hechos?', ayuda: 'El documento incluye una declaración bajo juramento sobre esto; responde con la verdad.', opciones: [ { v: 'no', t: 'No, es la primera' }, { v: 'si', t: 'Sí' } ], requerido: true },
      { id: 'infoOtraTutela', tipo: 'info', mostrarSi: { campo: 'otraTutela', valor: 'si' }, texto: 'Atención: no se puede presentar dos veces la misma tutela (por los mismos hechos y derechos); el juez la rechazaría por "temeraria". Si ya ganaste la tutela y la entidad no cumple, lo que corresponde es un INCIDENTE DE DESACATO ante el mismo juez. Si la perdiste y hay hechos nuevos, descríbelos claramente en el relato.' }
    ];
  };

  AJ.casos.push(
  /* ---------------- TUTELA SALUD: SERVICIO NEGADO O DEMORADO ---------------- */
  {
    id: 'tut_salud_servicio', tipo: 'tutela', categoria: 'eps',
    titulo: 'Tutela por salud: la EPS no autoriza, no entrega o demora un servicio',
    resumen: 'Medicamentos, citas con especialista, cirugías, exámenes, terapias, insumos (pañales, oxígeno, sillas de ruedas) ordenados por el médico y no garantizados.',
    palabras: ['tutela', 'salud', 'EPS', 'medicamento', 'cirugía', 'cita', 'especialista', 'examen', 'procedimiento', 'autorización', 'negaron', 'demora', 'pañales', 'oxígeno', 'silla de ruedas', 'terapias', 'MIPRES', 'cáncer', 'urgente'],
    destinatario: { categoria: 'eps', ejemploNombre: 'Ej.: Nueva EPS', cargo: 'Representante legal' },
    campos: [
      { id: 'regimen', tipo: 'select', etiqueta: '¿Cómo está el paciente en la EPS?', ayuda: 'Si no sabes, mira el carné o la app de la EPS. Si entró por el Sisbén y no paga: subsidiado. Si le descuentan del sueldo, paga o está como beneficiario de alguien que paga: contributivo.', opciones: [ { v: 'contributivo', t: 'Contributivo: le descuentan del sueldo, paga, o es beneficiario(a) de alguien que paga', legal: 'régimen contributivo' }, { v: 'subsidiado', t: 'Subsidiado: entró por el Sisbén y no paga', legal: 'régimen subsidiado' }, { v: 'especial', t: 'Especial: es o fue maestro(a) (Fomag), policía, militar o de Ecopetrol', legal: 'régimen especial o de excepción' } ], valorInicial: 'contributivo', ancho: 'completa' },
      { id: 'tipoServicio', tipo: 'select', etiqueta: '¿Qué te ordenaron y no te han garantizado?', requerido: true, opciones: [
        { v: 'medicamento', t: 'Un medicamento', legal: 'el medicamento' }, { v: 'cita', t: 'Una cita con especialista', legal: 'la consulta de medicina especializada' },
        { v: 'cirugia', t: 'Una cirugía o procedimiento', legal: 'el procedimiento quirúrgico' }, { v: 'examen', t: 'Un examen o imagen diagnóstica', legal: 'el examen o ayuda diagnóstica' },
        { v: 'terapias', t: 'Terapias', legal: 'las sesiones de terapia' }, { v: 'insumos', t: 'Insumos o dispositivos (pañales, oxígeno, silla de ruedas, prótesis)', legal: 'los insumos o dispositivos médicos' },
        { v: 'remision', t: 'Remisión a otra IPS o ciudad', legal: 'la remisión al prestador requerido' }, { v: 'hospitalizacion', t: 'Hospitalización, UCI o atención domiciliaria', legal: 'la atención hospitalaria o domiciliaria' }
      ], ancho: 'media' },
      { id: 'servicio', tipo: 'texto', etiqueta: 'Nombre exacto del servicio (cópialo de la orden médica)', requerido: true, ancho: 'completa' },
      { id: 'diagnostico', tipo: 'texto', etiqueta: '¿Qué enfermedad tiene? (como lo dijo el médico o como aparece en la fórmula; si no sabes el nombre exacto, descríbela)', ejemplo: 'Ej.: diabetes / "le falló el riñón" / un tumor en el seno', requerido: true, ancho: 'media' },
      { id: 'fechaOrden', tipo: 'fecha', etiqueta: 'Fecha de la orden médica', ancho: 'media' },
      { id: 'medico', tipo: 'texto', etiqueta: 'Médico y clínica u hospital (IPS) donde lo ordenaron', ejemplo: 'Ej.: Dra. Ana Torres, oncóloga, Hospital Pablo Tobón Uribe', ancho: 'completa' },
      { id: 'respuestaEps', tipo: 'select', etiqueta: '¿Qué ha hecho la EPS?', opciones: [
        { v: 'nada', t: 'Nada: "está en trámite", "no hay agenda", "no hay contrato"', legal: 'se ha limitado a responder que el servicio está en trámite, que no hay agenda o que no tiene contrato con un prestador' },
        { v: 'nego', t: 'Lo negó por escrito (no cubierto, falta trámite, "no pertinente")', legal: 'negó expresamente el servicio con argumentos administrativos o económicos' },
        { v: 'autorizo_sin_cita', t: 'Lo autorizó pero no hay fecha ni IPS que lo preste', legal: 'expidió la autorización pero no ha garantizado la prestación efectiva por falta de agenda o de prestador' },
        { v: 'incompleto', t: 'Entrega incompleta o interrumpió el tratamiento', legal: 'realiza entregas incompletas o interrumpió un tratamiento ya iniciado' },
        { v: 'lejos', t: 'Lo asignó en otra ciudad sin transporte', legal: 'asignó el servicio en otra ciudad sin garantizar el transporte y el alojamiento' }
      ], valorInicial: 'nada', ancho: 'completa' },
      { id: 'riesgo', tipo: 'textarea', etiqueta: '¿Qué le pasa al paciente por la demora? (dolor, deterioro, riesgo de muerte, pérdida de función)', requerido: true, filas: 3 },
      { id: 'recursos', tipo: 'radio', etiqueta: '¿El paciente o su familia pueden pagar el servicio por su cuenta?', opciones: [ { v: 'no', t: 'No, no tenemos los recursos' }, { v: 'si', t: 'Sí, pero la EPS está obligada' } ], requerido: true },
      ...C.previo({ etiqueta: '¿Reclamaste por escrito a la EPS o pusiste queja en la Supersalud?' }),
      C.relato({ requerido: false, etiqueta: '¿Algo más que el juez deba saber? (opcional)' })
    ],
    asunto: d => `Acción de tutela – Derecho fundamental a la salud – ${d.servicio || 'servicio ordenado por el médico tratante'}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} se encuentra afiliad${a.o} a ${R.entidad(d)} en el ${R.opcionTexto(cd('tut_salud_servicio', 'regimen'), d.regimen)}${a.doc ? ` e identificad${a.o} con ${a.doc}` : ''}.`);
      h.push(`Padece ${d.diagnostico || '[diagnóstico]'}, y ${d.fechaOrden ? `${R.elDia(d.fechaOrden)} ` : ''}${d.medico ? `el médico tratante ${d.medico}` : 'su médico tratante, adscrito a la red de la EPS,'} le ordenó ${R.opcionTexto(cd('tut_salud_servicio', 'tipoServicio'), d.tipoServicio)} "${d.servicio || '[servicio]'}".`);
      h.push(`Pese a la orden médica, ${R.entidad(d)} ${R.opcionTexto(cd('tut_salud_servicio', 'respuestaEps'), d.respuestaEps)}.`);
      h.push(`La falta del servicio está causando un daño grave a la salud: ${R.oracion(d.riesgo)}`);
      if (d.recursos === 'no') h.push(`${a.Nom} y su familia carecen de los recursos económicos para asumir el costo del servicio por su cuenta${R.bajosRecursos(d) ? ', como se acredita con la clasificación del Sisbén y demás documentos anexos' : ''}.`);
      h.push(...R.hechosPrevio(d, 'la autorización y prestación del servicio'));
      return h;
    },
    derechos: [
      { v: 'salud', inicial: true, t: 'Salud', legal: 'derecho fundamental a la salud (artículo 49 de la Constitución y Ley 1751 de 2015)' },
      { v: 'vida', inicial: true, t: 'Vida digna e integridad', legal: 'derecho a la vida en condiciones dignas y a la integridad personal (artículos 1, 11 y 12 de la Constitución)' },
      { v: 'seguridad', t: 'Seguridad social', legal: 'derecho a la seguridad social (artículo 48 de la Constitución)' },
      { v: 'especial', t: 'Protección especial (niños, adultos mayores, discapacidad)', legal: 'derechos de los sujetos de especial protección constitucional (artículos 13, 44, 46 y 47 de la Constitución)' }
    ],
    normas: ['cp86', 'cp49', 'l1751_2', 'l1751_6', 'l1751_8', 'l1751_10', 'l1751_14', 'l1751_17', 't760', 'c313', 'd2591_42'],
    fundamentos: d => {
      const f = [];
      if (d.tipoServicio === 'medicamento' || d.tipoServicio === 'insumos') f.push(AJ.normas.res1604.texto + ` (${AJ.normas.res1604.cita}).`);
      if (d.tipoServicio === 'cita') f.push(AJ.normas.res1552.texto + ` (${AJ.normas.res1552.cita}).`);
      if (d.respuestaEps === 'nego') f.push(AJ.normas.l1751_15.texto + ` (${AJ.normas.l1751_15.cita}).`, AJ.normas.mipres.texto + ` (${AJ.normas.mipres.cita}).`);
      if (d.respuestaEps === 'lejos' || d.recursos === 'no') f.push(AJ.normas.integral.texto + ` (${AJ.normas.integral.cita}).`);
      if ((d.condicion || []).length) f.push(AJ.normas.l1751_11.texto + ` (${AJ.normas.l1751_11.cita}).`);
      return f;
    },
    procedencia: d => [
      'Subsidiariedad: aunque la Superintendencia Nacional de Salud tiene funciones jurisdiccionales (artículo 41 de la Ley 1122 de 2007, modificado por el artículo 6 de la Ley 1949 de 2019), la Corte Constitucional ha reiterado (sentencias T-425 de 2017, T-224 de 2020 y SU-508 de 2020) que ese mecanismo no puede presumirse idóneo ni eficaz, y que la tutela procede de manera directa cuando está comprometida la vida, la integridad o la dignidad del paciente, cuando se trata de sujetos de especial protección constitucional o cuando la urgencia hace indispensable la intervención del juez constitucional.',
      'Inmediatez: la vulneración es actual y continúa, pues el servicio sigue sin prestarse y el daño a la salud se agrava con cada día de demora.'
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja los derechos vulnerados', legal: d => `TUTELAR los derechos fundamentales a la salud, a la vida digna y a la seguridad social de ${R.actor(d).nom}, vulnerados por ${R.entidad(d)}.` },
      { v: 'ordenar', inicial: true, t: 'Que ordene a la EPS autorizar y prestar el servicio en 48 horas', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes a la notificación del fallo, autorice y garantice la prestación efectiva de ${R.opcionTexto(cd('tut_salud_servicio', 'tipoServicio'), d.tipoServicio)} "${d.servicio || '[servicio]'}", que ordenó el médico tratante, en una IPS de la red con la oportunidad que la condición del paciente exige.` },
      { v: 'integral', inicial: true, t: 'Que ordene el tratamiento integral de la enfermedad', legal: d => `ORDENAR a ${R.entidad(d)} que garantice el tratamiento integral de ${d.diagnostico || 'la enfermedad diagnosticada'}, suministrando sin dilaciones ni trámites administrativos adicionales todos los servicios, medicamentos, insumos, controles y procedimientos que ordene el médico tratante en relación con dicha patología.` },
      { v: 'transporte', t: 'Que cubra transporte, alojamiento y un acompañante', legal: d => `ORDENAR a ${R.entidad(d)} que asuma los gastos de transporte, alojamiento y alimentación del paciente y de un acompañante cuando los servicios deban prestarse fuera de su municipio de residencia.` },
      { v: 'cuidador', t: 'Que garantice cuidador o atención domiciliaria', legal: d => `ORDENAR a ${R.entidad(d)} que valore la necesidad de atención domiciliaria y de un cuidador, y los suministre si el médico tratante los considera necesarios.` },
      { v: 'desacato', inicial: true, t: 'Que advierta a la EPS sobre el desacato si no cumple', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato previsto en el artículo 52 del Decreto 2591 de 1991.` }
    ],
    medida: d => `Solicito respetuosamente que, con fundamento en el artículo 7 del Decreto 2591 de 1991, se decrete como MEDIDA PROVISIONAL, desde la admisión de la tutela, que ${R.entidad(d)} autorice y preste de inmediato ${R.opcionTexto(cd('tut_salud_servicio', 'tipoServicio'), d.tipoServicio)} "${d.servicio || '[servicio]'}", pues la espera del fallo puede causar un daño irreversible: ${R.oracion(d.medidaTexto || d.riesgo)}`,
    anexos: [ { v: 'cedula', t: 'Copia de la cédula del paciente (y de quien presenta la tutela, si es otra persona)' }, { v: 'orden', t: 'Copia de la orden médica o fórmula' }, { v: 'historia', t: 'Historia clínica o epicrisis' }, { v: 'negativa', t: 'Respuesta o negativa de la EPS (si existe)' }, { v: 'peticion', t: 'Copia del derecho de petición o queja previa' }, { v: 'sisben', t: 'Certificado del Sisbén o prueba de falta de recursos' }, { v: 'fotos', t: 'Fotos o certificados que muestren la condición del paciente' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'El juez debe fallar en máximo 10 días. Preséntala por Tutela en Línea o en la Oficina de Reparto del municipio. No necesitas abogado.', siNoResponden: 'Si el juez concede la tutela y la EPS incumple el plazo ordenado en el fallo, informa al juzgado y solicita el cumplimiento; según el caso, puede proceder el incidente de desacato. Si la niega, revisa el término de tres días para impugnar desde la notificación.' }
  },

  /* ---------------- TUTELA SALUD: TRATAMIENTO INTEGRAL / ENFERMEDAD CRÓNICA ---------------- */
  {
    id: 'tut_salud_integral', tipo: 'tutela', categoria: 'eps',
    titulo: 'Tutela por tratamiento integral (enfermedad crónica, discapacidad, cáncer, adulto mayor)',
    resumen: 'Para pacientes que deben pelear cada servicio: la tutela pide que el juez ordene a la EPS garantizar TODO el tratamiento, más transporte, cuidador, insumos y suministros, sin nuevas tutelas.',
    palabras: ['tratamiento integral', 'crónico', 'cáncer', 'discapacidad', 'adulto mayor', 'cuidador', 'transporte', 'pañales', 'suplementos', 'diálisis', 'quimioterapia', 'parálisis', 'autismo', 'terapias', 'EPS'],
    destinatario: { categoria: 'eps', ejemploNombre: 'Ej.: Savia Salud EPS', cargo: 'Representante legal' },
    campos: [
      { id: 'diagnostico', tipo: 'texto', etiqueta: 'Diagnóstico principal', requerido: true, ancho: 'completa' },
      { id: 'estado', tipo: 'textarea', etiqueta: 'Estado actual del paciente (movilidad, dependencia, dolor, cuidados que necesita)', requerido: true, filas: 3 },
      { id: 'servicios', tipo: 'textarea', etiqueta: '¿Qué servicios le han negado, demorado o entregado incompletos? (uno por línea, con fechas)', requerido: true, filas: 4, ejemplo: 'Ej.:\nPañales: ordenados en marzo, entregan 30 al mes cuando el médico ordenó 120.\nTerapia física: autorizada en abril, solo han dado 2 de 20 sesiones.\nCita con neurología: en espera desde febrero.' },
      { id: 'necesidades', tipo: 'checks', etiqueta: '¿Qué apoyos adicionales necesita el paciente?', opciones: [
        { v: 'transporte', t: 'Transporte a las citas (no hay dinero o no puede movilizarse)', legal: 'el transporte a las citas y procedimientos, con acompañante' },
        { v: 'cuidador', t: 'Cuidador o enfermería en casa', legal: 'el servicio de cuidador o enfermería domiciliaria' },
        { v: 'insumos', t: 'Pañales, cremas, suplementos nutricionales', legal: 'los insumos de higiene y los suplementos nutricionales' },
        { v: 'equipos', t: 'Cama hospitalaria, silla de ruedas, oxígeno', legal: 'los equipos y dispositivos de apoyo (cama hospitalaria, silla de ruedas, oxígeno)' },
        { v: 'domiciliaria', t: 'Atención médica en casa', legal: 'la atención médica domiciliaria' }
      ] },
      { id: 'recursos', tipo: 'textarea', etiqueta: 'Situación económica de la familia', ejemplo: 'Ej.: Vivimos de un salario mínimo; soy la única cuidadora y no puedo trabajar.', requerido: true, filas: 2 },
      C.relato({ requerido: false, etiqueta: '¿Algo más que el juez deba saber? (opcional)' })
    ],
    asunto: d => `Acción de tutela – Derecho fundamental a la salud – Tratamiento integral de ${d.diagnostico || 'paciente con enfermedad crónica'}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} está afiliad${a.o} a ${R.entidad(d)} y padece ${d.diagnostico || '[diagnóstico]'}.`);
      h.push(`Estado actual: ${R.oracion(d.estado)}`);
      h.push(`La EPS ha incumplido de manera reiterada las órdenes del médico tratante, obligando a la familia a reclamar servicio por servicio: ${R.relatoAHechos(d.servicios).join(' ')}`);
      if ((d.necesidades || []).length) h.push(`El paciente requiere, además, ${R.lista(d.necesidades.map(v => R.opcionTexto(cd('tut_salud_integral', 'necesidades'), v)))}.`);
      h.push(`Situación económica: ${R.oracion(d.recursos)}`);
      return h;
    },
    derechos: [
      { v: 'salud', inicial: true, t: 'Salud', legal: 'derecho fundamental a la salud (artículo 49 de la Constitución y Ley 1751 de 2015)' },
      { v: 'vida', inicial: true, t: 'Vida digna', legal: 'derecho a la vida en condiciones dignas (artículos 1 y 11 de la Constitución)' },
      { v: 'especial', inicial: true, t: 'Protección especial', legal: 'derechos de los sujetos de especial protección constitucional (artículos 13, 46 y 47 de la Constitución)' },
      { v: 'seguridad', t: 'Seguridad social', legal: 'derecho a la seguridad social (artículo 48 de la Constitución)' }
    ],
    normas: ['cp86', 'cp49', 'cp13', 'l1751_2', 'l1751_6', 'l1751_8', 'l1751_11', 'l1751_17', 't760', 'integral', 'l1618', 'd2591_42'],
    procedencia: d => [
      'Subsidiariedad: la Corte Constitucional ha señalado que la tutela es el mecanismo procedente para proteger la salud de pacientes con enfermedades crónicas o catastróficas y de sujetos de especial protección, pues los demás medios (Supersalud, jurisdicción ordinaria) no ofrecen la celeridad que su condición exige (sentencias T-760 de 2008, T-081 de 2019 y SU-508 de 2020).',
      'La orden de tratamiento integral se justifica porque la EPS ha mostrado negligencia reiterada y el paciente no puede verse obligado a instaurar una nueva acción por cada servicio que requiera.'
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja los derechos', legal: d => `TUTELAR los derechos fundamentales a la salud, a la vida digna y a la seguridad social de ${R.actor(d).nom}.` },
      { v: 'servicios', inicial: true, t: 'Que ordene prestar de inmediato los servicios pendientes', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes, autorice y preste de manera efectiva todos los servicios, medicamentos e insumos relacionados en los hechos, en las cantidades y frecuencias ordenadas por el médico tratante.` },
      { v: 'integral', inicial: true, t: 'Que ordene el tratamiento integral', legal: d => `ORDENAR a ${R.entidad(d)} garantizar el tratamiento integral de ${d.diagnostico || 'la patología diagnosticada'}, incluyendo todos los servicios, tecnologías, insumos, controles, rehabilitación y cuidados que prescriba el médico tratante, sin exigir trámites administrativos adicionales ni nuevas acciones judiciales.` },
      { v: 'apoyos', inicial: true, t: 'Que ordene transporte, cuidador, insumos y equipos', legal: d => `ORDENAR a ${R.entidad(d)} que suministre ${R.lista((d.necesidades || []).map(v => R.opcionTexto(cd('tut_salud_integral', 'necesidades'), v))) || 'los apoyos requeridos (transporte con acompañante, cuidador, insumos y equipos)'}, previa valoración del médico tratante cuando sea necesaria, la cual deberá realizarse dentro de los cinco (5) días siguientes.` },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` }
    ],
    medida: d => `Solicito como MEDIDA PROVISIONAL (artículo 7 del Decreto 2591 de 1991) que se ordene a ${R.entidad(d)} suministrar de inmediato los servicios e insumos cuya falta pone en riesgo la vida o la integridad del paciente: ${R.oracion(d.medidaTexto || d.servicios)}`,
    anexos: [ { v: 'cedula', t: 'Cédulas del paciente y de quien presenta la tutela' }, { v: 'historia', t: 'Historia clínica completa' }, { v: 'ordenes', t: 'Órdenes médicas de todos los servicios' }, { v: 'negativas', t: 'Negativas, autorizaciones vencidas o respuestas de la EPS' }, { v: 'discapacidad', t: 'Certificado de discapacidad o dictamen (si existe)' }, { v: 'sisben', t: 'Sisbén o prueba de la situación económica' }, { v: 'tutelas', t: 'Fallos de tutelas anteriores (si hubo)' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'Si el paciente no puede actuar, el familiar presenta la tutela como "agente oficioso" (ya está contemplado en el documento).', siNoResponden: 'Si la EPS incumple el fallo, "Incidente de desacato". El juez conserva competencia hasta que el derecho esté restablecido.' }
  },

  /* ---------------- TUTELA POR DERECHO DE PETICIÓN ---------------- */
  {
    id: 'tut_peticion', tipo: 'tutela', categoria: 'municipio',
    titulo: 'Tutela porque no respondieron mi derecho de petición',
    resumen: 'Para pedir protección judicial cuando no recibes respuesta o esta no resuelve de fondo tu petición, según el término aplicable. El juez evalúa el caso y, si concede la tutela, fija las órdenes y su plazo de cumplimiento.',
    palabras: ['tutela', 'derecho de petición', 'no respondieron', 'sin respuesta', 'silencio', '15 días', 'respuesta evasiva', 'radicado'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Colpensiones / Alcaldía de Soacha / EPS Sanitas' },
    campos: [
      { id: 'fechaPeticion', tipo: 'fecha', etiqueta: '¿Cuándo radicaste el derecho de petición?', requerido: true, ancho: 'media' },
      { id: 'radicado', tipo: 'texto', etiqueta: 'Número de radicado (si lo tienes)', ancho: 'media' },
      { id: 'medio', tipo: 'select', etiqueta: '¿Cómo lo presentaste?', opciones: [ { v: 'escrito', t: 'Por escrito en ventanilla (tengo sello de recibido)', legal: 'por escrito, con constancia de recibido' }, { v: 'correo', t: 'Por correo electrónico (tengo el correo enviado)', legal: 'por correo electrónico, con constancia de envío' }, { v: 'web', t: 'Por la página web o app (tengo radicado)', legal: 'a través del canal virtual, con número de radicado' }, { v: 'sin_prueba', t: 'La entregué, pero no tengo sello ni radicado', legal: 'de manera personal en la entidad' } ], valorInicial: 'escrito', ancho: 'media' },
      { id: 'infoSinPrueba', tipo: 'info', mostrarSi: { campo: 'medio', valor: 'sin_prueba' }, texto: 'Sin prueba de que entregaste la petición, el juez casi siempre niega la tutela. Vuelve a presentarla y pide sello con fecha en tu copia, o envíala por correo electrónico y guarda el envío. Si no responden en el plazo, entonces presenta esta tutela.' },
      { id: 'tipoPeticion', tipo: 'select', etiqueta: '¿Qué tipo de petición era?', opciones: [ { v: 'general', t: 'Petición general (15 días hábiles)', legal: 'una petición de interés particular', dias: 15 }, { v: 'documentos', t: 'Información o copias (10 días hábiles)', legal: 'una petición de información y documentos', dias: 10 }, { v: 'consulta', t: 'Consulta (30 días hábiles)', legal: 'una consulta', dias: 30 } ], valorInicial: 'general', ancho: 'media' },
      { id: 'objeto', tipo: 'textarea', etiqueta: '¿Qué pedías en esa petición?', requerido: true, filas: 3, ejemplo: 'Ej.: Que me informaran el estado de mi solicitud de pensión y corrigieran mi historia laboral.' },
      { id: 'respuesta', tipo: 'select', etiqueta: '¿Qué ha pasado desde entonces?', opciones: [
        { v: 'nada', t: 'No han respondido nada', legal: 'no ha recibido ninguna respuesta' },
        { v: 'parcial', t: 'Respondieron algo, pero no resuelve lo que pedí (evasivo)', legal: 'recibió una comunicación que no resuelve de fondo lo pedido, pues es evasiva, parcial o se refiere a asuntos distintos' },
        { v: 'tramite', t: 'Solo dijeron "está en trámite"', legal: 'solo recibió una respuesta en la que se indica que la solicitud "se encuentra en trámite", sin resolverla' },
        { v: 'remitieron', t: 'Dijeron que la enviaron a otra oficina y nadie responde', legal: 'fue informado de una remisión a otra dependencia, sin que ninguna haya resuelto' }
      ], valorInicial: 'nada', ancho: 'completa' },
      { id: 'importancia', tipo: 'textarea', etiqueta: '¿Por qué necesitas esa respuesta? (qué derecho o trámite depende de ella)', requerido: true, filas: 2 }
    ],
    asunto: d => `Acción de tutela – Derecho fundamental de petición – Radicado ${d.radicado || 'sin número'} del ${R.fechaLarga(d.fechaPeticion)}`,
    hechos: d => {
      const a = R.actor(d);
      const op = cd('tut_peticion', 'tipoPeticion').opciones.find(o => o.v === d.tipoPeticion) || { dias: 15 };
      const f = AJ.festivos.parseISO(d.fechaPeticion);
      const venc = f ? AJ.festivos.sumarDiasHabiles(f, op.dias) : null;
      const h = [];
      const quien = a.tercero ? `${R.mayus(d.nombre)}, en nombre de ${a.nom},` : a.nom;
      h.push(`${R.capital(R.elDia(d.fechaPeticion))}, ${quien} presentó ante ${R.entidad(d)} ${R.opcionTexto(cd('tut_peticion', 'tipoPeticion'), d.tipoPeticion)} ${R.opcionTexto(cd('tut_peticion', 'medio'), d.medio)}${d.radicado ? `, radicada bajo el número ${d.radicado}` : ''}.`);
      h.push(`En dicha petición solicitó: ${R.oracion(d.objeto)}`);
      const vencido = venc && venc < R.hoy();
      if (venc) h.push(`El término legal de ${R.dias(op.dias, 'habiles')} para resolverla ${vencido ? 'venció' : 'vence'} el ${R.fechaLarga(venc)}${vencido ? `, es decir, hace ${AJ.festivos.diasHabilesEntre(venc, R.hoy())} días hábiles` : ''}.`);
      h.push(`A la fecha, ${quien} ${R.opcionTexto(cd('tut_peticion', 'respuesta'), d.respuesta)}.`);
      h.push(`La respuesta es necesaria porque: ${R.oracion(d.importancia)}`);
      return h;
    },
    derechos: [
      { v: 'peticion', inicial: true, t: 'Derecho de petición', legal: 'derecho fundamental de petición (artículo 23 de la Constitución y Ley 1755 de 2015)' },
      { v: 'debido', t: 'Debido proceso administrativo', legal: 'derecho al debido proceso administrativo (artículo 29 de la Constitución)' },
      { v: 'informacion', t: 'Acceso a la información', legal: 'derecho de acceso a la información pública (artículo 74 de la Constitución y Ley 1712 de 2014)' },
      { v: 'conexo', t: 'El derecho que dependía de la respuesta (salud, pensión, etc.)', legal: 'los derechos cuya garantía depende de la respuesta (seguridad social, salud, mínimo vital, según los hechos)' }
    ],
    normas: ['cp86', 'cp23', 'l1755_13', 'l1755_14', 'l1755_14p', 'l1755_21', 'l1755_31', 'l1755_32', 'l1755_33', 't377', 'c951'],
    procedencia: d => [
      'Subsidiariedad: la jurisprudencia constitucional es uniforme en señalar que no existe otro medio de defensa judicial idóneo para obtener una respuesta a un derecho de petición, por lo que la tutela es el mecanismo procedente y directo (Sentencia C-951 de 2014, entre muchas otras).',
      'Inmediatez: la vulneración persiste, pues la petición continúa sin respuesta de fondo.'
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja el derecho de petición', legal: d => `TUTELAR el derecho fundamental de petición de ${R.actor(d).nom}, vulnerado por ${R.entidad(d)}.` },
      { v: 'responder', inicial: true, t: 'Que ordene responder de fondo en 48 horas', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes a la notificación del fallo, dé respuesta de fondo, clara, completa y congruente a la petición ${d.radicado ? `No. ${d.radicado} ` : ''}del ${R.fechaLarga(d.fechaPeticion)}, y la notifique a la parte accionante en la dirección y el correo indicados en esta tutela.` },
      { v: 'desacato', inicial: true, t: 'Que advierta a la entidad sobre el desacato', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` },
      { v: 'disciplinario', t: 'Que compulse copias a la Procuraduría por la omisión', legal: 'COMPULSAR copias a la Procuraduría General de la Nación o a la oficina de control interno disciplinario para que investigue la omisión, conforme al artículo 31 de la Ley 1755 de 2015.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'peticion', t: 'Copia del derecho de petición con sello de recibido, radicado o correo enviado (INDISPENSABLE)' }, { v: 'respuesta', t: 'Copia de la respuesta evasiva, si existe' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'La prueba clave es la constancia de que radicaste la petición. Sin ella, el juez puede negar la tutela.', siNoResponden: 'Si la entidad incumple el plazo ordenado en el fallo, informa al juzgado y solicita el cumplimiento; según las circunstancias puede proceder el incidente de desacato.' }
  },

  /* ---------------- TUTELA MÍNIMO VITAL: SALARIOS ---------------- */
  {
    id: 'tut_salario', tipo: 'tutela', categoria: 'empleador',
    titulo: 'Tutela por salarios u honorarios no pagados (mínimo vital)',
    resumen: 'Cuando el empleador o contratante deja de pagar y eso te deja sin cómo vivir. La tutela procede excepcionalmente, por afectación del mínimo vital.',
    palabras: ['tutela', 'salario', 'sueldo', 'no me pagan', 'mínimo vital', 'honorarios', 'empleador', 'empresa', 'contrato', 'quincena', 'prestación de servicios', 'alcaldía no paga'],
    destinatario: { categoria: 'empleador', ejemploNombre: 'Ej.: Constructora ABC S.A.S. / Hospital Municipal E.S.E.' },
    campos: [
      { id: 'vinculo', tipo: 'select', etiqueta: 'Tipo de vínculo', opciones: [ { v: 'laboral', t: 'Contrato de trabajo', legal: 'contrato de trabajo' }, { v: 'prestacion', t: 'Contrato de prestación de servicios', legal: 'contrato de prestación de servicios' }, { v: 'verbal', t: 'Sin contrato escrito', legal: 'contrato de trabajo verbal' }, { v: 'publico', t: 'Servidor público o contratista del Estado', legal: 'vinculación con una entidad pública' } ], valorInicial: 'laboral', ancho: 'media' },
      { id: 'cargo', tipo: 'texto', etiqueta: 'Cargo u oficio', ancho: 'media' },
      { id: 'salario', tipo: 'texto', etiqueta: 'Salario u honorarios mensuales', requerido: true, ancho: 'media' },
      { id: 'periodos', tipo: 'texto', etiqueta: 'Períodos sin pagar', ejemplo: 'Ej.: Julio, agosto y septiembre de 2026', requerido: true, ancho: 'media' },
      { id: 'valorDeuda', tipo: 'texto', etiqueta: 'Total adeudado (aproximado)', ancho: 'media' },
      { id: 'activo', tipo: 'radio', etiqueta: '¿Sigues trabajando allí?', opciones: [ { v: 'si', t: 'Sí' }, { v: 'no', t: 'No, ya terminó' } ], requerido: true, ancho: 'media' },
      { id: 'dependientes', tipo: 'texto', etiqueta: '¿Quiénes dependen de ese ingreso?', ejemplo: 'Ej.: Mis dos hijos menores y mi madre de 70 años', requerido: true, ancho: 'completa' },
      { id: 'afectacion', tipo: 'textarea', etiqueta: '¿Qué consecuencias ha tenido el no pago? (arriendo, comida, servicios, salud, deudas)', requerido: true, filas: 3 },
      { id: 'otrosIngresos', tipo: 'radio', etiqueta: '¿Tienes otros ingresos?', opciones: [ { v: 'no', t: 'No, ese era mi único ingreso' }, { v: 'si', t: 'Sí, pero no alcanzan' } ], requerido: true },
      ...C.previo({ etiqueta: '¿Reclamaste por escrito al empleador?' }),
      C.relato({ requerido: false, etiqueta: '¿Algo más que el juez deba saber? (opcional)' })
    ],
    asunto: d => 'Acción de tutela – Derecho fundamental al mínimo vital – Salarios adeudados',
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} ${d.activo === 'si' ? 'presta' : 'prestó'} sus servicios a ${R.entidad(d)} mediante ${R.opcionTexto(cd('tut_salario', 'vinculo'), d.vinculo)}${d.cargo ? `, en el cargo de ${d.cargo}` : ''}, con una remuneración mensual de ${R.moneda(d.salario) || d.salario}.`);
      h.push(`${R.entidad(d)} no ha pagado la remuneración correspondiente a ${d.periodos}${d.valorDeuda ? `, para un total aproximado de ${R.moneda(d.valorDeuda) || d.valorDeuda}` : ''}.`);
      h.push(`De ese ingreso dependen ${d.dependientes}. ${d.otrosIngresos === 'no' ? 'Constituye el único ingreso del hogar.' : 'Los demás ingresos del hogar son insuficientes para cubrir las necesidades básicas.'}`);
      h.push(`El no pago ha afectado gravemente la subsistencia del hogar: ${R.oracion(d.afectacion)}`);
      h.push(...R.hechosPrevio(d, 'el pago de los salarios adeudados'));
      return h;
    },
    derechos: [
      { v: 'minimo', inicial: true, t: 'Mínimo vital', legal: 'derecho fundamental al mínimo vital y a la vida digna (artículos 1, 11 y 53 de la Constitución)' },
      { v: 'trabajo', inicial: true, t: 'Trabajo en condiciones dignas', legal: 'derecho al trabajo en condiciones dignas y justas y a la remuneración mínima vital y móvil (artículos 25 y 53 de la Constitución)' },
      { v: 'seguridad', t: 'Seguridad social', legal: 'derecho a la seguridad social (artículo 48 de la Constitución)' },
      { v: 'ninos', t: 'Derechos de los niños que dependen del ingreso', legal: 'derechos fundamentales de los niños que dependen del ingreso (artículo 44 de la Constitución)' }
    ],
    normas: ['cp86', 'cp25', 'cp53', 'cst_57', 'cst_134', 'su995', 'd2591_42', 'cp1'],
    procedencia: d => [
      'Subsidiariedad: aunque existe la acción ordinaria laboral, la Corte Constitucional (SU-995 de 1999 y T-016 de 2015, entre otras) ha establecido que la tutela procede para el pago de salarios cuando su retención afecta el mínimo vital del trabajador y su familia, pues el proceso ordinario no es eficaz frente a la urgencia de atender las necesidades básicas. La afectación del mínimo vital se presume cuando el salario es la única fuente de ingresos del trabajador, cuando el incumplimiento se prolonga por más de dos meses o cuando la remuneración equivale al salario mínimo, y el empleador no desvirtúa esa situación.',
      'Inmediatez: el incumplimiento es actual y sus efectos sobre la subsistencia del hogar se agravan cada día.'
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja el mínimo vital', legal: d => `TUTELAR los derechos fundamentales al mínimo vital, al trabajo en condiciones dignas y a la seguridad social de ${R.actor(d).nom}.` },
      { v: 'pagar', inicial: true, t: 'Que ordene pagar los salarios adeudados en 48 horas', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes a la notificación del fallo, pague la totalidad de la remuneración adeudada correspondiente a ${d.periodos}, y en adelante cancele oportunamente los salarios causados.` },
      { v: 'seguridad', t: 'Que ordene pagar la seguridad social atrasada', legal: d => `ORDENAR a ${R.entidad(d)} que se ponga al día en los aportes a salud, pensión y riesgos laborales del accionante.` },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` }
    ],
    medida: d => `Solicito como MEDIDA PROVISIONAL (artículo 7 del Decreto 2591 de 1991) que se ordene a ${R.entidad(d)} el pago inmediato de al menos un mes de la remuneración adeudada, pues la espera del fallo puede causar un daño irreversible: ${R.oracion(d.medidaTexto || d.afectacion)}`,
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'contrato', t: 'Contrato o prueba de la relación (carné, mensajes, testigos)' }, { v: 'pagos', t: 'Desprendibles o consignaciones de meses anteriores' }, { v: 'reclamo', t: 'Copia de la reclamación al empleador' }, { v: 'gastos', t: 'Recibos de arriendo, servicios, deudas (prueba del mínimo vital)' }, { v: 'registros', t: 'Registros civiles de los hijos' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'La tutela es excepcional: funciona mejor cuando pruebas que ese ingreso es el único y que hay personas a cargo. Para la liquidación completa necesitarás demanda laboral (consultorio jurídico).', siNoResponden: 'Si el juez niega la tutela por existir la vía ordinaria, acude a un consultorio jurídico universitario para la demanda laboral y presenta queja ante el Ministerio del Trabajo.' }
  },

  /* ---------------- TUTELA INCAPACIDADES ---------------- */
  {
    id: 'tut_incapacidades', tipo: 'tutela', categoria: 'eps',
    titulo: 'Tutela por incapacidades médicas no pagadas',
    resumen: 'La EPS, la ARL, el fondo de pensiones o el empleador no pagan las incapacidades y no tienes otro ingreso mientras estás enfermo.',
    palabras: ['tutela', 'incapacidad', 'incapacidades', 'no pagan', 'EPS', 'ARL', 'fondo de pensiones', 'enfermedad', '180 días', 'mínimo vital'],
    destinatario: { categoria: 'eps', ejemploNombre: 'Ej.: EPS Sanitas / Porvenir / ARL Sura' },
    campos: [
      { id: 'quien', tipo: 'select', etiqueta: '¿Quién debe pagar?', requerido: true, opciones: cd('pet_incapacidades', 'quien').opciones, ancho: 'completa' },
      { id: 'diagnostico', tipo: 'texto', etiqueta: 'Diagnóstico', requerido: true, ancho: 'media' },
      { id: 'diasAcumulados', tipo: 'texto', etiqueta: 'Días de incapacidad acumulados', ancho: 'media' },
      { id: 'periodos', tipo: 'textarea', etiqueta: 'Incapacidades sin pagar (fechas y días)', requerido: true, filas: 3 },
      { id: 'salario', tipo: 'texto', etiqueta: 'Salario o ingreso base', ancho: 'media' },
      { id: 'valorDeuda', tipo: 'texto', etiqueta: 'Valor aproximado adeudado', ancho: 'media' },
      { id: 'afectacion', tipo: 'textarea', etiqueta: '¿Cómo te afecta no recibir ese dinero? ¿Quién depende de ti?', requerido: true, filas: 3 },
      ...C.previo({ etiqueta: '¿Reclamaste por escrito el pago?' }),
      C.relato({ requerido: false, etiqueta: '¿Algo más que el juez deba saber? (opcional)' })
    ],
    asunto: d => 'Acción de tutela – Mínimo vital y seguridad social – Incapacidades no pagadas',
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} está afiliad${a.o} al Sistema de Seguridad Social Integral${d.salario ? `, con un ingreso base de cotización de ${R.moneda(d.salario) || d.salario}` : ''}, y se encuentra incapacitad${a.o} por su médico tratante con diagnóstico de ${d.diagnostico}${d.diasAcumulados ? `, acumulando ${d.diasAcumulados} días de incapacidad` : ''}.`);
      h.push(`Las siguientes incapacidades no han sido pagadas: ${R.relatoAHechos(d.periodos).join(' ')}${d.valorDeuda ? ` Valor aproximado: ${R.moneda(d.valorDeuda) || d.valorDeuda}.` : ''}`);
      h.push(`El pago corresponde a ${R.opcionTexto(cd('tut_incapacidades', 'quien'), d.quien)}, que ha omitido reconocerlo.`);
      h.push(`El subsidio por incapacidad es el único sustituto del salario durante la enfermedad: ${R.oracion(d.afectacion)}`);
      h.push(...R.hechosPrevio(d, 'el pago de las incapacidades'));
      return h;
    },
    derechos: [
      { v: 'minimo', inicial: true, t: 'Mínimo vital', legal: 'derecho fundamental al mínimo vital y a la vida digna (artículos 1, 11 y 53 de la Constitución)' },
      { v: 'seguridad', inicial: true, t: 'Seguridad social', legal: 'derecho a la seguridad social (artículo 48 de la Constitución)' },
      { v: 'salud', inicial: true, t: 'Salud', legal: 'derecho fundamental a la salud (artículo 49 de la Constitución)' }
    ],
    normas: ['cp86', 'cp48', 'cp53', 'l100_206', 'l1562', 'su995', 'd2591_42'],
    procedencia: d => [
      'Subsidiariedad: la Corte Constitucional (sentencias T-140 de 2016, T-401 de 2017, T-246 de 2018 y T-514 de 2020, entre otras) ha reiterado que la tutela procede para ordenar el pago de incapacidades cuando el trabajador enfermo carece de otros ingresos, pues el subsidio por incapacidad sustituye el salario y su no pago afecta el mínimo vital; en estos casos la jurisdicción ordinaria no es un medio eficaz.',
      'La Corte también ha señalado que las controversias entre EPS, AFP y empleador sobre quién debe pagar no pueden trasladarse al trabajador: el juez ordena el pago a la entidad que corresponda según la etapa de la incapacidad (EPS del día 3 al 180; administradora de pensiones del 181 al 540, incluso cuando el concepto de rehabilitación es desfavorable, conforme a la Sentencia C-270 de 2023; EPS a partir del día 541, artículo 67 de la Ley 1753 de 2015).'
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja los derechos', legal: d => `TUTELAR los derechos fundamentales al mínimo vital, a la seguridad social y a la salud de ${R.actor(d).nom}.` },
      { v: 'pagar', inicial: true, t: 'Que ordene pagar las incapacidades en 48 horas', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes a la notificación del fallo, reconozca y pague la totalidad de las incapacidades relacionadas en los hechos, y continúe pagando oportunamente las que se expidan mientras subsista la incapacidad.` },
      { v: 'concepto', t: 'Que ordene emitir el concepto de rehabilitación y la calificación', legal: d => `ORDENAR a ${R.entidad(d)} emitir el concepto de rehabilitación y remitirlo a la administradora de pensiones, e iniciar el trámite de calificación de pérdida de capacidad laboral.` },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` }
    ],
    medida: d => `Solicito como MEDIDA PROVISIONAL (artículo 7 del Decreto 2591 de 1991) que se ordene a ${R.entidad(d)} pagar de inmediato las incapacidades adeudadas, pues la espera del fallo puede causar un daño irreversible: ${R.oracion(d.medidaTexto || d.afectacion)}`,
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'incapacidades', t: 'Copia de todos los certificados de incapacidad' }, { v: 'historia', t: 'Historia clínica' }, { v: 'reclamo', t: 'Copia de la reclamación previa y la respuesta' }, { v: 'pagos', t: 'Soportes de incapacidades pagadas anteriormente' }, { v: 'gastos', t: 'Pruebas del mínimo vital (arriendo, hijos, deudas)' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, siNoResponden: 'Si no cumplen el fallo: "Incidente de desacato".' }
  },

  /* ---------------- TUTELA PENSIÓN ---------------- */
  {
    id: 'tut_pension', tipo: 'tutela', categoria: 'nacional',
    titulo: 'Tutela porque no resuelven o no pagan mi pensión',
    resumen: 'Colpensiones o el fondo privado no deciden la solicitud en los 4 meses (2 para sobrevivientes), no te incluyen en nómina o no corrigen la historia laboral, y eres adulto mayor, inválido o sin ingresos.',
    palabras: ['tutela', 'pensión', 'Colpensiones', 'fondo', 'Porvenir', 'Protección', 'vejez', 'invalidez', 'sobrevivientes', 'nómina', 'adulto mayor', 'historia laboral', 'no resuelven'],
    destinatario: { categoria: 'nacional', nombre: 'Colpensiones (Administradora Colombiana de Pensiones)', cargo: 'Representante legal' },
    campos: [
      { id: 'tramite', tipo: 'select', etiqueta: '¿Cuál es el problema?', requerido: true, opciones: [
        { v: 'vejez', t: 'Pedí la pensión de vejez y no la resuelven (más de 4 meses)', legal: 'la solicitud de pensión de vejez' },
        { v: 'invalidez', t: 'Pedí la pensión de invalidez y no la resuelven', legal: 'la solicitud de pensión de invalidez' },
        { v: 'sobrevivientes', t: 'Pedí la pensión de sobrevivientes y no la resuelven (más de 2 meses)', legal: 'la solicitud de pensión de sobrevivientes' },
        { v: 'nomina', t: 'Me reconocieron la pensión pero no me pagan ni me incluyen en nómina', legal: 'la inclusión en nómina y el pago de la pensión reconocida' },
        { v: 'historia', t: 'No corrigen mi historia laboral y por eso me niegan la pensión', legal: 'la corrección de la historia laboral' }
      ], ancho: 'completa' },
      { id: 'fechaSolicitud', tipo: 'fecha', etiqueta: 'Fecha de la solicitud de pensión', requerido: true, ancho: 'media' },
      { id: 'radicado', tipo: 'texto', etiqueta: 'Radicado o número de resolución', ancho: 'media' },
      { id: 'edad', tipo: 'texto', etiqueta: 'Edad del afectado', requerido: true, ancho: 'media' },
      { id: 'semanas', tipo: 'texto', etiqueta: 'Semanas cotizadas', ancho: 'media' },
      { id: 'situacion', tipo: 'textarea', etiqueta: 'Situación económica y de salud (de qué vive, quién lo mantiene, enfermedades)', requerido: true, filas: 3 },
      ...C.previo({ etiqueta: '¿Ya presentaste derecho de petición pidiendo que resolvieran?' }),
      C.relato({ requerido: false, etiqueta: '¿Algo más que el juez deba saber? (opcional)' })
    ],
    asunto: d => `Acción de tutela – Seguridad social, mínimo vital y petición – ${R.opcionTexto(cd('tut_pension', 'tramite'), d.tramite)}`,
    hechos: d => {
      const a = R.actor(d);
      const f = AJ.festivos.parseISO(d.fechaSolicitud);
      const meses = f ? Math.floor((R.hoy() - f) / (30.44 * 24 * 3600 * 1000)) : null;
      const h = [];
      h.push(`${a.Nom}, de ${d.edad} años de edad, está afiliad${a.o} a ${R.entidad(d)}${d.semanas ? ` y registra ${d.semanas} semanas cotizadas` : ''}.`);
      h.push(`${R.capital(R.elDia(d.fechaSolicitud))} radicó ${R.opcionTexto(cd('tut_pension', 'tramite'), d.tramite)}${d.radicado ? ` (radicado o resolución No. ${d.radicado})` : ''}, con los documentos requeridos.`);
      if (meses !== null) h.push(`Han transcurrido ${meses} meses sin que la entidad haya ${d.tramite === 'nomina' ? 'incluido en nómina ni pagado la pensión' : 'resuelto de fondo la solicitud'}, superando el término legal de ${d.tramite === 'sobrevivientes' ? 'dos (2) meses (Ley 717 de 2001)' : d.tramite === 'nomina' ? 'seis (6) meses (Ley 700 de 2001)' : 'cuatro (4) meses (artículo 33 de la Ley 100 de 1993 y artículo 19 del Decreto 656 de 1994)'}.`);
      h.push(`Situación actual: ${R.oracion(d.situacion)}`);
      h.push(...R.hechosPrevio(d, 'la decisión sobre la pensión'));
      return h;
    },
    derechos: [
      { v: 'seguridad', inicial: true, t: 'Seguridad social', legal: 'derecho a la seguridad social (artículo 48 de la Constitución)' },
      { v: 'minimo', inicial: true, t: 'Mínimo vital', legal: 'derecho fundamental al mínimo vital y a la vida digna (artículos 1, 11 y 46 de la Constitución)' },
      { v: 'peticion', inicial: true, t: 'Derecho de petición', legal: 'derecho fundamental de petición (artículo 23 de la Constitución)' },
      { v: 'mayor', t: 'Protección del adulto mayor', legal: 'derechos de las personas adultas mayores (artículo 46 de la Constitución)' },
      { v: 'debido', t: 'Debido proceso', legal: 'derecho al debido proceso administrativo (artículo 29 de la Constitución)' }
    ],
    normas: ['cp86', 'cp48', 'cp46', 'cp23', 'l100_33', 'l717', 'l700_4', 'l1755_14', 't377', 'l1850'],
    procedencia: d => [
      'Subsidiariedad: la Corte Constitucional ha señalado (sentencias SU-975 de 2003, T-1013 de 2003, T-257 de 2005 y, para la pensión de sobrevivientes, SU-005 de 2018, entre otras) que la mora de la administradora en resolver la solicitud pensional vulnera directamente el derecho de petición y, cuando el solicitante es adulto mayor, inválido o carece de ingresos, también la seguridad social y el mínimo vital, sin que la jurisdicción ordinaria sea un medio eficaz dada la urgencia y la edad del afectado.',
      'Inmediatez: la omisión persiste y el daño se agrava con el paso del tiempo, dada la condición de la parte accionante.'
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja los derechos', legal: d => `TUTELAR los derechos fundamentales de petición, a la seguridad social y al mínimo vital de ${R.actor(d).nom}.` },
      { v: 'resolver', inicial: true, t: 'Que ordene resolver de fondo la solicitud en 48 horas (o en un plazo corto)', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes a la notificación del fallo, o en el plazo breve que el despacho señale, resuelva de fondo mediante acto administrativo motivado ${R.opcionTexto(cd('tut_pension', 'tramite'), d.tramite)} y lo notifique a la parte accionante.` },
      { v: 'nomina', inicial: d => d.tramite === 'nomina', t: 'Que ordene incluir en nómina y pagar el retroactivo', legal: d => `ORDENAR a ${R.entidad(d)} que incluya a la parte accionante en la nómina de pensionados del período inmediatamente siguiente y pague las mesadas causadas y no pagadas (retroactivo).` },
      { v: 'historia', inicial: d => d.tramite === 'historia', t: 'Que ordene corregir la historia laboral', legal: d => `ORDENAR a ${R.entidad(d)} corregir y actualizar la historia laboral incluyendo los períodos cotizados que no aparecen, y volver a estudiar la solicitud pensional con la historia corregida.` },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'solicitud', t: 'Copia de la solicitud de pensión radicada (con fecha)' }, { v: 'historia', t: 'Historia laboral' }, { v: 'resolucion', t: 'Resolución de reconocimiento (si existe)' }, { v: 'peticion', t: 'Derecho de petición previo y respuesta' }, { v: 'medicos', t: 'Historia clínica o dictamen de invalidez' }, { v: 'economia', t: 'Pruebas de la situación económica' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'Colpensiones es entidad nacional: la tutela se reparte a un juez del circuito. Los fondos privados (Porvenir, Protección, Colfondos, Skandia) van a juez municipal. La reforma pensional (Ley 2381 de 2024) no está en vigor: la Corte la suspendió y su aplicación quedó diferida, de modo que hoy rigen la Ley 100 de 1993 y los plazos citados en esta tutela.', siNoResponden: 'Incidente de desacato si no cumplen el fallo. Si niegan la pensión mediante resolución, tienes 10 días hábiles para recurso de reposición y apelación.' }
  },

  /* ---------------- TUTELA ESTABILIDAD LABORAL REFORZADA ---------------- */
  {
    id: 'tut_estabilidad', tipo: 'tutela', categoria: 'empleador', modulo: 'mujer',
    titulo: 'Tutela por despido en embarazo, enfermedad o discapacidad (estabilidad laboral reforzada)',
    resumen: 'Te despidieron o no renovaron el contrato estando embarazada, en licencia de maternidad, incapacitado, con una enfermedad grave o con discapacidad, sin permiso del Ministerio del Trabajo.',
    palabras: ['tutela', 'despido', 'embarazo', 'embarazada', 'lactancia', 'licencia de maternidad', 'enfermedad', 'incapacidad', 'discapacidad', 'reintegro', 'fuero', 'estabilidad laboral reforzada', 'no renovaron', 'contrato', 'prepensionado'],
    destinatario: { categoria: 'empleador', ejemploNombre: 'Ej.: Comercializadora Los Andes S.A.S.' },
    campos: [
      { id: 'situacionLaboral', tipo: 'select', etiqueta: '¿Cuál es tu situación?', requerido: true, opciones: [
        { v: 'embarazo', t: 'Estaba embarazada', legal: 'se encontraba en estado de embarazo (fuero de maternidad)' },
        { v: 'licencia', t: 'Estaba en licencia de maternidad', legal: 'se encontraba en licencia de maternidad (fuero de maternidad)' },
        { v: 'lactancia', t: 'Estaba en período de lactancia (hasta 6 meses después del parto)', legal: 'se encontraba en período de lactancia (fuero de maternidad)' },
        { v: 'enfermedad', t: 'Estaba incapacitado(a) o con una enfermedad que afecta mi trabajo', legal: 'se encontraba en una condición de salud que le impedía o dificultaba sustancialmente el desempeño de sus labores (estabilidad ocupacional reforzada)' },
        { v: 'discapacidad', t: 'Tengo una discapacidad o pérdida de capacidad laboral', legal: 'tiene una condición de discapacidad o pérdida de capacidad laboral calificada' },
        { v: 'prepension', t: 'Me faltan menos de 3 años para pensionarme', legal: 'se encuentra en condición de prepensionado, a menos de tres años de cumplir los requisitos de pensión' },
        { v: 'accidente', t: 'Sufrí un accidente de trabajo y me despidieron', legal: 'sufrió un accidente de trabajo o enfermedad laboral' }
      ], ancho: 'completa' },
      { id: 'vinculo', tipo: 'select', etiqueta: 'Tipo de contrato', opciones: [ { v: 'indefinido', t: 'A término indefinido', legal: 'contrato de trabajo a término indefinido' }, { v: 'fijo', t: 'A término fijo', legal: 'contrato de trabajo a término fijo' }, { v: 'obra', t: 'Por obra o labor', legal: 'contrato por obra o labor' }, { v: 'prestacion', t: 'Prestación de servicios', legal: 'contrato de prestación de servicios' }, { v: 'verbal', t: 'Verbal / sin contrato', legal: 'contrato de trabajo verbal' } ], valorInicial: 'indefinido', ancho: 'media' },
      { id: 'cargo', tipo: 'texto', etiqueta: 'Cargo', ancho: 'media' },
      { id: 'salario', tipo: 'texto', etiqueta: 'Salario', ancho: 'media' },
      { id: 'fechaInicio', tipo: 'fecha', etiqueta: 'Fecha de ingreso', ancho: 'media' },
      { id: 'fechaDespido', tipo: 'fecha', etiqueta: 'Fecha del despido o terminación', requerido: true, ancho: 'media' },
      { id: 'sabia', tipo: 'radio', etiqueta: '¿El empleador conocía tu situación (embarazo, enfermedad) antes del despido?', opciones: [ { v: 'si', t: 'Sí, lo sabía (le avisé, tenía incapacidades, era evidente)' }, { v: 'no', t: 'No estoy seguro(a)' } ], requerido: true },
      { id: 'permiso', tipo: 'radio', etiqueta: '¿El empleador pidió permiso al Ministerio del Trabajo (inspector) para despedirte?', opciones: [ { v: 'no', t: 'No' }, { v: 'si', t: 'Sí' }, { v: 'nose', t: 'No lo sé' } ], requerido: true },
      { id: 'motivo', tipo: 'texto', etiqueta: '¿Qué razón te dieron para el despido?', ejemplo: 'Ej.: "Terminación del contrato por vencimiento del plazo" / ninguna', ancho: 'completa' },
      { id: 'afectacion', tipo: 'textarea', etiqueta: '¿Cómo te afecta el despido? (salud, ingresos, seguridad social, tratamiento)', requerido: true, filas: 3 },
      C.relato({ requerido: false, etiqueta: '¿Algo más que el juez deba saber? (opcional)' })
    ],
    asunto: d => 'Acción de tutela – Estabilidad laboral reforzada – Reintegro',
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} se vinculó a ${R.entidad(d)}${d.fechaInicio ? ` el ${R.fechaLarga(d.fechaInicio)}` : ''} mediante ${R.opcionTexto(cd('tut_estabilidad', 'vinculo'), d.vinculo)}${d.cargo ? `, en el cargo de ${d.cargo}` : ''}${d.salario ? `, con un salario de ${R.moneda(d.salario) || d.salario}` : ''}.`);
      h.push(`Al momento de la terminación del vínculo, ${a.nom} ${R.opcionTexto(cd('tut_estabilidad', 'situacionLaboral'), d.situacionLaboral)}.`);
      h.push(`${R.capital(R.elDia(d.fechaDespido))}, ${R.entidad(d)} dio por terminado el vínculo${d.motivo ? `, aduciendo: "${d.motivo}"` : ', sin expresar motivo'}${d.permiso === 'no' ? ', sin solicitar la autorización previa del Ministerio del Trabajo que exige la ley' : ''}.`);
      if (d.sabia === 'si') h.push('El empleador conocía plenamente la situación de la parte accionante antes de la terminación.');
      h.push(`La terminación del vínculo afecta gravemente a la parte accionante: ${R.oracion(d.afectacion)}`);
      return h;
    },
    derechos: [
      { v: 'estabilidad', inicial: true, t: 'Estabilidad laboral reforzada', legal: 'derecho a la estabilidad laboral reforzada (artículos 13, 25, 43, 47 y 53 de la Constitución)' },
      { v: 'minimo', inicial: true, t: 'Mínimo vital', legal: 'derecho fundamental al mínimo vital (artículos 1 y 53 de la Constitución)' },
      { v: 'salud', inicial: true, t: 'Salud y seguridad social', legal: 'derechos a la salud y a la seguridad social (artículos 48 y 49 de la Constitución)' },
      { v: 'igualdad', t: 'Igualdad y no discriminación', legal: 'derecho a la igualdad y a no ser discriminado (artículo 13 de la Constitución)' },
      { v: 'ninos', t: 'Derechos del que está por nacer o del recién nacido', legal: 'derechos del niño que está por nacer o recién nacido (artículos 43 y 44 de la Constitución)' }
    ],
    normas: ['cp86', 'cp13', 'cp25', 'cp43', 'cp53', 'cst_239', 'l361_26', 'su070', 'su049', 'd2591_42'],
    fundamentos: d => d.situacionLaboral === 'prepension' ? ['La Corte Constitucional ha reconocido la estabilidad laboral reforzada de los prepensionados (sentencias SU-003 de 2018 y T-357 de 2016): quienes se encuentran a tres (3) años o menos de cumplir los requisitos de edad y semanas para pensionarse y necesitan seguir cotizando no pueden ser desvinculados sin que se garantice su acceso a la pensión, so pena de vulnerar su mínimo vital y su seguridad social.'] : [],
    procedencia: d => [
      'Subsidiariedad: aunque existe la acción ordinaria laboral, la Corte Constitucional ha establecido (SU-070 de 2013, SU-049 de 2017 y SU-075 de 2018) que la tutela procede para proteger la estabilidad laboral reforzada cuando el accionante es sujeto de especial protección (mujer embarazada, persona con afectación de salud o discapacidad) y el despido afecta su mínimo vital, su salud o la continuidad de su tratamiento, pues el proceso ordinario no es eficaz frente a esa urgencia; conforme a la SU-075 de 2018, cuando el empleador conocía el estado de embarazo o existe duda razonable al respecto, opera plenamente el fuero de maternidad.',
      `Inmediatez: la terminación ocurrió ${R.elDia(d.fechaDespido)}, y sus efectos sobre la salud y la subsistencia de la parte accionante son actuales.`
    ],
    peticiones: [
      { v: 'tutelar', inicial: true, fijo: true, t: 'Que el juez proteja los derechos', legal: d => `TUTELAR los derechos fundamentales a la estabilidad laboral reforzada, al mínimo vital, a la salud, a la seguridad social y a la igualdad de ${R.actor(d).nom}.` },
      { v: 'ineficacia', inicial: true, t: 'Que declare que el despido no tiene efectos', legal: d => `DECLARAR la ineficacia de la terminación del vínculo efectuada por ${R.entidad(d)} ${R.elDia(d.fechaDespido)}, por haberse producido sin la autorización del Ministerio del Trabajo.` },
      { v: 'reintegro', inicial: true, t: 'Que ordene reintegrarme a un cargo igual o mejor', legal: d => `ORDENAR a ${R.entidad(d)} que, dentro de las cuarenta y ocho (48) horas siguientes a la notificación del fallo, reintegre a la parte accionante al cargo que desempeñaba o a uno de igual o superior categoría, compatible con su estado de salud, sin solución de continuidad.` },
      { v: 'salarios', inicial: true, t: 'Que ordene pagar los salarios y la seguridad social dejados de pagar', legal: d => `ORDENAR a ${R.entidad(d)} pagar los salarios, prestaciones y aportes a seguridad social causados desde la fecha del despido hasta el reintegro efectivo.` },
      { v: 'indemnizacion', t: 'Que ordene la indemnización de ley (60 días embarazo / 180 días discapacidad)', legal: d => `ORDENAR a ${R.entidad(d)} pagar la indemnización prevista en ${['embarazo', 'licencia', 'lactancia'].includes(d.situacionLaboral) ? 'el artículo 239 del Código Sustantivo del Trabajo (sesenta días de salario)' : 'el artículo 26 de la Ley 361 de 1997 (ciento ochenta días de salario)'}.` },
      { v: 'desacato', inicial: true, t: 'Que advierta sobre el desacato', legal: d => `ADVERTIR a ${R.entidad(d)} que el incumplimiento del fallo dará lugar al incidente de desacato del artículo 52 del Decreto 2591 de 1991.` }
    ],
    medida: d => `Solicito como MEDIDA PROVISIONAL (artículo 7 del Decreto 2591 de 1991) que se ordene a ${R.entidad(d)} mantener la afiliación a salud de la parte accionante y pagar los aportes correspondientes mientras se decide la tutela, pues la espera del fallo puede causar un daño irreversible: ${R.oracion(d.medidaTexto || d.afectacion)}`,
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'contrato', t: 'Contrato de trabajo y carta de despido o terminación' }, { v: 'medicos', t: 'Prueba del embarazo, incapacidades, historia clínica o certificado de discapacidad' }, { v: 'aviso', t: 'Prueba de que el empleador conocía la situación (correos, chats, incapacidades radicadas)' }, { v: 'pagos', t: 'Desprendibles de nómina' }, { v: 'afiliacion', t: 'Certificado de afiliación a EPS y estado actual' } ],
    guia: { plazo: { dias: 10, tipo: 'calendario' }, nota: 'Presenta la tutela lo antes posible después del despido (idealmente antes de 6 meses). Si el juez concede el reintegro como medida transitoria, deberás iniciar la demanda laboral ordinaria en 4 meses.', siNoResponden: 'Incidente de desacato si no reintegran. En paralelo, queja ante el Ministerio del Trabajo.' }
  }
  );
})();
