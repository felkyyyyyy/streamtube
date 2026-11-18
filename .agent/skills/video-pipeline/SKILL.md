---
name: video-pipeline
description: Implementation guide for StreamTube's upload, validation, FFmpeg transcoding, HLS delivery, and Range streaming pipeline.
---

# Video Pipeline Skill

## Upload Flow
1. `POST /api/v1/videos` accepts `multipart/form-data` (video file + optional custom thumbnail + metadata JSON/fields).
2. Stream uploaded bytes in 1 MiB chunks to temporary file while counting size (reject `413` if `> MAX_VIDEO_SIZE_BYTES`) and checking magic bytes header on first chunk.
3. Upload raw file to `StorageBackend` at `videos/{video_id}/source{ext}`.
4. Create `Video` record with `status="processing"` (or `"ready"` immediately if sync inline processing enabled for tests).
5. Enqueue `video_id` onto Redis queue `streamtube:transcode`.

## Background Worker (`app/worker/transcoder.py`)
1. Pop `video_id` from Redis (`BLPOP`).
2. Download raw video to isolated temp dir (`tempfile.TemporaryDirectory`).
3. Run `ffprobe` (`shell=False`, `-protocol_whitelist file,pipe`, timeout 30s) to extract `duration`, `width`, `height`, validate at least one video stream exists.
4. If no custom thumbnail exists, extract JPEG frame at `min(3, duration/3)` seconds via `ffmpeg`, upload to `videos/{video_id}/thumb.jpg`.
5. Transcode to HLS (`master.m3u8` + `stream_0.m3u8` + `seg_%03d.ts`, H.264/AAC, `-preset veryfast`, 4s segments, max 720p) and upload all generated files under `videos/{video_id}/hls/`.
6. Update DB: `status="ready"`, `hls_master_key`, `thumbnail_key`, `duration_seconds`, `width`, `height`.
7. On error: log structured error, set `status="failed"` (original file remains inspectable or marked failed cleanly).

## Playback & Access Control
1. `GET /api/v1/videos/{id}` checks `can_view_video(current_user, video)` and returns metadata + short-lived signed `playback_token` (15 min TTL).
2. `GET /api/v1/media/{id}/hls/master.m3u8?token=...` validates token or user session -> serves manifest with tokenized child playlist URLs.
3. `GET /api/v1/media/{id}/hls/{filename}?token=...` validates path (strict regex `^[a-zA-Z0-9_.-]+$`), validates token -> serves `.m3u8` (with tokenized `.ts` URLs) or streams `.ts` segment.
4. `GET /api/v1/media/{id}/stream?token=...` supports HTTP `Range: bytes=start-end` (`206 Partial Content`) directly from raw source video for instant playback before HLS completes or as fallback.
5. `GET /api/v1/media/{id}/thumbnail?token=...` enforces same visibility check for private/hidden videos.
