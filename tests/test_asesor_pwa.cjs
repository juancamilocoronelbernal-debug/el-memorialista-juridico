'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { webcrypto, createHash } = require('node:crypto');

const root = path.resolve(__dirname, '..');
const origin = 'https://memorialista.example';
const workerSource = fs.readFileSync(path.join(root, 'app/static/asesor/pwa/sw.js'), 'utf8');

function localFile(url) {
  const pathname = new URL(url, origin).pathname;
  if (pathname === '/asesor/offline-shell.html') return path.join(root, 'app/static/asesor/pwa/shell.html');
  if (pathname === '/asesor/manifest.webmanifest') return path.join(root, 'app/static/asesor/pwa/manifest.webmanifest');
  if (!pathname.startsWith('/static/asesor/')) throw new Error('Unexpected URL requested: ' + url);
  return path.join(root, 'app', pathname.slice(1));
}

function harness(options = {}) {
  const events = new Map(), buckets = new Map(), calls = [];
  const state = { offline: false, navigation: null, claimed: false };
  const caches = {
    async open(name) {
      if (!buckets.has(name)) buckets.set(name, new Map());
      const entries = buckets.get(name);
      return {
        async put(key, response) { entries.set(typeof key === 'string' ? key : key.url, response.clone()); },
        async match(key) { return entries.get(typeof key === 'string' ? key : key.url)?.clone(); },
      };
    },
    async keys() { return [...buckets.keys()]; },
    async delete(name) { return buckets.delete(name); },
  };
  const context = vm.createContext({
    console, URL, Request, Response, Headers, Uint8Array, crypto: webcrypto, caches,
    self: {
      location: { origin },
      addEventListener(type, handler) { events.set(type, handler); },
      clients: { async claim() { state.claimed = true; } },
    },
    async fetch(request, settings) {
      calls.push({ request, settings });
      if (state.offline) throw new TypeError('Offline');
      if (request.mode === 'navigate' && state.navigation) return state.navigation.clone();
      const url = new URL(request.url, origin);
      if (request.mode === 'navigate') return new Response('Live public page', { status: 200 });
      let body = fs.readFileSync(localFile(url.href));
      const headers = { 'Cache-Control': 'public, max-age=0', 'Content-Type': 'application/octet-stream' };
      if (options.corrupt === url.pathname) body = Buffer.from('Unexpected personal or changed data');
      if (options.private === url.pathname) headers['Cache-Control'] = 'private, no-store';
      if (options.vary === url.pathname) headers.Vary = 'Accept-Encoding, Cookie';
      const response = new Response(body, { status: 200, headers });
      Object.defineProperty(response, 'url', { value: options.redirect === url.pathname ? origin + '/app' : url.href });
      Object.defineProperty(response, 'redirected', { value: options.redirect === url.pathname });
      return response;
    },
  });
  vm.runInContext(workerSource, context);
  const assets = JSON.parse(vm.runInContext('JSON.stringify(PUBLIC_ASSETS)', context));
  const cacheName = vm.runInContext('CACHE_NAME', context);
  async function lifecycle(name, extra = {}) {
    let promise;
    events.get(name)({ waitUntil(value) { promise = value; }, ...extra });
    await promise;
  }
  async function request(url, config = {}) {
    let response;
    const req = { url: new URL(url, origin).href, method: config.method || 'GET', mode: config.mode || 'cors',
      headers: new Headers(config.headers || {}), credentials: 'include', redirect: 'manual' };
    events.get('fetch')({ request: req, respondWith(value) { response = value; } });
    return response === undefined ? undefined : await response;
  }
  return { assets, cacheName, buckets, calls, caches, state, lifecycle, request, events };
}

test('build allowlist contains all referenced advisor scripts and no private routes', () => {
  const h = harness();
  assert.ok(h.assets.length >= 20);
  const html = fs.readFileSync(path.join(root, 'app/static/asesor/pwa/shell.html'), 'utf8');
  const scripts = [...html.matchAll(/<script\b[^>]*src="([^"]+)"/g)].map(match => match[1]);
  for (const script of scripts) assert.ok(h.assets.some(asset => asset.url === script), script);
  for (const asset of h.assets) {
    assert.ok(asset.url.startsWith('/static/asesor/') || ['/asesor/offline-shell.html', '/asesor/manifest.webmanifest'].includes(asset.url), asset.url);
    assert.ok(!/\/(?:auth|api|app|login|generador)(?:\/|$)|auditor\.js/.test(asset.url), asset.url);
    assert.equal(createHash('sha256').update(fs.readFileSync(localFile(asset.url))).digest('hex'), asset.sha256, asset.url);
  }
  assert.ok(!h.assets.some(asset => ['/', '/asesor/'].includes(asset.url)));
});

test('precache fetches only byte-verified public assets without cookies or redirects', async () => {
  const h = harness();
  await h.lifecycle('install');
  assert.equal(h.buckets.get(h.cacheName).size, h.assets.length);
  assert.equal(h.calls.length, h.assets.length);
  for (const { request } of h.calls) {
    assert.equal(request.credentials, 'omit');
    assert.equal(request.redirect, 'error');
    assert.equal(request.cache, 'reload');
    assert.equal(request.headers.has('authorization'), false);
    assert.equal(request.headers.has('cookie'), false);
  }
});

