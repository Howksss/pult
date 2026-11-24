import re
from pathlib import Path

from sqlalchemy import CHAR, JSON, Boolean, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.types import TypeEngine

from app.models import Base

DIAGRAM = Path(__file__).resolve().parents[2] / "docs" / "data" / "er_diagram.puml"
ENTITY = re.compile(r"entity (\w+) \{(.*?)\n\}", re.S)
COLUMN = re.compile(r"^(\*)?\s*(\w+) : ([^<]+?)\s*(<<.*>>)?$")


def diagram() -> dict[str, dict[str, tuple[str, bool]]]:
    tables: dict[str, dict[str, tuple[str, bool]]] = {}
    for name, body in ENTITY.findall(DIAGRAM.read_text(encoding="utf-8")):
        columns = {}
        for line in body.splitlines():
            match = COLUMN.match(line.strip())
            if match:
                columns[match.group(2)] = (match.group(3), match.group(1) == "*")
        tables[name] = columns
    return tables


def sql_type(column_type: TypeEngine[object]) -> str:
    if isinstance(column_type, Enum):
        return str(column_type.name)
    if isinstance(column_type, CHAR):
        return f"char({column_type.length})"
    if isinstance(column_type, String) and not isinstance(column_type, Text):
        return f"varchar({column_type.length})"
    names: list[tuple[type, str]] = [
        (Text, "text"),
        (Boolean, "boolean"),
        (Integer, "integer"),
        (Float, "double precision"),
        (JSON, "jsonb"),
    ]
    if isinstance(column_type, DateTime):
        return "timestamptz" if column_type.timezone else "timestamp"
    return next(name for kind, name in names if isinstance(column_type, kind))


def models() -> dict[str, dict[str, tuple[str, bool]]]:
    return {
        table.name: {column.name: (sql_type(column.type), not column.nullable) for column in table.columns}
        for table in Base.metadata.sorted_tables
    }


def test_diagram_has_every_table_and_nothing_else():
    assert sorted(diagram()) == sorted(models())


def test_diagram_columns_types_and_nullability_match_models():
    drawn = diagram()
    for table, columns in models().items():
        assert drawn[table] == columns, table
