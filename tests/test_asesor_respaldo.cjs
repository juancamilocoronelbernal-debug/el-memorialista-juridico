'use strict';
/** Respaldos ciudadanos: compatibilidad, integridad y conservación de cadenas.
 * node --test tests/test_asesor_respaldo.cjs
 * Scripts reales; almacenamiento simulado, sin DOM de navegador, PDF ni red.
 */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
process.env.TZ = 'UTC';

const sourceDir = path.resolve(__dirname, '../app/static/asesor/js');
const scripts = [
  'festivos.js', 'datos/normas.js', 'datos/entidades.js', 'datos/comunes.js',
  'datos/peticiones.js', 'datos/peticiones2.js', 'datos/peticiones3.js',
  'datos/tutelas.js', 'datos/tutelas2.js', 'datos/otros.js', 'datos/contratos.js',
  'datos/mujer.js', 'datos/sinonimos.js', 'motor.js', 'seguimiento.js', 'mejoras.js', 'app.js',
].map(name => [name, fs.readFileSync(path.join(sourceDir, name), 'utf8')]);

const plain = value => JSON.parse(JSON.stringify(value));

function abrir() {
  const storage = new Map();
  const writes = [];
  const aviso = { textContent: '', className: '' };
  const context = {
    console: { log() {}, warn() {}, error() {} },
    document: {
      addEventListener() {},
      querySelector: selector => selector === '#aviso' ? aviso : null,
      querySelectorAll: () => [],
      getElementById: id => id === 'aviso' ? aviso : null,
    },
    localStorage: {
      getItem: key => storage.get(key) ?? null,
      setItem(key, value) { writes.push([key, String(value)]); storage.set(key, String(value)); },
      removeItem: key => storage.delete(key),
    },
    setTimeout: () => 1, clearTimeout() {}, Date, Map, Set, URL, TextEncoder,
  };
  context.window = context;
  vm.createContext(context);
  for (const [name, source] of scripts) vm.runInContext(source, context, { filename: name });
  context.AJ.casos = context.AJ.casos.filter(caso => !caso.retirado);
  return { AJ: context.AJ, context, storage, writes, aviso };
}

function seguimiento(overrides = {}) {
  return {
    fecha: '2026-10-01', numero: 'RAD-01', canal: 'tutela_linea', juzgado: 'Juzgado de prueba',
    decision: 'concedio', fechaRespuesta: '2026-10-08', fechaNotificacion: '2026-10-09',
    fechaApertura: '2026-10-10', fechaRecepcionExpediente: '2026-10-11',
    fechaInicioCumplimiento: '2026-10-08', horaInicioCumplimiento: '16:30',
    horaNotificacion: '14:05', plazoCumplimiento: '48', unidadCumplimiento: 'horas',
    cumple: 'no', respuesta: 'parcial', numeroRespuesta: 'RESP-1', nota: 'Conservo la constancia.',
    actualizado: '2026-10-12T15:00:00.000Z', ...overrides,
  };
}

function origen(overrides = {}) {
  return { id: 'peticion_previa', casoId: 'pet_eps_servicio', titulo: 'Petición anterior', fecha: '2026-09-28', ...overrides };
}

function documento(overrides = {}) {
  return {
    id: 'doc_tutela', casoId: 'tut_salud_servicio', titulo: 'Tutela de prueba',
    fecha: '2026-10-12T16:00:00.000Z', datos: { nombre: 'María Prueba', relato: 'Hechos de prueba.', anexos: ['id', 'orden'] },
    ...overrides,
  };
}

