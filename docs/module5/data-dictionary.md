# Словарь данных

Документ собран скриптом `backend/scripts/data_dictionary.py` из живой базы после `alembic upgrade head` (версия схемы `0011`). Описания берутся из комментариев `COMMENT ON` в базе (миграция 0009), поэтому словарь и схема не расходятся. Вручную не править: после изменения схемы запустить скрипт заново.

Формат: таблица → столбец → тип → описание → ограничения. Ниже каждой таблицы — её ограничения с правилом предметной области и индексы с запросом, который они ускоряют.

Содержание: [app_user](#app_user), [user_session](#user_session), [project](#project), [project_member](#project_member), [block](#block), [block_link](#block_link), [block_scope](#block_scope), [health_check](#health_check), [check_result](#check_result), [agent_task](#agent_task), [task_message](#task_message), [change_request](#change_request), [deployment](#deployment), [audit_event](#audit_event), [alembic_version](#alembic_version), [api_key](#api_key), [v_block_status](#v_block_status), [перечисления](#перечисления).

## app_user

Пользователь Pult: в разных проектах он может быть владельцем, разработчиком или заказчиком (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор пользователя | PK |
| `email` | varchar(255) | да |  | Адрес почты, он же логин. Хранится в нижнем регистре | NOT NULL; UNIQUE; CHECK ck_app_user_email_format |
| `full_name` | varchar(150) | да |  | Имя для интерфейса и уведомлений | NOT NULL; CHECK ck_app_user_full_name_not_blank |
| `password_hash` | varchar(255) | да |  | Хэш пароля Argon2id. Сам пароль не хранится | NOT NULL |
| `created_at` | timestamptz | да | `now()` | Момент регистрации | NOT NULL |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `app_user_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Пользователь однозначно определяется идентификатором |
| `app_user_email_key` | UNIQUE | UNIQUE (email) | Один адрес почты — один пользователь: адрес служит логином |
| `ck_app_user_email_format` | CHECK | CHECK ((((email)::text ~ '^[^@[:space:]]+@[^@[:space:]]+[.][^@[:space:]]+$'::text) AND ((email)::text = lower((email)::text)))) | Логин — адрес почты в нижнем регистре, чтобы Ivan@ и ivan@ не стали двумя людьми |
| `ck_app_user_full_name_not_blank` | CHECK | CHECK ((TRIM(BOTH FROM full_name) <> ''::text)) | У пользователя есть имя для интерфейса |

## user_session

Сессия входа пользователя (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор сессии | PK |
| `user_id` | integer | да |  | Пользователь, который вошёл | NOT NULL; FK → app_user, ON DELETE CASCADE |
| `token_hash` | varchar(64) | да |  | SHA-256 токена сессии из cookie pult_session. Сам токен не хранится | NOT NULL; UNIQUE |
| `expires_at` | timestamptz | да |  | Момент, после которого сессия недействительна | NOT NULL; CHECK ck_user_session_expires_after_created |
| `created_at` | timestamptz | да | `now()` | Момент входа | NOT NULL; CHECK ck_user_session_expires_after_created |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `user_session_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Сессия однозначно определяется идентификатором |
| `user_session_token_hash_key` | UNIQUE | UNIQUE (token_hash) | Токен сессии указывает ровно на одну сессию |
| `user_session_user_id_fkey` | FOREIGN KEY | FOREIGN KEY (user_id) REFERENCES app_user(id) ON DELETE CASCADE | Сессии удалённого пользователя закрываются. CASCADE |
| `ck_user_session_expires_after_created` | CHECK | CHECK ((expires_at > created_at)) | Сессия истекает позже, чем начинается |

## project

Проект: система клиента, которую сопровождает Pult, и её репозиторий (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор проекта | PK |
| `name` | varchar(150) | да |  | Название проекта | NOT NULL; CHECK ck_project_name_not_blank |
| `description` | text | нет |  | Описание для участников |  |
| `repo_full_name` | varchar(200) | да |  | Репозиторий системы клиента на GitHub в виде владелец/имя | NOT NULL; CHECK ck_project_repo_full_name_format |
| `default_branch` | varchar(100) | да |  | Основная ветка репозитория, от неё агент создаёт ветки задач | NOT NULL; CHECK ck_project_default_branch_not_blank |
| `created_at` | timestamptz | да | `now()` | Момент создания проекта | NOT NULL |
| `probe_token_hash` | varchar(64) | нет |  | SHA-256 токена probe, с которым сервер клиента присылает результаты проверок | UNIQUE |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `project_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Проект однозначно определяется идентификатором |
| `uq_project_probe_token_hash` | UNIQUE | UNIQUE (probe_token_hash) | По токену probe однозначно определяется проект |
| `ck_project_default_branch_not_blank` | CHECK | CHECK ((TRIM(BOTH FROM default_branch) <> ''::text)) | У репозитория указана основная ветка |
| `ck_project_name_not_blank` | CHECK | CHECK ((TRIM(BOTH FROM name) <> ''::text)) | У проекта есть название |
| `ck_project_repo_full_name_format` | CHECK | CHECK (((repo_full_name)::text ~ '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'::text)) | Репозиторий указан как владелец/имя, как на GitHub |

## project_member

Участие пользователя в проекте и его роль (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `project_id` | integer | да |  | Проект | PK (составной); FK → project, ON DELETE CASCADE |
| `user_id` | integer | да |  | Пользователь | PK (составной); FK → app_user, ON DELETE CASCADE |
| `role` | member_role | да |  | Роль в проекте, значения в типе member_role | NOT NULL |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `project_member_pkey` | PRIMARY KEY | PRIMARY KEY (project_id, user_id) | Пользователь входит в проект один раз и с одной ролью |
| `project_member_project_id_fkey` | FOREIGN KEY | FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE | Участие в удалённом проекте теряет смысл. CASCADE |
| `project_member_user_id_fkey` | FOREIGN KEY | FOREIGN KEY (user_id) REFERENCES app_user(id) ON DELETE CASCADE | Участие удалённого пользователя теряет смысл. CASCADE |

Индексы и запросы, которые они ускоряют:

| Индекс | Определение | Зачем |
|---|---|---|
| `ix_project_member_user_id` | btree (user_id) | Проекты пользователя: GET /auth/me и GET /projects. Первичный ключ начинается с project_id и этот запрос не покрывает |

## block

Блок графа системы клиента: сервер, задание, бот, интеграция, конфигурация или хранилище (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор блока | PK |
| `project_id` | integer | да |  | Проект, которому принадлежит блок | NOT NULL; UNIQUE (составной); FK → project, ON DELETE CASCADE |
| `kind` | block_kind | да |  | Тип блока, значения в типе block_kind | NOT NULL |
| `name` | varchar(100) | да |  | Имя блока, уникальное в пределах проекта | NOT NULL; UNIQUE (составной); CHECK ck_block_name_not_blank |
| `description` | text | нет |  | Описание блока |  |
| `pos_x` | double precision | да |  | Координата X блока на холсте доски, пиксели | NOT NULL |
| `pos_y` | double precision | да |  | Координата Y блока на холсте доски, пиксели | NOT NULL |
| `created_at` | timestamptz | да | `now()` | Момент создания блока | NOT NULL |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `block_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Блок однозначно определяется идентификатором |
| `block_project_id_name_key` | UNIQUE | UNIQUE (project_id, name) | В одном проекте нет двух блоков с одинаковым именем |
| `block_project_id_fkey` | FOREIGN KEY | FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE | Блок принадлежит существующему проекту. CASCADE: блоки — часть проекта |
| `ck_block_name_not_blank` | CHECK | CHECK ((TRIM(BOTH FROM name) <> ''::text)) | У блока есть имя на доске |

Индексы и запросы, которые они ускоряют:

| Индекс | Определение | Зачем |
|---|---|---|
| `ix_block_project_id` | btree (project_id) | Блоки проекта: загрузка графа GET /projects/{id}/graph и проверка прав |

## block_link

Направленная связь между двумя блоками одного проекта (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор связи | PK |
| `source_block_id` | integer | да |  | Блок, от которого идёт связь | NOT NULL; UNIQUE (составной); FK → block, ON DELETE CASCADE; CHECK block_link_not_self |
| `target_block_id` | integer | да |  | Блок, к которому идёт связь | NOT NULL; UNIQUE (составной); FK → block, ON DELETE CASCADE; CHECK block_link_not_self |
| `label` | varchar(100) | нет |  | Подпись на стрелке: что передаётся по связи |  |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `block_link_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Связь однозначно определяется идентификатором |
| `uq_block_link_source_target` | UNIQUE | UNIQUE (source_block_id, target_block_id) | Между двумя блоками в одну сторону не больше одной связи |
| `block_link_source_block_id_fkey` | FOREIGN KEY | FOREIGN KEY (source_block_id) REFERENCES block(id) ON DELETE CASCADE | Связь без блока-источника невозможна. CASCADE |
| `block_link_target_block_id_fkey` | FOREIGN KEY | FOREIGN KEY (target_block_id) REFERENCES block(id) ON DELETE CASCADE | Связь без блока-приёмника невозможна. CASCADE |
| `block_link_not_self` | CHECK | CHECK ((source_block_id <> target_block_id)) | Блок не может быть связан сам с собой |

Индексы и запросы, которые они ускоряют:

| Индекс | Определение | Зачем |
|---|---|---|
| `ix_block_link_target_block_id` | btree (target_block_id) | Каскадное удаление связей при удалении блока-приёмника. Поиск по источнику покрывает uq_block_link_source_target |

## block_scope

Шаблон пути в репозитории и право агента блока на файлы по этому пути (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор записи области | PK |
| `block_id` | integer | да |  | Блок, агенту которого выдан доступ | NOT NULL; UNIQUE (составной); FK → block, ON DELETE CASCADE |
| `path_glob` | varchar(300) | да |  | Шаблон пути (glob) от корня репозитория, например pipeline/** | NOT NULL; UNIQUE (составной); CHECK ck_block_scope_relative_path |
| `access` | scope_access | да |  | Право на файлы, значения в типе scope_access | NOT NULL |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `block_scope_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Запись области однозначно определяется идентификатором |
| `uq_block_scope_block_id_path_glob` | UNIQUE | UNIQUE (block_id, path_glob) | Один и тот же путь не выдаётся блоку дважды |
| `block_scope_block_id_fkey` | FOREIGN KEY | FOREIGN KEY (block_id) REFERENCES block(id) ON DELETE CASCADE | Область доступа — часть настройки блока. CASCADE |
| `ck_block_scope_relative_path` | CHECK | CHECK ((((path_glob)::text <> ''::text) AND ("left"((path_glob)::text, 1) <> '/'::text) AND (strpos((path_glob)::text, chr(92)) = 0) AND ((path_glob)::text !~ '(^\|/)[.][.](/\|$)'::text))) | Агент работает только внутри репозитория: путь относительный, без «..» и обратной косой черты |

## health_check

Настройка проверки блока (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор проверки | PK |
| `block_id` | integer | да |  | Блок, состояние которого показывает проверка | NOT NULL; FK → block, ON DELETE CASCADE |
| `method` | check_method | да |  | Способ проверки, значения в типе check_method | NOT NULL |
| `target` | varchar(500) | да |  | Что проверяется: URL, хост и порт, команда или текст строки журнала | NOT NULL; CHECK ck_health_check_target_not_blank |
| `interval_sec` | integer | да |  | Как часто выполняется проверка, секунды | NOT NULL; CHECK ck_health_check_interval_range; CHECK ck_health_check_timeout_within_interval |
| `timeout_sec` | integer | да |  | Сколько ждать ответа, секунды | NOT NULL; CHECK ck_health_check_timeout_range; CHECK ck_health_check_timeout_within_interval |
| `name` | varchar(120) | нет |  | Название для интерфейса. Если пусто, строится из метода и цели |  |
| `config` | jsonb | да | `'{}'::jsonb` | Параметры метода в JSON: ожидаемый код ответа, текст в ответе, порог задержки, за сколько дней предупреждать об истечении сертификата | NOT NULL |
| `enabled` | boolean | да | `true` | Выключенная проверка не влияет на статус блока | NOT NULL |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `health_check_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Проверка однозначно определяется идентификатором |
| `health_check_block_id_fkey` | FOREIGN KEY | FOREIGN KEY (block_id) REFERENCES block(id) ON DELETE CASCADE | Проверка — часть настройки блока. CASCADE |
| `ck_health_check_interval_range` | CHECK | CHECK (((interval_sec >= 10) AND (interval_sec <= 604800))) | Проверка не чаще раза в 10 с и не реже раза в неделю |
| `ck_health_check_target_not_blank` | CHECK | CHECK ((TRIM(BOTH FROM target) <> ''::text)) | У проверки есть цель |
| `ck_health_check_timeout_range` | CHECK | CHECK (((timeout_sec >= 1) AND (timeout_sec <= 60))) | Ответа ждём от 1 до 60 с |
| `ck_health_check_timeout_within_interval` | CHECK | CHECK ((timeout_sec <= interval_sec)) | Проверка не может ждать ответа дольше своего интервала, иначе запуски наложатся |

Индексы и запросы, которые они ускоряют:

| Индекс | Определение | Зачем |
|---|---|---|
| `ix_health_check_block_id` | btree (block_id) | Проверки блока: GET /blocks/{id}/checks, расчёт статусов графа, каскадное удаление при удалении блока |

## check_result

Результат одного выполнения проверки (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор результата | PK |
| `health_check_id` | integer | да |  | Проверка, к которой относится результат | NOT NULL; FK → health_check, ON DELETE CASCADE |
| `checked_at` | timestamptz | да | `now()` | Момент выполнения проверки | NOT NULL |
| `status` | check_status | да |  | Итог проверки, значения в типе check_status | NOT NULL |
| `latency_ms` | integer | нет |  | Время ответа, миллисекунды | CHECK ck_check_result_latency_not_negative |
| `message` | text | нет |  | Короткое описание результата для человека |  |
| `error_kind` | varchar(40) | нет |  | Код вида ошибки латиницей: timeout, dns, tls, http_status и другие | CHECK ck_check_result_error_kind_format |
| `details` | jsonb | нет |  | Подробности ошибки в JSON: адрес, код ответа, фрагмент тела. Не больше 8000 символов |  |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `check_result_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Результат однозначно определяется идентификатором |
| `check_result_health_check_id_fkey` | FOREIGN KEY | FOREIGN KEY (health_check_id) REFERENCES health_check(id) ON DELETE CASCADE | Результаты без проверки не нужны. CASCADE |
| `ck_check_result_error_kind_format` | CHECK | CHECK (((error_kind IS NULL) OR ((error_kind)::text ~ '^[a-z_]{1,40}$'::text))) | Код ошибки — латиница и подчёркивание, до 40 символов |
| `ck_check_result_latency_not_negative` | CHECK | CHECK (((latency_ms IS NULL) OR (latency_ms >= 0))) | Время ответа не бывает отрицательным |

Индексы и запросы, которые они ускоряют:

| Индекс | Определение | Зачем |
|---|---|---|
| `ix_check_result_checked_at_brin` | brin (checked_at) WITH (autosummarize='on') | Выборки результатов за период по времени, компактный BRIN для журнала, который пишется по возрастанию времени |
| `uq_check_result_check_time` | btree (health_check_id, checked_at DESC) | Последний результат и история проверки, плюс защита от дублей: повтор пачки probe с тем же моментом проверки не создаёт вторую строку |

## agent_task

Задача ИИ-агенту по блоку (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор задачи | PK |
| `block_id` | integer | да |  | Блок, по которому поставлена задача | NOT NULL; FK → block, ON DELETE CASCADE |
| `author_id` | integer | да |  | Пользователь, который поставил задачу | NOT NULL; FK → app_user, ON DELETE RESTRICT |
| `title` | varchar(200) | да |  | Формулировка задачи | NOT NULL; CHECK ck_agent_task_title_not_blank |
| `status` | task_status | да |  | Этап задачи, значения в типе task_status | NOT NULL |
| `finished_at` | timestamptz | нет |  | Момент завершения. Пусто, пока задача не закрыта | CHECK ck_agent_task_finished_after_created |
| `created_at` | timestamptz | да | `now()` | Момент постановки задачи | NOT NULL; CHECK ck_agent_task_finished_after_created |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `agent_task_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Задача однозначно определяется идентификатором |
| `agent_task_author_id_fkey` | FOREIGN KEY | FOREIGN KEY (author_id) REFERENCES app_user(id) ON DELETE RESTRICT | Нельзя удалить пользователя, который ставил задачи: история задач хранит автора. RESTRICT |
| `agent_task_block_id_fkey` | FOREIGN KEY | FOREIGN KEY (block_id) REFERENCES block(id) ON DELETE CASCADE | Задачи по удалённому блоку удаляются вместе с ним. CASCADE |
| `ck_agent_task_finished_after_created` | CHECK | CHECK (((finished_at IS NULL) OR (finished_at >= created_at))) | Задача не может завершиться раньше, чем поставлена |
| `ck_agent_task_title_not_blank` | CHECK | CHECK ((TRIM(BOTH FROM title) <> ''::text)) | У задачи есть формулировка |

Индексы и запросы, которые они ускоряют:

| Индекс | Определение | Зачем |
|---|---|---|
| `ix_agent_task_block_id` | btree (block_id) | Каскадное удаление задач при удалении блока |

## task_message

Сообщение в чате задачи агента (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор сообщения | PK |
| `task_id` | integer | да |  | Задача, к которой относится сообщение | NOT NULL; FK → agent_task, ON DELETE CASCADE |
| `role` | message_role | да |  | Автор сообщения, значения в типе message_role | NOT NULL |
| `content` | jsonb | да |  | Содержимое сообщения: список блоков в формате Claude API (JSON) | NOT NULL |
| `input_tokens` | integer | нет |  | Входные токены модели на это сообщение | CHECK ck_task_message_tokens_not_negative |
| `output_tokens` | integer | нет |  | Выходные токены модели на это сообщение | CHECK ck_task_message_tokens_not_negative |
| `created_at` | timestamptz | да | `now()` | Момент сообщения | NOT NULL |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `task_message_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Сообщение однозначно определяется идентификатором |
| `task_message_task_id_fkey` | FOREIGN KEY | FOREIGN KEY (task_id) REFERENCES agent_task(id) ON DELETE CASCADE | Сообщения — часть задачи. CASCADE |
| `ck_task_message_tokens_not_negative` | CHECK | CHECK ((((input_tokens IS NULL) OR (input_tokens >= 0)) AND ((output_tokens IS NULL) OR (output_tokens >= 0)))) | Расход токенов не бывает отрицательным |

Индексы и запросы, которые они ускоряют:

| Индекс | Определение | Зачем |
|---|---|---|
| `ix_task_message_task_id` | btree (task_id) | Сообщения задачи: чат задачи и каскадное удаление |

## change_request

Pull request, который агент открыл по задаче, и решение по его ревью (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор запроса на изменение | PK |
| `task_id` | integer | да |  | Задача. У задачи не больше одного pull request | NOT NULL; UNIQUE; FK → agent_task, ON DELETE CASCADE |
| `branch_name` | varchar(200) | да |  | Ветка с изменениями агента | NOT NULL |
| `pr_number` | integer | да |  | Номер pull request в репозитории проекта | NOT NULL; CHECK ck_change_request_pr_number_positive |
| `status` | cr_status | да |  | Состояние pull request, значения в типе cr_status | NOT NULL |
| `reviewer_id` | integer | нет |  | Пользователь, который принял решение по ревью | FK → app_user, ON DELETE RESTRICT; CHECK ck_change_request_reviewed_by_reviewer |
| `reviewed_at` | timestamptz | нет |  | Момент решения по ревью | CHECK ck_change_request_reviewed_by_reviewer |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `change_request_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Запрос на изменение однозначно определяется идентификатором |
| `change_request_task_id_key` | UNIQUE | UNIQUE (task_id) | У задачи не больше одного pull request |
| `change_request_reviewer_id_fkey` | FOREIGN KEY | FOREIGN KEY (reviewer_id) REFERENCES app_user(id) ON DELETE RESTRICT | Нельзя удалить пользователя, который принимал решение по ревью: решение должно иметь автора. RESTRICT |
| `change_request_task_id_fkey` | FOREIGN KEY | FOREIGN KEY (task_id) REFERENCES agent_task(id) ON DELETE CASCADE | Pull request существует только в рамках задачи. CASCADE |
| `ck_change_request_pr_number_positive` | CHECK | CHECK ((pr_number > 0)) | Номера pull request на GitHub начинаются с 1 |
| `ck_change_request_reviewed_by_reviewer` | CHECK | CHECK (((reviewed_at IS NULL) OR (reviewer_id IS NOT NULL))) | Если ревью проведено, известно, кто его провёл |

## deployment

Выкатка слитого pull request на систему клиента (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор выкатки | PK |
| `change_request_id` | integer | да |  | Pull request, изменения которого выкатываются | NOT NULL; FK → change_request, ON DELETE CASCADE |
| `commit_sha` | char(40) | да |  | Хэш выкатываемого коммита, 40 шестнадцатеричных символов | NOT NULL; CHECK ck_deployment_commit_sha_format |
| `status` | deploy_status | да |  | Состояние выкатки, значения в типе deploy_status | NOT NULL; CHECK ck_deployment_finished_when_done |
| `started_at` | timestamptz | да | `now()` | Момент начала выкатки | NOT NULL; CHECK ck_deployment_finished_after_started |
| `finished_at` | timestamptz | нет |  | Момент окончания. Пусто, пока выкатка идёт | CHECK ck_deployment_finished_after_started; CHECK ck_deployment_finished_when_done |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `deployment_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Выкатка однозначно определяется идентификатором |
| `deployment_change_request_id_fkey` | FOREIGN KEY | FOREIGN KEY (change_request_id) REFERENCES change_request(id) ON DELETE CASCADE | Выкатка относится к pull request. CASCADE |
| `ck_deployment_commit_sha_format` | CHECK | CHECK ((commit_sha ~ '^[0-9a-f]{40}$'::text)) | Выкатывается конкретный коммит: полный хэш из 40 символов |
| `ck_deployment_finished_after_started` | CHECK | CHECK (((finished_at IS NULL) OR (finished_at >= started_at))) | Выкатка не может закончиться раньше, чем началась |
| `ck_deployment_finished_when_done` | CHECK | CHECK (((status = 'running'::deploy_status) = (finished_at IS NULL))) | У идущей выкатки нет времени окончания, у завершённой оно есть |

Индексы и запросы, которые они ускоряют:

| Индекс | Определение | Зачем |
|---|---|---|
| `uq_deployment_one_running` | btree (change_request_id) WHERE (status = 'running'::deploy_status) | У pull request не может идти две выкатки одновременно |

## audit_event

Запись журнала аудита: кто, что и когда сделал (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор записи | PK |
| `user_id` | integer | нет |  | Кто выполнил действие. Пусто для действий системы | FK → app_user, ON DELETE RESTRICT |
| `block_id` | integer | нет |  | Блок, к которому относится действие. После удаления блока обнуляется | FK → block, ON DELETE SET NULL |
| `action` | varchar(100) | да |  | Код действия, например change_request.approved | NOT NULL; CHECK ck_audit_event_action_not_blank |
| `payload` | jsonb | нет |  | Подробности действия в JSON |  |
| `created_at` | timestamptz | да | `now()` | Момент действия | NOT NULL |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `audit_event_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Запись аудита однозначно определяется идентификатором |
| `audit_event_block_id_fkey` | FOREIGN KEY | FOREIGN KEY (block_id) REFERENCES block(id) ON DELETE SET NULL | Журнал аудита переживает удаление блока: ссылка обнуляется, запись остаётся. SET NULL |
| `audit_event_user_id_fkey` | FOREIGN KEY | FOREIGN KEY (user_id) REFERENCES app_user(id) ON DELETE RESTRICT | Нельзя удалить пользователя, у которого есть записи аудита: журнал не теряет авторов. RESTRICT |
| `ck_audit_event_action_not_blank` | CHECK | CHECK ((TRIM(BOTH FROM action) <> ''::text)) | У записи аудита есть код действия |

Индексы и запросы, которые они ускоряют:

| Индекс | Определение | Зачем |
|---|---|---|
| `ix_audit_event_block_id` | btree (block_id) | Обнуление ссылок аудита при удалении блока и журнал действий по блоку |

## alembic_version

Служебная таблица Alembic: версия схемы, до которой применены миграции (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `version_num` | varchar(32) | да |  | Номер последней применённой миграции | PK |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `alembic_version_pkc` | PRIMARY KEY | PRIMARY KEY (version_num) | Версия схемы записана ровно один раз |

## api_key

API-ключ пользователя для интеграций: заголовок X-API-Key вместо cookie сессии (таблица).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `id` | integer | да | автонумерация | Идентификатор ключа | PK |
| `user_id` | integer | да |  | Владелец ключа: запросы с ключом выполняются с его правами | NOT NULL; FK → app_user, ON DELETE CASCADE |
| `name` | varchar(100) | да |  | Название ключа, чтобы отличать интеграции: n8n, Bruno, скрипт выгрузки | NOT NULL; CHECK ck_api_key_name_not_blank |
| `prefix` | varchar(16) | да |  | Первые символы ключа для списка ключей. По ним ключ узнают, но не восстанавливают | NOT NULL |
| `token_hash` | varchar(64) | да |  | SHA-256 ключа. Сам ключ показывается один раз при выпуске и не хранится | NOT NULL; UNIQUE |
| `created_at` | timestamptz | да | `now()` | Момент выпуска ключа | NOT NULL; CHECK ck_api_key_expires_after_created |
| `expires_at` | timestamptz | да |  | Момент, после которого ключ не принимается | NOT NULL; CHECK ck_api_key_expires_after_created |
| `last_used_at` | timestamptz | нет |  | Когда ключ последний раз предъявляли, с точностью до минуты |  |

Ограничения и правила, которые они защищают:

| Ограничение | Вид | Определение | Правило предметной области |
|---|---|---|---|
| `api_key_pkey` | PRIMARY KEY | PRIMARY KEY (id) | Ключ однозначно определяется идентификатором |
| `api_key_token_hash_key` | UNIQUE | UNIQUE (token_hash) | Предъявленный ключ указывает ровно на одну запись |
| `api_key_user_id_fkey` | FOREIGN KEY | FOREIGN KEY (user_id) REFERENCES app_user(id) ON DELETE CASCADE | Ключи удалённого пользователя отзываются вместе с ним. CASCADE |
| `ck_api_key_expires_after_created` | CHECK | CHECK ((expires_at > created_at)) | Бессрочных ключей нет: срок действия позже момента выпуска |
| `ck_api_key_name_not_blank` | CHECK | CHECK ((TRIM(BOTH FROM name) <> ''::text)) | У ключа есть название |

Индексы и запросы, которые они ускоряют:

| Индекс | Определение | Зачем |
|---|---|---|
| `ix_api_key_user_id` | btree (user_id) | Список ключей пользователя GET /api-keys |

## v_block_status

Статус каждого блока по последним результатам его включённых проверок (представление).

| Столбец | Тип | Обязательный | По умолчанию | Описание | Ограничения |
|---|---|---|---|---|---|
| `block_id` | integer | нет |  | Блок |  |
| `project_id` | integer | нет |  | Проект блока |  |
| `name` | varchar(100) | нет |  | Имя блока |  |
| `status` | text | нет |  | Худший статус проверок блока: fail, warn, ok или unknown, если данных нет или они устарели |  |

## Перечисления

Значения перечислимых типов PostgreSQL (`ENUM`).

### block_kind

| Значение | Смысл |
|---|---|
| `server` | сервер |
| `scheduled_job` | задание по расписанию |
| `bot` | бот |
| `integration` | внешняя интеграция |
| `config` | конфигурация |
| `storage` | хранилище файлов или данных |

### check_method

| Значение | Смысл |
|---|---|
| `heartbeat` | сервер клиента сам отмечается раз в интервал |
| `http` | запрос к URL |
| `log_pattern` | поиск строки в журнале |
| `exit_code` | код завершения задания |
| `tls` | срок действия сертификата |
| `tcp` | порт принимает соединение |

### check_status

| Значение | Смысл |
|---|---|
| `ok` | в норме |
| `warn` | работает с отклонением |
| `fail` | сбой |

### cr_status

| Значение | Смысл |
|---|---|
| `open` | открыт |
| `approved` | одобрен |
| `changes_requested` | нужны правки |
| `merged` | слит |
| `closed` | закрыт без слияния |

### deploy_status

| Значение | Смысл |
|---|---|
| `running` | идёт |
| `succeeded` | успешно |
| `failed` | с ошибкой |
| `rolled_back` | откачена |

### member_role

| Значение | Смысл |
|---|---|
| `owner` | владелец: настраивает проект, блоки, проверки и участников |
| `developer` | разработчик: видит всё и запускает проверки |
| `client` | заказчик: видит состояние своей системы |

### message_role

| Значение | Смысл |
|---|---|
| `user` | сообщение человека |
| `assistant` | ответ агента |
| `tool` | результат инструмента агента |

### scope_access

| Значение | Смысл |
|---|---|
| `read` | агент только читает файлы |
| `write` | агент читает и меняет файлы |

### task_status

| Значение | Смысл |
|---|---|
| `new` | поставлена |
| `running` | агент работает |
| `awaiting_review` | pull request ждёт ревью |
| `approved` | изменения одобрены |
| `rejected` | отклонены |
| `deployed` | выкачены |
| `failed` | агент не справился |
