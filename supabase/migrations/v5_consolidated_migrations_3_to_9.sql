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
-- Firma mediante enlace privado y declaración de consentimiento.
-- No certifica identidad ni crea una firma digital acreditada. El original se
-- congela y las transiciones sólo se realizan en las funciones autorizadas.
begin;

create table if not exists public.despacho_firmas (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  title text not null check (char_length(title) between 1 and 240),
  document_text text not null check (char_length(document_text) between 1 and 300000),
  document_hash text not null check (document_hash ~ '^[a-f0-9]{64}$'),
  signer_name text not null check (char_length(signer_name) between 2 and 160),
  signer_email text not null check (char_length(signer_email) between 3 and 254),
  token_hash text not null unique check (token_hash ~ '^[a-f0-9]{64}$'),
  status text not null default 'pending' check (status in ('pending','signed','cancelled')),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  signed_at timestamptz,
  signed_name text,
  signed_email text,
  signer_ip text,
  signer_agent text,
  consent_text text,
  audit jsonb not null default '[]'::jsonb,
  check ((status = 'signed' and signed_at is not null and signed_name is not null
          and signed_email is not null and consent_text is not null)
         or (status <> 'signed' and signed_at is null))
);
create index if not exists despacho_firmas_owner_idx on public.despacho_firmas(owner_id,created_at desc);
alter table public.despacho_firmas enable row level security;
revoke all on public.despacho_firmas from anon, authenticated;
grant select on public.despacho_firmas to authenticated;
grant all on public.despacho_firmas to service_role;
drop policy if exists despacho_firmas_read_own on public.despacho_firmas;
create policy despacho_firmas_read_own on public.despacho_firmas for select to authenticated
  using (owner_id = (select auth.uid()));

create or replace function public.despacho_crear_firma(
  p_title text, p_text text, p_name text, p_email text, p_token_hash text, p_days integer
) returns jsonb language plpgsql security definer set search_path = '' as $$
declare r public.despacho_firmas;
begin
  if auth.uid() is null then raise exception 'AUTH_REQUIRED'; end if;
  if p_days is null or p_name is null or p_title is null or p_text is null
     or p_email is null or p_token_hash is null
     or p_days not between 1 and 30 or char_length(btrim(p_name)) not between 2 and 160
     or char_length(btrim(p_title)) not between 1 and 240
     or char_length(p_text) not between 1 and 300000
     or p_email !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
     or char_length(p_email) > 254 or p_token_hash !~ '^[a-f0-9]{64}$' then
    raise exception 'INVALID_INPUT';
  end if;
  -- Serializa el cupo por propietario: dos transacciones simultáneas no pueden
  -- leer el mismo contador y superar juntas el límite diario.
  perform pg_advisory_xact_lock(hashtextextended('despacho_firmas:' || auth.uid()::text, 0));
  if (select count(*) from public.despacho_firmas where owner_id = auth.uid()
      and created_at > clock_timestamp() - interval '24 hours') >= 100 then
    raise exception 'SIGNATURE_LIMIT';
  end if;
  insert into public.despacho_firmas(owner_id,title,document_text,document_hash,signer_name,
    signer_email,token_hash,expires_at,audit)
  values(auth.uid(),btrim(p_title),p_text,encode(sha256(convert_to(p_text,'UTF8')),'hex'),
    btrim(p_name),lower(btrim(p_email)),p_token_hash,clock_timestamp()+make_interval(days=>p_days),
    jsonb_build_array(jsonb_build_object('event','created','at',clock_timestamp(),'by',auth.uid())))
  returning * into r;
  return to_jsonb(r) - 'token_hash' - 'owner_id';
end $$;

