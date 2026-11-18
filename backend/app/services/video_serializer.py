from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_media_playback_token
from app.models.social import Comment, Subscription
from app.models.user import User
from app.models.video import Video, VideoReaction, VideoVisibility
from app.schemas.user import ChannelSummary
from app.schemas.video import VideoCard, VideoDetail
from app.services.policies import can_edit_video, can_stream_video


def _parse_tags(raw: str) -> list[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def build_video_card(video: Video, current_user: User | None) -> VideoCard:
    settings = get_settings()
    prefix = settings.API_V1_PREFIX
    thumb_url: str | None = None
    if video.thumbnail_key:
        if video.visibility == VideoVisibility.PRIVATE.value or video.moderation_status == "hidden":
            token = create_media_playback_token(video.id, current_user.id if current_user else None)
            thumb_url = f"{prefix}/media/{video.id}/thumbnail?token={token}"
        else:
            thumb_url = f"{prefix}/media/{video.id}/thumbnail"

    return VideoCard(
        id=video.id,
        title=video.title,
        description=video.description,
        category=video.category,
        tags=_parse_tags(video.tags),
        visibility=video.visibility,
        status=video.status,
        moderation_status=video.moderation_status,
        duration_seconds=video.duration_seconds,
        views_count=video.views_count,
        likes_count=video.likes_count,
        dislikes_count=video.dislikes_count,
        thumbnail_url=thumb_url,
        created_at=video.created_at,
        owner=ChannelSummary.model_validate(video.owner),
    )


def build_video_detail(db: Session, video: Video, current_user: User | None) -> VideoDetail:
    settings = get_settings()
    prefix = settings.API_V1_PREFIX
    card = build_video_card(video, current_user)

    user_reaction = 0
    is_subscribed = False
    if current_user:
        rx = db.execute(
            select(VideoReaction.value).where(
                VideoReaction.video_id == video.id,
                VideoReaction.user_id == current_user.id,
            )
        ).scalar_one_or_none()
        user_reaction = int(rx) if rx is not None else 0

        sub = db.execute(
            select(Subscription.id).where(
                Subscription.subscriber_id == current_user.id,
                Subscription.channel_id == video.owner_id,
            )
        ).scalar_one_or_none()
        is_subscribed = sub is not None

    subs_count = db.execute(
        select(func.count(Subscription.id)).where(Subscription.channel_id == video.owner_id)
    ).scalar_one()

    comments_count = db.execute(
        select(func.count(Comment.id)).where(
            Comment.video_id == video.id,
            Comment.is_deleted.is_(False),
        )
    ).scalar_one()

    playback_token: str | None = None
    hls_url: str | None = None
    stream_url: str | None = None
    if can_stream_video(db, current_user, video):
        playback_token = create_media_playback_token(
            video.id, current_user.id if current_user else None
        )
        stream_url = f"{prefix}/media/{video.id}/stream?token={playback_token}"
        if video.hls_master_key:
            hls_url = f"{prefix}/media/{video.id}/hls/master.m3u8?token={playback_token}"

    return VideoDetail(
        **card.model_dump(),
        moderation_reason=video.moderation_reason,
        width=video.width,
        height=video.height,
        file_size_bytes=video.file_size_bytes,
        mime_type=video.mime_type,
        hls_url=hls_url,
        stream_url=stream_url,
        playback_token=playback_token,
        user_reaction=user_reaction,
        owner_subscribers_count=int(subs_count or 0),
        is_subscribed=is_subscribed,
        comments_count=int(comments_count or 0),
        can_edit=can_edit_video(current_user, video),
    )
