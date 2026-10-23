"""Migración histórica anterior a v3; no ejecutar sobre la arquitectura actual.

El código se conserva como referencia de la evolución del generador. Reaplicarlo
puede reintroducir lógica antigua y romper autenticación, catálogo o auditoría.
Los cambios actuales se hacen directamente en app/private/generador.html.
"""
import re

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = PROJECT_ROOT / "app" / "private" / "generador.html"

# Guardia previa a toda lectura/modificación: esta migración no es compatible
# con el generador privado ni con la portada ciudadana de v3. Sin bypass.
if INDEX_PATH.is_file() or (PROJECT_ROOT / "app" / "static" / "asesor").is_dir():
    raise SystemExit(
        "Migración histórica bloqueada: El Memorialista v3 ya separa asesor y "
        "generador privado. No reapliques código anterior. Edita "
        "app/private/generador.html y sus servicios de sesión directamente."
    )
if not INDEX_PATH.is_file():
    raise SystemExit("No existe un destino compatible para esta migración histórica.")

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Agregar estilos CSS para citas verificadas
css_target = ".vchip:focus-visible{outline:2px solid var(--sello);outline-offset:1px}"
css_addition = """.vchip:focus-visible{outline:2px solid var(--sello);outline-offset:1px}
.vchip.verde{background:#dcfce7;color:#166534}
.vchip.amarillo{background:#fef9c3;color:#854d0e}
.vchip.rojo{background:#fee2e2;color:#991b1b}
.cita-badge{display:inline-flex;align-items:center;gap:4px;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:700}
.cita-badge.verde{background:#dcfce7;color:#166534}
.cita-badge.amarillo{background:#fef9c3;color:#854d0e}
.cita-badge.rojo{background:#fee2e2;color:#991b1b}"""

if css_target in content:
    content = content.replace(css_target, css_addition)

# 2. Actualizar state para incluir citasVerificadas
state_target = "catalogoAbierto: true,\n};"
state_replacement = """catalogoAbierto: true,
  citasVerificadas: [],
  verificandoCitas: false,
};"""
if state_target in content:
    content = content.replace(state_target, state_replacement)

# 3. Actualizar grupoRedaccion para tener 'verificables' por defecto
gr_target = "{ k: '_juris', l: 'Jurisprudencia', t: 'select', opciones: [['concisa', 'Concisa']"
# Revisar cómo está en index.html
old_juris = "{ k: '_juris', l: 'Jurisprudencia', t: 'select', opciones: [['sugerir', 'Sugerir sentencias, marcadas para verificar'], ['usuario', 'Solo la que yo indique'], ['ninguna', 'No citar jurisprudencia']] }"
new_juris = "{ k: '_juris', l: 'Jurisprudencia', t: 'select', opciones: [['verificables', 'Solo citas verificables'], ['sugerir', 'Sugerir sentencias, marcadas para verificar'], ['usuario', 'Solo la que yo indique'], ['ninguna', 'No citar jurisprudencia']] }"
if old_juris in content:
    content = content.replace(old_juris, new_juris)

old_def_juris = "if (cl.k === '_juris') cl.def = (tipo && tipo.juris) || 'sugerir';"
new_def_juris = "if (cl.k === '_juris') cl.def = (tipo && tipo.juris) || 'verificables';"
if old_def_juris in content:
    content = content.replace(old_def_juris, new_def_juris)

# 4. Reemplazar la sección de Verificación (recogerMarcas, actualizarVerificacion, pintarPanel, etc.)
verif_section_start = "/* =========================================================\n   Verificación: datos por completar y citas por verificar\n   ========================================================= */"
verif_section_end = "/* =========================================================\n   Word (.docx): XML de WordprocessingML\n   ========================================================= */"

idx1 = content.find(verif_section_start)
idx2 = content.find(verif_section_end)

if idx1 == -1 or idx2 == -1:
    raise RuntimeError("No se encontraron los delimitadores de la sección de verificación")

