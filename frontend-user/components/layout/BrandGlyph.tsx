import type { SVGProps } from "react";

/**
 * SachchaSauda brand mark — red chevron over a diamond. Geometry is the
 * 512px mark in `public/icon.svg` scaled to lucide's 24x24 box, so it
 * drops into every place an icon sat (same `className` sizing).
 *
 * The chevron is always the brand red (`fill-brand` → tailwind.config.ts);
 * the diamond follows `currentColor`, so it goes ink on light surfaces and
 * white on dark ones exactly like the brand artwork. Regenerate these
 * numbers with `public/icons/_gen_brand_assets.py` if the mark changes.
 */
export function BrandGlyph({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className={className}
      {...props}
    >
      <polygon
        className="fill-brand"
        points="12.00,3.09 23.28,14.37 16.29,14.37 12.00,10.08 7.71,14.37 0.72,14.37"
      />
      <polygon points="12.00,13.40 15.76,17.15 12.00,20.91 8.24,17.15" fill="currentColor" />
    </svg>
  );
}
