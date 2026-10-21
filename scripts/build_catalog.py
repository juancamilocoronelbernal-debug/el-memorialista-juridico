"""Script para extraer el catálogo de index.html y generar los archivos JSON en app/catalogo/"""
import os
import json
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(BASE_DIR, "app", "static", "index.html")
CATALOGO_DIR = os.path.join(BASE_DIR, "app", "catalogo")
TIPOS_DIR = os.path.join(CATALOGO_DIR, "tipos")

os.makedirs(TIPOS_DIR, exist_ok=True)

# 1. Extraer TIPOS_LISTA mediante osascript
with open(INDEX_HTML, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Líneas donde se definen C, DESP, TIPOS_LISTA
js_code = "".join(lines[706:1201])
full_js = js_code + "\nJSON.stringify(TIPOS_LISTA);"

tmp_js = "/tmp/extract_tipos.js"
with open(tmp_js, "w", encoding="utf-8") as f:
    f.write(full_js)

res = subprocess.run(["osascript", "-l", "JavaScript", tmp_js], capture_output=True, text=True)
if res.returncode != 0:
    raise RuntimeError(f"Error evaluando JS: {res.stderr}")

tipos_lista = json.loads(res.stdout.strip())
print(f"Extraídos {len(tipos_lista)} tipos de documentos.")

FUENTES_POR_TIPO = {
    "tutela": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=2790",
        "https://www.corteconstitucional.gov.co/relatoria/"
    ],
    "impugnacion_tutela": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=2790"
    ],
    "desacato": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=2790"
    ],
    "cumplimiento": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=341"
    ],
    "popular": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=188"
    ],
    "peticion": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=65334"
    ],
    "recurso_admin": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=42691"
    ],
    "revocatoria": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=42691"
    ],
    "queja_disciplinaria": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=90940",
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=23118"
    ],
    "demanda_verbal": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425"
    ],
    "demanda_ejecutiva": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425"
    ],
    "contestacion": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425",
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=254181"
    ],
    "conciliacion": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=189689"
    ],
    "divorcio": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=250873",
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425"
    ],
    "alimentos": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=22106",
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425"
    ],
    "laboral_demanda": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=254181",
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=33104"
    ],
    "nulidad_restablecimiento": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=42691"
    ],
    "reparacion_directa": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=42691"
    ],
    "denuncia": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=14787"
    ],
    "recurso_judicial": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425"
    ],
    "apelacion_sentencia": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425",
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=187425"
    ],
    "alegatos": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425",
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=42691"
    ],
    "poder": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425",
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=187425"
    ],
    "memorial": [
        "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425"
    ],
    "otro": [
        "https://www.secretariasenado.gov.co/senado/basedoc/constitucion_politica_1991.html"
    ]
}

FECHA_REVISION = "2026-10-21"
REVISADO_POR = "Comité Jurídico El Memorialista"
VERSION_CATALOGO = "2.2.1"

for tipo in tipos_lista:
    t_id = tipo["id"]
    tipo["version"] = VERSION_CATALOGO
    tipo["fecha_revision"] = FECHA_REVISION
    tipo["revisado_por"] = REVISADO_POR
    tipo["fuentes"] = FUENTES_POR_TIPO.get(t_id, [
        "https://www.secretariasenado.gov.co/senado/basedoc/constitucion_politica_1991.html"
    ])
    tipo_path = os.path.join(TIPOS_DIR, f"{t_id}.json")
    with open(tipo_path, "w", encoding="utf-8") as f:
        json.dump(tipo, f, ensure_ascii=False, indent=2)

print(f"Guardados {len(tipos_lista)} archivos en {TIPOS_DIR}")

