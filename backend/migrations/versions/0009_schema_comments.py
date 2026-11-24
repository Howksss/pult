from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES: dict[str, tuple[str, dict[str, str]]] = {
    "app_user": (
        "Пользователь Pult: в разных проектах он может быть владельцем, разработчиком или заказчиком",
        {
            "id": "Идентификатор пользователя",
            "email": "Адрес почты, он же логин. Хранится в нижнем регистре",
            "full_name": "Имя для интерфейса и уведомлений",
            "password_hash": "Хэш пароля Argon2id. Сам пароль не хранится",
            "created_at": "Момент регистрации",
        },
    ),
    "project": (
        "Проект: система клиента, которую сопровождает Pult, и её репозиторий",
        {
            "id": "Идентификатор проекта",
            "name": "Название проекта",
            "description": "Описание для участников",
            "repo_full_name": "Репозиторий системы клиента на GitHub в виде владелец/имя",
            "default_branch": "Основная ветка репозитория, от неё агент создаёт ветки задач",
            "probe_token_hash": "SHA-256 токена probe, с которым сервер клиента "
            "присылает результаты проверок",
            "created_at": "Момент создания проекта",
        },
    ),
    "project_member": (
        "Участие пользователя в проекте и его роль",
        {
            "project_id": "Проект",
            "user_id": "Пользователь",
            "role": "Роль в проекте, значения в типе member_role",
        },
    ),
    "block": (
        "Блок графа системы клиента: сервер, задание, бот, интеграция, конфигурация или хранилище",
        {
            "id": "Идентификатор блока",
            "project_id": "Проект, которому принадлежит блок",
            "kind": "Тип блока, значения в типе block_kind",
            "name": "Имя блока, уникальное в пределах проекта",
            "description": "Описание блока",
            "pos_x": "Координата X блока на холсте доски, пиксели",
            "pos_y": "Координата Y блока на холсте доски, пиксели",
            "created_at": "Момент создания блока",
        },
    ),
    "block_link": (
        "Направленная связь между двумя блоками одного проекта",
        {
            "id": "Идентификатор связи",
            "source_block_id": "Блок, от которого идёт связь",
            "target_block_id": "Блок, к которому идёт связь",
            "label": "Подпись на стрелке: что передаётся по связи",
        },
    ),
    "block_scope": (
        "Шаблон пути в репозитории и право агента блока на файлы по этому пути",
        {
            "id": "Идентификатор записи области",
            "block_id": "Блок, агенту которого выдан доступ",
            "path_glob": "Шаблон пути (glob) от корня репозитория, например pipeline/**",
            "access": "Право на файлы, значения в типе scope_access",
        },
    ),
    "health_check": (
        "Настройка проверки блока",
        {
            "id": "Идентификатор проверки",
            "block_id": "Блок, состояние которого показывает проверка",
            "method": "Способ проверки, значения в типе check_method",
            "target": "Что проверяется: URL, хост и порт, команда или текст строки журнала",
            "interval_sec": "Как часто выполняется проверка, секунды",
            "timeout_sec": "Сколько ждать ответа, секунды",
            "name": "Название для интерфейса. Если пусто, строится из метода и цели",
            "config": "Параметры метода в JSON: ожидаемый код ответа, текст в ответе, порог задержки, "
            "за сколько дней предупреждать об истечении сертификата",
            "enabled": "Выключенная проверка не влияет на статус блока",
        },
    ),
    "check_result": (
        "Результат одного выполнения проверки",
        {
            "id": "Идентификатор результата",
            "health_check_id": "Проверка, к которой относится результат",
            "checked_at": "Момент выполнения проверки",
            "status": "Итог проверки, значения в типе check_status",
            "latency_ms": "Время ответа, миллисекунды",
            "message": "Короткое описание результата для человека",
            "error_kind": "Код вида ошибки латиницей: timeout, dns, tls, http_status и другие",
            "details": "Подробности ошибки в JSON: адрес, код ответа, фрагмент тела. Не больше 8000 символов",
        },
    ),
    "user_session": (
        "Сессия входа пользователя",
        {
            "id": "Идентификатор сессии",
            "user_id": "Пользователь, который вошёл",
            "token_hash": "SHA-256 токена сессии из cookie pult_session. Сам токен не хранится",
            "expires_at": "Момент, после которого сессия недействительна",
            "created_at": "Момент входа",
        },
    ),
    "agent_task": (
        "Задача ИИ-агенту по блоку",
        {
            "id": "Идентификатор задачи",
            "block_id": "Блок, по которому поставлена задача",
            "author_id": "Пользователь, который поставил задачу",
            "title": "Формулировка задачи",
            "status": "Этап задачи, значения в типе task_status",
            "finished_at": "Момент завершения. Пусто, пока задача не закрыта",
            "created_at": "Момент постановки задачи",
        },
    ),
    "task_message": (
        "Сообщение в чате задачи агента",
        {
            "id": "Идентификатор сообщения",
            "task_id": "Задача, к которой относится сообщение",
            "role": "Автор сообщения, значения в типе message_role",
            "content": "Содержимое сообщения: список блоков в формате Claude API (JSON)",
            "input_tokens": "Входные токены модели на это сообщение",
            "output_tokens": "Выходные токены модели на это сообщение",
            "created_at": "Момент сообщения",
        },
    ),
    "change_request": (
        "Pull request, который агент открыл по задаче, и решение по его ревью",
        {
            "id": "Идентификатор запроса на изменение",
            "task_id": "Задача. У задачи не больше одного pull request",
            "branch_name": "Ветка с изменениями агента",
            "pr_number": "Номер pull request в репозитории проекта",
            "status": "Состояние pull request, значения в типе cr_status",
            "reviewer_id": "Пользователь, который принял решение по ревью",
            "reviewed_at": "Момент решения по ревью",
        },
    ),
    "deployment": (
        "Выкатка слитого pull request на систему клиента",
        {
            "id": "Идентификатор выкатки",
            "change_request_id": "Pull request, изменения которого выкатываются",
            "commit_sha": "Хэш выкатываемого коммита, 40 шестнадцатеричных символов",
            "status": "Состояние выкатки, значения в типе deploy_status",
            "started_at": "Момент начала выкатки",
            "finished_at": "Момент окончания. Пусто, пока выкатка идёт",
        },
    ),
    "audit_event": (
        "Запись журнала аудита: кто, что и когда сделал",
        {
            "id": "Идентификатор записи",
            "user_id": "Кто выполнил действие. Пусто для действий системы",
            "block_id": "Блок, к которому относится действие. После удаления блока обнуляется",
            "action": "Код действия, например change_request.approved",
            "payload": "Подробности действия в JSON",
            "created_at": "Момент действия",
        },
    ),
    "alembic_version": (
        "Служебная таблица Alembic: версия схемы, до которой применены миграции",
        {"version_num": "Номер последней применённой миграции"},
    ),
}

