'use strict';
/** Motor ciudadano real sin navegador, red ni dependencias npm.
 * Ejecutar: node --test tests/test_asesor_engine.cjs
 */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
process.env.TZ = 'UTC';
const root = path.resolve(__dirname, '../app/static/asesor/js');
const errors = [];
const storage = new Map();
const context = {
  console: { log() {}, warn() {}, error(...args) { errors.push(args.map(String).join(' ')); } },
  document: { addEventListener() {} },
  localStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, String(value)), removeItem: key => storage.delete(key) },
  setTimeout, clearTimeout, Date, Map, Set, URL, TextEncoder,
};
context.window = context;
vm.createContext(context);
const scripts = ['festivos.js', 'datos/normas.js', 'datos/entidades.js', 'datos/comunes.js',
  'datos/peticiones.js', 'datos/peticiones2.js', 'datos/peticiones3.js', 'datos/tutelas.js',
  'datos/tutelas2.js', 'datos/otros.js', 'datos/contratos.js', 'datos/mujer.js',
  'datos/sinonimos.js', 'motor.js', 'mejoras.js', 'app.js'];
for (const file of scripts) vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), context, { filename: file });
const AJ = context.AJ;
AJ.casos = AJ.casos.filter(c => !c.retirado);
const casos = AJ.casos;

function populated(caso) {
  const datos = AJ.ui.inicializarDatos(caso);
  for (const field of AJ.ui.camposDelCaso(caso).flatMap(section => section.campos)) {
    if (field.tipo === 'info') continue;
    if (field.tipo === 'checks') datos[field.id] = (field.opciones || []).map(o => o.v);
    else if (['select', 'radio'].includes(field.tipo)) datos[field.id] = datos[field.id] || field.opciones?.[0]?.v || '';
    else if (field.tipo === 'fecha') datos[field.id] = '2026-09-01';
    else if (/correo|email/i.test(field.id)) datos[field.id] = 'persona@example.invalid';
    else if (/monto|precio|salario|canon|valor|cuota|dias|plazo|edad|interes|porcentaje|cantidad|numero|mora|meses/i.test(field.id)) datos[field.id] = '100000';
    else datos[field.id] = datos[field.id] || 'Dato de prueba';
  }
  Object.assign(datos, { nombre: 'María Prueba', numDoc: '123456789', ciudad: 'Bogotá D.C.',
    relato: 'El primero de septiembre presenté una solicitud.\nConservo la constancia de radicación.',
    entidadNombre: 'Entidad de Prueba', direccion: 'Calle de Prueba 1', telefono: '3000000000',
    correo: 'persona@example.invalid', cpNombre: 'Carlos Prueba', cpNumDoc: '987654321',
    cpCiudad: 'Bogotá D.C.', modo: 'propio' });
  return datos;
}

test('conserva 66 casos activos, 169 normas y los 10 tipos de documentos', () => {
  assert.equal(casos.length, 66);
  assert.equal(new Set(casos.map(c => c.id)).size, 66);
  assert.equal(Object.keys(AJ.normas).length, 169);
  assert.equal(new Set(casos.map(c => c.tipo)).size, 10);
  for (const c of casos) assert.ok(AJ.tipos[c.tipo], c.id);
});

for (const caso of casos) test(`motor: ${caso.id} genera vista vacía y documento con datos`, () => {
  const before = errors.length;
  for (const data of [AJ.ui.inicializarDatos(caso), populated(caso)]) {
    const result = AJ.motor.generar(caso, data);
    assert.ok(result.texto.length > 250, caso.id);
    assert.ok(result.html.length > 250, caso.id);
    assert.ok(result.bloques.length > 2, caso.id);
    assert.doesNotMatch(result.texto, /\b(?:undefined|NaN)\b|\[object Object\]/, caso.id);
    assert.doesNotMatch(result.html, /<script\b|<iframe\b|<img\b/i, caso.id);
  }
  assert.equal(errors.length, before, errors.slice(before).join('\n'));
});

test('el documento escapa HTML de nombres, hechos y destinatarios', () => {
  const caso = casos.find(c => c.id === 'pet_eps_servicio');
  const data = populated(caso);
  data.nombre = '<img src=x onerror=alert(1)>';
  data.relato = '<script>alert(1)</script>';
  data.entidadNombre = '<svg onload=alert(1)>';
  const result = AJ.motor.generar(caso, data);
  assert.doesNotMatch(result.html, /<(script|img|svg)\b/i);
  assert.match(result.html, /&lt;script&gt;/);
  assert.match(result.texto, /<script>/); // texto descargable conserva el literal, sin ejecutarlo
});

