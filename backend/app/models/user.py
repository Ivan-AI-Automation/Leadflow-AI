from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.email_draft import EmailDraft
    from app.models.exported_email_batch import ExportedEmailBatch
    from app.models.lead import Lead
    from app.models.lead_activity import LeadActivity
    from app.models.lead_import import LeadImport


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    lead_imports: Mapped[list["LeadImport"]] = relationship(
        "LeadImport",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    leads: Mapped[list["Lead"]] = relationship(
        "Lead",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    email_drafts: Mapped[list["EmailDraft"]] = relationship(
        "EmailDraft",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    lead_activities: Mapped[list["LeadActivity"]] = relationship(
        "LeadActivity",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    exported_email_batches: Mapped[list["ExportedEmailBatch"]] = relationship(
        "ExportedEmailBatch",
        back_populates="user",
        cascade="all, delete-orphan",
    )
