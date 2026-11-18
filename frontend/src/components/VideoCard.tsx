import React from 'react';
import { Link } from 'react-router-dom';
import { EyeOff, Globe, Link2, Lock, Play } from 'lucide-react';
import type { VideoCardItem } from '../types';
import { formatDuration, formatRelativeTime, formatViews } from '../utils/format';
import { Avatar } from './Avatar';

interface VideoCardProps {
  video: VideoCardItem;
  layout?: 'grid' | 'horizontal' | 'compact';
}

const VisibilityBadge: React.FC<{ visibility: string; moderationStatus: string }> = ({
  visibility,
  moderationStatus,
}) => {
  if (moderationStatus === 'hidden') {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-red-600/90 text-[11px] font-medium text-white">
        <EyeOff className="w-3 h-3" /> Hidden
      </span>
    );
  }
  if (visibility === 'private') {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-600/90 text-[11px] font-medium text-white">
        <Lock className="w-3 h-3" /> Private
      </span>
    );
  }
  if (visibility === 'unlisted') {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-zinc-700/90 text-[11px] font-medium text-zinc-100">
        <Link2 className="w-3 h-3" /> Unlisted
      </span>
    );
  }
  return null;
};

const ThumbnailBox: React.FC<{ video: VideoCardItem; className?: string }> = ({
  video,
  className = '',
}) => (
  <div
    className={`relative aspect-video bg-zinc-900 rounded-xl overflow-hidden group-hover:rounded-md transition-all duration-200 ${className}`}
  >
    {video.thumbnail_url ? (
      <img
        src={video.thumbnail_url}
        alt={video.title}
        loading="lazy"
        className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-300"
      />
    ) : (
      <div
        className="w-full h-full flex flex-col items-center justify-center gap-2 bg-gradient-to-br from-zinc-800 to-zinc-950 text-zinc-400"
      >
        <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center">
          <Play className="w-6 h-6 fill-current text-white/80 ml-0.5" />
        </div>
        <span className="text-xs uppercase tracking-wider opacity-70">{video.category}</span>
      </div>
    )}

    <div className="absolute top-2 left-2 flex gap-1">
      <VisibilityBadge visibility={video.visibility} moderationStatus={video.moderation_status} />
      {video.status === 'processing' && (
        <span className="px-1.5 py-0.5 rounded bg-blue-600/90 text-[11px] font-medium text-white">
          Processing
        </span>
      )}
    </div>

    {video.duration_seconds > 0 && (
      <span className="absolute bottom-1.5 right-1.5 px-1.5 py-0.5 rounded bg-black/85 text-white text-xs font-medium tracking-tight">
        {formatDuration(video.duration_seconds)}
      </span>
    )}
  </div>
);

export const VideoCard: React.FC<VideoCardProps> = ({ video, layout = 'grid' }) => {
  if (layout === 'compact') {
    return (
      <Link to={`/watch/${video.id}`} className="group flex gap-2.5 items-start">
        <ThumbnailBox video={video} className="w-40 shrink-0" />
        <div className="min-w-0 flex-1 py-0.5">
          <h4 className="text-sm font-medium text-[#f1f1f1] line-clamp-2 leading-snug group-hover:text-white">
            {video.title}
          </h4>
          <p className="text-xs text-[#aaaaaa] mt-1 truncate hover:text-white">
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
      <div className="group flex flex-col sm:flex-row gap-4">
        <Link to={`/watch/${video.id}`} className="sm:w-[360px] shrink-0 block">
          <ThumbnailBox video={video} />
        </Link>
        <div className="min-w-0 flex-1 py-1">
          <Link to={`/watch/${video.id}`}>
            <h3 className="text-lg font-medium text-[#f1f1f1] line-clamp-2 leading-snug group-hover:text-white">
              {video.title}
            </h3>
          </Link>
          <p className="text-xs text-[#aaaaaa] mt-1">
            {formatViews(video.views_count)} views • {formatRelativeTime(video.created_at)}
          </p>
          <Link
            to={`/channel/${video.owner.username}`}
            className="inline-flex items-center gap-2 my-3 text-xs text-[#aaaaaa] hover:text-white"
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
    <div className="group flex flex-col">
      <Link to={`/watch/${video.id}`} className="block">
        <ThumbnailBox video={video} />
      </Link>
      <div className="flex gap-3 mt-3 pr-2">
        <Link to={`/channel/${video.owner.username}`} className="shrink-0 mt-0.5">
          <Avatar name={video.owner.channel_name} color={video.owner.avatar_color} size="md" />
        </Link>
        <div className="min-w-0 flex-1">
          <Link to={`/watch/${video.id}`}>
            <h3 className="text-[15px] font-medium text-[#f1f1f1] line-clamp-2 leading-snug group-hover:text-white">
              {video.title}
            </h3>
          </Link>
          <Link
            to={`/channel/${video.owner.username}`}
            className="block text-[13px] text-[#aaaaaa] hover:text-[#f1f1f1] mt-1 truncate"
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
