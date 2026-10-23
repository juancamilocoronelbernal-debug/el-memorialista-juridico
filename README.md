# El Memorialista 3.0

**Orientación ciudadana abierta al público y generador profesional protegido por inicio de sesión.**

La aplicación conserva el servidor FastAPI y el generador del proyecto entregado. Integra orientación paso a paso, búsqueda tolerante a errores, formularios, seguimiento de trámites y descargas DOCX/PDF en la parte pública, con separación entre ambas experiencias.

La guía [docs/INTEGRACION_COMPLETA.md](docs/INTEGRACION_COMPLETA.md) describe la versión integrada actual y los pasos para actualizar el proyecto en Antigravity, conservar la configuración y los datos, y verificar la instalación de destino. La versión actual es **5.0.2 (integración visual del generador con el despacho)**.

### Nuevo diseño del generador (5.0.2)

La ruta `/generador` utiliza ahora el mismo lenguaje visual que `/app`: menú lateral, marfil/verde, tipografía editorial, acceso al Agente y a los cinco productos del despacho. En móvil, el menú se convierte en un panel desplegable y las cinco pestañas tradicionales siguen disponibles. El diseño está en `app/private/generador-theme.css` y se sirve solo a una sesión válida desde `/app/assets/generador-theme.css`.

**Los prompts, los motores de redacción, los 26 tipos profesionales, los formularios, el historial y la exportación permanecen intactos.** Los selectores `id` originales siguen en uso. El CSS de la interfaz no cambia las propiedades tipográficas ni los márgenes de la hoja legal generada.

Aprende el funcionamiento de todos los módulos en [**docs/GUIA_USO_COMPLETA.md**](docs/GUIA_USO_COMPLETA.md). Para comprobar esta mejora visual consulta [docs/CAMBIOS_DISENO_GENERADOR_V502.md](docs/CAMBIOS_DISENO_GENERADOR_V502.md).

## 1. Comportamiento de la web

| Entrada | Sin sesión válida | Con sesión válida |
| --- | --- | --- |
| `/` | Orientación ciudadana | Redirección a `/app` |
| `/asesor/` | Asesor ciudadano instalable | Redirección a `/app` cuando hay conexión |
| `/login` | Inicio de sesión | Redirección a `/app` |
| `/auth/callback` | Procesa el enlace de acceso o recuperación | Procesa también enlaces nuevos o de otra cuenta |
| `/app` y `/generador` | Redirección al inicio de sesión | Generador profesional |
| APIs de documentos, cálculos, auditoría y archivos | Rechazo antes de procesar el contenido | Token de Supabase verificado por el servidor |

Después de entrar, el usuario trabaja directamente en **Mi despacho**, sin el asesor ciudadano dentro de su navegación. Al salir vuelve a la portada pública. El servidor protege el HTML privado y sus recursos, además de las APIs; ocultar controles en JavaScript no es la barrera de acceso.

### Asesor público

- **66 casos activos**, distribuidos en 10 tipos, y **169 entradas normativas** del proyecto de origen.
- Orientador de **22 nodos de preguntas**, con recorridos por situación y sugerencias de documentos que la persona puede revisar.
- Búsqueda por situaciones y sinónimos, tolerante a tildes, prefijos y errores de escritura; filtros por categoría, tipo y módulo, y sección de orientación para mujeres.
- Formularios condicionales, progreso de llenado, validación de campos y fechas, representación y contratos con varias partes.
- Vista previa, edición de datos, copia, TXT, **Word DOCX nativo en OOXML**, **PDF directo con fuentes Unicode locales** e impresión desde el navegador.
- Borradores opcionales en el navegador, duplicación, eliminación y copias JSON v2 que conservan los datos, el seguimiento y el documento de origen.
- Seguimiento de entrega, radicado, respuestas y decisiones; plazos orientativos según el caso y preparación del siguiente documento con los datos pertinentes prellenados.
- Letra al **100 %, 112 %, 125 % o 140 %**, alto contraste y lectura en voz alta cuando el dispositivo dispone de una voz local en español.
- Guías de presentación, calculadora de plazos y directorio de entidades.
- Aplicación web instalable en `/asesor/`, con caché limitada a recursos públicos; disponibilidad de instalación según navegador y HTTPS.
- Páginas de lectura sin JavaScript para los 66 casos en `/plantillas/`, cuatro guías públicas y metadatos para buscadores.
- Versión autónoma descargable: `app/static/asesor/descargas/el-memorialista-ciudadano-sin-internet.html`.

