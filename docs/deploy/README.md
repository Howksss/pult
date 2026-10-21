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

## Рабочий сервер

Наружу смотрит только обратный прокси на хосте. Порты API, frontend и Prometheus в compose слушают `127.0.0.1`, номера задаются в `deploy/.env` (`API_PORT`, `WEB_PORT`, `PROMETHEUS_PORT`), чтобы не мешать соседним сервисам на той же машине.

```
Интернет ──443──▶ nginx хоста (TLS, Basic, лимиты) ──▶ 127.0.0.1:WEB_PORT frontend ──▶ api:8000
probe ──443──▶ /api/v1/probe/ без Basic, по X-Probe-Token
```

Шаблон сайта — `deploy/proxy/nginx-site.conf`:

| Что | Зачем |
|---|---|
| HTTPS, сертификат Let's Encrypt через webroot, HSTS | трафик и пароль не идут открытым текстом |
| HTTP Basic на всё, кроме `/api/v1/probe/` и `/api/health` | до учётных записей 0.3.0 граф и перетаскивание блоков доступны только своим (угроза T2) |
| `limit_req` 20 запросов в секунду на адрес для `/api/`, 2 для probe, ответ 429 | поток запросов не кладёт API (угроза T10) |
| `client_max_body_size 1m` | пачка от probe ограничена ещё и по размеру |
| `nosniff`, `DENY` для фреймов, `no-referrer` | страницу нельзя встроить в чужую, адрес не утекает |

### Первый запуск

```bash
git clone https://github.com/Howksss/pult /opt/pult && cd /opt/pult
cp deploy/.env.example deploy/.env
# POSTGRES_PASSWORD: openssl rand -hex 24; свободные WEB_PORT и API_PORT; образы конкретной версии
docker compose -f deploy/docker-compose.yml pull
docker compose -f deploy/docker-compose.yml up -d --no-build
WEB_URL=http://127.0.0.1:$WEB_PORT API_URL=http://127.0.0.1:$API_PORT deploy/smoke.sh

printf 'owner:%s\n' "$(openssl passwd -6)" > /etc/nginx/pult.htpasswd
sed "s/pult.example.com/<домен>/g; s/127.0.0.1:8080/127.0.0.1:$WEB_PORT/" deploy/proxy/nginx-site.conf > /etc/nginx/sites-available/pult
```

Сертификат выпускается до включения блока 443: сначала в сайте остаётся только блок 80 с `/.well-known/acme-challenge/`, затем `certbot certonly --webroot -w /var/www/html -d <домен>`, затем включается весь сайт, `nginx -t` и `systemctl reload nginx`. Продление делает `certbot.timer`.

Токен probe для проекта задаётся только хэшем: `update project set probe_token_hash = encode(sha256('<токен>'::bytea), 'hex')`. Демо-токен из `seed_demo.sql` на рабочем сервере заменяется сразу после загрузки данных.

### Резервные копии

`deploy/db/backup-compose.sh` снимает `pg_dump` прямо из контейнера `db`, проверяет копию `pg_restore --list` и удаляет копии старше 14 дней. Запуск по cron раз в сутки:

```
15 3 * * * /opt/pult/deploy/db/backup-compose.sh >> /var/log/pult-backup.log 2>&1
```

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
