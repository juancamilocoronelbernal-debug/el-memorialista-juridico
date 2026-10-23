/**
 * El Memorialista - Auditoría de datos y herramientas jurídicas
 * Frontend puramente en JavaScript sin IA.
 * 
 * Incluye:
 * 1. NIT: cálculo y validación de dígito de verificación DIAN (algoritmo oficial).
 * 2. Radicado: exigencia de 23 dígitos, formato 5-2-2-3-4-5-2 y decodificación DANE/CSJ.
 * 3. numeroALetras(): conversión determinista a pesos colombianos ("M/CTE.").
 * 4. Verificación de coincidencia entre cifra y letras en el escrito.
 * 5. Auditoría de consistencia (invenciones y omisiones formulario vs. escrito).
 */

(function (global) {
  'use strict';

  // =========================================================================
  // 1. DÍGITO DE VERIFICACIÓN DIAN (NIT)
  // =========================================================================
  const PESOS_DIAN = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71];

  function calcularDvNit(nit) {
    const soloDigitos = String(nit || '').replace(/\D/g, '');
    if (!soloDigitos) return null;
    let suma = 0;
    const len = soloDigitos.length;
    for (let i = 0; i < len && i < PESOS_DIAN.length; i++) {
      const digito = parseInt(soloDigitos[len - 1 - i], 10);
      suma += digito * PESOS_DIAN[i];
    }
    const residuo = suma % 11;
    return (residuo === 0 || residuo === 1) ? residuo : (11 - residuo);
  }

  function formatearMiles(numeroStr) {
    const s = String(numeroStr || '').replace(/\D/g, '');
    if (!s) return '';
    return s.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function formatearNit(nit, incluirDv = true) {
    const soloDigitos = String(nit || '').replace(/\D/g, '');
    if (!soloDigitos) return String(nit || '');
    const dv = calcularDvNit(soloDigitos);
    const baseFmt = formatearMiles(soloDigitos);
    return incluirDv ? `${baseFmt}-${dv}` : baseFmt;
  }

  function validarNit(nitTexto) {
    const s = String(nitTexto || '').trim();
    if (!s) {
      return { valido: false, nitBase: '', dvIngresado: null, dvCalculado: null, mensaje: 'NIT vacío' };
    }

    if (s.includes('-')) {
      const partes = s.split('-');
      const base = partes[0].replace(/\D/g, '');
      const dvRaw = partes[partes.length - 1].replace(/\D/g, '');
      if (base && dvRaw) {
        const dvIngresado = parseInt(dvRaw.slice(-1), 10);
        const dvCalculado = calcularDvNit(base);
        const esValido = (dvIngresado === dvCalculado);
        return {
          valido: esValido,
          nitBase: base,
          dvIngresado: dvIngresado,
          dvCalculado: dvCalculado,
          nitFormateado: `${formatearMiles(base)}-${dvCalculado}`,
          mensaje: esValido
            ? 'Dígito de verificación DIAN correcto.'
            : `El dígito de verificación ingresado (${dvIngresado}) no coincide con el calculado por la DIAN (${dvCalculado}). Debe ser ${formatearMiles(base)}-${dvCalculado}.`
        };
      }
    }

    const soloDigitos = s.replace(/\D/g, '');
    if (!soloDigitos) {
      return { valido: false, nitBase: '', dvIngresado: null, dvCalculado: null, mensaje: 'Sin dígitos' };
    }
    const dvCalculado = calcularDvNit(soloDigitos);
    return {
      valido: true,
      nitBase: soloDigitos,
      dvIngresado: null,
      dvCalculado: dvCalculado,
      nitFormateado: `${formatearMiles(soloDigitos)}-${dvCalculado}`,
      mensaje: `Dígito de verificación DIAN: ${dvCalculado}`
    };
  }

  // =========================================================================
  // 2. RADICADO JUDICIAL (23 DÍGITOS: 5-2-2-3-4-5-2)
  // =========================================================================
  const MUNICIPIOS_DANE = {
    '05001': 'Medellín (Antioquia)',
    '05045': 'Apartadó (Antioquia)',
    '05088': 'Bello (Antioquia)',
    '05154': 'Caucasia (Antioquia)',
    '05266': 'Envigado (Antioquia)',
    '05360': 'Itagüí (Antioquia)',
    '05615': 'Rionegro (Antioquia)',
    '05837': 'Turbo (Antioquia)',
    '08001': 'Barranquilla (Atlántico)',
    '08758': 'Soledad (Atlántico)',
    '11001': 'Bogotá, D.C. (Cundinamarca)',
    '13001': 'Cartagena de Indias (Bolívar)',
    '13430': 'Magangué (Bolívar)',
    '15001': 'Tunja (Boyacá)',
    '15238': 'Duitama (Boyacá)',
    '15759': 'Sogamoso (Boyacá)',
    '17001': 'Manizales (Caldas)',
    '18001': 'Florencia (Caquetá)',
    '19001': 'Popayán (Cauca)',
    '20001': 'Valledupar (Cesar)',
    '23001': 'Montería (Córdoba)',
    '25175': 'Chía (Cundinamarca)',
    '25269': 'Facatativá (Cundinamarca)',
    '25290': 'Fusagasugá (Cundinamarca)',
    '25307': 'Girardot (Cundinamarca)',
    '25754': 'Soacha (Cundinamarca)',
    '25899': 'Zipaquirá (Cundinamarca)',
    '27001': 'Quibdó (Chocó)',
    '41001': 'Neiva (Huila)',
    '41551': 'Pitalito (Huila)',
    '44001': 'Riohacha (La Guajira)',
    '44430': 'Maicao (La Guajira)',
    '47001': 'Santa Marta (Magdalena)',
    '47189': 'Ciénaga (Magdalena)',
    '50001': 'Villavicencio (Meta)',
    '52001': 'Pasto (Nariño)',
    '52356': 'Ipiales (Nariño)',
    '52835': 'Tumaco (Nariño)',
    '54001': 'Cúcuta (Norte de Santander)',
    '54498': 'Ocaña (Norte de Santander)',
    '63001': 'Armenia (Quindío)',
    '66001': 'Pereira (Risaralda)',
    '66170': 'Dosquebradas (Risaralda)',
    '68001': 'Bucaramanga (Santander)',
    '68081': 'Barrancabermeja (Santander)',
    '68276': 'Floridablanca (Santander)',
    '68307': 'Girón (Santander)',
    '68547': 'Piedecuesta (Santander)',
    '70001': 'Sincelejo (Sucre)',
    '73001': 'Ibagué (Tolima)',
    '73268': 'Espinal (Tolima)',
    '76001': 'Cali (Valle del Cauca)',
    '76109': 'Buenaventura (Valle del Cauca)',
    '76111': 'Guadalajara de Buga (Valle del Cauca)',
    '76147': 'Cartago (Valle del Cauca)',
    '76520': 'Palmira (Valle del Cauca)',
    '76834': 'Tuluá (Valle del Cauca)',
    '81001': 'Arauca (Arauca)',
    '85001': 'Yopal (Casanare)',
    '86001': 'Mocoa (Putumayo)',
    '88001': 'San Andrés (Archipiélago de San Andrés)',
    '91001': 'Leticia (Amazonas)',
    '94001': 'Inírida (Guainía)',
    '95001': 'San José del Guaviare (Guaviare)',
    '97001': 'Mitú (Vaupés)',
    '99001': 'Puerto Carreño (Vichada)'
  };

  const ENTIDADES_CSJ = {
    '01': 'Corte Suprema de Justicia',
    '02': 'Consejo de Estado',
    '03': 'Corte Constitucional',
    '04': 'Comisión Nacional de Disciplina Judicial',
    '22': 'Tribunal Superior de Distrito Judicial',
    '23': 'Tribunal Administrativo',
    '31': 'Juzgado del Circuito',
    '33': 'Juzgado Administrativo',
    '40': 'Juzgado Municipal / Pequeñas Causas',
    '41': 'Juzgado de Ejecución de Penas',
    '60': 'Centro de Servicios Judiciales'
  };

  const ESPECIALIDADES_CSJ = {
    '01': 'Penal',
    '02': 'Penal para Adolescentes',
    '03': 'Civil',
    '04': 'Laboral',
    '05': 'Familia',
    '06': 'Contencioso Administrativo',
    '07': 'Agrario',
    '08': 'Comercial',
    '09': 'Disciplinario',
    '10': 'Extinción de Dominio',
    '11': 'Constitucional / Tutelas',
    '89': 'Promiscuo'
  };

  function extraerDigitosRadicado(s) {
    return String(s || '').replace(/\D/g, '');
  }

  function validarRadicado(s) {
    const d = extraerDigitosRadicado(s);
    if (d.length === 23) {
      return { valido: true, mensaje: 'Radicado completo: 23 dígitos válidos.' };
    }
    if (d.length === 0) {
      return { valido: false, mensaje: 'El radicado judicial está vacío; debe tener 23 dígitos.' };
    }
    return {
      valido: false,
      mensaje: `El radicado judicial debe tener exactamente 23 dígitos (actualmente tiene ${d.length}).`
    };
  }

  function formatearRadicado(s) {
    const d = extraerDigitosRadicado(s);
    if (d.length !== 23) return String(s || '').trim();
    return `${d.slice(0, 5)}-${d.slice(5, 7)}-${d.slice(7, 9)}-${d.slice(9, 12)}-${d.slice(12, 16)}-${d.slice(16, 21)}-${d.slice(21, 23)}`;
  }

  function decodificarRadicado(s) {
    const d = extraerDigitosRadicado(s);
    if (d.length !== 23) {
      return {
        valido: false,
        digitos: d,
        totalDigitos: d.length,
        mensaje: `Tiene ${d.length} dígitos; debe tener exactamente 23.`
      };
    }

    const codMun = d.slice(0, 5);
    const codEnt = d.slice(5, 7);
    const codEsp = d.slice(7, 9);
    const codDesp = d.slice(9, 12);
    const ano = parseInt(d.slice(12, 16), 10);
    const consecutivo = d.slice(16, 21);
    const codRec = d.slice(21, 23);

    const nombreMun = MUNICIPIOS_DANE[codMun] || `Municipio DANE ${codMun}`;
    const nombreEnt = ENTIDADES_CSJ[codEnt] || `Entidad ${codEnt}`;
    const nombreEsp = ESPECIALIDADES_CSJ[codEsp] || `Especialidad ${codEsp}`;

    return {
      valido: true,
      digitos: d,
      totalDigitos: 23,
      formateado: `${codMun}-${codEnt}-${codEsp}-${codDesp}-${ano}-${consecutivo}-${codRec}`,
      municipioCodigo: codMun,
      municipioNombre: nombreMun,
      entidadCodigo: codEnt,
      entidadNombre: nombreEnt,
      especialidadCodigo: codEsp,
      especialidadNombre: nombreEsp,
      despachoNumero: codDesp,
      ano: ano,
      consecutivo: consecutivo,
      consecutivoNumero: parseInt(consecutivo, 10),
      recursoCodigo: codRec,
      resumen: `${nombreMun} · ${nombreEnt} (${nombreEsp}) · Despacho ${parseInt(codDesp, 10)} · Año ${ano} · Consecutivo ${consecutivo}`
    };
  }

  // =========================================================================
  // 3. NÚMEROS A LETRAS DETERMINISTA (PESOS COLOMBIANOS, "M/CTE")
  // =========================================================================
  const UNIDADES_JS = ['', 'UN', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE'];
  const DIEZ_A_DIECINUEVE_JS = [
    'DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE',
    'DIECISÉIS', 'DIECISIETE', 'DIECIOCHO', 'DIECINUEVE'
  ];
  const VEINTES_JS = [
    'VEINTE', 'VEINTIÚN', 'VEINTIDÓS', 'VEINTITRÉS', 'VEINTICUATRO', 'VEINTICINCO',
    'VEINTISÉIS', 'VEINTISIETE', 'VEINTIOCHO', 'VEINTINUEVE'
  ];
  const DECENAS_JS = ['', '', '', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA'];
  const CENTENAS_JS = [
    '', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS',
    'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS'
  ];

  function seccionTresDigitos(n) {
    if (n === 0) return '';
    if (n === 100) return 'CIEN';

    const c = Math.floor(n / 100);
    const resto = n % 100;
    const d = Math.floor(resto / 10);
    const u = resto % 10;

    const partes = [];
    if (c > 0) partes.push(CENTENAS_JS[c]);

    if (resto > 0) {
      if (resto < 10) {
        partes.push(UNIDADES_JS[resto]);
      } else if (resto < 20) {
        partes.push(DIEZ_A_DIECINUEVE_JS[resto - 10]);
      } else if (resto < 30) {
        partes.push(VEINTES_JS[resto - 20]);
      } else {
        if (u === 0) partes.push(DECENAS_JS[d]);
        else partes.push(`${DECENAS_JS[d]} Y ${UNIDADES_JS[u]}`);
      }
    }
    return partes.join(' ');
  }

  function numeroALetrasEntero(n) {
    if (n === 0) return { texto: 'CERO', dePesos: false };
    if (n === 1) return { texto: 'UN', dePesos: false };

    const g0 = n % 1000;
    const g1 = Math.floor(n / 1000) % 1000;
    const g2 = Math.floor(n / 1000000) % 1000;
    const g3 = Math.floor(n / 1000000000) % 1000;
    const g4 = Math.floor(n / 1000000000000) % 1000;

    const partes = [];

    if (g4 > 0) {
      if (g4 === 1) partes.push('UN BILLÓN');
      else partes.push(`${seccionTresDigitos(g4)} BILLONES`);
    }

    const millonesTotal = g3 * 1000 + g2;
    if (millonesTotal > 0) {
      if (g3 > 0 && g2 === 0) {
        if (g3 === 1) partes.push('UN MIL MILLONES');
        else partes.push(`${seccionTresDigitos(g3)} MIL MILLONES`);
      } else if (g3 > 0 && g2 > 0) {
        if (g3 === 1) partes.push(`UN MIL ${seccionTresDigitos(g2)} MILLONES`);
        else partes.push(`${seccionTresDigitos(g3)} MIL ${seccionTresDigitos(g2)} MILLONES`);
      } else {
        if (g2 === 1) partes.push('UN MILLÓN');
        else partes.push(`${seccionTresDigitos(g2)} MILLONES`);
      }
    }

    if (g1 > 0) {
      if (g1 === 1) partes.push('UN MIL');
      else partes.push(`${seccionTresDigitos(g1)} MIL`);
    }

    if (g0 > 0) {
      partes.push(seccionTresDigitos(g0));
    }

    const texto = partes.join(' ');
    const dePesos = (millonesTotal > 0 || g4 > 0) && (g1 === 0 && g0 === 0);

    return { texto, dePesos };
  }

  function numeroALetras(valor) {
    if (valor == null || valor === '') return '';

    let num;
    if (typeof valor === 'string') {
      let s = valor.trim().replace(/\$|COP|cop/g, '').trim();
      if (!s) return '';
      if (s.includes(',') && s.includes('.')) {
        if (s.lastIndexOf(',') > s.lastIndexOf('.')) s = s.replace(/\./g, '').replace(',', '.');
        else s = s.replace(/,/g, '');
      } else if (s.includes(',')) {
        const p = s.split(',');
        if (p.length === 2 && p[1].length <= 2) s = `${p[0]}.${p[1]}`;
        else s = s.replace(/,/g, '');
      } else {
        const p = s.split('.');
        if (p.length > 2 || (p.length === 2 && p[1].length === 3)) s = s.replace(/\./g, '');
      }
      num = parseFloat(s);
    } else {
      num = Number(valor);
    }

    if (isNaN(num)) return '';

    const prefijo = num < 0 ? 'MENOS ' : '';
    num = Math.abs(num);

    let entero = Math.floor(num);
    let centavos = Math.round((num - entero) * 100);
    if (centavos >= 100) { entero += 1; centavos = 0; }

    const res = numeroALetrasEntero(entero);
    let moneda;
    if (entero === 1) moneda = 'PESO';
    else if (res.dePesos) moneda = 'DE PESOS';
    else moneda = 'PESOS';

    if (centavos > 0) {
      const centStr = String(centavos).padStart(2, '0');
      return `${prefijo}${res.texto} ${moneda} CON ${centStr}/100 M/CTE.`;
    }
    return `${prefijo}${res.texto} ${moneda} M/CTE.`;
  }

  // =========================================================================
  // 4. AUDITORÍA DE DATOS (FORMULARIO VS. ESCRITO)
  // =========================================================================

  // Meses en español
  const MESES_MAP = {
    enero: '01', febrero: '02', marzo: '03', abril: '04', mayo: '05', junio: '06',
    julio: '07', agosto: '08', septiembre: '09', setiembre: '09', octubre: '10',
    noviembre: '11', diciembre: '12'
  };

  // Palabras para valores numéricos en letras
  const PALABRAS_NUMEROS = {
    un: 1, uno: 1, una: 1, dos: 2, tres: 3, cuatro: 4, cinco: 5, seis: 6, siete: 7, ocho: 8, nueve: 9,
    diez: 10, once: 11, doce: 12, trece: 13, catorce: 14, quince: 15,
    dieciseis: 16, dieciséis: 16, diecisiete: 17, dieciocho: 18, diecinueve: 19,
    veinte: 20, veintiun: 21, veintiún: 21, veintiuno: 21, veintiuna: 21,
    veintidos: 22, veintidós: 22, veintitres: 23, veintitrés: 23, veinticuatro: 24,
    veinticinco: 25, veintiseis: 26, veintiséis: 26, veintisiete: 27, veintiocho: 28, veintinueve: 29,
    treinta: 30, cuarenta: 40, cincuenta: 50, sesenta: 60, setenta: 70, ochenta: 80, noventa: 90,
    cien: 100, ciento: 100, doscientos: 200, doscientas: 200, trescientos: 300, trescientas: 300,
    cuatrocientos: 400, cuatrocientas: 400, quinientos: 500, quinientas: 500,
    seiscientos: 600, seiscientas: 600, setecientos: 700, setecientas: 700,
    ochocientos: 800, ochocientas: 800, novecientos: 900, novecientas: 900
  };

  const CIUDADES_COLOMBIA = new Set([
    'bogota', 'medellin', 'cali', 'barranquilla', 'bucaramanga', 'cartagena',
    'cucuta', 'pereira', 'manizales', 'ibague', 'santa marta', 'villavicencio',
    'pasto', 'monteria', 'valledupar', 'armenia', 'popayan', 'sincelejo',
    'neiva', 'tunja', 'riohacha', 'florencia', 'yopal', 'quibdo', 'mocoa',
    'san andres', 'itagui', 'bello', 'soacha', 'palmira', 'envigado'
  ]);

  function pad2(n) {
    return String(n).padStart(2, '0');
  }

  function normalizarNombre(s) {
    return String(s || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function esCiudadOGeografia(s) {
    const norm = normalizarNombre(s);
    if (!norm) return true;
    const tokens = norm.split(/\s+/).filter(Boolean);
    return tokens.every(t => t === 'de' || t === 'del' || t === 'd' || t === 'c' || t === 'distrito' || t === 'capital' || CIUDADES_COLOMBIA.has(t));
  }

  function esEncabezadoOAutoridad(s) {
    const norm = normalizarNombre(s);
    if (!norm) return true;

    if (norm.includes('pesos') || norm.includes('m cte') || norm.includes('moneda corriente')) return true;
    if (palabrasANumero(s) !== null) return true;
    if (esCiudadOGeografia(s)) return true;

    const patrones = [
      'juez', 'juzgad', 'tribunal', 'magistrad', 'corte', 'despacho', 'republica', 'rama judicial',
      'notificacion', 'pretension', 'hechos', 'derecho', 'prueba', 'anexo', 'juramento', 'medida',
      'cuantia', 'competencia', 'tutela', 'demanda', 'poder', 'alegato', 'recurso', 'notaria',
      'secretari', 'ministeri', 'alcaldi', 'inspeccion', 'procuradur', 'fiscali', 'personeri',
      'defensori', 'consejo', 'centro de conciliacion', 'atentamente', 'cordialmente',
      'articulo', 'ley ', 'decreto', 'constitucion', 'acuerdo', 'resolucion', 'circulo',
      'primero', 'segundo', 'tercero', 'cuarto', 'quinto', 'sexto', 'septimo', 'octavo', 'noveno', 'decimo',
      'paragrafo', 'capitulo', 'seccion', 'numeral', 'inciso', 'acapite', 'asunto', 'referencia', 'canal digital', 'parte actora', 'parte demandada',
      'por medio del cual', 'en contra de', 'al tenor de', 'en merito de lo expuesto',
      'sentencia', 'ejecucion', 'mandamiento', 'proceso', 'contrato', 'arrendamiento', 'promesa', 'compraventa'
    ];

    return patrones.some(p => norm.includes(p));
  }

  function palabrasANumero(texto) {
    const palabras = String(texto || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\by\b/g, ' ')
      .replace(/[^a-z\s]/g, ' ')
      .split(/\s+/)
      .filter(Boolean);

    let total = 0;
    let grupo = 0;
    let encontro = false;

    for (const p of palabras) {
      if (PALABRAS_NUMEROS[p] !== undefined) {
        grupo += PALABRAS_NUMEROS[p];
        encontro = true;
      } else if (p === 'mil') {
        if (grupo === 0) grupo = 1;
        total += grupo * 1000;
        grupo = 0;
        encontro = true;
      } else if (p === 'millon' || p === 'millones') {
        if (grupo === 0) grupo = 1;
        total += grupo * 1000000;
        grupo = 0;
        encontro = true;
      } else if (p === 'billon' || p === 'billones') {
        if (grupo === 0) grupo = 1;
        total += grupo * 1000000000000;
        grupo = 0;
        encontro = true;
      }
    }
    total += grupo;
    return encontro && total > 0 ? total : null;
  }

  function extraerEntidades(texto, opciones = {}) {
    const textoStr = String(texto || '').normalize('NFC');
    const entidades = [];
    if (!textoStr.trim()) return entidades;

    let textoTrabajo = textoStr;

    // 1. Radicados de 23 dígitos
    const reRadicado = /(?<!\d)(\d(?:[-\s]?\d){22})(?!\d)/g;
    let match;
    while ((match = reRadicado.exec(textoStr)) !== null) {
      const original = match[1];
      const norm = original.replace(/[-\s\.]/g, '');
      if (norm.length === 23) {
        const dec = decodificarRadicado(norm);
        entidades.push({
          tipo: 'radicado',
          valor: original,
          textoOriginal: original,
          normalizado: norm,
          formateado: dec.formateado,
          decodificado: dec,
          detalle: `Radicado judicial (23 dígitos): ${dec.formateado} (${dec.resumen})`
        });
        textoTrabajo = textoTrabajo.replace(original, ' '.repeat(original.length));
      }
    }

    // 2. Matrículas inmobiliarias
    const reMatricula = /\b(?:matr[ií]cula(?: inmobiliaria)?\s*(?:n[oó]\.?|número)?\s*[:#]?\s*([0-9A-Za-z]+-[0-9A-Za-z]+|[0-9A-Za-z]{6,12})|(\d{2,3}[A-Z]?-\d{4,8}))\b/gi;
    while ((match = reMatricula.exec(textoTrabajo)) !== null) {
      const original = match[1] || match[2];
      if (original) {
        const norm = original.toUpperCase().replace(/\s+/g, '');
        if (!/^\d{4}-\d{2}$/.test(norm)) {
          entidades.push({
            tipo: 'matrícula',
            valor: original,
            textoOriginal: match[0],
            normalizado: norm,
            detalle: `Matrícula inmobiliaria: ${original}`
          });
          textoTrabajo = textoTrabajo.replace(match[0], ' '.repeat(match[0].length));
        }
      }
    }

    // 3. Valores en pesos (cifras y letras)
    const reValorCifras = /(?:\$|COP)\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\b|\b(\d{1,3}(?:\.\d{3})+)\s*(?:de\s+)?(?:pesos|m\/cte|moneda corriente)\b/gi;
    while ((match = reValorCifras.exec(textoTrabajo)) !== null) {
      const cifra = match[1] || match[2];
      const normNum = parseInt(cifra.replace(/\./g, '').split(',')[0], 10);
      if (!isNaN(normNum) && normNum > 0) {
        entidades.push({
          tipo: 'valor',
          valor: `$${normNum.toLocaleString('es-CO')}`,
          textoOriginal: match[0],
          normalizado: String(normNum),
          detalle: `Valor en pesos: $${normNum.toLocaleString('es-CO')}`
        });
        textoTrabajo = textoTrabajo.replace(match[0], ' '.repeat(match[0].length));
      }
    }

    const reValorLetras = /\b((?:(?:un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|diecis[eé]is|diecisiete|dieciocho|diecinueve|veinte|veinti[úu]n|veintiuno|veintiuna|veintid[oó]s|veintitr[eé]s|veinticuatro|veinticinco|veintis[eé]is|veintisiete|veintiocho|veintinueve|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|doscientos|doscientas|trescientos|trescientas|cuatrocientos|cuatrocientas|quinientos|quinientas|seiscientos|seiscientas|setecientos|setecientas|ochocientos|ochocientas|novecientos|novecientas|mil|mill[oó]n|millones|bill[oó]n|billones|y)\s+){1,10}(?:de\s+)?pesos(?:\s+(?:moneda\s+corriente|m\/cte))?)\b/gi;
    while ((match = reValorLetras.exec(textoTrabajo)) !== null) {
      const frase = match[1];
      const num = palabrasANumero(frase);
      if (num && num > 0) {
        entidades.push({
          tipo: 'valor',
          valor: `$${num.toLocaleString('es-CO')} (${frase.trim()})`,
          textoOriginal: frase.trim(),
          normalizado: String(num),
          detalle: `Valor en letras: ${frase.trim()} ($${num.toLocaleString('es-CO')})`
        });
        textoTrabajo = textoTrabajo.replace(match[0], ' '.repeat(match[0].length));
      }
    }

    // 4. Fechas
    const reFechaTexto = /\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b/gi;
    while ((match = reFechaTexto.exec(textoTrabajo)) !== null) {
      const d = parseInt(match[1], 10);
      const mNombre = match[2].toLowerCase();
      const a = parseInt(match[3], 10);
      const m = MESES_MAP[mNombre];
      if (d >= 1 && d <= 31 && m && a >= 1900 && a <= 2100) {
        const iso = `${a}-${m}-${pad2(d)}`;
        entidades.push({
          tipo: 'fecha',
          valor: match[0],
          textoOriginal: match[0],
          normalizado: iso,
          detalle: `Fecha: ${match[0]} (${iso})`
        });
        textoTrabajo = textoTrabajo.replace(match[0], ' '.repeat(match[0].length));
      }
    }

    const reFechaNum = /\b(\d{1,2})[\/\.-](\d{1,2})[\/\.-](\d{4})\b/g;
    while ((match = reFechaNum.exec(textoTrabajo)) !== null) {
      const d = parseInt(match[1], 10);
      const m = parseInt(match[2], 10);
      const a = parseInt(match[3], 10);
      if (d >= 1 && d <= 31 && m >= 1 && m <= 12 && a >= 1900 && a <= 2100) {
        const iso = `${a}-${pad2(m)}-${pad2(d)}`;
        entidades.push({
          tipo: 'fecha',
          valor: match[0],
          textoOriginal: match[0],
          normalizado: iso,
          detalle: `Fecha: ${match[0]} (${iso})`
        });
        textoTrabajo = textoTrabajo.replace(match[0], ' '.repeat(match[0].length));
      }
    }

    const reFechaIso = /\b(\d{4})-(\d{2})-(\d{2})\b/g;
    while ((match = reFechaIso.exec(textoTrabajo)) !== null) {
      const a = parseInt(match[1], 10);
      const m = parseInt(match[2], 10);
      const d = parseInt(match[3], 10);
      if (d >= 1 && d <= 31 && m >= 1 && m <= 12 && a >= 1900 && a <= 2100) {
        const iso = `${a}-${pad2(m)}-${pad2(d)}`;
        entidades.push({
          tipo: 'fecha',
          valor: iso,
          textoOriginal: match[0],
          normalizado: iso,
          detalle: `Fecha: ${iso}`
        });
        textoTrabajo = textoTrabajo.replace(match[0], ' '.repeat(match[0].length));
      }
    }

    // 5. Correos electrónicos
    const reCorreo = /\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b/g;
    while ((match = reCorreo.exec(textoTrabajo)) !== null) {
      const email = match[1].toLowerCase().trim();
      entidades.push({
        tipo: 'correo',
        valor: email,
        textoOriginal: match[1],
        normalizado: email,
        detalle: `Correo electrónico: ${email}`
      });
      textoTrabajo = textoTrabajo.replace(match[0], ' '.repeat(match[0].length));
    }

    // 6. Teléfonos
    const reTel = /\b(?:\+?57\s*)?(3\d{2})[-\s\.]?(\d{3})[-\s\.]?(\d{4})\b|\b(?:tel[eé]fono|celular|m[oó]vil|tel\.?|cel\.?)\s*[:#]?\s*([0-9\s\.\(\)\+-]{7,15})\b/gi;
    while ((match = reTel.exec(textoTrabajo)) !== null) {
      let raw = match[0];
      let digits = raw.replace(/\D/g, '');
      if (digits.startsWith('57') && digits.length === 12) digits = digits.slice(2);
      if (digits.length >= 7 && digits.length <= 10) {
        entidades.push({
          tipo: 'teléfono',
          valor: raw.trim(),
          textoOriginal: raw.trim(),
          normalizado: digits,
          detalle: `Teléfono: ${digits}`
        });
        textoTrabajo = textoTrabajo.replace(raw, ' '.repeat(raw.length));
      }
    }

    // 7. Cédulas y NIT (con y sin puntos)
    const reNit = /\b(?:NIT|N\.I\.T\.)\s*[:#]?\s*(\d{1,3}(?:\.\d{3}){2,3}(?:-\d)?|\d{8,10}(?:-\d)?)\b|\b(\d{3}\.\d{3}\.\d{3}-\d)\b/gi;
    while ((match = reNit.exec(textoTrabajo)) !== null) {
      const nitRaw = match[1] || match[2];
      const validacion = validarNit(nitRaw);
      entidades.push({
        tipo: 'cédula / NIT',
        valor: nitRaw,
        textoOriginal: match[0],
        normalizado: validacion.nitBase || nitRaw.replace(/\D/g, '').slice(0, 9),
        validacionNit: validacion,
        detalle: `NIT: ${nitRaw}` + (!validacion.valido && validacion.dvIngresado !== null ? ` (⚠️ ${validacion.mensaje})` : '')
      });
      textoTrabajo = textoTrabajo.replace(match[0], ' '.repeat(match[0].length));
    }

    const reCedula = /\b(?:c\.?c\.?|c[eé]dula(?: de ciudadan[ií]a)?|identificad[oa] con|c\.?e\.?|ti)\s*(?:n[oó]\.?|número)?\s*[:#]?\s*(\d{1,3}(?:\.\d{3}){1,3}|\d{6,10})\b|\b(\d{1,3}(?:\.\d{3}){1,3})\b/gi;
    while ((match = reCedula.exec(textoTrabajo)) !== null) {
      const cedRaw = match[1] || match[2];
      const digitos = cedRaw.replace(/\D/g, '');
      if (digitos.length >= 6 && digitos.length <= 10 && digitos !== '2026' && digitos !== '2025' && digitos !== '2024') {
        entidades.push({
          tipo: 'cédula / NIT',
          valor: cedRaw,
          textoOriginal: match[0],
          normalizado: digitos,
          detalle: `Cédula de ciudadanía: ${cedRaw}`
        });
        textoTrabajo = textoTrabajo.replace(match[0], ' '.repeat(match[0].length));
      }
    }

    return entidades;
  }

  function extraerPartesDeDatos(datos) {
    const partes = [];
    if (!datos || typeof datos !== 'object') return partes;

    const camposPartes = [
      'accionante', 'accionado', 'demandante', 'demandado', 'convocante', 'convocado',
      'arrendador', 'arrendatario', 'otorgante', 'apoderado', 'denunciante', 'denunciado',
      'cliente', 'contraparte', 'trabajador', 'empleador', 'comprador', 'vendedor',
      'peticionario', 'entidad', 'titular', 'paciente'
    ];

    for (const [k, v] of Object.entries(datos)) {
      if (!v || typeof v !== 'string') continue;
      const esCampoParte = camposPartes.includes(k.toLowerCase());

      if (esCampoParte) {
        const partesStr = v.split(/\n|;|\by\b/i);
        for (let fragmento of partesStr) {
          fragmento = fragmento.trim();
          if (!fragmento) continue;
          const nombreLimpio = fragmento.split(/,|identificad[oa]|c\.?c\.?|nit|mayor de edad|\(/i)[0].trim();
          if (nombreLimpio.length >= 3 && !/^\d+$/.test(nombreLimpio)) {
            partes.push({
              tipo: 'parte',
              valor: nombreLimpio,
              textoOriginal: nombreLimpio,
              normalizado: normalizarNombre(nombreLimpio),
              detalle: `Parte procesal (${k}): ${nombreLimpio}`
            });
          }
        }
      }
    }
    return partes;
  }

  function extraerPartesDeEscrito(texto, perfilAbogado = {}) {
    const partes = [];
    const textoStr = String(texto || '').normalize('NFC');
    if (!textoStr.trim()) return partes;

    const nombreAbogadoNorm = normalizarNombre(perfilAbogado.nombre || '');

    // 1. Nombres en negrilla (**TEXTO**)
    const reNegrilla = /\*\*([A-Za-zÁÉÍÓÚáéíóúñÑ\s\.\&]{3,60})\*\*/g;
    let match;
    while ((match = reNegrilla.exec(textoStr)) !== null) {
      const candidato = match[1].trim();
      const norm = normalizarNombre(candidato);

      if (
        candidato.split(/\s+/).length >= 2 &&
        !esEncabezadoOAutoridad(candidato) &&
        norm !== nombreAbogadoNorm
      ) {
        partes.push({
          tipo: 'parte',
          valor: candidato,
          textoOriginal: `**${candidato}**`,
          normalizado: norm,
          detalle: `Parte procesal en negrilla: ${candidato}`
        });
      }
    }

    // 2. Nombres en mayúscula sostenida (al menos 2 palabras en mayúsculas)
    const reMayus = /\b([A-ZÁÉÍÓÚÑ]{3,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,}){1,5})\b/g;
    while ((match = reMayus.exec(textoStr)) !== null) {
      const candidato = match[1].trim();
      const norm = normalizarNombre(candidato);

      if (
        candidato.split(/\s+/).length >= 2 &&
        !esEncabezadoOAutoridad(candidato) &&
        norm !== nombreAbogadoNorm &&
        !partes.some(p => p.normalizado === norm)
      ) {
        partes.push({
          tipo: 'parte',
          valor: candidato,
          textoOriginal: candidato,
          normalizado: norm,
          detalle: `Parte procesal en mayúsculas: ${candidato}`
        });
      }
    }

    return partes;
  }

  /**
   * Verifica la concordancia entre expresiones en cifras y en letras en el escrito.
   */
  function detectarDiscrepanciasCifrasLetras(textoDoc, entidadesDatos = []) {
    const discrepancias = [];
    if (!textoDoc) return discrepancias;

    // Patrón 1: Cifra seguida de letras entre paréntesis, ej: $80.000.000 (ocho millones de pesos)
    const regexA = /\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*\(\s*([A-Za-zÁÉÍÓÚáéíóúñÑ\s]{4,80}?(?:de\s+)?pesos(?:\s+(?:m\/cte|moneda corriente))?)\s*\)/gi;
    let match;
    while ((match = regexA.exec(textoDoc)) !== null) {
      const cifraStr = match[1];
      const letrasStr = match[2];
      const numCifra = parseInt(cifraStr.replace(/\./g, '').split(',')[0], 10);
      const numLetras = palabrasANumero(letrasStr);
      if (!isNaN(numCifra) && numCifra > 0 && numLetras !== null && numLetras > 0) {
        if (numCifra !== numLetras) {
          discrepancias.push({
            tipo: 'discrepancia_cifra_letras',
            cifra: numCifra,
            cifraTexto: `$${numCifra.toLocaleString('es-CO')}`,
            letras: numLetras,
            letrasTexto: letrasStr.trim(),
            textoOriginal: match[0],
            detalle: `Discrepancia entre cifra y letras: se escribió "$${numCifra.toLocaleString('es-CO')}" pero en letras dice "${letrasStr.trim()}" ($${numLetras.toLocaleString('es-CO')}).`
          });
        }
      }
    }

    // Patrón 2: Letras seguidas de cifra entre paréntesis, ej: ocho millones de pesos ($80.000.000)
    const regexB = /([A-Za-zÁÉÍÓÚáéíóúñÑ\s]{4,80}?(?:de\s+)?pesos(?:\s+(?:m\/cte|moneda corriente))?)\s*\(\s*\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*\)/gi;
    while ((match = regexB.exec(textoDoc)) !== null) {
      const letrasStr = match[1];
      const cifraStr = match[2];
      const numLetras = palabrasANumero(letrasStr);
      const numCifra = parseInt(cifraStr.replace(/\./g, '').split(',')[0], 10);
      if (!isNaN(numCifra) && numCifra > 0 && numLetras !== null && numLetras > 0) {
        if (numCifra !== numLetras) {
          if (!discrepancias.some(d => d.cifra === numCifra && d.letras === numLetras)) {
            discrepancias.push({
              tipo: 'discrepancia_cifra_letras',
              cifra: numCifra,
              cifraTexto: `$${numCifra.toLocaleString('es-CO')}`,
              letras: numLetras,
              letrasTexto: letrasStr.trim(),
              textoOriginal: match[0],
              detalle: `Discrepancia entre cifra y letras: en letras dice "${letrasStr.trim()}" ($${numLetras.toLocaleString('es-CO')}) pero entre paréntesis dice "$${numCifra.toLocaleString('es-CO')}".`
            });
          }
        }
      }
    }

    // Patrón 3: Cifra del formulario vs. letras discordantes en el texto
    if (Array.isArray(entidadesDatos)) {
      const valoresForm = entidadesDatos.filter(e => e.tipo === 'valor' && !isNaN(Number(e.normalizado)));
      for (const vf of valoresForm) {
        const valNum = Number(vf.normalizado);
        if (valNum <= 0) continue;
        const reLetras = /\b((?:(?:un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|diecis[eé]is|diecisiete|dieciocho|diecinueve|veinte|veinti[úu]n|veintiuno|veintiuna|veintid[oó]s|veintitr[eé]s|veinticuatro|veinticinco|veintis[eé]is|veintisiete|veintiocho|veintinueve|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|doscientos|doscientas|trescientos|trescientas|cuatrocientos|cuatrocientas|quinientos|quinientas|seiscientos|seiscientas|setecientos|setecientas|ochocientos|ochocientas|novecientos|novecientas|mil|mill[oó]n|millones|bill[oó]n|billones|y)\s+){1,10}(?:de\s+)?pesos)\b/gi;
        let m;
        while ((m = reLetras.exec(textoDoc)) !== null) {
          const frase = m[1];
          const numLetras = palabrasANumero(frase);
          if (numLetras && numLetras > 0 && numLetras !== valNum) {
            const letrasCorrectas = numeroALetras(valNum).toLowerCase();
            if (!textoDoc.toLowerCase().includes(letrasCorrectas.slice(0, 20))) {
              if (!discrepancias.some(d => d.cifra === valNum && d.letras === numLetras)) {
                discrepancias.push({
                  tipo: 'discrepancia_cifra_letras',
                  cifra: valNum,
                  cifraTexto: `$${valNum.toLocaleString('es-CO')}`,
                  letras: numLetras,
                  letrasTexto: frase.trim(),
                  textoOriginal: m[0],
                  detalle: `Discrepancia con el formulario: en los datos ingresaste $${valNum.toLocaleString('es-CO')} pero en el escrito dice en letras "${frase.trim()}" ($${numLetras.toLocaleString('es-CO')}).`
                });
              }
            }
          }
        }
      }
    }

    return discrepancias;
  }

  /**
   * Realiza la auditoría integral entre datos del formulario y texto generado.
   */
  function auditarDatosYEscrito(datos, texto, perfil = {}, opciones = {}) {
    const textoDoc = String(texto || '').normalize('NFC');
    const abogado = (perfil && perfil.abogado) || {};

    const fechaHoyIso = opciones.fechaHoy || new Date().toISOString().slice(0, 10);

    const abogadoNorm = {
      nombre: normalizarNombre(abogado.nombre || ''),
      cedula: String(abogado.cedula || '').replace(/\D/g, ''),
      tp: String(abogado.tp || '').replace(/\D/g, ''),
      telefono: String(abogado.telefono || '').replace(/\D/g, ''),
      correo: String(abogado.correo || '').toLowerCase().trim()
    };

    // 1. Extraer entidades de datos del formulario
    const entidadesDatos = [];
    if (datos && typeof datos === 'object') {
      for (const [clave, valor] of Object.entries(datos)) {
        if (valor == null) continue;
        const kLower = clave.toLowerCase();
        const vStr = Array.isArray(valor) ? valor.join(', ') : String(valor);
        const vTrim = vStr.trim();
        if (!vTrim) continue;

        if (kLower.includes('cuantia') || kLower.includes('valor') || kLower.includes('monto') || kLower.includes('canon') || kLower.includes('salario')) {
          const reCifra = /\b(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+)\b/g;
          let m;
          while ((m = reCifra.exec(vTrim)) !== null) {
            const num = parseInt(m[1].replace(/\./g, '').split(',')[0], 10);
            if (!isNaN(num) && num > 0) {
              entidadesDatos.push({
                tipo: 'valor',
                valor: `$${num.toLocaleString('es-CO')}`,
                textoOriginal: vTrim,
                normalizado: String(num),
                detalle: `Valor en formulario (${clave}): $${num.toLocaleString('es-CO')}`
              });
            }
          }
          const numLetras = palabrasANumero(vTrim);
          if (numLetras && numLetras > 0) {
            entidadesDatos.push({
              tipo: 'valor',
              valor: `$${numLetras.toLocaleString('es-CO')} (${vTrim})`,
              textoOriginal: vTrim,
              normalizado: String(numLetras),
              detalle: `Valor en formulario (${clave}): $${numLetras.toLocaleString('es-CO')}`
            });
          }
        }

        if (kLower.includes('cedula') || kLower.includes('identificacion') || kLower.includes('cc') || kLower.includes('nit')) {
          const digitos = vTrim.replace(/\D/g, '');
          if (kLower.includes('nit') && digitos.length >= 8) {
            const baseNit = digitos.slice(0, 9);
            const valNit = validarNit(vTrim);
            entidadesDatos.push({
              tipo: 'cédula / NIT',
              valor: vTrim,
              textoOriginal: vTrim,
              normalizado: baseNit,
              validacionNit: valNit,
              detalle: `NIT en formulario (${clave}): ${vTrim}`
            });
          } else if (digitos.length >= 6 && digitos.length <= 10) {
            entidadesDatos.push({
              tipo: 'cédula / NIT',
              valor: vTrim,
              textoOriginal: vTrim,
              normalizado: digitos,
              detalle: `Cédula en formulario (${clave}): ${vTrim}`
            });
          }
        }

        if (kLower.includes('telefono') || kLower.includes('celular') || kLower.includes('tel')) {
          let digitos = vTrim.replace(/\D/g, '');
          if (digitsStart57(digitos)) digitos = digitos.slice(2);
          if (digitos.length >= 7 && digitos.length <= 10) {
            entidadesDatos.push({
              tipo: 'teléfono',
              valor: vTrim,
              textoOriginal: vTrim,
              normalizado: digitos,
              detalle: `Teléfono en formulario (${clave}): ${digitos}`
            });
          }
        }

        if (kLower.includes('radicado')) {
          const digitosRad = vTrim.replace(/[-\s\.]/g, '');
          if (digitosRad.length === 23) {
            const dec = decodificarRadicado(digitosRad);
            entidadesDatos.push({
              tipo: 'radicado',
              valor: vTrim,
              textoOriginal: vTrim,
              normalizado: digitosRad,
              formateado: dec.formateado,
              decodificado: dec,
              detalle: `Radicado en formulario (${clave}): ${dec.formateado}`
            });
          }
        }

        if (kLower.includes('matricula')) {
          const normMat = vTrim.toUpperCase().replace(/\s+/g, '');
          if (normMat.length >= 4) {
            entidadesDatos.push({
              tipo: 'matrícula',
              valor: vTrim,
              textoOriginal: vTrim,
              normalizado: normMat,
              detalle: `Matrícula en formulario (${clave}): ${vTrim}`
            });
          }
        }

        const extraidas = extraerEntidades(vTrim, opciones);
        entidadesDatos.push(...extraidas);
      }

      const partesDatos = extraerPartesDeDatos(datos);
      entidadesDatos.push(...partesDatos);
    }

    // 2. Extraer entidades del texto del escrito
    const entidadesTexto = extraerEntidades(textoDoc, opciones);
    const partesTexto = extraerPartesDeEscrito(textoDoc, abogado);
    entidadesTexto.push(...partesTexto);

    // 3. Filtrar exclusiones de entidadesTexto (Abogado y Fecha de Hoy)
    const entidadesTextoFiltradas = entidadesTexto.filter(e => {
      if (e.tipo === 'fecha' && e.normalizado === fechaHoyIso) {
        return false;
      }
      if (e.tipo === 'cédula / NIT') {
        if (abogadoNorm.cedula && e.normalizado === abogadoNorm.cedula) return false;
        if (abogadoNorm.tp && e.normalizado === abogadoNorm.tp) return false;
      }
      if (e.tipo === 'correo' && abogadoNorm.correo && e.normalizado === abogadoNorm.correo) {
        return false;
      }
      if (e.tipo === 'teléfono' && abogadoNorm.telefono && e.normalizado === abogadoNorm.telefono) {
        return false;
      }
      if (e.tipo === 'parte') {
        if (abogadoNorm.nombre && (e.normalizado === abogadoNorm.nombre || abogadoNorm.nombre.includes(e.normalizado))) {
          return false;
        }
      }
      return true;
    });

    // 4. Invenciones (en el escrito pero no en datos)
    const invenciones = [];
    const vistasInv = new Set();

    for (const et of entidadesTextoFiltradas) {
      const claveUnica = `${et.tipo}:${et.normalizado}`;
      if (vistasInv.has(claveUnica)) continue;

      let coincide = false;
      if (et.tipo === 'parte') {
        coincide = entidadesDatos.some(ed => {
          if (ed.tipo !== 'parte') return false;
          return ed.normalizado === et.normalizado ||
            ed.normalizado.includes(et.normalizado) ||
            et.normalizado.includes(ed.normalizado);
        });
      } else {
        coincide = entidadesDatos.some(ed => ed.tipo === et.tipo && ed.normalizado === et.normalizado);
        if (!coincide && datos && typeof datos === 'object') {
          for (const v of Object.values(datos)) {
            if (typeof v === 'string' && (v.includes(et.normalizado) || v.includes(et.valor))) {
              coincide = true;
              break;
            }
          }
        }
      }

      if (!coincide) {
        vistasInv.add(claveUnica);
        invenciones.push({
          tipo: et.tipo,
          valor: et.valor,
          textoOriginal: et.textoOriginal || et.valor,
          normalizado: et.normalizado,
          detalle: `En el escrito pero no en tus datos (${et.tipo})`
        });
      }
    }

    // 5. Omisiones (en tus datos pero no en el escrito)
    const omisiones = [];
    const vistasOm = new Set();

    for (const ed of entidadesDatos) {
      const claveUnica = `${ed.tipo}:${ed.normalizado}`;
      if (vistasOm.has(claveUnica)) continue;

      if (ed.tipo === 'cédula / NIT' && (ed.normalizado === abogadoNorm.cedula || ed.normalizado === abogadoNorm.tp)) continue;
      if (ed.tipo === 'correo' && ed.normalizado === abogadoNorm.correo) continue;
      if (ed.tipo === 'teléfono' && ed.normalizado === abogadoNorm.telefono) continue;
      if (ed.tipo === 'parte' && ed.normalizado === abogadoNorm.nombre) continue;

      let presente = false;
      if (ed.tipo === 'parte') {
        const textoNorm = normalizarNombre(textoDoc);
        presente = entidadesTexto.some(et => {
          if (et.tipo !== 'parte') return false;
          return et.normalizado === ed.normalizado ||
            et.normalizado.includes(ed.normalizado) ||
            ed.normalizado.includes(et.normalizado);
        }) || (ed.normalizado.length >= 4 && textoNorm.includes(ed.normalizado));
      } else {
        presente = entidadesTexto.some(et => et.tipo === ed.tipo && et.normalizado === ed.normalizado);
        if (!presente && ed.normalizado) {
          if (ed.tipo === 'valor') {
            presente = textoDoc.includes(ed.normalizado) || textoDoc.includes(ed.valor);
          } else if (ed.tipo === 'cédula / NIT') {
            const soloDigitosTexto = textoDoc.replace(/\D/g, '');
            presente = soloDigitosTexto.includes(ed.normalizado);
          } else if (ed.tipo === 'teléfono' || ed.tipo === 'radicado') {
            const soloDigitosTexto = textoDoc.replace(/\D/g, '');
            presente = soloDigitosTexto.includes(ed.normalizado);
          } else if (ed.tipo === 'correo' || ed.tipo === 'matrícula') {
            presente = textoDoc.toLowerCase().includes(ed.normalizado.toLowerCase());
          }
        }
      }

      if (!presente) {
        vistasOm.add(claveUnica);
        omisiones.push({
          tipo: ed.tipo,
          valor: ed.valor,
          textoOriginal: ed.textoOriginal || ed.valor,
          normalizado: ed.normalizado,
          detalle: `En tus datos pero no en el escrito (${ed.tipo})`
        });
      }
    }

    // 6. Discrepancias entre cifra y letras
    const discrepanciasCifrasLetras = detectarDiscrepanciasCifrasLetras(textoDoc, entidadesDatos);

    // 7. Alertas de NIT (dígito de verificación incorrecto)
    const alertasNit = [];
    const nitsVistos = new Set();
    [...entidadesDatos, ...entidadesTextoFiltradas].forEach(e => {
      if (e.tipo === 'cédula / NIT' && e.validacionNit && e.validacionNit.dvIngresado !== null) {
        if (!e.validacionNit.valido && !nitsVistos.has(e.valor)) {
          nitsVistos.add(e.valor);
          alertasNit.push({
            tipo: 'alerta_nit',
            nit: e.valor,
            dvIngresado: e.validacionNit.dvIngresado,
            dvCalculado: e.validacionNit.dvCalculado,
            textoOriginal: e.textoOriginal || e.valor,
            detalle: e.validacionNit.mensaje
          });
        }
      }
    });

    return {
      invenciones,
      omisiones,
      discrepanciasCifrasLetras,
      alertasNit,
      total: invenciones.length + omisiones.length + discrepanciasCifrasLetras.length + alertasNit.length,
      entidadesDatos,
      entidadesTexto: entidadesTextoFiltradas
    };
  }

  function digitsStart57(d) {
    return d.startsWith('57') && d.length === 12;
  }

  // Exportar para navegadores y entornos CommonJS / JXA / node
  const exportTarget = typeof exports !== 'undefined' ? exports : (typeof window !== 'undefined' ? window : global);
  exportTarget.auditarDatosYEscrito = auditarDatosYEscrito;
  exportTarget.extraerEntidades = extraerEntidades;
  exportTarget.palabrasANumero = palabrasANumero;
  exportTarget.normalizarNombre = normalizarNombre;
  exportTarget.calcularDvNit = calcularDvNit;
  exportTarget.validarNit = validarNit;
  exportTarget.formatearNit = formatearNit;
  exportTarget.formatearRadicado = formatearRadicado;
  exportTarget.decodificarRadicado = decodificarRadicado;
  exportTarget.validarRadicado = validarRadicado;
  exportTarget.numeroALetras = numeroALetras;
  exportTarget.detectarDiscrepanciasCifrasLetras = detectarDiscrepanciasCifrasLetras;

})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
