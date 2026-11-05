from pathlib import Path
import json,html,shutil,hashlib
import http.server,threading,functools
from playwright.sync_api import sync_playwright
from PIL import Image
root=Path(__file__).resolve().parents[2];samples=root/'newsroom/samples'
assets=samples/'assets';assets.mkdir(exist_ok=True)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base='http://127.0.0.1:'+str(server.server_port)
def uri(path):return base+'/'+str(path.relative_to(root))
font=uri(assets/'Manrope-ExtraBold.ttf')
manifest=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 for index,directory in enumerate(sorted(samples.glob('0*'))):
  d=json.loads((directory/'draft.json').read_text());v=json.loads((directory/'visual.json').read_text())
  label={'fact':'ПРОВЕРЕНО','rumor':'СЛУХ','analysis':'РАЗБОР'}[d['kind']]
  media=['rockstar-official-poster.jpg','rumor-screenshot.png','schedule-screenshot.png'][index]
  color=['#c4e879','#ffba70','#c7adff'][index]
  body=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><style>
  @font-face{{font-family:Manrope;src:url('{font}')}}
  *{{box-sizing:border-box}}body{{margin:0;background:#111017;color:#f4f0ea;width:1280px;height:960px;font-family:Manrope,Arial;overflow:hidden}}
  header{{height:132px;padding:28px 54px;display:flex;align-items:center;gap:20px;border-bottom:1px solid #34313e}}header img{{width:70px;height:70px;border-radius:50%}}.brand{{font-size:27px}}.edition{{margin-left:auto;text-align:right;font-size:14px;color:#b6afc3;line-height:1.7}}
  main{{display:grid;grid-template-columns:540px 1fr;gap:35px;padding:40px 54px;height:716px}}.tag{{font-size:20px;letter-spacing:3px;color:{color};margin-bottom:30px}}h1{{font-size:49px;line-height:1.13;letter-spacing:-2px;text-transform:uppercase;margin:0 0 40px}}.accent{{font-size:51px;line-height:1.1;color:{color};margin-top:16px}}.note{{font:21px/1.5 Arial;color:#b6afc3;margin-top:38px;max-width:460px}}
  .evidence{{height:635px;display:flex;align-items:center;justify-content:center;background:#19171f;overflow:hidden;border:1px solid #3a3547}}.evidence img{{width:100%;height:100%;object-fit:{'cover' if index==0 else 'contain'};object-position:top}}
  footer{{margin:0 54px;padding-top:21px;border-top:1px solid #34313e;font:17px/1.5 Arial;color:#b6afc3;display:flex;justify-content:space-between;gap:20px}}.handle{{color:#f4f0ea;white-space:nowrap}}
  </style><header><img src="{uri(assets/'channel-avatar.jpg')}"><div class="brand">GTA6 Досье Лестера</div><div class="edition">ДОСЬЕ / 00{index+1}<br>ПРОБА СТИЛЯ · 05.11.2026</div></header><main><section><div class="tag">{label}</div><h1>{html.escape(v['title']).replace(chr(10),'<br>')}</h1><div class="accent">{v['big']}</div><div class="note">{html.escape(v['caption'])}</div></section><div class="evidence"><img src="{uri(assets/media)}"></div></main><footer><span>{'rockstargames.com/VI' if index==0 else d['source_posts'][0]['url'].replace('https://','')}<br>Материал для согласования. Не опубликован.</span><span class="handle">@lesterdossier</span></footer></html>'''
  (directory/'preview.html').write_text(body)
  page=b.new_page(viewport={'width':1280,'height':960},device_scale_factor=1)
  page.goto(uri(directory/'preview.html'));page.screenshot(path=str(directory/'image.png'))
  Image.open(directory/'image.png').convert('RGB').save(directory/'image.jpg',quality=94)
  page.close()
  (directory/'preview.html').write_text(body.replace(base+'/', '../../../'))
  d['image']={'file':f'samples/{directory.name}/image.jpg','sha256':hashlib.sha256((directory/'image.jpg').read_bytes()).hexdigest(),'role':'official_promotional_art' if index==0 else 'secondary_source_screenshot','source_url':d['source_posts'][0]['url']}
  (directory/'draft.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
  manifest.append({'sample':directory.name,'draft_hash':hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'source_url':d['image']['source_url'],'image_sha256':d['image']['sha256']})
 b.close()
(samples/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
# This file can be opened independently; all sample media/fonts are local.
parts=['<!doctype html><html lang="ru"><meta charset="utf-8"><title>Досье Лестера — три образца</title><style>body{background:#111017;color:#f4f0ea;font:20px/1.6 Arial;margin:40px auto;max-width:1080px}article{margin:50px 0;border-top:1px solid #45404d;padding-top:35px}img{width:100%}pre{white-space:pre-wrap;font:20px/1.6 Arial}a{color:#c7adff}</style><h1>Три образца редакции</h1><p>Согласование стиля · 5 ноября 2026 · ничего не опубликовано.</p>']
for directory in sorted(samples.glob('0*')):
 d=json.loads((directory/'draft.json').read_text());parts.append(f'<article><h2>{html.escape(d["title"])}</h2><img src="{directory.name}/image.jpg"><pre>{html.escape((directory/"post.md").read_text())}</pre></article>')
parts.append('</html>');(samples/'review.html').write_text(''.join(parts))
print('Three images and review page rendered locally; generated imagery: 0')
