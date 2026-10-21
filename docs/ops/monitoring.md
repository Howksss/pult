# Наблюдаемость

## Логи

Каждый запрос пишется одной JSON-строкой в stdout (`app/core/observability.py`): время, уровень, `request_id`, метод, шаблон маршрута, статус, длительность в мс. `X-Request-ID` берётся из запроса или генерируется и возвращается в ответе, по нему связываются записи прокси, API и жалоба пользователя. Токены и тела запросов в лог не пишутся.

```json
{"time": "2026-10-21T18:40:12+0800", "level": "INFO", "logger": "pult.access", "message": "request", "request_id": "3f2a…", "method": "GET", "route": "/api/v1/projects/{project_id}/graph", "status": 200, "duration_ms": 7.4}
```

## Метрики

`GET /metrics` в формате Prometheus:

| Метрика | Тип | Метки |
|---|---|---|
| `pult_http_requests_total` | counter | `method`, `route` (шаблон пути, а не фактический URL), `status` |
| `pult_http_request_duration_seconds` | histogram | `method`, `route`; границы до 5 с, включая 0,3 с для NFR-P4 |

Метка `route` — шаблон (`/api/v1/projects/{project_id}/graph`), поэтому число временных рядов не растёт с числом проектов.

## Проверки работоспособности

| Эндпоинт | Что проверяет | Кто использует |
|---|---|---|
| `/api/health` | процесс отвечает | `HEALTHCHECK` контейнера, smoke-тест |
| `/api/ready` | процесс отвечает и БД доступна (`select 1`), иначе 503 problem+json | балансировщик, мониторинг |

## Мониторинг и оповещения

`docker compose -f deploy/docker-compose.yml --profile monitoring up -d` дополнительно поднимает Prometheus на порту 9090 с правилами из `deploy/monitoring/alerts.yml`:

| Оповещение | Условие | Требование |
|---|---|---|
| `PultApiDown` | API не отвечает на сбор метрик 2 мин | NFR-A1 |
| `PultHighErrorRate` | больше 2 % ответов 5xx за 5 мин | NFR-A1 |
| `PultSlowGraph` | p95 чтения графа выше 300 мс 10 мин | NFR-P4 |
| `PultNoProbeData` | 10 мин нет принятых пачек от probe | FR-08, NFR-P3 |

Реакция на оповещения — в [runbook.md](runbook.md).
