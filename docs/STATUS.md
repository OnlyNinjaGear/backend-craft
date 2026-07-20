# Готовность backend-craft

Обновлено: 2026-07-19. Текущий канал: **post-v0.1 `main`, team pilot**.

Последний неизменяемый тег `v0.1` не содержит последующие cards/rules и
implementation-evidence contract. Для пилота используется `main`. Старый тег не
передвигается; после закрытия релизных ворот создается новый.

## Короткий ответ

Скилл уже можно устанавливать в другие проекты. Его router, reference packs,
fixtures, CI и hook работают как единый пакет. Четыре режима работы проверены
слепыми тестами.

Это не означает полное покрытие Python, Go или TypeScript. Проект проверяет
production failure surfaces на representative stacks. Стек считается
проверенным только в пределах доказательств, перечисленных ниже.

`Frozen v0.1` означает заморозку scope. Это не статус незавершенного продукта.

## Шкала

Эти состояния относятся к readiness dashboard. Они не заменяют статусы
failure cards и Semgrep rules.

| Состояние | Значение |
|---|---|
| `READY` | текущий релизный контур можно использовать |
| `VALIDATED` | есть инструкции, runnable fixture/reducer и слепая проверка поведения агента |
| `OBSERVED` | прогнано на реальном коде, но нет выделенного regression fixture |
| `PARTIAL` | есть часть runnable evidence, но остается известный пробел |
| `DOCUMENTED` | есть sources и инструкции, но нет dedicated runnable evidence |
| `OUT` | не входит в текущий scope; поддержка не заявляется |

## Режимы работы

| Режим | Состояние | Evidence |
|---|---|---|
| Start: новый backend | `VALIDATED` | [001](../forward-test-results/001-start-mode.md), [101](../forward-test-results/101-start-mode.md) |
| Retrofit: подключение к существующему проекту | `VALIDATED` | [002](../forward-test-results/002-retrofit.md), [102](../forward-test-results/102-retrofit.md) |
| Harden: аудит и исправление backend | `VALIDATED` | [014](../forward-test-results/014-rewrite-discipline.md), [302](../forward-test-results/302-rewrite-discipline-retest.md) |
| Continue: обычная фича или bugfix | `VALIDATED` | тесты [003-013](../forward-test-results/) и targeted regression [301](../forward-test-results/301-write-tests.md) |

## Production failure surfaces

| Область | Состояние | Основное доказательство |
|---|---|---|
| API contracts и DTO | `VALIDATED` | `api-contracts.md`, tenant/DTO forward tests 003 и 011 |
| Authorization и tenancy | `VALIDATED` | `auth-tenancy-security.md`, Python/TS fixtures, forward test 003 |
| Persistence и migrations | `VALIDATED` | `persistence-migrations.md`, SQL rules, forward tests 004 и 005 |
| Retry, timeout, queues, cancellation | `VALIDATED` | `reliability-async.md`, три fixtures, forward tests 006-010 |
| Observability | `VALIDATED` | `observability-ops.md`, forward test 012 |
| Testing и proof discipline | `VALIDATED` | `testing-verification.md`, regressions 114, 301 и 302 |
| Library choice | `VALIDATED` | `library-decisions.md`, forward test 013 |
| Existing-code fit | `VALIDATED` | `codebase-fit.md`, forward tests 002 и 014 |
| Stack selection | `VALIDATED` | `stack-recipes.md`, forward tests 001 и 101 |
| Self-hosted inference ops | `OBSERVED` | `self-hosted-inference.md`, 9 cards из реальной fleet-сессии 2026-07-19; без dedicated fixture и forward tests |

## Технологии

