import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiKey, AppUser
from app.services.auth import token_hash

KEY_PREFIX = "pult_"
SHOWN_CHARS = 12
TOUCH_EVERY = timedelta(minutes=1)


def as_utc(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def issue_key(session: Session, user: AppUser, name: str, days: int) -> tuple[ApiKey, str]:
    key = KEY_PREFIX + secrets.token_urlsafe(32)
    row = ApiKey(
        user_id=user.id,
        name=name,
        prefix=key[:SHOWN_CHARS],
        token_hash=token_hash(key),
        expires_at=datetime.now(UTC) + timedelta(days=days),
    )
    session.add(row)
    session.commit()
    return row, key


def user_by_api_key(session: Session, key: str) -> AppUser | None:
    row = session.scalar(select(ApiKey).where(ApiKey.token_hash == token_hash(key)))
    now = datetime.now(UTC)
    if row is None or as_utc(row.expires_at) <= now:
        return None
    if row.last_used_at is None or now - as_utc(row.last_used_at) >= TOUCH_EVERY:
        row.last_used_at = now
        session.commit()
    return session.get(AppUser, row.user_id)
