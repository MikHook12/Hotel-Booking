"""Validate repository documentation with Python standard library only."""
from pathlib import Path
import csv,json,re
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]
errors=[]
for path in ROOT.rglob('*.md'):
    if '.git' in path.parts:
        continue
    for label,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',path.read_text(encoding='utf8')):
        target=target.strip().strip('<>')
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('#'):
            continue
        target=unquote(target.split('#',1)[0])
        resolved=(path.parent/target).resolve()
        if not resolved.is_relative_to(ROOT) or not resolved.exists():
            errors.append(f'{path.relative_to(ROOT)}: missing or escaping link {target}')

DATA=ROOT/'docs/phase-3/data'
def rows(name):
    with (DATA/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.reader(f))

model=json.loads((DATA/'model.json').read_text(encoding='utf8'))
tasks=model['tasks']
if len(tasks)!=25:
    errors.append('Expected 25 WBS packages')
if sum(t['m'] for t in tasks.values())!=220 or sum(t['cost'] for t in tasks.values())!=167800:
    errors.append('The preserved example no longer matches its stated hours/cost')
for name,col in [('estimates.csv',0),('backlog.csv',4),('tracker-seed.csv',3)]:
    for row in rows(name)[1:]:
        if row[col] not in tasks:
            errors.append(f'{name}: unknown WBS {row[col]}')
tracker=rows('tracker-seed.csv')[1:]
ids=[r[0] for r in tracker]
if len(ids)!=len(set(ids)):
    errors.append('Duplicate tracker IDs')
for row in tracker:
    if row[2] and row[2] not in ids:
        errors.append(f'Unresolved parent {row[2]} for {row[0]}')
for scenario,rate in [(dict(alloc=model['alloc'],start={k:v['start'] for k,v in tasks.items()},finish={k:v['finish'] for k,v in tasks.items()}),1.2),(model['scenario9'],1.8)]:
    for key,task in tasks.items():
        if any(scenario['start'][key]<scenario['finish'][p] for p in task['pred']):
            errors.append(f'Dependency violation {key}')
    for day in range(max(scenario['finish'].values())):
        for person in model['people']:
            hours=sum(a[3] for a in scenario['alloc'] if a[0]==day and a[1]==person)
            if hours>rate+1e-8:
                errors.append(f'Resource overload {person}, day {day}')

with (DATA/'tracker-seed.csv').open(encoding='utf-8-sig',newline='') as f:
    current=list(csv.DictReader(f))
if len(current)!=59:
    errors.append('Expected 59 prepared cards')
if any(r['Факт, ч'] or r['Остаток, ч'] for r in current):
    errors.append('Actual or remaining hours were populated without evidence')
if any(r['Статус']!='Сделано' for r in current if r['ID'] in ['WP-1.1','WP-1.2']):
    errors.append('Submitted document status missing')
if sum(float(r['План, ч']) for r in current if r['Тип']=='Задача')!=45:
    errors.append('First iteration scenario should total 45h')

# Iteration plans and budget allocation use the same WBS and resource model.
from collections import defaultdict
planned=defaultdict(float)
for phase,expected_hours in [(5,45),(6,30)]:
    with (ROOT/f'docs/phase-{phase}/data/iteration-{phase-4}.csv').open(encoding='utf-8-sig',newline='') as f:
        iteration=list(csv.DictReader(f))
    if len(iteration)!=16 or len({r['ID'] for r in iteration})!=16:
        errors.append(f'Phase {phase}: expected 16 unique tasks')
    if abs(sum(float(r['План ч']) for r in iteration)-expected_hours)>1e-8:
        errors.append(f'Phase {phase}: inconsistent hours')
    workload=defaultdict(float)
    for r in iteration:
        if r['ИСР'] not in tasks:
            errors.append(f"Unknown WBS in {r['ID']}")
        planned[r['ИСР']]+=float(r['План ч'])
        workload[r['Ответственный']]+=float(r['План ч'])
    if any(v>12 for v in workload.values()):
        errors.append(f'Phase {phase}: resource capacity exceeded')
for w,hours in planned.items():
    if hours>tasks[w]['e']+1e-8:
        errors.append(f'Iteration task estimates exceed the scenario package {w}')
with (ROOT/'docs/control/control-units.csv').open(encoding='utf-8-sig',newline='') as f:
    units=list(csv.DictReader(f))
alloc=defaultdict(lambda:[0.,0.,0.])
for u in units:
    alloc[u['ИСР']][0]+=float(u['Доля бюджета'])
    alloc[u['ИСР']][1]+=float(u['Бюджет ч'])
    alloc[u['ИСР']][2]+=float(u['Бюджет руб'])
if set(alloc)!=set(tasks):
    errors.append('Control allocation must cover all WBS packages')
for w,t in tasks.items():
    a=alloc[w]
    if abs(a[0]-1)>1e-8 or abs(a[1]-t['e'])>1e-8 or abs(a[2]-t['cost'])>.01:
        errors.append(f'Control budget does not reconcile for {w}')

for path in ROOT.rglob('*.md'):
    txt=path.read_text(encoding='utf-8')
    if re.search(r'ChatGPT|помощник|нейросет|от имени ИИ|в этой задаче|в данной работе|не предоставлен|не представлены|логин требует подтверждения',txt,re.I):
        errors.append(f'Editorial wording: {path.relative_to(ROOT)}')

if errors:
    raise SystemExit('\n'.join(errors))
print('OK: links, WBS, two iteration plans, budgets, capacity, control allocation and document wording')
