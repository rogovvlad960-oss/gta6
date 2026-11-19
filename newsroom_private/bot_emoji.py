"""Telegram rich text and verified semantic premium emoji, with UTF-16 offsets."""
import re
from html.parser import HTMLParser
LOGO='5282847372223740079'
LIGHTNING='5222430393688432601'
# Each selected graphic was visually checked; fallback labels alone are unreliable.
SEMANTIC_EMOJI={
 '📰':LOGO,'⚡️':LIGHTNING,'⚡':LIGHTNING,
 '💸':'5346023102742571644','💵':'5346023102742571644',
 '🔫':'5222098491500702725','🚘':'5278320231880631425','🚗':'5278320231880631425',
 '💣':'5282741466920156473','🗺️':'5282842763723832120',
 '🎥':'5280793836690384768','❗️':'5222464272390463282','❗':'5222464272390463282',
 '📝':'5283224216949261313',
}
def units(text):return len(text.encode('utf-16-le'))//2
class CaptionParser(HTMLParser):
 TAGS={'b':'bold','strong':'bold','i':'italic','em':'italic','u':'underline','s':'strikethrough','code':'code','pre':'pre','blockquote':'blockquote','tg-spoiler':'spoiler','a':'text_link','tg-emoji':'custom_emoji'}
 def __init__(self):super().__init__(convert_charrefs=True);self.text='';self.entities=[];self.stack=[]
 def handle_starttag(self,tag,attrs):
  if tag=='br':self.text+='\n';return
  attrs=dict(attrs)
  if tag=='span' and attrs.get('class')=='tg-spoiler':kind='spoiler'
  elif tag in self.TAGS:kind=self.TAGS[tag]
  else:return
  extra={}
  if tag=='tg-emoji':
   ident=attrs.get('emoji-id','')
   if not ident.isdecimal():raise ValueError('invalid_custom_emoji_id')
   extra={'custom_emoji_id':ident}
  if tag=='a':extra={'url':attrs.get('href','')}
  kind='expandable_blockquote'if tag=='blockquote'and'expandable'in attrs else kind
  self.stack.append((tag,units(self.text),kind,extra))
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i][0]==tag:
    _,start,kind,extra=self.stack.pop(i);length=units(self.text)-start
    if length:self.entities.append({'type':kind,'offset':start,'length':length,**extra})
    return
 def handle_data(self,data):self.text+=data

def format_message(html_text,*,limit=4096):
 parser=CaptionParser();parser.feed(html_text);parser.close();text=parser.text;entities=parser.entities
 occupied=[(e['offset'],e['offset']+e['length'])for e in entities if e['type']in('custom_emoji','code','pre')]
 pattern='|'.join(re.escape(x)for x in sorted(SEMANTIC_EMOJI,key=len,reverse=True))
 for match in re.finditer(pattern,text):
  offset=units(text[:match.start()]);length=units(match.group())
  if any(offset<b and offset+length>a for a,b in occupied):continue
  entities.append({'type':'custom_emoji','offset':offset,'length':length,'custom_emoji_id':SEMANTIC_EMOJI[match.group()]})
 if units(text)>limit:raise RuntimeError('caption_too_long'if limit==1024 else'message_too_long')
 return text,sorted(entities,key=lambda e:(e['offset'],-e['length']))

def format_caption(html_caption,urgent=False):
 pattern='|'.join(re.escape(x)for x in sorted(SEMANTIC_EMOJI,key=len,reverse=True))
 selected=re.match(r'^<b>('+pattern+r')\s',html_caption)
 icon='⚡️'if urgent else(selected.group(1)if selected else'📰')
 html_caption=re.sub(r'^<b>[^\w<]*','<b>'+icon+' ',html_caption,count=1)
 text,entities=format_message(html_caption,limit=1024)
 if not text.startswith(icon):raise RuntimeError('custom_emoji_anchor_missing')
 return text,entities

def verify_returned(message,expected):
 need={(e['offset'],e['length'],e['custom_emoji_id'])for e in expected if e['type']=='custom_emoji'}
 returned=message.get('caption_entities',message.get('entities',[]))
 actual={(e['offset'],e['length'],e['custom_emoji_id'])for e in returned if e['type']=='custom_emoji'}
 if not need or not need.issubset(actual):raise RuntimeError('premium_emoji_not_preserved')
 verify_formatting(message,expected)


def verify_formatting(message,expected):
 returned=message.get('caption_entities',message.get('entities',[]))
 supported={'bold','italic','underline','strikethrough','code','pre','blockquote','expandable_blockquote','spoiler'}
 # Telegram can split a bold span around a custom emoji or merge adjacent spans.
 for entity in expected:
  if entity['type']not in supported:continue
  cursor=entity['offset'];end=cursor+entity['length']
  spans=sorted((item['offset'],item['offset']+item['length'])for item in returned if item['type']==entity['type'])
  for left,right in spans:
   if left>cursor:break
   if right>cursor:cursor=right
   if cursor>=end:break
  if cursor<end:raise RuntimeError('rich_formatting_not_preserved')
