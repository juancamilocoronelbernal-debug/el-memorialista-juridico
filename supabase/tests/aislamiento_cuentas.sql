-- PRUEBA DE INTEGRACIÓN RLS, SIN DATOS PERSISTENTES.
-- Ejecutar DESPUÉS de schema.sql / migraciones en una instancia Supabase DE PRUEBA
-- usando SQL Editor como propietario. Todo termina en ROLLBACK.
-- Cubre permisos PostgreSQL reales: anon, authenticated y gestión administrativa.
BEGIN;
SET LOCAL statement_timeout = '30s';

CREATE TEMP TABLE qa_identidades (
    etiqueta TEXT PRIMARY KEY, usuario UUID DEFAULT gen_random_uuid(), firma UUID,
    cliente UUID DEFAULT gen_random_uuid(), caso UUID DEFAULT gen_random_uuid(),
    documento UUID DEFAULT gen_random_uuid(), compartido UUID DEFAULT gen_random_uuid(),
    caso_equipo UUID DEFAULT gen_random_uuid(), documento_equipo UUID DEFAULT gen_random_uuid()
) ON COMMIT DROP;
INSERT INTO qa_identidades (etiqueta) VALUES ('alice'), ('bob'), ('colaborador');
INSERT INTO auth.users (id, email, raw_user_meta_data, raw_app_meta_data, created_at, updated_at)
    SELECT usuario, usuario::text || '@example.invalid', '{"nombre":"QA aislamiento"}'::jsonb,
           '{}'::jsonb, now(), now() FROM qa_identidades;
UPDATE qa_identidades q SET firma = p.firma_id FROM public.perfiles p WHERE p.id = q.usuario;
GRANT SELECT ON qa_identidades TO authenticated, anon;

CREATE FUNCTION pg_temp.comprobar(condicion BOOLEAN, mensaje TEXT)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    IF condicion IS DISTINCT FROM true THEN RAISE EXCEPTION 'FALLO QA: %', mensaje; END IF;
END;
$$;
CREATE FUNCTION pg_temp.denegado(sentencia TEXT)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE sentencia;
    EXCEPTION WHEN insufficient_privilege THEN
        RETURN;
    END;
    RAISE EXCEPTION 'FALLO QA: operación privilegiada aceptada: %', sentencia;
END;
$$;
GRANT EXECUTE ON FUNCTION pg_temp.comprobar(BOOLEAN, TEXT), pg_temp.denegado(TEXT) TO authenticated, anon;

-- Expedientes personales de dos usuarios, creados por el propietario para fixture.
INSERT INTO public.clientes (id, user_id, numero_documento, nombre_razon_social)
    SELECT cliente, usuario, 'QA', 'Cliente privado ' || etiqueta FROM qa_identidades;
INSERT INTO public.casos (id, user_id, cliente_id, nombre_caso)
    SELECT caso, usuario, cliente, 'Caso privado ' || etiqueta FROM qa_identidades;
INSERT INTO public.documentos (id, caso_id, tipo, titulo, creado_por)
    SELECT documento, caso, 'memorial', 'Documento privado ' || etiqueta, usuario FROM qa_identidades;
INSERT INTO public.documentos (id, firma_id, tipo, titulo, creado_por)
    SELECT compartido, firma, 'memorial', 'Documento compartido ' || etiqueta, usuario FROM qa_identidades;

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims', json_build_object('sub', usuario, 'role', 'authenticated')::text, true),
       set_config('request.jwt.claim.sub', usuario::text, true)
    FROM qa_identidades WHERE etiqueta = 'alice';

SELECT pg_temp.comprobar((SELECT count(*) = 1 FROM public.documentos
    WHERE id = (SELECT documento FROM qa_identidades WHERE etiqueta = 'alice')), 'Alice ve su escrito');
SELECT pg_temp.comprobar((SELECT count(*) = 0 FROM public.documentos
    WHERE id = (SELECT documento FROM qa_identidades WHERE etiqueta = 'bob')), 'Alice no ve datos de Bob');