VIEWS: dict[str, tuple[str, dict[str, str]]] = {
    "v_block_status": (
        "Статус каждого блока по последним результатам его включённых проверок",
        {
            "block_id": "Блок",
            "project_id": "Проект блока",
            "name": "Имя блока",
            "status": "Худший статус проверок блока: fail, warn, ok "
            "или unknown, если данных нет или они устарели",
        },
    ),
}

TYPES = {
    "member_role": "owner — владелец: настраивает проект, блоки, проверки и участников; "
    "developer — разработчик: видит всё и запускает проверки; "
    "client — заказчик: видит состояние своей системы",
    "block_kind": "server — сервер; scheduled_job — задание по расписанию; bot — бот; "
    "integration — внешняя интеграция; config — конфигурация; storage — хранилище файлов или данных",
    "scope_access": "read — агент только читает файлы; write — агент читает и меняет файлы",
    "check_method": "heartbeat — сервер клиента сам отмечается раз в интервал; http — запрос к URL; "
    "log_pattern — поиск строки в журнале; exit_code — код завершения задания; "
    "tls — срок действия сертификата; tcp — порт принимает соединение",
    "check_status": "ok — в норме; warn — работает с отклонением; fail — сбой",
    "task_status": "new — поставлена; running — агент работает; awaiting_review — pull request ждёт ревью; "
    "approved — изменения одобрены; rejected — отклонены; deployed — выкачены; failed — агент не справился",
    "message_role": "user — сообщение человека; assistant — ответ агента; "
    "tool — результат инструмента агента",
    "cr_status": "open — открыт; approved — одобрен; changes_requested — нужны правки; "
    "merged — слит; closed — закрыт без слияния",
    "deploy_status": "running — идёт; succeeded — успешно; failed — с ошибкой; rolled_back — откачена",
}

