/** Client-side contracts using a small DOM/provider double; no browser or external account. */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');
const root = path.resolve(__dirname, '..');
const sessionSource = fs.readFileSync(path.join(root, 'app/static/auth/session.js'), 'utf8');
const loginSource = fs.readFileSync(path.join(root, 'app/static/auth/login.js'), 'utf8');
const privateHtml = fs.readFileSync(path.join(root, 'app/private/generador.html'), 'utf8');
const validConfig = { configurado: true, supabase_url: 'https://project.example.test', supabase_anon_key: 'public-key', allow_signup: false };
const validSession = { access_token: 'unit-test-token', user: { id: 'user-a', email: 'abogada@example.test' } };

class Element {
  constructor(id) { this.id = id; this.value = ''; this.hidden = false; this.disabled = false; this.dataset = {}; this.attrs = {}; this.listeners = {}; this.textContent = ''; this.type = 'text'; this.children = []; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k]; }
  addEventListener(event, fn) { (this.listeners[event] ||= []).push(fn); }
  querySelectorAll() { return this.children; }
  reportValidity() { return true; }
  async fire(event) { for (const fn of this.listeners[event] || []) await fn({ preventDefault() {}, target: this }); }
}

function harness(options = {}) {
  const elements = new Map();
  const get = id => { if (!elements.has(id)) elements.set(id, new Element(id)); return elements.get(id); };
  get('loginForm').hidden = true;
  get('email').value = 'abogada@example.test';
  get('password').type = 'password';
  const modeButtons = ['password', 'magic'].map(mode => Object.assign(new Element(mode), { dataset: { mode } }));
  get('loginForm').children = ['email', 'password', 'name', 'submitButton', 'togglePassword'].map(get);
  let currentUrl = new URL(options.url || 'https://memorialista.test/login');
  const navigation = [], requests = [], authCalls = [], createdClients = [], listeners = [];
  const location = {};
  const setUrl = url => { currentUrl = new URL(url, currentUrl); for (const key of ['origin', 'pathname', 'search', 'hash', 'href']) location[key] = currentUrl[key]; };
  location.replace = value => { navigation.push(value); setUrl(value); };
  location.reload = () => navigation.push('reload');
  setUrl(currentUrl);
  const config = { ...validConfig, ...(options.config || {}) };
  let session = options.session || null;
  const auth = {
    onAuthStateChange(fn) { listeners.push(fn); return { data: { subscription: { unsubscribe() {} } } }; },
    async getSession() { return { data: { session }, error: options.sessionError || null }; },
    async signInWithPassword(data) {
      authCalls.push(['password', data]);
      if (options.passwordError) return { data: { session: null }, error: options.passwordError };
      session = validSession;
      if (options.emitSignedIn) listeners.forEach(fn => fn('SIGNED_IN', session));
      return { data: { session }, error: null };
    },
    async signInWithOtp(data) { authCalls.push(['magic', data]); return { error: null }; },
    async signUp(data) { authCalls.push(['register', data]); return { data: { session: null }, error: null }; },
    async resetPasswordForEmail(...args) { authCalls.push(['recover', ...args]); return { error: null }; },
    async updateUser(data) { authCalls.push(['reset', data]); return { error: null }; },
  };
  const context = {
    URLSearchParams, URL, Promise, Error, Object, String, Boolean, JSON,
    setTimeout, clearTimeout,
    location,
    history: { replaceState(_state, _title, url) { setUrl(url); } },
    document: { getElementById: get, querySelector() { return get('mode-tabs'); }, querySelectorAll() { return modeButtons; } },
    addEventListener() {},
    supabase: { createClient(...args) { createdClients.push(args); return { auth }; } },
    async fetch(url, init = {}) {
      requests.push({ url, init });
      if (url === '/api/auth/config') return { ok: options.configStatus ? options.configStatus < 400 : true, async json() { return config; } };
      if (url === '/api/auth/sesion') {
        const status = init.method === 'DELETE' ? (options.deleteStatus || 200) : (options.bridgeStatus || 200);
        return { ok: status < 400, status, async json() { return status >= 400 ? { detail: 'Sesión rechazada por el servidor.' } : { ok: true, usuario: validSession.user, redirect: '/app' }; } };
      }
      throw new Error('Unexpected endpoint: ' + url);
    },
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(sessionSource, context, { filename: 'session.js' });
  return { context, get, modeButtons, navigation, requests, authCalls, createdClients, config, setUrl,
    startLogin() { vm.runInContext(loginSource, context, { filename: 'login.js' }); } };
}
const settle = async () => { for (let i = 0; i < 5; i++) await new Promise(resolve => setImmediate(resolve)); };

// The browser may present a form, but it never decides whether a token is valid.
test('missing configuration fails closed and can be retried after configuration is restored', async () => {
  const h = harness({ config: { configurado: false } });
  await assert.rejects(h.context.MemAuth.init(), error => error.code === 'not_configured');
  assert.equal(h.createdClients.length, 0);
  assert.deepEqual(h.navigation, []);
  h.config.configurado = true;
  const ready = await h.context.MemAuth.init();
  assert.ok(ready.client.auth);
  assert.equal(h.createdClients.length, 1);
});

test('concurrent initialization produces one provider client', async () => {
  const h = harness();
  const [a, b] = await Promise.all([h.context.MemAuth.init(), h.context.MemAuth.init()]);
  assert.equal(a.client, b.client);
  assert.equal(h.createdClients.length, 1);
  assert.equal(h.requests.filter(r => r.url === '/api/auth/config').length, 1);
});

test('session bridge requires a token and surfaces server rejection', async () => {
  const h = harness({ bridgeStatus: 401 });
  await assert.rejects(h.context.MemAuth.establish(null), /caducado/);
  assert.equal(h.requests.length, 0);
  await assert.rejects(h.context.MemAuth.establish(validSession), error => error.status === 401);
  assert.equal(h.requests[0].init.headers.Authorization, 'Bearer unit-test-token');
  assert.equal(h.requests[0].init.credentials, 'same-origin');
  assert.deepEqual(h.navigation, []);
});

test('failed server logout is reported and not treated as success', async () => {
  const h = harness({ deleteStatus: 503 });
  await assert.rejects(h.context.MemAuth.clearCookie(), /cerrar la sesión/);
  assert.equal(h.requests[0].init.method, 'DELETE');
});

test('post-login destination is restricted to the professional area', () => {
  const h = harness();
  for (const url of ['https://evil.test/', '//evil.test', '/static/index.html', 'javascript:alert(1)', '/app/../../evil', '/']) {
    h.setUrl('/login?next=' + encodeURIComponent(url));
    assert.equal(h.context.MemAuth.destination(), '/app');
  }
  h.setUrl('/login?next=%2Fgenerador');
  assert.equal(h.context.MemAuth.destination(), '/generador');
});

test('unconfigured login never shows an actionable form or invents a session', async () => {
  const h = harness({ config: { configurado: false } });
  h.startLogin(); await settle();
  assert.equal(h.get('loginForm').hidden, true);
  assert.equal(h.get('status').dataset.type, 'error');
  assert.deepEqual(h.authCalls, []);
  assert.deepEqual(h.navigation, []);
});

test('valid provider session still cannot enter when backend bridge rejects it', async () => {
  const h = harness({ session: validSession, bridgeStatus: 401 });
  h.startLogin(); await settle();
  assert.deepEqual(h.navigation, []);
  assert.equal(h.get('status').dataset.type, 'error');
  assert.equal(h.get('submitButton').disabled, false);
});

test('password login navigates only after the backend accepts the session', async () => {
  const h = harness({ emitSignedIn: true });
  h.startLogin(); await settle();
  h.get('password').value = 'test-password-only';
  await h.get('loginForm').fire('submit'); await settle();
  assert.equal(h.authCalls[0][0], 'password');
  assert.ok(h.requests.some(r => r.url === '/api/auth/sesion' && r.init.method === 'POST'));
  assert.deepEqual(h.navigation, ['/app']);
});

test('allowed next destination survives callback URL cleanup', async () => {
  const h = harness({ url: 'https://memorialista.test/login?next=%2Fgenerador' });
  h.startLogin(); await settle();
  h.get('password').value = 'test-password-only';
  await h.get('loginForm').fire('submit'); await settle();
  assert.deepEqual(h.navigation, ['/generador']);
});

test('invalid credentials do not contact the session bridge', async () => {
  const h = harness({ passwordError: { code: 'invalid_credentials', message: 'Provider detail' } });
  h.startLogin(); await settle();
  h.get('password').value = 'wrong-password';
  await h.get('loginForm').fire('submit');
  assert.equal(h.requests.filter(r => r.url === '/api/auth/sesion').length, 0);
  assert.match(h.get('status').textContent, /no coinciden/);
  assert.deepEqual(h.navigation, []);
});

test('magic link with registration disabled never creates an account', async () => {
  const h = harness();
  h.startLogin(); await settle();
  await h.modeButtons.find(b => b.dataset.mode === 'magic').fire('click');
  await h.get('loginForm').fire('submit');
  const call = h.authCalls.find(c => c[0] === 'magic');
  assert.equal(call[1].options.shouldCreateUser, false);
  assert.equal(call[1].options.emailRedirectTo, 'https://memorialista.test/auth/callback');
  assert.equal(h.get('registerButton').hidden, true);
  assert.deepEqual(h.navigation, []);
});

test('recovery link requires a password update before entering the generator', async () => {
  const h = harness({ session: validSession, url: 'https://memorialista.test/auth/callback?mode=recovery#access_token=temporary&type=recovery' });
  h.startLogin(); await settle();
  assert.deepEqual(h.navigation, []);
  assert.equal(h.get('password').minLength, 12);
  assert.equal(h.context.location.hash, '');
  h.get('password').value = 'a-new-password-for-test';
  await h.get('loginForm').fire('submit');
  assert.equal(h.authCalls[0][0], 'reset');
  assert.deepEqual(h.navigation, ['/app']);
});

function storageContext() {
  const values = new Map([['memorialista:perfil', JSON.stringify({ nombre: 'Legacy shared browser data' })]]);
  const start = privateHtml.indexOf("let cuentaLocalId = '';");
  const end = privateHtml.indexOf('const mensajeAlmacen', start);
  assert.ok(start >= 0 && end > start, 'The local persistence boundary is present.');
  const context = { Error, JSON, TextEncoder, Uint8Array, crypto: webcrypto, localStorage: {
    getItem(k) { return values.get(k) ?? null; }, setItem(k, v) { values.set(k, String(v)); }, removeItem(k) { values.delete(k); }
  }};
  vm.createContext(context);
  vm.runInContext(privateHtml.slice(start, end) + '\nglobalThis.storage = { setUser: id => cuentaLocalId = id, read: lsGet, write: lsSet, remove: lsDel, key: claveLocal };', context);
  const cloudStart = privateHtml.indexOf('async function nube(');
  const cloudEnd = privateHtml.indexOf('async function migrarDatosNavegadorASupabase', cloudStart);
  assert.ok(cloudStart >= 0 && cloudEnd > cloudStart);
  vm.runInContext(privateHtml.slice(cloudStart, cloudEnd) + '\nglobalThis.cloud = { check: nube, id: idNube };', context);
  return { context, values };
}

test('local drafts remain isolated across account changes and legacy data is never assigned implicitly', () => {
  const { context: c, values } = storageContext();
  assert.equal(c.storage.write('perfil', { nombre: 'Unauthenticated' }), false);
  assert.throws(() => c.storage.key('perfil'), /validada/);
  c.storage.setUser('account-a');
  assert.equal(c.storage.read('perfil'), null);
  c.storage.write('perfil', { nombre: 'A' });
  c.storage.setUser('account-b');
  assert.equal(c.storage.read('perfil'), null);
  c.storage.write('perfil', { nombre: 'B' });
  c.storage.remove('perfil');
  c.storage.setUser('account-a');
  assert.equal(c.storage.read('perfil').nombre, 'A');
  assert.ok(values.has('memorialista:perfil'));
});

test('cloud identifiers are stable for retries and distinct for users, classes and documents', async () => {
  const { context: c } = storageContext();
  c.storage.setUser('account-a');
  const id = await c.cloud.id('documento', 'draft-one');
  assert.match(id, /^[0-9a-f]{8}-[0-9a-f]{4}-8[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  assert.equal(await c.cloud.id('documento', 'draft-one'), id);
  assert.notEqual(await c.cloud.id('documento', 'draft-two'), id);
  assert.notEqual(await c.cloud.id('caso', 'draft-one'), id);
  c.storage.setUser('account-b');
  assert.notEqual(await c.cloud.id('documento', 'draft-one'), id);
});

test('a resolved cloud operation containing an error is still a failure', async () => {
  const { context: c } = storageContext();
  await assert.rejects(c.cloud.check(Promise.resolve({ data: null, error: { message: 'RLS denied' } })), /RLS denied/);
  assert.equal((await c.cloud.check(Promise.resolve({ data: { id: 'one' }, error: null }))).id, 'one');
});

/** A lazy Supabase/PostgREST-style query double, including immutable versions. */
function cloudDatabase({ failVersionInserts = 0 } = {}) {
  const tables = { casos: new Map(), documentos: new Map(), versiones: new Map() };
  const operations = [];
  const copy = value => value == null ? value : JSON.parse(JSON.stringify(value));
  const jsonbOrder = value => Array.isArray(value) ? value.map(jsonbOrder)
    : value && typeof value === 'object' ? Object.fromEntries(Object.entries(value).reverse().map(([key, item]) => [key, jsonbOrder(item)]))
      : value;
  class Query {
    constructor(table) { this.table = table; this.action = 'select'; this.filters = []; this.bounds = null; this.one = false; this.result = null; }
    select(columns) { this.columns = columns; return this; }
    eq(key, value) { this.filters.push([key, value]); return this; }
    order(key, options) { this.orderBy = [key, options]; return this; }
    range(start, end) { this.bounds = [start, end]; return this; }
    maybeSingle() { this.one = true; return this; }
    single() { this.one = true; return this; }
    upsert(row) { this.action = 'upsert'; this.row = copy(row); return this; }
    insert(row) { this.action = 'insert'; this.row = copy(row); return this; }
    then(resolve, reject) {
      this.result ||= Promise.resolve().then(() => this.execute());
      return this.result.then(resolve, reject);
    }
    execute() {
      operations.push({ table: this.table, action: this.action, row: copy(this.row), filters: [...this.filters] });
      const table = tables[this.table];
      assert.ok(table, 'Unexpected cloud table: ' + this.table);
      if (this.action === 'select') {
        let rows = [...table.values()].filter(row => this.filters.every(([key, value]) => row[key] === value));
        if (this.orderBy) {
          const [key, options] = this.orderBy;
          rows.sort((a, b) => String(a[key]).localeCompare(String(b[key])) * (options.ascending === false ? -1 : 1));
        }
        if (this.bounds) rows = rows.slice(this.bounds[0], this.bounds[1] + 1);
        return { data: copy(this.one ? rows[0] || null : rows), error: null };
      }
      if (this.table === 'versiones' && this.action === 'upsert') {
        return { data: null, error: { code: '42501', message: 'Versions are immutable; UPDATE is not permitted.' } };
      }
      if (this.table === 'versiones' && failVersionInserts > 0) {
        failVersionInserts--;
        return { data: null, error: { code: '08006', message: 'Temporary failure inserting the version.' } };
      }
      if (this.action === 'insert' && table.has(this.row.id)) {
        return { data: null, error: { code: '23505', message: 'Duplicate primary key.' } };
      }
      // PostgreSQL JSONB does not preserve the JavaScript property insertion order.
      table.set(this.row.id, jsonbOrder(this.row));
      return { data: null, error: null };
    }
  }
  return { client: { from(table) { return new Query(table); } }, tables, operations };
}

function syncContext(options = {}) {
  const { context } = storageContext();
  const database = cloudDatabase(options);
  const local = new Map();
  const localWrites = [];
  const notices = [];
  const navigation = [];
  const recoveryButton = { disabled: false };
  context.storage.setUser('account-a');
  Object.assign(context, {
    sbClient: database.client,
    state: { usuario: { id: 'account-a' } },
    cerrandoSesion: false,
    clon: value => JSON.parse(JSON.stringify(value)),
    $: () => recoveryButton,
    IDB: { async get(store, key) { assert.equal(store, 'historial'); return local.get(key) || null; } },
    Almacen: { async guardarHist(id, data) { const row = JSON.parse(JSON.stringify({ id, ...data })); local.set(id, row); localWrites.push(row); } },
    toast: (...args) => notices.push(args),
    cerrarModalCuenta() {},
    irVista: value => navigation.push(value),
  });
  const start = privateHtml.indexOf('const colasSincronizacion = new Map();');
  const end = privateHtml.indexOf('async function exportarTodosMisDatos()', start);
  assert.ok(start >= 0 && end > start, 'Cloud sync/recovery functions are present.');
  vm.runInContext(privateHtml.slice(start, end) + '\nglobalThis.syncTest = { upload: sincronizarDocumentoConSupabase, recover: recuperarDocumentosNube };', context);
  return { context, database, local, localWrites, notices, navigation, recoveryButton };
}

const sampleDraft = () => ({
  titulo: 'Petición de prueba', tipo: 'peticion', texto: 'Contenido de prueba sin datos reales.', versiones: [],
  datos: { cliente: { nombre: 'Persona de prueba', ubicacion: { municipio: 'Pasto', zona: 'urbana' } }, hechos: ['Hecho uno', 'Hecho dos'], radicado: '' },
});

test('repeating a cloud backup creates no new version when JSONB only reorders keys', async () => {
  const h = syncContext();
  const draft = sampleDraft();
  await h.context.syncTest.upload('draft-one', draft);
  const reordered = sampleDraft();
  reordered.datos = { radicado: '', hechos: ['Hecho uno', 'Hecho dos'], cliente: { ubicacion: { zona: 'urbana', municipio: 'Pasto' }, nombre: 'Persona de prueba' } };
  await h.context.syncTest.upload('draft-one', reordered);
  assert.equal(h.database.tables.documentos.size, 1);
  assert.equal(h.database.tables.versiones.size, 1);
  assert.equal([...h.database.tables.documentos.values()][0].version, 1);
  assert.equal(h.database.operations.filter(op => op.table === 'documentos' && op.action === 'upsert').length, 1);
  assert.equal(h.database.operations.filter(op => op.table === 'versiones' && op.action === 'insert').length, 1);
});

test('retry repairs a missing immutable version after the document was already saved', async () => {
  const h = syncContext({ failVersionInserts: 1 });
  const draft = sampleDraft();
  await assert.rejects(h.context.syncTest.upload('draft-one', draft), /Temporary failure/);
  assert.equal(h.database.tables.documentos.size, 1);
  assert.equal(h.database.tables.versiones.size, 0);
  await h.context.syncTest.upload('draft-one', draft);
  assert.equal(h.database.tables.versiones.size, 1);
  const document = [...h.database.tables.documentos.values()][0];
  const version = [...h.database.tables.versiones.values()][0];
  assert.equal(document.version, 1);
  assert.equal(version.version, 1);
  assert.equal(version.documento_id, document.id);
  assert.equal(version.texto, draft.texto);
  assert.equal(h.database.operations.filter(op => op.table === 'documentos' && op.action === 'upsert').length, 1);
  assert.equal(h.database.operations.filter(op => op.table === 'versiones' && op.action === 'insert').length, 2);
  assert.equal(h.database.operations.filter(op => op.table === 'versiones' && op.action === 'upsert').length, 0);
});

test('cloud recovery preserves a differing local draft and adds one separate reusable copy', async () => {
  const h = syncContext();
  const localDraft = { id: 'draft-one', titulo: 'Mi trabajo local', texto: 'Texto local aún sin respaldar.', datos: { hechos: 'Hechos locales.' }, tipo: 'peticion' };
  h.local.set(localDraft.id, JSON.parse(JSON.stringify(localDraft)));
  h.database.tables.documentos.set('remote-a', {
    id: 'remote-a', creado_por: 'account-a', titulo: 'Versión remota', tipo: 'peticion', version: 3,
    texto: 'Texto remoto diferente.', datos: { hechos: 'Hechos remotos.', __memorialista: { id_local: 'draft-one', versiones: [{ texto: 'Primera versión remota.' }] } },
    created_at: '2026-10-20T12:00:00Z', updated_at: '2026-10-22T12:00:00Z',
  });
  h.database.tables.documentos.set('remote-b', {
    id: 'remote-b', creado_por: 'account-b', titulo: 'Documento de otro usuario', texto: 'No recuperar.', datos: {}, version: 1,
    created_at: '2026-10-20T12:00:00Z', updated_at: '2026-10-22T12:00:00Z',
  });
  await h.context.syncTest.recover();
  assert.deepEqual(h.local.get('draft-one'), localDraft);
  assert.equal(h.local.size, 2);
  assert.equal(h.localWrites.length, 1);
  const copy = h.localWrites[0];
  assert.notEqual(copy.id, 'draft-one');
  assert.match(copy.titulo, /copia de la nube/);
  assert.equal(copy.texto, 'Texto remoto diferente.');
  assert.equal(copy.datos.hechos, 'Hechos remotos.');
  assert.equal(copy.datos.__memorialista, undefined);
  assert.equal(copy.versiones.length, 1);
  assert.equal(h.recoveryButton.disabled, false);
  assert.deepEqual(h.navigation, ['historial']);
  // Repeating recovery does not duplicate the separate cloud copy.
  await h.context.syncTest.recover();
  assert.equal(h.local.size, 2);
  assert.equal(h.localWrites.length, 1);
  assert.deepEqual(h.local.get('draft-one'), localDraft);
  assert.equal(h.notices.at(-1)[1], 'ok');
});
