# Документация

Здесь не сам скилл, а материалы вокруг него: как он устроен, чем проверен и как
его можно менять без превращения в набор советов обо всем.

Сам скилл лежит в [../.claude/skills/backend-craft/](../.claude/skills/backend-craft/).

## Начать отсюда

| Документ | Зачем читать |
|---|---|
| [STATUS.md](STATUS.md) | что входит в `v0.1` и что намеренно не входит |
| [ARCHITECTURE.md](ARCHITECTURE.md) | почему выбран один router skill |
| [../FAILURE_CARDS.md](../FAILURE_CARDS.md) | список ошибок, на которых держится скилл |
| [SOURCES.md](SOURCES.md) | какие источники можно использовать как опору |

## Проверки

| Документ | Что описывает |
|---|---|
| [CHECKERS.md](CHECKERS.md) | Semgrep rules, статусы и real-backend validation |
| [FORWARD_TESTS.md](FORWARD_TESTS.md) | как проводить слепые проверки скилла |
| [EVIDENCE_LOG.md](EVIDENCE_LOG.md) | почему карточки и правила получили свой статус |
| [../fixtures/README.md](../fixtures/README.md) | намеренно сломанные fixtures |

## Как менять проект

| Документ | Что задает |
|---|---|
| [CASE_PIPELINE.md](CASE_PIPELINE.md) | как превращать реальные баги в карточки, проверки и tests |
| [BACKGROUND_WORKER.md](BACKGROUND_WORKER.md) | prompt для фонового Claude worker'а |
| [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md) | как внешним разработчикам помогать проекту |
| [WRITING_STYLE.md](WRITING_STYLE.md) | как писать README, docs и комментарии |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | правила для PR и локальные проверки |
| [../SECURITY.md](../SECURITY.md) | как сообщать о проблемах безопасности |

## История

| Документ | Что это |
|---|---|
| [ANATOMY.md](ANATOMY.md) | ранний разбор формы скиллов |
| [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md) | handoff после заморозки `v0.1` |
