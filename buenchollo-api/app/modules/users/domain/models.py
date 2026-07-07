import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.database import Base

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
