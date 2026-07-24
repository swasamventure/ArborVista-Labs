from pathlib import Path
import subprocess, json
ROOT = Path(__file__).resolve().parents[1]
checks=[]
def check(name, cond, detail=''):
    checks.append({'name':name,'passed':bool(cond),'detail':str(detail)})
k=ROOT/'images'/'kitchen'
check('Kitchen image 1 exists',(k/'arbor-vista-charcoal-kitchen-1.webp').exists())
check('Kitchen image 2 exists',(k/'arbor-vista-charcoal-kitchen-2.webp').exists())
check('Kitchen image 3 removed',not (k/'arbor-vista-charcoal-kitchen-3.webp').exists())
check('Kitchen image 4 removed',not (k/'arbor-vista-charcoal-kitchen-4.webp').exists())
for rel in ('cabin.html','gallery.html'):
    t=(ROOT/rel).read_text(encoding='utf-8')
    check(f'{rel} uses image 1 once',t.count('arbor-vista-charcoal-kitchen-1.webp')==1)
    check(f'{rel} uses image 2 once',t.count('arbor-vista-charcoal-kitchen-2.webp')==1)
    check(f'{rel} has no image 3 reference','arbor-vista-charcoal-kitchen-3.webp' not in t)
    check(f'{rel} has no image 4 reference','arbor-vista-charcoal-kitchen-4.webp' not in t)
public_text='\n'.join(p.read_text(encoding='utf-8',errors='ignore') for p in [ROOT/'cabin.html', ROOT/'gallery.html'])
check('No public page references image 3','arbor-vista-charcoal-kitchen-3.webp' not in public_text)
check('No public page references image 4','arbor-vista-charcoal-kitchen-4.webp' not in public_text)
node=subprocess.run(['node','--check',str(ROOT/'assets'/'script.js')],capture_output=True,text=True)
check('Shared JavaScript syntax passes',node.returncode==0,node.stderr)
passed=sum(c['passed'] for c in checks)
report={'version':'3.3.1','status':'PASS' if passed==len(checks) else 'FAIL','checks_passed':passed,'checks_total':len(checks),'checks':checks}
(ROOT/'QA_REPORT_V3.3.1.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(f'{passed}/{len(checks)} checks passed')
if passed!=len(checks):
    [print('FAIL',c['name'],c['detail']) for c in checks if not c['passed']]
    raise SystemExit(1)
