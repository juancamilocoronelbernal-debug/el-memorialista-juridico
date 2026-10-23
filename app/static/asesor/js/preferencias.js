/* preferencias.js — Aplica el tema, el tamaño de letra y el contraste elegidos
   ANTES de pintar la página (evita el parpadeo). Se carga en el <head>. */
(function () {
  try {
    var raiz = document.documentElement;
    var tema = JSON.parse(localStorage.getItem('aj_tema') || '""');
    if (tema === 'dark' || tema === 'light') raiz.setAttribute('data-theme', tema);
    var a = JSON.parse(localStorage.getItem('aj_accesibilidad') || 'null');
    if (a && typeof a === 'object' && !Array.isArray(a)) {
      var escalas = [1, 1.12, 1.25, 1.4];
      var i = Number.isInteger(a.escala) ? Math.max(0, Math.min(escalas.length - 1, a.escala)) : 0;
      raiz.style.setProperty('--escala', String(escalas[i]));
      if (a.contraste === true) raiz.setAttribute('data-contraste', 'alto');
    }
  } catch (e) { /* sin almacenamiento: valores por defecto */ }
})();