test('tutela conserva hechos, pretensiones, juramento y agencia oficiosa', () => {
  const caso = casos.find(c => c.id === 'tut_salud_servicio');
  const data = populated(caso);
  Object.assign(data, { modo: 'representante', afectadoNombre: 'Luis Menor', afectadoTipoDoc: 'TI',
    afectadoNumDoc: '12345678', afectadoRazon: 'menor', parentesco: 'hijo' });
  const result = AJ.motor.generar(caso, data);
  for (const text of ['HECHOS', 'PRETENSIONES', 'JURAMENTO', 'LUIS MENOR']) assert.ok(result.texto.includes(text), text);
  assert.match(result.texto, /representante legal/);
});

test('contratos conservan cláusulas y las dos partes', () => {
  const caso = casos.find(c => c.tipo === 'contrato' && !c.unilateral);
  const result = AJ.motor.generar(caso, populated(caso));
  assert.match(result.texto, /CLÁUSULAS/);
  assert.match(result.texto, /MARÍA PRUEBA/);
  assert.match(result.texto, /CARLOS PRUEBA/);
});

test('no afirma anexos que la persona no ha seleccionado', () => {
  for (const id of ['pet_eps_servicio', 'tut_salud_servicio']) {
    const caso = casos.find(c => c.id === id);
    const data = { ...populated(caso), anexos: [], anexosOtros: '' };
    const result = AJ.motor.generar(caso, data);
    assert.match(result.texto, /No se relacionan anexos en este borrador/);
    assert.doesNotMatch(result.texto, /Me permito anexar los siguientes documentos|los siguientes documentos, que se anexan|Copia de mi documento de identidad/);
  }
});

test('anexos seleccionados y otros documentos sí aparecen en el escrito', () => {
  const caso = casos.find(c => c.id === 'pet_eps_servicio');
  const data = { ...populated(caso), anexos: ['orden'], anexosOtros: 'Constancia adicional de radicación' };
  const result = AJ.motor.generar(caso, data);
  assert.match(result.texto, /Copia de la orden o fórmula médica/);
  assert.match(result.texto, /Constancia adicional de radicación/);
  assert.doesNotMatch(result.texto, /Copia de la cédula del paciente|No se relacionan anexos/);
});

test('título dinámico distingue comunicaciones de servicios públicos domiciliarios', () => {
  const caso = casos.find(c => c.id === 'pet_spd');
  const comunicacion = AJ.motor.generar(caso, { ...populated(caso), servicio: 'internet' });
  const domiciliario = AJ.motor.generar(caso, { ...populated(caso), servicio: 'agua' });
  assert.match(comunicacion.texto, /RECLAMACIÓN \(PQR\) – SERVICIOS DE COMUNICACIONES/);
  assert.match(domiciliario.texto, /RECLAMACIÓN \(artículos 152 y 154 de la Ley 142 de 1994\)/);
  for (const result of [comunicacion, domiciliario]) assert.doesNotMatch(result.texto, /d => d\.servicio|tituloDoc/);
});

test('búsqueda natural identifica etapa procesal y excluye casos retirados', () => {
  assert.equal(AJ.mejoras.buscar('no me responden mi petición')[0].id, 'tut_peticion');
  assert.equal(AJ.mejoras.buscar('gané la tutela y no cumplen el fallo')[0].id, 'desacato');
  assert.ok(['pet_eps_servicio', 'tut_salud_servicio'].includes(AJ.mejoras.buscar('la EPS no entrega medicamento')[0].id));
  assert.equal(AJ.mejoras.buscar('zzzzxyy').length, 0);
  assert.ok(AJ.mejoras.buscar('', 'contrato').every(c => c.tipo === 'contrato' && !c.retirado));
});

function record(overrides = {}) {
  return { id: 'doc_test_1', casoId: 'pet_eps_servicio', titulo: 'Prueba',
    fecha: '2026-10-22T15:00:00.000Z', datos: { nombre: 'Prueba', anexos: ['id'] }, ...overrides };
}
test('respaldo admite formato original y versionado conservando datos', () => {
  assert.equal(AJ.mejoras.validarRespaldo([record()])[0].datos.nombre, 'Prueba');
  assert.equal(AJ.mejoras.validarRespaldo({ version: 1, documentos: [record()] }).length, 1);
  assert.equal(AJ.mejoras.datosSeguros({ valor: 10 }).valor, '10');
});
test('importación rechaza inyección de atributos, claves peligrosas y datos malformados', () => {
  const bad = [
    [record({ id: '" onclick="alert(1)' })],
    [record({ casoId: 'caso_inexistente' })],
    [record({ fecha: 'fecha falsa' })],
    [record(), record()],
    [record({ datos: JSON.parse('{"__proto__":{"polluted":true}}') })],
    [record({ datos: { constructor: 'prototype' } })],
    [record({ datos: { nested: { value: 'object' } } })],
    [record({ datos: { valor: Infinity } })],
    [record({ datos: { texto: 'x'.repeat(40001) } })],
    Array.from({ length: 201 }, (_, n) => record({ id: 'doc_' + n })),
    { version: 99, documentos: [] },
  ];
  for (const value of bad) assert.throws(() => AJ.mejoras.validarRespaldo(value));
  assert.equal({}.polluted, undefined);
});

