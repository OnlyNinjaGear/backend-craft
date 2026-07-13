# backend-craft

[![CI](https://github.com/OnlyNinjaGear/backend-craft/actions/workflows/ci.yml/badge.svg)](https://github.com/OnlyNinjaGear/backend-craft/actions/workflows/ci.yml)
![Failure patterns](https://img.shields.io/badge/failure%20patterns-41-4c566a)
![Rules](https://img.shields.io/badge/semgrep-16%20rules-2ea44f)
![Fixtures](https://img.shields.io/badge/fixtures-3%20runnable-d97706)

[English](README.en.md)

Production-risk скилл для Claude Code и Codex.

Помогает агенту проектировать, ревьюить и усиливать backend: проверять
API-контракты, права, tenant boundaries, миграции, повторы, таймауты,
идемпотентность и фоновые задачи до того, как проблема уйдет в production.

**41 failure pattern · 16 Semgrep rules · 3 runnable fixtures · 16 planted flaws**

[Установка](#установка) · [Поддерживаемые стеки](#поддерживаемые-стеки) ·
[Как это работает](#как-это-работает) · [Готовность проекта](docs/STATUS.md)

## Что получает разработчик

| Задача | Что делает скилл |
|---|---|
| Новый backend | помогает выбрать стек, библиотеки, API, модель данных, миграции, тесты и CI |
| Существующий проект | сначала читает код и границы системы, затем предлагает план без переписывания всего подряд |
| Новая фича | проверяет контракты, права, данные, повторные вызовы, таймауты и failure paths |
| Ревью или аудит | ищет ошибки с реальным blast radius, а не спорит о стиле |
| Выбор библиотеки | сравнивает риски, стоимость внедрения и способ проверить решение |

Каждая существенная рекомендация должна закончиться тестом, checker'ом,
измерением или конкретным verification plan.

## Поддерживаемые стеки

`Tested` означает dedicated fixture и слепые agent-тесты. `Real-code checked` —
прогон на настоящем репозитории без отдельного fixture. `Guidance` — инструкции
есть, но dedicated проверка еще не собрана.

| Язык или стек | Уровень | Что есть |
|---|---|---|
| Python + FastAPI | Tested | fixture с 5 production flaws; async и observability scenarios |
| Go + `net/http` | Tested | fixture с 6 flaws; concurrency, cancellation и payment scenarios |
| TypeScript + Fastify | Tested | fixture с 5 flaws; DTO, export и retrofit scenarios |
| NestJS | Real-code checked | checker и hook проверены на реальном admin API |
| PostgreSQL | Partial | migration scenarios, SQL checks и runnable reducer |
| MongoDB, Django/DRF, Redis/BullMQ | Guidance | sources, failure cards и stack recipes без dedicated fixtures |

Kafka, RabbitMQ и Kubernetes не входят в текущий scope. Полная матрица с
доказательствами и открытыми воротами лежит в
[docs/STATUS.md](docs/STATUS.md).

## Как это работает

Скилл начинает не с языка, а с поверхности риска. Он определяет, что может
измениться, загружает только подходящие reference packs и проверяет результат.

| Режим | Когда используется | Результат |
|---|---|---|
| **Start** | проект начинается с нуля | foundation: стек, контракты, данные, auth, reliability, tests и CI |
| **Retrofit** | backend уже существует | inventory, карта P0/P1-рисков и поэтапный план исправлений |
| **Harden** | нужен аудит всего backend | findings по blast radius, минимальные patches и verifier для каждого изменения |
| **Continue** | добавляется фича или исправляется баг | impact read, точечная реализация и доказательство измененного поведения |

## Примеры запросов

```text
Use backend-craft to design the backend foundation for a small B2B SaaS.
```

```text
Use backend-craft to review this existing backend for production risks.
Do not rewrite it; give me a staged hardening plan.
```

```text
Use backend-craft while adding this mutating endpoint. Clients may retry.
```

```text
Use backend-craft to review this pull request. Prioritize auth, data integrity,
failure handling, and missing verification.
```

## Установка

Через plugin marketplace (рекомендуется — даёт автообновления):

```
/plugin marketplace add OnlyNinjaGear/backend-craft
/plugin install backend-craft@backend-craft-marketplace
```

Обновление: `/plugin marketplace update backend-craft-marketplace`, либо
дождаться авто-апдейта и выполнить `/reload-plugins`.

Ручной способ (без автообновлений, если marketplace недоступен):

```bash
git clone https://github.com/OnlyNinjaGear/backend-craft.git
mkdir -p /path/to/your-project/.claude/skills
cp -R backend-craft/.claude/skills/backend-craft \
  /path/to/your-project/.claude/skills/
```

Сам скилл работает без дополнительных инструментов. Semgrep rules и
PostToolUse hook подключаются отдельно.

## Что он проверяет

| Область | Типовые риски |
|---|---|
| API | contract drift, DTO leaks, неправильные статусы, небезопасные webhooks |
| Auth и tenancy | BOLA, пропущенный tenant filter, роли, PII, secrets, SSRF |
| Данные | SQL injection, транзакции вокруг network calls, миграции, индексы, N+1 |
| Надежность | retry storms, отсутствие jitter/caps, timeout leaks, cancellation, duplicate delivery |
| Очереди и workers | idempotency, poison messages, unbounded concurrency, shutdown |
| Observability | correlation, cardinality, redaction, ошибки без сигнала |
| Verification | happy-path-only tests, DB integration, contract diff, migration proof |
| Языки | Python async/exceptions, Go contexts/goroutines/errors, Node runtime boundaries |

## Почему результатам можно доверять

| Артефакт | Текущее состояние |
|---|---:|
| Failure cards | 41 |
| Карточки со статусом `production-tested` | 15 |
| Semgrep rules | 16 |
| Rules со статусом `production-tested` | 2 |
| Rules со статусом `fixture-tested` | 11 |
| Rules со статусом `draft` | 3 |
| Fixtures | 3 проекта, 16 planted flaws |
| Forward tests | 3 раунда, 30 result files |
| Real-code validation | mixed NestJS/Go/Python monorepo |
| Hook acceptance | 14/14 assertions |

Fixtures намеренно выглядят как обычный зеленый backend: они собираются и
проходят happy-path tests, но содержат production-safety defects. Отдельные
агенты получают задачи без списка ответов, а результаты оцениваются отдельно.

[Readiness dashboard](docs/STATUS.md) · [Evidence log](docs/EVIDENCE_LOG.md) ·
[Forward-test protocol](docs/FORWARD_TESTS.md)

## Опциональные инструменты

| Компонент | Зачем нужен |
|---|---|
| [Semgrep pack](rules/semgrep/backend-craft.yml) | ловит 16 high-confidence синтаксических паттернов |
| [PostToolUse hook](hooks/README.md) | после правки показывает до 5 advisory findings и не блокирует агента |
| [Failure cards](FAILURE_CARDS.md) | объясняют trigger, blast radius, safe pattern, verifier и escape hatch |
| [Fixtures](fixtures/README.md) | воспроизводят типовые ошибки и границы false positives |

Чистый checker run не доказывает безопасность backend. Семантические ошибки —
например BOLA или неверная идемпотентность — требуют теста и review.

## Статус проекта

Текущий `main` готов для командного пилота. Scope контролируется: новые темы не
добавляются без конкретного failure signal и проверяемого результата. История
тегов, точные уровни покрытия и конечная очередь следующего релиза находятся в
[docs/STATUS.md](docs/STATUS.md).

## Как помочь

Полезный вклад — это не новый раздел «про Kafka», а один проверяемый кейс:

- анонимизированный production bug с reducer;
- официальный источник, из которого следует конкретный verifier;
- checker с true-positive и false-positive boundary;
- runnable fixture;
- слепой forward test.

Начните с [CONTRIBUTING.md](CONTRIBUTING.md) и
[руководства для контрибьюторов](docs/CONTRIBUTOR_GUIDE.md). Архитектура,
источники и правила пополнения собраны в [docs/](docs/README.md).

## Что проект не обещает

- не превращает любой backend в production-ready одним запросом;
- не считает один проверенный framework доказательством полного покрытия языка;
- не заменяет project-local tests, linters, security review и опыт команды.
