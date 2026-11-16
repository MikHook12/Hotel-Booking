# Исходные данные предварительного расчёта

| Файл | Содержание |
| --- | --- |
| [estimates.csv](estimates.csv) |25 пакетов, a/m/b, ставки, формулы |
| [pert-activities.csv](pert-activities.csv) |Сроки и резервы реальных дуг |
| [pert-events.csv](pert-events.csv) |Ранние и поздние события |
| [pert-arcs.csv](pert-arcs.csv) |Все реальные и фиктивные дуги с резервами |
| [schedule.csv](schedule.csv) |Два ресурсных сценария |
| [resources.csv](resources.csv) |Часы и ставки участников |
| [weekly-load.csv](weekly-load.csv) |Загрузка сценария 9 ч/нед |
| [risks.csv](risks.csv) |Структурированный реестр рисков |
| [backlog.csv](backlog.csv) |18 историй |
| [tracker-seed.csv](tracker-seed.csv) |25 пакетов,18 историй,16 задачI1; ещё не журнал факта |
| [model.py](model.py) / [model.json](model.json) |Алгоритм и рассчитанные значения |

CSV используют UTF-8 с BOM и запятую. В estimates.csv поля с `=` являются формулами для табличного редактора; model.json содержит рассчитанные значения.

Чтобы воспроизвести пример без изменения репозитория, скопируйте model.py в пустой временный каталог, создайте в нём папку work и выполните `python model.py`. Результат сохраняется в work/model.json. Скрипт не обращается к сети и не изменяет приложение. Текущая модель — сценарий до аудита кода, не baseline.
