"""Deterministic editorial cards from existing approved artwork. No generative API."""
from pathlib import Path
import hashlib
import json
import re
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent
MONTH=r'января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря'

def date_facts(body, title=""):
    result=[]
    for m in re.finditer(r'\b([0-3]?\d)\s+('+MONTH+r')(?:\s+(20\d\d))?',body,re.I):
        before=body[max(0,m.start()-100):m.start()]
        labels=list(re.finditer(r'предзагруз|релиз|выход|выйдет|запуск',before,re.I))
        label='ДАТА'
        if not labels and 'предзагруз' in title.lower() and re.search('скачив',before,re.I):label='ПРЕДЗАГРУЗКА'
        if labels:label='ПРЕДЗАГРУЗКА' if labels[-1].group(0).lower().startswith('предзагруз') else 'ВЫХОД ИГРЫ'
        value=m.group(0).upper()
        if (label,value) not in result:result.append((label,value))
    return result[:2]

def render_card(draft, sequence=1, output=None):
    image=Image.open(ROOT/'samples/01-fact/image.jpg').convert('RGB')
    draw=ImageDraw.Draw(image);width,height=image.size
    # Reuse the approved presenter and art, replace only the information areas.
    draw.rectangle((0,0,width,88),fill='#111017')
    draw.rectangle((0,115,665,514),fill='#111017')
    font_path=ROOT/'samples/assets/Manrope-ExtraBold.ttf'
    font=lambda size:ImageFont.truetype(str(font_path),size)
    draw.text((140,25),'GTA6 Досье Лестера',font=font(36),fill='#f5f1eb')
    tag=f'ДОСЬЕ / {sequence:03}'
    draw.text((width-55-draw.textlength(tag,font=font(23)),32),tag,font=font(23),fill='#bfb8ca')
    logo=Image.open(ROOT/'emoji/assets/5312273060752039273.png').convert('RGBA')
    logo.thumbnail((72,64));image.paste(logo,(54,18),logo)
    def wrapped(text,f,max_width):
        lines=[];line=''
        for word in re.findall(r'GTA\s+VI|\S+',text):
            trial=(line+' '+word).strip()
            if line and draw.textlength(trial,font=f)>max_width:lines.append(line);line=word
            else:line=trial
        if line:lines.append(line)
        return lines
    title=draft['title'].upper();facts=date_facts(draft['body'],draft['title'])
    for size in range(50,23,-2):
        f=font(size);lines=wrapped(title,f,585)
        if len(lines)*(size+9) <= (185 if facts else 285) and len(lines) <= (2 if len(title)<85 else 4):break
    if len(lines)>4:
        lines=lines[:4]
        while draw.textlength(lines[-1]+'…',font=f)>585:lines[-1]=lines[-1][:-1]
        lines[-1]+='…'
    y=137
    for line in lines:draw.text((58,y),line,font=f,fill='#f7f4ed');y+=size+9
    y=max(y+17,333 if facts else y+17)
    if facts:
        for label,value in facts:
            draw.line((62,y,62,y+72),fill='#c4e879',width=5)
            draw.text((83,y-4),label,font=font(23),fill='#f4f0e8')
            vf=font(43)
            while draw.textlength(value,font=vf)>550:vf=font(vf.size-2)
            draw.text((83,y+23),value,font=vf,fill='#c4e879');y+=91
    else:
        label={'fact':'ПРОВЕРЕНО','analysis':'РАЗБОР','rumor':'СЛУХ'}.get(draft['kind'],'ДОСЬЕ')
        draw.text((58,min(y,460)),label,font=font(32),fill='#c4e879')
    key=hashlib.sha256(json.dumps({'title':draft['title'],'body':draft['body'],'sequence':sequence},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    path=Path(output) if output else ROOT/'runtime/cards'/f'{key}.jpg'
    path.parent.mkdir(parents=True,exist_ok=True);image.save(path,quality=92,optimize=True)
    return {'file':str(path.resolve().relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'role':'author_illustration','public_sources_hidden':True,'emoji_pack_graphics':True,'template':'approved-lester-v1'}
