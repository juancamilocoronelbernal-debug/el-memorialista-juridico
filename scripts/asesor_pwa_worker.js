/* Generated with the explicit public asset list by build_asesor_pwa.py.
 * Scope: /asesor/. No root, login, session, private HTML, API or user documents.
 */
'use strict';
const CACHE_PREFIX = 'em-asesor-public-v1-';
const CACHE_NAME = CACHE_PREFIX + __PUBLIC_VERSION__;
const PUBLIC_ASSETS = __PUBLIC_ASSETS__;
const ASSETS = new Map(PUBLIC_ASSETS.map(asset => [asset.url, asset]));
const SHELL_URL = '/asesor/offline-shell.html';

function localURL(path) { return new URL(path, self.location.origin).href; }

function publicAsset(request) {
  if (request.method !== 'GET' || request.headers.has('authorization') || request.headers.has('range')) return null;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.username || url.password || url.hash) return null;
  return ASSETS.get(url.pathname + url.search) || null;
}

async function validatedFetch(asset) {
  // Build a fresh request: never forward cookies, bearer tokens, submitted
  // answers, arbitrary query strings or redirects from a controlled page.
  const request = new Request(localURL(asset.url), {
    method: 'GET', credentials: 'omit', cache: 'reload', redirect: 'error',
    referrerPolicy: 'no-referrer', mode: 'same-origin',
  });
  const response = await fetch(request);
  if (!response.ok || response.status !== 200 || response.redirected ||
      ['opaque', 'opaqueredirect', 'error'].includes(response.type) ||
      response.url !== request.url) throw new Error('Non-public asset response refused');
  const cacheControl = response.headers.get('cache-control') || '';
  const vary = response.headers.get('vary') || '';
  if (/\b(?:private|no-store)\b/i.test(cacheControl) || /(?:^|,)\s*(?:cookie|authorization|\*)\s*(?:,|$)/i.test(vary)) {
    throw new Error('Personalized or non-cacheable response refused');
  }
  // Even a mistakenly personalized public endpoint cannot enter this cache:
  // its bytes must equal the deployment's known, static public source file.
  const bytes = await response.clone().arrayBuffer();
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)))
    .map(value => value.toString(16).padStart(2, '0')).join('');
  if (hash !== asset.sha256) throw new Error('Public asset integrity mismatch');
  return response;
}

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    try {
      // Sequential writes keep a failed install atomic: no pending writes can
      // recreate a partially deleted cache after a rejection.
      for (const asset of PUBLIC_ASSETS) {
        await cache.put(localURL(asset.url), await validatedFetch(asset));
      }
    } catch (error) {
      await caches.delete(CACHE_NAME);
      throw error;
    }
    // Do not skipWaiting: an update must not replace scripts under an open form.
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

async function publicNavigation(request) {
  try {
    // Network only, never cache.put. The live route verifies the session and
    // may redirect to /app. Navigation redirects remain browser navigation.
    const response = await fetch(request, { cache: 'no-store' });
    if (response.type === 'opaqueredirect' || response.status < 500) return response;
  } catch (_) { /* Offline: the independent, already verified public shell. */ }
  const cached = await (await caches.open(CACHE_NAME)).match(localURL(SHELL_URL));
  if (cached) {
    const headers = new Headers({ 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store', 'X-Memorialista-Offline': '1' });
    const csp = cached.headers.get('Content-Security-Policy');
    if (csp) headers.set('Content-Security-Policy', csp);
    return new Response(cached.body, { status: 200, headers });
  }
  return new Response('El asesor todavía no está disponible sin conexión. Abre /asesor/ con internet para prepararlo.', {
    status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' },
  });
}

async function publicResource(asset) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(localURL(asset.url));
  if (cached) return cached;
  // Cache may be evicted by the browser. Recover only the exact public bytes.
  try {
    const response = await validatedFetch(asset);
    await cache.put(localURL(asset.url), response.clone());
    return response;
  } catch (_) {
    return new Response('Recurso ciudadano no disponible sin conexión.', {
      status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' },
    });
  }
}

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET' || request.headers.has('authorization') || request.headers.has('range')) return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.username || url.password) return;
  // Exact route only, never a prefix fallback. /asesor/api, arbitrary queries,
  // /, /app, /login, /auth, /api and private static files all pass through.
  if (request.mode === 'navigate' && url.pathname === '/asesor/' && !url.search) {
    event.respondWith(publicNavigation(request));
    return;
  }
  const asset = publicAsset(request);
  if (asset) event.respondWith(publicResource(asset));
});

self.addEventListener('message', event => {
  if (event.data?.type !== 'ASESOR_PUBLIC_CACHE_STATUS' || !event.ports?.[0]) return;
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    const ready = (await Promise.all(PUBLIC_ASSETS.map(asset => cache.match(localURL(asset.url))))).every(Boolean);
    event.ports[0].postMessage({ type: 'ASESOR_PUBLIC_CACHE_STATUS', ready });
  })());
});
