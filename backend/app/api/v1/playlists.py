from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.models.social import Playlist, PlaylistItem
from app.models.user import User
from app.models.video import Video
from app.schemas.social import (
    PlaylistAddVideoRequest,
    PlaylistCreateRequest,
    PlaylistDetail,
    PlaylistSummary,
    PlaylistUpdateRequest,
)
from app.schemas.user import ChannelSummary
from app.services.policies import can_view_video, is_staff
from app.services.video_serializer import build_video_card

router = APIRouter(prefix="/playlists", tags=["Playlists"])


def _can_view_playlist(playlist: Playlist, current_user: User | None) -> bool:
    if playlist.visibility == "public":
        return True
    if current_user and (playlist.owner_id == current_user.id or is_staff(current_user)):
        return True
    return False


def _serialize_summary(db: Session, playlist: Playlist, current_user: User | None) -> PlaylistSummary:
    visible_videos = []
    for item in playlist.items:
        if item.video and can_view_video(db, current_user, item.video):
            visible_videos.append(item.video)

    cover = None
    if visible_videos:
        cover = build_video_card(visible_videos[0], current_user).thumbnail_url

    return PlaylistSummary(
        id=playlist.id,
        title=playlist.title,
        description=playlist.description,
        visibility=playlist.visibility,
        videos_count=len(visible_videos),
        cover_thumbnail_url=cover,
        created_at=playlist.created_at,
        owner=ChannelSummary.model_validate(playlist.owner),
    )


@router.get("", response_model=list[PlaylistSummary], summary="List playlists by channel or current user")
def list_playlists(
    channel: str | None = Query(default=None, description="Channel username or ID"),
    mine: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[PlaylistSummary]:
    stmt = (
        select(Playlist)
        .options(
            joinedload(Playlist.owner),
            joinedload(Playlist.items).joinedload(PlaylistItem.video).joinedload(Video.owner),
        )
        .order_by(Playlist.updated_at.desc())
    )

    if mine:
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
        stmt = stmt.where(Playlist.owner_id == current_user.id)
    elif channel:
        clean = channel.lstrip("@").strip()
        owner = db.execute(
            select(User).where(or_(User.id == clean, User.username == clean.lower()))
        ).scalar_one_or_none()
        if not owner:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
        stmt = stmt.where(Playlist.owner_id == owner.id)
        if not (current_user and (current_user.id == owner.id or is_staff(current_user))):
            stmt = stmt.where(Playlist.visibility == "public")
    else:
        stmt = stmt.where(Playlist.visibility == "public")

    playlists = db.execute(stmt).unique().scalars().all()
    return [_serialize_summary(db, p, current_user) for p in playlists]


@router.post(
    "",
    response_model=PlaylistSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new playlist",
)
def create_playlist(
    payload: PlaylistCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlaylistSummary:
    playlist = Playlist(
        owner_id=current_user.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        visibility=payload.visibility,
    )
    db.add(playlist)
    db.commit()
    playlist = db.execute(
        select(Playlist)
        .options(joinedload(Playlist.owner), joinedload(Playlist.items))
        .where(Playlist.id == playlist.id)
    ).unique().scalar_one()
    return _serialize_summary(db, playlist, current_user)


@router.get("/{playlist_id}", response_model=PlaylistDetail, summary="Get playlist and its videos")
def get_playlist(
    playlist_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> PlaylistDetail:
    playlist = db.execute(
        select(Playlist)
        .options(
            joinedload(Playlist.owner),
            joinedload(Playlist.items).joinedload(PlaylistItem.video).joinedload(Video.owner),
        )
        .where(Playlist.id == playlist_id)
    ).unique().scalar_one_or_none()
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    if not _can_view_playlist(playlist, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    summary = _serialize_summary(db, playlist, current_user)
    videos = [
        build_video_card(item.video, current_user)
        for item in playlist.items
        if item.video and can_view_video(db, current_user, item.video)
    ]
    return PlaylistDetail(**summary.model_dump(), videos=videos)


@router.patch("/{playlist_id}", response_model=PlaylistSummary, summary="Update playlist metadata")
def update_playlist(
    playlist_id: str,
    payload: PlaylistUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlaylistSummary:
    playlist = db.execute(
        select(Playlist)
        .options(
            joinedload(Playlist.owner),
            joinedload(Playlist.items).joinedload(PlaylistItem.video).joinedload(Video.owner),
        )
        .where(Playlist.id == playlist_id)
    ).unique().scalar_one_or_none()
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    if playlist.owner_id != current_user.id and not is_staff(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if payload.title is not None:
        playlist.title = payload.title.strip()
    if payload.description is not None:
        playlist.description = payload.description.strip()
    if payload.visibility is not None:
        playlist.visibility = payload.visibility
    db.commit()
    db.refresh(playlist)
    return _serialize_summary(db, playlist, current_user)


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a playlist")
def delete_playlist(
    playlist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    playlist = db.get(Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    if playlist.owner_id != current_user.id and not is_staff(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(playlist)
    db.commit()


@router.post("/{playlist_id}/items", status_code=status.HTTP_201_CREATED, summary="Add a video to a playlist")
def add_video_to_playlist(
    playlist_id: str,
    payload: PlaylistAddVideoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    playlist = db.get(Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    if playlist.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only playlist owner can add videos")

    video = db.get(Video, payload.video_id)
    if not video or not can_view_video(db, current_user, video):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found or inaccessible")

    existing = db.execute(
        select(PlaylistItem).where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.video_id == payload.video_id,
        )
    ).scalar_one_or_none()
    if existing:
        return {"playlist_id": playlist_id, "video_id": payload.video_id, "already_present": True}

    max_pos = db.execute(
        select(func.coalesce(func.max(PlaylistItem.position), -1)).where(
            PlaylistItem.playlist_id == playlist_id
        )
    ).scalar_one()

    db.add(PlaylistItem(playlist_id=playlist_id, video_id=payload.video_id, position=int(max_pos) + 1))
    db.commit()
    return {"playlist_id": playlist_id, "video_id": payload.video_id, "already_present": False}


@router.delete(
    "/{playlist_id}/items/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a video from a playlist",
)
def remove_video_from_playlist(
    playlist_id: str,
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    playlist = db.get(Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    if playlist.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    item = db.execute(
        select(PlaylistItem).where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.video_id == video_id,
        )
    ).scalar_one_or_none()
    if item:
        db.delete(item)
        db.commit()