La redacción ciudadana funciona mediante plantillas y reglas locales. No requiere cuenta, clave de IA ni llamadas a Gemini. El service worker tiene alcance `/asesor/` y solo almacena el contenido público permitido; no intercepta el generador, el acceso ni las APIs. Los borradores persistentes se guardan por decisión de la persona y son accesibles a quienes usen el mismo perfil del navegador. El formulario también conserva una recuperación automática en la sesión de la pestaña; algunos navegadores la restauran tras cerrarse. El control de borrado permite limpiar esos datos.

Las copias JSON admiten el arreglo heredado de la versión de Claude y los formatos v1 y v2, hasta 200 documentos y 5 MB por archivo importado. La exportación actual usa v2 y conserva `seguimiento` y `origen`. Al importar, se omiten las copias idénticas; si un identificador coincide pero el contenido cambia, se conservan ambas versiones y sus enlaces de origen. Una entrada desconocida o inválida se rechaza completa. Si un historial anterior no se puede validar, la aplicación conserva sus bytes, bloquea la sobrescritura y permite descargar el original desde Mis documentos. Los errores de almacenamiento no se presentan como un guardado exitoso.

El seguimiento se consulta al abrir la aplicación. No envía notificaciones ni consulta expedientes oficiales. El cómputo usa los datos que registre la persona, festivos nacionales y reglas del caso; requiere revisar la notificación efectiva, las prórrogas, las suspensiones y las reglas especiales. La aplicación no presenta documentos ante autoridades ni determina el resultado de un trámite.

### Word y PDF ciudadanos

Word se genera como un paquete DOCX OOXML editable. El PDF incorpora las fuentes DejaVu y un mapa Unicode para conservar el texto al buscarlo o copiarlo. Se verificaron español, caracteres latinos extendidos, griego y cirílico, además de signos habituales, mediante pruebas de generación y extracción de texto. Esto no implica cobertura universal de todas las escrituras.

Si un carácter no está cubierto o requiere una composición que el exportador no realiza, la descarga PDF muestra un **error explícito** y ofrece Word o **Imprimir → Guardar como PDF**. No sustituye silenciosamente el nombre o texto por signos de interrogación. Word conserva los caracteres originales; la presentación final en Word o al imprimir depende de las fuentes disponibles en el dispositivo. La licencia de DejaVu se conserva en [app/static/asesor/licenses/DejaVu-LICENSE.txt](app/static/asesor/licenses/DejaVu-LICENSE.txt).

La comparación con el sitio publicado, las mejoras y las diferencias deliberadas se documentan en [docs/PARIDAD_ASESOR.md](docs/PARIDAD_ASESOR.md).

Se corrigieron ocho grupos de orientaciones jurídicas visibles. Las fuentes y el alcance están en [docs/ASESOR_CIUDADANO.md](docs/ASESOR_CIUDADANO.md). Esto no equivale a una auditoría integral de las 169 entradas normativas.

### Generador privado

Se conserva el catálogo de **26 tipos de escritos** y sus funciones: generación progresiva con IA, ajustes, análisis de estilo, revisión de requisitos, verificación de citas, auditoría de fidelidad, comparación de versiones, cálculos, términos, preparación de radicación, membretes, plantillas y exportaciones DOCX/PDF.

Las mejoras incluyen autenticación real, aislamiento de borradores por usuario, respaldo remoto con identificadores estables, versiones sin duplicados al repetir un guardado y recuperación explícita desde la nube que conserva un borrador local diferente.

## 2. Instalación local

Se verificó con **Python 3.12.14**. Node.js se utiliza únicamente para las pruebas del frontend y algunas comprobaciones de paridad; no hace falta para servir la aplicación.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -c constraints.txt
cp .env.example .env
```

En Windows, activa el entorno con `.venv\Scripts\Activate.ps1`. Completa `.env` como se indica en la siguiente sección y arranca:

```bash
uvicorn app.main:app --no-proxy-headers --reload --host 127.0.0.1 --port 8000
```

Abre `http://localhost:8000`. Mantén el mismo nombre de host en el navegador, `APP_BASE_URL` y las URLs de Auth: `localhost` y `127.0.0.1` son orígenes distintos.

El asesor público funciona aunque no hayas configurado Supabase o Gemini. El generador permanece cerrado si no puede verificar una sesión. No hay códigos universales, cuentas simuladas ni excepciones de autenticación en desarrollo.

## 3. Configurar Supabase

### Base de datos y Storage

