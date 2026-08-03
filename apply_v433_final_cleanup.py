#!/usr/bin/env python3
from pathlib import Path
from bs4 import BeautifulSoup
import re, shutil, sys

root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
patch=Path(__file__).resolve().parent
assets=root/'assets'
assets.mkdir(parents=True,exist_ok=True)

for name in [
    'arbor-vista-logo-horizontal-v433.png',
    'arbor-vista-logo-horizontal-v433.webp',
    'v433-final-cleanup.css',
    'v43.js',
]:
    shutil.copy2(patch/'assets'/name,assets/name)

changed=0
for html_path in sorted(root.glob('*.html')):
    soup=BeautifulSoup(html_path.read_text(encoding='utf-8'),'html.parser')
    if html_path.name=='index.html':
        for selector in ['.av-utility','.av-hero-note']:
            for node in soup.select(selector):
                node.decompose()
    if soup.head and not soup.head.find('link',attrs={'href':re.compile(r'v433-final-cleanup\.css')}):
        link=soup.new_tag('link',rel='stylesheet',href='assets/v433-final-cleanup.css?v=4.3.3-final-verified')
        v43=soup.head.find('link',attrs={'href':re.compile(r'style-v43\.css')})
        (v43.insert_after(link) if v43 else soup.head.append(link))
    for lockup in soup.select('.brand-logo-v433'):
        classes=list(lockup.get('class',[]))
        if 'brand-logo-horizontal' not in classes:
            classes.append('brand-logo-horizontal')
        lockup['class']=classes
        img=lockup.find('img')
        if not img:
            continue
        img['src']='assets/arbor-vista-logo-horizontal-v433.webp?v=4.3.3-final-verified'
        img['width']='1200'
        img['height']='281'
    for script in soup.find_all('script',src=True):
        if re.search(r'assets/v43\.js',script['src']):
            script['src']='assets/v43.js?v=4.3.3-final-verified'
    html_path.write_text('<!DOCTYPE html>\n'+str(soup),encoding='utf-8')
    changed+=1

print(f'Applied v4.3.3 final visual cleanup to {changed} HTML files.')
