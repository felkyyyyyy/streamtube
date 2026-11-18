import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  Film,
  Globe,
  Image as ImageIcon,
  Link2,
  Loader2,
  Lock,
  UploadCloud,
} from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { VideoDetail, VideoVisibility } from '../types';
import { formatFileSize } from '../utils/format';

export const UploadPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [file, setFile] = useState<File | null>(null);
  const [thumbnail, setThumbnail] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('Programming');
  const [tags, setTags] = useState('');
  const [visibility, setVisibility] = useState<VideoVisibility>('public');
  const [allowedUsernames, setAllowedUsernames] = useState('');
  const [categories, setCategories] = useState<string[]>([
    'Programming',
    'Technology',
    'Music',
    'Education',
    'Science',
    'Design',
    'Gaming',
    'Entertainment',
    'General',
  ]);

  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadedVideo, setUploadedVideo] = useState<VideoDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getCategories()
      .then((cats) => setCategories(cats.filter((c) => c !== 'All')))
      .catch(() => {});
  }, []);

  // Poll transcoding status after upload until ready or failed
  useEffect(() => {
    if (!uploadedVideo || uploadedVideo.status === 'ready' || uploadedVideo.status === 'failed') {
      return;
    }
    const timer = setInterval(async () => {
      try {
        const fresh = await api.getVideo(uploadedVideo.id);
        setUploadedVideo(fresh);
      } catch {
        // ignore transient errors
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [uploadedVideo]);

  if (!user) {
    return (
      <div className="max-w-lg mx-auto py-16 text-center bg-[#181818] rounded-2xl border border-zinc-800 p-8">
        <UploadCloud className="w-12 h-12 mx-auto text-zinc-500 mb-3" />
        <h2 className="text-lg font-semibold">Sign in to upload videos</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Create an account or sign in to publish public or private videos.
        </p>
        <Link
          to="/login"
          className="inline-block mt-5 px-6 py-2 rounded-full bg-[#3ea6ff] text-black font-semibold text-sm"
        >
          Sign in
        </Link>
      </div>
    );
  }

  const handleFilePick = (picked: File | null) => {
    if (!picked) return;
    setFile(picked);
    if (!title) {
      setTitle(picked.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' '));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a video file to upload.');
      return;
    }
    setError(null);
    setUploading(true);
    setProgress(0);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title.trim());
    formData.append('description', description.trim());
    formData.append('category', category);
    formData.append('tags', tags.trim());
    formData.append('visibility', visibility);
    if (visibility === 'private' && allowedUsernames.trim()) {
      formData.append('allowed_usernames', allowedUsernames.trim());
    }
    if (thumbnail) {
      formData.append('thumbnail', thumbnail);
    }

    try {
      const video = await api.uploadVideoWithProgress(formData, setProgress);
      setUploadedVideo(video);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  if (uploadedVideo) {
    return (
      <div className="max-w-2xl mx-auto py-8">
        <div className="bg-[#181818] border border-zinc-800 rounded-2xl p-6 sm:p-8 text-center">
          {uploadedVideo.status === 'ready' ? (
            <CheckCircle2 className="w-14 h-14 text-emerald-400 mx-auto mb-3" />
          ) : (
            <Loader2 className="w-14 h-14 text-[#3ea6ff] mx-auto mb-3 animate-spin" />
          )}
          <h1 className="text-2xl font-bold">{uploadedVideo.title}</h1>
          <p className="text-sm text-zinc-400 mt-2">
            {uploadedVideo.status === 'ready'
              ? uploadedVideo.hls_url
                ? 'Video uploaded and transcoded to adaptive HLS!'
                : 'Video uploaded and ready to stream!'
              : 'Upload complete! Background worker is generating thumbnail and HLS stream — you can watch immediately via Range streaming.'}
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 mt-6">
            <button
              type="button"
              onClick={() => navigate(`/watch/${uploadedVideo.id}`)}
              className="px-6 py-2.5 rounded-full bg-[#ff0000] hover:bg-red-700 text-white font-semibold text-sm cursor-pointer"
            >
              Watch Video Now
            </button>
            <button
              type="button"
              onClick={() => {
                setUploadedVideo(null);
                setFile(null);
                setThumbnail(null);
                setTitle('');
                setDescription('');
                setTags('');
                setProgress(0);
              }}
              className="px-5 py-2.5 rounded-full bg-[#272727] hover:bg-[#3f3f3f] text-sm font-medium cursor-pointer"
            >
              Upload Another
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto pb-12">
      <h1 className="text-2xl font-bold mb-1">Upload Video</h1>
      <p className="text-sm text-zinc-400 mb-6">
        Supports MP4, WebM, MOV, MKV up to 500 MB. Videos are automatically processed into adaptive HLS streams.
      </p>

      {error && (
        <div className="mb-5 p-3.5 rounded-xl bg-red-950/60 border border-red-800 text-red-200 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6 bg-[#181818] border border-zinc-800 rounded-2xl p-6">
        {/* Dropzone */}
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            handleFilePick(e.dataTransfer.files?.[0] || null);
          }}
          className={`flex flex-col items-center justify-center border-2 border-dashed rounded-2xl p-8 cursor-pointer transition-all duration-200 ${
            isDragging
              ? 'border-[#3ea6ff] bg-[#3ea6ff]/10 scale-[1.01] shadow-[0_0_30px_-8px_rgba(62,166,255,0.45)]'
              : 'border-zinc-700 hover:border-[#3ea6ff] bg-[#121212]'
          }`}
        >
          <input
            type="file"
            accept="video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov,.mkv"
            className="hidden"
            onChange={(e) => handleFilePick(e.target.files?.[0] || null)}
          />
          {file ? (
            <div className="text-center">
              <Film className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
              <p className="text-sm font-semibold text-white">{file.name}</p>
              <p className="text-xs text-zinc-400 mt-1">{formatFileSize(file.size)} • Click to replace</p>
            </div>
          ) : (
            <div className="text-center">
              <UploadCloud className="w-12 h-12 text-zinc-400 mx-auto mb-2" />
              <p className="text-sm font-semibold">Drag and drop video file here, or click to select</p>
              <p className="text-xs text-zinc-500 mt-1">MP4, WebM, MOV, MKV • Max 500 MB</p>
            </div>
          )}
        </label>

        {/* Metadata */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">Title *</label>
            <input
              type="text"
              required
              maxLength={150}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Give your video a descriptive title"
              className="w-full px-3.5 py-2.5 rounded-xl bg-[#121212] border border-zinc-700 text-sm focus:outline-none focus:border-[#3ea6ff]"
            />
          </div>

          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">Description</label>
            <textarea
              rows={4}
              maxLength={5000}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Tell viewers about your video..."
              className="w-full px-3.5 py-2.5 rounded-xl bg-[#121212] border border-zinc-700 text-sm focus:outline-none focus:border-[#3ea6ff]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-[#121212] border border-zinc-700 text-sm focus:outline-none focus:border-[#3ea6ff]"
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">
              Tags (comma separated)
            </label>
            <input
              type="text"
              maxLength={300}
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="fastapi, python, tutorial"
              className="w-full px-3.5 py-2.5 rounded-xl bg-[#121212] border border-zinc-700 text-sm focus:outline-none focus:border-[#3ea6ff]"
            />
          </div>
        </div>

        {/* Custom Thumbnail */}
        <div>
          <label className="block text-xs font-medium text-zinc-300 mb-1.5">
            Custom Thumbnail (optional — auto-extracted via FFmpeg if omitted)
          </label>
          <label className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#272727] hover:bg-[#3f3f3f] text-xs font-medium cursor-pointer">
            <ImageIcon className="w-4 h-4" />
            <span>{thumbnail ? thumbnail.name : 'Choose JPG / PNG / WebP'}</span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => setThumbnail(e.target.files?.[0] || null)}
            />
          </label>
        </div>

        {/* Visibility */}
        <div>
          <label className="block text-xs font-medium text-zinc-300 mb-2">Visibility</label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              {
                val: 'public' as const,
                icon: Globe,
                title: 'Public',
                desc: 'Everyone can search and watch',
              },
              {
                val: 'unlisted' as const,
                icon: Link2,
                title: 'Unlisted',
                desc: 'Anyone with direct link can watch',
              },
              {
                val: 'private' as const,
                icon: Lock,
                title: 'Private',
                desc: 'Only you & explicitly allowed users',
              },
            ].map((opt) => {
              const Icon = opt.icon;
              const selected = visibility === opt.val;
              return (
                <button
                  key={opt.val}
                  type="button"
                  onClick={() => setVisibility(opt.val)}
                  className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                    selected
                      ? 'border-[#3ea6ff] bg-[#3ea6ff]/10'
                      : 'border-zinc-700 bg-[#121212] hover:border-zinc-500'
                  }`}
                >
                  <div className="flex items-center gap-2 font-semibold text-sm">
                    <Icon className="w-4 h-4" /> {opt.title}
                  </div>
                  <p className="text-xs text-zinc-400 mt-1">{opt.desc}</p>
                </button>
              );
            })}
          </div>
        </div>

        {visibility === 'private' && (
          <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-700/50">
            <label className="block text-xs font-semibold text-amber-300 mb-1.5">
              Grant Private Access (usernames or emails, comma separated)
            </label>
            <input
              type="text"
              value={allowedUsernames}
              onChange={(e) => setAllowedUsernames(e.target.value)}
              placeholder="alice, bob"
              className="w-full px-3.5 py-2 rounded-lg bg-[#121212] border border-zinc-700 text-sm focus:outline-none focus:border-amber-400"
            />
            <p className="text-[11px] text-zinc-400 mt-1.5">
              You can also add or revoke individual users anytime from the video watch page.
            </p>
          </div>
        )}

        {/* Progress Bar */}
        {uploading && (
          <div className="space-y-2 animate-fade-in">
            <div className="flex items-center justify-between text-xs font-medium">
              <span className="text-[#3ea6ff]">Uploading video to storage...</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full h-2.5 rounded-full bg-zinc-800 overflow-hidden">
              <div
                className="h-full progress-sheen transition-all duration-200 ease-out rounded-full"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={uploading || !file}
            className="px-6 py-2.5 rounded-full bg-[#ff0000] hover:bg-red-700 disabled:opacity-50 text-white font-semibold text-sm flex items-center gap-2 cursor-pointer"
          >
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
            <span>{uploading ? `Uploading (${progress}%)...` : 'Publish Video'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
