import json,os,unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from . import monitor as m

class QueueRepairTests(unittest.TestCase):
 def post(self,text='Новый момент в GTA VI',ident='test/1'):
  return {'id':ident,'url':'https://t.me/'+ident,'text':text,'published_at':m.e.stamp(),'images':['https://cdn4.telesco.pe/file/frame.jpg'],'links':[]}
 def data(self):return {'history':[],'examined':{}}
 def test_video_duration_is_not_publication_date(self):
  html=f'''<div class="tgme_widget_message" data-post="test/1"><div class="tgme_widget_message_text">В GTA VI нашли интересную новую игровую сцену</div><time class="tgme_widget_message_video_duration">00:28</time><i class="tgme_widget_message_video_thumb" style="background-image:url('https://cdn4.telesco.pe/file/frame.jpg')"></i><time datetime="{m.e.stamp()}"></time></div>'''
  posts=m.parse_feed(html);self.assertEqual(len(posts),1);self.assertEqual(posts[0]['images'],['https://cdn4.telesco.pe/file/frame.jpg'])
 def test_unsafe_video_poster_is_never_accepted(self):
  html=f'''<div class="tgme_widget_message" data-post="test/1"><div class="tgme_widget_message_text">В GTA VI нашли интересную новую игровую сцену</div><video poster="http://localhost/private"></video><time datetime="{m.e.stamp()}"></time></div>'''
  self.assertEqual(m.parse_feed(html),[])
 def test_sent_selection_does_not_discard_other_candidates(self):
  data=self.data();posts=[self.post(),self.post('Другой сюжет в GTA VI','test/2')];m.mark_selected(data,{'source_ids':['test/1']},posts,'sent');self.assertEqual([p['id']for p in m.available_posts(posts,data,m.e.now())],['test/2'])
 def test_rejected_batch_can_retry_after_backoff(self):
  data=self.data();posts=[self.post()];now=m.e.now();m.defer_posts(data,posts,now,'temporary_editor_skip');self.assertEqual(m.available_posts(posts,data,now),[]);self.assertEqual(m.available_posts(posts,data,now+timedelta(minutes=61)),posts);self.assertEqual(data['examined'],{})
 def test_deferred_one_does_not_hide_other_candidates(self):
  data=self.data();posts=[self.post(),self.post('Другой сюжет в GTA VI','test/2')];now=m.e.now();m.defer_posts(data,posts[:1],now,'image_review_rejected');self.assertEqual(m.available_posts(posts,data,now),posts[1:])
 def test_sent_source_cannot_be_reintroduced_by_migration(self):
  data=self.data();p=self.post();data['history']=[{'status':'sent','source_hashes':[m.e.digest(p['text'])]}];self.assertEqual(m.available_posts([p],data,m.e.now()),[])
 def test_uncertainty_is_added_before_validation_and_private_history_used(self):
  p=self.post();d={'kind':'rumor','priority':'normal','title':'Новая находка','body':'В сети обсуждают необычный игровой момент. Подождём подробностей.','event_key':'new','source_ids':[p['id']],'evidence_refs':['e0_0']}
  responses=[{'choices':[{'message':{'content':json.dumps(d)}}],'usage':{'prompt_tokens':10,'completion_tokens':10}},{'choices':[{'message':{'content':json.dumps({'approved':True})}}],'usage':{'prompt_tokens':10,'completion_tokens':10}}];calls=[]
  def request(url,payload,headers):calls.append(payload);return json.dumps(responses[len(calls)-1])
  state=SimpleNamespace(data={'history':[{'event_key':'public-topic'}],'spend':{},'errors':[]},save=lambda:None)
  with patch.dict(os.environ,{'NEWSROOM_AI_SPEND_APPROVED':'true','NEWSROOM_LLM_KEY':'test'}),patch.object(m.e,'request',side_effect=request):out=m.e.generate([p],[],state,editor_history=[{'event_key':'private-topic'}])
  self.assertIsNotNone(out);self.assertIn('не подтверждено',out['body']);self.assertEqual(json.loads(calls[0]['messages'][1]['content'])['HISTORY'],['private-topic'])
 def test_irrelevant_first_image_does_not_drop_the_story(self):
  post=self.post();post['images'].append('https://cdn4.telesco.pe/file/matching.jpg');state=object()
  with patch.object(m,'vision_check',side_effect=[False,True])as review:
   self.assertEqual(m.choose_image(state,{'source_ids':[post['id']]},[post]),post['images'][1]);self.assertEqual(review.call_count,2)
 def test_image_review_stops_after_three_candidates(self):
  post=self.post();post['images']=['https://cdn4.telesco.pe/file/'+str(i)+'.jpg'for i in range(6)]
  with patch.object(m,'vision_check',return_value=False)as review:
   self.assertIsNone(m.choose_image(object(),{'source_ids':[post['id']]},[post]));self.assertEqual(review.call_count,3)
 def test_invalid_rumor_refs_are_bound_only_to_real_selected_sources(self):
  post=self.post();other=self.post('Другая история в GTA VI','test/2');catalog=m.e.evidence_catalog([post,other],[]);draft={'kind':'rumor','source_ids':[post['id']],'evidence_refs':['invented']};m.e.resolve_evidence(draft,catalog,[post,other]);self.assertEqual(draft['citations'],[post['url']]);self.assertTrue(all(c['url']==post['url']for c in draft['claims']))
 def test_invalid_source_cannot_be_repaired(self):
  post=self.post();draft={'kind':'rumor','source_ids':['invented/1'],'evidence_refs':['invented']}
  with self.assertRaises(ValueError):m.e.resolve_evidence(draft,m.e.evidence_catalog([post],[]),[post])
 def test_image_alternatives_cover_other_selected_sources(self):
  a=self.post();a['images']=['https://cdn4.telesco.pe/file/'+str(i)+'.jpg'for i in range(5)];b=self.post('Другой кадр GTA VI','test/2')
  with patch.object(m,'vision_check',side_effect=[False,True])as review:
   self.assertEqual(m.choose_image(object(),{'source_ids':[a['id'],b['id']]},[a,b]),b['images'][0]);self.assertEqual(review.call_count,2)
 def test_twelve_attempts_do_not_prevent_six_post_target_after_rejections(self):
  now=m.e.now().astimezone(m.e.MSK).replace(hour=12);day=now.date().isoformat();data={'history':[{'status':'sent','test':True,'at':(now-timedelta(hours=2)).isoformat()}],'examined':{},'deferred':{},'attempts':{day:12},'errors':[],'policy':'rumors-v3-media-queue'};state=SimpleNamespace(data={'private_editor':data,'history':[],'spend':{},'errors':[]},load=lambda:None,save=lambda:None)
  with patch.object(m.e,'now',return_value=now),patch.object(m.e,'State',return_value=state),patch.object(m,'check_recipient',return_value=123),patch.object(m,'fetch_feed',return_value=[self.post()]),patch.object(m.e,'evidence',return_value={'url':'https://www.rockstargames.com/VI','text':'Verified page content long enough','checked_at':now.isoformat()}),patch.object(m.e,'generate',return_value=None):
   result=m.run('cycle')
  self.assertNotEqual(result.get('idle'),'daily_model_attempt_cap');self.assertEqual(data['attempts'][day],13)
if __name__=='__main__':unittest.main()
