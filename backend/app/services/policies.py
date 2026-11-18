from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.video import ModerationStatus, Video, VideoAccessGrant, VideoVisibility


def is_staff(user: User | None) -> bool:
    return bool(user and user.role in (UserRole.MODERATOR.value, UserRole.ADMIN.value))


def is_admin(user: User | None) -> bool:
    return bool(user and user.role == UserRole.ADMIN.value)


def has_private_grant(db: Session, video_id: str, user_id: str) -> bool:
    stmt = select(VideoAccessGrant.id).where(
        VideoAccessGrant.video_id == video_id,
        VideoAccessGrant.user_id == user_id,
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def can_view_video(db: Session, user: User | None, video: Video) -> bool:
    """Centralized authorization policy for video visibility & moderation."""
    # Hidden (moderated) videos are strictly restricted to moderators/admins and owner (for status awareness)
    if video.moderation_status == ModerationStatus.HIDDEN.value:
        if is_staff(user):
            return True
        if user and video.owner_id == user.id:
            return True
        return False

    if video.visibility in (VideoVisibility.PUBLIC.value, VideoVisibility.UNLISTED.value):
        return True

    # Private video: ONLY owner, explicitly granted users, or staff (admin/moderator)
    if video.visibility == VideoVisibility.PRIVATE.value:
        if not user:
            return False
        if video.owner_id == user.id:
            return True
        if is_staff(user):
            return True
        return has_private_grant(db, video.id, user.id)

    return False


def can_stream_video(db: Session, user: User | None, video: Video) -> bool:
    """Whether user can play media bytes. Hidden videos can be inspected by staff, not played by others."""
    if video.moderation_status == ModerationStatus.HIDDEN.value:
        return is_staff(user)
    return can_view_video(db, user, video)


def can_edit_video(user: User | None, video: Video) -> bool:
    if not user:
        return False
    return video.owner_id == user.id or is_admin(user)


def can_delete_video(user: User | None, video: Video) -> bool:
    if not user:
        return False
    return video.owner_id == user.id or is_staff(user)


def can_manage_grants(user: User | None, video: Video) -> bool:
    if not user:
        return False
    return video.owner_id == user.id or is_admin(user)
