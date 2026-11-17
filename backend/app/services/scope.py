import re
from collections.abc import Iterable
from functools import lru_cache

from app.models import ScopeAccess

DRIVE = re.compile(r"^[A-Za-z]:")


def split_parts(path: str) -> list[str] | None:
    if not path or "\\" in path or path.startswith("/") or DRIVE.match(path):
        return None
    if any(ord(char) < 32 for char in path):
        return None
    parts = [part for part in path.split("/") if part not in ("", ".")]
    if not parts or ".." in parts:
        return None
    return parts


def normalize_glob(pattern: str) -> str:
    pattern = pattern.strip()
    if not pattern:
        raise ValueError("путь не указан")
    if "\\" in pattern:
        raise ValueError("используйте / вместо \\")
    if pattern.startswith("/") or DRIVE.match(pattern):
        raise ValueError("путь должен быть относительным от корня репозитория")
    if any(ord(char) < 32 for char in pattern):
        raise ValueError("в пути недопустимые символы")
    if ".." in pattern.split("/"):
        raise ValueError("путь не может выходить за репозиторий: «..» запрещено")
    parts = split_parts(pattern)
    if parts is None:
        raise ValueError("путь не указан")
    normalized = "/".join(parts)
    return f"{normalized}/**" if pattern.endswith("/") else normalized


def normalize_path(path: str) -> str | None:
    parts = split_parts(path.strip())
    return "/".join(parts) if parts else None


@lru_cache(maxsize=512)
def glob_regex(pattern: str) -> re.Pattern[str]:
    out = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif pattern[index] == "*":
            out.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(pattern[index]))
            index += 1
    return re.compile("".join(out))


def allows(scopes: Iterable[tuple[str, ScopeAccess]], path: str, access: ScopeAccess) -> bool:
    normalized = normalize_path(path)
    if normalized is None:
        return False
    for pattern, granted in scopes:
        if access is ScopeAccess.write and granted is not ScopeAccess.write:
            continue
        if glob_regex(pattern).fullmatch(normalized):
            return True
    return False
