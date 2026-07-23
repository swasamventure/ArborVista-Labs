
#!/usr/bin/env python3
from pathlib import Path
import json, sqlite3, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Backend'))
from ical_db import init_db, connect
checks=[]
def ck(name,cond): checks.append((name,bool(cond)))
ck('admin dashboard exists',(ROOT/'admin/dashboard.html').exists())
ck('admin reservations exists',(ROOT/'admin/reservations.html').exists())
ck('local API server exists',(ROOT/'Backend/server.py').exists())
ck('Stripe integration excluded','api.stripe.com' not in (ROOT/'Backend/server.py').read_text().lower() and 'stripe.checkout' not in (ROOT/'Backend/server.py').read_text().lower())
ck('Email sending excluded','resend' not in (ROOT/'Backend/server.py').read_text().lower() and 'smtp' not in (ROOT/'Backend/server.py').read_text().lower())
for i in range(1,5): ck(f'charcoal kitchen {i}',(ROOT/f'images/kitchen/arbor-vista-charcoal-kitchen-{i}.webp').exists())
for f in ['cabin.html','gallery.html']: ck(f'{f} uses charcoal images','arbor-vista-charcoal-kitchen-1.webp' in (ROOT/f).read_text())
ck('booking uses API endpoint','api/booking-requests' in (ROOT/'assets/script.js').read_text())
ck('schema has booking requests','CREATE TABLE IF NOT EXISTS booking_requests' in (ROOT/'Backend/schema.sql').read_text())
ck('schema has documents','CREATE TABLE IF NOT EXISTS documents' in (ROOT/'Backend/schema.sql').read_text())
ck('outbound ICS endpoint','/api/export.ics' in (ROOT/'Backend/server.py').read_text())
passed=sum(x for _,x in checks)
print(f'v3.2 merged QA: {passed}/{len(checks)} PASS')
for n,x in checks: print(('PASS' if x else 'FAIL'),n)
if passed!=len(checks): raise SystemExit(1)
(ROOT/'QA_REPORT_V3.2.json').write_text(json.dumps({'passed':passed,'total':len(checks),'checks':[{'name':n,'pass':x} for n,x in checks]},indent=2))
