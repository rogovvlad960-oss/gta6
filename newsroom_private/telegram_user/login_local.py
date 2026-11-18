"""Run ONLY on the owner's computer. Never paste login codes/session into chat."""
import asyncio,getpass,os
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession

async def main():
 print('Официальные API ID и API Hash: https://my.telegram.org/apps')
 api_id=int(input('API ID: ').strip());api_hash=getpass.getpass('API Hash (скрыт): ').strip()
 c=TelegramClient(StringSession(),api_id,api_hash)
 try:
  await c.start(phone=lambda:getpass.getpass('Номер Telegram с + (скрыт): '),code_callback=lambda:getpass.getpass('Код входа Telegram (только здесь, скрыт): '),password=lambda:getpass.getpass('Облачный пароль Telegram, если включён (скрыт): '))
  me=await c.get_me()
  if not getattr(me,'premium',False):raise RuntimeError('Для этого подключения нужен Premium на аккаунте')
  target=Path.cwd()/'telegram-user-private';target.mkdir(mode=0o700,exist_ok=True)
  values={'TELEGRAM_API_ID':str(api_id),'TELEGRAM_API_HASH':api_hash,'TELEGRAM_USER_SESSION':c.session.save()}
  for name,value in values.items():
   path=target/(name+'.txt');path.write_text(value);os.chmod(path,0o600)
  print('Вход подтверждён. Три файла для GitHub Secrets сохранены в:',target)
  print('НЕ присылай файлы в чат, НЕ загружай их в репозиторий. Содержимое — только в GitHub Settings → Secrets and variables → Actions.')
 finally:await c.disconnect()
if __name__=='__main__':asyncio.run(main())
