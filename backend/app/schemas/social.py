from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.user import ChannelSummary
from app.schemas.video import VideoCard


class CommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: str | None = None


class CommentItem(BaseModel):
    id: str
    video_id: str
    parent_id: str | None
    content: str
    is_deleted: bool
    created_at: datetime
    author: ChannelSummary
    can_delete: bool = False


class PlaylistCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    visibility: Literal["public", "private"] = "public"


class PlaylistUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    visibility: Literal["public", "private"] | None = None


class PlaylistAddVideoRequest(BaseModel):
    video_id: str


class PlaylistSummary(BaseModel):
    id: str
    title: str
    description: str
    visibility: str
    videos_count: int
    cover_thumbnail_url: str | None = None
    created_at: datetime
    owner: ChannelSummary


class PlaylistDetail(PlaylistSummary):
    videos: list[VideoCard]
