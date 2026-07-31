from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json,base64,mimetypes,re,io
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def ck(name,ok,detail=''):checks.append({'name':name,'passed':bool(ok),'detail':str(detail)})

_DATA_CACHE={}
def data_uri(path:Path):
    key=str(path)
    if key in _DATA_CACHE:return _DATA_CACHE[key]
    mime=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    if mime.startswith('image/') and path.suffix.lower() not in ['.svg']:
        with Image.open(path) as im:
            im.thumbnail((900,700))
            if im.mode not in ('RGB','L'):im=im.convert('RGB')
            buf=io.BytesIO();im.save(buf,format='JPEG',quality=68,optimize=True)
            value='data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()
    else:
        value=f'data:{mime};base64,'+base64.b64encode(path.read_bytes()).decode()
    _DATA_CACHE[key]=value
    return value

def inline_css(text:str, base:Path):
    def repl(m):
        raw=m.group(1).strip().strip('"\'')
        clean=raw.split('?',1)[0]
        if raw.startswith(('data:','http:','https:','#')): return m.group(0)
        p=(base/clean).resolve()
        if p.exists(): return f'url("{data_uri(p)}")'
        return m.group(0)
    return re.sub(r'url\(([^)]+)\)',repl,text)

def render_html(name:str):
    path=ROOT/name
    soup=BeautifulSoup(path.read_text(encoding='utf-8'),'html.parser')
    # Remove external font links.
    for link in list(soup.find_all('link',href=True)):
        href=link['href']
        if href.startswith('https://'):
            link.decompose();continue
        if link.get('rel') and 'stylesheet' in link.get('rel'):
            local=(ROOT/href.split('?',1)[0]).resolve()
            if local.exists():
                style=soup.new_tag('style');style.string=inline_css(local.read_text(encoding='utf-8'),local.parent);link.replace_with(style)
    # Inline scripts.
    for sc in list(soup.find_all('script',src=True)):
        src=sc['src']
        if src.startswith(('http:','https:')): sc.decompose();continue
        local=(ROOT/src.split('?',1)[0]).resolve()
        if local.exists():
            sc2=soup.new_tag('script');sc2.string=local.read_text(encoding='utf-8');sc.replace_with(sc2)
    # Inline direct img sources and deferred data-src.
    for img in soup.find_all('img'):
        for attr in ['src','data-src']:
            val=img.get(attr)
            if val and not val.startswith('data:'):
                local=(ROOT/val.split('?',1)[0]).resolve()
                if local.exists(): img[attr]=data_uri(local)
    # Inline gallery JSON image paths.
    data=soup.select_one('#v432GalleryData')
    if data and data.string:
        items=json.loads(data.string)
        for item in items:
            local=(ROOT/item['src'].split('?',1)[0]).resolve()
            if local.exists(): item['src']=data_uri(local)
        data.string=json.dumps(items).replace('</','<\\/')
    return str(soup)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    shots=ROOT/'QA/screenshots';shots.mkdir(parents=True,exist_ok=True)
    all_errors=[]
    def open_page(name, viewport={'width':1440,'height':1000}):
        page=browser.new_page(viewport=viewport)
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.set_content(render_html(name),wait_until='load')
        page.wait_for_timeout(450)
        all_errors.extend([f'{name}: {e}' for e in errors])
        return page

    page=open_page('index.html')
    ck('Homepage logo visible',page.locator('header .brand-lockup').is_visible())
    ck('Homepage direct booking visible',page.locator('a[href="book-direct.html"]').count()>=3,page.locator('a[href="book-direct.html"]').count())
    rot=page.locator('[data-v43-rotator]').first
    ck('Homepage rotator visible',rot.is_visible())
    first=rot.locator('[data-rotator-slide].is-active h3').inner_text()
    page.wait_for_timeout(3300)
    active_text=rot.locator('[data-rotator-slide].is-active h3').inner_text()
    ck('Homepage rotates after three seconds',first!=active_text,(first,active_text))
    pause=rot.locator('.v432-rotator-pause')
    ck('Pause button injected',pause.count()==1,pause.count())
    pause.click();ck('Pause button toggles',pause.get_attribute('aria-pressed')=='true',pause.get_attribute('aria-pressed'))
    page.screenshot(path=str(shots/'home-v432-desktop.png'),full_page=True);page.close()

    page=open_page('cabin.html')
    color=page.locator('.cabin-v43-hero h1').evaluate("el=>getComputedStyle(el).color")
    ck('Cabin hero heading is white',color in ['rgb(255, 255, 255)','rgba(255, 255, 255, 1)'],color)
    ck('Cabin has two rotators',page.locator('[data-v43-rotator]').count()==2,page.locator('[data-v43-rotator]').count())
    page.screenshot(path=str(shots/'cabin-v432-desktop.png'),full_page=True);page.close()

    page=open_page('explore.html')
    ck('Explore has one destination rotator',page.locator('.v432-destination-rotator').count()==1)
    ck('Explore has no three-column image grid',page.locator('.photo-gallery.three-col').count()==0)
    page.screenshot(path=str(shots/'explore-v432-desktop.png'),full_page=True);page.close()

    page=open_page('gallery.html')
    ck('Gallery shows one image',page.locator('.v432-gallery-stage img').count()==1)
    first=page.locator('[data-gallery-caption]').inner_text();page.wait_for_timeout(3300);second=page.locator('[data-gallery-caption]').inner_text()
    ck('Gallery rotates after three seconds',first!=second,(first,second))
    page.locator('[data-gallery-filter]').nth(1).click();page.wait_for_timeout(300)
    ck('Gallery filter works',page.locator('[data-gallery-counter]').inner_text().strip()!='')
    page.screenshot(path=str(shots/'gallery-v432-desktop.png'),full_page=True);page.close()

    page=open_page('book-direct.html')
    ck('Four booking navigation steps remain',page.locator('[data-step-nav]').count()==4,page.locator('[data-step-nav]').count())
    ck('Booking form remains present',page.locator('#bookingFlow').count()==1)
    page.screenshot(path=str(shots/'book-direct-v432-desktop.png'),full_page=True);page.close()

    page=open_page('index.html',{'width':390,'height':844})
    ck('Mobile sticky availability visible',page.locator('.sticky-book').is_visible())
    ck('Mobile body has no horizontal overflow',page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1'))
    page.screenshot(path=str(shots/'home-v432-mobile.png'),full_page=True);page.close()
    page=open_page('gallery.html',{'width':390,'height':844})
    ck('Mobile gallery has no horizontal overflow',page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1'))
    page.screenshot(path=str(shots/'gallery-v432-mobile.png'),full_page=True);page.close()
    ck('No page JavaScript errors',not all_errors,all_errors)
    browser.close()
passed=sum(x['passed'] for x in checks)
report={'version':'4.3.2','status':'PASS' if passed==len(checks) else 'FAIL','checks_passed':passed,'checks_total':len(checks),'checks':checks}
(ROOT/'QA_REPORT_V4.3.2_BROWSER.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['status']=='PASS' else 1)