SELECT pg_temp.comprobar((SELECT count(*) = 0 FROM public.clientes
    WHERE id = (SELECT cliente FROM qa_identidades WHERE etiqueta = 'bob')), 'Alice no ve cliente de Bob');
UPDATE public.documentos SET texto = 'Actualización legítima' WHERE id = (SELECT documento FROM qa_identidades WHERE etiqueta = 'alice');
SELECT pg_temp.comprobar((SELECT texto = 'Actualización legítima' FROM public.documentos
    WHERE id = (SELECT documento FROM qa_identidades WHERE etiqueta = 'alice')), 'Propietario actualiza su escrito');

-- El upsert de datos personales del frontend sigue funcionando.
INSERT INTO public.perfiles (id, email, nombre_completo)
    SELECT usuario, usuario::text || '@example.invalid', 'Perfil actualizado'
    FROM qa_identidades WHERE etiqueta = 'alice'
ON CONFLICT (id) DO UPDATE SET nombre_completo = EXCLUDED.nombre_completo;
SELECT pg_temp.comprobar((SELECT nombre_completo = 'Perfil actualizado' FROM public.perfiles
    WHERE id = (SELECT usuario FROM qa_identidades WHERE etiqueta = 'alice')), 'Upsert seguro del perfil');

SELECT pg_temp.denegado(format('UPDATE public.perfiles SET firma_id = %L WHERE id = %L',
    (SELECT firma FROM qa_identidades WHERE etiqueta = 'bob'), (SELECT usuario FROM qa_identidades WHERE etiqueta = 'alice')));
SELECT pg_temp.denegado(format('UPDATE public.perfiles SET limite_diario = 100000 WHERE id = %L',
    (SELECT usuario FROM qa_identidades WHERE etiqueta = 'alice')));
SELECT pg_temp.denegado(format('SELECT public.administrar_membresia(%L, %L, ''admin'')',
    (SELECT usuario FROM qa_identidades WHERE etiqueta = 'alice'), (SELECT firma FROM qa_identidades WHERE etiqueta = 'bob')));
SELECT pg_temp.denegado(format('INSERT INTO public.clientes (user_id, numero_documento, nombre_razon_social) VALUES (%L, ''QA'', ''Falsificado'')',
    (SELECT usuario FROM qa_identidades WHERE etiqueta = 'bob')));
SELECT pg_temp.denegado(format('INSERT INTO public.clientes (user_id, firma_id, numero_documento, nombre_razon_social) VALUES (%L, %L, ''QA'', ''Firma ajena'')',
    (SELECT usuario FROM qa_identidades WHERE etiqueta = 'alice'), (SELECT firma FROM qa_identidades WHERE etiqueta = 'bob')));
SELECT pg_temp.denegado(format('INSERT INTO public.casos (user_id, cliente_id, nombre_caso) VALUES (%L, %L, ''Cruce prohibido'')',
    (SELECT usuario FROM qa_identidades WHERE etiqueta = 'alice'), (SELECT cliente FROM qa_identidades WHERE etiqueta = 'bob')));
SELECT pg_temp.denegado(format('INSERT INTO public.documentos (creado_por, caso_id, tipo, titulo) VALUES (%L, %L, ''memorial'', ''Cruce prohibido'')',
    (SELECT usuario FROM qa_identidades WHERE etiqueta = 'alice'), (SELECT caso FROM qa_identidades WHERE etiqueta = 'bob')));
SELECT pg_temp.denegado(format('UPDATE public.documentos SET creado_por = %L WHERE id = %L',
    (SELECT usuario FROM qa_identidades WHERE etiqueta = 'bob'), (SELECT documento FROM qa_identidades WHERE etiqueta = 'alice')));
INSERT INTO public.versiones (documento_id, version, texto, creado_por)
    SELECT documento, 1, 'Versión válida', usuario FROM qa_identidades WHERE etiqueta = 'alice';
