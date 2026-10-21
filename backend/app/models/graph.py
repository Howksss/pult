import enum

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin


class BlockKind(str, enum.Enum):
    server = "server"
    scheduled_job = "scheduled_job"
    bot = "bot"
    integration = "integration"
    config = "config"
    storage = "storage"


class Project(CreatedAtMixin, Base):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    repo_full_name: Mapped[str] = mapped_column(String(200))
    default_branch: Mapped[str] = mapped_column(String(100), default="main")

    blocks: Mapped[list["Block"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Block.id"
    )


class Block(CreatedAtMixin, Base):
    __tablename__ = "block"
    __table_args__ = (UniqueConstraint("project_id", "name"),)

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
    __table_args__ = (CheckConstraint("source_block_id <> target_block_id", name="block_link_not_self"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_block_id: Mapped[int] = mapped_column(ForeignKey("block.id", ondelete="CASCADE"))
    target_block_id: Mapped[int] = mapped_column(ForeignKey("block.id", ondelete="CASCADE"))
    label: Mapped[str | None] = mapped_column(String(100))
