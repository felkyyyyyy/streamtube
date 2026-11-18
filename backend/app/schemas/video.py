from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.user import ChannelSummary


class VideoCard(BaseModel):
    id: str
    title: str
    description: str
    category: str
    tags: list[str]
    visibility: str
    status: str
    moderation_status: str
    duration_seconds: int
    views_count: int
    likes_count: int
    dislikes_count: int
    thumbnail_url: str | None
    created_at: datetime
    owner: ChannelSummary


class VideoDetail(VideoCard):
    moderation_reason: str | None = None
    width: int
    height: int
    file_size_bytes: int
    mime_type: str
    hls_url: str | None = None
    stream_url: str | None = None
    playback_token: str | None = None
    user_reaction: int = 0  # 1 like, -1 dislike, 0 none
    owner_subscribers_count: int = 0
    is_subscribed: bool = False
    comments_count: int = 0
    can_edit: bool = False


class VideoUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, max_length=50)
    tags: str | None = Field(default=None, max_length=300)
    visibility: Literal["public", "unlisted", "private"] | None = None


class ReactionRequest(BaseModel):
    value: Literal[1, -1, 0]


class ReactionResponse(BaseModel):
    video_id: str
    user_reaction: int
    likes_count: int
    dislikes_count: int


class AccessGrantCreateRequest(BaseModel):
    username_or_email: str = Field(..., min_length=2, max_length=255)


class AccessGrantItem(BaseModel):
    id: str
    user_id: str
    username: str
    channel_name: str
    avatar_color: str
    created_at: datetime


class VideoListResponse(BaseModel):
    items: list[VideoCard]
    total: int
    page: int
    page_size: int
