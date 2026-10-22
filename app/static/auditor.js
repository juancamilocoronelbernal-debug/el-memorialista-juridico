/**
 * El Memorialista - Auditoría de datos (formulario vs. escrito generado)
 * Frontend puramente en JavaScript sin IA.
 * 
 * Extrae y normaliza:
 * 1. Cédulas y NIT (con y sin puntos).
 * 2. Radicados de 23 dígitos (con o sin guiones).
 * 3. Fechas (DD/MM/AAAA, DD-MM-AAAA, "3 de marzo de 2026", ISO).
 * 4. Valores en pesos (en cifras y en letras).
 * 5. Correos electrónicos.
 * 6. Teléfonos celulares y fijos colombianos.
 * 7. Matrículas inmobiliarias.
 * 8. Partes procesales (nombres en mayúsculas sostenidas o negrilla).
 * 
 * Excluye:
 * - Datos del abogado (nombre, cédula, TP, teléfono, correo, ciudad).
 * - Fecha de hoy.
 */

(function (global) {
  'use strict';

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

  /**
   * Determina si un texto corresponde a una ciudad o locación geográfica.
   */
  function esCiudadOGeografia(s) {
    const norm = normalizarNombre(s);
    if (!norm) return true;
    const tokens = norm.split(/\s+/).filter(Boolean);
    return tokens.every(t => t === 'de' || t === 'del' || t === 'd' || t === 'c' || t === 'distrito' || t === 'capital' || CIUDADES_COLOMBIA.has(t));
  }

  /**
   * Determina si un texto en mayúsculas o negrilla es una autoridad judicial,
   * encabezado procesal o palabra reservada en lugar de una parte.
   */
  function esEncabezadoOAutoridad(s) {
    const norm = normalizarNombre(s);
    if (!norm) return true;

    // Si es una cifra en letras o incluye 'pesos', es un valor económico
    if (norm.includes('pesos') || norm.includes('m cte') || norm.includes('moneda corriente')) return true;
    if (palabrasANumero(s) !== null) return true;

    // Si es ciudad geográfica
    if (esCiudadOGeografia(s)) return true;

    const patrones = [
      'juez', 'juzgad', 'tribunal', 'magistrad', 'corte', 'despacho', 'republica', 'rama judicial',
      'notificacion', 'pretension', 'hechos', 'derecho', 'prueba', 'anexo', 'juramento', 'medida',
      'cuantia', 'competencia', 'tutela', 'demanda', 'poder', 'alegato', 'recurso', 'notaria',
      'secretari', 'ministeri', 'alcaldi', 'inspeccion', 'procuradur', 'fiscali', 'personeri',
      'defensori', 'consejo', 'centro de conciliacion', 'atentamente', 'cordialmente',
      'articulo', 'ley ', 'decreto', 'constitucion', 'acuerdo', 'resolucion', 'circulo',
      'primero', 'segundo', 'tercero', 'cuarto', 'quinto', 'sexto', 'septimo', 'octavo', 'noveno', 'decimo',
      'paragrafo', 'capitulo', 'seccion', 'numeral', 'inciso', 'acapite', 'asunto',
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

  /**
   * Extrae entidades estructuradas desde un bloque de texto.
   */
  function extraerEntidades(texto, opciones = {}) {
    const textoStr = String(texto || '').normalize('NFC');
    const entidades = [];
    if (!textoStr.trim()) return entidades;

    let textoTrabajo = textoStr;

    // 1. Radicados de 23 dígitos (con o sin guiones/espacios)
    // Ejemplo: 11001-31-03-001-2023-00123-00 o 11001310300120230012300
    const reRadicado = /(?<!\d)(\d(?:[-\s]?\d){22})(?!\d)/g;
    let match;
    while ((match = reRadicado.exec(textoStr)) !== null) {
      const original = match[1];
      const norm = original.replace(/[-\s\.]/g, '');
      if (norm.length === 23) {
        entidades.push({
          tipo: 'radicado',
          valor: original,
          textoOriginal: original,
          normalizado: norm,
          detalle: `Radicado judicial (23 dígitos): ${original}`
        });
        textoTrabajo = textoTrabajo.replace(original, ' '.repeat(original.length));
      }
    }

    // 2. Matrículas inmobiliarias
    // SNR: 50C-123456, 050-123456, 50N-001234
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

    // 3. Valores en pesos (en cifras y en letras)
    // a) Cifras: $50.000.000, $ 50.000.000, 50.000.000 pesos, etc.
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

    // b) Letras: cincuenta millones de pesos [m/cte / moneda corriente]
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

    // 4. Fechas (DD/MM/AAAA, DD-MM-AAAA, "3 de marzo de 2026", ISO AAAA-MM-DD)
    // a) Formato textual: "3 de marzo de 2026"
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

    // b) Formato numérico DD/MM/AAAA o DD-MM-AAAA
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

    // c) Formato ISO AAAA-MM-DD
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
    // Celulares colombianos (3xx xxx xxxx) o precedidos por tel/cel
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
    // a) NIT: 900.123.456-7 o precedido de NIT
    const reNit = /\b(?:NIT|N\.I\.T\.)\s*[:#]?\s*(\d{1,3}(?:\.\d{3}){2,3}(?:-\d)?|\d{8,10}(?:-\d)?)\b|\b(\d{3}\.\d{3}\.\d{3}-\d)\b/gi;
    while ((match = reNit.exec(textoTrabajo)) !== null) {
      const nitRaw = match[1] || match[2];
      const baseNit = nitRaw.replace(/\D/g, '').slice(0, 9);
      entidades.push({
        tipo: 'cédula / NIT',
        valor: nitRaw,
        textoOriginal: match[0],
        normalizado: baseNit,
        detalle: `NIT: ${nitRaw}`
      });
      textoTrabajo = textoTrabajo.replace(match[0], ' '.repeat(match[0].length));
    }

    // b) Cédula: con formato de puntos 1.020.304.050 o precedida por C.C. / cédula
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

  /**
   * Extrae nombres de partes desde los datos del formulario.
   */
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

  /**
   * Extrae nombres de partes desde el texto del escrito (en mayúsculas sostenidas o negrilla).
   */
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
          textoOriginal: match[0],
          normalizado: norm,
          detalle: `Nombre en negrilla: ${candidato}`
        });
      }
    }

    // 2. Nombres en mayúscula sostenida (mínimo 2 palabras de >=2 letras)
    // Usar lookarounds en vez de \b para evitar el fallo de \b con tildes (Á, É, Í, Ó, Ú, Ñ)
    const reMayus = /(?<![A-Za-zÁÉÍÓÚáéíóúñÑ])([A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,}){1,8})(?![A-Za-zÁÉÍÓÚáéíóúñÑ])/g;
    while ((match = reMayus.exec(textoStr)) !== null) {
      const candidato = match[1].trim();
      const norm = normalizarNombre(candidato);

      if (
        !esEncabezadoOAutoridad(candidato) &&
        norm !== nombreAbogadoNorm
      ) {
        if (!partes.some(p => p.normalizado === norm)) {
          partes.push({
            tipo: 'parte',
            valor: candidato,
            textoOriginal: match[0],
            normalizado: norm,
            detalle: `Nombre en mayúsculas: ${candidato}`
          });
        }
      }
    }

    return partes;
  }

  /**
   * Ejecuta la auditoría completa entre datos del formulario y el escrito generado.
   * 
   * @param {Object} datos - state.datos (formulario)
   * @param {string} texto - state.texto (escrito generado)
   * @param {Object} perfil - state.perfil (contiene perfil.abogado)
   * @param {Object} opciones - { fechaHoy: 'YYYY-MM-DD' } opcional
   * @returns {Object} { invenciones: [], omisiones: [], total: number }
   */
  function auditarDatosYEscrito(datos, texto, perfil = {}, opciones = {}) {
    const textoDoc = String(texto || '').normalize('NFC');
    const abogado = (perfil && perfil.abogado) || {};

    // 1. Fecha de hoy para exclusión
    let fechaHoyIso = opciones.fechaHoy;
    if (!fechaHoyIso) {
      const hoy = new Date();
      fechaHoyIso = `${hoy.getFullYear()}-${pad2(hoy.getMonth() + 1)}-${pad2(hoy.getDate())}`;
    }

    // 2. Conjunto de exclusiones del abogado
    const abogadoNorm = {
      nombre: normalizarNombre(abogado.nombre || ''),
      cedula: String(abogado.cedula || '').replace(/\D/g, ''),
      tp: String(abogado.tp || '').replace(/\D/g, ''),
      correo: String(abogado.correo || '').toLowerCase().trim(),
      telefono: String(abogado.telefono || '').replace(/\D/g, ''),
      ciudad: normalizarNombre(abogado.ciudad || '')
    };

    // 3. Extraer entidades de todos los valores del formulario
    const entidadesDatos = [];
    if (datos && typeof datos === 'object') {
      for (const [clave, val] of Object.entries(datos)) {
        if (typeof val === 'string' && val.trim()) {
          const vTrim = val.trim();
          const kLower = clave.toLowerCase();

          // Si el campo es de valor/cuantía
          if (kLower.includes('cuantia') || kLower.includes('canon') || kLower.includes('valor')) {
            const digitosVal = vTrim.replace(/[^\d]/g, '');
            if (digitosVal.length > 0) {
              const num = parseInt(digitosVal, 10);
              if (num > 0) {
                entidadesDatos.push({
                  tipo: 'valor',
                  valor: `$${num.toLocaleString('es-CO')}`,
                  textoOriginal: vTrim,
                  normalizado: String(num),
                  detalle: `Valor en formulario (${clave}): $${num.toLocaleString('es-CO')}`
                });
              }
            }
            // También revisar si viene en letras
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

          // Si el campo es de cédula / NIT
          if (kLower.includes('cedula') || kLower.includes('identificacion') || kLower.includes('cc') || kLower.includes('nit')) {
            const digitos = vTrim.replace(/\D/g, '');
            if (kLower.includes('nit') && digitos.length >= 8) {
              const baseNit = digitos.slice(0, 9);
              entidadesDatos.push({
                tipo: 'cédula / NIT',
                valor: vTrim,
                textoOriginal: vTrim,
                normalizado: baseNit,
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

          // Si el campo es de teléfono
          if (kLower.includes('telefono') || kLower.includes('celular') || kLower.includes('tel')) {
            let digitos = vTrim.replace(/\D/g, '');
            if (digitos.startsWith('57') && digitos.length === 12) digitos = digitos.slice(2);
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

          // Si el campo es radicado
          if (kLower.includes('radicado')) {
            const digitosRad = vTrim.replace(/[-\s\.]/g, '');
            if (digitosRad.length === 23) {
              entidadesDatos.push({
                tipo: 'radicado',
                valor: vTrim,
                textoOriginal: vTrim,
                normalizado: digitosRad,
                detalle: `Radicado en formulario (${clave}): ${vTrim}`
              });
            }
          }

          // Si el campo es matrícula inmobiliaria
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

          // Extraer patrones generales en el texto del campo (fechas, correos, etc.)
          const extraidas = extraerEntidades(vTrim, opciones);
          entidadesDatos.push(...extraidas);
        }
      }
      // Agregar partes de datos
      const partesDatos = extraerPartesDeDatos(datos);
      entidadesDatos.push(...partesDatos);
    }

    // 4. Extraer entidades del texto del escrito
    const entidadesTexto = extraerEntidades(textoDoc, opciones);
    const partesTexto = extraerPartesDeEscrito(textoDoc, abogado);
    entidadesTexto.push(...partesTexto);

    // 5. Filtrar exclusiones de entidadesTexto (Abogado y Fecha de Hoy)
    const entidadesTextoFiltradas = entidadesTexto.filter(e => {
      // Excluir fecha de hoy
      if (e.tipo === 'fecha' && e.normalizado === fechaHoyIso) {
        return false;
      }
      // Excluir abogado
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

    // 6. Comparación de entidades:
    // a) Posibles Invenciones: En el escrito pero NO en tus datos
    const invenciones = [];
    const vistasInv = new Set();

    for (const et of entidadesTextoFiltradas) {
      const claveUnica = `${et.tipo}:${et.normalizado}`;
      if (vistasInv.has(claveUnica)) continue;

      let coincide = false;
      if (et.tipo === 'parte') {
        // En partes, coincidencia si está en entidadesDatos o si el texto normalizado contiene o es contenido
        coincide = entidadesDatos.some(ed => {
          if (ed.tipo !== 'parte') return false;
          return ed.normalizado === et.normalizado ||
            ed.normalizado.includes(et.normalizado) ||
            et.normalizado.includes(ed.normalizado);
        });
      } else {
        coincide = entidadesDatos.some(ed => ed.tipo === et.tipo && ed.normalizado === et.normalizado);
        // Si no coincidió en entidadesDatos pero el valor literal exacto estaba en algún campo de datos
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

    // b) Posibles Omisiones: En tus datos pero NO en el escrito
    const omisiones = [];
    const vistasOm = new Set();

    for (const ed of entidadesDatos) {
      const claveUnica = `${ed.tipo}:${ed.normalizado}`;
      if (vistasOm.has(claveUnica)) continue;

      // No contar datos del abogado como omisiones del escrito
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
        // Respaldo: si el valor normalizado aparece directamente en el texto
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

    return {
      invenciones,
      omisiones,
      total: invenciones.length + omisiones.length
    };
  }

  // Exportar para navegadores y entornos CommonJS / JXA / node
  const exportTarget = typeof exports !== 'undefined' ? exports : (typeof window !== 'undefined' ? window : global);
  exportTarget.auditarDatosYEscrito = auditarDatosYEscrito;
  exportTarget.extraerEntidades = extraerEntidades;
  exportTarget.palabrasANumero = palabrasANumero;
  exportTarget.normalizarNombre = normalizarNombre;

})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