test('v2 conserva seguimiento completo y documento de origen al exportar, importar y guardar', () => {
  const { AJ, storage } = abrir();
  const source = documento({ seguimiento: seguimiento(), origen: origen() });
  AJ.mejoras.guardarHistorial([source]);
  const backup = JSON.parse(AJ.mejoras.serializarRespaldo(AJ.mejoras.leerHistorial()));
  assert.equal(backup.version, 2);
  assert.match(backup.aplicacion, /El Memorialista/);
  assert.equal(backup.documentos.length, 1);
  assert.deepEqual(backup.documentos[0], source);
  storage.clear();
  AJ.mejoras.guardarHistorial(AJ.mejoras.validarRespaldo(backup));
  assert.deepEqual(plain(AJ.mejoras.leerHistorial()), [source]);
});

test('acepta v1, v2 y el arreglo heredado de Claude sin perder metadatos', () => {
  const { AJ } = abrir();
  const records = [documento({ seguimiento: seguimiento({ respuesta: 'tramite' }), origen: origen() })];
  const before = JSON.stringify(records);
  for (const envelope of [records, { version: 1, documentos: records }, { version: 2, documentos: records }]) {
    assert.deepEqual(plain(AJ.mejoras.validarRespaldo(envelope)), records);
  }
  assert.equal(JSON.stringify(records), before);
});

test('una copia antigua conserva la notificación sin inventar el inicio del cumplimiento', () => {
  const { AJ } = abrir();
  const anterior = seguimiento();
  delete anterior.fechaInicioCumplimiento;
  delete anterior.horaInicioCumplimiento;
  const records = [documento({ seguimiento: anterior })];
  for (const envelope of [records, { version: 1, documentos: records }, { version: 2, documentos: records }]) {
    const imported = AJ.mejoras.validarRespaldo(envelope)[0];
    assert.deepEqual(plain(imported.seguimiento), anterior);
    assert.equal(imported.seguimiento.fechaNotificacion, '2026-10-09');
    assert.equal(imported.seguimiento.horaNotificacion, '14:05');
    assert.equal(imported.seguimiento.fechaInicioCumplimiento, undefined);
    assert.equal(imported.seguimiento.horaInicioCumplimiento, undefined);
    assert.equal(AJ.seguimiento.plazoCumplimiento(imported.seguimiento), null);
  }
});

test('los campos nuevos de apertura y recepción existen en la copia y en su formulario', () => {
  const { AJ } = abrir();
  const normalized = AJ.mejoras.seguimientoSeguro(seguimiento());
  assert.equal(normalized.fechaApertura, '2026-10-10');
  assert.equal(normalized.fechaRecepcionExpediente, '2026-10-11');
  assert.equal(normalized.fechaInicioCumplimiento, '2026-10-08');
  assert.equal(normalized.horaInicioCumplimiento, '16:30');
  const desacato = AJ.casos.find(caso => caso.id === 'desacato');
  const impugnacion = AJ.casos.find(caso => caso.id === 'impugnacion');
  assert.match(AJ.ui.formularioSeguimiento(desacato, normalized, 'doc_1'), /name="fechaApertura"[^>]*value="2026-10-10"/);
  assert.match(AJ.ui.formularioSeguimiento(impugnacion, normalized, 'doc_2'), /name="fechaRecepcionExpediente"[^>]*value="2026-10-11"/);
  const tutela = AJ.casos.find(caso => caso.id === 'tut_salud_servicio');
  const html = AJ.ui.formularioSeguimiento(tutela, normalized, 'doc_3');
  assert.match(html, /name="fechaNotificacion"[^>]*value="2026-10-09"/);
  assert.match(html, /name="fechaInicioCumplimiento"[^>]*value="2026-10-08"/);
  assert.match(html, /name="horaInicioCumplimiento"[^>]*value="16:30"/);
});

