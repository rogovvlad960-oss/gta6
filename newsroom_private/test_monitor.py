import unittest
from datetime import timedelta, datetime, timezone
from unittest.mock import patch
from . import monitor as m
class Tests(unittest.TestCase):
 def test_unsafe_images(self):
  for u in ['http://cdn4.telesco.pe/file/x','https://localhost/x','https://cdn4.telesco.pe.evil/x','https://x@cdn4.telesco.pe/x','https://127.0.0.1/x']:self.assertFalse(m.safe_image(u))
  self.assertTrue(m.safe_image('https://cdn4.telesco.pe/file/x.jpg'))
 def test_uncertain_blocks_new_posts(self):
  self.assertEqual(m.blocked({'history':[{'status':'uncertain'}]},m.e.now()),'delivery_requires_reconciliation')
 def test_daily_cap(self):
  records=[{'at':m.e.stamp(),'status':'sent'}for _ in range(6)];self.assertEqual(m.blocked({'history':records},m.e.now()),'daily_cap')
 def test_below_six_posts_is_allowed(self):
  records=[{'at':m.e.stamp(),'status':'sent'}for _ in range(5)]
  self.assertIsNone(m.blocked({'history':records},m.e.now()))
 def test_probe_not_counted(self):
  self.assertIsNone(m.blocked({'history':[{'at':m.e.stamp(),'status':'sent','test':True}for _ in range(3)]},m.e.now()))
 def test_private_only(self):
  with patch.object(m,'recipient',return_value=123),patch.object(m,'telegram',side_effect=[{'ok':True,'result':{'username':'GTA6NewsHustleBot'}},{'ok':True,'result':{'id':123,'type':'channel'}}]):
   with self.assertRaisesRegex(RuntimeError,'private_recipient_required'):m.check_recipient()
 def test_caption_limits_and_escaping(self):
  self.assertIn('&lt;',m.caption({'title':'<x>','body':'text'}))
  with self.assertRaisesRegex(RuntimeError,'caption_too_long'):m.caption({'title':'x','body':'x'*1025})
 def test_body_emphasis_safe(self):
  self.assertEqual(m.body_html('Кадр **под водой**'),'Кадр <b>под водой</b>')
  self.assertIn('<b>под водой</b>',m.caption({'title':'Кадр','body':'Вид **под водой**'}))
  self.assertEqual(m.body_html('<script>x</script>'),'&lt;script&gt;x&lt;/script&gt;')
  self.assertNotIn('<b>',m.body_html('**'+('x'*71)+'**'))
 def test_report_uses_natural_attribution_without_added_disclaimer(self):
  out=m.caption({'kind':'rumor','title':'Деталь','body':'По словам автора, найдена новая деталь'})
  self.assertNotIn('подтвержден',out);self.assertNotIn('подтверждения',out);self.assertIn('По словам автора',out)
  self.assertTrue(out.endswith('@lesterdossier'))
 def test_streamer_name_is_not_advertisement(self):
  self.assertIsNone(m.e.reject_reason({'text':'Бустер показал смешной момент в GTA VI','published_at':m.e.stamp()}))
  self.assertEqual(m.e.reject_reason({'text':'Буст канала про GTA VI','published_at':m.e.stamp()}),'advertisement_or_giveaway')
 def test_night_boundaries_moscow(self):
  for hour,minute,expected in [(0,59,False),(1,0,True),(7,59,True),(8,0,False),(23,45,False)]:
   t=datetime(2026,11,18,hour,minute,tzinfo=m.e.MSK)
   self.assertEqual(m.quiet_hours(t),expected)
 def test_night_never_opens_state_or_telegram(self):
  t=datetime(2026,11,18,3,0,tzinfo=m.e.MSK)
  with patch.object(m.e,'now',return_value=t),patch.object(m.e,'State',side_effect=AssertionError('State must not open')),patch.object(m,'check_recipient',side_effect=AssertionError('Telegram must not be called')):
   self.assertEqual(m.run('cycle')['idle'],'quiet_hours_moscow_01_08')
 def test_invalid_model_evidence_is_rejected_without_crashing(self):
  import json, os
  from types import SimpleNamespace
  state=SimpleNamespace(data={'history':[],'spend':{},'errors':[]},save=lambda:None)
  response={'choices':[{'message':{'content':json.dumps({'evidence_refs':['invented']})}}], 'usage':{'prompt_tokens':10,'completion_tokens':10}}
  with patch.dict(os.environ,{'NEWSROOM_AI_SPEND_APPROVED':'true','NEWSROOM_LLM_KEY':'test-only'}),patch.object(m.e,'request',return_value=json.dumps(response)):
   self.assertIsNone(m.e.generate([],[],state))
  self.assertEqual(state.data['errors'][-1]['code'],'unknown_evidence_reference')
  self.assertLess(sum(state.data['spend'].values()),.001)
 def test_duplicate_event(self):
  d={'event_key':'one','title':'t','body':'b'};data={'history':[{'status':'sent','event_key':'one'}]};self.assertTrue(m.seen_draft(d,[],data))
 def test_new_event(self):
  self.assertFalse(m.seen_draft({'event_key':'new','title':'t','body':'b'},[],{'history':[]}))
 def test_premium_caption_preserves_bold_utf16_and_literal_html(self):
  from .bot_emoji import format_caption,units,LOGO
  text,entities=format_caption(m.caption({'title':'🚔 КОПЫ','body':'Деталь **важная** <x>'}))
  self.assertEqual(text,'📰 КОПЫ\n\nДеталь важная <x>\n\n@lesterdossier')
  custom=next(e for e in entities if e['type']=='custom_emoji')
  self.assertEqual(custom,{'type':'custom_emoji','offset':0,'length':2,'custom_emoji_id':LOGO})
  body_bold=next(e for e in entities if e['type']=='bold'and e['offset']>0)
  self.assertEqual(body_bold['offset'],units('📰 КОПЫ\n\nДеталь '))
 def test_urgent_and_body_lightning_use_pack_entities(self):
  from .bot_emoji import format_caption,LIGHTNING
  text,entities=format_caption('<b>🚔 Заголовок</b>\n⚡️ Важная деталь',urgent=True)
  custom=[e for e in entities if e['type']=='custom_emoji']
  self.assertEqual(len(custom),2);self.assertTrue(all(e['custom_emoji_id']==LIGHTNING for e in custom))
 def test_stripped_premium_emoji_is_not_claimed_success(self):
  from .bot_emoji import format_caption,verify_returned
  text,entities=format_caption('<b>⚡️ Новость</b>')
  with self.assertRaisesRegex(RuntimeError,'premium_emoji_not_preserved'):verify_returned({'caption_entities':[]},entities)
  verify_returned({'caption_entities':entities},entities)
if __name__=='__main__':unittest.main()
