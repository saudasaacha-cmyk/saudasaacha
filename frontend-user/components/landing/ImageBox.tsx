import type { LucideIcon } from 'lucide-react';
import { ImageIcon } from 'lucide-react';

/* ───────────────────────────────────────────────────────────────────────────
   ImageBox — premium placeholder used wherever a real screenshot / mockup /
   illustration will later be dropped in. Renders an intentional, framed
   "image slot" (soft gradient, subtle grid, centered icon chip + label) so the
   layout reads as finished even before the asset exists.

   Swap for a real <img>/<Image> later — keep the same wrapper className so the
   surrounding layout is unaffected.
─────────────────────────────────────────────────────────────────────────── */

type Ratio = 'video' | 'wide' | 'square' | 'portrait' | 'tall' | 'auto';

const ratioClass: Record<Ratio, string> = {
  video: 'aspect-video',
  wide: 'aspect-[16/7]',
  square: 'aspect-square',
  portrait: 'aspect-[4/5]',
  tall: 'aspect-[9/16]',
  auto: '',
};

type Variant = 'light' | 'blue' | 'dark';

const variantStyles: Record<
  Variant,
  { surface: string; grid: string; chip: string; icon: string; label: string; sub: string; tag: string }
> = {
  light: {
    surface:
      'bg-gradient-to-br from-brand-50 via-white to-brand-50 border-brand-200',
    grid: 'rgba(31,70,119,0.07)',
    chip: 'bg-white border-brand-200 shadow-sm',
    icon: 'text-[#C4161C]',
    label: 'text-brand-700',
    sub: 'text-brand-400',
    tag: 'bg-gold-100 border-gold-300 text-gold-800',
  },
  blue: {
    surface:
      'bg-gradient-to-br from-brand-50 via-brand-100/70 to-brand-200/50 border-brand-300',
    grid: 'rgba(31,70,119,0.10)',
    chip: 'bg-white border-brand-200 shadow-sm',
    icon: 'text-[#C4161C]',
    label: 'text-brand-800',
    sub: 'text-brand-600',
    tag: 'bg-gold-100 border-gold-300 text-gold-800',
  },
  dark: {
    surface:
      'bg-gradient-to-br from-brand-800 via-brand-900 to-brand-800 border-white/10',
    grid: 'rgba(230,184,57,0.08)',
    chip: 'bg-white/10 border-gold-400/40',
    icon: 'text-gold-400',
    label: 'text-slate-200',
    sub: 'text-slate-400',
    tag: 'bg-gold-400/15 border-gold-400/30 text-gold-300',
  },
};

interface ImageBoxProps {
  /** Main caption shown under the icon, e.g. "Trading Dashboard". */
  label?: string;
  /** Optional secondary line, e.g. "1280 × 720". */
  sublabel?: string;
  /** Lucide icon rendered in the centre chip. Defaults to a generic image icon. */
  icon?: LucideIcon;
  /** Aspect ratio preset. Use `auto` + a height class via `className` for custom sizes. */
  ratio?: Ratio;
  /** Colour treatment. */
  variant?: Variant;
  /** Corner radius (Tailwind class). */
  rounded?: string;
  /** Extra classes on the outer wrapper (height, shadow, etc.). */
  className?: string;
  /** Real image source. When set, the placeholder chrome (tag, grid, icon, label)
   *  is dropped and the image fills the box via object-cover. */
  src?: string;
  /** Alt text for the real image. */
  alt?: string;
}

export default function ImageBox({
  label = 'Image',
  sublabel,
  icon: Icon = ImageIcon,
  ratio = 'video',
  variant = 'light',
  rounded = 'rounded-3xl',
  className = '',
  src,
  alt = '',
}: ImageBoxProps) {
  const v = variantStyles[variant];

  // A real image was supplied — render it and skip all placeholder chrome.
  if (src) {
    return (
      <div className={`relative overflow-hidden ${rounded} ${ratioClass[ratio]} ${className}`}>
        <img src={src} alt={alt} className="absolute inset-0 w-full h-full object-cover" />
      </div>
    );
  }

  return (
    <div
      className={`group/imgbox relative overflow-hidden border ${rounded} ${v.surface} ${ratioClass[ratio]} ${className}`}
    >
      {/* Subtle grid */}
      <div
        className="absolute inset-0 opacity-60 pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(${v.grid} 1px, transparent 1px), linear-gradient(90deg, ${v.grid} 1px, transparent 1px)`,
          backgroundSize: '32px 32px',
        }}
      />

      {/* Dashed inner frame */}
      <div className={`absolute inset-3 ${rounded} border-2 border-dashed border-current opacity-25 pointer-events-none`} />

      {/* Corner tag */}
      <span
        className={`absolute top-3 left-3 z-10 text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full border ${v.tag}`}
      >
        Image Box
      </span>

      {/* Centre content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center">
        <div
          className={`w-14 h-14 rounded-2xl border flex items-center justify-center transition-transform duration-500 group-hover/imgbox:scale-105 ${v.chip}`}
        >
          <Icon size={24} className={v.icon} strokeWidth={1.75} />
        </div>
        {label && (
          <div className={`text-sm font-semibold font-manrope ${v.label}`}>{label}</div>
        )}
        {sublabel && <div className={`text-xs ${v.sub}`}>{sublabel}</div>}
      </div>

      {/* Sheen sweep on hover */}
      <div className="absolute inset-0 -translate-x-full group-hover/imgbox:translate-x-full transition-transform duration-[1100ms] ease-out pointer-events-none bg-gradient-to-r from-transparent via-white/25 to-transparent" />
    </div>
  );
}
