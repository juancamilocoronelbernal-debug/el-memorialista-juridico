'use strict';
/** Funciones ciudadanas locales: node tests/test_asesor_features.cjs
 * No red, navegador, npm ni escritura de documentos personales.
 */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
process.env.TZ = 'UTC';
const root = path.resolve(__dirname, '../app/static/asesor/js');
const storage = new Map(), styles = new Map(), errors = [];
const element = { dataset: {}, style: { setProperty: (k, v) => styles.set(k, v) }, setAttribute(k, v) { this[k] = v; } };
const context = {
  console: { log() {}, warn() {}, error(...args) { errors.push(args.map(String).join(' ')); } },
  document: { addEventListener() {}, documentElement: element },
  localStorage: { getItem: k => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, String(v)), removeItem: k => storage.delete(k) },
  Date, TextEncoder, TextDecoder, Uint8Array, Uint32Array, DataView, Map, Set, URL, atob,
  setTimeout, clearTimeout,
};
context.window = context;
vm.createContext(context);
const scripts = ['festivos.js', 'datos/normas.js', 'datos/entidades.js', 'datos/comunes.js',
  'datos/peticiones.js', 'datos/peticiones2.js', 'datos/peticiones3.js', 'datos/tutelas.js',
  'datos/tutelas2.js', 'datos/otros.js', 'datos/contratos.js', 'datos/mujer.js', 'datos/sinonimos.js',
  'motor.js', 'mejoras.js', 'pdf-fuentes.js', 'exportar.js', 'buscador.js', 'orientador.js',
  'seguimiento.js', 'accesibilidad.js', 'app.js'];
for (const file of scripts) vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), context, { filename: file });
const AJ = context.AJ, casos = AJ.casos.filter(c => !c.retirado);
const caso = id => { const c = casos.find(c => c.id === id); assert.ok(c, id); return c; };
const plain = x => JSON.parse(JSON.stringify(x));
const clean = s => String(s).normalize('NFC').replace(/\s+/g, ' ').trim();
const hoy = s => new Date(`${s}T12:00:00-05:00`);

function llenar(c) {
  const ui = AJ.ui || AJ.app;
  const d = ui.inicializarDatos(c);
  for (const f of ui.camposDelCaso(c).flatMap(s => s.campos)) {
    if (f.tipo === 'info') continue;
    if (f.tipo === 'checks') d[f.id] = (f.opciones || []).map(o => o.v);
    else if (['select', 'radio'].includes(f.tipo)) d[f.id] = d[f.id] || f.opciones?.[0]?.v || '';
    else if (f.tipo === 'fecha') d[f.id] = '2026-09-01';
    else if (/correo|email/i.test(f.id)) d[f.id] = 'persona@example.invalid';
    else if (/monto|precio|salario|canon|valor|cuota|dias|plazo|edad|interes|porcentaje|cantidad|numero|mora|meses/i.test(f.id)) d[f.id] = '100000';
    else d[f.id] = d[f.id] || 'Dato de prueba';
  }
  return Object.assign(d, { nombre: 'María Łukasz Șerban', numDoc: '123456789', ciudad: 'Bogotá D.C.',
    relato: 'El primero de septiembre presenté una solicitud. Conservo el radicado.',
    entidadNombre: 'Entidad de Prueba', direccion: 'Calle 1', telefono: '3000000000',
    correo: 'persona@example.invalid', cpNombre: 'Carlos Prueba', cpNumDoc: '987654321', cpCiudad: 'Bogotá D.C.', modo: 'propio' });
}

