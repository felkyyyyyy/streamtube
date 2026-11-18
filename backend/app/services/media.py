import json
import logging
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from app.models.video import Video, VideoStatus
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv", ".m4v", ".avi"}
ALLOWED_VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-matroska",
    "video/x-msvideo",
    "application/octet-stream",  # verified via magic bytes
}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

SAFE_HLS_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def validate_video_magic_bytes(header: bytes) -> bool:
    """Validate common video container magic bytes to prevent arbitrary file uploads."""
    if len(header) < 12:
        return False
    # MP4 / MOV / M4V: ISO Base Media File Format ('ftyp' at offset 4)
    if header[4:8] == b"ftyp":
        return True
    # WebM / Matroska (EBML header)
    if header[:4] == b"\x1a\x45\xdf\xa3":
        return True
    # AVI (RIFF....AVI )
    if header[:4] == b"RIFF" and header[8:12] == b"AVI ":
        return True
    # Ogg
    if header[:4] == b"OggS":
        return True
    return False


def validate_image_magic_bytes(header: bytes) -> bool:
    if len(header) < 12:
        return False
    # JPEG
    if header[:3] == b"\xff\xd8\xff":
        return True
    # PNG
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    # WebP
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return True
    return False


def has_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def probe_video(input_path: Path) -> dict:
    """Inspect video metadata safely with ffprobe (no shell, restricted protocols)."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-protocol_whitelist",
        "file,pipe",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(input_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if res.returncode != 0:
        raise ValueError(f"Invalid media file (ffprobe failed): {res.stderr.strip()[:200]}")

    data = json.loads(res.stdout or "{}")
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    if not video_streams:
        raise ValueError("Uploaded file does not contain a valid video stream")

    vstream = video_streams[0]
    fmt = data.get("format", {})
    duration_raw = fmt.get("duration") or vstream.get("duration") or "0"
    try:
        duration_seconds = max(0, int(round(float(duration_raw))))
    except (ValueError, TypeError):
        duration_seconds = 0

    return {
        "duration_seconds": duration_seconds,
        "width": int(vstream.get("width") or 0),
        "height": int(vstream.get("height") or 0),
        "has_audio": any(s.get("codec_type") == "audio" for s in data.get("streams", [])),
    }


def extract_thumbnail(input_path: Path, output_jpg: Path, duration_seconds: int) -> bool:
    seek_sec = min(3, max(0, duration_seconds // 3))
    cmd = [
        "ffmpeg",
        "-y",
        "-protocol_whitelist",
        "file,pipe",
        "-ss",
        str(seek_sec),
        "-i",
        str(input_path),
        "-frames:v",
        "1",
        "-vf",
        "scale=640:-2",
        "-q:v",
        "4",
        str(output_jpg),
    ]
    res = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
    return res.returncode == 0 and output_jpg.exists() and output_jpg.stat().st_size > 0


def transcode_to_hls(input_path: Path, output_dir: Path, has_audio: bool) -> Path:
    """Transcode uploaded video into fast-loading H.264/AAC HLS segments."""
    output_dir.mkdir(parents=True, exist_ok=True)
    variant_playlist = output_dir / "stream_0.m3u8"
    master_playlist = output_dir / "master.m3u8"
    seg_pattern = str(output_dir / "seg_%03d.ts")

    cmd = [
        "ffmpeg",
        "-y",
        "-protocol_whitelist",
        "file,pipe",
        "-i",
        str(input_path),
        "-vf",
        "scale='min(1280,iw)':-2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "24",
        "-pix_fmt",
        "yuv420p",
        "-g",
        "48",
        "-sc_threshold",
        "0",
    ]
    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", "128k", "-ac", "2"]
    else:
        cmd += ["-an"]

    cmd += [
        "-f",
        "hls",
        "-hls_time",
        "4",
        "-hls_playlist_type",
        "vod",
        "-hls_segment_filename",
        seg_pattern,
        str(variant_playlist),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    if res.returncode != 0 or not variant_playlist.exists():
        raise RuntimeError(f"HLS transcoding failed: {res.stderr.strip()[:300]}")

    master_content = (
        "#EXTM3U\n"
        "#EXT-X-VERSION:3\n"
        "#EXT-X-STREAM-INF:BANDWIDTH=1800000,RESOLUTION=1280x720\n"
        "stream_0.m3u8\n"
    )
    master_playlist.write_text(master_content, encoding="utf-8")
    return master_playlist


def process_video_assets(video: Video, storage: StorageBackend) -> None:
    """Download raw source, probe metadata, generate thumbnail + HLS, upload back to storage."""
    if not has_ffmpeg():
        logger.warning("FFmpeg not installed; marking video %s ready with raw stream fallback", video.id)
        video.status = VideoStatus.READY.value
        return

    with tempfile.TemporaryDirectory(prefix=f"yt_{video.id[:8]}_") as tmp:
        tmp_dir = Path(tmp)
        ext = Path(video.storage_key).suffix or ".mp4"
        raw_path = tmp_dir / f"source{ext}"
        storage.download_file(video.storage_key, raw_path)

        meta = probe_video(raw_path)
        video.duration_seconds = meta["duration_seconds"]
        video.width = meta["width"]
        video.height = meta["height"]

        # Generate thumbnail if user didn't provide custom one
        if not video.thumbnail_key:
            thumb_path = tmp_dir / "thumb.jpg"
            if extract_thumbnail(raw_path, thumb_path, video.duration_seconds):
                thumb_key = f"videos/{video.id}/thumb.jpg"
                storage.put_file(thumb_key, thumb_path, content_type="image/jpeg")
                video.thumbnail_key = thumb_key

        # Transcode to HLS
        hls_dir = tmp_dir / "hls"
        transcode_to_hls(raw_path, hls_dir, has_audio=meta["has_audio"])

        for file_path in sorted(hls_dir.iterdir()):
            if not file_path.is_file():
                continue
            ctype = (
                "application/vnd.apple.mpegurl"
                if file_path.suffix == ".m3u8"
                else "video/MP2T"
            )
            storage.put_file(
                f"videos/{video.id}/hls/{file_path.name}",
                file_path,
                content_type=ctype,
            )

        video.hls_master_key = f"videos/{video.id}/hls/master.m3u8"
        video.status = VideoStatus.READY.value


def rewrite_m3u8_with_token(playlist_text: str, token: str) -> str:
    """Append signed playback token to every relative playlist/segment URI in an HLS manifest."""
    out_lines: list[str] = []
    for line in playlist_text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            sep = "&" if "?" in stripped else "?"
            out_lines.append(f"{stripped}{sep}token={token}")
        else:
            out_lines.append(line)
    return "\n".join(out_lines) + "\n"


def parse_range_header(range_header: str | None, file_size: int) -> tuple[int, int] | None:
    """Parse HTTP Range header ('bytes=start-end'). Returns (start, end) inclusive or None."""
    if not range_header or file_size <= 0:
        return None
    match = re.match(r"^bytes=(\d*)-(\d*)$", range_header.strip())
    if not match:
        return None
    start_str, end_str = match.groups()
    if start_str == "" and end_str == "":
        return None
    if start_str == "":
        suffix_len = int(end_str)
        if suffix_len <= 0:
            return None
        start = max(0, file_size - suffix_len)
        end = file_size - 1
    else:
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1

    if start >= file_size or end < start:
        return None
    end = min(end, file_size - 1)
    return start, end
