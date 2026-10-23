/**
 * Recorrido real de la sección ciudadana: Chromium + FastAPI local, sin cuentas
 * ni servicios externos. Los datos de este archivo son ficticios.
 *
 * Preparación (en otra terminal):
 *   GEMINI_API_KEY= GROQ_API_KEY= SUPABASE_URL= SUPABASE_ANON_KEY= \
 *   SUPABASE_SERVICE_ROLE_KEY= SUPABASE_JWT_SECRET= KEEP_ALIVE=false \
 *   python -m uvicorn app.main:app --host 127.0.0.1 --port 8768
 *
 * Instalar Playwright y su Chromium en el entorno de pruebas. Después:
 *   node --test tests/test_asesor_browser.mjs
 *
 * Variables opcionales: ASESOR_BASE_URL (solo loopback), PLAYWRIGHT_MODULE
 * (ruta al módulo instalado), PLAYWRIGHT_CHROMIUM_EXECUTABLE (binario local),
 * ASESOR_BROWSER_ARTIFACTS (capturas/descargas), ASESOR_BROWSER_SKIP_OFFLINE=1
 * (únicamente mientras se reconstruyen los activos; la verificación final no
 * debe omitir las pruebas sin conexión).
 */
import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { mkdir, mkdtemp, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { inflateRawSync } from 'node:zlib';

const imported = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { chromium } = imported.default || imported;
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const base = new URL(process.env.ASESOR_BASE_URL || 'http://127.0.0.1:8768/');
assert.ok(['localhost', '127.0.0.1', '[::1]'].includes(base.hostname), 'Usa exclusivamente un servidor local de pruebas.');
const artifacts = process.env.ASESOR_BROWSER_ARTIFACTS
  ? path.resolve(process.env.ASESOR_BROWSER_ARTIFACTS)
  : await mkdtemp(path.join(tmpdir(), 'memorialista-browser-'));
await mkdir(artifacts, { recursive: true });
const skipOffline = process.env.ASESOR_BROWSER_SKIP_OFFLINE === '1';
const hoy = new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Bogota' }).format(new Date());
const ayer = new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Bogota' }).format(new Date(Date.now() - 86400000));
const presentacion = new Date(Date.now() - 60 * 86400000).toISOString().slice(0, 10);
const datos = {
  nombre: 'María Prueba Ñandú', genero: 'f', tipoDoc: 'CC', numDoc: '1000000001',
  ciudad: 'Bogotá D.C.', direccion: 'Calle de Prueba 1', telefono: '3000000000',
  correo: 'persona@example.invalid', entidadNombre: 'EPS de Prueba',
  entidadCiudad: 'Bogotá D.C.', tipoServicio: 'cita',
  servicio: 'Consulta de control de prueba',
  riesgo: 'Demora ficticia para verificar el formulario. No corresponde a una persona real.',
  relato: 'Caso ficticio de prueba. Se solicitó una cita de control y se conserva la constancia.',
};
let browser;

before(async () => {
  browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {}),
  });
}, { timeout: 30000 });
after(async () => { await browser?.close(); });

async function nuevaPagina(viewport = { width: 1440, height: 1000 }) {
  const context = await browser.newContext({ viewport, locale: 'es-CO', timezoneId: 'America/Bogota', acceptDownloads: true });
  const page = await context.newPage();
  const errors = [], externos = [];
  page.setDefaultTimeout(10000);
  page.on('pageerror', error => errors.push(error.stack || error.message));
  page.on('request', request => {
    if (/^https?:/.test(request.url()) && new URL(request.url()).origin !== base.origin) externos.push(request.url());
  });
  await page.addInitScript(() => {
    window.__violacionesCSP = [];
    document.addEventListener('securitypolicyviolation', event => {
      window.__violacionesCSP.push(`${event.violatedDirective}: ${event.blockedURI}`);
    });
  });
  return { context, page, errors, externos };
}

async function abrir(page, ruta = '/') {
  const response = await page.goto(new URL(ruta, base).href, { waitUntil: 'networkidle' });
  assert.equal(response.status(), 200);
  assert.match(response.headers()['content-security-policy'] || '', /script-src-attr 'none'/);
  await page.waitForFunction(() => window.AJ?.ui && AJ.casos.length === 66);
  if (await page.locator('#b-aceptar-aviso').isVisible()) await page.locator('#b-aceptar-aviso').click();
}

async function vista(page, hash, selector) {
  await page.evaluate(value => { location.hash = value; }, hash);
  await page.locator(selector).waitFor({ state: 'visible' });
}

