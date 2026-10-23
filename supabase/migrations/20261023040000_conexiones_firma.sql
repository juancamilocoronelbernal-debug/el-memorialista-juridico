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
