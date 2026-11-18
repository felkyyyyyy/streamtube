from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.user import ChannelSummary


class ReportCreateRequest(BaseModel):
    video_id: str
    reason: Literal[
        "spam", "harassment", "copyright", "inappropriate", "misinformation", "other"
    ]
    details: str = Field(default="", max_length=2000)


class ReportItem(BaseModel):
    id: str
    video_id: str
    video_title: str
    video_moderation_status: str
    video_owner_username: str
    reporter: ChannelSummary
    reason: str
    details: str
    status: str
    resolution_note: str | None
    created_at: datetime
    resolved_at: datetime | None


class ModerationDecisionRequest(BaseModel):
    action: Literal["hide_video", "dismiss"]
    note: str = Field(default="", max_length=1000)


class VideoModerationRequest(BaseModel):
    reason: str = Field(default="Policy violation", max_length=1000)


class RoleUpdateRequest(BaseModel):
    role: Literal["user", "moderator", "admin"]


class ModerationLogItem(BaseModel):
    id: str
    actor_username: str | None
    action: str
    target_type: str
    target_id: str
    reason: str
    created_at: datetime


class AdminUserItem(BaseModel):
    id: str
    username: str
    email: str
    channel_name: str
    role: str
    is_active: bool
    videos_count: int
    created_at: datetime
