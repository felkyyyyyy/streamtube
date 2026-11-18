from tests.conftest import VALID_MP4_BYTES, register_and_login


def _upload_public(client, headers, title, category="Technology"):
    resp = client.post(
        "/api/v1/videos",
        headers=headers,
        data={"title": title, "category": category, "visibility": "public"},
        files={"file": ("clip.mp4", VALID_MP4_BYTES, "video/mp4")},
    )
    assert resp.status_code == 201
    return resp.json()


def test_channels_subscriptions_search_and_playlists(client):
    creator, creator_headers = register_and_login(client, "tech_guru")
    _, viewer_headers = register_and_login(client, "fan_user")

    v1 = _upload_public(client, creator_headers, "Python FastAPI Deep Dive", "Programming")
    v2 = _upload_public(client, creator_headers, "PostgreSQL Indexing Guide", "Technology")

    # Search by title
    s = client.get("/api/v1/videos?q=FastAPI")
    assert s.status_code == 200
    assert len(s.json()["items"]) == 1
    assert s.json()["items"][0]["id"] == v1["id"]

    # Subscribe to channel
    sub = client.post(f"/api/v1/channels/{creator['id']}/subscribe", headers=viewer_headers)
    assert sub.status_code == 200
    assert sub.json()["subscribed"] is True
    assert sub.json()["subscribers_count"] == 1

    # Self-subscribe fails
    self_sub = client.post(f"/api/v1/channels/{creator['id']}/subscribe", headers=creator_headers)
    assert self_sub.status_code == 400

    # Subscriptions feed returns subscribed channel's videos
    sub_feed = client.get("/api/v1/videos?feed=subscriptions", headers=viewer_headers)
    assert sub_feed.status_code == 200
    assert len(sub_feed.json()["items"]) == 2

    # Channel profile reflects subscriber & video count
    prof = client.get(f"/api/v1/channels/{creator['username']}", headers=viewer_headers)
    assert prof.status_code == 200
    assert prof.json()["subscribers_count"] == 1
    assert prof.json()["videos_count"] == 2
    assert prof.json()["is_subscribed"] is True

    # Playlists CRUD
    pl = client.post(
        "/api/v1/playlists",
        json={"title": "Backend Mastery", "description": "Best tutorials", "visibility": "public"},
        headers=creator_headers,
    )
    assert pl.status_code == 201
    pl_id = pl.json()["id"]

    assert (
        client.post(
            f"/api/v1/playlists/{pl_id}/items",
            json={"video_id": v1["id"]},
            headers=creator_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/playlists/{pl_id}/items",
            json={"video_id": v2["id"]},
            headers=creator_headers,
        ).status_code
        == 201
    )

    pl_detail = client.get(f"/api/v1/playlists/{pl_id}")
    assert pl_detail.status_code == 200
    assert len(pl_detail.json()["videos"]) == 2

    # Non-owner cannot add to creator's playlist
    assert (
        client.post(
            f"/api/v1/playlists/{pl_id}/items",
            json={"video_id": v1["id"]},
            headers=viewer_headers,
        ).status_code
        == 403
    )

    # Remove item
    assert (
        client.delete(f"/api/v1/playlists/{pl_id}/items/{v1['id']}", headers=creator_headers).status_code
        == 204
    )
    assert len(client.get(f"/api/v1/playlists/{pl_id}").json()["videos"]) == 1
