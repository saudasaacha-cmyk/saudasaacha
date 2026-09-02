"use client";

import { useRef, useState } from "react";
import { Play } from "lucide-react";

/** Video with a custom centered play button over the thumbnail.
 *  Click to play; when paused/ended the thumbnail + play button return. */
export function HeroVideo({ src, poster }: { src: string; poster: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);

  return (
    <div className="relative overflow-hidden rounded-3xl border border-mp-border bg-black shadow-xl shadow-mp-primary/10">
      <video
        ref={ref}
        className="block aspect-video w-full object-cover"
        src={src}
        poster={poster}
        playsInline
        controls={playing}
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
      />

      {!playing && (
        <button
          type="button"
          onClick={() => ref.current?.play()}
          aria-label="Play video"
          className="absolute inset-0 grid place-items-center bg-cover bg-center"
          style={{ backgroundImage: `url(${poster})` }}
        >
          <span className="grid size-20 place-items-center rounded-full bg-mp-primary text-white shadow-lg shadow-mp-primary/40 ring-4 ring-white/20 transition-transform duration-200 hover:scale-105">
            <Play className="size-8 translate-x-0.5 fill-current" />
          </span>
        </button>
      )}
    </div>
  );
}
