/* Instalación exclusiva de la aplicación ciudadana. No registra / ni /app. */
(function () {
  'use strict';
  if (window.AJ_SIN_INTERNET || !['/', '/asesor/'].includes(location.pathname)) return;
  let promptInstall = null;
  let status = '';
  let registration = null;
  let installed = matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  let controls;

  function update() {
    if (!controls) return;
    const button = controls.querySelector('[data-pwa-install]');
    button.hidden = !promptInstall || installed;
    controls.querySelector('[data-pwa-status]').textContent = status;
  }

  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault(); promptInstall = event; update();
  });
  window.addEventListener('appinstalled', () => {
    installed = true; promptInstall = null;
    status = 'El asesor se instaló. Puedes abrirlo desde el icono de tu dispositivo.';
    update();
  });

  function verifyCache(worker) {
    if (!worker || !window.MessageChannel) return;
    const channel = new MessageChannel();
    const timer = setTimeout(() => channel.port1.close(), 4000);
    channel.port1.onmessage = event => {
      clearTimeout(timer); channel.port1.close();
      if (event.data?.type !== 'ASESOR_PUBLIC_CACHE_STATUS') return;
      status = event.data.ready
        ? 'El asesor ciudadano está preparado para abrir sin conexión desde su aplicación. El generador con sesión necesita internet.'
        : 'La copia sin conexión aún no está completa. Mantén internet y vuelve a abrir la aplicación ciudadana.';
      update();
    };
    worker.postMessage({ type: 'ASESOR_PUBLIC_CACHE_STATUS' }, [channel.port2]);
  }

  function observeWorker(worker) {
    if (!worker) return;
    worker.addEventListener('statechange', () => {
      if (worker.state === 'activated') verifyCache(worker);
      if (worker.state === 'installed' && registration?.active) {
        status = 'Hay una actualización lista. Guarda tu borrador y cierra todas las ventanas del asesor para usarla al volver a abrirlo.';
        update();
      }
      if (worker.state === 'redundant' && !registration?.active) {
        status = 'No se pudo preparar el uso sin conexión. Comprueba internet y el espacio disponible; también puedes descargar el archivo autónomo.';
        update();
      }
    });
  }

  async function start() {
    controls = document.getElementById('pwa-tools');
    if (!controls) {
      controls = document.createElement('section');
      controls.id = 'pwa-tools'; controls.className = 'seccion pwa-tools';
      controls.style.cssText = 'max-width:1156px;margin:48px auto;padding:24px';
      controls.setAttribute('aria-labelledby', 'pwa-title');
      controls.innerHTML = '<h2 id="pwa-title">Lleva el asesor contigo</h2><p>Instala la orientación ciudadana para abrir sus casos, formularios y guías sin conexión después de la primera carga.</p><div class="acciones"><a class="btn" href="/asesor/">Abrir aplicación ciudadana</a><button class="btn btn-primario" type="button" data-pwa-install hidden>Instalar asesor</button><a class="btn" href="#acerca/sin-internet">Descargar archivo autónomo</a></div><p data-pwa-status role="status" aria-live="polite"></p><p class="ayuda">Si no aparece el botón Instalar, busca “Añadir a pantalla de inicio” o “Instalar aplicación” en el menú de tu navegador, si ofrece esa opción. El navegador puede borrar la copia sin conexión para liberar espacio.</p>';
      const footer = document.querySelector('footer');
      if (footer) footer.before(controls); else document.body.append(controls);
    }
    controls.querySelector('[data-pwa-install]')?.addEventListener('click', async () => {
      if (!promptInstall) return;
      const prompt = promptInstall; promptInstall = null; update();
      try {
        await prompt.prompt();
        const choice = await prompt.userChoice;
        status = choice.outcome === 'accepted' ? 'Instalación aceptada. El navegador añadirá el asesor a tu dispositivo.' : 'Puedes seguir usando el asesor en esta página.';
      } catch (_) { status = 'No se pudo abrir la instalación. Prueba desde el menú de tu navegador.'; }
      update();
    });
    if (!window.isSecureContext || !('serviceWorker' in navigator)) {
      status = 'Este navegador no permite preparar la aplicación sin conexión aquí. Puedes usar la web o descargar el archivo autónomo.';
      update(); return;
    }
    status = 'Preparando los recursos públicos para usarlos sin conexión…'; update();
    try {
      registration = await navigator.serviceWorker.register('/asesor/sw.js', { scope: '/asesor/', updateViaCache: 'none' });
      observeWorker(registration.installing);
      registration.addEventListener('updatefound', () => observeWorker(registration.installing));
      if (registration.active) verifyCache(registration.active);
      if (registration.waiting) {
        status = 'Hay una actualización lista. Guarda tu borrador y cierra todas las ventanas del asesor para usarla al volver a abrirlo.';
        update();
      }
    } catch (_) {
      status = 'No se pudo preparar el uso sin conexión. Sigue usando la web o descarga el archivo autónomo.';
      update();
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
