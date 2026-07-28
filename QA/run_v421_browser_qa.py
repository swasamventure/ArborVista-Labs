from pathlib import Path
import json, re
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
ADMIN=ROOT/'admin'
checks=[]
def ck(name,ok,detail=''): checks.append((name,bool(ok),str(detail)))
html=(ADMIN/'market-intelligence.html').read_text()
admin_css=(ADMIN/'admin.css').read_text()
market_css=(ADMIN/'market-intelligence.css').read_text()
data_js=(ADMIN/'data/market-intelligence-real-snapshot.js').read_text()
app_js=(ADMIN/'market-intelligence.js').read_text()
html=re.sub(r'<link rel="stylesheet" href="admin.css\?v=4\.2\.1">\s*<link rel="stylesheet" href="market-intelligence.css\?v=4\.2\.1">',lambda _:f'<style>{admin_css}\n{market_css}</style>',html)
html=html.replace('<script src="../config/runtime-config.js"></script>','')
html=re.sub(r'<script src="data/market-intelligence-real-snapshot.js\?v=4\.2\.1"></script>\s*<script src="market-intelligence.js\?v=4\.2\.1"></script>',lambda _:f'<script>{data_js}</script><script>{app_js}</script>',html)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
    errors=[]
    page.on('console',lambda m: errors.append(f'{m.type}: {m.text}') if m.type=='error' else None)
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.set_content(html,wait_until='load')
    page.wait_for_selector('#miSummaryMetrics article')
    ck('Six metadata summary cards',page.locator('#miSummaryMetrics article').count()==6,page.locator('#miSummaryMetrics article').count())
    ck('83 public comp rows',page.locator('#miCompTable tbody tr').count()==83,page.locator('#miCompTable tbody tr').count())
    body=page.locator('body').inner_text()
    ck('Three platforms represented',all(x in body for x in ['Airbnb','Vrbo','Booking.com']))
    ck('Observation plan renders',page.locator('#miObservationPlan tbody tr').count()==8,page.locator('#miObservationPlan tbody tr').count())
    ck('Metadata charts render',page.locator('svg.market-chart').count()>=4,page.locator('svg.market-chart').count())
    ck('No browser JavaScript errors',not errors,errors)
    ck('Real snapshot label visible','Real Comp Snapshot' in body)
    ck('No performance claims for metadata-only records','No performance claim' in page.locator('#miCompTable').inner_text())
    with page.expect_download() as dl: page.click('#miExportAnalysis')
    ck('Analysis CSV downloads',dl.value.suggested_filename.endswith('market-analysis.csv'),dl.value.suggested_filename)
    (ROOT/'QA/screenshots').mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(ROOT/'QA/screenshots/market-intelligence-v421-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.set_content(html,wait_until='load')
    page.wait_for_selector('#miSummaryMetrics article')
    ck('Mobile page renders',page.locator('#miCompTable tbody tr').count()==83)
    page.screenshot(path=str(ROOT/'QA/screenshots/market-intelligence-v421-mobile.png'),full_page=True)
    browser.close()
passed=sum(x[1] for x in checks)
print(f'{passed}/{len(checks)} browser checks passed')
for x in checks:
    if not x[1]: print('FAIL',x[0],x[2])
(ROOT/'QA_REPORT_V4.2.1_BROWSER.json').write_text(json.dumps({'status':'PASS' if passed==len(checks) else 'FAIL','checks_passed':passed,'checks_total':len(checks),'checks':[{'name':n,'passed':ok,'detail':d} for n,ok,d in checks]},indent=2))
raise SystemExit(0 if passed==len(checks) else 1)
