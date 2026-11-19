import unittest
from .bot_emoji import format_message,format_caption,verify_returned,units,SEMANTIC_EMOJI

class PostFormatTests(unittest.TestCase):
 def test_rich_reference_post_preserves_utf16_and_copyable_sequences(self):
  text,entities=format_message('<b>💸 Деньги</b>\n🔫 <i>Оружие</i>\n<code>↑ → ↓ ←</code>\n🚗 Транспорт')
  packed=text.encode('utf-16-le')
  spans={e['type']:packed[e['offset']*2:(e['offset']+e['length'])*2].decode('utf-16-le')for e in entities if e['type']in('bold','italic','code')}
  self.assertEqual(spans,{'bold':'💸 Деньги','italic':'Оружие','code':'↑ → ↓ ←'})
  custom=[e for e in entities if e['type']=='custom_emoji'];self.assertEqual(len({e['custom_emoji_id']for e in custom}),3)
  verify_returned({'entities':entities},entities)
 def test_long_post_and_caption_have_different_telegram_limits(self):
  html='<b>💸 Список</b>\n'+'а'*1500
  text,_=format_message(html);self.assertGreater(units(text),1024)
  with self.assertRaisesRegex(RuntimeError,'caption_too_long'):format_caption(html)
 def test_semantic_header_is_retained_and_code_is_not_reformatted(self):
  text,entities=format_caption('<b>💸 Деньги</b>\n<code>💸 ↑</code>')
  custom=[e for e in entities if e['type']=='custom_emoji'];self.assertTrue(text.startswith('💸'))
  self.assertEqual(len(custom),1);self.assertEqual(custom[0]['custom_emoji_id'],SEMANTIC_EMOJI['💸'])
if __name__=='__main__':unittest.main()
