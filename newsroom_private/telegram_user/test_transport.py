import unittest
from unittest.mock import AsyncMock,patch
from types import SimpleNamespace
from . import transport as t
from telethon.tl.types import MessageEntityBold,MessageEntityCustomEmoji
class Tests(unittest.TestCase):
 def test_custom_emoji_is_inline_with_utf16_offsets_and_bold(self):
  text,entities=t.formatted('<b>🚔 КОПЫ</b>\n\nТекст <b>детали</b>')
  self.assertEqual(text,'📰 КОПЫ\n\nТекст детали')
  custom=next(e for e in entities if isinstance(e,MessageEntityCustomEmoji))
  self.assertEqual((custom.offset,custom.length,custom.document_id),(0,2,t.LOGO))
  bold=[e for e in entities if isinstance(e,MessageEntityBold)]
  self.assertEqual(bold[0].length,t.utf16len('📰 КОПЫ'))
  self.assertEqual(bold[1].offset,t.utf16len('📰 КОПЫ\n\nТекст '))
 def test_urgent_uses_verified_pack_lightning(self):
  text,entities=t.formatted('<b>⚡️ Новость</b>',urgent=True)
  custom=next(e for e in entities if isinstance(e,MessageEntityCustomEmoji))
  self.assertTrue(text.startswith('⚡️ '));self.assertEqual(custom.document_id,t.LIGHTNING);self.assertEqual(custom.length,2)
 def test_no_arbitrary_target_parameter(self):
  import inspect
  self.assertEqual(list(inspect.signature(t.send_photo).parameters),['image','html_text','urgent'])
 def test_missing_credentials_does_not_prompt_for_login(self):
  import asyncio
  with patch.dict(t.os.environ,{},clear=True):
   with self.assertRaisesRegex(RuntimeError,'credentials_missing'):asyncio.run(t.client())
 def test_other_account_is_rejected_and_disconnected(self):
  self.check_identity(100,99,True,'owner_mismatch')
 def test_non_premium_account_is_rejected_and_disconnected(self):
  self.check_identity(100,100,False,'premium_required')
 def check_identity(self,me_id,approved,premium,error):
  import asyncio,tempfile,json,hashlib
  from pathlib import Path
  c=SimpleNamespace(connect=AsyncMock(),disconnect=AsyncMock(),is_user_authorized=AsyncMock(return_value=True),get_me=AsyncMock(return_value=SimpleNamespace(id=me_id,premium=premium)))
  with tempfile.TemporaryDirectory()as td:
   Path(td,'route.enc.json').write_text(json.dumps({'recipient_salt':'test','recipient_hash':hashlib.sha256(('test:'+str(approved)).encode()).hexdigest()}))
   with patch.object(t,'ROOT',Path(td)),patch.dict(t.os.environ,{'TELEGRAM_API_ID':'1','TELEGRAM_API_HASH':'test','TELEGRAM_USER_SESSION':'test'}),patch('telethon.TelegramClient',return_value=c),patch('telethon.sessions.StringSession'):
    with self.assertRaisesRegex(RuntimeError,error):asyncio.run(t.client())
   c.disconnect.assert_awaited_once()
if __name__=='__main__':unittest.main()
