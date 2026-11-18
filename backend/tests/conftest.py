import os
from pathlib import Path
import tempfile

# Configure test environment BEFORE importing app modules
_tmp_root = tempfile.mkdtemp(prefix="streamtube_test_")
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp_root, 'test.db').as_posix()}"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["LOCAL_STORAGE_PATH"] = str(Path(_tmp_root, "storage"))
os.environ["ENABLE_BACKGROUND_WORKER"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-for-jwt-signing-123456"
os.environ["MEDIA_SIGNING_SECRET"] = "test-media-signing-secret-1234567890"

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.core.rate_limit import rate_limiter
from app.core.security import hash_password
from app.main import app
from app.models.user import User, UserRole
from app.storage.factory import set_storage_override
from app.storage.local import LocalStorage

VALID_MP4_BYTES = (
    b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    + b"\x00\x00\x00\x20mdat"
    + b"\x11\x22\x33\x44" * 32
)

VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc`\x00\x00\x00\x02\x00\x01"
    b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture(autouse=True)
def reset_state(tmp_path: Path):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    storage = LocalStorage(tmp_path / "media")
    set_storage_override(storage)
    rate_limiter.reset()
    yield storage
    set_storage_override(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def register_and_login(
    client: TestClient,
    username: str,
    email: str | None = None,
    password: str = "StrongPass123!",
) -> tuple[dict, dict]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email or f"{username}@example.com",
            "password": password,
            "channel_name": f"{username.title()} Channel",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    return data["user"], headers


def create_privileged_user(
    client: TestClient,
    db_session,
    username: str,
    role: UserRole,
    password: str = "StaffPass123!",
) -> tuple[User, dict]:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash=hash_password(password),
        role=role.value,
        channel_name=f"{username.title()} Staff",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return user, {"Authorization": f"Bearer {token}"}
