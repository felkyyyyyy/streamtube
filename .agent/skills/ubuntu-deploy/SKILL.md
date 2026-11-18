---
name: ubuntu-deploy
description: Guidelines for ensuring reliable single-command deployment on a clean Ubuntu 22.04/24.04 VM.
---

# Ubuntu One-Command Deploy Skill

`./deploy.sh` MUST work idempotently on a fresh Ubuntu 22.04/24.04 VM with root or sudo access:
1. Check/install `docker` and `docker compose` plugin (using official Docker apt repo or `get.docker.com` fallback) and start `docker` daemon.
2. Generate `.env` from `.env.example` with fresh cryptographically random secrets (`openssl rand -hex 32`) if `.env` does not already exist.
3. Run `docker compose up -d --build --remove-orphans`.
4. Wait until PostgreSQL, MinIO, Redis, and FastAPI `/api/v1/health` are healthy.
5. Run Alembic migrations (`alembic upgrade head`) inside the `backend` container.
6. Run idempotent demo seed script (`python -m app.scripts.seed`) inside the `backend` container to create demo users (admin, moderator, creators, viewer), channels, real FFmpeg-generated videos (public + private with grants), playlists, likes, comments, subscriptions, and sample moderation reports.
7. Run smoke test against `http://localhost/api/v1/health` and `http://localhost/docs` and print access URLs and demo accounts.
