# Frontera de datos del espacio privado

## Qué cambia en la base de datos

La migración `supabase/migrations/20261022010000_separacion_publica_privada_rls.sql` se aplica sobre el esquema existente y puede ejecutarse más de una vez. No borra expedientes ni reasigna usuarios. El esquema completo `supabase/schema.sql` incorpora los mismos cambios para instalaciones nuevas.

- Las tablas `firmas`, `perfiles`, `clientes`, `casos`, `documentos` y `versiones` tienen RLS y no conceden acceso al rol `anon`.
- Cada persona puede editar su perfil, pero no cambiar su `firma_id`, su rol o sus cuotas desde el navegador. El alta de Supabase crea su despacho personal mediante un trigger. Nunca se toma el rol o la firma de `user_metadata`.
- El autor, el propietario y el ámbito personal/compartido de cada registro son inmutables para los clientes web. Las inserciones exigen que el autor sea el usuario autenticado.
- Un caso solo puede vincular un cliente visible del mismo ámbito. Un documento solo puede vincular un caso visible del mismo ámbito. Las versiones requieren acceso al documento y autoría propia.
- Las versiones son instantáneas: se crean y consultan, pero no se sobrescriben. El autor puede eliminar su documento si no contiene versiones de otra persona. El borrado de un caso comprueba también los documentos y versiones que se eliminarían en cascada. El administrador del despacho conserva la gestión del expediente compartido; un miembro no puede aprovechar una cascada para borrar aportes de otros.
- Los miembros de una firma conservan acceso a los registros expresamente compartidos con ella. Los registros personales, con `firma_id = NULL`, no se comparten por pertenecer a un despacho.
- Las funciones `SECURITY DEFINER` fijan `search_path = ''` y sus permisos de ejecución se restringen explícitamente.

Estas medidas controlan el acceso en PostgreSQL, incluso si alguien intenta llamar directamente a la API de Supabase. La protección de rutas web y de las APIs de FastAPI sigue siendo necesaria y se implementa por separado.

## Administración de un equipo

No se ha añadido una interfaz de invitaciones. La pertenencia a un despacho se configura deliberadamente desde SQL Editor o desde un backend con la clave `service_role`, después de comprobar la identidad y la autorización de sus miembros.

```sql
-- Sustituir los valores entre <...> por UUID reales y verificados.
SELECT public.administrar_membresia(
  '<uuid-del-usuario>'::uuid,
  '<uuid-del-despacho>'::uuid,
  'abogado'
);
```

Los roles admitidos son `admin`, `abogado` y `asistente`. El navegador no tiene permiso para ejecutar esta función. La clave de servicio nunca debe incluirse en JavaScript público. Reasignar una persona cambia su acceso futuro a la firma; no traslada automáticamente sus documentos personales ni los documentos de la firma anterior. Los cambios de propiedad o de ámbito requieren una operación administrativa explícita.

## Archivos privados

El bucket `archivos-privados` permanece privado. Los archivos personales admitidos usan las rutas:

```text
logo/<uuid-usuario>/...
firma/<uuid-usuario>/...
plantilla/<uuid-usuario>/...
```

Los recursos compartidos usan `despacho/<uuid-despacho>/...`. Los miembros pueden leerlos y los administradores del despacho pueden escribirlos. La política de actualización verifica tanto el objeto de origen como su ruta de destino. No se admite mover un objeto a la carpeta de otra cuenta.

La migración limita las cargas a PNG, JPEG, WebP, DOCX y PDF, con un máximo de 10 MiB por archivo. Si una instalación anterior guardó recursos compartidos bajo una ruta diferente, un administrador debe reorganizar esos objetos hacia el formato `despacho/<uuid-despacho>/...`; la migración no mueve archivos por sí sola.

## Verificación reproducible

Los contratos estáticos se ejecutan sin una base de datos:

```bash
pytest -q tests/test_security_sql.py
```

La prueba `supabase/tests/aislamiento_cuentas.sql` comprueba acceso permitido y denegado con los roles reales `authenticated` y `anon`. Crea tres usuarios temporales, verifica aislamiento entre cuentas, colaboración autorizada, inmutabilidad de permisos, relaciones de expedientes, versiones y rutas de Storage, y termina en `ROLLBACK`. Ejecutarla en SQL Editor, como propietario, sobre una **instancia de prueba** con el esquema aplicado. No necesita pgTAP.

Los tests de contrato no equivalen a ejecutar las políticas en tu proyecto Supabase. Antes de activar un despliegue con datos reales, ejecutar la prueba transaccional y comprobar la configuración de Auth, correo y URLs de redirección del proyecto destino. Las políticas no reparan retroactivamente pertenencias o datos incorrectamente compartidos antes de aplicar la migración.

## Documentación técnica de referencia

- [Supabase: Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security).
- [PostgreSQL: CREATE POLICY y semántica de USING / WITH CHECK](https://www.postgresql.org/docs/current/sql-createpolicy.html).
