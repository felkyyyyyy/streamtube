from app.models.user import UserRole
from app.scripts.seed import seed_database
from tests.conftest import VALID_MP4_BYTES, create_privileged_user, register_and_login


def test_moderation_report_hide_unhide_and_audit_log(client, db_session):
    _, creator_headers = register_and_login(client, "bad_actor")
    _, reporter_headers = register_and_login(client, "good_citizen")
    _, mod_headers = create_privileged_user(client, db_session, "mod_guard", UserRole.MODERATOR)

    up = client.post(
        "/api/v1/videos",
        headers=creator_headers,
        data={"title": "Suspicious Video", "visibility": "public"},
        files={"file": ("clip.mp4", VALID_MP4_BYTES, "video/mp4")},
    )
    assert up.status_code == 201
    vid = up.json()["id"]

    # User files a report
    rep = client.post(
        "/api/v1/reports",
        json={"video_id": vid, "reason": "spam", "details": "Misleading content"},
        headers=reporter_headers,
    )
    assert rep.status_code == 201
    rep_id = rep.json()["id"]

    # Duplicate open report blocked
    dup = client.post(
        "/api/v1/reports",
        json={"video_id": vid, "reason": "spam", "details": "Again"},
        headers=reporter_headers,
    )
    assert dup.status_code == 409

    # Moderator sees report and hides video
    queue = client.get("/api/v1/moderation/reports?status=open", headers=mod_headers)
    assert queue.status_code == 200
    assert any(r["id"] == rep_id for r in queue.json())

    resolve = client.post(
        f"/api/v1/moderation/reports/{rep_id}/resolve",
        json={"action": "hide_video", "note": "Confirmed spam violation"},
        headers=mod_headers,
    )
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "resolved_hidden"

    # Hidden video disappears from feed and is blocked for regular users
    feed = client.get("/api/v1/videos")
    assert all(v["id"] != vid for v in feed.json()["items"])
    assert client.get(f"/api/v1/videos/{vid}", headers=reporter_headers).status_code == 403
    assert client.get(f"/api/v1/media/{vid}/stream", headers=reporter_headers).status_code == 403

    # Moderator can still inspect & restore (unhide)
    assert client.get(f"/api/v1/videos/{vid}", headers=mod_headers).status_code == 200
    unhide = client.post(
        f"/api/v1/moderation/videos/{vid}/unhide",
        json={"reason": "Appeal accepted"},
        headers=mod_headers,
    )
    assert unhide.status_code == 200
    assert client.get(f"/api/v1/videos/{vid}", headers=reporter_headers).status_code == 200

    # Audit logs recorded both actions
    logs = client.get("/api/v1/moderation/logs", headers=mod_headers)
    assert logs.status_code == 200
    actions = [entry["action"] for entry in logs.json()]
    assert "hide_video" in actions
    assert "unhide_video" in actions


def test_security_headers_swagger_and_seed_idempotency(client, db_session):
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"

    # Swagger & OpenAPI available
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200

    # Seeder is idempotent across repeated invocations
    seed_database(db_session)
    count_first = len(client.get("/api/v1/videos").json()["items"])
    assert count_first == 6  # 6 public demo videos (+ 1 private not listed publicly)

    seed_database(db_session)
    count_second = len(client.get("/api/v1/videos").json()["items"])
    assert count_second == count_first
