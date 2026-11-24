# Журнал изменений API

Версия контракта — поле `info.version` в [openapi.yaml](openapi.yaml), правила версионирования — в [README](README.md#версионирование). Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

## [1.1.0] — 2026-11-25

Совместимые изменения: всё новое добавлено в `/api/v1`, прежние запросы работают как раньше. Задача [#105](https://github.com/Howksss/pult/issues/105).

### Добавлено

- Аутентификация по API-ключу: заголовок `X-API-Key`, схема `apiKey`. Выпуск `POST /api-keys` (ключ показывается один раз, срок от 1 до 365 дней), список `GET /api-keys`, отзыв `DELETE /api-keys/{key_id}`.
- `GET`, `PATCH`, `DELETE /projects/{project_id}`.
- `GET /projects/{project_id}/blocks` с фильтрами `kind`, `status`, `q`; `GET /blocks/{block_id}`.
- `GET /projects/{project_id}/links` с фильтром `block_id`; `PATCH` и `DELETE /links/{link_id}`.
- `GET /checks/{check_id}` и история `GET /checks/{check_id}/results` с фильтрами `status`, `since`, `until`.
- `PUT /blocks/{block_id}/scopes` — замена области блока целиком.
- Пагинация `limit` и `offset` и заголовок `X-Total-Count` у списков; фильтр `role` у проектов и участников, `access` у области.
- Поле `duplicates` в ответе `POST /probe/results`.
- Ответы 400 (тело не JSON) и 500 (непредвиденная ошибка, без подробностей) в формате RFC 9457 у всех операций. Примеры ответов и тел запросов в схемах.
- Ответ 409 у `POST /projects/{project_id}/links` (связь уже есть) и у `POST /projects` (проект на этот репозиторий у пользователя уже есть).

### Изменено

- Повтор пачки probe с теми же проверками и моментами не записывает результаты второй раз: `accepted` — сколько записано, `duplicates` — сколько пропущено.
- Таймаут проверки не может быть больше интервала: 422.
- Синтаксически неверный JSON — 400 вместо 422.

### Исправлено

- `POST /probe/results` на PostgreSQL возвращал `accepted: -1` ([#106](https://github.com/Howksss/pult/issues/106), найдено прогоном коллекции Bruno).

## [1.0.0] — 2026-10-21

Первая версия контракта. Задачи [#29](https://github.com/Howksss/pult/issues/29) и [#30](https://github.com/Howksss/pult/issues/30).

- Граф проекта `GET /projects/{project_id}/graph`, блоки `POST /projects/{project_id}/blocks`, `PATCH` и `DELETE /blocks/{block_id}`, связи `POST /projects/{project_id}/links`.
- Приём результатов probe `POST /probe/results` с токеном `X-Probe-Token`.
- Служебные `GET /api/health` и `GET /api/ready`.
- Ошибки `application/problem+json` по RFC 9457.

С 17.11.2026 в 1.0.0 без изменения версии добавлены проверки блока (#90, #92), область доступа (#94), вход, проекты и участники (#96), шкала по часам (#98). Все изменения совместимые. С версии 1.1.0 каждое изменение контракта получает запись здесь.