test('guardar historial respeta límite y no transmite datos', () => {
  AJ.mejoras.guardarHistorial([record()]);
  assert.equal(JSON.parse(storage.get('aj_documentos'))[0].id, 'doc_test_1');
  assert.throws(() => AJ.mejoras.guardarHistorial(Array(201).fill(record())));
  assert.equal(typeof context.fetch, 'undefined');
});

test('guardar un borrador agrega y actualiza sin borrar otros documentos', () => {
  storage.delete('aj_documentos');
  AJ.mejoras.guardarBorrador(record());
  AJ.mejoras.guardarBorrador(record({ id: 'doc_test_2', titulo: 'Segundo' }));
  AJ.mejoras.guardarBorrador(record({ titulo: 'Primero actualizado' }));
  const saved = AJ.mejoras.leerHistorial();
  assert.equal(saved.length, 2);
  assert.equal(saved.find(item => item.id === 'doc_test_1').titulo, 'Primero actualizado');
  assert.equal(saved.find(item => item.id === 'doc_test_2').titulo, 'Segundo');
});

test('un historial ilegible o antiguo se conserva byte por byte al intentar guardar', () => {
  const originals = [
    '{json incompleto',
    '',
    JSON.stringify([record({ casoId: 'caso_retirado' })]),
    JSON.stringify([record({ datos: { nested: { value: 'historial heredado' } } })]),
    JSON.stringify(Array.from({ length: 201 }, (_, n) => record({ id: 'doc_' + n }))),
  ];
  for (const original of originals) {
    storage.set('aj_documentos', original);
    assert.throws(() => AJ.mejoras.guardarBorrador(record({ id: 'doc_nuevo' })), /historial existente/);
    assert.equal(storage.get('aj_documentos'), original, 'nunca sustituir el original por una lista nueva');
  }
  storage.delete('aj_documentos');
});

test('la validación de un nuevo borrador no modifica el historial previo', () => {
  const original = JSON.stringify([record()]);
  storage.set('aj_documentos', original);
  assert.throws(() => AJ.mejoras.guardarBorrador(record({ id: 'doc_malo', datos: { constructor: 'x' } })));
  assert.equal(storage.get('aj_documentos'), original);
});

test('un error del navegador al guardar se propaga y conserva la copia anterior', () => {
  const original = JSON.stringify([record()]);
  storage.set('aj_documentos', original);
  const write = context.localStorage.setItem;
  context.localStorage.setItem = () => { throw new Error('QuotaExceededError'); };
  try {
    assert.throws(() => AJ.mejoras.guardarBorrador(record({ id: 'doc_nuevo' })), /QuotaExceededError/);
    assert.equal(storage.get('aj_documentos'), original);
  } finally { context.localStorage.setItem = write; }
});

test('el límite incluye los bytes UTF-8 y el formato de la copia exportada', () => {
  const original = JSON.stringify([record()]);
  storage.set('aj_documentos', original);
  for (const text of ['x'.repeat(39979), '漢'.repeat(14000)]) {
    const datos = Object.fromEntries(Array.from({ length: 125 }, (_, n) => ['campo' + n, text]));
    const large = record({ datos });
    assert.throws(() => AJ.mejoras.guardarHistorial([large]), /5 MB/);
    assert.equal(storage.get('aj_documentos'), original);
  }
});

test('una copia cercana al límite se exporta y se valida sin perder datos', () => {
  const datos = Object.fromEntries(Array.from({ length: 125 }, (_, n) => ['campo' + n, 'x'.repeat(39900)]));
  AJ.mejoras.guardarHistorial([record({ datos })]);
  const exported = AJ.mejoras.serializarRespaldo(AJ.mejoras.leerHistorial());
  assert.ok(new TextEncoder().encode(exported).byteLength <= 5000000);
  const imported = AJ.mejoras.validarRespaldo(JSON.parse(exported));
  assert.equal(imported.length, 1);
  assert.equal(imported[0].datos.campo124, datos.campo124);
  storage.delete('aj_documentos');
});

test('calendario rechaza fechas desbordadas y respeta años bisiestos', () => {
  for (const date of ['2026-02-29', '2026-02-31', '2026-13-01', '2026-00-01', '2026-04-31', '2026-01-00', 'x', null, '1900-02-29']) assert.equal(AJ.festivos.parseISO(date), null, String(date));
  assert.equal(AJ.festivos.clave(AJ.festivos.parseISO('2024-02-29')), '2024-02-29');
  assert.equal(AJ.festivos.clave(AJ.festivos.sumarMeses(AJ.festivos.parseISO('2026-01-31'), 1)), '2026-02-28');
  assert.equal(AJ.festivos.clave(AJ.festivos.sumarDiasHabiles(AJ.festivos.parseISO('2026-10-09'), 1)), '2026-10-13');
});
