import {test} from 'node:test';
import assert from 'node:assert/strict';
import {active, tick} from './clock-worker.mjs';
test('night never dispatches or needs credentials', async () => {
  let called=false;
  const r=await tick({}, Date.parse('2026-11-18T02:00:00Z'), async()=>{called=true;});
  assert.equal(called,false);assert.equal(r.idle,'quiet_hours_moscow_01_08');
});
test('08:00 opens and 01:00 closes Moscow',()=>{
 assert.equal(active(Date.parse('2026-11-18T05:00:00Z')),true);
 assert.equal(active(Date.parse('2026-11-18T22:00:00Z')),false);
 assert.equal(active(Date.parse('2026-11-18T21:59:00Z')),true);
});
test('day dispatches only the private workflow; no channel API',async()=>{
 let request;
 await tick({GITHUB_DISPATCH_TOKEN:'test-placeholder'},Date.parse('2026-11-18T12:00:00Z'),async(url,opt)=>{request={url,opt};return{status:204};});
 assert.match(request.url,/private-newsroom.yml\/dispatches$/);
 assert.deepEqual(JSON.parse(request.opt.body),{ref:'main',inputs:{mode:'cycle'}});
});
