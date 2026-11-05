from playwright.sync_api import sync_playwright
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from pathlib import Path
import mimetypes
out=Path(__file__).resolve().parents[2]/'out/newsroom-captures';out.mkdir(exist_ok=True,parents=True)
# Browser lacks this machine's CA setup. Fetch through Python's verified TLS trust,
# then fulfill the browser request without disabling certificate verification.
def verified_route(route):
 u=route.request.url;p=urlparse(u);host=p.hostname or ''
 if p.scheme!='https' or not any(host==h or host.endswith('.'+h) for h in ('t.me','telegram.org','telesco.pe')):
  route.abort();return
 try:
  with urlopen(Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=12) as r:
   data=r.read(5_000_001)
   if len(data)>5_000_000:route.abort();return
   route.fulfill(status=r.status,content_type=r.headers.get('Content-Type','application/octet-stream'),body=data)
 except Exception:route.abort()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 for name,u in [('rumor','https://t.me/leonidagov/2612?embed=1'),('schedule','https://t.me/GTA6_m/9300?embed=1')]:
  page=b.new_page(viewport={'width':900,'height':1200},device_scale_factor=1)
  page.route('**/*',verified_route)
  page.goto(u,wait_until='domcontentloaded',timeout=45000)
  page.locator('.tgme_widget_message').first.screenshot(path=str(out/(name+'.png')),timeout=20000)
  print(name,page.locator('body').inner_text()[:110])
  page.close()
 b.close()
