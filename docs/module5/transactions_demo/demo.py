import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENCODING = "cp1251" if os.name == "nt" else "utf-8"
CLIENT_ENCODING = "WIN1251" if os.name == "nt" else "UTF8"
BALANCES = "SELECT id, owner, balance FROM accounts ORDER BY id;"

SCENARIOS = {
    "01_commit": [
        ("A", BALANCES),
        ("A", "BEGIN;"),
        ("A", "UPDATE accounts SET balance = balance - 300 WHERE id = 1;"),
        ("A", "UPDATE accounts SET balance = balance + 300 WHERE id = 2;"),
        ("A", "INSERT INTO transfer_log (from_id, to_id, amount) VALUES (1, 2, 300);"),
        ("A", "COMMIT;"),
        ("A", BALANCES),
        ("A", "SELECT count(*) AS transfers FROM transfer_log;"),
    ],
    "02_rollback": [
        ("A", "BEGIN;"),
        ("A", "UPDATE accounts SET balance = balance - 200 WHERE id = 1;"),
        ("A", "SELECT balance FROM accounts WHERE id = 1;"),
        ("B", "SELECT balance FROM accounts WHERE id = 1;"),
        ("A", "INSERT INTO transfer_log (from_id, to_id, amount) VALUES (1, 3, 200);"),
        ("A", "UPDATE accounts SET balance = balance + 200 WHERE id = 3;"),
        ("A", "ROLLBACK;"),
        ("A", BALANCES),
        ("A", "SELECT count(*) AS transfers FROM transfer_log;"),
    ],
    "03_check": [
        ("A", "BEGIN;"),
        ("A", "UPDATE accounts SET balance = balance + 5000 WHERE id = 2;"),
        ("A", "UPDATE accounts SET balance = balance - 5000 WHERE id = 1;"),
        ("A", "ROLLBACK;"),
        ("A", BALANCES),
    ],
    "04_read_committed": [
        ("A", "BEGIN ISOLATION LEVEL READ COMMITTED;"),
        ("A", "SELECT balance FROM accounts WHERE id = 1;"),
        ("B", "UPDATE accounts SET balance = balance + 100 WHERE id = 1;"),
        ("A", "SELECT balance FROM accounts WHERE id = 1;"),
        ("A", "COMMIT;"),
    ],
    "05_repeatable_read": [
        ("A", "BEGIN ISOLATION LEVEL REPEATABLE READ;"),
        ("A", "SELECT balance FROM accounts WHERE id = 1;"),
        ("B", "UPDATE accounts SET balance = balance + 100 WHERE id = 1;"),
        ("A", "SELECT balance FROM accounts WHERE id = 1;"),
        ("A", "UPDATE accounts SET balance = balance - 50 WHERE id = 1;"),
        ("A", "ROLLBACK;"),
        ("A", "SELECT balance FROM accounts WHERE id = 1;"),
    ],
}


class Psql:
    def __init__(self, database: str) -> None:
        env = dict(os.environ, LANG="C", LC_ALL="C", LANGUAGE="en", PGCLIENTENCODING=CLIENT_ENCODING)
        self.process = subprocess.Popen(
            ["psql", "-X", "-q", "-v", "ON_ERROR_STOP=0", "-d", database],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding=ENCODING,
            env=env,
            bufsize=1,
        )

    def run(self, sql: str) -> list[str]:
        assert self.process.stdin is not None and self.process.stdout is not None
        self.process.stdin.write(sql + "\n\\echo __done__\n")
        self.process.stdin.flush()
        lines = []
        for line in self.process.stdout:
            if line.strip() == "__done__":
                break
            if line.strip():
                lines.append(line.rstrip())
        return lines

    def close(self) -> None:
        assert self.process.stdin is not None
        self.process.stdin.close()
        self.process.wait()


def setup(database: str) -> None:
    subprocess.run(
        ["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-d", database, "-f", str(HERE / "setup.sql")],
        check=True,
    )


def play(database: str, steps: list[tuple[str, str]]) -> str:
    sessions = {"A": Psql(database), "B": Psql(database)}
    transcript = []
    for name, sql in steps:
        transcript.append(f"{name}=> {sql}")
        transcript.extend(f"     {line}" for line in sessions[name].run(sql))
    for session in sessions.values():
        session.close()
    return "\n".join(transcript) + "\n"


def main(database: str) -> None:
    setup(database)
    for name, steps in SCENARIOS.items():
        if name == "04_read_committed":
            setup(database)
        output = play(database, steps)
        (HERE / f"{name}.txt").write_text(output, encoding="utf-8", newline="\n")
        sys.stdout.write(f"== {name}\n{output}\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "bank_demo")
