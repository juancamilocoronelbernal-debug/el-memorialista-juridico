# Integración actual de El Memorialista

Fecha de esta guía: **23 de octubre de 2026**. Integración iniciada el 22 de octubre.

Esta entrega reúne la orientación ciudadana pública y el generador profesional del proyecto original. La orientación funciona en el navegador; el despacho utiliza el servidor FastAPI y exige una sesión de Supabase validada. Los servicios de correo, base de datos, Storage e IA necesitan configuración y una comprobación real en la instalación de destino.

Esta es la guía de actualización para quien vaya a abrir el proyecto en **Antigravity**, ejecutarlo o desplegarlo. No requiere reconstruir la base de datos existente ni reemplazar las credenciales del propietario.

## 1. Qué contiene esta versión

| Área | Comportamiento actual |
| --- | --- |
| Entrada pública | `/`, con catálogo de 66 casos activos, 10 tipos y 169 entradas normativas. |
| Orientador | 22 nodos de preguntas que conducen a casos y pasos posibles; permite volver a respuestas anteriores. |
| Búsqueda | Sinónimos, lenguaje cotidiano, normalización de tildes, prefijos y tolerancia a errores de escritura; filtros por tipo, categoría y módulo. |
| Formularios | Preguntas condicionales, validación, representación, contratos con varias partes, vista previa y edición. |
| Documentos | Copia de texto, TXT, DOCX OOXML editable, PDF directo e impresión. |
| Seguimiento | Registro de entrega y radicado, respuesta, fallo y notificación según el caso; fechas orientativas y siguiente documento con datos pertinentes prellenados. |
| Accesibilidad | Letra al 100 %, 112 %, 125 % y 140 %, alto contraste y lectura con una voz local en español, si el dispositivo la ofrece. |
| Copias ciudadanas | Exportación v2 e importación de v2, v1 y arreglos heredados de la versión de Claude, con seguimiento y origen. |
| Sin conexión | PWA pública en `/asesor/` y HTML autónomo descargable con los recursos públicos incorporados. |
| Generador | `/app` y `/generador`, con autenticación, catálogo profesional, IA, cálculos, auditoría, exportaciones y operaciones de respaldo/recuperación en Supabase. |

El usuario autenticado entra directamente a **Mi despacho**. La navegación del despacho no incorpora el orientador ciudadano. En la versión conectada, visitar `/`, `/asesor/` o `/login` con una sesión válida conduce a `/app`. Sin conexión, la PWA puede mostrar su copia pública, pero no permite entrar al generador privado ni validar una sesión contra el proveedor.

### Dos espacios de datos

| Datos | Dónde se guardan | Cómo se trasladan |
| --- | --- | --- |
| Respuestas del formulario ciudadano | Memoria y recuperación automática en `sessionStorage` de la pestaña; borrador persistente cuando la persona lo guarda. | Descargar el documento o guardar/exportar la copia ciudadana. |
| Borradores y seguimiento ciudadanos | Almacenamiento del navegador y origen de la web. No dependen de una cuenta. | Copia JSON desde Mis documentos. No se suben a Supabase al iniciar sesión. |
| Preferencias de accesibilidad | Navegador. | Se conservan si el navegador permite almacenamiento. |
| Datos locales del despacho | `localStorage` e IndexedDB separados por el identificador de la cuenta validada. | Copia propia del generador y sus controles de respaldo. |
| Escrito, versión o archivo privado respaldado | Supabase del propietario, con políticas RLS y Storage privado. | Acciones de respaldo, recuperación y exportación del despacho. |

La copia JSON ciudadana y la copia del generador son formatos distintos. En un equipo compartido, las personas que usen el mismo perfil del navegador pueden acceder a los borradores públicos guardados. Algunos navegadores restauran también la sesión de una pestaña cerrada: cerrar la ventana no garantiza borrar sus respuestas. Usa el control de borrado de datos al terminar en un equipo compartido. La separación por cuenta del despacho no cifra el disco del equipo. Cambiar el dominio de la web también cambia su almacenamiento local: exporta las copias antes de moverla a otro origen.

## 2. Word y PDF: funcionamiento y alcance

