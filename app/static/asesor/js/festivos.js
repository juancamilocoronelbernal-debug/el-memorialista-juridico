/* ============================================================
   festivos.js — Calendario de festivos de Colombia y cálculo de
   plazos en días hábiles (Ley 51 de 1983, "Ley Emiliani").
   ============================================================ */
window.AJ = window.AJ || {};

AJ.festivos = (function () {
  const cache = {};

  // Domingo de Pascua (algoritmo de Meeus/Jones/Butcher, calendario gregoriano)
  function pascua(y) {
    const a = y % 19, b = Math.floor(y / 100), c = y % 100;
    const d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25);
    const g = Math.floor((b - f + 1) / 3);
    const h = (19 * a + b - d - g + 15) % 30;
    const i = Math.floor(c / 4), k = c % 4;
    const l = (32 + 2 * e + 2 * i - h - k) % 7;
    const m = Math.floor((a + 11 * h + 22 * l) / 451);
    const mes = Math.floor((h + l - 7 * m + 114) / 31);
    const dia = ((h + l - 7 * m + 114) % 31) + 1;
    return new Date(y, mes - 1, dia);
  }

  function sumarDias(fecha, n) {
    const r = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
    r.setDate(r.getDate() + n);
    return r;
  }

  // Traslado al lunes siguiente cuando el festivo no cae en lunes (Ley Emiliani)
  function lunesSiguiente(fecha) {
    const dow = fecha.getDay();
    return dow === 1 ? fecha : sumarDias(fecha, (8 - dow) % 7);
  }

  function clave(fecha) {
    const m = String(fecha.getMonth() + 1).padStart(2, '0');
    const d = String(fecha.getDate()).padStart(2, '0');
    return `${fecha.getFullYear()}-${m}-${d}`;
  }

  function listaAnio(y) {
    if (cache[y]) return cache[y];
    const P = pascua(y);
    const fijos = [
      [0, 1, 'Año Nuevo'], [4, 1, 'Día del Trabajo'], [6, 20, 'Día de la Independencia'],
      [7, 7, 'Batalla de Boyacá'], [11, 8, 'Inmaculada Concepción'], [11, 25, 'Navidad']
    ];
    const trasladables = [
      [0, 6, 'Reyes Magos'], [2, 19, 'San José'], [5, 29, 'San Pedro y San Pablo'],
      [7, 15, 'Asunción de la Virgen'], [9, 12, 'Día de la Raza'], [10, 1, 'Todos los Santos'],
      [10, 11, 'Independencia de Cartagena']
    ];
    const lista = [];
    fijos.forEach(([m, d, n]) => lista.push({ fecha: new Date(y, m, d), nombre: n }));
    trasladables.forEach(([m, d, n]) => lista.push({ fecha: lunesSiguiente(new Date(y, m, d)), nombre: n }));
    lista.push({ fecha: sumarDias(P, -3), nombre: 'Jueves Santo' });
    lista.push({ fecha: sumarDias(P, -2), nombre: 'Viernes Santo' });
    lista.push({ fecha: sumarDias(P, 43), nombre: 'Ascensión del Señor' });
    lista.push({ fecha: sumarDias(P, 64), nombre: 'Corpus Christi' });
    lista.push({ fecha: sumarDias(P, 71), nombre: 'Sagrado Corazón' });
    lista.sort((a, b) => a.fecha - b.fecha);
    const mapa = {};
    lista.forEach(f => { mapa[clave(f.fecha)] = f.nombre; });
    cache[y] = { lista, mapa };
    return cache[y];
  }

  function nombreFestivo(fecha) {
    return listaAnio(fecha.getFullYear()).mapa[clave(fecha)] || null;
  }

  function esFestivo(fecha) { return !!nombreFestivo(fecha); }

  function esHabil(fecha) {
    const dow = fecha.getDay();
    return dow !== 0 && dow !== 6 && !esFestivo(fecha);
  }

  // Suma n días hábiles contados a partir del día siguiente a "desde"
  function sumarDiasHabiles(desde, n) {
    let f = new Date(desde.getFullYear(), desde.getMonth(), desde.getDate());
    let c = 0;
    while (c < n) {
      f = sumarDias(f, 1);
      if (esHabil(f)) c++;
    }
    return f;
  }

  function sumarMeses(desde, n) {
    const r = new Date(desde.getFullYear(), desde.getMonth(), desde.getDate());
    const dia = r.getDate();
    r.setMonth(r.getMonth() + n);
    if (r.getDate() !== dia) r.setDate(0); // fin de mes si el día no existe
    return r;
  }

  function diasHabilesEntre(desde, hasta) {
    let f = new Date(desde.getFullYear(), desde.getMonth(), desde.getDate());
    let c = 0;
    while (f < hasta) {
      f = sumarDias(f, 1);
      if (esHabil(f)) c++;
    }
    return c;
  }

  function parseISO(s) {
    if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
    const [y, m, d] = s.split('-').map(Number);
    if (y < 1900 || y > 2100 || m < 1 || m > 12 || d < 1 || d > 31) return null;
    const date = new Date(y, m - 1, d);
    return date.getFullYear() === y && date.getMonth() === m - 1 && date.getDate() === d ? date : null;
  }

  return { pascua, listaAnio, esFestivo, esHabil, nombreFestivo, sumarDias, sumarDiasHabiles, sumarMeses, diasHabilesEntre, parseISO, clave };
})();