test('todas las fechas de seguimiento rechazan desbordes y relaciones temporales imposibles', () => {
  const { AJ } = abrir();
  for (const field of ['fecha', 'fechaRespuesta', 'fechaNotificacion', 'fechaInicioCumplimiento', 'fechaApertura', 'fechaRecepcionExpediente']) {
    assert.throws(() => AJ.mejoras.seguimientoSeguro(seguimiento({ [field]: '2026-02-30' })), /fecha/i);
    assert.throws(() => AJ.mejoras.seguimientoSeguro(seguimiento({ [field]: 'not-a-date' })), /fecha/i);
  }
  for (const field of ['fechaRespuesta', 'fechaNotificacion', 'fechaInicioCumplimiento', 'fechaApertura', 'fechaRecepcionExpediente']) {
    assert.throws(() => AJ.mejoras.seguimientoSeguro(seguimiento({ [field]: '2026-09-30' })), /anterior/i);
  }
  assert.throws(() => AJ.mejoras.seguimientoSeguro(seguimiento({ fechaNotificacion: '2026-10-07' })), /anterior/i);
  assert.throws(() => AJ.mejoras.seguimientoSeguro(seguimiento({ fechaInicioCumplimiento: '2026-10-07' })), /anterior/i);
  assert.throws(() => AJ.mejoras.seguimientoSeguro(seguimiento({ horaNotificacion: '24:59' })), /hora/i);
  assert.throws(() => AJ.mejoras.seguimientoSeguro(seguimiento({ horaInicioCumplimiento: '24:59' })), /hora/i);
  assert.throws(() => AJ.mejoras.seguimientoSeguro(seguimiento({ plazoCumplimiento: '1.5', unidadCumplimiento: 'dias_calendario' })), /entero/i);
});

test('formatos futuros, campos desconocidos y valores inválidos no se importan parcialmente', () => {
  const { AJ, storage, writes } = abrir();
  const previous = JSON.stringify([documento({ id: 'doc_anterior' })]);
  storage.set('aj_documentos', previous);
  const malformed = [
    { version: 99, documentos: [documento()] },
    [documento({ campoFuturo: 'No ignorar' })],
    [documento({ seguimiento: { fecha: '2026-10-01', nuevoTermino: 'No ignorar' } })],
    [documento({ origen: origen({ documentoCompleto: 'No ignorar' }) })],
    [documento({ seguimiento: seguimiento({ plazoCumplimiento: '-1' }) })],
    [documento({ seguimiento: seguimiento({ unidadCumplimiento: 'dias_habiles' }) })],
    [documento({ seguimiento: seguimiento({ nota: { contenido: 'objeto' } }) })],
    [documento({ origen: origen({ casoId: 'caso_que_no_existe' }) })],
    [documento({ origen: origen({ fecha: '2026-02-30' }) })],
    [documento({ datos: JSON.parse('{"__proto__":{"polluted":true}}') })],
    [documento({ seguimiento: JSON.parse('{"constructor":"malicioso"}') })],
  ];
  for (const envelope of malformed) {
    assert.throws(() => {
      const incoming = AJ.mejoras.validarRespaldo(envelope);
      const merged = AJ.mejoras.fusionarRespaldo(AJ.mejoras.leerHistorial(), incoming);
      AJ.mejoras.guardarHistorial(merged.documentos);
    });
    assert.equal(storage.get('aj_documentos'), previous);
  }
  assert.equal(writes.length, 0);
  assert.equal({}.polluted, undefined);
});

test('un historial corrupto o con metadatos desconocidos permanece byte por byte intacto', () => {
  const { AJ, storage, writes } = abrir();
  for (const original of ['{historial incompleto', '', JSON.stringify([documento({ seguimiento: { futuro: 'conservar' } })])]) {
    storage.set('aj_documentos', original);
    assert.throws(() => AJ.mejoras.guardarBorrador(documento({ id: 'otro' })), /historial existente/i);
    assert.throws(() => AJ.mejoras.fusionarRespaldo(AJ.mejoras.leerHistorial(), [documento()]), /historial existente/i);
    assert.equal(storage.get('aj_documentos'), original);
  }
  assert.equal(writes.length, 0);
});

