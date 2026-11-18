// Optional independent free clock. No Telegram/OpenAI secrets, no publishing.
export function active(ms) {
  const hour = new Date(ms + 3 * 3600000).getUTCHours();
  return hour === 0 || hour >= 8;
}
export async function tick(env, ms, send = fetch) {
  if (!active(ms)) return {idle: 'quiet_hours_moscow_01_08'};
  if (!env.GITHUB_DISPATCH_TOKEN) throw Error('dispatch_secret_missing');
  const r = await send('https://api.github.com/repos/rogovvlad960-oss/gta6/actions/workflows/private-newsroom.yml/dispatches', {
    method: 'POST',
    headers: {'Authorization': `Bearer ${env.GITHUB_DISPATCH_TOKEN}`, 'Accept': 'application/vnd.github+json',
      'Content-Type': 'application/json', 'User-Agent': 'LesterPrivateClock', 'X-GitHub-Api-Version': '2022-11-28'},
    body: JSON.stringify({ref: 'main', inputs: {mode: 'cycle', cloudflare_tick: new Date(ms).toISOString()}}), signal: AbortSignal.timeout(15000)
  });
  if (r.status !== 204) throw Error(`dispatch_http_${r.status}`);
  return {dispatched: true, scheduled_at: new Date(ms).toISOString()};
}
export default {
  async fetch(request, env) { return Response.json({service: 'Lester private clock', quiet_moscow: '01:00-08:00', interval_minutes: 15, github_dispatch_configured: Boolean(env.GITHUB_DISPATCH_TOKEN)}); },
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(tick(env, controller.scheduledTime).then(x => console.log(JSON.stringify(x)))
      .catch(e => { console.error(/^[a-z_0-9]+$/.test(e.message) ? e.message : 'clock_failed'); throw Error('clock_failed'); }));
  }
};
