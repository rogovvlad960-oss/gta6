import copy
import contextlib
import io
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from newsroom import editor as e

AT = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc) # 15:00 Moscow
P = {'id': 'leonidagov/2612', 'text': 'GTA 6: неподтверждённый ранний доступ блогера', 'url': 'https://t.me/leonidagov/2612', 'published_at': AT.isoformat(), 'links': []}
PROOF = {'url': e.PRIMARY_FALLBACK, 'text': 'Coming November 19, 2026. Pre-Load Begins November 10.'}
D = {'kind': 'fact', 'title': 'Дата в досье', 'body': 'Дата выхода — 19 ноября.', 'event_key': 'release-date-2026-11-19', 'source_ids': [P['id']], 'citations': [e.PRIMARY_FALLBACK], 'claims': [{'url': e.PRIMARY_FALLBACK, 'quote': 'Coming November 19, 2026'}]}

class FakeBot:
    def __init__(self, fail=False): self.calls = 0; self.fail = fail
    def check(self): return {'can_post_messages': True}
    def send(self, draft):
        self.calls += 1
        if self.fail: raise TimeoutError('must not appear in logs')
        return {'message_id': 42}

class Tests(unittest.TestCase):
    def setUp(self):
        self.stdout_capture = contextlib.redirect_stdout(io.StringIO()); self.stdout_capture.__enter__()
        self.tmp = tempfile.TemporaryDirectory()
        self.state = e.State(Path(self.tmp.name) / 'state.json'); self.state.init()
    def tearDown(self):
        self.tmp.cleanup(); self.stdout_capture.__exit__(None,None,None)
    def test_public_widget_dates_text_links_and_breaks(self):
        page = '<div><div class="tgme_widget_message" data-post="x/12"><div class="tgme_widget_message_text js-message_text">GTA 6<br>Текст &amp; <b>факт</b><a href="https://www.rockstargames.com/VI">источник</a></div><time datetime="2026-11-05T06:05:05+00:00">date</time></div></div>'
        p = e.parse_feed(page)[0]
        self.assertIn('GTA 6\nТекст & факт', p['text']); self.assertIn('09:05:05+03:00', p['published_moscow']); self.assertEqual(p['links'], [e.PRIMARY_FALLBACK])
    def test_reply_quote_not_mixed_into_own_post(self):
        page='<div data-post="x/1"><div class="tgme_widget_message_text js-message_reply_text">Старая цитата GTA 6</div><div class="tgme_widget_message_text js-message_text">Новый собственный текст GTA 6</div><time datetime="2026-11-05T06:00:00+00:00"></time></div>'
        self.assertEqual(e.parse_feed(page)[0]['text'],'Новый собственный текст GTA 6')
    def test_pagination_fetches_past_album_page(self):
        def fixture(id,date):
            return f'<div data-post="x/{id}"><div class="tgme_widget_message_text js-message_text">Текст GTA 6 {id}</div><time datetime="{date}"></time></div>'.encode()
        with patch.object(e,'request',side_effect=[fixture(100,AT.isoformat()),fixture(80,(AT-timedelta(days=3)).isoformat())]) as r:
            posts=e.fetch_source('x',cutoff=AT-timedelta(days=2))
            self.assertEqual(len(posts),2);self.assertIn('?before=100',r.call_args_list[1].args[0])
    def test_new_channel_ends_at_first_message(self):
        page=f'<div data-post="x/1"><div class="tgme_widget_message_text js-message_text">Channel created</div><time datetime="{AT.isoformat()}"></time></div>'.encode()
        with patch.object(e,'request',return_value=page) as r:
            self.assertEqual(len(e.fetch_source('x',cutoff=AT-timedelta(days=7),max_pages=1)),1)
            self.assertEqual(r.call_count,1)
    def test_pagination_limit_is_visible_failure(self):
        page=f'<div data-post="x/100"><div class="tgme_widget_message_text js-message_text">Текст GTA 6</div><time datetime="{AT.isoformat()}"></time></div>'.encode()
        with patch.object(e,'request',return_value=page):
            with self.assertRaisesRegex(RuntimeError,'page_limit'):e.fetch_source('x',cutoff=AT-timedelta(days=2),max_pages=1)
    def test_factcheck_rejection_prevents_candidate(self):
        responses=[{'choices':[{'message':{'content':json.dumps(D)}}]}, {'choices':[{'message':{'content':'{"approved":false,"reason":"unsupported"}'}}]}]
        with patch.dict(e.CONFIG,{'monthly_budget_usd':2}),patch.dict(e.os.environ,{'NEWSROOM_AI_SPEND_APPROVED':'true','NEWSROOM_LLM_KEY':'test-placeholder'}),patch.object(e,'request',side_effect=[json.dumps(r).encode() for r in responses]) as call:
            self.assertIsNone(e.generate([P],[PROOF],self.state));self.assertEqual(call.call_count,2)
        self.state.load();self.assertEqual(self.state.data['errors'][-1]['code'],'editorial_factcheck_rejected');self.assertGreater(sum(self.state.data['spend'].values()),0)
    def test_factcheck_accepts_supported_candidate(self):
        responses=[{'choices':[{'message':{'content':json.dumps(D)}}]}, {'choices':[{'message':{'content':'{"approved":true}'}}]}]
        with patch.dict(e.CONFIG,{'monthly_budget_usd':2}),patch.dict(e.os.environ,{'NEWSROOM_AI_SPEND_APPROVED':'true','NEWSROOM_LLM_KEY':'test-placeholder'}),patch.object(e,'request',side_effect=[json.dumps(r).encode() for r in responses]):
            self.assertEqual(e.generate([P],[PROOF],self.state),D)
    def test_monthly_reservation_refuses_over_budget(self):
        with patch.dict(e.CONFIG,{'monthly_budget_usd':0.000001}),patch.dict(e.os.environ,{'NEWSROOM_AI_SPEND_APPROVED':'true','NEWSROOM_LLM_KEY':'test-placeholder'}),patch.object(e,'request') as r:
            with self.assertRaisesRegex(RuntimeError,'monthly_ai_budget_reached'):e.generate([P],[PROOF],self.state)
            r.assert_not_called()
    def test_image_changed_no_send(self):
        d={**D,'image':{'file':'samples/01-fact/image.jpg','sha256':'wrong'}}
        with patch.dict(e.os.environ,{'TELEGRAM_BOT_TOKEN':'test-placeholder'}),patch.object(e,'request') as r:
            with self.assertRaisesRegex(RuntimeError,'approved_image_changed'):e.Bot().send(d)
            r.assert_not_called()
    def test_sample_images_and_claims_match(self):
        for p in (e.ROOT/'samples').glob('0*/draft.json'):
            d=json.loads(p.read_text());e.validate_draft(d,d['source_posts'],d['proofs'])
            self.assertEqual(e.hashlib.sha256((e.ROOT/d['image']['file']).read_bytes()).hexdigest(),d['image']['sha256'])
            self.assertLessEqual(len(e.format_post(d)),1024)
    def test_empty_landing_is_not_access(self):
        with self.assertRaises(RuntimeError): e.parse_feed('<h1>Telegram channel</h1>')
    def test_date_without_timezone_rejected(self):
        with self.assertRaises(ValueError): e.parse_feed('<div data-post="x/1"><div class="tgme_widget_message_text">Text</div><time datetime="2026-11-05T06:00:00"></time></div>')
    def test_missing_state_is_not_empty(self):
        with self.assertRaises(FileNotFoundError): e.State(Path(self.tmp.name)/'missing').load()
    def test_large_history_uses_github_raw_representation(self):
        state=e.State()
        with patch.object(state,'github',side_effect=[{'sha':'abc','encoding':'none','content':''},e.initial_state()]) as g:
            self.assertEqual(state.load()['version'],1)
            self.assertEqual(state.sha,'abc');self.assertTrue(g.call_args.kwargs['raw'])
    def test_reinitialize_refused(self):
        with self.assertRaises(RuntimeError): self.state.init()
    def test_ad_and_off_topic_and_old_rejected(self):
        self.assertEqual(e.reject_reason({**P, 'text': 'РОЗЫГРЫШ GTA 6'}, AT), 'advertisement_or_giveaway')
        self.assertEqual(e.reject_reason({**P, 'text': 'GTA 5 на iPhone'}, AT), 'not_gta6_news')
        self.assertEqual(e.reject_reason(P, AT+timedelta(days=3)), 'stale_or_future')
    def test_marketing_news_not_automatically_advert(self):
        post={**P,'text':'Rockstar запускает рекламу GTA 6 на билбордах большого города — подробности кампании'}
        self.assertIsNone(e.reject_reason(post,AT))
    def test_approval_hash_required_before_any_network(self):
        import argparse
        args=argparse.Namespace(command='test-post',state=str(self.state.local),draft=str(e.ROOT/'samples/01-fact/draft.json'),approved_hash='wrong')
        with patch.object(e,'request') as r:
            with self.assertRaisesRegex(RuntimeError,'exact_post_not_approved'):e.run(args)
            r.assert_not_called()
    def test_only_visually_confirmed_published_test_unlocks_marker(self):
        import argparse
        args=argparse.Namespace(command='confirm-test',state=str(self.state.local),approved_hash=e.digest(D),message_id='42')
        with self.assertRaisesRegex(RuntimeError,'test_not_found'):e.run(args)
        e.publish(self.state,FakeBot(),D,[P],test=True,at=AT)
        e.run(args);self.state.load();self.assertEqual(self.state.data['live_test']['message_id'],42)
    def test_utc_previous_evening_counts_as_moscow_today(self):
        self.state.data['live_test']={'message_id':1}
        self.state.data['history']=[{'status':'published','at':d} for d in ['2026-11-04T22:00:00+00:00','2026-11-05T01:00:00+00:00','2026-11-05T03:00:00+00:00']]
        with patch.dict(e.CONFIG,{'autopublish':True}),patch.dict(e.os.environ,{'NEWSROOM_AUTOPUBLISH':'true','NEWSROOM_STYLE_APPROVED':'true'}):
            with self.assertRaisesRegex(RuntimeError,'daily_cap'):e.publish(self.state,FakeBot(),D,[P],at=AT-timedelta(hours=6))
    def test_confirmed_usage_releases_unused_reserve(self):
        self.state.data['spend']['2026-11']=1
        e.settle_cost(self.state,'2026-11',.1,[{'usage':{'prompt_tokens':1000,'completion_tokens':100}}])
        self.assertAlmostEqual(self.state.data['spend']['2026-11'],.10056)
    def test_cross_source_duplicate(self):
        self.assertGreater(e.similarity('GTA 6 дата выхода ноябрь 19 2026', 'Дата выхода GTA 6: 19 ноябрь 2026'), .72)
    def test_fake_primary_domains(self):
        for url in ('https://rockstargames.com.evil.test/VI','http://www.rockstargames.com/VI','https://user@www.rockstargames.com/VI','https://127.0.0.1/'):
            self.assertFalse(e.official(url))
    def test_real_primary_domain(self):
        self.assertTrue(e.official(e.PRIMARY_FALLBACK));self.assertTrue(e.official('https://support.rockstargames.com/articles/example'))
    def test_valid_draft(self): self.assertEqual(e.validate_draft(copy.deepcopy(D), [P], [PROOF]), D)
    def test_unfetched_citation_rejected(self):
        d=copy.deepcopy(D); d['citations']=['https://www.rockstargames.com/invented']
        with self.assertRaises(ValueError): e.validate_draft(d,[P],[PROOF])
    def test_invented_quote_rejected(self):
        d=copy.deepcopy(D); d['claims'][0]['quote']='GTA6 costs $100 officially'
        with self.assertRaises(ValueError): e.validate_draft(d,[P],[PROOF])
    def test_secondary_fact_rejected(self):
        d=copy.deepcopy(D); d['citations']=[P['url']]
        with self.assertRaises(ValueError): e.validate_draft(d,[P],[])
    def test_rumor_requires_uncertainty(self):
        d=copy.deepcopy(D); d['kind']='rumor'; d['citations']=[P['url']];d['claims']=[{'url':P['url'],'quote':P['text']}]
        with self.assertRaises(ValueError): e.validate_draft(d,[P],[])
        d['body']='Ранний доступ не подтверждено.'
        self.assertEqual(e.validate_draft(d,[P],[])['kind'],'rumor')
    def test_sources_kept_internal_but_never_in_caption(self):
        d=copy.deepcopy(D)
        e.validate_draft(d,[P],[PROOF]);caption=e.format_post(d)
        self.assertNotIn(e.PRIMARY_FALLBACK,caption);self.assertNotIn('href=',caption);self.assertNotIn('Источник',caption)
        self.assertEqual(d['citations'],[e.PRIMARY_FALLBACK])
    def test_source_links_in_body_rejected(self):
        d=copy.deepcopy(D);d['body']='Ссылка: '+e.PRIMARY_FALLBACK
        with self.assertRaisesRegex(ValueError,'public_source_reference'):e.validate_draft(d,[P],[PROOF])
    def test_old_source_bearing_image_cannot_publish(self):
        d=json.loads((e.ROOT/'samples/02-rumor/draft.json').read_text())
        bot=FakeBot()
        with self.assertRaisesRegex(RuntimeError,'image_public_sources_not_reviewed'):e.publish(self.state,bot,d,d['source_posts'],test=True,at=AT)
        self.assertEqual(bot.calls,0);self.assertEqual(self.state.data['history'],[])
    def test_telegram_html_escaped(self):
        self.assertIn('&lt;script&gt;',e.format_post({**D,'body':'<script>'}))
    def test_budget_zero_no_api_call(self):
        with patch.dict(e.CONFIG, {'monthly_budget_usd':0}), patch.dict(e.os.environ, {'NEWSROOM_AI_SPEND_APPROVED':'true'}), patch.object(e,'request') as r:
            with self.assertRaisesRegex(RuntimeError,'ai_budget_disabled'): e.generate([P],[PROOF],self.state)
            r.assert_not_called()
    def test_no_consent_no_api(self):
        with patch.dict(e.os.environ, {'NEWSROOM_AI_SPEND_APPROVED':'false'}),patch.object(e,'request') as r:
            with self.assertRaisesRegex(RuntimeError,'not_approved'): e.generate([P],[PROOF],self.state)
            r.assert_not_called()
    def test_autopublish_disabled(self):
        bot=FakeBot()
        with self.assertRaisesRegex(RuntimeError,'gate_closed'): e.publish(self.state,bot,D,[P],at=AT)
        self.assertEqual(bot.calls,0)
    def test_approved_test_persists_message_without_enabling_auto(self):
        bot=FakeBot(); e.publish(self.state,bot,D,[P],test=True,at=AT)
        self.state.load();self.assertEqual(self.state.data['history'][0]['message_id'],42);self.assertIsNone(self.state.data['live_test'])
    def test_duplicate_test_does_not_send(self):
        bot=FakeBot();e.publish(self.state,bot,D,[P],test=True,at=AT)
        with self.assertRaisesRegex(RuntimeError,'duplicate'):e.publish(self.state,bot,D,[P],test=True,at=AT)
        self.assertEqual(bot.calls,1)
    def test_timeout_reserves_and_blocks_resend(self):
        bot=FakeBot(fail=True)
        with self.assertRaisesRegex(RuntimeError,'delivery_uncertain'):e.publish(self.state,bot,D,[P],test=True,at=AT)
        self.state.load();self.assertEqual(self.state.data['history'][0]['status'],'uncertain')
        with self.assertRaisesRegex(RuntimeError,'unresolved'):e.publish(self.state,bot,D,[P],test=True,at=AT)
        self.assertEqual(bot.calls,1)
    def test_failed_reservation_no_send(self):
        bot=FakeBot()
        with patch.object(self.state,'save',side_effect=RuntimeError('http_409')):
            with self.assertRaises(RuntimeError):e.publish(self.state,bot,D,[P],test=True,at=AT)
        self.assertEqual(bot.calls,0)
    def test_save_after_delivery_failure_leaves_pending(self):
        bot=FakeBot(); save=self.state.save
        def fail_after():
            if self.state.data['history'] and self.state.data['history'][0]['status']=='published':raise RuntimeError('http_409')
            save()
        with patch.object(self.state,'save',side_effect=fail_after):
            with self.assertRaises(RuntimeError):e.publish(self.state,bot,D,[P],test=True,at=AT)
        self.state.load();self.assertEqual(self.state.data['history'][0]['status'],'pending');self.assertEqual(bot.calls,1)
    def test_daily_cap_and_timezone(self):
        self.state.data['live_test']={'message_id':1}
        self.state.data['history']=[{'status':'published','at':(AT-timedelta(hours=i)).isoformat()} for i in (6,5,4)]
        with patch.dict(e.CONFIG,{'autopublish':True}),patch.dict(e.os.environ,{'NEWSROOM_AUTOPUBLISH':'true','NEWSROOM_STYLE_APPROVED':'true'}):
            with self.assertRaisesRegex(RuntimeError,'daily_cap'):e.publish(self.state,FakeBot(),D,[P],at=AT)
    def test_out_of_window(self):
        self.state.data['live_test']={'message_id':1}
        with patch.dict(e.CONFIG,{'autopublish':True}),patch.dict(e.os.environ,{'NEWSROOM_AUTOPUBLISH':'true','NEWSROOM_STYLE_APPROVED':'true'}):
            with self.assertRaisesRegex(RuntimeError,'outside_moscow'):e.publish(self.state,FakeBot(),D,[P],at=AT+timedelta(hours=1))
    def test_photo_sender_uses_approved_bytes_and_caption(self):
        d=json.loads((e.ROOT/'samples/01-fact/draft.json').read_text())
        with patch.dict(e.os.environ,{'TELEGRAM_BOT_TOKEN':'test-placeholder'}),patch.object(e,'request',return_value=b'{"ok":true,"result":{"message_id":7}}') as r:
            self.assertEqual(e.Bot().send(d)['message_id'],7)
            self.assertTrue(r.call_args.args[0].endswith('/sendPhoto'))
            self.assertIn((e.ROOT/d['image']['file']).read_bytes(),r.call_args.args[1])
            self.assertIn(e.format_post(d).encode(),r.call_args.args[1])
    def test_source_outage_fails_cli_without_publication(self):
        import argparse
        args=argparse.Namespace(command='audit',state=None,output=str(Path(self.tmp.name)/'audit'))
        with patch.object(e,'collect',return_value=([],[],[{'source':'leonidagov','code':'http_403'}])),patch.object(e.Bot,'send') as send:
            with self.assertRaisesRegex(RuntimeError,'partial_source_outage'):e.run(args)
            send.assert_not_called()
    def test_model_cannot_add_unapproved_image_field(self):
        d={**D,'image':{'file':'unapproved','sha256':'unapproved'}}
        response={'choices':[{'message':{'content':json.dumps(d)}}]}
        with patch.dict(e.CONFIG,{'monthly_budget_usd':2}),patch.dict(e.os.environ,{'NEWSROOM_AI_SPEND_APPROVED':'true','NEWSROOM_LLM_KEY':'test-placeholder'}),patch.object(e,'request',return_value=json.dumps(response).encode()):
            with self.assertRaisesRegex(ValueError,'unexpected_model_fields'):e.generate([P],[PROOF],self.state)
    def test_connections_metadata_only_no_sending(self):
        with patch.dict(e.os.environ,{'NEWSROOM_LLM_KEY':'test-placeholder','TELEGRAM_BOT_TOKEN':'test-placeholder'}),patch.object(e.Bot,'check',return_value={'can_post_messages':True}),patch.object(e,'request',return_value=json.dumps({'id':e.CONFIG['model']}).encode()) as r:
            result=e.check_connections()
            self.assertTrue(result['openai']['ok']);self.assertFalse(result['openai']['billing_balance_verified'])
            self.assertEqual(r.call_args.kwargs['method'],'GET');self.assertIn('/v1/models/',r.call_args.args[0])
    def test_connections_missing_secret_no_api(self):
        with patch.dict(e.os.environ,{'NEWSROOM_LLM_KEY':'','TELEGRAM_BOT_TOKEN':'test-placeholder'}),patch.object(e.Bot,'check',return_value={}),patch.object(e,'request') as r:
            self.assertEqual(e.check_connections()['openai']['error'],'llm_secret_missing');r.assert_not_called()
    def test_connections_error_is_redacted(self):
        with patch.dict(e.os.environ,{'NEWSROOM_LLM_KEY':'test-placeholder','TELEGRAM_BOT_TOKEN':'test-placeholder'}),patch.object(e.Bot,'check',side_effect=RuntimeError('secret value must not leak')),patch.object(e,'request',side_effect=RuntimeError('http_401')):
            result=e.check_connections();self.assertEqual(result['telegram']['error'],'RuntimeError');self.assertEqual(result['openai']['error'],'http_401')
    def test_urgent_bypasses_normal_slot_at_night(self):
        self.state.data['live_test']={'message_id':1}
        d={**D,'priority':'urgent','_urgent_verified':True}
        with patch.dict(e.CONFIG,{'autopublish':True}),patch.dict(e.os.environ,{'NEWSROOM_AUTOPUBLISH':'true','NEWSROOM_STYLE_APPROVED':'true'}):
            self.assertEqual(e.publish(self.state,FakeBot(),d,[P],at=AT+timedelta(hours=10))['status'],'published')
    def test_normal_story_still_blocked_at_night(self):
        with self.assertRaisesRegex(RuntimeError,'outside_moscow'):e.publication_limits(self.state,urgent=False,at=AT+timedelta(hours=10))
    def test_urgent_candidate_keywords_not_enough_for_publishing(self):
        p={**P,'text':'Rockstar выпустила новый официальный трейлер GTA 6 с игровыми кадрами'}
        self.assertTrue(e.urgent_candidate(p,self.state,AT))
        self.assertFalse(e.urgent_verified({**D,'priority':'urgent'}))
        self.assertFalse(e.urgent_candidate({**p,'text':'СЛУХ: '+p['text']},self.state,AT))
    def test_urgent_rejected_candidate_not_rebilled(self):
        p={**P,'text':'Rockstar выпустила новый официальный трейлер GTA 6 с игровыми кадрами'}
        self.state.data['urgent_examined']={e.digest(p['text']):AT.isoformat()}
        self.assertFalse(e.urgent_candidate(p,self.state,AT))
    def test_urgent_stale_candidate_is_not_breaking(self):
        p={**P,'text':'Rockstar выпустила новый официальный трейлер GTA 6 с игровыми кадрами'}
        self.assertFalse(e.urgent_candidate(p,self.state,AT+timedelta(hours=7)))
    def test_urgent_has_one_extra_daily_slot(self):
        self.state.data['history']=[{'status':'published','at':(AT-timedelta(hours=i)).isoformat()} for i in (6,5,4)]
        e.publication_limits(self.state,urgent=True,at=AT)
        with self.assertRaisesRegex(RuntimeError,'daily_cap'):e.publication_limits(self.state,urgent=False,at=AT)
        self.state.data['history'].append({'status':'published','at':(AT-timedelta(hours=1)).isoformat()})
        with self.assertRaisesRegex(RuntimeError,'daily_cap'):e.publication_limits(self.state,urgent=True,at=AT)
    def test_urgent_does_not_bypass_uncertain_delivery(self):
        self.state.data['live_test']={'message_id':1}
        self.state.data['history']=[{'status':'uncertain','at':(AT-timedelta(hours=1)).isoformat()}]
        with patch.dict(e.CONFIG,{'autopublish':True}),patch.dict(e.os.environ,{'NEWSROOM_AUTOPUBLISH':'true','NEWSROOM_STYLE_APPROVED':'true'}):
            with self.assertRaisesRegex(RuntimeError,'unresolved_delivery'):e.publish(self.state,FakeBot(),{**D,'_urgent_verified':True},[P],at=AT)
    def test_urgency_requires_second_review_confirmation(self):
        d={**D,'priority':'urgent'}
        for confirm in (False,True):
            responses=[{'choices':[{'message':{'content':json.dumps(d)}}]}, {'choices':[{'message':{'content':json.dumps({'approved':True,'urgent_confirmed':confirm})}}]}]
            with patch.dict(e.os.environ,{'NEWSROOM_AI_SPEND_APPROVED':'true','NEWSROOM_LLM_KEY':'test-placeholder'}),patch.object(e,'request',side_effect=[json.dumps(r).encode() for r in responses]):
                result=e.generate([P],[PROOF],self.state,urgent_only=True)
                if confirm:self.assertTrue(result['_urgent_verified'])
                else:self.assertIsNone(result)
    def test_bot_identity_and_permissions(self):
        with patch.dict(e.os.environ,{'TELEGRAM_BOT_TOKEN':'test-placeholder'}):
            bot=e.Bot()
            with patch.object(bot,'call',side_effect=[{'id':1,'username':'wrong'}]):
                with self.assertRaisesRegex(RuntimeError,'wrong_bot'):bot.check()
            with patch.object(bot,'call',side_effect=[{'id':1,'username':'GTA6NewsHustleBot'},{'id':-1,'type':'channel'},{'status':'administrator','can_post_messages':False}]):
                with self.assertRaisesRegex(RuntimeError,'cannot_post'):bot.check()
            with patch.object(bot,'call',side_effect=[{'id':1,'username':'GTA6NewsHustleBot'},{'id':-1,'type':'channel'},{'status':'administrator','can_post_messages':True}]):
                self.assertTrue(bot.check()['can_post_messages'])

if __name__=='__main__':unittest.main()
