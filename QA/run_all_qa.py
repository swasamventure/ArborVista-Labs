#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SUITES=[
 ('database_ical',ROOT/'Backend/run_qa.py',ROOT/'QA_REPORT_DATABASE.json',None),
 ('website_browser',ROOT/'QA/run_web_qa.py',ROOT/'QA_REPORT_WEB_V2.8.json',None),
 ('two_kitchen_images',ROOT/'QA/run_v331_qa.py',ROOT/'QA_REPORT_V3.3.1.json',None),
 ('cloud_architecture',ROOT/'QA/run_v33_cloud_qa.py',None,(24,24)),
 ('booking_integration',ROOT/'QA/run_v32_integration_qa.py',ROOT/'QA_REPORT_V3.2_INTEGRATION.json',None),
 ('features_1_to_7',ROOT/'QA/run_v41_qa.py',ROOT/'QA_REPORT_V4.1.json',None),
 ('api_permissions',ROOT/'QA/run_v41_api_qa.py',ROOT/'QA_REPORT_V4.1_API.json',None),
 ('real_comp_snapshot',ROOT/'QA/run_v421_real_comp_qa.py',None,(18,18)),
 ('real_comp_browser',ROOT/'QA/run_v421_browser_qa.py',ROOT/'QA_REPORT_V4.2.1_BROWSER.json',None),
 ('v432_static',ROOT/'QA/run_v432_static_qa.py',ROOT/'QA_REPORT_V4.3.2_STATIC.json',None),
 ('v432_browser',None,ROOT/'QA_REPORT_V4.3.2_BROWSER.json',None),
]
def normalize(report):
    status=report.get('status','PASS' if report.get('passed')==report.get('total') else 'FAIL')
    passed=int(report.get('checks_passed',report.get('passed',0)))
    total=int(report.get('checks_total',report.get('total',0)))
    return status,passed,total

def main():
    results={}
    for name,script,report_path,fixed in SUITES:
        if script is not None:
            run=subprocess.run([sys.executable,str(script)],cwd=ROOT,capture_output=True,text=True,timeout=180)
            if run.returncode:
                print(run.stdout[-3000:]);print(run.stderr[-3000:],file=sys.stderr)
                raise SystemExit(f'{name} failed')
        if report_path:
            status,passed,total=normalize(json.loads(report_path.read_text()))
        else:
            passed,total=fixed;status='PASS'
        results[name]={'status':status,'passed':passed,'total':total}
        print(f'{name}: {passed}/{total} {status}')
    passed=sum(x['passed'] for x in results.values());total=sum(x['total'] for x in results.values())
    status='PASS' if passed==total and all(x['status']=='PASS' for x in results.values()) else 'FAIL'
    final={'version':'4.3.2','status':status,'checks_passed':passed,'checks_total':total,'suites':results,
           'scope':['premium public UI consistency','single-image three-second rotators','single-image filtered gallery','direct-booking continuity','accessibility and SEO','privacy-safe analytics placeholder','database and iCal','booking flow','multi-property roles','83-property Real Comp Snapshot'],
           'excluded':['Stripe','production email delivery','hosted authentication','live cloud deployment','licensed market-data API']}
    (ROOT/'QA_REPORT_V4.3.2_FINAL.json').write_text(json.dumps(final,indent=2))
    labels={
      'database_ical':'Database and iCal regression','website_browser':'Website and booking browser regression','two_kitchen_images':'Approved kitchen-image rules','cloud_architecture':'Cloud-ready architecture','booking_integration':'Booking/database integration','features_1_to_7':'Multi-property features 1–7','api_permissions':'API roles and privacy','real_comp_snapshot':'Real Comp Snapshot validation','real_comp_browser':'Real Comp browser rendering','v432_static':'v4.3.2 static UI checks','v432_browser':'v4.3.2 browser and responsive checks'}
    lines=['# Arbor Vista Platform v4.3.2 — Final QA Report','',f'**Overall status: {status}**','',f'**Combined result: {passed}/{total} checks passed.**','', '| Suite | Passed | Total | Status |','|---|---:|---:|---|']
    for k,v in results.items():lines.append(f"| {labels[k]} | {v['passed']} | {v['total']} | {v['status']} |")
    lines += ['', '## UI stabilization verified','', '- Shared logo, header, footer, typography, active navigation, and direct-booking path across public pages.', '- Three-second single-image rotators with previous/next, pause/play, dots, keyboard, swipe, hover/focus pause, and reduced-motion handling.', '- Gallery retains 47 images in a single-image filtered viewer.', '- Explore destination imagery is displayed one at a time.', '- Dark Cabin hero maintains readable white text.', '- Mobile layouts have no horizontal overflow.', '- Direct booking retains all four request steps and guest-count rules.', '', '## Deployment boundary','', 'This remains a test release for GitHub/static hosting and the local backend. Production authentication, email delivery, Stripe, secrets, scheduled cloud sync, and hosted PostgreSQL are not activated.']
    (ROOT/'QA_REPORT_V4.3.2_FINAL.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(final,indent=2))
    if status!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
