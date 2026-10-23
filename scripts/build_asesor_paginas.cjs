/* Catálogo de lectura pública, derivado exclusivamente del asesor integrado.
 * Ejecutar: node scripts/build_asesor_paginas.cjs [--check]
 * Los slugs mantienen las URLs del upstream dc646a1c9472d630251929d29d6078187336bd50.
 * No carga app/private, datos de usuarios ni configuración del servidor.
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const source = path.join(root, 'app/static/asesor/js');
const output = path.join(root, 'app/data/asesor_paginas.json');
const files = ['festivos.js', 'datos/normas.js', 'datos/entidades.js', 'datos/comunes.js',
  'datos/peticiones.js', 'datos/peticiones2.js', 'datos/peticiones3.js', 'datos/tutelas.js',
  'datos/tutelas2.js', 'datos/otros.js', 'datos/contratos.js', 'datos/mujer.js',
  'datos/sinonimos.js', 'motor.js'];
const SLUGS = {
  pet_municipio_planeacion: 'derecho-de-peticion-planeacion-municipal', pet_municipio_servicios: 'derecho-de-peticion-alcaldia-barrio-vereda', pet_municipio_sisben: 'derecho-de-peticion-sisben',
  pet_municipio_transito: 'derecho-de-peticion-transito-comparendo-prescripcion', pet_municipio_predial: 'derecho-de-peticion-impuesto-predial', pet_municipio_policia: 'querella-inspeccion-de-policia-ruido-vecinos',
  pet_eps_servicio: 'derecho-de-peticion-eps-cita-medicamento-cirugia', pet_eps_historia: 'derecho-de-peticion-historia-clinica', pet_incapacidades: 'derecho-de-peticion-incapacidades-no-pagadas',
  pet_pension: 'derecho-de-peticion-colpensiones-pension', pet_empleador: 'derecho-de-peticion-empleador-salarios-liquidacion', pet_spd: 'reclamo-servicios-publicos-factura-alta',
  pet_banco: 'derecho-de-peticion-banco', pet_colegio: 'derecho-de-peticion-colegio-cupo-certificados', pet_info_publica: 'solicitud-informacion-publica', pet_copias: 'solicitud-de-copias-expediente',
  pet_queja_funcionario: 'queja-contra-funcionario-publico', pet_victimas: 'derecho-de-peticion-unidad-de-victimas', pet_migracion: 'derecho-de-peticion-migracion-colombia-ppt', pet_juzgado: 'derecho-de-peticion-juzgado-fiscalia',
  pet_icbf: 'derecho-de-peticion-icbf-comisaria-de-familia', pet_arrendador: 'reclamacion-arrendador-arrendatario', pet_prosperidad: 'derecho-de-peticion-prosperidad-social-subsidio', pet_general: 'derecho-de-peticion-modelo-general',
  tut_salud_servicio: 'tutela-eps-medicamentos-citas-cirugias', tut_salud_integral: 'tutela-tratamiento-integral', tut_peticion: 'tutela-derecho-de-peticion-sin-respuesta', tut_salario: 'tutela-salarios-no-pagados-minimo-vital',
  tut_incapacidades: 'tutela-incapacidades-no-pagadas', tut_pension: 'tutela-pension', tut_estabilidad: 'tutela-despido-embarazo-enfermedad-discapacidad', tut_educacion: 'tutela-derecho-a-la-educacion',
  tut_debido_proceso: 'tutela-debido-proceso', tut_habeas_data: 'tutela-habeas-data-datacredito', tut_servicios_publicos: 'tutela-corte-agua-energia', tut_victimas: 'tutela-victimas-del-conflicto',
  tut_vida_seguridad: 'tutela-amenazas-proteccion-unp', tut_migrantes: 'tutela-migrantes-salud-educacion', tut_general: 'tutela-general-cualquier-derecho',
  desacato: 'incidente-de-desacato-tutela', impugnacion: 'impugnacion-fallo-de-tutela', rec_reposicion: 'recurso-de-reposicion-y-apelacion', rec_spd: 'recurso-reposicion-servicios-publicos',
  queja_supersalud: 'queja-supersalud-eps', queja_consumidor: 'reclamacion-garantia-consumidor', queja_financiera: 'queja-defensor-consumidor-financiero', hd_reclamo: 'reclamo-habeas-data-datacredito', hd_supresion: 'solicitud-supresion-datos-personales',
  fam_alimentos: 'conciliacion-cuota-alimentaria', fam_proteccion: 'medida-de-proteccion-violencia-intrafamiliar', fam_custodia: 'conciliacion-custodia-y-visitas',
  con_arriendo_vivienda: 'contrato-de-arrendamiento-de-vivienda', con_compraventa_vehiculo: 'contrato-compraventa-vehiculo-moto', con_compraventa_bien: 'contrato-compraventa-bien-mueble', con_servicio_domestico: 'contrato-servicio-domestico',
  con_pagare: 'pagare-prestamo-entre-personas', con_poder: 'poder-especial-tramite', con_acuerdo_pago: 'acuerdo-de-pago-deuda', con_recibo: 'recibo-de-pago-paz-y-salvo',
  muj_denuncia: 'denuncia-violencia-contra-la-mujer-fiscalia', muj_tutela_proteccion: 'tutela-falta-de-proteccion-violencia-mujer', muj_declaracion_cabeza: 'declaracion-madre-cabeza-de-familia', muj_cabeza_familia: 'peticion-madre-cabeza-de-familia-prioridad',
  muj_licencia_maternidad: 'licencia-de-maternidad-no-pagada', muj_acoso_laboral: 'queja-acoso-laboral-acoso-sexual', muj_salud_sexual: 'peticion-eps-salud-sexual-reproductiva'
};
const slugify = s => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const context = { console, Date, Map, Set, URL };
context.window = context;
vm.createContext(context);
const hash = crypto.createHash('sha256');
for (const file of files) {
  const text = fs.readFileSync(path.join(source, file), 'utf8');
  hash.update(file + '\0' + text + '\0');
  vm.runInContext(text, context, { filename: file, timeout: 5000 });
}
const AJ = context.AJ;
const cases = AJ.casos.filter(c => !c.retirado);
const option = o => ({ texto: String(o.t || ''), condicional: Boolean(o.si) });
const serialized = cases.map(c => {
  const defaults = Object.fromEntries((c.campos || []).filter(f => f.valorInicial !== undefined).map(f => [f.id, f.valorInicial]));
  // Las referencias que dependen de una respuesta se anuncian como posibles,
  // nunca como una selección jurídica definitiva para el visitante.
  const scenarios = [defaults];
  for (const field of c.campos || []) for (const choice of field.opciones || []) {
    scenarios.push({ ...defaults, [field.id]: field.tipo === 'checks' ? [choice.v] : choice.v });
  }
  const refs = new Set();
  for (const data of scenarios) {
    const selected = typeof c.normas === 'function' ? c.normas(data) : c.normas || [];
    for (const id of selected.filter(Boolean)) {
      if (!AJ.normas[id]) throw new Error(`Referencia desconocida ${id} en ${c.id}`);
      refs.add(id);
    }
  }
  return {
    id: c.id,
    slug: SLUGS[c.id] || slugify(c.titulo).split('-').slice(0, 7).join('-'),
    titulo: c.titulo,
    resumen: c.resumen,
    tipo: c.tipo,
    tipo_nombre: AJ.tipos[c.tipo].nombre,
    categoria: AJ.entidades.categoria(c.categoria).nombre,
    campos: (c.campos || []).filter(f => f.tipo !== 'info').map(f => ({
      id: f.id, etiqueta: f.etiqueta, requerido: Boolean(f.requerido),
      condicional: Boolean(f.mostrarSi || f.ocultarSi),
      opciones: (f.opciones || []).map(o => String(o.t || ''))
    })),
    peticiones: (c.peticiones || []).map(option),
    anexos: (c.anexos || []).map(option),
    normas: [...refs].map(id => ({ id, cita: AJ.normas[id].cita })),
    guia: { nota: c.guia?.nota || '', siguiente: c.guia?.siNoResponden || '' }
  };
});
if (new Set(serialized.map(c => c.slug)).size !== serialized.length) throw new Error('Slugs repetidos.');
if (new Set(serialized.map(c => c.id)).size !== serialized.length) throw new Error('Casos repetidos.');
const result = JSON.stringify({ version: 1, fuente_sha256: hash.digest('hex'),
  referencias_totales: Object.keys(AJ.normas).length,
  tipos: Object.entries(AJ.tipos).map(([id, t]) => ({ id, nombre: t.nombre })), casos: serialized }, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (!fs.existsSync(output) || fs.readFileSync(output, 'utf8') !== result) {
    console.error('El catálogo público necesita regenerarse: node scripts/build_asesor_paginas.cjs');
    process.exitCode = 1;
  } else console.log(`Catálogo público al día: ${serialized.length} páginas.`);
} else {
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, result);
  console.log(`Catálogo público generado: ${serialized.length} páginas.`);
}
