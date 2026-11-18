import React from 'react';
import { Link } from 'react-router-dom';
import { EyeOff, Globe, Link2, Lock, Play } from 'lucide-react';
import type { VideoCardItem } from '../types';
import { formatDuration, formatRelativeTime, formatViews } from '../utils/format';
import { Avatar } from './Avatar';

interface VideoCardProps {
  video: VideoCardItem;
  layout?: 'grid' | 'horizontal' | 'compact';
  index?: number;
}

const CATEGORY_GRADIENTS: Record<string, string> = {
  Programming: 'from-blue-950/90 via-indigo-950/80 to-zinc-950',
  Technology: 'from-cyan-950/90 via-slate-900 to-zinc-950',
  Music: 'from-purple-950/90 via-fuchsia-950/70 to-zinc-950',
  Design: 'from-rose-950/90 via-pink-950/70 to-zinc-950',
  Education: 'from-amber-950/85 via-orange-950/60 to-zinc-950',
  Science: 'from-emerald-950/90 via-teal-950/70 to-zinc-950',
  Gaming: 'from-violet-950/90 via-indigo-950/70 to-zinc-950',
  Entertainment: 'from-red-950/90 via-rose-950/70 to-zinc-950',
};

const VisibilityBadge: React.FC<{ visibility: string; moderationStatus: string }> = ({
  visibility,
  moderationStatus,
}) => {
  if (moderationStatus === 'hidden') {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-red-600/90 backdrop-blur-sm text-[11px] font-medium text-white shadow">
        <EyeOff className="w-3 h-3" /> Hidden
      </span>
    );
  }
  if (visibility === 'private') {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-600/90 backdrop-blur-sm text-[11px] font-medium text-white shadow">
        <Lock className="w-3 h-3" /> Private
      </span>
    );
  }
  if (visibility === 'unlisted') {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-zinc-700/90 backdrop-blur-sm text-[11px] font-medium text-zinc-100 shadow">
        <Link2 className="w-3 h-3" /> Unlisted
      </span>
    );
  }
  return null;
};

const ThumbnailBox: React.FC<{ video: VideoCardItem; className?: string }> = ({
  video,
  className = '',
}) => {
  const grad = CATEGORY_GRADIENTS[video.category] || 'from-zinc-800 via-zinc-900 to-zinc-950';
  return (
    <div
      className={`relative aspect-video bg-zinc-900 rounded-xl overflow-hidden border border-white/[0.04] group-hover:border-white/15 group-hover:rounded-lg group-hover:shadow-[0_10px_30px_-10px_rgba(0,0,0,0.85)] transition-all duration-300 ease-out ${className}`}
    >
      {video.thumbnail_url ? (
        <img
          src={video.thumbnail_url}
          alt={video.title}
          loading="lazy"
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 ease-out"
        />
      ) : (
        <div
          className={`w-full h-full flex flex-col items-center justify-center gap-2 bg-gradient-to-br ${grad} text-zinc-300`}
        >
          <div className="w-12 h-12 rounded-full bg-white/10 backdrop-blur-sm border border-white/15 flex items-center justify-center group-hover:scale-110 group-hover:bg-[#ff0000]/90 group-hover:border-red-400/50 transition-all duration-300 ease-out shadow-lg">
            <Play className="w-5 h-5 fill-current text-white ml-0.5" />
          </div>
          <span className="text-[11px] uppercase tracking-widest opacity-75 font-medium">
            {video.category}
          </span>
        </div>
      )}

      {/* Subtle hover play overlay for image thumbnails */}
      {video.thumbnail_url && (
        <div className="pointer-events-none absolute inset-0 bg-black/0 group-hover:bg-black/25 transition-colors duration-300 flex items-center justify-center">
          <div className="w-12 h-12 rounded-full bg-black/75 backdrop-blur-sm border border-white/20 flex items-center justify-center opacity-0 scale-75 group-hover:opacity-100 group-hover:scale-100 transition-all duration-300 ease-out shadow-xl">
            <Play className="w-5 h-5 fill-current text-white ml-0.5" />
          </div>
        </div>
      )}

      <div className="absolute top-2 left-2 flex gap-1">
        <VisibilityBadge visibility={video.visibility} moderationStatus={video.moderation_status} />
        {video.status === 'processing' && (
          <span className="px-1.5 py-0.5 rounded bg-blue-600/90 backdrop-blur-sm text-[11px] font-medium text-white animate-pulse">
            Processing
          </span>
        )}
      </div>

      {video.duration_seconds > 0 && (
        <span className="absolute bottom-1.5 right-1.5 px-1.5 py-0.5 rounded bg-black/85 backdrop-blur-sm text-white text-xs font-medium tracking-tight group-hover:bg-black transition-colors duration-200">
          {formatDuration(video.duration_seconds)}
        </span>
      )}
    </div>
  );
};