/** Lee el ZIP de forma independiente y comprueba los CRC y directorio central. */
function abrirZip(bytes) {
  const b = Buffer.from(bytes), entries = new Map();
  let at = 0;
  while (b.readUInt32LE(at) === 0x04034b50) {
    assert.equal(b.readUInt16LE(at + 8), 0, 'ZIP store');
    const n = b.readUInt16LE(at + 26), extra = b.readUInt16LE(at + 28), size = b.readUInt32LE(at + 18);
    const name = b.subarray(at + 30, at + 30 + n).toString('utf8');
    const data = b.subarray(at + 30 + n + extra, at + 30 + n + extra + size);
    assert.equal(data.length, size);
    assert.equal(AJ.exportar.crc32(data), b.readUInt32LE(at + 14), name);
    assert.ok(!entries.has(name), name);
    entries.set(name, { offset: at, data }); at += 30 + n + extra + size;
  }
  const centralAt = at; let count = 0;
  while (b.readUInt32LE(at) === 0x02014b50) {
    const n = b.readUInt16LE(at + 28), extra = b.readUInt16LE(at + 30), comment = b.readUInt16LE(at + 32);
    const name = b.subarray(at + 46, at + 46 + n).toString('utf8');
    assert.equal(b.readUInt32LE(at + 42), entries.get(name)?.offset, name);
    assert.equal(b.readUInt32LE(at + 20), entries.get(name)?.data.length, name);
    at += 46 + n + extra + comment; count++;
  }
  assert.equal(b.readUInt32LE(at), 0x06054b50);
  assert.equal(b.readUInt32LE(at + 16), centralAt);
  assert.equal(b.readUInt16LE(at + 10), count);
  assert.equal(count, entries.size);
  assert.equal(at + 22, b.length);
  return Object.fromEntries([...entries].map(([name, v]) => [name, v.data.toString('utf8')]));
}

/** Verifica offsets/longitudes y extrae el texto mediante ToUnicode del PDF real. */
function abrirPdf(bytes) {
  const s = Buffer.from(bytes).toString('latin1');
  assert.ok(s.startsWith('%PDF-1.4'));
  const xref = Number(s.match(/startxref\n(\d+)\n%%EOF\n$/)?.[1]);
  assert.equal(s.slice(xref, xref + 4), 'xref');
  const xlines = s.slice(xref).split('\n'), count = Number(xlines[1].split(' ')[1]);
  assert.ok(count > 16);
  const objects = new Map(), streams = new Map();
  for (let i = 1; i < count; i++) {
    const offset = Number(xlines[i + 2].slice(0, 10));
    const next = i + 1 < count ? Number(xlines[i + 3].slice(0, 10)) : xref;
    assert.equal(s.slice(offset, offset + `${i} 0 obj\n`.length), `${i} 0 obj\n`);
    const obj = s.slice(offset, next);
    assert.ok(obj.endsWith('\nendobj\n'));
    objects.set(i, obj);
    const stream = obj.indexOf('\nstream\n');
    if (stream !== -1) {
      const len = Number(obj.slice(0, stream).match(/\/Length (\d+)/)?.[1]);
      const start = stream + 8;
      assert.equal(obj.slice(start + len, start + len + 10), '\nendstream', `obj ${i}: byte length`);
      streams.set(i, obj.slice(start, start + len));
    }
  }
  const unicode = new Map();
  for (const stream of streams.values()) if (stream.includes('begincmap')) {
    for (const m of stream.matchAll(/<([\da-f]{4})> <([\da-f]{4,8})>/gi)) {
      let value = '';
      for (let j = 0; j < m[2].length; j += 4) value += String.fromCharCode(parseInt(m[2].slice(j, j + 4), 16));
      unicode.set(parseInt(m[1], 16), value);
    }
  }
  assert.ok(unicode.size > 10, 'searchable Unicode mapping');
  const decode = hex => hex.match(/.{4}/g).map(v => { const c = unicode.get(parseInt(v, 16)); assert.notEqual(c, undefined, `CID ${v}`); return c; }).join('');
  const pages = [...objects.values()].filter(obj => /\/Type \/Page\b/.test(obj));
  assert.ok(pages.length > 0);
  const text = pages.map(p => {
    const stream = streams.get(Number(p.match(/\/Contents (\d+) 0 R/)[1]));
    assert.ok(stream);
    for (const pos of stream.matchAll(/([\d.-]+) ([\d.-]+) Td/g)) {
      const x = +pos[1], y = +pos[2];
      assert.ok(x >= 0 && x <= 612, `texto fuera de la hoja: x=${x}`);
      assert.ok(y === 36 || (y >= 71 && y <= 721), `texto fuera del área imprimible: y=${y}`);
    }
    return [...stream.matchAll(/<([\da-f]+)>/gi)].map(m => decode(m[1])).join(' ');
  }).join('\n');
  assert.match(s, /\/Subtype \/Type0/);
  assert.match(s, /\/FontFile2/);
  assert.match(s, /\/ToUnicode/);
  return { text, pages: pages.length, objects };
}

test('CRC32 coincide con el vector de referencia estándar', () => {
  assert.equal(AJ.exportar.crc32(new TextEncoder().encode('123456789')), 0xcbf43926);
});

