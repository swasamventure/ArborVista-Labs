#!/usr/bin/env python3
from pathlib import Path
from bs4 import BeautifulSoup
import json, re, sys

root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
fail=[]

index=root/'index.html'
if not index.exists():
    fail.append('index.html is missing')
else:
    text=index.read_text(encoding='utf-8')
    soup=BeautifulSoup(text,'html.parser')
    if 'Escape. Unwind. Reconnect. Your mountain retreat awaits.' in text:
        fail.append('redundant utility copy remains')
    if 'Direct booking coming in v4.4 · Current reservations are securely completed on Airbnb.' in text:
        fail.append('temporary hero note remains')
    if not soup.find('link',href=re.compile(r'v433-final-cleanup\.css')):
        fail.append('cleanup CSS link missing')
    if not soup.select_one('[data-airbnb-reviews-section]'):
        fail.append('What Guests Say section is missing')
    if not soup.find('script',src=re.compile(r'airbnb-reviews-v433\.js')):
        fail.append('Airbnb review loader is missing')
    if soup.select_one('.v43-review-proof'):
        fail.append('old link-only review section remains')
    if soup.select_one('#guest-reviews-title') and soup.select_one('#guest-reviews-title').get_text(strip=True)!='What Guests Say':
        fail.append('What Guests Say heading is incorrect')

required=[
    'assets/arbor-vista-logo-horizontal-v433.webp',
    'assets/v433-final-cleanup.css',
    'assets/v43.js',
    'assets/airbnb-reviews-v433.js',
    'data/airbnb-reviews.json',
    'scripts/update_airbnb_reviews.py',
    '.github/workflows/update-airbnb-reviews.yml',
]
for name in required:
    if not (root/name).exists():
        fail.append(f'{name} is missing')

data_path=root/'data'/'airbnb-reviews.json'
if data_path.exists():
    try:
        data=json.loads(data_path.read_text(encoding='utf-8'))
        if data.get('listingId')!='1587774879621242014':
            fail.append('review snapshot listing ID is incorrect')
        if not isinstance(data.get('rating'),(int,float)):
            fail.append('review snapshot rating is missing')
        if not isinstance(data.get('reviewCount'),int):
            fail.append('review snapshot count is missing')
        if not data.get('featuredReviews'):
            fail.append('featured review excerpt is missing')
    except Exception as exc:
        fail.append(f'review snapshot JSON is invalid: {exc}')

for html in root.glob('*.html'):
    text=html.read_text(encoding='utf-8')
    if 'brand-logo-v433' in text and 'assets/v43.js' not in text:
        fail.append(f'{html.name}: shared v43.js missing')

if fail:
    print('FAIL')
    for item in fail:
        print('-',item)
    raise SystemExit(1)

print('PASS — v4.3.3 final verified cleanup and What Guests Say snapshot are installed.')
