import unittest
from datetime import datetime,timedelta
from unittest.mock import patch
from . import engine as e
from . import publishing as p

class PublishingTests(unittest.TestCase):
 def at(self,h,m=0):return datetime(2026,11,27,h,m,tzinfo=e.MSK)
 def record(self,h,**extra):return {'at':self.at(h).isoformat(),'status':'sent','destination':'channel',**extra}
 def test_three_morning_posts_wait_for_sixteen(self):
  d={'history':[self.record(h)for h in [8,9,10]]};out=p.news_gate(d,self.at(11,30));self.assertEqual(out['next_window_moscow'],self.at(16).isoformat());self.assertIsNone(p.news_gate(d,self.at(16)))
 def test_private_review_posts_do_not_consume_channel_windows(self):
  d={'history':[self.record(0,destination='private')]}
  with patch.dict(e.CONFIG,{'delivery_target':'channel'}):self.assertEqual(p.today_records(d,self.at(9)),[]);self.assertIsNone(p.news_gate(d,self.at(9)))
 def test_no_news_before_nine(self):self.assertEqual(p.news_gate({'history':[]},self.at(8,59))['idle'],'publication_window_not_due')
 def test_missed_windows_are_not_caught_up_in_bursts(self):
  d={'history':[self.record(16,publication_slot=p.slot(self.at(16)))]};self.assertEqual(p.news_gate(d,self.at(16,59))['idle'],'publication_window_not_due');self.assertIsNone(p.news_gate(d,self.at(18)))
 def test_six_slots_allow_at_most_one_story_each(self):
  d={'history':[]}
  for h in [9,11,14,16,18,22]:
   self.assertIsNone(p.news_gate(d,self.at(h)));d['history'].append(self.record(h,publication_slot=p.slot(self.at(h))));self.assertIsNotNone(p.news_gate(d,self.at(h,45)))
 def test_poll_is_separate_from_six_news_but_one_per_day(self):
  d={'history':[self.record(h)for h in [9,11,14,16,18]]};self.assertTrue(p.poll_due(d,self.at(20)));d['history'].append(self.record(20,kind='poll'));self.assertFalse(p.poll_due(d,self.at(21)));self.assertEqual(len(p.today_records(d,self.at(21))),5)
 def test_poll_respects_interval_and_closes_at_twenty_two(self):
  d={'history':[self.record(20)]};self.assertFalse(p.poll_due(d,self.at(20,20)));self.assertFalse(p.poll_due({'history':[]},self.at(22)))
 def test_polls_are_preferences_not_invented_game_facts(self):
  for key,q,options in p.POLLS:self.assertTrue(q.endswith('?'));self.assertGreaterEqual(len(options),2);self.assertEqual(len(set(options)),len(options))

