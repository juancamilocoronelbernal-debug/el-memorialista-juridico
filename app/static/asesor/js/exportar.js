/* ============================================================
   exportar.js — Descargas generadas 100 % en el navegador:
   - Word (.docx) real, que abre en Word, Google Docs, LibreOffice,
     WPS y en los celulares (antes era un .doc "disfrazado").
   - PDF directo, sin el cuadro de impresión (útil en el celular).
   - Recordatorio de calendario (.ics) para el vencimiento.
   Nada de esto usa internet ni librerías externas: funciona igual
   en la versión sin conexión.
   ============================================================ */
window.AJ = window.AJ || {};

(function () {
  'use strict';

  const utf8 = s => new TextEncoder().encode(String(s));

  /* ---------- ZIP (método "store", sin compresión) ---------- */
  const TABLA_CRC = (() => {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
      t[n] = c >>> 0;
    }
    return t;
  })();
  function crc32(bytes) {
    let c = 0xFFFFFFFF;
    for (let i = 0; i < bytes.length; i++) c = TABLA_CRC[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }
  function fechaDos(d) {
    const anio = Math.max(1980, d.getFullYear());
    return {
      hora: (d.getHours() << 11) | (d.getMinutes() << 5) | Math.floor(d.getSeconds() / 2),
      dia: ((anio - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate()
    };
  }
  /** archivos: [{ nombre: 'word/document.xml', datos: string | Uint8Array }] → Uint8Array */
  function zip(archivos, fecha) {
    const f = fechaDos(fecha || new Date());
    const partes = [];
    const central = [];
    let desplazamiento = 0;
    const u16 = (v, n, o) => { v.setUint16(o, n, true); };
    const u32 = (v, n, o) => { v.setUint32(o, n >>> 0, true); };
    archivos.forEach(a => {
      const nombre = utf8(a.nombre);
      const datos = a.datos instanceof Uint8Array ? a.datos : utf8(a.datos);
      const crc = crc32(datos);
      const cab = new Uint8Array(30 + nombre.length);
      const v = new DataView(cab.buffer);
      u32(v, 0x04034b50, 0); u16(v, 20, 4); u16(v, 0x0800, 6); u16(v, 0, 8);
      u16(v, f.hora, 10); u16(v, f.dia, 12); u32(v, crc, 14); u32(v, datos.length, 18); u32(v, datos.length, 22);
      u16(v, nombre.length, 26); u16(v, 0, 28); cab.set(nombre, 30);
      partes.push(cab, datos);
      const cd = new Uint8Array(46 + nombre.length);
      const w = new DataView(cd.buffer);
      u32(w, 0x02014b50, 0); u16(w, 20, 4); u16(w, 20, 6); u16(w, 0x0800, 8); u16(w, 0, 10);
      u16(w, f.hora, 12); u16(w, f.dia, 14); u32(w, crc, 16); u32(w, datos.length, 20); u32(w, datos.length, 24);
      u16(w, nombre.length, 28); u16(w, 0, 30); u16(w, 0, 32); u16(w, 0, 34); u16(w, 0, 36); u32(w, 0, 38); u32(w, desplazamiento, 42);
      cd.set(nombre, 46);
      central.push(cd);
      desplazamiento += cab.length + datos.length;
    });
    const tamCentral = central.reduce((s, x) => s + x.length, 0);
    const fin = new Uint8Array(22);
    const e = new DataView(fin.buffer);
    u32(e, 0x06054b50, 0); u16(e, 0, 4); u16(e, 0, 6); u16(e, archivos.length, 8); u16(e, archivos.length, 10);
    u32(e, tamCentral, 12); u32(e, desplazamiento, 16); u16(e, 0, 20);
    const todo = [...partes, ...central, fin];
    const salida = new Uint8Array(todo.reduce((s, x) => s + x.length, 0));
    let o = 0;
    todo.forEach(x => { salida.set(x, o); o += x.length; });
    return salida;
  }

  /* ---------- Word (.docx) ---------- */
  const W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main';
  const R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
  const xml = s => String(s == null ? '' : s)
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\uFFFE\uFFFF]/g, '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  // Medidas en veinteavos de punto (twips): carta 21,59 x 27,94 cm, márgenes 2,5 cm y 3 cm
  const PAGINA = { ancho: 12240, alto: 15840, sup: 1418, inf: 1418, izq: 1701, der: 1701 };
  const ANCHO_TEXTO = PAGINA.ancho - PAGINA.izq - PAGINA.der;

  function run(texto, o) {
    o = o || {};
    const props = [o.b ? '<w:b/><w:bCs/>' : '', o.i ? '<w:i/>' : '', o.color ? `<w:color w:val="${o.color}"/>` : '', o.sz ? `<w:sz w:val="${o.sz}"/><w:szCs w:val="${o.sz}"/>` : ''].join('');
    return `<w:r>${props ? `<w:rPr>${props}</w:rPr>` : ''}<w:t xml:space="preserve">${xml(texto)}</w:t></w:r>`;
  }
  function parrafo(runs, o) {
    o = o || {};
    const ppr = [
      o.keepNext ? '<w:keepNext/>' : '', o.keepLines ? '<w:keepLines/>' : '',
      o.tabs ? `<w:tabs>${o.tabs.map(t => `<w:tab w:val="left" w:pos="${t}"/>`).join('')}</w:tabs>` : '',
      `<w:spacing w:before="${o.antes || 0}" w:after="${o.despues == null ? 200 : o.despues}" w:line="${o.linea || 336}" w:lineRule="auto"/>`,
      o.ind ? `<w:ind w:left="${o.ind.izq || 0}" w:hanging="${o.ind.colgante || 0}"/>` : '',
      `<w:jc w:val="${o.jc || 'left'}"/>`
    ].join('');
    return `<w:p><w:pPr>${ppr}</w:pPr>${Array.isArray(runs) ? runs.join('') : runs}</w:p>`;
  }
  const salto = '<w:r><w:br/></w:r>';

  function firmaCelda(f, ancho) {
    const lineas = (f.lines || []).map(l => run(l)).join(salto);
    const huella = `<w:tbl><w:tblPr><w:tblW w:w="1134" w:type="dxa"/><w:tblBorders><w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/><w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/><w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/><w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/></w:tblBorders><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid><w:gridCol w:w="1134"/></w:tblGrid><w:tr><w:trPr><w:trHeight w:val="1134" w:hRule="exact"/></w:trPr><w:tc><w:tcPr><w:tcW w:w="1134" w:type="dxa"/><w:vAlign w:val="bottom"/></w:tcPr>${parrafo(run('Huella', { sz: 14, color: '555555' }), { despues: 0, jc: 'center' })}</w:tc></w:tr></w:tbl>`;
    return `<w:tc><w:tcPr><w:tcW w:w="${ancho}" w:type="dxa"/></w:tcPr>${parrafo(run('______________________________'), { antes: 720, despues: 40, keepNext: true })}${parrafo([run(f.rol || '', { b: true }), salto, lineas], { despues: 120, keepNext: true, keepLines: true })}${huella}${parrafo('', { despues: 0 })}</w:tc>`;
  }

  function cuerpoDocx(bloques, titulo) {
    const out = [];
    out.push(parrafo(run(titulo, { b: true, sz: 28 }), { jc: 'center', despues: 360, keepNext: true }));
    bloques.forEach(x => {
      switch (x.k) {
        case 'fecha': out.push(parrafo(run(x.t), { despues: 280 })); break;
        case 'dest': out.push(parrafo(x.lines.map(l => run(l)).join(salto), { despues: 280, keepLines: true })); break;
        case 'ref': out.push(parrafo(x.lines.map((l, i) => run(l, { b: i === 0 })).join(salto), { despues: 280, keepLines: true })); break;
        case 'h': out.push(parrafo(run(x.t, { b: true }), { antes: 320, despues: 160, keepNext: true })); break;
        case 'p': out.push(parrafo(run(x.t), { jc: 'both' })); break;
        case 'ol':
        case 'ul':
          x.items.forEach((it, i) => out.push(parrafo([run(x.k === 'ol' ? `${i + 1}.` : '•'), '<w:r><w:tab/></w:r>', run(it)], { jc: 'both', despues: i === x.items.length - 1 ? 200 : 120, ind: { izq: 567, colgante: 567 }, tabs: [567] })));
          break;
        case 'firma':
          out.push(parrafo(run('______________________________'), { antes: 800, despues: 40, keepNext: true }));
          out.push(parrafo(x.lines.map((l, i) => run(l, { b: i === 0 })).join(salto), { despues: 0, keepLines: true }));
          break;
        case 'firmas': {
          const ancho = Math.floor(ANCHO_TEXTO / 2);
          const filas = [];
          for (let i = 0; i < x.items.length; i += 2) filas.push(x.items.slice(i, i + 2));
          const sinBordes = '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>';
          out.push(`<w:tbl><w:tblPr><w:tblW w:w="${ancho * 2}" w:type="dxa"/>${sinBordes}<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="227" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid><w:gridCol w:w="${ancho}"/><w:gridCol w:w="${ancho}"/></w:tblGrid>${filas.map(par => `<w:tr><w:trPr><w:cantSplit/></w:trPr>${firmaCelda(par[0], ancho)}${par[1] ? firmaCelda(par[1], ancho) : `<w:tc><w:tcPr><w:tcW w:w="${ancho}" w:type="dxa"/></w:tcPr>${parrafo('', { despues: 0 })}</w:tc>`}</w:tr>`).join('')}</w:tbl>`);
          out.push(parrafo('', { despues: 0 }));
          break;
        }
      }
    });
    return out.join('');
  }

  function docx(bloques, titulo, meta) {
    meta = meta || {};
    const ahora = new Date();
    const iso = ahora.toISOString().replace(/\.\d+Z$/, 'Z');
    const autor = meta.autor || 'El Memorialista';
    const piePagina = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="${W_NS}" xmlns:r="${R_NS}">${parrafo([run('Página ', { sz: 18, color: '555555' }), `<w:fldSimple w:instr=" PAGE ">${run('1', { sz: 18, color: '555555' })}</w:fldSimple>`, run(' de ', { sz: 18, color: '555555' }), `<w:fldSimple w:instr=" NUMPAGES ">${run('1', { sz: 18, color: '555555' })}</w:fldSimple>`], { jc: 'center', despues: 0 })}</w:ftr>`;
    const documento = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="${W_NS}" xmlns:r="${R_NS}"><w:body>${cuerpoDocx(bloques, titulo)}<w:sectPr><w:footerReference w:type="default" r:id="rIdPie"/><w:pgSz w:w="${PAGINA.ancho}" w:h="${PAGINA.alto}"/><w:pgMar w:top="${PAGINA.sup}" w:right="${PAGINA.der}" w:bottom="${PAGINA.inf}" w:left="${PAGINA.izq}" w:header="709" w:footer="567" w:gutter="0"/></w:sectPr></w:body></w:document>`;
    const estilos = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="${W_NS}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="24"/><w:szCs w:val="24"/><w:lang w:val="es-CO" w:eastAsia="es-CO" w:bidi="ar-SA"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="200" w:line="336" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style><w:style w:type="table" w:default="1" w:styleId="TablaNormal"><w:name w:val="Normal Table"/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style></w:styles>`;
    const ajustes = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="${W_NS}"><w:defaultTabStop w:val="709"/><w:characterSpacingControl w:val="doNotCompress"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>`;
    const archivos = [
      { nombre: '[Content_Types].xml', datos: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>` },
      { nombre: '_rels/.rels', datos: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>` },
      { nombre: 'word/_rels/document.xml.rels', datos: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdEstilos" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rIdAjustes" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/><Relationship Id="rIdPie" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>` },
      { nombre: 'word/document.xml', datos: documento },
      { nombre: 'word/styles.xml', datos: estilos },
      { nombre: 'word/settings.xml', datos: ajustes },
      { nombre: 'word/footer1.xml', datos: piePagina },
      { nombre: 'docProps/core.xml', datos: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>${xml(titulo)}</dc:title><dc:creator>${xml(autor)}</dc:creator><cp:lastModifiedBy>${xml(autor)}</cp:lastModifiedBy><dc:language>es-CO</dc:language><dcterms:created xsi:type="dcterms:W3CDTF">${iso}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">${iso}</dcterms:modified></cp:coreProperties>` },
      { nombre: 'docProps/app.xml', datos: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>${xml(autor)}</Application></Properties>` }
    ];
    return zip(archivos, ahora);
  }

  /* ---------- PDF ---------- */
  // Las fuentes locales se incorporan completas al PDF. El mapa ToUnicode conserva
  // los nombres también al buscar o copiar texto. No transliteramos ni reemplazamos
  // caracteres por "?": si no se pueden representar, se ofrece Word/Imprimir.
  function fuentePdf(nombre) {
    const f = AJ.pdfFuentes && AJ.pdfFuentes[nombre];
    if (!f || !f.mapa || !f.datos) {
      const error = new Error('No se cargó la fuente local del PDF. Vuelve a abrir la página o descarga el documento en Word; también puedes usar Imprimir y guardar como PDF.');
      error.code = 'PDF_FUENTE_NO_DISPONIBLE';
      throw error;
    }
    return f;
  }
  function aCodigos(texto) {
    return Array.from(String(texto == null ? '' : texto).normalize('NFC').replace(/\r\n?|\n|\t/g, ' '), ch => ch.codePointAt(0));
  }
  function validarCodigos(cods, fuente) {
    const f = fuentePdf(fuente);
    const faltan = [...new Set(cods.filter(c => !f.mapa[c]
      // Este compositor no realiza escritura bidireccional ni posiciona marcas
      // combinantes aisladas. Evita un nombre visualmente incorrecto aun si hay glifo.
      || (c >= 0x0590 && c <= 0x08ff) || (c >= 0xfb1d && c <= 0xfdff)
      || (c >= 0xfe70 && c <= 0xfeff) || /\p{Mark}/u.test(String.fromCodePoint(c))))];
    if (faltan.length) {
      const muestra = faltan.slice(0, 8).map(c => `U+${c.toString(16).toUpperCase().padStart(4, '0')} (${String.fromCodePoint(c)})`).join(', ');
      const error = new Error(`El PDF directo no puede representar con fidelidad estos caracteres: ${muestra}. Descarga Word para conservar el texto completo, o usa Imprimir y guardar como PDF con las fuentes de tu dispositivo.`);
      error.code = 'PDF_CARACTERES_NO_COMPATIBLES';
      error.caracteres = faltan.map(c => String.fromCodePoint(c));
      throw error;
    }
    return f;
  }
  const anchoCodigos = (cods, fuente, tam) => {
    const f = validarCodigos(cods, fuente);
    return cods.reduce((s, c) => s + f.mapa[c][1], 0) * tam / 1000;
  };

  // Parte un texto en líneas que caben en "ancho" (puntos)
  function partir(texto, fuente, tam, ancho) {
    const palabras = aCodigos(texto).reduce((acc, c) => {
      if (c === 32) { if (acc[acc.length - 1].length) acc.push([]); } else acc[acc.length - 1].push(c);
      return acc;
    }, [[]]).filter(p => p.length);
    const espacio = anchoCodigos([32], fuente, tam);
    const lineas = [];
    let actual = [], anchoActual = 0;
    const cerrar = () => { if (actual.length) lineas.push({ palabras: actual, ancho: anchoActual }); actual = []; anchoActual = 0; };
    palabras.forEach(p => {
      let ap = anchoCodigos(p, fuente, tam);
      if (ap > ancho) { // palabra más larga que la línea (correos, enlaces): se corta por caracteres
        cerrar();
        let trozo = [];
        p.forEach(c => {
          const ac = anchoCodigos([c], fuente, tam);
          if (anchoCodigos(trozo, fuente, tam) + ac > ancho && trozo.length) { lineas.push({ palabras: [trozo], ancho: anchoCodigos(trozo, fuente, tam) }); trozo = []; }
          trozo.push(c);
        });
        p = trozo; ap = anchoCodigos(p, fuente, tam);
      }
      const extra = actual.length ? espacio + ap : ap;
      if (anchoActual + extra > ancho && actual.length) { cerrar(); actual = [p]; anchoActual = ap; }
      else { actual.push(p); anchoActual += extra; }
    });
    cerrar();
    return lineas;
  }

  const num = n => (Math.round(n * 100) / 100).toString();
  function hexUtf16(s) {
    s = String(s == null ? '' : s);
    let h = 'FEFF';
    for (let i = 0; i < s.length; i++) h += s.charCodeAt(i).toString(16).padStart(4, '0').toUpperCase();
    return '<' + h + '>';
  }

  function pdf(bloques, titulo, meta) {
    meta = meta || {};
    const cids = new Map(), usados = { F1: new Set(), F2: new Set() };
    const cidDe = (c, fuente) => {
      if (!cids.has(c)) cids.set(c, cids.size + 1);
      usados[fuente].add(c);
      return cids.get(c).toString(16).padStart(4, '0');
    };
    const cadenaPdf = (cods, fuente = 'F1') => '<' + cods.map(c => cidDe(c, fuente)).join('') + '>';
    const mostrar = (cods, fuente, extra, tam) => {
      if (!extra) return cadenaPdf(cods, fuente) + ' Tj';
      const partes = []; let grupo = [];
      cods.forEach(c => {
        grupo.push(c);
        if (c === 32) { partes.push(cadenaPdf(grupo, fuente), num(-extra * 1000 / tam)); grupo = []; }
      });
      if (grupo.length) partes.push(cadenaPdf(grupo, fuente));
      return '[' + partes.join(' ') + '] TJ';
    };
    const P = { ancho: 612, alto: 792, sup: 71, inf: 71, izq: 85, der: 85 };
    const anchoTexto = P.ancho - P.izq - P.der;
    const TAM = 12, INTER = 16.8;
    const paginas = [];
    let ops = null, y = 0; // y: distancia desde el borde superior hasta la línea base actual
    const nueva = () => { ops = []; paginas.push(ops); y = P.sup; };
    const libre = () => P.alto - P.inf - y;
    nueva();
    const asegurar = alto => { if (alto > libre() && y > P.sup + 1) nueva(); };
    const linea = (cods, fuente, tam, x, alinear, anchoDisp, ultima) => {
      const yb = P.alto - y;
      let tw = 0, xx = x;
      const anchoL = anchoCodigos(cods, fuente, tam);
      if (alinear === 'centro') xx = x + (anchoDisp - anchoL) / 2;
      else if (alinear === 'justificado' && !ultima) {
        const espacios = cods.filter(c => c === 32).length;
        if (espacios) { tw = (anchoDisp - anchoL) / espacios; if (tw > tam * 0.9) tw = 0; }
      }
      ops.push(`BT /${fuente} ${num(tam)} Tf ${num(xx)} ${num(yb)} Td ${mostrar(cods, fuente, tw, tam)} ET`);
    };
    const unir = palabras => palabras.reduce((acc, p, i) => (i ? acc.concat([32], p) : acc.concat(p)), []);

    // Avanza a la siguiente línea base (la primera línea de cada página arranca en el margen superior)
    const bajar = (inter, tam) => { if (inter > libre()) nueva(); y += y === P.sup ? tam * 0.8 : inter; };

    // Párrafo con sangría francesa opcional (listas)
    function texto(t, o) {
      o = o || {};
      const fuente = o.negrita ? 'F2' : 'F1', tam = o.tam || TAM, inter = o.inter || (tam * 1.4);
      const sang = o.sangria || 0;
      const lineas = partir(t, fuente, tam, anchoTexto - sang);
      if (!lineas.length) { y += o.despues || 0; return; }
      // Un título nunca queda solo al pie: necesita espacio para él y dos líneas del texto que sigue
      const minimo = (o.antes || 0) + inter * (o.conSiguiente ? 3 : Math.min(2, lineas.length));
      asegurar(o.juntas ? inter * lineas.length : minimo);
      if (o.antes && y > P.sup + 1) y += o.antes;
      lineas.forEach((l, i) => {
        bajar(inter, tam);
        if (i === 0 && o.vineta) ops.push(`BT /F1 ${num(tam)} Tf 0 Tw ${num(P.izq)} ${num(P.alto - y)} Td ${cadenaPdf(aCodigos(o.vineta))} Tj ET`);
        linea(unir(l.palabras), fuente, tam, P.izq + sang, o.alinear || 'izquierda', anchoTexto - sang, i === lineas.length - 1);
      });
      y += o.despues == null ? 10 : o.despues;
    }
    function lineasSimples(lines, o) {
      o = o || {};
      const conjunto = [];
      lines.forEach((l, i) => partir(l, (o.primeraNegrita && i === 0) ? 'F2' : 'F1', TAM, anchoTexto).forEach(p => conjunto.push({ p, f: (o.primeraNegrita && i === 0) ? 'F2' : 'F1' })));
      asegurar(conjunto.length * INTER + (o.antes || 0));
      if (o.antes && y > P.sup + 1) y += o.antes;
      conjunto.forEach(({ p, f }) => { bajar(INTER, TAM); linea(unir(p.palabras), f, TAM, P.izq, 'izquierda', anchoTexto, true); });
      y += o.despues == null ? 14 : o.despues;
    }
    function bloqueFirma(lines, x, anchoCol) {
      ops.push(`0.6 w ${num(x)} ${num(P.alto - y)} m ${num(x + Math.min(220, anchoCol - 10))} ${num(P.alto - y)} l S`);
      lines.forEach((l, i) => partir(l, i === 0 ? 'F2' : 'F1', 11, anchoCol - 10).forEach(p => { bajar(14, 11); linea(unir(p.palabras), i === 0 ? 'F2' : 'F1', 11, x, 'izquierda', anchoCol, true); }));
    }
    const altoFirma = (lines, anchoCol) => lines.reduce((s, l, i) => s + partir(l, i === 0 ? 'F2' : 'F1', 11, anchoCol - 10).length * 14, 0);
    const huella = xCol => {
      asegurar(52);
      const yh = y + 8;
      ops.push(`0.6 w ${num(xCol)} ${num(P.alto - yh - 40)} 40 40 re S`);
      ops.push(`BT /F1 7 Tf ${num(xCol + 8)} ${num(P.alto - yh - 36)} Td ${cadenaPdf(aCodigos('Huella'))} Tj ET`);
      y = yh + 44;
    };

    texto(titulo, { negrita: true, tam: 14, alinear: 'centro', despues: 18 });
    bloques.forEach(x => {
      switch (x.k) {
        case 'fecha': texto(x.t, { despues: 14 }); break;
        case 'dest': lineasSimples(x.lines); break;
        case 'ref': lineasSimples(x.lines, { primeraNegrita: true }); break;
        case 'h': texto(x.t, { negrita: true, antes: 8, despues: 6, conSiguiente: true }); break;
        case 'p': texto(x.t, { alinear: 'justificado' }); break;
        case 'ol':
        case 'ul':
          x.items.forEach((it, i) => texto(it, { alinear: 'justificado', sangria: 24, vineta: x.k === 'ol' ? `${i + 1}.` : '\u2022', despues: i === x.items.length - 1 ? 10 : 5 }));
          break;
        case 'firma': {
          const alto = 40 + altoFirma(x.lines, anchoTexto) + 10;
          asegurar(Math.min(alto, P.alto - P.sup - P.inf));
          y += 40;
          bloqueFirma(x.lines, P.izq, anchoTexto);
          y += 10;
          break;
        }
        case 'firmas': {
          const anchoCol = anchoTexto / 2;
          for (let i = 0; i < x.items.length; i += 2) {
            const par = x.items.slice(i, i + 2);
            const altoFila = 36 + Math.max(...par.map(f => altoFirma([f.rol, ...f.lines], anchoCol))) + 52;
            // Datos excepcionalmente largos: firma a ancho completo y paginada.
            // Evita que nombres o direcciones salgan por debajo de la hoja.
            if (altoFila > P.alto - P.sup - P.inf) {
              par.forEach(f => {
                asegurar(Math.min(36 + altoFirma([f.rol, ...f.lines], anchoTexto) + 52, P.alto - P.sup - P.inf));
                y += 36; bloqueFirma([f.rol, ...f.lines], P.izq, anchoTexto); huella(P.izq); y += 6;
              });
              continue;
            }
            asegurar(altoFila);
            const y0 = y + 36;
            let maxY = y0;
            par.forEach((f, j) => {
              y = y0;
              const xCol = P.izq + j * anchoCol;
              bloqueFirma([f.rol, ...f.lines], xCol, anchoCol);
              huella(xCol);
              maxY = Math.max(maxY, y);
            });
            y = maxY + 6;
          }
          break;
        }
      }
    });

    // Ensamblar los flujos antes de la fuente: los pies también necesitan CIDs.
    const total = paginas.length;
    const flujos = paginas.map((o, i) => {
      const pieCods = aCodigos(`Página ${i + 1} de ${total}`);
      const pie = `BT /F1 9 Tf ${num(P.ancho / 2 - anchoCodigos(pieCods, 'F1', 9) / 2)} 36 Td ${cadenaPdf(pieCods)} Tj ET`;
      return ['0 0 0 rg 0 0 0 RG', ...o, '0.35 0.35 0.35 rg', pie].join('\n');
    });
    const objetos = [];
    const agregar = contenido => { objetos.push(contenido); return objetos.length; };
    const flujoBinario = (contenido, extras = '') => agregar(`<< /Length ${contenido.length} ${extras} >>\nstream\n${contenido}\nendstream`);
    const binario = bytes => { let s = ''; for (let i = 0; i < bytes.length; i += 8192) s += String.fromCharCode(...bytes.subarray(i, i + 8192)); return s; };
    const idCatalogo = agregar(null), idPaginas = agregar(null);
    function incorporarFuente(nombre) {
      const f = fuentePdf(nombre);
      const cps = [...usados[nombre]].sort((a, b) => cids.get(a) - cids.get(b));
      const ultimo = Math.max(0, ...cps.map(c => cids.get(c)));
      const mapaGlifos = new Uint8Array((ultimo + 1) * 2);
      const anchos = [];
      cps.forEach(c => {
        const cid = cids.get(c), glifo = f.mapa[c][0];
        mapaGlifos[cid * 2] = glifo >> 8; mapaGlifos[cid * 2 + 1] = glifo & 255;
        anchos.push(`${cid} [${f.mapa[c][1]}]`);
      });
      const cmap = ['/CIDInit /ProcSet findresource begin', '12 dict begin', 'begincmap',
        '/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def',
        `/CMapName /${f.nombre}-Unicode def`, '/CMapType 2 def', '1 begincodespacerange', '<0000> <FFFF>', 'endcodespacerange'];
      for (let i = 0; i < cps.length; i += 100) {
        const grupo = cps.slice(i, i + 100);
        cmap.push(`${grupo.length} beginbfchar`);
        grupo.forEach(c => cmap.push(`<${cids.get(c).toString(16).padStart(4, '0')}> ${hexUtf16(String.fromCodePoint(c)).replace('<FEFF', '<')}`));
        cmap.push('endbfchar');
      }
      cmap.push('endcmap', 'CMapName currentdict /CMap defineresource pop', 'end', 'end');
      const raw = atob(f.datos);
      const idArchivo = flujoBinario(raw, `/Length1 ${raw.length}`);
      const idDescriptor = agregar(`<< /Type /FontDescriptor /FontName /${f.nombre} /Flags 32 /FontBBox [${f.caja.join(' ')}] /ItalicAngle ${f.inclinacion} /Ascent ${f.ascenso} /Descent ${f.descenso} /CapHeight ${f.altoMayusculas} /StemV ${nombre === 'F2' ? 120 : 80} /FontFile2 ${idArchivo} 0 R >>`);
      const idMapa = flujoBinario(binario(mapaGlifos));
      const idUnicode = flujoBinario(cmap.join('\n'));
      const idDescendiente = agregar(`<< /Type /Font /Subtype /CIDFontType2 /BaseFont /${f.nombre} /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> /FontDescriptor ${idDescriptor} 0 R /CIDToGIDMap ${idMapa} 0 R /DW 600 /W [${anchos.join(' ')}] >>`);
      return agregar(`<< /Type /Font /Subtype /Type0 /BaseFont /${f.nombre} /Encoding /Identity-H /DescendantFonts [${idDescendiente} 0 R] /ToUnicode ${idUnicode} 0 R >>`);
    }
    const idF1 = incorporarFuente('F1'), idF2 = incorporarFuente('F2');
    const ahora = new Date();
    const d2 = n => String(n).padStart(2, '0');
    const fechaPdf = `D:${ahora.getUTCFullYear()}${d2(ahora.getUTCMonth() + 1)}${d2(ahora.getUTCDate())}${d2(ahora.getUTCHours())}${d2(ahora.getUTCMinutes())}${d2(ahora.getUTCSeconds())}Z`;
    const idInfo = agregar(`<< /Title ${hexUtf16(titulo)} /Producer ${hexUtf16(meta.autor || 'El Memorialista')} /Creator ${hexUtf16(meta.autor || 'El Memorialista')} /CreationDate (${fechaPdf}) >>`);
    const kids = [];
    flujos.forEach(flujo => {
      const idFlujo = agregar(`<< /Length ${flujo.length} >>\nstream\n${flujo}\nendstream`);
      kids.push(agregar(`<< /Type /Page /Parent ${idPaginas} 0 R /MediaBox [0 0 ${P.ancho} ${P.alto}] /Resources << /Font << /F1 ${idF1} 0 R /F2 ${idF2} 0 R >> >> /Contents ${idFlujo} 0 R >>`));
    });
    objetos[idCatalogo - 1] = `<< /Type /Catalog /Pages ${idPaginas} 0 R /Lang (es-CO) /ViewerPreferences << /DisplayDocTitle true >> >>`;
    objetos[idPaginas - 1] = `<< /Type /Pages /Kids [${kids.map(k => `${k} 0 R`).join(' ')}] /Count ${kids.length} >>`;
    let salida = '%PDF-1.4\n%\u00E2\u00E3\u00CF\u00D3\n';
    const offsets = [];
    objetos.forEach((o, i) => { offsets.push(salida.length); salida += `${i + 1} 0 obj\n${o}\nendobj\n`; });
    const xref = salida.length;
    salida += `xref\n0 ${objetos.length + 1}\n0000000000 65535 f \n` + offsets.map(o => `${String(o).padStart(10, '0')} 00000 n \n`).join('');
    salida += `trailer\n<< /Size ${objetos.length + 1} /Root ${idCatalogo} 0 R /Info ${idInfo} 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
    const bytes = new Uint8Array(salida.length);
    for (let i = 0; i < salida.length; i++) bytes[i] = salida.charCodeAt(i) & 0xFF;
    return bytes;
  }

  /* ---------- Calendario (.ics) ---------- */
  function ics(evento) {
    if (!evento || !(evento.fecha instanceof Date) || !Number.isFinite(evento.fecha.getTime())) {
      throw new Error('El recordatorio necesita una fecha válida. Revisa los datos del trámite.');
    }
    const d2 = n => String(n).padStart(2, '0');
    const dia = f => `${f.getFullYear()}${d2(f.getMonth() + 1)}${d2(f.getDate())}`;
    const instante = f => `${f.getUTCFullYear()}${d2(f.getUTCMonth() + 1)}${d2(f.getUTCDate())}T${d2(f.getUTCHours())}${d2(f.getUTCMinutes())}${d2(f.getUTCSeconds())}Z`;
    const escapar = s => String(s || '').replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r\n|\r|\n/g, '\\n');
    const plegar = lineaIcs => {
      const bytes = utf8(lineaIcs);
      if (bytes.length <= 75) return lineaIcs;
      const partes = [];
      let actual = '', largo = 0;
      for (const ch of lineaIcs) {
        const b = utf8(ch).length;
        if (largo + b > (partes.length ? 74 : 75)) { partes.push(actual); actual = ''; largo = 0; }
        actual += ch; largo += b;
      }
      partes.push(actual);
      return partes.join('\r\n ');
    };
    const fecha = evento.fecha;
    const conHora = evento.precision === 'hora';
    const fin = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate() + 1);
    const ahora = new Date();
    const sello = instante(ahora);
    const uid = `${instante(fecha)}-${Math.random().toString(36).slice(2, 10)}@el-memorialista.local`;
    const fechas = conHora
      ? [`DTSTART:${instante(fecha)}`, `DTEND:${instante(new Date(fecha.getTime() + 60000))}`]
      : [`DTSTART;VALUE=DATE:${dia(fecha)}`, `DTEND;VALUE=DATE:${dia(fin)}`];
    const lineas = [
      'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//El Memorialista//Recordatorios//ES', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
      'BEGIN:VEVENT', `UID:${uid}`, `DTSTAMP:${sello}`, ...fechas,
      `SUMMARY:${escapar(evento.titulo)}`, `DESCRIPTION:${escapar(evento.descripcion)}`, 'TRANSP:TRANSPARENT',
      'BEGIN:VALARM', 'ACTION:DISPLAY', `DESCRIPTION:${escapar(evento.titulo)}`, conHora ? 'TRIGGER:-PT1H' : 'TRIGGER:-PT15H', 'END:VALARM',
      'BEGIN:VALARM', 'ACTION:DISPLAY', `DESCRIPTION:${escapar(evento.titulo)}`, conHora ? 'TRIGGER:PT0S' : 'TRIGGER:PT8H', 'END:VALARM',
      'END:VEVENT', 'END:VCALENDAR'
    ];
    return lineas.map(plegar).join('\r\n') + '\r\n';
  }

  AJ.exportar = { zip, crc32, docx, pdf, ics, partir, aCodigos };
})();
