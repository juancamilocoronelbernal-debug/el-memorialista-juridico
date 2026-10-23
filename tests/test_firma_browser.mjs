/**
 * Formulario público de firma servido por la aplicación local real.
 * Sólo se interceptan las dos operaciones POST de firma; no se firman documentos
 * reales ni se usan credenciales, proveedores externos o destinatarios reales.
 *
 * Requiere el servidor en http://127.0.0.1:8787.
 * node --test tests/test_firma_browser.mjs
 * Opcionales: FIRMA_BASE_URL (sólo loopback), PLAYWRIGHT_MODULE y
 * PLAYWRIGHT_CHROMIUM_EXECUTABLE.
 */
import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';

const imported = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { chromium } = imported.default || imported;
const base = new URL(process.env.FIRMA_BASE_URL || 'http://127.0.0.1:8787');
assert.ok(['localhost', '127.0.0.1', '[::1]'].includes(base.hostname), 'Utiliza un servidor local de pruebas.');
const origin = base.origin;
const token = 'f'.repeat(43);
assert.equal(token.length, 43);
let browser;

before(async () => {
  browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {}),
  });
});
after(async () => { await browser?.close(); });

function record(overrides = {}) {
  return {
    id: 'e0698a19-9b01-4642-a038-9403aedf7bb2',
    title: 'Documento ficticio para la prueba',
    signer_name: 'Persona Ficticia',
    document_text: 'Texto de prueba. No constituye una solicitud de firma real.',
    document_hash: 'a'.repeat(64),
    status: 'pending',
    expires_at: '2030-01-01T00:00:00Z',
    signed_at: null,
    ...overrides,
  };
}

async function fixture(t, initial = record()) {
  const context = await browser.newContext({ locale: 'es-CO', timezoneId: 'America/Bogota' });
  t.after(() => context.close());
  const page = await context.newPage();
  page.setDefaultTimeout(10_000);
  const state = { record: initial, views: [], acceptances: [], requests: [], errors: [], dialogs: [], csp: [], viewError: null, acceptError: null };
  page.on('request', request => state.requests.push({ url: request.url(), referer: request.headers().referer || '' }));
  page.on('pageerror', error => state.errors.push(error.message));
  page.on('dialog', async dialog => { state.dialogs.push(dialog.message()); await dialog.dismiss(); });
  page.on('console', message => {
    if (message.type() === 'error' && /Content Security Policy|violates.*directive/i.test(message.text())) state.csp.push(message.text());
  });

  for (const operation of ['ver', 'aceptar']) {
    await page.route(origin + '/api/firmas-publicas/' + operation, async route => {
      const request = route.request();
      assert.equal(request.method(), 'POST', 'El token sólo se transmite mediante POST.');
      assert.equal(new URL(request.url()).search, '');
      assert.equal(request.headers().authorization, undefined);
      const body = request.postDataJSON();
      assert.equal(body.token, token);
      const error = operation === 'ver' ? state.viewError : state.acceptError;
      (operation === 'ver' ? state.views : state.acceptances).push(body);
      if (error) {
        await route.fulfill({ status: error.status, contentType: 'application/json', body: JSON.stringify({ detail: error.detail }) });
        return;
      }
      if (operation === 'aceptar') {
        state.record = { ...state.record, status: 'signed', signed_at: '2026-10-23T12:00:00Z' };
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.record) });
    });
  }

  const open = async () => {
    const response = await page.goto(origin + '/firmar#' + token);
    assert.equal(response.status(), 200, 'El HTML procede del servidor local real.');
    assert.match(response.headers()['content-security-policy'], /script-src 'self'/);
  };
  const clean = () => {
    assert.deepEqual(state.errors, []);
    assert.deepEqual(state.dialogs, []);
    assert.deepEqual(state.csp, []);
    assert.ok(state.requests.every(request => !request.url.includes(token) && !request.referer.includes(token)), 'El secreto no aparece en URL de petición ni en Referer.');
    for (const asset of ['/static/firma/firma.js', '/static/firma/firma.css']) {
      assert.ok(state.requests.some(request => request.url === origin + asset), 'Se carga el recurso real ' + asset);
    }
  };
  return { page, state, open, clean };
}

async function fillSigner(page) {
  await page.getByLabel('Nombre completo', { exact: true }).fill('Persona Ficticia');
  await page.getByLabel('Correo al que se dirige la solicitud', { exact: true }).fill('persona@example.invalid');
}

