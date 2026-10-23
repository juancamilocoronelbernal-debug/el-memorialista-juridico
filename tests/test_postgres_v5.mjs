/** Real PostgreSQL/pgvector execution in PGlite. No Supabase network or accounts.
 * The auth/storage provider schemas below are fixtures; all application SQL is
 * loaded unchanged. This does not certify hosted Auth, Storage or PostgREST.
 */
import assert from 'node:assert/strict';
import {readFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const {PGlite}=await import(process.env.MEMORIALISTA_PGLITE_MODULE||'@electric-sql/pglite');
const {vector}=await import(process.env.MEMORIALISTA_VECTOR_MODULE||'@electric-sql/pglite-pgvector');
const {pgcrypto}=await import(process.env.MEMORIALISTA_PGCRYPTO_MODULE||'@electric-sql/pglite/contrib/pgcrypto');
const {uuid_ossp}=await import(process.env.MEMORIALISTA_UUID_MODULE||'@electric-sql/pglite/contrib/uuid_ossp');
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const db=new PGlite({extensions:{vector,pgcrypto,'uuid-ossp':uuid_ossp}});
let passed=0;
async function check(name,fn){await fn();passed++;console.log('PASS '+name);}
async function denied(query,params=[]){let failed=false;try{await db.query(query,params);}catch{failed=true;}assert.ok(failed,'Expected permission or invariant rejection');}
const owner='00000000-0000-4000-8000-000000000001';
const other='00000000-0000-4000-8000-000000000002';
const doc='00000000-0000-4000-8000-000000000011';
const secret='00000000-0000-4000-8000-000000000012';
async function asUser(uid){await db.exec('RESET ROLE');await db.query("SELECT set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claim.role','authenticated',false)",[uid]);await db.exec('SET ROLE authenticated');}
try{
await db.exec(`
 CREATE ROLE anon NOLOGIN;
 CREATE ROLE authenticated NOLOGIN;
 CREATE ROLE service_role NOLOGIN BYPASSRLS;
 CREATE SCHEMA auth;
 CREATE SCHEMA storage;
 CREATE TABLE auth.users(id uuid PRIMARY KEY,email text,raw_user_meta_data jsonb DEFAULT '{}'::jsonb,created_at timestamptz DEFAULT now(),email_confirmed_at timestamptz);
 CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
 CREATE FUNCTION auth.role() RETURNS text LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting('request.jwt.claim.role',true),'') $$;
 CREATE FUNCTION auth.jwt() RETURNS jsonb LANGUAGE sql STABLE AS $$ SELECT jsonb_build_object('sub',auth.uid(),'role',auth.role()) $$;
 GRANT USAGE ON SCHEMA auth,storage,public TO anon,authenticated,service_role;
 CREATE TABLE storage.buckets(id text PRIMARY KEY,name text,public boolean DEFAULT false,file_size_limit bigint,allowed_mime_types text[]);
 CREATE TABLE storage.objects(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),bucket_id text,name text,owner uuid,metadata jsonb DEFAULT '{}'::jsonb);
 ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;
 GRANT ALL ON storage.objects TO authenticated,service_role;
 CREATE FUNCTION storage.foldername(text) RETURNS text[] LANGUAGE sql IMMUTABLE AS $$ SELECT string_to_array($1,'/') $$;
`);
const directory=path.join(root,'supabase','migrations');
for(const name of (await readdir(directory)).filter(n=>n.endsWith('.sql')).sort()){
 try{await db.exec(await readFile(path.join(directory,name),'utf8'));console.log('MIGRATED '+name);}
 catch(error){console.error('MIGRATION FAILED '+name+' '+error.message);throw error;}
}
await check('All migrations can run twice',async()=>{
 for(const name of (await readdir(directory)).filter(n=>n.endsWith('.sql')).sort())await db.exec(await readFile(path.join(directory,name),'utf8'));
});
await db.query('INSERT INTO auth.users(id,email) VALUES($1,$2),($3,$4)',[owner,'owner@example.invalid',other,'other@example.invalid']);
await db.query("INSERT INTO public.despacho_items(id,owner_id,kind,title,data) VALUES($1,$2,'document','Contrato', $3),($4,$5,'document','Secreto ajeno',$6)",[
 doc,owner,JSON.stringify({text:'La cláusula de arbitraje obliga a las partes.',pages:[{page:1,text:'La cláusula de arbitraje obliga a las partes.'}],pagination:'pages'}),secret,other,JSON.stringify({text:'Secreto de otra cuenta'})]);
await asUser(owner);
await check('RLS hides other account documents',async()=>{const r=await db.query('SELECT id FROM public.despacho_items');assert.equal(r.rows.length,1);assert.equal(r.rows[0].id,doc);});
await check('Index RPC refuses foreign document',()=>denied('SELECT public.despacho_indexar_documento($1,1,$2)',[secret,JSON.stringify([{content:'Secreto',page:1}])]));
await check('Index RPC rejects stale version',()=>denied('SELECT public.despacho_indexar_documento($1,2,$2)',[doc,JSON.stringify([{content:'Arbitraje',page:1}])]));
const embedding=[1,...Array(767).fill(0)];
await check('Index and Spanish full-text search execute',async()=>{
 await db.query('SELECT public.despacho_indexar_documento($1,1,$2)',[doc,JSON.stringify([{content:'La cláusula de arbitraje obliga a las partes.',page:1,embedding,embedding_model:'test'}])]);
 const r=await db.query("SELECT * FROM public.despacho_buscar_conocimiento('arbitraje',null,null,'documents',null,'{}',20)");
 assert.equal(r.rows.length,1);assert.equal(r.rows[0].document_id,doc);assert.equal(r.rows[0].method,'text');
});
await check('Vector search executes under RLS',async()=>{
 const r=await db.query("SELECT * FROM public.despacho_buscar_conocimiento('conciliacion',$1::extensions.vector,'test','documents',null,'{}',20)",[JSON.stringify(embedding)]);
 assert.equal(r.rows.length,1);assert.equal(r.rows[0].method,'semantic');
});
await check('Selected-document filter cannot broaden search',async()=>{
 const r=await db.query("SELECT * FROM public.despacho_buscar_conocimiento('arbitraje',null,null,'documents',null,$1,20)",[JSON.stringify({document_ids:[secret]})]);
 assert.equal(r.rows.length,0);
});
await check('Internal search cannot impersonate another account from a user JWT',async()=>{
 const r=await db.query("SELECT * FROM public.despacho_buscar_conocimiento_interno($1,'arbitraje')",[other]);
 assert.equal(r.rows.length,0);
 const coverage=await db.query('SELECT public.despacho_cobertura_indice_interna($1) AS result',[other]);
 assert.equal(coverage.rows[0].result,null);
});
await check('Scheduled service search explicitly scopes one owner without a saved user JWT',async()=>{
 await db.exec('RESET ROLE');
 await db.query("SELECT set_config('request.jwt.claim.sub','',false),set_config('request.jwt.claim.role','service_role',false)");
 await db.exec('SET ROLE service_role');
 assert.equal((await db.query("SELECT * FROM public.despacho_buscar_conocimiento_interno($1,'arbitraje')",[owner])).rows.length,1);
 assert.equal((await db.query("SELECT * FROM public.despacho_buscar_conocimiento_interno($1,'arbitraje')",[other])).rows.length,0);
 await asUser(owner);
});
await check('Embedding model mismatch is excluded',async()=>{
 const r=await db.query("SELECT * FROM public.despacho_buscar_conocimiento('irrelevante',$1::extensions.vector,'different','documents',null,'{}',20)",[JSON.stringify(embedding)]);assert.equal(r.rows.length,0);
});
await check('Semantic coverage counts only the configured embedding model',async()=>{
 const old=await db.query("SELECT public.despacho_cobertura_indice('test') AS result");
 const current=await db.query("SELECT public.despacho_cobertura_indice('different') AS result");
 assert.equal(old.rows[0].result.semantic_documents,1);
 assert.equal(current.rows[0].result.semantic_documents,0);
 assert.equal(current.rows[0].result.indexed_documents,1);
 assert.equal(current.rows[0].result.embedding_model,'different');
 const foreign=await db.query('SELECT public.despacho_cobertura_indice_interna($1,$2) AS result',[other,'test']);
 assert.equal(foreign.rows[0].result,null);
});
await asUser(other);
await check('Other account cannot read indexed passages',async()=>{assert.equal((await db.query('SELECT * FROM public.despacho_indice')).rows.length,0);assert.equal((await db.query("SELECT * FROM public.despacho_buscar_conocimiento('arbitraje')")).rows.length,0);});
await asUser(owner);
await check('A changed document never returns stale indexed text',async()=>{
 await db.query("UPDATE public.despacho_items SET title='Nuevo título',version=version+1 WHERE id=$1",[doc]);
 assert.equal((await db.query("SELECT * FROM public.despacho_buscar_conocimiento('arbitraje')")).rows.length,0);
});
await check('Anonymous users cannot invoke search RPC',async()=>{await db.exec('RESET ROLE; SET ROLE anon');await denied("SELECT * FROM public.despacho_buscar_conocimiento('arbitraje')");});
const {testAgentV5}=await import('./test_postgres_agent_v5.mjs');
await testAgentV5(db,check);
const {testSigningV5}=await import('./test_postgres_signing_v5.mjs');
await testSigningV5(db,check);
const {testRoomsV5}=await import('./test_postgres_rooms_v5.mjs');
await testRoomsV5(db,check);
const {testQuotasV5}=await import('./test_postgres_quotas_v5.mjs');
await testQuotasV5(db,check);
console.log(JSON.stringify({passed,failed:0,engine:'PGlite PostgreSQL + pgvector',provider_schemas:'auth/storage fixtures; application migrations unchanged'}));
} catch(error){console.error(error.message);process.exitCode=1;} finally{await db.close();}
