"""Single source for the RIZING BULL mark — emits every raster + vector asset.

    py frontend-user/public/icons/_gen_brand_assets.py

The mark is the charging bull over the gold arrow from the brand artwork.
Unlike the chevron it replaced it is a rendered illustration, not geometry,
so the master lives beside this script as `_brand-mark.png` — the supplied
artwork with its white studio background flood-filled to alpha and trimmed
to the mark (the "RIZING BULL" wordmark underneath it is dropped, because
every lockup below sets that as real text so it picks up the bundled Space
Grotesk and stays crisp at any size).

Every output is derived from that one master, so the favicon, the PWA
tiles, the inline `BrandGlyph` component and the standalone wordmarks can
never drift apart.

Writes:
    frontend-user/public/icons/icon-{192,512}.png, icon-maskable-512.png
    frontend-user/public/febicon.png                 (favicon + OG card)
    frontend-user/public/icon.svg
    frontend-user/public/logo.svg, logo-light.svg
    frontend-admin/public/icon-{192,512}.png
    frontend-admin/app/icon.svg
    frontend-admin/public/logo.svg

...and prints the base64 WebP both apps' `components/layout/BrandGlyph.tsx`
inline, so the 24px glyph needs no network request and survives offline.
"""
import base64
import io
import os
import sys
from collections import deque

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
USER_PUBLIC = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(USER_PUBLIC))
ADMIN = os.path.join(ROOT, "frontend-admin")

MASTER = os.path.join(HERE, "_brand-mark.png")
SOURCE = os.path.join(HERE, "_brand-source.jpg")   # the artwork as supplied

# Sampled off the artwork itself — keep in sync with `brand` / `gold` in
# both tailwind.config.ts, which cannot read this file.
NAVY = "#031A41"         # "RIZING", and the bull's body
GOLD = "#F7CA09"         # "BULL", the arrow, the horns
PAPER = "#FFFFFF"
# The icon tile. Light blue rather than the app's own near-black: the
# bull is navy with gold, so on a dark tile its body loses the edge that
# separates it from the background, and at launcher size it read as a
# gold arrow with a smudge behind it. This is `brand-100`, so it is a
# token the palette already has rather than a colour invented for icons.
TILE = "#DBEDFF"
TILE_RGB = (219, 237, 255)

# How much of a tile's width the mark spans. Maskable icons stay inside the
# 80% safe zone so an OS circle-crop cannot clip the horns or the arrow tip.
FILL = 0.84
FILL_MASKABLE = 0.64


def load_mark() -> Image.Image:
    img = Image.open(MASTER).convert("RGBA")
    assert img.getchannel("A").getextrema()[0] == 0, (
        "master has no transparent pixels — the background was not removed"
    )
    return img


# ── Re-cutting the master from the artwork ───────────────────────────
#     py _gen_brand_assets.py --extract [path/to/artwork.jpg]
#
# Defaults to `_brand-source.jpg`, the artwork exactly as supplied, kept
# beside this script so the cut can be redone with different thresholds
# without hunting for the original. Only needed when the artwork itself
# changes; the master it writes is checked in, so the normal run above
# never touches either file.
WHITE = 228              # at/above this on every channel = studio backdrop
SOFT = 252               # ...ramping to fully clear by here, for clean edges
HOLE_PX = 2000           # enclosed white smaller than this is a HIGHLIGHT


