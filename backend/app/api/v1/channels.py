from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.models.social import Subscription
from app.models.user import User
from app.models.video import ModerationStatus, Video, VideoVisibility
from app.schemas.user import (
    ChannelProfile,
    ChannelSummary,
    ChannelUpdateRequest,
    SubscriptionToggleResponse,
    UserLookupItem,
)
from app.schemas.video import VideoCard
from app.services.policies import is_staff
from app.services.video_serializer import build_video_card

router = APIRouter(tags=["Channels & Subscriptions"])


def _find_channel(db: Session, identifier: str) -> User:
    clean = identifier.lstrip("@").strip()
    user = db.execute(
        select(User).where(or_(User.id == clean, User.username == clean.lower()))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return user


@router.get("/channels/{identifier}", response_model=ChannelProfile, summary="Get channel profile")
def get_channel(
    identifier: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> ChannelProfile:
    channel = _find_channel(db, identifier)

    subs_count = db.execute(
        select(func.count(Subscription.id)).where(Subscription.channel_id == channel.id)
    ).scalar_one()

    videos_query = select(func.count(Video.id)).where(Video.owner_id == channel.id)
    if not (current_user and (current_user.id == channel.id or is_staff(current_user))):
        videos_query = videos_query.where(
            Video.visibility == VideoVisibility.PUBLIC.value,
            Video.moderation_status == ModerationStatus.ACTIVE.value,
        )
    videos_count = db.execute(videos_query).scalar_one()

    is_subscribed = False
    if current_user and current_user.id != channel.id:
        is_subscribed = (
            db.execute(
                select(Subscription.id).where(
                    Subscription.subscriber_id == current_user.id,
                    Subscription.channel_id == channel.id,
                )
            ).scalar_one_or_none()
            is not None
        )

    return ChannelProfile(
        id=channel.id,
        username=channel.username,
        channel_name=channel.channel_name,
        channel_description=channel.channel_description,
        avatar_color=channel.avatar_color,
        banner_color=channel.banner_color,
        role=channel.role,
        subscribers_count=int(subs_count or 0),
        videos_count=int(videos_count or 0),
        is_subscribed=is_subscribed,
        created_at=channel.created_at,
    )


@router.get(
    "/channels/{identifier}/videos",
    response_model=list[VideoCard],
    summary="List videos uploaded by channel",
)
def get_channel_videos(
    identifier: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[VideoCard]:
    channel = _find_channel(db, identifier)
    stmt = (
        select(Video)
        .options(joinedload(Video.owner))
        .where(Video.owner_id == channel.id)
        .order_by(Video.created_at.desc())
    )
    if not (current_user and (current_user.id == channel.id or is_staff(current_user))):
        stmt = stmt.where(
            Video.visibility == VideoVisibility.PUBLIC.value,
            Video.moderation_status == ModerationStatus.ACTIVE.value,
        )
    videos = db.execute(stmt).scalars().all()
    return [build_video_card(v, current_user) for v in videos]


@router.patch("/channels/me", response_model=ChannelProfile, summary="Update current user's channel profile")
def update_my_channel(
    payload: ChannelUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChannelProfile:
    if payload.channel_name is not None:
        current_user.channel_name = payload.channel_name.strip()
    if payload.channel_description is not None:
        current_user.channel_description = payload.channel_description.strip()
    if payload.avatar_color is not None:
        current_user.avatar_color = payload.avatar_color
    if payload.banner_color is not None:
        current_user.banner_color = payload.banner_color
    db.commit()
    db.refresh(current_user)
    return get_channel(current_user.id, db=db, current_user=current_user)


@router.post(
    "/channels/{channel_id}/subscribe",
    response_model=SubscriptionToggleResponse,
    summary="Toggle subscription to a channel",
)
def toggle_subscription(
    channel_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionToggleResponse:
    channel = _find_channel(db, channel_id)
    if channel.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot subscribe to your own channel",
        )

    existing = db.execute(
        select(Subscription).where(
            Subscription.subscriber_id == current_user.id,
            Subscription.channel_id == channel.id,
        )
    ).scalar_one_or_none()

    if existing:
        db.delete(existing)
        subscribed = False
    else:
        db.add(Subscription(subscriber_id=current_user.id, channel_id=channel.id))
        subscribed = True
    db.commit()

    subs_count = db.execute(
        select(func.count(Subscription.id)).where(Subscription.channel_id == channel.id)
    ).scalar_one()
    return SubscriptionToggleResponse(
        channel_id=channel.id,
        subscribed=subscribed,
        subscribers_count=int(subs_count or 0),
    )


@router.get(
    "/subscriptions",
    response_model=list[ChannelSummary],
    summary="List channels the current user is subscribed to",
)
def list_my_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChannelSummary]:
    stmt = (
        select(User)
        .join(Subscription, Subscription.channel_id == User.id)
        .where(Subscription.subscriber_id == current_user.id)
        .order_by(Subscription.created_at.desc())
    )
    channels = db.execute(stmt).scalars().all()
    return [ChannelSummary.model_validate(c) for c in channels]


@router.get(
    "/users/search",
    response_model=list[UserLookupItem],
    summary="Search users by username for granting private video access",
)
def search_users(
    q: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[UserLookupItem]:
    pattern = f"%{q.strip().lower()}%"
    stmt = (
        select(User)
        .where(
            User.is_active.is_(True),
            or_(
                func.lower(User.username).like(pattern),
                func.lower(User.channel_name).like(pattern),
            ),
        )
        .limit(10)
    )
    users = db.execute(stmt).scalars().all()
    return [UserLookupItem.model_validate(u) for u in users]
