#!/usr/bin/env python3
from pathlib import Path
import sys, tempfile, shutil, json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Backend'))
import server
from ical_db import init_db, connect, availability, export_ics

tmp=Path(tempfile.mkdtemp())/'integration.db'
server.DB=tmp
init_db(tmp,reset=True)
checks=[]
def ck(n,c,d=''): checks.append({'name':n,'pass':bool(c),'detail':str(d)})

payload={'check_in':'2027-02-10','check_out':'2027-02-13','adults':'4','children':'2','vehicles':'2','first_name':'Test','last_name':'Guest','email':'test@example.com','phone':'5125551212','legal_name':'Test Guest','electronic_signature':'Test Guest','agreement_date':'2026-07-23','special_requests':'QA'}
r=server.create_booking(payload)
ck('Direct request saved to database',r['status']=='pending',r)
with connect(tmp) as c:
    ck('Booking request row created',c.execute('select count(*) from booking_requests').fetchone()[0]==1)
    ck('Guest row created',c.execute('select count(*) from guests').fetchone()[0]==1)
    ck('Signed document row created',c.execute('select count(*) from documents').fetchone()[0]==1)
    n=c.execute("select * from notification_log").fetchone()
    ck('Email explicitly disabled',n['status']=='disabled' and n['recipient']=='swasam.venture@gmail.com',dict(n))
a=availability('prop_arbor_vista','2027-02-11','2027-02-12',db_path=tmp)
ck('Pending request blocks availability',not a['available'],a)
try:
    server.create_booking(payload); duplicate=False
except ValueError: duplicate=True
ck('Overlapping request rejected',duplicate)
try:
    p=dict(payload);p['check_in']='2027-03-01';p['check_out']='2027-03-03';p['adults']='7';p['children']='2';server.create_booking(p); over=False
except ValueError: over=True
ck('More than eight guests rejected',over)
p=dict(payload);p['check_in']='2027-03-01';p['check_out']='2027-03-03';p['adults']='6';p['children']='2';r2=server.create_booking(p)
ck('Eight-guest request accepted',r2['status']=='pending',r2)
out=tmp.parent/'out.ics'; count=export_ics(out,db_path=tmp)
ck('Outbound iCal generated',count>=2 and 'BEGIN:VCALENDAR' in out.read_text(),count)
passed=sum(x['pass'] for x in checks)
report={'version':'3.2','passed':passed,'total':len(checks),'status':'PASS' if passed==len(checks) else 'FAIL','checks':checks}
(ROOT/'QA_REPORT_V3.2_INTEGRATION.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
if report['status']!='PASS': raise SystemExit(1)
