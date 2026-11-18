from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import gen_uuid, utcnow


class ReportReason(StrEnum):
    SPAM = "spam"
    HARASSMENT = "harassment"
    COPYRIGHT = "copyright"
    INAPPROPRIATE = "inappropriate"
    MISINFORMATION = "misinformation"
    OTHER = "other"


class ReportStatus(StrEnum):
    OPEN = "open"
    RESOLVED_HIDDEN = "resolved_hidden"
    DISMISSED = "dismissed"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reporter_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=ReportStatus.OPEN.value, index=True, nullable=False
    )
    reviewed_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    video = relationship("Video", back_populates="reports")
    reporter = relationship("User", foreign_keys=[reporter_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by_id])


class ModerationLog(Base):
    __tablename__ = "moderation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    actor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True, nullable=False
    )

    actor = relationship("User")