PRIMARY_KEYS = {
    "app_user": "Пользователь однозначно определяется идентификатором",
    "project": "Проект однозначно определяется идентификатором",
    "project_member": "Пользователь входит в проект один раз и с одной ролью",
    "block": "Блок однозначно определяется идентификатором",
    "block_link": "Связь однозначно определяется идентификатором",
    "block_scope": "Запись области однозначно определяется идентификатором",
    "health_check": "Проверка однозначно определяется идентификатором",
    "check_result": "Результат однозначно определяется идентификатором",
    "user_session": "Сессия однозначно определяется идентификатором",
    "agent_task": "Задача однозначно определяется идентификатором",
    "task_message": "Сообщение однозначно определяется идентификатором",
    "change_request": "Запрос на изменение однозначно определяется идентификатором",
    "deployment": "Выкатка однозначно определяется идентификатором",
    "audit_event": "Запись аудита однозначно определяется идентификатором",
}

CONSTRAINTS = [
    (
        "block",
        "block_project_id_fkey",
        "Блок принадлежит существующему проекту. CASCADE: блоки — часть проекта",
    ),
    ("project_member", "project_member_project_id_fkey", "Участие в удалённом проекте теряет смысл. CASCADE"),
    (
        "project_member",
        "project_member_user_id_fkey",
        "Участие удалённого пользователя теряет смысл. CASCADE",
    ),
    ("block_link", "block_link_source_block_id_fkey", "Связь без блока-источника невозможна. CASCADE"),
    ("block_link", "block_link_target_block_id_fkey", "Связь без блока-приёмника невозможна. CASCADE"),
    ("block_scope", "block_scope_block_id_fkey", "Область доступа — часть настройки блока. CASCADE"),
    ("health_check", "health_check_block_id_fkey", "Проверка — часть настройки блока. CASCADE"),
    ("check_result", "check_result_health_check_id_fkey", "Результаты без проверки не нужны. CASCADE"),
    ("user_session", "user_session_user_id_fkey", "Сессии удалённого пользователя закрываются. CASCADE"),
    ("agent_task", "agent_task_block_id_fkey", "Задачи по удалённому блоку удаляются вместе с ним. CASCADE"),
    (
        "agent_task",
        "agent_task_author_id_fkey",
        "Нельзя удалить пользователя, который ставил задачи: история задач хранит автора. RESTRICT",
    ),
    ("task_message", "task_message_task_id_fkey", "Сообщения — часть задачи. CASCADE"),
    (
        "change_request",
        "change_request_task_id_fkey",
        "Pull request существует только в рамках задачи. CASCADE",
    ),
    (
        "change_request",
        "change_request_reviewer_id_fkey",
        "Нельзя удалить пользователя, который принимал решение по ревью: "
        "решение должно иметь автора. RESTRICT",
    ),
    ("deployment", "deployment_change_request_id_fkey", "Выкатка относится к pull request. CASCADE"),
    (
        "audit_event",
        "audit_event_user_id_fkey",
        "Нельзя удалить пользователя, у которого есть записи аудита: журнал не теряет авторов. RESTRICT",
    ),
    (
        "audit_event",
        "audit_event_block_id_fkey",
        "Журнал аудита переживает удаление блока: ссылка обнуляется, запись остаётся. SET NULL",
    ),
    ("app_user", "app_user_email_key", "Один адрес почты — один пользователь: адрес служит логином"),
    ("project", "uq_project_probe_token_hash", "По токену probe однозначно определяется проект"),
    ("block", "block_project_id_name_key", "В одном проекте нет двух блоков с одинаковым именем"),
    ("block_link", "uq_block_link_source_target", "Между двумя блоками в одну сторону не больше одной связи"),
    ("block_scope", "uq_block_scope_block_id_path_glob", "Один и тот же путь не выдаётся блоку дважды"),
    ("user_session", "user_session_token_hash_key", "Токен сессии указывает ровно на одну сессию"),
    ("change_request", "change_request_task_id_key", "У задачи не больше одного pull request"),
    ("block_link", "block_link_not_self", "Блок не может быть связан сам с собой"),
    ("project", "ck_project_name_not_blank", "У проекта есть название"),
    ("project", "ck_project_default_branch_not_blank", "У репозитория указана основная ветка"),
    ("project", "ck_project_repo_full_name_format", "Репозиторий указан как владелец/имя, как на GitHub"),
    (
        "app_user",
        "ck_app_user_email_format",
        "Логин — адрес почты в нижнем регистре, чтобы Ivan@ и ivan@ не стали двумя людьми",
    ),
    ("app_user", "ck_app_user_full_name_not_blank", "У пользователя есть имя для интерфейса"),
    ("block", "ck_block_name_not_blank", "У блока есть имя на доске"),
    (
        "block_scope",
        "ck_block_scope_relative_path",
        "Агент работает только внутри репозитория: путь относительный, без «..» и обратной косой черты",
    ),
    (
        "health_check",
        "ck_health_check_interval_range",
        "Проверка не чаще раза в 10 с и не реже раза в неделю",
    ),
    ("health_check", "ck_health_check_timeout_range", "Ответа ждём от 1 до 60 с"),
    (
        "health_check",
        "ck_health_check_timeout_within_interval",
        "Проверка не может ждать ответа дольше своего интервала, иначе запуски наложатся",
    ),
    ("health_check", "ck_health_check_target_not_blank", "У проверки есть цель"),
    ("check_result", "ck_check_result_latency_not_negative", "Время ответа не бывает отрицательным"),
    (
        "check_result",
        "ck_check_result_error_kind_format",
        "Код ошибки — латиница и подчёркивание, до 40 символов",
    ),
    ("user_session", "ck_user_session_expires_after_created", "Сессия истекает позже, чем начинается"),
    ("agent_task", "ck_agent_task_title_not_blank", "У задачи есть формулировка"),
    (
        "agent_task",
        "ck_agent_task_finished_after_created",
        "Задача не может завершиться раньше, чем поставлена",
    ),
    ("task_message", "ck_task_message_tokens_not_negative", "Расход токенов не бывает отрицательным"),
    (
        "change_request",
        "ck_change_request_pr_number_positive",
        "Номера pull request на GitHub начинаются с 1",
    ),
    (
        "change_request",
        "ck_change_request_reviewed_by_reviewer",
        "Если ревью проведено, известно, кто его провёл",
    ),
    (
        "deployment",
        "ck_deployment_commit_sha_format",
        "Выкатывается конкретный коммит: полный хэш из 40 символов",
    ),
    (
        "deployment",
        "ck_deployment_finished_after_started",
        "Выкатка не может закончиться раньше, чем началась",
    ),
    (
        "deployment",
        "ck_deployment_finished_when_done",
        "У идущей выкатки нет времени окончания, у завершённой оно есть",
    ),
    ("audit_event", "ck_audit_event_action_not_blank", "У записи аудита есть код действия"),
    ("alembic_version", "alembic_version_pkc", "Версия схемы записана ровно один раз"),
]

