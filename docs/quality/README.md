# Качество кода

| Что проверяется | Backend | Frontend | Где запускается |
|---|---|---|---|
| Стиль и типовые ошибки | Ruff (E, W, F, I, B, UP, SIM, N, S, RUF) | ESLint 9, typescript-eslint strict, react-hooks | pre-commit, CI |
| Форматирование | `ruff format` | Prettier | при сохранении в VS Code, pre-commit, CI |
| Типы | mypy, strict, плагин pydantic | `tsc -b`, strict | CI |
| Статический анализ | Pylint + mccabe (сложность ≤ 8), CodeQL | SonarJS (правила recommended в ESLint), CodeQL | CI, SonarJS ещё и в pre-commit |
| Тесты и покрытие | pytest + pytest-cov, порог 90 % с ветвлениями | Vitest + Testing Library, порог 90 % для компонентов | CI |
| Сообщения коммитов | commitlint, Conventional Commits | | хук `commit-msg`, CI (задание `commits`) |
| Общие проверки | пробелы, перевод строки в конце файла, YAML и TOML, маркеры конфликтов, крупные файлы, приватные ключи | | pre-commit, CI (задание `hooks`) |

Все четыре задания CI (`backend`, `frontend`, `hooks`, `commits`) обязательны для слияния в main ([правила](../process/branching.md)).

Настройка рабочего места:

```bash
cd backend && python -m venv .venv && .venv/Scripts/activate
pip install -r requirements-dev.txt
cd .. && pre-commit install
cd frontend && npm install
```

В VS Code: рекомендованные расширения из `.vscode/extensions.json`, конфигурации отладки «API (uvicorn)», «Тесты backend (pytest)» и «Frontend (Chrome)» в `.vscode/launch.json`.

Документы: [тест-план](test-plan.md), [работа с ИИ-ассистентами](ai-assistants.md), [отчёты модуля 4](../module4/README.md).