# 2. Contexto normativo
contexto_normativo = [
    {
        "id": "ley_2213_2022",
        "texto": "Ley 2213 de 2022: la virtualidad en los procesos judiciales es permanente (canal digital de partes, testigos y peritos; envío simultáneo de la demanda; notificación personal por mensaje de datos; poderes por mensaje de datos). Según la sentencia C-522 de 2023, las cargas de admisión del inciso 5 del artículo 6 no se aplican a la acción de tutela.",
        "version": VERSION_CATALOGO,
        "fecha_revision": FECHA_REVISION,
        "revisado_por": REVISADO_POR,
        "fuentes": [
            "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=187425",
            "https://www.corteconstitucional.gov.co/relatoria/2023/C-522-23.htm"
        ]
    },
    {
        "id": "ley_2452_2025",
        "texto": "Ley 2452 de 2025: nuevo Código Procesal del Trabajo y de la Seguridad Social, aplicable a los procesos laborales iniciados desde el 6 de abril de 2026; los iniciados antes siguen con el Decreto-Ley 2158 de 1948. Los antiguos jueces de pequeñas causas laborales pasaron a ser jueces laborales municipales.",
        "version": VERSION_CATALOGO,
        "fecha_revision": FECHA_REVISION,
        "revisado_por": REVISADO_POR,
        "fuentes": [
            "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=254181"
        ]
    },
    {
        "id": "ley_2466_2025",
        "texto": "Ley 2466 de 2025: reforma laboral que modificó el Código Sustantivo del Trabajo; algunas medidas son de aplicación gradual.",
        "version": VERSION_CATALOGO,
        "fecha_revision": FECHA_REVISION,
        "revisado_por": REVISADO_POR,
        "fuentes": [
            "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=258414"
        ]
    },
    {
        "id": "ley_2220_2022",
        "texto": "Ley 2220 de 2022: Estatuto de Conciliación, vigente desde el 30 de diciembre de 2022. En asuntos laborales la conciliación no es requisito de procedibilidad.",
        "version": VERSION_CATALOGO,
        "fecha_revision": FECHA_REVISION,
        "revisado_por": REVISADO_POR,
        "fuentes": [
            "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes/30044670"
        ]
    },
    {
        "id": "ley_2442_2024",
        "texto": "Ley 2442 de 2024: agregó al artículo 154 del Código Civil la causal de divorcio por la sola voluntad de cualquiera de los cónyuges.",
        "version": VERSION_CATALOGO,
        "fecha_revision": FECHA_REVISION,
        "revisado_por": REVISADO_POR,
        "fuentes": [
            "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=250873"
        ]
    },
    {
        "id": "smmlv_2026",
        "plantilla": "Salario mínimo mensual legal vigente en 2026: {smmlv} (dato configurado por el abogado).",
        "version": VERSION_CATALOGO,
        "fecha_revision": FECHA_REVISION,
        "revisado_por": REVISADO_POR,
        "fuentes": [
            "https://www.mintrabajo.gov.co/"
        ]
    },
    {
        "id": "regla_procesal_reciente",
        "texto": "Si una regla procesal cambió recientemente y no tienes certeza del artículo exacto, describe la regla sin número de artículo o marca [VERIFICAR].",
        "version": VERSION_CATALOGO,
        "fecha_revision": FECHA_REVISION,
        "revisado_por": REVISADO_POR,
        "fuentes": [
            "https://www.ramajudicial.gov.co/"
        ]
    }
]

with open(os.path.join(CATALOGO_DIR, "contexto_normativo.json"), "w", encoding="utf-8") as f:
    json.dump(contexto_normativo, f, ensure_ascii=False, indent=2)

# 3. Areas
areas = [
    "Constitucional",
    "Peticiones y actuaciones administrativas",
    "Civil y comercial",
    "Familia",
    "Laboral",
    "Contencioso administrativo",
    "Penal",
    "Procesos en curso",
    "Otro"
]
with open(os.path.join(CATALOGO_DIR, "areas.json"), "w", encoding="utf-8") as f:
    json.dump(areas, f, ensure_ascii=False, indent=2)

# 4. Formato de salida
formato_salida = {
    "version": VERSION_CATALOGO,
    "fecha_revision": FECHA_REVISION,
    "revisado_por": REVISADO_POR,
    "texto": (
        "FORMATO DE SALIDA (obligatorio; texto plano con estas marcas y ninguna otra):\n"
        "- Separa los párrafos con una línea en blanco. Dentro de un párrafo, un salto de línea simple es un cambio de línea forzado: úsalo solo en el destinatario, en la referencia y en los bloques de firma.\n"
        "- Título del escrito, si lo lleva: una línea que empiece con \"# \".\n"
        "- Títulos de capítulo (HECHOS, PRETENSIONES, PRUEBAS…): una línea que empiece con \"## \".\n"
        "- Subtítulos dentro de un capítulo: una línea que empiece con \"### \".\n"
        "- Bloque de referencia (referencia, radicado, partes): cada línea empieza con \"| \", por ejemplo: | **Referencia:** Acción de tutela\n"
        "- Transcripción textual de una norma: cada línea empieza con \"> \".\n"
        "- Viñetas: líneas que empiezan con \"- \".\n"
        "- Negrilla con **dos asteriscos**, cursiva con *un asterisco*, subrayado con __dos guiones bajos__.\n"
        "- Cada hecho y cada pretensión va en su propio párrafo.\n"
        "- La firma del abogado se indica solo con la marca [[FIRMA]] o [[FIRMA: rol]] en una línea sola.\n"
        "- No uses tablas, código, enlaces ni otras marcas."
    )
}
with open(os.path.join(CATALOGO_DIR, "formato_salida.json"), "w", encoding="utf-8") as f:
    json.dump(formato_salida, f, ensure_ascii=False, indent=2)

