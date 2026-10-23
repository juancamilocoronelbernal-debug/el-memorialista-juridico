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