El Word ciudadano es un **DOCX OOXML nativo**: contiene XML, relaciones, estilos y las partes del paquete de Office. Puede editarse en una aplicación compatible. El exportador conserva el texto original y escapa los caracteres que tienen significado especial en XML.

El PDF se genera localmente, con fuentes **DejaVu** incorporadas y un mapa `ToUnicode` para que el texto pueda buscarse y copiarse. Las pruebas de generación y extracción verifican español, caracteres latinos extendidos, griego, cirílico y signos habituales. También comprueban textos extensos, saltos de página y firmas. Esa cobertura no equivale a soportar todas las escrituras, combinaciones de caracteres o reglas de composición tipográfica.

Si el exportador no puede representar un carácter fielmente, muestra un error explícito antes de entregar el PDF. Ofrece **Word** o **Imprimir → Guardar como PDF** con las fuentes del dispositivo. No translitera nombres ni los sustituye silenciosamente por `?`. La fidelidad visual de la alternativa depende de que el dispositivo tenga las fuentes necesarias. Una fuente local ausente también produce un error visible.

Los recursos están en `app/static/asesor/js/pdf-fuentes.js`; su aviso se conserva en [DejaVu-LICENSE.txt](../app/static/asesor/licenses/DejaVu-LICENSE.txt). DejaVu tiene su propia licencia; el cambio de identidad de la aplicación no elimina los avisos de esta dependencia ni los del SDK de Supabase.

## 3. Seguimiento y copias de seguridad

Después de registrar una entrega, la aplicación permite consultar el trámite desde **Mis documentos**. Las fechas necesarias dependen del tipo de documento: recepción de la solicitud, notificación efectiva, apertura de un incidente o recepción del expediente por el superior.

En una tutela, **la notificación del fallo a la persona y el inicio del plazo de cumplimiento de la orden son datos distintos**. `fechaNotificacion` sirve para orientar el término de impugnación de quien registra el trámite. `fechaInicioCumplimiento` y `horaInicioCumplimiento` deben tomarse de la orden y su constancia; no se deducen automáticamente de la notificación a esa persona. Si falta ese inicio, no se calcula el cumplimiento. El módulo distingue horas continuas y días calendario enteros; estos últimos vencen al final del último día calculado. Se utiliza la hora de Colombia.

El seguimiento utiliza los datos que introduzca la persona. No consulta sistemas judiciales, no radica escritos y no envía alertas por correo ni notificaciones en segundo plano. El estado se consulta al abrir la aplicación. Los plazos son orientativos: no conocen cierres extraordinarios, pruebas, prórrogas, suspensiones o particularidades que no estén registradas. El cómputo no declara por sí mismo que se concedió una solicitud o que procede una acción.

Cuando hay un siguiente documento disponible, el prellenado reutiliza identidad, entidad y antecedentes pertinentes. Conserva una referencia al documento de origen. No copia automáticamente todos los anexos o pretensiones de un trámite distinto; la persona debe revisar las respuestas antes de generar el nuevo escrito.

### Importación conservadora

La exportación ciudadana actual usa `version: 2`. Se admiten también copias v1 y el arreglo heredado de Claude. Los metadatos compatibles de `seguimiento` y `origen` se mantienen al exportar, importar y editar. Esto incluye `fechaApertura`, `fechaRecepcionExpediente`, `fechaInicioCumplimiento` y `horaInicioCumplimiento`. Una copia antigua que no incluya el inicio del cumplimiento conserva sus datos, pero no obtiene una fecha de cumplimiento inferida.

La importación permite hasta **200 documentos** y **5 MB** por archivo. Valida la copia completa antes de escribir: una versión futura, campos desconocidos o valores inválidos producen un error y conservan el estado previo. Si el historial existente está corrupto, queda intacto y se ofrece descargar sus bytes originales para recuperarlo.

Las copias idénticas se omiten. Si dos documentos comparten identificador pero tienen distinto contenido, se conservan ambos y se asigna un nuevo identificador al importado. Los enlaces entre documentos importados se ajustan, incluidos hijos y nietos afectados. Si conservar ambas versiones supera el límite, no se importa parcialmente. Una operación válida escribe una sola vez; un fallo de cuota o de acceso al almacenamiento se informa como fallo.

### Fuentes del módulo de seguimiento