class MediaTests(unittest.TestCase):
 def test_video_only_posts_are_found(self):
  from . import monitor as m
  markup='<div class="tgme_widget_message" data-post="test/1"><time datetime="'+e.stamp()+'"></time><div class="tgme_widget_message_text">В GTA VI игрок показывает необычную машину и дорогу к ней.</div><video src="https://cdn4.telesco.pe/file/clip.mp4"></video></div>'
  posts=m.parse_feed(markup);self.assertEqual(posts[0]['videos'],['https://cdn4.telesco.pe/file/clip.mp4']);self.assertEqual(posts[0]['images'],[])
 def test_video_url_allowlist(self):
  from .video_posts import safe_video
  self.assertTrue(safe_video('https://cdn4.telesco.pe/file/x.mp4?token=a'))
  for url in ['http://cdn4.telesco.pe/x.mp4','https://cdn4.telesco.pe.evil/x.mp4','https://127.0.0.1/x.mp4','file:///tmp/x.mp4','https://user@cdn4.telesco.pe/x.mp4','https://cdn4.telesco.pe/x.html']:self.assertFalse(safe_video(url))
 def test_unknown_rights_are_queued_not_assumed(self):
  from types import SimpleNamespace
  from . import monitor as m
  from . import video_posts as v
  s=SimpleNamespace(data={'private_editor':{'history':[]}},save=lambda:None)
  post={'id':'test/1','url':'https://t.me/test/1','text':'Игровой фрагмент GTA VI','videos':['https://cdn4.telesco.pe/file/x.mp4']}
  with patch.object(e,'request',side_effect=AssertionError('No download without permission')):
   self.assertIsNone(v.choose(m,s,{'source_ids':['test/1']},[post]))
  self.assertEqual(s.data['private_editor']['video_review_queue']['test/1']['reason'],'reuse_permission_unknown')
 def test_guides_rank_above_generic_piracy_news(self):
  from .video_posts import priority_score
  self.assertGreater(priority_score({'text':'Где найти машину: маршрут на карте к северу от города','videos':[]}),priority_score({'text':'Новости: пираты взломали неофициальный порт','videos':[]}))
 def test_original_video_has_caption_entities_and_unchanged_bytes(self):
  import os,json
  from types import SimpleNamespace
  from . import monitor as m
  from . import video_posts as v
  from .bot_emoji import format_caption
  draft={'title':'Видео','body':'Как найти машину.\n\n> Маршрут.\n\n_Реплика._','event_key':'video-test','source_ids':[]};text,entities=format_caption(m.caption(draft))
  raw=b'ORIGINAL_VIDEO_BYTES';video={'bytes':raw,'sha256':'hash','source_url':'https://t.me/test/1','rights':{'status':'reviewed_permission'}}
  msg={'message_id':105,'chat':{'type':'channel','id':-10,'username':'lesterdossier'},'video':{'file_id':'video'},'caption':text,'caption_entities':entities};state=SimpleNamespace(data={'private_editor':{'history':[]}},save=lambda:None);calls=[]
  def request(url,payload,headers):calls.append((url,payload));return json.dumps({'ok':True,'result':msg}).encode()
  with patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':'test'}),patch.dict(e.CONFIG,{'delivery_target':'channel'}),patch.object(m,'seen_draft',return_value=False),patch.object(m,'check_destination',return_value=-10),patch.object(e,'request',side_effect=request):out=v.send(m,state,draft,[],video)
  self.assertTrue(out['media_unchanged']);self.assertIn(raw,calls[0][1]);self.assertTrue(calls[0][0].endswith('/sendVideo'));self.assertEqual(state.data['private_editor']['history'][0]['kind'],'video')
 def test_native_poll_is_sent_once_and_recorded_separately(self):
  from types import SimpleNamespace
  from . import monitor as m
  state=SimpleNamespace(data={'private_editor':{'history':[]}},save=lambda:None);now=datetime(2026,11,27,20,tzinfo=e.MSK)
  msg={'message_id':106,'chat':{'id':-10,'type':'channel','username':'lesterdossier'},'poll':{'id':'poll-1'}}
  with patch.dict(e.CONFIG,{'delivery_target':'channel'}),patch.object(m,'check_destination',return_value=-10),patch.object(m,'telegram',return_value={'ok':True,'result':msg})as send:
   out=p.send_poll(m,state,now)
  payload=send.call_args.args[1];self.assertTrue(payload['question'].endswith('@lesterdossier'));self.assertTrue(all('text'in o for o in payload['options']));self.assertEqual(out['kind'],'poll');self.assertFalse(p.poll_due(state.data['private_editor'],now))
 def test_real_mp4_inspection_checks_duration_and_frames(self):
  import subprocess,tempfile,shutil
  from pathlib import Path
  from .video_posts import inspect
  if not shutil.which('ffmpeg'):self.skipTest('ffmpeg unavailable')
  with tempfile.TemporaryDirectory()as d:
   path=Path(d)/'clip.mp4';subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=640x360:r=10:d=2','-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(path)],check=True,timeout=30,capture_output=True);info,frames=inspect(path.read_bytes())
  self.assertEqual(info['width'],640);self.assertEqual(len(frames),3);self.assertTrue(all(f.startswith(b'\xff\xd8')for f in frames))
