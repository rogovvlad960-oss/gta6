import unittest
from io import BytesIO
from PIL import Image
from .bot_emoji import format_message,verify_returned
from .monitor import body_html
from .image_branding import brand_external_image

class RulesTests(unittest.TestCase):
 def test_post_has_single_footer_and_no_emoji_pairs(self):
  from .monitor import caption
  text,entities=format_message(caption({'title':'⚡️🔥 Заголовок','body':'💸 💵 **Деталь**\n\n> Памятка\n\n_Панч_\n\n@lesterdossier'}))
  self.assertEqual(text.count('@lesterdossier'),1);self.assertTrue(text.endswith('@lesterdossier'))
  self.assertNotIn('⚡️🔥',text);self.assertNotIn('💸 💵',text)
  self.assertTrue({'bold','italic','blockquote'}.issubset({x['type']for x in entities}))
 def test_emoji_sequences_keep_flags_and_family_intact(self):
  from .engine import separate_emoji
  self.assertEqual(separate_emoji('🇷🇺 Текст 👨‍👩‍👧‍👦'),'🇷🇺 Текст 👨‍👩‍👧‍👦')
  self.assertEqual(separate_emoji('🇷🇺🔥 Текст'),'🇷🇺 Текст')
 def test_attribution_is_valid_without_stock_disclaimer(self):
  from . import engine
  source={'id':'test/1','url':'https://t.me/test/1','text':'Игроки сообщают, что нашли новую пещеру в GTA VI.'}
  draft={'kind':'rumor','title':'Пещера в GTA VI','body':source['text'],'event_key':'cave','source_ids':['test/1'],'citations':[source['url']],'claims':[{'url':source['url'],'quote':source['text']}]}
  self.assertEqual(engine.validate_draft(draft,[source],[]),draft)
  draft['body']='В GTA VI точно добавили эту пещеру.'
  with self.assertRaisesRegex(ValueError,'unlabeled_uncertainty'):engine.validate_draft(draft,[source],[])
 def test_long_bold_phrase_renders_and_plain_model_output_gets_required_styles(self):
  from .monitor import caption,check_post_style
  from .bot_emoji import format_caption
  long='Стабильный FPS '+('важная деталь '*8)
  text,entities=format_caption(caption({'title':'Новость','body':'Обычный абзац.\n\n**'+long.strip()+'**'}))
  self.assertNotIn('**',text);check_post_style(text,entities)
  data=text.encode('utf-16-le');bold=[data[e['offset']*2:(e['offset']+e['length'])*2].decode('utf-16-le')for e in entities if e['type']=='bold']
  self.assertIn(long.strip(),bold)
 def test_style_preflight_rejects_unformatted_post(self):
  from .monitor import check_post_style
  with self.assertRaisesRegex(RuntimeError,'required_post_formatting_missing'):check_post_style('Текст\n\n@lesterdossier',[])
 def test_generated_body_keeps_italic_quote_and_spoiler(self):
  text,entities=format_message('<b>📰 Заголовок</b>\n'+body_html('_Комментарий_\n\n> Первый шаг\n> Второй шаг\n\n||Панч||'))
  data=text.encode('utf-16-le');spans={e['type']:data[e['offset']*2:(e['offset']+e['length'])*2].decode('utf-16-le')for e in entities if e['type']in('italic','blockquote','spoiler')}
  self.assertEqual(spans,{'italic':'Комментарий','blockquote':'Первый шаг\nВторой шаг','spoiler':'Панч'})
  verify_returned({'entities':entities},entities)
  with self.assertRaisesRegex(RuntimeError,'rich_formatting_not_preserved'):
   verify_returned({'entities':[e for e in entities if e['type']!='spoiler']},entities)
 def test_telegram_bold_split_around_custom_emoji_is_valid(self):
  text,entities=format_message('<b>📝 Заголовок</b>')
  actual=[e for e in entities if e['type']!='bold']+[{'type':'bold','offset':0,'length':2},{'type':'bold','offset':2,'length':len(text.encode('utf-16-le'))//2-2}]
  verify_returned({'entities':actual},entities)
 def test_external_html_is_still_literal(self):
  text,entities=format_message(body_html('||<script>alert(1)</script>||'))
  self.assertEqual(text,'<script>alert(1)</script>');self.assertEqual(entities[0]['type'],'spoiler')
 def test_both_spoiler_html_forms(self):
  text,entities=format_message('<tg-spoiler>а</tg-spoiler> <span class="tg-spoiler">б</span>')
  self.assertEqual([e['type']for e in entities],['spoiler','spoiler'])
 def test_branding_failure_never_falls_back_to_raw_delivery(self):
  from types import SimpleNamespace
  from unittest.mock import patch
  from . import monitor
  state=SimpleNamespace(data={},save=lambda:None)
  with patch.object(monitor,'seen_draft',return_value=False),patch.object(monitor,'check_recipient',return_value=123),patch.object(monitor.e,'request',return_value=b'\x89PNGdummy')as request,patch('newsroom_private.image_branding.brand_external_image',side_effect=ValueError('bad image')):
   with self.assertRaises(ValueError):monitor.send_reserved(state,{'title':'Кадр','body':'Текст','event_key':'fixture','source_ids':[]},[],'https://cdn4.telesco.pe/file/x.jpg')
   self.assertEqual(request.call_count,1)
   self.assertEqual(state.data['private_editor']['history'],[])
 def test_foreign_image_is_recomposed_without_source_crop(self):
  source=Image.new('RGB',(800,450),(210,120,35));buf=BytesIO();source.save(buf,format='PNG');raw=buf.getvalue()
  blob,meta=brand_external_image(raw,'Почему этот кадр обсуждают игроки')
  result=Image.open(BytesIO(blob));self.assertEqual(result.size,(1600,1400));self.assertTrue(meta['source_fully_visible']);self.assertNotEqual(meta['source_sha256'],meta['output_sha256'])
  x,y,right,bottom=meta['source_rect'];self.assertAlmostEqual((right-x)/(bottom-y),800/450,places=2)
  pixel=result.getpixel(((x+right)//2,(y+bottom)//2));self.assertLess(sum(abs(a-b)for a,b in zip(pixel,(210,120,35))),12)
if __name__=='__main__':unittest.main()
