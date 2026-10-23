-- Firma por enlace: pruebas reales de PostgreSQL, permisos y transiciones.
-- Ejecutar como propietario en un proyecto Supabase DE PRUEBA después de las
-- migraciones. No requiere claves de API ni envía mensajes. Todo hace ROLLBACK.
BEGIN;
SET LOCAL statement_timeout='30s';

CREATE TEMP TABLE qa_firma_usuarios(label text PRIMARY KEY,user_id uuid DEFAULT gen_random_uuid()) ON COMMIT DROP;
INSERT INTO qa_firma_usuarios(label) VALUES('alice'),('bob');
INSERT INTO auth.users(id,email,raw_user_meta_data,raw_app_meta_data,created_at,updated_at)
SELECT user_id,user_id::text||'@example.invalid','{"nombre":"QA firma"}'::jsonb,'{}'::jsonb,now(),now()
FROM qa_firma_usuarios;

CREATE TEMP TABLE qa_firma_casos(
    label text PRIMARY KEY,id uuid,old_hash text NOT NULL,new_hash text NOT NULL,original_hash text
) ON COMMIT DROP;
INSERT INTO qa_firma_casos(label,old_hash,new_hash)
SELECT label,encode(sha256(convert_to('fixture-old-'||label,'UTF8')),'hex'),
       encode(sha256(convert_to('fixture-new-'||label,'UTF8')),'hex')
FROM (VALUES('rotation'),('cancelled'),('expired')) cases(label);
GRANT SELECT ON qa_firma_usuarios TO authenticated,anon,service_role;
GRANT SELECT,UPDATE ON qa_firma_casos TO authenticated,service_role;

CREATE FUNCTION pg_temp.assert_firma(ok boolean,message text)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN IF ok IS DISTINCT FROM true THEN RAISE EXCEPTION 'FAIL FIRMA: %',message; END IF; END;
$$;
CREATE FUNCTION pg_temp.expect_firma_error(sql_text text,expected_code text,expected_message text DEFAULT NULL)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE sql_text;
    EXCEPTION WHEN OTHERS THEN
        IF SQLSTATE=expected_code AND (expected_message IS NULL OR position(expected_message in SQLERRM)>0) THEN
            RETURN;
        END IF;
        RAISE EXCEPTION 'FAIL FIRMA: unexpected exception % / %, expected % / %',
                        SQLSTATE,SQLERRM,expected_code,expected_message;
    END;
    RAISE EXCEPTION 'FAIL FIRMA: operation was not rejected: %',sql_text;
END;
$$;
GRANT EXECUTE ON FUNCTION pg_temp.assert_firma(boolean,text),pg_temp.expect_firma_error(text,text,text)
TO authenticated,anon,service_role;

-- El propietario crea usando su JWT; el owner no se acepta como parámetro.
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims',json_build_object('sub',user_id,'role','authenticated')::text,true),
       set_config('request.jwt.claim.sub',user_id::text,true)
FROM qa_firma_usuarios WHERE label='alice';

DO $$
DECLARE fixture record; result jsonb;
BEGIN
    FOR fixture IN SELECT * FROM qa_firma_casos LOOP
        result=public.despacho_crear_firma('Acuerdo de prueba '||fixture.label,
            'Documento completo e inmutable de prueba.','Persona de prueba','firmante@example.invalid',fixture.old_hash,7);
        PERFORM pg_temp.assert_firma(NOT (result ? 'token_hash') AND NOT (result ? 'owner_id'),'Creation response omits secret hash and owner');
        UPDATE qa_firma_casos SET id=(result->>'id')::uuid,original_hash=result->>'document_hash'
        WHERE label=fixture.label;
    END LOOP;
END;
$$;
SELECT pg_temp.assert_firma((SELECT count(*)=3 FROM public.despacho_firmas),'Owner reads its three requests');
SELECT pg_temp.assert_firma((SELECT bool_and(owner_id=(SELECT user_id FROM qa_firma_usuarios WHERE label='alice'))
    FROM public.despacho_firmas),'RPC fixes owner from auth.uid');

