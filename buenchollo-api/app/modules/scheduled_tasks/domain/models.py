import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

import app.modules.users.domain.models  # noqa: F401


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    frequency_preset: Mapped[str] = mapped_column(String(16), default="weekly", nullable=False)
    run_hour: Mapped[int] = mapped_column(SmallInteger, default=4, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )


class ScheduledTaskRun(Base):
    __tablename__ = "scheduled_task_runs"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(
        ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), type_=Uuid(as_uuid=False), nullable=False
    )
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_checked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_affected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    triggered_by: Mapped[str | None] = mapped_column(
        ForeignKey("profiles.user_id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    items: Mapped[list["ScheduledTaskRunItem"]] = relationship(
        "ScheduledTaskRunItem", cascade="all, delete-orphan", back_populates="run"
    )


class ScheduledTaskRunItem(Base):
    __tablename__ = "scheduled_task_run_items"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(
        ForeignKey("scheduled_task_runs.id", ondelete="CASCADE"), type_=Uuid(as_uuid=False), nullable=False
    )
    deal_id_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    store_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    store_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    subcategory_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    affiliate_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    old_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    new_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restored_deal_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )

    run: Mapped["ScheduledTaskRun"] = relationship("ScheduledTaskRun", back_populates="items")
