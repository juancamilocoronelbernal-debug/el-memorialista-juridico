(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let client, config, mode = 'password', busy = false, entering = false, recovery = false;
  const labels = {
    password: ['Bienvenido a tu espacio.', 'Inicia sesión para continuar con tus documentos.', 'Entrar a mi espacio'],
    magic: ['Un enlace y estás dentro.', 'Te enviaremos un enlace de acceso de un solo uso a tu correo.', 'Enviar enlace de acceso'],
    register: ['Crea tu espacio profesional.', 'Confirma tu correo para activar tu cuenta.', 'Crear mi cuenta'],
    recover: ['Recupera el acceso.', 'Recibirás un enlace para establecer una nueva contraseña.', 'Enviar enlace de recuperación'],
    reset: ['Una nueva contraseña.', 'Elige una contraseña segura para tu cuenta.', 'Guardar contraseña y entrar']
  };

  function status(text, type = 'info') {
    $('status').hidden = !text;
    $('status').textContent = text;
    $('status').dataset.type = type;
  }
  function setMode(next) {
    if (busy) return;
    mode = next;
    const [title, subtitle, button] = labels[mode];
    $('formTitle').textContent = title;
    $('formSubtitle').textContent = subtitle;
    $('submitButton').textContent = button + ' ↗';
    const needsPassword = ['password','register','reset'].includes(mode);
    $('passwordGroup').hidden = !needsPassword;
    $('password').required = needsPassword;
    $('password').minLength = mode === 'password' ? 1 : 12;
    $('password').autocomplete = mode === 'password' ? 'current-password' : 'new-password';
    $('password').value = '';
    $('passwordHint').hidden = !['register','reset'].includes(mode);
    $('emailGroup').hidden = mode === 'reset';
    $('email').required = mode !== 'reset';
    $('nameGroup').hidden = mode !== 'register';
    $('name').required = mode === 'register';
    $('recoverButton').hidden = !['password','magic'].includes(mode);
    $('registerButton').hidden = !config?.allow_signup || !['password','magic'].includes(mode);
    $('backButton').hidden = ['password','magic','reset'].includes(mode);
    document.querySelector('.mode-tabs').hidden = !['password','magic'].includes(mode);
    document.querySelectorAll('[data-mode]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
    status('');
  }
  function setBusy(value) {
    busy = value;
    $('accessCard').setAttribute('aria-busy', String(value));
    $('loginForm').querySelectorAll('button, input').forEach(el => { el.disabled = value; });
  }
  async function enter(session) {
    if (entering || recovery) return;
    entering = true;
    setBusy(true);
    status('Validando tu sesión y preparando tu espacio…');
    try {
      await MemAuth.establish(session);
      // Los tokens de callback nunca permanecen en la dirección ni en el historial.
      const next = MemAuth.destination();
      history.replaceState(null, '', '/login');
      location.replace(next);
    } catch (error) {
      entering = false;
      status(MemAuth.message(error), 'error');
      setBusy(false);
    }
  }
  async function initialize() {
    $('retryButton').hidden = true;
    try {
      const hash = new URLSearchParams(location.hash.slice(1));
      const query = new URLSearchParams(location.search);
      recovery = query.get('mode') === 'recovery' || hash.get('type') === 'recovery';
      const callbackError = hash.get('error_description') || query.get('error_description');
      ({ client, config } = await MemAuth.init());
      client.auth.onAuthStateChange((event, session) => {
        if (event === 'PASSWORD_RECOVERY') {
          recovery = true;
          setTimeout(() => { setBusy(false); setMode('reset'); }, 0);
        } else if (event === 'SIGNED_IN' && session && !recovery) {
          setTimeout(() => enter(session), 0);
        }
      });
      const { data: { session }, error } = await client.auth.getSession();
      $('loginForm').hidden = false;
      $('accessCard').setAttribute('aria-busy', 'false');
      if (callbackError || error) {
        history.replaceState(null, '', '/login');
        setMode('magic');
        status('El enlace no es válido, ya se utilizó o ha caducado. Solicita uno nuevo.', 'error');
      } else if (recovery && session) {
        history.replaceState(null, '', '/auth/callback?mode=recovery');
        setMode('reset');
      } else if (session) {
        await enter(session);
      } else {
        setMode('password');
        if (query.get('reason') === 'expired') status('Tu sesión terminó. Inicia sesión para retomar tu trabajo.');
        if (recovery) { recovery = false; setMode('recover'); status('Solicita un enlace nuevo para cambiar tu contraseña.'); }
      }
    } catch (error) {
      $('accessCard').setAttribute('aria-busy', 'false');
      status(MemAuth.message(error), 'error');
      $('retryButton').hidden = error.code === 'not_configured';
    }
  }

  $('loginForm').addEventListener('submit', async event => {
    event.preventDefault();
    if (busy || !$('loginForm').reportValidity()) return;
    setBusy(true);
    const email = $('email').value.trim();
    const password = $('password').value;
    const callback = location.origin + '/auth/callback';
    try {
      if (mode === 'password') {
        const { data, error } = await client.auth.signInWithPassword({ email, password });
        if (error) throw error;
        await enter(data.session);
      } else if (mode === 'magic') {
        const { error } = await client.auth.signInWithOtp({ email, options: { emailRedirectTo: callback, shouldCreateUser: Boolean(config.allow_signup) } });
        if (error) throw error;
        status('Si este correo tiene acceso, recibirá un enlace. Revisa también la carpeta de correo no deseado.', 'success');
      } else if (mode === 'register') {
        const { data, error } = await client.auth.signUp({ email, password, options: { emailRedirectTo: callback, data: { nombre: $('name').value.trim() } } });
        if (error) throw error;
        if (data.session) await enter(data.session);
        else status('Revisa tu correo y confirma la cuenta con el enlace recibido. Después podrás entrar a tu espacio.', 'success');
      } else if (mode === 'recover') {
        const { error } = await client.auth.resetPasswordForEmail(email, { redirectTo: callback + '?mode=recovery' });
        if (error) throw error;
        status('Si existe una cuenta con este correo, recibirá un enlace para recuperar el acceso.', 'success');
      } else if (mode === 'reset') {
        const { error } = await client.auth.updateUser({ password });
        if (error) throw error;
        recovery = false;
        const { data: { session } } = await client.auth.getSession();
        await enter(session);
      }
    } catch (error) {
      status(MemAuth.message(error), 'error');
    } finally {
      if (!entering) setBusy(false);
    }
  });
  document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => setMode(button.dataset.mode)));
  $('recoverButton').addEventListener('click', () => setMode('recover'));
  $('registerButton').addEventListener('click', () => setMode('register'));
  $('backButton').addEventListener('click', () => setMode('password'));
  $('retryButton').addEventListener('click', initialize);
  $('togglePassword').addEventListener('click', () => {
    const visible = $('password').type === 'password';
    $('password').type = visible ? 'text' : 'password';
    $('togglePassword').textContent = visible ? 'Ocultar' : 'Mostrar';
    $('togglePassword').setAttribute('aria-label', visible ? 'Ocultar contraseña' : 'Mostrar contraseña');
    $('togglePassword').setAttribute('aria-pressed', String(visible));
  });
  window.addEventListener('pageshow', event => { if (event.persisted) location.reload(); });
  initialize();
})();
