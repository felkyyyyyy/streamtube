# Git Workflow Rules

- Use **Conventional Commits**:
  - `chore:` — repo setup, tooling, agent configuration
  - `infra:` — Docker, Nginx, PostgreSQL, MinIO, Redis, Ubuntu `deploy.sh`
  - `feat(db):` — SQLAlchemy models and Alembic migrations
  - `feat(auth):` — registration, login, JWT/refresh tokens, RBAC
  - `feat(video):` — storage backend, upload, FFmpeg worker, HLS & Range streaming, private ACLs
  - `feat(social):` — channels, subscriptions, playlists, likes, comments, search
  - `feat(moderation):` — reports, video hiding, admin controls, audit logs
  - `feat(frontend):` — React YouTube-style UI screens
  - `feat(seed):` — idempotent demo data & synthetic video generator
  - `test:` — automated pytest test suite
  - `security:` — security hardening & audit fixes
  - `docs:` — README, architecture, DB schema, security docs
- Commit logically after each cohesive unit of work is complete and verified.
- Never rewrite or squash commit history before submission.