new_verif_code = """/* =========================================================
   Verificación: datos por completar y citas por verificar
   ========================================================= */
let panelAbierto = false;

function recogerMarcas() {
  const cuerpo = $('#cuerpo');
  const items = [];
  const walker = document.createTreeWalker(cuerpo, NodeFilter.SHOW_TEXT);
  const re = /\\[(COMPLETAR|VERIFICAR)(?::\\s*([^\\]]*))?\\]/g;
  let n;
  while ((n = walker.nextNode())) {
    let m; re.lastIndex = 0;
    while ((m = re.exec(n.nodeValue))) {
      const bloque = n.parentElement.closest('#cuerpo > *');
      const previo = textoPrevio(bloque, n, m.index);
      items.push({ tipo: m[1] === 'COMPLETAR' ? 'c' : 'v', detalle: (m[2] || '').trim(), nodo: n, off: m.index, bloque, previo });
    }
  }
  return items;
}

function textoPrevio(bloque, nodo, off) {
  if (!bloque) return '';
  const r = document.createRange();
  r.setStart(bloque, 0);
  try { r.setEnd(nodo, off); } catch { return ''; }
  return r.toString().replace(/\\[(?:COMPLETAR|VERIFICAR)[^\\]]*\\]/g, '').replace(/\\s+/g, ' ').trim();
}

async function verificarCitasDocumento() {
  if (state.ejemplo || state.generando || !state.texto || state.verificandoCitas) return;
  state.verificandoCitas = true;
  actualizarVerificacion();
  try {
    const res = await apiFetch('/api/verificar-citas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto: state.texto })
    });
    if (!res.ok) throw new Error('Error al verificar citas');
    const data = await res.json();
    state.citasVerificadas = data.citas || [];

    // Requerimiento 6: Si la opción es "Solo citas verificables", marca con [VERIFICAR] las citas en rojo
    const citasRojas = state.citasVerificadas.filter(c => c.color === 'rojo');
    if (citasRojas.length && (state.datos._juris === 'verificables' || !state.datos._juris)) {
      let modificado = state.texto;
      let huboCambio = false;
      for (const cr of citasRojas) {
        const orig = cr.texto_original;
        if (orig && modificado.includes(orig) && !modificado.includes(orig + ' [VERIFICAR]')) {
          modificado = modificado.replaceAll(orig, orig + ' [VERIFICAR]');
          huboCambio = true;
        }
      }
      if (huboCambio) {
        state.texto = modificado;
        renderHoja();
        guardarBorrador();
      }
    }
  } catch (err) {
    console.error('Error al verificar citas:', err);
  } finally {
    state.verificandoCitas = false;
    actualizarVerificacion();
  }
}

function actualizarVerificacion() {
  const verif = $('#verif'), panel = $('#panelVerif');
  if (state.ejemplo || state.generando || !state.texto) { verif.hidden = true; panel.hidden = true; return; }
  const items = recogerMarcas();
  const nc = items.filter(i => i.tipo === 'c').length, nv = items.filter(i => i.tipo === 'v').length;
  verif.replaceChildren();

  if (state.verificandoCitas) {
    verif.append(h('span', { class: 'vchip amarillo' }, '⏳ Verificando citas en fuentes oficiales…'));
  } else if (state.citasVerificadas && state.citasVerificadas.length) {
    const nVerdes = state.citasVerificadas.filter(c => c.color === 'verde').length;
    const nAmarillas = state.citasVerificadas.filter(c => c.color === 'amarillo').length;
    const nRojas = state.citasVerificadas.filter(c => c.color === 'rojo').length;

    if (nRojas) verif.append(h('button', { class: 'vchip rojo', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, `✗ ${nRojas} ${nRojas === 1 ? 'cita no encontrada' : 'citas no encontradas'}`));
    if (nAmarillas) verif.append(h('button', { class: 'vchip amarillo', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, `⚠ ${nAmarillas} ${nAmarillas === 1 ? 'cita por verificar' : 'citas por verificar'}`));
    if (nVerdes) verif.append(h('button', { class: 'vchip verde', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, `✓ ${nVerdes} ${nVerdes === 1 ? 'cita verificada' : 'citas verificadas'}`));
  }

  if (nc) verif.append(h('button', { class: 'vchip c', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, `${nc} ${nc === 1 ? 'dato' : 'datos'} por completar`));
  if (nv && (!state.citasVerificadas || !state.citasVerificadas.length)) verif.append(h('button', { class: 'vchip v', type: 'button', 'aria-expanded': String(panelAbierto), onclick: alternarPanel }, `${nv} ${nv === 1 ? 'cita' : 'citas'} por verificar`));

  if (!verif.children.length) verif.append(h('span', { class: 'vchip ok' }, '✓ Sin datos pendientes'));
  verif.hidden = false;
  if (panelAbierto) pintarPanel(items); else panel.hidden = true;
}

function alternarPanel() { panelAbierto = !panelAbierto; actualizarVerificacion(); }

function pintarPanel(items) {
  const panel = $('#panelVerif');
  panel.replaceChildren();

  // 1. Citas verificadas oficialmente
  if (state.citasVerificadas && state.citasVerificadas.length) {
    panel.append(h('h3', {}, 'Citas y jurisprudencia verificadas'));
    const ol = h('ol', { style: 'padding-left: 20px; margin-bottom: 16px;' });
    state.citasVerificadas.forEach(c => {
      const li = h('li', { style: 'margin-bottom: 10px; line-height: 1.4;' });
      const badgeClase = c.color === 'verde' ? 'verde' : c.color === 'rojo' ? 'rojo' : 'amarillo';
      const badgeTexto = c.color === 'verde' ? '✓ Existe y respalda' : c.color === 'rojo' ? '✗ No encontrada' : '⚠ Respaldo parcial / sin verificar';
      li.append(
        h('div', { style: 'display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 3px;' },
          h('strong', {}, c.nombre || c.texto_original),
          h('span', { class: `cita-badge ${badgeClase}` }, badgeTexto)
        )
      );
      if (c.url) {
        li.append(h('div', { style: 'font-size: 12px; margin-bottom: 2px;' },
          h('a', { href: c.url, target: '_blank', rel: 'noopener noreferrer', style: 'color: var(--azul, #2563eb); text-decoration: underline;' }, 'Ver documento oficial ↗')
        ));
      }
      if (c.pertinencia && c.pertinencia.fragmento) {
        li.append(h('div', { class: 'ctx', style: 'font-size: 12px; color: var(--color-texto-suave, #555); font-style: italic; background: rgba(0,0,0,0.03); padding: 4px 6px; border-radius: 4px; margin-top: 2px;' },
          `«${c.pertinencia.fragmento}»`
        ));
      }
      ol.append(li);
    });
    panel.append(ol);
  }

  // 2. Datos por completar
  const datosComp = items.filter(i => i.tipo === 'c');
  if (datosComp.length) {
    panel.append(h('h3', {}, 'Datos por completar'));
    const ol = h('ol', { style: 'padding-left: 20px;' });
    datosComp.forEach(it => {
      const li = h('li', { style: 'margin-bottom: 6px;' });
      li.append(h('strong', {}, it.detalle || 'Dato faltante'));
      li.append(h('span', { class: 'acc', style: 'margin-left: 8px;' }, h('button', { class: 'enlace', type: 'button', onclick: () => irAMarca(it) }, 'Ver en el texto')));
      if (it.previo) li.append(h('div', { class: 'ctx', style: 'font-size: 12px; color: #666;' }, '…' + it.previo.slice(-80)));
      ol.append(li);
    });
    panel.append(ol);
  }

  panel.append(h('p', { class: 'nota', style: 'margin-top: 12px; font-size: 12px; color: #666;' }, 'Las citas en verde cuentan con registro oficial verificado en la relatoría o base de leyes. Las citas en rojo no fueron halladas y deben corregirse o eliminarse antes de radicar.'));
  panel.hidden = false;
}

function irAMarca(it) {
  const el = it.bloque || it.nodo.parentElement;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.classList.remove('destello'); void el.offsetWidth; el.classList.add('destello');
  try {
    const r = document.createRange(); r.setStart(it.nodo, it.off); r.setEnd(it.nodo, Math.min(it.nodo.length, it.off + 11));
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  } catch { /* nodo cambió */ }
}

"""

