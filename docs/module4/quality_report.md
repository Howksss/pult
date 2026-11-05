# Качество кода: форматтеры, линтеры, статический анализ

Прогон 27.10.2026, ветка main после #78. Сырые логи лежат в [reports/](reports).

## Инструменты

| Что | Backend (Python) | Frontend (TypeScript) |
|---|---|---|
| Форматтер | `ruff format` | Prettier, ширина 100 |
| Линтер | Ruff: правила E, W, F, I, B, UP, SIM, N, S (bandit), RUF | ESLint 9: recommended, typescript-eslint strict, react-hooks |
| Статический анализ | mypy strict, Pylint 4.1.3 + mccabe, CodeQL | SonarJS (295 правил recommended), `tsc` strict, CodeQL |
| Перед коммитом | pre-commit: ruff, ruff-format, общие хуки, commitlint | pre-commit: eslint, prettier |
| В CI | все перечисленные, задания `backend`, `frontend`, `hooks`, `commits` | |

Где что настроено, описано в [environment_setup.md](environment_setup.md).

## Форматирование

Форматтеры применены ко всему коду, проверка в CI падает, если хоть один файл отформатирован иначе:

```
$ cd backend && ruff format --check .
43 files already formatted

$ cd frontend && npx prettier --check .
Checking formatting...
All matched files use Prettier code style!
```

## Линтеры

```
$ cd backend && ruff check .
All checks passed!

$ cd frontend && npx eslint . --max-warnings 0
(пусто, код выхода 0)
```

Ruff, ESLint и pre-commit настроены в задаче #17. С тех пор каждая правка проходит их в pre-commit и CI, поэтому замечаний нет. Правила RUF001–RUF003 отключены: они ругаются на кириллицу в строках, а интерфейс и сообщения на русском.

## Проверка перед коммитом

Хуки ставятся командой `pre-commit install`, конфигурация в `.pre-commit-config.yaml`. На этапе `pre-commit` запускаются общие хуки (пробелы в конце строк, перевод строки в конце файла, YAML/TOML, маркеры конфликтов, крупные файлы, приватные ключи), Ruff и `ruff format` для `backend/`, ESLint и Prettier для `frontend/`. На этапе `commit-msg` commitlint проверяет формат Conventional Commits.

Проверка, что коммит действительно блокируется ([reports/precommit_blocked.txt](reports/precommit_blocked.txt)):

1. Файл с неотформатированным кодом и лишним импортом. Ruff удалил импорт и нашёл `E701` (две инструкции в одной строке), `ruff format` переформатировал файл. Коммит не создан, код выхода 1.
2. Сообщение «поправил всякое» без типа. commitlint вернул `subject-empty` и `type-empty`, коммит не создан.

## Статический анализ

### Pylint

Первый прогон с настройками по умолчанию: **185 замечаний, 6.89/10** ([reports/pylint_before.txt](reports/pylint_before.txt)).

| Замечание | Кол-во | Решение |
|---|---|---|
| `missing-module/class/function-docstring` | 101 | Отключено. В проекте нет докстрингов: имена говорящие, а объяснения живут в `docs/` и ADR |
| `invalid-name` | 41 | Все 41 — члены enum в нижнем регистре (`ok`, `warn`, `fail`). Значения совпадают с enum в PostgreSQL и с API, поэтому `class-const-naming-style = "any"` |
| `line-too-long` | 25 | У Pylint по умолчанию 100, у Ruff в проекте 110. Выставлено `max-line-length = 110` |
| `too-few-public-methods` | 15 | ORM-модели и схемы Pydantic — это данные, а не поведение. Отключено |
| `unnecessary-comprehension` | 2 | **Исправлено**: `{k: v for k, v in rows}` → `dict(...)` в `api/probe.py` |
| `too-many-locals` | 1 | **Исправлено рефакторингом**: в `submit_results` было 18 локальных переменных при пороге 15 |

После настройки остались только три настоящих замечания, все в `submit_results`. Функция разбита на три шага: `owned_checks` (проверка, что проверки принадлежат проекту), `record_results` (статусы до, запись, статусы после, commit) и `notify` (уведомления в Telegram). Сам обработчик стал читаться как сценарий из четырёх строк. Рефакторинг делался с ИИ-ассистентом и проверялся вручную, подробности в [ai_usage_and_risks.md](ai_usage_and_risks.md).

Итог: **10.00/10** ([reports/pylint_after.txt](reports/pylint_after.txt)). Подключён mccabe с порогом сложности 8, функций сложнее нет. Pylint добавлен в задание `backend` в CI.

В CI на Python 3.12 Pylint выдал ещё 23 × `E1136 unsubscriptable-object` на `Mapped[...]` в `app/models/graph.py`. Локально на Python 3.13 этого нет. Это ложное срабатывание astroid на типе SQLAlchemy, а подписки и так проверяет mypy strict, поэтому проверка отключена (коммит 0ee46da, обсуждение в #78).

### mypy

`mypy` в режиме strict с плагином pydantic: `Success: no issues found in 25 source files`. Он же поймал ошибку в черновике рефакторинга, который предложил ИИ (см. ai_usage_and_risks.md).

### SonarJS

Плагин `eslint-plugin-sonarjs` 4.2.2 подключён в `frontend/eslint.config.js`. Активно 295 правил из набора recommended: когнитивная сложность, дублирование, подозрительные конструкции, уязвимые шаблоны. На 22 файлах замечаний **0** ([reports/eslint_sonarjs.txt](reports/eslint_sonarjs.txt)). Плагин остаётся в `npm run lint`, то есть в pre-commit и CI.

### CodeQL

CodeQL (GitHub code scanning) проверяет Python и TypeScript в CI с задачи #45. На 27.10 было открыто 12 замечаний уровня note, все `py/unused-global-variable` в `backend/migrations/versions/*.py` ([reports/codeql_alerts.txt](reports/codeql_alerts.txt)):

```
#1  note  py/unused-global-variable  backend/migrations/versions/0001_initial_schema.py:7  The global variable 'revision' is not used.
...
#12 note  py/unused-global-variable  backend/migrations/versions/0003_probe_token.py:9  The global variable 'depends_on' is not used.
```

Все 12 ложные: переменные `revision`, `down_revision`, `branch_labels` и `depends_on` читает Alembic, когда строит цепочку миграций. Закрыты как false positive с этим объяснением. Каждая новая миграция будет давать такие же замечания, их нужно закрывать так же.

## Итог

| Проверка | До | После |
|---|---|---|
| Pylint | 185 замечаний, 6.89/10 | 0, 10.00/10 |
| mypy strict | 0 | 0 |
| Ruff | 0 | 0 |
| ESLint + SonarJS | SonarJS не было | 0 из 295 правил |
| CodeQL | 12 открытых (note) | 0 открытых, 12 закрыты как ложные |
