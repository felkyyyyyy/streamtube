"""Idempotent demo data seeder for StreamTube.

Generates real playable MP4 + HLS videos and thumbnails using FFmpeg when available,
populates demo users (admin, moderator, creators, viewers), public & private videos
with explicit ACL grants, playlists, subscriptions, likes, comments, and moderation reports.
"""
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import subprocess
import tempfile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.moderation import Report, ReportReason, ReportStatus
from app.models.social import Comment, Playlist, PlaylistItem, Subscription
from app.models.user import User, UserRole
from app.models.video import (
    ModerationStatus,
    Video,
    VideoAccessGrant,
    VideoReaction,
    VideoStatus,
    VideoVisibility,
)
from app.services.media import has_ffmpeg, process_video_assets
from app.storage.factory import get_storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("streamtube.seed")

# Minimal valid ISO BMFF ftyp box fallback if FFmpeg is unavailable
MINIMAL_MP4_FALLBACK = (
    b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    b"\x00\x00\x00\x08free"
)

DEMO_USERS = [
    {
        "username": "admin",
        "email": "admin@streamtube.dev",
        "password": "AdminPass123!",
        "role": UserRole.ADMIN.value,
        "channel_name": "StreamTube Admin",
        "channel_description": "Platform administration and system operations channel.",
        "avatar_color": "#dc2626",
        "banner_color": "#450a0a",
    },
    {
        "username": "moderator",
        "email": "mod@streamtube.dev",
        "password": "ModPass123!",
        "role": UserRole.MODERATOR.value,
        "channel_name": "Trust & Safety",
        "channel_description": "Community guidelines & content moderation team.",
        "avatar_color": "#d97706",
        "banner_color": "#451a03",
    },
    {
        "username": "techdev",
        "email": "tech@streamtube.dev",
        "password": "DemoPass123!",
        "role": UserRole.USER.value,
        "channel_name": "TechCraft Studio",
        "channel_description": "Deep dives into FastAPI, PostgreSQL, video streaming, and distributed systems.",
        "avatar_color": "#2563eb",
        "banner_color": "#1e3a8a",
    },
    {
        "username": "synthwave",
        "email": "music@streamtube.dev",
        "password": "DemoPass123!",
        "role": UserRole.USER.value,
        "channel_name": "Neon Soundscape",
        "channel_description": "Ambient synthwave, coding focus beats, and modular synthesizer sessions.",
        "avatar_color": "#7c3aed",
        "banner_color": "#3b0764",
    },
    {
        "username": "alice",
        "email": "alice@streamtube.dev",
        "password": "DemoPass123!",
        "role": UserRole.USER.value,
        "channel_name": "Alice Reviews",
        "channel_description": "Design systems, UI architecture, and indie software reviews.",
        "avatar_color": "#059669",
        "banner_color": "#064e3b",
    },
    {
        "username": "bob",
        "email": "bob@streamtube.dev",
        "password": "DemoPass123!",
        "role": UserRole.USER.value,
        "channel_name": "Bob's Lab",
        "channel_description": "Hardware hacking, Linux homelabs, and weekend experiments.",
        "avatar_color": "#0891b2",
        "banner_color": "#164e63",
    },
]