test('private, session, API, arbitrary queries and external requests are not intercepted', async () => {
  const h = harness();
  const paths = ['/', '/login', '/auth/callback', '/api/health', '/api/auth/sesion', '/api/documentos', '/app', '/app/', '/generador', '/auditor.js', '/static/auditor.js', '/static/auth/session.js', '/static/index.html', '/asesor/login', '/asesor/api/private', '/asesor/?token=example', '/asesor/offline-shell.html?token=example', '/static/asesor/js/app.js?token=example', 'https://other.example/static/asesor/js/app.js'];
  for (const url of paths) for (const mode of ['navigate', 'cors']) {
    assert.equal(await h.request(url, { mode }), undefined, `${mode}: ${url}`);
  }
  const asset = h.assets.find(asset => asset.url.includes('/js/app.js'));
  assert.equal(await h.request(asset.url, { method: 'POST' }), undefined);
  assert.equal(await h.request(asset.url, { headers: { Authorization: 'Bearer test' } }), undefined);
  assert.equal(await h.request(asset.url, { headers: { Range: 'bytes=0-99' } }), undefined);
  assert.equal(await h.request('/asesor/', { mode: 'navigate', headers: { Authorization: 'Bearer test' } }), undefined);
  assert.equal(h.calls.length, 0);
  assert.equal(h.buckets.size, 0);
});

test('offline public navigation receives the static shell and all scripts from cache', async () => {
  const h = harness();
  await h.lifecycle('install');
  h.state.offline = true;
  const response = await h.request('/asesor/', { mode: 'navigate' });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('x-memorialista-offline'), '1');
  assert.equal(await response.text(), fs.readFileSync(localFile('/asesor/offline-shell.html'), 'utf8'));
  for (const asset of h.assets.filter(asset => asset.url.includes('/js/'))) {
    const resource = await h.request(asset.url);
    assert.equal(resource.status, 200);
    assert.equal(await resource.text(), fs.readFileSync(localFile(asset.url), 'utf8'));
  }
  assert.equal(await h.request('/app', { mode: 'navigate' }), undefined);
});

test('a live session redirect is returned but never placed in any cache', async () => {
  const h = harness();
  await h.lifecycle('install');
  const keys = [...h.buckets.get(h.cacheName).keys()];
  h.state.navigation = new Response(null, { status: 303, headers: { Location: '/app', 'Cache-Control': 'private, no-store' } });
  const response = await h.request('/asesor/', { mode: 'navigate' });
  assert.equal(response.status, 303);
  assert.equal(response.headers.get('location'), '/app');
  assert.deepEqual([...h.buckets.get(h.cacheName).keys()], keys);
  assert.equal(h.calls.at(-1).settings.cache, 'no-store');
  assert.equal(h.calls.at(-1).request.credentials, 'include');
});

test('even a personalized 200 navigation response is never cached', async () => {
  const h = harness();
  await h.lifecycle('install');
  h.state.navigation = new Response('Private document fixture', { headers: { 'Cache-Control': 'private, no-store' } });
  assert.equal(await (await h.request('/asesor/', { mode: 'navigate' })).text(), 'Private document fixture');
  for (const entries of h.buckets.values()) for (const response of entries.values()) {
    assert.ok(!(await response.clone().text()).includes('Private document fixture'));
  }
});

test('server failures use only the existing public shell', async () => {
  const h = harness();
  await h.lifecycle('install');
  h.state.navigation = new Response('Unavailable', { status: 503 });
  const response = await h.request('/asesor/', { mode: 'navigate' });
  assert.equal(response.headers.get('x-memorialista-offline'), '1');
  assert.equal(await response.text(), fs.readFileSync(localFile('/asesor/offline-shell.html'), 'utf8'));
});

test('missing or evicted cache does not provide any private fallback', async () => {
  const h = harness(); h.state.offline = true;
  const response = await h.request('/asesor/', { mode: 'navigate' });
  assert.equal(response.status, 503);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal(await h.request('/app', { mode: 'navigate' }), undefined);
  assert.equal(await h.request('/login', { mode: 'navigate' }), undefined);
});

for (const kind of ['corrupt', 'private', 'vary', 'redirect']) {
  test(`install rejects ${kind} responses atomically and preserves the older cache`, async () => {
    const h = harness({ [kind]: '/asesor/offline-shell.html' });
    await h.caches.open('em-asesor-public-v1-older');
    await assert.rejects(() => h.lifecycle('install'));
    assert.equal(h.buckets.has(h.cacheName), false);
    assert.equal(h.buckets.has('em-asesor-public-v1-older'), true);
  });
}

test('activation deletes only obsolete advisor caches', async () => {
  const h = harness();
  await h.lifecycle('install');
  await h.caches.open('em-asesor-public-v1-older');
  await h.caches.open('another-application-cache');
  await h.lifecycle('activate');
  assert.equal(h.state.claimed, true);
  assert.equal(h.buckets.has('em-asesor-public-v1-older'), false);
  assert.equal(h.buckets.has('another-application-cache'), true);
  assert.equal(h.buckets.has(h.cacheName), true);
});

test('cache status reports ready only after all public resources are present', async () => {
  const h = harness();
  let message;
  const extra = { data: { type: 'ASESOR_PUBLIC_CACHE_STATUS' }, ports: [{ postMessage(value) { message = value; } }] };
  await h.lifecycle('message', extra);
  assert.equal(message.ready, false);
  await h.lifecycle('install');
  await h.lifecycle('message', extra);
  assert.equal(message.ready, true);
  h.buckets.get(h.cacheName).delete(new URL(h.assets[0].url, origin).href);
  await h.lifecycle('message', extra);
  assert.equal(message.ready, false);
});
