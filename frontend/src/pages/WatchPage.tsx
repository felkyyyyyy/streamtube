import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Check,
  Eye,
  EyeOff,
  Flag,
  ListPlus,
  Lock,
  MessageSquare,
  Send,
  Settings2,
  Share2,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  UserPlus,
  X,
} from 'lucide-react';
import { api, ApiError } from '../api/client';
import { Avatar } from '../components/Avatar';
import { VideoCard } from '../components/VideoCard';
import { VideoPlayer } from '../components/VideoPlayer';
import { useAuth } from '../context/AuthContext';
import type {
  AccessGrantItem,
  CommentItem,
  PlaylistSummary,
  VideoCardItem,
  VideoDetail,
  VideoVisibility,
} from '../types';
import { formatRelativeTime, formatViews } from '../utils/format';

export const WatchPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, isStaff } = useAuth();

  const [video, setVideo] = useState<VideoDetail | null>(null);
  const [recommendations, setRecommendations] = useState<VideoCardItem[]>([]);
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ status: number; message: string } | null>(null);
  const [descExpanded, setDescExpanded] = useState(false);

  // Comment state
  const [commentText, setCommentText] = useState('');
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');

  // Action feedback
  const [copied, setCopied] = useState(false);

  // Modals
  const [reportOpen, setReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState('spam');
  const [reportDetails, setReportDetails] = useState('');
  const [reportMsg, setReportMsg] = useState<string | null>(null);

  const [playlistOpen, setPlaylistOpen] = useState(false);
  const [myPlaylists, setMyPlaylists] = useState<PlaylistSummary[]>([]);
  const [newPlTitle, setNewPlTitle] = useState('');
  const [plMsg, setPlMsg] = useState<string | null>(null);

  const [manageOpen, setManageOpen] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editVis, setEditVis] = useState<VideoVisibility>('public');
  const [grants, setGrants] = useState<AccessGrantItem[]>([]);
  const [grantInput, setGrantInput] = useState('');
  const [manageMsg, setManageMsg] = useState<string | null>(null);

  const viewRecorded = useRef<string | null>(null);

  const loadAll = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [v, recs, comms] = await Promise.all([
        api.getVideo(id),
        api.getRecommendations(id).catch(() => []),
        api.listComments(id).catch(() => []),
      ]);
      setVideo(v);
      setRecommendations(recs);
      setComments(comms);
      setEditTitle(v.title);
      setEditDesc(v.description);
      setEditVis(v.visibility);

      if (viewRecorded.current !== id) {
        viewRecorded.current = id;
        api
          .recordView(id)
          .then((r) => setVideo((prev) => (prev ? { ...prev, views_count: r.views_count } : prev)))
          .catch(() => {});
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ status: err.status, message: err.message });
      } else {
        setError({ status: 500, message: 'Failed to load video' });
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadAll();
  }, [loadAll, user]);

  const handleReact = async (val: 1 | -1) => {
    if (!user) return navigate('/login');
    if (!video) return;
    const res = await api.reactVideo(video.id, val);
    setVideo({
      ...video,
      user_reaction: res.user_reaction,
      likes_count: res.likes_count,
      dislikes_count: res.dislikes_count,
    });
  };

  const handleSubscribe = async () => {
    if (!user) return navigate('/login');
    if (!video) return;
    const res = await api.toggleSubscribe(video.owner.id);
    setVideo({
      ...video,
      is_subscribed: res.subscribed,
      owner_subscribers_count: res.subscribers_count,
    });
  };

  const handlePostComment = async (e: React.FormEvent, parentId: string | null = null) => {
    e.preventDefault();
    if (!user) return navigate('/login');
    if (!video) return;
    const text = (parentId ? replyText : commentText).trim();
    if (!text) return;
    const created = await api.postComment(video.id, text, parentId);
    setComments((prev) => [created, ...prev]);
    setVideo({ ...video, comments_count: video.comments_count + 1 });
    if (parentId) {
      setReplyText('');
      setReplyTo(null);
    } else {
      setCommentText('');
    }
  };

  const handleDeleteComment = async (commentId: string) => {
    await api.deleteComment(commentId);
    setComments((prev) => prev.filter((c) => c.id !== commentId));
    if (video) setVideo({ ...video, comments_count: Math.max(0, video.comments_count - 1) });
  };

  const openManageModal = async () => {
    if (!video) return;
    setManageMsg(null);
    setManageOpen(true);
    try {
      const g = await api.listAccessGrants(video.id);
      setGrants(g);
    } catch {
      setGrants([]);
    }
  };

  const handleSaveMeta = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!video) return;
    const updated = await api.updateVideo(video.id, {
      title: editTitle,
      description: editDesc,
      visibility: editVis,
    });
    setVideo(updated);
    setManageMsg('Video settings saved.');
  };

  const handleGrantAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!video || !grantInput.trim()) return;
    setManageMsg(null);
    try {
      const created = await api.grantAccess(video.id, grantInput.trim());
      setGrants((prev) => [created, ...prev.filter((x) => x.user_id !== created.user_id)]);
      setGrantInput('');
      setManageMsg(`Access granted to @${created.username}`);
    } catch (err) {
      setManageMsg(err instanceof Error ? err.message : 'Could not grant access');
    }
  };

  const handleGrantRevoke = async (targetUserId: string) => {
    if (!video) return;
    await api.revokeAccess(video.id, targetUserId);
    setGrants((prev) => prev.filter((g) => g.user_id !== targetUserId));
    setManageMsg('Access revoked immediately.');
  };

  const handleDeleteVideo = async () => {
    if (!video || !window.confirm('Delete this video permanently?')) return;
    await api.deleteVideo(video.id);
    navigate('/studio');
  };

  const openPlaylistModal = async () => {
    if (!user) return navigate('/login');
    setPlMsg(null);
    setPlaylistOpen(true);
    const pls = await api.listPlaylists({ mine: true });
    setMyPlaylists(pls);
  };

  const handleAddToPlaylist = async (playlistId: string) => {
    if (!video) return;
    await api.addToPlaylist(playlistId, video.id);
    setPlMsg('Saved to playlist!');
  };

  const handleCreatePlaylistAndAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!video || !newPlTitle.trim()) return;
    const pl = await api.createPlaylist({
      title: newPlTitle.trim(),
      description: '',
      visibility: 'public',
    });
    await api.addToPlaylist(pl.id, video.id);
    setMyPlaylists((prev) => [pl, ...prev]);
    setNewPlTitle('');
    setPlMsg(`Created "${pl.title}" and saved video!`);
  };

  const handleSubmitReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!video) return;
    setReportMsg(null);
    try {
      await api.reportVideo({ video_id: video.id, reason: reportReason, details: reportDetails });
      setReportMsg('Report submitted to moderation team. Thank you.');
      setReportDetails('');
    } catch (err) {
      setReportMsg(err instanceof Error ? err.message : 'Failed to submit report');
    }
  };

  const handleStaffToggleHide = async () => {
    if (!video) return;
    if (video.moderation_status === 'hidden') {
      await api.unhideVideo(video.id, 'Restored from watch page');
    } else {
      const reason = window.prompt('Reason for hiding this video:', 'Community guidelines violation');
      if (!reason) return;
      await api.hideVideo(video.id, reason);
    }
    loadAll();
  };

  if (loading) {
    return (
      <div className="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6 animate-pulse">
        <div className="lg:col-span-8 space-y-4">
          <div className="aspect-video bg-zinc-800 rounded-xl" />
          <div className="h-7 bg-zinc-800 rounded w-3/4" />
          <div className="h-12 bg-zinc-800 rounded" />
        </div>
        <div className="lg:col-span-4 space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 bg-zinc-800 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="max-w-xl mx-auto py-20 text-center bg-[#181818] border border-zinc-800 rounded-2xl p-8">
        <Lock className="w-12 h-12 mx-auto text-amber-500 mb-3" />
        <h2 className="text-xl font-bold">
          {error?.status === 403 ? 'Private or Restricted Video' : 'Video Not Found'}
        </h2>
        <p className="text-sm text-zinc-400 mt-2">
          {error?.message || 'This video is unavailable.'}
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link
            to="/"
            className="px-5 py-2 rounded-full bg-[#272727] hover:bg-[#3f3f3f] text-sm font-medium"
          >
            Back to Home
          </Link>
          {!user && (
            <Link
              to="/login"
              className="px-5 py-2 rounded-full bg-[#3ea6ff] text-black font-semibold text-sm"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    );
  }

  const rootComments = comments.filter((c) => !c.parent_id);
  const repliesByParent = comments.reduce<Record<string, CommentItem[]>>((acc, c) => {
    if (c.parent_id) {
      acc[c.parent_id] = acc[c.parent_id] || [];
      acc[c.parent_id].push(c);
    }
    return acc;
  }, {});

  return (
    <div className="max-w-[1640px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Main Column */}
      <div className="lg:col-span-8 min-w-0">
        {video.moderation_status === 'hidden' && (
          <div className="mb-4 p-3.5 rounded-xl bg-red-950/60 border border-red-700 text-red-200 text-sm flex items-center justify-between gap-3">
            <div>
              <strong>Hidden by Moderation:</strong> {video.moderation_reason || 'Policy violation'}
            </div>
            {isStaff && (
              <button
                type="button"
                onClick={handleStaffToggleHide}
                className="px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold cursor-pointer"
              >
                Restore Video
              </button>
            )}
          </div>
        )}

        {video.stream_url || video.hls_url ? (
          <VideoPlayer
            hlsUrl={video.hls_url}
            streamUrl={video.stream_url}
            posterUrl={video.thumbnail_url}
            title={video.title}
          />
        ) : (
          <div className="aspect-video rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400">
            Playback unavailable while this video is hidden.
          </div>
        )}

        {/* Video Title & Badges */}
        <div className="mt-4">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-bold leading-snug">{video.title}</h1>
            {video.visibility === 'private' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-600/20 text-amber-300 border border-amber-500/40 text-xs font-medium">
                <Lock className="w-3 h-3" /> Private
              </span>
            )}
          </div>

          {/* Channel + Action Buttons Row */}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Link to={`/channel/${video.owner.username}`}>
                <Avatar name={video.owner.channel_name} color={video.owner.avatar_color} size="md" />
              </Link>
              <div>
                <Link
                  to={`/channel/${video.owner.username}`}
                  className="font-semibold text-sm hover:text-white block"
                >
                  {video.owner.channel_name}
                </Link>
                <p className="text-xs text-zinc-400">
                  {video.owner_subscribers_count} subscriber{video.owner_subscribers_count === 1 ? '' : 's'}
                </p>
              </div>
              {(!user || user.id !== video.owner.id) && (
                <button
                  type="button"
                  onClick={handleSubscribe}
                  className={`ml-3 px-4 py-2 rounded-full text-sm font-semibold transition-colors cursor-pointer ${
                    video.is_subscribed
                      ? 'bg-[#272727] hover:bg-[#3f3f3f] text-white'
                      : 'bg-white hover:bg-zinc-200 text-black'
                  }`}
                >
                  {video.is_subscribed ? 'Subscribed' : 'Subscribe'}
                </button>
              )}
            </div>

            {/* Action Pills */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex items-center rounded-full bg-[#272727] overflow-hidden">
                <button
                  type="button"
                  onClick={() => handleReact(1)}
                  className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium hover:bg-[#3f3f3f] transition-colors cursor-pointer ${
                    video.user_reaction === 1 ? 'text-[#3ea6ff]' : 'text-white'
                  }`}
                >
                  <ThumbsUp className={`w-4 h-4 ${video.user_reaction === 1 ? 'fill-current' : ''}`} />
                  <span>{video.likes_count}</span>
                </button>
                <div className="w-px h-5 bg-zinc-600" />
                <button
                  type="button"
                  onClick={() => handleReact(-1)}
                  className={`flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium hover:bg-[#3f3f3f] transition-colors cursor-pointer ${
                    video.user_reaction === -1 ? 'text-red-400' : 'text-white'
                  }`}
                >
                  <ThumbsDown className={`w-4 h-4 ${video.user_reaction === -1 ? 'fill-current' : ''}`} />
                  {video.dislikes_count > 0 && <span>{video.dislikes_count}</span>}
                </button>
              </div>

              <button
                type="button"
                onClick={() => {
                  navigator.clipboard?.writeText(window.location.href);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#272727] hover:bg-[#3f3f3f] text-sm font-medium cursor-pointer"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Share2 className="w-4 h-4" />}
                <span>{copied ? 'Copied' : 'Share'}</span>
              </button>

              <button
                type="button"
                onClick={openPlaylistModal}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#272727] hover:bg-[#3f3f3f] text-sm font-medium cursor-pointer"
              >
                <ListPlus className="w-4 h-4" />
                <span>Save</span>
              </button>

              {video.can_edit && (
                <button
                  type="button"
                  onClick={openManageModal}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#272727] hover:bg-[#3f3f3f] text-sm font-medium text-[#3ea6ff] cursor-pointer"
                >
                  <Settings2 className="w-4 h-4" />
                  <span>Manage / Access</span>
                </button>
              )}

              {user && user.id !== video.owner.id && (
                <button
                  type="button"
                  onClick={() => {
                    setReportMsg(null);
                    setReportOpen(true);
                  }}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-[#272727] hover:bg-[#3f3f3f] text-sm font-medium text-zinc-300 cursor-pointer"
                  title="Report video"
                >
                  <Flag className="w-4 h-4" />
                  <span className="hidden sm:inline">Report</span>
                </button>
              )}

              {isStaff && (
                <button
                  type="button"
                  onClick={handleStaffToggleHide}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/40 text-amber-300 text-sm font-medium cursor-pointer"
                >
                  {video.moderation_status === 'hidden' ? (
                    <>
                      <Eye className="w-4 h-4" /> Unhide
                    </>
                  ) : (
                    <>
                      <EyeOff className="w-4 h-4" /> Hide
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          {/* Expandable Description Box */}
          <div
            onClick={() => setDescExpanded((v) => !v)}
            className="mt-4 p-3.5 rounded-xl bg-[#272727]/80 hover:bg-[#2f2f2f] transition-colors cursor-pointer text-sm"
          >
            <div className="flex flex-wrap items-center gap-2 font-semibold text-zinc-100">
              <span>{formatViews(video.views_count)} views</span>
              <span>•</span>
              <span>{formatRelativeTime(video.created_at)}</span>
              <span className="px-2 py-0.5 rounded bg-zinc-700/80 text-xs font-normal">
                {video.category}
              </span>
              {video.width > 0 && (
                <span className="text-xs text-zinc-400 font-normal">
                  {video.width}×{video.height}
                </span>
              )}
            </div>
            <p
              className={`mt-2 text-zinc-200 whitespace-pre-wrap leading-relaxed ${
                descExpanded ? '' : 'line-clamp-2'
              }`}
            >
              {video.description || 'No description provided.'}
            </p>
            {video.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {video.tags.map((tag) => (
                  <Link
                    key={tag}
                    to={`/search?q=${encodeURIComponent(tag)}`}
                    onClick={(e) => e.stopPropagation()}
                    className="text-xs text-[#3ea6ff] hover:underline"
                  >
                    #{tag}
                  </Link>
                ))}
              </div>
            )}
            <span className="block mt-1.5 text-xs font-semibold text-zinc-400">
              {descExpanded ? 'Show less' : 'Show more'}
            </span>
          </div>
        </div>

        {/* Comments Section */}
        <section className="mt-7">
          <div className="flex items-center gap-2 mb-5">
            <MessageSquare className="w-5 h-5" />
            <h2 className="text-lg font-bold">{video.comments_count} Comments</h2>
          </div>

          {user ? (
            <form onSubmit={(e) => handlePostComment(e, null)} className="flex gap-3 mb-6">
              <Avatar name={user.channel_name} color={user.avatar_color} size="md" />
              <div className="flex-1">
                <input
                  type="text"
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  placeholder="Add a comment..."
                  className="w-full bg-transparent border-b border-zinc-700 focus:border-white py-2 text-sm focus:outline-none"
                />
                {commentText.trim() && (
                  <div className="flex justify-end gap-2 mt-2">
                    <button
                      type="button"
                      onClick={() => setCommentText('')}
                      className="px-4 py-1.5 rounded-full text-xs font-medium hover:bg-[#272727] cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-1.5 rounded-full bg-[#3ea6ff] text-black text-xs font-semibold flex items-center gap-1 cursor-pointer"
                    >
                      <Send className="w-3.5 h-3.5" /> Comment
                    </button>
                  </div>
                )}
              </div>
            </form>
          ) : (
            <div className="mb-6 p-3.5 rounded-xl bg-[#181818] border border-zinc-800 text-sm text-zinc-400">
              <Link to="/login" className="text-[#3ea6ff] hover:underline font-medium">
                Sign in
              </Link>{' '}
              to leave a comment or react to this video.
            </div>
          )}

          <div className="space-y-5">
            {rootComments.map((c) => (
              <div key={c.id} className="flex gap-3">
                <Link to={`/channel/${c.author.username}`}>
                  <Avatar name={c.author.channel_name} color={c.author.avatar_color} size="md" />
                </Link>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-xs">
                    <Link to={`/channel/${c.author.username}`} className="font-semibold text-zinc-100">
                      @{c.author.username}
                    </Link>
                    <span className="text-zinc-500">{formatRelativeTime(c.created_at)}</span>
                  </div>
                  <p className="text-sm text-zinc-200 mt-1 whitespace-pre-wrap break-words">
                    {c.content}
                  </p>
                  <div className="flex items-center gap-4 mt-1.5 text-xs text-zinc-400">
                    {user && (
                      <button
                        type="button"
                        onClick={() => setReplyTo(replyTo === c.id ? null : c.id)}
                        className="hover:text-white font-medium cursor-pointer"
                      >
                        Reply
                      </button>
                    )}
                    {c.can_delete && (
                      <button
                        type="button"
                        onClick={() => handleDeleteComment(c.id)}
                        className="inline-flex items-center gap-1 text-red-400 hover:text-red-300 cursor-pointer"
                      >
                        <Trash2 className="w-3 h-3" /> Delete
                      </button>
                    )}
                  </div>

                  {replyTo === c.id && (
                    <form onSubmit={(e) => handlePostComment(e, c.id)} className="mt-3 flex gap-2">
                      <input
                        type="text"
                        value={replyText}
                        onChange={(e) => setReplyText(e.target.value)}
                        placeholder={`Reply to @${c.author.username}...`}
                        className="flex-1 bg-[#121212] border border-zinc-700 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-[#3ea6ff]"
                      />
                      <button
                        type="submit"
                        className="px-3 py-1.5 rounded-lg bg-[#3ea6ff] text-black text-xs font-semibold cursor-pointer"
                      >
                        Reply
                      </button>
                    </form>
                  )}

                  {(repliesByParent[c.id] || []).length > 0 && (
                    <div className="mt-3 pl-4 border-l border-zinc-800 space-y-3">
                      {repliesByParent[c.id].map((r) => (
                        <div key={r.id} className="flex gap-2.5">
                          <Avatar name={r.author.channel_name} color={r.author.avatar_color} size="xs" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 text-xs">
                              <span className="font-semibold">@{r.author.username}</span>
                              <span className="text-zinc-500">{formatRelativeTime(r.created_at)}</span>
                            </div>
                            <p className="text-sm text-zinc-200 mt-0.5">{r.content}</p>
                            {r.can_delete && (
                              <button
                                type="button"
                                onClick={() => handleDeleteComment(r.id)}
                                className="mt-1 text-xs text-red-400 hover:text-red-300 cursor-pointer"
                              >
                                Delete
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Right Column: Recommended Videos */}
      <aside className="lg:col-span-4 space-y-3">
        <h3 className="text-sm font-semibold text-zinc-300 mb-2">Up Next</h3>
        {recommendations.map((rec) => (
          <VideoCard key={rec.id} video={rec} layout="compact" />
        ))}
      </aside>

      {/* Save to Playlist Modal */}
      {playlistOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-[#212121] border border-zinc-700 rounded-2xl w-full max-w-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold">Save to Playlist</h3>
              <button type="button" onClick={() => setPlaylistOpen(false)} className="cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            {plMsg && <p className="mb-3 text-xs text-emerald-400">{plMsg}</p>}
            <div className="space-y-2 max-h-48 overflow-y-auto mb-4">
              {myPlaylists.length === 0 ? (
                <p className="text-xs text-zinc-400">You don't have any playlists yet.</p>
              ) : (
                myPlaylists.map((pl) => (
                  <button
                    key={pl.id}
                    type="button"
                    onClick={() => handleAddToPlaylist(pl.id)}
                    className="w-full text-left px-3 py-2 rounded-lg bg-[#2c2c2c] hover:bg-[#3a3a3a] text-sm flex items-center justify-between cursor-pointer"
                  >
                    <span className="truncate">{pl.title}</span>
                    <span className="text-xs text-zinc-400">{pl.videos_count} videos</span>
                  </button>
                ))
              )}
            </div>
            <form onSubmit={handleCreatePlaylistAndAdd} className="flex gap-2">
              <input
                type="text"
                value={newPlTitle}
                onChange={(e) => setNewPlTitle(e.target.value)}
                placeholder="New playlist title..."
                className="flex-1 bg-[#121212] border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              />
              <button
                type="submit"
                className="px-3.5 py-2 rounded-lg bg-[#3ea6ff] text-black text-xs font-semibold cursor-pointer"
              >
                Create
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Report Modal */}
      {reportOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-[#212121] border border-zinc-700 rounded-2xl w-full max-w-md p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold">Report Video</h3>
              <button type="button" onClick={() => setReportOpen(false)} className="cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            {reportMsg && (
              <div className="mb-3 p-2.5 rounded-lg bg-zinc-800 text-xs text-emerald-300">
                {reportMsg}
              </div>
            )}
            <form onSubmit={handleSubmitReport} className="space-y-3">
              <select
                value={reportReason}
                onChange={(e) => setReportReason(e.target.value)}
                className="w-full bg-[#121212] border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              >
                <option value="spam">Spam or misleading</option>
                <option value="harassment">Harassment or hate speech</option>
                <option value="copyright">Copyright infringement</option>
                <option value="inappropriate">Inappropriate content</option>
                <option value="misinformation">Misinformation</option>
                <option value="other">Other</option>
              </select>
              <textarea
                rows={3}
                value={reportDetails}
                onChange={(e) => setReportDetails(e.target.value)}
                placeholder="Additional details for moderators..."
                className="w-full bg-[#121212] border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setReportOpen(false)}
                  className="px-4 py-2 rounded-lg text-xs hover:bg-zinc-700 cursor-pointer"
                >
                  Close
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold cursor-pointer"
                >
                  Submit Report
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Owner Manage & Private Access Grants Modal */}
      {manageOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-[#212121] border border-zinc-700 rounded-2xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold">Manage Video & Private Access</h3>
              <button type="button" onClick={() => setManageOpen(false)} className="cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            {manageMsg && (
              <div className="mb-4 p-2.5 rounded-lg bg-zinc-800 text-xs text-[#3ea6ff]">
                {manageMsg}
              </div>
            )}

            <form onSubmit={handleSaveMeta} className="space-y-3 pb-5 border-b border-zinc-700">
              <div>
                <label className="block text-xs text-zinc-400 mb-1">Title</label>
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="w-full bg-[#121212] border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-400 mb-1">Description</label>
                <textarea
                  rows={3}
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  className="w-full bg-[#121212] border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-400 mb-1">Visibility</label>
                <select
                  value={editVis}
                  onChange={(e) => setEditVis(e.target.value as VideoVisibility)}
                  className="w-full bg-[#121212] border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="public">Public</option>
                  <option value="unlisted">Unlisted</option>
                  <option value="private">Private (ACL restricted)</option>
                </select>
              </div>
              <div className="flex justify-between items-center pt-1">
                <button
                  type="button"
                  onClick={handleDeleteVideo}
                  className="inline-flex items-center gap-1 text-xs text-red-400 hover:text-red-300 cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Delete Video
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-[#3ea6ff] text-black text-xs font-semibold cursor-pointer"
                >
                  Save Changes
                </button>
              </div>
            </form>

            {/* Private Access Control List */}
            <div className="pt-5">
              <div className="flex items-center gap-2 mb-2">
                <Lock className="w-4 h-4 text-amber-400" />
                <h4 className="font-semibold text-sm">Allowed Users (Private Video Access)</h4>
              </div>
              <form onSubmit={handleGrantAdd} className="flex gap-2 mb-3">
                <input
                  type="text"
                  value={grantInput}
                  onChange={(e) => setGrantInput(e.target.value)}
                  placeholder="Enter username or email (e.g. alice)"
                  className="flex-1 bg-[#121212] border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                />
                <button
                  type="submit"
                  className="inline-flex items-center gap-1 px-3.5 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-black text-xs font-semibold cursor-pointer"
                >
                  <UserPlus className="w-3.5 h-3.5" /> Grant
                </button>
              </form>

              <div className="space-y-2 max-h-40 overflow-y-auto">
                {grants.length === 0 ? (
                  <p className="text-xs text-zinc-500">
                    No other users have been granted private access yet.
                  </p>
                ) : (
                  grants.map((g) => (
                    <div
                      key={g.id}
                      className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#181818]"
                    >
                      <div className="flex items-center gap-2.5">
                        <Avatar name={g.channel_name} color={g.avatar_color} size="xs" />
                        <div>
                          <p className="text-xs font-medium">{g.channel_name}</p>
                          <p className="text-[11px] text-zinc-400">@{g.username}</p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleGrantRevoke(g.user_id)}
                        className="text-xs text-red-400 hover:text-red-300 cursor-pointer"
                      >
                        Revoke
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
