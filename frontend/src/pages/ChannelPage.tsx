import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Calendar, Film, ListVideo, Plus, Trash2, Users } from 'lucide-react';
import { api } from '../api/client';
import { Avatar } from '../components/Avatar';
import { VideoCard } from '../components/VideoCard';
import { useAuth } from '../context/AuthContext';
import type { ChannelProfile, PlaylistDetail, PlaylistSummary, VideoCardItem } from '../types';

export const ChannelPage: React.FC = () => {
  const { handle } = useParams<{ handle: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [channel, setChannel] = useState<ChannelProfile | null>(null);
  const [videos, setVideos] = useState<VideoCardItem[]>([]);
  const [playlists, setPlaylists] = useState<PlaylistSummary[]>([]);
  const [activePlaylist, setActivePlaylist] = useState<PlaylistDetail | null>(null);
  const [tab, setTab] = useState<'videos' | 'playlists' | 'about'>('videos');
  const [loading, setLoading] = useState(true);

  const [newPlTitle, setNewPlTitle] = useState('');
  const [newPlDesc, setNewPlDesc] = useState('');

  useEffect(() => {
    if (!handle) return;
    let active = true;
    setLoading(true);
    setActivePlaylist(null);
    Promise.all([
      api.getChannel(handle),
      api.getChannelVideos(handle),
      api.listPlaylists({ channel: handle }),
    ])
      .then(([ch, vids, pls]) => {
        if (active) {
          setChannel(ch);
          setVideos(vids);
          setPlaylists(pls);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [handle, user]);

  const handleSubscribe = async () => {
    if (!user) return navigate('/login');
    if (!channel) return;
    const res = await api.toggleSubscribe(channel.id);
    setChannel({
      ...channel,
      is_subscribed: res.subscribed,
      subscribers_count: res.subscribers_count,
    });
  };

  const handleCreatePlaylist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlTitle.trim()) return;
    const pl = await api.createPlaylist({
      title: newPlTitle.trim(),
      description: newPlDesc.trim(),
      visibility: 'public',
    });
    setPlaylists((prev) => [pl, ...prev]);
    setNewPlTitle('');
    setNewPlDesc('');
  };

  const handleOpenPlaylist = async (plId: string) => {
    const detail = await api.getPlaylist(plId);
    setActivePlaylist(detail);
  };

  const handleDeletePlaylist = async (plId: string) => {
    if (!window.confirm('Delete this playlist?')) return;
    await api.deletePlaylist(plId);
    setPlaylists((prev) => prev.filter((p) => p.id !== plId));
    if (activePlaylist?.id === plId) setActivePlaylist(null);
  };

  if (loading) {
    return <div className="max-w-6xl mx-auto h-64 bg-zinc-900 rounded-2xl animate-pulse" />;
  }

  if (!channel) {
    return (
      <div className="max-w-lg mx-auto py-16 text-center">
        <h2 className="text-xl font-bold">Channel not found</h2>
        <Link to="/" className="text-sm text-[#3ea6ff] mt-3 inline-block">
          Go Home
        </Link>
      </div>
    );
  }

  const isOwner = user?.id === channel.id;

  return (
    <div className="max-w-[1400px] mx-auto">
      {/* Banner */}
      <div
        style={{ background: `linear-gradient(135deg, ${channel.banner_color}, #0f0f0f)` }}
        className="h-36 sm:h-48 rounded-2xl border border-zinc-800/80 mb-6"
      />

      {/* Profile Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-zinc-800">
        <div className="flex items-center gap-5">
          <Avatar name={channel.channel_name} color={channel.avatar_color} size="xl" />
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold">{channel.channel_name}</h1>
            <p className="text-sm text-zinc-400 mt-1">
              @{channel.username} • {channel.subscribers_count} subscriber
              {channel.subscribers_count === 1 ? '' : 's'} • {channel.videos_count} video
              {channel.videos_count === 1 ? '' : 's'}
            </p>
            {channel.channel_description && (
              <p className="text-sm text-zinc-300 mt-2 max-w-2xl line-clamp-2">
                {channel.channel_description}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isOwner ? (
            <Link
              to="/upload"
              className="px-5 py-2 rounded-full bg-[#ff0000] hover:bg-red-700 text-white text-sm font-semibold"
            >
              Upload Video
            </Link>
          ) : (
            <button
              type="button"
              onClick={handleSubscribe}
              className={`px-6 py-2.5 rounded-full text-sm font-semibold transition-colors cursor-pointer ${
                channel.is_subscribed
                  ? 'bg-[#272727] hover:bg-[#3f3f3f] text-white'
                  : 'bg-white hover:bg-zinc-200 text-black'
              }`}
            >
              {channel.is_subscribed ? 'Subscribed' : 'Subscribe'}
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-6 border-b border-zinc-800 mb-6">
        {(
          [
            { key: 'videos', label: `Videos (${videos.length})` },
            { key: 'playlists', label: `Playlists (${playlists.length})` },
            { key: 'about', label: 'About' },
          ] as const
        ).map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => {
              setTab(t.key);
              setActivePlaylist(null);
            }}
            className={`py-3 text-sm font-semibold border-b-2 transition-colors cursor-pointer ${
              tab === t.key
                ? 'border-white text-white'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'videos' &&
        (videos.length === 0 ? (
          <div className="py-16 text-center text-zinc-400 bg-[#181818] rounded-2xl border border-zinc-800">
            <Film className="w-10 h-10 mx-auto text-zinc-600 mb-2" />
            <p>This channel hasn't uploaded any videos yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-8">
            {videos.map((v, idx) => (
              <VideoCard key={v.id} video={v} layout="grid" index={idx} />
            ))}
          </div>
        ))}

      {tab === 'playlists' && (
        <div className="space-y-6">
          {isOwner && (
            <form
              onSubmit={handleCreatePlaylist}
              className="p-4 rounded-xl bg-[#181818] border border-zinc-800 flex flex-wrap items-center gap-3"
            >
              <input
                type="text"
                required
                value={newPlTitle}
                onChange={(e) => setNewPlTitle(e.target.value)}
                placeholder="New playlist title"
                className="flex-1 min-w-[200px] bg-[#121212] border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              />
              <input
                type="text"
                value={newPlDesc}
                onChange={(e) => setNewPlDesc(e.target.value)}
                placeholder="Description (optional)"
                className="flex-1 min-w-[200px] bg-[#121212] border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              />
              <button
                type="submit"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#3ea6ff] text-black text-sm font-semibold cursor-pointer"
              >
                <Plus className="w-4 h-4" /> Create Playlist
              </button>
            </form>
          )}

          {activePlaylist ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between bg-[#181818] border border-zinc-800 rounded-xl p-4">
                <div>
                  <button
                    type="button"
                    onClick={() => setActivePlaylist(null)}
                    className="text-xs text-[#3ea6ff] hover:underline mb-1 cursor-pointer"
                  >
                    ← Back to all playlists
                  </button>
                  <h3 className="text-lg font-bold">{activePlaylist.title}</h3>
                  {activePlaylist.description && (
                    <p className="text-xs text-zinc-400 mt-0.5">{activePlaylist.description}</p>
                  )}
                </div>
                {isOwner && (
                  <button
                    type="button"
                    onClick={() => handleDeletePlaylist(activePlaylist.id)}
                    className="inline-flex items-center gap-1 text-xs text-red-400 hover:text-red-300 cursor-pointer"
                  >
                    <Trash2 className="w-4 h-4" /> Delete
                  </button>
                )}
              </div>
              {activePlaylist.videos.length === 0 ? (
                <p className="text-sm text-zinc-400">No videos in this playlist yet.</p>
              ) : (
                <div className="space-y-4">
                  {activePlaylist.videos.map((v) => (
                    <VideoCard key={v.id} video={v} layout="horizontal" />
                  ))}
                </div>
              )}
            </div>
          ) : playlists.length === 0 ? (
            <div className="py-16 text-center text-zinc-400 bg-[#181818] rounded-2xl border border-zinc-800">
              <ListVideo className="w-10 h-10 mx-auto text-zinc-600 mb-2" />
              <p>No playlists yet.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {playlists.map((pl) => (
                <div
                  key={pl.id}
                  onClick={() => handleOpenPlaylist(pl.id)}
                  className="group cursor-pointer rounded-xl overflow-hidden bg-[#181818] border border-zinc-800 hover:border-zinc-600 transition-colors"
                >
                  <div className="relative aspect-video bg-zinc-900">
                    {pl.cover_thumbnail_url ? (
                      <img
                        src={pl.cover_thumbnail_url}
                        alt={pl.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-zinc-600">
                        <ListVideo className="w-10 h-10" />
                      </div>
                    )}
                    <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/80 text-xs font-medium flex items-center gap-1">
                      <ListVideo className="w-3.5 h-3.5" /> {pl.videos_count} videos
                    </div>
                  </div>
                  <div className="p-3.5">
                    <h3 className="font-semibold text-sm group-hover:text-white">{pl.title}</h3>
                    {pl.description && (
                      <p className="text-xs text-zinc-400 mt-1 line-clamp-2">{pl.description}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'about' && (
        <div className="max-w-2xl bg-[#181818] border border-zinc-800 rounded-2xl p-6 space-y-4">
          <h3 className="font-bold">About {channel.channel_name}</h3>
          <p className="text-sm text-zinc-300 whitespace-pre-wrap">
            {channel.channel_description || 'No channel description added yet.'}
          </p>
          <div className="pt-4 border-t border-zinc-800 flex flex-wrap gap-6 text-xs text-zinc-400">
            <span className="inline-flex items-center gap-1.5">
              <Users className="w-4 h-4" /> {channel.subscribers_count} subscribers
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Film className="w-4 h-4" /> {channel.videos_count} videos
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Calendar className="w-4 h-4" /> Joined{' '}
              {new Date(channel.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
