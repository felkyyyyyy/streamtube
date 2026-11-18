#!/usr/bin/env bash
set -euo pipefail

# StreamTube — Single-Command Production Deployment for Clean Ubuntu (22.04 / 24.04)
# Usage: bash deploy.sh   (or APP_PORT=8080 bash deploy.sh)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ "$(id -u)" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

log() {
  echo -e "\n\033[1;34m[StreamTube Deploy]\033[0m $*"
}

err() {
  echo -e "\n\033[1;31m[ERROR]\033[0m $*" >&2
}

install_docker_if_needed() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "Docker & Docker Compose plugin already installed."
  else
    log "Installing Docker Engine and Docker Compose plugin..."
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq ca-certificates curl gnupg openssl
    if ! command -v docker >/dev/null 2>&1; then
      curl -fsSL https://get.docker.com | $SUDO sh
    fi
    if ! docker compose version >/dev/null 2>&1; then
      $SUDO apt-get update -qq
      $SUDO apt-get install -y -qq docker-compose-plugin
    fi
  fi

  $SUDO systemctl enable docker >/dev/null 2>&1 || true
  $SUDO systemctl start docker >/dev/null 2>&1 || true
}

docker_cmd() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    $SUDO docker "$@"
  fi
}

generate_env_if_missing() {
  if [[ ! -f .env ]]; then
    log "Generating .env with cryptographically random secrets..."
    SECRET_KEY="$(openssl rand -hex 32)"
    MEDIA_SIGNING_SECRET="$(openssl rand -hex 32)"
    PG_PASS="$(openssl rand -hex 20)"
    MINIO_PASS="$(openssl rand -hex 20)"
    PORT_VAL="${APP_PORT:-80}"

    cat > .env <<EOF
APP_PORT=${PORT_VAL}
APP_ENV=production
SECRET_KEY=${SECRET_KEY}
MEDIA_SIGNING_SECRET=${MEDIA_SIGNING_SECRET}
COOKIE_SECURE=false
POSTGRES_USER=streamtube
POSTGRES_PASSWORD=${PG_PASS}
POSTGRES_DB=streamtube
MINIO_ROOT_USER=streamtube_minio
MINIO_ROOT_PASSWORD=${MINIO_PASS}
S3_BUCKET=streamtube-media
CORS_ORIGINS=http://localhost,http://127.0.0.1
EOF
    chmod 600 .env
  else
    log "Using existing .env configuration."
  fi
}

wait_for_service() {
  local url="$1"
  local label="$2"
  local max_tries=45
  local attempt=1

  log "Waiting for ${label} (${url})..."
  while [[ $attempt -le $max_tries ]]; do
    if curl -sf "$url" >/dev/null 2>&1; then
      log "${label} is healthy!"
      return 0
    fi
    sleep 2
    attempt=$((attempt + 1))
  done

  err "${label} failed to become healthy after $((max_tries * 2))s."
  docker_cmd compose logs --tail=60
  exit 1
}

main() {
  install_docker_if_needed
  generate_env_if_missing

  # Load APP_PORT from .env if set
  # shellcheck disable=SC1091
  source .env
  local port="${APP_PORT:-80}"

  log "Building and starting StreamTube services (PostgreSQL, Redis, MinIO, FastAPI, FFmpeg Worker, Nginx)..."
  docker_cmd compose up -d --build --remove-orphans

  wait_for_service "http://127.0.0.1:${port}/api/v1/health" "StreamTube API"

  log "Running Alembic database migrations..."
  docker_cmd compose exec -T backend alembic upgrade head

  log "Seeding demo data (users, channels, FFmpeg HD videos, HLS streams, playlists, comments, report)..."
  docker_cmd compose exec -T backend python -m app.scripts.seed

  log "Running automated smoke checks..."
  curl -sf "http://127.0.0.1:${port}/api/v1/health" | grep -q '"status":"ok"'
  curl -sf "http://127.0.0.1:${port}/docs" >/dev/null
  curl -sf "http://127.0.0.1:${port}/api/v1/videos" | grep -q '"items"'

  local host_ip
  host_ip="$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')"

  cat <<EOF

====================================================================
  StreamTube deployed successfully!
====================================================================
  Web App:      http://${host_ip}$([[ "$port" != "80" ]] && echo ":${port}")
  Swagger UI:   http://${host_ip}$([[ "$port" != "80" ]] && echo ":${port}")/docs
  Health Check: http://${host_ip}$([[ "$port" != "80" ]] && echo ":${port}")/api/v1/health

  Demo Accounts (also available as 1-click fill on /login):
    Admin:     admin     / AdminPass123!
    Moderator: moderator / ModPass123!
    Creator:   techdev   / DemoPass123!  (owns public + private video)
    Viewer:    alice     / DemoPass123!  (has access to private video)
    Viewer:    bob       / DemoPass123!  (no access to private video)

  Run backend tests inside container:
    docker compose exec backend pytest -v
====================================================================
EOF
}

main "$@"
