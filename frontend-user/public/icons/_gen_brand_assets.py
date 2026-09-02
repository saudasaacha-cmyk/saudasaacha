"""Single source for the SachchaSauda mark — emits every raster + vector asset.

    py frontend-user/public/icons/_gen_brand_assets.py

The mark is the red chevron over a diamond from the brand artwork. It is
defined ONCE below as normalised polygons (0..1 across the mark's width) and
every output is derived from it, so the favicon, the PWA tiles, the inline
`BrandGlyph` component and the standalone wordmarks can never drift apart.

Writes:
    frontend-user/public/icons/icon-{192,512}.png, icon-maskable-512.png
    frontend-user/public/febicon.png                 (favicon + OG card)
    frontend-user/public/icon.svg
    frontend-user/public/logo.svg, logo-light.svg
    frontend-admin/public/icon-{192,512}.png
    frontend-admin/app/icon.svg
    frontend-admin/public/logo.svg

`components/layout/BrandGlyph.tsx` (both apps) carries the same polygons in a
24x24 box — regenerate its coordinates from GLYPH_24 below if the mark moves.
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
USER_PUBLIC = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(USER_PUBLIC))
ADMIN = os.path.join(ROOT, "frontend-admin")

RED = "#E31E24"          # keep in sync with `brand` in both tailwind.config.ts
RED_RGB = (227, 30, 36)
INK = "#0B0B0B"          # wordmark text on light, tile ground on the icons
PAPER = "#FFFFFF"

# ── The mark, normalised to its own bounding box ──────────────────────
# u across the width, v down from the top; the mark is 0.725 as tall as
# it is wide. Chevron first (red), diamond second (ink / paper).
CHEVRON = [(0.5, 0.0), (1.0, 0.5), (0.69, 0.5), (0.5, 0.31), (0.31, 0.5), (0.0, 0.5)]
DIAMOND = [(0.5, 0.457), (0.6665, 0.6235), (0.5, 0.79), (0.3335, 0.6235)]
ASPECT = 0.79            # height / width

SS = 4                   # supersample factor — anti-aliasing, no extra deps


def _place(pts, x, y, w):
    return [(x + u * w, y + v * w) for u, v in pts]


# ── PNG tiles ────────────────────────────────────────────────────────
def make_tile(size: int, *, maskable: bool = False) -> Image.Image:
    """Dark tile + red chevron + white diamond — the dark half of the
    brand artwork, which is also what the app's own #0a0a0a theme wants."""
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = 0 if maskable else int(s * 0.22)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=radius, fill=(10, 10, 10, 255))

    # Maskable icons keep the mark inside the 80% safe zone so an OS
    # circle-crop can't clip the chevron's arms.
    mw = s * (0.58 if maskable else 0.72)
    x = (s - mw) / 2
    y = (s - mw * ASPECT) / 2
    d.polygon(_place(CHEVRON, x, y, mw), fill=RED_RGB + (255,))
    d.polygon(_place(DIAMOND, x, y, mw), fill=(255, 255, 255, 255))
    return img.resize((size, size), Image.LANCZOS)


def _check(img: Image.Image, *, maskable: bool) -> None:
    """Cheap regression guard: chevron painted, diamond painted, and a
    rounded tile actually has transparent corners."""
    px = img.load()
    w = img.width
    assert any(
        abs(px[x, y][0] - RED_RGB[0]) < 14 and px[x, y][1] < 70 and px[x, y][2] < 70
        for x in range(w) for y in range(w)
    ), "red chevron missing"
    assert any(px[x, y][:3] == (255, 255, 255) for x in range(w) for y in range(w)), "diamond missing"
    assert (px[0, 0][3] == 255) is maskable, "corner alpha does not match tile shape"


# ── SVG ──────────────────────────────────────────────────────────────
def _poly(pts, x, y, w, fill):
    body = " ".join(f"{px:.2f},{py:.2f}" for px, py in _place(pts, x, y, w))
    return f'<polygon points="{body}" fill="{fill}"/>'


def mark_svg(x, y, w, diamond_fill):
    return (f'{_poly(CHEVRON, x, y, w, RED)}\n  '
            f'{_poly(DIAMOND, x, y, w, diamond_fill)}')


def icon_svg() -> str:
    """512 app icon — same dark tile as the PNGs."""
    w = 512 * 0.72
    x = (512 - w) / 2
    y = (512 - w * ASPECT) / 2
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">\n'
            f'  <rect width="512" height="512" rx="113" fill="#0a0a0a"/>\n  '
            + mark_svg(x, y, w, PAPER) + '\n</svg>\n')


FONT = ("'Space Grotesk', Inter, ui-sans-serif, system-ui, -apple-system, "
        "'Segoe UI', Roboto, sans-serif")


def wordmark_svg(ink: str, *, suffix: str = "") -> str:
    """Horizontal lockup for share cards, email, and anywhere outside the
    apps. In-app the `Wordmark` component renders the same thing with real
    text so it picks up the bundled Space Grotesk."""
    mw = 58.0
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 340 64" width="340" height="64" role="img" aria-label="SachchaSauda">
  {mark_svg(4, (64 - mw * ASPECT) / 2, mw, ink)}
  <text x="74" y="43" font-family="{FONT}" font-size="31" font-weight="700" letter-spacing="-0.8">
    <tspan fill="{ink}">Sachcha</tspan><tspan fill="{RED}">Sauda</tspan>{suffix}
  </text>
</svg>
'''


def main() -> None:
    pngs = [
        (os.path.join(HERE, "icon-192.png"), 192, False),
        (os.path.join(HERE, "icon-512.png"), 512, False),
        (os.path.join(HERE, "icon-maskable-512.png"), 512, True),
        (os.path.join(USER_PUBLIC, "febicon.png"), 512, False),
        (os.path.join(ADMIN, "public", "icon-192.png"), 192, False),
        (os.path.join(ADMIN, "public", "icon-512.png"), 512, False),
    ]
    for path, size, maskable in pngs:
        img = make_tile(size, maskable=maskable)
        _check(img, maskable=maskable)
        img.save(path, "PNG")
        print(f"wrote {path} ({size}x{size})")

    svgs = {
        os.path.join(USER_PUBLIC, "icon.svg"): icon_svg(),
        os.path.join(ADMIN, "app", "icon.svg"): icon_svg(),
        os.path.join(USER_PUBLIC, "logo.svg"): wordmark_svg(INK),
        os.path.join(USER_PUBLIC, "logo-light.svg"): wordmark_svg(PAPER),
        os.path.join(ADMIN, "public", "logo.svg"): wordmark_svg(
            INK, suffix='<tspan fill="#94a3b8" font-weight="500"> Admin</tspan>'),
    }
    for path, body in svgs.items():
        open(path, "w", encoding="utf-8").write(body)
        print(f"wrote {path}")

    # The 24x24 numbers BrandGlyph.tsx hard-codes, printed so a geometry
    # change is a copy-paste away instead of a re-derivation.
    mw = 24 * 0.94
    x = (24 - mw) / 2
    y = (24 - mw * ASPECT) / 2
    print("\nBrandGlyph 24x24 — chevron:",
          " ".join(f"{a:.2f},{b:.2f}" for a, b in _place(CHEVRON, x, y, mw)))
    print("BrandGlyph 24x24 — diamond:",
          " ".join(f"{a:.2f},{b:.2f}" for a, b in _place(DIAMOND, x, y, mw)))


if __name__ == "__main__":
    main()
