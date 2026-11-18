from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.core.rate_limit import rate_limit_dependency
from app.models.moderation import ModerationLog
from app.models.social import Comment
from app.models.user import User
from app.models.video import Video
from app.schemas.social import CommentCreateRequest, CommentItem
from app.schemas.user import ChannelSummary
from app.services.policies import can_view_video, is_staff

router = APIRouter(tags=["Comments"])


def _serialize_comment(comment: Comment, current_user: User | None, video_owner_id: str) -> CommentItem:
    can_del = bool(
        current_user
        and (
            comment.author_id == current_user.id
            or video_owner_id == current_user.id
            or is_staff(current_user)
        )
    )
    return CommentItem(
        id=comment.id,
        video_id=comment.video_id,
        parent_id=comment.parent_id,
        content="[deleted]" if comment.is_deleted else comment.content,
        is_deleted=comment.is_deleted,
        created_at=comment.created_at,
        author=ChannelSummary.model_validate(comment.author),
        can_delete=can_del,
    )


@router.get("/videos/{video_id}/comments", response_model=list[CommentItem], summary="List video comments")
def list_comments(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[CommentItem]:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if not can_view_video(db, current_user, video):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    comments = db.execute(
        select(Comment)
        .options(joinedload(Comment.author))
        .where(Comment.video_id == video_id, Comment.is_deleted.is_(False))
        .order_by(Comment.created_at.desc())
    ).scalars().all()
    return [_serialize_comment(c, current_user, video.owner_id) for c in comments]


@router.post(
    "/videos/{video_id}/comments",
    response_model=CommentItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_dependency("comment_create", limit=40, window_seconds=300))],
    summary="Post a comment or reply on a video",
)
def create_comment(
    video_id: str,
    payload: CommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentItem:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if not can_view_video(db, current_user, video):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if payload.parent_id:
        parent = db.get(Comment, payload.parent_id)
        if not parent or parent.video_id != video_id or parent.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found")

    comment = Comment(
        video_id=video_id,
        author_id=current_user.id,
        parent_id=payload.parent_id,
        content=payload.content.strip(),
    )
    db.add(comment)
    db.commit()
    comment = db.execute(
        select(Comment).options(joinedload(Comment.author)).where(Comment.id == comment.id)
    ).scalar_one()
    return _serialize_comment(comment, current_user, video.owner_id)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a comment")
def delete_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    comment = db.get(Comment, comment_id)
    if not comment or comment.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    video = db.get(Video, comment.video_id)
    is_owner_or_video_owner = comment.author_id == current_user.id or (
        video and video.owner_id == current_user.id
    )
    if not (is_owner_or_video_owner or is_staff(current_user)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete comment")

    comment.is_deleted = True
    if is_staff(current_user) and not is_owner_or_video_owner:
        db.add(
            ModerationLog(
                actor_id=current_user.id,
                action="delete_comment",
                target_type="comment",
                target_id=comment.id,
                reason="Removed by moderator",
            )
        )
    db.commit()
