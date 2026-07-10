# Фоновый worker для развития скилла

Этот документ можно использовать как prompt для Claude Cowork, Claude Code
routine или отдельной сессии Claude Code.

Цель worker'а — не "дообучать модель". Он улучшает репозиторий: находит
проверяемые backend-кейсы, сжимает их до failure modes и готовит маленькие PR.

## Что выбрать

| Инструмент | Когда удобен |
|---|---|
| Claude Cowork | долгий фоновой поиск, периодические обзоры, работа с браузером и файлами |
| Claude Code routine | регулярная задача по репозиторию: раз в неделю собрать candidates и открыть issue/PR |
| Claude Code вручную | точечный разбор одного кейса или одного источника |

Для этого проекта важнее не инструмент, а контракт: worker не пишет большие
разделы "про тему". Он приносит доказательства.

## Главный prompt

```text
Ты работаешь с репозиторием backend-craft.

Цель: улучшать скилл через проверяемые backend failure modes.
Не расширяй scope без отдельного решения владельца.
Не коммить напрямую в main.
Готовь маленькие PR-кандидаты или issue drafts.

Перед работой прочитай:
- README.md
- CONTRIBUTING.md
- docs/CASE_PIPELINE.md
- docs/WRITING_STYLE.md
- docs/SOURCES.md
- docs/STATUS.md
- FAILURE_CARDS.md

Рабочий цикл:

1. Выбери один узкий источник или один реальный кейс.
   Хорошо: официальный документ, issue/PR с понятным багом, incident writeup.
   Плохо: "изучи Kafka", "добавь best practices", "улучши безопасность".

2. Проверь, есть ли уже такая failure card.
   Если да, не дублируй. Предложи уточнение, verifier или checker.
   Если нет, подготовь candidate card.

3. Сожми материал до повторяемого failure mode:
   - situation;
   - common agent failure;
   - blast radius;
   - safe pattern;
   - verifier;
   - escape hatch;
   - source или observed evidence.

4. Подготовь минимальный artifact:
   - failure card draft;
   - verifier/test idea;
   - Semgrep/ast-grep/checker idea;
   - fixture idea;
   - rejection note.

5. Проверь, что материал не является общим советом.
   Если verifier невозможен, оставь backlog note и не меняй skill.

6. Если есть изменение файлов:
   - держи PR маленьким;
   - обнови EVIDENCE_LOG.md, если меняется статус card/rule;
   - добавь fixture/checker только если можешь запустить проверку;
   - запусти минимальные команды из CONTRIBUTING.md.

7. В конце дай отчет:
   - что прочитал;
   - что извлек;
   - какие файлы изменил;
   - какие проверки запустил;
   - почему это не общая рекомендация;
   - что остается нерешенным.

Запрещено:
- копировать длинные куски документации;
- добавлять советы без failure mode;
- повышать статус до production-tested без evidence;
- добавлять новый язык/фреймворк/очередь/БД без решения владельца;
- использовать приватный код без анонимизации;
- менять публичный README внутренними TODO.
```

## Prompt для недельного обзора

```text
Сделай weekly source radar для backend-craft.

Ограничения:
- максимум 90 минут;
- максимум 3 candidates;
- только официальные docs, зрелые tool docs или публичные incident writeups;
- не меняй skill, если нет card/verifier/checker/playbook step;
- не открывай больше одного PR.

Темы этого прогона:
1. API compatibility и contract testing;
2. authorization/tenant boundaries;
3. migrations и DB safety;
4. retries/timeouts/idempotency;
5. queues/workers/cancellation.

Выход:
- таблица candidates;
- для каждого: source, failure mode, verifier, target file, decision;
- один PR candidate или issue drafts.
```

## Prompt для разбора реального кейса

```text
Разбери приложенный backend-кейс для backend-craft.

Не добавляй советы прямо в skill.
Сначала сделай evidence distillation:

1. Удали приватные данные.
2. Опиши баг в 5-7 строк.
3. Сведи к минимальному reducer.
4. Найди похожую failure card.
5. Если такой card нет, предложи новую.
6. Дай verifier: test, checker, query, log assertion, contract diff или review step.
7. Дай blind forward-test prompt.
8. Прими решение: reject / backlog / fixture-tested / production-tested.

Если reducer или verifier нет, не трогай skill. Оставь issue draft.
```

## Prompt для source digestion

```text
Разбери один официальный источник для backend-craft.

Источник: <URL>
Scope: <одна узкая тема>

Нужно:
1. Выписать только факты, которые меняют поведение backend-агента.
2. Для каждого факта дать situation, failure, blast radius, safe pattern,
   verifier и escape hatch.
3. Сопоставить с существующими failure cards.
4. Предложить точечную правку: card / reference / checker / reject.
5. Не копировать prose из источника.

Если после разбора получается только "надо делать хорошо", отклони материал.
```

## Хороший результат фонового запуска

Хороший результат — маленький и проверяемый.

Примеры:

- один PR с новой fixture-probe и обновленной card;
- issue с хорошо сжатым реальным кейсом и verifier idea;
- rejected note: источник прочитан, но не дал нового failure mode;
- уточнение `docs/SOURCES.md`, если источник устарел или уже покрыт.

Плохой результат:

- большой "раздел про Kafka";
- 20 новых карточек без tests;
- переписанный README;
- новые правила без false-positive boundary;
- статус `production-tested` без ссылки на evidence.

## Как часто запускать

| Режим | Частота |
|---|---|
| Source radar | раз в неделю |
| Реальный кейс из PR/incident | сразу после появления |
| Promotion sweep | раз в месяц |
| Большой scope expansion | только после отдельного решения владельца |

Фоновый worker должен оставлять след в issue или PR. Иначе через месяц будет
невозможно понять, чему скилл "научился".
