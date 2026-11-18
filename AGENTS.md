# StreamTube — Agent Engineering Guide (AGENTS.md)

This repository implements **StreamTube**, a full-stack YouTube clone built with **Python + FastAPI**, **PostgreSQL**, **Redis**, **MinIO (S3)**, **FFmpeg**, and a **React + TypeScript + Tailwind CSS** frontend, deployable on a clean Ubuntu server with a single command (`./deploy.sh`).

## Core Architectural Principles

1. **Video Pipeline is the Heart of the System**
   - Uploads are streamed directly to object storage (MinIO/S3, with local filesystem fallback for tests/dev) — never buffered wholly into RAM.
   - Uploaded media is validated by content-type, size limits, magic bytes, and `ffprobe` before processing.
   - Background worker transcodes videos with `ffmpeg` into adaptive **HLS** (`.m3u8` + `.ts` segments), extracts duration/resolution, and generates thumbnails.
   - Immediate playback fallback via authenticated HTTP `206 Partial Content` Range streaming ensures zero wait-time regressions while HLS transcoding runs.

2. **Private Video Access Control (Zero-Trust Media Delivery)**
   - Private videos and their thumbnails/HLS segments are NEVER served via public bucket URLs.
   - Every media request is authorized via either user session/JWT OR short-lived HMAC-signed playback tokens bound to `(video_id, user_id, exp)` issued only after `can_view_video(user, video)` passes.
   - Hidden (moderated) videos are inaccessible to regular users (`404`/`403`) and visible only to moderators, admins, and (metadata-only with notice) the owner.

3. **Clean Layered Backend Architecture**
   - `app/api/v1/` — Thin HTTP routers, request/response schemas, dependency injection.
   - `app/services/` — Business logic, authorization policies (`policies.py`), video pipeline (`media.py`).
   - `app/models/` — SQLAlchemy 2.0 ORM models with explicit constraints and indexes.
   - `app/schemas/` — Strict Pydantic v2 DTOs (no ORM leaks, explicit field validation).
   - `app/storage/` — Pluggable `StorageBackend` (`S3Storage` / `LocalStorage`).
   - `app/worker/` — Redis-backed background media processing worker.

4. **Security First**
   - See `.agent/rules/security.md` for mandatory security invariants on every endpoint.

5. **Git Hygiene**
   - Follow Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `infra:`, `security:`).
   - One logical, reviewable, atomic commit per phase/component. Never squash history.

## Detailed Rules & Skills
- Architecture rules: `.agent/rules/architecture.md`
- Security rules: `.agent/rules/security.md`
- Git workflow: `.agent/rules/git-workflow.md`
- Skills: `.agent/skills/video-pipeline/SKILL.md`, `.agent/skills/security-audit/SKILL.md`, `.agent/skills/ubuntu-deploy/SKILL.md`