Para un proyecto nuevo, ejecuta **`supabase/schema.sql`** en SQL Editor. Como alternativa, administra el esquema mediante las migraciones de `supabase/migrations`; no es necesario usar ambos métodos para la instalación inicial.

Para una instalación existente, conserva una copia de seguridad y aplica **`supabase/migrations/20261022010000_separacion_publica_privada_rls.sql`** antes de activar la nueva aplicación. Esta migración es idempotente y refuerza el esquema existente. No mueve archivos ni corrige retrospectivamente pertenencias o datos compartidos de forma incorrecta.

Se crea el bucket privado `archivos-privados`. Las tablas y los objetos se protegen mediante políticas RLS. Los perfiles no pueden autoasignarse otra firma, rol o cuota. Los detalles de pertenencias, colaboración y rutas están en [docs/SEGURIDAD_DATOS.md](docs/SEGURIDAD_DATOS.md).

El archivo **`supabase/tests/aislamiento_cuentas.sql`** permite comprobar las políticas con roles reales en una instancia de prueba. Crea datos temporales y termina en `ROLLBACK`. No se ejecutó sobre un proyecto Supabase real durante esta entrega.

### Auth y redirecciones

En Supabase Auth, habilita el proveedor de correo y configura la confirmación y el correo saliente para tu proyecto. Crea o invita la primera cuenta desde la administración de Supabase; la aplicación no incluye una contraseña inicial compartida.

En **URL Configuration**:

- Site URL: la URL canónica de tu instalación, por ejemplo `https://tu-dominio.example`.
- Redirect URLs: `https://tu-dominio.example/auth/callback` y `https://tu-dominio.example/auth/callback?mode=recovery`.
- Para desarrollo, añade las mismas dos rutas con `http://localhost:8000`.

