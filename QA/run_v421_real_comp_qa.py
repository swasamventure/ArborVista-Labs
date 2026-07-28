from pathlib import Path
import json, re, sys
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def ck(name,ok,detail=''): checks.append((name,bool(ok),str(detail)))
data=json.loads((ROOT/'admin/data/market-intelligence-real-snapshot.json').read_text())
prop=data['properties'][0]; comps=prop['comps']
ck('Release version',data['version']=='4.2.1-real-comp-snapshot',data['version'])
ck('Comp count 50 to 100',50<=len(comps)<=100,len(comps))
ck('At least 3 platforms',len(set(c['platform'] for c in comps))>=3,set(c['platform'] for c in comps))
ck('All records have public URLs',all(c.get('listingUrl','').startswith('https://') for c in comps))
ck('All records dated',all(c.get('sourceObservedAt')=='2026-07-28' for c in comps))
ck('No fake competitor occupancy/revenue',all(not c.get('metrics') for c in comps))
ck('Airbnb coverage',sum(c['platform']=='Airbnb' for c in comps)>=35)
ck('Vrbo coverage',sum(c['platform']=='Vrbo' for c in comps)>=10)
ck('Booking coverage',sum(c['platform']=='Booking.com' for c in comps)>=10)
ck('Observation template exists',(ROOT/'admin/data/market-rate-observation-template.csv').exists())
ck('Observation plan exists',(ROOT/'market-data/observations/arbor-vista-observation-plan.json').exists())
html=(ROOT/'admin/market-intelligence.html').read_text()
js=(ROOT/'admin/market-intelligence.js').read_text()
ck('HTML labels v4.2.1','v4.2.1' in html)
ck('HTML loads real snapshot','market-intelligence-real-snapshot.js' in html)
ck('Level 2 plan visible','Level 2 recurring observation plan' in html)
ck('AI next phase doc exists',(ROOT/'Docs/NEXT_PHASE_AI_GUEST_ASSISTANT.md').exists())
ck('Kitchen image 1 retained',(ROOT/'images/kitchen/arbor-vista-charcoal-kitchen-1.webp').exists())
ck('Kitchen image 2 retained',(ROOT/'images/kitchen/arbor-vista-charcoal-kitchen-2.webp').exists())
ck('Kitchen images 3 and 4 absent',not any((ROOT/'images/kitchen'/f'arbor-vista-charcoal-kitchen-{i}.webp').exists() for i in (3,4)))
failed=[c for c in checks if not c[1]]
print(f'{len(checks)-len(failed)}/{len(checks)} v4.2.1 checks passed')
for c in failed: print('FAIL',c[0],c[2])
raise SystemExit(1 if failed else 0)
