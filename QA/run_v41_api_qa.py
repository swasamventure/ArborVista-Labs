#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
checks=[]

def check(name, condition, detail=""):
    checks.append({"name":name,"passed":bool(condition),"detail":str(detail)[:2000]})

def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1",0)); return s.getsockname()[1]

def request(url, user=None, expect_error=False):
    headers={}
    if user: headers["X-Demo-User"]=user
    req=urllib.request.Request(url,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=8) as r:
            data=r.read(); ctype=r.headers.get("content-type","")
            return r.status, data.decode("utf-8") if "text" in ctype or "json" in ctype or "calendar" in ctype else data
    except urllib.error.HTTPError as e:
        return e.code,e.read().decode("utf-8")

with tempfile.TemporaryDirectory(prefix="arbor-v41-api-") as tmp:
    p=port(); db=Path(tmp)/"api.db"
    env=os.environ.copy(); env.update({
        "PORT":str(p),"ARBOR_HOST":"127.0.0.1","ARBOR_DB_PATH":str(db),
        "ARBOR_REQUIRE_DEMO_AUTH":"1","ARBOR_ALLOWED_ORIGINS":f"http://127.0.0.1:{p}",
    })
    proc=subprocess.Popen([sys.executable,"Backend/server.py"],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    base=f"http://127.0.0.1:{p}/api/v1"
    try:
        for _ in range(80):
            try:
                status,_=request(base+"/health")
                if status==200: break
            except Exception: pass
            time.sleep(.1)
        status,body=request(base+"/health")
        health=json.loads(body)
        check("Health endpoint reports v4.1",status==200 and health.get("version")=="4.1",health)

        status,body=request(base+"/auth/me")
        check("Dashboard API requires authentication in strict mode",status==401,body)

        status,body=request(base+"/auth/me", "user_owner")
        me=json.loads(body)
        check("Portfolio owner authentication works",status==200 and me.get("id")=="user_owner",me)

        status,body=request(base+"/properties", "user_owner")
        props=json.loads(body)
        check("Owner API returns both properties",status==200 and len(props)==2,props)

        status,body=request(base+"/reservations?property=all", "user_owner")
        reservations=json.loads(body)
        check("Portfolio reservation API includes property identity",status==200 and reservations and all(r.get("property_code") for r in reservations),reservations)

        status,body=request(base+"/reservations?property=arbor-vista-retreat", "user_cleaner")
        check("Cleaner cannot access guest reservation API",status==403,body)

        status,body=request(base+"/cleaning-feed/info?property=arbor-vista-retreat", "user_cleaner")
        info=json.loads(body)
        check("Cleaner can access assigned cleaning feed information",status==200 and info.get("properties"),info)
        check("Cleaning feed info says guest names are excluded","Guest names" in info.get("privacy",""),info)

        status,feed=request(base+"/ical/cleaning.ics?token=demo-cleaner-token-change-me")
        check("Token-protected cleaning feed is served",status==200 and "BEGIN:VCALENDAR" in feed,feed[:500])
        check("Cleaning feed API excludes guest names",all(x not in feed for x in ["Jordan Smith","Taylor Jones","Jordan S.","Taylor J.","Guest:"]),feed[:1400])
        check("Cleaning feed API includes both property identities","AVR-TN-01" in feed and "DEMO-TN-02" in feed and "prop_arbor_vista" in feed and "prop_demo_smokies" in feed,feed[:1600])

        status,body=request(base+"/reports/summary?property=all&start=2027-01-01&end=2028-01-01", "user_accountant")
        report=json.loads(body)
        check("Accountant can access portfolio reporting",status==200 and report.get("portfolio",{}).get("properties")==2,report)

        status,body=request(base+"/property-export/preview?property=arbor-vista-retreat", "user_manager")
        check("Manager cannot create property sale export",status==403,body)

        status,body=request(base+"/property-export/preview?property=arbor-vista-retreat", "user_owner")
        preview=json.loads(body)
        check("Property owner can preview transfer export",status==200 and preview.get("property",{}).get("code")=="AVR-TN-01",preview)
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill()

passed=sum(c["passed"] for c in checks)
report={"version":"4.1","status":"PASS" if passed==len(checks) else "FAIL","checks_passed":passed,"checks_total":len(checks),"checks":checks}
(ROOT/"QA_REPORT_V4.1_API.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
if passed!=len(checks): raise SystemExit(1)