test('la denegación de lectura no se interpreta como historial vacío', () => {
  const { AJ, context, storage, writes } = abrir();
  const original = JSON.stringify([documento()]);
  storage.set('aj_documentos', original);
  context.localStorage.getItem = () => { throw new Error('SecurityError'); };
  assert.throws(() => AJ.mejoras.guardarBorrador(documento({ id: 'otro' })), /leer el historial/i);
  assert.equal(storage.get('aj_documentos'), original);
  assert.equal(writes.length, 0);
});

test('al editar un borrador se conservan seguimiento y origen anteriores', () => {
  const { AJ, storage } = abrir();
  const previous = documento({ seguimiento: seguimiento(), origen: origen() });
  storage.set('aj_documentos', JSON.stringify([previous]));
  Object.assign(AJ.ui.estado, {
    caso: AJ.casos.find(caso => caso.id === previous.casoId),
    datos: { ...previous.datos, relato: 'Hechos corregidos por la persona.' },
    idGuardado: previous.id, origen: null,
  });
  assert.ok(AJ.ui.guardarActual());
  const saved = plain(AJ.mejoras.leerHistorial())[0];
  assert.equal(saved.datos.relato, 'Hechos corregidos por la persona.');
  assert.deepEqual(saved.seguimiento, previous.seguimiento);
  assert.deepEqual(saved.origen, previous.origen);
});

test('si se agota la cuota la UI devuelve fallo, mantiene el original y no asigna un ID ficticio', () => {
  const { AJ, context, storage, aviso } = abrir();
  const previous = JSON.stringify([documento()]);
  storage.set('aj_documentos', previous);
  Object.assign(AJ.ui.estado, {
    caso: AJ.casos.find(caso => caso.id === 'pet_eps_servicio'),
    datos: { nombre: 'Otra persona' }, idGuardado: null,
  });
  context.localStorage.setItem = () => { const error = new Error('No queda espacio para guardar.'); error.name = 'QuotaExceededError'; throw error; };
  assert.equal(AJ.ui.guardarActual(), null);
  assert.equal(AJ.ui.estado.idGuardado, null);
  assert.equal(storage.get('aj_documentos'), previous);
  assert.match(aviso.className, /error/);
  assert.match(aviso.textContent, /No queda espacio/);
  assert.doesNotMatch(aviso.className, /\bok\b/);
});

test('fusionar es puro y conservar un conflicto no sustituye el seguimiento local', () => {
  const { AJ, writes } = abrir();
  const local = [documento({ seguimiento: seguimiento(), origen: origen() })];
  const incoming = [documento({ datos: { nombre: 'Contenido importado' } })];
  const before = JSON.stringify({ local, incoming });
  const result = AJ.mejoras.fusionarRespaldo(local, incoming);
  assert.equal(JSON.stringify({ local, incoming }), before);
  assert.equal(writes.length, 0);
  assert.equal(result.importados, 1);
  assert.equal(result.conflictos, 1);
  assert.equal(result.duplicados, 0);
  assert.equal(result.documentos.length, 2);
  assert.deepEqual(plain(result.documentos.find(doc => doc.id === local[0].id)), local[0]);
  const imported = result.documentos.find(doc => doc.id !== local[0].id);
  assert.equal(imported.datos.nombre, 'Contenido importado');
  assert.match(imported.id, /^[a-zA-Z0-9_-]{1,100}$/);
});

test('las copias idénticas se omiten aunque metadatos opcionales sean null', () => {
  const { AJ } = abrir();
  const local = [documento()];
  const result = AJ.mejoras.fusionarRespaldo(local, [documento({ seguimiento: null, origen: null })]);
  assert.equal(result.documentos.length, 1);
  assert.equal(result.duplicados, 1);
  assert.equal(result.importados, 0);
});

test('el orden de claves JSON no convierte contenido equivalente en un conflicto', () => {
  const { AJ } = abrir();
  const a = documento({ datos: { nombre: 'Ana', relato: 'El mismo relato' }, seguimiento: { fecha: '2026-10-01', numero: '1' } });
  const b = documento({ datos: { relato: 'El mismo relato', nombre: 'Ana' }, seguimiento: { numero: '1', fecha: '2026-10-01' } });
  const result = AJ.mejoras.fusionarRespaldo([a], [b]);
  assert.equal(result.documentos.length, 1);
  assert.equal(result.duplicados, 1);
  assert.equal(result.conflictos, 0);
});

