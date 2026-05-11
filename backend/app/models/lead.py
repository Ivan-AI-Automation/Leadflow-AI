from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.email_draft import EmailDraft
    from app.models.lead_activity import LeadActivity
    from app.models.lead_import import LeadImport
    from app.models.lead_score import LeadScore
    from app.models.user import User


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_user_status", "user_id", "status"),
        Index("ix_leads_user_category", "user_id", "category"),
        Index("ix_leads_user_priority_score", "user_id", "priority_score"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    import_id: Mapped[int | None] = mapped_column(
        ForeignKey("lead_imports.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)
    source: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deal_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    budget_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    interest_level: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    timeline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="New", index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="Unscored", index=True, nullable=False)
    priority_score: Mapped[int] = mapped_column(Integer, default=0, index=True, nullable=False)
    missing_fields_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="leads")
    lead_import: Mapped["LeadImport | None"] = relationship("LeadImport", back_populates="leads")
    score: Mapped["LeadScore | None"] = relationship(
        "LeadScore",
        back_populates="lead",
        cascade="all, delete-orphan",
        uselist=False,
    )
    email_drafts: Mapped[list["EmailDraft"]] = relationship(
        "EmailDraft",
        back_populates="lead",
        cascade="all, delete-orphan",
    )
    activities: Mapped[list["LeadActivity"]] = relationship(
        "LeadActivity",
        back_populates="lead",
        cascade="all, delete-orphan",
    )
