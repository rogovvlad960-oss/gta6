// UTC cron, Moscow UTC+3. Secrets: TELEGRAM_BOT_TOKEN, NEWSROOM_QUEUE_KEY.
// No API text generation or paid image calls here; only verified prepared cards.
export function timing(ms) {
  const d=new Date(ms+3*3600000), hour=d.getUTCHours(), minute=d.getUTCMinutes();
  const day=d.toISOString().slice(0,10);
  return {day, normal:[9,15,21].includes(hour)&&minute<2, slot:`${day}T${String(hour).padStart(2,'0')}:00+03:00`, dayStart:Date.parse(`${day}T00:00:00+03:00`)};
}
export function validate(p, now) {
  if(!p||typeof p.event_key!=='string'||!/^[a-zA-Z0-9_-]{5,200}$/.test(p.event_key))throw Error('invalid_event_key');
  if(typeof p.caption!=='string'||p.caption.length>1024||p.caption.length<30)throw Error('invalid_caption');
  if(typeof p.image_base64!=='string'||p.image_base64.length>1500000||!/^[A-Za-z0-9+/]+={0,2}$/.test(p.image_base64))throw Error('invalid_image');
  if(!Number.isFinite(p.expires_at)||p.expires_at<=now||p.expires_at>now+48*3600000)throw Error('invalid_expiry');
  if(p.verified!==true||p.image_role!=='author_illustration'||!Array.isArray(p.claims)||!p.claims.length)throw Error('unverified_payload');
  if(p.urgent===true&&p.urgent_verified!==true)throw Error('unverified_urgent');
  if(!/^[a-f0-9]{64}$/.test(p.image_sha256||''))throw Error('invalid_image_hash');
  return p;
}
const response=(x,status=200)=>Response.json(x,{status});
async function log(env,code,event=null,slot=null) {
  await env.DB.prepare('INSERT INTO events(at,code,event_key,slot) VALUES(?,?,?,?)').bind(Date.now(),code,event,slot).run();
  console.log(JSON.stringify({code,event_key:event,slot}));
}
async function telegram(env,method,body) {
  const r=await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`,{method:'POST',headers:body instanceof FormData?{}:{'Content-Type':'application/json'},body:body instanceof FormData?body:JSON.stringify(body),signal:AbortSignal.timeout(15000)});
  const x=await r.json();if(!r.ok||!x.ok)throw Error('telegram_rejected');return x.result;
}
async function checkBot(env) {
  const me=await telegram(env,'getMe',{});
  if(me.username?.toLowerCase()!==env.BOT_USERNAME.toLowerCase())throw Error('wrong_bot');
  const chat=await telegram(env,'getChat',{chat_id:env.CHANNEL});
  const member=await telegram(env,'getChatMember',{chat_id:chat.id,user_id:me.id});
  if(chat.type!=='channel'||!(member.status==='creator'||member.status==='administrator'&&member.can_post_messages===true))throw Error('bot_cannot_post');
  return {bot:me.username,channel:env.CHANNEL,can_post_messages:true};
}
async function image(p) {
  const bytes=Uint8Array.from(atob(p.image_base64),c=>c.charCodeAt(0));
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
  if(digest!==p.image_sha256)throw Error('image_hash_mismatch');
  return bytes;
}
export async function dispatch(env, now=Date.now(), dry=false) {
  if(env.PUBLISH_ENABLED!=='true'&&!dry)return {idle:'disabled'};
  const t=timing(now);
  const unresolved=await env.DB.prepare("SELECT event_key FROM queue WHERE status IN ('pending','uncertain') LIMIT 1").first();
  if(unresolved)return {idle:'delivery_needs_reconciliation'};
  const row=await env.DB.prepare("SELECT * FROM queue WHERE status='ready' AND expires_at>? AND (urgent=1 OR ?=1) ORDER BY urgent DESC,created_at ASC LIMIT 1").bind(now,t.normal?1:0).first();
  if(!row){if(t.normal&&!dry)await log(env,'slot_empty',null,t.slot);return {idle:t.normal?'slot_empty':'no_urgent_ready'};}
  const slot=row.urgent?`urgent:${row.event_key}`:t.slot;
  if(dry)return {dry_run:true,event_key:row.event_key,slot,normal_slot:t.normal};
  const p=validate(JSON.parse(row.payload),now),bytes=await image(p);
  await checkBot(env); // Read-only checks before durable send reservation.
  // Atomic SQL reservation enforces slot uniqueness, caps, cooldown and cross-tick exclusion.
  const cap=row.urgent?4:3,gap=row.urgent?15*60000:4*3600000;
  const claim=await env.DB.prepare(`UPDATE queue SET status='pending',claimed_at=?,slot=? WHERE event_key=? AND status='ready'
   AND NOT EXISTS(SELECT 1 FROM queue WHERE status IN ('pending','uncertain'))
   AND NOT EXISTS(SELECT 1 FROM queue WHERE slot=?)
   AND (SELECT COUNT(*) FROM queue WHERE sent_at>=? AND status='sent')<?
   AND NOT EXISTS(SELECT 1 FROM queue WHERE sent_at>? AND status='sent')`).bind(now,slot,row.event_key,slot,t.dayStart,cap,now-gap).run();
  if(!claim.meta.changes)return {idle:'reservation_denied'};
  let sent;
  try {
    const form=new FormData();form.set('chat_id',env.CHANNEL);form.set('caption',p.caption);form.set('parse_mode','HTML');form.set('photo',new Blob([bytes],{type:'image/jpeg'}),'news.jpg');
    sent=await telegram(env,'sendPhoto',form);
  } catch {
    await env.DB.prepare("UPDATE queue SET status='uncertain' WHERE event_key=?").bind(row.event_key).run();
    await log(env,'delivery_uncertain',row.event_key,slot);return {error:'delivery_uncertain'};
  }
  // If this write fails after Telegram accepts, 'pending' remains and blocks repeats.
  await env.DB.prepare("UPDATE queue SET status='sent',sent_at=?,message_id=?,payload='' WHERE event_key=? AND status='pending'").bind(Date.now(),sent.message_id,row.event_key).run();
  await log(env,'published',row.event_key,slot);return {published:true,message_id:sent.message_id,event_key:row.event_key};
}
export function preparation(ms) {
  const d=new Date(ms+3*3600000),h=d.getUTCHours(),m=d.getUTCMinutes();
  if([8,11,14,17,20].includes(h)&&m===20)return 'prepare';
  if(m%10===5)return 'prepare-urgent';
  return null;
}
async function prepareNews(env,ms) {
  const operation=preparation(ms);
  if(!operation||env.PUBLISH_ENABLED!=='true')return;
  if(!env.GITHUB_DISPATCH_TOKEN)throw Error('dispatch_secret_missing');
  const r=await fetch('https://api.github.com/repos/rogovvlad960-oss/gta6/actions/workflows/newsroom.yml/dispatches',{
    method:'POST',headers:{'Authorization':`Bearer ${env.GITHUB_DISPATCH_TOKEN}`,'Accept':'application/vnd.github+json','User-Agent':'LesterDossierScheduler','Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28'},
    body:JSON.stringify({ref:'main',inputs:{operation}}),signal:AbortSignal.timeout(10000)});
  if(r.status!==204)throw Error('prepare_dispatch_failed');
  await log(env,'prepare_dispatched');
}
async function authenticated(request,env) {
  if(!env.NEWSROOM_QUEUE_KEY||!request.headers.get('Authorization'))return false;
  const digest=async s=>new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)));
  const [a,b]=await Promise.all([digest(request.headers.get('Authorization')),digest(`Bearer ${env.NEWSROOM_QUEUE_KEY}`)]);
  return a.reduce((v,x,i)=>v|(x^b[i]),0)===0;
}
export default {
 async fetch(request,env) {
  if(!await authenticated(request,env))return response({error:'unauthorized'},401);
  const path=new URL(request.url).pathname;
  try {
   if(path==='/api/verify'&&request.method==='GET')return response({...await checkBot(env),enabled:env.PUBLISH_ENABLED==='true'});
   if(path==='/api/status'&&request.method==='GET')return response({enabled:env.PUBLISH_ENABLED==='true',counts:(await env.DB.prepare('SELECT status,COUNT(*) AS count FROM queue GROUP BY status').all()).results,events:(await env.DB.prepare('SELECT at,code,event_key,slot FROM events ORDER BY id DESC LIMIT 30').all()).results});
   if(path==='/api/preview'&&request.method==='GET')return response(await dispatch(env,Date.now(),true));
   if(path==='/api/queue'&&request.method==='POST') {
    if(Number(request.headers.get('Content-Length')||0)>1700000)return response({error:'too_large'},413);
    const raw=await request.text();if(raw.length>1700000)return response({error:'too_large'},413);
    const p=validate(JSON.parse(raw),Date.now());await image(p);
    const old=await env.DB.prepare('SELECT event_key,status FROM queue WHERE event_key=?').bind(p.event_key).first();
    if(old)return response({queued:true,event_key:old.event_key,status:old.status});
    const count=await env.DB.prepare("SELECT COUNT(*) AS count FROM queue WHERE status='ready' AND expires_at>?").bind(Date.now()).first();if(count.count>=12)throw Error('queue_full');
    await env.DB.prepare('INSERT OR IGNORE INTO queue(event_key,payload,urgent,created_at,expires_at) VALUES(?,?,?,?,?)').bind(p.event_key,JSON.stringify(p),p.urgent===true?1:0,Date.now(),p.expires_at).run();
    await log(env,'queued',p.event_key);return response({queued:true,event_key:p.event_key});
   }
   return response({error:'not_found'},404);
  }catch(e){const code=/^[a-z_]+$/.test(e.message)?e.message:'request_failed';await log(env,code);return response({error:code},400);}
 },
 async scheduled(controller,env,ctx) {
  const ms=controller.scheduledTime;
  if(new Date(ms+3*3600000).getUTCHours()===3&&new Date(ms).getUTCMinutes()===0)ctx.waitUntil(env.DB.prepare("UPDATE queue SET status='expired',payload='' WHERE status='ready' AND expires_at<?").bind(ms).run());
  ctx.waitUntil(Promise.all([dispatch(env,ms).catch(()=>log(env,'dispatch_failed')),prepareNews(env,ms).catch(()=>log(env,'prepare_dispatch_failed'))]));
 }
};