# 5. Reglas obligatorias
reglas_obligatorias = {
    "version": VERSION_CATALOGO,
    "fecha_revision": FECHA_REVISION,
    "revisado_por": REVISADO_POR,
    "fuentes": ["https://www.ramajudicial.gov.co/"],
    "reglas": [
        "1. Usa únicamente los hechos, nombres, cifras, fechas y documentos que aparecen en los datos del caso. No inventes nada. Si falta un dato necesario, escribe en su lugar [COMPLETAR: descripción breve del dato].",
        "2. Puedes ordenar, depurar y redactar con lenguaje jurídico los hechos y las pretensiones, sin alterar su sentido ni agregar hechos nuevos.",
        "3. Cita solo normas colombianas que existan y estén vigentes. Si dudas del número de un artículo o de su vigencia, escribe [VERIFICAR] inmediatamente después de la cita.",
        {
            "id": "jurisprudencia",
            "sugerir": "4. Jurisprudencia: además de la que indique el abogado, puedes citar hasta {nSent} pronunciamientos de la Corte Constitucional, la Corte Suprema de Justicia o el Consejo de Estado que conozcas con certeza y que sean pertinentes; prefiere sentencias de unificación y precedentes muy reconocidos. Escribe [VERIFICAR] inmediatamente después de cada sentencia que cites y que no haya suministrado el abogado. Nunca inventes números de sentencia, radicados, fechas ni magistrados ponentes.",
            "usuario": "4. Jurisprudencia: cita únicamente la que indicó el abogado en los datos del caso; no agregues otras sentencias.",
            "ninguna": "4. Jurisprudencia: no cites sentencias. Funda el escrito en la Constitución, la ley y los hechos."
        },
        "5. Nunca pongas entre comillas un texto atribuido a una sentencia, a una norma o a un autor, salvo que el abogado lo haya suministrado textualmente o estés seguro de su texto exacto; en caso contrario, parafrasea.",
        "6. No escribas el membrete ni el encabezado o pie de página con los datos de contacto del abogado: se agregan automáticamente. Sí escribe el destinatario y la referencia.",
        {
            "id": "extension",
            "plantilla": "7. Extensión: {extension_texto}"
        },
        "8. Escribe solo el documento: sin comentarios, notas, advertencias ni explicaciones antes o después."
    ]
}
with open(os.path.join(CATALOGO_DIR, "reglas_obligatorias.json"), "w", encoding="utf-8") as f:
    json.dump(reglas_obligatorias, f, ensure_ascii=False, indent=2)

# 6. Grupo redacción
grupo_redaccion = {
    "version": VERSION_CATALOGO,
    "fecha_revision": FECHA_REVISION,
    "revisado_por": REVISADO_POR,
    "nombre_grupo": "Redacción",
    "campos": [
        {
            "k": "fundamentos",
            "l": "Normas o jurisprudencia que quieres citar",
            "t": "area",
            "rows": 2,
            "ph": "Opcional. Ej.: Sentencia T-760 de 2008; art. 49 de la Constitución."
        },
        {
            "k": "_extension",
            "l": "Extensión",
            "t": "select",
            "opciones": [["concisa", "Concisa"], ["estandar", "Estándar"], ["extensa", "Extensa y exhaustiva"]]
        },
        {
            "k": "_juris",
            "l": "Jurisprudencia",
            "t": "select",
            "opciones": [["sugerir", "Sugerir sentencias, marcadas para verificar"], ["usuario", "Solo la que yo indique"], ["ninguna", "No citar jurisprudencia"]]
        },
        {
            "k": "_firma",
            "l": "Quién firma",
            "t": "select",
            "opciones": [["apoderado", "Yo, como apoderado(a)"], ["propio", "Yo, en nombre propio"], ["cliente", "Mi cliente, en nombre propio"]]
        },
        {
            "k": "_membrete",
            "l": "Incluir mi membrete en este escrito",
            "t": "check",
            "def": True
        },
        {
            "k": "_notas",
            "l": "Indicaciones adicionales",
            "t": "area",
            "rows": 2,
            "ph": "Ej.: Enfatiza que la accionante es adulta mayor; no menciones el nombre del médico."
        }
    ]
}
with open(os.path.join(CATALOGO_DIR, "grupo_redaccion.json"), "w", encoding="utf-8") as f:
    json.dump(grupo_redaccion, f, ensure_ascii=False, indent=2)

print("¡Catálogo generado exitosamente!")
