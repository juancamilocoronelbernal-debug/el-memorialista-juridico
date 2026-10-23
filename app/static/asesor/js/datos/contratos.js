/* ============================================================
   contratos.js — Contratos y documentos privados más usados en
   Colombia (al estilo de las hojas Minerva): arrendamiento de
   vivienda, compraventa de vehículo y de bienes, servicio
   doméstico, pagaré, poder, acuerdo de pago y recibo.

   Los casos marcados con `retirado: true` (promesa de compraventa
   de inmueble, arrendamiento de local comercial, contrato de
   trabajo general y prestación de servicios) se conservan en el
   código pero no se muestran: el catálogo se concentra en
   orientación ciudadana y no reemplaza el trabajo de los abogados en
   negocios entre particulares; se concentra en documentos que
   protegen a la población vulnerable. Para reactivar uno, basta
   quitar la marca.
   ============================================================ */
window.AJ = window.AJ || {};
AJ.casos = AJ.casos || [];

(function () {
  const R = AJ.red;
  const cd = (c, f) => AJ.camposDe(c, f);
  const hoyISO = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
  const fechaFirma = () => ({ id: 'fechaFirma', tipo: 'fecha', etiqueta: 'Fecha en que se firma', valorInicial: hoyISO(), ancho: 'media' });
  const num = v => Number(String(v == null ? '' : v).replace(/[^\d]/g, '')) || 0;
  const pct = (v, p) => R.moneda(Math.round(num(v) * p));
  const diaMes = d => d ? `dentro de los primeros ${R.numeroLetras(d)} días de cada mes` : 'dentro de los primeros cinco (5) días de cada mes';
  const notif = (P) => ({ t: 'NOTIFICACIONES', c: `Las partes recibirán comunicaciones en las direcciones, teléfonos y correos electrónicos indicados al pie de sus firmas, y se obligan a informar por escrito cualquier cambio.` });
  const controversias = () => ({ t: 'SOLUCIÓN DE CONTROVERSIAS', c: 'Toda diferencia derivada de este contrato se intentará resolver primero de manera directa y, de no lograrse, mediante conciliación ante un centro de conciliación o una Casa de Justicia, antes de acudir a la justicia ordinaria.' });
  const merito = (que) => ({ t: 'MÉRITO EJECUTIVO', c: `Este documento presta mérito ejecutivo para el cobro de ${que || 'las sumas que se adeuden en virtud del mismo'}, sin necesidad de requerimiento previo, al que las partes renuncian expresamente.` });

  AJ.casos.push(
  /* ---------------- ARRENDAMIENTO DE VIVIENDA ---------------- */
  {
    id: 'con_arriendo_vivienda', tipo: 'contrato', categoria: 'particular',
    titulo: 'Contrato de arrendamiento de vivienda (casa, apartamento o habitación)',
    resumen: 'El contrato de arriendo de vivienda urbana según la Ley 820 de 2003: canon, duración, servicios, inventario, reparaciones, prohibición de depósitos y reglas de terminación. Sirve para arrendador y arrendatario.',
    palabras: ['arriendo', 'arrendamiento', 'vivienda', 'casa', 'apartamento', 'habitación', 'pieza', 'inquilino', 'arrendador', 'arrendatario', 'canon', 'contrato de arriendo', 'minerva 10-01'],
    tituloDoc: 'CONTRATO DE ARRENDAMIENTO DE VIVIENDA URBANA', nombreContrato: 'contrato de arrendamiento de vivienda urbana',
    roles: { a: 'EL ARRENDADOR', b: 'EL ARRENDATARIO' },
    rolCampo: { opciones: [ { v: 'a', t: 'Soy el arrendador (dueño o quien entrega el inmueble en arriendo)' }, { v: 'b', t: 'Soy el arrendatario (quien va a vivir en el inmueble y paga el arriendo)' } ] },
    campos: [
      { id: 'tipoInmueble', tipo: 'select', etiqueta: '¿Qué se arrienda?', requerido: true, opciones: [ { v: 'casa', t: 'Una casa', legal: 'la casa' }, { v: 'apartamento', t: 'Un apartamento', legal: 'el apartamento' }, { v: 'apartaestudio', t: 'Un apartaestudio', legal: 'el apartaestudio' }, { v: 'habitacion', t: 'Una habitación o pieza', legal: 'la habitación' }, { v: 'rural', t: 'Una vivienda en finca o zona rural', legal: 'la vivienda' } ], ancho: 'media' },
      { id: 'direccionInmueble', tipo: 'texto', etiqueta: 'Dirección completa del inmueble', ejemplo: 'Ej.: Calle 45 # 60-21, apartamento 301, barrio El Porvenir', requerido: true, ancho: 'media' },
      { id: 'ciudadInmueble', tipo: 'texto', etiqueta: 'Ciudad o municipio del inmueble', requerido: true, ancho: 'media' },
      { id: 'descripcion', tipo: 'texto', etiqueta: '¿Qué incluye? (habitaciones, baños, cocina, patio, parqueadero, muebles)', ejemplo: 'Ej.: 3 habitaciones, 2 baños, cocina integral, patio y parqueadero cubierto', ancho: 'media' },
      { id: 'canon', tipo: 'texto', etiqueta: 'Valor del arriendo mensual (canon)', ejemplo: 'Ej.: 950.000', requerido: true, ancho: 'media' },
      { id: 'diaPago', tipo: 'texto', etiqueta: 'Se paga dentro de los primeros ___ días de cada mes', ejemplo: 'Ej.: 5', ancho: 'media' },
      { id: 'medioPago', tipo: 'texto', etiqueta: '¿Cómo se paga?', ejemplo: 'Ej.: Consignación a la cuenta de ahorros Bancolombia 123-456789-00 / en efectivo contra recibo', ancho: 'completa' },
      { id: 'fechaInicio', tipo: 'fecha', etiqueta: 'Fecha en que empieza el arriendo', requerido: true, ancho: 'media' },
      { id: 'duracionMeses', tipo: 'select', etiqueta: 'Duración', opciones: [ { v: '6', t: '6 meses' }, { v: '12', t: '12 meses (lo usual)' }, { v: '24', t: '24 meses' }, { v: '36', t: '36 meses' } ], valorInicial: '12', ancho: 'media' },
      { id: 'servicios', tipo: 'radio', etiqueta: 'Servicios públicos (agua, luz, gas, internet)', requerido: true, opciones: [ { v: 'arrendatario', t: 'Los paga el arrendatario aparte del arriendo' }, { v: 'incluidos', t: 'Están incluidos en el arriendo' }, { v: 'mixto', t: 'Algunos incluidos y otros aparte (explica abajo)' } ] },
      { id: 'serviciosDetalle', tipo: 'texto', etiqueta: '¿Cuáles incluidos y cuáles aparte?', ejemplo: 'Ej.: agua y administración incluidas; luz, gas e internet los paga el arrendatario', mostrarSi: { campo: 'servicios', valor: 'mixto' }, ancho: 'completa' },
      { id: 'personas', tipo: 'texto', etiqueta: '¿Quiénes van a vivir en el inmueble?', ejemplo: 'Ej.: el arrendatario, su esposa y dos hijos', ancho: 'completa' },
      { id: 'coarrendatario', tipo: 'texto', etiqueta: 'Codeudor o coarrendatario (nombre y cédula), si lo hay', ejemplo: 'Ej.: Luis Ángel Pérez, C.C. 71.234.567', ancho: 'completa' },
      { id: 'inventario', tipo: 'textarea', etiqueta: 'Estado e inventario del inmueble al entregarlo (paredes, pisos, chapas, muebles, electrodomésticos)', ejemplo: 'Ej.:\nPintura en buen estado; chapa de la puerta principal nueva; estufa de 4 puestos marca Haceb en buen estado; calentador a gas funcionando.', filas: 3 }
    ],
    opcionales: [
      { v: 'mascotas', t: 'Se permiten mascotas', clausula: { t: 'MASCOTAS', c: 'EL ARRENDADOR autoriza la tenencia de mascotas domésticas en el inmueble, siempre que EL ARRENDATARIO responda por los daños que causen y cumpla el reglamento de propiedad horizontal y las normas de convivencia.' } },
      { v: 'nomascotas', t: 'No se permiten mascotas', clausula: { t: 'MASCOTAS', c: 'No se permite la tenencia de animales en el inmueble, salvo autorización escrita posterior de EL ARRENDADOR.' } },
      { v: 'visitas', t: 'El arrendador puede mostrar el inmueble en el último mes', clausula: { t: 'VISITAS', c: 'Durante el último mes de vigencia del contrato, EL ARRENDATARIO permitirá visitas al inmueble para su arrendamiento o venta, en horarios acordados previamente y con un máximo de tres visitas por semana.' } },
      { v: 'mejoras', t: 'El arrendatario puede hacer mejoras con autorización', clausula: { t: 'MEJORAS', c: 'EL ARRENDATARIO podrá realizar mejoras o adecuaciones con autorización previa y escrita de EL ARRENDADOR. Las mejoras que se adhieran al inmueble quedarán a favor de este sin lugar a indemnización, salvo acuerdo escrito en contrario.' } },
      { v: 'garantia', t: 'Hay fianza o póliza de arrendamiento (afianzadora)', clausula: d => ({ t: 'GARANTÍA', c: 'Las obligaciones de EL ARRENDATARIO están respaldadas por la fianza o póliza de arrendamiento indicada en documento aparte, cuyo costo asume la parte que allí se indique. En ningún caso se exigen depósitos en dinero ni cauciones reales, conforme al artículo 16 de la Ley 820 de 2003.' }) }
    ],
    clausulas: (d, P) => {
      const inm = `${R.opcionTexto(cd('con_arriendo_vivienda', 'tipoInmueble'), d.tipoInmueble)} ubicad${d.tipoInmueble === 'casa' || d.tipoInmueble === 'habitacion' || d.tipoInmueble === 'rural' ? 'a' : 'o'} en ${d.direccionInmueble || '[dirección]'}, ${d.ciudadInmueble || '[ciudad]'}`;
      const meses = R.numeroLetras(d.duracionMeses || 12);
      const serv = d.servicios === 'incluidos' ? 'Los servicios públicos domiciliarios del inmueble están incluidos en el canon y serán pagados por EL ARRENDADOR.' : d.servicios === 'mixto' ? `Servicios públicos: ${R.oracion(d.serviciosDetalle || 'según lo acordado')} Los que corresponden a EL ARRENDATARIO deberán pagarse oportunamente, y su no pago es causal de terminación del contrato.` : 'Los servicios públicos domiciliarios (acueducto, alcantarillado, energía, gas, aseo, internet y televisión) serán pagados oportunamente por EL ARRENDATARIO a partir de la fecha de entrega, quien devolverá el inmueble a paz y salvo por estos conceptos. EL ARRENDADOR no responde por la suspensión de los servicios causada por el no pago de EL ARRENDATARIO.';
      const c = [
        { t: 'OBJETO', c: `EL ARRENDADOR entrega a EL ARRENDATARIO, a título de arrendamiento, ${inm}${d.descripcion ? `, que comprende: ${d.descripcion}` : ''}, para que lo use y disfrute en las condiciones de este contrato.` },
        { t: 'DESTINACIÓN', c: `El inmueble se destinará exclusivamente a vivienda de EL ARRENDATARIO${d.personas ? ` y de las siguientes personas: ${d.personas}` : ' y su familia'}. Cualquier cambio de destinación requiere autorización escrita de EL ARRENDADOR y es causal de terminación del contrato (artículo 22 de la Ley 820 de 2003).` },
        { t: 'CANON', c: `El precio mensual del arrendamiento es de ${R.pesos(d.canon)}, que EL ARRENDATARIO pagará por anticipado ${diaMes(d.diaPago)}${d.medioPago ? `, mediante ${d.medioPago}` : ''}. EL ARRENDADOR entregará comprobante de cada pago (artículo 12 de la Ley 820 de 2003). El valor del canon no supera el uno por ciento (1 %) del valor comercial del inmueble, conforme al artículo 18 de la misma ley.` },
        { t: 'DURACIÓN', c: `El contrato tendrá una duración de ${meses} meses, contados a partir del ${R.fechaLarga(d.fechaInicio) || '[fecha de inicio]'}. Se prorrogará automáticamente por períodos iguales, siempre que las partes hayan cumplido sus obligaciones y EL ARRENDATARIO acepte el reajuste del canon (artículo 6 de la Ley 820 de 2003).` },
        { t: 'REAJUSTE DEL CANON', c: 'Cada doce (12) meses de vigencia el canon se incrementará en un porcentaje que no podrá superar el cien por ciento (100 %) del incremento del índice de precios al consumidor (IPC) del año calendario anterior, conforme al artículo 20 de la Ley 820 de 2003. EL ARRENDADOR informará por escrito el nuevo valor.' },
        { t: 'SERVICIOS PÚBLICOS', c: serv },
        { t: 'ENTREGA E INVENTARIO', c: `EL ARRENDADOR entrega el inmueble en buen estado de servicio, seguridad y sanidad, con las instalaciones y accesorios que se describen en el inventario que hace parte de este contrato${d.inventario ? `: ${R.oracion(d.inventario)}` : '.'} EL ARRENDATARIO lo recibe a satisfacción y se obliga a devolverlo en el mismo estado, salvo el deterioro natural por el uso normal y el paso del tiempo.` },
        { t: 'REPARACIONES', c: 'Las reparaciones locativas (daños causados por el uso: chapas, vidrios, pintura, destapes menores, grifería) son a cargo de EL ARRENDATARIO. Las reparaciones necesarias para conservar el inmueble (estructura, techos, tuberías, instalaciones eléctricas y daños no imputables al uso) son a cargo de EL ARRENDADOR, quien las atenderá dentro de un plazo razonable después de ser avisado por escrito (artículos 1985, 1993 y 1998 del Código Civil y artículos 8 y 9 de la Ley 820 de 2003).' },
        { t: 'PROHIBICIONES', c: 'EL ARRENDATARIO no podrá subarrendar ni ceder el contrato en todo o en parte, cambiar la destinación del inmueble, almacenar sustancias peligrosas ni realizar modificaciones estructurales, salvo autorización escrita de EL ARRENDADOR (artículo 17 de la Ley 820 de 2003). Cumplirá el reglamento de propiedad horizontal y las normas de convivencia.' },
        { t: 'DEPÓSITOS', c: 'Conforme al artículo 16 de la Ley 820 de 2003, EL ARRENDADOR no exige ni recibe depósitos en dinero efectivo ni cauciones reales para garantizar las obligaciones de este contrato.' }
      ];
      if (d.coarrendatario) c.push({ t: 'DEUDOR SOLIDARIO', c: `${R.mayus(d.coarrendatario)} se obliga solidariamente con EL ARRENDATARIO al pago del canon, los servicios públicos, las reparaciones locativas y las demás obligaciones de este contrato, incluso durante sus prórrogas, y firma en señal de aceptación.` });
      c.push(
        { t: 'TERMINACIÓN', c: 'Son causales de terminación las previstas en los artículos 22 a 24 de la Ley 820 de 2003, entre ellas: el no pago del canon o de los servicios públicos, el subarriendo o la cesión no autorizados, el cambio de destinación y la perturbación de la tranquilidad de los vecinos. Cualquiera de las partes podrá dar por terminado el contrato unilateralmente durante su vigencia con aviso escrito con tres (3) meses de anticipación y el pago de una indemnización equivalente a tres (3) cánones; y a la fecha de vencimiento del período inicial o de sus prórrogas, con aviso escrito de tres (3) meses, sin indemnización, en los casos que la ley autoriza.' },
        { t: 'CLÁUSULA PENAL', c: `El incumplimiento de cualquiera de las obligaciones de este contrato dará lugar al pago de una suma equivalente a dos (2) cánones de arrendamiento (${pct(d.canon, 2)}) a título de pena, sin perjuicio de que la parte cumplida exija el cumplimiento o la terminación del contrato y el pago de los perjuicios.` },
        { t: 'RESTITUCIÓN', c: 'Al terminar el contrato, EL ARRENDATARIO entregará el inmueble desocupado, en el estado descrito en el inventario, con los servicios públicos a paz y salvo y con las llaves, y las partes firmarán acta de entrega. Si EL ARRENDADOR se niega a recibir, EL ARRENDATARIO podrá entregar el inmueble conforme al artículo 2035 del Código Civil y al artículo 384 del Código General del Proceso.' },
        merito('los cánones, servicios públicos, cláusula penal y demás sumas que se adeuden'),
        controversias(),
        notif(P)
      );
      return c;
    },
    guia: { nota: 'No se puede exigir ni pagar depósito en dinero (artículo 16 de la Ley 820 de 2003). El arrendador sí puede pedir codeudor o póliza de arrendamiento.', pasos: ['Imprimir dos copias y firmarlas las dos partes (y el codeudor, si lo hay). Cada parte guarda una.', 'Hacer el inventario con fotos el día de la entrega y firmarlo: evita peleas al final.', 'Autenticar las firmas en notaría es opcional, pero recomendable para que el contrato sirva como prueba fuerte.', 'Pedir siempre recibo de cada pago del arriendo.', 'El aumento del canon solo cada 12 meses y máximo el IPC del año anterior.'] }
  },

  /* ---------------- ARRENDAMIENTO DE LOCAL COMERCIAL ---------------- */
  {
    id: 'con_arriendo_local', tipo: 'contrato', categoria: 'particular', retirado: true,
    titulo: 'Contrato de arrendamiento de local comercial u oficina',
    resumen: 'Para tiendas, oficinas, bodegas o consultorios: canon, duración, destinación, derecho de renovación y desahucio según el Código de Comercio (artículos 518 a 524).',
    palabras: ['local', 'local comercial', 'oficina', 'bodega', 'consultorio', 'negocio', 'tienda', 'arriendo comercial', 'arrendamiento', 'minerva 10-02', 'renovación', 'desahucio'],
    tituloDoc: 'CONTRATO DE ARRENDAMIENTO DE LOCAL COMERCIAL', nombreContrato: 'contrato de arrendamiento de inmueble para uso comercial',
    roles: { a: 'EL ARRENDADOR', b: 'EL ARRENDATARIO' },
    rolCampo: { opciones: [ { v: 'a', t: 'Soy el arrendador (dueño del local)' }, { v: 'b', t: 'Soy el arrendatario (quien va a usar el local para su negocio)' } ] },
    campos: [
      { id: 'direccionInmueble', tipo: 'texto', etiqueta: 'Dirección completa del local', requerido: true, ancho: 'media' },
      { id: 'ciudadInmueble', tipo: 'texto', etiqueta: 'Ciudad o municipio', requerido: true, ancho: 'media' },
      { id: 'descripcion', tipo: 'texto', etiqueta: 'Descripción (área, baños, bodega, vitrinas, parqueaderos)', ejemplo: 'Ej.: local de 45 m² con baño, mezanine y reja metálica', ancho: 'completa' },
      { id: 'actividad', tipo: 'texto', etiqueta: '¿Para qué negocio se va a usar?', ejemplo: 'Ej.: peluquería / tienda de ropa / oficina de contaduría', requerido: true, ancho: 'completa' },
      { id: 'canon', tipo: 'texto', etiqueta: 'Canon mensual', requerido: true, ancho: 'media' },
      { id: 'diaPago', tipo: 'texto', etiqueta: 'Se paga dentro de los primeros ___ días de cada mes', ejemplo: 'Ej.: 5', ancho: 'media' },
      { id: 'fechaInicio', tipo: 'fecha', etiqueta: 'Fecha de inicio', requerido: true, ancho: 'media' },
      { id: 'duracionMeses', tipo: 'select', etiqueta: 'Duración', opciones: [ { v: '12', t: '12 meses' }, { v: '24', t: '24 meses' }, { v: '36', t: '36 meses' }, { v: '60', t: '60 meses' } ], valorInicial: '12', ancho: 'media' },
      { id: 'incremento', tipo: 'texto', etiqueta: 'Incremento anual acordado', ejemplo: 'Ej.: IPC del año anterior + 2 puntos / 8 %', valorInicial: 'el IPC del año anterior', ancho: 'media' },
      { id: 'administracion', tipo: 'texto', etiqueta: 'Cuota de administración (si hay) y quién la paga', ejemplo: 'Ej.: 180.000 mensuales, a cargo del arrendatario', ancho: 'media' },
      { id: 'inventario', tipo: 'textarea', etiqueta: 'Estado e inventario del local al entregarlo', filas: 2 }
    ],
    opcionales: [
      { v: 'adecuaciones', t: 'El arrendatario puede hacer adecuaciones no estructurales', clausula: { t: 'ADECUACIONES', c: 'EL ARRENDATARIO podrá realizar adecuaciones no estructurales necesarias para su actividad (avisos, divisiones livianas, pintura, instalaciones), previo aviso escrito a EL ARRENDADOR, obteniendo los permisos requeridos y dejando el local, al terminar, en el estado en que lo recibió o en mejor estado si EL ARRENDADOR acepta las mejoras, sin lugar a indemnización.' } },
      { v: 'gracia', t: 'Hay un período de gracia sin canon para adecuar el local', clausula: d => ({ t: 'PERÍODO DE GRACIA', c: 'Durante el primer mes de vigencia EL ARRENDATARIO no pagará canon, en consideración a las adecuaciones que realizará en el local; los servicios públicos de ese período sí serán a su cargo.' }) },
      { v: 'horario', t: 'Horario de funcionamiento restringido por el edificio o centro comercial', clausula: { t: 'HORARIO Y REGLAMENTO', c: 'EL ARRENDATARIO cumplirá el reglamento de propiedad horizontal o del centro comercial y los horarios de funcionamiento allí establecidos, cuyo texto declara conocer.' } }
    ],
    clausulas: (d, P) => [
      { t: 'OBJETO', c: `EL ARRENDADOR entrega a EL ARRENDATARIO, a título de arrendamiento, el inmueble ubicado en ${d.direccionInmueble || '[dirección]'}, ${d.ciudadInmueble || '[ciudad]'}${d.descripcion ? `, que comprende: ${d.descripcion}` : ''}.` },
      { t: 'DESTINACIÓN', c: `El inmueble se destinará exclusivamente a la actividad comercial de ${d.actividad || '[actividad]'}. EL ARRENDATARIO obtendrá a su costa los permisos, licencias y registros que exija la ley para su funcionamiento y responderá por las sanciones que se deriven de su actividad. El cambio de destinación requiere autorización escrita de EL ARRENDADOR.` },
      { t: 'CANON', c: `El canon mensual es de ${R.pesos(d.canon)}, pagadero por anticipado ${diaMes(d.diaPago)} en la cuenta o lugar que indique EL ARRENDADOR, quien expedirá el comprobante correspondiente.` },
      { t: 'DURACIÓN Y RENOVACIÓN', c: `El contrato durará ${R.numeroLetras(d.duracionMeses || 12)} meses contados desde el ${R.fechaLarga(d.fechaInicio) || '[fecha]'}, prorrogables por períodos iguales salvo aviso escrito en contrario. Las partes reconocen el derecho de renovación de EL ARRENDATARIO que haya ocupado el inmueble por dos (2) años o más con un mismo establecimiento de comercio, y las causales y el desahucio de seis (6) meses previstos en los artículos 518 a 524 del Código de Comercio, normas de orden público que no pueden desconocerse.` },
      { t: 'INCREMENTO', c: `Al cumplirse cada año de vigencia el canon se incrementará en ${d.incremento || 'el IPC del año anterior'}.` },
      { t: 'SERVICIOS Y ADMINISTRACIÓN', c: `Los servicios públicos del local serán pagados por EL ARRENDATARIO desde la fecha de entrega${d.administracion ? `. Cuota de administración: ${d.administracion}` : ''}. Al terminar el contrato entregará los paz y salvos correspondientes.` },
      { t: 'ENTREGA E INVENTARIO', c: `EL ARRENDADOR entrega el inmueble en buen estado${d.inventario ? `, conforme al siguiente inventario: ${R.oracion(d.inventario)}` : '.'} EL ARRENDATARIO lo recibe a satisfacción y lo devolverá en el mismo estado, salvo el deterioro natural.` },
      { t: 'REPARACIONES Y MEJORAS', c: 'Las reparaciones locativas son a cargo de EL ARRENDATARIO y las necesarias a cargo de EL ARRENDADOR. Las mejoras útiles o voluntarias que EL ARRENDATARIO realice con autorización escrita quedarán a favor del inmueble sin indemnización, salvo acuerdo escrito en contrario (artículo 1994 del Código Civil).' },
      { t: 'SUBARRIENDO Y CESIÓN', c: 'Conforme al artículo 523 del Código de Comercio, EL ARRENDATARIO no podrá subarrendar totalmente el local ni cederlo sin autorización escrita, pero podrá subarrendar hasta la mitad del mismo siempre que se conserve la destinación, y podrá ceder el contrato junto con la enajenación del establecimiento de comercio.' },
      { t: 'TERMINACIÓN', c: 'El contrato terminará por vencimiento del plazo sin renovación en los casos de ley, por mutuo acuerdo y por incumplimiento de cualquiera de las obligaciones, en especial el no pago de dos o más cánones, el cambio de destinación, el subarriendo no autorizado y el deterioro grave del inmueble.' },
      { t: 'CLÁUSULA PENAL', c: `El incumplimiento de cualquiera de las partes dará lugar al pago de dos (2) cánones (${pct(d.canon, 2)}) a título de pena, sin perjuicio del cumplimiento y de los perjuicios adicionales.` },
      merito('los cánones y demás sumas derivadas de este contrato'),
      controversias(),
      notif(P)
    ],
    guia: { nota: 'Después de dos años con el mismo negocio, el arrendatario tiene derecho a renovar el contrato; el arrendador solo puede negarse por las causas del artículo 518 del Código de Comercio y avisando con 6 meses (desahucio).', pasos: ['Firmar dos copias; autenticar en notaría es opcional pero recomendable.', 'Verificar que el uso del suelo permita la actividad (certificado de Planeación) antes de firmar.', 'Hacer inventario con fotos y firmarlo.', 'Registrar el establecimiento de comercio en la Cámara de Comercio.'] }
  },

  /* ---------------- COMPRAVENTA DE VEHÍCULO ---------------- */
  {
    id: 'con_compraventa_vehiculo', tipo: 'contrato', categoria: 'particular',
    titulo: 'Contrato de compraventa de vehículo o motocicleta',
    resumen: 'Identificación completa del vehículo, precio, forma de pago, entrega, estado, documentos, traspaso ante tránsito y quién responde por multas e impuestos.',
    palabras: ['vehículo', 'carro', 'moto', 'motocicleta', 'camioneta', 'compraventa', 'venta', 'traspaso', 'placa', 'tránsito', 'RUNT', 'comprar carro', 'vender moto', 'minerva'],
    tituloDoc: 'CONTRATO DE COMPRAVENTA DE VEHÍCULO AUTOMOTOR', nombreContrato: 'contrato de compraventa de vehículo automotor',
    roles: { a: 'EL VENDEDOR', b: 'EL COMPRADOR' },
    rolCampo: { opciones: [ { v: 'a', t: 'Soy quien vende el vehículo' }, { v: 'b', t: 'Soy quien compra el vehículo' } ] },
    campos: [
      { id: 'clase', tipo: 'select', etiqueta: 'Clase de vehículo', opciones: [ { v: 'automovil', t: 'Automóvil' }, { v: 'camioneta', t: 'Camioneta o campero' }, { v: 'motocicleta', t: 'Motocicleta' }, { v: 'camion', t: 'Camión, bus o volqueta' }, { v: 'otro', t: 'Otro' } ], valorInicial: 'automovil', ancho: 'media' },
      { id: 'placa', tipo: 'texto', etiqueta: 'Placa', requerido: true, ancho: 'media' },
      { id: 'marca', tipo: 'texto', etiqueta: 'Marca', ejemplo: 'Ej.: Chevrolet', requerido: true, ancho: 'media' },
      { id: 'linea', tipo: 'texto', etiqueta: 'Línea o referencia', ejemplo: 'Ej.: Spark GT', ancho: 'media' },
      { id: 'modelo', tipo: 'texto', etiqueta: 'Modelo (año)', ejemplo: 'Ej.: 2019', requerido: true, ancho: 'media' },
      { id: 'color', tipo: 'texto', etiqueta: 'Color', ancho: 'media' },
      { id: 'motor', tipo: 'texto', etiqueta: 'Número de motor', ancho: 'media' },
      { id: 'chasis', tipo: 'texto', etiqueta: 'Número de chasis o serie (VIN)', ancho: 'media' },
      { id: 'servicio', tipo: 'select', etiqueta: 'Servicio', opciones: [ { v: 'particular', t: 'Particular' }, { v: 'publico', t: 'Público' } ], valorInicial: 'particular', ancho: 'media' },
      { id: 'kilometraje', tipo: 'texto', etiqueta: 'Kilometraje actual', ejemplo: 'Ej.: 65.000 km', ancho: 'media' },
      { id: 'precio', tipo: 'texto', etiqueta: 'Precio de venta', ejemplo: 'Ej.: 32.000.000', requerido: true, ancho: 'media' },
      { id: 'formaPago', tipo: 'radio', etiqueta: 'Forma de pago', requerido: true, opciones: [ { v: 'contado', t: 'De contado al firmar' }, { v: 'cuotas', t: 'Una parte ahora y el resto en cuotas o en una fecha (explica abajo)' } ] },
      { id: 'detallePago', tipo: 'textarea', etiqueta: 'Detalle del pago (cuánto ahora, cuánto después, fechas, cuenta)', ejemplo: 'Ej.: 20.000.000 al firmar por transferencia y 12.000.000 el 30 de noviembre de 2026', mostrarSi: { campo: 'formaPago', valor: 'cuotas' }, filas: 2 },
      { id: 'fechaEntrega', tipo: 'fecha', etiqueta: 'Fecha de entrega del vehículo', requerido: true, ancho: 'media' },
      { id: 'plazoTraspaso', tipo: 'texto', etiqueta: 'Días para hacer el traspaso en tránsito', valorInicial: '15', ancho: 'media' },
      { id: 'pagaTraspaso', tipo: 'radio', etiqueta: '¿Quién paga los gastos del traspaso?', requerido: true, opciones: [ { v: 'comprador', t: 'El comprador' }, { v: 'vendedor', t: 'El vendedor' }, { v: 'mitad', t: 'Por mitades' } ] },
      { id: 'documentos', tipo: 'checks', etiqueta: 'Documentos que el vendedor entrega', opciones: [ { v: 'tarjeta', t: 'Tarjeta de propiedad (licencia de tránsito)', legal: 'la licencia de tránsito (tarjeta de propiedad)' }, { v: 'soat', t: 'SOAT vigente', legal: 'el SOAT vigente' }, { v: 'rtm', t: 'Revisión técnico-mecánica vigente', legal: 'el certificado de revisión técnico-mecánica vigente' }, { v: 'multas', t: 'Paz y salvo de multas (SIMIT)', legal: 'la constancia de no tener multas pendientes (SIMIT)' }, { v: 'impuestos', t: 'Paz y salvo de impuesto de vehículos', legal: 'los recibos de pago del impuesto de vehículos' }, { v: 'llaves', t: 'Llaves, manual y herramientas', legal: 'las llaves, el manual y la herramienta' } ] },
      { id: 'gravamenes', tipo: 'radio', etiqueta: '¿El vehículo tiene prenda, crédito o embargo?', requerido: true, opciones: [ { v: 'libre', t: 'No, está libre' }, { v: 'prenda', t: 'Sí, tiene prenda o crédito que el vendedor va a levantar (explica en cláusulas adicionales)' } ] }
    ],
    opcionales: [
      { v: 'reserva', t: 'Reserva de dominio hasta que se pague todo (si hay cuotas)', clausula: { t: 'RESERVA DE DOMINIO', c: 'Conforme al artículo 952 del Código de Comercio, EL VENDEDOR se reserva el dominio del vehículo hasta el pago total del precio. EL COMPRADOR no podrá enajenarlo ni gravarlo mientras tanto, y el traspaso se realizará una vez cancelado el saldo.' } },
      { v: 'garantia', t: 'El vendedor da garantía mecánica por un tiempo', clausula: { t: 'GARANTÍA', c: 'EL VENDEDOR garantiza el buen funcionamiento del motor y la caja de cambios durante treinta (30) días contados desde la entrega, siempre que el vehículo no haya sufrido accidentes ni intervenciones de terceros; fuera de ello, el vehículo se vende en el estado en que se encuentra.' } },
      { v: 'prueba', t: 'El comprador hizo revisar el vehículo con un mecánico', clausula: { t: 'REVISIÓN PREVIA', c: 'EL COMPRADOR declara que inspeccionó el vehículo y lo hizo revisar por un mecánico de su confianza, y lo recibe a satisfacción en el estado en que se encuentra.' } }
    ],
    clausulas: (d, P) => {
      const v = `${R.opcionTexto(cd('con_compraventa_vehiculo', 'clase'), d.clase, 't')} de placa ${R.mayus(d.placa) || '[PLACA]'}, marca ${d.marca || '[marca]'}${d.linea ? `, línea ${d.linea}` : ''}, modelo ${d.modelo || '[modelo]'}${d.color ? `, color ${d.color}` : ''}${d.motor ? `, motor No. ${d.motor}` : ''}${d.chasis ? `, chasis o serie No. ${d.chasis}` : ''}, de servicio ${d.servicio || 'particular'}${d.kilometraje ? `, con un kilometraje de ${d.kilometraje}` : ''}`;
      const docs = (d.documentos || []).map(x => R.opcionTexto(cd('con_compraventa_vehiculo', 'documentos'), x));
      const pagaT = { comprador: 'EL COMPRADOR', vendedor: 'EL VENDEDOR', mitad: 'ambas partes por mitades' }[d.pagaTraspaso] || 'EL COMPRADOR';
      return [
        { t: 'OBJETO', c: `EL VENDEDOR transfiere a título de venta a EL COMPRADOR, quien adquiere, el ${v}.` },
        { t: 'PRECIO Y FORMA DE PAGO', c: `El precio de venta es de ${R.pesos(d.precio)}, que EL COMPRADOR paga ${d.formaPago === 'cuotas' ? `así: ${R.oracion(d.detallePago || '[detalle del pago]')}` : 'de contado en la fecha de firma de este contrato, suma que EL VENDEDOR declara recibida a satisfacción.'}` },
        { t: 'ENTREGA', c: `EL VENDEDOR entrega el vehículo el ${R.fechaLarga(d.fechaEntrega) || '[fecha]'}${docs.length ? `, junto con ${R.lista(docs)}` : ''}. A partir de la entrega, EL COMPRADOR asume la tenencia, el uso, los riesgos y la responsabilidad por infracciones de tránsito, impuestos y daños a terceros.` },
        { t: 'DECLARACIONES DEL VENDEDOR', c: `EL VENDEDOR declara que es el propietario inscrito del vehículo, que lo ha poseído de manera pacífica, que ${d.gravamenes === 'prenda' ? 'sobre el vehículo existe una prenda o crédito que se obliga a cancelar y levantar antes del traspaso' : 'el vehículo está libre de prendas, embargos, limitaciones al dominio y demandas'}, que no ha sido reportado como hurtado y que se encuentra a paz y salvo por impuestos y multas hasta la fecha de entrega. Las multas, impuestos y obligaciones causadas antes de la entrega son de su cargo.` },
        { t: 'ESTADO DEL VEHÍCULO', c: 'EL COMPRADOR declara que conoce el vehículo, lo ha inspeccionado y lo recibe en el estado de uso en que se encuentra, sin perjuicio del saneamiento por vicios ocultos que establecen los artículos 1914 y siguientes del Código Civil.' },
        { t: 'TRASPASO', c: `Las partes realizarán el traspaso ante el organismo de tránsito correspondiente dentro de los ${R.numeroLetras(d.plazoTraspaso || 15)} días siguientes a la entrega, conforme al artículo 47 de la Ley 769 de 2002. Los gastos del traspaso (formulario, derechos, improntas, autenticaciones y retención, si aplica) serán pagados por ${pagaT}. EL VENDEDOR firmará los documentos necesarios y comparecerá cuando se requiera. Si EL COMPRADOR no realiza el traspaso en el plazo, responderá ante EL VENDEDOR por todas las multas, impuestos y perjuicios que se causen y EL VENDEDOR podrá tramitar el traspaso a persona indeterminada previsto en la ley.` },
        { t: 'SANEAMIENTO', c: 'EL VENDEDOR responde por el saneamiento en caso de evicción y por los vicios ocultos del vehículo en los términos de los artículos 1893 y siguientes del Código Civil.' },
        { t: 'CLÁUSULA PENAL', c: `El incumplimiento de cualquiera de las partes dará lugar al pago de una pena equivalente al diez por ciento (10 %) del precio (${pct(d.precio, 0.1)}), sin perjuicio del cumplimiento de la obligación principal.` },
        merito('el precio o las sumas que se adeuden'),
        controversias(),
        notif(P)
      ];
    },
    guia: { nota: 'Para la ley, el dueño del vehículo es quien aparece inscrito en el RUNT. Mientras no se haga el traspaso, las multas y los impuestos le siguen llegando al vendedor.', pasos: ['Antes de pagar: consultar la placa en el RUNT (www.runt.gov.co) y el SIMIT (multas), y revisar que el vendedor sea el propietario inscrito.', 'Firmar dos copias y autenticar las firmas en notaría (el tránsito lo exige para el traspaso).', 'Hacer el traspaso en el organismo de tránsito (formulario de solicitud de trámites, improntas, SOAT y revisión técnico-mecánica vigentes, paz y salvos) dentro del plazo pactado.', 'El comprador debe comprar su propio SOAT a su nombre después del traspaso.'] }
  },

  /* ---------------- COMPRAVENTA DE BIEN MUEBLE ---------------- */
  {
    id: 'con_compraventa_bien', tipo: 'contrato', categoria: 'particular',
    titulo: 'Contrato de compraventa de un bien (celular, computador, muebles, maquinaria, animales)',
    resumen: 'Para dejar por escrito la venta de cualquier cosa que no sea inmueble ni vehículo: qué se vende, precio, entrega, estado y garantía.',
    palabras: ['compraventa', 'venta', 'comprar', 'vender', 'celular', 'computador', 'muebles', 'nevera', 'maquinaria', 'bicicleta', 'ganado', 'caballo', 'bien mueble', 'usado', 'contrato de venta'],
    tituloDoc: 'CONTRATO DE COMPRAVENTA DE BIEN MUEBLE', nombreContrato: 'contrato de compraventa',
    roles: { a: 'EL VENDEDOR', b: 'EL COMPRADOR' },
    rolCampo: { opciones: [ { v: 'a', t: 'Soy quien vende' }, { v: 'b', t: 'Soy quien compra' } ] },
    campos: [
      { id: 'bien', tipo: 'textarea', etiqueta: '¿Qué se vende? (descripción completa: tipo, marca, modelo, serial o IMEI, cantidad, características)', ejemplo: 'Ej.: Computador portátil Lenovo IdeaPad 3, serial PF2ABC12, 8 GB de RAM, con cargador', requerido: true, filas: 2 },
      { id: 'estado', tipo: 'select', etiqueta: 'Estado', opciones: [ { v: 'nuevo', t: 'Nuevo', legal: 'nuevo' }, { v: 'usado', t: 'Usado, en buen estado', legal: 'usado y en buen estado de funcionamiento' }, { v: 'reparar', t: 'Usado, con fallas conocidas (explica abajo)', legal: 'usado y con las fallas que se describen' } ], valorInicial: 'usado', ancho: 'media' },
      { id: 'fallas', tipo: 'texto', etiqueta: '¿Qué fallas tiene?', mostrarSi: { campo: 'estado', valor: 'reparar' }, ancho: 'media' },
      { id: 'precio', tipo: 'texto', etiqueta: 'Precio', requerido: true, ancho: 'media' },
      { id: 'formaPago', tipo: 'radio', etiqueta: 'Forma de pago', requerido: true, opciones: [ { v: 'contado', t: 'De contado al firmar' }, { v: 'cuotas', t: 'En cuotas o en otra fecha (explica abajo)' } ] },
      { id: 'detallePago', tipo: 'texto', etiqueta: 'Detalle del pago', mostrarSi: { campo: 'formaPago', valor: 'cuotas' }, ancho: 'completa' },
      { id: 'fechaEntrega', tipo: 'fecha', etiqueta: 'Fecha de entrega', requerido: true, ancho: 'media' },
      { id: 'lugarEntrega', tipo: 'texto', etiqueta: 'Lugar de entrega', ancho: 'media' },
      { id: 'garantia', tipo: 'radio', etiqueta: 'Garantía', requerido: true, opciones: [ { v: 'ninguna', t: 'Sin garantía (venta entre particulares, en el estado en que está)' }, { v: 'meses', t: 'Con garantía por un tiempo (indica cuánto)' }, { v: 'legal', t: 'El vendedor es un negocio: aplica la garantía legal de la Ley 1480 de 2011' } ] },
      { id: 'garantiaMeses', tipo: 'texto', etiqueta: '¿Cuántos meses de garantía?', mostrarSi: { campo: 'garantia', valor: 'meses' }, ancho: 'media' }
    ],
    opcionales: [
      { v: 'reserva', t: 'Reserva de dominio hasta el pago total', clausula: { t: 'RESERVA DE DOMINIO', c: 'EL VENDEDOR se reserva el dominio del bien hasta el pago total del precio (artículo 952 del Código de Comercio); mientras tanto EL COMPRADOR no podrá venderlo ni entregarlo en garantía.' } },
      { v: 'accesorios', t: 'Se entregan accesorios, factura original o manuales', clausula: { t: 'ACCESORIOS Y DOCUMENTOS', c: 'Junto con el bien, EL VENDEDOR entrega los accesorios, la factura original y los manuales con que cuenta, los cuales hacen parte de la venta.' } }
    ],
    clausulas: (d, P) => [
      { t: 'OBJETO', c: `EL VENDEDOR vende y entrega a EL COMPRADOR, quien compra y recibe, el siguiente bien: ${R.oracion(d.bien)}` },
      { t: 'PRECIO Y FORMA DE PAGO', c: `El precio es de ${R.pesos(d.precio)}, que EL COMPRADOR paga ${d.formaPago === 'cuotas' ? `así: ${R.oracion(d.detallePago || '[detalle]')}` : 'de contado al firmar este contrato, suma que EL VENDEDOR declara recibida a satisfacción.'}` },
      { t: 'ENTREGA Y RIESGO', c: `La entrega se realiza el ${R.fechaLarga(d.fechaEntrega) || '[fecha]'}${d.lugarEntrega ? ` en ${d.lugarEntrega}` : ''}. Desde la entrega, el riesgo de pérdida o deterioro del bien corre por cuenta de EL COMPRADOR.` },
      { t: 'ESTADO Y GARANTÍA', c: `El bien se vende ${R.opcionTexto(cd('con_compraventa_bien', 'estado'), d.estado)}${d.estado === 'reparar' && d.fallas ? `: ${d.fallas}` : ''}. ${d.garantia === 'legal' ? 'Por tratarse de una venta realizada por un productor o proveedor, aplica la garantía legal de la Ley 1480 de 2011 (reparación gratuita, cambio o devolución del dinero).' : d.garantia === 'meses' ? `EL VENDEDOR garantiza el buen funcionamiento del bien durante ${R.numeroLetras(d.garantiaMeses || 1)} meses contados desde la entrega, siempre que no haya sido manipulado indebidamente por EL COMPRADOR.` : 'EL COMPRADOR declara que examinó el bien y lo recibe a satisfacción en el estado en que se encuentra, sin garantía de funcionamiento, sin perjuicio del saneamiento por vicios ocultos que no hayan sido informados (artículos 1914 y siguientes del Código Civil).'}` },
      { t: 'DECLARACIONES DEL VENDEDOR', c: 'EL VENDEDOR declara que es el propietario del bien, que lo adquirió lícitamente, que no está reportado como hurtado ni soporta prendas, embargos o reclamaciones de terceros, y responde por el saneamiento en caso de evicción (artículos 1893 y siguientes del Código Civil).' },
      { t: 'CLÁUSULA PENAL', c: `El incumplimiento de cualquiera de las partes dará lugar a una pena del diez por ciento (10 %) del precio (${pct(d.precio, 0.1)}), sin perjuicio del cumplimiento.` },
      merito('el precio o las sumas adeudadas'),
      controversias(),
      notif(P)
    ],
    guia: { nota: 'Si quien vende es un almacén o negocio, la garantía legal de la Ley 1480 de 2011 aplica aunque no esté escrita.', pasos: ['Firmar dos copias.', 'Para celulares: verificar el IMEI en www.imeicolombia.com.co antes de pagar (que no esté reportado).', 'Guardar comprobante de pago (transferencia o recibo).'] }
  },

  /* ---------------- PROMESA DE COMPRAVENTA DE INMUEBLE ---------------- */
  {
    id: 'con_promesa_inmueble', tipo: 'contrato', categoria: 'particular', retirado: true,
    titulo: 'Promesa de compraventa de casa, apartamento o lote',
    resumen: 'El paso previo a la escritura pública: identifica el inmueble, el precio, las arras, la fecha y notaría de la escritura, la entrega, los gastos y la cláusula penal (artículo 89 de la Ley 153 de 1887).',
    palabras: ['promesa', 'promesa de compraventa', 'casa', 'apartamento', 'lote', 'inmueble', 'finca', 'escritura', 'notaría', 'arras', 'comprar casa', 'vender casa', 'minerva'],
    tituloDoc: 'CONTRATO DE PROMESA DE COMPRAVENTA DE INMUEBLE', nombreContrato: 'contrato de promesa de compraventa',
    roles: { a: 'EL PROMETIENTE VENDEDOR', b: 'EL PROMETIENTE COMPRADOR' },
    rolCampo: { opciones: [ { v: 'a', t: 'Soy quien vende (prometiente vendedor)' }, { v: 'b', t: 'Soy quien compra (prometiente comprador)' } ] },
    campos: [
      { id: 'tipoInmueble', tipo: 'select', etiqueta: 'Tipo de inmueble', opciones: [ { v: 'casa', t: 'Casa' }, { v: 'apartamento', t: 'Apartamento' }, { v: 'lote', t: 'Lote' }, { v: 'finca', t: 'Finca o predio rural' }, { v: 'local', t: 'Local u oficina' } ], valorInicial: 'casa', ancho: 'media' },
      { id: 'direccionInmueble', tipo: 'texto', etiqueta: 'Dirección', requerido: true, ancho: 'media' },
      { id: 'ciudadInmueble', tipo: 'texto', etiqueta: 'Ciudad o municipio', requerido: true, ancho: 'media' },
      { id: 'matricula', tipo: 'texto', etiqueta: 'Matrícula inmobiliaria (está en el certificado de tradición y libertad)', ejemplo: 'Ej.: 001-1234567', requerido: true, ancho: 'media' },
      { id: 'catastral', tipo: 'texto', etiqueta: 'Cédula o referencia catastral (está en el recibo del predial)', ancho: 'media' },
      { id: 'area', tipo: 'texto', etiqueta: 'Área', ejemplo: 'Ej.: 72 m² construidos / 2 hectáreas', ancho: 'media' },
      { id: 'escrituraAdq', tipo: 'texto', etiqueta: 'Escritura con la que el vendedor adquirió (número, fecha, notaría)', ejemplo: 'Ej.: Escritura 1.234 del 5 de mayo de 2015, Notaría 10 de Medellín', ancho: 'completa' },
      { id: 'precio', tipo: 'texto', etiqueta: 'Precio total', requerido: true, ancho: 'media' },
      { id: 'arras', tipo: 'texto', etiqueta: 'Valor que se paga al firmar la promesa (arras)', ejemplo: 'Ej.: 20.000.000', ancho: 'media' },
      { id: 'tipoArras', tipo: 'radio', etiqueta: 'Tipo de arras', requerido: true, opciones: [ { v: 'confirmatorias', t: 'Confirmatorias: son parte del precio y el contrato obliga (lo usual)' }, { v: 'penitenciales', t: 'De retracto: cualquiera puede arrepentirse perdiéndolas (comprador) o devolviéndolas dobladas (vendedor)' } ] },
      { id: 'saldo', tipo: 'textarea', etiqueta: '¿Cómo se paga el resto del precio?', ejemplo: 'Ej.: 150.000.000 con crédito hipotecario de Bancolombia desembolsado a la firma de la escritura, y 30.000.000 en efectivo el día de la escritura', requerido: true, filas: 2 },
      { id: 'fechaEscritura', tipo: 'fecha', etiqueta: 'Fecha en que se firmará la escritura', requerido: true, ancho: 'media' },
      { id: 'horaEscritura', tipo: 'texto', etiqueta: 'Hora', ejemplo: 'Ej.: 10:00 a. m.', valorInicial: '10:00 a. m.', ancho: 'media' },
      { id: 'notaria', tipo: 'texto', etiqueta: 'Notaría donde se firmará', ejemplo: 'Ej.: Notaría 15 del Círculo de Medellín', requerido: true, ancho: 'completa' },
      { id: 'fechaEntrega', tipo: 'fecha', etiqueta: 'Fecha de entrega material del inmueble', ancho: 'media' },
      { id: 'gastos', tipo: 'select', etiqueta: 'Gastos de escritura y registro', opciones: [ { v: 'usual', t: 'Lo usual: notaría por mitades; registro y beneficencia el comprador; retención el vendedor', legal: 'los gastos notariales se pagarán por partes iguales; los derechos de registro y el impuesto de beneficencia serán a cargo de EL PROMETIENTE COMPRADOR, y la retención en la fuente a cargo de EL PROMETIENTE VENDEDOR' }, { v: 'comprador', t: 'Todos los paga el comprador', legal: 'todos los gastos notariales, de registro y de beneficencia serán a cargo de EL PROMETIENTE COMPRADOR, y la retención en la fuente a cargo de EL PROMETIENTE VENDEDOR' }, { v: 'vendedor', t: 'Todos los paga el vendedor', legal: 'todos los gastos notariales, de registro, de beneficencia y la retención en la fuente serán a cargo de EL PROMETIENTE VENDEDOR' } ], valorInicial: 'usual', ancho: 'completa' },
      { id: 'gravamenes', tipo: 'radio', etiqueta: '¿El inmueble tiene hipoteca, embargo o patrimonio de familia?', requerido: true, opciones: [ { v: 'libre', t: 'No, está libre' }, { v: 'hipoteca', t: 'Tiene hipoteca que se cancelará con el precio' }, { v: 'otro', t: 'Otra situación (explica en cláusulas adicionales)' } ] }
    ],
    opcionales: [
      { v: 'credito', t: 'La compra depende de que aprueben un crédito', clausula: { t: 'CONDICIÓN DE CRÉDITO', c: 'Si la entidad financiera no aprueba el crédito solicitado por EL PROMETIENTE COMPRADOR antes de la fecha de la escritura, este podrá desistir de la promesa dentro de los cinco (5) días siguientes a la negativa, con derecho a la devolución de las sumas entregadas sin intereses ni penalidad, siempre que acredite la negativa por escrito.' } },
      { v: 'arriendo', t: 'El inmueble está arrendado y se entregará con el contrato de arriendo', clausula: { t: 'INMUEBLE ARRENDADO', c: 'El inmueble se encuentra arrendado; EL PROMETIENTE COMPRADOR lo recibirá respetando el contrato de arrendamiento vigente, que le será cedido en la escritura, y recibirá los cánones a partir de la entrega.' } },
      { v: 'muebles', t: 'Se incluyen muebles o electrodomésticos', clausula: { t: 'BIENES INCLUIDOS', c: 'En el precio quedan incluidos los muebles, electrodomésticos y accesorios que las partes relacionan en inventario firmado por ambas, que hace parte de esta promesa.' } }
    ],
    clausulas: (d, P) => [
      { t: 'OBJETO', c: `EL PROMETIENTE VENDEDOR promete vender a EL PROMETIENTE COMPRADOR, quien promete comprar, el derecho de dominio y la posesión que tiene sobre el inmueble (${R.opcionTexto(cd('con_promesa_inmueble', 'tipoInmueble'), d.tipoInmueble, 't').toLowerCase()}) ubicado en ${d.direccionInmueble || '[dirección]'}, ${d.ciudadInmueble || '[ciudad]'}, identificado con matrícula inmobiliaria No. ${d.matricula || '[matrícula]'}${d.catastral ? ` y cédula catastral No. ${d.catastral}` : ''}${d.area ? `, con un área aproximada de ${d.area}` : ''}, cuyos linderos y demás especificaciones son los que constan en ${d.escrituraAdq ? `la ${d.escrituraAdq}` : 'el título de adquisición de EL PROMETIENTE VENDEDOR'} y en el certificado de tradición y libertad, que las partes declaran conocer.` },
      { t: 'PRECIO', c: `El precio de la compraventa prometida es de ${R.pesos(d.precio)}.` },
      { t: 'FORMA DE PAGO', c: `${d.arras ? `a) La suma de ${R.pesos(d.arras)}, que EL PROMETIENTE COMPRADOR entrega en la fecha de firma de esta promesa a título de arras ${d.tipoArras === 'penitenciales' ? 'de retracto' : 'confirmatorias'}, y que EL PROMETIENTE VENDEDOR declara recibida. b) ` : ''}El ${d.arras ? 'saldo' : 'precio'} se pagará así: ${R.oracion(d.saldo || '[forma de pago del saldo]')}` },
      { t: 'ARRAS', c: d.tipoArras === 'penitenciales' ? 'Las arras entregadas son de retracto (artículo 1859 del Código Civil): cualquiera de las partes podrá retractarse antes de la fecha de la escritura; si se retracta EL PROMETIENTE COMPRADOR, las perderá; si se retracta EL PROMETIENTE VENDEDOR, las devolverá dobladas.' : 'Las arras entregadas son confirmatorias y hacen parte del precio (artículo 1861 del Código Civil); ninguna de las partes podrá retractarse, y su incumplimiento dará lugar a la cláusula penal y a las demás acciones legales.' },
      { t: 'ESCRITURA PÚBLICA', c: `La escritura pública de compraventa se firmará el ${R.fechaLarga(d.fechaEscritura) || '[fecha]'} a las ${d.horaEscritura || '10:00 a. m.'} en la ${d.notaria || '[notaría]'}. Si ese día la notaría no presta servicio, la firma se realizará el siguiente día hábil a la misma hora. Cada parte aportará los documentos que le correspondan (paz y salvos, certificados, poderes) con al menos cinco (5) días de anticipación.` },
      { t: 'ENTREGA', c: `EL PROMETIENTE VENDEDOR entregará materialmente el inmueble ${d.fechaEntrega ? `el ${R.fechaLarga(d.fechaEntrega)}` : 'el día de la firma de la escritura'}, desocupado, en el estado en que se encuentra, con los servicios públicos, el impuesto predial, la valorización y la administración a paz y salvo hasta la fecha de entrega.` },
      { t: 'DECLARACIONES Y OBLIGACIONES DEL PROMETIENTE VENDEDOR', c: `EL PROMETIENTE VENDEDOR declara que es el único propietario del inmueble, que lo posee de manera pacífica, que ${d.gravamenes === 'hipoteca' ? 'sobre él existe una hipoteca que cancelará con parte del precio y cuya cancelación se tramitará en la misma escritura' : d.gravamenes === 'otro' ? 'la situación jurídica del inmueble es la que se describe en las cláusulas adicionales' : 'está libre de hipotecas, embargos, pleitos, patrimonio de familia, afectación a vivienda familiar, servidumbres no aparentes y demás limitaciones'}, y se obliga a no enajenarlo ni gravarlo hasta la firma de la escritura y a responder por el saneamiento por evicción y vicios ocultos.` },
      { t: 'OBLIGACIONES DEL PROMETIENTE COMPRADOR', c: 'EL PROMETIENTE COMPRADOR se obliga a pagar el precio en la forma convenida, a comparecer a la notaría en la fecha señalada y a asumir, desde la entrega, los impuestos, servicios y cuotas de administración.' },
      { t: 'GASTOS', c: `${R.capital(R.opcionTexto(cd('con_promesa_inmueble', 'gastos'), d.gastos))}.` },
      { t: 'CLÁUSULA PENAL', c: `Quien incumpla esta promesa pagará a la otra parte, a título de pena, una suma equivalente al diez por ciento (10 %) del precio (${pct(d.precio, 0.1)}), sin perjuicio de que la parte cumplida exija el cumplimiento o la resolución del contrato con indemnización de perjuicios (artículo 1546 del Código Civil).` },
      merito('la cláusula penal y las sumas adeudadas'),
      controversias(),
      notif(P)
    ],
    guia: { nota: 'La promesa no transfiere la propiedad: el comprador solo será dueño cuando se firme la escritura en la notaría y se registre en la Oficina de Registro de Instrumentos Públicos.', pasos: ['Antes de firmar: pedir el certificado de tradición y libertad actualizado (www.supernotariado.gov.co) y revisar que el vendedor sea el dueño y que no haya embargos ni hipotecas.', 'Firmar dos copias; autenticar las firmas en notaría es muy recomendable.', 'Ir a la notaría el día y hora pactados con cédulas, paz y salvo de predial y de administración, y el dinero o la carta de aprobación del crédito.', 'Después de la escritura, registrarla en la Oficina de Registro de Instrumentos Públicos: solo entonces el comprador es el dueño.'] }
  },

  /* ---------------- CONTRATO DE TRABAJO ---------------- */
  {
    id: 'con_trabajo', tipo: 'contrato', categoria: 'empleador', retirado: true,
    titulo: 'Contrato de trabajo (a término fijo, indefinido o por obra o labor)',
    resumen: 'Contrato laboral según el Código Sustantivo del Trabajo: cargo, funciones, salario, jornada de 42 horas, período de prueba, prestaciones, seguridad social y terminación. Para empleadores y trabajadores.',
    palabras: ['contrato de trabajo', 'contrato laboral', 'término fijo', 'indefinido', 'obra o labor', 'empleado', 'trabajador', 'empleador', 'salario', 'período de prueba', 'minerva', 'contratar'],
    tituloDoc: d => `CONTRATO INDIVIDUAL DE TRABAJO ${({ indefinido: 'A TÉRMINO INDEFINIDO', fijo: 'A TÉRMINO FIJO', obra: 'POR DURACIÓN DE LA OBRA O LABOR' })[d.tipoContrato] || ''}`.trim(), nombreContrato: 'contrato individual de trabajo',
    roles: { a: 'EL EMPLEADOR', b: 'EL TRABAJADOR' },
    rolCampo: { opciones: [ { v: 'a', t: 'Soy el empleador (quien contrata)' }, { v: 'b', t: 'Soy el trabajador' } ] },
    campos: [
      { id: 'tipoContrato', tipo: 'select', etiqueta: 'Tipo de contrato', requerido: true, opciones: [ { v: 'indefinido', t: 'A término indefinido (sin fecha de terminación)' }, { v: 'fijo', t: 'A término fijo (con fecha de terminación; máximo 3 años)' }, { v: 'obra', t: 'Por duración de la obra o labor (termina cuando se acaba la obra)' } ], valorInicial: 'indefinido', ancho: 'completa' },
      { id: 'duracionMeses', tipo: 'texto', etiqueta: 'Duración en meses', ejemplo: 'Ej.: 6', mostrarSi: { campo: 'tipoContrato', valor: 'fijo' }, ancho: 'media' },
      { id: 'obra', tipo: 'texto', etiqueta: '¿Cuál es la obra o labor?', ejemplo: 'Ej.: construcción de la segunda etapa del edificio Torre Verde', mostrarSi: { campo: 'tipoContrato', valor: 'obra' }, ancho: 'completa' },
      { id: 'cargo', tipo: 'texto', etiqueta: 'Cargo u oficio', requerido: true, ancho: 'media' },
      { id: 'lugarTrabajo', tipo: 'texto', etiqueta: 'Lugar de trabajo', ejemplo: 'Ej.: Bodega de la empresa, calle 30 # 50-20, Itagüí', ancho: 'media' },
      { id: 'funciones', tipo: 'textarea', etiqueta: 'Funciones principales', ejemplo: 'Ej.: Recibir y despachar mercancía, mantener el inventario actualizado, atender proveedores.', requerido: true, filas: 2 },
      { id: 'salario', tipo: 'texto', etiqueta: 'Salario mensual', ejemplo: 'Ej.: 1.750.000', requerido: true, ancho: 'media' },
      { id: 'periodoPago', tipo: 'select', etiqueta: 'Se paga', opciones: [ { v: 'mensual', t: 'Mensualmente' }, { v: 'quincenal', t: 'Cada quincena' } ], valorInicial: 'quincenal', ancho: 'media' },
      { id: 'jornada', tipo: 'texto', etiqueta: 'Horario', ejemplo: 'Ej.: lunes a viernes de 7:00 a. m. a 4:00 p. m., con una hora de almuerzo', valorInicial: 'lunes a viernes de 8:00 a. m. a 5:00 p. m., con una hora de almuerzo, y sábados de 8:00 a. m. a 12:00 m.', ancho: 'completa' },
      { id: 'fechaInicio', tipo: 'fecha', etiqueta: 'Fecha de inicio', requerido: true, ancho: 'media' },
      { id: 'periodoPrueba', tipo: 'select', etiqueta: 'Período de prueba', opciones: [ { v: 'dos', t: 'Sí, de dos meses (el máximo legal)' }, { v: 'uno', t: 'Sí, de un mes' }, { v: 'no', t: 'Sin período de prueba' } ], valorInicial: 'dos', ancho: 'media' }
    ],
    opcionales: [
      { v: 'confidencialidad', t: 'Confidencialidad sobre la información de la empresa', clausula: { t: 'CONFIDENCIALIDAD', c: 'EL TRABAJADOR guardará reserva sobre la información confidencial de EL EMPLEADOR (clientes, precios, procesos, datos personales) durante la vigencia del contrato y después de su terminación, sin que ello limite su derecho a trabajar en su oficio.' } },
      { v: 'remoto', t: 'Trabajo en casa o remoto total o parcial', clausula: { t: 'TRABAJO EN CASA', c: 'Las partes acuerdan que EL TRABAJADOR podrá prestar sus servicios desde su domicilio en los días que se definan, conforme a la Ley 2088 de 2021, con derecho al auxilio de conectividad en los casos de ley, a la desconexión laboral (Ley 2191 de 2022) y a las mismas garantías del trabajo presencial.' } },
      { v: 'dotacion', t: 'Dejar expresa la entrega de dotación', clausula: { t: 'DOTACIÓN', c: 'Si EL TRABAJADOR devenga hasta dos (2) salarios mínimos, EL EMPLEADOR le entregará un par de zapatos y un vestido de labor cada cuatro meses (30 de abril, 31 de agosto y 20 de diciembre), conforme al artículo 230 del Código Sustantivo del Trabajo.' } }
    ],
    clausulas: (d, P) => {
      const dur = { indefinido: 'El contrato es a término indefinido y estará vigente mientras subsistan las causas que le dieron origen y la materia del trabajo (artículo 47 del Código Sustantivo del Trabajo).', fijo: `El contrato es a término fijo de ${R.numeroLetras(d.duracionMeses || 1)} meses, contados desde la fecha de inicio. Si ninguna de las partes avisa por escrito a la otra su decisión de no prorrogarlo con una antelación no inferior a treinta (30) días, se entenderá renovado por un período igual, y así sucesivamente; cuando el término sea inferior a un año, solo podrá prorrogarse por períodos iguales hasta por tres (3) veces, después de lo cual la renovación no podrá ser inferior a un año (artículo 46 del Código Sustantivo del Trabajo).`, obra: `El contrato durará el tiempo necesario para la ejecución de la siguiente obra o labor: ${d.obra || '[obra o labor]'}, y terminará al concluir la parte de la obra que corresponde al cargo contratado (artículo 45 del Código Sustantivo del Trabajo).` }[d.tipoContrato] || '';
      const prueba = d.periodoPrueba === 'no' ? 'Las partes no pactan período de prueba.' : `Las partes pactan un período de prueba de ${d.periodoPrueba === 'uno' ? 'un (1) mes' : 'dos (2) meses'}${d.tipoContrato === 'fijo' ? ', que en ningún caso excederá la quinta parte del término inicial del contrato' : ''}, durante el cual cualquiera de ellas podrá terminar el contrato sin previo aviso ni indemnización (artículos 76 a 80 del Código Sustantivo del Trabajo).`;
      return [
        { t: 'OBJETO Y CARGO', c: `EL EMPLEADOR contrata a EL TRABAJADOR para desempeñar el cargo de ${d.cargo || '[cargo]'}${d.lugarTrabajo ? ` en ${d.lugarTrabajo}` : ''}, bajo su continuada dependencia y subordinación, con las siguientes funciones principales: ${R.oracion(d.funciones)} EL TRABAJADOR podrá ser trasladado a cargos afines sin desmejora de su salario ni de su categoría.` },
        { t: 'DURACIÓN', c: dur },
        { t: 'PERÍODO DE PRUEBA', c: prueba },
        { t: 'SALARIO', c: `EL EMPLEADOR pagará a EL TRABAJADOR un salario mensual de ${R.pesos(d.salario)}, que en ningún caso será inferior al salario mínimo legal mensual vigente, pagadero ${d.periodoPago === 'mensual' ? 'mensualmente' : 'por quincenas vencidas'} en dinero, mediante consignación en la cuenta que indique EL TRABAJADOR. Si el salario no supera dos (2) salarios mínimos, EL TRABAJADOR recibirá además el auxilio legal de transporte. El salario se reajustará cada año al menos en el porcentaje de incremento del salario mínimo.` },
        { t: 'JORNADA', c: `La jornada ordinaria será de ${d.jornada || 'la que fije EL EMPLEADOR dentro de los límites legales'}, sin exceder la jornada máxima legal de cuarenta y dos (42) horas semanales (artículo 161 del Código Sustantivo del Trabajo, modificado por la Ley 2101 de 2021), distribuidas conforme a la ley. El trabajo suplementario, nocturno, dominical o festivo se pagará con los recargos legales y requerirá autorización previa de EL EMPLEADOR.` },
        { t: 'PRESTACIONES Y SEGURIDAD SOCIAL', c: 'EL TRABAJADOR tendrá derecho a las prestaciones legales: auxilio de cesantía consignado anualmente en el fondo que elija, intereses sobre cesantías, prima de servicios en junio y diciembre, vacaciones de quince (15) días hábiles por cada año de servicio y dotación cuando la ley lo exija. EL EMPLEADOR lo afiliará desde el primer día a salud (EPS), pensiones (AFP), riesgos laborales (ARL) y caja de compensación familiar, y pagará los aportes que le corresponden, descontando del salario únicamente los aportes a cargo de EL TRABAJADOR.' },
        { t: 'OBLIGACIONES DE EL TRABAJADOR', c: 'Además de las previstas en el artículo 58 del Código Sustantivo del Trabajo, EL TRABAJADOR se obliga a prestar personalmente el servicio, cumplir el horario y el reglamento interno, cuidar los bienes a su cargo, acatar las normas de seguridad y salud en el trabajo e informar oportunamente las incapacidades y novedades.' },
        { t: 'OBLIGACIONES DE EL EMPLEADOR', c: 'Además de las previstas en el artículo 57 del Código Sustantivo del Trabajo, EL EMPLEADOR se obliga a pagar el salario y las prestaciones en las fechas convenidas, suministrar los elementos de trabajo y de protección, garantizar condiciones de seguridad y salud, respetar la dignidad de EL TRABAJADOR y expedir las certificaciones laborales que solicite.' },
        { t: 'TERMINACIÓN', c: 'El contrato terminará por las causas del artículo 61 del Código Sustantivo del Trabajo. Cualquiera de las partes podrá darlo por terminado con justa causa, conforme al artículo 62, comunicándola por escrito en el momento de la terminación. Si EL EMPLEADOR lo termina sin justa causa, pagará la indemnización del artículo 64. A la terminación, EL EMPLEADOR pagará la liquidación definitiva de salarios y prestaciones dentro de los plazos legales.' },
        { t: 'NORMAS APLICABLES', c: 'Este contrato se rige por el Código Sustantivo del Trabajo y las normas que lo complementan. Cualquier estipulación que desmejore los derechos mínimos del trabajador se tendrá por no escrita (artículos 13, 14 y 43 del Código Sustantivo del Trabajo). Las modificaciones se harán por escrito.' },
        notif(P)
      ];
    },
    guia: { nota: 'El salario no puede ser inferior al mínimo legal vigente. El período de prueba solo vale si está escrito y no puede pasar de dos meses.', pasos: ['Firmar dos copias y entregar una al trabajador (artículo 39 del Código Sustantivo del Trabajo).', 'Afiliar al trabajador a EPS, fondo de pensiones, ARL y caja de compensación antes de que empiece, y pagar los aportes cada mes por la planilla PILA.', 'Pagar el salario por consignación y guardar los comprobantes y desprendibles.', 'Si el contrato es a término fijo, avisar por escrito con 30 días de anticipación si no se va a renovar.'] }
  },

  /* ---------------- SERVICIO DOMÉSTICO ---------------- */
  {
    id: 'con_servicio_domestico', tipo: 'contrato', categoria: 'empleador',
    titulo: 'Contrato de trabajo para empleada o empleado del servicio doméstico',
    resumen: 'Para trabajadoras internas o por días: funciones, horario, salario, alimentación y alojamiento, seguridad social, prima, cesantías, vacaciones y descanso, según el Código Sustantivo del Trabajo, la Ley 1788 de 2016 y el Convenio 189 de la OIT.',
    palabras: ['empleada doméstica', 'servicio doméstico', 'empleada', 'niñera', 'cuidadora', 'interna', 'por días', 'oficios varios', 'trabajo en casa de familia', 'contrato empleada', 'minerva'],
    tituloDoc: 'CONTRATO DE TRABAJO PARA EL SERVICIO DOMÉSTICO', nombreContrato: 'contrato de trabajo para el servicio doméstico',
    roles: d => ({ a: 'EL EMPLEADOR', b: ((d.miRol === 'b' ? d.genero : d.cpGenero) === 'm') ? 'EL TRABAJADOR' : 'LA TRABAJADORA' }),
    rolCampo: { opciones: [ { v: 'a', t: 'Soy el empleador (la familia que contrata)' }, { v: 'b', t: 'Soy la trabajadora o el trabajador' } ] },
    campos: [
      { id: 'modalidad', tipo: 'select', etiqueta: 'Modalidad', requerido: true, opciones: [ { v: 'interna', t: 'Interna (vive en la casa)' }, { v: 'externa', t: 'Externa de tiempo completo' }, { v: 'dias', t: 'Por días (algunos días a la semana)' } ], valorInicial: 'externa', ancho: 'media' },
      { id: 'dias', tipo: 'texto', etiqueta: 'Días de trabajo a la semana', ejemplo: 'Ej.: lunes a viernes / martes y jueves', requerido: true, ancho: 'media' },
      { id: 'horario', tipo: 'texto', etiqueta: 'Horario', ejemplo: 'Ej.: de 7:00 a. m. a 3:00 p. m.', requerido: true, ancho: 'media' },
      { id: 'salario', tipo: 'texto', etiqueta: 'Salario', ejemplo: 'Ej.: 1.423.500 mensuales / 70.000 por día', requerido: true, ancho: 'media' },
      { id: 'unidadSalario', tipo: 'select', etiqueta: 'El salario es', opciones: [ { v: 'mes', t: 'Mensual' }, { v: 'dia', t: 'Por cada día trabajado' } ], valorInicial: 'mes', ancho: 'media' },
      { id: 'lugarTrabajo', tipo: 'texto', etiqueta: 'Dirección de la casa donde trabaja', requerido: true, ancho: 'media' },
      { id: 'funciones', tipo: 'textarea', etiqueta: 'Funciones', ejemplo: 'Ej.: Aseo general de la casa, lavado y planchado de ropa, preparación de alimentos, cuidado de dos niños de 4 y 7 años.', requerido: true, filas: 2 },
      { id: 'fechaInicio', tipo: 'fecha', etiqueta: 'Fecha de inicio', requerido: true, ancho: 'media' },
      { id: 'periodoPrueba', tipo: 'select', etiqueta: 'Período de prueba', opciones: [ { v: 'dos', t: 'Sí, de dos meses' }, { v: 'uno', t: 'Sí, de un mes' }, { v: 'no', t: 'No' } ], valorInicial: 'uno', ancho: 'media' }
    ],
    opcionales: [
      { v: 'alimentacion', t: 'Se da alimentación y alojamiento (internas) y se acuerda que no son salario', clausula: { t: 'ALIMENTACIÓN Y ALOJAMIENTO', c: 'EL EMPLEADOR suministrará alimentación y, en la modalidad interna, alojamiento digno y privado. Conforme al artículo 128 del Código Sustantivo del Trabajo, las partes acuerdan expresamente que estos beneficios no constituyen salario para ningún efecto.' } },
      { v: 'transporte', t: 'Se paga el auxilio de transporte', clausula: { t: 'AUXILIO DE TRANSPORTE', c: 'Por devengar hasta dos (2) salarios mínimos y no residir en el lugar de trabajo, la persona trabajadora recibirá el auxilio legal de transporte proporcional a los días laborados.' } },
      { v: 'cuidado', t: 'Incluye cuidado de niños, personas mayores o enfermas', clausula: { t: 'CUIDADO DE PERSONAS', c: 'El cuidado de personas incluido en las funciones se prestará con las instrucciones escritas de EL EMPLEADOR sobre medicamentos, alimentación y emergencias; EL EMPLEADOR dejará los números de contacto y autorizaciones necesarias.' } }
    ],
    clausulas: (d, P) => {
      const T = P.B.rol;
      const interna = d.modalidad === 'interna';
      return [
        { t: 'OBJETO', c: `EL EMPLEADOR contrata a ${T} para prestar servicios de trabajo doméstico en la vivienda ubicada en ${d.lugarTrabajo || '[dirección]'}, en la modalidad ${R.opcionTexto(cd('con_servicio_domestico', 'modalidad'), d.modalidad, 't').toLowerCase()}, con las siguientes funciones: ${R.oracion(d.funciones)} No se exigirán labores distintas sin acuerdo previo.` },
        { t: 'JORNADA Y DESCANSO', c: `${T} trabajará ${d.dias || '[días]'}, en el horario de ${d.horario || '[horario]'}. ${interna ? 'Por tratarse de trabajo interno, la jornada no excederá de diez (10) horas diarias (Decreto 824 de 1988 y Sentencia C-372 de 1998 de la Corte Constitucional), con los descansos para alimentación y un descanso nocturno continuo.' : 'La jornada no excederá la máxima legal de cuarenta y dos (42) horas semanales.'} Tendrá derecho al descanso dominical y festivo remunerado; el trabajo en domingos o festivos se pagará con los recargos legales o se compensará con descanso.` },
        { t: 'SALARIO', c: `EL EMPLEADOR pagará ${d.unidadSalario === 'dia' ? `la suma de ${R.pesos(d.salario)} por cada día trabajado, que en ningún caso será inferior al salario mínimo diario legal vigente` : `un salario mensual de ${R.pesos(d.salario)}, que en ningún caso será inferior al salario mínimo legal mensual vigente`}, pagadero ${d.unidadSalario === 'dia' ? 'al final de cada día o semana, según se acuerde' : 'por quincenas o mensualidades vencidas'}, en dinero y con comprobante.` },
        { t: 'SEGURIDAD SOCIAL', c: `EL EMPLEADOR afiliará a ${T}, desde el inicio del contrato, a salud (EPS), pensiones, riesgos laborales (ARL) y caja de compensación familiar (Decreto 721 de 2013), y pagará mensualmente los aportes sobre el salario real${d.unidadSalario === 'dia' ? ', por los días trabajados, conforme a las normas sobre cotización por semanas' : ''}, descontando solo la parte que corresponde a la persona trabajadora.` },
        { t: 'PRESTACIONES SOCIALES', c: `${T} tendrá derecho a la prima de servicios (Ley 1788 de 2016), al auxilio de cesantía y sus intereses, a vacaciones de quince (15) días hábiles por cada año de servicio, a la dotación de calzado y vestido de labor cuando la ley lo exija y a las licencias de ley, en proporción al tiempo laborado.` },
        { t: 'DURACIÓN Y PERÍODO DE PRUEBA', c: `El contrato es a término indefinido a partir del ${R.fechaLarga(d.fechaInicio) || '[fecha]'}. ${d.periodoPrueba === 'no' ? 'No se pacta período de prueba.' : `Se pacta un período de prueba de ${d.periodoPrueba === 'dos' ? 'dos (2) meses' : 'un (1) mes'}.`}` },
        { t: 'OBLIGACIONES DE EL EMPLEADOR', c: `Tratar a ${T} con respeto y dignidad; pagar el salario y las prestaciones a tiempo; no retener sus documentos de identidad; respetar su intimidad, su descanso y su derecho a comunicarse; suministrar los elementos de aseo y protección necesarios; y expedir constancias laborales cuando las solicite.` },
        { t: 'OBLIGACIONES DE LA PERSONA TRABAJADORA', c: 'Cumplir las funciones acordadas con diligencia y honradez, cuidar los bienes de la casa, guardar reserva sobre la vida privada de la familia, avisar oportunamente las ausencias y cumplir las normas de seguridad.' },
        { t: 'TERMINACIÓN', c: 'El contrato podrá terminar por mutuo acuerdo, por renuncia, o por justa causa conforme al artículo 62 del Código Sustantivo del Trabajo, comunicada por escrito. La terminación sin justa causa por parte de EL EMPLEADOR dará lugar a la indemnización del artículo 64. A la terminación se pagará la liquidación completa de prestaciones.' },
        { t: 'NORMAS APLICABLES', c: 'Este contrato se rige por el Código Sustantivo del Trabajo, la Ley 1788 de 2016 y el Convenio 189 de la OIT sobre trabajo doméstico (Ley 1595 de 2012). Toda cláusula que desmejore los derechos mínimos se tendrá por no escrita.' },
        notif(P)
      ];
    },
    guia: { nota: 'Las trabajadoras domésticas tienen los mismos derechos que cualquier trabajador: mínimo, prima, cesantías, vacaciones, seguridad social y descanso. Pagar menos del mínimo proporcional o no afiliar a seguridad social genera deudas y sanciones.', pasos: ['Firmar dos copias y entregar una a la trabajadora.', 'Afiliar a EPS, pensión, ARL y caja de compensación antes del primer día. Para pagar la planilla hay aplicaciones y operadores autorizados (PILA) que calculan los aportes, incluso por días.', 'Pagar el salario con comprobante (transferencia o recibo firmado).', 'Consignar las cesantías al fondo antes del 15 de febrero y pagar la prima en junio y diciembre.'] }
  },

  /* ---------------- PRESTACIÓN DE SERVICIOS ---------------- */
  {
    id: 'con_prestacion_servicios', tipo: 'contrato', categoria: 'particular', retirado: true,
    titulo: 'Contrato de prestación de servicios (contratista independiente)',
    resumen: 'Para servicios profesionales, técnicos u oficios sin subordinación: objeto, entregables, honorarios, duración, seguridad social del contratista y terminación. Con advertencia sobre cuándo es realmente un contrato de trabajo.',
    palabras: ['prestación de servicios', 'contratista', 'honorarios', 'freelance', 'independiente', 'OPS', 'servicios profesionales', 'técnico', 'maestro de obra', 'contador', 'diseñador', 'asesoría'],
    tituloDoc: 'CONTRATO DE PRESTACIÓN DE SERVICIOS', nombreContrato: 'contrato de prestación de servicios',
    roles: { a: 'EL CONTRATANTE', b: 'EL CONTRATISTA' },
    rolCampo: { opciones: [ { v: 'a', t: 'Soy quien contrata el servicio (contratante)' }, { v: 'b', t: 'Soy quien presta el servicio (contratista)' } ] },
    campos: [
      { id: 'objeto', tipo: 'textarea', etiqueta: '¿Qué servicio se va a prestar?', ejemplo: 'Ej.: Diseño y desarrollo de la página web de la tienda, con catálogo de productos y carrito de compras.', requerido: true, filas: 2 },
      { id: 'entregables', tipo: 'textarea', etiqueta: 'Entregables o resultados concretos (opcional)', ejemplo: 'Ej.: 1) Diseño aprobado. 2) Sitio publicado. 3) Capacitación de 2 horas.', filas: 2 },
      { id: 'honorarios', tipo: 'texto', etiqueta: 'Valor de los honorarios', ejemplo: 'Ej.: 3.500.000', requerido: true, ancho: 'media' },
      { id: 'formaHonorarios', tipo: 'select', etiqueta: 'Forma de pago', opciones: [ { v: 'total', t: 'Valor total, pagado por etapas o al final', legal: 'valor total' }, { v: 'mensual', t: 'Valor mensual', legal: 'valor mensual' }, { v: 'hora', t: 'Valor por hora o por día', legal: 'valor por unidad de tiempo' } ], valorInicial: 'total', ancho: 'media' },
      { id: 'detallePago', tipo: 'texto', etiqueta: 'Detalle (anticipo, cuotas, fechas)', ejemplo: 'Ej.: 50 % al firmar y 50 % a la entrega final', ancho: 'completa' },
      { id: 'fechaInicio', tipo: 'fecha', etiqueta: 'Fecha de inicio', requerido: true, ancho: 'media' },
      { id: 'duracion', tipo: 'texto', etiqueta: 'Duración o fecha de entrega', ejemplo: 'Ej.: 3 meses / hasta el 15 de diciembre de 2026', requerido: true, ancho: 'media' },
      { id: 'lugar', tipo: 'texto', etiqueta: 'Lugar donde se prestará (si aplica)', ancho: 'completa' }
    ],
    opcionales: [
      { v: 'confidencialidad', t: 'Confidencialidad', clausula: { t: 'CONFIDENCIALIDAD', c: 'EL CONTRATISTA mantendrá en reserva la información a la que tenga acceso con ocasión del contrato y no la usará para fines distintos de su ejecución, durante la vigencia del contrato y dos (2) años después.' } },
      { v: 'propiedad', t: 'Lo que se produzca queda para el contratante (obra por encargo)', clausula: { t: 'PROPIEDAD INTELECTUAL', c: 'Los diseños, textos, programas y demás obras que EL CONTRATISTA elabore en ejecución de este contrato se entienden realizados por encargo, y los derechos patrimoniales sobre ellos pertenecen a EL CONTRATANTE conforme al artículo 20 de la Ley 23 de 1982, sin perjuicio de los derechos morales de autor.' } },
      { v: 'penal', t: 'Cláusula penal por incumplimiento', clausula: d => ({ t: 'CLÁUSULA PENAL', c: `El incumplimiento de cualquiera de las partes dará lugar al pago de una pena equivalente al diez por ciento (10 %) del valor del contrato (${pct(d.honorarios, 0.1)}), sin perjuicio del cumplimiento y de los perjuicios.` }) },
      { v: 'garantia', t: 'Garantía de calidad del trabajo por un tiempo', clausula: { t: 'GARANTÍA', c: 'EL CONTRATISTA garantiza la calidad del servicio y corregirá sin costo los defectos que se presenten dentro de los tres (3) meses siguientes a la entrega, siempre que sean atribuibles a su trabajo.' } }
    ],
    clausulas: (d, P) => [
      { t: 'OBJETO', c: `EL CONTRATISTA se obliga a prestar a EL CONTRATANTE, de manera independiente y con plena autonomía técnica y administrativa, el siguiente servicio: ${R.oracion(d.objeto)}${d.entregables ? ` Entregables: ${R.oracion(d.entregables)}` : ''}` },
      { t: 'HONORARIOS Y FORMA DE PAGO', c: `EL CONTRATANTE pagará a EL CONTRATISTA la suma de ${R.pesos(d.honorarios)} como ${R.opcionTexto(cd('con_prestacion_servicios', 'formaHonorarios'), d.formaHonorarios)}${d.detallePago ? `, así: ${d.detallePago}` : ''}, previa presentación de la cuenta de cobro o factura y de la constancia de pago de aportes a seguridad social. Sobre los pagos se practicarán las retenciones de ley.` },
      { t: 'DURACIÓN', c: `El contrato inicia el ${R.fechaLarga(d.fechaInicio) || '[fecha]'} y tendrá una duración de ${d.duracion || '[duración]'}${d.lugar ? `. El servicio se prestará en ${d.lugar}` : ''}.` },
      { t: 'NATURALEZA DEL CONTRATO', c: 'Este es un contrato civil de prestación de servicios. EL CONTRATISTA ejecutará el objeto con sus propios medios, sin cumplir horario ni recibir órdenes sobre la forma de hacer el trabajo, y podrá prestar servicios a terceros. En consecuencia, no existe relación laboral ni subordinación, y EL CONTRATISTA no tiene derecho a prestaciones sociales. Las partes reconocen que, si en la práctica se configuran los elementos del artículo 23 del Código Sustantivo del Trabajo, primará la realidad sobre lo escrito.' },
      { t: 'SEGURIDAD SOCIAL', c: 'EL CONTRATISTA se afiliará y cotizará como trabajador independiente a salud, pensiones y riesgos laborales sobre la base que ordena la ley (el cuarenta por ciento del valor mensual de los honorarios, sin que sea inferior a un salario mínimo), y presentará la planilla pagada antes de cada pago. EL CONTRATANTE verificará su cumplimiento y afiliará al contratista a la ARL cuando la actividad sea de riesgo IV o V.' },
      { t: 'OBLIGACIONES DE EL CONTRATISTA', c: 'Ejecutar el servicio con calidad y en los plazos acordados; informar los avances; atender las observaciones razonables de EL CONTRATANTE sobre el resultado; responder por los daños que cause por su culpa; y guardar reserva sobre la información recibida.' },
      { t: 'OBLIGACIONES DE EL CONTRATANTE', c: 'Pagar los honorarios en las fechas pactadas; suministrar la información y los accesos necesarios; y aprobar o formular observaciones a los entregables dentro de los cinco (5) días siguientes a su presentación.' },
      { t: 'TERMINACIÓN', c: 'El contrato terminará por cumplimiento del objeto, por mutuo acuerdo, por incumplimiento de cualquiera de las partes o por decisión unilateral comunicada por escrito con quince (15) días de anticipación, caso en el cual se pagarán los servicios efectivamente prestados hasta esa fecha.' },
      controversias(),
      notif(P)
    ],
    guia: { nota: 'Si hay horario, órdenes permanentes y el trabajo se hace solo para una persona, en realidad es un contrato de trabajo (principio de primacía de la realidad), aunque el papel diga "prestación de servicios". En ese caso el trabajador puede reclamar prestaciones.', pasos: ['Firmar dos copias.', 'El contratista debe pagar su seguridad social como independiente cada mes (planilla PILA) y entregar la constancia con cada cuenta de cobro.', 'Guardar los entregables y las aprobaciones por escrito (correos o chats).'] }
  },

  /* ---------------- PAGARÉ ---------------- */
  {
    id: 'con_pagare', tipo: 'contrato', categoria: 'particular',
    titulo: 'Pagaré (préstamo de dinero entre personas)',
    resumen: 'Título valor con el que quien recibe un préstamo se obliga a pagarlo en una fecha o en cuotas, con intereses dentro del límite legal. Presta mérito ejecutivo: el acreedor puede cobrarlo ante un juez sin necesidad de otro documento.',
    palabras: ['pagaré', 'préstamo', 'prestar dinero', 'prestamista', 'deuda', 'intereses', 'cuotas', 'letra', 'título valor', 'me prestaron', 'le presté', 'minerva'],
    tituloDoc: 'PAGARÉ', nombreContrato: 'pagaré',
    roles: { a: 'EL DEUDOR', b: 'EL ACREEDOR' },
    rolCampo: { opciones: [ { v: 'a', t: 'Soy quien recibe el préstamo (deudor)' }, { v: 'b', t: 'Soy quien presta el dinero (acreedor)' } ] },
    campos: [
      { id: 'monto', tipo: 'texto', etiqueta: 'Valor del préstamo', ejemplo: 'Ej.: 5.000.000', requerido: true, ancho: 'media' },
      { id: 'numero', tipo: 'texto', etiqueta: 'Número del pagaré (opcional)', ejemplo: 'Ej.: 001', ancho: 'media' },
      { id: 'formaPago', tipo: 'radio', etiqueta: '¿Cómo se paga?', requerido: true, opciones: [ { v: 'fecha', t: 'Todo en una fecha' }, { v: 'cuotas', t: 'En cuotas' } ] },
      { id: 'fechaVencimiento', tipo: 'fecha', etiqueta: 'Fecha de pago', mostrarSi: { campo: 'formaPago', valor: 'fecha' }, ancho: 'media' },
      { id: 'numeroCuotas', tipo: 'texto', etiqueta: 'Número de cuotas', ejemplo: 'Ej.: 10', mostrarSi: { campo: 'formaPago', valor: 'cuotas' }, ancho: 'media' },
      { id: 'valorCuota', tipo: 'texto', etiqueta: 'Valor de cada cuota', ejemplo: 'Ej.: 550.000', mostrarSi: { campo: 'formaPago', valor: 'cuotas' }, ancho: 'media' },
      { id: 'fechaPrimeraCuota', tipo: 'fecha', etiqueta: 'Fecha de la primera cuota', mostrarSi: { campo: 'formaPago', valor: 'cuotas' }, ancho: 'media' },
      { id: 'interes', tipo: 'texto', etiqueta: 'Interés mensual acordado (%); déjalo vacío si no hay', ejemplo: 'Ej.: 1,5', ayuda: 'No puede superar el límite de usura que certifica la Superintendencia Financiera (aproximadamente 1,5 veces el interés bancario corriente). Cobrar más es delito.', ancho: 'media' },
      { id: 'lugarPago', tipo: 'texto', etiqueta: 'Lugar o medio de pago', ejemplo: 'Ej.: Consignación a la cuenta Nequi 300 123 4567 / en Medellín, en efectivo', requerido: true, ancho: 'media' },
      { id: 'codeudor', tipo: 'texto', etiqueta: 'Codeudor (nombre y cédula), si lo hay', ancho: 'completa' }
    ],
    encabezado: (d, P) => [`PAGARÉ No. ${d.numero || '___'} · Valor: ${R.moneda(d.monto) || '$____'} · ${d.formaPago === 'cuotas' ? `${R.numeroLetras(d.numeroCuotas || 1)} cuotas` : `Vence: ${R.fechaLarga(d.fechaVencimiento) || '[fecha]'}`} · Lugar y fecha de creación: ${d.ciudad || '[ciudad]'}, ${R.fechaLarga(d.fechaFirma) || R.fechaLarga(R.hoy())}`],
    intro: (d, P) => `Yo, ${P.A.ident}, en mi condición de DEUDOR, declaro que debo y pagaré incondicionalmente, a la orden de ${P.B.ident}, o a quien represente sus derechos, en ${d.lugarPago || '[lugar de pago]'}, la suma de ${R.pesos(d.monto)}, que recibí a título de préstamo (mutuo) a mi entera satisfacción, ${d.formaPago === 'cuotas' ? `en ${R.numeroLetras(d.numeroCuotas || 1)} cuotas mensuales y sucesivas de ${R.pesos(d.valorCuota)} cada una, la primera el ${R.fechaLarga(d.fechaPrimeraCuota) || '[fecha]'} y las siguientes el mismo día de cada mes` : `el día ${R.fechaLarga(d.fechaVencimiento) || '[fecha de vencimiento]'}`}, bajo las siguientes condiciones:`,
    clausulas: (d, P) => {
      const c = [];
      c.push({ t: 'INTERESES DE PLAZO', c: d.interes ? `Sobre el capital se reconocerán intereses de plazo del ${d.interes} % mensual, pagaderos junto con el capital o con cada cuota, tasa que no supera el límite máximo legal certificado por la Superintendencia Financiera de Colombia.` : 'El préstamo no causa intereses de plazo.' });
      c.push({ t: 'INTERESES DE MORA', c: 'En caso de mora, el capital causará intereses moratorios a la tasa máxima legal permitida, desde el día siguiente al vencimiento y hasta el pago total, sin necesidad de requerimiento ni constitución en mora, a los que renuncio.' });
      if (d.formaPago === 'cuotas') c.push({ t: 'CLÁUSULA ACELERATORIA', c: 'El no pago oportuno de una cualquiera de las cuotas facultará a EL ACREEDOR para declarar vencido el plazo y exigir de inmediato el pago total del saldo del capital con sus intereses.' });
      if (d.codeudor) c.push({ t: 'CODEUDOR', c: `${R.mayus(d.codeudor)} se obliga solidariamente con EL DEUDOR al pago de este pagaré, en las mismas condiciones, y firma en señal de aceptación.` });
      c.push({ t: 'RENUNCIAS Y GASTOS', c: 'Renuncio a la presentación para el pago, al protesto y a los avisos de rechazo. Los gastos de cobranza judicial o extrajudicial, incluidos honorarios de abogado, serán a mi cargo. Este pagaré presta mérito ejecutivo conforme a los artículos 709 y siguientes del Código de Comercio.' });
      return c;
    },
    cierre: (d, P) => `Firmado en ${d.ciudad || '[ciudad]'}, el ${R.fechaLarga(d.fechaFirma) || R.fechaLarga(R.hoy())}.`,
    firmas: (d, P) => { const f = [{ rol: 'EL DEUDOR', lines: P.A.firma }]; if (d.codeudor) f.push({ rol: 'CODEUDOR', lines: [R.mayus(d.codeudor)] }); return f; },
    guia: { nota: 'Cobrar intereses por encima del límite de usura es un delito (artículo 305 del Código Penal). El interés bancario corriente y el límite de usura se publican cada mes en www.superfinanciera.gov.co.', pasos: ['Solo firma el deudor (y el codeudor). El acreedor conserva el original: es el único documento con el que puede cobrar.', 'Autenticar la firma en notaría es opcional, pero le da más fuerza probatoria.', 'Cuando el deudor pague, debe exigir que le devuelvan el pagaré original o que le escriban "cancelado" con firma y fecha, y pedir recibo.', 'El pagaré prescribe a los tres años desde el vencimiento (artículo 789 del Código de Comercio).'] }
  },

  /* ---------------- PODER ESPECIAL ---------------- */
  {
    id: 'con_poder', tipo: 'contrato', categoria: 'particular',
    titulo: 'Poder especial para que otra persona haga un trámite por ti',
    resumen: 'Autoriza a una persona de confianza a reclamar documentos, firmar, recibir dinero o representarte en un trámite concreto ante una entidad, un banco, una notaría o un empleador.',
    palabras: ['poder', 'autorización', 'autorizar', 'apoderado', 'representar', 'reclamar por mí', 'trámite', 'firmar por mí', 'recoger documentos', 'poder especial', 'carta poder'],
    tituloDoc: 'PODER ESPECIAL', nombreContrato: 'poder especial',
    roles: { a: 'EL PODERDANTE', b: 'EL APODERADO' },
    rolCampo: { opciones: [ { v: 'a', t: 'Soy quien da el poder (poderdante)' }, { v: 'b', t: 'Soy quien recibe el poder (apoderado)' } ] },
    campos: [
      { id: 'tramite', tipo: 'textarea', etiqueta: '¿Qué trámite o gestión debe hacer el apoderado? (sé muy específico)', ejemplo: 'Ej.: Reclamar y recibir mi liquidación de prestaciones sociales en Confecciones del Norte S.A.S., firmar los documentos necesarios y recibir el pago.', requerido: true, filas: 3 },
      { id: 'entidad', tipo: 'texto', etiqueta: '¿Ante qué entidad, empresa o persona?', ejemplo: 'Ej.: Confecciones del Norte S.A.S. / Colpensiones / Notaría 5 de Cali', requerido: true, ancho: 'completa' },
      { id: 'vigencia', tipo: 'texto', etiqueta: '¿Hasta cuándo vale el poder?', ejemplo: 'Ej.: hasta el 31 de diciembre de 2026 / hasta que termine el trámite', valorInicial: 'hasta que termine el trámite', ancho: 'media' },
      { id: 'facultades', tipo: 'checks', etiqueta: 'Facultades adicionales', opciones: [ { v: 'recibir', t: 'Recibir dinero, cheques o bienes a mi nombre', legal: 'recibir dineros, cheques, títulos o bienes en mi nombre y expedir los recibos correspondientes' }, { v: 'firmar', t: 'Firmar documentos y formularios', legal: 'firmar los documentos, formularios, actas y constancias que el trámite exija' }, { v: 'desistir', t: 'Desistir, conciliar o transigir', legal: 'desistir, conciliar, transigir y recibir notificaciones' }, { v: 'sustituir', t: 'Sustituir el poder en otra persona', legal: 'sustituir este poder y reasumirlo cuando lo considere conveniente' } ] }
    ],
    intro: (d, P) => `Yo, ${P.A.ident}, por medio del presente documento confiero PODER ESPECIAL, AMPLIO Y SUFICIENTE a ${P.B.ident}, para que en mi nombre y representación adelante ante ${d.entidad || '[entidad]'} la siguiente gestión: ${R.oracion(d.tramite)}`,
    clausulas: (d, P) => [
      { t: 'FACULTADES', c: `EL APODERADO queda facultado para presentar solicitudes, aportar y retirar documentos, solicitar copias, atender requerimientos${(d.facultades || []).length ? `, ${R.lista(d.facultades.map(f => R.opcionTexto(cd('con_poder', 'facultades'), f)))}` : ''} y, en general, realizar todos los actos necesarios para cumplir el encargo, sin exceder su objeto.` },
      { t: 'VIGENCIA', c: `Este poder estará vigente ${d.vigencia || 'hasta que termine el trámite'}, y podrá ser revocado por EL PODERDANTE en cualquier momento mediante comunicación escrita.` },
      { t: 'RENDICIÓN DE CUENTAS', c: 'EL APODERADO informará a EL PODERDANTE el resultado de la gestión y le entregará los documentos, dineros o bienes que reciba, con los soportes correspondientes.' }
    ],
    cierre: (d, P) => `Para constancia se firma en ${d.ciudad || '[ciudad]'}, el ${R.fechaLarga(d.fechaFirma) || R.fechaLarga(R.hoy())}. EL APODERADO acepta el poder conferido.`,
    firmas: (d, P) => [{ rol: 'EL PODERDANTE', lines: P.A.firma }, { rol: 'EL APODERADO (acepta)', lines: P.B.firma }],
    guia: { nota: 'Para trámites ante entidades públicas, notarías, bancos y empresas, el poder normalmente debe llevar presentación personal (reconocimiento de la firma) del poderdante ante notario. Para actuar ante un juez (salvo en tutela), el apoderado debe ser abogado.', pasos: ['Imprimir, firmar y llevar a la notaría para la presentación personal (diligencia breve y de bajo costo). Algunas entidades aceptan autorización simple con copia de la cédula: pregunta antes.', 'Entregar al apoderado el poder original y copia de la cédula del poderdante.', 'Pedir al apoderado los soportes de lo que reciba o firme.'] }
  },

  /* ---------------- ACUERDO DE PAGO ---------------- */
  {
    id: 'con_acuerdo_pago', tipo: 'contrato', categoria: 'particular',
    titulo: 'Acuerdo de pago de una deuda (reconocimiento y cuotas)',
    resumen: 'Deja por escrito cuánto se debe, por qué, y cómo se va a pagar: cuotas, fechas, intereses y qué pasa si se incumple. Sirve para arriendos atrasados, préstamos, daños o cuentas pendientes.',
    palabras: ['acuerdo de pago', 'deuda', 'me deben', 'debo', 'cuotas', 'reconocimiento de deuda', 'arriendo atrasado', 'préstamo', 'plan de pagos', 'refinanciar', 'conciliación'],
    tituloDoc: 'ACUERDO DE PAGO Y RECONOCIMIENTO DE DEUDA', nombreContrato: 'acuerdo de pago',
    roles: { a: 'EL DEUDOR', b: 'EL ACREEDOR' },
    rolCampo: { opciones: [ { v: 'a', t: 'Soy quien debe (deudor)' }, { v: 'b', t: 'Soy a quien le deben (acreedor)' } ] },
    campos: [
      { id: 'monto', tipo: 'texto', etiqueta: 'Valor total de la deuda', requerido: true, ancho: 'media' },
      { id: 'origen', tipo: 'texto', etiqueta: '¿De dónde viene la deuda?', ejemplo: 'Ej.: arriendos de junio, julio y agosto de 2026 / préstamo del 10 de marzo de 2026 / daño del vehículo en el choque del 2 de mayo', requerido: true, ancho: 'completa' },
      { id: 'numeroCuotas', tipo: 'texto', etiqueta: 'Número de cuotas', requerido: true, ancho: 'media' },
      { id: 'valorCuota', tipo: 'texto', etiqueta: 'Valor de cada cuota', requerido: true, ancho: 'media' },
      { id: 'fechaPrimeraCuota', tipo: 'fecha', etiqueta: 'Fecha de la primera cuota', requerido: true, ancho: 'media' },
      { id: 'medioPago', tipo: 'texto', etiqueta: 'Medio de pago', ejemplo: 'Ej.: transferencia a la cuenta de ahorros Davivienda 0012-3456-7890', requerido: true, ancho: 'media' },
      { id: 'interes', tipo: 'texto', etiqueta: 'Interés mensual acordado (%), si lo hay', ancho: 'media' }
    ],
    opcionales: [
      { v: 'condonacion', t: 'Si el deudor cumple, el acreedor perdona intereses o parte de la deuda', clausula: { t: 'BENEFICIO POR CUMPLIMIENTO', c: 'Si EL DEUDOR paga puntualmente la totalidad de las cuotas, EL ACREEDOR condonará los intereses de mora causados hasta la fecha de este acuerdo y cualquier suma adicional derivada del incumplimiento anterior.' } },
      { v: 'reportes', t: 'El acreedor retirará reportes negativos al terminar de pagar', clausula: { t: 'REPORTES', c: 'Dentro de los diez (10) días siguientes al pago total, EL ACREEDOR actualizará o retirará los reportes negativos que haya efectuado en centrales de riesgo y expedirá el paz y salvo correspondiente.' } }
    ],
    clausulas: (d, P) => [
      { t: 'RECONOCIMIENTO DE LA DEUDA', c: `EL DEUDOR reconoce que adeuda a EL ACREEDOR la suma de ${R.pesos(d.monto)}, por concepto de ${d.origen || '[origen de la deuda]'}, suma que acepta como cierta, líquida y exigible.` },
      { t: 'FORMA DE PAGO', c: `EL DEUDOR pagará la deuda en ${R.numeroLetras(d.numeroCuotas || 1)} cuotas mensuales de ${R.pesos(d.valorCuota)} cada una, la primera el ${R.fechaLarga(d.fechaPrimeraCuota) || '[fecha]'} y las siguientes el mismo día de los meses subsiguientes, mediante ${d.medioPago || '[medio de pago]'}. EL ACREEDOR expedirá recibo de cada pago.` },
      { t: 'INTERESES', c: d.interes ? `Sobre el saldo se causarán intereses de plazo del ${d.interes} % mensual, dentro del límite legal. En caso de mora se causarán intereses moratorios a la tasa máxima legal.` : 'El saldo no causará intereses de plazo mientras se cumpla el acuerdo. En caso de mora se causarán intereses moratorios a la tasa máxima legal.' },
      { t: 'INCUMPLIMIENTO', c: 'El no pago de una cuota en la fecha pactada facultará a EL ACREEDOR para exigir de inmediato la totalidad del saldo, con sus intereses, y para iniciar el cobro judicial. Este acuerdo presta mérito ejecutivo.' },
      { t: 'PAZ Y SALVO', c: 'Pagada la totalidad de la deuda, EL ACREEDOR expedirá paz y salvo dentro de los cinco (5) días siguientes y las partes se declararán mutuamente a paz y salvo por el concepto indicado.' },
      controversias(),
      notif(P)
    ],
    guia: { nota: 'Este acuerdo no reemplaza el contrato o la obligación original, la complementa: define cómo se paga. Si la deuda es de un arriendo, no interrumpe por sí sola un proceso de restitución salvo que así se pacte.', pasos: ['Firmar dos copias; cada parte guarda una.', 'Pagar siempre por un medio que deje rastro (transferencia) y pedir recibo.', 'Al terminar de pagar, exigir el paz y salvo por escrito.'] }
  },

  /* ---------------- RECIBO DE PAGO / PAZ Y SALVO ---------------- */
  {
    id: 'con_recibo', tipo: 'contrato', categoria: 'particular',
    titulo: 'Recibo de pago o paz y salvo',
    resumen: 'Constancia de que una persona recibió dinero de otra por un concepto (arriendo, préstamo, trabajo, venta), con saldo pendiente o paz y salvo total.',
    palabras: ['recibo', 'paz y salvo', 'constancia de pago', 'recibí', 'pagué', 'comprobante', 'abono', 'cancelación'],
    tituloDoc: d => d.saldo === 'total' ? 'RECIBO DE PAGO Y PAZ Y SALVO' : 'RECIBO DE PAGO', nombreContrato: 'recibo',
    roles: { a: 'QUIEN RECIBE', b: 'QUIEN PAGA' },
    rolCampo: { opciones: [ { v: 'a', t: 'Soy quien recibe el dinero y firma el recibo' }, { v: 'b', t: 'Soy quien paga' } ] },
    campos: [
      { id: 'monto', tipo: 'texto', etiqueta: 'Valor recibido', requerido: true, ancho: 'media' },
      { id: 'formaPago', tipo: 'select', etiqueta: 'Forma de pago', opciones: [ { v: 'efectivo', t: 'Efectivo', legal: 'en efectivo' }, { v: 'transferencia', t: 'Transferencia o consignación', legal: 'mediante transferencia o consignación bancaria' }, { v: 'cheque', t: 'Cheque', legal: 'mediante cheque' } ], valorInicial: 'efectivo', ancho: 'media' },
      { id: 'concepto', tipo: 'texto', etiqueta: '¿Por qué concepto?', ejemplo: 'Ej.: arriendo del mes de octubre de 2026 del apartamento 301 / abono al préstamo del 10 de marzo / pago del trabajo de pintura', requerido: true, ancho: 'completa' },
      { id: 'saldo', tipo: 'radio', etiqueta: '¿Queda algún saldo pendiente?', requerido: true, opciones: [ { v: 'total', t: 'No: con este pago queda todo cancelado (paz y salvo)' }, { v: 'parcial', t: 'Sí, queda un saldo (indica cuánto)' } ] },
      { id: 'saldoValor', tipo: 'texto', etiqueta: 'Saldo que queda pendiente', mostrarSi: { campo: 'saldo', valor: 'parcial' }, ancho: 'media' }
    ],
    intro: (d, P) => `Yo, ${P.A.ident}, declaro que he recibido de ${P.B.ident}, la suma de ${R.pesos(d.monto)}, ${R.opcionTexto(cd('con_recibo', 'formaPago'), d.formaPago)}, por concepto de ${d.concepto || '[concepto]'}. ${d.saldo === 'total' ? 'Con este pago la obligación indicada queda cancelada en su totalidad, y declaro a quien paga a PAZ Y SALVO por este concepto.' : `Queda pendiente un saldo de ${R.pesos(d.saldoValor)}.`}`,
    clausulas: () => [],
    cierre: (d, P) => `Para constancia se firma en ${d.ciudad || '[ciudad]'}, el ${R.fechaLarga(d.fechaFirma) || R.fechaLarga(R.hoy())}.`,
    firmas: (d, P) => [{ rol: 'QUIEN RECIBE', lines: P.A.firma }],
    guia: { nota: 'Quien paga debe guardar el recibo original firmado por quien recibe. Si el pago fue por transferencia, guarda también el comprobante.', pasos: ['Imprimir y firmar por quien recibe el dinero; entregar el original a quien paga.', 'Si es el último pago, pedir que diga expresamente "paz y salvo".'] }
  }
  );
})();
