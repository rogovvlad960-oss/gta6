import unittest
from datetime import datetime,timedelta
from unittest.mock import patch
from . import engine as e
from . import publishing as p

class PublishingTests(unittest.TestCase):
 def at(self,h,m=0):return datetime(2026,11,27,h,m,tzinfo=e.MSK)
 def record(self,h,**extra):return {'at':self.at(h).isoformat(),'status':'sent',**extra}
 def test_three_morning_posts_wait_for_sixteen(self):
  d={'history':[self.record(h)for h in [8,9,10]]};out=p.news_gate(d,self.at(11,30));self.assertEqual(out['next_window_moscow'],self.at(16).isoformat());self.assertIsNone(p.news_gate(d,self.at(16)))
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
