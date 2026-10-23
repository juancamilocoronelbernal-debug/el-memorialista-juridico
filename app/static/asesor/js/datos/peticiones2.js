/* ============================================================
   peticiones2.js — Casos de DERECHO DE PETICIÓN (parte 2):
   incapacidades, pensiones, empleador, servicios públicos,
   bancos, colegios, información pública y copias.
   ============================================================ */
window.AJ = window.AJ || {};
AJ.casos = AJ.casos || [];

(function () {
  const R = AJ.red;
  const C = AJ.campos;
  const cd = (c, f) => AJ.camposDe(c, f);

  AJ.casos.push(
  /* ---------------- SALUD / TRABAJO: INCAPACIDADES ---------------- */
  {
    id: 'pet_incapacidades', tipo: 'peticion', categoria: 'eps',
    titulo: 'Petición por incapacidades médicas no pagadas (EPS, ARL, fondo de pensiones o empleador)',
    resumen: 'Exigir el pago de incapacidades atrasadas, su transcripción, o el concepto de rehabilitación. El subsidio reemplaza tu salario: su no pago afecta el mínimo vital.',
    palabras: ['incapacidad', 'incapacidades', 'pago', 'EPS', 'ARL', 'fondo de pensiones', 'empleador', 'enfermedad', 'accidente de trabajo', 'rehabilitación', '180 días', 'salario'],
    destinatario: { categoria: 'eps', ejemploNombre: 'Ej.: EPS Sura / ARL Positiva / Porvenir / Empresa XYZ S.A.S.', cargo: 'Área de prestaciones económicas / Representante legal' },
    campos: [
      { id: 'quien', tipo: 'select', etiqueta: '¿Quién te debe las incapacidades?', requerido: true, opciones: [
        { v: 'eps', t: 'La EPS (enfermedad general, días 3 a 180)', legal: 'la EPS, por tratarse de incapacidades de origen común entre los días 3 y 180' },
        { v: 'arl', t: 'La ARL (accidente o enfermedad laboral)', legal: 'la ARL, por tratarse de incapacidades de origen laboral' },
        { v: 'afp', t: 'El fondo de pensiones (después del día 180)', legal: 'la administradora de fondos de pensiones, por tratarse de incapacidades posteriores al día 180' },
        { v: 'empleador', t: 'Mi empleador (no me ha pagado lo que ya le reconocieron o los 2 primeros días)', legal: 'el empleador, que debe pagar al trabajador el valor de las incapacidades' }
      ] },
      { id: 'periodos', tipo: 'textarea', etiqueta: 'Incapacidades pendientes (fechas y días de cada una)', ejemplo: 'Ej.:\nDel 1 al 30 de junio de 2026 (30 días)\nDel 1 al 15 de julio de 2026 (15 días)', requerido: true, filas: 3 },
      { id: 'diagnostico', tipo: 'texto', etiqueta: 'Diagnóstico (si lo sabes)', ancho: 'media' },
      { id: 'diasAcumulados', tipo: 'texto', etiqueta: 'Días de incapacidad acumulados en total (aproximado)', ejemplo: 'Ej.: 210', ancho: 'media' },
      { id: 'salario', tipo: 'texto', etiqueta: 'Tu salario o ingreso base de cotización', ejemplo: 'Ej.: 1.750.000', ancho: 'media' },
      { id: 'situacion', tipo: 'textarea', etiqueta: '¿Cómo te afecta no recibir ese dinero?', ejemplo: 'Ej.: Es mi único ingreso; tengo dos hijos y debo el arriendo de dos meses.', filas: 2, requerido: true },
      ...C.previo({ etiqueta: '¿Ya habías reclamado el pago?' }),
      C.relato({ requerido: false, etiqueta: '¿Algo más que debamos contar? (opcional)' })
    ],
    asunto: d => 'Derecho de petición – Pago de incapacidades médicas adeudadas',
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} se encuentra afiliad${a.o} al Sistema de Seguridad Social Integral${d.salario ? `, con un ingreso base de cotización de ${R.moneda(d.salario) || d.salario}` : ''}, y ha sido incapacitad${a.o} por su médico tratante${d.diagnostico ? ` con diagnóstico de ${d.diagnostico}` : ''}${d.diasAcumulados ? `, acumulando aproximadamente ${d.diasAcumulados} días de incapacidad` : ''}.`);
      h.push(`Las siguientes incapacidades no han sido pagadas: ${R.relatoAHechos(d.periodos).join(' ')}`);
      h.push(`El pago corresponde a ${R.opcionTexto(cd('pet_incapacidades', 'quien'), d.quien)}.`);
      if (d.situacion) h.push(`El subsidio por incapacidad es el único sustituto del salario durante la enfermedad. Su no pago afecta el mínimo vital: ${R.oracion(d.situacion)}`);
      h.push(...R.hechosPrevio(d, 'el pago de las incapacidades'));
      return h;
    },
    normas: d => ['cp48', 'cp53', 'l100_206', d.quien === 'arl' ? 'l1562' : null, 'cp23', 'l1755_33', 'l1755_14', 'su995'].filter(Boolean),
    fundamentos: d => d.quien === 'afp' ? ['Conforme al artículo 142 del Decreto Ley 019 de 2012, condicionado por la Sentencia C-270 de 2023, cuando la incapacidad supera los 180 días la EPS debe emitir el concepto de rehabilitación antes del día 120 y remitirlo a la administradora de pensiones antes del día 150; la administradora de pensiones debe pagar el subsidio desde el día 181 hasta el 540 tanto si el concepto es favorable como si es desfavorable (en este último caso iniciando de inmediato la calificación de pérdida de capacidad laboral). Si la EPS no emitió ni remitió el concepto oportunamente, ella misma debe asumir el pago desde el día 181.'] : [],
    peticiones: [
      { v: 'pagar', inicial: true, t: 'Que paguen todas las incapacidades pendientes en un plazo corto', legal: 'Reconocer y pagar la totalidad de las incapacidades relacionadas en los hechos, con los intereses moratorios a que haya lugar, dentro de un término que no supere los diez (10) días hábiles, dada la afectación del mínimo vital.' },
      { v: 'liquidacion', inicial: true, t: 'Que me entreguen la liquidación detallada de cada incapacidad', legal: 'Entregar la liquidación detallada de cada incapacidad (días, ingreso base, porcentaje aplicado y valor), indicando las ya pagadas y las pendientes.' },
      { v: 'transcribir', t: 'Que transcriban las incapacidades que faltan', legal: 'Transcribir o validar en el sistema las incapacidades expedidas por médicos externos o pendientes de registro.' },
      { v: 'concepto', t: 'Que emitan y me entreguen el concepto de rehabilitación', legal: 'Emitir el concepto de rehabilitación previsto en el artículo 142 del Decreto Ley 019 de 2012, remitirlo a la administradora de pensiones y entregarme copia.' },
      { v: 'calificacion', t: 'Que inicien la calificación de pérdida de capacidad laboral', legal: 'Iniciar el trámite de calificación de la pérdida de capacidad laboral y de su origen, e informarme la fecha de la valoración.' },
      { v: 'motivos', t: 'Si no pagan, que me expliquen por escrito la razón', legal: 'En caso de negativa, exponer por escrito las razones y normas que la sustentan e indicar la entidad que, a su juicio, debe asumir el pago, remitiéndole la solicitud.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'incapacidades', t: 'Copia de los certificados de incapacidad' }, { v: 'historia', t: 'Historia clínica o epicrisis' }, { v: 'pagos', t: 'Soportes de pagos recibidos o desprendibles de nómina' }, { v: 'contrato', t: 'Contrato de trabajo o certificación laboral' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, siNoResponden: 'Sin pago ni respuesta en 15 días hábiles, presenta la "Tutela por incapacidades no pagadas" de esta plataforma (procede por afectación del mínimo vital).' }
  },

  /* ---------------- PENSIONES ---------------- */
  {
    id: 'pet_pension', tipo: 'peticion', categoria: 'nacional',
    titulo: 'Petición a Colpensiones o al fondo de pensiones (pensión, historia laboral, estado del trámite)',
    resumen: 'Exigir respuesta sobre una solicitud de pensión, corregir la historia laboral, pedir certificados de semanas, indemnización sustitutiva o inclusión en nómina.',
    palabras: ['pensión', 'Colpensiones', 'Porvenir', 'Protección', 'Colfondos', 'historia laboral', 'semanas', 'vejez', 'invalidez', 'sobrevivientes', 'sustitución', 'nómina', 'indemnización sustitutiva', 'devolución de saldos', 'adulto mayor'],
    destinatario: { categoria: 'nacional', nombre: 'Colpensiones (Administradora Colombiana de Pensiones)', cargo: 'Gerencia Nacional de Reconocimiento / Oficina de atención al ciudadano', ejemploCargo: 'Ej.: Gerencia de reconocimiento de prestaciones' },
    campos: [
      { id: 'tramite', tipo: 'select', etiqueta: '¿Qué necesitas?', requerido: true, opciones: [
        { v: 'vejez', t: 'Que resuelvan mi solicitud de pensión de vejez', legal: 'la solicitud de reconocimiento de la pensión de vejez' },
        { v: 'invalidez', t: 'Que resuelvan mi solicitud de pensión de invalidez', legal: 'la solicitud de reconocimiento de la pensión de invalidez' },
        { v: 'sobrevivientes', t: 'Que resuelvan la pensión de sobrevivientes o sustitución (falleció mi familiar)', legal: 'la solicitud de pensión de sobrevivientes o sustitución pensional' },
        { v: 'historia', t: 'Que corrijan mi historia laboral (semanas que faltan)', legal: 'la corrección de la historia laboral' },
        { v: 'certificado', t: 'Un certificado de semanas cotizadas o de afiliación', legal: 'la expedición del certificado de semanas cotizadas' },
        { v: 'nomina', t: 'Que me incluyan en nómina y paguen el retroactivo (ya me reconocieron la pensión)', legal: 'la inclusión en nómina y el pago del retroactivo de la pensión ya reconocida' },
        { v: 'indemnizacion', t: 'Indemnización sustitutiva o devolución de saldos', legal: 'el reconocimiento de la indemnización sustitutiva o la devolución de saldos' },
        { v: 'traslado', t: 'Información sobre traslado de régimen o doble asesoría', legal: 'la información sobre el traslado de régimen y la doble asesoría' }
      ] },
      { id: 'fechaSolicitud', tipo: 'fecha', etiqueta: 'Fecha en que radicaste la solicitud de pensión (si aplica)', ancho: 'media' },
      { id: 'radicado', tipo: 'texto', etiqueta: 'Número de radicado o de la resolución', ancho: 'media' },
      { id: 'edad', tipo: 'texto', etiqueta: 'Tu edad', ejemplo: 'Ej.: 63', ancho: 'media' },
      { id: 'semanas', tipo: 'texto', etiqueta: 'Semanas cotizadas (según tu historia laboral)', ejemplo: 'Ej.: 1.350', ancho: 'media' },
      { id: 'detalleHistoria', tipo: 'textarea', etiqueta: 'Si faltan semanas: ¿qué empleadores y períodos no aparecen?', ejemplo: 'Ej.: Trabajé en Textiles del Norte S.A. de enero de 1998 a diciembre de 2003 y no aparecen esas semanas.', filas: 3, mostrarSi: { campo: 'tramite', valor: 'historia' } },
      { id: 'situacion', tipo: 'textarea', etiqueta: '¿Cómo te afecta la demora?', ejemplo: 'Ej.: No tengo otro ingreso; dependo de mis hijos y tengo hipertensión.', filas: 2, requerido: true },
      C.relato({ requerido: false, etiqueta: '¿Algo más que debamos contar? (opcional)' })
    ],
    asunto: d => `Derecho de petición – ${R.capital(R.opcionTexto(cd('pet_pension', 'tramite'), d.tramite))}${d.radicado ? ` (radicado ${d.radicado})` : ''}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} está afiliad${a.o} al Sistema General de Pensiones a través de ${R.entidad(d)}${d.edad ? `, tiene ${d.edad} años de edad` : ''}${d.semanas ? ` y registra aproximadamente ${d.semanas} semanas cotizadas` : ''}.`);
      if (d.fechaSolicitud) h.push(`${R.capital(R.elDia(d.fechaSolicitud))} radicó ante la entidad ${R.opcionTexto(cd('pet_pension', 'tramite'), d.tramite)}${d.radicado ? `, bajo el radicado No. ${d.radicado}` : ''}, con la documentación requerida.`);
      if (d.fechaSolicitud) {
        const meses = Math.floor((R.hoy() - AJ.festivos.parseISO(d.fechaSolicitud)) / (30.44 * 24 * 3600 * 1000));
        if (meses >= 1) h.push(`Han transcurrido ${meses} meses desde la radicación sin que la entidad haya resuelto de fondo la solicitud, superando los términos legales.`);
      }
      if (d.tramite === 'historia' && d.detalleHistoria) h.push(`La historia laboral presenta inconsistencias: ${R.oracion(d.detalleHistoria)}`);
      if (d.situacion) h.push(`La demora afecta gravemente el mínimo vital y la seguridad social: ${R.oracion(d.situacion)}`);
      return h;
    },
    normas: d => ['cp48', 'cp46', 'cp23', 'l1755_14', 'l1755_20', 'l100_33', d.tramite === 'sobrevivientes' ? 'l717' : null, ['nomina', 'vejez', 'invalidez'].includes(d.tramite) ? 'l700_4' : null, 't377'].filter(Boolean),
    fundamentos: d => d.tramite === 'historia' ? ['La historia laboral es el soporte del derecho pensional. Conforme a la jurisprudencia constitucional (sentencias T-855 de 2011 y SU-226 de 2019), la administradora debe mantenerla completa y actualizada, adelantar las acciones de cobro de los aportes en mora y, cuando el empleador omitió la afiliación, exigirle el cálculo actuarial, sin trasladar al afiliado las consecuencias de la mora o de la omisión patronal.'] : [],
    peticiones: [
      { v: 'resolver', inicial: true, t: 'Que resuelvan de fondo mi solicitud mediante resolución', legal: d => `Resolver de fondo, mediante acto administrativo motivado, ${R.opcionTexto(cd('pet_pension', 'tramite'), d.tramite)}, dentro de los términos legales, y notificármelo en la dirección y correo indicados.` },
      { v: 'estado', inicial: true, t: 'Que me informen el estado del trámite y qué documentos faltan', legal: 'Informar el estado actual del trámite, los documentos que eventualmente falten y la fecha en que se expedirá la decisión.' },
      { v: 'historia', inicial: d => d.tramite === 'historia', t: 'Que corrijan mi historia laboral e incluyan las semanas que faltan', legal: 'Corregir la historia laboral incluyendo los períodos cotizados que no aparecen, adelantar las acciones de cobro contra los empleadores en mora y expedir la historia laboral actualizada.' },
      { v: 'nomina', inicial: d => d.tramite === 'nomina', t: 'Que me incluyan en nómina y paguen el retroactivo', legal: 'Incluir al pensionado en la nómina de la entidad y pagar las mesadas causadas desde la fecha de reconocimiento (retroactivo), con los intereses moratorios del artículo 141 de la Ley 100 de 1993.' },
      { v: 'certificado', inicial: d => d.tramite === 'certificado', t: 'Que expidan el certificado o la historia laboral', legal: 'Expedir el certificado de semanas cotizadas y la historia laboral detallada, dentro de los diez (10) días hábiles siguientes.' },
      { v: 'copias', t: 'Que me entreguen copia del expediente', legal: 'Expedir copia íntegra del expediente administrativo de la solicitud pensional.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'historia', t: 'Historia laboral descargada' }, { v: 'radicado', t: 'Copia de la solicitud radicada y la resolución (si existe)' }, { v: 'certificados', t: 'Certificaciones laborales de los períodos faltantes' }, { v: 'defuncion', t: 'Registro civil de defunción y de matrimonio o prueba de convivencia (sobrevivientes)' }, { v: 'calificacion', t: 'Dictamen de pérdida de capacidad laboral (invalidez)' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Para resolver la pensión de vejez e invalidez la ley da 4 meses; para la de sobrevivientes, 2 meses; para pagar las mesadas, máximo 6 meses desde la solicitud.', siNoResponden: 'Sin respuesta a esta petición en 15 días hábiles, o si vencieron los 4 meses (2 para sobrevivientes) sin resolución, presenta la "Tutela porque no resuelven mi pensión".' }
  },

  /* ---------------- EMPLEADOR ---------------- */
  {
    id: 'pet_empleador', tipo: 'peticion', categoria: 'empleador',
    titulo: 'Petición al empleador: salarios, liquidación, certificado laboral, seguridad social',
    resumen: 'Reclamar por escrito salarios o prestaciones no pagadas, la liquidación, el certificado laboral, las planillas de seguridad social o la afiliación que no hicieron.',
    palabras: ['empleador', 'empresa', 'salario', 'sueldo', 'liquidación', 'prestaciones', 'prima', 'cesantías', 'vacaciones', 'certificado laboral', 'carta laboral', 'seguridad social', 'planilla', 'PILA', 'despido', 'honorarios', 'contrato'],
    destinatario: { categoria: 'empleador', ejemploNombre: 'Ej.: Distribuidora El Sol S.A.S.', cargo: 'Representante legal / Gerencia de talento humano' },
    campos: [
      { id: 'vinculo', tipo: 'select', etiqueta: '¿Qué tipo de vínculo tienes o tenías?', requerido: true, opciones: [
        { v: 'laboral', t: 'Contrato de trabajo (fijo, indefinido, por obra, verbal)', legal: 'un contrato de trabajo' }, { v: 'domestico', t: 'Trabajo doméstico o de cuidado', legal: 'un contrato de trabajo como empleado(a) del servicio doméstico' },
        { v: 'prestacion', t: 'Contrato de prestación de servicios (honorarios)', legal: 'un contrato de prestación de servicios' }, { v: 'verbal', t: 'Sin contrato escrito (de palabra)', legal: 'un contrato de trabajo verbal' }
      ], ancho: 'media' },
      { id: 'estado', tipo: 'select', etiqueta: '¿Sigues trabajando allí?', opciones: [ { v: 'activo', t: 'Sí, sigo trabajando', legal: 'la relación laboral se encuentra vigente' }, { v: 'terminado', t: 'No, ya terminó', legal: 'la relación laboral terminó' } ], valorInicial: 'activo', ancho: 'media' },
      { id: 'cargo', tipo: 'texto', etiqueta: 'Cargo u oficio', ejemplo: 'Ej.: Auxiliar de bodega', ancho: 'media' },
      { id: 'salario', tipo: 'texto', etiqueta: 'Salario u honorarios mensuales', ejemplo: 'Ej.: 1.423.500', ancho: 'media' },
      { id: 'fechaInicio', tipo: 'fecha', etiqueta: 'Fecha de inicio', ancho: 'media' },
      { id: 'fechaFin', tipo: 'fecha', etiqueta: 'Fecha de terminación (si terminó)', mostrarSi: { campo: 'estado', valor: 'terminado' }, ancho: 'media' },
      { id: 'reclamo', tipo: 'checks', etiqueta: '¿Qué te deben o qué necesitas?', requerido: true, opciones: [
        { v: 'salarios', t: 'Salarios u honorarios atrasados', legal: 'los salarios u honorarios adeudados' }, { v: 'liquidacion', t: 'La liquidación final (cesantías, prima, vacaciones, intereses)', legal: 'la liquidación definitiva de prestaciones sociales' },
        { v: 'prima', t: 'Prima de servicios', legal: 'la prima de servicios' }, { v: 'cesantias', t: 'Cesantías e intereses (o consignación al fondo)', legal: 'las cesantías y sus intereses' },
        { v: 'vacaciones', t: 'Vacaciones', legal: 'las vacaciones' }, { v: 'horas', t: 'Horas extras, recargos o dominicales', legal: 'las horas extras, recargos nocturnos, dominicales y festivos' },
        { v: 'seguridad', t: 'Afiliación o pagos de salud, pensión y ARL', legal: 'la afiliación y el pago de los aportes a salud, pensión y riesgos laborales' }, { v: 'certificado', t: 'Certificado o carta laboral', legal: 'la certificación laboral' },
        { v: 'planillas', t: 'Copia de las planillas de seguridad social y desprendibles', legal: 'copia de las planillas de pago de aportes y de los desprendibles de nómina' }, { v: 'contrato', t: 'Copia de mi contrato', legal: 'copia del contrato' },
        { v: 'dotacion', t: 'Dotación (uniforme y calzado)', legal: 'la dotación de calzado y vestido de labor' }, { v: 'indemnizacion', t: 'Indemnización por despido sin justa causa', legal: 'la indemnización por terminación del contrato sin justa causa' }
      ] },
      { id: 'valorDeuda', tipo: 'texto', etiqueta: 'Valor aproximado que te deben', ejemplo: 'Ej.: 3.200.000', ancho: 'media' },
      { id: 'periodoDeuda', tipo: 'texto', etiqueta: 'Períodos que te deben', ejemplo: 'Ej.: Salarios de julio y agosto de 2026', ancho: 'media' },
      ...C.previo({ etiqueta: '¿Ya habías reclamado al empleador?' }),
      C.relato({ ejemplo: 'Ej.:\nTrabajé como auxiliar desde el 3 de febrero de 2025.\nEl 30 de agosto de 2026 me dijeron que no volviera, sin carta ni explicación.\nNo me han pagado agosto ni la liquidación.' })
    ],
    asunto: d => `Derecho de petición – Reclamación de ${R.lista((d.reclamo || []).map(v => R.opcionTexto(cd('pet_empleador', 'reclamo'), v))) || 'acreencias laborales'}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} ${d.estado === 'terminado' ? 'estuvo vinculad' + a.o : 'se encuentra vinculad' + a.o} a ${R.entidad(d)} mediante ${R.generizar(R.opcionTexto(cd('pet_empleador', 'vinculo'), d.vinculo), a.g)}${d.cargo ? `, desempeñando el cargo de ${d.cargo}` : ''}${d.fechaInicio ? `, desde el ${R.fechaLarga(d.fechaInicio)}` : ''}${d.estado === 'terminado' && d.fechaFin ? ` hasta el ${R.fechaLarga(d.fechaFin)}` : ''}${d.salario ? `, con una remuneración mensual de ${R.moneda(d.salario) || d.salario}` : ''}.`);
      h.push(`A la fecha, el empleador adeuda o no ha entregado ${R.lista((d.reclamo || []).map(v => R.opcionTexto(cd('pet_empleador', 'reclamo'), v)))}${d.periodoDeuda ? ` (${d.periodoDeuda})` : ''}${d.valorDeuda ? `, por un valor aproximado de ${R.moneda(d.valorDeuda) || d.valorDeuda}` : ''}.`);
      if (d.vinculo === 'prestacion' || d.vinculo === 'verbal') h.push('Con independencia del nombre que se haya dado al contrato, en la práctica se cumplió horario, se recibieron órdenes y se prestó el servicio de manera personal, de modo que opera el principio de primacía de la realidad sobre las formas (artículo 53 de la Constitución y artículo 24 del Código Sustantivo del Trabajo).');
      h.push(...R.hechosPrevio(d, 'el pago y la entrega de lo aquí reclamado'));
      return h;
    },
    normas: ['cp25', 'cp53', 'cst_57', 'cst_134', 'cst_65', 'l50_99', 'pila', 'cp23', 'l1755_32', 'su995'],
    fundamentos: d => {
      const f = [];
      if ((d.reclamo || []).includes('horas')) f.push('Conforme a la Ley 2466 de 2025 (reforma laboral), el trabajo nocturno se remunera con recargo del treinta y cinco por ciento (35 %) desde las 7:00 p. m. (artículo 160 del Código Sustantivo del Trabajo, vigente desde el 25 de diciembre de 2025), y el trabajo en dominicales y festivos con recargo del ochenta por ciento (80 %) desde julio de 2025, del noventa por ciento (90 %) desde julio de 2026 y del cien por ciento (100 %) desde julio de 2027 (artículo 179 del mismo código).');
      if (d.vinculo === 'domestico') f.push('Las trabajadoras y trabajadores del servicio doméstico tienen derecho a prima de servicios (Ley 1788 de 2016), a la afiliación a caja de compensación (Decreto 721 de 2013) y a todas las prestaciones del Código Sustantivo del Trabajo (Convenio 189 de la OIT, Ley 1595 de 2012). Cuando el empleador omitió la afiliación a pensiones, debe pagar el cálculo actuarial por el tiempo no cotizado (literal d del parágrafo 1 del artículo 33 de la Ley 100 de 1993; Sentencia SU-226 de 2019).');
      return f;
    },
    peticiones: [
      { v: 'pagar', inicial: true, t: 'Que me paguen todo lo que me deben en un plazo corto', legal: d => `Pagar dentro de los cinco (5) días hábiles siguientes ${R.lista((d.reclamo || []).filter(v => !['certificado', 'planillas', 'contrato'].includes(v)).map(v => R.opcionTexto(cd('pet_empleador', 'reclamo'), v))) || 'las sumas adeudadas'}, debidamente liquidadas, junto con la indemnización moratoria que corresponda.` },
      { v: 'liquidacion', inicial: true, t: 'Que me entreguen la liquidación detallada por escrito', legal: 'Entregar por escrito la liquidación detallada de cada concepto (salarios, prestaciones, vacaciones, indemnizaciones), con los períodos, bases y valores aplicados.' },
      { v: 'documentos', t: 'Que me entreguen certificado laboral, planillas y copia del contrato', legal: 'Expedir el certificado laboral (tiempo de servicio, cargo y salario), entregar copia del contrato y de las planillas de pago de aportes a seguridad social y los desprendibles de nómina.' },
      { v: 'afiliar', t: 'Que me afilien y paguen la seguridad social atrasada', legal: 'Afiliar al trabajador al sistema de seguridad social integral y pagar los aportes a salud, pensión y riesgos laborales dejados de cancelar, con los intereses de mora, acreditando el pago.' },
      { v: 'motivos', t: 'Si no van a pagar, que me expliquen por escrito por qué', legal: 'En caso de considerar que no se adeuda alguna suma, explicar por escrito las razones y aportar los soportes de los pagos efectuados.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'contrato', t: 'Copia del contrato (si lo tengo)' }, { v: 'pagos', t: 'Desprendibles, consignaciones o pantallazos de pagos recibidos' }, { v: 'chats', t: 'Mensajes o correos con el empleador' }, { v: 'carta', t: 'Carta de despido o renuncia' }, { v: 'testigos', t: 'Nombres de compañeros que pueden declarar' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'Esta reclamación escrita interrumpe la prescripción de los derechos laborales por una sola vez (artículo 489 del CST) y sirve de prueba. Guarda copia firmada o el correo enviado.', siNoResponden: 'Si no pagan: (1) queja ante el Ministerio del Trabajo; (2) si el no pago afecta tu sustento, "Tutela por salarios no pagados (mínimo vital)"; (3) demanda laboral, con ayuda de un consultorio jurídico universitario (gratis).' }
  },

  /* ---------------- SERVICIOS PÚBLICOS ---------------- */
  {
    id: 'pet_spd', tipo: 'peticion', categoria: 'spd',
    tituloDoc: d => d.servicio === 'internet' ? 'RECLAMACIÓN (PQR) – SERVICIOS DE COMUNICACIONES' : 'RECLAMACIÓN (artículos 152 y 154 de la Ley 142 de 1994)',
    titulo: 'Reclamo a la empresa de servicios públicos (factura alta, cobro indebido, corte, reconexión)',
    resumen: 'Reclamación formal por facturas excesivas, cobros de servicios no prestados, suspensión indebida, medidor dañado o no reconexión. La empresa debe responder en el término aplicable. En algunos casos puede operar el silencio administrativo positivo, con condiciones y excepciones.',
    palabras: ['factura', 'recibo', 'luz', 'energía', 'agua', 'acueducto', 'gas', 'aseo', 'internet', 'telefonía', 'corte', 'suspensión', 'reconexión', 'medidor', 'cobro', 'EPM', 'Enel', 'Air-e', 'Afinia', 'Claro', 'Movistar', 'Tigo'],
    destinatario: { categoria: 'spd', ejemploNombre: 'Ej.: Empresas Públicas de Medellín (EPM)', cargo: 'Oficina de Peticiones, Quejas y Recursos' },
    campos: [
      { id: 'servicio', tipo: 'select', etiqueta: '¿De qué servicio se trata?', requerido: true, opciones: [
        { v: 'energia', t: 'Energía eléctrica' }, { v: 'acueducto', t: 'Acueducto y alcantarillado' }, { v: 'gas', t: 'Gas natural' }, { v: 'aseo', t: 'Aseo' }, { v: 'internet', t: 'Internet, telefonía o televisión' }
      ], ancho: 'media' },
      { id: 'cuenta', tipo: 'texto', etiqueta: 'Número de cuenta, contrato o NIC', ejemplo: 'Ej.: 1234567', ancho: 'media' },
      { id: 'direccionServicio', tipo: 'texto', etiqueta: 'Dirección del inmueble donde se presta el servicio', requerido: true, ancho: 'completa' },
      { id: 'problema', tipo: 'select', etiqueta: '¿Cuál es el problema?', requerido: true, opciones: [
        { v: 'alta', t: 'La factura llegó mucho más alta de lo normal', legal: 'la factura presenta un valor desproporcionado frente al consumo histórico del inmueble (desviación significativa)' },
        { v: 'cobro_indebido', t: 'Me cobran algo que no consumí o no pedí', legal: 'se facturan bienes o servicios no consumidos ni solicitados' },
        { v: 'corte', t: 'Me cortaron el servicio sin avisar o estando al día', legal: 'el servicio fue suspendido sin previo aviso o sin causa legal' },
        { v: 'reconexion', t: 'Pagué y no me han reconectado', legal: 'pese a haber pagado, la empresa no ha restablecido el servicio' },
        { v: 'medidor', t: 'El medidor está dañado o me cobran por "promedio"', legal: 'el medidor presenta fallas o la empresa factura por promedio sin medición real' },
        { v: 'calidad', t: 'El servicio es malo o se interrumpe constantemente', legal: 'el servicio se presta con interrupciones o deficiencias de calidad' },
        { v: 'mora', t: 'Me cobran intereses o deudas de otro propietario', legal: 'se cobran obligaciones de períodos o usuarios anteriores que no corresponden al suscriptor' }
      ], ancho: 'completa' },
      { id: 'facturas', tipo: 'texto', etiqueta: 'Número y período de las facturas reclamadas', ejemplo: 'Ej.: Factura 98765432, período agosto 2026', ancho: 'media' },
      { id: 'valores', tipo: 'texto', etiqueta: 'Valor cobrado vs. valor normal', ejemplo: 'Ej.: Cobraron 480.000; normalmente pago 90.000', ancho: 'media' },
      { id: 'vulnerable', tipo: 'checks', etiqueta: 'En la vivienda hay (marca si aplica):', opciones: [ { v: 'ninos', t: 'Niños o niñas', legal: 'niños' }, { v: 'mayores', t: 'Personas mayores', legal: 'personas adultas mayores' }, { v: 'enfermos', t: 'Personas enfermas o con discapacidad (oxígeno, diálisis, etc.)', legal: 'personas con enfermedades o discapacidad que dependen del servicio' } ] },
      ...C.previo({ etiqueta: '¿Ya habías reclamado a la empresa?' }),
      C.relato({ ejemplo: 'Ej.:\nEl recibo de agosto llegó por 480.000 pesos; normalmente pago entre 80.000 y 95.000.\nNo hemos cambiado nada en la casa ni tenemos fugas.\nFui a la oficina y me dijeron que pagara y después reclamara.' })
    ],
    asunto: d => `Reclamación – ${R.capital(R.opcionTexto(cd('pet_spd', 'problema'), d.problema))} (cuenta ${d.cuenta || 'N/A'})`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} es suscriptor${a.g === 'f' ? 'a' : ''} o usuari${a.o} del servicio de ${R.opcionTexto(cd('pet_spd', 'servicio'), d.servicio, 't').toLowerCase()} prestado por ${R.entidad(d)} en el inmueble ubicado en ${d.direccionServicio || '[dirección]'}${d.cuenta ? `, cuenta o contrato No. ${d.cuenta}` : ''}.`);
      h.push(`Se presenta la siguiente irregularidad: ${R.opcionTexto(cd('pet_spd', 'problema'), d.problema)}${d.facturas ? ` (${d.facturas})` : ''}${d.valores ? `. ${R.oracion(d.valores)}` : '.'}`);
      if ((d.vulnerable || []).length) h.push(`En el inmueble habitan ${R.lista(d.vulnerable.map(v => R.opcionTexto(cd('pet_spd', 'vulnerable'), v)))}, sujetos de especial protección constitucional para quienes el servicio es indispensable.`);
      h.push(...R.hechosPrevio(d, 'la corrección de la facturación'));
      return h;
    },
    normas: d => d.servicio === 'internet' ? ['cp365', 'tic', 'l1480_23', 'cp23', 'l1755_33'] : ['cp365', 'l142_152', 'l142_146', 'l142_140', 'l142_158', 'l142_154', 'cp23', 'l1755_33'],
    fundamentos: d => {
      const f = [];
      if ((d.problema === 'corte' || d.problema === 'reconexion') && d.servicio !== 'internet') f.push(AJ.normas.t740.texto + ` (${AJ.normas.t740.cita}).`);
      return f;
    },
    peticiones: [
      { v: 'revisar', inicial: true, t: 'Que revisen la factura y la corrijan según el consumo real', legal: d => d.servicio === 'internet' ? 'Revisar la facturación reclamada, retirar los cargos por servicios no solicitados o no informados y reliquidar las facturas, conforme al Régimen de Protección de los Derechos de los Usuarios de Servicios de Comunicaciones (Resolución CRC 5050 de 2016).' : 'Revisar la facturación reclamada, investigar la desviación significativa conforme al artículo 149 de la Ley 142 de 1994 y reliquidarla con base en el consumo real o el promedio histórico del inmueble.' },
      { v: 'no_cortar', inicial: true, t: 'Que no suspendan el servicio mientras resuelven el reclamo', legal: d => d.servicio === 'internet' ? 'Abstenerse de suspender el servicio o de iniciar cobros por las sumas reclamadas mientras se resuelve esta petición y los recursos, aceptando el pago de los valores no reclamados.' : 'Abstenerse de suspender el servicio o de iniciar cobros por las sumas reclamadas mientras se resuelve esta petición y los recursos, conforme al artículo 155 de la Ley 142 de 1994, aceptando el pago de los valores no reclamados.' },
      { v: 'reconectar', inicial: d => ['corte', 'reconexion'].includes(d.problema), t: 'Que reconecten el servicio de inmediato', legal: 'Restablecer el servicio de manera inmediata, en un término no superior a veinticuatro (24) horas, dado que se eliminó la causa de la suspensión o esta fue ilegal.' },
      { v: 'medidor', inicial: d => d.problema === 'medidor', t: 'Que revisen o cambien el medidor con mi presencia', legal: 'Practicar una revisión técnica del medidor y de las instalaciones, en fecha y hora que se me informen previamente para estar presente, y entregar copia del acta.' },
      { v: 'copias', t: 'Que me entreguen el historial de consumos y las lecturas', legal: 'Entregar el historial de consumos y facturación de los últimos veinticuatro (24) meses, las lecturas del medidor y los soportes de la facturación reclamada.' },
      { v: 'devolver', t: 'Que me devuelvan o abonen lo cobrado de más', legal: 'Devolver o abonar en las siguientes facturas las sumas cobradas en exceso, debidamente indexadas.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'facturas', t: 'Copia de las facturas reclamadas y de facturas anteriores' }, { v: 'pagos', t: 'Soportes de pago' }, { v: 'fotos', t: 'Fotos del medidor o de las instalaciones' }, { v: 'medicas', t: 'Certificados médicos (si alguien depende del servicio)' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, nota: 'En peticiones, quejas y recursos relativos al contrato de servicios públicos domiciliarios, el plazo general es de quince días hábiles. El silencio administrativo positivo tiene condiciones y excepciones, entre ellas la práctica de pruebas y la demora atribuible al usuario. Verifica el caso y solicita su reconocimiento si corresponde (artículo 123 del Decreto 2150 de 1995, que subrogó el artículo 158 de la Ley 142 de 1994). Si responden negando, tienes 5 días hábiles para presentar recurso de reposición y en subsidio apelación ante la Superservicios (en esta plataforma: "Recurso contra la respuesta de la empresa de servicios públicos"). Si es internet, telefonía o televisión, el plazo para recurrir es de 10 días hábiles y la apelación va a la Superintendencia de Industria y Comercio, no a la Superservicios.', siNoResponden: 'Pide a la empresa que reconozca el silencio administrativo positivo; si se niega, queja ante la Superservicios. Si hay personas vulnerables sin agua o energía, presenta la "Tutela por corte de servicios públicos".' }
  },

  /* ---------------- BANCO ---------------- */
  {
    id: 'pet_banco', tipo: 'peticion', categoria: 'financiera',
    titulo: 'Petición a un banco o entidad financiera (cobros, paz y salvo, estado de cuenta, copia del contrato)',
    resumen: 'Pedir explicación de cobros, paz y salvo, estado de cuenta, copia del pagaré o contrato, detener cobranza abusiva o aclarar deudas que no reconoces.',
    palabras: ['banco', 'crédito', 'tarjeta', 'cobro', 'paz y salvo', 'estado de cuenta', 'pagaré', 'contrato', 'cobranza', 'acoso', 'fraude', 'transacción no reconocida', 'intereses', 'cuota', 'Nequi', 'Daviplata'],
    destinatario: { categoria: 'financiera', ejemploNombre: 'Ej.: Bancolombia S.A.', cargo: 'Representante legal / Defensor del Consumidor Financiero' },
    campos: [
      { id: 'producto', tipo: 'texto', etiqueta: 'Producto y número (crédito, tarjeta, cuenta)', ejemplo: 'Ej.: Tarjeta de crédito Visa terminada en 4521 / Crédito de libre inversión No. 00123', requerido: true, ancho: 'completa' },
      { id: 'tramite', tipo: 'checks', etiqueta: '¿Qué necesitas?', requerido: true, opciones: [
        { v: 'explicar', t: 'Que me expliquen cobros, intereses o cargos que no entiendo', legal: 'la explicación detallada de los cobros, intereses, seguros y cargos aplicados' },
        { v: 'no_reconozco', t: 'Que reversen una transacción o deuda que no reconozco (fraude)', legal: 'la reversión de las transacciones no reconocidas y la investigación del posible fraude' },
        { v: 'pazysalvo', t: 'Un paz y salvo o certificado de deuda', legal: 'la expedición del paz y salvo o certificado del estado de la obligación' },
        { v: 'estado', t: 'Estado de cuenta y detalle de pagos', legal: 'el estado de cuenta con el detalle de los pagos aplicados a capital, intereses y otros conceptos' },
        { v: 'copia', t: 'Copia del contrato, pagaré o seguro', legal: 'copia del contrato, del pagaré, de la carta de instrucciones y de las pólizas asociadas' },
        { v: 'cobranza', t: 'Que cesen las llamadas y mensajes de cobranza abusivos', legal: 'el cese de las prácticas de cobranza abusivas (llamadas reiteradas, a terceros, en horarios no permitidos)' },
        { v: 'reestructurar', t: 'Reestructurar o refinanciar mi deuda', legal: 'el estudio de una reestructuración o alivio de la obligación' },
        { v: 'cancelar', t: 'Cancelar un producto o un seguro que no pedí', legal: 'la cancelación del producto o servicio no solicitado y la devolución de lo cobrado' }
      ] },
      { id: 'valor', tipo: 'texto', etiqueta: 'Valor en discusión (si aplica)', ejemplo: 'Ej.: 2.350.000', ancho: 'media' },
      { id: 'fechaHechos', tipo: 'fecha', etiqueta: 'Fecha de los hechos (transacción, cobro, llamada)', ancho: 'media' },
      ...C.previo({ etiqueta: '¿Ya habías reclamado al banco (sucursal, línea, app)?' }),
      C.relato({ ejemplo: 'Ej.:\nEl 12 de septiembre de 2026 aparecieron tres compras por internet que yo no hice, por 2.350.000 pesos.\nLlamé ese mismo día, bloqueé la tarjeta y me dieron el radicado 445566.\nMe respondieron que la compra fue con clave y que no devuelven nada.' })
    ],
    asunto: d => `Derecho de petición y reclamación – ${d.producto || 'producto financiero'}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} es consumidor${a.g === 'f' ? 'a' : ''} financier${a.o} de ${R.entidad(d)}, titular de ${d.producto || 'el producto descrito'}.`);
      h.push(`Requiere ${R.lista((d.tramite || []).map(v => R.opcionTexto(cd('pet_banco', 'tramite'), v)))}${d.valor ? `, en relación con un valor de ${R.moneda(d.valor) || d.valor}` : ''}${d.fechaHechos ? `, por hechos ocurridos ${R.elDia(d.fechaHechos)}` : ''}.`);
      h.push(...R.hechosPrevio(d, 'la atención de esta reclamación'));
      return h;
    },
    normas: ['cp23', 'l1755_32', 'l1755_33', 'l1755_14', 'l1328_7', 'l1328_13', 'cp15', 'cp83'],
    fundamentos: d => {
      const f = [];
      if ((d.tramite || []).includes('no_reconozco')) f.push('Conforme al artículo 51 de la Ley 1480 de 2011, a la Ley 1328 de 2009 y a la jurisprudencia de la Sala de Casación Civil de la Corte Suprema de Justicia (sentencias SC18614-2016 del 19 de diciembre de 2016 y SC5176-2020 del 18 de diciembre de 2020), las entidades financieras asumen, como riesgo propio de su actividad profesional, las consecuencias de las transacciones fraudulentas realizadas a través de sus productos y canales electrónicos, salvo que demuestren la culpa del cliente o una causa extraña; la carga de probar que la operación fue realizada por el titular corresponde al banco. Además, la Ley Estatutaria 2573 de 2026 obliga a suspender los cobros, los intereses y los reportes negativos mientras se verifica una suplantación de identidad denunciada por el titular.');
      if ((d.tramite || []).includes('cobranza')) f.push('La Ley 2300 de 2023 establece que la cobranza solo puede realizarse de lunes a viernes entre las 7:00 a. m. y las 7:00 p. m. y los sábados entre las 8:00 a. m. y las 3:00 p. m., nunca en domingos o festivos, con un máximo de un contacto a la semana y uno al día, por los canales autorizados por el deudor y sin contactar a terceros; la Circular Externa 029 de 2014 de la Superintendencia Financiera y la Ley 1328 de 2009 prohíben además las amenazas, las informaciones engañosas y los gastos de cobranza no informados previamente.');
      return f;
    },
    peticiones: [
      { v: 'resolver', inicial: true, t: 'Que resuelvan mi solicitud de fondo y por escrito en 15 días hábiles', legal: d => `Resolver de fondo y por escrito, dentro de los quince (15) días hábiles siguientes, ${R.lista((d.tramite || []).map(v => R.opcionTexto(cd('pet_banco', 'tramite'), v))) || 'lo solicitado'}.` },
      { v: 'documentos', t: 'Que me entreguen copia de contrato, pagaré, extractos y grabaciones', legal: 'Entregar copia del contrato, del pagaré con su carta de instrucciones, de los extractos, de las pólizas y de las grabaciones o registros de las transacciones y reclamos relacionados.' },
      { v: 'no_reportar', inicial: true, t: 'Que no me reporten en centrales de riesgo mientras resuelven', legal: 'Abstenerse de reportar negativamente al titular en las centrales de riesgo y de iniciar cobro jurídico sobre las sumas en discusión mientras se resuelve la reclamación.' },
      { v: 'defensor', t: 'Que trasladen mi queja al Defensor del Consumidor Financiero', legal: 'Dar traslado de esta queja al Defensor del Consumidor Financiero de la entidad para su trámite, e informarme el radicado asignado.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'extractos', t: 'Extractos o pantallazos de los movimientos' }, { v: 'radicados', t: 'Radicados de reclamos anteriores' }, { v: 'denuncia', t: 'Denuncia ante la Fiscalía (en casos de fraude)' }, { v: 'llamadas', t: 'Registro de llamadas o mensajes de cobranza' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, siNoResponden: 'Si no responden o la respuesta no te satisface: queja ante el Defensor del Consumidor Financiero de la entidad (gratis) y luego ante la Superintendencia Financiera. Para transacciones fraudulentas también puedes demandar ante la Superfinanciera (función jurisdiccional).' }
  },

  /* ---------------- COLEGIO / UNIVERSIDAD ---------------- */
  {
    id: 'pet_colegio', tipo: 'peticion', categoria: 'educacion',
    titulo: 'Petición a un colegio, universidad o secretaría de educación (cupo, certificados, notas, matrícula)',
    resumen: 'Pedir un cupo escolar, la entrega de certificados retenidos, revisión de calificaciones, matrícula, traslado o respeto del debido proceso en sanciones.',
    palabras: ['colegio', 'escuela', 'universidad', 'cupo', 'matrícula', 'certificado', 'notas', 'calificaciones', 'boletín', 'diploma', 'secretaría de educación', 'traslado', 'expulsión', 'sanción', 'pensión del colegio', 'bullying', 'acoso escolar', 'SENA', 'ICETEX'],
    destinatario: { categoria: 'educacion', ejemploNombre: 'Ej.: Institución Educativa San Juan Bosco', cargo: 'Rector(a) / Secretaría de Educación Municipal' },
    campos: [
      { id: 'estudiante', tipo: 'texto', etiqueta: 'Nombre del estudiante y grado o programa', ejemplo: 'Ej.: Samuel Ríos, grado 7° / Ana Pérez, 5° semestre de Enfermería', requerido: true, ancho: 'completa' },
      { id: 'tramite', tipo: 'select', etiqueta: '¿Qué necesitas?', requerido: true, opciones: [
        { v: 'cupo', t: 'Un cupo escolar (no hay cupo o me lo negaron)', legal: 'la asignación de cupo escolar' },
        { v: 'certificados', t: 'Certificados, boletines o diploma que no me entregan', legal: 'la entrega de los certificados de estudio, boletines o el diploma' },
        { v: 'notas', t: 'Revisión de calificaciones o de una decisión académica', legal: 'la revisión de las calificaciones o de la decisión académica' },
        { v: 'sancion', t: 'Una sanción, expulsión o cancelación de matrícula sin debido proceso', legal: 'la revisión de la sanción disciplinaria impuesta sin el debido proceso' },
        { v: 'acoso', t: 'Que actúen frente a acoso escolar o maltrato', legal: 'la activación de la ruta de atención frente a la situación de acoso escolar o maltrato' },
        { v: 'traslado', t: 'Traslado a otra institución', legal: 'el traslado del estudiante a otra institución' },
        { v: 'cobros', t: 'Cobros no autorizados o aumento de pensión irregular', legal: 'la revisión de cobros no autorizados' },
        { v: 'inclusion', t: 'Apoyos o ajustes para un estudiante con discapacidad', legal: 'los ajustes razonables y apoyos pedagógicos para el estudiante con discapacidad' },
        { v: 'otro', t: 'Otro asunto', legal: 'el asunto descrito en los hechos' }
      ], ancho: 'completa' },
      ...C.previo({ etiqueta: '¿Ya lo habías solicitado al colegio o universidad?' }),
      C.relato({ ejemplo: 'Ej.:\nMi hijo terminó 7° en 2025 en el colegio.\nNos trasladamos de ciudad y el nuevo colegio exige los certificados.\nEl colegio anterior dice que no los entrega hasta que pague dos meses de pensión atrasados.' })
    ],
    asunto: d => `Derecho de petición – ${R.capital(R.opcionTexto(cd('pet_colegio', 'tramite'), d.tramite))} – ${d.estudiante || 'estudiante'}`,
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${d.estudiante || 'El estudiante'} ${d.tramite === 'cupo' ? 'requiere acceder a' : 'se encuentra o estuvo matriculad' + (a.tercero ? a.o : 'o(a)') + ' en'} ${R.entidad(d)}.`);
      h.push(`Se requiere ${R.opcionTexto(cd('pet_colegio', 'tramite'), d.tramite)}, sin que hasta la fecha la institución lo haya garantizado.`);
      h.push(...R.hechosPrevio(d, R.opcionTexto(cd('pet_colegio', 'tramite'), d.tramite)));
      return h;
    },
    normas: ['cp67', 'cp44', 'l115_4', 'l1098_28', 'cp23', 'l1755_32', 'l1755_14'],
    fundamentos: d => {
      const f = [];
      if (d.tramite === 'certificados' || d.tramite === 'cobros') f.push(AJ.normas.su624.texto + ` (${AJ.normas.su624.cita}).`, AJ.normas.t_cert.texto + ` (${AJ.normas.t_cert.cita}).`);
      if (d.tramite === 'sancion') f.push(AJ.normas.cp29.texto + ` (${AJ.normas.cp29.cita}).`, 'La Corte Constitucional ha reiterado (entre otras, sentencias T-390 de 2011 y T-478 de 2015) que el manual de convivencia debe respetar la Constitución y que toda sanción exige un procedimiento previo con comunicación de los cargos, oportunidad de defensa, pruebas, decisión motivada y recursos.');
      if (d.tramite === 'acoso') f.push('La Ley 1620 de 2013 y el Decreto 1965 de 2013 obligan a las instituciones a activar la Ruta de Atención Integral para la Convivencia Escolar ante situaciones de acoso, con medidas de protección a la víctima, atención y reporte al comité de convivencia y, cuando corresponda, a las autoridades.');
      if (d.tramite === 'inclusion') f.push('El Decreto 1421 de 2017 obliga a las instituciones educativas a elaborar el Plan Individual de Ajustes Razonables (PIAR) y a garantizar los apoyos necesarios para los estudiantes con discapacidad, sin que puedan negar el cupo ni condicionar la permanencia.');
      if (d.tramite === 'cupo') f.push('Conforme al artículo 67 de la Constitución, al artículo 28 de la Ley 1098 de 2006 y a la jurisprudencia constitucional (sentencias T-008 de 2016 y T-434 de 2018, entre otras), las secretarías de educación deben garantizar un cupo en una institución oficial cercana a la residencia del menor y, cuando la distancia lo exige, el transporte escolar; la falta de cupo no es excusa válida para negar el acceso.');
      return f;
    },
    peticiones: [
      { v: 'resolver', inicial: true, t: 'Que resuelvan de fondo mi solicitud en el plazo legal', legal: d => `Garantizar ${R.opcionTexto(cd('pet_colegio', 'tramite'), d.tramite)} y comunicar por escrito la decisión dentro de los quince (15) días hábiles siguientes.` },
      { v: 'certificados', t: 'Que entreguen de inmediato los certificados', legal: 'Expedir y entregar de inmediato los certificados de estudio, boletines y constancias requeridos, sin condicionarlos al pago de obligaciones económicas, conforme a la jurisprudencia constitucional.' },
      { v: 'debido_proceso', t: 'Que respeten el debido proceso y revoquen la sanción', legal: 'Revocar la sanción impuesta sin el debido proceso y, de considerarlo necesario, adelantar el procedimiento previsto en el manual de convivencia con todas las garantías.' },
      { v: 'copias', t: 'Que me entreguen copia del manual de convivencia, actas y expediente', legal: 'Expedir copia del manual de convivencia, del observador del estudiante, de las actas y del expediente disciplinario o académico relacionado.' },
      { v: 'remitir', t: 'Si no son competentes, que remitan a la Secretaría de Educación', legal: 'Si la competencia corresponde a la Secretaría de Educación, remitirle la petición dentro de los cinco (5) días siguientes e informármelo.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de mi cédula y del documento del estudiante' }, { v: 'registro', t: 'Registro civil del menor' }, { v: 'boletines', t: 'Boletines, certificados o constancias previas' }, { v: 'cartas', t: 'Comunicaciones del colegio (sanción, negativa, cobro)' }, { v: 'medicos', t: 'Diagnóstico o certificado de discapacidad (si aplica)' } ],
    guia: { plazo: { dias: 15, tipo: 'habiles' }, siNoResponden: 'Sin respuesta en 15 días hábiles, o si el menor sigue sin estudiar, presenta la "Tutela por el derecho a la educación". También puedes quejarte ante la Secretaría de Educación y, si hay maltrato, ante el ICBF (línea 141).' }
  },

  /* ---------------- INFORMACIÓN PÚBLICA ---------------- */
  {
    id: 'pet_info_publica', tipo: 'peticion', categoria: 'municipio',
    titulo: 'Solicitud de información pública (contratos, presupuesto, obras, nómina, decisiones)',
    resumen: 'Pedir a cualquier entidad pública documentos e información que deben ser públicos: contratos, presupuesto, ejecución de obras, estudios, actas. Plazo: 10 días hábiles. No tienes que explicar para qué.',
    palabras: ['información pública', 'transparencia', 'contrato', 'presupuesto', 'obra', 'nómina', 'actas', 'estudios', 'veeduría', 'control ciudadano', 'Ley 1712', 'copias'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Alcaldía de Pereira / Hospital San Jorge / Concejo Municipal', cargo: 'Secretaría General / Oficina de atención al ciudadano' },
    campos: [
      { id: 'informacion', tipo: 'textarea', etiqueta: '¿Qué información o documentos necesitas? (sé lo más específico posible)', ejemplo: 'Ej.:\nCopia del contrato de obra No. 123 de 2025 para la pavimentación de la calle 10, con sus estudios previos, actas de inicio y de avance, informes de interventoría y pagos realizados.', requerido: true, filas: 5 },
      { id: 'periodo', tipo: 'texto', etiqueta: 'Período o vigencia', ejemplo: 'Ej.: Vigencias 2024 a 2026', ancho: 'media' },
      { id: 'formato', tipo: 'select', etiqueta: '¿En qué formato la prefieres?', opciones: [ { v: 'digital', t: 'Digital, al correo electrónico (gratis)', legal: 'en formato digital, al correo electrónico indicado' }, { v: 'fisico', t: 'Copia física', legal: 'en copia física' }, { v: 'consulta', t: 'Consulta directa en la entidad', legal: 'mediante consulta directa en las instalaciones de la entidad' } ], valorInicial: 'digital', ancho: 'media' },
      { id: 'proposito', tipo: 'texto', etiqueta: 'Propósito (opcional; la ley no te obliga a decirlo)', ejemplo: 'Ej.: Veeduría ciudadana sobre la obra del barrio', ancho: 'completa' }
    ],
    asunto: d => 'Solicitud de acceso a información pública – Ley 1712 de 2014',
    hechos: d => {
      const h = [];
      h.push(`${R.entidad(d)} es sujeto obligado por la Ley 1712 de 2014 y tiene en su poder la siguiente información de carácter público: ${R.relatoAHechos(d.informacion).join(' ')}${d.periodo ? ` (período: ${d.periodo}).` : ''}`);
      if (d.proposito) h.push(`Aunque la ley no exige motivar la solicitud, se informa que la información se requiere para: ${R.oracion(d.proposito)}`);
      h.push('La información solicitada no está sometida a reserva legal ni constitucional, o, de estarlo parcialmente, debe entregarse la parte no reservada conforme al principio de divisibilidad (artículo 21 de la Ley 1712 de 2014).');
      return h;
    },
    normas: ['cp74', 'cp23', 'l1712_4', 'l1712_25', 'l1755_14', 'l1755_24', 'cp209'],
    peticiones: [
      { v: 'entregar', inicial: true, t: 'Que me entreguen la información completa en 10 días hábiles', legal: d => `Entregar de manera completa, veraz y actualizada la información y los documentos relacionados en los hechos, ${R.opcionTexto(cd('pet_info_publica', 'formato'), d.formato)}, dentro de los diez (10) días hábiles siguientes a la recepción de esta solicitud.` },
      { v: 'motivar', inicial: true, t: 'Si niegan algo, que lo motiven por escrito citando la norma de reserva', legal: 'En caso de negar total o parcialmente la información, motivar la decisión por escrito, indicando la norma legal o constitucional que establece la reserva, su plazo y el funcionario responsable, conforme a los artículos 18, 19 y 28 de la Ley 1712 de 2014.' },
      { v: 'gratis', t: 'Que no cobren por la información digital', legal: 'Abstenerse de cobrar por la entrega en formato digital, y en caso de copias físicas, cobrar únicamente el costo de reproducción informado previamente.' },
      { v: 'remitir', t: 'Si otra entidad la tiene, que remitan la solicitud', legal: 'Si la información reposa en otra entidad, remitirle la solicitud dentro de los cinco (5) días siguientes e informármelo.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula (opcional)' }, { v: 'referencias', t: 'Referencias de los contratos, obras o actos (números, fechas, enlaces del SECOP)' } ],
    guia: { plazo: { dias: 10, tipo: 'habiles' }, nota: 'Si no responden en 10 días hábiles, se entiende aceptada y deben entregar en 3 días. Contra la negativa procede recurso de reposición en 3 días (artículo 27 de la Ley 1712 de 2014) y, para información reservada, el trámite ante el Tribunal Administrativo.', siNoResponden: 'Tutela por violación del derecho de petición y de acceso a la información. También puedes acudir a la Procuraduría, garante de la Ley 1712.' }
  },

  /* ---------------- COPIAS DE DOCUMENTOS / EXPEDIENTE ---------------- */
  {
    id: 'pet_copias', tipo: 'peticion', categoria: 'municipio',
    titulo: 'Solicitud de copias de documentos o de un expediente propio',
    resumen: 'Pedir copia de un expediente, resolución, acta, contrato, hoja de vida, historia laboral o cualquier documento que te involucre, ante cualquier entidad pública o privada. Plazo: 10 días hábiles.',
    palabras: ['copia', 'copias', 'expediente', 'resolución', 'acta', 'documento', 'certificado', 'constancia', 'hoja de vida', 'archivo', 'notaría', 'registraduría', 'registro civil', 'escritura'],
    destinatario: { categoria: 'municipio', ejemploNombre: 'Ej.: Notaría 15 de Bogotá / Registraduría / Secretaría de Educación', cargo: 'Oficina de archivo y correspondencia' },
    campos: [
      { id: 'documentos', tipo: 'textarea', etiqueta: '¿Qué documentos necesitas? (sé específico: nombre, número, fecha)', ejemplo: 'Ej.:\nCopia auténtica de la Resolución 0456 del 12 de marzo de 2026 que me negó el subsidio.\nCopia completa del expediente administrativo No. 2026-0033.', requerido: true, filas: 4 },
      { id: 'relacion', tipo: 'texto', etiqueta: '¿Cuál es tu relación con esos documentos?', ejemplo: 'Ej.: Soy el titular / Soy parte del proceso / Soy heredero', requerido: true, ancho: 'completa' },
      { id: 'formato', tipo: 'select', etiqueta: 'Formato', opciones: [ { v: 'digital', t: 'Digital, al correo (gratis)', legal: 'en formato digital' }, { v: 'simple', t: 'Copia simple física', legal: 'en copia simple' }, { v: 'autentica', t: 'Copia auténtica', legal: 'en copia auténtica' } ], valorInicial: 'digital', ancho: 'media' },
      { id: 'urgencia', tipo: 'texto', etiqueta: '¿Para cuándo los necesitas y por qué? (opcional)', ejemplo: 'Ej.: Antes del 30 de octubre para presentar un recurso', ancho: 'media' }
    ],
    asunto: d => 'Derecho de petición – Solicitud de copias de documentos',
    hechos: d => {
      const a = R.actor(d);
      const h = [];
      h.push(`${a.Nom} tiene interés directo en los siguientes documentos que reposan en ${R.entidad(d)}: ${R.relatoAHechos(d.documentos).join(' ')}`);
      if (d.relacion) h.push(`Relación con los documentos: ${R.oracion(d.relacion)}`);
      if (d.urgencia) h.push(`Los documentos se requieren con urgencia: ${R.oracion(d.urgencia)}`);
      return h;
    },
    normas: ['cp23', 'cp74', 'l1755_13', 'l1755_14', 'l1755_24', 'l1755_32'],
    peticiones: [
      { v: 'entregar', inicial: true, t: 'Que me entreguen las copias en 10 días hábiles', legal: d => `Expedir y entregar ${R.opcionTexto(cd('pet_copias', 'formato'), d.formato)} los documentos relacionados, dentro de los diez (10) días hábiles siguientes a la recepción de esta solicitud.` },
      { v: 'costo', inicial: true, t: 'Que me informen previamente el costo de las copias físicas, si lo hay', legal: 'Informar previamente el valor de reproducción cuando se trate de copias físicas, el cual no podrá exceder el costo real, conforme al artículo 29 de la Ley 1437 de 2011.' },
      { v: 'motivar', t: 'Si niegan algo, que me digan por escrito la norma de reserva', legal: 'En caso de negativa por reserva, indicar por escrito la norma que la establece, conforme al artículo 25 de la Ley 1437 de 2011.' }
    ],
    anexos: [ { v: 'cedula', t: 'Copia de la cédula' }, { v: 'prueba', t: 'Prueba de la relación con el documento (poder, registro civil, radicado)' } ],
    guia: { plazo: { dias: 10, tipo: 'habiles' }, nota: 'Si no responden en 10 días hábiles, la ley entiende aceptada la solicitud y deben entregar las copias en los 3 días siguientes.', siNoResponden: 'Tutela por violación del derecho de petición (recuerda anexar copia de esta solicitud con el sello de recibido o el correo enviado).' }
  }
  );
})();
