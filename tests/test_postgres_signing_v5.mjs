/** OAuth/signing RPC invariants against the parent's real PostgreSQL fixture.
 * No provider requests, real accounts, messages or simulated database calls.
 * Row locks are exercised sequentially; this is not a multi-process race test.
 */
import assert from 'node:assert/strict';
import {createHash, randomUUID} from 'node:crypto';

export async function testSigningV5(db, check) {
  const owner=randomUUID(), other=randomUUID(), doc=randomUUID(), foreign=randomUUID();
  const hash=value=>createHash('sha256').update(value).digest('hex');
  const consent='He revisado el PDF y acepto firmar estos documentos mediante el código enviado a mi correo.';
  async function role(name, uid='') {
    assert.ok(['authenticated','anon','service_role'].includes(name));
    await db.exec('RESET ROLE');
    await db.query("SELECT set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claim.role',$2,false)",[uid,name]);
    await db.exec('SET ROLE '+name);
  }
  async function result(name,args=[]) {
    assert.match(name,/^despacho_[a-z_]+$/);
    const r=await db.query('SELECT public.'+name+'('+args.map((_,i)=>'$'+(i+1)).join(',')+') AS value',args);
    return r.rows[0].value;
  }
  async function denied(sql,args=[]) {
    await assert.rejects(()=>db.query(sql,args));
  }
  async function rootQuery(sql,args=[]) { await db.exec('RESET ROLE'); return db.query(sql,args); }
  function request(order='parallel', count=1, documentId=doc) {
    const id=randomUUID();
    const documents=[{id:documentId,title:'Contrato revisado',version:1,text:'Texto íntegro del contrato de prueba.',sha256:hash('document-pdf'),pages:1,first_page:1,last_page:1,representation:'pdf_original'}];
    const recipients=Array.from({length:count},(_,i)=>({id:randomUUID(),name:'Persona '+(i+1),email:'persona'+(i+1)+'@example.invalid',position:i+1}));
    const title='Solicitud de prueba', bundleHash=hash('bundle-'+id);
    const manifest={format:'el-memorialista-firma-v5',id,title,bundle_hash:bundleHash,documents:documents.map(({text,...rest})=>rest),recipients,signing_order:order};
    const canonical=JSON.stringify(manifest), manifestHash=hash(canonical);
    return {id,title,documents,recipients,manifestHash,bundleHash,args:[id,title,JSON.stringify(documents),JSON.stringify(recipients),order,7,owner+'/'+id+'/expediente.pdf',bundleHash,manifestHash,canonical]};
  }
  async function create(req) {
    await role('authenticated',owner);
    const created=await result('despacho_signing_create',req.args);
    assert.equal(created.id,req.id,JSON.stringify(created));
    return created;
  }
  async function link(req,index=0) {
    await role('authenticated',owner);
    const token=hash('link-'+req.id+'-'+index);
    assert.equal((await result('despacho_signing_link',[req.id,req.recipients[index].id,token])).recipient.id,req.recipients[index].id);
    return token;
  }
  async function accept(req,token,otp,name='Persona firmante') {
    return result('despacho_signing_accept',[token,otp,name,consent,req.manifestHash,'192.0.2.1','Controlled PostgreSQL fixture']);
  }
  await db.exec('RESET ROLE');
  await db.query('INSERT INTO auth.users(id,email) VALUES($1,$2),($3,$4)',[owner,'signing-owner@example.invalid',other,'signing-other@example.invalid']);
  await db.query("INSERT INTO public.despacho_items(id,owner_id,kind,title,data) VALUES($1,$2,'document','Contrato',$3),($4,$5,'document','Documento ajeno',$6)",[doc,owner,JSON.stringify({text:'Contrato de prueba.'}),foreign,other,JSON.stringify({text:'Texto de otra cuenta.'})]);

  await check('OAuth/signing secret tables and service RPCs reject client access',async()=>{
    await role('authenticated',owner);
    for(const table of ['despacho_conexiones','despacho_oauth_estados','despacho_firma_expedientes','despacho_firma_destinatarios','despacho_firma_eventos']) {
      await denied('SELECT * FROM public.'+table);
      await denied('DELETE FROM public.'+table);
    }
    await denied('SELECT public._despacho_signing_json($1,true)',[randomUUID()]);
    await denied('SELECT public.despacho_oauth_consume($1,$2,$3,$4)',[owner,'google_drive',hash('state'),hash('binding')]);
    await denied('SELECT public.despacho_signing_otp($1,$2,$3)',[hash('link'),hash('otp'),randomUUID()]);
    await denied('SELECT public.despacho_signing_view($1,$2,$3,true)',[hash('link'),'','']);
    await denied('SELECT public.despacho_signing_accept($1,$2,$3,$4,$5,$6,$7)',[hash('link'),hash('otp'),'Persona',consent,hash('manifest'),'','']);
    await role('anon');
    await denied('SELECT public.despacho_signing_list(null)');
    await denied('SELECT public.despacho_signing_export($1)',[owner]);
    await denied('SELECT public.despacho_connections_export($1)',[owner]);
  });

  await check('OAuth state is bound to owner, provider, browser and one use',async()=>{
    await role('service_role');
    const state=hash('state-'+owner), binding=hash('binding-'+owner), secret='encrypted-test-state-'+owner;
    assert.deepEqual(await result('despacho_oauth_begin',[owner,'google_drive',state,binding,secret]),{created:true});
    assert.equal((await result('despacho_oauth_consume',[other,'google_drive',state,binding])).error,'STATE_INVALID');
    assert.equal((await result('despacho_oauth_consume',[owner,'google_drive',state,hash('wrong-binding')])).error,'STATE_INVALID');
    assert.equal((await result('despacho_oauth_consume',[owner,'microsoft_onedrive',state,binding])).error,'STATE_INVALID');
    assert.equal((await result('despacho_oauth_consume',[owner,'google_drive',state,binding])).secret,secret);
    assert.equal((await result('despacho_oauth_consume',[owner,'google_drive',state,binding])).error,'STATE_INVALID');
    const row=(await db.query('SELECT secret,consumed_at FROM public.despacho_oauth_estados WHERE state_hash=$1',[state])).rows[0];
    assert.equal(row.secret,'consumed'); assert.ok(row.consumed_at);
    const expired=hash('expired-'+owner);
    await result('despacho_oauth_begin',[owner,'google_drive',expired,binding,secret]);
    await db.query("UPDATE public.despacho_oauth_estados SET expires_at=clock_timestamp()-interval '1 second' WHERE state_hash=$1",[expired]);
    assert.equal((await result('despacho_oauth_consume',[owner,'google_drive',expired,binding])).error,'STATE_INVALID');
  });

  await check('OAuth refresh lease rejects foreign/stale owners and disconnected records',async()=>{
    await role('service_role');
    const initial='encrypted-provider-credential-'.repeat(3);
    const saved=await result('despacho_oauth_save',[owner,'google_drive','test@example.invalid','[]',initial]);
    assert.ok(saved.id); assert.equal(saved.owner_id,owner); assert.ok(!('secret' in saved));
    const again=await result('despacho_oauth_save',[owner,'google_drive','test@example.invalid','[]',initial]);
    assert.equal(again.id,saved.id);
    await role('authenticated',owner);
    const safe=await result('despacho_connections_export',[owner]);
    assert.equal(safe[0].id,saved.id);assert.equal(safe[0].owner_id,owner);
    assert.ok(!JSON.stringify(safe).includes(initial));
    assert.ok(!JSON.stringify(safe).includes('refresh_lease'));assert.ok(!JSON.stringify(safe).includes('secret'));
    assert.equal((await result('despacho_connections_export',[other])).error,'NOT_FOUND');
    await role('service_role');
    const leaseA=randomUUID(),leaseB=randomUUID();
    assert.equal((await result('despacho_oauth_claim_refresh',[other,saved.id,leaseA])).error,'NOT_FOUND');
    assert.equal((await result('despacho_oauth_claim_refresh',[owner,saved.id,leaseA])).acquired,true);
    assert.equal((await result('despacho_oauth_claim_refresh',[owner,saved.id,leaseB])).acquired,false);
    assert.equal((await result('despacho_oauth_finish_refresh',[owner,saved.id,leaseB,initial])).saved,false);
    await db.query("UPDATE public.despacho_conexiones SET refresh_until=clock_timestamp()-interval '1 second' WHERE id=$1",[saved.id]);
    assert.equal((await result('despacho_oauth_claim_refresh',[owner,saved.id,leaseB])).acquired,true);
    assert.equal((await result('despacho_oauth_finish_refresh',[owner,saved.id,leaseA,initial])).saved,false);
    assert.equal((await result('despacho_oauth_finish_refresh',[owner,saved.id,leaseB,initial])).saved,true);
    assert.equal((await result('despacho_oauth_claim_refresh',[owner,saved.id,leaseA])).acquired,true);
    await db.query('DELETE FROM public.despacho_conexiones WHERE id=$1 AND owner_id=$2',[saved.id,owner]);
    assert.equal((await result('despacho_oauth_finish_refresh',[owner,saved.id,leaseA,initial])).saved,false);
    assert.equal((await db.query('SELECT id FROM public.despacho_conexiones WHERE id=$1',[saved.id])).rows.length,0);
  });

  await check('External import deduplication is enforced per account in PostgreSQL',async()=>{
    await role('authenticated',owner);
    const key=hash('external-import');
    await db.query("INSERT INTO public.despacho_items(id,owner_id,kind,title,data) VALUES($1,$2,'document','Importado',$3)",[randomUUID(),owner,JSON.stringify({text:'Copia externa',external_key:key})]);
    await denied("INSERT INTO public.despacho_items(id,owner_id,kind,title,data) VALUES($1,$2,'document','Duplicado',$3)",[randomUUID(),owner,JSON.stringify({text:'Duplicado',external_key:key})]);
    await role('authenticated',other);
    await db.query("INSERT INTO public.despacho_items(id,owner_id,kind,title,data) VALUES($1,$2,'document','Mi copia',$3)",[randomUUID(),other,JSON.stringify({text:'Copia aislada',external_key:key})]);
  });

  const sequential=request('sequential',2);
  await check('Frozen signing creation is idempotent and confined to owned documents',async()=>{
    const first=await create(sequential), again=await result('despacho_signing_create',sequential.args);
    assert.equal(first.id,again.id); assert.equal(again.audit.filter(e=>e.event==='created').length,1);
    const invalid=request('parallel',1,foreign);
    assert.equal((await result('despacho_signing_create',invalid.args)).error,'INVALID_INPUT');
    const wrongPath=request(); wrongPath.args[6]=other+'/'+wrongPath.id+'/expediente.pdf';
    assert.equal((await result('despacho_signing_create',wrongPath.args)).error,'INVALID_INPUT');
    const wrongHash=request(); wrongHash.args[8]=hash('tampered-manifest');
    assert.equal((await result('despacho_signing_create',wrongHash.args)).error,'INVALID_INPUT');
    await role('authenticated',other);
    assert.deepEqual(await result('despacho_signing_list',[sequential.id]),[]);
    assert.equal((await result('despacho_signing_export',[owner])).error,'NOT_FOUND');
    assert.equal((await result('despacho_signing_cancel',[sequential.id])).error,'NOT_FOUND');
    assert.equal((await result('despacho_signing_link',[sequential.id,sequential.recipients[0].id,hash('foreign-link')])).error,'NOT_FOUND');
  });

  const token1=await link(sequential,0), token2=await link(sequential,1);
  const otp1=hash('first-otp'),otp2=hash('second-otp');
  await check('Signing order, link rotation cooldown and first-open evidence are enforced',async()=>{
    await role('authenticated',owner);
    assert.equal((await result('despacho_signing_link',[sequential.id,sequential.recipients[0].id,hash('too-soon')])).error,'LINK_WAIT');
    await role('service_role');
    assert.equal((await result('despacho_signing_view',[token2,'192.0.2.2','Fixture',true])).can_sign,false);
    assert.equal((await result('despacho_signing_otp',[token2,otp2,randomUUID()])).error,'WAIT_TURN');
    assert.equal((await accept(sequential,token2,otp2)).error,'WAIT_TURN');
    assert.equal((await result('despacho_signing_view',[token1,'192.0.2.1','Fixture',true])).can_sign,true);
    await result('despacho_signing_view',[token1,'192.0.2.1','Fixture',true]);
    assert.equal(Number((await db.query("SELECT count(*) AS n FROM public.despacho_firma_eventos WHERE recipient_id=$1 AND event='opened'",[sequential.recipients[0].id])).rows[0].n),1);
  });

  await check('OTP must be delivered, match the document and succeed once per signer',async()=>{
    await role('service_role');
    const generation=randomUUID();
    assert.equal((await result('despacho_signing_otp',[token1,otp1,generation])).recipient_id,sequential.recipients[0].id);
    assert.equal((await result('despacho_signing_otp',[token1,otp1,randomUUID()])).error,'OTP_WAIT');
    assert.equal((await result('despacho_signing_otp_delivery',[sequential.recipients[0].id,randomUUID(),true])).recorded,false);
    assert.equal((await accept(sequential,token1,otp1)).error,'OTP_INVALID');
    assert.equal((await result('despacho_signing_otp_delivery',[sequential.recipients[0].id,generation,true])).recorded,true);
    assert.equal((await result('despacho_signing_accept',[token1,otp1,'Persona',consent,hash('wrong-document'),'',''])).error,'DOCUMENT_CHANGED');
    assert.equal((await accept(sequential,token1,hash('wrong-otp'))).error,'OTP_INVALID');
    const signed=await accept(sequential,token1,otp1,'Primera persona');
    assert.equal(signed.signed,true); assert.equal(signed.completed,false);
    const repeated=await accept(sequential,token1,otp1,'Cambio que no debe guardarse');
    assert.equal(repeated.idempotent,true); assert.equal(repeated.signed_at,signed.signed_at);
    const r=(await db.query('SELECT * FROM public.despacho_firma_destinatarios WHERE id=$1',[sequential.recipients[0].id])).rows[0];
    assert.equal(r.signed_name,'Primera persona'); assert.equal(r.otp_hash,null); assert.equal(r.otp_generation,null); assert.equal(r.otp_delivered,false);
    assert.equal(r.otp_failures,2);
    assert.equal(Number((await db.query("SELECT count(*) AS n FROM public.despacho_firma_eventos WHERE recipient_id=$1 AND event='signed'",[sequential.recipients[0].id])).rows[0].n),1);
  });

  await check('An envelope completes only after all recipients finish in order',async()=>{
    await role('service_role');
    assert.equal((await result('despacho_signing_view',[token2,'','',false])).can_sign,true);
    const generation=randomUUID();
    await result('despacho_signing_otp',[token2,otp2,generation]);
    await result('despacho_signing_otp_delivery',[sequential.recipients[1].id,generation,true]);
    const signed=await accept(sequential,token2,otp2,'Segunda persona');
    assert.equal(signed.completed,true);
    assert.equal((await accept(sequential,token2,otp2)).idempotent,true);
    await role('authenticated',owner);
    const record=(await result('despacho_signing_list',[sequential.id]))[0];
    assert.equal(record.status,'completed'); assert.ok(record.completed_at);
    assert.ok(record.recipients.every(r=>r.status==='signed'));
    assert.equal(record.audit.filter(e=>e.event==='completed').length,1);
    assert.equal((await result('despacho_signing_cancel',[sequential.id])).error,'NOT_PENDING');
  });

  const locked=request(); await create(locked); const lockedToken=await link(locked);
  const lockedOtp=hash('correct-lockout-code');
  await check('Failed OTP attempts persist and lock out even a subsequently correct code',async()=>{
    await role('service_role');
    const generation=randomUUID();
    await result('despacho_signing_otp',[lockedToken,lockedOtp,generation]);
    await result('despacho_signing_otp_delivery',[locked.recipients[0].id,generation,true]);
    for(let i=0;i<5;i++)assert.equal((await accept(locked,lockedToken,hash('wrong-'+i))).error,'OTP_INVALID');
    assert.equal((await accept(locked,lockedToken,lockedOtp)).error,'OTP_LIMIT');
    const r=(await db.query('SELECT otp_attempts,otp_failures,status FROM public.despacho_firma_destinatarios WHERE id=$1',[locked.recipients[0].id])).rows[0];
    assert.equal(r.otp_attempts,5);assert.equal(r.otp_failures,5);assert.equal(r.status,'pending');
  });

  await check('OTP expiry, delivery generations and daily rate limits remain durable',async()=>{
    await role('service_role');
    const rid=locked.recipients[0].id;
    await db.query("UPDATE public.despacho_firma_destinatarios SET otp_last_sent_at=clock_timestamp()-interval '61 seconds' WHERE id=$1",[rid]);
    const generation=randomUUID(), freshOtp=hash('fresh-code');
    await result('despacho_signing_otp',[lockedToken,freshOtp,generation]);
    assert.equal((await result('despacho_signing_otp_delivery',[rid,randomUUID(),false])).recorded,false);
    await result('despacho_signing_otp_delivery',[rid,generation,true]);
    await db.query("UPDATE public.despacho_firma_destinatarios SET otp_expires_at=clock_timestamp()-interval '1 second' WHERE id=$1",[rid]);
    assert.equal((await accept(locked,lockedToken,freshOtp)).error,'OTP_INVALID');
    await db.query("UPDATE public.despacho_firma_destinatarios SET otp_last_sent_at=clock_timestamp()-interval '61 seconds',otp_failures=20 WHERE id=$1",[rid]);
    assert.equal((await result('despacho_signing_otp',[lockedToken,freshOtp,randomUUID()])).error,'OTP_LIMIT');
    await db.query("UPDATE public.despacho_firma_destinatarios SET otp_window_at=clock_timestamp()-interval '25 hours' WHERE id=$1",[rid]);
    assert.equal((await result('despacho_signing_otp',[lockedToken,freshOtp,randomUUID()])).recipient_id,rid);
    const r=(await db.query('SELECT otp_requests,otp_attempts,otp_failures FROM public.despacho_firma_destinatarios WHERE id=$1',[rid])).rows[0];
    assert.deepEqual(r,{otp_requests:1,otp_attempts:0,otp_failures:0});
  });

  await check('Rotating and cancelling links invalidates old tokens and pending OTP delivery',async()=>{
    const rid=locked.recipients[0].id, freshToken=hash('rotated-link-'+locked.id);
    await rootQuery("UPDATE public.despacho_firma_destinatarios SET last_link_at=clock_timestamp()-interval '31 seconds' WHERE id=$1",[rid]);
    await role('authenticated',owner);
    await result('despacho_signing_link',[locked.id,rid,freshToken]);
    await role('service_role');
    assert.equal((await result('despacho_signing_view',[lockedToken,'','',false])).error,'LINK_UNAVAILABLE');
    assert.equal((await accept(locked,lockedToken,lockedOtp)).error,'LINK_UNAVAILABLE');
    assert.equal((await db.query('SELECT otp_hash FROM public.despacho_firma_destinatarios WHERE id=$1',[rid])).rows[0].otp_hash,null);
    await db.query("UPDATE public.despacho_firma_destinatarios SET otp_last_sent_at=clock_timestamp()-interval '61 seconds' WHERE id=$1",[rid]);
    const generation=randomUUID();
    await result('despacho_signing_otp',[freshToken,lockedOtp,generation]);
    await role('authenticated',owner);
    assert.equal((await result('despacho_signing_cancel',[locked.id])).status,'cancelled');
    await role('service_role');
    assert.equal((await result('despacho_signing_otp_delivery',[rid,generation,true])).recorded,false);
    assert.equal((await result('despacho_signing_view',[freshToken,'','',false])).error,'LINK_UNAVAILABLE');
    assert.equal((await accept(locked,freshToken,lockedOtp)).error,'LINK_UNAVAILABLE');
  });

  const expired=request(); await create(expired); const expiredToken=await link(expired);
  await check('Expired signing requests cannot open, obtain OTP or accept',async()=>{
    await rootQuery("UPDATE public.despacho_firma_expedientes SET expires_at=clock_timestamp()-interval '1 second' WHERE id=$1",[expired.id]);
    await role('service_role');
    assert.equal((await result('despacho_signing_view',[expiredToken,'','',false])).error,'LINK_UNAVAILABLE');
    assert.equal((await result('despacho_signing_otp',[expiredToken,hash('otp'),randomUUID()])).error,'LINK_UNAVAILABLE');
    assert.equal((await accept(expired,expiredToken,hash('otp'))).error,'LINK_UNAVAILABLE');
  });

  await check('Authenticated account export contains evidence but never signing secrets',async()=>{
    await role('authenticated',owner);
    const exported=await result('despacho_signing_export',[owner]);
    assert.equal(exported.length,3); assert.ok(exported.every(e=>e.owner_id===owner));
    assert.equal(exported.find(e=>e.id===sequential.id).documents[0].text,'Texto íntegro del contrato de prueba.');
    const serialized=JSON.stringify(exported);
    for(const forbidden of ['token_hash','otp_hash','otp_generation','otp_expires_at','refresh_token','access_token',token1,token2,lockedToken,expiredToken,otp1,otp2,lockedOtp])assert.ok(!serialized.includes(forbidden),forbidden+' leaked');
    assert.ok(serialized.includes('email_verified'));assert.ok(serialized.includes('Primera persona'));
    const listing=await result('despacho_signing_list',[null]);
    assert.ok(listing.every(e=>e.documents.every(d=>!('text' in d))));
    assert.equal((await result('despacho_signing_export',[other])).error,'NOT_FOUND');
  });

  await check('Deleting Auth cascades local OAuth credentials, pending states and signature records',async()=>{
    await role('service_role');
    await result('despacho_oauth_save',[owner,'microsoft_outlook','mail@example.invalid','[]','encrypted-credential-'.repeat(4)]);
    await rootQuery('DELETE FROM auth.users WHERE id=$1',[owner]);
    for(const table of ['despacho_conexiones','despacho_oauth_estados','despacho_firma_expedientes'])assert.equal(Number((await db.query('SELECT count(*) AS n FROM public.'+table+' WHERE owner_id=$1',[owner])).rows[0].n),0);
    assert.equal(Number((await db.query('SELECT count(*) AS n FROM public.despacho_firma_destinatarios WHERE envelope_id=$1',[sequential.id])).rows[0].n),0);
    assert.equal(Number((await db.query('SELECT count(*) AS n FROM public.despacho_firma_eventos WHERE envelope_id=$1',[sequential.id])).rows[0].n),0);
    assert.equal(Number((await db.query('SELECT count(*) AS n FROM public.despacho_items WHERE owner_id=$1',[other])).rows[0].n),2);
  });
  await db.exec('RESET ROLE');
  await db.query('DELETE FROM auth.users WHERE id=$1',[other]);
}
