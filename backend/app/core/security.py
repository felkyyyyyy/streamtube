import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from app.core.config import get_settings

_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False


def create_access_token(user_id: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "access" or not payload.get("sub"):
            return None
        return payload
    except jwt.PyJWTError:
        return None


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_media_playback_token(video_id: str, user_id: str | None) -> str:
    """Create a short-lived HMAC-SHA256 signed token scoped to (video_id, user_id, exp)."""
    settings = get_settings()
    exp = int(time.time()) + settings.MEDIA_TOKEN_EXPIRE_SECONDS
    payload_dict = {
        "vid": video_id,
        "uid": user_id or "anon",
        "exp": exp,
    }
    raw_payload = json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(raw_payload).rstrip(b"=").decode("ascii")
    sig = hmac.new(
        settings.MEDIA_SIGNING_SECRET.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    encoded_sig = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    return f"{encoded_payload}.{encoded_sig}"


def verify_media_playback_token(token: str, expected_video_id: str) -> dict[str, Any] | None:
    """Validate HMAC signature, expiration, and bound video_id using constant-time comparison."""
    settings = get_settings()
    parts = token.split(".")
    if len(parts) != 2:
        return None
    encoded_payload, encoded_sig = parts
    expected_sig = hmac.new(
        settings.MEDIA_SIGNING_SECRET.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    expected_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b"=").decode("ascii")
    if not hmac.compare_digest(encoded_sig, expected_b64):
        return None

    try:
        padded = encoded_payload + "=" * (-len(encoded_payload) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return None

    if payload.get("vid") != expected_video_id:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload
