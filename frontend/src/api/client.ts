import type {
  AccessGrantItem,
  AdminUserItem,
  AuthResponse,
  ChannelProfile,
  ChannelSummary,
  CommentItem,
  ModerationLogItem,
  PlaylistDetail,
  PlaylistSummary,
  ReportItem,
  UserPublic,
  UserRole,
  VideoCardItem,
  VideoDetail,
  VideoListResponse,
  VideoVisibility,
} from '../types';

const API_BASE = '/api/v1';

let accessToken: string | null = localStorage.getItem('st_access_token');

export function setAccessToken(token: string | null) {
  accessToken = token;
  if (token) {
    localStorage.setItem('st_access_token', token);
  } else {
    localStorage.removeItem('st_access_token');
  }
}

export function getAccessToken(): string | null {
  return accessToken;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      return body.detail.map((e: { msg: string }) => e.msg).join('; ');
    }
  } catch {
    // ignore parse failure
  }
  return res.statusText || `HTTP ${res.status}`;
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });

  if (res.status === 401 && retry && !path.startsWith('/auth/')) {
    const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });
    if (refreshRes.ok) {
      const data: AuthResponse = await refreshRes.json();
      setAccessToken(data.access_token);
      return request<T>(path, init, false);
    } else {
      setAccessToken(null);
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorMessage(res));
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Auth
  register: (payload: { username: string; email: string; password: string; channel_name?: string }) =>
    request<AuthResponse>('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload: { identifier: string; password: string }) =>
    request<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  me: () => request<UserPublic>('/auth/me'),

  // Videos
  listVideos: (params: {
    q?: string;
    category?: string;
    sort?: 'newest' | 'popular' | 'oldest';
    feed?: 'all' | 'subscriptions' | 'mine' | 'shared';
    page?: number;
    page_size?: number;
  } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '') qs.set(k, String(v));
    });
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return request<VideoListResponse>(`/videos${suffix}`);
  },
  getCategories: () => request<string[]>('/videos/categories'),
  getVideo: (id: string) => request<VideoDetail>(`/videos/${id}`),
  getRecommendations: (id: string) => request<VideoCardItem[]>(`/videos/${id}/recommendations`),
  recordView: (id: string) => request<{ video_id: string; views_count: number }>(`/videos/${id}/view`, { method: 'POST' }),
  reactVideo: (id: string, value: 1 | -1 | 0) =>
    request<{ video_id: string; user_reaction: number; likes_count: number; dislikes_count: number }>(
      `/videos/${id}/reaction`,
      { method: 'POST', body: JSON.stringify({ value }) },
    ),
  updateVideo: (
    id: string,
    payload: Partial<{ title: string; description: string; category: string; tags: string; visibility: VideoVisibility }>,
  ) => request<VideoDetail>(`/videos/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteVideo: (id: string) => request<void>(`/videos/${id}`, { method: 'DELETE' }),

  // Private Access Grants
  listAccessGrants: (videoId: string) => request<AccessGrantItem[]>(`/videos/${videoId}/access`),
  grantAccess: (videoId: string, username_or_email: string) =>
    request<AccessGrantItem>(`/videos/${videoId}/access`, {
      method: 'POST',
      body: JSON.stringify({ username_or_email }),
    }),
  revokeAccess: (videoId: string, userId: string) =>
    request<void>(`/videos/${videoId}/access/${userId}`, { method: 'DELETE' }),

  // Upload with XHR progress callback
  uploadVideoWithProgress: (formData: FormData, onProgress: (pct: number) => void): Promise<VideoDetail> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_BASE}/videos`);
      xhr.withCredentials = true;
      if (accessToken) {
        xhr.setRequestHeader('Authorization', `Bearer ${accessToken}`);
      }
      xhr.upload.onprogress = (ev) => {
        if (ev.lengthComputable) {
          onProgress(Math.round((ev.loaded / ev.total) * 100));
        }
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText) as VideoDetail);
          } catch {
            reject(new ApiError(xhr.status, 'Invalid response from server'));
          }
        } else {
          let msg = xhr.statusText || `HTTP ${xhr.status}`;
          try {
            const parsed = JSON.parse(xhr.responseText);
            if (typeof parsed.detail === 'string') msg = parsed.detail;
          } catch {
            // ignore
          }
          reject(new ApiError(xhr.status, msg));
        }
      };
      xhr.onerror = () => reject(new ApiError(0, 'Network error during upload'));
      xhr.send(formData);
    });
  },

  // Comments
  listComments: (videoId: string) => request<CommentItem[]>(`/videos/${videoId}/comments`),
  postComment: (videoId: string, content: string, parent_id?: string | null) =>
    request<CommentItem>(`/videos/${videoId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content, parent_id: parent_id || null }),
    }),
  deleteComment: (commentId: string) => request<void>(`/comments/${commentId}`, { method: 'DELETE' }),

  // Channels & Subscriptions
  getChannel: (handle: string) => request<ChannelProfile>(`/channels/${encodeURIComponent(handle)}`),
  getChannelVideos: (handle: string) =>
    request<VideoCardItem[]>(`/channels/${encodeURIComponent(handle)}/videos`),
  updateMyChannel: (payload: {
    channel_name?: string;
    channel_description?: string;
    avatar_color?: string;
    banner_color?: string;
  }) => request<ChannelProfile>('/channels/me', { method: 'PATCH', body: JSON.stringify(payload) }),
  toggleSubscribe: (channelId: string) =>
    request<{ channel_id: string; subscribed: boolean; subscribers_count: number }>(
      `/channels/${channelId}/subscribe`,
      { method: 'POST' },
    ),
  listMySubscriptions: () => request<ChannelSummary[]>('/subscriptions'),
  searchUsers: (q: string) =>
    request<ChannelSummary[]>(`/users/search?q=${encodeURIComponent(q)}`),

  // Playlists
  listPlaylists: (params: { channel?: string; mine?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.channel) qs.set('channel', params.channel);
    if (params.mine) qs.set('mine', 'true');
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return request<PlaylistSummary[]>(`/playlists${suffix}`);
  },
  getPlaylist: (id: string) => request<PlaylistDetail>(`/playlists/${id}`),
  createPlaylist: (payload: { title: string; description: string; visibility: 'public' | 'private' }) =>
    request<PlaylistSummary>('/playlists', { method: 'POST', body: JSON.stringify(payload) }),
  deletePlaylist: (id: string) => request<void>(`/playlists/${id}`, { method: 'DELETE' }),
  addToPlaylist: (playlistId: string, videoId: string) =>
    request<{ playlist_id: string; video_id: string }>(`/playlists/${playlistId}/items`, {
      method: 'POST',
      body: JSON.stringify({ video_id: videoId }),
    }),
  removeFromPlaylist: (playlistId: string, videoId: string) =>
    request<void>(`/playlists/${playlistId}/items/${videoId}`, { method: 'DELETE' }),

  // Moderation & Admin
  reportVideo: (payload: { video_id: string; reason: string; details: string }) =>
    request<ReportItem>('/reports', { method: 'POST', body: JSON.stringify(payload) }),
  listReports: (status: 'open' | 'resolved_hidden' | 'dismissed' | 'all' = 'open') =>
    request<ReportItem[]>(`/moderation/reports?status=${status}`),
  resolveReport: (reportId: string, action: 'hide_video' | 'dismiss', note: string) =>
    request<ReportItem>(`/moderation/reports/${reportId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ action, note }),
    }),
  hideVideo: (videoId: string, reason: string) =>
    request<{ video_id: string; moderation_status: string }>(`/moderation/videos/${videoId}/hide`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  unhideVideo: (videoId: string, reason: string) =>
    request<{ video_id: string; moderation_status: string }>(`/moderation/videos/${videoId}/unhide`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  listHiddenVideos: () => request<VideoCardItem[]>('/moderation/videos/hidden'),
  listModerationLogs: () => request<ModerationLogItem[]>('/moderation/logs'),
  listAdminUsers: () => request<AdminUserItem[]>('/admin/users'),
  updateUserRole: (userId: string, role: UserRole) =>
    request<AdminUserItem>(`/admin/users/${userId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    }),
  toggleUserActive: (userId: string, active: boolean) =>
    request<AdminUserItem>(`/admin/users/${userId}/active?active=${active}`, { method: 'PATCH' }),
};
