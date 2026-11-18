from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_moderator
from app.core.rate_limit import rate_limit_dependency
from app.models.moderation import ModerationLog, Report, ReportStatus
from app.models.user import User
from app.models.video import ModerationStatus, Video
from app.schemas.moderation import (
    AdminUserItem,
    ModerationDecisionRequest,
    ModerationLogItem,
    ReportCreateRequest,
    ReportItem,
    RoleUpdateRequest,
    VideoModerationRequest,
)
from app.schemas.user import ChannelSummary
from app.schemas.video import VideoCard
from app.services.policies import can_view_video
from app.services.video_serializer import build_video_card

router = APIRouter(tags=["Moderation & Administration"])


def _serialize_report(r: Report) -> ReportItem:
    return ReportItem(
        id=r.id,
        video_id=r.video_id,
        video_title=r.video.title,
        video_moderation_status=r.video.moderation_status,
        video_owner_username=r.video.owner.username,
        reporter=ChannelSummary.model_validate(r.reporter),
        reason=r.reason,
        details=r.details,
        status=r.status,
        resolution_note=r.resolution_note,
        created_at=r.created_at,
        resolved_at=r.resolved_at,
    )


@router.post(
    "/reports",
    response_model=ReportItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_dependency("report_create", limit=20, window_seconds=3600))],
    summary="Report a video for moderation review",
)
def create_report(
    payload: ReportCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportItem:
    video = db.execute(
        select(Video).options(joinedload(Video.owner)).where(Video.id == payload.video_id)
    ).scalar_one_or_none()
    if not video or not can_view_video(db, current_user, video):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    existing = db.execute(
        select(Report).where(
            Report.video_id == payload.video_id,
            Report.reporter_id == current_user.id,
            Report.status == ReportStatus.OPEN.value,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an open report for this video",
        )

    report = Report(
        video_id=video.id,
        reporter_id=current_user.id,
        reason=payload.reason,
        details=payload.details.strip(),
        status=ReportStatus.OPEN.value,
    )
    db.add(report)
    db.commit()

    report = db.execute(
        select(Report)
        .options(
            joinedload(Report.reporter),
            joinedload(Report.video).joinedload(Video.owner),
        )
        .where(Report.id == report.id)
    ).scalar_one()
    return _serialize_report(report)


@router.get(
    "/moderation/reports",
    response_model=list[ReportItem],
    summary="List moderation reports queue (moderator/admin)",
)
def list_reports(
    status_filter: Literal["open", "resolved_hidden", "dismissed", "all"] = Query(default="open", alias="status"),
    db: Session = Depends(get_db),
    _staff: User = Depends(require_moderator),
) -> list[ReportItem]:
    stmt = (
        select(Report)
        .options(
            joinedload(Report.reporter),
            joinedload(Report.video).joinedload(Video.owner),
        )
        .order_by(Report.created_at.desc())
    )
    if status_filter != "all":
        stmt = stmt.where(Report.status == status_filter)
    reports = db.execute(stmt).scalars().all()
    return [_serialize_report(r) for r in reports]


@router.post(
    "/moderation/reports/{report_id}/resolve",
    response_model=ReportItem,
    summary="Resolve a report by hiding the video or dismissing (moderator/admin)",
)
def resolve_report(
    report_id: str,
    payload: ModerationDecisionRequest,
    db: Session = Depends(get_db),
    staff: User = Depends(require_moderator),
) -> ReportItem:
    report = db.execute(
        select(Report)
        .options(
            joinedload(Report.reporter),
            joinedload(Report.video).joinedload(Video.owner),
        )
        .where(Report.id == report_id)
    ).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    now = datetime.now(timezone.utc)
    note = payload.note.strip() or (
        f"Hidden due to {report.reason}" if payload.action == "hide_video" else "Dismissed after review"
    )

    if payload.action == "hide_video":
        video = report.video
        video.moderation_status = ModerationStatus.HIDDEN.value
        video.moderation_reason = note

        # Resolve all open reports on this video
        open_reports = db.execute(
            select(Report).where(
                Report.video_id == video.id,
                Report.status == ReportStatus.OPEN.value,
            )
        ).scalars().all()
        for r in open_reports:
            r.status = ReportStatus.RESOLVED_HIDDEN.value
            r.reviewed_by_id = staff.id
            r.resolution_note = note
            r.resolved_at = now

        report.status = ReportStatus.RESOLVED_HIDDEN.value
        report.reviewed_by_id = staff.id
        report.resolution_note = note
        report.resolved_at = now

        db.add(
            ModerationLog(
                actor_id=staff.id,
                action="hide_video",
                target_type="video",
                target_id=video.id,
                reason=note,
            )
        )
    else:
        report.status = ReportStatus.DISMISSED.value
        report.reviewed_by_id = staff.id
        report.resolution_note = note
        report.resolved_at = now
        db.add(
            ModerationLog(
                actor_id=staff.id,
                action="dismiss_report",
                target_type="report",
                target_id=report.id,
                reason=note,
            )
        )

    db.commit()
    db.refresh(report)
    return _serialize_report(report)


@router.post(
    "/moderation/videos/{video_id}/hide",
    summary="Hide a video directly (moderator/admin)",
)
def hide_video(
    video_id: str,
    payload: VideoModerationRequest,
    db: Session = Depends(get_db),
    staff: User = Depends(require_moderator),
) -> dict:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    reason = payload.reason.strip() or "Hidden by moderator"
    video.moderation_status = ModerationStatus.HIDDEN.value
    video.moderation_reason = reason
    db.add(
        ModerationLog(
            actor_id=staff.id,
            action="hide_video",
            target_type="video",
            target_id=video.id,
            reason=reason,
        )
    )
    db.commit()
    return {"video_id": video.id, "moderation_status": video.moderation_status, "reason": reason}


@router.post(
    "/moderation/videos/{video_id}/unhide",
    summary="Restore a hidden video (moderator/admin)",
)
def unhide_video(
    video_id: str,
    payload: VideoModerationRequest,
    db: Session = Depends(get_db),
    staff: User = Depends(require_moderator),
) -> dict:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    reason = payload.reason.strip() or "Restored by moderator"
    video.moderation_status = ModerationStatus.ACTIVE.value
    video.moderation_reason = None
    db.add(
        ModerationLog(
            actor_id=staff.id,
            action="unhide_video",
            target_type="video",
            target_id=video.id,
            reason=reason,
        )
    )
    db.commit()
    return {"video_id": video.id, "moderation_status": video.moderation_status}


@router.get(
    "/moderation/videos/hidden",
    response_model=list[VideoCard],
    summary="List currently hidden videos (moderator/admin)",
)
def list_hidden_videos(
    db: Session = Depends(get_db),
    staff: User = Depends(require_moderator),
) -> list[VideoCard]:
    videos = db.execute(
        select(Video)
        .options(joinedload(Video.owner))
        .where(Video.moderation_status == ModerationStatus.HIDDEN.value)
        .order_by(Video.updated_at.desc())
    ).scalars().all()
    return [build_video_card(v, staff) for v in videos]


@router.get(
    "/moderation/logs",
    response_model=list[ModerationLogItem],
    summary="List recent moderation audit log entries (moderator/admin)",
)
def list_moderation_logs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _staff: User = Depends(require_moderator),
) -> list[ModerationLogItem]:
    logs = db.execute(
        select(ModerationLog)
        .options(joinedload(ModerationLog.actor))
        .order_by(ModerationLog.created_at.desc())
        .limit(limit)
    ).scalars().all()
    return [
        ModerationLogItem(
            id=item.id,
            actor_username=item.actor.username if item.actor else None,
            action=item.action,
            target_type=item.target_type,
            target_id=item.target_id,
            reason=item.reason,
            created_at=item.created_at,
        )
        for item in logs
    ]


@router.get("/admin/users", response_model=list[AdminUserItem], summary="List all users (admin only)")
def list_users_admin(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[AdminUserItem]:
    users = db.execute(select(User).order_by(User.created_at.desc())).scalars().all()
    counts = dict(
        db.execute(select(Video.owner_id, func.count(Video.id)).group_by(Video.owner_id)).all()
    )
    return [
        AdminUserItem(
            id=u.id,
            username=u.username,
            email=u.email,
            channel_name=u.channel_name,
            role=u.role,
            is_active=u.is_active,
            videos_count=int(counts.get(u.id, 0)),
            created_at=u.created_at,
        )
        for u in users
    ]


@router.patch(
    "/admin/users/{user_id}/role",
    response_model=AdminUserItem,
    summary="Update a user's role (admin only)",
)
def update_user_role(
    user_id: str,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AdminUserItem:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot change their own role",
        )
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    old_role = user.role
    user.role = payload.role
    db.add(
        ModerationLog(
            actor_id=admin.id,
            action="change_user_role",
            target_type="user",
            target_id=user.id,
            reason=f"Role changed from {old_role} to {payload.role}",
        )
    )
    db.commit()
    db.refresh(user)
    vcount = db.execute(select(func.count(Video.id)).where(Video.owner_id == user.id)).scalar_one()
    return AdminUserItem(
        id=user.id,
        username=user.username,
        email=user.email,
        channel_name=user.channel_name,
        role=user.role,
        is_active=user.is_active,
        videos_count=int(vcount or 0),
        created_at=user.created_at,
    )


@router.patch(
    "/admin/users/{user_id}/active",
    response_model=AdminUserItem,
    summary="Activate or suspend a user account (admin only)",
)
def toggle_user_active(
    user_id: str,
    active: bool = Query(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AdminUserItem:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot suspend themselves",
        )
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = active
    db.add(
        ModerationLog(
            actor_id=admin.id,
            action="toggle_user_active",
            target_type="user",
            target_id=user.id,
            reason=f"Account set to {'active' if active else 'suspended'}",
        )
    )
    db.commit()
    db.refresh(user)
    vcount = db.execute(select(func.count(Video.id)).where(Video.owner_id == user.id)).scalar_one()
    return AdminUserItem(
        id=user.id,
        username=user.username,
        email=user.email,
        channel_name=user.channel_name,
        role=user.role,
        is_active=user.is_active,
        videos_count=int(vcount or 0),
        created_at=user.created_at,
    )
