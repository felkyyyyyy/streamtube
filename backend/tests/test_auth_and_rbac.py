from app.models.user import UserRole
from tests.conftest import create_privileged_user, register_and_login


def test_register_login_refresh_and_logout(client):
    user, headers = register_and_login(client, "alex_dev", "alex@example.com", "MySecretPass1!")
    assert user["username"] == "alex_dev"
    assert user["role"] == "user"

    # Duplicate registration fails with 409
    dup = client.post(
        "/api/v1/auth/register",
        json={
            "username": "alex_dev",
            "email": "other@example.com",
            "password": "MySecretPass1!",
        },
    )
    assert dup.status_code == 409

    # /auth/me works with Bearer token
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "alex_dev"

    # Login by email works
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": "alex@example.com", "password": "MySecretPass1!"},
    )
    assert login_resp.status_code == 200
    assert "refresh_token" in login_resp.cookies

    # Wrong password returns 401
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "alex_dev", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # Refresh rotates cookie token
    refresh_resp = client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200
    assert refresh_resp.json()["access_token"]

    # Logout revokes refresh token
    logout_resp = client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 204
    after_logout = client.post("/api/v1/auth/refresh")
    assert after_logout.status_code == 401


def test_rbac_role_boundaries(client, db_session):
    regular_user, user_headers = register_and_login(client, "viewer1")
    _, mod_headers = create_privileged_user(client, db_session, "mod1", UserRole.MODERATOR)
    admin_user, admin_headers = create_privileged_user(client, db_session, "admin1", UserRole.ADMIN)

    # Regular user blocked from moderation and admin
    assert client.get("/api/v1/moderation/reports", headers=user_headers).status_code == 403
    assert client.get("/api/v1/admin/users", headers=user_headers).status_code == 403

    # Moderator allowed on moderation, blocked on admin
    assert client.get("/api/v1/moderation/reports", headers=mod_headers).status_code == 200
    assert client.get("/api/v1/admin/users", headers=mod_headers).status_code == 403

    # Admin allowed on both and can promote a user
    assert client.get("/api/v1/admin/users", headers=admin_headers).status_code == 200
    promote = client.patch(
        f"/api/v1/admin/users/{regular_user['id']}/role",
        json={"role": "moderator"},
        headers=admin_headers,
    )
    assert promote.status_code == 200
    assert promote.json()["role"] == "moderator"

    # Admin cannot demote themselves
    self_demote = client.patch(
        f"/api/v1/admin/users/{admin_user.id}/role",
        json={"role": "user"},
        headers=admin_headers,
    )
    assert self_demote.status_code == 400
