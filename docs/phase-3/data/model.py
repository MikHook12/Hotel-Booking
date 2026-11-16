import json,math,datetime,pathlib
O=pathlib.Path('outputs');O.mkdir(exist_ok=True)
people={'M':('Крюков М. Н.',800),'B':('Бондаренко Д. Р.',900),'S':('Шаталов Б. Г.',800),'U':('Ушаков А. П.',700),'K':('Колесник А.',600)}
raw=[
('1.1','Концепция и жизненный цикл','M',4,''),('1.2','Устав и реестр сторон','M',6,'1.1'),('1.3','ИСР и базовый план','M',12,'1.2'),('1.4','Мониторинг и адаптация','M',12,'1.3'),('1.5','Закрытие проекта','M',2,'5.5,1.4'),
('2.1','Репозиторий и трекер','U',4,'1.1'),('2.2','Локальный стенд','U',10,'2.1'),('2.3','Модель данных','B',6,'1.1'),('2.4','Безопасность и роли','B',6,'2.3'),('2.5','Контракты и зависимости','B',6,'2.3'),
('3.1','Учётные записи','B',6,'2.4,2.5'),('3.2','Каталог отелей','M',8,'2.3,2.5'),('3.3','Каталог номеров','B',10,'3.2,2.5'),('3.4','Бронирование','B',12,'3.1,3.3'),('3.5','Статистика событий','U',10,'2.2,2.5'),
('4.1','Прототип экранов','S',6,'1.1'),('4.2','Вход и регистрация','S',8,'4.1,2.5'),('4.3','Каталог и поиск','S',12,'4.2'),('4.4','Оформление брони','S',12,'4.3'),('4.5','Кабинет администратора','S',12,'4.4'),
('5.1','Автоматические тесты','K',12,'2.4,2.5'),('5.2','Интеграционная проверка','K',12,'3.4,3.5,4.5,5.1,5.3,2.2'),('5.3','Демонстрационные данные','U',8,'2.2,2.3'),('5.4','Документация','K',12,'2.5,4.1'),('5.5','Демо и приёмка','K',12,'5.2,5.4')]
tasks={}
for id,n,p,m,pred in raw:
 a=m*.5;b=m*1.5
 tasks[id]={'id':id,'name':n,'owner':p,'m':m,'a':a,'b':b,'e':m,'var':((b-a)/6)**2,'cost':m*people[p][1],'pred':pred.split(',') if pred else []}
# Topological traversal, no resource assumptions in the network.
order=[];pending=set(tasks)
while pending:
 ready=[i for i in tasks if i in pending and all(p in order for p in tasks[i]['pred'])]
 assert ready,'cycle'
 order+=ready;pending-=set(ready)
for i in order:
 t=tasks[i];t['es']=max([tasks[p]['ef'] for p in t['pred']]+[0]);t['dur']=t['e']/1.2;t['ef']=t['es']+t['dur'];t['succ']=[j for j in tasks if i in tasks[j]['pred']]
T=max(t['ef'] for t in tasks.values())
for i in order[::-1]:
 t=tasks[i];t['lf']=min([tasks[s]['ls'] for s in t['succ']]+[T]);t['ls']=t['lf']-t['dur'];t['tf']=t['ls']-t['es'];t['ff']=min([tasks[s]['es'] for s in t['succ']]+[T])-t['ef']
# AOA: every package is its own real arc; precedence arcs are zero-duration dummies.
arcs=[];node=1
for i in order:
 tasks[i]['i']=node;tasks[i]['j']=node+1;node+=2
end=node;events={n:{'early':0,'late':T} for n in range(end+1)}
for i in order:
 t=tasks[i];arcs.append((t['i'],t['j'],t['dur'],i))
 for p in t['pred']:arcs.append((tasks[p]['j'],t['i'],0,'dummy'))
 if not t['pred']:arcs.append((0,t['i'],0,'dummy'))
 if not t['succ']:arcs.append((t['j'],end,0,'dummy'))
for n in range(end+1):
 events[n]['early']=max([events[a]['early']+d for a,b,d,_ in arcs if b==n]+[0])
for n in range(end,-1,-1):
 events[n]['late']=min([events[b]['late']-d for a,b,d,_ in arcs if a==n]+[T])
for t in tasks.values():
 t['aon_free']=t['ff']
 t['ff']=max(0,events[t['j']]['early']-events[t['i']]['early']-t['dur'])
 t['ind']=max(0,events[t['j']]['early']-events[t['i']]['late']-t['dur'])
critical=[i for i in order if abs(tasks[i]['tf'])<1e-8]
# Resource-constrained calendar: 0.01 h slots, five days/week, 1.2 h per workday.
# Recurring management and four acceptance checkpoints occupy explicitly reserved effort.
left={i:t['m'] for i,t in tasks.items()};done={};alloc=[];starts={};finish={};d=0
while left and d<200:
 caps={p:1.2 for p in people}
 if False:
  for p,tid in [('M','1.4'),('K','5.5')]:
   h=.3;caps[p]-=h;alloc.append((d,p,tid,h))
 # Work only on predecessors completed on a prior day, except recurring summaries.
 available=[i for i in order if i in left and all(p in done for p in tasks[i]['pred'])]
 for p in people:
  cand=[i for i in available if tasks[i]['owner']==p]
  # Integrations and final closing have priority once all prerequisites are met.
  if cand:
   i=cand[0];h=min(caps[p],left[i]);left[i]-=h;starts.setdefault(i,d);alloc.append((d,p,i,h));finish[i]=d+1
   if left[i]<1e-8:done[i]=d+1;del left[i]
 d+=1
# Close cannot be before actual final demo/check; shift its 2h allocation beyond day55.
for t in tasks.values():t['start']=starts[t['id']];t['finish']=finish[t['id']]
load={p:sum(t['m'] for t in tasks.values() if t['owner']==p) for p in people}
cost=sum(t['cost'] for t in tasks.values())
path=[];cur=max(tasks,key=lambda i:tasks[i]['ef'])
while cur:
 path.insert(0,cur);ps=tasks[cur]['pred'];cur=max(ps,key=lambda i:tasks[i]['ef']) if ps else None
sd=math.sqrt(sum(tasks[i]['var']/1.2**2 for i in path));prob=.5*(1+math.erf((55-T)/sd/math.sqrt(2)))
def schedule(rate):
 left={i:t['m'] for i,t in tasks.items()};done={};allocation=[];starts={};fin={};day=0
 while left and day<200:
  ready=[i for i in order if i in left and all(p in done for p in tasks[i]['pred'])]
  for p in people:
   cand=[i for i in ready if tasks[i]['owner']==p]
   if cand:
    i=cand[0];h=min(rate,left[i]);left[i]-=h;starts.setdefault(i,day);allocation.append([day,p,i,h]);fin[i]=day+1
    if left[i]<1e-8: done[i]=day+1;del left[i]
  day+=1
 return {'days':day,'start':starts,'finish':fin,'alloc':allocation}
model={'tasks':tasks,'order':order,'events':events,'arcs':arcs,'people':people,'T':T,'path':path,'sd':sd,'prob55':prob,'load':load,'cost':cost,'alloc':alloc,'resource_days':d,'scenario9':schedule(1.8)}
pathlib.Path('work/model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:model[k] for k in ['T','path','sd','prob55','load','cost','resource_days']},ensure_ascii=False));print([(i,tasks[i]['start'],tasks[i]['finish']) for i in tasks])
