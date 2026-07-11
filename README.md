# backend-craft

[![CI](https://github.com/OnlyNinjaGear/backend-craft/actions/workflows/ci.yml/badge.svg)](https://github.com/OnlyNinjaGear/backend-craft/actions/workflows/ci.yml)
![Channel](https://img.shields.io/badge/channel-main-blue)
![Readiness](https://img.shields.io/badge/readiness-team%20pilot-yellowgreen)
![Rules](https://img.shields.io/badge/semgrep-16%20rules-2ea44f)
![Fixtures](https://img.shields.io/badge/fixtures-16%20planted%20flaws-orange)

[English README](README.en.md)

`backend-craft` — скилл для Claude Code и Codex. Он нужен, когда агент пишет,
ревьюит или приводит в порядок backend.

Скилл не обещает "production-ready" одним запросом. Он делает более полезную
вещь: заставляет агента перед правкой понять, где может сломаться система.
API-контракт. Права. Tenant boundary. Миграция. Повторный webhook. Таймаут.
Очередь. Фоновая задача.

Потом агент открывает нужную памятку и доказывает результат тестом, чекером или
явным планом проверки.

## Можно ли использовать сейчас

Да. Текущий `main` можно подключать к новому или существующему backend-проекту и
использовать для работы и ревью. Текущий уровень — **team pilot**: основной
workflow проверен, но проект еще не заявляет полное покрытие языков и
фреймворков.

Последний неизменяемый тег `v0.1` старше текущего evidence-пакета. Для пилота
используйте `main`; перед публичным релизом проекту нужен новый тег.

`Frozen` означает заморозку scope, а не незавершенность. Новые темы не
добавляются без доказанного пробела, но исправления и новые evidence принимаются.

| Контур | Состояние | Что подтверждено |
|---|---|---|
| Router и 4 режима работы | Готов | Start, Retrofit, Harden и Continue прошли слепые тесты |
| Python + FastAPI | Проверен как representative stack | fixture с 5 ошибками, Python async и observability forward tests |
| Go + `net/http` | Проверен как representative stack | fixture с 6 ошибками, concurrency и payment forward tests |
| TypeScript + Fastify | Проверен как representative stack | fixture с 5 ошибками, export, DTO и rewrite forward tests |
| NestJS | Наблюдался на реальном коде | checker и hook прогнаны на mixed monorepo; отдельного fixture нет |
| PostgreSQL | Частично проверен | инструкции, migration tests и reducer; один verifier требует устранить timing-зависимость |
| MongoDB, Django/DRF, Redis/BullMQ | Только documented | есть источники и recipes, но нет dedicated fixtures и blind tests |
| Kafka, RabbitMQ, Kubernetes | Вне `v0.1` | проект не заявляет их поддержку |

Это не означает, что «Python завершен на 100%». Проверен конкретный стек и
набор production failure surfaces. Полная карта, открытые ворота следующего
релиза и порядок работы для Claude лежат в
[docs/STATUS.md](docs/STATUS.md).

## Когда использовать

| Ситуация | Что должен сделать агент |
|---|---|
| Новый проект | выбрать стек, библиотеки, модель API, миграции, тесты и CI без ранних тупиков |
| Существующий проект | сначала понять текущий стек и риски, потом предлагать правки |
| Ревью backend-кода | искать не стиль, а ошибки с реальным радиусом поражения |
| Новая фича | проверить контракты, данные, права, повторы, таймауты и тесты вокруг изменения |
| Выбор библиотеки | объяснить, какой риск библиотека убирает и где она добавляет новый |

## Что внутри

| Часть | Зачем она нужна |
|---|---|
| [`.claude/skills/backend-craft/`](.claude/skills/backend-craft/) | сам скилл, который можно положить в проект |
| [`FAILURE_CARDS.md`](FAILURE_CARDS.md) | карточки типовых backend-ошибок |
| [`rules/semgrep/backend-craft.yml`](rules/semgrep/backend-craft.yml) | проверки для паттернов, которые можно ловить механически |
| [`hooks/`](hooks/) | необязательный PostToolUse hook для быстрых подсказок после правок |
| [`fixtures/`](fixtures/) | три маленьких backend-проекта с заранее посаженными ошибками |
| [`forward-test-results/`](forward-test-results/) | результаты слепых тестов: как агенты работали со скиллом |
| [`docs/`](docs/) | архитектура, статусы, источники и правила пополнения |

## Что уже проверено

| Артефакт | Текущее состояние |
|---|---:|
| Failure cards | 41 |
| Карточки со статусом `production-tested` | 15 |
| Semgrep rules | 16 |
| Rules со статусом `production-tested` | 2 |
| Rules со статусом `fixture-tested` | 11 |
| Rules со статусом `draft` | 3 |
| Fixtures | 3 проекта, 16 посаженных ошибок |
| Forward tests | 3 раунда |
| Hook acceptance | 14/14 assertions |
| GitHub CI | включен |

Подробности лежат в [docs/STATUS.md](docs/STATUS.md),
[docs/CHECKERS.md](docs/CHECKERS.md) и
[docs/EVIDENCE_LOG.md](docs/EVIDENCE_LOG.md).

## Какие риски покрыты

| Область | Что проверяется |
|---|---|
| API | совместимость контрактов, DTO, статусы, ошибки, webhooks |
| Auth и tenancy | BOLA, утечки между tenant'ами, роли, PII, секреты, SSRF |
| Данные | SQL injection, транзакции, миграции, индексы, N+1 |
| Надежность | таймауты, retry, jitter, cancellation, очереди, idempotency |
| Наблюдаемость | request/job correlation, метрики без взрыва labels, redaction |
| Тесты | failure-path tests, DB integration tests, contract diffs, migration proof |
| Языки | Python async/exceptions, Go context/goroutines/errors, TypeScript runtime boundaries |

## Установка

Скопируйте скилл в проект, где работает Claude Code:

```bash
mkdir -p /path/to/your-project/.claude/skills
cp -R .claude/skills/backend-craft /path/to/your-project/.claude/skills/
```

Semgrep-пак (`rules/`) и hook (`hooks/`) лежат вне папки скилла и копируются
отдельно — они нужны, только если вы хотите механические проверки и подсказки
после правок. Сам скилл работает и без них.

Дальше можно просить агента работать с ним явно:

```text
Use backend-craft to review this backend for production risks.
```

```text
Use backend-craft to design the backend foundation for a small B2B SaaS.
```

```text
Use backend-craft while adding this mutating endpoint. Clients may retry.
```

## Hook

В [hooks/](hooks/) есть необязательный hook. Он запускается после правки файла и
дает агенту короткие замечания по измененному backend-коду.

| Свойство | Поведение |
|---|---|
| Режим | только советует |
| Exit code | всегда `0`, чтобы не ломать работу агента |
| Лимит | максимум 5 замечаний за событие |
| Dedup | одно и то же замечание показывается один раз за session |
| Приоритет | сначала локальные проверки проекта, потом Semgrep |
| Ограничение | тишина от hook не значит, что backend безопасен |

Как подключить: [hooks/README.md](hooks/README.md).

## Локальные проверки

| Проверка | Команда |
|---|---|
| Форма репозитория | `uv run --with pyyaml python scripts/validate_repo.py` |
| Python fixture | `cd fixtures/python-fastapi && uv run pytest -q` |
| Go fixture | `cd fixtures/go-http && go vet ./... && go test ./...` |
| TypeScript fixture | `cd fixtures/ts-fastify && pnpm install --frozen-lockfile && pnpm typecheck && pnpm test` |
| Semgrep pack | `uvx semgrep --config rules/semgrep/backend-craft.yml --no-git-ignore --exclude node_modules .` |
| Hook acceptance | `hooks/test-hook.sh` |

GitHub Actions запускает эти проверки в
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Как развивать

`v0.1` заморожен. Это значит: не добавлять новые языки, очереди, базы данных и
большие разделы просто потому, что они полезны.

Новая информация попадает в скилл только если из нее получается хотя бы одно:

- failure card;
- verifier;
- checker;
- шаг playbook со ссылкой на источник.

Реальные кейсы нужно прогонять через
[docs/CASE_PIPELINE.md](docs/CASE_PIPELINE.md). Общие советы вроде "обрабатывай
ошибки аккуратно" не принимаются.

## Как помочь

Если вы хотите присоединиться, начните с
[docs/CONTRIBUTOR_GUIDE.md](docs/CONTRIBUTOR_GUIDE.md).
Широкие идеи лучше сначала принести в
[Discussions](https://github.com/OnlyNinjaGear/backend-craft/discussions), а
конкретные кейсы — в issue по шаблону.

Самые полезные вклады:

- реальный backend-кейс с анонимизированным reducer;
- официальный источник, который дает конкретный verifier;
- checker с false-positive boundary;
- fixture, которую можно запустить в CI;
- слепой forward test.

## Документация

| Документ | Что там |
|---|---|
| [docs/README.md](docs/README.md) | короткая навигация |
| [docs/STATUS.md](docs/STATUS.md) | готовность, coverage matrix и следующие релизные ворота |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | почему скилл устроен как router, а не как набор языковых шпаргалок |
| [FAILURE_CARDS.md](FAILURE_CARDS.md) | карточки backend-ошибок |
| [docs/CHECKERS.md](docs/CHECKERS.md) | статусы Semgrep rules и проверок |
| [docs/SOURCES.md](docs/SOURCES.md) | источники, которые можно использовать |
| [docs/FORWARD_TESTS.md](docs/FORWARD_TESTS.md) | как проводить слепые тесты |
| [docs/CASE_PIPELINE.md](docs/CASE_PIPELINE.md) | как превращать реальные баги в материал для скилла |
| [docs/BACKGROUND_WORKER.md](docs/BACKGROUND_WORKER.md) | prompt для Claude Cowork / Claude Code routine |
| [docs/CONTRIBUTOR_GUIDE.md](docs/CONTRIBUTOR_GUIDE.md) | как разработчикам помочь проекту |
| [docs/WRITING_STYLE.md](docs/WRITING_STYLE.md) | как писать тексты без шаблонного тона |

## Что не входит в v0.1

| Тема | Почему отложена |
|---|---|
| Flyway / Liquibase | Java/JVM scope пока не открыт |
| Kafka consumer semantics | event-stream scope пока не открыт |
| Sidekiq-class queues | Ruby/Rails scope пока не открыт |
| Redis/BullMQ runtime semantics | есть рекомендация по выбору, но нет отдельного fixture и failure suite |
| Kubernetes и deployment platform | infrastructure scope пока не открыт |
| MongoDB и Django/DRF fixtures | есть documented guidance, но нет отдельной runnable проверки |
| Новые `production-tested` promotions | нужны подходящие реальные backend-кейсы |
| Отдельные языковые скиллы | пока router-модель проходит forward tests |
