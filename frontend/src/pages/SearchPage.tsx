import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, SlidersHorizontal } from 'lucide-react';
import { api } from '../api/client';
import { VideoCard } from '../components/VideoCard';
import type { VideoCardItem } from '../types';

export const SearchPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const q = searchParams.get('q') || '';
  const [sort, setSort] = useState<'newest' | 'popular' | 'oldest'>('newest');
  const [videos, setVideos] = useState<VideoCardItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .listVideos({ q, sort, page_size: 30 })
      .then((res) => {
        if (active) {
          setVideos(res.items);
          setTotal(res.total);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [q, sort]);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 mb-6 border-b border-zinc-800">
        <div>
          <h1 className="text-lg font-semibold">
            Search results for <span className="text-[#3ea6ff]">"{q}"</span>
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">{total} matching videos</p>
        </div>
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4 text-zinc-400" />
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as 'newest' | 'popular' | 'oldest')}
            className="bg-[#272727] text-sm rounded-lg px-3 py-1.5 border border-zinc-700 focus:outline-none cursor-pointer"
          >
            <option value="newest">Upload date (newest)</option>
            <option value="popular">View count</option>
            <option value="oldest">Upload date (oldest)</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="space-y-5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex gap-4 animate-pulse">
              <div className="w-[360px] aspect-video bg-zinc-800 rounded-xl shrink-0" />
              <div className="flex-1 space-y-3 py-2">
                <div className="h-5 bg-zinc-800 rounded w-3/4" />
                <div className="h-3 bg-zinc-800 rounded w-1/3" />
                <div className="h-3 bg-zinc-800 rounded w-5/6" />
              </div>
            </div>
          ))}
        </div>
      ) : videos.length === 0 ? (
        <div className="text-center py-20 bg-[#181818] rounded-2xl border border-zinc-800">
          <Search className="w-10 h-10 mx-auto text-zinc-600 mb-3" />
          <h3 className="text-base font-medium">No matching videos</h3>
          <p className="text-sm text-zinc-400 mt-1">
            Try different keywords or browse categories on the Home feed.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {videos.map((v) => (
            <VideoCard key={v.id} video={v} layout="horizontal" />
          ))}
        </div>
      )}
    </div>
  );
};
