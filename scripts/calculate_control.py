"""Calculate iteration control metrics from the approved plan and project registers."""
from pathlib import Path
from datetime import date
from collections import defaultdict
import argparse, csv, json, math

ROOT=Path(__file__).resolve().parents[1]
CONTROL=ROOT/'docs/control'
def rows(name):
    with (CONTROL/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def metrics(bac,pv,ev,ac,velocity):
    cpi=ev/ac if ac>0 else None
    spi=ev/pv if pv>0 else None
    eac=ac+(bac-ev)/cpi if cpi is not None and cpi>0 else None
    return dict(BAC=bac,PV=pv,EV=ev,AC=ac,CV=ev-ac,SV=ev-pv,CPI=cpi,SPI=spi,EAC=eac,VAC=bac-eac if eac is not None else None,velocity=velocity)
def calculate(config):
    units=rows('control-units.csv'); rates={r['Исполнитель']:float(r['Ставка руб/ч'])for r in rows('rates.csv')}
    logs=rows('time-log.csv'); acceptance=rows('story-acceptance.csv')
    errors=[]; pending=[]
    n=config['report_iteration']
    if type(n)is not int or n not in (1,2,3,4):raise ValueError('report_iteration must be 1..4')
    for key in ['report_date','baseline_approved_date']:
        if not config.get(key):pending.append(key)
    if config.get('actuals_complete') is not True:pending.append('actuals_complete')
    if config.get('acceptance_complete') is not True:pending.append('acceptance_complete')
    if pending:return dict(status='Ожидает отчётных данных',required=pending,report_iteration=n)
    cutoff=date.fromisoformat(config['report_date'])
    approved=date.fromisoformat(config['baseline_approved_date'])
    if approved>cutoff:errors.append('Дата согласования плана позже отчётной даты')
    ids=[r['ID']for r in units]
    if len(ids)!=len(set(ids)):errors.append('Повтор идентификатора бюджетной единицы')
    model=json.loads((ROOT/'docs/phase-3/data/model.json').read_text(encoding='utf-8'))
    sums=defaultdict(lambda:[0.,0.,0.])
    pv=ev=ac=0.
    for r in units:
        w=r['ИСР'];share=float(r['Доля бюджета']);budget=float(r['Бюджет руб']);hours=float(r['Бюджет ч']);planned=int(r['Плановая итерация'])
        if not all(math.isfinite(v) and v>=0 for v in (share,budget,hours)):errors.append('Некорректный бюджет '+r['ID'])
        sums[w][0]+=share;sums[w][1]+=budget;sums[w][2]+=hours
        if planned<=n:
            pv+=budget
            if r['Статус'] not in ('Принято','Не принято','В работе'):errors.append('Не определён результат '+r['ID'])
        if r['Статус']=='Принято':
            if not all(r[k]for k in ['Итерация приёмки','Дата','Доказательство']):errors.append('Неполное основание приёмки '+r['ID']);continue
            ai=int(r['Итерация приёмки']);ad=date.fromisoformat(r['Дата'])
            if ai<0 or ai>4:errors.append('Недопустимая итерация приёмки '+r['ID'])
            if ai<=n and ad<=cutoff:ev+=budget
            if ai<=n and ad>cutoff:errors.append('Дата приёмки позже границы '+r['ID'])
    for w,t in model['tasks'].items():
        s=sums[w]
        if abs(s[0]-1)>1e-8 or abs(s[1]-t['cost'])>.01 or abs(s[2]-t['e'])>1e-6:errors.append('Несогласованный бюджет ИСР '+w)
    if set(sums)!=set(model['tasks']):errors.append('Состав бюджетных единиц отличается от ИСР')
    if abs(sum(v[1]for v in sums.values())-float(config['BAC']))>.01:errors.append('BAC отличается от распределённого бюджета')
    task_wbs={}
    for phase in [5,6]:
        with (ROOT/f'docs/phase-{phase}/data/iteration-{phase-4}.csv').open(encoding='utf-8-sig',newline='') as f:
            task_wbs.update({r['ID']:r['ИСР']for r in csv.DictReader(f)})
    daily=defaultdict(float)
    for r in logs:
        it=int(r['Итерация']);d=date.fromisoformat(r['Дата']);hours=float(r['Часы']);person=r['Исполнитель']
        if not math.isfinite(hours)or hours<=0:errors.append('Недопустимое время '+r['Задача']);continue
        if it not in range(5):errors.append('Недопустимая итерация '+r['Задача'])
        if person not in rates:errors.append('Неизвестный исполнитель '+person);continue
        if r['ИСР']not in model['tasks']:errors.append('Неизвестный ИСР '+r['ИСР'])
        if r['Задача']in task_wbs and task_wbs[r['Задача']]!=r['ИСР']:errors.append('ИСР задачи отличается от плана '+r['Задача'])
        if not r['Результат']:errors.append('Нет ссылки на результат '+r['Задача'])
        daily[(d,person)]+=hours
        if it<=n and d<=cutoff:ac+=hours*rates[person]
        if it<=n and d>cutoff:errors.append('Время после отчётной даты '+r['Задача'])
    if any(v>24 for v in daily.values()):errors.append('Суточное время участника превышает 24 часа')
    velocity=0.;seen=set()
    for r in acceptance:
        sid=r['История']
        if sid in seen:errors.append('Повтор истории '+sid)
        seen.add(sid)
        if int(r['Плановая итерация'])<=n and r['Решение']not in ('Принято','На доработку','Перенесено'):errors.append('Не определено решение по истории '+sid)
        if r['Решение']=='Принято':
            if not all(r[k]for k in ['SP согласовано','Итерация приёмки','Дата','Основание']):errors.append('Неполная приёмка истории '+sid);continue
            sp=float(r['SP согласовано']);ai=int(r['Итерация приёмки']);ad=date.fromisoformat(r['Дата'])
            if not math.isfinite(sp)or sp<=0:errors.append('Некорректные SP '+sid)
            if ai<=n and ad>cutoff:errors.append('История принята после отчётной даты '+sid)
            if ai==n and ad<=cutoff:velocity+=sp
    if errors:raise ValueError('\n'.join(errors))
    return dict(status='Рассчитано',report_iteration=n,report_date=cutoff.isoformat(),**metrics(float(config['BAC']),pv,ev,ac,velocity))
def self_check():
    x=metrics(1000,500,400,450,8)
    assert x['CV']==-50 and x['SV']==-100 and abs(x['EAC']-1125)<1e-8 and abs(x['VAC']+125)<1e-8
    assert metrics(1000,0,0,0,0)['EAC'] is None
    assert metrics(1000,500,0,200,0)['CPI']==0
    assert metrics(1000,500,0,200,0)['EAC'] is None
    assert metrics(1000,1000,1000,1200,9)['EAC']==1200
    return dict(status='OK',checks=['отклонения и прогноз','нулевые знаменатели','нулевая эффективность','завершённый бюджет'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',default='docs/control/report-I1.json');p.add_argument('--self-check',action='store_true');p.add_argument('--out')
    args=p.parse_args()
    try:
        result=self_check()if args.self_check else calculate(json.loads((ROOT/args.config).read_text(encoding='utf-8')))
    except (ValueError,KeyError,TypeError) as e:raise SystemExit('Ошибка данных: '+str(e))
    text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
    if args.out:(ROOT/args.out).write_text(text+'\n',encoding='utf-8')
    print(text)
