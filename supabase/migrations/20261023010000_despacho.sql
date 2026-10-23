-- El Memorialista: private workspace. Idempotent; existing generator tables remain intact.
BEGIN;

CREATE TABLE IF NOT EXISTS public.despacho_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('matter','document','conversation','event','monitor','playbook','table','source')),
    title text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 240),
    matter_id uuid,
    data jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(data) = 'object' AND octet_length(data::text) <= 4194304),
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    monitor_next_check timestamptz DEFAULT now(),
    monitor_lease_until timestamptz,
    monitor_lease uuid,
    UNIQUE(owner_id,id),
    FOREIGN KEY (owner_id,matter_id) REFERENCES public.despacho_items(owner_id,id) ON DELETE NO ACTION DEFERRABLE INITIALLY IMMEDIATE,
    CHECK (kind <> 'matter' OR matter_id IS NULL)
);
CREATE INDEX IF NOT EXISTS despacho_items_owner_kind ON public.despacho_items(owner_id,kind,updated_at DESC);
CREATE INDEX IF NOT EXISTS despacho_items_matter ON public.despacho_items(owner_id,matter_id);
CREATE INDEX IF NOT EXISTS despacho_items_due ON public.despacho_items(monitor_next_check) WHERE kind='monitor';

CREATE TABLE IF NOT EXISTS public.despacho_auditoria (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    item_id uuid NOT NULL,
    operation text NOT NULL CHECK (operation IN ('create','update','delete','protect','unprotect')),
    version integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS despacho_audit_owner_item ON public.despacho_auditoria(owner_id,item_id,created_at DESC);

ALTER TABLE public.despacho_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_auditoria ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.despacho_items, public.despacho_auditoria FROM PUBLIC,anon,authenticated;
GRANT SELECT,DELETE ON public.despacho_items TO authenticated;
GRANT INSERT(id,owner_id,kind,title,matter_id,data,version) ON public.despacho_items TO authenticated;
GRANT UPDATE(title,matter_id,data,version) ON public.despacho_items TO authenticated;
GRANT SELECT ON public.despacho_auditoria TO authenticated;
GRANT ALL ON public.despacho_items,public.despacho_auditoria TO service_role;
DROP POLICY IF EXISTS despacho_owner ON public.despacho_items;
CREATE POLICY despacho_owner ON public.despacho_items FOR ALL TO authenticated
    USING (owner_id=(SELECT auth.uid())) WITH CHECK (owner_id=(SELECT auth.uid()));
DROP POLICY IF EXISTS despacho_audit_owner ON public.despacho_auditoria;
CREATE POLICY despacho_audit_owner ON public.despacho_auditoria FOR SELECT TO authenticated
    USING (owner_id=(SELECT auth.uid()));

CREATE OR REPLACE FUNCTION public.despacho_validar_fila()
RETURNS trigger LANGUAGE plpgsql SET search_path='' AS $$
DECLARE padre public.despacho_items; intervalo integer; previous_versions jsonb; next_versions jsonb; i integer;
BEGIN
    IF TG_OP='DELETE' THEN
        IF current_user IN ('authenticated','anon') AND OLD.kind='document'
           AND (OLD.data->>'locked'='true' OR OLD.data->>'final'='true') THEN
            RAISE EXCEPTION 'El documento está protegido.' USING ERRCODE='55000';
        END IF;
        RETURN OLD;
    END IF;
    IF TG_OP='INSERT' THEN
        -- Serialize only this owner's insert quota, including simultaneous imports.
        PERFORM pg_advisory_xact_lock(hashtextextended(NEW.owner_id::text,0));
        IF (SELECT count(*) FROM public.despacho_items WHERE owner_id=NEW.owner_id)>=2000 THEN
            RAISE EXCEPTION 'Máximo de 2000 elementos por cuenta.' USING ERRCODE='23514';
        END IF;
    END IF;
    IF NEW.matter_id IS NOT NULL THEN
        SELECT * INTO padre FROM public.despacho_items WHERE id=NEW.matter_id AND owner_id=NEW.owner_id;
        IF NOT FOUND OR padre.kind <> 'matter' THEN
            RAISE EXCEPTION 'El asunto no pertenece al propietario.' USING ERRCODE='23514';
        END IF;
    END IF;
    IF TG_OP='UPDATE' THEN
        IF NEW.id IS DISTINCT FROM OLD.id OR NEW.owner_id IS DISTINCT FROM OLD.owner_id OR NEW.kind IS DISTINCT FROM OLD.kind THEN
            RAISE EXCEPTION 'La identidad del registro es inmutable.' USING ERRCODE='42501';
        END IF;
        IF NEW.version <> OLD.version + 1 THEN
            RAISE EXCEPTION 'Versión concurrente.' USING ERRCODE='40001';
        END IF;
        IF OLD.kind='document' AND (OLD.data->>'locked'='true' OR OLD.data->>'final'='true')
           AND ((NEW.data - 'locked' - 'final') IS DISTINCT FROM (OLD.data - 'locked' - 'final')) THEN
            RAISE EXCEPTION 'Desprotege el documento primero.' USING ERRCODE='55000';
        END IF;
        IF OLD.kind='document' THEN
            previous_versions=COALESCE(OLD.data->'versions','[]'::jsonb);
            next_versions=COALESCE(NEW.data->'versions','[]'::jsonb);
            IF jsonb_typeof(next_versions) <> 'array' OR jsonb_typeof(previous_versions) <> 'array'
               OR jsonb_array_length(next_versions)<jsonb_array_length(previous_versions)
               OR jsonb_array_length(next_versions)>50 THEN
                RAISE EXCEPTION 'No se puede eliminar el historial de versiones.' USING ERRCODE='55000';
            END IF;
            FOR i IN 0..jsonb_array_length(previous_versions)-1 LOOP
                IF (next_versions->i) IS DISTINCT FROM (previous_versions->i) THEN
                    RAISE EXCEPTION 'Las versiones anteriores son inmutables.' USING ERRCODE='55000';
                END IF;
            END LOOP;
            IF (NEW.data->'text') IS DISTINCT FROM (OLD.data->'text')
               OR (NEW.data->'pages') IS DISTINCT FROM (OLD.data->'pages')
               OR (NEW.data->'storage_path') IS DISTINCT FROM (OLD.data->'storage_path') THEN
                IF jsonb_array_length(next_versions)<>jsonb_array_length(previous_versions)+1
                   OR ((next_versions -> -1)->'text') IS DISTINCT FROM (OLD.data->'text')
                   OR ((next_versions -> -1)->'storage_path') IS DISTINCT FROM (OLD.data->'storage_path') THEN
                    RAISE EXCEPTION 'Un cambio de contenido exige conservar su versión anterior.' USING ERRCODE='55000';
                END IF;
            END IF;
        END IF;
        NEW.created_at=OLD.created_at;
    ELSIF NEW.version <> 1 THEN
        RAISE EXCEPTION 'La versión inicial debe ser 1.' USING ERRCODE='23514';
    END IF;
    NEW.updated_at=clock_timestamp();
    IF NEW.kind='monitor' THEN
        IF jsonb_typeof(NEW.data->'interval_minutes') IS DISTINCT FROM 'number'
           OR (NEW.data->>'interval_minutes') !~ '^[0-9]+$' THEN
            RAISE EXCEPTION 'Intervalo inválido.' USING ERRCODE='23514';
        END IF;
        intervalo=(NEW.data->>'interval_minutes')::integer;
        IF intervalo < 15 OR intervalo > 10080 THEN
            RAISE EXCEPTION 'Intervalo inválido.' USING ERRCODE='23514';
        END IF;
        IF TG_OP='INSERT' THEN NEW.monitor_next_check=now();
        ELSIF NEW.data->>'last_checked' IS DISTINCT FROM OLD.data->>'last_checked' THEN
            NEW.monitor_next_check=now()+make_interval(mins=>intervalo);
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.despacho_validar_fila() FROM PUBLIC,anon,authenticated;
DROP TRIGGER IF EXISTS despacho_validar ON public.despacho_items;
CREATE TRIGGER despacho_validar BEFORE INSERT OR UPDATE OR DELETE ON public.despacho_items
    FOR EACH ROW EXECUTE FUNCTION public.despacho_validar_fila();

CREATE OR REPLACE FUNCTION public.despacho_registrar_auditoria()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE operacion text;
BEGIN
    IF TG_OP='DELETE' THEN
        IF EXISTS(SELECT 1 FROM auth.users WHERE id=OLD.owner_id) THEN
            INSERT INTO public.despacho_auditoria(owner_id,item_id,operation,version)
            VALUES(OLD.owner_id,OLD.id,'delete',OLD.version);
        END IF;
        RETURN OLD;
    END IF;
    operacion=CASE WHEN TG_OP='INSERT' THEN 'create' ELSE 'update' END;
    IF TG_OP='UPDATE' AND NEW.kind='document' THEN
        IF ((NEW.data->>'locked'='true' OR NEW.data->>'final'='true') IS TRUE)
           AND NOT ((OLD.data->>'locked'='true' OR OLD.data->>'final'='true') IS TRUE) THEN operacion='protect';
        ELSIF ((OLD.data->>'locked'='true' OR OLD.data->>'final'='true') IS TRUE)
           AND NOT ((NEW.data->>'locked'='true' OR NEW.data->>'final'='true') IS TRUE) THEN operacion='unprotect'; END IF;
    END IF;
    INSERT INTO public.despacho_auditoria(owner_id,item_id,operation,version)
    VALUES(NEW.owner_id,NEW.id,operacion,NEW.version);
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.despacho_registrar_auditoria() FROM PUBLIC,anon,authenticated;
DROP TRIGGER IF EXISTS despacho_auditar ON public.despacho_items;
CREATE TRIGGER despacho_auditar AFTER INSERT OR UPDATE OR DELETE ON public.despacho_items
    FOR EACH ROW EXECUTE FUNCTION public.despacho_registrar_auditoria();

CREATE OR REPLACE FUNCTION public.despacho_importar_items(p_items jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE r jsonb; cantidad integer=0;
BEGIN
    IF auth.uid() IS NULL OR jsonb_typeof(p_items) <> 'array' OR jsonb_array_length(p_items)>2000
       OR octet_length(p_items::text)>25165824 THEN
        RAISE EXCEPTION 'Copia inválida.' USING ERRCODE='22023';
    END IF;
    FOR r IN SELECT value FROM jsonb_array_elements(p_items) ORDER BY
        CASE WHEN value->>'kind'='matter' THEN 0 WHEN value->>'kind'='event' THEN 2 ELSE 1 END
    LOOP
        IF (r->>'owner_id')::uuid IS DISTINCT FROM auth.uid() THEN
            RAISE EXCEPTION 'Propietario inválido.' USING ERRCODE='42501';
        END IF;
        INSERT INTO public.despacho_items(id,owner_id,kind,title,matter_id,data,version)
        VALUES((r->>'id')::uuid,auth.uid(),r->>'kind',r->>'title',NULLIF(r->>'matter_id','')::uuid,r->'data',1);
        cantidad=cantidad+1;
    END LOOP;
    RETURN jsonb_build_object('imported',cantidad);
END;
$$;
REVOKE ALL ON FUNCTION public.despacho_importar_items(jsonb) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_importar_items(jsonb) TO authenticated;

-- Dedicated worker claims with row locks. Never exposed to ordinary users.
CREATE OR REPLACE FUNCTION public.despacho_reclamar_monitores(p_limit integer DEFAULT 10)
RETURNS SETOF public.despacho_items LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE r public.despacho_items;
BEGIN
    FOR r IN SELECT * FROM public.despacho_items WHERE kind='monitor' AND data->>'enabled'='true'
        AND monitor_next_check<=now() AND (monitor_lease_until IS NULL OR monitor_lease_until<now())
        ORDER BY monitor_next_check LIMIT LEAST(GREATEST(p_limit,1),20) FOR UPDATE SKIP LOCKED
    LOOP
        UPDATE public.despacho_items SET monitor_lease=gen_random_uuid(),monitor_lease_until=now()+interval '5 minutes',version=version+1
        WHERE id=r.id RETURNING * INTO r;
        RETURN NEXT r;
    END LOOP;
END;
$$;
REVOKE ALL ON FUNCTION public.despacho_reclamar_monitores(integer) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_reclamar_monitores(integer) TO service_role;

CREATE OR REPLACE FUNCTION public.despacho_finalizar_monitor(p_id uuid,p_lease uuid,p_expected_version integer,p_data jsonb)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE r public.despacho_items;
BEGIN
    SELECT * INTO r FROM public.despacho_items WHERE id=p_id AND kind='monitor' FOR UPDATE;
    IF NOT FOUND OR r.monitor_lease IS DISTINCT FROM p_lease THEN RETURN false; END IF;
    IF r.version <> p_expected_version THEN
        UPDATE public.despacho_items SET monitor_lease=NULL,monitor_lease_until=NULL,
            monitor_next_check=now()+interval '1 minute',version=version+1 WHERE id=p_id;
        RETURN false;
    END IF;
    UPDATE public.despacho_items SET data=p_data,monitor_lease=NULL,monitor_lease_until=NULL,version=version+1,
        monitor_next_check=now()+make_interval(mins=>(r.data->>'interval_minutes')::integer)
    WHERE id=p_id;
    RETURN true;
END;
$$;
REVOKE ALL ON FUNCTION public.despacho_finalizar_monitor(uuid,uuid,integer,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_finalizar_monitor(uuid,uuid,integer,jsonb) TO service_role;

INSERT INTO storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
VALUES('despacho-documentos','despacho-documentos',false,10485760,ARRAY[
    'application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain','text/markdown'])
ON CONFLICT(id) DO UPDATE SET public=false,file_size_limit=EXCLUDED.file_size_limit,allowed_mime_types=EXCLUDED.allowed_mime_types;
DROP POLICY IF EXISTS despacho_storage_select ON storage.objects;
CREATE POLICY despacho_storage_select ON storage.objects FOR SELECT TO authenticated
    USING(bucket_id='despacho-documentos' AND (storage.foldername(name))[1]=(SELECT auth.uid())::text);
DROP POLICY IF EXISTS despacho_storage_insert ON storage.objects;
CREATE POLICY despacho_storage_insert ON storage.objects FOR INSERT TO authenticated
    WITH CHECK(bucket_id='despacho-documentos' AND (storage.foldername(name))[1]=(SELECT auth.uid())::text);
DROP POLICY IF EXISTS despacho_storage_delete ON storage.objects;
CREATE OR REPLACE FUNCTION public.despacho_puede_borrar_original(p_name text)
RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
    SELECT (storage.foldername(p_name))[1]=(SELECT auth.uid())::text
    AND NOT EXISTS(
        SELECT 1 FROM public.despacho_items d WHERE d.owner_id=(SELECT auth.uid()) AND d.kind='document'
          AND (d.data->>'locked'='true' OR d.data->>'final'='true')
          AND (d.data->>'storage_path'=p_name OR COALESCE(d.data->'versions','[]'::jsonb)
               @> jsonb_build_array(jsonb_build_object('storage_path',p_name)))
    );
$$;
REVOKE ALL ON FUNCTION public.despacho_puede_borrar_original(text) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_puede_borrar_original(text) TO authenticated,service_role;
CREATE POLICY despacho_storage_delete ON storage.objects FOR DELETE TO authenticated
    USING(bucket_id='despacho-documentos' AND public.despacho_puede_borrar_original(name));
-- Originals are immutable: new versions get new object paths, no UPDATE policy.
COMMIT;
