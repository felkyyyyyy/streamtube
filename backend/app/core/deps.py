from fastapi import Cookie, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None,
    access_cookie: str | None,
) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    if access_cookie:
        return access_cookie
    return None


def get_optional_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    access_token: str | None = Cookie(default=None),
) -> User | None:
    token = _extract_token(credentials, access_token)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user = db.get(User, payload["sub"])
    if not user or not user.is_active:
        return None
    return user


def get_current_user(
    user: User | None = Depends(get_optional_user),
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_moderator(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.MODERATOR.value, UserRole.ADMIN.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator or admin privileges required",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return user
