import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, pg_check


class MemberRole(str, enum.Enum):
    owner = "owner"
    developer = "developer"
    client = "client"


class AppUser(CreatedAtMixin, Base):
    __tablename__ = "app_user"
    __table_args__ = (
        pg_check(
            "email ~ '^[^@[:space:]]+@[^@[:space:]]+[.][^@[:space:]]+$' AND email = lower(email)",
            "ck_app_user_email_format",
        ),
        CheckConstraint("trim(full_name) <> ''", name="ck_app_user_full_name_not_blank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(255))


class ProjectMember(Base):
    __tablename__ = "project_member"

    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[MemberRole] = mapped_column(Enum(MemberRole, name="member_role"))


class UserSession(CreatedAtMixin, Base):
    __tablename__ = "user_session"
    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="ck_user_session_expires_after_created"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
