from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.lead import Lead
    from app.models.user import User


class LeadImport(Base):
    __tablename__ = "lead_imports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    rows_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    columns_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    columns_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    dtypes_json: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="lead_imports")
    leads: Mapped[list["Lead"]] = relationship(
        "Lead",
        back_populates="lead_import",
        cascade="all, delete-orphan",
    )