SELECT pg_temp.denegado(format('INSERT INTO public.versiones (documento_id, version, texto, creado_por) VALUES (%L, 2, ''Falso'', %L)',
    (SELECT documento FROM qa_identidades WHERE etiqueta = 'alice'), (SELECT usuario FROM qa_identidades WHERE etiqueta = 'bob')));
SELECT pg_temp.denegado(format('INSERT INTO public.versiones (documento_id, version, texto, creado_por) VALUES (%L, 2, ''Ajeno'', %L)',
    (SELECT documento FROM qa_identidades WHERE etiqueta = 'bob'), (SELECT usuario FROM qa_identidades WHERE etiqueta = 'alice')));
SELECT pg_temp.denegado('UPDATE public.versiones SET texto = ''Alteración de versión''');

INSERT INTO storage.objects (bucket_id, name)
    SELECT 'archivos-privados', 'logo/' || usuario::text || '/qa.png' FROM qa_identidades WHERE etiqueta = 'alice';
SELECT pg_temp.denegado(format('UPDATE storage.objects SET name = %L WHERE bucket_id = ''archivos-privados'' AND name = %L',
    'logo/' || (SELECT usuario::text FROM qa_identidades WHERE etiqueta = 'bob') || '/qa.png',
    'logo/' || (SELECT usuario::text FROM qa_identidades WHERE etiqueta = 'alice') || '/qa.png'));
SELECT pg_temp.denegado(format('INSERT INTO storage.objects (bucket_id, name) VALUES (''archivos-privados'', %L)',
    'logo/' || (SELECT usuario::text FROM qa_identidades WHERE etiqueta = 'bob') || '/intruso.png'));

RESET ROLE;
-- La colaboración se habilita únicamente mediante acción administrativa.
SELECT public.administrar_membresia(
    (SELECT usuario FROM qa_identidades WHERE etiqueta = 'colaborador'),
    (SELECT firma FROM qa_identidades WHERE etiqueta = 'alice'), 'abogado');
-- Caso de un miembro, con un documento ajeno y una versión ajena de su escrito.
INSERT INTO public.casos (id, user_id, firma_id, nombre_caso)
    SELECT caso_equipo, usuario, (SELECT firma FROM qa_identidades WHERE etiqueta = 'alice'), 'Caso de equipo'
    FROM qa_identidades WHERE etiqueta = 'colaborador';
UPDATE public.documentos SET caso_id = (SELECT caso_equipo FROM qa_identidades WHERE etiqueta = 'colaborador')
    WHERE id = (SELECT compartido FROM qa_identidades WHERE etiqueta = 'alice');
INSERT INTO public.documentos (id, caso_id, firma_id, tipo, titulo, creado_por)
    SELECT documento_equipo, caso_equipo, (SELECT firma FROM qa_identidades WHERE etiqueta = 'alice'),
           'memorial', 'Escrito con aportes de otro miembro', usuario
    FROM qa_identidades WHERE etiqueta = 'colaborador';
INSERT INTO public.versiones (documento_id, version, texto, creado_por)
    SELECT (SELECT documento_equipo FROM qa_identidades WHERE etiqueta = 'colaborador'),
           1, 'Aporte de Alice', usuario FROM qa_identidades WHERE etiqueta = 'alice';
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims', json_build_object('sub', usuario, 'role', 'authenticated')::text, true),
       set_config('request.jwt.claim.sub', usuario::text, true)
    FROM qa_identidades WHERE etiqueta = 'colaborador';
SELECT pg_temp.comprobar((SELECT count(*) = 1 FROM public.documentos
    WHERE id = (SELECT compartido FROM qa_identidades WHERE etiqueta = 'alice')), 'Colaborador ve escrito de firma');
SELECT pg_temp.comprobar((SELECT count(*) = 0 FROM public.documentos
    WHERE id = (SELECT documento FROM qa_identidades WHERE etiqueta = 'alice')), 'Colaborador no ve escrito personal');
