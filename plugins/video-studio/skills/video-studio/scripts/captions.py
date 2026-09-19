"""Frame-exact transparent caption track (ProRes 4444) + matching SRT.

Why not ffmpeg subtitles / concat:
  * the `subtitles` filter needs libass, missing from some ffmpeg builds;
  * a concat-demuxer image track quantizes each entry to a frame and drifts;
  * word-timed cues blink off between chunks unless small gaps are bridged.
Every output frame is emitted explicitly here, so drift is at most one frame.

Composite the result as the LAST overlay in the EDL (video-use Hard Rule 1).

    captions.py --edl edit/edl.json --offsets edit/offsets.json --out edit/captions.mov
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PUNCT = set(".,!?;:")


def build_cues(edl: dict, offsets: list[dict], transcripts: Path, words_per: int,
               skip_beats: set[str], case: str, bridge: float):
    cues = []
    for r, o in zip(edl["ranges"], offsets):
        if r.get("beat") in skip_beats:
            continue
        tr = json.loads((transcripts / f"{r['source']}.json").read_text())
        s, e, off = float(r["start"]), float(r["end"]), float(o["out_start"])
        words = [w for w in tr["words"] if w.get("type") == "word" and w.get("start") is not None
                 and not (w["end"] <= s or w["start"] >= e)]
        chunk, chunks = [], []
        for w in words:
            t = (w.get("text") or "").strip()
            if not t:
                continue
            chunk.append(w)
            if len(chunk) >= words_per or t[-1] in PUNCT:
                chunks.append(chunk)
                chunk = []
        if chunk:
            chunks.append(chunk)
        for ch in chunks:
            a = max(s, ch[0]["start"]) - s + off
            b = min(e, ch[-1]["end"]) - s + off
            if b <= a:
                b = a + 0.4
            text = re.sub(r"\s+", " ", " ".join(w["text"].strip() for w in ch)).strip().rstrip(",;:")
            cues.append([a, b, text.upper() if case == "upper" else text])
    cues.sort(key=lambda c: c[0])
    for i in range(len(cues) - 1):
        gap = cues[i + 1][0] - cues[i][1]
        if 0 <= gap < bridge:
            cues[i][1] = cues[i + 1][0]
    return [tuple(c) for c in cues]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--edl", type=Path, required=True)
    ap.add_argument("--offsets", type=Path, required=True, help="from offsets.py")
    ap.add_argument("--transcripts", type=Path, help="default: <edl dir>/transcripts")
    ap.add_argument("--out", type=Path, required=True, help="caption track .mov")
    ap.add_argument("--srt", type=Path, help="default: <out>.srt")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--font", default="/System/Library/Fonts/Helvetica.ttc")
    ap.add_argument("--font-index", type=int, default=1, help="1 = Helvetica Bold")
    ap.add_argument("--size-max", type=int, default=72)
    ap.add_argument("--size-min", type=int, default=54)
    ap.add_argument("--stroke", type=int, default=7)
    ap.add_argument("--margin", type=int, default=100, help="side safe margin, px")
    ap.add_argument("--bottom-from-edge", type=int, default=595,
                    help="px from frame bottom to text bottom; 595 keeps 9:16 captions above platform UI")
    ap.add_argument("--words-per-chunk", type=int, default=2)
    ap.add_argument("--case", choices=["upper", "natural"], default="upper")
    ap.add_argument("--bridge", type=float, default=0.25, help="bridge gaps shorter than this (s)")
    ap.add_argument("--skip-beat", action="append", default=[], help="beats with no captions, e.g. COLD-OPEN")
    a = ap.parse_args()

    edl = json.loads(a.edl.read_text())
    offsets = json.loads(a.offsets.read_text())
    if len(offsets) != len(edl["ranges"]):
        raise SystemExit("offsets/ranges mismatch — re-run offsets.py after changing the EDL")
    transcripts = a.transcripts or a.edl.parent / "transcripts"
    cues = build_cues(edl, offsets, transcripts, a.words_per_chunk, set(a.skip_beat), a.case, a.bridge)
    total = offsets[-1]["out_start"] + offsets[-1]["dur"]

    W, H = a.width, a.height
    max_w = W - 2 * a.margin
    bottom = H - a.bottom_from_edge

    def fit(text):
        for size in range(a.size_max, a.size_min - 1, -3):
            f = ImageFont.truetype(a.font, size, index=a.font_index)
            if f.getlength(text) + 2 * a.stroke <= max_w:
                return f, [text]
        words = text.split()
        for k in range(len(words) - 1, 0, -1):
            lines = [" ".join(words[:k]), " ".join(words[k:])]
            for size in range(a.size_max, a.size_min - 1, -3):
                f = ImageFont.truetype(a.font, size, index=a.font_index)
                if all(f.getlength(l) + 2 * a.stroke <= max_w for l in lines):
                    return f, lines
        return ImageFont.truetype(a.font, a.size_min, index=a.font_index), [text]

    def render(text):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if text:
            d = ImageDraw.Draw(img)
            f, lines = fit(text)
            asc, desc = f.getmetrics()
            lh = asc + desc
            y = bottom - (lh * len(lines) + 12 * (len(lines) - 1))
            for line in lines:
                d.text((W // 2, y), line, font=f, fill=(255, 255, 255, 255),
                       stroke_width=a.stroke, stroke_fill=(0, 0, 0, 255), anchor="ma")
                y += lh + 12
        return img.tobytes()

    n = int(round(total * a.fps))
    p = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
         "-r", str(a.fps), "-i", "pipe:0", "-c:v", "prores_ks", "-profile:v", "4444",
         "-pix_fmt", "yuva444p12le", "-an", str(a.out)], stdin=subprocess.PIPE)
    blank = render(None)
    key, frame, ci, on, wrapped = object(), blank, 0, 0, set()
    for i in range(n):
        t = i / a.fps
        while ci < len(cues) and cues[ci][1] <= t:
            ci += 1
        text = cues[ci][2] if ci < len(cues) and cues[ci][0] <= t < cues[ci][1] else None
        if text != key:
            key, frame = text, (render(text) if text else blank)
            if text and len(fit(text)[1]) > 1:
                wrapped.add(text)
        on += bool(text)
        p.stdin.write(frame)
    p.stdin.close()
    if p.wait():
        raise SystemExit("encode failed")

    def ts(x):
        ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    srt = a.srt or a.out.with_suffix(".srt")
    srt.write_text("\n".join(f"{i}\n{ts(x)} --> {ts(y)}\n{t}\n" for i, (x, y, t) in enumerate(cues, 1)))

    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", str(a.out)], capture_output=True, text=True).stdout)
    print(f"cues {len(cues)} | timeline {total:.3f}s | track {dur:.3f}s | drift {dur - total:+.3f}s "
          f"| captioned {100 * on / max(n, 1):.0f}% of frames | wrapped {len(wrapped)}")
    print(f"track {a.out}\nsrt   {srt}")


if __name__ == "__main__":
    main()
