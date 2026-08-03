#!/usr/bin/env python3
from pathlib import Path
from bs4 import BeautifulSoup, Doctype
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
    'airbnb-reviews-v433.js',
]:
    shutil.copy2(patch/'assets'/name,assets/name)

(root/'data').mkdir(parents=True,exist_ok=True)
shutil.copy2(patch/'data'/'airbnb-reviews.json',root/'data'/'airbnb-reviews.json')

(root/'scripts').mkdir(parents=True,exist_ok=True)
shutil.copy2(patch/'scripts'/'update_airbnb_reviews.py',root/'scripts'/'update_airbnb_reviews.py')

(root/'.github'/'workflows').mkdir(parents=True,exist_ok=True)
shutil.copy2(
    patch/'.github'/'workflows'/'update-airbnb-reviews.yml',
    root/'.github'/'workflows'/'update-airbnb-reviews.yml'
)

review_markup='<section aria-labelledby="guest-reviews-title" class="v433-guest-reviews" data-airbnb-reviews-section="">\n<div class="container">\n<div class="v433-reviews-heading">\n<div>\n<p class="v43-kicker dark-kicker">Verified Airbnb feedback</p>\n<h2 id="guest-reviews-title">What Guests Say</h2>\n<p>Current rating highlights and the featured guest excerpt are loaded from a locally stored Airbnb review snapshot.</p>\n</div>\n<div aria-label="Airbnb rating summary" class="v433-rating-summary">\n<span class="v433-rating-number" data-airbnb-rating="">4.82</span>\n<span aria-hidden="true" class="v433-rating-stars">★★★★★</span>\n<strong><span data-airbnb-review-count="">11</span> Airbnb reviews</strong>\n<small data-airbnb-guest-favorite="">Guest favorite</small>\n</div>\n</div>\n<div class="v433-review-grid">\n<article class="v433-review-card v433-review-card-featured">\n<div aria-label="5 out of 5 stars" class="v433-review-stars">★★★★★</div>\n<blockquote data-airbnb-featured-review="">“Extremely clean and cozy, private, with a pristine hot tub and all the listed amenities.”</blockquote>\n<p data-airbnb-featured-label="">Verified Airbnb guest excerpt</p>\n</article>\n<article class="v433-review-card">\n<p class="v433-review-label">Top category ratings</p>\n<div class="v433-category-ratings">\n<span><b data-airbnb-communication="">5.0</b> Communication</span>\n<span><b data-airbnb-cleanliness="">4.9</b> Cleanliness</span>\n<span><b data-airbnb-accuracy="">4.9</b> Accuracy</span>\n<span><b data-airbnb-checkin="">4.9</b> Check-in</span>\n</div>\n</article>\n<article class="v433-review-card">\n<p class="v433-review-label">Guests frequently mention</p>\n<div class="v433-review-themes" data-airbnb-review-themes="">\n<span>Hospitality</span>\n<span>Cleanliness</span>\n<span>Comfort</span>\n<span>Location</span>\n<span>Hot tub</span>\n</div>\n<p class="v433-five-star"><b data-airbnb-five-star="">91%</b> of reviews are five-star ratings.</p>\n</article>\n</div>\n<div class="v433-reviews-footer">\n<a class="v43-button v43-button-dark" data-airbnb-reviews-link="" href="https://www.airbnb.com/rooms/1587774879621242014#reviews" rel="noopener" target="_blank">Read all reviews on Airbnb</a>\n<p>Airbnb snapshot last checked <time data-airbnb-last-checked="" datetime="2026-08-03">August 3, 2026</time>.</p>\n</div>\n</div>\n</section>'

changed=0
for html_path in sorted(root.glob('*.html')):
    soup=BeautifulSoup(html_path.read_text(encoding='utf-8'),'html.parser')

    if html_path.name=='index.html':
        for selector in ['.av-utility','.av-hero-note']:
            for node in soup.select(selector):
                node.decompose()

        existing=soup.select_one('.v43-review-proof, .v433-guest-reviews')
        replacement=BeautifulSoup(review_markup,'html.parser')
        if existing:
            existing.replace_with(replacement)
        elif soup.main:
            soup.main.append(replacement)

        if not soup.find('script',src=re.compile(r'airbnb-reviews-v433\.js')):
            reviews_script=soup.new_tag(
                'script',
                src='assets/airbnb-reviews-v433.js?v=4.3.3-final-verified-reviews'
            )
            v43=soup.find('script',src=re.compile(r'assets/v43\.js'))
            (v43.insert_after(reviews_script) if v43 else soup.body.append(reviews_script))

    if soup.head and not soup.head.find('link',attrs={'href':re.compile(r'v433-final-cleanup\.css')}):
        link=soup.new_tag(
            'link',
            rel='stylesheet',
            href='assets/v433-final-cleanup.css?v=4.3.3-final-verified-reviews'
        )
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
        img['src']='assets/arbor-vista-logo-horizontal-v433.webp?v=4.3.3-final-verified-reviews'
        img['width']='1200'
        img['height']='281'

    for script in soup.find_all('script',src=True):
        if re.search(r'assets/v43\.js',script['src']):
            script['src']='assets/v43.js?v=4.3.3-final-verified-reviews'

    for item in list(soup.contents):
        if isinstance(item, Doctype):
            item.extract()
    text='<!DOCTYPE html>\n'+str(soup).lstrip()
    html_path.write_text(text,encoding='utf-8')
    changed+=1

print(f'Applied v4.3.3 final cleanup and What Guests Say snapshot to {changed} HTML files.')
