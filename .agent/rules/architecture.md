# Architecture Rules

## Backend Stack
- **FastAPI** with full OpenAPI 3.1 metadata and interactive Swagger UI at `/docs`.
- **SQLAlchemy 2.0** (declarative `Mapped[]` typing) + **Alembic** migrations.
- **PostgreSQL 16** in production; test suite runs cleanly against isolated database fixtures.
- **MinIO (S3 API)** for raw video uploads, transcoded HLS assets, thumbnails, and avatars; abstracted behind `StorageBackend` so local/test runs require no external service.
- **Redis 7** for background video transcoding queue and rate-limiting counters (with graceful in-memory fallback for unit tests).

## Domain Entities & Relationships
- `users`: identity, role (`user`, `moderator`, `admin`), channel metadata (`handle`, `channel_name`, `description`, `avatar_key`, `banner_color`), `is_active`.
- `videos`: `id` (UUID), `owner_id`, `title`, `description`, `category`, `tags`, `visibility` (`public`, `unlisted`, `private`), `status` (`uploading`, `processing`, `ready`, `failed`), `moderation_status` (`active`, `hidden`), `moderation_reason`, `storage_key`, `hls_master_key`, `thumbnail_key`, `duration_seconds`, `width`, `height`, `file_size_bytes`, `mime_type`, `views_count`, `likes_count`, `dislikes_count`.
- `video_access_grants`: `(video_id, user_id, granted_by_id, created_at)` with unique constraint on `(video_id, user_id)`.
- `video_reactions`: `(video_id, user_id, value)` where `value in (1, -1)`, unique `(video_id, user_id)`.
- `comments`: threaded comments (`parent_id` nullable self-FK), soft-delete/moderation support.
- `subscriptions`: `(subscriber_id, channel_id)`, unique constraint, check `subscriber_id != channel_id`.
- `playlists` & `playlist_items`: ordered video collections per channel with visibility.
- `reports`: user complaints against videos (`reason`, `details`, `status`, `reviewed_by_id`, `resolution_note`).
- `moderation_logs`: immutable audit trail of moderator/admin actions.
- `refresh_tokens`: hashed refresh token store for revocation and rotation.

## Frontend Stack
- React 19 + TypeScript + Vite + Tailwind CSS v4.
- `hls.js` for adaptive HLS playback with automatic MP4 Range fallback.
- YouTube-inspired layout: sticky header with search bar + upload/user controls, collapsible left navigation drawer, responsive video grid, dedicated watch/channel/search/upload/auth/moderation routes.
- Served as static files via Nginx, which proxies `/api`, `/docs`, `/redoc`, and `/openapi.json` to FastAPI.
