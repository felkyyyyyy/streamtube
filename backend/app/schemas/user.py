from datetime import datetime
from pydantic import BaseModel, Field


class ChannelSummary(BaseModel):
    id: str
    username: str
    channel_name: str
    avatar_color: str

    model_config = {"from_attributes": True}


class ChannelProfile(BaseModel):
    id: str
    username: str
    channel_name: str
    channel_description: str
    avatar_color: str
    banner_color: str
    role: str
    subscribers_count: int
    videos_count: int
    is_subscribed: bool = False
    created_at: datetime


class ChannelUpdateRequest(BaseModel):
    channel_name: str | None = Field(default=None, min_length=2, max_length=80)
    channel_description: str | None = Field(default=None, max_length=2000)
    avatar_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    banner_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class SubscriptionToggleResponse(BaseModel):
    channel_id: str
    subscribed: bool
    subscribers_count: int


class UserLookupItem(BaseModel):
    id: str
    username: str
    channel_name: str
    avatar_color: str

    model_config = {"from_attributes": True}
