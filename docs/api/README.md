# API

Контракт: [openapi.yaml](openapi.yaml) (OpenAPI 3.1, версия 1.1.0). Он пишется **до** реализации и служит источником истины для backend, frontend, probe и коллекции Bruno. Стиль API и почему REST — [ADR 005](../adr/005_api_style.md), что менялось — [журнал изменений](changelog.md), все ресурсы и операции с кодами ответов — [operations.md](operations.md).

## Порядок работы

1. Изменение API начинается с правки `openapi.yaml`. Его проверяет Redocly CLI в CI (`npx @redocly/cli@1.25.15 lint docs/api/openapi.yaml`).
2. Backend реализует операции по контракту. Тесты с помощником `tests/contract.py` сверяют реализацию с контрактом: набор операций совпадает в обе стороны, каждый ответ в тестах проверяется по коду и схеме.
3. Документация [redoc.html](redoc.html) и таблица [operations.md](operations.md) собираются из контракта (команды ниже).
4. Коллекция Bruno в [`tests/api`](../../tests/api) прогоняется против запущенного API. Расхождение с контрактом заводится задачей с меткой `bug` и исправляется в коде или контракте ([пример: #106](https://github.com/Howksss/pult/issues/106)).

## Среды

| Среда | Адрес | Для чего |
|---|---|---|
| локальный стенд | `http://localhost:8000` | разработка: `alembic -x seed=demo upgrade head`, затем `uvicorn app.main:app` в `backend` |
| mock-сервер | `http://127.0.0.1:4010` | frontend и тестировщики до готовности реализации, ответы по примерам из контракта |
| рабочий сервер | `https://pultops.ru` | пилот |

Mock-сервер Prism поднимается из контракта одной командой и проверяет запросы по схемам: без `X-API-Key` отвечает 401, на неверное тело — 422, на верный запрос — пример из контракта.

```bash
npx @stoplight/prism-cli@5 mock docs/api/openapi.yaml -p 4010
```

Документация Redoc — один файл без сервера, открывается в браузере:

```bash
npx @redocly/cli@1.25.15 build-docs docs/api/openapi.yaml -o docs/api/redoc.html
python backend/scripts/api_operations.py       # таблица operations.md
```

## Как получить доступ

| Кто | Чем | Как получить |
|---|---|---|
| человек в интерфейсе | cookie `pult_session` | `POST /api/v1/auth/register` или `/login`, на рабочем сервере регистрацию может закрыть владелец (`ALLOW_SIGNUP=false`) |
| интеграция, скрипт, Bruno | заголовок `X-API-Key` | войти и выпустить ключ `POST /api/v1/api-keys`. Ключ показывается один раз, живёт от 1 до 365 дней (по умолчанию 90), права — как у владельца ключа. Отозвать — `DELETE /api/v1/api-keys/{id}` |
| probe на сервере клиента | заголовок `X-Probe-Token` | выдаётся один раз при создании проекта |

401 — не удалось установить, кто вы: нет сессии или ключа, ключ неверный или истёк. Неверный ключ не подменяется cookie. 403 — вы известны, но роли в проекте не хватает. Чужой проект отвечает 404, чтобы не выдавать, что он существует.

В базе хранятся только SHA-256 ключей и токенов. Секретов подписи нет, поэтому `.env` ключей не содержит; в репозитории только `.env.example`.

## Примеры вызовов

```bash
PULT=http://localhost:8000

# войти и выпустить ключ для интеграции
curl -s -c jar -H "Content-Type: application/json"   -d '{"email": "owner@example.com", "password": "pult-demo-2026"}' $PULT/api/v1/auth/login > /dev/null
KEY=$(curl -s -b jar -H "Content-Type: application/json" -d '{"name": "скрипт", "expires_in_days": 30}'   $PULT/api/v1/api-keys | jq -r .key)

# блоки проекта со сбоем, первые 20
curl -s -H "X-API-Key: $KEY" "$PULT/api/v1/projects/1/blocks?status=fail&limit=20"

# сбои проверки за сутки, всего — в заголовке X-Total-Count
curl -si -H "X-API-Key: $KEY" "$PULT/api/v1/checks/10/results?status=fail&since=2026-11-24T00:00:00Z"

# добавить блок и соединить его с сервером
curl -s -H "X-API-Key: $KEY" -H "Content-Type: application/json"   -d '{"kind": "bot", "name": "Telegram-бот"}' $PULT/api/v1/projects/1/blocks
curl -s -H "X-API-Key: $KEY" -H "Content-Type: application/json"   -d '{"source_block_id": 1, "target_block_id": 9, "label": "уведомления"}' $PULT/api/v1/projects/1/links

# заменить область агента блока целиком, повтор даёт то же состояние
curl -s -X PUT -H "X-API-Key: $KEY" -H "Content-Type: application/json"   -d '[{"path_glob": "bots/", "access": "write"}, {"path_glob": "docs/*.md"}]' $PULT/api/v1/blocks/8/scopes

# результат проверки от probe; повтор той же пачки вернёт accepted 0, duplicates 1
curl -s -H "X-Probe-Token: demo-probe-token" -H "Content-Type: application/json"   -d '{"results": [{"health_check_id": 10, "status": "ok", "checked_at": "2026-11-25T08:00:00Z"}]}'   $PULT/api/v1/probe/results
```

## Списки: фильтры и пагинация

У списков параметры `limit` (1–500, по умолчанию 100) и `offset`. Общее число элементов с учётом фильтров — в заголовке `X-Total-Count`. Фильтры — в параметрах запроса: `role` у проектов и участников, `kind`, `status`, `q` у блоков, `block_id` у связей, `access` у области, `status`, `since`, `until` у истории результатов.

## Идемпотентность

- `GET`, `PUT`, `DELETE` идемпотентны: `PUT /blocks/{id}/scopes` заменяет область целиком, повтор даёт то же состояние.
- Повтор `POST` не создаёт дубликат: имя блока в проекте, связь между теми же блоками, путь в области, участник, второй проект на тот же репозиторий у пользователя — 409.
- Повтор пачки probe (обрыв связи, повторная отправка) не записывает результаты второй раз: результат однозначно задают проверка и момент `checked_at`.

## Коллекция Bruno

Каталог [`tests/api`](../../tests/api), три группы: успешные сценарии, ошибки 400/404/409/422, доступ 401/403. Адрес — в окружении (`environments/local.bru`, `mock.bru`), ключи — в переменных окружения `PULT_OWNER_KEY`, `PULT_DEVELOPER_KEY`, `PULT_PROBE_TOKEN` (файл `tests/api/.env` не коммитится, образец — `.env.example`).

```bash
cd tests/api
python issue_keys.py                       # ключи владельца и разработчика демо-данных в .env
npx @usebruno/cli@4 run --env local --reporter-html results.html
```

## Версионирование

| Изменение | Пример | Что делаем |
|---|---|---|
| Новый эндпоинт или необязательное поле | `GET /api/v1/blocks/{id}/history` | остаёмся в `/api/v1`, версия контракта MINOR+1 |
| Исправление описания, примера | опечатка в `summary` | версия контракта PATCH+1 |
| Удаление или переименование поля, смена типа, новое обязательное поле запроса | `x` → `pos_x` | новый префикс `/api/v2`, версия контракта MAJOR+1, `/api/v1` живёт до перехода клиентов |

Правило из лекции 3: «ломаешь API — повышай MAJOR».

## Ошибки

Все ошибки отдаются как `application/problem+json` ([RFC 9457](https://www.rfc-editor.org/rfc/rfc9457)):

```json
{
  "type": "https://pult.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "project 42 not found"
}
```

У ошибок проверки входных данных (422) и синтаксиса JSON (400) есть поле `errors` со списком нарушений. Синтаксически неверный JSON — 400, JSON, не прошедший проверку по схеме, — 422. Непредвиденная ошибка — 500 с типом `internal` и без подробностей: они пишутся только в журнал сервера.

## Аутентификация probe

Probe на сервере клиента передаёт токен проекта в заголовке `X-Probe-Token`. В БД хранится только SHA-256 токена (`project.probe_token_hash`). Токен даёт право только отправлять результаты (`POST /api/v1/probe/results`) и только по проверкам своего проекта (NFR-S5). Результаты по чужим проверкам отклоняются целиком с кодом 422. Токен ищется в БД по SHA-256, поэтому сравнение по времени ничего не даёт атакующему: перебирать пришлось бы хэш, а не сам токен. По той же причине не нужен `hmac.compare_digest`. Утечка таблицы `project` не раскрывает токены.

## Проверки и подробности ошибок

У блока может быть сколько угодно проверок. Каждая отвечает на один вопрос, который мешает софту работать: «POS отвечает», «остатки отдаются», «сертификат не истекает», «автозаказ отработал». Интеграционных тестов здесь нет: поведение правится задачами агенту.

| Тип | Кто выполняет | Что проверяет | Настройки `config` |
|---|---|---|---|
| `http` | Pult (`worker`) | Код ответа, время, текст в ответе | `expect_status` (список кодов, по умолчанию 200–399), `contains`, `warn_latency_ms`, `method` |
| `tls` | Pult (`worker`) | Срок сертификата и его проверку | `warn_days` (14), `fail_days` (3) |
| `tcp` | Pult (`worker`) | Порт принимает соединение | — |
| `exit_code` | Сервер клиента | Задание по расписанию отработало с кодом 0 | — |
| `heartbeat` | Сервер клиента | Сервер на связи | — |
| `log_pattern` | Сервер клиента | В логе нет строк по шаблону | — |

Результат хранит `message` (что сломалось, одной фразой), `error_kind` (класс ошибки) и `details` (подробности: код ответа и кусок тела, хвост stderr, найденные строки лога). `GET /api/v1/blocks/{id}/checks` отдаёт проверки блока с последним результатом, историей, шкалой `timeline` (24 часа, по каждому часу число результатов `ok`, `warn`, `fail`) и `failing_since` — с какого результата идёт текущая серия сбоев, в графе у блока есть `reason` — причина статуса по самой тяжёлой проверке.

Задания и heartbeat отчитываются сами, отдельный агент на сервере не нужен. Достаточно обёртки `/usr/local/bin/pult-run` (нужны `curl` и `jq`):

```sh
#!/bin/sh
id=$1; shift
start=$(date +%s)
out=$("$@" 2>&1); code=$?
duration=$(( ($(date +%s) - start) * 1000 ))
body=$(jq -n --argjson id "$id" --argjson code "$code" --argjson duration "$duration" \
  --arg command "$*" --arg tail "$(printf '%s' "$out" | tail -c 2000)" '{results: [{
    health_check_id: $id, checked_at: (now | todate),
    status: (if $code == 0 then "ok" else "fail" end),
    message: (if $code == 0 then null else "Код выхода \($code)" end),
    error_kind: (if $code == 0 then null else "exit_code" end),
    details: {exit_code: $code, command: $command, duration_ms: $duration, stderr_tail: $tail}}]}')
curl -fsS -m 10 "$PULT_URL/api/v1/probe/results" -H "X-Probe-Token: $PULT_TOKEN" -H "Content-Type: application/json" -d "$body"
exit "$code"
```

и строки в crontab, где `3` — номер проверки из Pult:

```
PULT_URL=https://pultops.ru
PULT_TOKEN=...
0 9 * * * /usr/local/bin/pult-run 3 python /opt/pilot/main_orders.py
```

Проверки заводятся из панели блока или через API: `POST /api/v1/blocks/{id}/checks`, `PATCH` и `DELETE /api/v1/checks/{id}`, `POST /api/v1/checks/{id}/run` — выполнить сейчас (только `http`, `tls`, `tcp`, остальные — 409). Цель и настройки проверяются по типу. Адреса во внутренней сети отклоняются и при сохранении, и при выполнении (угроза T13 в [модели угроз](../security/threat-model.md)); для локальной разработки это снимается переменной `ALLOW_PRIVATE_TARGETS=true`.

Если задание или heartbeat молчит дольше полутора интервалов, проверка получает статус «сбой» с причиной «нет отчёта N мин»: задание не запустилось. Внешние проверки `http`, `tls`, `tcp` без свежих результатов дольше трёх интервалов — «нет данных»: остановлен `worker`.

## Область доступа блока

Область — пути репозитория, которые агент читает или меняет по задачам этого блока (FR-06, FR-15). `GET` и `POST /api/v1/blocks/{id}/scopes`, `PATCH` и `DELETE /api/v1/scopes/{id}`. Путь — шаблон относительно корня: `*` — в пределах папки, `**` — любые вложенные папки, `?` — один символ, `bots/` — вся папка (сохраняется как `bots/**`). Шаблоны с `/` в начале, `..`, `\` или буквой диска отклоняются, повтор в блоке — 409. Право `read` — только чтение, `write` — чтение и запись.

Проверку пути делает `app/services/scope.py` (`allows`): путь нормализуется, всё, что выходит за репозиторий, сразу запрещено, запись разрешается только по `write`. Эту функцию вызывает агент перед каждой операцией с файлом.

## Аутентификация пользователей

Регистрация и вход — `POST /api/v1/auth/register` и `/login` (email и пароль, пароль от 10 символов, хранится Argon2id), выход — `/logout`, текущий пользователь с проектами — `GET /api/v1/auth/me`. Сессия — cookie `pult_session` (HttpOnly, SameSite=Lax, Secure, 30 дней), в БД только SHA-256 токена (NFR-S4). Все операции, кроме health и probe, требуют сессию или API-ключ: схемы `userSession` и `apiKey` в контракте.

Права по ролям проекта: смотреть граф, проверки, область и участников — любой участник; менять граф, проверки, область и участников — владелец; «Проверить сейчас» — владелец и разработчик. Чужой проект и его блоки отвечают 404, нехватка роли — 403. Последнего владельца нельзя понизить или убрать.

Проект создаёт любой вошедший пользователь (`POST /api/v1/projects`) и становится владельцем; токен probe возвращается один раз. Участники добавляются по email уже зарегистрированных пользователей. Регистрацию можно закрыть `ALLOW_SIGNUP=false`; для разработки по http — `COOKIE_SECURE=false`. Выдать роль из консоли сервера: `PYTHONPATH=. python scripts/add_member.py <email> <project_id> owner`.
