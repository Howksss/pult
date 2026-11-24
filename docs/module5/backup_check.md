# Проверка восстановления копии

Копия, которую не пробовали восстановить, копией не считается. Ниже — проверка на рабочем сервере 24.11.2026 и проверка воспроизводимости в CI.

## Рабочий сервер, 24.11.2026

Порядок:

1. Снята копия рабочей базы скриптом из cron `deploy/db/backup-compose.sh`: `pult_20261124T152139Z.dump`, 3 463 831 байт.
2. `deploy/db/restore-check-compose.sh` развернул эту копию в пустую базу `pult_restore_check` рядом с рабочей, сверил базы через `verify.sh` и удалил временную базу.

```text
$ date -u
Tue Nov 24 15:24:50 UTC 2026
$ deploy/db/restore-check-compose.sh
copy: pult_20261124T152139Z.dump, 3463831 bytes
NOTICE:  database "pult_restore_check" does not exist, skipping
restore took 6 s
schema           e43e148570c5deab  ok
agent_task                  1  ok
app_user                    4  ok
audit_event                 0  ok
block                       8  ok
block_link                  9  ok
block_scope                 5  ok
change_request              0  ok
check_result           489629  ok
deployment                  0  ok
health_check                8  ok
project                     2  ok
project_member              5  ok
task_message                0  ok
user_session                7  ok
alembic_version          0006  ok
verify exit 0, pult_restore_check dropped
```

| Что сверялось | Результат |
|---|---|
| Структура: хэш `pg_dump --schema-only` | совпадает (`e43e148570c5deab`) |
| Число строк в 14 таблицах | совпадает во всех, в том числе 489 629 результатов проверок |
| Версия схемы Alembic | `0006` в обеих базах |
| Время восстановления | 6 с |

Рабочая база во время проверки продолжала принимать результаты проверок раз в минуту. Строки, пришедшие после снятия копии, `verify.sh` не учитывает: сравнивает только строки с идентификатором не больше максимального в копии.

Проверка снята до выкатки этой версии, поэтому схема в ней `0006`. После выкатки миграций `0007`–`0010` проверка повторяется командой `deploy/db/restore-check-compose.sh`, и каждый месяц она идёт по cron.

## CI: воспроизводимость и восстановление

Задание `database` в `.github/workflows/ci.yml` на каждый pull request:

1. `alembic -x seed=demo upgrade head` на пустой базе `pult`.
2. Та же команда на второй пустой базе `pult_repeat` и `verify.sh pult pult_repeat`: одна команда дважды даёт одинаковую структуру и одинаковые данные.
3. Откат новых миграций до `0006` и повторное применение.
4. Словарь данных, собранный из базы, совпадает с `docs/module5/data-dictionary.md`.
5. `backup.sh`, `restore.sh` в `pult_restore` и `verify.sh pult pult_restore`.

Тот же сценарий локально на PostgreSQL 16.10:

```text
$ alembic -x seed=demo upgrade head           # пустая база pult_m5, 17 с
$ alembic -x seed=demo upgrade head           # пустая база pult_repeat
$ deploy/db/verify.sh pult_m5 pult_repeat
schema           9fa824b0f9ba3a9a  ok
agent_task                 1  ok
app_user                   3  ok
audit_event                0  ok
block                      8  ok
block_link                 9  ok
block_scope                5  ok
change_request             0  ok
check_result          475182  ok
deployment                 0  ok
health_check              11  ok
project                    1  ok
project_member             3  ok
task_message               0  ok
user_session               0  ok
alembic_version         0010  ok
```
