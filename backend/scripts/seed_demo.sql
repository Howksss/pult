BEGIN;

DO $$ BEGIN PERFORM setseed(0.42); END $$;

INSERT INTO app_user (email, full_name, password_hash)
VALUES
    ('owner@example.com', 'Владелец проекта', 'argon2-hash-placeholder'),
    ('client@example.com', 'Управляющий сети', 'argon2-hash-placeholder');

INSERT INTO project (name, description, repo_full_name, default_branch, probe_token_hash)
VALUES (
    'Пилот: планирование выпечки',
    'Ежедневный расчёт плана выпечки для сети пекарен и рассылка в Telegram',
    'example/pilot-system',
    'main',
    encode(sha256('demo-probe-token'::bytea), 'hex')
);

INSERT INTO project_member (project_id, user_id, role)
SELECT p.id, u.id, CASE WHEN u.email LIKE 'owner%' THEN 'owner'::member_role ELSE 'client'::member_role END
FROM project AS p
CROSS JOIN app_user AS u;

INSERT INTO block (project_id, kind, name, description, pos_x, pos_y)
SELECT p.id, b.kind::block_kind, b.name, b.description, b.x, b.y
FROM project AS p
CROSS JOIN (
    VALUES
        ('server', 'VPS', 'Сервер Ubuntu, cron', 0, 0),
        ('scheduled_job', 'Расчёт плана', 'Прогон в 08:00', 260, -80),
        ('scheduled_job', 'Автозаказ', 'Прогон в 09:00', 260, 80),
        ('integration', 'POS-система', 'Продажи и остатки', 520, -160),
        ('integration', 'Погода API', 'Прогноз на завтра', 520, -40),
        ('config', 'Конфигурация', 'Настройки и коэффициенты', 520, 80),
        ('storage', 'Excel-шаблоны', 'Шаблоны планов точек', 520, 200),
        ('bot', 'Telegram-бот', 'Рассылка планов управляющим', 780, 0)
) AS b (kind, name, description, x, y);

INSERT INTO block_link (source_block_id, target_block_id, label)
SELECT s.id, t.id, l.label
FROM (
    VALUES
        ('VPS', 'Расчёт плана', 'cron 08:00'),
        ('VPS', 'Автозаказ', 'cron 09:00'),
        ('Расчёт плана', 'POS-система', 'продажи за 8 недель'),
        ('Расчёт плана', 'Погода API', 'прогноз'),
        ('Расчёт плана', 'Конфигурация', 'коэффициенты'),
        ('Расчёт плана', 'Excel-шаблоны', 'заполнение'),
        ('Расчёт плана', 'Telegram-бот', 'файлы планов'),
        ('Автозаказ', 'POS-система', 'остатки'),
        ('Автозаказ', 'Telegram-бот', 'заказ')
) AS l (source_name, target_name, label)
JOIN block AS s ON s.name = l.source_name
JOIN block AS t ON t.name = l.target_name;

INSERT INTO block_scope (block_id, path_glob, access)
SELECT b.id, s.path_glob, s.access::scope_access
FROM (
    VALUES
        ('Расчёт плана', 'pipeline/**', 'write'),
        ('Расчёт плана', 'tests/test_calculator.py', 'write'),
        ('Конфигурация', 'config.example.yaml', 'write'),
        ('Telegram-бот', 'bots/**', 'write'),
        ('POS-система', 'integrations/pos.py', 'read')
) AS s (block_name, path_glob, access)
JOIN block AS b ON b.name = s.block_name;

INSERT INTO health_check (block_id, method, target, interval_sec, timeout_sec)
SELECT b.id, c.method::check_method, c.target, 60, 10
FROM (
    VALUES
        ('VPS', 'heartbeat', 'probe'),
        ('Расчёт плана', 'exit_code', 'main.py'),
        ('Автозаказ', 'exit_code', 'main_orders.py'),
        ('POS-система', 'http', 'https://pos.example/api/ping'),
        ('Погода API', 'http', 'https://weather.example/forecast'),
        ('Конфигурация', 'log_pattern', 'ConfigError'),
        ('Excel-шаблоны', 'log_pattern', 'TemplateError'),
        ('Telegram-бот', 'http', 'https://api.telegram.org/getMe')
) AS c (block_name, method, target)
JOIN block AS b ON b.name = c.block_name;

INSERT INTO check_result (health_check_id, checked_at, status, latency_ms, message)
SELECT
    hc.id,
    ts,
    CASE
        WHEN r < 0.004 THEN 'fail'::check_status
        WHEN r < 0.02 THEN 'warn'::check_status
        ELSE 'ok'::check_status
    END,
    (40 + random() * 160)::int,
    NULL
FROM health_check AS hc
JOIN block AS b ON b.id = hc.block_id
CROSS JOIN generate_series(
    date_trunc('minute', now()) - interval '30 days',
    date_trunc('minute', now()) - interval '1 minute',
    interval '1 minute'
) AS ts
CROSS JOIN LATERAL (SELECT random() AS r, ts AS sample_time, hc.id AS check_id) AS rnd
WHERE NOT (b.name = 'Погода API' AND ts > now() - interval '20 minutes')
ORDER BY ts, hc.id;

INSERT INTO check_result (health_check_id, checked_at, status, latency_ms, message)
SELECT hc.id, date_trunc('minute', now()), 'fail', 10000, 'timeout after 10 s'
FROM health_check AS hc
JOIN block AS b ON b.id = hc.block_id
WHERE b.name = 'POS-система';

INSERT INTO agent_task (block_id, author_id, title, status, finished_at)
SELECT b.id, u.id, 'POS-система не отвечает, план не рассчитан', 'awaiting_review', NULL
FROM block AS b
CROSS JOIN app_user AS u
WHERE b.name = 'POS-система' AND u.email = 'client@example.com';

COMMIT;

VACUUM (ANALYZE) block, health_check, check_result;
