import unittest
from datetime import timedelta
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
 def test_rumor_label_cannot_be_omitted(self):
  out=m.caption({'kind':'rumor','title':'Деталь','body':'Сообщают о детали, не подтверждено'})
  self.assertTrue(out.startswith('<b>⚠️ НЕ ПОДТВЕРЖДЕНО</b>'))
 def test_duplicate_event(self):
  d={'event_key':'one','title':'t','body':'b'};data={'history':[{'status':'sent','event_key':'one'}]};self.assertTrue(m.seen_draft(d,[],data))
 def test_new_event(self):
  self.assertFalse(m.seen_draft({'event_key':'new','title':'t','body':'b'},[],{'history':[]}))
if __name__=='__main__':unittest.main()
