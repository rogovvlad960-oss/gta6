"""Deliver a hash-verified review MP4 as a private document using runner secrets."""
import hashlib,html,json,os,re,sys,uuid
from urllib.parse import urlparse
from newsroom_private import engine as e,monitor as m
from newsroom_private.bot_emoji import format_caption,verify_returned

def main():
 url=os.environ['REVIEW_ASSET_URL'];expected=os.environ['REVIEW_SHA256'];name=os.environ['REVIEW_FILENAME'];caption=os.environ['REVIEW_CAPTION'].strip()
 u=urlparse(url)
 if u.scheme!='https'or u.hostname!='resource2.heygen.ai'or not u.path.startswith('/video/')or u.username or u.password:raise RuntimeError('review_asset_url_rejected')
 if not re.fullmatch('[a-f0-9]{64}',expected)or not re.fullmatch('[A-Za-z0-9._-]+\.mp4',name):raise RuntimeError('review_metadata_invalid')
 state=e.State();state.load();m.ROUTING_STATE=state;cid=m.check_recipient()
 ledger=state.data.setdefault('review_file_deliveries',{});key=hashlib.sha256((expected+'\0'+caption).encode()).hexdigest()
 if key in ledger:
  if ledger[key]['status']=='sent':print(json.dumps({'already_sent':True,**ledger[key]}));return
  raise RuntimeError('review_delivery_requires_reconciliation')
 blob=e.request(url,limit=49_000_000)
 if hashlib.sha256(blob).hexdigest()!=expected:raise RuntimeError('review_sha256_mismatch')
 lines=caption.split('\n',1);markup='<b>'+html.escape(lines[0])+'</b>'+('\n'+html.escape(lines[1])if len(lines)>1 else'');text,entities=format_caption(markup)
 record={'status':'pending','sha256':expected,'bytes':len(blob),'filename':name};ledger[key]=record;state.save()
 try:
  b='review'+uuid.uuid4().hex;parts=[]
  for k,v in [('chat_id',str(cid)),('caption',text),('caption_entities',json.dumps(entities,ensure_ascii=False)),('disable_content_type_detection','true'),('disable_notification','false')]:parts.append((f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n').encode())
  parts.extend([(f'--{b}\r\nContent-Disposition: form-data; name="document"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode(),blob,f'\r\n--{b}--\r\n'.encode()])
  d=json.loads(e.request('https://api.telegram.org/bot'+os.environ['TELEGRAM_BOT_TOKEN']+'/sendDocument',b''.join(parts),{'Content-Type':'multipart/form-data; boundary='+b}))
  if not d.get('ok'):raise RuntimeError('review_telegram_rejected')
  result=d['result'];record['message_id']=result.get('message_id')
  if result.get('chat',{}).get('type')!='private'or result['chat']['id']!=cid:raise RuntimeError('review_recipient_mismatch')
  if 'document'not in result or 'video'in result:raise RuntimeError('review_expected_document')
  if result['document'].get('file_size')!=len(blob):raise RuntimeError('review_document_size_mismatch')
  if result.get('caption')!=text:raise RuntimeError('review_caption_mismatch')
  verify_returned(result,entities)
 except Exception:
  record['status']='uncertain';state.save();raise
 record.update(status='sent',document_verified=True,caption_verified=True,premium_emoji_verified=True);state.save();print(json.dumps(record))
if __name__=='__main__':
 try:main()
 except Exception as exc:
  print(json.dumps({'error':str(exc)if re.fullmatch('[a-z_]+',str(exc))else type(exc).__name__}));sys.exit(1)
