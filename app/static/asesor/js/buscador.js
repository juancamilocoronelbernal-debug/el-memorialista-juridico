/* ============================================================
   buscador.js — Encuentra el caso aunque la persona escriba con
   errores ("tutla", "pencion", "datacredito"), sin tildes o con
   sus propias palabras ("me cortaron la luz").
   Todo se calcula en el navegador.
   ============================================================ */
window.AJ = window.AJ || {};

AJ.buscador = (function () {
  'use strict';

  const VACIAS = new Set(['que', 'con', 'para', 'por', 'una', 'uno', 'unos', 'unas', 'los', 'las', 'del', 'mis', 'sus', 'tengo', 'quiero', 'necesito', 'como', 'hacer', 'poner', 'puedo', 'ayuda', 'ayudar', 'porque', 'pero', 'desde', 'hace', 'esta', 'este', 'esto', 'estos', 'estas', 'eso', 'ese', 'esa', 'muy', 'mas', 'tan', 'sin', 'sobre', 'cuando', 'donde', 'cual', 'quien', 'nos', 'les', 'ellos', 'ella', 'ellas', 'entre', 'hasta', 'todo', 'toda', 'todos', 'nada', 'algo', 'otra', 'otro', 'favor', 'hola', 'buenas', 'buenos', 'dias', 'tardes', 'senor', 'senora', 'mucho', 'poco', 'tambien', 'solo', 'aun', 'ya', 'han', 'hay', 'fue', 'ser', 'son', 'era', 'estoy', 'esta', 'estan', 'tiene', 'tienen', 'dice', 'dicen', 'dijo', 'dijeron', 'mio', 'mia', 'tuyo', 'cuanto', 'cuanta', 'asi', 'pues', 'entonces', 'algun', 'alguna', 'alguien', 'dar', 'doy', 'dan', 'hago', 'hizo', 'quisiera', 'gustaria', 'saber', 'sabe']);

  function normalizar(s) {
    return String(s == null ? '' : s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
  }
  function tokens(s) {
    return normalizar(s).split(' ').filter(t => t.length > 2 && !VACIAS.has(t));
  }

  /* Distancia de edición (con transposición), cortando apenas supera el máximo */
  function distancia(a, b, max) {
    if (a === b) return 0;
    if (Math.abs(a.length - b.length) > max) return max + 1;
    let prev2 = null, prev = Array.from({ length: b.length + 1 }, (_, j) => j);
    for (let i = 1; i <= a.length; i++) {
      const cur = [i];
      let minimo = i;
      for (let j = 1; j <= b.length; j++) {
        const costo = a[i - 1] === b[j - 1] ? 0 : 1;
        let v = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + costo);
        if (prev2 && i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) v = Math.min(v, prev2[j - 2] + 1);
        cur.push(v);
        if (v < minimo) minimo = v;
      }
      if (minimo > max) return max + 1;
      prev2 = prev; prev = cur;
    }
    return prev[b.length];
  }

  let indice = null;
  let fuente = null;

  /* Índice por caso: palabras del título, de todo el texto y frases cotidianas */
  function construir(casos, tipos, entidades, sinonimos) {
    fuente = casos;
    tipos = tipos || {};
    indice = (casos || []).filter(c => !c.retirado).map(c => {
      const sin = (sinonimos && sinonimos[c.id]) || [];
      const categoria = entidades && entidades.categoria ? entidades.categoria(c.categoria) : null;
      const textos = [c.titulo, c.resumen, (c.palabras || []).join(' '), sin.join(' '), tipos[c.tipo] ? tipos[c.tipo].nombre : '', categoria ? categoria.nombre : ''];
      const tit = new Set(tokens(c.titulo));
      const todo = new Set(textos.flatMap(t => tokens(t)));
      const frases = [...(c.palabras || []), ...sin].map(normalizar).filter(f => f.includes(' ') && f.length > 5);
      return { c, tit, todo, lista: [...todo], frases, titulo: normalizar(c.titulo) };
    });
    return indice;
  }

  function puntuar(item, terminos, frase) {
    let puntos = 0, aciertos = 0;
    terminos.forEach(t => {
      let p = 0;
      if (item.tit.has(t)) p = 3;
      else if (item.todo.has(t)) p = 2;
      else {
        // Prefijos: "reportaron" ~ "reportado", "cortaron" ~ "corte", "pension" ~ "pensiones"
        if (t.length >= 4) {
          for (const w of item.lista) {
            if ((w.length >= 4 && (w.startsWith(t) || t.startsWith(w))) || (t.length >= 6 && w.length >= 6 && w.slice(0, 5) === t.slice(0, 5))) { p = 1.5; break; }
          }
        }
        // Errores de escritura: "tutla", "pencion", "eps" mal escrito, letras cambiadas
        if (!p && t.length >= 4) {
          const max = t.length >= 8 ? 2 : 1;
          for (const w of item.lista) {
            if (w.length >= 4 && distancia(t, w, max) <= max) { p = item.tit.has(w) ? 1.5 : 1; break; }
          }
        }
      }
      if (p) aciertos++;
      puntos += p;
    });
    if (!aciertos) return 0;
    // Frases cotidianas completas ("me cortaron la luz", "no me dan la cita")
    if (frase) item.frases.forEach(f => { if (frase.includes(f)) puntos += 3; });
    if (frase && frase.length > 4 && item.titulo.includes(frase)) puntos += 4;
    // Premia que coincidan casi todas las palabras escritas
    puntos += 2 * (aciertos / terminos.length);
    return puntos;
  }

  /** Devuelve los casos ordenados por pertinencia. opciones: { tipo, categoria, modulo, limite } */
  function buscar(q, opciones) {
    opciones = opciones || {};
    q = String(q == null ? '' : q).slice(0, 500);
    if (!indice || fuente !== AJ.casos) construir(AJ.casos, AJ.tipos, AJ.entidades, AJ.sinonimos);
    const terminos = [...new Set(tokens(q))].slice(0, 40);
    const frase = normalizar(q);
    const res = [];
    indice.forEach(item => {
      const c = item.c;
      if (c.retirado) return;
      if (opciones.tipo && c.tipo !== opciones.tipo) return;
      if (opciones.modulo && c.modulo !== opciones.modulo) return;
      if (opciones.categoria && c.categoria !== opciones.categoria) return;
      if (!terminos.length) { res.push({ c, puntos: 0 }); return; }
      const puntos = puntuar(item, terminos, frase);
      if (puntos > 0) res.push({ c, puntos });
    });
    if (terminos.length) {
      res.sort((a, b) => b.puntos - a.puntos);
      // Quita resultados muy débiles cuando hay buenos candidatos
      const mejor = res.length ? res[0].puntos : 0;
      const filtrados = res.filter(r => r.puntos >= Math.min(2, mejor * 0.25));
      return (opciones.limite ? filtrados.slice(0, opciones.limite) : filtrados).map(r => r.c);
    }
    return (opciones.limite > 0 ? res.slice(0, Math.floor(opciones.limite)) : res).map(r => r.c);
  }

  return { normalizar, tokens, distancia, construir, buscar };
})();
