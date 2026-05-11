from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lead import Lead
    from app.models.user import User


class EmailDraft(TimestampMixin, Base):
    __tablename__ = "email_drafts"
    __table_args__ = (Index("ix_email_drafts_user_status", "user_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str] = mapped_column(String(50), default="Professional", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Draft", index=True, nullable=False)
    ai_provider: Mapped[str] = mapped_column(String(50), default="mock", nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="email_drafts")
    lead: Mapped["Lead"] = relationship("Lead", back_populates="email_drafts")