function cadena() {
  const parent = documento({ id: 'padre', casoId: 'pet_eps_servicio', titulo: 'Petición padre' });
  const child = documento({ id: 'hijo', titulo: 'Tutela hija', origen: origen({ id: parent.id, titulo: parent.titulo }) });
  const grandchild = documento({ id: 'nieto', casoId: 'desacato', titulo: 'Incidente nieto', origen: origen({ id: child.id, casoId: child.casoId, titulo: child.titulo }) });
  return { parent, child, grandchild };
}

test('al renombrar un padre importado se ajusta el origen del hijo aunque llegue antes', () => {
  const { AJ } = abrir();
  const { parent, child } = cadena();
  const changed = { ...parent, datos: { nombre: 'Versión importada' } };
  const result = AJ.mejoras.fusionarRespaldo([parent], [child, changed]);
  const importedParent = result.documentos.find(doc => doc.id !== parent.id && doc.casoId === parent.casoId);
  const importedChild = result.documentos.find(doc => doc.id === child.id);
  assert.ok(importedParent && importedChild);
  assert.equal(importedChild.origen.id, importedParent.id);
  assert.equal(result.documentos.find(doc => doc.id === parent.id).datos.nombre, parent.datos.nombre);
});

test('el cambio de un ancestro conserva también hijos y nietos antes idénticos, con la cadena correcta', () => {
  const { AJ } = abrir();
  const { parent, child, grandchild } = cadena();
  const local = [parent, child, grandchild];
  const incoming = [grandchild, child, { ...parent, datos: { nombre: 'Padre importado distinto' } }];
  const result = AJ.mejoras.fusionarRespaldo(local, incoming);
  assert.equal(result.documentos.length, 6);
  assert.equal(result.importados, 3);
  assert.equal(result.conflictos, 3);
  assert.equal(result.duplicados, 0);
  for (const previous of local) assert.deepEqual(plain(result.documentos.find(doc => doc.id === previous.id)), previous);
  const newParent = result.documentos.find(doc => doc.id !== parent.id && doc.casoId === parent.casoId);
  const newChild = result.documentos.find(doc => doc.id !== child.id && doc.casoId === child.casoId);
  const newGrandchild = result.documentos.find(doc => doc.id !== grandchild.id && doc.casoId === grandchild.casoId);
  assert.equal(newChild.origen.id, newParent.id);
  assert.equal(newGrandchild.origen.id, newChild.id);
});

test('un origen que no se incluye en la importación mantiene su enlace local', () => {
  const { AJ } = abrir();
  const { parent, child } = cadena();
  const result = AJ.mejoras.fusionarRespaldo([parent], [child]);
  assert.equal(result.documentos.find(doc => doc.id === child.id).origen.id, parent.id);
  assert.equal(result.conflictos, 0);
});

test('los IDs generados no pisan documentos existentes ni IDs reservados por la entrada', () => {
  const { AJ } = abrir();
  const local = [documento({ id: 'doc', datos: { nombre: 'Local' } }), documento({ id: 'doc_importado_1' })];
  const incoming = [documento({ id: 'doc', datos: { nombre: 'Importado' } }), documento({ id: 'doc_importado_2' })];
  const result = AJ.mejoras.fusionarRespaldo(local, incoming);
  assert.equal(result.documentos.length, 4);
  assert.equal(new Set(result.documentos.map(doc => doc.id)).size, 4);
  for (const doc of result.documentos) assert.match(doc.id, /^[a-zA-Z0-9_-]{1,100}$/);
  assert.equal(result.documentos.find(doc => doc.id === 'doc').datos.nombre, 'Local');
  assert.ok(result.documentos.some(doc => doc.id !== 'doc' && doc.datos.nombre === 'Importado'));
});

