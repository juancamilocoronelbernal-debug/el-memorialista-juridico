/** Durable UTC budget invariants; imported by test_postgres_v5.mjs. */
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';

export async function testQuotasV5(db,check){
  const owner='00000000-0000-4000-8000-000000000001';
  const other='00000000-0000-4000-8000-000000000002';
  async function role(name,uid=owner){
    assert.ok(['service_role','authenticated','anon'].includes(name));
    await db.exec('RESET ROLE');
    await db.query("SELECT set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claim.role',$2,false)",[uid,name]);
    await db.exec('SET ROLE '+name);
  }
  async function reserve(uid=owner,personal=2,global=3){
    return (await db.query('SELECT public.despacho_automation_reserve($1,$2,$3) AS value',[uid,personal,global])).rows[0].value;
  }
  async function count(){return Number((await db.query("SELECT coalesce(sum(calls),0) AS n FROM public.despacho_automation_global_usage WHERE usage_day=(now() AT TIME ZONE 'UTC')::date")).rows[0].n);}
  await role('authenticated');
  await check('Automation quotas are inaccessible to clients and cannot be self-reset',async()=>{
    await assert.rejects(()=>reserve());
    await assert.rejects(()=>db.query('SELECT * FROM public.despacho_automation_global_usage'));
    await assert.rejects(()=>db.query('DELETE FROM public.despacho_automation_user_usage'));
  });
  await role('service_role');
  await check('Automation quota rejects unknown owners and invalid limits without charging',async()=>{
    await assert.rejects(()=>reserve(randomUUID()));
    await assert.rejects(()=>reserve(owner,-1,3));
    assert.equal(await count(),0);
    assert.equal((await reserve(owner,0,3)).allowed,false);
    assert.equal(await count(),0);
  });
  await check('Automation UTC counters ignore yesterday and do not depend on connection timezone',async()=>{
    await db.query("INSERT INTO public.despacho_automation_global_usage(usage_day,calls) VALUES((now() AT TIME ZONE 'UTC')::date-1,999999)");
    await db.exec("SET TIME ZONE 'Etc/GMT+12'");
    const first=await reserve();
    assert.equal(first.allowed,true);assert.equal(first.user_used,1);assert.equal(first.global_used,1);
    assert.equal(new Date(first.reset_at).getUTCHours(),0);
    const days=(await db.query("SELECT usage_day=(now() AT TIME ZONE 'UTC')::date AS correct FROM public.despacho_automation_user_usage WHERE owner_id=$1",[owner])).rows;
    assert.ok(days.every(r=>r.correct));
    await db.exec('RESET TIME ZONE');
  });
  await check('Automation user budget is durable and denied attempts do not spend global quota',async()=>{
    const second=await reserve();assert.equal(second.allowed,true);assert.equal(second.user_used,2);
    const denied=await reserve();assert.equal(denied.allowed,false);assert.equal(denied.scope,'user');assert.equal(await count(),2);
    await role('service_role');
    assert.equal((await reserve()).allowed,false);
  });
  await check('Automation global limit combines accounts and blocks additional reservations',async()=>{
    const third=await reserve(other);assert.equal(third.allowed,true);assert.equal(third.user_used,1);assert.equal(third.global_used,3);
    const denied=await reserve(other);assert.equal(denied.allowed,false);assert.equal(denied.scope,'global');assert.equal(await count(),3);
    assert.equal((await db.query('SELECT calls FROM public.despacho_automation_user_usage WHERE owner_id=$1',[other])).rows[0].calls,1);
  });
  await check('Automation transactional rollback releases both counters together',async()=>{
    await db.exec('BEGIN');
    assert.equal((await reserve(owner,10,10)).allowed,true);
    await db.exec('ROLLBACK');
    assert.equal(await count(),3);
    assert.equal((await db.query('SELECT calls FROM public.despacho_automation_user_usage WHERE owner_id=$1',[owner])).rows[0].calls,2);
  });
  await check('Deleting an account cannot erase already consumed global automation budget',async()=>{
    const temporary=randomUUID();
    await db.exec('RESET ROLE');
    await db.query('INSERT INTO auth.users(id,email) VALUES($1,$2)',[temporary,'quota-fixture@example.invalid']);
    await role('service_role');
    assert.equal((await reserve(temporary,10,10)).allowed,true);
    await db.exec('RESET ROLE');
    await db.query('DELETE FROM auth.users WHERE id=$1',[temporary]);
    await role('service_role');
    assert.equal(await count(),4);
    assert.equal((await db.query('SELECT * FROM public.despacho_automation_user_usage WHERE owner_id=$1',[temporary])).rows.length,0);
  });
  await role('authenticated');
}
