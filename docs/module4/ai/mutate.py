import subprocess
import sys
from pathlib import Path

target = Path("app/services/graph_status.py")
original = target.read_text(encoding="utf-8")
mutants = {
    "M1 проверка без результатов пропускается": (
        "            snapshots[block_id].append(None)\n",
        "            continue\n",
    ),
    "M2 берётся самый старый результат": (
        ".order_by(CheckResult.checked_at.desc())",
        ".order_by(CheckResult.checked_at.asc())",
    ),
    "M3 наивное время считается локальным": (
        "moment.replace(tzinfo=UTC)",
        "moment.astimezone(UTC)",
    ),
    "M4 блоки без проверок выпадают из ответа": (
        "for block_id in block_ids}",
        "for block_id in snapshots}",
    ),
    "M5 вместо интервала берётся таймаут проверки": (
        "select(HealthCheck.block_id, HealthCheck.interval_sec,",
        "select(HealthCheck.block_id, HealthCheck.timeout_sec,",
    ),
}
test_file = sys.argv[1]
try:
    for name, (old, new) in mutants.items():
        assert old in original, name
        target.write_text(original.replace(old, new), encoding="utf-8", newline="\n")
        run = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "pytest", "-p", "no:cacheprovider", "--no-cov", "-q", "-rf", test_file],
            capture_output=True, text=True, encoding="utf-8",
        )
        failed = [line.split("::")[1].split(" ")[0] for line in run.stdout.splitlines() if line.startswith("FAILED")]
        print(f"{name}: {'УБИТ' if failed else 'ВЫЖИЛ'}")
        for test in failed:
            print(f"    {test}")
finally:
    target.write_text(original, encoding="utf-8", newline="\n")
