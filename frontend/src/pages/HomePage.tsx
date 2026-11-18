import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Film, FolderLock, PlaySquare, Tv, Upload } from 'lucide-react';
import { api } from '../api/client';
import { VideoCard } from '../components/VideoCard';
import { useAuth } from '../context/AuthContext';
import type { VideoCardItem } from '../types';

interface HomePageProps {
  feed?: 'all' | 'subscriptions' | 'mine' | 'shared';
}

const FEED_META = {
  all: { title: null, subtitle: null, icon: Film },
  subscriptions: {
    title: 'Subscriptions',
    subtitle: 'Latest uploads from channels you subscribe to',
    icon: Tv,
  },
  mine: {
    title: 'My Videos (Creator Studio)',
    subtitle: 'Manage your public, unlisted, and private uploads',
    icon: PlaySquare,
  },
  shared: {
    title: 'Shared With Me',
    subtitle: 'Private videos owners have explicitly granted you access to view',
    icon: FolderLock,
  },
};

export const HomePage: React.FC<HomePageProps> = ({ feed = 'all' }) => {
  const { user } = useAuth();
  const [videos, setVideos] = useState<VideoCardItem[]>([]);
  const [categories, setCategories] = useState<string[]>(['All']);
  const [category, setCategory] = useState('All');
  const [sort, setSort] = useState<'newest' | 'popular'>('newest');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    api
      .listVideos({
        feed,
        category: category === 'All' ? undefined : category,
        sort,
        page_size: 24,
      })
      .then((res) => {
        if (active) setVideos(res.items);
      })
      .catch((err) => {
        if (active) setError(err.message || 'Failed to load videos');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [feed, category, sort, user]);

  const meta = FEED_META[feed];
  const HeaderIcon = meta.icon;

  return (
    <div className="max-w-[1800px] mx-auto">
      {meta.title && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[#272727] text-white">
              <HeaderIcon className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold">{meta.title}</h1>
              <p className="text-xs text-zinc-400">{meta.subtitle}</p>
            </div>
          </div>
          {feed === 'mine' && (
            <Link
              to="/upload"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#ff0000] hover:bg-red-700 text-sm font-semibold text-white transition-colors"
            >
              <Upload className="w-4 h-4" /> Upload Video
            </Link>
          )}
        </div>
      )}

      {/* Category Chips + Sort */}
      <div className="flex items-center justify-between gap-3 mb-6">
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
          {categories.map((cat) => {
            const active = category === cat;
            return (
              <button
                key={cat}
                type="button"
                onClick={() => setCategory(cat)}
                className={`px-3.5 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors cursor-pointer ${
                  active
                    ? 'bg-[#f1f1f1] text-[#0f0f0f]'
                    : 'bg-[#272727] text-[#f1f1f1] hover:bg-[#3f3f3f]'
                }`}
              >
                {cat}
              </button>
            );
          })}
        </div>

        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as 'newest' | 'popular')}
          className="bg-[#272727] text-sm text-[#f1f1f1] rounded-lg px-3 py-1.5 border border-zinc-700 focus:outline-none focus:border-[#3ea6ff] shrink-0 cursor-pointer"
        >
          <option value="newest">Newest</option>
          <option value="popular">Most viewed</option>
        </select>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/50 border border-red-800 text-red-200 text-sm mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-8">
          {Array.from({ length: 8 }).map((_, idx) => (
            <div key={idx} className="animate-pulse">
              <div className="aspect-video bg-zinc-800 rounded-xl" />
              <div className="flex gap-3 mt-3">
                <div className="w-9 h-9 rounded-full bg-zinc-800 shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-zinc-800 rounded w-5/6" />
                  <div className="h-3 bg-zinc-800 rounded w-1/2" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : videos.length === 0 ? (
        <div className="text-center py-20 bg-[#181818] rounded-2xl border border-zinc-800/80">
          <Film className="w-12 h-12 mx-auto text-zinc-600 mb-3" />
          <h3 className="text-lg font-semibold text-zinc-200">No videos found</h3>
          <p className="text-sm text-zinc-400 mt-1 max-w-md mx-auto">
            {feed === 'subscriptions'
              ? 'Subscribe to channels to see their latest videos here.'
              : feed === 'shared'
                ? 'When a creator grants you access to a private video, it will appear here.'
                : 'Try selecting a different category or upload your first video.'}
          </p>
          {user && (
            <Link
              to="/upload"
              className="inline-flex items-center gap-2 mt-5 px-5 py-2 rounded-full bg-[#ff0000] hover:bg-red-700 text-sm font-medium text-white"
            >
              <Upload className="w-4 h-4" /> Upload Video
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-8">
          {videos.map((v) => (
            <VideoCard key={v.id} video={v} layout="grid" />
          ))}
        </div>
      )}
    </div>
  );
};
