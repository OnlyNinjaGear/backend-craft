# Как помочь проекту

`backend-craft` растет не через списки советов. Нужны маленькие, проверяемые
улучшения.

## Что можно принести

| Вклад | Хороший пример |
|---|---|
| Реальный кейс | "агент добавил endpoint и забыл idempotency key; вот reducer и test idea" |
| Source digestion | "в Fastify hooks есть encapsulation; вот failure mode и verifier" |
| Failure card | короткая карточка с situation, failure, blast radius, safe pattern, verifier |
| Checker | Semgrep/ast-grep rule с false-positive boundary и fixture |
| Fixture | маленький проект или файл, где ошибка воспроизводится |
| Forward test | prompt и результат слепого прогона |
| Документация | правка, которая делает репозиторий понятнее без новых обещаний |

## С чего начать

1. Прочитайте [README.md](../README.md).
2. Прочитайте [docs/CASE_PIPELINE.md](CASE_PIPELINE.md).
3. Проверьте [FAILURE_CARDS.md](../FAILURE_CARDS.md), чтобы не дублировать
   существующую карточку.
4. Откройте issue по шаблону.
5. Дождитесь короткого согласования scope, если тема новая.

## Какие issue открывать

| Шаблон | Когда использовать |
|---|---|
| Real backend case | есть баг, PR, incident или ошибка агента |
| Source digestion | есть официальный документ или tool docs |
| Checker proposal | есть механический паттерн для Semgrep/ast-grep/hook |

Не открывайте issue вида "добавить best practices по X". Сначала нужен
failure mode.

Если идея широкая, начните с
[GitHub Discussions](https://github.com/OnlyNinjaGear/backend-craft/discussions).
После обсуждения ее можно сузить до case, source или checker issue.

## Что должно быть в PR

Хороший PR отвечает на вопросы:

- какую ошибку он предотвращает;
- где эта ошибка встречается;
- почему существующих cards недостаточно;
- чем это проверено;
- где граница правила;
- какие команды запускались.

Если PR меняет card/rule status, обновите [docs/EVIDENCE_LOG.md](EVIDENCE_LOG.md).

## Минимальная проверка

```bash
uv run --with pyyaml python scripts/validate_repo.py
hooks/test-hook.sh
```

Если менялись fixtures или checker rules, запустите соответствующий fixture:

```bash
cd fixtures/python-fastapi && uv run pytest -q
cd ../go-http && go vet ./... && go test ./...
cd ../ts-fastify && pnpm install --frozen-lockfile && pnpm typecheck && pnpm test
```

## Как писать

Пишите коротко. Не продавайте проект. Не добавляйте внутренние TODO в публичные
документы. Правила стиля лежат в [docs/WRITING_STYLE.md](WRITING_STYLE.md).

## Что будет отклонено

- материал без verifier;
- длинная выжимка из документации;
- новая область без согласованного scope;
- checker без false-positive boundary;
- fixture, которую нельзя запустить;
- PR, где много тем сразу.
