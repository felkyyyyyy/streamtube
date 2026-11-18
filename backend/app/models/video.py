from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import gen_uuid, utcnow


class VideoVisibility(StrEnum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


class VideoStatus(StrEnum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ModerationStatus(StrEnum):
    ACTIVE = "active"
    HIDDEN = "hidden"


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        Index("ix_videos_feed", "visibility", "moderation_status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    title: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="General", index=True, nullable=False)
    tags: Mapped[str] = mapped_column(String(300), default="", nullable=False)

    visibility: Mapped[str] = mapped_column(
        String(20), default=VideoVisibility.PUBLIC.value, index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=VideoStatus.PROCESSING.value, index=True, nullable=False
    )
    moderation_status: Mapped[str] = mapped_column(
        String(20), default=ModerationStatus.ACTIVE.value, index=True, nullable=False
    )
    moderation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    hls_master_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    thumbnail_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), default="video/mp4", nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    views_count: Mapped[int] = mapped_column(Integer, default=0, index=True, nullable=False)
    likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dislikes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    owner = relationship("User", back_populates="videos")
    access_grants = relationship(
        "VideoAccessGrant", back_populates="video", cascade="all, delete-orphan"
    )
    reactions = relationship("VideoReaction", back_populates="video", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="video", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="video", cascade="all, delete-orphan")


class VideoAccessGrant(Base):
    __tablename__ = "video_access_grants"
    __table_args__ = (
        UniqueConstraint("video_id", "user_id", name="uq_video_access_grant"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    granted_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    video = relationship("Video", back_populates="access_grants")
    user = relationship("User", foreign_keys=[user_id])


class VideoReaction(Base):
    __tablename__ = "video_reactions"
    __table_args__ = (
        UniqueConstraint("video_id", "user_id", name="uq_video_reaction"),
        CheckConstraint("value IN (1, -1)", name="ck_video_reaction_value"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    value: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1 = like, -1 = dislike
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    video = relationship("Video", back_populates="reactions")
