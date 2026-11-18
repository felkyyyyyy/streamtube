"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-18 17:47:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(40), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("channel_name", sa.String(80), nullable=False),
        sa.Column("channel_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("avatar_color", sa.String(16), nullable=False, server_default="#e11d48"),
        sa.Column("banner_color", sa.String(32), nullable=False, server_default="#1e293b"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "videos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(50), nullable=False, server_default="General"),
        sa.Column("tags", sa.String(300), nullable=False, server_default=""),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="public"),
        sa.Column("status", sa.String(20), nullable=False, server_default="processing"),
        sa.Column("moderation_status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("moderation_reason", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("hls_master_key", sa.String(512), nullable=True),
        sa.Column("thumbnail_key", sa.String(512), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=False, server_default="video/mp4"),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("views_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("likes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dislikes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_videos_owner_id", "videos", ["owner_id"])
    op.create_index("ix_videos_title", "videos", ["title"])
    op.create_index("ix_videos_category", "videos", ["category"])
    op.create_index("ix_videos_visibility", "videos", ["visibility"])
    op.create_index("ix_videos_status", "videos", ["status"])
    op.create_index("ix_videos_moderation_status", "videos", ["moderation_status"])
    op.create_index("ix_videos_views_count", "videos", ["views_count"])
    op.create_index("ix_videos_created_at", "videos", ["created_at"])
    op.create_index("ix_videos_feed", "videos", ["visibility", "moderation_status", "created_at"])

    op.create_table(
        "video_access_grants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("video_id", sa.String(36), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("granted_by_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("video_id", "user_id", name="uq_video_access_grant"),
    )
    op.create_index("ix_video_access_grants_video_id", "video_access_grants", ["video_id"])
    op.create_index("ix_video_access_grants_user_id", "video_access_grants", ["user_id"])

    op.create_table(
        "video_reactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("video_id", sa.String(36), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("video_id", "user_id", name="uq_video_reaction"),
        sa.CheckConstraint("value IN (1, -1)", name="ck_video_reaction_value"),
    )
    op.create_index("ix_video_reactions_video_id", "video_reactions", ["video_id"])
    op.create_index("ix_video_reactions_user_id", "video_reactions", ["user_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("video_id", sa.String(36), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("comments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_comments_video_id", "comments", ["video_id"])
    op.create_index("ix_comments_author_id", "comments", ["author_id"])
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"])
    op.create_index("ix_comments_created_at", "comments", ["created_at"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subscriber_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("subscriber_id", "channel_id", name="uq_subscription_pair"),
        sa.CheckConstraint("subscriber_id != channel_id", name="ck_no_self_subscription"),
    )
    op.create_index("ix_subscriptions_subscriber_id", "subscriptions", ["subscriber_id"])
    op.create_index("ix_subscriptions_channel_id", "subscriptions", ["channel_id"])

    op.create_table(
        "playlists",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="public"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_playlists_owner_id", "playlists", ["owner_id"])

    op.create_table(
        "playlist_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("playlist_id", sa.String(36), sa.ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("video_id", sa.String(36), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("playlist_id", "video_id", name="uq_playlist_video"),
    )
    op.create_index("ix_playlist_items_playlist_id", "playlist_items", ["playlist_id"])
    op.create_index("ix_playlist_items_video_id", "playlist_items", ["video_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("video_id", sa.String(36), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reporter_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("details", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("reviewed_by_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_reports_video_id", "reports", ["video_id"])
    op.create_index("ix_reports_reporter_id", "reports", ["reporter_id"])
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_created_at", "reports", ["created_at"])

    op.create_table(
        "moderation_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_moderation_logs_actor_id", "moderation_logs", ["actor_id"])
    op.create_index("ix_moderation_logs_target_id", "moderation_logs", ["target_id"])
    op.create_index("ix_moderation_logs_created_at", "moderation_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("moderation_logs")
    op.drop_table("reports")
    op.drop_table("playlist_items")
    op.drop_table("playlists")
    op.drop_table("subscriptions")
    op.drop_table("comments")
    op.drop_table("video_reactions")
    op.drop_table("video_access_grants")
    op.drop_table("videos")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
