import unittest
from delivery_tools.review_file import prepare_review_caption

class ReviewCaptionTests(unittest.TestCase):
 def test_authored_html_is_not_printed_as_tags(self):
  source='<b>🗺️ КЛУБ ИЛИ ЦЕЛЫЙ ШТАТ?</b>\n\n🌴 <b>Леонида-Кис.</b> Острова\n<i>Реплика Лестера</i>\n<blockquote>Куда поедешь?</blockquote>\n<tg-spoiler>Секрет</tg-spoiler>\n<a href="https://example.com/map">Карта</a>'
  text,entities=prepare_review_caption(source)
  self.assertIn('🌴 Леонида-Кис. Острова',text)
  self.assertNotIn('<b>',text);self.assertNotIn('&lt;',text)
  self.assertTrue({'bold','italic','blockquote','spoiler','text_link','custom_emoji'}<={x['type']for x in entities})
  bold=next(x for x in entities if x['type']=='bold'and x['offset']>0)
  self.assertEqual(text.encode('utf-16-le')[bold['offset']*2:(bold['offset']+bold['length'])*2].decode('utf-16-le'),'Леонида-Кис.')
 def test_legacy_plain_text_keeps_characters(self):
  text,entities=prepare_review_caption('НОВЫЙ РОЛИК\n1 < 2 & GTA > V')
  self.assertIn('НОВЫЙ РОЛИК\n1 < 2 & GTA > V',text)
  self.assertTrue(any(e['type']=='bold'for e in entities))
 def test_explicit_plain_text_does_not_interpret_tags(self):
  text,_=prepare_review_caption('ЗАГОЛОВОК\nТекст <b>пример</b>','text')
  self.assertIn('<b>пример</b>',text)
 def test_strong_header_normalized(self):
  text,entities=prepare_review_caption('<STRONG>ЗАГОЛОВОК</STRONG>\n<i>Курсив</i>')
  self.assertNotIn('<STRONG>',text)
  self.assertTrue({'bold','italic'}<={x['type']for x in entities})
 def test_html_body_and_plain_header(self):
  text,entities=prepare_review_caption('ЗАГОЛОВОК\n<b>Локация</b>')
  self.assertNotIn('<b>',text)
  self.assertEqual(sum(e['type']=='bold'for e in entities),2)
 def test_invalid_format(self):
  with self.assertRaisesRegex(RuntimeError,'review_caption_format_invalid'):prepare_review_caption('Текст','unsupported')

if __name__=='__main__':unittest.main()
