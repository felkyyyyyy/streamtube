import logging
import signal
import sys
import time

from app.core.database import SessionLocal
from app.models.video import Video, VideoStatus
from app.services.media import process_video_assets
from app.services.queue import transcode_queue
from app.storage.factory import get_storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("streamtube.worker")

_running = True


def _handle_signal(_signum, _frame):
    global _running
    logger.info("Shutdown signal received, stopping worker gracefully...")
    _running = False


def process_one(video_id: str) -> None:
    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        if not video:
            logger.warning("Video %s not found in DB, skipping", video_id)
            return

        logger.info("Starting transcoding for video %s (%s)", video.id, video.title)
        video.status = VideoStatus.PROCESSING.value
        db.commit()

        storage = get_storage()
        process_video_assets(video, storage)
        db.commit()
        logger.info(
            "Finished transcoding video %s: duration=%ss, hls=%s",
            video.id,
            video.duration_seconds,
            video.hls_master_key,
        )
    except Exception as exc:
        logger.exception("Transcoding failed for video %s: %s", video_id, exc)
        db.rollback()
        video = db.get(Video, video_id)
        if video:
            video.status = VideoStatus.FAILED.value
            db.commit()
    finally:
        db.close()


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    logger.info("StreamTube background transcoding worker started")

    while _running:
        try:
            video_id = transcode_queue.pop_blocking(timeout=3)
            if video_id:
                process_one(video_id)
        except Exception as exc:
            logger.error("Worker loop error: %s", exc)
            time.sleep(2)

    logger.info("Worker exited cleanly")
    sys.exit(0)


if __name__ == "__main__":
    main()
