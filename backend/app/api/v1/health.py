from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.queue import transcode_queue
from app.storage.factory import get_storage

router = APIRouter(tags=["Health"])


@router.get("/health", summary="System health check")
def healthcheck(db: Session = Depends(get_db)) -> dict:
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    storage_ok = get_storage().healthcheck()
    redis_ok = transcode_queue.healthcheck()

    return {
        "status": "ok" if (db_ok and storage_ok) else "degraded",
        "database": "ok" if db_ok else "error",
        "storage": "ok" if storage_ok else "error",
        "redis": "ok" if redis_ok else "unavailable",
    }
