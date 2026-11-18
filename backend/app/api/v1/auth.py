from datetime import datetime, timedelta, timezone
import hashlib

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import rate_limit_dependency
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import RefreshToken, User, UserRole
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserPublic

router = APIRouter(prefix="/auth", tags=["Authentication"])

AVATAR_PALETTE = [
    "#e11d48",
    "#2563eb",
    "#059669",
    "#d97706",
    "#7c3aed",
    "#0891b2",
    "#db2777",
    "#ea580c",
]


def _pick_avatar_color(username: str) -> str:
    digest = hashlib.sha256(username.encode("utf-8")).digest()
    return AVATAR_PALETTE[digest[0] % len(AVATAR_PALETTE)]


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )


def _issue_session(db: Session, user: User, response: Response) -> AuthResponse:
    settings = get_settings()
    access = create_access_token(user.id, user.role)
    raw_refresh = generate_refresh_token()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    db.commit()
    _set_auth_cookies(response, access, raw_refresh)
    return AuthResponse(access_token=access, user=UserPublic.model_validate(user))


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_dependency("auth_register", limit=15, window_seconds=300))],
    summary="Register a new user account",
)
def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    existing = db.execute(
        select(User).where(
            or_(User.username == payload.username, User.email == payload.email.lower())
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email is already registered",
        )

    user = User(
        username=payload.username,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=UserRole.USER.value,
        channel_name=(payload.channel_name or payload.username).strip(),
        avatar_color=_pick_avatar_color(payload.username),
    )
    db.add(user)
    db.flush()
    return _issue_session(db, user, response)


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(rate_limit_dependency("auth_login", limit=20, window_seconds=300))],
    summary="Login with username or email",
)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    ident = payload.identifier.strip().lower()
    user = db.execute(
        select(User).where(or_(User.username == ident, User.email == ident))
    ).scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended",
        )

    return _issue_session(db, user, response)


@router.post("/refresh", response_model=AuthResponse, summary="Rotate refresh token and issue new access token")
def refresh_session(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> AuthResponse:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    token_row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not token_row or token_row.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    expires = token_row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user = db.get(User, token_row.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User unavailable")

    token_row.revoked = True
    return _issue_session(db, user, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Logout and revoke refresh token")
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> None:
    if refresh_token:
        token_row = db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
        ).scalar_one_or_none()
        if token_row:
            token_row.revoked = True
            db.commit()

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.get("/me", response_model=UserPublic, summary="Get currently authenticated user")
def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)