SELECT pg_temp.comprobar((SELECT count(*) = 0 FROM storage.objects
    WHERE name = 'logo/' || (SELECT usuario::text FROM qa_identidades WHERE etiqueta = 'alice') || '/qa.png'), 'Firma personal no compartida');
SELECT pg_temp.denegado(format('UPDATE public.perfiles SET rol = ''admin'' WHERE id = %L',
    (SELECT usuario FROM qa_identidades WHERE etiqueta = 'colaborador')));
UPDATE public.documentos SET texto = 'Edición de equipo' WHERE id = (SELECT compartido FROM qa_identidades WHERE etiqueta = 'alice');
SELECT pg_temp.comprobar((SELECT texto = 'Edición de equipo' FROM public.documentos
    WHERE id = (SELECT compartido FROM qa_identidades WHERE etiqueta = 'alice')), 'Colaboración legítima');
DELETE FROM public.documentos WHERE id = (SELECT compartido FROM qa_identidades WHERE etiqueta = 'alice');
SELECT pg_temp.comprobar((SELECT count(*) = 1 FROM public.documentos
    WHERE id = (SELECT compartido FROM qa_identidades WHERE etiqueta = 'alice')), 'Solo propietario o admin elimina escrito compartido');
SELECT pg_temp.comprobar(public.puede_acceder_archivo_privado('despacho/' ||
    (SELECT firma::text FROM qa_identidades WHERE etiqueta = 'alice') || '/logo.png', false), 'Colaborador lee recurso de despacho');
SELECT pg_temp.comprobar(NOT public.puede_acceder_archivo_privado('despacho/' ||
    (SELECT firma::text FROM qa_identidades WHERE etiqueta = 'alice') || '/logo.png', true), 'Colaborador no altera recurso de despacho');

DELETE FROM public.documentos WHERE id = (SELECT documento_equipo FROM qa_identidades WHERE etiqueta = 'colaborador');
SELECT pg_temp.comprobar((SELECT count(*) = 1 FROM public.documentos
    WHERE id = (SELECT documento_equipo FROM qa_identidades WHERE etiqueta = 'colaborador')),
    'Autor no borra versiones ajenas en cascada');
DELETE FROM public.casos WHERE id = (SELECT caso_equipo FROM qa_identidades WHERE etiqueta = 'colaborador');
SELECT pg_temp.comprobar((SELECT count(*) = 1 FROM public.casos
    WHERE id = (SELECT caso_equipo FROM qa_identidades WHERE etiqueta = 'colaborador')),
    'Autor del caso no borra documentos ajenos en cascada');
-- El administrador de la firma sí conserva la gestión del expediente completo.
SELECT set_config('request.jwt.claims', json_build_object('sub', usuario, 'role', 'authenticated')::text, true),
       set_config('request.jwt.claim.sub', usuario::text, true)
    FROM qa_identidades WHERE etiqueta = 'alice';
DELETE FROM public.casos WHERE id = (SELECT caso_equipo FROM qa_identidades WHERE etiqueta = 'colaborador');
SELECT pg_temp.comprobar((SELECT count(*) = 0 FROM public.casos
    WHERE id = (SELECT caso_equipo FROM qa_identidades WHERE etiqueta = 'colaborador')),
    'Administrador conserva gestión de borrado del expediente compartido');

RESET ROLE;
SET LOCAL ROLE anon;
SELECT set_config('request.jwt.claims', '{"role":"anon"}', true), set_config('request.jwt.claim.sub', '', true);
SELECT pg_temp.denegado('SELECT * FROM public.documentos');
SELECT pg_temp.denegado('SELECT * FROM public.clientes');
SELECT pg_temp.denegado('SELECT * FROM public.perfiles');
RESET ROLE;
SELECT 'Pruebas RLS completadas; se revierte la transacción.' AS resultado;
ROLLBACK;
