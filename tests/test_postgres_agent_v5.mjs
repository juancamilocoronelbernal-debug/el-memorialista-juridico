/** RPC/state/RLS integration, using the parent's real PostgreSQL PGlite harness.
 * A single connection validates transactional invariants and competing versions;
 * it does not claim to test multiple hosts/processes simultaneously.
 */
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';

export async function testAgentV5(db,check){
  const owner='00000000-0000-4000-8000-000000000001';
  const other='00000000-0000-4000-8000-000000000002';
  const hash='a'.repeat(64), hash2='b'.repeat(64);
  const plan=[{id:'step-1',tool:'analyze',title:'Analizar',instruction:'Analiza la cuestión.'},{id:'step-2',tool:'save_document',title:'Guardar borrador',instruction:''}];
  async function role(name,uid=owner){
    assert.ok(['service_role','authenticated','anon'].includes(name));
    await db.exec('RESET ROLE');
    await db.query("SELECT set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claim.role',$2,false)",[uid,name]);
    await db.exec('SET ROLE '+name);
  }
  async function rejected(sql,args=[]){await assert.rejects(()=>db.query(sql,args));}
  async function rpc(name,args){
    assert.ok(/^despacho_agent_[a-z_]+$/.test(name));
    const placeholders=args.map((_,i)=>'$'+(i+1)).join(',');
    return (await db.query(`SELECT public.${name}(${placeholders}) AS value`,args)).rows[0].value;
  }
  async function read(id){return (await db.query('SELECT * FROM public.despacho_agent_jobs WHERE id=$1',[id])).rows[0];}
  async function make(uid=owner,steps=plan){
    return (await db.query('INSERT INTO public.despacho_agent_jobs(owner_id,title,objective,plan,plan_hash) VALUES($1,$2,$3,$4,$5) RETURNING *',
      [uid,'Encargo SQL','Prueba de invariantes del agente',JSON.stringify(steps),hash])).rows[0];
  }
  const control=(j,action,data={})=>rpc('despacho_agent_control',[j.owner_id,j.id,j.version,action,JSON.stringify(data)]);
  const claim=(j,lease=randomUUID())=>rpc('despacho_agent_claim_step',[j.owner_id,j.id,j.version,lease]);
  const result=(step)=>JSON.stringify({step_id:step.id,tool:step.tool,title:step.title,result:{answer:'Resultado de prueba, revisar.'}});
  const finish=(j,error='')=>rpc('despacho_agent_finish_step',[j.owner_id,j.id,j.lease_token,j.cursor,result(j.plan[j.cursor]),error]);
  const manual=(j,value)=>rpc('despacho_agent_browser_manual',[j.owner_id,j.id,value]);
  await role('service_role');
  let job=await make(), foreign=await make(other);
  await check('Agent RLS hides foreign jobs and audit events',async()=>{
    await role('authenticated');
    assert.deepEqual((await db.query('SELECT id FROM public.despacho_agent_jobs ORDER BY id')).rows.map(r=>r.id),[job.id]);
    assert.ok((await db.query('SELECT * FROM public.despacho_agent_events')).rows.every(r=>r.owner_id===owner));
  });
  await check('Agent authenticated clients cannot mutate jobs or approve RPCs directly',async()=>{
    await rejected('UPDATE public.despacho_agent_jobs SET state=\'approved\' WHERE id=$1',[job.id]);
    await assert.rejects(()=>control(job,'approve'));
    await rejected('SELECT * FROM public.despacho_agent_browser_actions');
    await rejected('SELECT public.despacho_agent_enqueue_due()');
  });
  await role('service_role');
  await check('Agent draft cannot execute and owner scope rejects a foreign approval',async()=>{
    await assert.rejects(()=>claim(job));
    await assert.rejects(()=>rpc('despacho_agent_control',[other,job.id,job.version,'approve','{}']));
    assert.equal((await read(job.id)).state,'draft');
  });
  await check('Agent plan edit increments version and stale approval fails',async()=>{
    const previous=job;
    job=await control(job,'edit',{plan,plan_hash:hash2});
    assert.equal(job.version,2);assert.equal(job.plan_hash,hash2);
    await assert.rejects(()=>control(previous,'approve'));
    job=await control(job,'approve');
    assert.equal(job.approved_hash,hash2);assert.ok(job.approved_at);
    await assert.rejects(()=>control(job,'edit',{plan,plan_hash:hash}));
  });
  await check('Agent only one competing version can claim an unexpired step lease',async()=>{
    const before=job;
    job=await claim(job);
    assert.equal(job.state,'running');assert.ok(new Date(job.lease_until)>new Date());
    await assert.rejects(()=>claim(before));
    await assert.rejects(()=>claim(job));
    await assert.rejects(()=>control(job,'retry'));
  });
  await check('Agent rejects wrong lease and wrong step results',async()=>{
    await assert.rejects(()=>rpc('despacho_agent_finish_step',[owner,job.id,randomUUID(),job.cursor,result(plan[0]),'']));
    await assert.rejects(()=>rpc('despacho_agent_finish_step',[owner,job.id,job.lease_token,job.cursor,result(plan[1]),'']));
    assert.equal((await read(job.id)).cursor,0);
  });
  await check('Agent failure preserves cursor and explicit retry makes progress once',async()=>{
    job=await finish(job,'Proveedor no disponible');
    assert.equal(job.state,'failed');assert.equal(job.cursor,0);assert.equal(job.results.length,0);
    job=await control(job,'retry');
    job=await claim(job);
    const before=job;
    job=await finish(job);
    assert.equal(job.cursor,1);assert.equal(job.results.length,1);assert.equal(job.state,'approved');
    await assert.rejects(()=>finish(before));
  });
  await check('Agent expired lease can be recovered and old completion is fenced out',async()=>{
    let recovery=await control(await make(),'approve');
    const obsolete=await claim(recovery);
    await db.query("UPDATE public.despacho_agent_jobs SET lease_until=now()-interval '1 second' WHERE id=$1",[obsolete.id]);
    recovery=await control(await read(obsolete.id),'retry');
    recovery=await claim(recovery);
    await assert.rejects(()=>finish(obsolete));
    recovery=await finish(recovery);
    assert.equal(recovery.cursor,1);
  });
  await check('Agent cancellation wins over late step completion',async()=>{
    let cancellation=await control(await make(),'approve');
    const pending=await claim(cancellation);
    cancellation=await control(pending,'cancel');
    const late=await finish(pending);
    assert.equal(late.state,'cancelled');assert.equal(late.cursor,0);
    await assert.rejects(()=>claim(cancellation));
    await assert.rejects(()=>control(cancellation,'retry'));
  });
  let action;
  const session=randomUUID(), pageHash='page:1';
  async function propose(j=job){return rpc('despacho_agent_browser_propose',[owner,j.id,session,JSON.stringify({action:'click',ref:'c0',label:'Buscar',url:'https://www.ramajudicial.gov.co/'}),pageHash]);}
  const claimAction=(a,j=job,s=session,h=pageHash)=>rpc('despacho_agent_browser_claim',[owner,j.id,a.id,s,h,j.version]);
  await check('Manual browser takeover pauses agent claims and external proposals',async()=>{
    job=await manual(job,true);assert.equal(job.manual_control,true);assert.equal(job.state,'waiting_approval');
    await assert.rejects(()=>claim(job));
    await assert.rejects(()=>propose());
    job=await manual(job,false);assert.equal(job.manual_control,false);assert.equal(job.state,'approved');
    const event=(await db.query("SELECT detail FROM public.despacho_agent_events WHERE job_id=$1 AND event='manual_takeover_finished'",[job.id])).rows.at(-1);
    assert.equal(event.detail.result_verified,false);
  });
  await check('Browser approval binds the exact job version session and observed page',async()=>{
    action=await propose();job=await read(job.id);assert.equal(job.state,'waiting_approval');
    await assert.rejects(()=>claimAction(action,{...job,version:job.version-1}));
    await assert.rejects(()=>claimAction(action,job,randomUUID()));
    await assert.rejects(()=>claimAction(action,job,session,'changed-page'));
    assert.equal((await claimAction(action)).state,'executing');
  });
  await check('Browser approved action is single use and blocks manual takeover',async()=>{
    await assert.rejects(()=>claimAction(action));
    await assert.rejects(()=>propose());
    await assert.rejects(()=>manual(job,true));
    await assert.rejects(()=>rpc('despacho_agent_browser_reset',[owner,job.id]));
  });
  await check('Browser uncertain result is recorded without automatic replay',async()=>{
    job=await rpc('despacho_agent_browser_finish',[owner,job.id,action.id,'{}','El efecto no se pudo confirmar']);
    assert.equal(job.state,'approved');assert.match(job.last_error,/confirmar/);
    assert.equal((await db.query('SELECT state FROM public.despacho_agent_browser_actions WHERE id=$1',[action.id])).rows[0].state,'failed');
    await assert.rejects(()=>claimAction(action));
  });
  await check('Browser expired approval cannot run and closing restores the job',async()=>{
    action=await propose();job=await read(job.id);
    await db.query("UPDATE public.despacho_agent_browser_actions SET expires_at=now()-interval '1 second' WHERE id=$1",[action.id]);
    await assert.rejects(()=>claimAction(action));
    job=await rpc('despacho_agent_browser_reset',[owner,job.id]);assert.equal(job.state,'approved');
  });
  await check('Browser lost execution requires explicit recovery and never replays its action',async()=>{
    action=await propose();job=await read(job.id);
    await claimAction(action);
    await db.query("UPDATE public.despacho_agent_browser_actions SET expires_at=now()-interval '1 second' WHERE id=$1",[action.id]);
    job=await rpc('despacho_agent_browser_reset',[owner,job.id]);
    assert.equal(job.state,'approved');assert.match(job.last_error,/incierto/);
    const abandoned=(await db.query('SELECT state,result FROM public.despacho_agent_browser_actions WHERE id=$1',[action.id])).rows[0];
    assert.equal(abandoned.state,'failed');assert.equal(abandoned.result.result_verified,false);
    await assert.rejects(()=>claimAction(action));
    await assert.rejects(()=>rpc('despacho_agent_browser_finish',[owner,job.id,action.id,'{}','']));
  });
  await check('Agent final step completes plan with exactly one result per step',async()=>{
    job=await finish(await claim(job));assert.equal(job.state,'completed');assert.equal(job.cursor,2);assert.equal(job.results.length,2);
    await assert.rejects(()=>claim(job));
  });
  let schedule;
  await check('Schedule template must be owned approved and contain safe recurring tools',async()=>{
    const when=new Date(Date.now()+3600000).toISOString();
    await assert.rejects(()=>rpc('despacho_agent_schedule_create',[other,job.id,60,when,true]));
    await assert.rejects(()=>rpc('despacho_agent_schedule_create',[other,foreign.id,60,when,true]));
    const browserJob=await control(await make(owner,[{id:'step-1',tool:'browser_read',title:'Visitar',instruction:'',url:'https://www.ramajudicial.gov.co/'}]),'approve');
    await assert.rejects(()=>rpc('despacho_agent_schedule_create',[owner,browserJob.id,60,when,true]));
    schedule=await rpc('despacho_agent_schedule_create',[owner,job.id,60,when,true]);
  });
  await check('Schedule owner RLS and version protect edits',async()=>{
    await role('authenticated',other);
    assert.equal((await db.query('SELECT * FROM public.despacho_agent_schedules')).rows.length,0);
    await role('service_role');
    await assert.rejects(()=>rpc('despacho_agent_schedule_update',[other,schedule.id,schedule.version,'{"enabled":false}']));
    const previous=schedule;
    schedule=await rpc('despacho_agent_schedule_update',[owner,schedule.id,schedule.version,'{"enabled":true}']);
    await assert.rejects(()=>rpc('despacho_agent_schedule_update',[owner,schedule.id,previous.version,'{"enabled":false}']));
  });
  await check('Durable enqueue clones an approved plan once and prevents overlapping runs',async()=>{
    await db.query("UPDATE public.despacho_agent_schedules SET next_run_at=now()-interval '1 second' WHERE id=$1",[schedule.id]);
    assert.equal(await rpc('despacho_agent_enqueue_due',[]),1);
    assert.equal(await rpc('despacho_agent_enqueue_due',[]),0);
    const run=(await db.query('SELECT * FROM public.despacho_agent_jobs WHERE schedule_id=$1',[schedule.id])).rows[0];
    assert.equal(run.owner_id,owner);assert.equal(run.approved_hash,job.approved_hash);assert.deepEqual(run.plan,job.plan);assert.equal(run.cursor,0);
    await db.query("UPDATE public.despacho_agent_schedules SET next_run_at=now()-interval '1 second' WHERE id=$1",[schedule.id]);
    assert.equal(await rpc('despacho_agent_enqueue_due',[]),0);
    assert.equal((await db.query('SELECT id FROM public.despacho_agent_jobs WHERE schedule_id=$1',[schedule.id])).rows.length,1);
  });
  await role('authenticated');
}
