# Среда разработки

## Языки и IDE

| Часть | Язык | Основное |
|---|---|---|
| backend | Python 3.12 | FastAPI, SQLAlchemy 2, Alembic, pytest |
| frontend | TypeScript 5.6 | React 18, Vite, React Flow, Vitest |
| БД | SQL (PostgreSQL 16) | миграции Alembic, psql |

IDE — **VS Code**. Одно окно на оба языка: Python и TypeScript поддерживаются расширениями, отладчик один, в нём же открываются PlantUML- и BPMN-диаграммы из `docs/`. Рассматривал PyCharm: для TypeScript пришлось бы держать отдельную WebStorm. Cursor отпал, потому что это отдельная сборка VS Code и настройки проекта пришлось бы дублировать.

## Что лежит в репозитории

| Файл | Зачем |
|---|---|
| `.editorconfig` | UTF-8, LF, перевод строки в конце файла, отступ 4 для Python и 2 для TS/JSON/YAML |
| `.vscode/settings.json` | форматирование при сохранении, Ruff для Python, Prettier для TS и JSON, линейки 110 (Python) и 100 (TS), pytest в панели тестов |
| `.vscode/extensions.json` | рекомендованные расширения, VS Code сам предлагает их поставить |
| `.vscode/launch.json` | отладка: API под uvicorn, pytest, фронтенд в Chrome |
| `.vscode/tasks.json` | задачи: проверки и тесты backend и frontend, все хуки pre-commit |
| `.pre-commit-config.yaml` | хуки перед коммитом и проверка сообщения коммита |
| `backend/pyproject.toml` | Ruff, mypy, Pylint, pytest и coverage |
| `frontend/eslint.config.js`, `frontend/.prettierrc.json` | ESLint (typescript-eslint strict, react-hooks, SonarJS) и Prettier |
| `frontend/vite.config.ts` | Vitest: jsdom, покрытие v8, порог 90 % |

## Расширения

| Расширение | Для чего |
|---|---|
| Python, Python Debugger (`ms-python.python`, `ms-python.debugpy`) | интерпретатор из `backend/.venv`, запуск и отладка, панель тестов pytest |
| Ruff (`charliermarsh.ruff`) | линтер и форматтер Python прямо в редакторе |
| Mypy Type Checker (`ms-python.mypy-type-checker`) | ошибки типов при сохранении |
| ESLint (`dbaeumer.vscode-eslint`) | замечания ESLint и SonarJS в редакторе |
| Prettier (`esbenp.prettier-vscode`) | форматирование TS, JSON, CSS |
| Vitest (`vitest.explorer`) | тесты фронтенда в панели тестов |
| PlantUML (`jebbs.plantuml`) | предпросмотр C4- и ER-диаграмм |
| BPMN Editor (`bpmn-io.vs-code-bpmn-io`) | редактирование `docs/bpmn/*.bpmn` |

Все они перечислены в `.vscode/extensions.json`. VS Code предлагает их при открытии папки, из терминала то же самое делает `code --install-extension <id>`.

## Горячие клавиши и тема

Тема — Default Dark Modern. Сочетания клавиш хранятся в пользовательском `keybindings.json`, а не в репозитории (VS Code не читает их из папки проекта). У меня они привязаны к задачам из `tasks.json`:

| Клавиши | Задача |
|---|---|
| `Ctrl+Alt+T` | backend: тесты |
| `Ctrl+Alt+L` | backend: проверки (ruff, ruff format, mypy, pylint) |
| `Ctrl+Alt+Y` | frontend: тесты |
| `Ctrl+Alt+K` | frontend: проверки (ESLint) |
| `Ctrl+Alt+P` | pre-commit: все файлы |

```json
[
  { "key": "ctrl+alt+t", "command": "workbench.action.tasks.runTask", "args": "backend: тесты" },
  { "key": "ctrl+alt+l", "command": "workbench.action.tasks.runTask", "args": "backend: проверки" },
  { "key": "ctrl+alt+y", "command": "workbench.action.tasks.runTask", "args": "frontend: тесты" },
  { "key": "ctrl+alt+k", "command": "workbench.action.tasks.runTask", "args": "frontend: проверки" },
  { "key": "ctrl+alt+p", "command": "workbench.action.tasks.runTask", "args": "pre-commit: все файлы" }
]
```

Остальное стандартное: `F5` — отладка по выбранной конфигурации, `Shift+Alt+F` — отформатировать файл, `Ctrl+Shift+P` → «Tasks: Run Task» — любая задача.

## Как поднять рабочее место

```bash
git clone https://github.com/Howksss/pult.git && cd pult
cd backend && python -m venv .venv && .venv/Scripts/activate   # Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cd .. && pre-commit install
cd frontend && npm ci
```

В VS Code: принять рекомендованные расширения, выбрать интерпретатор `backend/.venv` (Python: Select Interpreter). Задачи `.vscode/tasks.json` берут Python из выбранного интерпретатора.

Тесты на PostgreSQL (`test_pg_*`) запускаются, только если задан `TEST_DATABASE_URL` с базой после `alembic upgrade head`. Без него они пропускаются, в CI идут всегда.
