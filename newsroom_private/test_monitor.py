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
  records=[{'at':m.e.stamp(),'status':'sent'}for _ in range(3)];self.assertEqual(m.blocked({'history':records},m.e.now()),'daily_cap')
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
 def test_rumor_uncertainty_is_inline(self):
  out=m.caption({'kind':'rumor','title':'Деталь','body':'Сообщают о детали, не подтверждено'})
  self.assertNotIn('⚠️',out)
  self.assertNotIn('<b>НЕ ПОДТВЕРЖДЕНО',out)
  self.assertIn('не подтверждено',out)
  fallback=m.caption({'kind':'rumor','title':'Деталь','body':'Сообщают о детали'})
  self.assertIn('подтверждения пока нет',fallback)
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
 def test_duplicate_event(self):
  d={'event_key':'one','title':'t','body':'b'};data={'history':[{'status':'sent','event_key':'one'}]};self.assertTrue(m.seen_draft(d,[],data))
 def test_new_event(self):
  self.assertFalse(m.seen_draft({'event_key':'new','title':'t','body':'b'},[],{'history':[]}))
if __name__=='__main__':unittest.main()