El inventario de fuentes y su fecha de revisión se encuentra en `AJ.seguimiento.FUENTES`, dentro de [seguimiento.js](../app/static/asesor/js/seguimiento.js). Los enlaces siguientes documentan las referencias incorporadas, sin constituir una revisión nueva de todos los supuestos jurídicos:

| Materia | Fuente primaria enlazada por el módulo |
| --- | --- |
| Derecho de petición | [Ley 1755 de 2015](https://cancilleria.gov.co/normograma/compilacion/docs/ley_1755_2015.htm). |
| Tutela e impugnación | [Decreto 2591 de 1991](https://cancilleria.gov.co/normograma/compilacion/docs/decreto_2591_1991.htm). |
| Incidente de desacato | [Sentencia C-367 de 2014](https://www.corteconstitucional.gov.co/relatoria/2014/c-367-14.htm). |
| Comunicaciones | [Resolución CRC 8171 de 2026](https://normograma.crcom.gov.co/crc/compilacion/docs/resolucion_crc_8171_2026.htm). |
| Servicios públicos domiciliarios | [Ley 142 de 1994](https://cancilleria.gov.co/normograma/compilacion/docs/ley_0142_1994.htm). |
| Datos personales y datos financieros | [Ley 1581 de 2012](https://www.cancilleria.gov.co/normograma/compilacion/docs/ley_1581_2012.htm) y [Ley 1266 de 2008](https://cancilleria.gov.co/normograma/compilacion/docs/ley_1266_2008.htm). |
| Recursos administrativos | [Ley 1437 de 2011](https://cancilleria.gov.co/normograma/compilacion/docs/ley_1437_2011.htm). |

### Ajustes del formulario de datos personales y cobranza

El caso `hd_supresion` distingue una consulta de acceso/origen de datos de un reclamo que solicita corrección, supresión u otra actuación. Su asunto, solicitudes y seguimiento reflejan esa selección; la confirmación escrita solicita explicar las actuaciones o un impedimento legal, sin prometer una supresión automática. La referencia incorporada es la [Ley 1581 de 2012, artículos 14–16](https://www.cancilleria.gov.co/normograma/compilacion/docs/ley_1581_2012.htm): término ordinario de consulta de 10 días hábiles, con hasta 5 adicionales bajo las condiciones legales, y de reclamo de 15 días hábiles, con hasta 8 adicionales bajo esas condiciones.

Los textos de cobranza se ajustaron a la [Ley 2300 de 2023, artículos 2–5](https://www.secretariasenado.gov.co/senado/basedoc/ley_2300_2023.html). Tras establecer contacto directo, la regla incorporada impide contactar por distintos canales durante una misma semana y más de una vez el mismo día, además de las condiciones sobre canales, horarios y referencias. Se retiró la afirmación anterior que lo resumía como un límite general de «una vez por semana». Esta corrección focal no equivale a una revisión integral de todo el catálogo.

## 4. Actualizar el proyecto en Antigravity

### Paso 1. Conservar la instalación actual

Abre la carpeta del proyecto Python completo. Antes de reemplazar archivos, conserva una copia o un commit de la versión que funciona y exporta los datos locales que deban mantenerse. Si la base ya tiene usuarios o documentos, realiza además el respaldo de esa base y de sus archivos conforme a tu instalación de Supabase.

Conserva **`.env`**, las variables del alojamiento, el dominio, las credenciales y los datos existentes. `.env.example` sirve para comparar nombres y añadir opciones nuevas; no reemplaza un `.env` configurado. No copies secretos dentro de un prompt, capturas, archivos públicos o el repositorio. Si trabajas con Git, revisa la lista de archivos antes del commit.

Actualiza el código del proyecto completo, incluidas las carpetas `app/private`, `app/static/asesor`, `supabase`, `scripts` y `tests`, las dependencias y los archivos de despliegue. Publicar solo `app/static` no instala las APIs, la autenticación ni la generación profesional.

### Paso 2. Instalar las dependencias

Usa el entorno Python de la aplicación. En una instalación nueva:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -c constraints.txt
```

En Windows, la activación es `.venv\Scripts\Activate.ps1`. En una instalación existente, activa su entorno y ejecuta la instalación con `requirements.txt` y `constraints.txt`. Node se necesita para reconstruir recursos y ejecutar pruebas de JavaScript; los recursos compilados incluidos permiten servir la aplicación sin Node en producción.

Solo si no tienes un `.env` local, crea uno a partir de `.env.example`. En el alojamiento utiliza su panel de variables. Comprueba lo siguiente sin mostrar valores secretos:

| Variable | Qué configurar |
| --- | --- |
| `ENVIRONMENT` | `development` para HTTP local; `production` para la web HTTPS. |
| `APP_BASE_URL` | Origen canónico de la web, sin barra final. En local puede ser `http://localhost:8000`. |
| `SUPABASE_URL` | URL del proyecto Supabase existente, si ya contiene los datos. |
| `SUPABASE_ANON_KEY` | Clave anon/publishable de ese mismo proyecto. Se entrega al navegador; su acceso está sujeto a RLS. Nunca uses aquí la clave de servicio. |
| `SUPABASE_STORAGE_BUCKET` | `archivos-privados`, el bucket que configura el SQL incluido. |
| `AUTH_ALLOW_SIGNUP` | `False` si el acceso será por invitación. Configura también las altas públicas en Supabase Auth. |
| `AUTH_COOKIE_MAX_AGE_SECONDS` | Duración de la cookie; el ejemplo usa `3600`. El servidor sigue verificando la sesión. |
| `SUPABASE_SERVICE_ROLE_KEY` | Solo servidor, para operaciones administrativas como eliminar cuentas. No hace falta para el inicio de sesión normal. |
| `GEMINI_API_KEY` | Solo servidor; necesaria para la redacción profesional con Gemini. |
| `GEMINI_MODEL`, `GEMINI_MODEL_PRO`, `GEMINI_FALLBACK_MODELS` | Modelos que realmente admita la cuenta del proveedor. Los nombres del ejemplo son configuración, no una comprobación de acceso o disponibilidad. |
| `GROQ_API_KEY`, `GROQ_MODEL` | Respaldo opcional de IA, solo servidor. |
| `ALLOWED_ORIGINS` | Vacío cuando frontend y API comparten origen, como en el despliegue incluido. |
| `KEEP_ALIVE` | El ejemplo y Render usan `False`. |

Las demás opciones de IA y cuotas están descritas en `.env.example`. No se requiere `SUPABASE_JWT_SECRET`: la validación se hace con Supabase Auth. `APP_ACCESS_CODE` no concede acceso y no hay tokens de prueba que permitan entrar al producto.

### Paso 3. Elegir el SQL correcto

| Situación | Archivo que debes aplicar como propietario, en SQL Editor |
| --- | --- |
| Supabase ya creado con el esquema del generador original | `supabase/migrations/20261022010000_separacion_publica_privada_rls.sql`. |
| Proyecto nuevo sin las tablas de la aplicación | `supabase/schema.sql`. |

La migración de seguridad ya está incluida: **no crees otra ni vuelvas a crear las tablas para actualizar**. Las seis tablas del original conservan su estructura. La migración reemplaza políticas, ajusta permisos, instala protecciones de perfil y propiedad, restringe la administración de membresías y mantiene el bucket privado. Es idempotente y no elimina registros ni objetos de Storage; tampoco necesita columnas nuevas.

Las rutas originales `logo/{usuario}`, `firma/{usuario}` y `plantilla/{usuario}` siguen admitidas. El bucket conserva el límite de 10 MB y actualiza los tipos permitidos; las cargas SVG nuevas no están admitidas. La migración no mueve archivos ni revisa retrospectivamente si las membresías o datos compartidos existentes fueron asignados correctamente. Si el esquema de tu instalación se modificó por separado, compara esas modificaciones antes de aplicar el SQL del proyecto.

La prueba `supabase/tests/aislamiento_cuentas.sql` utiliza roles reales y termina en `ROLLBACK`. Ejecútala en una instancia de prueba tras aplicar el esquema. Los contratos locales que leen SQL no sustituyen esta comprobación de PostgreSQL/RLS.

### Paso 4. Configurar el acceso y el correo

En Supabase Auth, configura el proveedor de correo, confirmación de cuentas y correo saliente. Crea o invita la cuenta inicial desde la administración de Supabase. La aplicación admite contraseña, enlace de acceso y recuperación; su funcionamiento real depende de Auth y de la entrega del correo.

Configura la URL canónica como **Site URL** y permite estas rutas de retorno para ese dominio:

```text
https://tu-dominio.example/auth/callback
https://tu-dominio.example/auth/callback?mode=recovery
```

Sustituye el dominio del ejemplo. Para desarrollo añade las mismas rutas con `http://localhost:8000`. Utiliza el mismo host al visitar la web y en `APP_BASE_URL`: `localhost` y `127.0.0.1` son orígenes distintos.

Si el acceso es solo por invitación, deja `AUTH_ALLOW_SIGNUP=False` y desactiva las altas públicas en Supabase Auth. La variable de la aplicación controla la interfaz; no reemplaza la restricción del proveedor. Referencias del proveedor: [redirecciones](https://supabase.com/docs/guides/auth/redirect-urls) y [contraseñas](https://supabase.com/docs/guides/auth/passwords).

### Paso 5. Arrancar y desplegar

Para desarrollo local:

```bash
uvicorn app.main:app --no-proxy-headers --reload --host 127.0.0.1 --port 8000
```

Abre `http://localhost:8000` si ese es el origen configurado. `/api/health` comprueba que el servidor responde; una respuesta correcta no prueba por sí sola que funcionen Supabase, el correo o la IA.

En Render, usa `render.yaml`, conserva o completa las variables del servicio y ajusta `APP_BASE_URL` y las redirecciones de Auth al dominio definitivo. Para Docker:

```bash
docker build -t el-memorialista:3 .
docker run --rm --env-file .env -p 8000:8000 el-memorialista:3
```

Las cookies con `ENVIRONMENT=production` requieren HTTPS. Para abrir el contenedor por HTTP local utiliza `ENVIRONMENT=development` en su configuración. La construcción Docker, el despliegue Render y los proveedores requieren comprobación en el entorno de destino.

### IP del cliente detrás de un proxy

Docker, Render y el comando anterior usan **`--no-proxy-headers`**. Así Uvicorn conserva la IP real de la conexión y la aplicación puede decidir si confía en el proxy antes de interpretar cabeceras.

El valor inicial es `PROXY_IPS_CONFIABLES=` vacío, `PROXIES_CONFIABLES=0` e `IP_CABECERA_CONFIABLE=` vacía. Ese modo ignora cabeceras de IP aportadas por el cliente. No se cambia automáticamente por detectar Render.

Si necesitas identificar clientes detrás de un proxy, confirma con el alojamiento la cadena real y elige **uno** de estos modos:

1. `PROXY_IPS_CONFIABLES`: IPs/CIDR del proxy que conecta al servidor y de los saltos internos confiados; `PROXIES_CONFIABLES`: número exacto de saltos que se leen desde la derecha de `X-Forwarded-For`; `IP_CABECERA_CONFIABLE`: vacía.
2. `PROXY_IPS_CONFIABLES`: IPs/CIDR reales; `IP_CABECERA_CONFIABLE`: nombre de una cabecera exclusiva que ese proxy reemplace con una sola IP; `PROXIES_CONFIABLES=0`.

No uses redes de todo Internet ni inventes IPs del proveedor. La configuración valida direcciones y rechaza modos incompatibles. Si una cabecera es inválida o su emisor no es confiable, se utiliza la IP de conexión. Con el modo inicial, varios visitantes detrás del mismo proxy pueden compartir sus límites por IP. Los límites de uso se mantienen por proceso; para varias réplicas o cuotas persistentes se necesita un almacén compartido.

## 5. Comprobaciones locales y puesta en servicio

El resultado de la ejecución de esta entrega está en [VERIFICACION_INTEGRADA.md](VERIFICACION_INTEGRADA.md): 515 pruebas aprobadas y una comprobación manual heredada omitida. El informe distingue los recorridos reales de navegador de las respuestas simuladas de servicios externos.

Instala las dependencias de desarrollo en el entorno de pruebas y ejecuta:

```bash
python -m pip install -r requirements-dev.txt -c constraints.txt
python -m pytest -q
node tests/test_asesor_engine.cjs
node tests/test_asesor_features.cjs
node tests/test_asesor_respaldo.cjs
node tests/test_auth_client.cjs
node tests/test_asesor_pwa.cjs
node scripts/build_asesor_paginas.cjs --check
```

Las suites cubren, entre otras cosas, rutas privadas y sesiones, proxies y CSP, DOCX/PDF, orientador, búsqueda, seguimiento, prellenado, importación conservadora y caché pública. Las pruebas locales de servicios externos usan respuestas simuladas. La prueba heredada de dictado de macOS es manual y se omite por defecto.

El recorrido `tests/test_asesor_browser.mjs` utiliza un servidor FastAPI local y Playwright con Chromium instalado. Prueba formularios, descargas, seguimiento, copias, presentación móvil y funcionamiento público sin conexión. Su cabecera documenta las variables de ejecución. Para probar únicamente la parte pública, arranca otra instancia local con los proveedores deshabilitados explícitamente:

```bash
KEEP_ALIVE=False GEMINI_API_KEY= GROQ_API_KEY= SUPABASE_URL= SUPABASE_ANON_KEY= SUPABASE_SERVICE_ROLE_KEY= python -m uvicorn app.main:app --no-proxy-headers --host 127.0.0.1 --port 8768
```

En otra terminal, con Playwright y su navegador disponibles:

```bash
node tests/test_asesor_browser.mjs
```

Ese recorrido usa datos ficticios y no demuestra un inicio de sesión real. La revisión final debe incluir la parte offline; `ASESOR_BROWSER_SKIP_OFFLINE=1` es únicamente una ayuda temporal mientras se regeneran los recursos.

Si cambias código, datos, estilos o fuentes del asesor, reconstruye antes de probar la PWA y el HTML autónomo:

```bash
node scripts/build_asesor_paginas.cjs
python scripts/build_asesor_offline.py
python scripts/build_asesor_pwa.py
```

La PWA solo almacena recursos públicos permitidos y tiene alcance `/asesor/`. Las cabeceras CSP de la web y el shell offline restringen la ejecución a los recursos y scripts previstos. Al modificar scripts incrustados, usa los generadores para actualizar sus hashes; no soluciones un bloqueo añadiendo `unsafe-inline` a `script-src`.

### Lo que se debe comprobar en la instalación real

Usa dos cuentas y documentos ficticios para verificar acceso, recuperación por correo y cierre; que una cuenta no vea los borradores locales o archivos privados de la otra; que respaldo y recuperación funcionen; y que las colaboraciones autorizadas respeten las políticas. Comprueba también una generación real con el modelo configurado y revisa contenido, cuotas y errores. No marques estas comprobaciones como realizadas porque hayan pasado los mocks o porque `/api/health` responda.

Comprueba instalación, actualización y reapertura de la PWA en los navegadores que usarán las personas. La instalación requiere HTTPS o localhost, soporte del navegador y una primera carga con conexión. El HTML autónomo se actualiza descargándolo de nuevo; su almacenamiento puede estar limitado cuando se abre como archivo local.

## 6. Cómo leer los informes anteriores

[VERIFICACION.md](VERIFICACION.md), [PARIDAD_ASESOR.md](PARIDAD_ASESOR.md) y [ASESOR_CIUDADANO.md](ASESOR_CIUDADANO.md) conservan el historial de etapas anteriores. Los pasajes que describen Word como `.doc`, PDF mediante impresión, ausencia de seguimiento o un alcance previo de la interfaz corresponden a aquellas etapas; las funciones actuales están descritas en esta guía. Las cifras de pruebas anteriores no se suman para atribuirlas a una sola ejecución actual.

`CAMBIOS_GENERADOR_ORIGINAL.md` y su JSON son el registro de comparación de identidad y cambios del generador original. Se conservan como evidencia de esa comparación; no son un inventario exhaustivo de todas las mejoras ciudadanas posteriores. Esta guía no reescribe ese historial ni convierte la revisión focal de textos jurídicos en una certificación integral de todas las normas o documentos.

El estado de esta entrega debe distinguir siempre **implementado**, **comprobado localmente** y **verificado con proveedores reales**. La configuración y las pruebas de destino completan la puesta en servicio; no están sustituidas por una demostración visual.
