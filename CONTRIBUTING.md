# Как вносить изменения

`backend-craft v0.1` заморожен. По умолчанию репозиторий принимает только
исправления, упаковку и доказательства к уже существующим карточкам.

Новые области, языки, библиотеки и большие rule families требуют отдельного
решения владельца до начала работы.

## Что можно делать без расширения scope

- исправлять ошибки в существующих инструкциях, checkers, fixtures или hook;
- улучшать README и документацию;
- чинить CI и упаковку;
- добавлять новые доказательства к существующей failure card;
- уточнять источники, если они меняют конкретное правило или verifier.

Если вы пришли с новым кейсом, начните с
[docs/CONTRIBUTOR_GUIDE.md](docs/CONTRIBUTOR_GUIDE.md). Для фоновой работы через
Claude используйте [docs/BACKGROUND_WORKER.md](docs/BACKGROUND_WORKER.md).

## Что не принимается

- общие советы без проверяемого failure mode;
- новые темы "на всякий случай";
- копипаста из документации без вывода в card, verifier или checker;
- большие переписывания скилла без слепого теста.

## Планка для нового знания

Материал может попасть в скилл только если дает хотя бы одно:

- failure card;
- verifier;
- checker;
- шаг playbook со ссылкой на источник.

Процесс описан в [docs/CASE_PIPELINE.md](docs/CASE_PIPELINE.md).

## Стиль текста

Перед правкой README, docs или комментариев прочитайте
[docs/WRITING_STYLE.md](docs/WRITING_STYLE.md).

Коротко: пишите как инженер, который отвечает за результат. Без маркетинга.
Без внутренних заметок для владельца. Без фраз, которые не помогают принять
решение.

## Проверки

Минимум перед PR:

```bash
uv run --with pyyaml python scripts/validate_repo.py
hooks/test-hook.sh
```

Если менялись fixtures или rules, запустите релевантные проверки:

```bash
cd fixtures/python-fastapi && uv run pytest -q
cd ../go-http && go vet ./... && go test ./...
cd ../ts-fastify && pnpm install --frozen-lockfile && pnpm typecheck && pnpm test
```
