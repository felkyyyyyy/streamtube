from tests.conftest import VALID_MP4_BYTES, VALID_PNG_BYTES, register_and_login


def _upload(client, headers, title="Demo Video", visibility="public", allowed_usernames=""):
    return client.post(
        "/api/v1/videos",
        headers=headers,
        data={
            "title": title,
            "description": "Test description",
            "category": "Programming",
            "tags": "fastapi,test",
            "visibility": visibility,
            "allowed_usernames": allowed_usernames,
        },
        files={
            "file": ("sample.mp4", VALID_MP4_BYTES, "video/mp4"),
            "thumbnail": ("thumb.png", VALID_PNG_BYTES, "image/png"),
        },
    )


def test_golden_user_flow_register_upload_watch_like_comment(client):
    # 1. Registration
    _, headers = register_and_login(client, "creator_one")

    # 2. Upload
    up = _upload(client, headers, title="My First FastAPI Video")
    assert up.status_code == 201, up.text
    video = up.json()
    vid = video["id"]
    assert video["title"] == "My First FastAPI Video"
    assert video["stream_url"] is not None
    assert video["thumbnail_url"] is not None

    # 3. Watch (metadata + Range 206 streaming + view count)
    watch = client.get(f"/api/v1/videos/{vid}")
    assert watch.status_code == 200
    stream_resp = client.get(
        watch.json()["stream_url"],
        headers={"Range": "bytes=0-15"},
    )
    assert stream_resp.status_code == 206
    assert stream_resp.headers["content-range"].startswith("bytes 0-15/")
    assert len(stream_resp.content) == 16

    view_resp = client.post(f"/api/v1/videos/{vid}/view")
    assert view_resp.status_code == 200
    assert view_resp.json()["views_count"] == 1

    # 4. Like
    like = client.post(f"/api/v1/videos/{vid}/reaction", json={"value": 1}, headers=headers)
    assert like.status_code == 200
    assert like.json()["likes_count"] == 1
    assert like.json()["user_reaction"] == 1

    # 5. Comment
    comment = client.post(
        f"/api/v1/videos/{vid}/comments",
        json={"content": "Awesome video!"},
        headers=headers,
    )
    assert comment.status_code == 201
    assert comment.json()["content"] == "Awesome video!"

    comments_list = client.get(f"/api/v1/videos/{vid}/comments")
    assert comments_list.status_code == 200
    assert len(comments_list.json()) == 1


def test_upload_rejects_malicious_non_video_payload(client):
    _, headers = register_and_login(client, "uploader_sec")

    # Fake .mp4 containing HTML/JS script
    resp = client.post(
        "/api/v1/videos",
        headers=headers,
        data={"title": "Malicious", "visibility": "public"},
        files={"file": ("evil.mp4", b"<script>alert(1)</script>not a video", "video/mp4")},
    )
    assert resp.status_code == 415

    # Disallowed extension
    resp_ext = client.post(
        "/api/v1/videos",
        headers=headers,
        data={"title": "Shell script", "visibility": "public"},
        files={"file": ("shell.sh", VALID_MP4_BYTES, "video/mp4")},
    )
    assert resp_ext.status_code == 400


