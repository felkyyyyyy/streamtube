from pathlib import Path
import tempfile
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.core.rate_limit import rate_limit_dependency
from app.models.social import Subscription
from app.models.user import User, gen_uuid
from app.models.video import (
    ModerationStatus,
    Video,
    VideoAccessGrant,
    VideoReaction,
    VideoStatus,
    VideoVisibility,
)
from app.schemas.video import (
    AccessGrantCreateRequest,
    AccessGrantItem,
    ReactionRequest,
    ReactionResponse,
    VideoCard,
    VideoDetail,
    VideoListResponse,
    VideoUpdateRequest,
)
from app.services.media import (
    ALLOWED_VIDEO_EXTENSIONS,
    validate_image_magic_bytes,
    validate_video_magic_bytes,
)
from app.services.policies import (
    can_delete_video,
    can_edit_video,
    can_manage_grants,
    can_view_video,
)
from app.services.queue import transcode_queue
from app.services.video_serializer import build_video_card, build_video_detail
from app.storage.factory import get_storage

router = APIRouter(prefix="/videos", tags=["Videos"])

CHUNK_SIZE = 1024 * 1024  # 1 MiB


@router.get("", response_model=VideoListResponse, summary="List or search videos")
def list_videos(
    q: str | None = Query(default=None, max_length=120, description="Search query (title, tags, channel)"),
    category: str | None = Query(default=None, max_length=50),
    sort: Literal["newest", "popular", "oldest"] = Query(default="newest"),
    feed: Literal["all", "subscriptions", "mine", "shared"] = Query(default="all"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> VideoListResponse:
    base = select(Video).options(joinedload(Video.owner)).join(User, Video.owner_id == User.id)

    if feed == "all":
        base = base.where(
            Video.visibility == VideoVisibility.PUBLIC.value,
            Video.moderation_status == ModerationStatus.ACTIVE.value,
        )
    elif feed == "subscriptions":
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
        sub_ids = select(Subscription.channel_id).where(Subscription.subscriber_id == current_user.id)
        base = base.where(
            Video.owner_id.in_(sub_ids),
            Video.visibility == VideoVisibility.PUBLIC.value,
            Video.moderation_status == ModerationStatus.ACTIVE.value,
        )
    elif feed == "mine":
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
        base = base.where(Video.owner_id == current_user.id)
    elif feed == "shared":
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
        granted_ids = select(VideoAccessGrant.video_id).where(
            VideoAccessGrant.user_id == current_user.id
        )
        base = base.where(
            Video.id.in_(granted_ids),
            Video.visibility == VideoVisibility.PRIVATE.value,
            Video.moderation_status == ModerationStatus.ACTIVE.value,
        )

    if category and category.lower() != "all":
        base = base.where(func.lower(Video.category) == category.strip().lower())

    if q and q.strip():
        pattern = f"%{q.strip().lower()}%"
        base = base.where(
            or_(
                func.lower(Video.title).like(pattern),
                func.lower(Video.description).like(pattern),
                func.lower(Video.tags).like(pattern),
                func.lower(User.channel_name).like(pattern),
                func.lower(User.username).like(pattern),
            )
        )

    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()

    if sort == "popular":
        base = base.order_by(Video.views_count.desc(), Video.created_at.desc())
    elif sort == "oldest":
        base = base.order_by(Video.created_at.asc())
    else:
        base = base.order_by(Video.created_at.desc())

    offset = (page - 1) * page_size
    videos = db.execute(base.offset(offset).limit(page_size)).scalars().all()
    return VideoListResponse(
        items=[build_video_card(v, current_user) for v in videos],
        total=int(total or 0),
        page=page,
        page_size=page_size,
    )


@router.get("/categories", response_model=list[str], summary="List available video categories")
def list_categories() -> list[str]:
    return [
        "All",
        "Technology",
        "Programming",
        "Gaming",
        "Music",
        "Education",
        "Science",
        "Entertainment",
        "Design",
        "General",
    ]


@router.post(
    "",
    response_model=VideoDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_dependency("video_upload", limit=20, window_seconds=3600))],
    summary="Upload a new video with metadata and optional thumbnail",
)
async def upload_video(
    file: UploadFile = File(..., description="Video file (MP4, WebM, MOV, MKV)"),
    title: str = Form(..., min_length=1, max_length=150),
    description: str = Form(default="", max_length=5000),
    category: str = Form(default="General", max_length=50),
    tags: str = Form(default="", max_length=300),
    visibility: Literal["public", "unlisted", "private"] = Form(default="public"),
    allowed_usernames: str = Form(
        default="", description="Comma-separated usernames granted access if visibility=private"
    ),
    thumbnail: UploadFile | None = File(default=None, description="Optional custom thumbnail (JPG/PNG/WebP)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoDetail:
    settings = get_settings()
    storage = get_storage()

    original_ext = Path(file.filename or "video.mp4").suffix.lower()
    if original_ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension. Allowed: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}",
        )

    video_id = gen_uuid()
    storage_key = f"videos/{video_id}/source{original_ext}"
    total_bytes = 0
    header_bytes = b""

    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
        try:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                if len(header_bytes) < 32:
                    header_bytes += chunk[: 32 - len(header_bytes)]
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_VIDEO_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Video exceeds max allowed size ({settings.MAX_VIDEO_SIZE_BYTES // (1024 * 1024)} MB)",
                    )
                tmp_file.write(chunk)
        except Exception:
            tmp_file.close()
            tmp_path.unlink(missing_ok=True)
            raise

    try:
        if total_bytes < 16 or not validate_video_magic_bytes(header_bytes):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File content does not match a valid video container signature",
            )

        mime_type = file.content_type or "video/mp4"
        if not mime_type.startswith("video/"):
            mime_type = "video/mp4"
        storage.put_file(storage_key, tmp_path, content_type=mime_type)
    finally:
        tmp_path.unlink(missing_ok=True)

    thumb_key: str | None = None
    if thumbnail is not None and thumbnail.filename:
        thumb_data = await thumbnail.read(settings.MAX_THUMBNAIL_SIZE_BYTES + 1)
        if len(thumb_data) > settings.MAX_THUMBNAIL_SIZE_BYTES:
            storage.delete_prefix(f"videos/{video_id}")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Thumbnail image exceeds 10 MB limit",
            )
        if not validate_image_magic_bytes(thumb_data[:16]):
            storage.delete_prefix(f"videos/{video_id}")
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Invalid thumbnail image format (JPG, PNG, or WebP required)",
            )
        thumb_ext = ".png" if thumb_data[:4] == b"\x89PNG" else ".webp" if thumb_data[8:12] == b"WEBP" else ".jpg"
        thumb_ctype = "image/png" if thumb_ext == ".png" else "image/webp" if thumb_ext == ".webp" else "image/jpeg"
        thumb_key = f"videos/{video_id}/custom_thumb{thumb_ext}"
        storage.put_bytes(thumb_key, thumb_data, content_type=thumb_ctype)

    initial_status = VideoStatus.PROCESSING.value if settings.ENABLE_BACKGROUND_WORKER else VideoStatus.READY.value

    video = Video(
        id=video_id,
        owner_id=current_user.id,
        title=title.strip(),
        description=description.strip(),
        category=category.strip() or "General",
        tags=tags.strip(),
        visibility=visibility,
        status=initial_status,
        storage_key=storage_key,
        thumbnail_key=thumb_key,
        mime_type=mime_type,
        file_size_bytes=total_bytes,
    )
    db.add(video)
    db.flush()

    # Grant initial private access if provided
    if visibility == VideoVisibility.PRIVATE.value and allowed_usernames.strip():
        names = {n.strip().lower().lstrip("@") for n in allowed_usernames.split(",") if n.strip()}
        if names:
            users = db.execute(
                select(User).where(or_(User.username.in_(names), User.email.in_(names)))
            ).scalars().all()
            for u in users:
                if u.id != current_user.id:
                    db.add(
                        VideoAccessGrant(
                            video_id=video.id,
                            user_id=u.id,
                            granted_by_id=current_user.id,
                        )
                    )

    db.commit()
    enqueued = transcode_queue.enqueue(video.id)
    if not enqueued and video.status == VideoStatus.PROCESSING.value:
        video.status = VideoStatus.READY.value
        db.commit()

    video = db.execute(
        select(Video).options(joinedload(Video.owner)).where(Video.id == video.id)
    ).scalar_one()
    return build_video_detail(db, video, current_user)