Los enlaces y las recuperaciones dependen de esta lista. Usa las rutas del dominio real, sin permitir cualquier dominio. Consulta la [documentación oficial de redirecciones](https://supabase.com/docs/guides/auth/redirect-urls) y la de [acceso por contraseña](https://supabase.com/docs/guides/auth/passwords).

Por defecto, `AUTH_ALLOW_SIGNUP=False` oculta el registro. **Para acceso solo por invitación, desactiva además las altas públicas en Supabase Auth**: una opción de interfaz no sustituye la configuración del proveedor. Si quieres registro abierto, habilítalo en ambos lugares. Los enlaces de acceso para usuarios existentes y la recuperación de contraseña están implementados.

### Variables del servidor

| Variable | Uso |
| --- | --- |
| `SUPABASE_URL` | URL del proyecto que autentica y almacena los datos. |
| `SUPABASE_ANON_KEY` | Clave anon o publishable del mismo proyecto; se entrega al cliente y depende de RLS. |
| `APP_BASE_URL` | Origen canónico, sin barra final: debe coincidir con la web visitada. También se usa para canonical, Open Graph y sitemap públicos. |
| `AUTH_ALLOW_SIGNUP` | Visibilidad del registro, desactivado por defecto. |
| `SUPABASE_STORAGE_BUCKET` | `archivos-privados`, el nombre creado por el SQL incluido. |
| `SUPABASE_SERVICE_ROLE_KEY` | Secreto exclusivo del servidor para operaciones administrativas como eliminar una cuenta. No se necesita para iniciar sesión. |
| `GEMINI_API_KEY` | Clave del proveedor para la generación privada con IA. |
| `GROQ_API_KEY` | Respaldo opcional de IA. |
| `ENVIRONMENT` | `development` en HTTP local; `production` en el despliegue HTTPS. |

El archivo `.env.example` incluye las demás opciones. No se necesita `SUPABASE_JWT_SECRET`: el servidor valida los tokens con Supabase Auth. Las claves de servicio y de IA nunca deben colocarse en el HTML o en archivos públicos. Ninguna clave real está incluida en esta entrega.

Los modelos de Gemini configurados en el proyecto se conservan en `.env.example`. Su uso depende del acceso, la cuota y la disponibilidad del proyecto proveedor. Las pruebas de esta entrega no consumieron generaciones reales de IA.

## 4. Datos locales, nube y actualización desde una versión anterior

Los borradores y el seguimiento del **asesor público** permanecen en el navegador y tienen su propia copia JSON. No se sincronizan con Supabase ni se transfieren al generador al iniciar sesión. El **generador privado** tiene almacenamiento por cuenta y operaciones explícitas de respaldo y recuperación en Supabase. Los dos formatos de copia pertenecen a espacios distintos.

El generador separa `localStorage` e IndexedDB mediante el identificador de la cuenta validada. Al cambiar de cuenta se reinicializa el espacio de trabajo. Esto evita mezclar borradores entre sesiones de la aplicación; no cifra los archivos del dispositivo ni sustituye una cuenta de sistema separada en un ordenador compartido.

Antes de actualizar una instalación antigua, descarga su copia de seguridad. Los datos guardados por la versión anterior en claves globales no se asignan automáticamente a la primera persona que entre. El usuario puede restaurar su propia copia desde el generador.

- **Descargar copia de seguridad** conserva datos locales, perfil, imágenes, plantilla e historial en el formato de la aplicación.
- **Respaldar mis datos en la nube** guarda los recursos admitidos y los escritos del usuario. El guardado comprueba los errores devueltos por Supabase.
- **Recuperar mis escritos de la nube** descarga escritos propios de forma paginada. Si encuentra un borrador local distinto, crea una copia adicional en vez de sobrescribirlo. Esta función recupera escritos; no reconstruye automáticamente todo el diseño local del membrete o de la plantilla.
- **Exportar mis datos de la nube (JSON)** exporta los registros accesibles del usuario. El archivo declara que no contiene los binarios de Storage.
- Borrar el historial local no elimina automáticamente el respaldo remoto. La interfaz lo indica.

La eliminación de cuenta requiere configuración administrativa y se detiene si afectaría aportes ajenos en un expediente compartido. No se informa éxito si falla un paso del proveedor.

## 5. Despliegue

Este proyecto requiere un **servidor Python**. Publicar únicamente `app/static` no proporciona autenticación, IA ni las APIs privadas.

### Render

El archivo `render.yaml` define un servicio web Python, instala las versiones comprobadas mediante `constraints.txt` y utiliza `/api/health` como comprobación de disponibilidad. La configuración sigue la [referencia de Blueprints de Render](https://render.com/docs/blueprint-spec).

1. Sube el proyecto a tu repositorio de aplicación y conéctalo como Blueprint.
2. Completa las variables solicitadas, especialmente Supabase, Gemini y `APP_BASE_URL`.
3. Aplica el esquema o la migración que corresponda y configura las URLs de Auth para el dominio final.
4. Comprueba el acceso con una cuenta de prueba, la recuperación por correo, el aislamiento entre cuentas y una generación real antes de introducir documentos de trabajo.

El manifiesto no contrata un plan de pago. No se realizó un despliegue como parte de esta entrega.

### Proxies e IP del cliente

Los arranques incluidos usan `--no-proxy-headers` para que Uvicorn conserve la IP de la conexión real. La aplicación decide si puede leer una cabecera de IP después de comprobar el proxy que la envió; no se activa confianza automática por estar alojada en Render.

Conserva `PROXY_IPS_CONFIABLES=` vacío, `PROXIES_CONFIABLES=0` e `IP_CABECERA_CONFIABLE=` vacía si no se ha comprobado la configuración del alojamiento. Detrás de un proxy, eso puede agrupar a varios visitantes bajo la IP de ese proxy para los límites por IP. Para distinguirlos, configura las IPs/CIDR reales en `PROXY_IPS_CONFIABLES` y el número exacto de saltos de `X-Forwarded-For` en `PROXIES_CONFIABLES`; como alternativa, usa una cabecera exclusiva que el proxy reemplace, indicada por `IP_CABECERA_CONFIABLE`, manteniendo los saltos en cero. Los dos modos son excluyentes. La guía de integración detalla las comprobaciones.

### Docker

También se incluye un `Dockerfile` con usuario sin privilegios:

```bash
docker build -t el-memorialista:3 .
docker run --rm --env-file .env -p 8000:8000 el-memorialista:3
```

Para acceso local por HTTP usa `ENVIRONMENT=development`. En un despliegue HTTPS usa `ENVIRONMENT=production`, el origen real y un proxy correctamente configurado. Las cookies de producción requieren HTTPS. La construcción Docker no se ejecutó en esta entrega.

Las cuotas actuales se mantienen en memoria **por proceso**. El arranque incluido usa un único proceso. Si escalas a varias réplicas o necesitas conservar cuotas tras reinicios, sustituye ese almacén por uno compartido antes de asumir un límite global persistente.

## 6. Pruebas y mantenimiento

```bash
python -m pip install -r requirements-dev.txt -c constraints.txt
python -m pytest -q
node tests/test_asesor_engine.cjs
node tests/test_asesor_features.cjs
node tests/test_asesor_respaldo.cjs
node tests/test_auth_client.cjs
node tests/test_asesor_pwa.cjs
```

El detalle de la ejecución actual está en [docs/VERIFICACION_INTEGRADA.md](docs/VERIFICACION_INTEGRADA.md): **515 pruebas aprobadas, 0 fallos y 1 prueba manual heredada omitida**. [docs/VERIFICACION.md](docs/VERIFICACION.md) conserva el historial de etapas anteriores; sus cifras no se suman a las actuales. La guía [docs/INTEGRACION_COMPLETA.md](docs/INTEGRACION_COMPLETA.md) explica la configuración y cómo ejecutar el recorrido de navegador con Playwright. [PROMPT_PARA_ANTIGRAVITY.md](PROMPT_PARA_ANTIGRAVITY.md) contiene el encargo de incorporación al proyecto existente.

El evaluador de escritos admite simulación sin cuota:

```bash
python scripts/evaluar.py --mock --limite 3
```

Para evaluar generaciones reales, configura las claves de IA y proporciona una sesión válida en la variable `MEMORIALISTA_ACCESS_TOKEN`, sin registrarla ni incorporarla al repositorio:

```bash
python scripts/evaluar.py --servidor http://localhost:8000 --tipo tutela --limite 1
```

La evaluación real consume cuota y el modo simulado no demuestra la calidad de respuestas de un proveedor real. Ante cambios futuros de modelo, prompt o guía, ejecuta la evaluación y revisa cualquier regresión antes de desplegar.

Al modificar datos, estilos o lógica del asesor, regenera el catálogo de páginas, la versión autónoma y los recursos de la aplicación instalable:

```bash
node scripts/build_asesor_paginas.cjs
python scripts/build_asesor_offline.py
python scripts/build_asesor_pwa.py
```

Los recursos generados se incluyen en la entrega: Node no es necesario en el servidor de producción. La PWA requiere HTTPS o localhost y una primera carga con conexión. Su copia pública permite preparar documentos sin internet; iniciar sesión, utilizar el generador privado y abrir sitios oficiales requieren conexión. La instalación concreta depende del navegador. El HTML autónomo sigue disponible como alternativa.

Configura `APP_BASE_URL` con el origen real antes de publicar el sitemap. Si falta o es inválido, las páginas continúan funcionando, pero omiten URLs canónicas absolutas y `/sitemap.xml` responde 503 en lugar de anunciar un dominio inventado. `robots.txt` no sustituye los controles de autenticación del servidor.

Los scripts `update_index_html.py`, `update_verificador_frontend.py` y `build_catalog.py` son utilidades históricas de extracción o migración, no pasos de instalación de v3. Sus guardias impiden sobreescribir la arquitectura actual con código antiguo.

### Archivos principales

| Archivo o directorio | Responsabilidad |
| --- | --- |
| `app/main.py` | Rutas, frontera de acceso y cabeceras. |
| `app/static/index.html` y `app/static/asesor/` | Experiencia ciudadana pública. |
| `app/routers/asesor_pwa.py` | Entrada e instalación pública, separadas del espacio privado. |
| `app/routers/asesor_paginas.py` | Páginas de plantillas, guías y recursos para buscadores. |
| `app/static/login.html` y `app/static/auth/` | Inicio de sesión y puente de sesión. |
| `app/private/generador.html` | Generador entregado solo con sesión válida. |
| `app/private/auditor.js` | Auditor del espacio profesional. |
| `app/services/` y `app/routers/` | IA, cálculos, auditoría, documentos y autenticación. |
| `supabase/` | Esquema, migraciones y pruebas de aislamiento. |
| `tests/` | Regresiones del servidor y los clientes. |

## 7. Identidad de la entrega y dependencias

La interfaz y su información legal utilizan la identidad **El Memorialista**. El responsable del proyecto manifestó contar con autorización del titular para retirar las marcas y los créditos anteriores; se aplicó esa instrucción sin atribuir al ajuste una reescritura del motor ni ampliar el alcance del permiso indicado.

La arquitectura, las funciones conservadas y el alcance de las correcciones se documentan en [docs/ASESOR_CIUDADANO.md](docs/ASESOR_CIUDADANO.md). El SDK Supabase incluido conserva su licencia MIT por separado, al igual que los avisos de otras dependencias que correspondan.

Las fuentes locales utilizadas en el PDF conservan su propia licencia DejaVu/Bitstream Vera. Estos avisos de dependencias se distribuyen con el código y no se eliminan al cambiar la identidad de la aplicación.