def test_private_video_access_control_and_immediate_revocation(client):
    _, owner_headers = register_and_login(client, "owner_u")
    alice, alice_headers = register_and_login(client, "alice_u")
    _, bob_headers = register_and_login(client, "bob_u")

    up = _upload(
        client,
        owner_headers,
        title="Top Secret Private Clip",
        visibility="private",
        allowed_usernames="alice_u",
    )
    assert up.status_code == 201
    vid = up.json()["id"]

    # Private video MUST NOT appear in public feed
    feed = client.get("/api/v1/videos")
    assert all(v["id"] != vid for v in feed.json()["items"])

    # Unauthenticated user blocked on metadata, stream, and thumbnail
    assert client.get(f"/api/v1/videos/{vid}").status_code == 403
    assert client.get(f"/api/v1/media/{vid}/stream").status_code == 403
    assert client.get(f"/api/v1/media/{vid}/thumbnail").status_code == 403

    # Bob (no grant) blocked on metadata, stream, and thumbnail
    assert client.get(f"/api/v1/videos/{vid}", headers=bob_headers).status_code == 403
    assert client.get(f"/api/v1/media/{vid}/stream", headers=bob_headers).status_code == 403
    assert client.get(f"/api/v1/media/{vid}/thumbnail", headers=bob_headers).status_code == 403

    # Alice (granted) sees video in 'shared' feed, can inspect metadata, stream, and thumbnail
    shared = client.get("/api/v1/videos?feed=shared", headers=alice_headers)
    assert shared.status_code == 200
    assert any(v["id"] == vid for v in shared.json()["items"])

    alice_watch = client.get(f"/api/v1/videos/{vid}", headers=alice_headers)
    assert alice_watch.status_code == 200
    alice_stream_url = alice_watch.json()["stream_url"]
    alice_thumb_url = alice_watch.json()["thumbnail_url"]
    assert client.get(alice_stream_url).status_code == 200
    assert client.get(alice_thumb_url).status_code == 200

    # Bob cannot manage grants on owner's video
    assert (
        client.post(
            f"/api/v1/videos/{vid}/access",
            json={"username_or_email": "bob_u"},
            headers=bob_headers,
        ).status_code
        == 403
    )

    # Owner revokes Alice's access -> Alice's previously signed playback token is IMMEDIATELY rejected!
    revoke = client.delete(f"/api/v1/videos/{vid}/access/{alice['id']}", headers=owner_headers)
    assert revoke.status_code == 204
    assert client.get(f"/api/v1/videos/{vid}", headers=alice_headers).status_code == 403
    assert client.get(alice_stream_url).status_code == 403


def test_hls_manifest_token_rewriting_and_path_traversal_defense(client, reset_state):
    _, owner_headers = register_and_login(client, "hls_owner")
    up = _upload(client, owner_headers, title="HLS Video", visibility="private")
    vid = up.json()["id"]

    # Place synthetic HLS files in storage
    storage = reset_state
    storage.put_bytes(
        f"videos/{vid}/hls/master.m3u8",
        b"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=800000\nstream_0.m3u8\n",
        content_type="application/vnd.apple.mpegurl",
    )
    storage.put_bytes(
        f"videos/{vid}/hls/stream_0.m3u8",
        b"#EXTM3U\n#EXTINF:4.0,\nseg_000.ts\n#EXT-X-ENDLIST\n",
        content_type="application/vnd.apple.mpegurl",
    )
    storage.put_bytes(f"videos/{vid}/hls/seg_000.ts", b"\x47" * 188, content_type="video/MP2T")

    # Fetch master playlist as owner
    m = client.get(f"/api/v1/media/{vid}/hls/master.m3u8", headers=owner_headers)
    assert m.status_code == 200
    assert "stream_0.m3u8?token=" in m.text

    # Extract tokenized child URL and fetch without headers (just like hls.js!)
    child_line = [ln for ln in m.text.splitlines() if ln.startswith("stream_0.m3u8")][0]
    v_resp = client.get(f"/api/v1/media/{vid}/hls/{child_line}")
    assert v_resp.status_code == 200
    assert "seg_000.ts?token=" in v_resp.text

    seg_line = [ln for ln in v_resp.text.splitlines() if ln.startswith("seg_000.ts")][0]
    seg_resp = client.get(f"/api/v1/media/{vid}/hls/{seg_line}")
    assert seg_resp.status_code == 200
    assert seg_resp.content == b"\x47" * 188

    # Path traversal blocked
    trav = client.get(f"/api/v1/media/{vid}/hls/..%2Fsource.mp4", headers=owner_headers)
    assert trav.status_code in (400, 404)
