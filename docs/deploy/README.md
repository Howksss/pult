# Контейнеры и развёртывание

## Образы

| Образ | Сборка | Запуск |
|---|---|---|
| `pult-backend` | Двухэтапная: на этапе `build` собираются wheels зависимостей, в итоговый образ `python:3.12-slim` попадают только они, `app`, `migrations` и `alembic.ini` | Пользователь `pult` (uid 10001), не root. `HEALTHCHECK` опрашивает `/api/health` |
| `pult-frontend` | Двухэтапная: `npm ci` и `vite build` в `node:20-alpine`, в итоговый образ попадает только `dist` | `nginx-unprivileged` на порту 8080 без root. `/api/` проксируется в `api:8000`, остальные пути отдают SPA |

`.dockerignore` исключает из контекста сборки виртуальные окружения, `node_modules`, кэши и тесты.

## Окружение целиком: `deploy/docker-compose.yml`

```
db (PostgreSQL 16, healthcheck pg_isready)
  └─ migrate (alembic upgrade head, разовый)
       └─ api (FastAPI, healthcheck)
            └─ frontend (nginx, порт 8080)
```

Порядок запуска задают условия `depends_on`: миграции стартуют, когда БД готова, API — когда миграции завершились успешно, frontend — когда API прошёл проверку работоспособности.

```bash
cp deploy/.env.example deploy/.env
docker compose -f deploy/docker-compose.yml up -d --build
deploy/smoke.sh
```

## Окружения

| Окружение | Где | Как обновляется |
|---|---|---|
| Разработка | ноутбук разработчика | `uvicorn --reload` и `npm run dev` |
| Тестовое | runner GitHub Actions, задание `images` | на каждый pull request: сборка образов, подъём compose, тестовые данные, `smoke.sh` |
| Рабочее | VPS | `docker compose pull && docker compose up -d` с образами из GHCR конкретной версии |

## Конвейер

1. **Pull request.** Задание `images` собирает оба образа, поднимает окружение, загружает тестовые данные и запускает `smoke.sh`: health API, отдача frontend, ошибка problem+json через прокси nginx, граф из 8 блоков. Задание обязательное для слияния.
2. **main.** Те же шаги, затем образы публикуются в `ghcr.io/howksss/pult-backend` и `ghcr.io/howksss/pult-frontend` с тегами `sha-<коммит>` и `main`.
3. **Тег `v*`.** Дополнительно образы получают тег версии, например `0.2.0`.

## Развёртывание и откат

```bash
export BACKEND_IMAGE=ghcr.io/howksss/pult-backend:0.2.0
export FRONTEND_IMAGE=ghcr.io/howksss/pult-frontend:0.2.0
deploy/db/backup.sh
docker compose -f deploy/docker-compose.yml pull
docker compose -f deploy/docker-compose.yml up -d
deploy/smoke.sh
```

Откат: указать предыдущую версию в `BACKEND_IMAGE` и `FRONTEND_IMAGE` и повторить `up -d`. Если в новой версии была миграция схемы, перед откатом выполнить `alembic downgrade <ревизия>` в контейнере `migrate` предыдущей версии или восстановить копию, сделанную перед развёртыванием.