DEMO_VIDEOS = [
    {
        "owner": "techdev",
        "title": "Building Adaptive HLS Video Streaming with FastAPI & FFmpeg",
        "description": (
            "Learn how modern video platforms ingest uploads, validate containers with ffprobe, "
            "transcode into HLS segments in background workers, and serve byte-range fallbacks."
        ),
        "category": "Programming",
        "tags": "fastapi,ffmpeg,hls,streaming,python",
        "visibility": VideoVisibility.PUBLIC.value,
        "views": 18420,
        "days_ago": 5,
        "ffmpeg_src": "testsrc2=size=1280x720:rate=24",
        "freq": 440,
        "duration": 10,
    },
    {
        "owner": "techdev",
        "title": "PostgreSQL Schema Design for High-Scale Social Platforms",
        "description": (
            "Composite indexes, check constraints, foreign key cascades, and access-control "
            "tables explained with real query plans."
        ),
        "category": "Technology",
        "tags": "postgresql,database,architecture,sql",
        "visibility": VideoVisibility.PUBLIC.value,
        "views": 12350,
        "days_ago": 4,
        "ffmpeg_src": "smptehdbars=size=1280x720:rate=24",
        "freq": 523,
        "duration": 8,
    },
    {
        "owner": "synthwave",
        "title": "Midnight Coding Session — Generative Ambient Synth (HD)",
        "description": (
            "Relaxing generative harmonic tones and visual geometry for late-night coding "
            "and deep architecture sessions."
        ),
        "category": "Music",
        "tags": "synthwave,ambient,coding,music",
        "visibility": VideoVisibility.PUBLIC.value,
        "views": 45190,
        "days_ago": 3,
        "ffmpeg_src": "mandelbrot=size=1280x720:rate=24",
        "freq": 330,
        "duration": 10,
    },
    {
        "owner": "alice",
        "title": "YouTube UI Anatomy: Crafting a Responsive Dark-Mode Video App",
        "description": (
            "Breaking down grid breakpoints, aspect-ratio video cards, collapsible navigation "
            "rails, and keyboard-friendly playback controls."
        ),
        "category": "Design",
        "tags": "ui,ux,tailwind,react,design",
        "visibility": VideoVisibility.PUBLIC.value,
        "views": 9870,
        "days_ago": 2,
        "ffmpeg_src": "rgbtestsrc=size=1280x720:rate=24",
        "freq": 392,
        "duration": 8,
    },
    {
        "owner": "bob",
        "title": "Self-Hosting MinIO S3 & Docker Compose on Ubuntu 24.04",
        "description": (
            "Step-by-step walkthrough of deploying object storage, Redis queues, Nginx reverse "
            "proxy, and isolated containers with a single bash command."
        ),
        "category": "Education",
        "tags": "ubuntu,docker,minio,devops,linux",
        "visibility": VideoVisibility.PUBLIC.value,
        "views": 7430,
        "days_ago": 1,
        "ffmpeg_src": "yuvtestsrc=size=1280x720:rate=24",
        "freq": 494,
        "duration": 8,
    },
    {
        "owner": "bob",
        "title": "Zero-Trust Media Security: Signed Tokens & Private Video ACLs",
        "description": (
            "Why public S3 buckets leak private content and how HMAC-signed playback URLs "
            "with real-time DB revocation protect creator videos."
        ),
        "category": "Science",
        "tags": "security,appsec,hmac,rbac,privacy",
        "visibility": VideoVisibility.PUBLIC.value,
        "views": 6120,
        "days_ago": 0,
        "ffmpeg_src": "testsrc=size=1280x720:rate=24",
        "freq": 587,
        "duration": 8,
    },
    {
        "owner": "techdev",
        "title": "[PRIVATE] Unreleased Architecture Roadmap & Security Audit",
        "description": (
            "Private internal video shared exclusively with @alice. "
            "Unauthorized users cannot access metadata, thumbnail, or stream segments."
        ),
        "category": "Technology",
        "tags": "private,roadmap,internal",
        "visibility": VideoVisibility.PRIVATE.value,
        "views": 14,
        "days_ago": 1,
        "ffmpeg_src": "smptebars=size=1280x720:rate=24",
        "freq": 660,
        "duration": 8,
    },
]


def _generate_demo_mp4(dest: Path, ffmpeg_src: str, freq: int, duration: int) -> bool:
    if not has_ffmpeg():
        dest.write_bytes(MINIMAL_MP4_FALLBACK)
        return False

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"{ffmpeg_src}:duration={duration}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency={freq}:duration={duration}",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    if res.returncode != 0 or not dest.exists():
        logger.warning("FFmpeg synthetic video generation failed: %s", res.stderr[:200])
        dest.write_bytes(MINIMAL_MP4_FALLBACK)
        return False
    return True


