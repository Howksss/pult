import sys
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Connection, create_engine, text

from app.core.config import get_settings

ORDER = [
    "app_user",
    "user_session",
    "project",
    "project_member",
    "block",
    "block_link",
    "block_scope",
    "health_check",
    "check_result",
    "agent_task",
    "task_message",
    "change_request",
    "deployment",
    "audit_event",
    "alembic_version",
]
ON_DELETE = {"a": "NO ACTION", "r": "RESTRICT", "c": "CASCADE", "n": "SET NULL", "d": "SET DEFAULT"}
KINDS = {"p": "PRIMARY KEY", "f": "FOREIGN KEY", "u": "UNIQUE", "c": "CHECK"}
TYPES = [
    ("timestamp with time zone", "timestamptz"),
    ("character varying", "varchar"),
    ("character(", "char("),
]

RELATIONS = """
select c.oid, c.relname, c.relkind, obj_description(c.oid, 'pg_class') as comment
from pg_class c
where c.relnamespace = 'public'::regnamespace and c.relkind in ('r', 'v')
"""
COLUMNS = """
select a.attnum, a.attname, format_type(a.atttypid, a.atttypmod) as type, a.attnotnull,
    pg_get_expr(d.adbin, d.adrelid) as default, col_description(a.attrelid, a.attnum) as comment
from pg_attribute a
left join pg_attrdef d on d.adrelid = a.attrelid and d.adnum = a.attnum
where a.attrelid = :oid and a.attnum > 0 and not a.attisdropped
order by a.attnum
"""
CONSTRAINTS = """
select k.conname, k.contype, k.conkey, pg_get_constraintdef(k.oid) as definition, k.confdeltype,
    k.confrelid::regclass::text as target, obj_description(k.oid, 'pg_constraint') as comment
from pg_constraint k
where k.conrelid = :oid
order by position(k.contype in 'pufc'), k.conname
"""
INDEXES = """
select i.relname, pg_get_indexdef(i.oid) as definition, obj_description(i.oid, 'pg_class') as comment
from pg_index x
join pg_class i on i.oid = x.indexrelid
where x.indrelid = :oid and not exists (select 1 from pg_constraint k where k.conindid = x.indexrelid)
order by i.relname
"""
ENUMS = """
select t.typname, obj_description(t.oid, 'pg_type') as comment
from pg_type t
where t.typnamespace = 'public'::regnamespace and t.typtype = 'e'
order by t.typname
"""
VERSION = "select version_num from alembic_version"


def cell(value: Any) -> str:
    return "" if value is None else str(value).replace("|", "\\|").replace("\n", " ")


def table(header: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)
    return [*lines, ""]


def short_type(name: str) -> str:
    for long, short in TYPES:
        name = name.replace(long, short)
    return name


def default(expression: str | None) -> str:
    if expression is None:
        return ""
    if expression.startswith("nextval("):
        return "автонумерация"
    return f"`{expression}`"


def column_rules(attnum: int, not_null: bool, constraints: Sequence[Any]) -> str:
    rules = []
    for row in constraints:
        if attnum not in row.conkey:
            continue
        if row.contype == "f":
            rules.append(f"FK → {row.target}, ON DELETE {ON_DELETE[row.confdeltype]}")
        elif row.contype in "pu":
            name = "PK" if row.contype == "p" else "UNIQUE"
            rules.append(name if len(row.conkey) == 1 else f"{name} (составной)")
        else:
            rules.append(f"CHECK {row.conname}")
    if not_null and not any(rule.startswith("PK") for rule in rules):
        rules.insert(0, "NOT NULL")
    return "; ".join(rules)


def relation_section(connection: Connection, relation: Any) -> list[str]:
    columns = connection.execute(text(COLUMNS), {"oid": relation.oid}).all()
    constraints = connection.execute(text(CONSTRAINTS), {"oid": relation.oid}).all()
    indexes = connection.execute(text(INDEXES), {"oid": relation.oid}).all()
    kind = "представление" if relation.relkind == "v" else "таблица"
    lines = [f"## {relation.relname}", "", f"{relation.comment} ({kind}).", ""]
    lines += table(
        ["Столбец", "Тип", "Обязательный", "По умолчанию", "Описание", "Ограничения"],
        [
            (
                f"`{column.attname}`",
                short_type(column.type),
                "да" if column.attnotnull else "нет",
                default(column.default),
                column.comment,
                column_rules(column.attnum, column.attnotnull, constraints),
            )
            for column in columns
        ],
    )
    if constraints:
        lines += ["Ограничения и правила, которые они защищают:", ""]
        lines += table(
            ["Ограничение", "Вид", "Определение", "Правило предметной области"],
            [(f"`{row.conname}`", KINDS[row.contype], row.definition, row.comment) for row in constraints],
        )
    if indexes:
        lines += ["Индексы и запросы, которые они ускоряют:", ""]
        lines += table(
            ["Индекс", "Определение", "Зачем"],
            [(f"`{row.relname}`", row.definition.split(" USING ")[-1], row.comment) for row in indexes],
        )
    return lines


def enum_section(connection: Connection) -> list[str]:
    lines = ["## Перечисления", "", "Значения перечислимых типов PostgreSQL (`ENUM`).", ""]
    for row in connection.execute(text(ENUMS)):
        lines += [f"### {row.typname}", ""]
        values = [part.split(" — ", 1) for part in row.comment.split("; ")]
        lines += table(["Значение", "Смысл"], [(f"`{value}`", meaning) for value, meaning in values])
    return lines


def render(connection: Connection) -> str:
    relations = {row.relname: row for row in connection.execute(text(RELATIONS))}
    names = [name for name in ORDER if name in relations]
    names += sorted(name for name in relations if name not in ORDER)
    version = connection.scalar(text(VERSION))
    lines = [
        "# Словарь данных",
        "",
        "Документ собран скриптом `backend/scripts/data_dictionary.py` из живой базы после "
        f"`alembic upgrade head` (версия схемы `{version}`). Описания берутся из комментариев "
        "`COMMENT ON` в базе (миграция 0009), поэтому словарь и схема не расходятся. Вручную не править: "
        "после изменения схемы запустить скрипт заново.",
        "",
        "Формат: таблица → столбец → тип → описание → ограничения. "
        "Ниже каждой таблицы — её ограничения с правилом предметной области и индексы с запросом, "
        "который они ускоряют.",
        "",
        "Содержание: "
        + ", ".join(f"[{name}](#{name})" for name in names)
        + ", [перечисления](#перечисления).",
        "",
    ]
    for name in names:
        lines += relation_section(connection, relations[name])
    lines += enum_section(connection)
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Sequence[str]) -> None:
    engine = create_engine(get_settings().database_url)
    with engine.connect() as connection:
        document = render(connection)
    if len(argv) > 1:
        with open(argv[1], "w", encoding="utf-8", newline="\n") as output:
            output.write(document)
    else:
        sys.stdout.write(document)


if __name__ == "__main__":
    main(sys.argv)
