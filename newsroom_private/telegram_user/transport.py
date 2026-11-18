import asyncio,hashlib,io,json,os,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PACK='GamingEmoji_by_MoiStikiBot'
LOGO=5282847372223740079
LIGHTNING=5222430393688432601

def utf16len(text):return len(text.encode('utf-16-le'))//2

def formatted(html_text,urgent=False):
 from telethon.extensions import html
 from telethon.tl.types import MessageEntityCustomEmoji
 fallback='⚡️'if urgent else '📰'
 source=re.sub(r'^<b>[^\w<]*','<b>'+fallback+' ',html_text,count=1)
 text,entities=html.parse(source)
 if not text.startswith(fallback):raise RuntimeError('custom_emoji_anchor_missing')
 entities.append(MessageEntityCustomEmoji(offset=0,length=utf16len(fallback),document_id=LIGHTNING if urgent else LOGO))
 return text,entities

async def client():
 from telethon import TelegramClient
 from telethon.sessions import StringSession
 for name in ['TELEGRAM_API_ID','TELEGRAM_API_HASH','TELEGRAM_USER_SESSION']:
  if not os.environ.get(name):raise RuntimeError('telegram_user_credentials_missing')
 c=TelegramClient(StringSession(os.environ['TELEGRAM_USER_SESSION']),int(os.environ['TELEGRAM_API_ID']),os.environ['TELEGRAM_API_HASH'],connection_retries=1,request_retries=1,timeout=20,flood_sleep_threshold=0)
 try:
  await c.connect()
  if not await c.is_user_authorized():raise RuntimeError('telegram_user_login_required')
  me=await c.get_me();r=json.loads((ROOT/'route.enc.json').read_text())
  actual=hashlib.sha256((r['recipient_salt']+':'+str(me.id)).encode()).hexdigest()
  if actual!=r['recipient_hash']:raise RuntimeError('telegram_user_owner_mismatch')
  if not getattr(me,'premium',False):raise RuntimeError('telegram_user_premium_required')
  return c,me
 except BaseException:
  await c.disconnect();raise

async def _check():
 c,me=await client()
 try:return me.id
 finally:await c.disconnect()
def check():return asyncio.run(_check())

async def _send(image,html_text,urgent=False):
 from telethon.tl.functions.messages import GetCustomEmojiDocumentsRequest
 from telethon.tl.types import MessageEntityCustomEmoji
 c,me=await client()
 try:
  text,entities=formatted(html_text,urgent);doc=LIGHTNING if urgent else LOGO
  docs=await c(GetCustomEmojiDocumentsRequest(document_id=[doc]))
  if not docs:raise RuntimeError('custom_emoji_document_unavailable')
  if image is None:m=await c.send_message('me',text,formatting_entities=entities,link_preview=False)
  else:
   file=io.BytesIO(image);file.name='post.jpg'
   m=await c.send_file('me',file,caption=text,formatting_entities=entities,force_document=False)
  if m.chat_id!=me.id:raise RuntimeError('telegram_user_destination_mismatch')
  if not any(isinstance(x,MessageEntityCustomEmoji)and x.document_id==doc for x in (m.entities or [])):raise RuntimeError('custom_emoji_entity_missing_in_result')
  return {'message_id':m.id,'custom_emoji_id':str(doc),'destination':'saved_messages','account_owner_verified':True,'premium_verified':True}
 finally:await c.disconnect()
def send_photo(image,html_text,urgent=False):return asyncio.run(_send(image,html_text,urgent))

def main():
 try:
  r=asyncio.run(_send(None,'<b>🎮 Проверка премиум-эмодзи</b>\n\nЭто тест оформления «Досье Лестера» через твой аккаунт. Эмодзи вставлено в текст из твоего набора.'))
  print(json.dumps(r))
 except Exception as exc:
  code=str(exc)if re.fullmatch('[a-z_]+',str(exc))else type(exc).__name__
  print(json.dumps({'error':code}));raise SystemExit(1)
if __name__=='__main__':main()