def extract_master(src: str = SOURCE, out: str = MASTER) -> None:
    """White studio background out, mark trimmed, wordmark dropped.

    Naively clearing every near-white pixel also clears the backdrop seen
    BETWEEN the bull's legs — correct — while a border flood-fill leaves
    exactly those enclosed patches opaque and they show up as white blobs
    on the dark tiles. So: clear all of it, then put back only the
    enclosed patches small enough to be highlights (the eye glint is
    ~135px; the leg gaps are ~10k)."""
    import numpy as np

    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.int16)
    near = rgb.min(axis=2) > WHITE
    h, w = near.shape

    keep = np.zeros((h, w), bool)
    seen = np.zeros((h, w), bool)
    for sy in range(h):
        for sx in range(w):
            if not near[sy, sx] or seen[sy, sx]:
                continue
            seen[sy, sx] = True
            q, cells, edge = deque([(sy, sx)]), [], False
            while q:
                y, x = q.popleft()
                cells.append((y, x))
                edge = edge or y in (0, h - 1) or x in (0, w - 1)
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < h and 0 <= nx < w and near[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if not edge and len(cells) < HOLE_PX:
                for y, x in cells:
                    keep[y, x] = True

    alpha = np.clip((SOFT - rgb.max(axis=2)) / (SOFT - WHITE), 0, 1)
    alpha[~near | keep] = 1.0
    img = Image.fromarray(
        np.dstack([rgb.astype(np.uint8), (alpha * 255).astype(np.uint8)]), "RGBA"
    )

    # The lockup is mark-over-wordmark with a clear band between them; cut
    # at the widest empty row band so the wordmark (set as real text in
    # every lockup below) is dropped.
    ink = alpha > 0.02
    rows = ink.any(axis=1)
    bands, start = [], None
    for y, filled in enumerate([*rows, True]):
        if not filled and start is None:
            start = y
        elif filled and start is not None:
            bands.append((start, y))
            start = None
    inner = [b for b in bands if b[0] > 0 and b[1] < h]
    cut = max(inner, key=lambda b: b[1] - b[0])[0] if inner else h

    img = img.crop((0, 0, w, cut))
    img = img.crop(img.getchannel("A").point(lambda v: 255 * (v > 6)).getbbox())
    img.save(out, "PNG", optimize=True)
    print(f"wrote {out} — {img.width}x{img.height}, cut at y={cut}")


def fit(mark: Image.Image, width: int) -> Image.Image:
    return mark.resize((width, round(width * mark.height / mark.width)), Image.LANCZOS)


# ── PNG tiles ────────────────────────────────────────────────────────
def make_tile(mark: Image.Image, size: int, *, maskable: bool = False) -> Image.Image:
    """Dark rounded tile + the bull, centred."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if maskable:
        img.paste(TILE_RGB + (255,), (0, 0, size, size))
    else:
        from PIL import ImageDraw

        # Supersample the corner radius only — the mark is already smooth.
        ss = 4
        plate = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
        ImageDraw.Draw(plate).rounded_rectangle(
            (0, 0, size * ss - 1, size * ss - 1),
            radius=int(size * ss * 0.22),
            fill=TILE_RGB + (255,),
        )
        img = plate.resize((size, size), Image.LANCZOS)

    m = fit(mark, round(size * (FILL_MASKABLE if maskable else FILL)))
    img.alpha_composite(m, ((size - m.width) // 2, (size - m.height) // 2))
    return img


def _check(img: Image.Image, *, maskable: bool) -> None:
    """Cheap regression guard: gold present, blue present, and a rounded
    tile actually has transparent corners."""
    px = img.convert("RGBA").load()
    rng = range(0, img.width, max(1, img.width // 256))
    pixels = [px[x, y] for x in rng for y in rng if px[x, y][3] > 200]
    assert any(r > 180 and g > 130 and b < 110 for r, g, b, _ in pixels), "gold missing"
    assert any(b > r + 50 and b > 90 for r, g, b, _ in pixels), "bull blue missing"
    assert (px[0, 0][3] == 255) is maskable, "corner alpha does not match tile shape"


# ── SVG ──────────────────────────────────────────────────────────────
def mark_webp(mark: Image.Image, width: int, quality: int = 86) -> str:
    """The mark as a data URI. SVG rendered via <img> is a sandboxed
    context that cannot fetch external files, so embedding is the only way
    a standalone logo.svg can carry a raster mark at all."""
    buf = io.BytesIO()
    fit(mark, width).save(buf, "WEBP", quality=quality, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def icon_svg(mark: Image.Image) -> str:
    """512 app icon — same dark tile as the PNGs."""
    w = round(512 * FILL)
    h = round(w * mark.height / mark.width)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" '
        'height="512" role="img" aria-label="RIZING BULL">\n'
        f'  <rect width="512" height="512" rx="113" fill="{TILE}"/>\n'
        f'  <image x="{(512 - w) / 2:.1f}" y="{(512 - h) / 2:.1f}" width="{w}" '
        f'height="{h}" href="{mark_webp(mark, 512)}"/>\n'
        "</svg>\n"
    )


FONT = (
    "'Space Grotesk', Inter, ui-sans-serif, system-ui, -apple-system, "
    "'Segoe UI', Roboto, sans-serif"
)


def wordmark_svg(mark: Image.Image, ink: str, *, suffix: str = "") -> str:
    """Horizontal lockup for share cards, email, and anywhere outside the
    apps. In-app the `Wordmark` component renders the same thing with real
    text so it picks up the bundled Space Grotesk.

    `ink` carries the first word: navy on light surfaces, white on dark.
    "BULL" is always gold, exactly as in the artwork."""
    mh = 54.0
    mw = mh * mark.width / mark.height
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 340 64" width="340" height="64" role="img" aria-label="RIZING BULL">
  <image x="2" y="{(64 - mh) / 2:.1f}" width="{mw:.1f}" height="{mh:.1f}" href="{mark_webp(mark, 160)}"/>
  <text x="{mw + 12:.1f}" y="43" font-family="{FONT}" font-size="30" font-weight="700" letter-spacing="-0.6">
    <tspan fill="{ink}">RIZING</tspan><tspan fill="{GOLD}"> BULL</tspan>{suffix}
  </text>
</svg>
'''


def brand_glyph_tsx(mark: Image.Image) -> str:
    """The 24x24 inline glyph, identical in both apps.

    The mark is an illustration rather than geometry, so the glyph carries
    a small WebP instead of polygons. Inlining it as a data URI keeps the
    behaviour the polygons had: no second request, nothing to 404, and it
    still renders from the service worker's offline shell."""
    h = 24 * mark.height / mark.width
    return f'''import type {{ SVGProps }} from "react";

/**
 * RIZING BULL brand mark — the charging bull over the gold arrow, in
 * lucide's 24x24 box so it drops into every place an icon sat (same
 * `className` sizing).
 *
 * The artwork is a rendered illustration, not geometry, so unlike the
 * chevron this replaced it cannot follow `currentColor` — it carries its
 * own navy and gold on every surface, exactly as in the brand artwork.
 * The WebP is inlined so the glyph still needs no network request and
 * renders inside the service worker's offline shell.
 *
 * Generated — regenerate with `public/icons/_gen_brand_assets.py`, which
 * writes this file in BOTH apps from the one master so they cannot drift.
 */
const MARK =
  "{mark_webp(mark, 96, quality=82)}";

export function BrandGlyph({{ className, ...props }}: SVGProps<SVGSVGElement>) {{
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className={{className}}
      {{...props}}
    >
      <image href={{MARK}} x="0" y="{(24 - h) / 2:.2f}" width="24" height="{h:.2f}" />
    </svg>
  );
}}
'''


def main() -> None:
    mark = load_mark()
    print(f"master {MASTER} — {mark.width}x{mark.height}")

    pngs = [
        (os.path.join(HERE, "icon-192.png"), 192, False),
        (os.path.join(HERE, "icon-512.png"), 512, False),
        (os.path.join(HERE, "icon-maskable-512.png"), 512, True),
        (os.path.join(USER_PUBLIC, "febicon.png"), 512, False),
        (os.path.join(ADMIN, "public", "icon-192.png"), 192, False),
        (os.path.join(ADMIN, "public", "icon-512.png"), 512, False),
    ]
    for path, size, maskable in pngs:
        img = make_tile(mark, size, maskable=maskable)
        _check(img, maskable=maskable)
        img.save(path, "PNG", optimize=True)
        print(f"wrote {path} ({size}x{size}, {os.path.getsize(path) // 1024} KB)")

    svgs = {
        os.path.join(USER_PUBLIC, "icon.svg"): icon_svg(mark),
        os.path.join(ADMIN, "app", "icon.svg"): icon_svg(mark),
        os.path.join(USER_PUBLIC, "logo.svg"): wordmark_svg(mark, NAVY),
        os.path.join(USER_PUBLIC, "logo-light.svg"): wordmark_svg(mark, PAPER),
        os.path.join(ADMIN, "public", "logo.svg"): wordmark_svg(
            mark, NAVY, suffix='<tspan fill="#94a3b8" font-weight="500"> Admin</tspan>'
        ),
    }
    for path, body in svgs.items():
        open(path, "w", encoding="utf-8").write(body)
        print(f"wrote {path} ({len(body) // 1024} KB)")

    for path in (
        os.path.join(ROOT, "frontend-user", "components", "layout", "BrandGlyph.tsx"),
        os.path.join(ADMIN, "components", "layout", "BrandGlyph.tsx"),
    ):
        body = brand_glyph_tsx(mark)
        open(path, "w", encoding="utf-8").write(body)
        print(f"wrote {path} ({len(body) // 1024} KB)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--extract":
        extract_master(*sys.argv[2:3])
    main()
