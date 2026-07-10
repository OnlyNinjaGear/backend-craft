# backend-craft

[![CI](https://github.com/OnlyNinjaGear/backend-craft/actions/workflows/ci.yml/badge.svg)](https://github.com/OnlyNinjaGear/backend-craft/actions/workflows/ci.yml)
![Status](https://img.shields.io/badge/status-v0.1%20frozen-blue)
![Rules](https://img.shields.io/badge/semgrep-13%20rules-2ea44f)
![Fixtures](https://img.shields.io/badge/fixtures-16%20planted%20flaws-orange)

[English README](README.en.md)

`backend-craft` — универсальный backend-safety skill для Claude Code/Codex.
Он помогает агенту не писать правдоподобный backend-код, который ломается в
production: утечки tenant-данных, небезопасные миграции, повторные платежи,
retry-storm, потерянные фоновые задачи, невалидные API-контракты и похожие
ошибки.

Это **не** шпаргалка "пиши хорошо". Скилл сначала определяет поверхность риска,
а потом подключает нужные reference-файлы и языковой адаптер.

## Коротко

| Вопрос | Ответ |
|---|---|
| Что это? | Skill-пакет для backend-разработки и ревью агентами Claude Code/Codex |
| Для кого? | Для проектов на Python, Go, TypeScript/Node с Postgres/MongoDB и типовыми backend-рисками |
| Как устроен? | Один router skill + reference packs по production failure surfaces |
| Текущий статус | `v0.1 frozen`: разработка остановлена, расширение только по явному решению владельца |
| Проверено | 3 раунда forward tests, fixtures, Semgrep baseline, hook acceptance, real-backend validation |

## Какие риски закрывает

| Поверхность | Примеры провалов, которые скилл заставляет проверять |
|---|---|
| API contracts | несовместимые изменения, публичные DTO, ошибки/статусы, webhooks |
| Auth / tenancy | BOLA, tenant leaks, role mistakes, PII/secrets/logging, SSRF |
| Persistence | SQL injection, транзакции вокруг network calls, unsafe DDL, N+1 |
| Reliability | timeouts, retries, jitter, cancellation, queues, workers, idempotency |
| Observability | request/job correlation, bounded metric labels, redaction |
| Testing | failure-path tests, DB integration tests, contract diffs, migration proof |
| Language adapters | Python async/exceptions, Go context/goroutines/errors, TS runtime boundaries |

## Что внутри

| Путь | Назначение |
|---|---|
| [`.claude/skills/backend-craft/`](.claude/skills/backend-craft/) | сам installable skill |
| [`FAILURE_CARDS.md`](FAILURE_CARDS.md) | база failure cards |
| [`rules/semgrep/backend-craft.yml`](rules/semgrep/backend-craft.yml) | Semgrep-пак для механически ловимых паттернов |
| [`hooks/`](hooks/) | optional PostToolUse hook, advisory-only |
| [`fixtures/`](fixtures/) | три специально сломанных backend-манекена |
| [`forward-test-results/`](forward-test-results/) | результаты экзаменов скилла |
| [`docs/`](docs/) | архитектура, evidence log, sources, статус |

## Статус v0.1

| Артефакт | Статус |
|---|---:|
| Failure cards | 39 |
| Production-tested cards | 15 |
| Semgrep rules | 13 |
| Production-tested Semgrep rules | 2 |
| Fixture-tested Semgrep rules | 11 |
| Draft Semgrep rules | 0 |
| Fixtures | 3 проекта, 16 planted flaws |
| Forward tests | 3 раунда |
| Hook acceptance | 14/14 assertions |
| GitHub CI | включён |

Подробности: [docs/STATUS.md](docs/STATUS.md), [docs/CHECKERS.md](docs/CHECKERS.md),
[docs/EVIDENCE_LOG.md](docs/EVIDENCE_LOG.md).

## Установка

Скопируйте skill в проект, где работает Claude Code:

```bash
mkdir -p /path/to/your-project/.claude/skills
cp -R .claude/skills/backend-craft /path/to/your-project/.claude/skills/
```

После этого используйте в запросах:

```text
Use backend-craft to review this backend for production risks.
```

```text
Use backend-craft to design the backend foundation for a small B2B SaaS.
```

```text
Use backend-craft while adding this mutating endpoint. Clients may retry.
```

## Optional hook

В [hooks/](hooks/) есть PostToolUse hook, который после edit/write запускает
лёгкие проверки по изменённому backend-файлу:

| Свойство | Поведение |
|---|---|
| Режим | advisory-only |
| Exit code | всегда `0`, не блокирует работу агента |
| Лимит | максимум 5 findings за событие |
| Dedup | одно и то же замечание показывается один раз за session |
| Приоритет | сначала project-local tools, затем Semgrep gap-filler |
| Важное ограничение | чистый checker run не означает, что backend безопасен |

Инструкция подключения: [hooks/README.md](hooks/README.md).

## Проверки локально

| Проверка | Команда |
|---|---|
| Sanity репозитория | `uv run --with pyyaml python scripts/validate_repo.py` |
| Python fixture | `cd fixtures/python-fastapi && uv run pytest -q` |
| Go fixture | `cd fixtures/go-http && go vet ./... && go test ./...` |
| TypeScript fixture | `cd fixtures/ts-fastify && pnpm install --frozen-lockfile && pnpm typecheck && pnpm test` |
| Semgrep baseline | `uvx semgrep --config rules/semgrep/backend-craft.yml --no-git-ignore --exclude node_modules .` |
| Hook acceptance | `hooks/test-hook.sh` |

GitHub Actions повторяет основные проверки в [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Как читать документацию

| Документ | Зачем нужен |
|---|---|
| [docs/README.md](docs/README.md) | навигация по документации |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | почему skill устроен как router, а не набор языковых шпаргалок |
| [FAILURE_CARDS.md](FAILURE_CARDS.md) | атомарные failure cards |
| [docs/CHECKERS.md](docs/CHECKERS.md) | статусы Semgrep rules и real-backend validation |
| [docs/SOURCES.md](docs/SOURCES.md) | какие официальные источники допущены и зачем |
| [docs/FORWARD_TESTS.md](docs/FORWARD_TESTS.md) | методика forward-тестирования |
| [fixtures/README.md](fixtures/README.md) | intentionally flawed fixtures |

## Что не входит в v0.1

Это намеренно отложено в backlog:

| Тема | Почему не сейчас |
|---|---|
| Flyway / Liquibase | JVM/Java scope не открыт |
| Kafka consumer semantics | event-stream scope не открыт |
| Sidekiq-class queues | Ruby/Rails scope не открыт |
| Новые production-tested promotions | делать только когда появится подходящий реальный backend |
| Разделение на языковые skills | только если будущие forward tests докажут, что router-модель недостаточна |

## Граница проекта

Новые знания добавляются только если они дают одно из:

- failure card;
- verifier;
- checker;
- source-backed playbook step.

Общие советы вида "пишите безопасно" или "обрабатывайте ошибки хорошо" сюда не
принимаются.