def seed_database(db: Session) -> None:
    storage = get_storage()
    users_by_name: dict[str, User] = {}

    for udata in DEMO_USERS:
        existing = db.execute(select(User).where(User.username == udata["username"])).scalar_one_or_none()
        if existing:
            users_by_name[udata["username"]] = existing
            continue
        user = User(
            username=udata["username"],
            email=udata["email"],
            password_hash=hash_password(udata["password"]),
            role=udata["role"],
            channel_name=udata["channel_name"],
            channel_description=udata["channel_description"],
            avatar_color=udata["avatar_color"],
            banner_color=udata["banner_color"],
        )
        db.add(user)
        db.flush()
        users_by_name[udata["username"]] = user
        logger.info("Created user: %s (%s)", user.username, user.role)

    db.commit()

    videos_by_title: dict[str, Video] = {}
    now = datetime.now(timezone.utc)

    for vdata in DEMO_VIDEOS:
        existing = db.execute(select(Video).where(Video.title == vdata["title"])).scalar_one_or_none()
        if existing:
            videos_by_title[vdata["title"]] = existing
            continue

        owner = users_by_name[vdata["owner"]]
        video = Video(
            owner_id=owner.id,
            title=vdata["title"],
            description=vdata["description"],
            category=vdata["category"],
            tags=vdata["tags"],
            visibility=vdata["visibility"],
            status=VideoStatus.PROCESSING.value,
            moderation_status=ModerationStatus.ACTIVE.value,
            storage_key="",
            mime_type="video/mp4",
            views_count=vdata["views"],
            duration_seconds=vdata["duration"],
            created_at=now - timedelta(days=vdata["days_ago"], hours=2),
        )
        db.add(video)
        db.flush()

        storage_key = f"videos/{video.id}/source.mp4"
        video.storage_key = storage_key

        with tempfile.TemporaryDirectory(prefix="seed_vid_") as tmp:
            mp4_path = Path(tmp) / "source.mp4"
            generated_real = _generate_demo_mp4(
                mp4_path, vdata["ffmpeg_src"], vdata["freq"], vdata["duration"]
            )
            video.file_size_bytes = mp4_path.stat().st_size
            storage.put_file(storage_key, mp4_path, content_type="video/mp4")

        if generated_real:
            try:
                process_video_assets(video, storage)
            except Exception as exc:
                logger.warning("Failed to process seed video %s: %s", video.title, exc)
                video.status = VideoStatus.READY.value
        else:
            video.status = VideoStatus.READY.value

        db.commit()
        videos_by_title[vdata["title"]] = video
        logger.info("Seeded video: %s (hls=%s)", video.title, bool(video.hls_master_key))

    # Grant private video access to alice
    private_video = videos_by_title.get("[PRIVATE] Unreleased Architecture Roadmap & Security Audit")
    if private_video:
        alice = users_by_name["alice"]
        techdev = users_by_name["techdev"]
        exists_grant = db.execute(
            select(VideoAccessGrant).where(
                VideoAccessGrant.video_id == private_video.id,
                VideoAccessGrant.user_id == alice.id,
            )
        ).scalar_one_or_none()
        if not exists_grant:
            db.add(
                VideoAccessGrant(
                    video_id=private_video.id,
                    user_id=alice.id,
                    granted_by_id=techdev.id,
                )
            )
            db.commit()

    # Subscriptions
    sub_pairs = [
        ("alice", "techdev"),
        ("alice", "synthwave"),
        ("bob", "techdev"),
        ("bob", "alice"),
        ("techdev", "synthwave"),
        ("techdev", "bob"),
        ("moderator", "techdev"),
    ]
    for sub_name, chan_name in sub_pairs:
        s_user = users_by_name[sub_name]
        c_user = users_by_name[chan_name]
        exists_sub = db.execute(
            select(Subscription).where(
                Subscription.subscriber_id == s_user.id,
                Subscription.channel_id == c_user.id,
            )
        ).scalar_one_or_none()
        if not exists_sub:
            db.add(Subscription(subscriber_id=s_user.id, channel_id=c_user.id))
    db.commit()

    # Reactions
    first_vid = videos_by_title.get("Building Adaptive HLS Video Streaming with FastAPI & FFmpeg")
    second_vid = videos_by_title.get("PostgreSQL Schema Design for High-Scale Social Platforms")
    music_vid = videos_by_title.get("Midnight Coding Session — Generative Ambient Synth (HD)")

    reaction_seeds = [
        (first_vid, "alice", 1),
        (first_vid, "bob", 1),
        (first_vid, "synthwave", 1),
        (second_vid, "alice", 1),
        (second_vid, "bob", 1),
        (music_vid, "techdev", 1),
        (music_vid, "alice", 1),
        (music_vid, "bob", 1),
    ]
    for vid, uname, val in reaction_seeds:
        if not vid:
            continue
        u = users_by_name[uname]
        exists_rx = db.execute(
            select(VideoReaction).where(
                VideoReaction.video_id == vid.id,
                VideoReaction.user_id == u.id,
            )
        ).scalar_one_or_none()
        if not exists_rx:
            db.add(VideoReaction(video_id=vid.id, user_id=u.id, value=val))
            if val == 1:
                vid.likes_count += 1
            else:
                vid.dislikes_count += 1
    db.commit()

    # Comments
    if first_vid:
        existing_comments = db.execute(
            select(Comment).where(Comment.video_id == first_vid.id)
        ).scalars().all()
        if not existing_comments:
            c1 = Comment(
                video_id=first_vid.id,
                author_id=users_by_name["alice"].id,
                content="Super clean explanation of signed HLS playlists! Zero-trust media delivery is often overlooked.",
            )
            db.add(c1)
            db.flush()
            db.add(
                Comment(
                    video_id=first_vid.id,
                    author_id=users_by_name["techdev"].id,
                    parent_id=c1.id,
                    content="Thanks Alice! Rewriting relative .ts URLs with short-lived HMAC tokens keeps hls.js happy and private videos safe.",
                )
            )
            db.add(
                Comment(
                    video_id=first_vid.id,
                    author_id=users_by_name["bob"].id,
                    content="Just deployed this exact stack on Ubuntu 24.04 — worked on the first try!",
                )
            )
            db.commit()

    # Playlists
    techdev = users_by_name["techdev"]
    existing_pl = db.execute(
        select(Playlist).where(
            Playlist.owner_id == techdev.id,
            Playlist.title == "Backend & Streaming Architecture",
        )
    ).scalar_one_or_none()
    if not existing_pl and first_vid and second_vid:
        pl = Playlist(
            owner_id=techdev.id,
            title="Backend & Streaming Architecture",
            description="Curated videos on building scalable video platforms with FastAPI and PostgreSQL.",
            visibility="public",
        )
        db.add(pl)
        db.flush()
        db.add(PlaylistItem(playlist_id=pl.id, video_id=first_vid.id, position=0))
        db.add(PlaylistItem(playlist_id=pl.id, video_id=second_vid.id, position=1))
        db.commit()

    # Sample open moderation report so moderators can immediately review a ticket
    sec_vid = videos_by_title.get("Zero-Trust Media Security: Signed Tokens & Private Video ACLs")
    if sec_vid:
        existing_rep = db.execute(
            select(Report).where(Report.video_id == sec_vid.id)
        ).scalar_one_or_none()
        if not existing_rep:
            db.add(
                Report(
                    video_id=sec_vid.id,
                    reporter_id=users_by_name["alice"].id,
                    reason=ReportReason.OTHER.value,
                    details="Demo report for testing the moderation dashboard workflow (safe to dismiss or hide).",
                    status=ReportStatus.OPEN.value,
                )
            )
            db.commit()

    logger.info("Seed completed successfully.")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