-- Un propietario tampoco puede editar el original, forjar el estado o firmar
-- llamando al RPC administrativo desde el navegador.
SELECT pg_temp.expect_firma_error(format('UPDATE public.despacho_firmas SET document_text=''Alterado'' WHERE id=%L',
    (SELECT id FROM qa_firma_casos WHERE label='rotation')),'42501');
SELECT pg_temp.expect_firma_error(format('UPDATE public.despacho_firmas SET status=''signed'' WHERE id=%L',
    (SELECT id FROM qa_firma_casos WHERE label='rotation')),'42501');
SELECT pg_temp.expect_firma_error(format('SELECT public.despacho_ver_firma(%L)',
    (SELECT old_hash FROM qa_firma_casos WHERE label='rotation')),'42501');
SELECT pg_temp.expect_firma_error(format(
    'SELECT public.despacho_aceptar_firma(%L,''Persona de prueba'',''firmante@example.invalid'',''192.0.2.1'',''QA'',true)',
    (SELECT old_hash FROM qa_firma_casos WHERE label='rotation')),'42501');

-- Otra cuenta no lee, cancela ni rota una solicitud ajena.
SELECT set_config('request.jwt.claims',json_build_object('sub',user_id,'role','authenticated')::text,true),
       set_config('request.jwt.claim.sub',user_id::text,true)
FROM qa_firma_usuarios WHERE label='bob';
SELECT pg_temp.assert_firma((SELECT count(*)=0 FROM public.despacho_firmas),'Other account cannot read requests');
SELECT pg_temp.expect_firma_error(format('SELECT public.despacho_cancelar_firma(%L)',
    (SELECT id FROM qa_firma_casos WHERE label='rotation')),'P0001','NOT_FOUND');
SELECT pg_temp.expect_firma_error(format('SELECT public.despacho_renovar_enlace_firma(%L,%L)',
    (SELECT id FROM qa_firma_casos WHERE label='rotation'),
    (SELECT new_hash FROM qa_firma_casos WHERE label='rotation')),'P0001','NOT_FOUND');

-- Los RPC públicos no se conceden a anon, ni siquiera conociendo un hash.
RESET ROLE;
SET LOCAL ROLE anon;
SELECT pg_temp.expect_firma_error('SELECT * FROM public.despacho_firmas','42501');
SELECT pg_temp.expect_firma_error('SELECT public.despacho_ver_firma(repeat(''a'',64))','42501');
SELECT pg_temp.expect_firma_error(
    'SELECT public.despacho_aceptar_firma(repeat(''a'',64),''Persona'',''firmante@example.invalid'',''192.0.2.1'',''QA'',true)',
    '42501');
SELECT pg_temp.expect_firma_error(
    'SELECT public.despacho_crear_firma(''Prueba'',''Documento'',''Persona'',''firmante@example.invalid'',repeat(''a'',64),7)',
    '42501');

RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims',json_build_object('sub',user_id,'role','authenticated')::text,true),
       set_config('request.jwt.claim.sub',user_id::text,true)
FROM qa_firma_usuarios WHERE label='alice';
SELECT public.despacho_renovar_enlace_firma(id,new_hash) FROM qa_firma_casos WHERE label='rotation';
SELECT public.despacho_cancelar_firma(id) FROM qa_firma_casos WHERE label='cancelled';

-- Fixture temporal de vencimiento: sólo lo altera el propietario de la base.
RESET ROLE;
UPDATE public.despacho_firmas SET expires_at=clock_timestamp()-interval '1 minute'
WHERE id=(SELECT id FROM qa_firma_casos WHERE label='expired');

SET LOCAL ROLE service_role;
SELECT pg_temp.expect_firma_error(format('SELECT public.despacho_ver_firma(%L)',
    (SELECT old_hash FROM qa_firma_casos WHERE label='rotation')),'P0001','LINK_UNAVAILABLE');
