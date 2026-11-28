import test from 'node:test';
import assert from 'node:assert/strict';
import {timing,preparation,validate,dispatch} from './worker.mjs';
const ms=s=>Date.parse(s);
const payload={event_key:'test-event',caption:'Полноценный проверенный текст новости',image_base64:'AAAA',image_sha256:'a'.repeat(64),image_role:'author_illustration',expires_at:ms('2026-11-09T00:00:00Z'),verified:true,claims:[{quote:'fact'}]};
test('Moscow normal slots are exactly 09,15,21 with one minute recovery',()=>{
 for(const hour of ['06','12','18']){
  assert.equal(timing(ms(`2026-11-08T${hour}:00:00Z`)).normal,true);
  assert.equal(timing(ms(`2026-11-08T${hour}:01:59Z`)).normal,true);
  assert.equal(timing(ms(`2026-11-08T${hour}:02:00Z`)).normal,false);
 }
 assert.equal(timing(ms('2026-11-08T09:00:00Z')).normal,false);
 assert.equal(timing(ms('2026-11-08T23:00:00Z')).day,'2026-11-09');
});
test('prepare before publishing; ordinary check cannot become urgent accidentally',()=>{
 assert.equal(preparation(ms('2026-11-08T05:20:00Z')),'prepare');
 assert.equal(preparation(ms('2026-11-08T23:05:00Z')),'prepare-urgent');
 assert.equal(preparation(ms('2026-11-08T06:00:00Z')),null);
});
test('reject unverified, expired, changed category and unconfirmed urgency',()=>{
 const now=ms('2026-11-08T06:00:00Z');validate(payload,now);
 for(const patch of [{verified:false},{expires_at:now},{urgent:true},{image_role:'screenshot'},{image_sha256:'bad'}])assert.throws(()=>validate({...payload,...patch},now));
});
test('disabled means no database access or Telegram calls',async()=>{
 assert.deepEqual(await dispatch({PUBLISH_ENABLED:'false'}),{idle:'disabled'});
});
test('ambiguous prior delivery prevents any automatic resend',async()=>{
 const env={PUBLISH_ENABLED:'true',DB:{prepare(){return {first:async()=>({event_key:'old'})}}}};
 assert.deepEqual(await dispatch(env),{idle:'delivery_needs_reconciliation'});
});
test('empty normal slot and ordinary news outside slot never trigger Telegram',async()=>{
 const env={PUBLISH_ENABLED:'true',DB:{prepare(sql){return {bind(){return this},first:async()=>null,run:async()=>({meta:{changes:1}})}}}};
 assert.equal((await dispatch(env,ms('2026-11-08T06:00:00Z'))).idle,'slot_empty');
 assert.equal((await dispatch(env,ms('2026-11-08T07:00:00Z'))).idle,'no_urgent_ready');
});
test('dry preview cannot send or mutate the queue',async()=>{
 let writes=0;
 const env={DB:{prepare(sql){return {bind(){return this},first:async()=>sql.includes("IN ('pending'")?null:{event_key:'ready-story',urgent:0},run:async()=>{writes++}}}}};
 const result=await dispatch(env,ms('2026-11-08T06:00:00Z'),true);
 assert.equal(result.dry_run,true);assert.equal(writes,0);
});
async function fixture(ambiguous=false) {
 const data=Uint8Array.from([255,216,255,217]);
 const hash=Buffer.from(await crypto.subtle.digest('SHA-256',data)).toString('hex');
 const p={...payload,image_base64:Buffer.from(data).toString('base64'),image_sha256:hash};
 const writes=[],calls=[],row={event_key:p.event_key,payload:JSON.stringify(p),urgent:0};
 const env={PUBLISH_ENABLED:'true',CHANNEL:'@lesterdossier',BOT_USERNAME:'GTA6NewsHustleBot',TELEGRAM_BOT_TOKEN:'placeholder',DB:{prepare(sql){return {bind(...args){this.args=args;return this},first:async()=>sql.includes("IN ('pending'")?null:row,async run(){writes.push({sql,args:this.args});return {meta:{changes:1}}}}}}};
 const fetch=async(url,options)=>{
  const method=url.split('/').at(-1);calls.push(method);
  if(method==='sendPhoto'){
   if(ambiguous)throw Error('timeout');
   return Response.json({ok:true,result:{message_id:123}});
  }
  const result=method==='getMe'?{id:1,username:env.BOT_USERNAME}:method==='getChat'?{id:-100,type:'channel'}:{status:'administrator',can_post_messages:true};
  return Response.json({ok:true,result});
 };
 return {env,writes,calls,fetch};
}
test('successful card delivery reserves first and records real message ID',async(t)=>{
 const f=await fixture();t.mock.method(globalThis,'fetch',f.fetch);
 const r=await dispatch(f.env,ms('2026-11-08T06:00:00Z'));
 assert.equal(r.message_id,123);assert.equal(f.calls.filter(x=>x==='sendPhoto').length,1);
 assert.match(f.writes[0].sql,/status='pending'/);
 assert.ok(f.writes.some(x=>x.sql.startsWith("UPDATE queue SET status='sent'")&&x.args.includes(123)));
});
test('ambiguous Telegram send is recorded and never automatically retried',async(t)=>{
 const f=await fixture(true);t.mock.method(globalThis,'fetch',f.fetch);
 const r=await dispatch(f.env,ms('2026-11-08T06:00:00Z'));
 assert.equal(r.error,'delivery_uncertain');assert.equal(f.calls.filter(x=>x==='sendPhoto').length,1);
 assert.ok(f.writes.some(x=>x.sql.includes("status='uncertain'")));
 assert.equal(f.writes.some(x=>x.sql.startsWith("UPDATE queue SET status='sent'")),false);
});
