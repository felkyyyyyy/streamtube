from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_optional_user
from app.core.security import create_media_playback_token, verify_media_playback_token
from app.models.user import User
from app.models.video import ModerationStatus, Video, VideoVisibility
from app.services.media import (
    SAFE_HLS_FILENAME_RE,
    parse_range_header,
    rewrite_m3u8_with_token,
)
from app.services.policies import can_stream_video
from app.storage.factory import get_storage

router = APIRouter(prefix="/media", tags=["Media Delivery"])


def _authorize_media_access(
    db: Session,
    video: Video,
    current_user: User | None,
    token: str | None,
) -> User | None:
    """Enforce zero-trust access control for private and moderated media."""
    is_restricted = (
        video.visibility == VideoVisibility.PRIVATE.value
        or video.moderation_status == ModerationStatus.HIDDEN.value
    )
    if not is_restricted:
        return current_user

    # 1) Try explicit signed playback token (re-checking current DB permissions for instant revocation!)
    if token:
        payload = verify_media_playback_token(token, expected_video_id=video.id)
        if payload:
            uid = payload.get("uid")
            if uid and uid != "anon":
                token_user = db.get(User, uid)
                if token_user and token_user.is_active and can_stream_video(db, token_user, video):
                    return token_user

    # 2) Fallback to authenticated cookie / Bearer header
    if current_user and can_stream_video(db, current_user, video):
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access to this media asset is forbidden",
    )


@router.get("/{video_id}/stream", summary="Stream video via HTTP 206 Range requests")
def stream_video(
    video_id: str,
    token: str | None = Query(default=None),
    range_header: str | None = Header(default=None, alias="Range"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    _authorize_media_access(db, video, current_user, token)

    storage = get_storage()
    try:
        file_size = storage.get_size(video.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")

    cache_ctl = (
        "private, max-age=300"
        if video.visibility == VideoVisibility.PRIVATE.value
        else "public, max-age=3600"
    )

    if range_header:
        parsed = parse_range_header(range_header, file_size)
        if parsed is None:
            return Response(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                headers={"Content-Range": f"bytes */{file_size}"},
            )
        start, end = parsed
        content_length = end - start + 1
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Cache-Control": cache_ctl,
        }
        return StreamingResponse(
            storage.iter_range(video.storage_key, start, end),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            media_type=video.mime_type or "video/mp4",
            headers=headers,
        )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Cache-Control": cache_ctl,
    }
    return StreamingResponse(
        storage.iter_range(video.storage_key, 0, max(0, file_size - 1)),
        status_code=status.HTTP_200_OK,
        media_type=video.mime_type or "video/mp4",
        headers=headers,
    )


@router.get("/{video_id}/hls/{filename}", summary="Serve HLS manifest or transport stream segment")
def serve_hls_asset(
    video_id: str,
    filename: str,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    if not SAFE_HLS_FILENAME_RE.match(filename) or ".." in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid media filename")

    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    actor = _authorize_media_access(db, video, current_user, token)

    key = f"videos/{video.id}/hls/{filename}"
    storage = get_storage()
    if not storage.exists(key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="HLS asset not found")

    if filename.endswith(".m3u8"):
        raw_playlist = storage.get_bytes(key).decode("utf-8")
        effective_token = token or create_media_playback_token(video.id, actor.id if actor else None)
        rewritten = rewrite_m3u8_with_token(raw_playlist, effective_token)
        return Response(
            content=rewritten,
            media_type="application/vnd.apple.mpegurl",
            headers={"Cache-Control": "no-store"},
        )

    if filename.endswith(".ts"):
        size = storage.get_size(key)
        return StreamingResponse(
            storage.iter_range(key, 0, max(0, size - 1)),
            media_type="video/MP2T",
            headers={
                "Content-Length": str(size),
                "Cache-Control": "private, max-age=300"
                if video.visibility == VideoVisibility.PRIVATE.value
                else "public, max-age=86400",
            },
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported HLS asset type")


@router.get("/{video_id}/thumbnail", summary="Serve video thumbnail with visibility enforcement")
def serve_thumbnail(
    video_id: str,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    video = db.get(Video, video_id)
    if not video or not video.thumbnail_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found")
    _authorize_media_access(db, video, current_user, token)

    storage = get_storage()
    try:
        data = storage.get_bytes(video.thumbnail_key)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail missing")

    ctype = "image/jpeg"
    if video.thumbnail_key.endswith(".png"):
        ctype = "image/png"
    elif video.thumbnail_key.endswith(".webp"):
        ctype = "image/webp"

    cache_ctl = (
        "private, max-age=300"
        if video.visibility == VideoVisibility.PRIVATE.value
        else "public, max-age=86400"
    )
    return Response(content=data, media_type=ctype, headers={"Cache-Control": cache_ctl})