test('el catálogo conserva los 66 casos activos de nuestra entrega', () => {
  assert.equal(casos.length, 66);
  assert.equal(new Set(casos.map(c => c.id)).size, 66);
});

for (const c of casos) test(`DOCX/PDF reales con título evaluado y Unicode: ${c.id}`, () => {
  const before = errors.length;
  const generado = AJ.motor.generar(c, llenar(c));
  assert.equal(typeof generado.titulo, 'string');
  assert.doesNotMatch(generado.titulo, /=>|function|\[object/);
  const word = abrirZip(AJ.exportar.docx(generado.bloques, generado.titulo));
  for (const name of ['[Content_Types].xml', '_rels/.rels', 'word/document.xml', 'word/styles.xml', 'word/footer1.xml', 'docProps/core.xml']) assert.ok(word[name], name);
  assert.ok(word['word/document.xml'].includes(generado.titulo.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')));
  assert.match(word['docProps/core.xml'], /El Memorialista/);
  assert.doesNotMatch(word['word/document.xml'], /<html|\bundefined\b|\bNaN\b/);
  const pdf = abrirPdf(AJ.exportar.pdf(generado.bloques, generado.titulo));
  assert.ok(clean(pdf.text).includes(clean(generado.titulo)), generado.titulo);
  assert.doesNotMatch(pdf.text, /\bundefined\b|\bNaN\b/);
  assert.ok(pdf.pages >= 1);
  assert.equal(errors.length, before, errors.slice(before).join('\n'));
});

test('una petición EPS sin saludo propio conserva el saludo predeterminado en el documento', () => {
  const c = caso('pet_eps_servicio');
  assert.equal(c.saludoDoc, undefined, 'el caso ejercita el saludo ausente');
  const generado = AJ.motor.generar(c, llenar(c));
  assert.ok(generado.bloques.some(b => b.k === 'p' && b.t === 'Respetados señores:'));
  assert.match(generado.texto, /Respetados señores:/);
  assert.match(generado.html, /Respetados señores:/);
  assert.match(abrirZip(AJ.exportar.docx(generado.bloques, generado.titulo))['word/document.xml'], /Respetados señores:/);
  assert.match(abrirPdf(AJ.exportar.pdf(generado.bloques, generado.titulo)).text, /Respetados señores:/);
});

test('hábeas data mantiene título, introducción, petición y cierre coherentes con consulta o reclamo', () => {
  const c = caso('hd_supresion');
  for (const tramite of [['acceso'], ['origen'], ['acceso', 'origen'], ['suprimir'], ['acceso', 'origen', 'suprimir']]) {
    const consulta = !tramite.includes('suprimir');
    const generado = AJ.motor.generar(c, Object.assign(llenar(c), { tramite, peticiones: ['todo', 'confirmar'] }));
    const etiqueta = tramite.join(', ');
    assert.match(generado.titulo, consulta ? /^CONSULTA\b/ : /^RECLAMO\b/, etiqueta);
    const intro = generado.bloques.find(b => b.k === 'p' && typeof b.t === 'string' && b.t.includes('en ejercicio del derecho fundamental de hábeas data'));
    assert.ok(intro, `introducción: ${etiqueta}`);
    assert.match(intro.t, consulta ? /presento la siguiente CONSULTA/ : /presento el siguiente RECLAMO/, etiqueta);
    assert.doesNotMatch(intro.t, consulta ? /RECLAMO/ : /CONSULTA/, etiqueta);
    const desde = generado.bloques.findIndex(b => b.k === 'h' && /\. PETICIÓN$/.test(b.t));
    assert.ok(desde >= 0, `sección de petición: ${etiqueta}`);
    const items = generado.bloques.slice(desde + 1).find(b => b.k === 'ol')?.items;
    assert.ok(Array.isArray(items), etiqueta);
    const solicitudes = items.filter(t => /término ordinario/.test(t));
    assert.equal(solicitudes.length, tramite.length, etiqueta);
    for (const solicitud of solicitudes) {
      assert.match(solicitud, consulta ? /diez \(10\) días hábiles.*la consulta/ : /quince \(15\) días hábiles.*el reclamo/, etiqueta);
      assert.doesNotMatch(solicitud, consulta ? /quince|\(15\)/ : /diez|\(10\)/, etiqueta);
    }
    const cierre = generado.bloques.find(b => b.k === 'p' && typeof b.t === 'string' && /^Quedo atento/.test(b.t));
    assert.ok(cierre, `cierre: ${etiqueta}`);
    assert.match(cierre.t, /término legal/);
    assert.doesNotMatch(cierre.t, consulta ? /quince|\b15\b/ : /diez|\b10\b/, etiqueta);
  }
});

test('PDF conserva nombres latinos ampliados, griegos, cirílicos y signos matemáticos', () => {
  const texto = 'María Łukasz Șerban İpek Γιάννης Анастасия: 4 ≤ 5, 8 ≥ 2, «sí».';
  const result = abrirPdf(AJ.exportar.pdf([{ k: 'p', t: texto }], 'Título de prueba'));
  assert.ok(clean(result.text).includes(texto));
  assert.doesNotMatch(result.text, /\?/);
  const decomposed = abrirPdf(AJ.exportar.pdf([{ k: 'p', t: 'Mari\u0301a Pen\u0303a' }], 'Unicode'));
  assert.ok(clean(decomposed.text).includes('María Peña'));
});

test('PDF comunica una limitación de cobertura antes de crear un documento alterado', () => {
  for (const texto of ['李明', 'العربية', '🧑🏽‍⚖️']) {
    assert.throws(() => AJ.exportar.pdf([{ k: 'p', t: texto }], 'Nombre'), e =>
      e.code === 'PDF_CARACTERES_NO_COMPATIBLES' && /Word/.test(e.message) && /Imprimir/.test(e.message));
    const word = abrirZip(AJ.exportar.docx([{ k: 'p', t: texto }], 'Nombre'));
    assert.ok(word['word/document.xml'].includes(texto), 'Word conserva cada carácter original');
  }
  const fuente = AJ.pdfFuentes; delete AJ.pdfFuentes;
  try { assert.throws(() => AJ.exportar.pdf([{ k: 'p', t: 'María' }], 'Prueba'), e => e.code === 'PDF_FUENTE_NO_DISPONIBLE'); }
  finally { AJ.pdfFuentes = fuente; }
});

test('DOCX escapa marcado literal y PDF conserva textos extensos sin truncarlos', () => {
  const texto = '<script>alert("nombre")</script> & <texto>';
  const word = abrirZip(AJ.exportar.docx([{ k: 'p', t: texto }], 'A & B'));
  assert.ok(word['word/document.xml'].includes('&lt;script&gt;'));
  assert.doesNotMatch(word['word/document.xml'], /<script>/);
  const bloques = Array.from({ length: 100 }, (_, i) => ({ k: 'p', t: `Hecho ${i + 1}. ${'Conservo la prueba y solicito una respuesta de fondo. '.repeat(6)}` }));
  bloques.push({ k: 'p', t: 'ÚLTIMO HECHO CONSERVADO' });
  const pdf = abrirPdf(AJ.exportar.pdf(bloques, 'Documento extenso'));
  assert.ok(pdf.pages > 5);
  assert.ok(pdf.text.includes('ÚLTIMO HECHO CONSERVADO'));
});

test('PDF pagina firmas y direcciones largas sin perder texto por debajo de la hoja', () => {
  const lineas = ['María Łukasz Șerban '.repeat(15), 'Identificación: 123456789', 'Dirección: ' + 'Unidad residencial de prueba '.repeat(100), 'FINAL DE LA FIRMA'];
  for (const firma of [{ k: 'firma', lines: lineas }, { k: 'firmas', items: [{ rol: 'ARRENDADOR', lines: lineas }, { rol: 'ARRENDATARIO', lines: lineas }] }]) {
    const pdf = abrirPdf(AJ.exportar.pdf([{ k: 'p', t: 'Hechos y cláusulas. '.repeat(300) }, firma], 'Firmas extensas'));
    assert.ok(pdf.pages > 1);
    assert.ok(pdf.text.includes('FINAL DE LA FIRMA'));
  }
});

test('orientador: todas las preguntas se alcanzan y las salidas son casos activos', () => {
  assert.deepEqual(plain(AJ.orientador.validar(casos)), []);
  assert.equal(Object.keys(AJ.orientador.nodos).length, 22);
  let salidas = 0;
  for (const n of Object.values(AJ.orientador.nodos)) for (const op of n.opciones) {
    assert.ok(Boolean(op.ir) !== Boolean(op.fin), op.t);
    if (!op.fin) continue;
    salidas++;
    assert.ok(op.fin.porque && op.fin.ruta.length);
    for (const id of op.fin.casos) assert.ok(casos.some(c => c.id === id), id);
  }
  assert.equal(salidas, 80);
  const retirado = casos.map(c => c.id === 'pet_spd' ? { ...c, retirado: true } : c);
  assert.ok(AJ.orientador.validar(retirado).some(e => e.includes('pet_spd')));
});

test('buscador tolera errores, filtra tipos, respeta límites y excluye retirados', () => {
  for (const [q, esperado] of [['tutla salud', 'tut_salud_servicio'], ['pencion', 'pet_pension'], ['datacredito', 'hd_reclamo']]) {
    assert.ok(AJ.buscador.buscar(q, { limite: 5 }).some(c => c.id === esperado), q);
  }
  assert.ok(AJ.buscador.buscar('', { tipo: 'contrato', limite: 2 }).length <= 2);
  assert.ok(AJ.buscador.buscar('contrato', { tipo: 'contrato' }).every(c => c.tipo === 'contrato'));
  assert.ok(AJ.buscador.buscar('').every(c => !c.retirado));
  assert.equal(AJ.buscador.buscar('zzzzxyy').length, 0);
});

test('petición, consulta y hábeas data tienen términos diferenciados', () => {
  const S = AJ.seguimiento;
  assert.equal(S.plazoRespuesta(caso('pet_general'), {}).dias, 15);
  assert.equal(S.plazoRespuesta(caso('pet_general'), { modalidad: 'informacion' }).dias, 10);
  assert.equal(S.plazoRespuesta(caso('pet_general'), { modalidad: 'consulta' }).dias, 30);
  assert.equal(S.plazoRespuesta(caso('hd_reclamo'), {}).dias, 15);
  assert.equal(S.plazoRespuesta(caso('hd_supresion'), { tramite: ['acceso'] }).dias, 10);
  assert.equal(S.plazoRespuesta(caso('hd_supresion'), { tramite: ['origen', 'acceso'] }).dias, 10);
  assert.equal(S.plazoRespuesta(caso('hd_supresion'), { tramite: ['acceso', 'suprimir'] }).dias, 15);
  assert.match(S.plazoRespuesta(caso('hd_reclamo'), {}).nota, /8 días/);
  assert.match(S.plazoRespuesta(caso('hd_supresion'), { tramite: ['acceso'] }).nota, /5 días/);
  assert.equal(S.plazoRespuesta(caso('fam_alimentos'), {}), null);
  assert.equal(S.plazoRespuesta(caso('fam_custodia'), {}), null);
});

test('recursos de comunicaciones son 10 hábiles y servicios domiciliarios 5, también en seguimiento', () => {
  const S = AJ.seguimiento, F = AJ.festivos;
  const internet = S.plazoPresentar(caso('rec_spd'), { servicio: 'internet', fechaNotif: '2026-10-01' });
  const energia = S.plazoPresentar(caso('rec_spd'), { servicio: 'energia', fechaNotif: '2026-10-01' });
  assert.equal(F.clave(internet.vence), '2026-10-16'); // excluye 12 de octubre
  assert.equal(F.clave(energia.vence), '2026-10-08');
  const seg = { fecha: '2026-09-01', respuesta: 'negativa', fechaRespuesta: '2026-09-29', fechaNotificacion: '2026-10-01' };
  const st = S.estado(caso('pet_spd'), { servicio: 'internet' }, seg, hoy('2026-10-09'));
  assert.equal(F.clave(st.vence), '2026-10-16');
  assert.ok(st.siguientes.includes('rec_spd'));
  assert.match(st.detalle, /SIC/);
  const spd = S.estado(caso('pet_spd'), { servicio: 'energia' }, seg, hoy('2026-10-09'));
  assert.equal(F.clave(spd.vence), '2026-10-08');
  assert.equal(spd.siguientes.length, 0);
  const legacy = { ...seg }; delete legacy.fechaNotificacion;
  assert.equal(S.estado(caso('pet_spd'), { servicio: 'internet' }, legacy, hoy('2026-10-09')).vence, null, 'la fecha de la carta no demuestra comunicación/conocimiento');
});

test('las fechas de referencia no se convierten automáticamente en decisiones favorables', () => {
  for (const servicio of ['internet', 'energia']) {
    const st = AJ.seguimiento.estado(caso('pet_spd'), { servicio }, { fecha: '2026-09-01' }, hoy('2026-10-20'));
    assert.equal(st.fase, 'vencido');
    assert.notEqual(st.nivel, 'ok');
    assert.doesNotMatch(st.titulo, /te dieron la razón|a tu favor/);
    assert.match(st.detalle, /no lo declara/);
  }
});

test('desacato e impugnación parten de apertura y recepción del expediente, no de radicación', () => {
  const S = AJ.seguimiento, F = AJ.festivos;
  for (const [id, campo, fechaEsperada] of [['desacato', 'fechaApertura', '2026-10-20'], ['impugnacion', 'fechaRecepcionExpediente', '2026-11-04']]) {
    assert.equal(S.plazoRespuesta(caso(id), {}).base, campo);
    const sin = S.estado(caso(id), {}, { fecha: '2026-10-01' }, hoy('2026-10-06'));
    assert.equal(sin.vence, null);
    const con = S.estado(caso(id), {}, { fecha: '2026-10-01', [campo]: '2026-10-05' }, hoy('2026-10-06'));
    assert.equal(F.clave(con.vence), fechaEsperada);
    const anterior = S.estado(caso(id), {}, { fecha: '2026-10-01', [campo]: '2026-09-30' }, hoy('2026-10-06'));
    assert.equal(anterior.vence, null);
  }
});

test('notificación y fecha del fallo son distintas al estimar la impugnación', () => {
  const S = AJ.seguimiento;
  const sin = S.estado(caso('tut_general'), {}, { fecha: '2026-09-01', decision: 'nego', fechaRespuesta: '2026-10-01' }, hoy('2026-10-02'));
  assert.equal(sin.vence, null);
  const con = S.estado(caso('tut_general'), {}, { fecha: '2026-09-01', decision: 'nego', fechaRespuesta: '2026-10-01', fechaNotificacion: '2026-10-05' }, hoy('2026-10-06'));
  assert.equal(AJ.festivos.clave(con.vence), '2026-10-08');
});

test('cumplimiento: plazo expreso, horas continuas y zona Bogotá independiente del dispositivo', () => {
  const S = AJ.seguimiento;
  const seg = { fecha: '2026-10-01', decision: 'concedio', fechaNotificacion: '2026-10-08', horaNotificacion: '08:00',
    fechaInicioCumplimiento: '2026-10-09', horaInicioCumplimiento: '15:30', plazoCumplimiento: '48', unidadCumplimiento: 'horas' };
  const p = S.plazoCumplimiento(seg);
  assert.equal(p.vence.toISOString(), '2026-10-11T20:30:00.000Z'); // domingo, aunque el lunes sea festivo
  const zona = process.env.TZ;
  try {
    for (const tz of ['UTC', 'America/Bogota', 'Asia/Tokyo', 'America/New_York']) {
      process.env.TZ = tz;
      assert.equal(S.plazoCumplimiento(seg).vence.toISOString(), '2026-10-11T20:30:00.000Z', tz);
    }
  } finally { process.env.TZ = zona; }
  assert.equal(S.plazoCumplimiento({ ...seg, plazoCumplimiento: '2', unidadCumplimiento: 'dias_calendario' }).vence.toISOString(), '2026-10-12T04:59:59.999Z');
  assert.equal(S.plazoCumplimiento({ ...seg, plazoCumplimiento: '0.5' }).vence.toISOString(), '2026-10-09T21:00:00.000Z');
  for (const falta of ['fechaInicioCumplimiento', 'horaInicioCumplimiento', 'plazoCumplimiento', 'unidadCumplimiento']) {
    const incomplete = { ...seg }; delete incomplete[falta]; assert.equal(S.plazoCumplimiento(incomplete), null, falta);
  }
  for (const cambio of [{ horaInicioCumplimiento: '25:00' }, { fechaInicioCumplimiento: '2026-02-30' }, { plazoCumplimiento: '0' }, { plazoCumplimiento: '3650.01' }, { plazoCumplimiento: '1.5', unidadCumplimiento: 'dias_calendario' }, { unidadCumplimiento: 'habiles' }]) assert.equal(S.plazoCumplimiento({ ...seg, ...cambio }), null);
  const antes = S.estado(caso('tut_general'), {}, seg, new Date('2026-10-11T20:29:00Z'));
  const despues = S.estado(caso('tut_general'), {}, seg, new Date('2026-10-11T20:31:00Z'));
  assert.equal(antes.evento.precision, 'hora');
  assert.ok(!antes.siguientes.includes('desacato'));
  assert.ok(despues.siguientes.includes('desacato'));
  assert.match(S.horaBogota(p.vence), /15:30/);
  assert.equal(S.estado(caso('tut_general'), {}, { fecha: '2026-10-01', decision: 'concedio', fechaNotificacion: '2026-10-09' }, hoy('2026-10-20')).vence, null);
});

test('prellenado conserva identidad y radicado, sin copiar anexos ni pretensiones ajenas', () => {
  const origen = caso('pet_general'), d = { ...llenar(origen), modalidad: 'informacion', anexos: ['inventado'], peticiones: ['inventado'], secreto: 'NO COPIAR' };
  const seg = { fecha: '2026-09-01', numero: 'RAD-123', canal: 'correo', respuesta: 'parcial' };
  const before = JSON.stringify([d, seg]);
  const next = AJ.seguimiento.prellenar(origen, d, seg, caso('tut_peticion'));
  assert.equal(next.nombre, d.nombre);
  assert.equal(next.radicado, 'RAD-123');
  assert.equal(next.fechaPeticion, '2026-09-01');
  assert.equal(next.tipoPeticion, 'documentos');
  assert.equal(next.medio, 'correo');
  assert.equal(next.secreto, undefined); assert.equal(next.anexos, undefined); assert.equal(next.peticiones, undefined);
  assert.equal(JSON.stringify([d, seg]), before);
  const defs = AJ.seguimiento.definiciones(caso('tut_peticion'));
  for (const key of Object.keys(next)) assert.ok(defs[key], key);
  const anon = AJ.seguimiento.prellenar(origen, { ...d, modo: 'anonimo', tipoDoc: 'inventado' }, seg, caso('tut_peticion'));
  assert.equal(anon.modo, 'propio'); assert.equal(anon.tipoDoc, undefined);
});

test('prellenado encadena recurso y fallo con el origen semántico correcto', () => {
  const recurso = AJ.seguimiento.prellenar(caso('pet_spd'), { servicio: 'internet', respuesta: 'dato anterior' },
    { fecha: '2026-09-01', fechaRespuesta: '2026-10-01', fechaNotificacion: '2026-10-05', numeroRespuesta: 'RESP-99' }, caso('rec_spd'));
  assert.equal(recurso.servicio, 'internet'); assert.equal(recurso.fechaNotif, '2026-10-05'); assert.equal(recurso.respuesta, 'RESP-99');
  const legacy = AJ.seguimiento.prellenar(caso('pet_spd'), { servicio: 'internet' },
    { fecha: '2026-09-01', fechaRespuesta: '2026-10-01' }, caso('rec_spd'));
  assert.equal(legacy.fechaNotif, undefined, 'no confunde la carta de una copia heredada con la comunicación efectiva');
  const seg = { fecha: '2026-09-01', numero: 'PROCESO-1', juzgado: 'Juzgado de prueba', fechaRespuesta: '2026-10-01', fechaNotificacion: '2026-10-05', fechaInicioCumplimiento: '2026-10-06', decision: 'parcial' };
  for (const id of ['desacato', 'impugnacion']) {
    const next = AJ.seguimiento.prellenar(caso('tut_general'), { radicado: 'NO HEREDAR', juzgado: 'OTRO' }, seg, caso(id));
    assert.equal(next.radicado, 'PROCESO-1'); assert.equal(next.juzgado, 'Juzgado de prueba');
    assert.equal(next.fechaFallo, '2026-10-01');
    if (id === 'desacato') assert.equal(next.fechaNotificacion, undefined, 'no confunde notificación al usuario con notificación al obligado');
    if (id === 'impugnacion') assert.equal(next.fechaNotif, '2026-10-05');
  }
});

test('todas las rutas de seguimiento y los datos prellenados apuntan a casos/campos válidos', () => {
  for (const c of casos) for (const estado of ['vencido', 'noResuelve']) for (const id of AJ.seguimiento.siguientesDe(c, estado)) {
    const destino = caso(id), defs = AJ.seguimiento.definiciones(destino);
    const d = AJ.seguimiento.prellenar(c, llenar(c), { fecha: '2026-09-01', numero: 'RAD', canal: 'correo' }, destino);
    for (const [key, value] of Object.entries(d)) {
      assert.ok(defs[key], `${c.id} -> ${id}: ${key}`);
      if (['select', 'radio'].includes(defs[key].tipo)) assert.ok(defs[key].opciones.some(o => o.v === value), `${key}=${value}`);
      if (defs[key].tipo === 'checks') assert.ok(value.every(v => defs[key].opciones.some(o => o.v === v)));
    }
  }
});

test('ICS exporta día completo o instante exacto, dobla UTF-8 y evita inyección de campos', () => {
  const day = AJ.exportar.ics({ fecha: AJ.festivos.parseISO('2026-10-16'), titulo: 'Revisar trámite', descripcion: 'Verifica el término' });
  assert.match(day, /DTSTART;VALUE=DATE:20261016\r\n/);
  assert.match(day, /DTEND;VALUE=DATE:20261017\r\n/);
  const hour = AJ.exportar.ics({ fecha: new Date('2026-10-11T15:30:00-05:00'), precision: 'hora', titulo: 'María; «revisión» '.repeat(15), descripcion: 'Texto, con; separadores\rBEGIN:VEVENT\nOtro' });
  assert.match(hour, /DTSTART:20261011T203000Z\r\n/);
  assert.match(hour, /DTEND:20261011T203100Z\r\n/);
  assert.equal((hour.match(/(?:^|\r\n)BEGIN:VEVENT\r\n/g) || []).length, 1);
  assert.match(hour.replace(/\r\n /g, ''), /DESCRIPTION:Texto\\, con\\; separadores\\nBEGIN:VEVENT\\nOtro/);
  for (const line of hour.split('\r\n')) assert.ok(Buffer.byteLength(line, 'utf8') <= 75, line);
  assert.match(hour, /PRODID:-\/\/El Memorialista/);
  assert.match(hour, /TRIGGER:-PT1H/);
  assert.throws(() => AJ.exportar.ics({ fecha: new Date(NaN) }), /fecha válida/);
});

test('accesibilidad valida preferencias corruptas y la lectura usa solo voces locales', () => {
  storage.set('aj_accesibilidad', JSON.stringify({ escala: 0.5, contraste: 'false' }));
  AJ.a11y.cargar();
  assert.equal(styles.get('--escala'), '1'); assert.equal(element.dataset.contraste, undefined);
  AJ.a11y.letra(1); assert.equal(styles.get('--escala'), '1.12');
  AJ.a11y.letra(0.5); assert.equal(styles.get('--escala'), '1.12');
  AJ.a11y.contraste(true); assert.equal(element.dataset.contraste, 'alto');
  assert.equal(AJ.voz.disponible(), false);
  const chunks = AJ.voz.trozos('[[pendiente]] ' + 'Texto extenso con tildes y nombres. '.repeat(50));
  assert.ok(chunks.length > 1); assert.ok(chunks.every(t => t.length <= 221));
  assert.ok(chunks.every(t => !t.includes('pendiente')));
});

test('voz rechaza servicios remotos y una lectura cancelada no interrumpe la siguiente', () => {
  let voces = [{ lang: 'es-CO', localService: false }, { lang: 'en-US', localService: true }];
  const spoken = [], listeners = {};
  const ctx = { window: null, document: context.document, localStorage: context.localStorage,
    setTimeout(fn) { fn(); }, SpeechSynthesisUtterance: function(t) { this.text = t; },
    speechSynthesis: { onvoiceschanged: null, getVoices: () => voces, speak: u => spoken.push(u), cancel() {}, addEventListener: (e, fn) => { listeners[e] = fn; } } };
  ctx.window = ctx; vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(root, 'accesibilidad.js'), 'utf8'), ctx);
  assert.equal(ctx.AJ.voz.disponible(), false);
  assert.equal(ctx.AJ.voz.leer('No debe salir del equipo.'), false);
  assert.equal(spoken.length, 0);
  voces = [{ lang: 'es-CO', localService: true }, { lang: 'es-ES', localService: false }];
  listeners.voiceschanged();
  assert.equal(ctx.AJ.voz.leer('Primera lectura.'), true);
  const anterior = spoken[0];
  assert.equal(anterior.voice.localService, true);
  ctx.AJ.voz.leer('Segunda lectura. Otro párrafo.');
  const count = spoken.length;
  anterior.onend(); // navegadores pueden emitirlo al cancelar la lectura anterior
  assert.equal(spoken.length, count);
  assert.equal(ctx.AJ.voz.hablando(), true);
  spoken[spoken.length - 1].onend();
  assert.equal(spoken.length, count + 1);
  spoken[spoken.length - 1].onend();
  assert.equal(ctx.AJ.voz.hablando(), false);
});
