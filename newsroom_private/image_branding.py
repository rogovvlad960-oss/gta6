"""Create a branded editorial graphic while preserving the source frame intact."""
from pathlib import Path
from io import BytesIO
import hashlib,re
from PIL import Image,ImageOps,ImageDraw,ImageFont
ROOT=Path(__file__).parent
INK='#0b1116';PANEL='#16272d';WHITE='#f7f7f2';AMBER='#f4c66d';LIME='#d7ed7a'
def font(size,weight=700):
 f=ImageFont.truetype(str(ROOT/'assets/Inter.ttf'),size)
 try:f.set_variation_by_axes([weight if a['name']==b'Weight'else a['default']for a in f.get_variation_axes()])
 except (OSError,ValueError):pass
 return f

def headline_lines(text,face,width):
 clean=re.sub(r'^[^\w]+','',text).strip();rows=[];line=''
 for word in clean.split():
  candidate=(line+' '+word).strip()
  if line and face.getlength(candidate)>width:rows.append(line);line=word
  else:line=candidate
 if line:rows.append(line)
 if len(rows)==2:
  words=clean.split();balanced=[]
  for split in range(1,len(words)):
   pair=[' '.join(words[:split]),' '.join(words[split:])];sizes=[face.getlength(part)for part in pair]
   if max(sizes)<=width:balanced.append((abs(sizes[0]-sizes[1]),pair))
  if balanced:rows=min(balanced,key=lambda pair:pair[0])[1]
 return rows

def brand_external_image(raw,title):
 source_hash=hashlib.sha256(raw).hexdigest()
 im=Image.open(BytesIO(raw))
 if im.width*im.height>40_000_000:raise ValueError('source_image_too_large')
 im=ImageOps.exif_transpose(im).convert('RGBA')
 solid=Image.new('RGBA',im.size,INK);solid.alpha_composite(im);im=solid.convert('RGB')
 width,height=1600,(2000 if im.height>im.width else 1400)
 canvas=Image.new('RGB',(width,height),INK);draw=ImageDraw.Draw(canvas)
 draw.rounded_rectangle((70,38,78,75),radius=3,fill=AMBER)
 draw.text((98,39),'ДОСЬЕ ЛЕСТЕРА',font=font(31,800),fill=WHITE)
 handle='@lesterdossier';hf=font(29,720);draw.text((width-80-hf.getlength(handle),40),handle,font=hf,fill=LIME)
 size=65
 while size>=38:
  tf=font(size,780);lines=headline_lines(title,tf,width-160)
  if len(lines)<=2 and all(tf.getlength(line)<=width-160 for line in lines):break
  size-=3
 if len(lines)>2 or any(tf.getlength(line)>width-160 for line in lines):raise ValueError('image_headline_too_long')
 for i,line in enumerate(lines):draw.text((80,118+i*(size+13)),line,font=tf,fill=WHITE)
 left,top,right,bottom=80,318,width-80,height-160
 draw.rounded_rectangle((left-3,top-3,right+3,bottom+3),radius=24,fill=PANEL,outline='#718e80',width=2)
 fitted=ImageOps.contain(im,(right-left,bottom-top),Image.Resampling.LANCZOS)
 x=left+(right-left-fitted.width)//2;y=top+(bottom-top-fitted.height)//2
 canvas.paste(fitted,(x,y))
 draw.line((80,height-115,width-80,height-115),fill='#3b5651',width=2)
 draw.text((80,height-78),'GTA VI  /  ДОСЬЕ ЛЕСТЕРА',font=font(25,650),fill='#b3c7bd')
 draw.text((width-80-hf.getlength(handle),height-82),handle,font=hf,fill=LIME)
 output=BytesIO();canvas.save(output,format='JPEG',quality=94,optimize=True,subsampling=0);blob=output.getvalue()
 return blob,{'style':'lesterdossier-editorial-v1','source_sha256':source_hash,'output_sha256':hashlib.sha256(blob).hexdigest(),'source_size':list(im.size),'output_size':[width,height],'source_fully_visible':True,'source_rect':[x,y,x+fitted.width,y+fitted.height],'recomposed':True}

def editorial_card(draft):
 """Curated promotional art cover, never a made-up gameplay/statistics screenshot."""
 import json
 title=str(draft['title']);subject=title+' '+str(draft['body'])
 theme='keyart'
 for pattern,name in [(r'остров|каяк|катер|водн|дайв|подвод','islands'),(r'болот|аллигатор|аэролод','swamp'),(r'горах|горы|охот|калaг|калаг','mountains'),(r'вайс.сити|аэропорт|город','city')]:
  if re.search(pattern,subject,re.I):theme=name;break
 # Hardware/FPS/port stories use the game's key art, never an invented benchmark.
 if re.search(r'\bПК\b|FPS|RTX|порт|производительност',title,re.I):theme='keyart'
 path=ROOT/'assets/covers'/(theme+'.jpg')
 art=Image.open(path).convert('RGB')
 canvas=Image.new('RGB',(1600,1400),'#0e0b17')
 fitted=ImageOps.contain(art,(1600,1070),Image.Resampling.LANCZOS)
 x=(1600-fitted.width)//2;y=76+(1070-fitted.height)//2
 canvas.paste(fitted,(x,y))
 draw=ImageDraw.Draw(canvas)
 draw.rectangle((0,0,1600,76),fill='#0e0b17')
 draw.text((58,20),'ДОСЬЕ ЛЕСТЕРА',font=font(28,800),fill='#ffffff')
 hf=font(26,700);handle='@lesterdossier';draw.text((1542-hf.getlength(handle),22),handle,font=hf,fill='#f783c8')
 draw.rectangle((58,1167,1542,1172),fill='#f783c8')
 size=64
 while size>=36:
  face=font(size,850);lines=headline_lines(title,face,1484)
  if len(lines)<=2 and all(face.getlength(line)<=1484 for line in lines):break
  size-=2
 if len(lines)>2:raise ValueError('editorial_headline_too_long')
 for i,line in enumerate(lines):draw.text((58,1190+i*(size+12)),line,font=face,fill='#ffffff')
 draw.text((58,1350),'ОБЛОЖКА: ОФИЦИАЛЬНЫЙ АРТ GTA 6',font=font(21,600),fill='#bcaec5')
 output=BytesIO();canvas.save(output,format='JPEG',quality=94,optimize=True,subsampling=0);blob=output.getvalue()
 provenance=next(x for x in json.loads((ROOT/'assets/covers/sources.json').read_text())if x['file']==theme+'.jpg')
 return blob,{'style':'lesterdossier-official-art-cover-v2','source':'official_promotional_artwork','not_gameplay':True,'not_claim_evidence':True,'asset':theme,'source_url':provenance['source_url'],'reuse_license_verified':False,'output_sha256':hashlib.sha256(blob).hexdigest(),'output_size':[1600,1400],'source_fully_visible':True,'recomposed':True,'body_text_on_image':False}