test('Fragmento privado, contenido hostil como texto y consentimiento antes de aceptar', { timeout: 30_000 }, async t => {
  const hostile = record({
    title: '<img src=x onerror="window.__firmaXss=1"> Título de prueba',
    document_text: '</div><script>window.__firmaXss=2</script>\n<img src=x onerror="window.__firmaXss=3">',
    signer_name: '<svg onload="window.__firmaXss=4">Persona Ficticia</svg>',
  });
  const { page, state, open, clean } = await fixture(t, hostile);
  await open();
  await page.locator('#sign-form').waitFor({ state: 'visible' });
  assert.deepEqual(state.views, [{ token }]);
  assert.equal(await page.locator('#title').textContent(), hostile.title);
  assert.equal(await page.locator('#document').textContent(), hostile.document_text);
  assert.equal(await page.locator('#recipient').textContent(), 'Solicitud dirigida a ' + hostile.signer_name);
  assert.equal(await page.locator('#title img, #document img, #document script, #recipient svg').count(), 0);
  assert.equal(await page.evaluate(() => window.__firmaXss), undefined);

  await fillSigner(page);
  await page.getByRole('button', { name: 'Aceptar y firmar el documento', exact: true }).click();
  assert.equal(await page.getByRole('checkbox').evaluate(input => input.validity.valueMissing), true);
  assert.equal(state.acceptances.length, 0, 'No hay solicitud de aceptación sin consentimiento.');

  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Aceptar y firmar el documento', exact: true }).click();
  await page.locator('#success').waitFor({ state: 'visible' });
  assert.deepEqual(state.acceptances, [{ token, name: 'Persona Ficticia', email: 'persona@example.invalid', consent: true }]);
  assert.equal(await page.locator('#message').textContent(), 'El documento fue aceptado.');
  assert.equal(await page.locator('#sign-form').isVisible(), false);
  assert.match(await page.locator('#success-text').textContent(), new RegExp(hostile.id));
  assert.equal(await page.locator('#document').textContent(), hostile.document_text);
  clean();
});

test('Una solicitud ya firmada conserva la confirmación y no ofrece otro formulario', { timeout: 20_000 }, async t => {
  const { page, state, open, clean } = await fixture(t, record({ status: 'signed', signed_at: '2026-10-23T12:00:00Z' }));
  await open();
  await page.locator('#success').waitFor({ state: 'visible' });
  assert.equal(await page.locator('#message').textContent(), 'El documento fue aceptado.');
  assert.equal(await page.locator('#sign-form').isVisible(), false);
  assert.equal(await page.locator('#document-section').isVisible(), true);
  assert.equal(await page.getByRole('button', { name: 'Imprimir esta confirmación', exact: true }).isVisible(), true);
  assert.equal(state.views.length, 1);
  assert.equal(state.acceptances.length, 0);
  clean();
});

test('El fallo de aceptación y el enlace vencido se muestran sin confirmar una firma', { timeout: 30_000 }, async t => {
  const { page, state, open, clean } = await fixture(t);
  state.acceptError = { status: 503, detail: 'No pudimos completar la operación de firma. No se confirmó ningún cambio.' };
  await open();
  await page.locator('#sign-form').waitFor({ state: 'visible' });
  await fillSigner(page);
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Aceptar y firmar el documento', exact: true }).click();
  await page.locator('#message.error').filter({ hasText: state.acceptError.detail }).waitFor();
  assert.equal(await page.locator('#success').isVisible(), false);
  assert.equal(await page.locator('#sign-form').isVisible(), true);
  assert.equal(await page.getByRole('button', { name: 'Aceptar y firmar el documento', exact: true }).isEnabled(), true);
  assert.equal(state.acceptances.length, 1);

  state.viewError = { status: 404, detail: 'El enlace no está disponible, caducó o fue cancelado.' };
  await page.reload();
  await page.locator('#message.error').filter({ hasText: state.viewError.detail }).waitFor();
  assert.equal(await page.locator('#document-section').isVisible(), false);
  assert.equal(await page.locator('#sign-form').isVisible(), false);
  assert.equal(await page.locator('#success').isVisible(), false);
  assert.equal(state.views.length, 2);
  assert.equal(state.acceptances.length, 1);
  clean();
});
