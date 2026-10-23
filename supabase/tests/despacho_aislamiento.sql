-- Run in a TEST Supabase project as database owner after all migrations.
-- Real PostgreSQL/RLS assertions. Creates temporary users; always ROLLBACK.
BEGIN;
SET LOCAL statement_timeout='30s';
CREATE TEMP TABLE qa_despacho(label text,user_id uuid DEFAULT gen_random_uuid(),matter uuid DEFAULT gen_random_uuid(),doc uuid DEFAULT gen_random_uuid()) ON COMMIT DROP;
INSERT INTO qa_despacho(label) VALUES('a'),('b');
INSERT INTO auth.users(id,email,raw_user_meta_data,raw_app_meta_data,created_at,updated_at)
SELECT user_id,user_id::text||'@example.invalid','{"nombre":"QA Despacho"}'::jsonb,'{}'::jsonb,now(),now() FROM qa_despacho;
GRANT SELECT ON qa_despacho TO authenticated,anon;

CREATE FUNCTION pg_temp.assert_despacho(ok boolean,message text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN IF ok IS DISTINCT FROM true THEN RAISE EXCEPTION 'FAIL: %',message; END IF; END;
$$;
CREATE FUNCTION pg_temp.expect_despacho_error(sql_text text,expected_code text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    BEGIN EXECUTE sql_text;
    EXCEPTION WHEN OTHERS THEN
        IF SQLSTATE=expected_code THEN RETURN; END IF;
        RAISE EXCEPTION 'Unexpected SQLSTATE %, expected %',SQLSTATE,expected_code;
    END;
    RAISE EXCEPTION 'Expected rejection: %',sql_text;
END;
$$;
GRANT EXECUTE ON FUNCTION pg_temp.assert_despacho(boolean,text),pg_temp.expect_despacho_error(text,text) TO authenticated,anon;

INSERT INTO public.despacho_items(id,owner_id,kind,title)
SELECT matter,user_id,'matter','Asunto '||label FROM qa_despacho;
INSERT INTO public.despacho_items(id,owner_id,kind,title,matter_id,data)
SELECT doc,user_id,'document','Documento '||label,matter,'{"text":"Original","pages":[],"versions":[]}'::jsonb FROM qa_despacho;

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims',json_build_object('sub',user_id,'role','authenticated')::text,true),
       set_config('request.jwt.claim.sub',user_id::text,true) FROM qa_despacho WHERE label='a';
SELECT pg_temp.assert_despacho((SELECT count(*)=2 FROM public.despacho_items),'Only the owner reads its two records');
SELECT pg_temp.assert_despacho((SELECT count(*)=0 FROM public.despacho_items WHERE owner_id=(SELECT user_id FROM qa_despacho WHERE label='b')),'Foreign account is hidden');
SELECT pg_temp.expect_despacho_error(format('INSERT INTO public.despacho_items(owner_id,kind,title) VALUES(%L,''matter'',''Forbidden'')',
    (SELECT user_id FROM qa_despacho WHERE label='b')),'42501');
SELECT pg_temp.expect_despacho_error(format('UPDATE public.despacho_items SET owner_id=%L WHERE id=%L',
    (SELECT user_id FROM qa_despacho WHERE label='b'),(SELECT doc FROM qa_despacho WHERE label='a')),'42501');
SELECT pg_temp.expect_despacho_error(format('UPDATE public.despacho_items SET title=''Stale'',version=1 WHERE id=%L',
    (SELECT doc FROM qa_despacho WHERE label='a')),'40001');
UPDATE public.despacho_items SET title='Updated',version=version+1 WHERE id=(SELECT doc FROM qa_despacho WHERE label='a');
SELECT pg_temp.assert_despacho((SELECT version=2 FROM public.despacho_items WHERE id=(SELECT doc FROM qa_despacho WHERE label='a')),'Version increases');
SELECT pg_temp.expect_despacho_error(format('DELETE FROM public.despacho_items WHERE id=%L',
    (SELECT matter FROM qa_despacho WHERE label='a')),'23503');

UPDATE public.despacho_items SET data=data||'{"locked":true}'::jsonb,version=version+1 WHERE id=(SELECT doc FROM qa_despacho WHERE label='a');
SELECT pg_temp.expect_despacho_error(format('UPDATE public.despacho_items SET data=data||''{"text":"Altered","locked":false}''::jsonb,version=version+1 WHERE id=%L',
    (SELECT doc FROM qa_despacho WHERE label='a')),'55000');
SELECT pg_temp.expect_despacho_error(format('DELETE FROM public.despacho_items WHERE id=%L',
    (SELECT doc FROM qa_despacho WHERE label='a')),'55000');
UPDATE public.despacho_items SET data=data||'{"locked":false}'::jsonb,version=version+1 WHERE id=(SELECT doc FROM qa_despacho WHERE label='a');
SELECT pg_temp.assert_despacho((SELECT count(*)>=4 FROM public.despacho_auditoria WHERE item_id=(SELECT doc FROM qa_despacho WHERE label='a')),'Immutable audit records changes');
SELECT pg_temp.expect_despacho_error('DELETE FROM public.despacho_auditoria','42501');
SELECT pg_temp.expect_despacho_error('SELECT public.despacho_reclamar_monitores(1)','42501');

INSERT INTO storage.objects(bucket_id,name)
SELECT 'despacho-documentos',user_id::text||'/'||doc::text||'/'||gen_random_uuid()::text||'.pdf' FROM qa_despacho WHERE label='a';
SELECT pg_temp.assert_despacho((SELECT count(*)=1 FROM storage.objects WHERE bucket_id='despacho-documentos'),'Private original is readable');
SELECT pg_temp.expect_despacho_error(format('INSERT INTO storage.objects(bucket_id,name) VALUES(''despacho-documentos'',%L)',
    (SELECT user_id::text||'/'||doc::text||'/'||gen_random_uuid()::text||'.pdf' FROM qa_despacho WHERE label='b')),'42501');

RESET ROLE;
-- Account deletion must not be blocked by audit-row FK insertion during cascade.
DELETE FROM auth.users WHERE id=(SELECT user_id FROM qa_despacho WHERE label='a');
SELECT pg_temp.assert_despacho((SELECT count(*)=0 FROM public.despacho_items WHERE owner_id=(SELECT user_id FROM qa_despacho WHERE label='a')),'Account cascade removes private records');
SELECT pg_temp.assert_despacho((SELECT count(*)=0 FROM public.despacho_auditoria WHERE owner_id=(SELECT user_id FROM qa_despacho WHERE label='a')),'Account cascade removes audit records');
ROLLBACK;