@router.get("/{video_id}", response_model=VideoDetail, summary="Get video details and playback URLs")
def get_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> VideoDetail:
    video = db.execute(
        select(Video).options(joinedload(Video.owner)).where(Video.id == video_id)
    ).scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if not can_view_video(db, current_user, video):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this video",
        )
    return build_video_detail(db, video, current_user)


@router.get("/{video_id}/recommendations", response_model=list[VideoCard], summary="Get recommended videos")
def get_recommendations(
    video_id: str,
    limit: int = Query(default=12, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[VideoCard]:
    stmt = (
        select(Video)
        .options(joinedload(Video.owner))
        .where(
            Video.id != video_id,
            Video.visibility == VideoVisibility.PUBLIC.value,
            Video.moderation_status == ModerationStatus.ACTIVE.value,
        )
        .order_by(Video.views_count.desc(), Video.created_at.desc())
        .limit(limit)
    )
    videos = db.execute(stmt).scalars().all()
    return [build_video_card(v, current_user) for v in videos]


@router.patch("/{video_id}", response_model=VideoDetail, summary="Update video metadata or visibility")
def update_video(
    video_id: str,
    payload: VideoUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoDetail:
    video = db.execute(
        select(Video).options(joinedload(Video.owner)).where(Video.id == video_id)
    ).scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if not can_edit_video(current_user, video):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this video")

    if payload.title is not None:
        video.title = payload.title.strip()
    if payload.description is not None:
        video.description = payload.description.strip()
    if payload.category is not None:
        video.category = payload.category.strip()
    if payload.tags is not None:
        video.tags = payload.tags.strip()
    if payload.visibility is not None:
        video.visibility = payload.visibility

    db.commit()
    db.refresh(video)
    return build_video_detail(db, video, current_user)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a video and its media assets")
def delete_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if not can_delete_video(current_user, video):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this video")

    get_storage().delete_prefix(f"videos/{video.id}")
    db.delete(video)
    db.commit()


@router.post("/{video_id}/view", summary="Record a video view")
def record_view(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if not can_view_video(db, current_user, video):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    db.execute(
        update(Video).where(Video.id == video_id).values(views_count=Video.views_count + 1)
    )
    db.commit()
    db.refresh(video)
    return {"video_id": video.id, "views_count": video.views_count}


@router.post("/{video_id}/reaction", response_model=ReactionResponse, summary="Like, dislike, or clear reaction")
def react_to_video(
    video_id: str,
    payload: ReactionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReactionResponse:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if not can_view_video(db, current_user, video):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    existing = db.execute(
        select(VideoReaction).where(
            VideoReaction.video_id == video_id,
            VideoReaction.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if payload.value == 0:
        if existing:
            db.delete(existing)
        new_val = 0
    elif existing:
        if existing.value == payload.value:
            db.delete(existing)
            new_val = 0
        else:
            existing.value = payload.value
            new_val = payload.value
    else:
        db.add(VideoReaction(video_id=video_id, user_id=current_user.id, value=payload.value))
        new_val = payload.value

    db.flush()

    likes = db.execute(
        select(func.count(VideoReaction.id)).where(
            VideoReaction.video_id == video_id, VideoReaction.value == 1
        )
    ).scalar_one()
    dislikes = db.execute(
        select(func.count(VideoReaction.id)).where(
            VideoReaction.video_id == video_id, VideoReaction.value == -1
        )
    ).scalar_one()

    video.likes_count = int(likes or 0)
    video.dislikes_count = int(dislikes or 0)
    db.commit()

    return ReactionResponse(
        video_id=video.id,
        user_reaction=new_val,
        likes_count=video.likes_count,
        dislikes_count=video.dislikes_count,
    )


@router.get(
    "/{video_id}/access",
    response_model=list[AccessGrantItem],
    summary="List users granted access to a private video",
)
def list_access_grants(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AccessGrantItem]:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if not can_manage_grants(current_user, video):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner or admin can view access grants")

    grants = db.execute(
        select(VideoAccessGrant)
        .options(joinedload(VideoAccessGrant.user))
        .where(VideoAccessGrant.video_id == video_id)
        .order_by(VideoAccessGrant.created_at.desc())
    ).scalars().all()
    return [
        AccessGrantItem(
            id=g.id,
            user_id=g.user_id,
            username=g.user.username,
            channel_name=g.user.channel_name,
            avatar_color=g.user.avatar_color,
            created_at=g.created_at,
        )
        for g in grants
    ]


@router.post(
    "/{video_id}/access",
    response_model=AccessGrantItem,
    status_code=status.HTTP_201_CREATED,
    summary="Grant a user access to a private video",
)
def grant_video_access(
    video_id: str,
    payload: AccessGrantCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccessGrantItem:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if not can_manage_grants(current_user, video):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner or admin can grant access")

    ident = payload.username_or_email.strip().lower().lstrip("@")
    target = db.execute(
        select(User).where(or_(User.username == ident, User.email == ident))
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")
    if target.id == video.owner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner already has full access")

    existing = db.execute(
        select(VideoAccessGrant).where(
            VideoAccessGrant.video_id == video_id,
            VideoAccessGrant.user_id == target.id,
        )
    ).scalar_one_or_none()
    if existing:
        return AccessGrantItem(
            id=existing.id,
            user_id=target.id,
            username=target.username,
            channel_name=target.channel_name,
            avatar_color=target.avatar_color,
            created_at=existing.created_at,
        )

    grant = VideoAccessGrant(
        video_id=video_id,
        user_id=target.id,
        granted_by_id=current_user.id,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return AccessGrantItem(
        id=grant.id,
        user_id=target.id,
        username=target.username,
        channel_name=target.channel_name,
        avatar_color=target.avatar_color,
        created_at=grant.created_at,
    )


@router.delete(
    "/{video_id}/access/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a user's access to a private video",
)
def revoke_video_access(
    video_id: str,
    target_user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if not can_manage_grants(current_user, video):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    grant = db.execute(
        select(VideoAccessGrant).where(
            VideoAccessGrant.video_id == video_id,
            VideoAccessGrant.user_id == target_user_id,
        )
    ).scalar_one_or_none()
    if grant:
        db.delete(grant)
        db.commit()
