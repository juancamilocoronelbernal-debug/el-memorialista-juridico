"""Aplica las modificaciones al frontend index.html para soportar el catálogo dinámico y el envío de datos."""
import os

INDEX_PATH = "/Users/juan/.gemini/antigravity/scratch/el-memorialista-app/app/static/index.html"

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Reemplazar catálogo embebido (desde Catálogo de escritos hasta antes de EJEMPLO_TEXTO)
s_start = "/* =========================================================\n   Catálogo de escritos\n   ========================================================= */"
s_end = "/* Escrito de ejemplo para la primera vista */"

idx1 = content.find(s_start)
idx2 = content.find(s_end)

if idx1 == -1 or idx2 == -1:
    raise RuntimeError("No se encontraron los delimitadores del catálogo")

nuevo_catalogo = """/* =========================================================
   Catálogo de escritos (servidor v2.2.1)
   ========================================================= */
let TIPOS_LISTA = [];
let TIPOS = {};
let AREAS = [];

function grupoRedaccion(tipo) {
  const gr = (state.catalogo && state.catalogo.grupo_redaccion) || {};
  const baseCampos = gr.campos || [
    { k: 'fundamentos', l: 'Normas o jurisprudencia que quieres citar', t: 'area', rows: 2, ph: 'Opcional. Ej.: Sentencia T-760 de 2008; art. 49 de la Constitución.' },
    { k: '_extension', l: 'Extensión', t: 'select', opciones: [['concisa', 'Concisa'], ['estandar', 'Estándar'], ['extensa', 'Extensa y exhaustiva']] },
    { k: '_juris', l: 'Jurisprudencia', t: 'select', opciones: [['sugerir', 'Sugerir sentencias, marcadas para verificar'], ['usuario', 'Solo la que yo indique'], ['ninguna', 'No citar jurisprudencia']] },
    { k: '_firma', l: 'Quién firma', t: 'select', opciones: [['apoderado', 'Yo, como apoderado(a)'], ['propio', 'Yo, en nombre propio'], ['cliente', 'Mi cliente, en nombre propio']] },
    { k: '_membrete', l: 'Incluir mi membrete en este escrito', t: 'check', def: true },
    { k: '_notas', l: 'Indicaciones adicionales', t: 'area', rows: 2, ph: 'Ej.: Enfatiza que la accionante es adulta mayor; no menciones el nombre del médico.' },
  ];
  const campos = [];
  for (const c of baseCampos) {
    if (c.k === '_firma' && tipo && tipo.firma === 'poder') continue;
    const cl = { ...c };
    if (cl.k === '_extension') cl.def = (tipo && tipo.breve) ? 'concisa' : '@extension';
    if (cl.k === '_juris') cl.def = (tipo && tipo.juris) || 'sugerir';
    if (cl.k === '_firma') cl.def = (tipo && tipo.firma) || 'apoderado';
    campos.push(cl);
  }
  return { n: (gr && gr.nombre_grupo) || 'Redacción', campos };
}

"""

content = content[:idx1] + nuevo_catalogo + content[idx2:]

# 2. Reemplazar construcción de prompt en el cliente
p_start = "/* =========================================================\n   Redacción con Claude\n   ========================================================= */"
p_end = "let reloj = null, relojBase = '';"

idx_p1 = content.find(p_start)
idx_p2 = content.find(p_end)

if idx_p1 == -1 or idx_p2 == -1:
    raise RuntimeError("No se encontraron los delimitadores de redacción con Claude")

nuevo_redaccion_bloque = """/* =========================================================
   Redacción con IA (servidor v2.2.1)
   ========================================================= */
function camposTipo(tipo) {
  if (!tipo) return [];
  return [...(tipo.grupos || []).flatMap(g => g.campos || []), ...grupoRedaccion(tipo).campos];
}

"""

content = content[:idx_p1] + nuevo_redaccion_bloque + content[idx_p2:]

# 3. Reemplazar en redactar() el uso de construirPrompt() y el body del POST
redactar_old = """  if (modo === 'ajuste') {
    state.prevTexto = state.texto;
    textoPrevio = state.texto;
    if (!state.prompt) state.prompt = construirPrompt();
  } else {
    if (modo === 'regenerar' && state.texto) state.prevTexto = state.texto;
    state.prompt = construirPrompt();
  }"""

redactar_new = """  if (modo === 'ajuste') {
    state.prevTexto = state.texto;
    textoPrevio = state.texto;
  } else {
    if (modo === 'regenerar' && state.texto) state.prevTexto = state.texto;
  }"""

if redactar_old not in content:
    raise RuntimeError("No se encontró redactar_old en content")
content = content.replace(redactar_old, redactar_new)

body_old = """    const res = await apiFetch('/api/redactar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: state.prompt, modo, instruccion, texto_previo: textoPrevio, calidad: tier, protocolo: 'ndjson' }),
      signal: ctl.signal,
    });"""

