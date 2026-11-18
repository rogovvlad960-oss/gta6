"""Inline premium emoji for the verified private bot delivery, using UTF-16 offsets."""
import re
from html.parser import HTMLParser
LOGO='5282847372223740079'
LIGHTNING='5222430393688432601'
def units(text):return len(text.encode('utf-16-le'))//2
class CaptionParser(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.text='';self.entities=[];self.bold=[]
 def handle_starttag(self,tag,attrs):
  if tag=='b':self.bold.append(units(self.text))
 def handle_endtag(self,tag):
  if tag=='b'and self.bold:
   start=self.bold.pop();self.entities.append({'type':'bold','offset':start,'length':units(self.text)-start})
 def handle_data(self,data):self.text+=data

def format_caption(html_caption,urgent=False):
 icon='⚡️'if urgent else '📰'
 html_caption=re.sub(r'^<b>[^\w<]*','<b>'+icon+' ',html_caption,count=1)
 parser=CaptionParser();parser.feed(html_caption);parser.close();text=parser.text
 if not text.startswith(icon):raise RuntimeError('custom_emoji_anchor_missing')
 entities=parser.entities+[{'type':'custom_emoji','offset':0,'length':units(icon),'custom_emoji_id':LIGHTNING if urgent else LOGO}]
 for match in re.finditer('⚡️?',text):
  offset=units(text[:match.start()])
  if offset==0:continue
  entities.append({'type':'custom_emoji','offset':offset,'length':units(match.group()),'custom_emoji_id':LIGHTNING})
 if units(text)>1024:raise RuntimeError('caption_too_long')
 return text,sorted(entities,key=lambda e:e['offset'])

def verify_returned(message,expected):
 need={(e['offset'],e['length'],e['custom_emoji_id'])for e in expected if e['type']=='custom_emoji'}
 actual={(e['offset'],e['length'],e['custom_emoji_id'])for e in message.get('caption_entities',[])if e['type']=='custom_emoji'}
 if not need or not need.issubset(actual):raise RuntimeError('premium_emoji_not_preserved')