test('si conservar ambos supera 200 documentos, no cambia nada en el almacenamiento', () => {
  const { AJ, storage, writes } = abrir();
  const local = Array.from({ length: 200 }, (_, i) => documento({ id: `doc_${i}` }));
  const original = JSON.stringify(local);
  storage.set('aj_documentos', original);
  assert.throws(() => {
    const merged = AJ.mejoras.fusionarRespaldo(AJ.mejoras.leerHistorial(), [documento({ id: 'doc_0', datos: { nombre: 'Otro contenido' } })]);
    AJ.mejoras.guardarHistorial(merged.documentos);
  }, /200/);
  assert.equal(storage.get('aj_documentos'), original);
  assert.equal(writes.length, 0);
});

test('una importación válida escribe una sola vez y un error de cuota conserva el estado previo', () => {
  const { AJ, context, storage, writes } = abrir();
  const original = JSON.stringify([documento({ id: 'anterior', seguimiento: seguimiento() })]);
  storage.set('aj_documentos', original);
  const result = AJ.mejoras.fusionarRespaldo(AJ.mejoras.leerHistorial(), [documento({ id: 'nuevo', origen: origen() })]);
  AJ.mejoras.guardarHistorial(result.documentos);
  assert.equal(writes.length, 1);
  assert.equal(AJ.mejoras.leerHistorial().length, 2);
  const saved = storage.get('aj_documentos');
  context.localStorage.setItem = () => { throw new Error('QuotaExceededError'); };
  const next = AJ.mejoras.fusionarRespaldo(AJ.mejoras.leerHistorial(), [documento({ id: 'tercero' })]);
  assert.throws(() => AJ.mejoras.guardarHistorial(next.documentos), /QuotaExceededError/);
  assert.equal(storage.get('aj_documentos'), saved);
});

function nombresAtributos(html) {
  const names = [];
  for (const tag of html.matchAll(/<[a-z][a-z0-9-]*\b((?:[^"'<>]|"[^"]*"|'[^']*')*)>/gi)) {
    for (const attr of tag[1].matchAll(/([^\s"'=<>`]+)(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?/g)) names.push(attr[1].toLowerCase());
  }
  return names;
}

test('IDs hostiles se rechazan y los valores de seguimiento no crean etiquetas ni atributos ejecutables', () => {
  const { AJ } = abrir();
  const payload = '\"><img src=x onerror="alert(1)"><script>alert(2)</script>';
  assert.throws(() => AJ.mejoras.validarRespaldo([documento({ id: payload })]));
  assert.throws(() => AJ.mejoras.validarRespaldo([documento({ origen: origen({ id: payload }) })]));
  const caso = AJ.casos.find(c => c.id === 'tut_salud_servicio');
  const html = AJ.ui.formularioSeguimiento(caso, {
    numero: payload, juzgado: payload, nota: '</textarea><script>alert(3)</script>', horaNotificacion: payload,
  }, payload);
  assert.doesNotMatch(html, /<(?:img|script)\b/i);
  assert.match(html, /&lt;script&gt;/);
  assert.ok(nombresAtributos(html).every(name => !name.startsWith('on')));
  assert.equal((html.match(/<textarea\b/g) || []).length, 1);
});

test('las copias y su validación funcionan sin exportador PDF, fuentes ni acceso a red', () => {
  const { AJ, context } = abrir();
  assert.equal(AJ.exportar, undefined);
  assert.equal(context.fetch, undefined);
  assert.equal(context.XMLHttpRequest, undefined);
  const imported = AJ.mejoras.validarRespaldo(JSON.parse(AJ.mejoras.serializarRespaldo([documento({ origen: origen(), seguimiento: seguimiento() })])));
  assert.equal(imported.length, 1);
  assert.equal(imported[0].seguimiento.fechaApertura, '2026-10-10');
});