| Технология | Инструкции | Runnable evidence | Реальный проект | Состояние |
|---|---|---|---|---|
| Python + FastAPI | recipe + language adapter | fixture: 5 planted flaws; forward tests 010, 012 | mixed monorepo: checker/hook only | `VALIDATED` representative stack |
| Go + `net/http` | recipe + language adapter | fixture: 6 planted flaws; forward tests 004, 009 | mixed monorepo: checker/hook only | `VALIDATED` representative stack |
| TypeScript + Fastify | recipe + language adapter | fixture: 5 planted flaws; forward tests 008, 011, 014, 302 | mixed monorepo includes NestJS, not Fastify | `VALIDATED` representative stack |
| NestJS | recipe | no dedicated fixture | checker/hook on a real admin API | `OBSERVED` |
| PostgreSQL | persistence recipe + official sources | migration scenarios + SQL reducer | no full-project skill validation | `PARTIAL`; pg claim verifier has timing debt |
| MongoDB | persistence guidance + cards | none dedicated | none recorded | `DOCUMENTED` |
| Django + DRF | stack recipe + official sources | none dedicated | none recorded | `DOCUMENTED` |
| Redis + BullMQ | library decision only | none dedicated | none recorded | `DOCUMENTED` |
| Kafka | none admitted | none | none | `OUT` |
| RabbitMQ | generic queue principles only | none dedicated | none | `OUT` |
| Kubernetes | none | none | none | `OUT` |

`VALIDATED representative stack` не означает поддержку каждой библиотеки
языка. Например, FastAPI fixture не доказывает поведение Django, а `net/http`
fixture не доказывает интеграцию с Gin или Echo.

## Evidence inventory

| Артефакт | Состояние |
|---|---:|
| Reference packs | 11 |
| Failure cards | 57 |
| Cards со статусом `production-tested` | 17 |
| Cards со статусом `observed` | 8 |
| Cards со статусом `draft` | 32 |
| Semgrep rules | 16 |
| Rules со статусом `production-tested` | 2 |
| Rules со статусом `fixture-tested` | 11 |
| Rules со статусом `draft` | 3 |
| Fixtures | 3 проекта, 16 planted flaws |
| Forward-test results | 30 файлов: 14 + 14 + 2 regression tests |
| Последний regression round | 2/2 теста получили 4/4 |
| Real-backend records | 1 mixed NestJS/Go/Python monorepo; checker/hook validation |
| Hook acceptance | 14/14 assertions |
| CI | repository, Semgrep baseline, 3 fixtures и hook |

## Что завершено в текущем snapshot

- [x] Installable router skill и 11 routed reference packs.
- [x] Start, Retrofit, Harden и Continue прошли blind forward tests.
- [x] Python/FastAPI, Go/`net/http` и TypeScript/Fastify имеют runnable fixtures.
- [x] Semgrep baseline фиксирован на 11 findings и проверяется в CI.
- [x] Hook имеет bounded output и 14/14 acceptance assertions.
- [x] Реальный mixed monorepo использован для проверки checker/hook integration.

Поэтому текущий `main` готов для внутреннего использования и командного пилота.

## Ворота следующего релиза

Это конечная очередь, а не бесконечный source-digestion backlog.

| Приоритет | Ворота | Кто может закрыть | Done when |
|---:|---|---|---|
| 1 | Выбрать open-source license | владелец | в корне есть распознаваемый `LICENSE` |
| 2 | Убрать timing-зависимость из Postgres claim verifier | агент | нет `sleep`; observer детерминированно подтверждает lock wait; 20 повторов проходят |
| 3 | Разрешить судьбу 3 draft Semgrep rules | агент при наличии evidence | каждая rule повышена по fixture/real evidence или отклонена как шумная |
| 4 | Полный skill-run на независимом Python backend | владелец дает проект, агент выполняет | anonymized evidence содержит найденные риски, false positives и проверки |
| 5 | Полный skill-run на независимом Go backend | владелец дает проект, агент выполняет | тот же evidence contract, отдельно от mixed monorepo checker run |
| 6 | Выпустить неизменяемый release tag | владелец или release agent после ворот 1-5 | новый тег указывает на green `main`; старый `v0.1` не меняется |

После закрытия этих шести ворот можно выпускать следующий evidence release и
решать, готово ли имя `v1.0`. Redis, Kafka, Kubernetes и другие новые области не
являются обязательными для `v1.0`: они входят только после owner-approved scope
decision и конкретного failure signal.

## Как Claude выбирает следующую работу

1. Берет первый незакрытый пункт, который не требует решения владельца.
2. Не создает новый technology target ради заполнения таблицы.
3. Для нового знания требует prior signal и следует
   [IMPLEMENTATION_EVIDENCE_PASS.md](IMPLEMENTATION_EVIDENCE_PASS.md).
4. Если signal нет, результат `target UNSET` считается нормальным.
