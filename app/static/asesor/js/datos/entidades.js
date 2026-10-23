/* ============================================================
   entidades.js — Catálogo de entidades y destinatarios frecuentes,
   categorías (para saber ante qué juez va una tutela y qué normas
   aplican) y directorio de ayuda gratuita.
   ============================================================ */
window.AJ = window.AJ || {};

AJ.entidades = {
  /* Categorías de destinatario. "juez" indica a qué juez se reparte una tutela
     según el Decreto 1069 de 2015 (modificado por el Decreto 333 de 2021). */
  categorias: [
    { id: 'municipio', nombre: 'Alcaldía o entidad del municipio', icono: 'edificio', orden: 'municipal', naturaleza: 'publica', juez: 'municipal',
      descripcion: 'Secretarías (Planeación, Gobierno, Salud, Educación, Hacienda, Tránsito), Sisbén, Inspección de Policía, Comisaría de Familia, Personería, Catastro, empresas municipales.' },
    { id: 'departamento', nombre: 'Gobernación o entidad del departamento', icono: 'edificio', orden: 'departamental', naturaleza: 'publica', juez: 'municipal',
      descripcion: 'Secretarías departamentales de Salud, Educación, Hacienda, Tránsito departamental, hospitales departamentales.' },
    { id: 'nacional', nombre: 'Entidad del Gobierno nacional (Colpensiones, ICBF, Migración, DIAN, ministerios…)', icono: 'bandera', orden: 'nacional', naturaleza: 'publica', juez: 'circuito',
      descripcion: 'Colpensiones, UGPP, ICBF, Migración Colombia, Unidad para las Víctimas, Registraduría, DIAN, Policía, Fiscalía, ministerios, SENA, ICETEX, Prosperidad Social, UNP, superintendencias.' },
    { id: 'eps', nombre: 'EPS, IPS, clínica u hospital', icono: 'salud', orden: 'particular', naturaleza: 'privada', juez: 'municipal',
      descripcion: 'Entidades promotoras de salud (régimen contributivo o subsidiado), clínicas, hospitales, ARL y regímenes especiales (Magisterio, Policía, Ejército).' },
    { id: 'pensiones', nombre: 'Fondo de pensiones o cesantías', icono: 'pension', orden: 'particular', naturaleza: 'privada', juez: 'municipal',
      descripcion: 'Porvenir, Protección, Colfondos, Skandia (privados). Colpensiones es entidad pública nacional.' },
    { id: 'empleador', nombre: 'Empleador o empresa privada', icono: 'trabajo', orden: 'particular', naturaleza: 'privada', juez: 'municipal',
      descripcion: 'Empresas, empleadores de servicio doméstico, contratantes por prestación de servicios, cooperativas.' },
    { id: 'spd', nombre: 'Empresa de servicios públicos', icono: 'servicios', orden: 'particular', naturaleza: 'privada', juez: 'municipal',
      descripcion: 'Acueducto, energía, gas, aseo, internet, telefonía y televisión.' },
    { id: 'financiera', nombre: 'Banco, cooperativa o central de riesgo (Datacrédito, TransUnion)', icono: 'banco', orden: 'particular', naturaleza: 'privada', juez: 'municipal',
      descripcion: 'Bancos, cooperativas financieras, empresas de cobranza, Datacrédito (Experian), TransUnion (antes CIFIN), Procrédito.' },
    { id: 'educacion', nombre: 'Colegio, universidad o instituto', icono: 'educacion', orden: 'particular', naturaleza: 'mixta', juez: 'municipal',
      descripcion: 'Colegios públicos y privados, universidades, SENA, ICETEX, secretarías de educación.' },
    { id: 'judicial', nombre: 'Juzgado, Fiscalía o autoridad judicial', icono: 'balanza', orden: 'nacional', naturaleza: 'publica', juez: 'tribunal',
      descripcion: 'Juzgados, tribunales, Fiscalía. La tutela se reparte al superior funcional del despacho accionado (contra un juzgado municipal: juez del circuito; contra un juzgado del circuito: Tribunal Superior).' },
    { id: 'particular', nombre: 'Una persona, un almacén o un negocio (arrendador, vecino, tienda, vendedor)', icono: 'persona', orden: 'particular', naturaleza: 'privada', juez: 'municipal',
      descripcion: 'Arrendadores, vecinos, almacenes, prestadores de servicios, aseguradoras.' }
  ],

  /* Dependencias típicas de una alcaldía: ayudan a dirigir correctamente la petición. */
  dependenciasMunicipio: [
    { nombre: 'Secretaría de Planeación', temas: 'licencias, uso del suelo, estratificación, nomenclatura, POT, obras, Sisbén' },
    { nombre: 'Secretaría de Gobierno', temas: 'convivencia, inspecciones de policía, espacio público, seguridad' },
    { nombre: 'Secretaría de Hacienda', temas: 'impuesto predial, industria y comercio, paz y salvos, cobro coactivo' },
    { nombre: 'Secretaría de Tránsito y Transporte', temas: 'comparendos, fotomultas, licencias de conducción, matrículas' },
    { nombre: 'Secretaría de Salud', temas: 'afiliación al régimen subsidiado, Sisbén en salud, saneamiento, quejas contra EPS' },
    { nombre: 'Secretaría de Educación', temas: 'cupos escolares, traslados, PAE, transporte escolar, quejas contra colegios' },
    { nombre: 'Secretaría de Infraestructura u Obras Públicas', temas: 'vías, andenes, alumbrado, puentes, alcantarillado' },
    { nombre: 'Secretaría de Desarrollo Social o Bienestar', temas: 'programas sociales, adulto mayor, discapacidad, víctimas' },
    { nombre: 'Oficina del Sisbén', temas: 'encuesta, actualización, corrección de datos, puntaje' },
    { nombre: 'Inspección de Policía', temas: 'ruido, perturbación, invasiones, convivencia entre vecinos' },
    { nombre: 'Comisaría de Familia', temas: 'violencia intrafamiliar, custodia, alimentos, medidas de protección' },
    { nombre: 'Personería Municipal', temas: 'quejas contra funcionarios, derechos humanos, ayuda para tutelas' },
    { nombre: 'Oficina de Catastro', temas: 'avalúos, cédula catastral, correcciones del predio' },
    { nombre: 'Enlace de Víctimas', temas: 'declaraciones, ayuda humanitaria, orientación a víctimas' },
    { nombre: 'Umata o Secretaría de Agricultura', temas: 'asistencia técnica rural, proyectos productivos' },
    { nombre: 'Despacho del Alcalde', temas: 'cuando no se sabe qué dependencia es la competente' }
  ],

  /* Lista para autocompletar el nombre de la entidad. */
  lista: [
    // EPS
    { nombre: 'Nueva EPS', cat: 'eps' }, { nombre: 'EPS Sanitas', cat: 'eps' }, { nombre: 'EPS Sura', cat: 'eps' },
    { nombre: 'Salud Total EPS', cat: 'eps' }, { nombre: 'Compensar EPS', cat: 'eps' }, { nombre: 'Famisanar EPS', cat: 'eps' },
    { nombre: 'Coosalud EPS', cat: 'eps' }, { nombre: 'Mutual Ser EPS', cat: 'eps' }, { nombre: 'Savia Salud EPS', cat: 'eps' },
    { nombre: 'Emssanar EPS', cat: 'eps' }, { nombre: 'Asmet Salud EPS', cat: 'eps' }, { nombre: 'Capital Salud EPS', cat: 'eps' },
    { nombre: 'Aliansalud EPS', cat: 'eps' }, { nombre: 'Servicio Occidental de Salud (SOS) EPS', cat: 'eps' }, { nombre: 'Comfenalco Valle EPS', cat: 'eps' },
    { nombre: 'Cajacopi EPS', cat: 'eps' }, { nombre: 'Dusakawi EPSI', cat: 'eps' }, { nombre: 'Pijaos Salud EPSI', cat: 'eps' },
    { nombre: 'Salud Bolívar EPS', cat: 'eps' }, { nombre: 'Anas Wayuu EPSI', cat: 'eps' }, { nombre: 'Mallamas EPSI', cat: 'eps' },
    { nombre: 'Fondo Nacional de Prestaciones Sociales del Magisterio (Fomag)', cat: 'nacional' },
    { nombre: 'Dirección de Sanidad de la Policía Nacional', cat: 'nacional' }, { nombre: 'Dirección de Sanidad del Ejército Nacional', cat: 'nacional' },
    // Pensiones y cesantías
    { nombre: 'Colpensiones (Administradora Colombiana de Pensiones)', cat: 'nacional' }, { nombre: 'Porvenir', cat: 'pensiones' },
    { nombre: 'Protección', cat: 'pensiones' }, { nombre: 'Colfondos', cat: 'pensiones' }, { nombre: 'Skandia', cat: 'pensiones' },
    { nombre: 'Fondo Nacional del Ahorro', cat: 'nacional' }, { nombre: 'UGPP (Unidad de Gestión Pensional y Parafiscales)', cat: 'nacional' },
    { nombre: 'Fopep (Fondo de Pensiones Públicas del Nivel Nacional)', cat: 'nacional' },
    // ARL
    { nombre: 'ARL Sura', cat: 'eps' }, { nombre: 'Positiva Compañía de Seguros (ARL)', cat: 'nacional' }, { nombre: 'ARL Colmena', cat: 'eps' },
    { nombre: 'ARL Bolívar', cat: 'eps' }, { nombre: 'ARL Axa Colpatria', cat: 'eps' }, { nombre: 'ARL Equidad', cat: 'eps' },
    // Entidades nacionales
    { nombre: 'ICBF (Instituto Colombiano de Bienestar Familiar)', cat: 'nacional' }, { nombre: 'Migración Colombia', cat: 'nacional' },
    { nombre: 'Unidad para la Atención y Reparación Integral a las Víctimas', cat: 'nacional' }, { nombre: 'Unidad Nacional de Protección (UNP)', cat: 'nacional' },
    { nombre: 'Registraduría Nacional del Estado Civil', cat: 'nacional' }, { nombre: 'DIAN', cat: 'nacional' }, { nombre: 'Policía Nacional', cat: 'nacional' },
    { nombre: 'Fiscalía General de la Nación', cat: 'judicial' }, { nombre: 'Procuraduría General de la Nación', cat: 'judicial' },
    { nombre: 'Defensoría del Pueblo', cat: 'nacional' }, { nombre: 'Prosperidad Social (DPS)', cat: 'nacional' }, { nombre: 'SENA', cat: 'educacion' },
    { nombre: 'ICETEX', cat: 'educacion' }, { nombre: 'Ministerio de Salud y Protección Social', cat: 'nacional' }, { nombre: 'Ministerio del Trabajo', cat: 'nacional' },
    { nombre: 'Ministerio de Educación Nacional', cat: 'nacional' }, { nombre: 'Ministerio de Vivienda, Ciudad y Territorio', cat: 'nacional' },
    { nombre: 'Agencia Nacional de Tierras', cat: 'nacional' }, { nombre: 'Superintendencia Nacional de Salud', cat: 'nacional' },
    { nombre: 'Superintendencia de Servicios Públicos Domiciliarios', cat: 'nacional' }, { nombre: 'Superintendencia de Industria y Comercio', cat: 'nacional' },
    { nombre: 'Superintendencia Financiera de Colombia', cat: 'nacional' }, { nombre: 'Superintendencia de Notariado y Registro', cat: 'nacional' },
    { nombre: 'Superintendencia de Transporte', cat: 'nacional' }, { nombre: 'Departamento Nacional de Planeación (DNP) – Sisbén', cat: 'nacional' },
    { nombre: 'Instituto Nacional Penitenciario y Carcelario (INPEC)', cat: 'nacional' }, { nombre: 'Ejército Nacional', cat: 'nacional' },
    { nombre: 'Cancillería – Ministerio de Relaciones Exteriores', cat: 'nacional' }, { nombre: 'Caja de Retiro de las Fuerzas Militares', cat: 'nacional' },
    // Servicios públicos
    { nombre: 'EPM (Empresas Públicas de Medellín)', cat: 'spd' }, { nombre: 'Emcali', cat: 'spd' }, { nombre: 'Empresa de Acueducto y Alcantarillado de Bogotá', cat: 'spd' },
    { nombre: 'Enel Colombia (Codensa)', cat: 'spd' }, { nombre: 'Air-e', cat: 'spd' }, { nombre: 'Afinia', cat: 'spd' }, { nombre: 'Celsia', cat: 'spd' },
    { nombre: 'Vanti (Gas Natural)', cat: 'spd' }, { nombre: 'Triple A', cat: 'spd' }, { nombre: 'Acuavalle', cat: 'spd' }, { nombre: 'Aguas de Cartagena', cat: 'spd' },
    { nombre: 'Electrohuila', cat: 'spd' }, { nombre: 'Electrocaquetá', cat: 'spd' }, { nombre: 'Cedenar', cat: 'spd' }, { nombre: 'EMSA (Electrificadora del Meta)', cat: 'spd' },
    { nombre: 'Claro', cat: 'spd' }, { nombre: 'Movistar', cat: 'spd' }, { nombre: 'Tigo', cat: 'spd' }, { nombre: 'ETB', cat: 'spd' }, { nombre: 'WOM', cat: 'spd' },
    // Financieras
    { nombre: 'Bancolombia', cat: 'financiera' }, { nombre: 'Banco de Bogotá', cat: 'financiera' }, { nombre: 'Davivienda', cat: 'financiera' },
    { nombre: 'BBVA Colombia', cat: 'financiera' }, { nombre: 'Banco Popular', cat: 'financiera' }, { nombre: 'Banco de Occidente', cat: 'financiera' },
    { nombre: 'Banco Caja Social', cat: 'financiera' }, { nombre: 'Banco Agrario de Colombia', cat: 'financiera' }, { nombre: 'Scotiabank Colpatria', cat: 'financiera' },
    { nombre: 'Banco Falabella', cat: 'financiera' }, { nombre: 'Banco Pichincha', cat: 'financiera' }, { nombre: 'Banco AV Villas', cat: 'financiera' },
    { nombre: 'Nequi', cat: 'financiera' }, { nombre: 'Daviplata', cat: 'financiera' }, { nombre: 'Nu Colombia', cat: 'financiera' },
    { nombre: 'Datacrédito Experian', cat: 'financiera' }, { nombre: 'TransUnion (CIFIN)', cat: 'financiera' }, { nombre: 'Procrédito', cat: 'financiera' },
    // Cajas de compensación
    { nombre: 'Compensar (Caja de Compensación)', cat: 'empleador' }, { nombre: 'Colsubsidio', cat: 'empleador' }, { nombre: 'Cafam', cat: 'empleador' },
    { nombre: 'Comfama', cat: 'empleador' }, { nombre: 'Comfenalco Antioquia', cat: 'empleador' }, { nombre: 'Comfandi', cat: 'empleador' }
  ],

  /* Directorio de ayuda gratuita y canales oficiales. */
  directorio: [
    { nombre: 'Personería Municipal', queHace: 'Te ayuda gratis a redactar y presentar tutelas y derechos de petición, recibe quejas contra funcionarios y vigila los derechos humanos. Hay una en cada municipio, normalmente en la alcaldía.', canal: 'Oficina en tu municipio' },
    { nombre: 'Defensoría del Pueblo', queHace: 'Orientación jurídica gratuita, defensores públicos y acompañamiento en tutelas y casos de derechos humanos.', canal: 'www.defensoria.gov.co · Línea gratuita nacional 01 8000 914 814' },
    { nombre: 'Tutela en Línea (Rama Judicial)', queHace: 'Portal oficial para radicar acciones de tutela por internet, las 24 horas, sin costo. El sistema la reparte automáticamente al juez.', canal: 'https://procesojudicial.ramajudicial.gov.co/TutelaEnLinea' },
    { nombre: 'Consultorios jurídicos de universidades', queHace: 'Estudiantes de derecho supervisados por abogados atienden gratis casos de personas de escasos recursos (laboral, familia, civil, penal menor, tutelas).', canal: 'Facultades de derecho de tu ciudad' },
    { nombre: 'Casas de Justicia', queHace: 'Reúnen en un solo lugar Comisaría de Familia, Inspección de Policía, Fiscalía local, conciliadores, ICBF y consultorio jurídico.', canal: 'Ministerio de Justicia · www.minjusticia.gov.co' },
    { nombre: 'Superintendencia Nacional de Salud', queHace: 'Quejas contra EPS e IPS por negación o demora de servicios, mala atención, cobros indebidos. Puede ordenar la prestación del servicio.', canal: 'www.supersalud.gov.co · Línea 01 8000 513 700' },
    { nombre: 'Superintendencia de Servicios Públicos Domiciliarios', queHace: 'Segunda instancia (apelación) de reclamos contra empresas de agua, energía, gas y aseo. Recibe quejas por mal servicio.', canal: 'www.superservicios.gov.co' },
    { nombre: 'Superintendencia de Industria y Comercio', queHace: 'Protección al consumidor (garantías, publicidad engañosa), datos personales (hábeas data) y servicios de telefonía e internet.', canal: 'www.sic.gov.co' },
    { nombre: 'Superintendencia Financiera', queHace: 'Quejas contra bancos, aseguradoras y fondos de pensiones privados, después de acudir al Defensor del Consumidor Financiero de la entidad.', canal: 'www.superfinanciera.gov.co' },
    { nombre: 'Ministerio del Trabajo', queHace: 'Quejas contra empleadores por no pago de salarios, prestaciones o seguridad social; inspección laboral; autorizaciones de despido.', canal: 'www.mintrabajo.gov.co · Línea 120' },
    { nombre: 'ICBF – Línea 141', queHace: 'Protección de niños, niñas y adolescentes: maltrato, abandono, trabajo infantil, violencia.', canal: 'Línea gratuita 141 · www.icbf.gov.co' },
    { nombre: 'Línea 155', queHace: 'Orientación a mujeres víctimas de violencia, las 24 horas.', canal: 'Línea gratuita 155' },
    { nombre: 'Línea 123', queHace: 'Emergencias: Policía, ambulancia, bomberos.', canal: 'Línea 123' },
    { nombre: 'Procuraduría General de la Nación', queHace: 'Quejas disciplinarias contra funcionarios públicos que no responden peticiones o abusan de su cargo.', canal: 'www.procuraduria.gov.co' },
    { nombre: 'Unidad para las Víctimas', queHace: 'Registro de víctimas, ayuda humanitaria, indemnización administrativa.', canal: 'www.unidadvictimas.gov.co · Línea 01 8000 911 119' }
  ],

  buscar(texto) {
    const t = (texto || '').toLowerCase();
    if (!t) return [];
    return this.lista.filter(e => e.nombre.toLowerCase().includes(t)).slice(0, 8);
  },

  categoria(id) {
    return this.categorias.find(c => c.id === id) || this.categorias[0];
  },

  categoriaDeNombre(nombre) {
    const norm = s => (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim();
    const n = norm(nombre);
    if (n.length < 3) return null;
    const exacta = this.lista.find(x => norm(x.nombre) === n);
    if (exacta) return exacta.cat;
    const parcial = this.lista.find(x => { const xn = norm(x.nombre); return xn.includes(n) || (n.length >= 4 && n.includes(xn.split(' (')[0])); });
    if (parcial) return parcial.cat;
    if (/alcald|municip|secretar[ií]a de|inspecci[oó]n|comisar[ií]a|personer[ií]a|sisb[eé]n/.test(n)) return 'municipio';
    if (/gobernaci/.test(n)) return 'departamento';
    if (/\beps\b|ips\b|cl[ií]nica|hospital|\barl\b/.test(n)) return 'eps';
    if (/juzgado|tribunal|fiscal[ií]a|procuradur/.test(n)) return 'judicial';
    if (/colegio|escuela|instituci[oó]n educativa|universidad|sena\b|icetex/.test(n)) return 'educacion';
    if (/banco|cooperativa|financ|datacr[eé]dito|transunion|cifin|nequi|daviplata/.test(n)) return 'financiera';
    if (/acueducto|energ|electri|gas\b|aseo|telecom|internet/.test(n)) return 'spd';
    if (/ministerio|superintendencia|unidad|registradur|dian\b|polic[ií]a|migraci[oó]n|icbf|colpensiones|ugpp/.test(n)) return 'nacional';
    return null;
  }
};