body_new = """    const res = await apiFetch('/api/redactar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tipo: state.tipo,
        datos: state.datos,
        perfil: {
          abogado: state.perfil.abogado,
          estilo: state.perfil.estilo,
          ia: state.perfil.ia,
        },
        modo,
        instruccion,
        texto_previo: textoPrevio,
        calidad: tier,
        protocolo: 'ndjson'
      }),
      signal: ctl.signal,
    });"""

if body_old not in content:
    raise RuntimeError("No se encontró body_old en content")
content = content.replace(body_old, body_new)

# 4. Actualizar renderZonaTipo para mostrar la base normativa revisada
zona_intro_old = """    zona.append(h('div', { class: 'intro' }, h('h1', {}, '¿Qué escrito necesitas?'), h('p', {}, 'Elige el tipo de documento. Luego llenas los datos del caso y se redacta con tu membrete y tu estilo.')));"""
zona_intro_new = """    const fechaRev = (state.catalogo && state.catalogo.fecha_revision) || '21 de octubre de 2026';
    const badgeNormativo = () => h('div', { class: 'base-normativa-pill', style: 'font-size: 11px; color: var(--color-texto-suave, #6b7280); margin-top: 6px; display: inline-flex; align-items: center; gap: 6px;' },
      h('span', { style: 'display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #10b981;' }),
      `Base normativa revisada al ${fechaRev}`
    );
    zona.append(h('div', { class: 'intro' }, h('h1', {}, '¿Qué escrito necesitas?'), h('p', {}, 'Elige el tipo de documento. Luego llenas los datos del caso y se redacta con tu membrete y tu estilo.'), badgeNormativo()));"""

if zona_intro_old not in content:
    raise RuntimeError("No se encontró zona_intro_old en content")
content = content.replace(zona_intro_old, zona_intro_new)

zona_card_old = """  const card = h('div', { class: 'tipo-actual' },
    h('span', { class: 'eyebrow' }, t.area),
    h('h2', {}, t.nombre),
    h('button', { class: 'btn chico', type: 'button', onclick: () => { state.catalogoAbierto = true; renderZonaTipo(); } }, 'Cambiar'),
    h('span', { class: 'nm' }, t.norma),
    h('p', { class: 'd' }, t.desc));"""

zona_card_new = """  const fechaRev = (state.catalogo && state.catalogo.fecha_revision) || '21 de octubre de 2026';
  const badgeNormativo = () => h('div', { class: 'base-normativa-pill', style: 'font-size: 11px; color: var(--color-texto-suave, #6b7280); margin-top: 6px; display: inline-flex; align-items: center; gap: 6px;' },
    h('span', { style: 'display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #10b981;' }),
    `Base normativa revisada al ${fechaRev}`
  );
  const card = h('div', { class: 'tipo-actual' },
    h('span', { class: 'eyebrow' }, t.area),
    h('h2', {}, t.nombre),
    h('button', { class: 'btn chico', type: 'button', onclick: () => { state.catalogoAbierto = true; renderZonaTipo(); } }, 'Cambiar'),
    h('span', { class: 'nm' }, t.norma),
    h('p', { class: 'd' }, t.desc),
    badgeNormativo());"""

if zona_card_old not in content:
    raise RuntimeError("No se encontró zona_card_old en content")
content = content.replace(zona_card_old, zona_card_new)

# 5. Agregar cargarCatalogo() y llamarlo en iniciar()
cargar_cat_fn = """async function cargarCatalogo() {
  try {
    const res = await apiFetch('/api/catalogo');
    if (!res.ok) throw new Error('No se pudo cargar el catálogo');
    const cat = await res.json();
    state.catalogo = cat;
    TIPOS_LISTA = cat.tipos || [];
    TIPOS = Object.fromEntries(TIPOS_LISTA.map(t => [t.id, t]));
    AREAS = cat.areas || [];
    renderZonaTipo();
    if (state.tipo && TIPOS[state.tipo]) renderFormulario();
  } catch (e) {
    console.error('Error cargando catálogo:', e);
  }
}

function iniciar() {"""

if "function iniciar() {" not in content:
    raise RuntimeError("No se encontró function iniciar() en content")

content = content.replace("function iniciar() {", cargar_cat_fn)

# En iniciar(), llamar cargarCatalogo()
iniciar_init_old = """function iniciar() {
  { const d = new Date(); $('#selloFecha').textContent = `Recibido · ${dos(d.getDate())} ${MESES[d.getMonth()].slice(0, 3).toUpperCase()} ${d.getFullYear()}`; }
  cargarEspejoLocal();"""

iniciar_init_new = """function iniciar() {
  { const d = new Date(); $('#selloFecha').textContent = `Recibido · ${dos(d.getDate())} ${MESES[d.getMonth()].slice(0, 3).toUpperCase()} ${d.getFullYear()}`; }
  cargarEspejoLocal();
  cargarCatalogo();"""

if iniciar_init_old not in content:
    raise RuntimeError("No se encontró iniciar_init_old en content")

content = content.replace(iniciar_init_old, iniciar_init_new)

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("¡index.html actualizado exitosamente!")