SELECT pg_temp.expect_firma_error(format(
    'SELECT public.despacho_aceptar_firma(%L,''Persona'',''firmante@example.invalid'',''192.0.2.1'',''QA'',true)',
    (SELECT old_hash FROM qa_firma_casos WHERE label='rotation')),'P0001','LINK_UNAVAILABLE');
SELECT pg_temp.assert_firma((SELECT public.despacho_ver_firma(new_hash)->>'document_text'=
    'Documento completo e inmutable de prueba.' FROM qa_firma_casos WHERE label='rotation'),
    'Rotated link resolves the frozen original');

-- Rechazo explícito de falta de consentimiento y correo distinto al solicitado.
SELECT pg_temp.expect_firma_error(format(
    'SELECT public.despacho_aceptar_firma(%L,''Persona'',''firmante@example.invalid'',''192.0.2.1'',''QA'',false)',
    (SELECT new_hash FROM qa_firma_casos WHERE label='rotation')),'P0001','INVALID_ACCEPTANCE');
SELECT pg_temp.expect_firma_error(format(
    'SELECT public.despacho_aceptar_firma(%L,''Persona'',''otro@example.invalid'',''192.0.2.1'',''QA'',true)',
    (SELECT new_hash FROM qa_firma_casos WHERE label='rotation')),'P0001','INVALID_ACCEPTANCE');

SELECT pg_temp.assert_firma((SELECT public.despacho_aceptar_firma(new_hash,'Persona de prueba',
    'firmante@example.invalid','192.0.2.1','QA SQL',true)->>'status'='signed'
    FROM qa_firma_casos WHERE label='rotation'),'Service role can accept once with explicit consent');
SELECT pg_temp.expect_firma_error(format(
    'SELECT public.despacho_aceptar_firma(%L,''Persona'',''firmante@example.invalid'',''192.0.2.1'',''QA'',true)',
    (SELECT new_hash FROM qa_firma_casos WHERE label='rotation')),'P0001','ALREADY_SIGNED');
SELECT pg_temp.assert_firma((SELECT f.document_hash=q.original_hash AND f.signed_at IS NOT NULL
    AND f.document_text='Documento completo e inmutable de prueba.' AND jsonb_array_length(f.audit)=3
    FROM public.despacho_firmas f JOIN qa_firma_casos q ON q.id=f.id WHERE q.label='rotation'),
    'Accepted document keeps original hash and one creation, rotation and signature event');

-- Cancelación y vencimiento invalidan tanto la visualización como aceptación.
DO $$
DECLARE fixture record;
BEGIN
    FOR fixture IN SELECT * FROM qa_firma_casos WHERE label IN ('cancelled','expired') LOOP
        PERFORM pg_temp.expect_firma_error(format('SELECT public.despacho_ver_firma(%L)',fixture.old_hash),
            'P0001','LINK_UNAVAILABLE');
        PERFORM pg_temp.expect_firma_error(format(
            'SELECT public.despacho_aceptar_firma(%L,''Persona'',''firmante@example.invalid'',''192.0.2.1'',''QA'',true)',
            fixture.old_hash),'P0001','LINK_UNAVAILABLE');
    END LOOP;
END;
$$;

RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims',json_build_object('sub',user_id,'role','authenticated')::text,true),
       set_config('request.jwt.claim.sub',user_id::text,true)
FROM qa_firma_usuarios WHERE label='alice';
SELECT pg_temp.expect_firma_error(format('SELECT public.despacho_cancelar_firma(%L)',
    (SELECT id FROM qa_firma_casos WHERE label='rotation')),'P0001','NOT_PENDING');
SELECT pg_temp.expect_firma_error(format('SELECT public.despacho_renovar_enlace_firma(%L,%L)',
    (SELECT id FROM qa_firma_casos WHERE label='rotation'),
    (SELECT old_hash FROM qa_firma_casos WHERE label='rotation')),'P0001','NOT_PENDING');
RESET ROLE;
ROLLBACK;
