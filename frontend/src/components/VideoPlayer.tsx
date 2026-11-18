import React, { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';
import { Radio } from 'lucide-react';

interface VideoPlayerProps {
  hlsUrl: string | null;
  streamUrl: string | null;
  posterUrl: string | null;
  title: string;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  hlsUrl,
  streamUrl,
  posterUrl,
  title,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [mode, setMode] = useState<'hls' | 'range'>('range');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const el = videoRef.current;
    if (!el) return;
    setError(null);

    let hls: Hls | null = null;

    const attachFallback = () => {
      if (streamUrl) {
        setMode('range');
        el.src = streamUrl;
      } else {
        setError('Media stream unavailable');
      }
    };

    if (hlsUrl && Hls.isSupported()) {
      setMode('hls');
      hls = new Hls({
        enableWorker: true,
        lowLatencyMode: false,
      });
      hls.loadSource(hlsUrl);
      hls.attachMedia(el);
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          hls?.destroy();
          hls = null;
          attachFallback();
        }
      });
    } else if (hlsUrl && el.canPlayType('application/vnd.apple.mpegurl')) {
      setMode('hls');
      el.src = hlsUrl;
    } else {
      attachFallback();
    }

    return () => {
      if (hls) {
        hls.destroy();
      }
    };
  }, [hlsUrl, streamUrl]);

  return (
    <div className="relative w-full aspect-video bg-black rounded-xl overflow-hidden shadow-2xl border border-zinc-800/80">
      <video
        ref={videoRef}
        controls
        playsInline
        poster={posterUrl || undefined}
        aria-label={title}
        className="w-full h-full object-contain bg-black"
        onError={() => {
          if (mode === 'hls' && streamUrl && videoRef.current) {
            setMode('range');
            videoRef.current.src = streamUrl;
          } else {
            setError('Unable to decode video stream.');
          }
        }}
      />

      <div className="pointer-events-none absolute top-3 right-3 flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-black/70 text-[11px] font-medium text-zinc-200 border border-white/10">
        <Radio className={`w-3 h-3 ${mode === 'hls' ? 'text-emerald-400' : 'text-sky-400'}`} />
        <span>{mode === 'hls' ? 'HLS Adaptive' : 'HTTP Range'}</span>
      </div>

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/80 text-sm text-red-400 p-4 text-center">
          {error}
        </div>
      )}
    </div>
  );
};
