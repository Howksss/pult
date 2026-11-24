import enum

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, pg_check


class BlockKind(str, enum.Enum):
    server = "server"
    scheduled_job = "scheduled_job"
    bot = "bot"
    integration = "integration"
    config = "config"
    storage = "storage"


class ScopeAccess(str, enum.Enum):
    read = "read"
    write = "write"


class Project(CreatedAtMixin, Base):
    __tablename__ = "project"
    __table_args__ = (
        CheckConstraint("trim(name) <> ''", name="ck_project_name_not_blank"),
        CheckConstraint("trim(default_branch) <> ''", name="ck_project_default_branch_not_blank"),
        pg_check("repo_full_name ~ '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'", "ck_project_repo_full_name_format"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    repo_full_name: Mapped[str] = mapped_column(String(200))
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    probe_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)

    blocks: Mapped[list["Block"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Block.id"
    )


class Block(CreatedAtMixin, Base):
    __tablename__ = "block"
    __table_args__ = (
        UniqueConstraint("project_id", "name"),
        CheckConstraint("trim(name) <> ''", name="ck_block_name_not_blank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    kind: Mapped[BlockKind] = mapped_column(Enum(BlockKind, name="block_kind"))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    pos_x: Mapped[float] = mapped_column(default=0)
    pos_y: Mapped[float] = mapped_column(default=0)

    project: Mapped[Project] = relationship(back_populates="blocks")


class BlockLink(Base):
    __tablename__ = "block_link"
    __table_args__ = (
        CheckConstraint("source_block_id <> target_block_id", name="block_link_not_self"),
        UniqueConstraint("source_block_id", "target_block_id", name="uq_block_link_source_target"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_block_id: Mapped[int] = mapped_column(ForeignKey("block.id", ondelete="CASCADE"))
    target_block_id: Mapped[int] = mapped_column(ForeignKey("block.id", ondelete="CASCADE"), index=True)
    label: Mapped[str | None] = mapped_column(String(100))


class BlockScope(Base):
    __tablename__ = "block_scope"
    __table_args__ = (
        UniqueConstraint("block_id", "path_glob", name="uq_block_scope_block_id_path_glob"),
        pg_check(
            "path_glob <> '' AND left(path_glob, 1) <> '/' AND strpos(path_glob, chr(92)) = 0 "
            "AND path_glob !~ '(^|/)[.][.](/|$)'",
            "ck_block_scope_relative_path",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey("block.id", ondelete="CASCADE"))
    path_glob: Mapped[str] = mapped_column(String(300))
    access: Mapped[ScopeAccess] = mapped_column(Enum(ScopeAccess, name="scope_access"))
