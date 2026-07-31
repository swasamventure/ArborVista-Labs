from pathlib import Path
from bs4 import BeautifulSoup
import json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=['index.html','cabin.html','gallery.html','explore.html','plan.html','faq.html','welcome.html','book-direct.html','rental-agreement.html','404.html']
checks=[]
def ck(name,ok,detail=''): checks.append({'name':name,'passed':bool(ok),'detail':str(detail)})
for name in PUBLIC:
    s=BeautifulSoup((ROOT/name).read_text(encoding='utf-8'),'html.parser')
    ck(f'{name}: shared logo header',bool(s.select_one('header .brand-lockup')))
    ck(f'{name}: skip link',bool(s.select_one('.skip-link')))
    ck(f'{name}: v4.3.2 stylesheet',bool(s.find('link',href=lambda x:x and 'style-v43.css?v=4.3.2' in x)))
    ck(f'{name}: analytics placeholder',bool(s.find('script',src=lambda x:x and 'analytics-v432.js?v=4.3.2' in x)))
    ck(f'{name}: direct booking path',bool(s.find('a',href='book-direct.html')))
    if name!='book-direct.html': ck(f'{name}: sticky availability CTA',bool(s.select_one('a.sticky-book[href="book-direct.html"]')))
for name in ['index.html','cabin.html','explore.html']:
    s=BeautifulSoup((ROOT/name).read_text(encoding='utf-8'),'html.parser')
    rots=s.select('[data-v43-rotator]')
    ck(f'{name}: has stabilized rotator',len(rots)>=1,len(rots))
    ck(f'{name}: all rotators use 3000ms',all(r.get('data-delay')=='3000' for r in rots))
    ck(f'{name}: one active slide per rotator',all(len(r.select('.is-active[data-rotator-slide]'))==1 for r in rots))
s=BeautifulSoup((ROOT/'gallery.html').read_text(encoding='utf-8'),'html.parser')
ck('Gallery uses one image element',len(s.select('[data-v432-gallery] img[data-gallery-image]'))==1,len(s.select('img')))
ck('Gallery data retains full collection',len(json.loads(s.select_one('#v432GalleryData').string))>=40,len(json.loads(s.select_one('#v432GalleryData').string)))
ck('Explore no multi-image photo grid',not bool(BeautifulSoup((ROOT/'explore.html').read_text(),'html.parser').select_one('.photo-gallery.three-col')))
idx=BeautifulSoup((ROOT/'index.html').read_text(),'html.parser')
ck('Homepage uses no masonry or three-column photo gallery',not bool(idx.select_one('.masonry,.photo-gallery.three-col')))
ck('Only two approved kitchen images referenced outside gallery', 'arbor-vista-charcoal-kitchen-3' not in '\n'.join((ROOT/x).read_text(errors='ignore') for x in PUBLIC) and 'arbor-vista-charcoal-kitchen-4' not in '\n'.join((ROOT/x).read_text(errors='ignore') for x in PUBLIC))
js=(ROOT/'assets/v43.js').read_text()
ck('Rotator supports keyboard arrows',"ArrowLeft" in js and "ArrowRight" in js)
ck('Rotator supports pause/play','toggleUserPause' in js)
ck('Rotator supports swipe','touchstart' in js and 'touchend' in js)
ck('Rotator respects reduced motion','prefers-reduced-motion' in js)
analytics=(ROOT/'assets/analytics-v432.js').read_text()
ck('Analytics excludes common PII fields','email|phone|address|message|signature' in analytics)

for jsfile in ['assets/v43.js','assets/gallery-v432.js','assets/analytics-v432.js']:
    result=subprocess.run(['node','--check',str(ROOT/jsfile)],capture_output=True,text=True)
    ck(f'{jsfile}: JavaScript syntax',result.returncode==0,result.stderr)

ck('Sitemap includes all public URLs',all(('https://arborvistaretreat.com/'+('' if x=='index.html' else x)) in (ROOT/'sitemap.xml').read_text() for x in PUBLIC if x!='404.html'))
passed=sum(x['passed'] for x in checks)
report={'version':'4.3.2','status':'PASS' if passed==len(checks) else 'FAIL','checks_passed':passed,'checks_total':len(checks),'checks':checks}
(ROOT/'QA_REPORT_V4.3.2_STATIC.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['status']=='PASS' else 1)
