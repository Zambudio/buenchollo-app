import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

# Registrar tablas referenciadas por FK antes de resolver relaciones.
import app.modules.users.domain.models  # noqa: F401
import app.modules.deals.domain.models  # noqa: F401
import app.modules.categories.domain.models  # noqa: F401
import app.modules.stores.domain.models  # noqa: F401

SubmissionStatus = Literal["pending", "approved", "rejected", "withdrawn"]
PENDING: SubmissionStatus = "pending"
APPROVED: SubmissionStatus = "approved"
REJECTED: SubmissionStatus = "rejected"
WITHDRAWN: SubmissionStatus = "withdrawn"

_JSON = JSON().with_variant(JSONB(), "postgresql")


class DealSubmission(Base):
    __tablename__ = "deal_submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','rejected','withdrawn')",
            name="ck_deal_submissions_status",
        ),
        CheckConstraint(
            "previous_price IS NULL OR previous_price > current_price",
            name="ck_deal_submissions_previous_price",
        ),
        Index("ix_deal_submissions_status_created", "status", "created_at"),
        Index("ix_deal_submissions_user_created", "user_id", "created_at"),
        Index(
            "uq_deal_submissions_pending_asin",
            "asin",
            unique=True,
            postgresql_where=text("status = 'pending' AND asin IS NOT NULL"),
        ),
        Index(
            "uq_deal_submissions_pending_canonical",
            "canonical_url",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=PENDING)

    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    affiliate_url: Mapped[str] = mapped_column(Text, nullable=False)
    asin: Mapped[str | None] = mapped_column(String(16), nullable=True)

    store_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True
    )
    store_name: Mapped[str | None] = mapped_column(String(80), nullable=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    coupon_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    shipping_info: Mapped[str | None] = mapped_column(String(120), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    category_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    subcategory_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    images: Mapped[list[str]] = mapped_column(_JSON, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    warnings: Mapped[list[str]] = mapped_column(_JSON, nullable=False, default=list, server_default=text("'[]'::jsonb"))

    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deal_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship(
        "Profile",
        primaryjoin="DealSubmission.user_id == Profile.user_id",
        foreign_keys="DealSubmission.user_id",
        viewonly=True,
        lazy="raise",
    )
    category = relationship("Category", foreign_keys=[category_id], lazy="raise")
    subcategory = relationship("Category", foreign_keys=[subcategory_id], lazy="raise")
    store = relationship("Store", lazy="raise")
