# Security Rules & Invariants

Every endpoint, worker task, and deployment script MUST enforce these controls:

1. **Authentication & Session Safety**
   - Passwords hashed with **Argon2id** (`argon2-cffi`) — never plaintext, MD5, or SHA.
   - Short-lived JWT Access Tokens (HS256, 30 min TTL) + Rotating Refresh Tokens stored as SHA-256 hashes in DB and delivered via `HttpOnly; SameSite=Lax` cookies (plus `Authorization: Bearer` support for Swagger `/docs`).
   - Constant-time secret comparisons (`hmac.compare_digest`).

2. **Authorization (RBAC + Object-Level / IDOR)**
   - Roles: `user`, `moderator`, `admin`. Strict FastAPI dependencies (`require_user`, `require_moderator`, `require_admin`).
   - Centralized policy module (`app/services/policies.py`) for `can_view_video`, `can_edit_video`, `can_delete_video`, `can_manage_grants`.
   - Never trust client-supplied `owner_id`, `role`, or `moderation_status`.
   - Unauthorized access to private or hidden videos returns `403` or `404` without leaking metadata or storage keys.

3. **Upload & FFmpeg Hardening**
   - Strict max file size enforcement during chunked streaming read.
   - Validate MIME type AND magic bytes (MP4/WebM/MOV/MKV/AVI signatures).
   - Never construct shell commands with string interpolation — always `subprocess.run([...], shell=False)` with explicit timeout.
   - Pass `-protocol_whitelist file,pipe` to `ffmpeg`/`ffprobe` to block SSRF/local file exfiltration via crafted HLS/concat playlists.
   - Generate UUID-based object keys; never use user-provided filenames in filesystem or S3 paths (prevents path traversal).

4. **Signed Media Delivery**
   - Private video streams, HLS manifests, `.ts` segments, and thumbnails require valid HMAC-signed playback token (`?token=...`) scoped to `(video_id, user_id, exp)` or an authenticated cookie/header verified against `can_view_video`.
   - HLS playlists rewrite relative segment references to include the signed playback token so standard `hls.js` players work seamlessly without exposing raw storage credentials.

5. **Web & API Hardening**
   - Rate limiting on auth endpoints (`/auth/login`, `/auth/register`), uploads, and reports.
   - Security headers via Nginx & FastAPI middleware (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, CSP).
   - Parameterized SQL queries only (SQLAlchemy ORM / bound parameters).
   - No hardcoded production secrets — `deploy.sh` generates cryptographically random secrets in `.env`.