async function captura(page, name, fullPage = false) {
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  await page.screenshot({ path: path.join(artifacts, `${name}.png`), fullPage, animations: 'disabled' });
}

async function sinErrores(state) {
  assert.deepEqual(state.errors, [], 'Errores JavaScript del navegador');
  assert.deepEqual(await state.page.evaluate(() => window.__violacionesCSP || []), [], 'Violaciones CSP');
  assert.deepEqual(state.externos, [], 'La orientación no debe enviar respuestas a servicios externos');
}

async function sinDesbordamiento(page, label) {
  const info = await page.evaluate(() => ({
    width: innerWidth,
    scroll: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
    candidatos: [...document.querySelectorAll('body *')].filter(el => {
      const r = el.getBoundingClientRect(), s = getComputedStyle(el);
      return r.width > 0 && s.visibility !== 'hidden' && (r.left < -1 || r.right > innerWidth + 1) && !el.closest('[hidden]');
    }).slice(0, 12).map(el => ({ tag: el.tagName, id: el.id, clase: el.className, ancho: Math.round(el.getBoundingClientRect().width) })),
  }));
  assert.ok(info.scroll <= info.width + 1, `${label}: ${JSON.stringify(info)}`);
}

async function rellenar(page, fields = datos) {
  for (const [name, value] of Object.entries(fields)) {
    const input = page.locator(`#formulario [name="${name}"]`).first();
    assert.equal(await input.count(), 1, `Existe el campo ${name}`);
    const tag = await input.evaluate(el => el.tagName);
    if (tag === 'SELECT') await input.selectOption(value);
    else await input.fill(value);
  }
}

