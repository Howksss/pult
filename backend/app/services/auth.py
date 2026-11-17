import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AppUser, UserSession

SESSION_DAYS = 30
COOKIE = "pult_session"

hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def open_session(session: Session, user: AppUser) -> str:
    token = new_token()
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=token_hash(token),
            expires_at=datetime.now(UTC) + timedelta(days=SESSION_DAYS),
        )
    )
    session.commit()
    return token


def user_by_token(session: Session, token: str | None) -> AppUser | None:
    if not token:
        return None
    row = session.scalar(select(UserSession).where(UserSession.token_hash == token_hash(token)))
    if row is None:
        return None
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
    if expires <= datetime.now(UTC):
        session.delete(row)
        session.commit()
        return None
    return session.get(AppUser, row.user_id)


def close_session(session: Session, token: str | None) -> None:
    if token:
        session.execute(delete(UserSession).where(UserSession.token_hash == token_hash(token)))
        session.commit()
