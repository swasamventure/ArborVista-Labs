#!/usr/bin/env python3
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
import sys, re
root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
fail=[]
index=root/'index.html'
if not index.exists(): fail.append('index.html is missing')
else:
    text=index.read_text(encoding='utf-8')
    soup=BeautifulSoup(text,'html.parser')
    if 'Escape. Unwind. Reconnect. Your mountain retreat awaits.' in text: fail.append('redundant utility copy remains')
    if 'Direct booking coming in v4.4 · Current reservations are securely completed on Airbnb.' in text: fail.append('temporary hero note remains')
    if not soup.find('link',href=re.compile(r'v433-final-cleanup\.css')): fail.append('cleanup CSS link missing')
for name in ['assets/arbor-vista-logo-horizontal-v433.webp','assets/v433-final-cleanup.css','assets/v43.js']:
    if not (root/name).exists(): fail.append(f'{name} is missing')
for html in root.glob('*.html'):
    text=html.read_text(encoding='utf-8')
    if 'brand-logo-v433' in text and 'assets/v43.js' not in text: fail.append(f'{html.name}: shared v43.js missing')
if fail:
    print('FAIL')
    for item in fail: print('-',item)
    raise SystemExit(1)
print('PASS — v4.3.3 final verified logo cleanup is installed.')
