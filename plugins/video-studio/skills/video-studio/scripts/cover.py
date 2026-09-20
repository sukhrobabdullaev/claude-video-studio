"""Cover / thumbnail: best frame + kicker chip + two-line title + optional proof chip.

All type stays inside the centre 4:5 band so feed (4:5) and profile-grid (3:4) crops
never cut it; the script refuses to save otherwise. Writes crop previews next to it.

    cover.py --frame edit/cover/cand_2.6.jpg --kicker "CODEX · E2E TEST" \
             --line1 "QA TESTER" --line2 "KERAK EMAS" --chip "> verify the rest in practice e2e" \
             --out edit/cover/cover.jpg

Pick --frame from a contact sheet of ~8 candidates: eye contact, mouth near-closed, face centred.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from platform_paths import load_font  # noqa: E402


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frame", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--line1", required=True)
    ap.add_argument("--line2", default="")
    ap.add_argument("--kicker", default="")
    ap.add_argument("--chip", default="", help="mono proof line, e.g. the real prompt or command")
    ap.add_argument("--accent", default="#FF5A00")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--title-font", help="override the bundled Inter Bold with a .ttf")
    ap.add_argument("--mono-font", help="override the bundled JetBrains Mono Bold")
    a = ap.parse_args()

    W, H = a.width, a.height
    acc = hexrgb(a.accent)
    safe_h = int(W * 5 / 4)
    safe_top, safe_bot = (H - safe_h) // 2, (H - safe_h) // 2 + safe_h
    margin = int(W * 0.078)

    base = Image.open(a.frame).convert("RGB")
    s = max(W / base.width, H / base.height)
    base = base.resize((int(base.width * s), int(base.height * s)))
    base = base.crop(((base.width - W) // 2, (base.height - H) // 2, (base.width - W) // 2 + W, (base.height - H) // 2 + H))
    base = ImageEnhance.Brightness(ImageEnhance.Contrast(base).enhance(1.06)).enhance(0.97)

    scrim = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(scrim)
    top = int(H * 0.53)
    for y in range(top, H):
        sd.line((0, y, W, y), fill=int(215 * min(1.0, (y - top) / (H * 0.27)) ** 1.4))
    img = Image.composite(Image.new("RGB", (W, H), (8, 8, 8)), base, scrim).convert("RGBA")

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    def _face(kind, override, sz):
        if override:
            from PIL import ImageFont
            return ImageFont.truetype(override, sz)
        return load_font(kind, sz)

    title = lambda sz: _face("sans", a.title_font, sz)
    mono = lambda sz: _face("mono", a.mono_font, sz)

    size = int(W * 0.146)
    longest = max([a.line1, a.line2], key=lambda t: title(size).getlength(t))
    while title(size).getlength(longest) > W - 2 * margin and size > 60:
        size -= 4
    tf, lh = title(size), int(size * 0.98)
    lines = [t for t in (a.line1, a.line2) if t]

    kf, pf = mono(int(W * 0.033)), mono(int(W * 0.03))
    kick_h, chip_h, gap = (64 if a.kicker else 0), (62 if a.chip else 0), 28
    block = kick_h + (gap if a.kicker else 0) + lh * len(lines) + (18 + chip_h if a.chip else 0)
    y = min(safe_bot - 50, int(H * 0.83)) - block
    y0 = y

    if a.kicker:
        kw = kf.getlength(a.kicker)
        d.rounded_rectangle((margin, y, margin + kw + 44, y + kick_h), radius=32, fill=acc + (255,))
        d.text((margin + 22, y + 13), a.kicker, font=kf, fill=(10, 10, 10, 255))
        y += kick_h + gap

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdw = ImageDraw.Draw(shadow)
    for i, t in enumerate(lines):
        sdw.text((margin + 4, y + i * lh + 6), t, font=tf, fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(8)))
    for i, t in enumerate(lines):
        d.text((margin, y + i * lh), t, font=tf, fill=((255, 255, 255) if i == 0 or len(lines) == 1 else acc) + (255,))
    y += lh * len(lines)

    if a.chip:
        y += 18
        pw = pf.getlength(a.chip)
        d.rounded_rectangle((margin, y, margin + pw + 44, y + chip_h), radius=12, fill=(10, 10, 10, 235),
                            outline=(40, 40, 40, 255), width=1)
        d.text((margin + 22, y + 13), a.chip, font=pf, fill=(255, 255, 255, 235))
        y += chip_h

    if y0 < safe_top or y > safe_bot:
        raise SystemExit(f"type block y {y0}-{y} escapes 4:5 safe band {safe_top}-{safe_bot}: shorten text")

    out = Image.alpha_composite(img, layer).convert("RGB")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out, quality=95)
    out.crop((0, safe_top, W, safe_bot)).save(a.out.with_name(a.out.stem + "_check_4x5.jpg"), quality=90)
    g = (H - int(W * 4 / 3)) // 2
    out.crop((0, g, W, g + int(W * 4 / 3))).save(a.out.with_name(a.out.stem + "_check_3x4.jpg"), quality=90)
    print(f"{a.out} | title {size}px | type y {y0}-{y} inside 4:5 band {safe_top}-{safe_bot}")


if __name__ == "__main__":
    main()