content = content[:idx1] + new_verif_code + content[idx2:]

# 5. En terminarRedaccion(), disparar la verificación de citas
term_target = "guardarEnHistorial().then(ok => {"
term_replacement = """verificarCitasDocumento();
  guardarEnHistorial().then(ok => {"""
if term_target in content:
    content = content.replace(term_target, term_replacement)

# 6. En pedirExportacion(), pedir confirmación si hay citas en rojo
export_target = """function pedirExportacion(tipo) {
  sincronizarTexto();
  const marcas = recogerMarcas();
  const nv = marcas.filter(i => i.tipo === 'v').length, nc = marcas.filter(i => i.tipo === 'c').length;
  if (!nv && !nc) { exportar(tipo, false); return; }
  const caja = $('#panelVerif');
  caja.replaceChildren(
    h('h3', {}, tipo === 'docx' ? 'Antes de exportar a Word' : 'Antes de exportar a PDF'),
    nc ? h('p', { class: 'nota' }, `Quedan ${nc} ${nc === 1 ? 'dato' : 'datos'} por completar; saldrán resaltados en amarillo en el archivo.`) : null,
    nv ? h('p', { class: 'nota' }, `Hay ${nv} ${nv === 1 ? 'cita marcada' : 'citas marcadas'} con [VERIFICAR].`) : null,
    h('div', { class: 'ajuste-fila' },
      nv ? h('button', { class: 'btn primario chico', type: 'button', onclick: () => { caja.hidden = true; exportar(tipo, true); } }, 'Ya las verifiqué: exportar sin marcas') : null,
      h('button', { class: 'btn chico', type: 'button', onclick: () => { caja.hidden = true; exportar(tipo, false); } }, nv ? 'Exportar con las marcas' : 'Exportar'),
      h('button', { class: 'btn chico fantasma', type: 'button', onclick: () => { caja.hidden = true; actualizarVerificacion(); } }, 'Cancelar')));
  caja.hidden = false;
}"""

