/* ============================================================
   orientador.js — "No sé qué documento necesito": preguntas
   sencillas para explorar documentos y pasos posibles. La selección
   orienta, pero no determina la procedencia ni el resultado de una acción.
   El Memorialista funciona también sin conexión.
   ============================================================ */
window.AJ = window.AJ || {};

AJ.orientador = (function () {
  'use strict';

  const RUTA_PETICION = (que, dias) => [
    `Presenta el derecho de petición ${que} y guarda tu copia con sello, el número de radicado o el correo enviado.`,
    dias ? `El término ordinario para esta solicitud es ${dias} días hábiles; verifica las reglas especiales y cualquier prórroga. Registra la recepción en "Mis documentos" para consultar una fecha de referencia.` : 'Revisa en la guía el plazo según lo que pides y la entidad; puede haber términos especiales o prórrogas. Registra la recepción en "Mis documentos" para consultar el seguimiento al abrir la aplicación.',
    'Si falta una respuesta de fondo y venció el término aplicable, revisa si procede tutela por petición. Una respuesta negativa de fondo no implica por sí sola que se haya vulnerado ese derecho.'
  ];
  const RUTA_TUTELA = extra => [
    'Reúne las pruebas que tengas de lo ocurrido (órdenes, cartas, respuestas o fotos) y los datos de identificación pertinentes.',
    ...(extra || []),
    'Puedes usar Tutela en Línea o consultar la oficina judicial competente. El término de referencia para el fallo es 10 días hábiles desde la presentación; confirma el cómputo con el despacho.',
    'Si se concede una orden y no se cumple, revisa su alcance y plazo y consulta al juez las vías de cumplimiento e incidente de desacato.'
  ];
  const AYUDA_GRATIS = 'Puedes solicitar orientación en la Personería, la Defensoría del Pueblo o un consultorio jurídico universitario. Confirma sus canales oficiales, requisitos de atención y competencia para tu asunto.';

  const nodos = {
    inicio: {
      pregunta: '¿Sobre qué es tu problema?',
      ayuda: 'Escoge lo que más se parezca a tu situación. Puedes devolverte cuando quieras.',
      opciones: [
        { t: 'Salud: EPS, medicamentos, citas, cirugías o incapacidades', icono: 'salud', ir: 'salud' },
        { t: 'Trabajo, salario, acoso laboral o pensión', icono: 'trabajo', ir: 'trabajo' },
        { t: 'Agua, luz, gas, internet o celular', icono: 'servicios', ir: 'servicios' },
        { t: 'Bancos, deudas, cobranzas o Datacrédito', icono: 'banco', ir: 'finanzas' },
        { t: 'Familia: violencia, cuota alimentaria, custodia', icono: 'familia', ir: 'familia' },
        { t: 'La alcaldía, el barrio, tránsito, impuestos o Sisbén', icono: 'edificio', ir: 'municipio' },
        { t: 'Colegio, universidad o estudios', icono: 'educacion', ir: 'educacion' },
        { t: 'Víctimas del conflicto, amenazas o migrantes', icono: 'escudo', ir: 'proteccion' },
        { t: 'Ya presenté un documento y no responden o no cumplen', icono: 'calendario', ir: 'seguimiento' },
        { t: 'Una entidad decidió algo en mi contra (multa, resolución, sanción)', icono: 'martillo', ir: 'decision' },
        { t: 'Una compra, una garantía o un servicio que pagué', icono: 'alerta', ir: 'consumo' },
        { t: 'Necesito un contrato, un recibo, un pagaré o un poder', icono: 'documento', ir: 'contratos' },
        { t: 'Otra cosa', icono: 'info', ir: 'otro' }
      ]
    },

    /* ---------------- Salud ---------------- */
    salud: {
      pregunta: '¿Qué pasa con tu salud?',
      opciones: [
        { t: 'La EPS no autoriza o no entrega una cita, un medicamento, una cirugía, un examen o un insumo que ordenó el médico', ir: 'salud_urgencia' },
        { t: 'Tengo una enfermedad crónica, cáncer o una discapacidad y necesito que cubran todo el tratamiento', fin: {
          casos: ['tut_salud_integral', 'tut_salud_servicio'],
          porque: 'Con el tratamiento integral el juez ordena a la EPS cubrir todo lo que el médico tratante formule para esa enfermedad, sin que tengas que poner una tutela por cada orden.',
          ruta: RUTA_TUTELA(['Pide en la tutela el tratamiento integral y, si algo no da espera, la medida provisional.'])
        } },
        { t: 'No me pagan las incapacidades', ir: 'incapacidades' },
        { t: 'No me entregan la historia clínica u otros documentos médicos', fin: {
          casos: ['pet_eps_historia'],
          porque: 'La historia clínica te pertenece: la clínica, el hospital o la EPS deben darte copia. Como es una solicitud de documentos, tienen 10 días hábiles.',
          ruta: RUTA_PETICION('a la clínica, el hospital o la EPS', 10)
        } },
        { t: 'Embarazo, control prenatal, anticoncepción, IVE o atención por violencia sexual', fin: {
          casos: ['muj_salud_sexual', 'tut_salud_servicio'],
          porque: 'Son servicios que la EPS debe prestar sin demoras ni trámites que los hagan imposibles.',
          ruta: ['Presenta la petición a la EPS y guarda el radicado.', 'Si es urgente (riesgo en el embarazo, IVE, violencia sexual) no esperes: presenta de una vez la tutela por salud con medida provisional.', 'También puedes quejarte ante la Superintendencia de Salud.'],
          urgente: 'Si fuiste víctima de violencia sexual, la atención de urgencias es inmediata y gratuita en cualquier hospital. Línea 155 (24 horas).'
        } },
        { t: 'No me pagan la licencia de maternidad', fin: {
          casos: ['muj_licencia_maternidad'],
          porque: 'La licencia de maternidad reemplaza tu salario: la EPS o el empleador deben pagarla. Si es tu único ingreso, también puede proceder la tutela.',
          ruta: RUTA_PETICION('a la EPS o al empleador')
        } },
        { t: 'Soy migrante y no me atienden o no me afilian', fin: {
          casos: ['tut_migrantes', 'pet_migracion'],
          porque: 'Toda persona en Colombia tiene derecho a la atención de urgencias, y los migrantes regularizados (por ejemplo, con PPT) a afiliarse al sistema de salud.',
          ruta: RUTA_TUTELA()
        } },
        { t: 'Quiero quejarme de la EPS o de un hospital ante la Superintendencia de Salud', fin: {
          casos: ['queja_supersalud'],
          porque: 'La Superintendencia Nacional de Salud vigila a las EPS y puede ordenarles prestar el servicio. La queja no reemplaza la tutela si hay urgencia.',
          ruta: ['Presenta la queja con el radicado de lo que ya pediste a la EPS.', 'Guarda el número de la queja y revisa tu correo.', 'Si hay riesgo para tu salud, presenta la tutela por salud sin esperar.']
        } }
      ]
    },
    salud_urgencia: {
      pregunta: '¿Puedes esperar unos días, o es urgente?',
      ayuda: 'Es urgente si hay dolor fuerte, riesgo de empeorar, peligro para la vida o se interrumpió un tratamiento que no puede parar.',
      opciones: [
        { t: 'Es urgente: no puedo esperar', fin: {
          casos: ['tut_salud_servicio'],
          porque: 'Si hay riesgo para la salud o la vida, busca atención inmediata y orientación sobre tutela con medida provisional. El juez evalúa los hechos y la urgencia; no es necesario agotar una petición en todas las situaciones.',
          ruta: RUTA_TUTELA(['Marca en el formulario que la situación es urgente para pedir la medida provisional.']),
          urgente: 'Si la vida está en peligro en este momento, ve primero a urgencias: ninguna clínica u hospital puede negar la atención de urgencias.'
        } },
        { t: 'Puedo esperar unos días', fin: {
          casos: ['pet_eps_servicio', 'tut_salud_servicio'],
          porque: 'El derecho de petición deja constancia por escrito y obliga a la EPS a responder de fondo. Si no cumple, esa petición es una prueba fuerte para la tutela.',
          ruta: RUTA_PETICION('a la EPS')
        } }
      ]
    },
    incapacidades: {
      pregunta: '¿Las incapacidades son tu único ingreso?',
      opciones: [
        { t: 'Sí, no tengo con qué vivir mientras tanto', fin: {
          casos: ['tut_incapacidades', 'pet_incapacidades'],
          porque: 'Explica cómo la falta de pago afecta tu subsistencia y aporta las pruebas disponibles. Puede ser relevante para que un juez evalúe una tutela; la procedencia depende de las circunstancias y de los otros medios de defensa.',
          ruta: RUTA_TUTELA()
        } },
        { t: 'No, puedo esperar la respuesta', fin: {
          casos: ['pet_incapacidades', 'tut_incapacidades'],
          porque: 'Primero se pide por escrito a quien debe pagar (EPS, ARL, fondo de pensiones o empleador, según los días de incapacidad).',
          ruta: RUTA_PETICION('a quien debe pagar las incapacidades')
        } }
      ]
    },

    /* ---------------- Trabajo y pensión ---------------- */
    trabajo: {
      pregunta: '¿Qué pasa en tu trabajo?',
      opciones: [
        { t: 'No me pagan el salario, la liquidación o la seguridad social, o no me dan el certificado laboral', ir: 'trabajo_pago' },
        { t: 'Me despidieron estando embarazada, enferma(o), incapacitada(o) o con una discapacidad', fin: {
          casos: ['tut_estabilidad'],
          porque: 'Estas personas tienen estabilidad laboral reforzada: el empleador no puede despedirlas por esa condición sin autorización del Ministerio del Trabajo. El juez puede ordenar el reintegro.',
          ruta: RUTA_TUTELA(),
          plazo: 'Preséntala cuanto antes: el juez revisa que no haya pasado demasiado tiempo desde el despido.'
        } },
        { t: 'Me acosan en el trabajo (acoso laboral o acoso sexual)', fin: {
          casos: ['muj_acoso_laboral', 'muj_denuncia'],
          porque: 'La queja activa el Comité de Convivencia, al empleador o al Ministerio del Trabajo. El acoso sexual además es un delito que puedes denunciar ante la Fiscalía.',
          ruta: ['Presenta la queja con fechas, testigos y pruebas (mensajes, correos).', 'Si hubo acoso sexual, puedes presentar también la denuncia penal.', 'Si te despiden o te perjudican por quejarte, la ley te protege.']
        } },
        { t: 'Mi pensión: no la resuelven, no la pagan o mi historia laboral está mal', ir: 'pension' },
        { t: 'No me pagan la licencia de maternidad', fin: {
          casos: ['muj_licencia_maternidad'],
          porque: 'La licencia de maternidad reemplaza tu salario y la deben pagar la EPS o el empleador.',
          ruta: RUTA_PETICION('a la EPS o al empleador')
        } },
        { t: 'Necesito un contrato para una empleada o un empleado doméstico', fin: {
          casos: ['con_servicio_domestico'],
          porque: 'El contrato por escrito protege a las dos partes: salario, jornada, prestaciones y seguridad social.',
          ruta: ['Llena el contrato con los datos de las dos partes.', 'Imprímelo en dos copias y fírmenlo.', 'Afilia a la persona a salud, pensión, riesgos laborales y caja de compensación.']
        } }
      ]
    },
    trabajo_pago: {
      pregunta: '¿Puedes esperar la respuesta del empleador?',
      opciones: [
        { t: 'Sí, todavía puedo esperar', fin: {
          casos: ['pet_empleador', 'tut_salario'],
          porque: 'La petición deja por escrito lo que te deben y obliga al empleador a responder. También sirve como prueba para el Ministerio del Trabajo o un proceso laboral.',
          ruta: [...RUTA_PETICION('al empleador'), 'Puedes quejarte también ante el Ministerio del Trabajo (Línea 120).']
        } },
        { t: 'No: me deben varios meses y no tengo con qué vivir', fin: {
          casos: ['tut_salario', 'pet_empleador'],
          porque: 'Si la falta de pago afecta tu subsistencia, documenta esa situación. Puede justificar evaluar una tutela, según las circunstancias y la eficacia de los otros medios de defensa.',
          ruta: RUTA_TUTELA()
        } }
      ]
    },
    pension: {
      pregunta: '¿Qué pasa con tu pensión?',
      opciones: [
        { t: 'Ya la pedí y no la resuelven', fin: {
          casos: ['pet_pension', 'tut_pension'],
          porque: 'Los términos dependen del tipo de solicitud pensional y de la actuación pendiente. Revisa la guía, la fecha de recepción completa y las comunicaciones de la entidad.',
          ruta: ['Consulta por escrito el estado y la actuación pendiente.', 'Si persiste la afectación, revisa con orientación jurídica los requisitos de la acción que corresponda.', 'Si existe una orden judicial incumplida, informa al juzgado y conserva las pruebas.']
        } },
        { t: 'Ya me la reconocieron, pero no me la pagan', fin: {
          casos: ['tut_pension', 'pet_pension'],
          porque: 'La pensión es el sustento de la persona: si no la pagan, está en juego su mínimo vital.',
          ruta: RUTA_TUTELA()
        } },
        { t: 'Mi historia laboral tiene errores o faltan semanas', fin: {
          casos: ['pet_pension'],
          porque: 'La corrección de la historia laboral se pide por escrito al fondo o a Colpensiones, con los certificados de los empleadores.',
          ruta: RUTA_PETICION('a Colpensiones o al fondo')
        } }
      ]
    },

    /* ---------------- Servicios públicos ---------------- */
    servicios: {
      pregunta: '¿Qué pasó con el servicio?',
      opciones: [
        { t: 'La factura llegó muy alta o me cobran algo que no debo', fin: {
          casos: ['pet_spd', 'rec_spd'],
          porque: 'Presenta el reclamo y guarda la recepción. El término ordinario de respuesta es 15 días hábiles, con reglas y excepciones según el servicio. El contador no declara por sí solo un silencio favorable.',
          ruta: ['Presenta el reclamo y revisa las obligaciones de pago de las sumas no discutidas y las reglas del servicio.', 'Si procede recurso: referencia de 5 días hábiles en servicios domiciliarios; 10 en internet, telefonía o televisión.', 'La autoridad de apelación depende del servicio: Superservicios o, en comunicaciones, la SIC.']
        } },
        { t: 'Me cortaron el agua o la luz y en la casa hay niños, personas enfermas, mayores o con discapacidad', fin: {
          casos: ['tut_servicios_publicos', 'pet_spd'],
          porque: 'La Corte Constitucional ha ordenado reconectar el agua o la energía cuando el corte pone en riesgo a personas de especial protección, aunque haya deuda, mientras se hace un acuerdo de pago.',
          ruta: RUTA_TUTELA(['Pide la medida provisional para que reconecten mientras el juez decide.'])
        } },
        { t: 'Ya reclamé y la empresa me respondió en contra', fin: {
          casos: ['rec_spd'],
          porque: 'Revisa si la decisión admite reposición y apelación subsidiaria. En servicios domiciliarios la autoridad de apelación es Superservicios; en comunicaciones, la SIC.',
          ruta: ['Presenta el recurso a la empresa.', 'La respuesta tiene un término ordinario de 15 días hábiles. Antes de invocar silencio favorable, revisa si hubo pruebas, prórrogas u otras circunstancias previstas en el régimen aplicable.'],
          plazo: 'Referencia: 5 días hábiles para servicios domiciliarios; 10 para internet, telefonía o televisión. Verifica la fecha efectiva de conocimiento o comunicación de la decisión.'
        } },
        { t: 'Internet, telefonía celular o televisión', fin: {
          casos: ['pet_spd', 'rec_spd'],
          porque: 'Los operadores de internet, telefonía y televisión también deben atender tus reclamos (PQR) y responder en 15 días hábiles.',
          ruta: ['Presenta el reclamo al operador y guarda el código único (CUN).', 'Si responde en contra, presenta el recurso dentro de los 10 días hábiles siguientes.']
        } }
      ]
    },

    /* ---------------- Finanzas ---------------- */
    finanzas: {
      pregunta: '¿Qué pasa con el banco, la deuda o tus datos?',
      opciones: [
        { t: 'Me reportaron en Datacrédito o TransUnion sin razón, o ya pagué y sigo reportado(a)', fin: {
          casos: ['hd_reclamo', 'tut_habeas_data'],
          porque: 'El reclamo permite pedir que se verifique el reporte. El término ordinario es 15 días hábiles y puede ampliarse hasta 8 más con aviso motivado. La tutela exige verificar sus requisitos, no solo el paso del tiempo.',
          ruta: ['Presenta el reclamo de hábeas data y guarda el radicado.', 'Si no hay respuesta dentro del término aplicable o discrepas de la decisión, revisa los mecanismos ante la autoridad de control y las condiciones de una posible tutela.']
        } },
        { t: 'Me llaman a cobrar a toda hora, a mí o a mi familia, o usan mis datos sin permiso', fin: {
          casos: ['hd_supresion'],
          porque: 'Puedes exigir que dejen de usar tus datos para fines que no autorizaste y que no contacten a terceros. La Ley 2300 de 2023 limita los horarios y canales de cobranza.',
          ruta: ['Presenta la solicitud a la empresa.', 'Distingue consulta de datos (10 días hábiles) de reclamo (15); pueden existir prórrogas motivadas. Si persiste el problema, consulta los requisitos para acudir a la SIC.']
        } },
        { t: 'El banco me cobra algo indebido, no me da el paz y salvo o no me responde', fin: {
          casos: ['pet_banco', 'queja_financiera'],
          porque: 'El banco debe responder por escrito. Si no lo hace, puedes acudir al Defensor del Consumidor Financiero o a la Superintendencia Financiera.',
          ruta: RUTA_PETICION('al banco')
        } },
        { t: 'Presté plata o debo plata y quiero dejarlo por escrito', fin: {
          casos: ['con_pagare', 'con_acuerdo_pago', 'con_recibo'],
          porque: 'Un pagaré o un acuerdo de pago firmado protege a las dos partes y sirve como prueba si alguien incumple.',
          ruta: ['Escoge el documento: pagaré (préstamo), acuerdo de pago (deuda en cuotas) o recibo (pago hecho).', 'Fírmenlo las dos partes; con testigos es más fuerte.']
        } }
      ]
    },

    /* ---------------- Familia ---------------- */
    familia: {
      pregunta: '¿Qué está pasando en tu familia?',
      opciones: [
        { t: 'Sufro violencia en mi casa, de mi pareja o de mi expareja', ir: 'violencia' },
        { t: 'El padre o la madre de mis hijos no da para su sostenimiento', fin: {
          casos: ['fam_alimentos'],
          porque: 'La autoridad o el operador habilitado depende del beneficiario y del asunto. Hay opciones gratuitas; verifica la competencia y los documentos requeridos antes de solicitar la conciliación.',
          ruta: ['Presenta la solicitud con los gastos de los niños y lo que sabes de los ingresos del otro padre o madre.', 'Asiste a la audiencia de conciliación; el acta presta mérito ejecutivo.', 'Si no cumple lo acordado, se puede cobrar ante un juez.']
        } },
        { t: 'Soy una persona mayor y mis hijos no me ayudan, o mi pareja no me da para vivir', fin: {
          casos: ['fam_alimentos'],
          porque: 'La obligación de dar alimentos también protege a los padres, a las personas mayores y a los cónyuges o compañeros permanentes que lo necesitan.',
          ruta: ['Consulta un operador habilitado para conciliación de alimentos entre adultos; no presupongas que la autoridad de infancia es competente.', 'Asiste a la audiencia de conciliación.']
        } },
        { t: 'Custodia de mis hijos o régimen de visitas', fin: {
          casos: ['fam_custodia'],
          porque: 'Puedes solicitar orientación y conciliación sobre custodia o visitas ante la autoridad u operador competente, considerando el interés de los niños y cualquier situación de violencia.',
          ruta: ['Presenta la solicitud con tu propuesta.', 'Asiste a la conciliación. Si hay violencia, dilo en la solicitud.']
        } },
        { t: 'Necesito acreditar que soy madre o padre cabeza de familia', fin: {
          casos: ['muj_declaracion_cabeza', 'muj_cabeza_familia'],
          porque: 'La declaración juramentada sirve como prueba; con ella puedes pedir la prioridad en vivienda, educación, empleo y subsidios.',
          ruta: ['Firma la declaración juramentada.', 'Presenta la petición de prioridad a la entidad que corresponda, con la declaración como anexo.']
        } },
        { t: 'Un proceso en el ICBF o en la Comisaría de Familia no avanza', fin: {
          casos: ['pet_icbf'],
          porque: 'Puedes pedir por escrito información del proceso, una cita o que se tomen decisiones a tiempo.',
          ruta: RUTA_PETICION('al ICBF o a la Comisaría')
        } }
      ]
    },
    violencia: {
      pregunta: '¿Qué necesitas ahora?',
      ayuda: 'Si estás en peligro en este momento, llama al 123. La Línea 155 orienta a mujeres las 24 horas y la Línea 141 protege a niños, niñas y adolescentes.',
      opciones: [
        { t: 'Estoy en peligro ahora mismo', fin: {
          casos: ['fam_proteccion', 'muj_denuncia'],
          porque: 'Lo primero es tu seguridad. Después, la medida de protección ordena al agresor alejarse y la denuncia inicia la investigación penal.',
          ruta: ['Llama al 123 o ve a un lugar seguro.', 'Pide la medida de protección en la Comisaría de Familia (atiende de forma urgente).', 'Presenta la denuncia ante la Fiscalía o la Policía.'],
          urgente: 'Llama YA al 123 (Policía). Línea 155: orientación a mujeres, 24 horas. Línea 141: niños, niñas y adolescentes.'
        } },
        { t: 'Quiero que la Comisaría me proteja (medida de protección)', fin: {
          casos: ['fam_proteccion', 'muj_denuncia'],
          porque: 'La medida de protección puede ordenar que el agresor salga de la casa, que no se acerque y otras órdenes para cuidarte a ti y a tus hijos.',
          ruta: ['Presenta la solicitud en la Comisaría de Familia.', 'Puedes presentar al mismo tiempo la denuncia penal.', 'Si no recibes protección y continúa el riesgo, busca atención urgente y orientación sobre los mecanismos para exigirla, incluida una posible tutela.']
        } },
        { t: 'Quiero denunciar penalmente al agresor', fin: {
          casos: ['muj_denuncia', 'fam_proteccion'],
          porque: 'La violencia intrafamiliar, las lesiones, las amenazas y la violencia sexual son delitos. La Fiscalía debe investigar y puede pedir medidas de protección.',
          ruta: ['Presenta la denuncia y pide el número de noticia criminal.', 'Pide también la medida de protección en la Comisaría.'],
          urgente: 'Si hay peligro inmediato, llama al 123.'
        } },
        { t: 'Ya pedí protección y la Comisaría, la Fiscalía o la Policía no hacen nada', fin: {
          casos: ['muj_tutela_proteccion'],
          porque: 'Documenta las solicitudes de protección y las omisiones. Si persiste el riesgo, una tutela puede solicitar la protección de tus derechos; el juez evalúa las medidas que correspondan.',
          ruta: RUTA_TUTELA()
        } }
      ]
    },

    /* ---------------- Municipio ---------------- */
    municipio: {
      pregunta: '¿Con qué asunto del municipio necesitas ayuda?',
      opciones: [
        { t: 'Problemas del barrio o la vereda: vías, alumbrado, basuras, alcantarillado, parques', fin: { casos: ['pet_municipio_servicios'], porque: 'La alcaldía debe responder y actuar. Puedes presentarla en nombre de la comunidad y anexar firmas.', ruta: RUTA_PETICION('a la alcaldía') } },
        { t: 'Ruido, peleas o un vecino que invadió mi predio', fin: { casos: ['pet_municipio_policia'], porque: 'Los problemas de convivencia se resuelven con una querella ante la Inspección de Policía (Código Nacional de Seguridad y Convivencia).', ruta: ['Presenta la querella con fechas, horas y testigos.', 'Asiste a la audiencia que fije el inspector.'] } },
        { t: 'Una multa o comparendo de tránsito (prescripción o fotomulta mal notificada)', fin: { casos: ['pet_municipio_transito'], porque: 'Puedes pedir información del cobro, las notificaciones y la posible prescripción. El análisis exige revisar fechas y hechos que puedan interrumpir o suspender los términos.', ruta: RUTA_PETICION('a la Secretaría de Tránsito') } },
        { t: 'El impuesto predial o deudas viejas con el municipio', fin: { casos: ['pet_municipio_predial'], porque: 'Solicita el estado del cobro y sus actuaciones para verificar si procede la prescripción; no basta contar años sin revisar interrupciones, suspensiones y notificaciones.', ruta: RUTA_PETICION('a la Secretaría de Hacienda') } },
        { t: 'El Sisbén: encuesta, actualización o puntaje', fin: { casos: ['pet_municipio_sisben'], porque: 'La oficina del Sisbén debe hacer la encuesta, actualizar y corregir los datos cuando lo pides.', ruta: RUTA_PETICION('a la oficina del Sisbén') } },
        { t: 'Licencias, estrato, uso del suelo u obras (Planeación)', fin: { casos: ['pet_municipio_planeacion'], porque: 'Identifica si solicitas información o una decisión dentro de un trámite urbanístico: sus términos y requisitos pueden ser distintos.', ruta: RUTA_PETICION('a la Secretaría de Planeación') } },
        { t: 'Me quitaron un subsidio (Renta Ciudadana, Colombia Mayor, Familias en Acción)', fin: { casos: ['pet_prosperidad'], porque: 'Prosperidad Social debe explicarte por qué te suspendieron o retiraron y resolver tu caso.', ruta: RUTA_PETICION('a Prosperidad Social') } },
        { t: 'Quiero información pública: contratos, presupuesto, obras, nómina', fin: { casos: ['pet_info_publica'], porque: 'La información pública es de todos (Ley 1712 de 2014). Deben entregarla en 10 días hábiles.', ruta: RUTA_PETICION('a la entidad', 10) } },
        { t: 'Un funcionario me atendió mal o actuó de forma indebida', fin: { casos: ['pet_queja_funcionario'], porque: 'La queja activa la investigación disciplinaria. Puede presentarse de forma anónima si aportas pruebas.', ruta: ['Presenta la queja a la entidad, a la Personería o a la Procuraduría.', 'Guarda el radicado.'] } },
        { t: 'Necesito copias de un expediente o de documentos míos', fin: { casos: ['pet_copias'], porque: 'Tienes derecho a copias de los documentos que te conciernen. Deben entregarlas en 10 días hábiles.', ruta: RUTA_PETICION('a la entidad', 10) } }
      ]
    },

    /* ---------------- Educación ---------------- */
    educacion: {
      pregunta: '¿Qué pasa con el estudio?',
      opciones: [
        { t: 'No hay cupo, expulsaron al estudiante o no lo dejan estudiar', fin: {
          casos: ['tut_educacion', 'pet_colegio'],
          porque: 'La educación de los niños, niñas y adolescentes es un derecho fundamental: la tutela puede ordenar el cupo o el reintegro.',
          ruta: RUTA_TUTELA()
        } },
        { t: 'No entregan certificados, notas o la matrícula', fin: {
          casos: ['pet_colegio', 'tut_educacion'],
          porque: 'El colegio o la universidad deben responder por escrito. Retener certificados por deudas está limitado por la ley y la Corte.',
          ruta: RUTA_PETICION('al colegio, la universidad o la secretaría de educación')
        } }
      ]
    },

    /* ---------------- Protección y migrantes ---------------- */
    proteccion: {
      pregunta: '¿Cuál es tu situación?',
      opciones: [
        { t: 'Soy víctima del conflicto: registro, ayuda humanitaria o indemnización', fin: {
          casos: ['pet_victimas', 'tut_victimas'],
          porque: 'Puedes pedir el estado de la actuación y revisar el término aplicable. Si persiste una afectación de derechos, evalúa con orientación jurídica los mecanismos disponibles.',
          ruta: RUTA_PETICION('a la Unidad para las Víctimas')
        } },
        { t: 'Me están amenazando de muerte', fin: {
          casos: ['tut_vida_seguridad'],
          porque: 'Documenta las amenazas y las solicitudes de protección. Una tutela puede solicitar medidas para proteger tus derechos, según la urgencia y las circunstancias que valore el juez.',
          ruta: ['Denuncia las amenazas ante la Fiscalía y pide protección a la UNP.', 'Si no actúan, presenta la tutela con medida provisional.'],
          urgente: 'Si estás en peligro inmediato, llama al 123.'
        } },
        { t: 'Soy migrante: PPT, citas o documentos de Migración Colombia', fin: {
          casos: ['pet_migracion'],
          porque: 'Migración Colombia debe responder tus solicitudes por escrito y en los plazos de ley.',
          ruta: RUTA_PETICION('a Migración Colombia')
        } },
        { t: 'Soy migrante y no me atienden en salud o no me dejan estudiar', fin: {
          casos: ['tut_migrantes'],
          porque: 'La Corte Constitucional protege la atención de urgencias para todos y el acceso a la educación de los niños migrantes.',
          ruta: RUTA_TUTELA()
        } }
      ]
    },

    /* ---------------- Seguimiento ---------------- */
    seguimiento: {
      pregunta: '¿Qué documento presentaste?',
      opciones: [
        { t: 'Un derecho de petición y no me han respondido', ir: 'seguimiento_peticion' },
        { t: 'Gané una tutela y la entidad no cumple', fin: {
          casos: ['desacato'],
          porque: 'Revisa exactamente qué se ordenó, a quién y en qué plazo. Puedes solicitar cumplimiento y consultar si procede un incidente de desacato ante el juez competente; la sanción requiere una valoración judicial.',
          ruta: ['Ten a mano el número de radicado y la fecha del fallo.', 'Presenta el desacato ante el mismo juzgado.', 'La referencia es 10 días desde la apertura del incidente, no desde la radicación de tu escrito; pueden existir excepciones justificadas por el juez.']
        } },
        { t: 'Me negaron la tutela, o la concedieron solo en parte', ir: 'impugnar' },
        { t: 'Un reclamo a Datacrédito, TransUnion o la entidad que me reportó', fin: {
          casos: ['tut_habeas_data'],
          porque: 'Verifica el reclamo previo, la respuesta y una posible prórroga: el término ordinario es 15 días hábiles y puede ampliarse hasta 8 más con aviso motivado. La tutela depende de sus requisitos y de la afectación concreta.',
          ruta: RUTA_TUTELA()
        } },
        { t: 'Un juzgado o la Fiscalía no mueven mi proceso o mi denuncia', fin: {
          casos: ['pet_juzgado'],
          porque: 'Puedes pedir por escrito información del proceso, copias o que se impulse.',
          ruta: RUTA_PETICION('al juzgado o a la Fiscalía')
        } }
      ]
    },
    seguimiento_peticion: {
      pregunta: '¿Ya se cumplió el plazo para responder?',
      ayuda: '15 días hábiles en general; 10 si pediste copias o información; 30 si era una consulta. No se cuentan sábados, domingos ni festivos.',
      opciones: [
        { t: 'Sí, ya pasó el plazo y no responden', fin: {
          casos: ['tut_peticion'],
          porque: 'Una tutela puede pedir protección del derecho de petición cuando falta una respuesta de fondo dentro del término aplicable. El juez determina si procede y qué orden impartir.',
          ruta: RUTA_TUTELA(['Anexa tu copia de la petición con el sello, el radicado o el correo enviado: es la prueba principal.'])
        } },
        { t: 'Todavía no se cumple el plazo', fin: {
          casos: ['tut_peticion'],
          porque: 'Revisa primero el término aplicable y cualquier circunstancia especial. Si hay riesgo urgente para otros derechos, solicita orientación sin esperar automáticamente a que termine el contador.',
          ruta: ['Usa la calculadora de plazos (Guía) o registra la fecha en "Mis documentos" para saber cuándo vence.', 'Si falta respuesta al vencer el término aplicable, revisa si corresponde tutela por petición y qué pruebas aportar.'],
          plazo: 'Para una falta de respuesta revisa el término aplicable; las situaciones urgentes y otros derechos requieren analizar su propia vía de protección.'
        } },
        { t: 'Me respondieron, pero no resuelve lo que pedí (evasiva o "en trámite")', fin: {
          casos: ['tut_peticion'],
          porque: 'Una respuesta debe atender de fondo lo solicitado. Distingue una contestación incompleta de un aviso de prórroga permitido; conserva la comunicación para evaluar qué mecanismo corresponde.',
          ruta: RUTA_TUTELA()
        } }
      ]
    },
    impugnar: {
      pregunta: '¿Hace cuánto te notificaron el fallo?',
      opciones: [
        { t: 'Hace 3 días hábiles o menos', fin: {
          casos: ['impugnacion'],
          porque: 'La impugnación hace que un juez superior revise el fallo.',
          ruta: ['Explica por qué el juez se equivocó y anexa pruebas nuevas si las tienes.', 'Preséntala ante el mismo juez que falló.', 'El término de referencia de segunda instancia es 20 días desde la recepción del expediente por el superior, no desde el envío de tu impugnación.'],
          plazo: 'Preséntala hoy si puedes: solo hay 3 días hábiles desde la notificación.'
        } },
        { t: 'Ya pasaron más de 3 días hábiles', fin: {
          casos: [],
          porque: 'La fecha de notificación efectiva y sus constancias son esenciales. Busca orientación de inmediato para revisar el cómputo y las opciones; presentar otra tutela por el mismo asunto puede generar problemas procesales.',
          ruta: ['Acude a la Personería, a la Defensoría del Pueblo o a un consultorio jurídico.', 'Explica cualquier hecho nuevo y entrega el fallo previo a quien te oriente; no presupongas que una nueva tutela es admisible.'],
          ayuda: true
        } }
      ]
    },

    /* ---------------- Decisiones en contra ---------------- */
    decision: {
      pregunta: '¿Quién tomó la decisión?',
      opciones: [
        { t: 'Una entidad pública (alcaldía, tránsito, Colpensiones, una secretaría o un ministerio)', ir: 'decision_plazo' },
        { t: 'La empresa de servicios públicos respondió mi reclamo en contra', fin: {
          casos: ['rec_spd'],
          porque: 'Revisa el servicio y si la decisión admite reposición y apelación subsidiaria. La autoridad de apelación es Superservicios para servicios domiciliarios y la SIC para comunicaciones.',
          ruta: ['Presenta el recurso a la empresa.', 'La respuesta tiene un término ordinario de 15 días hábiles. Antes de invocar silencio favorable, revisa si hubo pruebas, prórrogas u otras circunstancias previstas en el régimen aplicable.'],
          plazo: 'Referencia: 5 días hábiles para servicios domiciliarios; 10 para internet, telefonía o televisión. Verifica la fecha efectiva de conocimiento o comunicación de la decisión.'
        } },
        { t: 'Me sancionaron o me cobran sin haberme notificado ni dejarme defender', fin: {
          casos: ['tut_debido_proceso', 'rec_reposicion'],
          porque: 'Nadie puede ser sancionado sin ser notificado y sin poder defenderse (debido proceso). Si no te notificaron, el plazo de los recursos no ha empezado a correr.',
          ruta: ['Si aún puedes, presenta los recursos diciendo que no te notificaron en debida forma.', 'Si no tienes otro medio eficaz, presenta la tutela por debido proceso.']
        } },
        { t: 'Un juez, dentro de un proceso (que no es de tutela)', fin: {
          casos: ['pet_juzgado'],
          porque: 'Los recursos dentro de los procesos judiciales tienen plazos muy cortos y, en la mayoría de los casos, requieren abogado.',
          ruta: ['Pide información del proceso si la necesitas.', 'Busca hoy mismo ayuda gratuita: los plazos para recurrir son de pocos días.'],
          ayuda: true
        } }
      ]
    },
    decision_plazo: {
      pregunta: '¿Hace cuánto te notificaron la decisión?',
      opciones: [
        { t: 'Hace 10 días hábiles o menos', fin: {
          casos: ['rec_reposicion'],
          porque: 'Con el recurso de reposición la misma entidad revisa su decisión; con la apelación la revisa su superior.',
          ruta: ['Presenta el recurso explicando por qué la decisión está mal y anexa pruebas.', 'Si no hay decisión, revisa con orientación jurídica el silencio administrativo: el referente de 2 meses del CPACA tiene reglas y suspensiones, incluida la práctica de pruebas.'],
          plazo: 'Tienes 10 días hábiles desde la notificación.'
        } },
        { t: 'Ya pasaron más de 10 días hábiles', fin: {
          casos: ['tut_debido_proceso', 'pet_general'],
          porque: 'El plazo de los recursos ya venció. Si nunca te notificaron en debida forma, el plazo no ha empezado a correr. Si la decisión viola un derecho fundamental y no tienes otro medio eficaz, puede proceder la tutela por debido proceso. También puedes pedir por escrito la revocatoria de la decisión.',
          ruta: ['Busca orientación: la Personería y los consultorios jurídicos ayudan gratis.', 'Presenta la tutela por debido proceso si te sancionaron sin dejarte defender.'],
          ayuda: true
        } }
      ]
    },

    /* ---------------- Consumo ---------------- */
    consumo: {
      pregunta: '¿Qué pasó con la compra o el servicio?',
      opciones: [
        { t: 'Un producto salió malo y no me responden por la garantía', fin: {
          casos: ['queja_consumidor'],
          porque: 'Revisa la garantía aplicable y presenta la reclamación directa al vendedor o productor. El término ordinario de respuesta es 15 días hábiles; conserva la prueba de presentación.',
          ruta: ['Presenta la reclamación directa con la factura.', 'Si no hay solución, revisa los requisitos y la competencia para una acción de protección al consumidor. La posibilidad de actuar sin abogado depende de las reglas de cuantía y postulación.']
        } },
        { t: 'Publicidad engañosa o me cobraron de más', fin: {
          casos: ['queja_consumidor'],
          porque: 'La Ley 1480 de 2011 te protege frente a la publicidad engañosa y los cobros indebidos.',
          ruta: ['Presenta la reclamación directa al vendedor.', 'Guarda la publicidad, la factura y los mensajes.']
        } },
        { t: 'Un banco, una aseguradora o un fondo', fin: {
          casos: ['queja_financiera', 'pet_banco'],
          porque: 'Las entidades financieras tienen un Defensor del Consumidor Financiero que debe atender tu queja gratis.',
          ruta: ['Presenta la queja al Defensor del Consumidor Financiero de la entidad.', 'Si no te resuelven, acude a la Superintendencia Financiera.']
        } },
        { t: 'Una empresa de servicios públicos, internet o celular', fin: {
          casos: ['pet_spd'],
          porque: 'Primero se reclama a la empresa; tiene 15 días hábiles para responder.',
          ruta: ['Presenta el reclamo y guarda el radicado o el CUN.', 'Si responde en contra, presenta el recurso a tiempo.']
        } }
      ]
    },

    /* ---------------- Contratos ---------------- */
    contratos: {
      pregunta: '¿Qué documento necesitas firmar?',
      opciones: [
        { t: 'Arrendar una casa, un apartamento o una habitación', fin: { casos: ['con_arriendo_vivienda'], porque: 'El contrato de arrendamiento de vivienda está regulado por la Ley 820 de 2003; por escrito evita problemas con el canon, los servicios y la entrega.', ruta: ['Llena los datos de las dos partes y del inmueble.', 'Imprime dos copias y fírmenlas.'] } },
        { t: 'Problemas con el arrendador o el arrendatario (depósito, reparaciones, entrega)', fin: { casos: ['pet_arrendador'], porque: 'Primero se reclama por escrito: deja constancia y abre la puerta a la conciliación.', ruta: ['Presenta la reclamación y guarda la constancia de entrega.', 'Si no hay solución, acude a conciliación en una Casa de Justicia.'] } },
        { t: 'Vender o comprar un carro o una moto', fin: { casos: ['con_compraventa_vehiculo'], porque: 'El contrato deja claros el precio, la entrega y quién hace el traspaso ante tránsito.', ruta: ['Llena el contrato con los datos de la tarjeta de propiedad.', 'Firmen y hagan el traspaso en el organismo de tránsito.'] } },
        { t: 'Vender o comprar otra cosa (celular, muebles, animales, maquinaria)', fin: { casos: ['con_compraventa_bien'], porque: 'Un contrato sencillo prueba la compra, el precio y el estado del bien.', ruta: ['Llena el contrato y fírmenlo las dos partes.'] } },
        { t: 'Contratar a una empleada o un empleado doméstico', fin: { casos: ['con_servicio_domestico'], porque: 'El contrato escrito protege a las dos partes.', ruta: ['Llena el contrato.', 'Afilia a la persona a la seguridad social.'] } },
        { t: 'Prestar plata (pagaré) o acordar cómo pagar una deuda', fin: { casos: ['con_pagare', 'con_acuerdo_pago'], porque: 'El pagaré es un título valor que permite cobrar si no pagan; el acuerdo de pago organiza una deuda en cuotas.', ruta: ['Escoge el documento y fírmenlo las dos partes.'] } },
        { t: 'Dejar constancia de un pago o un paz y salvo', fin: { casos: ['con_recibo'], porque: 'El recibo prueba que pagaste.', ruta: ['Llena el recibo y que lo firme quien recibe el dinero.'] } },
        { t: 'Autorizar a otra persona para que haga un trámite por mí (poder)', fin: { casos: ['con_poder'], porque: 'El poder especial autoriza a otra persona para un trámite concreto. Algunas entidades exigen autenticarlo en notaría.', ruta: ['Llena el poder con el trámite y la entidad.', 'Fírmalo; si la entidad lo pide, autentícalo en notaría.'] } }
      ]
    },

    /* ---------------- Otros ---------------- */
    otro: {
      pregunta: '¿Qué necesitas?',
      opciones: [
        { t: 'Pedirle algo a una entidad o empresa (información, una respuesta, un servicio, una decisión)', fin: {
          casos: ['pet_general'],
          porque: 'El derecho de petición sirve para pedir cualquier cosa respetuosa a entidades públicas y a muchas privadas, que deben responder de fondo.',
          ruta: RUTA_PETICION('a la entidad')
        } },
        { t: 'Una entidad o una persona viola un derecho fundamental y no encuentro mi caso', fin: {
          casos: ['tut_general'],
          porque: 'La tutela general sirve para proteger cualquier derecho fundamental cuando no hay otro medio eficaz.',
          ruta: RUTA_TUTELA()
        } },
        { t: 'Quiero que una persona me ayude gratis', fin: {
          casos: [],
          porque: AYUDA_GRATIS,
          ruta: ['Busca la Personería en la alcaldía de tu municipio.', 'Consulta los canales oficiales de la Defensoría del Pueblo para tu región.', 'Pregunta en la facultad de derecho de una universidad cercana por el consultorio jurídico.'],
          ayuda: true
        } }
      ]
    }
  };

  /* Revisa que todas las respuestas lleven a una pregunta existente o a casos activos */
  function validar(casos) {
    const ids = new Set((casos || AJ.casos || []).filter(c => !c.retirado).map(c => c.id));
    const errores = [];
    const alcanzados = new Set(['inicio']);
    const pendientes = ['inicio'];
    while (pendientes.length) {
      const id = pendientes.pop();
      const n = nodos[id];
      if (!n) { errores.push(`Falta la pregunta "${id}"`); continue; }
      if (!n.opciones || !n.opciones.length) errores.push(`La pregunta "${id}" no tiene opciones`);
      (n.opciones || []).forEach((o, i) => {
        if (o.ir) { if (!alcanzados.has(o.ir)) { alcanzados.add(o.ir); pendientes.push(o.ir); } if (!nodos[o.ir]) errores.push(`"${id}" opción ${i + 1} lleva a "${o.ir}", que no existe`); }
        else if (o.fin) {
          (o.fin.casos || []).forEach(c => { if (!ids.has(c)) errores.push(`"${id}" opción ${i + 1} recomienda "${c}", que no existe o está retirado`); });
          if (!o.fin.casos.length && !o.fin.ayuda) errores.push(`"${id}" opción ${i + 1} no recomienda nada`);
        } else errores.push(`"${id}" opción ${i + 1} no lleva a ningún lado`);
      });
    }
    Object.keys(nodos).forEach(id => { if (!alcanzados.has(id)) errores.push(`La pregunta "${id}" no se puede alcanzar`); });
    return errores;
  }

  return { nodos, validar, AYUDA_GRATIS };
})();
