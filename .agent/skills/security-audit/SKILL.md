---
name: security-audit
description: Security verification checklist for StreamTube API, media delivery, and infrastructure.
---

# Security Audit Skill

Before marking the project complete, verify every item:
- [ ] Unauthenticated user CANNOT view private video metadata, thumbnail, MP4 Range stream, or HLS manifest/segments.
- [ ] Authenticated user without explicit grant CANNOT view another user's private video (`403`).
- [ ] Authenticated user WITH explicit grant CAN view private video and its stream/HLS/thumbnail; revoking grant immediately blocks new playback tokens.
- [ ] Hidden (moderated) video is invisible in Home feed, Search, Channel listing, and direct Watch/Media endpoints for regular users, but accessible to `moderator` and `admin`.
- [ ] Regular `user` CANNOT access `/api/v1/moderation/*` or `/api/v1/admin/*` endpoints (`403`).
- [ ] User CANNOT edit/delete another user's video or comment or manage grants on another user's video (`403`).
- [ ] Path traversal attempts in media filename (`../../etc/passwd`) are rejected (`400`/`422`).
- [ ] Oversized or non-video files (e.g. HTML/PHP/EXE masquerading as `.mp4`) are rejected by magic-byte validation (`400`/`415`).
- [ ] Passwords are Argon2id-hashed and never returned in any API schema.
- [ ] Auth endpoints enforce rate limiting and do not leak whether email/username exists on login failure.
