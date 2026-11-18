export type UserRole = 'user' | 'moderator' | 'admin';
export type VideoVisibility = 'public' | 'unlisted' | 'private';
export type VideoStatus = 'uploading' | 'processing' | 'ready' | 'failed';
export type ModerationStatus = 'active' | 'hidden';

export interface UserPublic {
  id: string;
  username: string;
  email: string | null;
  role: UserRole;
  channel_name: string;
  channel_description: string;
  avatar_color: string;
  banner_color: string;
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserPublic;
}

export interface ChannelSummary {
  id: string;
  username: string;
  channel_name: string;
  avatar_color: string;
}

export interface ChannelProfile {
  id: string;
  username: string;
  channel_name: string;
  channel_description: string;
  avatar_color: string;
  banner_color: string;
  role: UserRole;
  subscribers_count: number;
  videos_count: number;
  is_subscribed: boolean;
  created_at: string;
}

export interface VideoCardItem {
  id: string;
  title: string;
  description: string;
  category: string;
  tags: string[];
  visibility: VideoVisibility;
  status: VideoStatus;
  moderation_status: ModerationStatus;
  duration_seconds: number;
  views_count: number;
  likes_count: number;
  dislikes_count: number;
  thumbnail_url: string | null;
  created_at: string;
  owner: ChannelSummary;
}

export interface VideoDetail extends VideoCardItem {
  moderation_reason: string | null;
  width: number;
  height: number;
  file_size_bytes: number;
  mime_type: string;
  hls_url: string | null;
  stream_url: string | null;
  playback_token: string | null;
  user_reaction: number;
  owner_subscribers_count: number;
  is_subscribed: boolean;
  comments_count: number;
  can_edit: boolean;
}

export interface VideoListResponse {
  items: VideoCardItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface AccessGrantItem {
  id: string;
  user_id: string;
  username: string;
  channel_name: string;
  avatar_color: string;
  created_at: string;
}

export interface CommentItem {
  id: string;
  video_id: string;
  parent_id: string | null;
  content: string;
  is_deleted: boolean;
  created_at: string;
  author: ChannelSummary;
  can_delete: boolean;
}

export interface PlaylistSummary {
  id: string;
  title: string;
  description: string;
  visibility: 'public' | 'private';
  videos_count: number;
  cover_thumbnail_url: string | null;
  created_at: string;
  owner: ChannelSummary;
}

export interface PlaylistDetail extends PlaylistSummary {
  videos: VideoCardItem[];
}

export interface ReportItem {
  id: string;
  video_id: string;
  video_title: string;
  video_moderation_status: ModerationStatus;
  video_owner_username: string;
  reporter: ChannelSummary;
  reason: string;
  details: string;
  status: 'open' | 'resolved_hidden' | 'dismissed';
  resolution_note: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface ModerationLogItem {
  id: string;
  actor_username: string | null;
  action: string;
  target_type: string;
  target_id: string;
  reason: string;
  created_at: string;
}

export interface AdminUserItem {
  id: string;
  username: string;
  email: string;
  channel_name: string;
  role: UserRole;
  is_active: boolean;
  videos_count: number;
  created_at: string;
}
