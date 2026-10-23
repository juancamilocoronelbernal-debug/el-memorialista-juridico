/* Sesiones del área profesional. La autorización real siempre reside en la API. */
(() => {
  'use strict';
  let initialization;
  async function init() {
    if (!initialization) initialization = (async () => {
      const response = await fetch('/api/auth/config', { cache: 'no-store', credentials: 'same-origin' });
      if (!response.ok) throw new Error('No pudimos comprobar el servicio de acceso. Inténtalo de nuevo.');
      const config = await response.json();
      if (!config.configurado || !config.supabase_url || !config.supabase_anon_key) {
        const error = new Error('El acceso profesional todavía no está habilitado. Puedes seguir utilizando el asesor ciudadano.');
        error.code = 'not_configured';
        throw error;
      }
      if (!window.supabase?.createClient) throw new Error('No se pudo cargar el servicio de acceso. Recarga la página.');
      const client = window.supabase.createClient(config.supabase_url, config.supabase_anon_key, {
        auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: 'implicit' }
      });
      return { config, client };
    })().catch(error => { initialization = null; throw error; });
    return initialization;
  }

  async function establish(session) {
    if (!session?.access_token) throw new Error('Tu sesión ha caducado. Inicia sesión de nuevo.');
    const response = await fetch('/api/auth/sesion', {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Authorization: 'Bearer ' + session.access_token }
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const error = new Error(typeof body.detail === 'string' ? body.detail : 'No pudimos validar tu sesión. Vuelve a iniciar sesión.');
      error.status = response.status;
      throw error;
    }
    return response.json();
  }

  async function clearCookie() {
    const response = await fetch('/api/auth/sesion', {
      method: 'DELETE', credentials: 'same-origin', cache: 'no-store'
    });
    if (!response.ok) throw new Error('No se pudo cerrar la sesión del servidor. Comprueba tu conexión y reintenta.');
  }

  function destination() {
    // Una lista cerrada impide redirecciones abiertas o salir del área profesional.
    const requested = new URLSearchParams(location.search).get('next');
    return requested === '/generador' ? '/generador' : '/app';
  }

  function message(error) {
    const code = String(error?.code || '');
    if (code === 'invalid_credentials') return 'El correo o la contraseña no coinciden. Revisa los datos o solicita un enlace de acceso.';
    if (code === 'email_not_confirmed') return 'Confirma tu correo con el enlace que recibiste antes de entrar.';
    if (code.includes('rate_limit') || error?.status === 429) return 'Has realizado varios intentos. Espera unos minutos antes de volver a intentarlo.';
    if (code === 'signup_disabled') return 'El registro está cerrado. Solicita una invitación al administrador.';
    if (code === 'otp_expired' || code === 'bad_code_verifier') return 'Este enlace caducó o ya se utilizó. Solicita uno nuevo.';
    if (code === 'weak_password') return 'Elige una contraseña más segura y diferente de tus datos personales.';
    if (/fetch|network/i.test(String(error?.message))) return 'No hay conexión con el servicio. Revisa tu conexión y vuelve a intentarlo.';
    return error?.message || 'No se pudo completar la operación. Inténtalo de nuevo.';
  }

  window.MemAuth = Object.freeze({ init, establish, clearCookie, destination, message });
})();
