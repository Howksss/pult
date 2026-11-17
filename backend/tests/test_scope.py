import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.models import Block, BlockKind, Project, ScopeAccess
from app.services.scope import allows, normalize_glob, normalize_path
from tests.contract import assert_matches_contract

READ, WRITE = ScopeAccess.read, ScopeAccess.write
SCOPES = "/api/v1/blocks/{block_id}/scopes"
SCOPE = "/api/v1/scopes/{scope_id}"


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("pipeline/**", "pipeline/**"),
        ("  ./pipeline//calc.py ", "pipeline/calc.py"),
        ("bots/", "bots/**"),
        ("config.example.yaml", "config.example.yaml"),
    ],
)
def test_normalize_glob(pattern, expected):
    assert normalize_glob(pattern) == expected


@pytest.mark.parametrize(
    ("pattern", "message"),
    [
        ("", "путь не указан"),
        ("/etc/passwd", "относительным"),
        ("C:/Windows", "относительным"),
        ("pipeline\\calc.py", "используйте /"),
        ("../secrets", "«..» запрещено"),
        ("pipeline/../../.ssh", "«..» запрещено"),
        ("./", "путь не указан"),
        ("pipeline/.py", "недопустимые символы"),
    ],
)
def test_bad_globs_are_rejected(pattern, message):
    with pytest.raises(ValueError, match=message):
        normalize_glob(pattern)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("pipeline/calc.py", "pipeline/calc.py"),
        ("./pipeline//calc.py", "pipeline/calc.py"),
        ("../etc/passwd", None),
        ("pipeline/../../etc/passwd", None),
        ("/etc/passwd", None),
        ("C:/Windows/win.ini", None),
        ("pipeline\\calc.py", None),
        ("pipeline/\x00calc.py", None),
        ("", None),
    ],
)
def test_normalize_path(path, expected):
    assert normalize_path(path) == expected


SCOPE_SET = [
    ("pipeline/**", WRITE),
    ("tests/test_*.py", WRITE),
    ("integrations/pos.py", READ),
    ("docs/**/*.md", READ),
    ("config.?aml", READ),
]


@pytest.mark.parametrize(
    ("path", "access", "allowed"),
    [
        ("pipeline/calc.py", WRITE, True),
        ("pipeline/deep/nested/calc.py", WRITE, True),
        ("pipeline", WRITE, False),
        ("tests/test_calc.py", WRITE, True),
        ("tests/unit/test_calc.py", WRITE, False),
        ("integrations/pos.py", READ, True),
        ("integrations/pos.py", WRITE, False),
        ("pipeline/calc.py", READ, True),
        ("docs/readme.md", READ, True),
        ("docs/a/b/readme.md", READ, True),
        ("config.yaml", READ, True),
        ("config.yml", READ, False),
        ("pipeline/../.env", READ, False),
        (".env", READ, False),
        ("main.py", READ, False),
    ],
)
def test_allows(path, access, allowed):
    assert allows(SCOPE_SET, path, access) is allowed


def test_glob_characters_are_literal():
    assert allows([("reports/plan(1).xlsx", READ)], "reports/plan(1).xlsx", READ)
    assert not allows([("reports/plan(1).xlsx", READ)], "reports/plan1.xlsx", READ)


@pytest.fixture
def block_id(db: sessionmaker[Session], tester) -> int:
    with db() as session:
        block = Block(
            project=Project(name="pilot", repo_full_name="example/pilot"),
            kind=BlockKind.scheduled_job,
            name="Расчёт плана",
        )
        session.add(block)
        session.commit()
        tester.join(block.project_id)
        return block.id


def call(client, method, template, expected, *, json=None, **params):
    response = client.request(method, template.format(**params), json=json)
    assert response.status_code == expected, response.text
    assert_matches_contract(method, template, response)
    return response


def test_scope_lifecycle(client, block_id):
    first = call(
        client, "POST", SCOPES, 201, json={"path_glob": "pipeline/", "access": "write"}, block_id=block_id
    )
    call(client, "POST", SCOPES, 201, json={"path_glob": "integrations/pos.py"}, block_id=block_id)
    listed = call(client, "GET", SCOPES, 200, block_id=block_id).json()
    assert [(scope["path_glob"], scope["access"]) for scope in listed] == [
        ("integrations/pos.py", "read"),
        ("pipeline/**", "write"),
    ]
    scope_id = first.json()["id"]
    assert (
        call(client, "PATCH", SCOPE, 200, json={"access": "read"}, scope_id=scope_id).json()["access"]
        == "read"
    )
    call(client, "DELETE", SCOPE, 204, scope_id=scope_id)
    assert len(call(client, "GET", SCOPES, 200, block_id=block_id).json()) == 1


def test_duplicate_scope_is_conflict(client, block_id):
    call(client, "POST", SCOPES, 201, json={"path_glob": "bots/**"}, block_id=block_id)
    body = call(client, "POST", SCOPES, 409, json={"path_glob": "./bots/"}, block_id=block_id).json()
    assert body["detail"] == "path bots/** is already in the block scope"


@pytest.mark.parametrize(
    "payload", [{"path_glob": "../.ssh/id_rsa"}, {"path_glob": "/etc"}, {"path_glob": "x", "access": "admin"}]
)
def test_bad_scopes_are_rejected(client, block_id, payload):
    call(client, "POST", SCOPES, 422, json=payload, block_id=block_id)


def test_unknown_block_and_scope_are_404(client, block_id):
    call(client, "GET", SCOPES, 404, block_id=999)
    call(client, "POST", SCOPES, 404, json={"path_glob": "a.py"}, block_id=999)
    call(client, "PATCH", SCOPE, 404, json={"access": "write"}, scope_id=999)
    call(client, "DELETE", SCOPE, 404, scope_id=999)