INDEXES = {
    "ix_block_project_id": "Блоки проекта: загрузка графа GET /projects/{id}/graph и проверка прав",
    "ix_block_link_target_block_id": "Каскадное удаление связей при удалении блока-приёмника. "
    "Поиск по источнику покрывает uq_block_link_source_target",
    "ix_health_check_block_id": "Проверки блока: GET /blocks/{id}/checks, расчёт статусов графа, "
    "каскадное удаление при удалении блока",
    "ix_check_result_check_time": "Последний результат и история проверки: представление v_block_status, "
    "панель проверок, расчёт начала сбоя",
    "ix_check_result_checked_at_brin": "Выборки результатов за период по времени, "
    "компактный BRIN для журнала, "
    "который пишется по возрастанию времени",
    "ix_project_member_user_id": "Проекты пользователя: GET /auth/me и GET /projects. "
    "Первичный ключ начинается с project_id и этот запрос не покрывает",
    "ix_agent_task_block_id": "Каскадное удаление задач при удалении блока",
    "ix_task_message_task_id": "Сообщения задачи: чат задачи и каскадное удаление",
    "ix_audit_event_block_id": "Обнуление ссылок аудита при удалении блока и журнал действий по блоку",
    "uq_deployment_one_running": "У pull request не может идти две выкатки одновременно",
}


def quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def statements() -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for kind, objects in (("TABLE", TABLES), ("VIEW", VIEWS)):
        for name, (comment, columns) in objects.items():
            items.append((f"COMMENT ON {kind} {name}", comment))
            items.extend((f"COMMENT ON COLUMN {name}.{column}", text) for column, text in columns.items())
    items.extend((f"COMMENT ON TYPE {name}", text) for name, text in TYPES.items())
    items.extend(
        (f"COMMENT ON CONSTRAINT {table}_pkey ON {table}", text) for table, text in PRIMARY_KEYS.items()
    )
    items.extend((f"COMMENT ON CONSTRAINT {name} ON {table}", text) for table, name, text in CONSTRAINTS)
    items.extend((f"COMMENT ON INDEX {name}", text) for name, text in INDEXES.items())
    return items


def upgrade() -> None:
    for target, text in statements():
        op.execute(f"{target} IS {quote(text)}")


def downgrade() -> None:
    for target, _ in statements():
        op.execute(f"{target} IS NULL")
