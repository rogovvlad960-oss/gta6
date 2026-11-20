import unittest,io
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
from . import monitor as m
from .image_branding import editorial_card

class DeliveryReliability(unittest.TestCase):
 def posts(self,n=7):return [{'id':f'test/{i}','url':f'https://t.me/test/{i}','text':f'В GTA VI обнаружили новую игровую деталь номер {i}','published_at':m.e.stamp(),'images':['https://cdn4.telesco.pe/file/frame.jpg'],'links':[]}for i in range(n)]
 def setup_state(self):
  now=m.e.now().astimezone(m.e.MSK).replace(hour=13);data={'history':[{'status':'sent','test':True,'at':(now-timedelta(hours=2)).isoformat()}],'examined':{},'deferred':{},'attempts':{},'errors':[],'policy':'rumors-v3-media-queue'};state=SimpleNamespace(data={'private_editor':data,'history':[],'spend':{},'errors':[]},load=lambda:None,save=lambda:None);return now,data,state
 def test_editorial_fallback_is_own_image_not_source_evidence(self):
  b,meta=editorial_card({'title':'📁 Файлы GTA VI могли оказаться в сети','body':'Пока это не подтверждено. В сети обсуждают архив с игровыми файлами.'});im=Image.open(io.BytesIO(b));self.assertEqual(im.size,(1600,1400));self.assertTrue(meta['not_gameplay']);self.assertEqual(meta['source'],'own_editorial_illustration');self.assertTrue(meta['recomposed'])
 def test_rejected_story_tries_next_batch_in_same_cycle(self):
  now,data,state=self.setup_state();posts=self.posts();draft={'title':'Деталь','body':'Обсуждают новую деталь','event_key':'detail','source_ids':['test/6']}
  with patch.object(m.e,'now',return_value=now),patch.object(m.e,'State',return_value=state),patch.object(m,'check_recipient',return_value=123),patch.object(m,'fetch_feed',side_effect=[posts,[],[],[]]),patch.object(m.e,'evidence',return_value={'url':'https://www.rockstargames.com/VI','text':'Actual evidence'}),patch.object(m.e,'generate',side_effect=[None,draft])as gen,patch.object(m,'choose_image',return_value=None),patch.object(m,'send_reserved',return_value={'delivered':True,'message_id':44})as send:
   out=m.run('cycle')
  self.assertTrue(out['delivered']);self.assertEqual(out['batches_tried'],2);self.assertEqual(gen.call_count,2);self.assertIsNone(send.call_args.args[3]);self.assertEqual(out['image_mode'],'own_editorial_illustration')
 def test_hour_cooldown_still_prevents_drafting_or_fallback(self):
  now,data,state=self.setup_state();data['history'].append({'status':'sent','at':(now-timedelta(minutes=40)).isoformat()})
  with patch.object(m.e,'now',return_value=now),patch.object(m.e,'State',return_value=state),patch.object(m,'check_recipient',return_value=123),patch.object(m,'fetch_feed',return_value=self.posts(1)),patch.object(m.e,'urgent_candidate',return_value=False),patch.object(m.e,'generate',side_effect=AssertionError('No generation during cooldown')):
   self.assertEqual(m.run('cycle')['idle'],'normal_cooldown')
 def test_all_rejected_texts_are_not_sent_as_illustration(self):
  now,data,state=self.setup_state()
  with patch.object(m.e,'now',return_value=now),patch.object(m.e,'State',return_value=state),patch.object(m,'check_recipient',return_value=123),patch.object(m,'fetch_feed',side_effect=[self.posts(12),[],[],[]]),patch.object(m.e,'evidence',return_value={'url':'https://www.rockstargames.com/VI','text':'Actual evidence'}),patch.object(m.e,'generate',return_value=None)as gen,patch.object(m,'send_reserved',side_effect=AssertionError('Never send unchecked text')):
   out=m.run('cycle')
  self.assertEqual(out['idle'],'no_supported_fresh_story');self.assertEqual(gen.call_count,2)
 def test_urgent_keyword_cannot_spend_budget_or_bypass_hour_gap(self):
  now,data,state=self.setup_state();data['history'].append({'status':'sent','at':(now-timedelta(minutes=2)).isoformat()})
  with patch.object(m.e,'now',return_value=now),patch.object(m.e,'State',return_value=state),patch.object(m,'check_recipient',return_value=123),patch.object(m,'fetch_feed',return_value=self.posts(1)),patch.object(m.e,'urgent_candidate',return_value=True),patch.object(m.e,'generate',side_effect=AssertionError('Urgent keyword must not trigger paid drafting during cooldown')):
   self.assertEqual(m.run('cycle')['idle'],'normal_cooldown')
if __name__=='__main__':unittest.main()
