# Документация backend-craft

Здесь лежат документы вокруг скилла: архитектура, evidence, источники,
протоколы проверки и frozen-status. Сам installable skill находится в
`.claude/skills/backend-craft/`.

## С чего начать

| Документ | Что внутри |
|---|---|
| [STATUS.md](STATUS.md) | frozen v0.1 status и backlog |
| [ARCHITECTURE.md](ARCHITECTURE.md) | почему выбран router skill + risk references |
| [../FAILURE_CARDS.md](../FAILURE_CARDS.md) | база failure cards |
| [SOURCES.md](SOURCES.md) | карта официальных источников |

## Проверка и доказательства

| Документ | Что проверяет |
|---|---|
| [CHECKERS.md](CHECKERS.md) | Semgrep pack, rule statuses, real-backend validation |
| [FORWARD_TESTS.md](FORWARD_TESTS.md) | protocol для blind forward tests |
| [EVIDENCE_LOG.md](EVIDENCE_LOG.md) | журнал promotion/retirement карточек и правил |
| [../fixtures/README.md](../fixtures/README.md) | intentionally flawed fixtures |

## Исторические заметки

| Документ | Контекст |
|---|---|
| [ANATOMY.md](ANATOMY.md) | ранние anatomy/review notes |
| [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md) | frozen handoff/backlog record |
