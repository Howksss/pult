# Pult

Pult — пульт сопровождения небольших production-систем. Систему клиента он показывает графом блоков: сервер, задания по расписанию, боты, внешние API, конфигурация. Каждый блок горит своим статусом. По клику на блок открывается чат с ИИ-агентом. Агенту доступны файлы только этого блока, а правки он предлагает через pull request, который проверяет человек.

**Какую проблему решает.** Сейчас при сбое клиент пишет разработчику в мессенджер, и тот вручную ищет по логам на сервере, что сломалось. Pult сразу показывает сломанный блок и даёт поставить задачу именно на него. Разработчик получает готовую правку с тестами, а не текст в чате.

**Для кого.** Для владельцев малого бизнеса с собственной автоматизацией (скрипты, боты, интеграции с учётной системой) и для разработчиков, которые такую автоматизацию сопровождают.

**Пилотная система** — автопланирование выпечки для небольшой сети пекарен. Она работает на VPS по cron, берёт продажи из POS-системы, учитывает погоду и праздники, собирает Excel-планы и рассылает их через Telegram-бота. Код пилотной системы лежит в отдельном закрытом репозитории и сюда не входит.

## Команда

| Участник | Роли |
|---|---|
| [@Howksss](https://github.com/Howksss) | руководитель проекта, аналитик, архитектор, разработчик, тестировщик, специалист по развертыванию |

## Трекер задач

GitHub Issues: https://github.com/Howksss/pult/issues

## Технологический стек

| Слой | Технологии |
|---|---|
| Frontend | React 18, TypeScript, Vite, React Flow (`@xyflow/react`) |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings |
| База данных | PostgreSQL 16 |
| ИИ-агент | Claude API (`anthropic` SDK, модель `claude-opus-5-5`), инструменты с ограничением по блоку |
| Инфраструктура | Docker, Docker Compose, GitHub Actions |
| Моделирование | PlantUML (C4, ER), BPMN 2.0 (bpmn.io) |
| Тестирование API | Bruno |

## Архитектура

Модульный монолит: одна кодовая база на FastAPI запускается в двух ролях. Процесс `api` обслуживает Web UI и принимает статусы от probe. Процесс `worker` выполняет задачи агента и собирает статусы. Очередь задач и все данные хранятся в PostgreSQL. Агент правит код клиента только в отдельной ветке и открывает pull request, а на сервер правка попадает через CI/CD после одобрения человеком.

![Контейнеры](docs/architecture/container_diagram.png)

## Документация

| Артефакт | Файл |
|---|---|
| Процессы As-Is и To-Be, узкие места, точки автоматизации | [docs/bpmn/README.md](docs/bpmn/README.md) |
| Схема текущего процесса (BPMN) | [docs/bpmn/as_is.bpmn](docs/bpmn/as_is.bpmn), [png](docs/bpmn/as_is.png) |
| Схема целевого процесса (BPMN) | [docs/bpmn/to_be.bpmn](docs/bpmn/to_be.bpmn), [png](docs/bpmn/to_be.png) |
| Функциональные требования | [docs/requirements/functional.md](docs/requirements/functional.md) |
| Нефункциональные требования | [docs/requirements/non_functional.md](docs/requirements/non_functional.md) |
| Контекстная диаграмма (C4, уровень 1) | [docs/architecture/context_diagram.puml](docs/architecture/context_diagram.puml), [png](docs/architecture/context_diagram.png) |
| Контейнеры (C4, уровень 2) | [docs/architecture/container_diagram.puml](docs/architecture/container_diagram.puml), [png](docs/architecture/container_diagram.png) |
| ER-диаграмма и нормализация | [docs/data/README.md](docs/data/README.md), [er_diagram.puml](docs/data/er_diagram.puml), [png](docs/data/er_diagram.png) |
| Журнал архитектурных решений | [docs/adr](docs/adr) |

## Структура репозитория

```
backend/     FastAPI-приложение и тесты
frontend/    React-приложение с графом блоков
deploy/      docker-compose для локального запуска
docs/        требования, модели процессов, архитектура, ADR
```

## Локальный запуск

```bash
cp .env.example .env

cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
curl http://localhost:8000/api/health

cd ../frontend
npm install
npm run dev
```

Все сервисы в контейнерах: `docker compose -f deploy/docker-compose.yml up --build`.
