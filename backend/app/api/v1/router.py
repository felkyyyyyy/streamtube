from fastapi import APIRouter

from app.api.v1 import auth, channels, comments, health, media, moderation, playlists, videos

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(channels.router)
api_router.include_router(videos.router)
api_router.include_router(media.router)
api_router.include_router(comments.router)
api_router.include_router(playlists.router)
api_router.include_router(moderation.router)
