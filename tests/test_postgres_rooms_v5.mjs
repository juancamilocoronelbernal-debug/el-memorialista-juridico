import assert from 'node:assert/strict';
import {createHash,randomUUID} from 'node:crypto';

/** Real PostgreSQL tests: no HTTP providers, storage objects or emails. */
export async function testRoomsV5(db,check){
  const owner=randomUUID(),other=randomUUID(),doc=randomUUID(),foreign=randomUUID();
  const hash=s=>createHash('sha256').update(s).digest('hex');
  async function role(name,uid=''){await db.exec('RESET ROLE');await db.query("SELECT set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claim.role',$2,false)",[uid,name]);await db.exec('SET ROLE '+name);}
  async function rpc(name,args=[]){return (await db.query('SELECT public.'+name+'('+args.map((_,i)=>'$'+(i+1)).join(',')+') AS value',args)).rows[0].value;}
  async function denied(sql,args=[]){await assert.rejects(()=>db.query(sql,args));}
  async function root(sql,args=[]){await db.exec('RESET ROLE');return db.query(sql,args);}
  const documents=[{id:doc,title:'Documento compartido',source_version:1,sha256:hash('document'),bytes:1200,pages:1,representation:'pdf_original'}];
  const room=randomUUID();
  const createArgs=[room,'Sala de prueba','Documentos para revisión',JSON.stringify(documents),null,30];
  const viewLink={id:randomUUID(),hash:hash('view-link-'+room)};
  const uploadLink={id:randomUUID(),hash:hash('upload-link-'+room)};
  const fullLink={id:randomUUID(),hash:hash('full-link-'+room)};
  await db.exec('RESET ROLE');
  await db.query('INSERT INTO auth.users(id,email) VALUES($1,$2),($3,$4)',[owner,'room-owner@example.invalid',other,'room-other@example.invalid']);
  await db.query("INSERT INTO public.despacho_items(id,owner_id,kind,title,data) VALUES($1,$2,'document','Propio',$3),($4,$5,'document','Ajeno',$3)",[doc,owner,JSON.stringify({text:'Contenido'}),foreign,other]);

  await check('Room secret tables, service RPCs and private bucket reject client access',async()=>{
    await role('authenticated',owner);
    for(const table of ['despacho_salas','despacho_sala_enlaces','despacho_sala_aportes','despacho_sala_eventos'])await denied('SELECT * FROM public.'+table);
    await denied('SELECT public._despacho_room_json($1,true)',[room]);
    await denied('SELECT public.despacho_rooms_public($1,null,$2,$3,$4)',[viewLink.hash,'open','','']);
    await denied('INSERT INTO storage.objects(bucket_id,name,owner) VALUES($1,$2,$3)',['despacho-salas-v5',owner+'/'+room+'/documents/'+doc+'.pdf',owner]);
    await role('anon');await denied('SELECT public.despacho_rooms_list(null)');await denied('SELECT public.despacho_rooms_export($1)',[owner]);
  });
  await check('Room creation binds owner and source version and is idempotent',async()=>{
    await role('authenticated',owner);
    const created=await rpc('despacho_rooms_create',createArgs);assert.equal(created.id,room,JSON.stringify(created));
    assert.equal((await rpc('despacho_rooms_create',createArgs)).audit.length,1);
    const foreignArgs=[randomUUID(),...createArgs.slice(1)];foreignArgs[3]=JSON.stringify([{...documents[0],id:foreign}]);
    assert.equal((await rpc('despacho_rooms_create',foreignArgs)).error,'INVALID_INPUT');
    const stale=[randomUUID(),...createArgs.slice(1)];stale[3]=JSON.stringify([{...documents[0],source_version:2}]);assert.equal((await rpc('despacho_rooms_create',stale)).error,'INVALID_INPUT');
    const duplicate=[randomUUID(),...createArgs.slice(1)];duplicate[3]=JSON.stringify([...documents,...documents]);assert.equal((await rpc('despacho_rooms_create',duplicate)).error,'INVALID_INPUT');
    await role('authenticated',other);assert.deepEqual(await rpc('despacho_rooms_list',[room]),[]);
    assert.equal((await rpc('despacho_rooms_revoke',[room,null])).error,'NOT_FOUND');
    assert.equal((await rpc('despacho_rooms_export',[owner])).error,'NOT_FOUND');
  });
  await check('Room link permissions and public metadata are distinct per recipient link',async()=>{
    await role('authenticated',owner);
    for(const [link,label,view,download,upload] of [[viewLink,'Revisor',true,false,false],[uploadLink,'Aportante',false,false,true],[fullLink,'Cliente',true,true,true]]){
      const created=await rpc('despacho_rooms_link',[room,link.id,label,link.hash,view,download,upload,7]);assert.equal(created.id,link.id);assert.ok(!('token_hash' in created));
    }
    assert.equal((await rpc('despacho_rooms_link',[room,randomUUID(),'Inválido',hash('invalid-link'),false,true,false,7])).error,'INVALID_INPUT');
    await role('service_role');
    const viewer=await rpc('despacho_rooms_public',[viewLink.hash,null,'open','192.0.2.1','Fixture']);assert.equal(viewer.documents.length,1);assert.equal(viewer.link.can_download,false);
    assert.equal((await rpc('despacho_rooms_public',[viewLink.hash,doc,'download','',''])).error,'FORBIDDEN');
    assert.equal((await rpc('despacho_rooms_public',[viewLink.hash,null,'upload','',''])).error,'FORBIDDEN');
    const uploader=await rpc('despacho_rooms_public',[uploadLink.hash,null,'open','','']);assert.deepEqual(uploader.documents,[]);assert.equal(uploader.link.can_upload,true);
    assert.equal((await rpc('despacho_rooms_public',[uploadLink.hash,doc,'view','',''])).error,'FORBIDDEN');
    assert.equal((await rpc('despacho_rooms_public',[fullLink.hash,foreign,'download','',''])).error,'NOT_FOUND');
    assert.equal((await rpc('despacho_rooms_public',[fullLink.hash,doc,'download','',''])).document.id,doc);
    await rpc('despacho_rooms_public',[viewLink.hash,null,'open','','']);
    assert.equal(Number((await db.query("SELECT count(*) AS n FROM public.despacho_sala_eventos WHERE link_id=$1 AND event='opened'",[viewLink.id])).rows[0].n),1);
  });
  const upload=randomUUID(),request=randomUUID(),uploadHash=hash('uploaded-file');
  const reserve=[uploadLink.hash,upload,request,'aporte.txt','text/plain',1234,uploadHash,'192.0.2.1'];
  await check('Room uploads reserve quota atomically and retries preserve one identity',async()=>{
    await role('service_role');
    const saved=await rpc('despacho_rooms_upload_reserve',reserve);assert.equal(saved.id,upload);assert.equal(saved.status,'pending');
    const replay=[...reserve];replay[1]=randomUUID();assert.equal((await rpc('despacho_rooms_upload_reserve',replay)).id,upload);
    replay[6]=hash('different');assert.equal((await rpc('despacho_rooms_upload_reserve',replay)).error,'INVALID_INPUT');
    assert.equal((await rpc('despacho_rooms_upload_finish',[fullLink.hash,upload,true])).error,'NOT_FOUND');
    const received=await rpc('despacho_rooms_upload_finish',[uploadLink.hash,upload,true]);assert.equal(received.status,'received');assert.ok(received.received_at);
    assert.equal((await rpc('despacho_rooms_upload_finish',[uploadLink.hash,upload,true])).status,'received');
    assert.equal(Number((await db.query("SELECT count(*) AS n FROM public.despacho_sala_eventos WHERE room_id=$1 AND event='upload_received'",[room])).rows[0].n),1);
  });
  const leaseA=randomUUID(),leaseB=randomUUID();let itemId;
  await check('Importing a client upload requires owner review and one recoverable lease',async()=>{
    await role('authenticated',other);assert.equal((await rpc('despacho_rooms_upload_claim',[room,upload,leaseA])).error,'NOT_FOUND');
    await role('authenticated',owner);
    const claimed=await rpc('despacho_rooms_upload_claim',[room,upload,leaseA]);assert.equal(claimed.status,'importing');itemId=claimed.item_id;
    assert.equal((await rpc('despacho_rooms_upload_claim',[room,upload,leaseB])).error,'BUSY');
    assert.equal((await rpc('despacho_rooms_upload_reject',[room,upload])).error,'BUSY');
    assert.equal((await rpc('despacho_rooms_upload_imported',[room,upload,leaseB,true])).error,'CONFLICT');
    assert.equal((await rpc('despacho_rooms_upload_imported',[room,upload,leaseA,true])).error,'INVALID_INPUT');
    await root("UPDATE public.despacho_sala_aportes SET import_until=clock_timestamp()-interval '1 second' WHERE id=$1",[upload]);
    await role('authenticated',owner);assert.equal((await rpc('despacho_rooms_upload_claim',[room,upload,leaseB])).item_id,itemId);
    assert.equal((await rpc('despacho_rooms_upload_imported',[room,upload,leaseA,false])).error,'CONFLICT');
    await db.query("INSERT INTO public.despacho_items(id,owner_id,kind,title,data) VALUES($1,$2,'document','Aporte recibido',$3)",[itemId,owner,JSON.stringify({text:'Contenido',room_upload_id:upload})]);
    const finished=await rpc('despacho_rooms_upload_imported',[room,upload,leaseB,true]);assert.equal(finished.status,'imported');assert.equal(finished.item_id,itemId);
    assert.equal((await rpc('despacho_rooms_upload_imported',[room,upload,leaseB,true])).status,'imported');
    assert.equal((await rpc('despacho_rooms_upload_reject',[room,upload])).error,'BUSY');
    const record=(await rpc('despacho_rooms_list',[room]))[0];assert.equal(record.audit.filter(e=>e.event==='upload_imported').length,1);assert.equal(record.documents.length,1);
  });
  await check('Room upload quota counts outstanding reservations before storage succeeds',async()=>{
    await role('service_role');
    for(let i=0;i<9;i++){
      const result=await rpc('despacho_rooms_upload_reserve',[fullLink.hash,randomUUID(),randomUUID(),'file-'+i+'.txt','text/plain',10485760,hash('large-'+i),'']);
      assert.equal(result.status,'pending',JSON.stringify(result));
    }
    const over=await rpc('despacho_rooms_upload_reserve',[fullLink.hash,randomUUID(),randomUUID(),'too-large.txt','text/plain',10485760,hash('limit'),'']);assert.equal(over.error,'LIMIT');
    const oversized=await rpc('despacho_rooms_upload_reserve',[fullLink.hash,randomUUID(),randomUUID(),'too-large.txt','text/plain',10485761,hash('oversized'),'']);assert.equal(oversized.error,'INVALID_INPUT');
  });
  await check('A rejected room upload cannot later finish or alter the shared documents',async()=>{
    await role('service_role');const pending=(await db.query("SELECT id FROM public.despacho_sala_aportes WHERE room_id=$1 AND status='pending' LIMIT 1",[room])).rows[0].id;
    await role('authenticated',owner);assert.equal((await rpc('despacho_rooms_upload_reject',[room,pending])).status,'rejected');
    await role('service_role');assert.equal((await rpc('despacho_rooms_upload_finish',[fullLink.hash,pending,true])).error,'CONFLICT');
    await role('authenticated',owner);assert.equal((await rpc('despacho_rooms_upload_claim',[room,pending,randomUUID()])).error,'CONFLICT');
    const saved=(await rpc('despacho_rooms_list',[room]))[0];assert.deepEqual(saved.documents,documents);
  });
  await check('Room links expire and revocation is checked on each download/upload',async()=>{
    await role('authenticated',owner);await rpc('despacho_rooms_revoke',[room,viewLink.id]);
    await role('service_role');assert.equal((await rpc('despacho_rooms_public',[viewLink.hash,doc,'view','',''])).error,'LINK_UNAVAILABLE');
    await db.query("UPDATE public.despacho_sala_enlaces SET expires_at=clock_timestamp()-interval '1 second' WHERE id=$1",[uploadLink.id]);
    assert.equal((await rpc('despacho_rooms_upload_reserve',[uploadLink.hash,randomUUID(),randomUUID(),'late.txt','text/plain',10,hash('late'),''])).error,'LINK_UNAVAILABLE');
    assert.equal((await rpc('despacho_rooms_public',[fullLink.hash,doc,'download','',''])).document.id,doc);
    await role('authenticated',owner);const revoked=await rpc('despacho_rooms_revoke',[room,null]);assert.equal(revoked.status,'revoked');
    assert.equal((await rpc('despacho_rooms_revoke',[room,null])).audit.filter(e=>e.event==='revoked').length,1);
    await role('service_role');assert.equal((await rpc('despacho_rooms_public',[fullLink.hash,doc,'download','',''])).error,'LINK_UNAVAILABLE');
    assert.equal((await rpc('despacho_rooms_upload_finish',[fullLink.hash,upload,true])).error,'LINK_UNAVAILABLE');
  });
  await check('Room export preserves evidence without access secrets or import leases',async()=>{
    await root("INSERT INTO public.despacho_sala_eventos(room_id,event) SELECT $1,'fixture_event' FROM generate_series(1,1001)",[room]);
    await role('authenticated',owner);const exported=await rpc('despacho_rooms_export',[owner]);assert.equal(exported.length,1);
    assert.equal(exported[0].uploads.find(u=>u.id===upload).status,'imported');assert.ok(exported[0].audit.length>0);
    assert.equal(exported[0].audit.length,exported[0].audit_count);assert.ok(exported[0].audit.length>1000);
    assert.equal((await rpc('despacho_rooms_list',[room]))[0].audit.length,1000);
    const raw=JSON.stringify(exported);for(const secret of ['token_hash','import_lease','import_until','request_id',viewLink.hash,uploadLink.hash,fullLink.hash,leaseA,leaseB])assert.ok(!raw.includes(secret),secret+' leaked');
    assert.equal((await rpc('despacho_rooms_list',[null,0,1])).length,1);assert.equal((await rpc('despacho_rooms_list',[null,1,1])).length,0);
    assert.equal((await rpc('despacho_rooms_list',[null,-1,1])).error,'INVALID_INPUT');
  });
  await check('Auth deletion cascades room metadata and preserves another account',async()=>{
    await root('DELETE FROM auth.users WHERE id=$1',[owner]);
    for(const table of ['despacho_sala_enlaces','despacho_sala_aportes','despacho_sala_eventos'])assert.equal(Number((await db.query('SELECT count(*) AS n FROM public.'+table+' WHERE room_id=$1',[room])).rows[0].n),0);
    assert.equal((await db.query('SELECT id FROM public.despacho_items WHERE id=$1',[foreign])).rows.length,1);
  });
  await db.exec('RESET ROLE');await db.query('DELETE FROM auth.users WHERE id=$1',[other]);
}