export const VideoCard: React.FC<VideoCardProps> = ({ video, layout = 'grid', index = 0 }) => {
  const animStyle = { animationDelay: `${Math.min(index * 45, 360)}ms` };

  if (layout === 'compact') {
    return (
      <Link
        to={`/watch/${video.id}`}
        style={animStyle}
        className="group flex gap-2.5 items-start p-1.5 -m-1.5 rounded-xl hover:bg-white/[0.04] transition-colors duration-200 animate-fade-up"
      >
        <ThumbnailBox video={video} className="w-40 shrink-0" />
        <div className="min-w-0 flex-1 py-0.5">
          <h4 className="text-sm font-medium text-[#f1f1f1] line-clamp-2 leading-snug group-hover:text-white transition-colors">
            {video.title}
          </h4>
          <p className="text-xs text-[#aaaaaa] mt-1 truncate group-hover:text-zinc-300 transition-colors">
            {video.owner.channel_name}
          </p>
          <p className="text-xs text-[#aaaaaa] mt-0.5">
            {formatViews(video.views_count)} views • {formatRelativeTime(video.created_at)}
          </p>
        </div>
      </Link>
    );
  }

  if (layout === 'horizontal') {
    return (
      <div
        style={animStyle}
        className="group flex flex-col sm:flex-row gap-4 p-2 -m-2 rounded-2xl hover:bg-white/[0.03] transition-colors duration-200 animate-fade-up"
      >
        <Link to={`/watch/${video.id}`} className="sm:w-[360px] shrink-0 block">
          <ThumbnailBox video={video} />
        </Link>
        <div className="min-w-0 flex-1 py-1">
          <Link to={`/watch/${video.id}`}>
            <h3 className="text-lg font-medium text-[#f1f1f1] line-clamp-2 leading-snug group-hover:text-white transition-colors">
              {video.title}
            </h3>
          </Link>
          <p className="text-xs text-[#aaaaaa] mt-1">
            {formatViews(video.views_count)} views • {formatRelativeTime(video.created_at)}
          </p>
          <Link
            to={`/channel/${video.owner.username}`}
            className="inline-flex items-center gap-2 my-3 text-xs text-[#aaaaaa] hover:text-white transition-colors"
          >
            <Avatar name={video.owner.channel_name} color={video.owner.avatar_color} size="xs" />
            <span>{video.owner.channel_name}</span>
          </Link>
          {video.description && (
            <p className="text-xs text-[#aaaaaa] line-clamp-2 leading-relaxed">
              {video.description}
            </p>
          )}
          <div className="flex items-center gap-2 mt-2">
            <span className="text-[11px] px-2 py-0.5 rounded bg-[#272727] text-zinc-300">
              {video.category}
            </span>
            {video.visibility === 'public' && (
              <span className="inline-flex items-center gap-1 text-[11px] text-zinc-500">
                <Globe className="w-3 h-3" /> Public
              </span>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      style={animStyle}
      className="group flex flex-col animate-fade-up hover:-translate-y-1 transition-transform duration-300 ease-out"
    >
      <Link to={`/watch/${video.id}`} className="block">
        <ThumbnailBox video={video} />
      </Link>
      <div className="flex gap-3 mt-3 pr-2">
        <Link
          to={`/channel/${video.owner.username}`}
          className="shrink-0 mt-0.5 hover:scale-105 transition-transform duration-200"
        >
          <Avatar name={video.owner.channel_name} color={video.owner.avatar_color} size="md" />
        </Link>
        <div className="min-w-0 flex-1">
          <Link to={`/watch/${video.id}`}>
            <h3 className="text-[15px] font-medium text-[#f1f1f1] line-clamp-2 leading-snug group-hover:text-white transition-colors">
              {video.title}
            </h3>
          </Link>
          <Link
            to={`/channel/${video.owner.username}`}
            className="block text-[13px] text-[#aaaaaa] hover:text-[#f1f1f1] mt-1 truncate transition-colors"
          >
            {video.owner.channel_name}
          </Link>
          <p className="text-[13px] text-[#aaaaaa]">
            {formatViews(video.views_count)} views • {formatRelativeTime(video.created_at)}
          </p>
        </div>
      </div>
    </div>
  );
};
