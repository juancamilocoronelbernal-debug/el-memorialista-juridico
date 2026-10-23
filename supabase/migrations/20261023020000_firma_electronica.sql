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