create or replace function public.despacho_cancelar_firma(p_id uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare r public.despacho_firmas;
begin
  if auth.uid() is null then raise exception 'AUTH_REQUIRED'; end if;
  select * into r from public.despacho_firmas where id=p_id and owner_id=auth.uid() for update;
  if not found then raise exception 'NOT_FOUND'; end if;
  if r.status <> 'pending' then raise exception 'NOT_PENDING'; end if;
  update public.despacho_firmas set status='cancelled',
    audit=audit||jsonb_build_array(jsonb_build_object('event','cancelled','at',clock_timestamp(),'by',auth.uid()))
    where id=r.id returning * into r;
  return to_jsonb(r) - 'token_hash' - 'owner_id';
end $$;

create or replace function public.despacho_renovar_enlace_firma(p_id uuid,p_token_hash text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare r public.despacho_firmas;
begin
  if auth.uid() is null then raise exception 'AUTH_REQUIRED'; end if;
  if p_token_hash is null or p_token_hash !~ '^[a-f0-9]{64}$' then raise exception 'INVALID_INPUT'; end if;
  select * into r from public.despacho_firmas where id=p_id and owner_id=auth.uid() for update;
  if not found then raise exception 'NOT_FOUND'; end if;
  if r.status <> 'pending' then raise exception 'NOT_PENDING'; end if;
  update public.despacho_firmas set token_hash=p_token_hash,expires_at=clock_timestamp()+interval '7 days',
    audit=audit||jsonb_build_array(jsonb_build_object('event','link_rotated','at',clock_timestamp(),'by',auth.uid()))
    where id=r.id returning * into r;
  return to_jsonb(r) - 'token_hash' - 'owner_id';
end $$;

-- Estas dos funciones son exclusivas del servidor: no son RPC anónimos.
-- La clave de servicio jamás se entrega al navegador. El servidor recibe el
-- token por POST, conserva sólo su hash y registra la IP según proxies fiables.
create or replace function public.despacho_ver_firma(p_token_hash text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare r public.despacho_firmas;
begin
  select * into r from public.despacho_firmas where token_hash=p_token_hash;
  if not found or r.status='cancelled' or r.expires_at<=clock_timestamp() then raise exception 'LINK_UNAVAILABLE'; end if;
  return jsonb_build_object('id',r.id,'title',r.title,'document_text',r.document_text,
    'document_hash',r.document_hash,'signer_name',r.signer_name,'status',r.status,
    'created_at',r.created_at,'expires_at',r.expires_at,'signed_at',r.signed_at,
    'identity_method','private_link_and_declared_identity');
end $$;

create or replace function public.despacho_aceptar_firma(p_token_hash text,p_name text,
  p_email text,p_ip text,p_agent text,p_consent boolean)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare r public.despacho_firmas;
  consent constant text := 'He leído el documento completo, acepto su contenido y manifiesto mi voluntad de firmarlo electrónicamente mediante este enlace privado.';
begin
  select * into r from public.despacho_firmas where token_hash=p_token_hash for update;
  if not found or r.status='cancelled' or r.expires_at<=clock_timestamp() then raise exception 'LINK_UNAVAILABLE'; end if;
  if r.status <> 'pending' then raise exception 'ALREADY_SIGNED'; end if;
  if p_consent is distinct from true or p_name is null or p_email is null
    or p_ip is null or p_agent is null or char_length(btrim(p_name)) not between 2 and 160
    or lower(btrim(p_email)) <> r.signer_email or char_length(p_ip)>64 or char_length(p_agent)>512
    then raise exception 'INVALID_ACCEPTANCE'; end if;
  update public.despacho_firmas set status='signed',signed_at=clock_timestamp(),signed_name=btrim(p_name),
    signed_email=lower(btrim(p_email)),signer_ip=p_ip,signer_agent=p_agent,consent_text=consent,
    audit=audit||jsonb_build_array(jsonb_build_object('event','signed','at',clock_timestamp(),
      'document_hash',r.document_hash,'method','private_link_and_declared_identity'))
    where id=r.id returning * into r;
  return jsonb_build_object('id',r.id,'title',r.title,'status',r.status,'signed_at',r.signed_at,
    'document_hash',r.document_hash,'signed_name',r.signed_name,'consent_text',r.consent_text);
end $$;

revoke all on function public.despacho_crear_firma(text,text,text,text,text,integer) from public,anon,authenticated;
revoke all on function public.despacho_cancelar_firma(uuid) from public,anon,authenticated;
revoke all on function public.despacho_renovar_enlace_firma(uuid,text) from public,anon,authenticated;
revoke all on function public.despacho_ver_firma(text) from public,anon,authenticated;
revoke all on function public.despacho_aceptar_firma(text,text,text,text,text,boolean) from public,anon,authenticated;
grant execute on function public.despacho_crear_firma(text,text,text,text,text,integer) to authenticated;
grant execute on function public.despacho_cancelar_firma(uuid) to authenticated;
grant execute on function public.despacho_renovar_enlace_firma(uuid,text) to authenticated;
grant execute on function public.despacho_ver_firma(text) to service_role;
grant execute on function public.despacho_aceptar_firma(text,text,text,text,text,boolean) to service_role;
commit;
-- El Memorialista V5: reviewed plans, durable steps and recurring assignments.
-- Browser actions are separate, single-use approvals. No user JWT is stored.
BEGIN;

CREATE TABLE IF NOT EXISTS public.despacho_agent_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title text NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    objective text NOT NULL CHECK (length(objective) BETWEEN 1 AND 12000),
    document_ids jsonb NOT NULL DEFAULT '[]' CHECK (jsonb_typeof(document_ids)='array' AND jsonb_array_length(document_ids)<=20),
    matter_id uuid,
    playbook_id uuid,
    allowed_urls jsonb NOT NULL DEFAULT '[]' CHECK (jsonb_typeof(allowed_urls)='array' AND jsonb_array_length(allowed_urls)<=8),
    plan jsonb NOT NULL CHECK (jsonb_typeof(plan)='array' AND jsonb_array_length(plan) BETWEEN 1 AND 8),
    plan_hash text NOT NULL CHECK (plan_hash ~ '^[0-9a-f]{64}$'),
    approved_hash text,
    approved_at timestamptz,
    state text NOT NULL DEFAULT 'draft' CHECK (state IN ('draft','approved','running','waiting_approval','completed','failed','cancelled')),
    version integer NOT NULL DEFAULT 1 CHECK (version>=1),
    cursor integer NOT NULL DEFAULT 0 CHECK (cursor BETWEEN 0 AND 8),
    results jsonb NOT NULL DEFAULT '[]' CHECK (jsonb_typeof(results)='array' AND jsonb_array_length(results)<=8 AND octet_length(results::text)<=4000000),
    last_error text NOT NULL DEFAULT '' CHECK (length(last_error)<=1200),
    lease_token uuid,
    lease_until timestamptz,
    manual_control boolean NOT NULL DEFAULT false,
    schedule_id uuid,
    scheduled_for timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(owner_id,id),
    UNIQUE(schedule_id,scheduled_for),
    CHECK (cursor<=jsonb_array_length(plan)),
    CHECK (jsonb_array_length(results)=cursor),
    FOREIGN KEY(owner_id,matter_id) REFERENCES public.despacho_items(owner_id,id) ON DELETE NO ACTION DEFERRABLE INITIALLY IMMEDIATE,
    FOREIGN KEY(owner_id,playbook_id) REFERENCES public.despacho_items(owner_id,id) ON DELETE NO ACTION DEFERRABLE INITIALLY IMMEDIATE
);
CREATE INDEX IF NOT EXISTS despacho_agent_jobs_owner ON public.despacho_agent_jobs(owner_id,created_at DESC);
CREATE INDEX IF NOT EXISTS despacho_agent_jobs_queue ON public.despacho_agent_jobs(state,lease_until,created_at) WHERE schedule_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.despacho_agent_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id uuid NOT NULL,
    at timestamptz NOT NULL DEFAULT now(),
    event text NOT NULL CHECK (length(event)<=80),
    detail jsonb NOT NULL DEFAULT '{}' CHECK (octet_length(detail::text)<=20000),
    FOREIGN KEY(owner_id,job_id) REFERENCES public.despacho_agent_jobs(owner_id,id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS despacho_agent_events_owner ON public.despacho_agent_events(owner_id,job_id,at);

CREATE TABLE IF NOT EXISTS public.despacho_agent_schedules (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id uuid NOT NULL,
    title text NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    interval_minutes integer NOT NULL CHECK (interval_minutes BETWEEN 60 AND 10080),
    next_run_at timestamptz NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    version integer NOT NULL DEFAULT 1,
    last_run_at timestamptz,
    last_job_id uuid,
    last_error text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(owner_id,id),
    FOREIGN KEY(owner_id,job_id) REFERENCES public.despacho_agent_jobs(owner_id,id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS despacho_agent_schedules_due ON public.despacho_agent_schedules(next_run_at) WHERE enabled;

CREATE TABLE IF NOT EXISTS public.despacho_agent_browser_actions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id uuid NOT NULL,
    session_id uuid NOT NULL,
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','executing','completed','failed','expired')),
    action jsonb NOT NULL CHECK (octet_length(action::text)<=12000),
    page_hash text NOT NULL,
    expires_at timestamptz NOT NULL,
    result jsonb NOT NULL DEFAULT '{}' CHECK (octet_length(result::text)<=100000),
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    FOREIGN KEY(owner_id,job_id) REFERENCES public.despacho_agent_jobs(owner_id,id) ON DELETE CASCADE
);

ALTER TABLE public.despacho_agent_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_agent_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_agent_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_agent_browser_actions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.despacho_agent_jobs,public.despacho_agent_events,public.despacho_agent_schedules,public.despacho_agent_browser_actions FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.despacho_agent_jobs,public.despacho_agent_events,public.despacho_agent_schedules TO authenticated;
GRANT ALL ON public.despacho_agent_jobs,public.despacho_agent_events,public.despacho_agent_schedules,public.despacho_agent_browser_actions TO service_role;
GRANT USAGE,SELECT ON SEQUENCE public.despacho_agent_events_id_seq TO service_role;
DROP POLICY IF EXISTS agent_job_owner ON public.despacho_agent_jobs;
CREATE POLICY agent_job_owner ON public.despacho_agent_jobs FOR SELECT TO authenticated USING(owner_id=(SELECT auth.uid()));
DROP POLICY IF EXISTS agent_events_owner ON public.despacho_agent_events;
CREATE POLICY agent_events_owner ON public.despacho_agent_events FOR SELECT TO authenticated USING(owner_id=(SELECT auth.uid()));
DROP POLICY IF EXISTS agent_schedule_owner ON public.despacho_agent_schedules;
CREATE POLICY agent_schedule_owner ON public.despacho_agent_schedules FOR SELECT TO authenticated USING(owner_id=(SELECT auth.uid()));

CREATE OR REPLACE FUNCTION public.despacho_agent_job_audit()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
    INSERT INTO public.despacho_agent_events(owner_id,job_id,event,detail)
    VALUES(NEW.owner_id,NEW.id,CASE WHEN TG_OP='INSERT' THEN 'plan_created' ELSE 'state_changed' END,
      jsonb_build_object('state',NEW.state,'cursor',NEW.cursor,'version',NEW.version,'plan_hash',NEW.plan_hash,'error',NEW.last_error));
    RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.despacho_agent_job_audit() FROM PUBLIC,anon,authenticated;
DROP TRIGGER IF EXISTS despacho_agent_job_audit ON public.despacho_agent_jobs;
CREATE TRIGGER despacho_agent_job_audit AFTER INSERT OR UPDATE ON public.despacho_agent_jobs FOR EACH ROW EXECUTE FUNCTION public.despacho_agent_job_audit();

CREATE OR REPLACE FUNCTION public.despacho_agent_control(p_owner uuid,p_id uuid,p_version integer,p_action text,p_data jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs; plan_new jsonb;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_id AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR j.version<>p_version THEN RAISE EXCEPTION 'stale job' USING ERRCODE='40001'; END IF;
    IF p_action='edit' THEN
        IF j.state<>'draft' THEN RAISE EXCEPTION 'approved plans are immutable' USING ERRCODE='55000'; END IF;
        plan_new=p_data->'plan';
        IF jsonb_typeof(plan_new)<>'array' OR jsonb_array_length(plan_new) NOT BETWEEN 1 AND 8 THEN RAISE EXCEPTION 'invalid plan' USING ERRCODE='22023'; END IF;
        UPDATE public.despacho_agent_jobs SET plan=plan_new,plan_hash=p_data->>'plan_hash',approved_hash=NULL,approved_at=NULL,version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO j;
    ELSIF p_action='approve' THEN
        IF j.state<>'draft' THEN RAISE EXCEPTION 'not a draft' USING ERRCODE='55000'; END IF;
        UPDATE public.despacho_agent_jobs SET state='approved',approved_hash=plan_hash,approved_at=now(),version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO j;
    ELSIF p_action='cancel' THEN
        IF j.state IN ('completed','cancelled') THEN RETURN to_jsonb(j); END IF;
        UPDATE public.despacho_agent_jobs SET state='cancelled',manual_control=false,lease_token=NULL,lease_until=NULL,version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO j;
        UPDATE public.despacho_agent_browser_actions SET state='expired' WHERE job_id=p_id AND owner_id=p_owner AND state='pending';
    ELSIF p_action='retry' THEN
        IF NOT (j.state='failed' OR (j.state='running' AND j.lease_until<now())) OR j.approved_hash IS DISTINCT FROM j.plan_hash THEN
            RAISE EXCEPTION 'not recoverable' USING ERRCODE='55000';
        END IF;
        UPDATE public.despacho_agent_jobs SET state='approved',last_error='',lease_token=NULL,lease_until=NULL,version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO j;
    ELSE RAISE EXCEPTION 'invalid action' USING ERRCODE='22023'; END IF;
    RETURN to_jsonb(j);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_claim_step(p_owner uuid,p_id uuid,p_version integer,p_lease uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_id AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR j.version<>p_version OR j.state NOT IN ('approved','running') OR j.manual_control OR j.cursor>=jsonb_array_length(j.plan)
       OR j.approved_hash IS DISTINCT FROM j.plan_hash OR (j.lease_until IS NOT NULL AND j.lease_until>now()) THEN
        RAISE EXCEPTION 'claim conflict' USING ERRCODE='40001';
    END IF;
    UPDATE public.despacho_agent_jobs SET state='running',lease_token=p_lease,lease_until=now()+interval '300 seconds',version=version+1,updated_at=now(),last_error='' WHERE id=p_id RETURNING * INTO j;
    RETURN to_jsonb(j);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_finish_step(p_owner uuid,p_id uuid,p_lease uuid,p_cursor integer,p_result jsonb,p_error text DEFAULT '')
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_id AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'missing job' USING ERRCODE='40001'; END IF;
    IF j.state='cancelled' THEN RETURN to_jsonb(j); END IF;
    IF j.lease_token IS DISTINCT FROM p_lease OR j.cursor<>p_cursor OR j.state<>'running' THEN RAISE EXCEPTION 'stale completion' USING ERRCODE='40001'; END IF;
    IF p_error<>'' THEN
        UPDATE public.despacho_agent_jobs SET state='failed',last_error=left(p_error,1200),lease_token=NULL,lease_until=NULL,version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO j;
    ELSE
        IF p_result->>'step_id' IS DISTINCT FROM (j.plan->p_cursor)->>'id' OR p_result->>'tool' IS DISTINCT FROM (j.plan->p_cursor)->>'tool' THEN
            RAISE EXCEPTION 'wrong step result' USING ERRCODE='22023';
        END IF;
        UPDATE public.despacho_agent_jobs SET cursor=cursor+1,results=results||jsonb_build_array(p_result),state=CASE WHEN cursor+1=jsonb_array_length(plan) THEN 'completed' ELSE 'approved' END,
            last_error='',lease_token=NULL,lease_until=NULL,version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO j;
    END IF;
    IF j.schedule_id IS NOT NULL THEN UPDATE public.despacho_agent_schedules SET last_error=j.last_error,updated_at=now() WHERE id=j.schedule_id AND owner_id=p_owner; END IF;
    RETURN to_jsonb(j);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_schedule_create(p_owner uuid,p_job uuid,p_interval integer,p_next timestamptz,p_enabled boolean DEFAULT true)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs; s public.despacho_agent_schedules;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended('agent-schedule:'||p_owner::text,0));
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE owner_id=p_owner AND id=p_job;
    IF NOT FOUND OR j.approved_hash IS DISTINCT FROM j.plan_hash OR j.state IN ('draft','cancelled','waiting_approval') THEN RAISE EXCEPTION 'not approved' USING ERRCODE='55000'; END IF;
    IF EXISTS(SELECT 1 FROM jsonb_array_elements(j.plan) e WHERE e->>'tool' NOT IN ('read_documents','research','analyze','draft','timeline','fetch_source','save_document')) THEN
        RAISE EXCEPTION 'unsafe recurring tool' USING ERRCODE='22023'; END IF;
    IF (SELECT count(*) FROM public.despacho_agent_schedules WHERE owner_id=p_owner)>=10 THEN RAISE EXCEPTION 'schedule quota' USING ERRCODE='23514'; END IF;
    IF p_interval NOT BETWEEN 60 AND 10080 OR p_next<now()-interval '1 minute' THEN RAISE EXCEPTION 'invalid schedule' USING ERRCODE='22023'; END IF;
    INSERT INTO public.despacho_agent_schedules(owner_id,job_id,title,interval_minutes,next_run_at,enabled) VALUES(p_owner,p_job,j.title,p_interval,p_next,p_enabled) RETURNING * INTO s;
    RETURN to_jsonb(s);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_schedule_update(p_owner uuid,p_id uuid,p_version integer,p_data jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE s public.despacho_agent_schedules;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO s FROM public.despacho_agent_schedules WHERE owner_id=p_owner AND id=p_id FOR UPDATE;
    IF NOT FOUND OR s.version<>p_version THEN RAISE EXCEPTION 'stale schedule' USING ERRCODE='40001'; END IF;
    UPDATE public.despacho_agent_schedules SET enabled=CASE WHEN p_data?'enabled' THEN (p_data->>'enabled')::boolean ELSE enabled END,
        interval_minutes=CASE WHEN p_data?'interval_minutes' THEN (p_data->>'interval_minutes')::integer ELSE interval_minutes END,
        next_run_at=CASE WHEN p_data?'next_run_at' THEN (p_data->>'next_run_at')::timestamptz ELSE next_run_at END,
        version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO s;
    RETURN to_jsonb(s);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_enqueue_due()
RETURNS integer LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE s public.despacho_agent_schedules; j public.despacho_agent_jobs; new_id uuid; n integer=0;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    FOR s IN SELECT * FROM public.despacho_agent_schedules WHERE enabled AND next_run_at<=now() ORDER BY next_run_at LIMIT 5 FOR UPDATE SKIP LOCKED LOOP
        SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=s.job_id AND owner_id=s.owner_id;
        IF NOT FOUND OR j.approved_hash IS DISTINCT FROM j.plan_hash OR j.state IN ('draft','cancelled') THEN
            UPDATE public.despacho_agent_schedules SET enabled=false,last_error='El plan de origen ya no está disponible o aprobado.',version=version+1,updated_at=now() WHERE id=s.id;
            CONTINUE;
        END IF;
        -- Avoid overlapping runs for one recurring assignment.
        IF EXISTS(SELECT 1 FROM public.despacho_agent_jobs WHERE schedule_id=s.id AND state IN ('approved','running','waiting_approval')) THEN
            UPDATE public.despacho_agent_schedules SET next_run_at=now()+interval '5 minutes',last_error='La ejecución anterior sigue en curso.',version=version+1,updated_at=now() WHERE id=s.id;
            CONTINUE;
        END IF;
        new_id=gen_random_uuid();
        INSERT INTO public.despacho_agent_jobs(id,owner_id,title,objective,document_ids,matter_id,playbook_id,allowed_urls,plan,plan_hash,approved_hash,approved_at,state,schedule_id,scheduled_for)
            VALUES(new_id,j.owner_id,j.title,j.objective,j.document_ids,j.matter_id,j.playbook_id,j.allowed_urls,j.plan,j.plan_hash,j.plan_hash,j.approved_at,'approved',s.id,s.next_run_at);
        UPDATE public.despacho_agent_schedules SET last_run_at=now(),last_job_id=new_id,next_run_at=now()+make_interval(mins=>s.interval_minutes),last_error='',version=version+1,updated_at=now() WHERE id=s.id;
        n=n+1;
    END LOOP;
    RETURN n;
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_browser_propose(p_owner uuid,p_job uuid,p_session uuid,p_action jsonb,p_hash text)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs; a public.despacho_agent_browser_actions;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_job AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR j.state IN ('draft','running','cancelled') OR j.manual_control OR j.approved_hash IS DISTINCT FROM j.plan_hash THEN RAISE EXCEPTION 'job not available' USING ERRCODE='55000'; END IF;
    IF EXISTS(SELECT 1 FROM public.despacho_agent_browser_actions WHERE job_id=p_job AND owner_id=p_owner AND state='executing') THEN RAISE EXCEPTION 'action in progress' USING ERRCODE='55000'; END IF;
    UPDATE public.despacho_agent_browser_actions SET state='expired' WHERE job_id=p_job AND owner_id=p_owner AND state='pending';
    INSERT INTO public.despacho_agent_browser_actions(owner_id,job_id,session_id,action,page_hash,expires_at)
        VALUES(p_owner,p_job,p_session,p_action||jsonb_build_object('prior_state',CASE WHEN j.cursor=jsonb_array_length(j.plan) THEN 'completed' ELSE 'approved' END),p_hash,now()+interval '5 minutes') RETURNING * INTO a;
    UPDATE public.despacho_agent_jobs SET state='waiting_approval',version=version+1,updated_at=now() WHERE id=p_job;
    INSERT INTO public.despacho_agent_events(owner_id,job_id,event,detail) VALUES(p_owner,p_job,'browser_action_proposed',jsonb_build_object('action_id',a.id,'action',p_action));
    RETURN to_jsonb(a);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_browser_claim(p_owner uuid,p_job uuid,p_action uuid,p_session uuid,p_hash text,p_version integer)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE a public.despacho_agent_browser_actions; j public.despacho_agent_jobs;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_job AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR j.version<>p_version OR j.state<>'waiting_approval' OR j.manual_control THEN RAISE EXCEPTION 'stale approval' USING ERRCODE='40001'; END IF;
    SELECT * INTO a FROM public.despacho_agent_browser_actions WHERE id=p_action AND job_id=p_job AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR a.state<>'pending' OR a.session_id<>p_session OR a.page_hash<>p_hash OR a.expires_at<=now() THEN RAISE EXCEPTION 'approval expired or used' USING ERRCODE='55000'; END IF;
    UPDATE public.despacho_agent_browser_actions SET state='executing',expires_at=now()+interval '2 minutes' WHERE id=a.id RETURNING * INTO a;
    INSERT INTO public.despacho_agent_events(owner_id,job_id,event,detail) VALUES(p_owner,p_job,'browser_action_approved',jsonb_build_object('action_id',a.id,'action',a.action));
    RETURN to_jsonb(a);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_browser_finish(p_owner uuid,p_job uuid,p_action uuid,p_result jsonb,p_error text DEFAULT '')
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE a public.despacho_agent_browser_actions; j public.despacho_agent_jobs;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_job AND owner_id=p_owner FOR UPDATE;
    SELECT * INTO a FROM public.despacho_agent_browser_actions WHERE id=p_action AND job_id=p_job AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR a.state<>'executing' THEN RAISE EXCEPTION 'invalid completion' USING ERRCODE='40001'; END IF;
    UPDATE public.despacho_agent_browser_actions SET state=CASE WHEN p_error='' THEN 'completed' ELSE 'failed' END,result=p_result||jsonb_build_object('error',left(p_error,1200)),finished_at=now() WHERE id=p_action;
    IF j.state<>'cancelled' THEN UPDATE public.despacho_agent_jobs SET state=coalesce(a.action->>'prior_state','approved'),last_error=left(p_error,1200),version=version+1,updated_at=now() WHERE id=p_job RETURNING * INTO j; END IF;
    INSERT INTO public.despacho_agent_events(owner_id,job_id,event,detail) VALUES(p_owner,p_job,CASE WHEN p_error='' THEN 'browser_action_completed' ELSE 'browser_action_uncertain' END,jsonb_build_object('action_id',a.id,'error',left(p_error,1200)));
    RETURN to_jsonb(j);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_browser_reset(p_owner uuid,p_job uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs; abandoned integer=0;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_job AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR j.state IN ('draft','running','cancelled') THEN RAISE EXCEPTION 'job unavailable' USING ERRCODE='55000'; END IF;
    IF EXISTS(SELECT 1 FROM public.despacho_agent_browser_actions WHERE job_id=p_job AND owner_id=p_owner AND state='executing' AND expires_at>now()) THEN
        RAISE EXCEPTION 'action in progress' USING ERRCODE='55000'; END IF;
    -- Only an explicit close/recovery can abandon an expired in-flight action.
    -- Its effect is unknown; the single-use action is never made pending again.
    UPDATE public.despacho_agent_browser_actions SET state='failed',finished_at=now(),
        result=jsonb_build_object('error','La sesión se cerró o perdió; revisa el sitio. El resultado no se pudo confirmar.','result_verified',false)
        WHERE job_id=p_job AND owner_id=p_owner AND state='executing' AND expires_at<=now();
    GET DIAGNOSTICS abandoned=ROW_COUNT;
    UPDATE public.despacho_agent_browser_actions SET state='expired' WHERE job_id=p_job AND owner_id=p_owner AND state='pending';
    IF j.state='waiting_approval' THEN
        UPDATE public.despacho_agent_jobs SET state=CASE WHEN cursor=jsonb_array_length(plan) THEN 'completed' ELSE 'approved' END,manual_control=false,
            last_error=CASE WHEN abandoned>0 THEN 'Se recuperó una sesión perdida. Revisa el sitio: el resultado de la interacción es incierto y no se repetirá.' ELSE last_error END,
            version=version+1,updated_at=now() WHERE id=p_job RETURNING * INTO j;
    END IF;
    IF abandoned>0 THEN INSERT INTO public.despacho_agent_events(owner_id,job_id,event,detail)
        VALUES(p_owner,p_job,'browser_action_abandoned',jsonb_build_object('count',abandoned,'result_verified',false)); END IF;
    RETURN to_jsonb(j);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_browser_manual(p_owner uuid,p_job uuid,p_manual boolean)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_job AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR j.state IN ('draft','running','cancelled') OR j.approved_hash IS DISTINCT FROM j.plan_hash THEN RAISE EXCEPTION 'job unavailable' USING ERRCODE='55000'; END IF;
    IF EXISTS(SELECT 1 FROM public.despacho_agent_browser_actions WHERE job_id=p_job AND owner_id=p_owner AND state='executing') THEN RAISE EXCEPTION 'action in progress' USING ERRCODE='55000'; END IF;
    UPDATE public.despacho_agent_browser_actions SET state='expired' WHERE job_id=p_job AND owner_id=p_owner AND state='pending';
    UPDATE public.despacho_agent_jobs SET manual_control=p_manual,
        state=CASE WHEN p_manual THEN 'waiting_approval' WHEN cursor=jsonb_array_length(plan) THEN 'completed' ELSE 'approved' END,
        version=version+1,updated_at=now() WHERE id=p_job RETURNING * INTO j;
    INSERT INTO public.despacho_agent_events(owner_id,job_id,event,detail)
        VALUES(p_owner,p_job,CASE WHEN p_manual THEN 'manual_takeover_started' ELSE 'manual_takeover_finished' END,jsonb_build_object('manual',p_manual,'result_verified',false));
    RETURN to_jsonb(j);
END $$;

REVOKE ALL ON FUNCTION public.despacho_agent_control(uuid,uuid,integer,text,jsonb),public.despacho_agent_claim_step(uuid,uuid,integer,uuid),public.despacho_agent_finish_step(uuid,uuid,uuid,integer,jsonb,text),
    public.despacho_agent_schedule_create(uuid,uuid,integer,timestamptz,boolean),public.despacho_agent_schedule_update(uuid,uuid,integer,jsonb),public.despacho_agent_enqueue_due(),
    public.despacho_agent_browser_propose(uuid,uuid,uuid,jsonb,text),public.despacho_agent_browser_claim(uuid,uuid,uuid,uuid,text,integer),public.despacho_agent_browser_finish(uuid,uuid,uuid,jsonb,text),public.despacho_agent_browser_reset(uuid,uuid),public.despacho_agent_browser_manual(uuid,uuid,boolean)
    FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_agent_control(uuid,uuid,integer,text,jsonb),public.despacho_agent_claim_step(uuid,uuid,integer,uuid),public.despacho_agent_finish_step(uuid,uuid,uuid,integer,jsonb,text),
    public.despacho_agent_schedule_create(uuid,uuid,integer,timestamptz,boolean),public.despacho_agent_schedule_update(uuid,uuid,integer,jsonb),public.despacho_agent_enqueue_due(),
    public.despacho_agent_browser_propose(uuid,uuid,uuid,jsonb,text),public.despacho_agent_browser_claim(uuid,uuid,uuid,uuid,text,integer),public.despacho_agent_browser_finish(uuid,uuid,uuid,jsonb,text),public.despacho_agent_browser_reset(uuid,uuid),public.despacho_agent_browser_manual(uuid,uuid,boolean)
    TO service_role;
COMMIT;
-- Conexiones OAuth y firma multiparte V5. Aplicar después de las migraciones V4.
-- Los secretos nunca tienen grants para anon/authenticated. Las operaciones de
-- firma se serializan por expediente y los fallos OTP se confirman, no se
-- revierten mediante una excepción que borraría el contador de intentos.
begin;

create table if not exists public.despacho_conexiones (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  provider text not null check (provider in ('google_drive','microsoft_onedrive','microsoft_sharepoint','microsoft_outlook')),
  label text not null check (char_length(label) between 1 and 254),
  scopes jsonb not null check (jsonb_typeof(scopes)='array'),
  secret text not null check (char_length(secret) between 50 and 100000),
  refresh_lease uuid,
  refresh_until timestamptz,
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  unique(owner_id,provider,label)
);
create table if not exists public.despacho_oauth_estados (
  state_hash text primary key check (state_hash ~ '^[a-f0-9]{64}$'),
  owner_id uuid not null references auth.users(id) on delete cascade,
  provider text not null,
  binding_hash text not null check (binding_hash ~ '^[a-f0-9]{64}$'),
  secret text not null,
  created_at timestamptz not null default clock_timestamp(),
  expires_at timestamptz not null default clock_timestamp()+interval '15 minutes',
  consumed_at timestamptz
);
create index if not exists despacho_oauth_owner_idx on public.despacho_oauth_estados(owner_id,created_at desc);
alter table public.despacho_conexiones enable row level security;
alter table public.despacho_oauth_estados enable row level security;
revoke all on public.despacho_conexiones,public.despacho_oauth_estados from public,anon,authenticated;
grant all on public.despacho_conexiones,public.despacho_oauth_estados to service_role;

create or replace function public.despacho_oauth_begin(p_owner uuid,p_provider text,p_state_hash text,p_binding_hash text,p_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
begin
  if p_owner is null or p_provider not in ('google_drive','microsoft_onedrive','microsoft_sharepoint','microsoft_outlook')
    or p_state_hash !~ '^[a-f0-9]{64}$' or p_binding_hash !~ '^[a-f0-9]{64}$' or char_length(p_secret)>20000 then return jsonb_build_object('error','INVALID_INPUT'); end if;
  perform pg_advisory_xact_lock(hashtextextended('oauth:'||p_owner::text,0));
  delete from public.despacho_oauth_estados where owner_id=p_owner and expires_at<clock_timestamp()-interval '1 day';
  if (select count(*) from public.despacho_oauth_estados where owner_id=p_owner and created_at>clock_timestamp()-interval '15 minutes')>=10
    then return jsonb_build_object('error','LIMIT'); end if;
  insert into public.despacho_oauth_estados(owner_id,provider,state_hash,binding_hash,secret)
    values(p_owner,p_provider,p_state_hash,p_binding_hash,p_secret);
  return jsonb_build_object('created',true);
end $$;

create or replace function public.despacho_oauth_consume(p_owner uuid,p_provider text,p_state_hash text,p_binding_hash text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.despacho_oauth_estados;
begin
  select * into r from public.despacho_oauth_estados where state_hash=p_state_hash and owner_id=p_owner and provider=p_provider for update;
  if not found or r.expires_at<=clock_timestamp() or r.consumed_at is not null or r.binding_hash<>p_binding_hash
    then return jsonb_build_object('error','STATE_INVALID'); end if;
  update public.despacho_oauth_estados set consumed_at=clock_timestamp(),secret='consumed' where state_hash=r.state_hash;
  return jsonb_build_object('secret',r.secret);
end $$;

create or replace function public.despacho_oauth_save(p_owner uuid,p_provider text,p_label text,p_scopes jsonb,p_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.despacho_conexiones;
begin
  perform pg_advisory_xact_lock(hashtextextended('oauth:'||p_owner::text,0));
  if (select count(*) from public.despacho_conexiones where owner_id=p_owner)>=20
    and not exists(select 1 from public.despacho_conexiones where owner_id=p_owner and provider=p_provider and label=p_label)
    then return jsonb_build_object('error','LIMIT'); end if;
  insert into public.despacho_conexiones(owner_id,provider,label,scopes,secret) values(p_owner,p_provider,p_label,p_scopes,p_secret)
    on conflict(owner_id,provider,label) do update set secret=excluded.secret,scopes=excluded.scopes,updated_at=clock_timestamp(),refresh_lease=null,refresh_until=null
    returning * into r;
  return to_jsonb(r)-'secret'-'refresh_lease'-'refresh_until';
end $$;

create or replace function public.despacho_oauth_claim_refresh(p_owner uuid,p_id uuid,p_lease uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.despacho_conexiones;
begin
  select * into r from public.despacho_conexiones where owner_id=p_owner and id=p_id for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  if r.refresh_until>clock_timestamp() then return jsonb_build_object('acquired',false); end if;
  update public.despacho_conexiones set refresh_lease=p_lease,refresh_until=clock_timestamp()+interval '60 seconds' where id=r.id;
  return jsonb_build_object('acquired',true,'secret',r.secret);
end $$;

create or replace function public.despacho_oauth_finish_refresh(p_owner uuid,p_id uuid,p_lease uuid,p_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare updated uuid;
begin
  update public.despacho_conexiones set secret=coalesce(p_secret,secret),refresh_lease=null,refresh_until=null,updated_at=clock_timestamp()
    where owner_id=p_owner and id=p_id and refresh_lease=p_lease returning id into updated;
  return jsonb_build_object('saved',updated is not null);
end $$;

create or replace function public.despacho_connections_export(p_owner uuid)
returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
  if p_owner is null or (coalesce(auth.role(),'')<>'service_role' and (auth.uid() is null or auth.uid()<>p_owner))
    then return jsonb_build_object('error','NOT_FOUND'); end if;
  return coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'owner_id',c.owner_id,'provider',c.provider,
      'label',c.label,'scopes',c.scopes,'created_at',c.created_at,'updated_at',c.updated_at) order by c.created_at)
    from public.despacho_conexiones c where c.owner_id=p_owner),'[]'::jsonb);
end
$$;

-- Imports are idempotent even if two requests race after reading the same list.
create unique index if not exists despacho_import_external_unique
  on public.despacho_items(owner_id,(data->>'external_key')) where kind='document' and data->>'external_key' is not null;

create table if not exists public.despacho_firma_expedientes (
  id uuid primary key,
  owner_id uuid not null references auth.users(id) on delete cascade,
  title text not null check(char_length(title) between 1 and 240),
  status text not null default 'pending' check(status in ('pending','completed','cancelled')),
  signing_order text not null check(signing_order in ('parallel','sequential')),
  documents jsonb not null check(jsonb_typeof(documents)='array' and jsonb_array_length(documents) between 1 and 10),
  manifest jsonb not null,
  manifest_hash text not null check(manifest_hash ~ '^[a-f0-9]{64}$'),
  bundle_hash text not null check(bundle_hash ~ '^[a-f0-9]{64}$'),
  storage_path text not null unique,
  created_at timestamptz not null default clock_timestamp(),
  expires_at timestamptz not null,
  completed_at timestamptz,
  version integer not null default 1,
  check ((status='completed' and completed_at is not null) or (status<>'completed' and completed_at is null))
);
create index if not exists despacho_signing_owner_idx on public.despacho_firma_expedientes(owner_id,created_at desc);
create table if not exists public.despacho_firma_destinatarios (
  id uuid primary key,
  envelope_id uuid not null references public.despacho_firma_expedientes(id) on delete cascade,
  name text not null check(char_length(name) between 2 and 160),
  email text not null check(char_length(email) between 3 and 254 and email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'),
  position integer not null check(position between 1 and 10),
  status text not null default 'pending' check(status in ('pending','signed')),
  token_hash text unique check(token_hash ~ '^[a-f0-9]{64}$'),
  last_link_at timestamptz,
  delivery_status text not null default 'not_sent' check(delivery_status in ('not_sent','smtp_accepted','unconfirmed')),
  opened_at timestamptz,
  otp_hash text check(otp_hash ~ '^[a-f0-9]{64}$'),
  otp_generation uuid,
  otp_expires_at timestamptz,
  otp_last_sent_at timestamptz,
  otp_window_at timestamptz,
  otp_requests integer not null default 0,
  otp_attempts integer not null default 0,
  otp_failures integer not null default 0,
  otp_delivered boolean not null default false,
  signed_at timestamptz,
  signed_name text,
  consent_text text,
  signer_ip text,
  signer_agent text,
  unique(envelope_id,position),unique(envelope_id,email),
  check((status='signed' and signed_at is not null and signed_name is not null and consent_text is not null)
    or (status='pending' and signed_at is null))
);
create table if not exists public.despacho_firma_eventos (
  id bigint generated always as identity primary key,
  envelope_id uuid not null references public.despacho_firma_expedientes(id) on delete cascade,
  recipient_id uuid references public.despacho_firma_destinatarios(id) on delete cascade,
  event text not null,
  at timestamptz not null default clock_timestamp(),
  details jsonb not null default '{}'::jsonb check(octet_length(details::text)<=8192)
);
create index if not exists despacho_signing_events_idx on public.despacho_firma_eventos(envelope_id,id);
alter table public.despacho_firma_expedientes enable row level security;
alter table public.despacho_firma_destinatarios enable row level security;
alter table public.despacho_firma_eventos enable row level security;
revoke all on public.despacho_firma_expedientes,public.despacho_firma_destinatarios,public.despacho_firma_eventos from public,anon,authenticated;
grant all on public.despacho_firma_expedientes,public.despacho_firma_destinatarios,public.despacho_firma_eventos to service_role;
grant usage,select on sequence public.despacho_firma_eventos_id_seq to service_role;
-- No direct DML/SELECT for clients. Security-definer RPCs derive the owner from
-- auth.uid(), return safe fields, and never return link/OTP digests.

insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('despacho-firmas-v5','despacho-firmas-v5',false,26214400,array['application/pdf'])
on conflict(id) do update set public=false,file_size_limit=excluded.file_size_limit,allowed_mime_types=excluded.allowed_mime_types;
-- No client Storage policies for this bucket. All bytes pass through verified
-- owner/link routes; ordinary DMS edit/delete endpoints cannot change a bundle.

create or replace function public._despacho_signing_json(p_id uuid,p_content boolean default true)
returns jsonb language sql stable security definer set search_path='' as $$
 select to_jsonb(e) || jsonb_build_object(
   'documents',case when p_content then e.documents else (select jsonb_agg(value-'text') from jsonb_array_elements(e.documents)) end,
   'recipients',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'name',r.name,'email',r.email,'position',r.position,'status',r.status,
      'delivery_status',r.delivery_status,'opened_at',r.opened_at,'signed_at',r.signed_at,'signed_name',r.signed_name,
      'consent_text',r.consent_text,'signer_ip',r.signer_ip,'signer_agent',r.signer_agent) order by r.position)
      from public.despacho_firma_destinatarios r where r.envelope_id=e.id),'[]'::jsonb),
   'audit',coalesce((select jsonb_agg(jsonb_build_object('event',v.event,'at',v.at,'recipient_id',v.recipient_id,'details',v.details) order by v.id)
      from public.despacho_firma_eventos v where v.envelope_id=e.id),'[]'::jsonb))
 from public.despacho_firma_expedientes e where e.id=p_id;
$$;

create or replace function public.despacho_signing_list(p_id uuid default null)
returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
  if auth.uid() is null then return jsonb_build_object('error','NOT_FOUND'); end if;
  return coalesce((select jsonb_agg(public._despacho_signing_json(e.id,p_id is not null) order by e.created_at desc)
    from (select id,created_at from public.despacho_firma_expedientes where owner_id=auth.uid() and (p_id is null or id=p_id)
      order by created_at desc limit 100) e),'[]'::jsonb);
end $$;

create or replace function public.despacho_signing_create(p_id uuid,p_title text,p_documents jsonb,p_recipients jsonb,p_order text,p_days integer,
 p_storage_path text,p_bundle_hash text,p_manifest_hash text,p_manifest text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare d jsonb; r jsonb; manifest jsonb; existing public.despacho_firma_expedientes;
begin
  if auth.uid() is null then return jsonb_build_object('error','NOT_FOUND'); end if;
  if p_id is null or p_title is null or p_days is null or p_order is null or p_documents is null or p_recipients is null or p_manifest is null
    or p_storage_path<>auth.uid()::text||'/'||p_id::text||'/expediente.pdf'
    or p_order not in ('parallel','sequential') or p_days not between 1 and 30 or char_length(btrim(p_title)) not between 1 and 240
    or jsonb_typeof(p_documents)<>'array' or jsonb_array_length(p_documents) not between 1 and 10
    or jsonb_typeof(p_recipients)<>'array' or jsonb_array_length(p_recipients) not between 1 and 10
    or octet_length(p_documents::text)>8000000 or char_length(p_manifest)>40000
    or p_bundle_hash !~ '^[a-f0-9]{64}$' or p_manifest_hash<>encode(sha256(convert_to(p_manifest,'UTF8')),'hex')
    then return jsonb_build_object('error','INVALID_INPUT'); end if;
  manifest:=p_manifest::jsonb;
  if manifest->>'id'<>p_id::text or manifest->>'title'<>p_title or manifest->>'bundle_hash'<>p_bundle_hash
    or manifest->>'signing_order'<>p_order or manifest->'recipients'<>p_recipients
    then return jsonb_build_object('error','INVALID_INPUT'); end if;
  perform pg_advisory_xact_lock(hashtextextended('signing:'||auth.uid()::text,0));
  select * into existing from public.despacho_firma_expedientes where id=p_id;
  if found then
    if existing.owner_id=auth.uid() and existing.manifest_hash=p_manifest_hash then return public._despacho_signing_json(existing.id); end if;
    return jsonb_build_object('error','INVALID_INPUT');
  end if;
  if (select count(*) from public.despacho_firma_expedientes where owner_id=auth.uid() and created_at>clock_timestamp()-interval '24 hours')>=100
    then return jsonb_build_object('error','LIMIT'); end if;
  for d in select value from jsonb_array_elements(p_documents) loop
    if not exists(select 1 from public.despacho_items where id=(d->>'id')::uuid and owner_id=auth.uid() and kind='document')
      or d->>'sha256' !~ '^[a-f0-9]{64}$' then return jsonb_build_object('error','INVALID_INPUT'); end if;
  end loop;
  insert into public.despacho_firma_expedientes(id,owner_id,title,signing_order,documents,manifest,manifest_hash,bundle_hash,storage_path,expires_at)
    values(p_id,auth.uid(),p_title,p_order,p_documents,manifest,p_manifest_hash,p_bundle_hash,p_storage_path,clock_timestamp()+make_interval(days=>p_days));
  for r in select value from jsonb_array_elements(p_recipients) loop
    insert into public.despacho_firma_destinatarios(id,envelope_id,name,email,position)
      values((r->>'id')::uuid,p_id,r->>'name',lower(r->>'email'),(r->>'position')::integer);
  end loop;
  insert into public.despacho_firma_eventos(envelope_id,event,details) values(p_id,'created',jsonb_build_object('by',auth.uid(),'manifest_hash',p_manifest_hash));
  return public._despacho_signing_json(p_id);
end $$;

create or replace function public.despacho_signing_link(p_id uuid,p_recipient uuid,p_hash text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare e public.despacho_firma_expedientes; r public.despacho_firma_destinatarios;
begin
  select * into e from public.despacho_firma_expedientes where id=p_id and owner_id=auth.uid() for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  if e.status<>'pending' or e.expires_at<=clock_timestamp() then return jsonb_build_object('error','NOT_PENDING'); end if;
  select * into r from public.despacho_firma_destinatarios where id=p_recipient and envelope_id=e.id for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  if r.status<>'pending' then return jsonb_build_object('error','NOT_PENDING'); end if;
  if p_hash is null or p_hash !~ '^[a-f0-9]{64}$' then return jsonb_build_object('error','INVALID_INPUT'); end if;
  if r.last_link_at>clock_timestamp()-interval '30 seconds' then return jsonb_build_object('error','LINK_WAIT','retry_after',30); end if;
  if (select count(*) from public.despacho_firma_eventos where envelope_id=e.id and event='link_rotated' and at>clock_timestamp()-interval '24 hours')>=100
    then return jsonb_build_object('error','LIMIT'); end if;
  update public.despacho_firma_destinatarios set token_hash=p_hash,last_link_at=clock_timestamp(),otp_hash=null,otp_generation=null,otp_expires_at=null,otp_delivered=false
    where id=r.id;
  insert into public.despacho_firma_eventos(envelope_id,recipient_id,event) values(e.id,r.id,'link_rotated');
  return jsonb_build_object('recipient',jsonb_build_object('id',r.id,'name',r.name,'email',r.email,'position',r.position,'status',r.status));
end $$;

create or replace function public.despacho_signing_delivery(p_owner uuid,p_id uuid,p_recipient uuid,p_status text,p_message_id text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare e public.despacho_firma_expedientes; rid uuid;
begin
  select * into e from public.despacho_firma_expedientes where id=p_id and owner_id=p_owner for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  if p_status not in ('smtp_accepted','unconfirmed') or char_length(p_message_id)>300 then return jsonb_build_object('error','INVALID_INPUT'); end if;
  update public.despacho_firma_destinatarios set delivery_status=p_status where id=p_recipient and envelope_id=e.id returning id into rid;
  if rid is null then return jsonb_build_object('error','NOT_FOUND'); end if;
  insert into public.despacho_firma_eventos(envelope_id,recipient_id,event,details) values(e.id,rid,'invitation_'||p_status,jsonb_build_object('message_id',p_message_id));
  return jsonb_build_object('recorded',true);
end $$;

create or replace function public.despacho_signing_cancel(p_id uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare e public.despacho_firma_expedientes;
begin
  select * into e from public.despacho_firma_expedientes where id=p_id and owner_id=auth.uid() for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  if e.status<>'pending' then return jsonb_build_object('error','NOT_PENDING'); end if;
  update public.despacho_firma_expedientes set status='cancelled',version=version+1 where id=e.id;
  update public.despacho_firma_destinatarios set token_hash=null,otp_hash=null,otp_generation=null,otp_expires_at=null where envelope_id=e.id;
  insert into public.despacho_firma_eventos(envelope_id,event,details) values(e.id,'cancelled',jsonb_build_object('by',auth.uid()));
  return public._despacho_signing_json(e.id);
end $$;

create or replace function public.despacho_signing_view(p_hash text,p_ip text,p_agent text,p_record_open boolean)
returns jsonb language plpgsql security definer set search_path='' as $$
declare e public.despacho_firma_expedientes; r public.despacho_firma_destinatarios; envelope uuid; can_sign boolean;
begin
  select envelope_id into envelope from public.despacho_firma_destinatarios where token_hash=p_hash;
  if envelope is null then return jsonb_build_object('error','LINK_UNAVAILABLE'); end if;
  select * into e from public.despacho_firma_expedientes where id=envelope for update;
  select * into r from public.despacho_firma_destinatarios where token_hash=p_hash and envelope_id=e.id for update;
  if not found or e.status='cancelled' or e.expires_at<=clock_timestamp() then return jsonb_build_object('error','LINK_UNAVAILABLE'); end if;
  if p_record_open and r.opened_at is null then
    update public.despacho_firma_destinatarios set opened_at=clock_timestamp() where id=r.id;
    insert into public.despacho_firma_eventos(envelope_id,recipient_id,event,details) values(e.id,r.id,'opened',jsonb_build_object('ip',left(p_ip,64),'agent',left(p_agent,512)));
  end if;
  can_sign:= e.status='pending' and r.status='pending' and (e.signing_order='parallel' or not exists(
    select 1 from public.despacho_firma_destinatarios where envelope_id=e.id and position<r.position and status<>'signed'));
  return jsonb_build_object('id',e.id,'title',e.title,'status',e.status,'manifest_hash',e.manifest_hash,'bundle_hash',e.bundle_hash,
    'storage_path',e.storage_path,'expires_at',e.expires_at,'documents',e.documents,'can_sign',can_sign,
    'recipient',jsonb_build_object('id',r.id,'name',r.name,'email',r.email,'status',r.status));
end $$;

create or replace function public.despacho_signing_otp(p_hash text,p_otp_hash text,p_generation uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare e public.despacho_firma_expedientes; r public.despacho_firma_destinatarios; envelope uuid;
begin
  select envelope_id into envelope from public.despacho_firma_destinatarios where token_hash=p_hash;
  if envelope is null then return jsonb_build_object('error','LINK_UNAVAILABLE'); end if;
  select * into e from public.despacho_firma_expedientes where id=envelope for update;
  select * into r from public.despacho_firma_destinatarios where token_hash=p_hash and envelope_id=e.id for update;
  if not found or e.status<>'pending' or e.expires_at<=clock_timestamp() or r.status<>'pending' then return jsonb_build_object('error','LINK_UNAVAILABLE'); end if;
  if p_otp_hash is null or p_otp_hash !~ '^[a-f0-9]{64}$' or p_generation is null then return jsonb_build_object('error','INVALID_INPUT'); end if;
  if e.signing_order='sequential' and exists(select 1 from public.despacho_firma_destinatarios where envelope_id=e.id and position<r.position and status<>'signed')
    then return jsonb_build_object('error','WAIT_TURN'); end if;
  if r.otp_last_sent_at>clock_timestamp()-interval '60 seconds' then return jsonb_build_object('error','OTP_WAIT','retry_after',60); end if;
  if r.otp_window_at is null or r.otp_window_at<clock_timestamp()-interval '24 hours' then
    r.otp_requests:=0; r.otp_failures:=0;
    update public.despacho_firma_destinatarios set otp_window_at=clock_timestamp(),otp_requests=0,otp_failures=0 where id=r.id;
  end if;
  if r.otp_requests>=10 or r.otp_failures>=20 then return jsonb_build_object('error','OTP_LIMIT','retry_after',86400); end if;
  update public.despacho_firma_destinatarios set otp_hash=p_otp_hash,otp_generation=p_generation,otp_expires_at=clock_timestamp()+interval '10 minutes',
    otp_last_sent_at=clock_timestamp(),otp_requests=otp_requests+1,otp_attempts=0,otp_delivered=false where id=r.id;
  insert into public.despacho_firma_eventos(envelope_id,recipient_id,event) values(e.id,r.id,'otp_requested');
  return jsonb_build_object('recipient_id',r.id,'email',r.email,'title',e.title);
end $$;

create or replace function public.despacho_signing_otp_delivery(p_recipient uuid,p_generation uuid,p_sent boolean)
returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.despacho_firma_destinatarios; envelope uuid;
begin
  select envelope_id into envelope from public.despacho_firma_destinatarios where id=p_recipient;
  perform 1 from public.despacho_firma_expedientes where id=envelope for update;
  select * into r from public.despacho_firma_destinatarios where id=p_recipient and otp_generation=p_generation for update;
  if not found then return jsonb_build_object('recorded',false); end if;
  update public.despacho_firma_destinatarios set otp_delivered=p_sent,otp_hash=case when p_sent then otp_hash else null end where id=r.id;
  insert into public.despacho_firma_eventos(envelope_id,recipient_id,event) values(r.envelope_id,r.id,case when p_sent then 'otp_smtp_accepted' else 'otp_delivery_unconfirmed' end);
  return jsonb_build_object('recorded',true);
end $$;

create or replace function public.despacho_signing_accept(p_hash text,p_otp_hash text,p_name text,p_consent text,p_manifest_hash text,p_ip text,p_agent text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare e public.despacho_firma_expedientes; r public.despacho_firma_destinatarios; envelope uuid; finished boolean;
begin
  select envelope_id into envelope from public.despacho_firma_destinatarios where token_hash=p_hash;
  if envelope is null then return jsonb_build_object('error','LINK_UNAVAILABLE'); end if;
  select * into e from public.despacho_firma_expedientes where id=envelope for update;
  select * into r from public.despacho_firma_destinatarios where token_hash=p_hash and envelope_id=e.id for update;
  if not found or e.status='cancelled' or e.expires_at<=clock_timestamp() then return jsonb_build_object('error','LINK_UNAVAILABLE'); end if;
  if p_name is null or p_consent is null or p_otp_hash is null or char_length(btrim(p_name)) not between 2 and 160
    or char_length(p_consent) not between 30 and 1000 or p_name ~ '[[:cntrl:]]' or p_otp_hash !~ '^[a-f0-9]{64}$'
    then return jsonb_build_object('error','INVALID_INPUT'); end if;
  if p_manifest_hash is null or p_manifest_hash<>e.manifest_hash then return jsonb_build_object('error','DOCUMENT_CHANGED'); end if;
  if r.status='signed' then return jsonb_build_object('signed',true,'completed',e.status='completed','signed_at',r.signed_at,'idempotent',true); end if;
  if e.status<>'pending' then return jsonb_build_object('error','NOT_PENDING'); end if;
  if e.signing_order='sequential' and exists(select 1 from public.despacho_firma_destinatarios where envelope_id=e.id and position<r.position and status<>'signed')
    then return jsonb_build_object('error','WAIT_TURN'); end if;
  if r.otp_failures>=20 or r.otp_attempts>=5 then return jsonb_build_object('error','OTP_LIMIT','retry_after',86400); end if;
  if r.otp_hash is null or not r.otp_delivered or r.otp_expires_at<=clock_timestamp() or r.otp_hash<>p_otp_hash then
    update public.despacho_firma_destinatarios set otp_attempts=otp_attempts+1,otp_failures=otp_failures+1 where id=r.id;
    insert into public.despacho_firma_eventos(envelope_id,recipient_id,event,details) values(e.id,r.id,'otp_rejected',jsonb_build_object('ip',left(p_ip,64)));
    return jsonb_build_object('error','OTP_INVALID');
  end if;
  update public.despacho_firma_destinatarios set status='signed',signed_at=clock_timestamp(),signed_name=btrim(p_name),consent_text=p_consent,
    signer_ip=left(p_ip,64),signer_agent=left(p_agent,512),otp_hash=null,otp_generation=null,otp_expires_at=null,otp_delivered=false
    where id=r.id returning * into r;
  finished:=not exists(select 1 from public.despacho_firma_destinatarios where envelope_id=e.id and status<>'signed');
  update public.despacho_firma_expedientes set status=case when finished then 'completed' else 'pending' end,
    completed_at=case when finished then clock_timestamp() else null end,version=version+1 where id=e.id;
  insert into public.despacho_firma_eventos(envelope_id,recipient_id,event,details) values(e.id,r.id,'signed',
    jsonb_build_object('manifest_hash',e.manifest_hash,'email_verified',r.email,'ip',r.signer_ip));
  if finished then insert into public.despacho_firma_eventos(envelope_id,event) values(e.id,'completed'); end if;
  return jsonb_build_object('signed',true,'completed',finished,'signed_at',r.signed_at,'recipient_id',r.id,'manifest_hash',e.manifest_hash);
end $$;

create or replace function public.despacho_signing_export(p_owner uuid)
returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
  if p_owner is null or (coalesce(auth.role(),'')<>'service_role' and (auth.uid() is null or auth.uid()<>p_owner))
    then return jsonb_build_object('error','NOT_FOUND'); end if;
  return coalesce((select jsonb_agg(public._despacho_signing_json(e.id) order by e.created_at)
    from public.despacho_firma_expedientes e where e.owner_id=p_owner),'[]'::jsonb);
end
$$;

-- Every SECURITY DEFINER helper starts with PUBLIC execute disabled. Public
-- routes can invoke only the service-role functions through the trusted server.
revoke all on function public.despacho_oauth_begin(uuid,text,text,text,text),public.despacho_oauth_consume(uuid,text,text,text),
 public.despacho_oauth_save(uuid,text,text,jsonb,text),public.despacho_oauth_claim_refresh(uuid,uuid,uuid),
 public.despacho_oauth_finish_refresh(uuid,uuid,uuid,text),public.despacho_connections_export(uuid),public._despacho_signing_json(uuid,boolean),
 public.despacho_signing_list(uuid),public.despacho_signing_create(uuid,text,jsonb,jsonb,text,integer,text,text,text,text),
 public.despacho_signing_link(uuid,uuid,text),public.despacho_signing_delivery(uuid,uuid,uuid,text,text),
 public.despacho_signing_cancel(uuid),public.despacho_signing_view(text,text,text,boolean),
 public.despacho_signing_otp(text,text,uuid),public.despacho_signing_otp_delivery(uuid,uuid,boolean),
 public.despacho_signing_accept(text,text,text,text,text,text,text),public.despacho_signing_export(uuid)
 from public,anon,authenticated;

grant execute on function public.despacho_oauth_begin(uuid,text,text,text,text),public.despacho_oauth_consume(uuid,text,text,text),
 public.despacho_oauth_save(uuid,text,text,jsonb,text),public.despacho_oauth_claim_refresh(uuid,uuid,uuid),
 public.despacho_oauth_finish_refresh(uuid,uuid,uuid,text),public.despacho_signing_delivery(uuid,uuid,uuid,text,text),
 public.despacho_signing_view(text,text,text,boolean),public.despacho_signing_otp(text,text,uuid),
 public.despacho_signing_otp_delivery(uuid,uuid,boolean),public.despacho_signing_accept(text,text,text,text,text,text,text),
 public.despacho_signing_export(uuid),public.despacho_connections_export(uuid) to service_role;
grant execute on function public.despacho_signing_list(uuid),public.despacho_signing_create(uuid,text,jsonb,jsonb,text,integer,text,text,text,text),
 public.despacho_signing_link(uuid,uuid,text),public.despacho_signing_cancel(uuid),public.despacho_signing_export(uuid),public.despacho_connections_export(uuid) to authenticated;

commit;
-- V5: contenido indexado por propietario, búsqueda textual + vectorial.
-- Los originales, permisos y versiones siguen en despacho_items.
BEGIN;
UPDATE storage.buckets SET allowed_mime_types=ARRAY['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document',
 'text/plain','text/markdown','image/png','image/jpeg','image/tiff','image/webp','message/rfc822'] WHERE id='despacho-documentos';
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
-- SECURITY INVOKER conserva RLS; el rol también necesita resolver el tipo vector.
GRANT USAGE ON SCHEMA extensions TO authenticated,service_role;

CREATE TABLE IF NOT EXISTS public.despacho_indice (
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    document_id uuid NOT NULL,
    document_version integer NOT NULL CHECK(document_version>0),
    ordinal integer NOT NULL CHECK(ordinal BETWEEN 0 AND 499),
    page integer CHECK(page>0),
    segment integer CHECK(segment>0),
    content text NOT NULL CHECK(char_length(content) BETWEEN 1 AND 4000),
    embedding extensions.vector(768),
    embedding_model text,
    fts tsvector GENERATED ALWAYS AS (to_tsvector('spanish'::regconfig, content)) STORED,
    indexed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(owner_id,document_id,ordinal),
    FOREIGN KEY(owner_id,document_id) REFERENCES public.despacho_items(owner_id,id) ON DELETE CASCADE,
    CHECK((embedding IS NULL)=(embedding_model IS NULL))
);
CREATE INDEX IF NOT EXISTS despacho_indice_fts ON public.despacho_indice USING gin(fts);
CREATE INDEX IF NOT EXISTS despacho_indice_owner ON public.despacho_indice(owner_id,document_id,document_version);
CREATE INDEX IF NOT EXISTS despacho_indice_vector ON public.despacho_indice USING hnsw(embedding extensions.vector_cosine_ops);
ALTER TABLE public.despacho_indice ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.despacho_indice FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT,DELETE ON public.despacho_indice TO authenticated;
GRANT ALL ON public.despacho_indice TO service_role;
DROP POLICY IF EXISTS despacho_indice_owner ON public.despacho_indice;
CREATE POLICY despacho_indice_owner ON public.despacho_indice FOR ALL TO authenticated
 USING(owner_id=(SELECT auth.uid())) WITH CHECK(owner_id=(SELECT auth.uid()));

CREATE OR REPLACE FUNCTION public.despacho_indexar_documento(p_document_id uuid,p_version integer,p_chunks jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE d public.despacho_items; c jsonb; n integer=0;
BEGIN
 IF auth.uid() IS NULL OR jsonb_typeof(p_chunks)<>'array' OR jsonb_array_length(p_chunks)>500
    OR octet_length(p_chunks::text)>12582912 THEN
   RAISE EXCEPTION 'Índice inválido.' USING ERRCODE='22023';
 END IF;
 SELECT * INTO d FROM public.despacho_items WHERE id=p_document_id AND owner_id=auth.uid() AND kind='document' FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Documento no accesible.' USING ERRCODE='42501'; END IF;
 IF d.version<>p_version THEN RAISE EXCEPTION 'El documento cambió durante la indexación.' USING ERRCODE='40001'; END IF;
 DELETE FROM public.despacho_indice WHERE document_id=p_document_id AND owner_id=auth.uid();
 FOR c IN SELECT value FROM jsonb_array_elements(p_chunks) LOOP
   INSERT INTO public.despacho_indice(owner_id,document_id,document_version,ordinal,page,segment,content,embedding,embedding_model)
   VALUES(auth.uid(),p_document_id,p_version,n,NULLIF(c->>'page','')::integer,NULLIF(c->>'segment','')::integer,c->>'content',
     CASE WHEN c->'embedding' IS NULL OR c->'embedding'='null'::jsonb THEN NULL ELSE (c->>'embedding')::extensions.vector END,
     NULLIF(c->>'embedding_model',''));
   n=n+1;
 END LOOP;
 RETURN jsonb_build_object('document_id',p_document_id,'document_version',p_version,'chunks',n);
END;
$$;
REVOKE ALL ON FUNCTION public.despacho_indexar_documento(uuid,integer,jsonb) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_indexar_documento(uuid,integer,jsonb) TO authenticated;

CREATE OR REPLACE FUNCTION public.despacho_buscar_conocimiento_interno(
 p_owner uuid,p_query text,p_embedding extensions.vector DEFAULT NULL,p_model text DEFAULT NULL,
 p_scope text DEFAULT 'documents',p_matter_id uuid DEFAULT NULL,p_filters jsonb DEFAULT '{}'::jsonb,p_limit integer DEFAULT 20)
RETURNS TABLE(document_id uuid,title text,excerpt text,page integer,segment integer,source_url text,
 document_version integer,score double precision,method text)
LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 WITH eligible AS (
   SELECT i.*,d.title,d.data FROM public.despacho_indice i
   JOIN public.despacho_items d ON d.id=i.document_id AND d.owner_id=i.owner_id AND d.version=i.document_version
   WHERE i.owner_id=p_owner AND (p_owner=auth.uid() OR auth.role()='service_role') AND d.kind='document'
   AND ((p_scope='legal' AND d.data->>'legal_source'='true') OR (p_scope='documents' AND COALESCE(d.data->>'legal_source','false')<>'true'))
   AND (p_matter_id IS NULL OR d.matter_id=p_matter_id)
   AND (p_filters->'document_ids' IS NULL OR d.id::text IN (SELECT jsonb_array_elements_text(p_filters->'document_ids')))
   AND (NULLIF(p_filters->>'court','') IS NULL OR d.data->'legal_metadata'->>'court'=p_filters->>'court')
   AND (NULLIF(p_filters->>'year','') IS NULL OR d.data->'legal_metadata'->>'year'=p_filters->>'year')
   AND (NULLIF(p_filters->>'document_type','') IS NULL OR d.data->'legal_metadata'->>'document_type'=p_filters->>'document_type')
 ), lexical AS (
   SELECT document_id,ordinal,row_number() OVER(ORDER BY ts_rank_cd(fts,websearch_to_tsquery('spanish',left(p_query,4000))) DESC,document_id,ordinal) AS r
   FROM eligible WHERE fts @@ websearch_to_tsquery('spanish',left(p_query,4000)) LIMIT 100
 ), semantic AS (
   SELECT document_id,ordinal,row_number() OVER(ORDER BY embedding OPERATOR(extensions.<=>) p_embedding,document_id,ordinal) AS r
   FROM eligible WHERE p_embedding IS NOT NULL AND embedding IS NOT NULL AND embedding_model=p_model
     AND embedding OPERATOR(extensions.<=>) p_embedding < 0.75
   ORDER BY embedding OPERATOR(extensions.<=>) p_embedding LIMIT 100
 ), ranked AS (
   SELECT COALESCE(l.document_id,s.document_id) document_id,COALESCE(l.ordinal,s.ordinal) ordinal,
     COALESCE(1.0/(60+l.r),0)+COALESCE(1.0/(60+s.r),0) AS relevance,
     CASE WHEN l.r IS NOT NULL AND s.r IS NOT NULL THEN 'hybrid' WHEN s.r IS NOT NULL THEN 'semantic' ELSE 'text' END AS method
   FROM lexical l FULL OUTER JOIN semantic s ON s.document_id=l.document_id AND s.ordinal=l.ordinal
 ) SELECT e.document_id,e.title,e.content,e.page,e.segment,e.data->>'source_url',e.document_version,r.relevance::double precision,r.method
 FROM ranked r JOIN eligible e ON e.document_id=r.document_id AND e.ordinal=r.ordinal
 ORDER BY r.relevance DESC,e.document_id,e.ordinal LIMIT LEAST(GREATEST(p_limit,1),50);
$$;
REVOKE ALL ON FUNCTION public.despacho_buscar_conocimiento_interno(uuid,text,extensions.vector,text,text,uuid,jsonb,integer) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_buscar_conocimiento_interno(uuid,text,extensions.vector,text,text,uuid,jsonb,integer) TO authenticated,service_role;

CREATE OR REPLACE FUNCTION public.despacho_buscar_conocimiento(
 p_query text,p_embedding extensions.vector DEFAULT NULL,p_model text DEFAULT NULL,
 p_scope text DEFAULT 'documents',p_matter_id uuid DEFAULT NULL,p_filters jsonb DEFAULT '{}'::jsonb,p_limit integer DEFAULT 20)
RETURNS TABLE(document_id uuid,title text,excerpt text,page integer,segment integer,source_url text,
 document_version integer,score double precision,method text)
LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT * FROM public.despacho_buscar_conocimiento_interno(auth.uid(),p_query,p_embedding,p_model,p_scope,p_matter_id,p_filters,p_limit);
$$;
REVOKE ALL ON FUNCTION public.despacho_buscar_conocimiento(text,extensions.vector,text,text,uuid,jsonb,integer) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_buscar_conocimiento(text,extensions.vector,text,text,uuid,jsonb,integer) TO authenticated;

CREATE OR REPLACE FUNCTION public.despacho_cobertura_indice_interna(p_owner uuid,p_model text)
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT jsonb_build_object(
  'documents',(SELECT count(*) FROM public.despacho_items WHERE owner_id=p_owner AND kind='document'),
  'indexed_documents',(SELECT count(DISTINCT i.document_id) FROM public.despacho_indice i JOIN public.despacho_items d
     ON d.id=i.document_id AND d.owner_id=i.owner_id AND d.version=i.document_version WHERE i.owner_id=p_owner),
  'semantic_documents',(SELECT count(DISTINCT i.document_id) FROM public.despacho_indice i JOIN public.despacho_items d
     ON d.id=i.document_id AND d.owner_id=i.owner_id AND d.version=i.document_version
     WHERE i.owner_id=p_owner AND i.embedding IS NOT NULL AND (p_model IS NULL OR i.embedding_model=p_model)),
  'embedding_model',p_model,
  'legal_documents',(SELECT count(*) FROM public.despacho_items WHERE owner_id=p_owner AND kind='document' AND data->>'legal_source'='true')
 ) WHERE p_owner=auth.uid() OR auth.role()='service_role';
$$;
REVOKE ALL ON FUNCTION public.despacho_cobertura_indice_interna(uuid,text) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_cobertura_indice_interna(uuid,text) TO authenticated,service_role;
CREATE OR REPLACE FUNCTION public.despacho_cobertura_indice_interna(p_owner uuid)
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT public.despacho_cobertura_indice_interna(p_owner,NULL);
$$;
REVOKE ALL ON FUNCTION public.despacho_cobertura_indice_interna(uuid) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_cobertura_indice_interna(uuid) TO authenticated,service_role;
CREATE OR REPLACE FUNCTION public.despacho_cobertura_indice(p_model text)
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT public.despacho_cobertura_indice_interna(auth.uid(),p_model);
$$;
REVOKE ALL ON FUNCTION public.despacho_cobertura_indice(text) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_cobertura_indice(text) TO authenticated;
CREATE OR REPLACE FUNCTION public.despacho_cobertura_indice()
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT public.despacho_cobertura_indice_interna(auth.uid());
$$;
REVOKE ALL ON FUNCTION public.despacho_cobertura_indice() FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_cobertura_indice() TO authenticated;
COMMIT;
-- Salas de documentos compartidos. Originales privados, permisos por enlace,
-- cuotas duraderas y aportes pendientes de incorporación expresa al DMS.
begin;
create table if not exists public.despacho_salas (
  id uuid primary key,
  owner_id uuid not null references auth.users(id) on delete cascade,
  matter_id uuid references public.despacho_items(id) on delete set null,
  title text not null check(char_length(title) between 1 and 240),
  description text not null default '' check(char_length(description)<=4000),
  documents jsonb not null check(jsonb_typeof(documents)='array' and jsonb_array_length(documents) between 1 and 20),
  status text not null default 'active' check(status in ('active','revoked')),
  created_at timestamptz not null default clock_timestamp(),
  expires_at timestamptz not null,
  revoked_at timestamptz,
  version integer not null default 1
);
create index if not exists despacho_salas_owner_idx on public.despacho_salas(owner_id,created_at desc);
create table if not exists public.despacho_sala_enlaces (
  id uuid primary key,
  room_id uuid not null references public.despacho_salas(id) on delete cascade,
  label text not null check(char_length(label) between 1 and 120),
  token_hash text not null unique check(token_hash ~ '^[a-f0-9]{64}$'),
  can_view boolean not null,
  can_download boolean not null,
  can_upload boolean not null,
  created_at timestamptz not null default clock_timestamp(),
  expires_at timestamptz not null,
  revoked_at timestamptz,
  opened_at timestamptz,
  check(can_view or can_upload),check(not can_download or can_view)
);
create table if not exists public.despacho_sala_aportes (
  id uuid primary key,
  room_id uuid not null references public.despacho_salas(id) on delete cascade,
  link_id uuid not null references public.despacho_sala_enlaces(id) on delete cascade,
  request_id uuid not null,
  filename text not null check(char_length(filename) between 1 and 200),
  mime text not null check(mime in ('application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain')),
  bytes bigint not null check(bytes between 1 and 10485760),
  sha256 text not null check(sha256 ~ '^[a-f0-9]{64}$'),
  status text not null default 'pending' check(status in ('pending','received','importing','imported','rejected','failed')),
  created_at timestamptz not null default clock_timestamp(),
  received_at timestamptz,
  item_id uuid,
  import_lease uuid,
  import_until timestamptz,
  unique(link_id,request_id)
);
create index if not exists despacho_sala_aportes_room_idx on public.despacho_sala_aportes(room_id,created_at);
create table if not exists public.despacho_sala_eventos (
  id bigint generated always as identity primary key,
  room_id uuid not null references public.despacho_salas(id) on delete cascade,
  link_id uuid references public.despacho_sala_enlaces(id) on delete cascade,
  event text not null,
  at timestamptz not null default clock_timestamp(),
  details jsonb not null default '{}'::jsonb check(octet_length(details::text)<=4096)
);
create index if not exists despacho_sala_eventos_room_idx on public.despacho_sala_eventos(room_id,id);
alter table public.despacho_salas enable row level security;
alter table public.despacho_sala_enlaces enable row level security;
alter table public.despacho_sala_aportes enable row level security;
alter table public.despacho_sala_eventos enable row level security;
revoke all on public.despacho_salas,public.despacho_sala_enlaces,public.despacho_sala_aportes,public.despacho_sala_eventos from public,anon,authenticated;
grant all on public.despacho_salas,public.despacho_sala_enlaces,public.despacho_sala_aportes,public.despacho_sala_eventos to service_role;
grant usage,select on sequence public.despacho_sala_eventos_id_seq to service_role;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('despacho-salas-v5','despacho-salas-v5',false,26214400,array['application/pdf','application/octet-stream'])
on conflict(id) do update set public=false,file_size_limit=excluded.file_size_limit,allowed_mime_types=excluded.allowed_mime_types;

create or replace function public._despacho_room_json(p_id uuid,p_full boolean default true)
returns jsonb language sql stable security definer set search_path='' as $$
  select to_jsonb(r)||jsonb_build_object(
    'links',case when p_full then coalesce((select jsonb_agg(to_jsonb(l)-'token_hash' order by l.created_at) from public.despacho_sala_enlaces l where l.room_id=r.id),'[]'::jsonb) else '[]'::jsonb end,
    'uploads',case when p_full then coalesce((select jsonb_agg(to_jsonb(u)-'import_lease'-'import_until'-'request_id' order by u.created_at desc) from public.despacho_sala_aportes u where u.room_id=r.id),'[]'::jsonb) else '[]'::jsonb end,
    'audit_count',case when p_full then (select count(*) from public.despacho_sala_eventos where room_id=r.id) else 0 end,
    'audit',case when p_full then coalesce((select jsonb_agg(jsonb_build_object('event',v.event,'at',v.at,'link_id',v.link_id,'details',v.details) order by v.id desc)
      from (select * from public.despacho_sala_eventos where room_id=r.id order by id desc limit 1000) v),'[]'::jsonb) else '[]'::jsonb end)
  from public.despacho_salas r where r.id=p_id;
$$;

drop function if exists public.despacho_rooms_list(uuid);
create or replace function public.despacho_rooms_list(p_id uuid default null,p_offset integer default 0,p_limit integer default 50)
returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
  if auth.uid() is null then return jsonb_build_object('error','NOT_FOUND'); end if;
  if p_offset is null or p_limit is null or p_offset not between 0 and 100000 or p_limit not between 1 and 100
    then return jsonb_build_object('error','INVALID_INPUT'); end if;
  return coalesce((select jsonb_agg(public._despacho_room_json(r.id,p_id is not null) order by r.created_at desc)
    from (select id,created_at from public.despacho_salas where owner_id=auth.uid() and (p_id is null or id=p_id) order by created_at desc limit p_limit offset p_offset) r),'[]'::jsonb);
end $$;

create or replace function public.despacho_rooms_create(p_id uuid,p_title text,p_description text,p_documents jsonb,p_matter uuid,p_days integer)
returns jsonb language plpgsql security definer set search_path='' as $$
declare d jsonb; r public.despacho_salas; total_bytes bigint:=0; total_pages integer:=0;
begin
  if auth.uid() is null then return jsonb_build_object('error','NOT_FOUND'); end if;
  if p_id is null or p_title is null or p_description is null or p_documents is null or p_days is null
    or char_length(btrim(p_title)) not between 1 and 240 or p_title ~ '[[:cntrl:]]' or char_length(p_description)>4000
    or p_days not between 1 and 90 or jsonb_typeof(p_documents)<>'array' or jsonb_array_length(p_documents) not between 1 and 20
    then return jsonb_build_object('error','INVALID_INPUT'); end if;
  if p_matter is not null and not exists(select 1 from public.despacho_items where id=p_matter and owner_id=auth.uid() and kind='matter')
    then return jsonb_build_object('error','INVALID_INPUT'); end if;
  perform pg_advisory_xact_lock(hashtextextended('rooms:'||auth.uid()::text,0));
  select * into r from public.despacho_salas where id=p_id;
  if found then
    if r.owner_id=auth.uid() and r.documents=p_documents and r.title=p_title and r.description=p_description and r.matter_id is not distinct from p_matter
      then return public._despacho_room_json(r.id); end if;
    return jsonb_build_object('error','INVALID_INPUT');
  end if;
  if (select count(*) from public.despacho_salas where owner_id=auth.uid() and created_at>clock_timestamp()-interval '24 hours')>=30
    then return jsonb_build_object('error','LIMIT'); end if;
  if (select count(distinct value->>'id') from jsonb_array_elements(p_documents))<>jsonb_array_length(p_documents)
    then return jsonb_build_object('error','INVALID_INPUT'); end if;
  for d in select value from jsonb_array_elements(p_documents) loop
    if not (d ?& array['id','title','source_version','sha256','bytes','pages','representation'])
      or not exists(select 1 from public.despacho_items where id=(d->>'id')::uuid and owner_id=auth.uid() and kind='document' and version=(d->>'source_version')::integer)
      or d->>'sha256' !~ '^[a-f0-9]{64}$' or (d->>'bytes')::bigint not between 1 and 26214400 or (d->>'pages')::integer not between 1 and 500
      then return jsonb_build_object('error','INVALID_INPUT'); end if;
    total_bytes:=total_bytes+(d->>'bytes')::bigint;total_pages:=total_pages+(d->>'pages')::integer;
  end loop;
  if total_bytes>26214400 or total_pages>500 then return jsonb_build_object('error','LIMIT'); end if;
  insert into public.despacho_salas(id,owner_id,matter_id,title,description,documents,expires_at)
    values(p_id,auth.uid(),p_matter,p_title,p_description,p_documents,clock_timestamp()+make_interval(days=>p_days));
  insert into public.despacho_sala_eventos(room_id,event,details) values(p_id,'created',jsonb_build_object('by',auth.uid()));
  return public._despacho_room_json(p_id);
end $$;

create or replace function public.despacho_rooms_link(p_room uuid,p_id uuid,p_label text,p_hash text,p_view boolean,p_download boolean,p_upload boolean,p_days integer)
returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.despacho_salas; l public.despacho_sala_enlaces;
begin
  select * into r from public.despacho_salas where id=p_room and owner_id=auth.uid() for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  if r.status<>'active' or r.expires_at<=clock_timestamp() then return jsonb_build_object('error','INACTIVE'); end if;
  if p_id is null or p_label is null or p_hash is null or p_view is null or p_download is null or p_upload is null or p_days is null
    or char_length(btrim(p_label)) not between 1 and 120 or p_label ~ '[[:cntrl:]]' or p_hash !~ '^[a-f0-9]{64}$'
    or not(p_view or p_upload) or (p_download and not p_view) or p_days not between 1 and 90
    then return jsonb_build_object('error','INVALID_INPUT'); end if;
  if (select count(*) from public.despacho_sala_enlaces where room_id=r.id)>=100
    then return jsonb_build_object('error','LIMIT'); end if;
  insert into public.despacho_sala_enlaces(id,room_id,label,token_hash,can_view,can_download,can_upload,expires_at)
    values(p_id,r.id,p_label,p_hash,p_view,p_download,p_upload,least(r.expires_at,clock_timestamp()+make_interval(days=>p_days))) returning * into l;
  insert into public.despacho_sala_eventos(room_id,link_id,event,details) values(r.id,l.id,'link_created',jsonb_build_object('label',p_label,'view',p_view,'download',p_download,'upload',p_upload));
  return to_jsonb(l)-'token_hash';
end $$;

create or replace function public.despacho_rooms_revoke(p_room uuid,p_link uuid default null)
returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.despacho_salas; l public.despacho_sala_enlaces;
begin
  select * into r from public.despacho_salas where id=p_room and owner_id=auth.uid() for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  if p_link is null then
    if r.status='revoked' then return public._despacho_room_json(r.id); end if;
    update public.despacho_salas set status='revoked',revoked_at=clock_timestamp(),version=version+1 where id=r.id;
    update public.despacho_sala_enlaces set revoked_at=coalesce(revoked_at,clock_timestamp()) where room_id=r.id;
    insert into public.despacho_sala_eventos(room_id,event) values(r.id,'revoked');
  else
    select * into l from public.despacho_sala_enlaces where id=p_link and room_id=r.id for update;
    if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
    if l.revoked_at is null then
      update public.despacho_sala_enlaces set revoked_at=clock_timestamp() where id=l.id;
      insert into public.despacho_sala_eventos(room_id,link_id,event) values(r.id,l.id,'link_revoked');
    end if;
  end if;
  return public._despacho_room_json(r.id);
end $$;

create or replace function public.despacho_rooms_public(p_hash text,p_document uuid,p_mode text,p_ip text,p_agent text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.despacho_salas; l public.despacho_sala_enlaces; room uuid; d jsonb;
begin
  select room_id into room from public.despacho_sala_enlaces where token_hash=p_hash;
  if room is null then return jsonb_build_object('error','LINK_UNAVAILABLE'); end if;
  select * into r from public.despacho_salas where id=room for update;
  select * into l from public.despacho_sala_enlaces where token_hash=p_hash and room_id=r.id for update;
  if not found or r.status<>'active' or r.expires_at<=clock_timestamp() or l.expires_at<=clock_timestamp() or l.revoked_at is not null
    then return jsonb_build_object('error','LINK_UNAVAILABLE'); end if;
  if p_mode not in ('open','view','download','upload','check') then return jsonb_build_object('error','INVALID_INPUT'); end if;
  if (p_mode='view' and not l.can_view) or (p_mode='download' and not l.can_download) or (p_mode='upload' and not l.can_upload)
    then return jsonb_build_object('error','FORBIDDEN'); end if;
  if p_mode in ('view','download') then
    select value into d from jsonb_array_elements(r.documents) where value->>'id'=p_document::text;
    if d is null then return jsonb_build_object('error','NOT_FOUND'); end if;
    if (select count(*) from public.despacho_sala_eventos where link_id=l.id and event in ('view_requested','download_requested') and at>clock_timestamp()-interval '1 hour')>=300
      then return jsonb_build_object('error','LIMIT'); end if;
    insert into public.despacho_sala_eventos(room_id,link_id,event,details) values(r.id,l.id,p_mode||'_requested',jsonb_build_object('document_id',p_document,'ip',left(p_ip,64),'agent',left(p_agent,512)));
  elsif p_mode='open' and l.opened_at is null then
    update public.despacho_sala_enlaces set opened_at=clock_timestamp() where id=l.id;
    insert into public.despacho_sala_eventos(room_id,link_id,event,details) values(r.id,l.id,'opened',jsonb_build_object('ip',left(p_ip,64),'agent',left(p_agent,512)));
  end if;
  return jsonb_build_object('id',r.id,'owner_id',r.owner_id,'title',r.title,'description',r.description,'expires_at',least(r.expires_at,l.expires_at),
    'documents',case when l.can_view then r.documents else '[]'::jsonb end,'document',d,
    'link',jsonb_build_object('id',l.id,'label',l.label,'can_view',l.can_view,'can_download',l.can_download,'can_upload',l.can_upload));
end $$;

create or replace function public.despacho_rooms_upload_reserve(p_hash text,p_id uuid,p_request uuid,p_filename text,p_mime text,p_bytes bigint,p_sha text,p_ip text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare access jsonb; u public.despacho_sala_aportes; room uuid; link uuid;
begin
  access:=public.despacho_rooms_public(p_hash,null,'upload',p_ip,'');
  if access ? 'error' then return access; end if;
  room:=(access->>'id')::uuid;link:=(access->'link'->>'id')::uuid;
  if p_id is null or p_request is null or p_filename is null or p_mime is null or p_bytes is null or p_sha is null
    or char_length(p_filename) not between 1 and 200 or p_filename ~ '[[:cntrl:]/\\]' or p_bytes not between 1 and 10485760 or p_sha !~ '^[a-f0-9]{64}$'
    or p_mime not in ('application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain')
    then return jsonb_build_object('error','INVALID_INPUT'); end if;
  select * into u from public.despacho_sala_aportes where link_id=link and request_id=p_request for update;
  if found then
    if u.sha256=p_sha and u.bytes=p_bytes and u.filename=p_filename then return to_jsonb(u)-'import_lease'-'import_until'; end if;
    return jsonb_build_object('error','INVALID_INPUT');
  end if;
  if (select count(*) from public.despacho_sala_aportes where link_id=link and created_at>clock_timestamp()-interval '24 hours')>=20
    or (select count(*) from public.despacho_sala_aportes where room_id=room and status not in ('failed','rejected'))>=100
    or (select coalesce(sum(bytes),0) from public.despacho_sala_aportes where room_id=room and status not in ('failed','rejected'))+p_bytes>104857600
    then return jsonb_build_object('error','LIMIT'); end if;
  insert into public.despacho_sala_aportes(id,room_id,link_id,request_id,filename,mime,bytes,sha256)
    values(p_id,room,link,p_request,p_filename,p_mime,p_bytes,p_sha) returning * into u;
  insert into public.despacho_sala_eventos(room_id,link_id,event,details) values(room,link,'upload_reserved',jsonb_build_object('upload_id',u.id,'filename',p_filename,'bytes',p_bytes,'ip',left(p_ip,64)));
  return to_jsonb(u)-'import_lease'-'import_until';
end $$;

create or replace function public.despacho_rooms_upload_finish(p_hash text,p_id uuid,p_success boolean)
returns jsonb language plpgsql security definer set search_path='' as $$
declare access jsonb; u public.despacho_sala_aportes;
begin
  access:=public.despacho_rooms_public(p_hash,null,'upload','','');
  if access ? 'error' then return access; end if;
  select * into u from public.despacho_sala_aportes where id=p_id and room_id=(access->>'id')::uuid and link_id=(access->'link'->>'id')::uuid for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  if u.status='received' and p_success then return to_jsonb(u)-'import_lease'-'import_until'-'request_id'; end if;
  if u.status<>'pending' then return jsonb_build_object('error','CONFLICT'); end if;
  update public.despacho_sala_aportes set status=case when p_success then 'received' else 'failed' end,received_at=case when p_success then clock_timestamp() else null end where id=u.id returning * into u;
  insert into public.despacho_sala_eventos(room_id,link_id,event,details) values(u.room_id,u.link_id,case when p_success then 'upload_received' else 'upload_failed' end,jsonb_build_object('upload_id',u.id,'sha256',u.sha256));
  return to_jsonb(u)-'import_lease'-'import_until'-'request_id';
end $$;

create or replace function public.despacho_rooms_upload_claim(p_room uuid,p_id uuid,p_lease uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.despacho_salas; u public.despacho_sala_aportes;
begin
  select * into r from public.despacho_salas where id=p_room and owner_id=auth.uid() for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  select * into u from public.despacho_sala_aportes where id=p_id and room_id=r.id for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  if u.status='imported' then return to_jsonb(u)-'import_lease'-'import_until'-'request_id'; end if;
  if p_lease is null then return jsonb_build_object('error','INVALID_INPUT'); end if;
  if u.status='importing' and u.import_until>clock_timestamp() then return jsonb_build_object('error','BUSY'); end if;
  if u.status not in ('received','importing') then return jsonb_build_object('error','CONFLICT'); end if;
  update public.despacho_sala_aportes set status='importing',import_lease=p_lease,import_until=clock_timestamp()+interval '2 minutes',item_id=coalesce(item_id,gen_random_uuid()) where id=u.id returning * into u;
  return to_jsonb(u)-'import_lease'-'import_until'-'request_id';
end $$;

create or replace function public.despacho_rooms_upload_imported(p_room uuid,p_id uuid,p_lease uuid,p_success boolean)
returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.despacho_salas; u public.despacho_sala_aportes;
begin
  select * into r from public.despacho_salas where id=p_room and owner_id=auth.uid() for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  select * into u from public.despacho_sala_aportes where id=p_id and room_id=r.id for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  if u.status='imported' and p_success then return to_jsonb(u)-'import_lease'-'import_until'-'request_id'; end if;
  if u.status<>'importing' or u.import_lease is distinct from p_lease then return jsonb_build_object('error','CONFLICT'); end if;
  if p_success and not exists(select 1 from public.despacho_items where id=u.item_id and owner_id=auth.uid() and kind='document' and data->>'room_upload_id'=u.id::text)
    then return jsonb_build_object('error','INVALID_INPUT'); end if;
  update public.despacho_sala_aportes set status=case when p_success then 'imported' else 'received' end,import_lease=null,import_until=null where id=u.id returning * into u;
  insert into public.despacho_sala_eventos(room_id,link_id,event,details) values(r.id,u.link_id,case when p_success then 'upload_imported' else 'import_unconfirmed' end,jsonb_build_object('upload_id',u.id,'item_id',u.item_id));
  return to_jsonb(u)-'import_lease'-'import_until'-'request_id';
end $$;

create or replace function public.despacho_rooms_upload_reject(p_room uuid,p_id uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.despacho_salas; u public.despacho_sala_aportes;
begin
  select * into r from public.despacho_salas where id=p_room and owner_id=auth.uid() for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  select * into u from public.despacho_sala_aportes where id=p_id and room_id=r.id for update;
  if not found then return jsonb_build_object('error','NOT_FOUND'); end if;
  if u.status='rejected' then return to_jsonb(u)-'import_lease'-'import_until'-'request_id'; end if;
  if u.status='imported' or (u.status='importing' and u.import_until>clock_timestamp()) then return jsonb_build_object('error','BUSY'); end if;
  if u.item_id is not null and exists(select 1 from public.despacho_items where id=u.item_id and owner_id=auth.uid()) then return jsonb_build_object('error','BUSY'); end if;
  update public.despacho_sala_aportes set status='rejected',import_lease=null,import_until=null where id=u.id returning * into u;
  insert into public.despacho_sala_eventos(room_id,link_id,event,details) values(r.id,u.link_id,'upload_rejected',jsonb_build_object('upload_id',u.id));
  return to_jsonb(u)-'import_lease'-'import_until'-'request_id';
end $$;

create or replace function public.despacho_rooms_export(p_owner uuid)
returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
  if p_owner is null or (coalesce(auth.role(),'')<>'service_role' and (auth.uid() is null or auth.uid()<>p_owner)) then return jsonb_build_object('error','NOT_FOUND'); end if;
  return coalesce((select jsonb_agg(public._despacho_room_json(r.id)||jsonb_build_object('audit',
    coalesce((select jsonb_agg(jsonb_build_object('event',v.event,'at',v.at,'link_id',v.link_id,'details',v.details) order by v.id)
      from public.despacho_sala_eventos v where v.room_id=r.id),'[]'::jsonb)) order by r.created_at)
    from public.despacho_salas r where r.owner_id=p_owner),'[]'::jsonb);
end $$;

revoke all on function public._despacho_room_json(uuid,boolean),public.despacho_rooms_list(uuid,integer,integer),public.despacho_rooms_create(uuid,text,text,jsonb,uuid,integer),
 public.despacho_rooms_link(uuid,uuid,text,text,boolean,boolean,boolean,integer),public.despacho_rooms_revoke(uuid,uuid),
 public.despacho_rooms_public(text,uuid,text,text,text),public.despacho_rooms_upload_reserve(text,uuid,uuid,text,text,bigint,text,text),
 public.despacho_rooms_upload_finish(text,uuid,boolean),public.despacho_rooms_upload_claim(uuid,uuid,uuid),
 public.despacho_rooms_upload_imported(uuid,uuid,uuid,boolean),public.despacho_rooms_upload_reject(uuid,uuid),public.despacho_rooms_export(uuid)
 from public,anon,authenticated;
grant execute on function public.despacho_rooms_list(uuid,integer,integer),public.despacho_rooms_create(uuid,text,text,jsonb,uuid,integer),
 public.despacho_rooms_link(uuid,uuid,text,text,boolean,boolean,boolean,integer),public.despacho_rooms_revoke(uuid,uuid),
 public.despacho_rooms_upload_claim(uuid,uuid,uuid),public.despacho_rooms_upload_imported(uuid,uuid,uuid,boolean),
 public.despacho_rooms_upload_reject(uuid,uuid),public.despacho_rooms_export(uuid) to authenticated;
grant execute on function public.despacho_rooms_public(text,uuid,text,text,text),public.despacho_rooms_upload_reserve(text,uuid,uuid,text,text,bigint,text,text),
 public.despacho_rooms_upload_finish(text,uuid,boolean),public.despacho_rooms_export(uuid) to service_role;
commit;
-- Durable call budgets for background work; never stores tokens or prompts.
BEGIN;
CREATE TABLE IF NOT EXISTS public.despacho_automation_user_usage (
    usage_day date NOT NULL,
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    calls integer NOT NULL CHECK(calls>=0),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(usage_day,owner_id)
);
CREATE TABLE IF NOT EXISTS public.despacho_automation_global_usage (
    usage_day date PRIMARY KEY,
    calls integer NOT NULL CHECK(calls>=0),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.despacho_automation_user_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_automation_global_usage ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.despacho_automation_user_usage,public.despacho_automation_global_usage FROM PUBLIC,anon,authenticated;
GRANT ALL ON public.despacho_automation_user_usage,public.despacho_automation_global_usage TO service_role;

CREATE OR REPLACE FUNCTION public.despacho_automation_reserve(p_owner uuid,p_user_limit integer,p_global_limit integer)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE today date=(now() AT TIME ZONE 'UTC')::date; reset_at timestamptz;
        personal integer=0; global_calls integer=0;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    IF p_owner IS NULL OR p_user_limit IS NULL OR p_global_limit IS NULL OR p_user_limit NOT BETWEEN 0 AND 1000000
       OR p_global_limit NOT BETWEEN 0 AND 1000000 THEN RAISE EXCEPTION 'invalid quota' USING ERRCODE='22023'; END IF;
    -- All workers serialize the global and personal reservation for one day.
    -- A denied reservation increments neither counter; rollback cannot charge
    -- only one of them. UTC is independent from the connection's timezone.
    PERFORM pg_advisory_xact_lock(hashtextextended('automation-daily:'||today::text,0));
    reset_at=((today+1)::timestamp AT TIME ZONE 'UTC');
    SELECT calls INTO personal FROM public.despacho_automation_user_usage WHERE usage_day=today AND owner_id=p_owner;
    SELECT calls INTO global_calls FROM public.despacho_automation_global_usage WHERE usage_day=today;
    personal=coalesce(personal,0);global_calls=coalesce(global_calls,0);
    IF personal>=p_user_limit THEN
        RETURN jsonb_build_object('allowed',false,'scope','user','used',personal,'limit',p_user_limit,'reset_at',reset_at);
    END IF;
    IF global_calls>=p_global_limit THEN
        RETURN jsonb_build_object('allowed',false,'scope','global','used',global_calls,'limit',p_global_limit,'reset_at',reset_at);
    END IF;
    INSERT INTO public.despacho_automation_user_usage(usage_day,owner_id,calls) VALUES(today,p_owner,1)
        ON CONFLICT(usage_day,owner_id) DO UPDATE SET calls=despacho_automation_user_usage.calls+1,updated_at=now();
    INSERT INTO public.despacho_automation_global_usage(usage_day,calls) VALUES(today,1)
        ON CONFLICT(usage_day) DO UPDATE SET calls=despacho_automation_global_usage.calls+1,updated_at=now();
    RETURN jsonb_build_object('allowed',true,'user_used',personal+1,'global_used',global_calls+1,
        'user_limit',p_user_limit,'global_limit',p_global_limit,'reset_at',reset_at,'unit','logical_call');
END;
$$;
REVOKE ALL ON FUNCTION public.despacho_automation_reserve(uuid,integer,integer) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_automation_reserve(uuid,integer,integer) TO service_role;
COMMIT;