async function crearPeticion(page, porOrientador = false) {
  if (porOrientador) {
    await vista(page, '#orientador', '.orientador-opciones');
    await page.locator('.orientador-opcion').filter({ hasText: 'Salud: EPS' }).click();
    await page.locator('.orientador-opcion').filter({ hasText: 'La EPS no autoriza' }).click();
    await page.getByRole('link', { name: 'Puedo esperar unos días', exact: true }).click();
    await page.locator('.orientador-principal .btn').click();
    assert.match(page.url(), /#caso\/pet_eps_servicio$/);
  } else await vista(page, '#caso/pet_eps_servicio', '#formulario');
  await page.locator('#formulario').waitFor();
  await rellenar(page);
  await page.locator('#formulario button[type="submit"]').click();
  await page.locator('#b-pdf').waitFor();
  assert.match(await page.locator('#app').innerText(), /María Prueba Ñandú|MARÍA PRUEBA ÑANDÚ/);
}

async function descarga(page, selector, filename) {
  const [download] = await Promise.all([page.waitForEvent('download'), page.locator(selector).click()]);
  assert.equal(await download.failure(), null);
  const destination = path.join(artifacts, filename || download.suggestedFilename());
  await download.saveAs(destination);
  return { bytes: await readFile(destination), filename: download.suggestedFilename(), destination };
}

function contenidoZip(buffer, sought) {
  // Lee la tabla central: funciona con entradas ZIP almacenadas o Deflate.
  for (let i = 0; i < buffer.length - 46; i++) {
    if (buffer.readUInt32LE(i) !== 0x02014b50) continue;
    const method = buffer.readUInt16LE(i + 10), size = buffer.readUInt32LE(i + 20);
    const nameLength = buffer.readUInt16LE(i + 28), extraLength = buffer.readUInt16LE(i + 30), commentLength = buffer.readUInt16LE(i + 32);
    const filename = buffer.subarray(i + 46, i + 46 + nameLength).toString();
    if (filename === sought) {
      const local = buffer.readUInt32LE(i + 42);
      const start = local + 30 + buffer.readUInt16LE(local + 26) + buffer.readUInt16LE(local + 28);
      const compressed = buffer.subarray(start, start + size);
      assert.ok([0, 8].includes(method), `Compresión ZIP soportada (${method})`);
      return (method === 8 ? inflateRawSync(compressed) : compressed).toString('utf8');
    }
    i += 45 + nameLength + extraLength + commentLength;
  }
  throw new Error(`Falta ${sought} en el DOCX`);
}

async function exportaciones(page, prefix) {
  const pdf = await descarga(page, '#b-pdf', `${prefix}.pdf`);
  assert.match(pdf.filename, /\.pdf$/i);
  assert.equal(pdf.bytes.subarray(0, 5).toString(), '%PDF-');
  assert.match(pdf.bytes.toString('latin1'), /\/Type\s*\/Page\b/);
  assert.match(pdf.bytes.toString('latin1'), /\/ToUnicode\b/, 'El PDF conserva un mapa Unicode');
  const pdfTitleHex = pdf.bytes.toString('latin1').match(/\/Title\s*<([0-9a-f]+)>/i)?.[1];
  assert.ok(pdfTitleHex, 'El PDF declara un título');
  const pdfTitle = Buffer.from(pdfTitleHex, 'hex').subarray(2).swap16().toString('utf16le');
  assert.ok(pdfTitle.trim().length > 0, 'El título del PDF no queda vacío');
  assert.doesNotMatch(pdfTitle, /undefined|\[object Object\]/);
  const docx = await descarga(page, '#b-word', `${prefix}.docx`);
  assert.match(docx.filename, /\.docx$/i);
  assert.equal(docx.bytes.readUInt32LE(), 0x04034b50);
  const xml = contenidoZip(docx.bytes, 'word/document.xml');
  assert.match(xml, /MARÍA PRUEBA ÑANDÚ|María Prueba Ñandú/);
  assert.match(xml, /EPS DE PRUEBA|EPS de Prueba/);
  const core = contenidoZip(docx.bytes, 'docProps/core.xml');
  assert.doesNotMatch(core, /Sueñomotora|Asesor Jurídico Ciudadano|midefensor/i);
  const docxTitle = core.match(/<dc:title>([\s\S]*?)<\/dc:title>/)?.[1] || '';
  assert.ok(docxTitle.trim().length > 0, 'El título del DOCX no queda vacío');
  assert.doesNotMatch(docxTitle, /undefined|\[object Object\]/);
  return { pdf, docx };
}

test('orientador, documento, descargas, seguimiento, prellenado y respaldo conservan los datos', { timeout: 120000 }, async t => {
  const state = await nuevaPagina();
  const { page, context } = state;
  t.after(() => context.close());
  await abrir(page);
  await captura(page, '01-inicio-escritorio');
  await sinDesbordamiento(page, 'Inicio escritorio');
  await crearPeticion(page, true);
  await captura(page, '02-documento-escritorio');
  await exportaciones(page, 'documento-prueba');
  await page.locator('#b-guardar').click();
  await vista(page, '#mis-documentos', '#lista-docs');
  assert.equal(await page.locator('.doc-item').count(), 1);
  await page.locator('[data-accion="seguimiento"]').click();
  const seg = page.locator('.form-seguimiento');
  await seg.locator('[name="fecha"]').fill(hoy);
  await seg.locator('[name="numero"]').fill('RAD-PRUEBA-001');
  await seg.locator('[name="canal"]').selectOption('correo');
  await seg.locator('[name="respuesta"]').selectOption('');
  await seg.locator('[name="nota"]').fill('Nota ficticia: conservar fecha, canal y radicado al exportar.');
  await seg.locator('button[type="submit"]').click();
  await page.waitForFunction(() => AJ.ui.docs.lista()[0]?.seguimiento?.numero === 'RAD-PRUEBA-001');
  const ics = await descarga(page, '[data-accion="calendario"]', 'recordatorio-prueba.ics');
  assert.match(ics.bytes.toString(), /BEGIN:VCALENDAR[\s\S]*BEGIN:VEVENT[\s\S]*DTSTART/);
  // Ahora simulamos una radicación anterior cuyo plazo ya transcurrió para
  // recorrer el siguiente documento; no esperamos recordatorios futuros de
  // un plazo que ya venció.
  await page.locator('[data-accion="seguimiento"]').click();
  await seg.locator('[name="fecha"]').fill(presentacion);
  await seg.locator('button[type="submit"]').click();
  await page.waitForFunction(fecha => AJ.ui.docs.lista()[0]?.seguimiento?.fecha === fecha, presentacion);
  const original = await page.evaluate(() => AJ.ui.docs.lista()[0]);
  assert.equal(original.seguimiento.fecha, presentacion);
  await captura(page, '03-seguimiento-escritorio');
  const siguiente = page.locator('[data-accion="siguiente"][data-caso="tut_peticion"]');
  await siguiente.click();
  await page.locator('#formulario').waitFor();
  const prefill = await page.evaluate(() => ({ datos: AJ.ui.estado.datos, origen: AJ.ui.estado.origen }));
  assert.equal(prefill.datos.nombre, datos.nombre);
  assert.equal(prefill.datos.numDoc, datos.numDoc);
  assert.equal(prefill.datos.entidadNombre, datos.entidadNombre);
  assert.equal(prefill.datos.fechaPeticion, presentacion);
  assert.equal(prefill.origen.id, original.id);
  assert.match(await page.locator('.prellenado').innerText(), /Ya llenamos parte del formulario/);
  await page.getByRole('button', { name: 'Guardar borrador en este navegador', exact: true }).click();
  await vista(page, '#mis-documentos', '#lista-docs');
  const idTutela = await page.evaluate(() => AJ.ui.docs.lista().find(reg => reg.casoId === 'tut_peticion').id);
  const tarjetaTutela = page.locator(`.doc-item[data-id="${idTutela}"]`);
  await tarjetaTutela.locator('[data-accion="seguimiento"]').click();
  const seguimientoTutela = tarjetaTutela.locator('.form-seguimiento');
  for (const [name, value] of Object.entries({
    fecha: presentacion, numero: 'TUT-PRUEBA-002', juzgado: 'Juzgado de Prueba',
    fechaRespuesta: ayer, fechaNotificacion: ayer,
    fechaInicioCumplimiento: hoy, horaInicioCumplimiento: '09:30',
    plazoCumplimiento: '48', nota: 'Fallo ficticio: plazo indicado expresamente en una orden de prueba.',
  })) await seguimientoTutela.locator(`[name="${name}"]`).fill(value);
  await seguimientoTutela.locator('[name="canal"]').selectOption('tutela_linea');
  await seguimientoTutela.locator('[name="decision"]').selectOption('concedio');
  await seguimientoTutela.locator('[name="unidadCumplimiento"]').selectOption('horas');
  await seguimientoTutela.locator('[name="cumple"]').selectOption('no');
  await seguimientoTutela.locator('button[type="submit"]').click();
  await page.waitForFunction(id => AJ.ui.docs.lista().find(reg => reg.id === id)?.seguimiento?.plazoCumplimiento === '48', idTutela);
  const expected = await page.evaluate(() => AJ.ui.docs.lista());
  assert.equal(expected.length, 2);
  assert.ok(expected.some(reg => reg.origen?.id === original.id));
  const seguimientoGuardado = expected.find(reg => reg.id === idTutela).seguimiento;
  assert.equal(seguimientoGuardado.fechaNotificacion, ayer);
  assert.equal(seguimientoGuardado.fechaInicioCumplimiento, hoy);
  assert.equal(seguimientoGuardado.horaInicioCumplimiento, '09:30');
  assert.equal(seguimientoGuardado.unidadCumplimiento, 'horas');
  assert.equal(seguimientoGuardado.juzgado, 'Juzgado de Prueba');
  const backup = await descarga(page, '#b-exportar', 'respaldo-prueba.json');
  assert.deepEqual(JSON.parse(backup.bytes).documentos, expected);
  await page.locator('#b-borrar-todo').click();
  await page.locator('#b-borrar-todo').click();
  assert.deepEqual(await page.evaluate(() => AJ.ui.docs.lista()), []);
  await page.locator('#i-importar').setInputFiles(backup.destination);
  await page.waitForFunction(() => AJ.ui.docs.lista().length === 2);
  assert.deepEqual(await page.evaluate(() => AJ.ui.docs.lista()), expected);
  // Una copia de otra versión se rechaza sin perder el historial ya guardado.
  await page.locator('#i-importar').setInputFiles({ name: 'otra-version.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify({ version: 999, documentos: expected })) });
  await page.waitForFunction(() => document.getElementById('aviso').classList.contains('error'));
  assert.deepEqual(await page.evaluate(() => AJ.ui.docs.lista()), expected);
  await page.reload({ waitUntil: 'networkidle' });
  assert.deepEqual(await page.evaluate(() => AJ.ui.docs.lista()), expected);
  await sinErrores(state);
  t.diagnostic(`Capturas y descargas: ${artifacts}`);
});

for (const width of [350, 390]) test(`móvil ${width}px: menú, formulario, letra al 140% y contraste`, { timeout: 60000 }, async t => {
  const state = await nuevaPagina({ width, height: 844 });
  const { page, context } = state;
  t.after(() => context.close());
  await abrir(page);
  await captura(page, `04-inicio-movil-${width}`);
  await sinDesbordamiento(page, `Inicio ${width}`);
  await page.locator('#menu-movil').click();
  assert.equal(await page.locator('#menu-movil').getAttribute('aria-expanded'), 'true');
  await page.locator('#nav-principal a[href="#orientador"]').click();
  await page.locator('.orientador-opciones').waitFor();
  assert.equal(await page.locator('#menu-movil').getAttribute('aria-expanded'), 'false');
  await sinDesbordamiento(page, `Orientador ${width}`);
  await page.locator('#b-accesibilidad').click();
  for (let i = 0; i < 3; i++) await page.locator('#a11y-mas').click();
  await page.locator('#a11y-contraste').click();
  assert.equal(await page.locator('#a11y-contraste').getAttribute('aria-pressed'), 'true');
  assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--escala').trim()), '1.4');
  assert.equal(await page.locator('#a11y-mas').isDisabled(), true);
  await captura(page, `05-accesibilidad-${width}`);
  await sinDesbordamiento(page, `Panel accesibilidad ${width}`);
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#panel-accesibilidad').isVisible(), false);
  await vista(page, '#caso/pet_eps_servicio', '#formulario');
  await sinDesbordamiento(page, `Formulario al 140% ${width}`);
  await captura(page, `06-formulario-140-contraste-${width}`);
  await page.locator('.preview-toggle').click();
  assert.equal(await page.locator('#previa').isVisible(), true);
  await sinDesbordamiento(page, `Vista previa al 140% ${width}`);
  // Contraste medido en colores computados de texto y botón: no es una
  // certificación integral de accesibilidad ni sustituye lector de pantalla.
  const contrast = await page.evaluate(() => {
    const rgb = color => (color.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
    const light = color => rgb(color).map(c => c / 255).map(c => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4).reduce((sum, c, i) => sum + c * [.2126, .7152, .0722][i], 0);
    return ['body', '#formulario button[type="submit"]'].map(selector => {
      const s = getComputedStyle(document.querySelector(selector));
      const a = light(s.color), b = light(s.backgroundColor);
      return { selector, color: s.color, background: s.backgroundColor, ratio: (Math.max(a, b) + .05) / (Math.min(a, b) + .05) };
    });
  });
  for (const item of contrast) assert.ok(item.ratio >= 4.5, JSON.stringify(item));
  await page.locator('#b-accesibilidad').click();
  await page.locator('#tema').click();
  assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
  await page.keyboard.press('Escape');
  await captura(page, `06b-formulario-oscuro-140-${width}`);
  await sinDesbordamiento(page, `Formulario oscuro al 140% ${width}`);
  await page.reload({ waitUntil: 'networkidle' });
  assert.deepEqual(await page.evaluate(() => AJ.a11y.estado()), { escala: 3, contraste: true, maximo: 3 });
  assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
  await sinErrores(state);
});

test('PWA: catálogo, orientador y exportaciones siguen disponibles al cortar la red', { skip: skipOffline, timeout: 120000 }, async t => {
  const state = await nuevaPagina();
  const { page, context } = state;
  t.after(() => context.close());
  await abrir(page, '/asesor/');
  await page.waitForFunction(async () => {
    const reg = await navigator.serviceWorker.getRegistration('/asesor/');
    return reg?.active?.state === 'activated';
  }, null, { timeout: 30000 });
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForFunction(() => !!navigator.serviceWorker.controller);
  const cache = await page.evaluate(async () => {
    const names = await caches.keys();
    const urls = [];
    for (const name of names) for (const request of await (await caches.open(name)).keys()) urls.push(new URL(request.url).pathname);
    return urls;
  });
  assert.ok(cache.includes('/static/asesor/js/exportar.js'));
  assert.ok(cache.includes('/static/asesor/js/seguimiento.js'));
  assert.ok(cache.includes('/static/asesor/js/pdf-fuentes.js'));
  assert.ok(cache.includes('/asesor/offline-shell.html'));
  assert.ok(cache.every(url => !/^\/(?:app|generador|login|api)(?:\/|$)/.test(url)), 'No se precachean rutas privadas');
  await context.setOffline(true);
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForFunction(() => AJ.casos.length === 66);
  await crearPeticion(page, true);
  await exportaciones(page, 'documento-pwa-offline');
  await captura(page, '07-pwa-sin-conexion');
  await sinErrores(state);
});

test('archivo autónomo: abre por file:// y exporta con la red desactivada', { skip: skipOffline, timeout: 90000 }, async t => {
  const state = await nuevaPagina();
  const { page, context } = state;
  t.after(() => context.close());
  await context.setOffline(true);
  const offline = path.join(root, 'app/static/asesor/descargas/el-memorialista-ciudadano-sin-internet.html');
  await page.goto(pathToFileURL(offline).href, { waitUntil: 'load' });
  await page.waitForFunction(() => window.AJ_SIN_INTERNET && AJ.casos.length === 66);
  assert.equal(await page.locator('[data-online-only]:visible').count(), 0);
  if (await page.locator('#b-aceptar-aviso').isVisible()) await page.locator('#b-aceptar-aviso').click();
  await crearPeticion(page, true);
  await exportaciones(page, 'documento-archivo-autonomo');
  await captura(page, '08-archivo-autonomo');
  await sinErrores(state);
});