export_replacement = """function pedirExportacion(tipo) {
  sincronizarTexto();
  const marcas = recogerMarcas();
  const nv = marcas.filter(i => i.tipo === 'v').length, nc = marcas.filter(i => i.tipo === 'c').length;
  const citasRojas = (state.citasVerificadas || []).filter(c => c.color === 'rojo');

  if (!nv && !nc && !citasRojas.length) { exportar(tipo, false); return; }

  const caja = $('#panelVerif');
  const contenido = [];
  contenido.push(h('h3', {}, tipo === 'docx' ? 'Antes de exportar a Word' : 'Antes de exportar a PDF'));

  if (citasRojas.length) {
    contenido.push(h('div', { style: 'background: #fef2f2; border: 1px solid #f87171; border-radius: 6px; padding: 10px; margin-bottom: 10px;' },
      h('p', { style: 'color: #991b1b; font-weight: 600; margin: 0 0 6px 0;' }, `⚠️ Advertencia: Hay ${citasRojas.length} ${citasRojas.length === 1 ? 'cita no encontrada' : 'citas no encontradas'} en las fuentes oficiales:`),
      h('ul', { style: 'margin: 0; padding-left: 18px; color: #b91c1c; font-size: 13px;' },
        citasRojas.map(cr => h('li', {}, cr.nombre || cr.texto_original))
      ),
      h('p', { style: 'margin: 6px 0 0 0; color: #7f1d1d; font-size: 12px;' }, 'Exportar con citas inexistentes puede acarrear sanciones disciplinarias o el rechazo de pretensiones. ¿Deseas exportar de todos modos?')
    ));
  }

  if (nc) contenido.push(h('p', { class: 'nota' }, `Quedan ${nc} ${nc === 1 ? 'dato' : 'datos'} por completar; saldrán resaltados en amarillo en el archivo.`));
  if (nv && !citasRojas.length) contenido.push(h('p', { class: 'nota' }, `Hay ${nv} ${nv === 1 ? 'cita marcada' : 'citas marcadas'} con [VERIFICAR].`));

  contenido.push(h('div', { class: 'ajuste-fila' },
    h('button', { class: 'btn primario chico', type: 'button', onclick: () => { caja.hidden = true; exportar(tipo, false); } }, citasRojas.length ? 'Confirmar y exportar de todos modos' : (nv ? 'Exportar con las marcas' : 'Exportar')),
    h('button', { class: 'btn chico fantasma', type: 'button', onclick: () => { caja.hidden = true; alternarPanel(); } }, 'Cancelar y revisar citas')
  ));

  caja.replaceChildren(...contenido);
  caja.hidden = false;
}"""

if export_target in content:
    content = content.replace(export_target, export_replacement)
else:
    raise RuntimeError("No se encontró export_target en content")

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("Migración histórica del verificador aplicada al generador privado.")
