"""Motion-matched highlight box (transparent ProRes 4444).

Handheld footage moves; a static box slides off its UI element within ~0.5s. This
estimates each frame's global translation against a reference frame by FFT phase
correlation, median-filters it, and offsets the box so it stays on target.

--rect is in OUTPUT-frame pixels at --ref time. --video must already be at output
resolution (e.g. the reframed intermediate the EDL range uses). Window/ref times are
SOURCE times in --video. Place the result in the EDL at the mapped output time.

It prints the measured drift. If the target leaves the frame, shorten --window.

    track_box.py --video edit/punch/demo.mp4 --rect 768 476 1072 606 \
                 --window 19.9 21.5 --ref 20.0 --out edit/animations/hl_1.mov
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def dims(video: Path) -> tuple[int, int]:
    s = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:stream_side_data=rotation", "-of", "json", str(video)],
        capture_output=True, text=True, check=True).stdout)["streams"][0]
    w, h = int(s["width"]), int(s["height"])
    rot = next((sd.get("rotation") for sd in s.get("side_data_list") or [] if "rotation" in sd), 0)
    return (h, w) if int(round(float(rot or 0))) % 180 else (w, h)


def eo(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", type=Path, required=True)
    ap.add_argument("--rect", type=float, nargs=4, required=True, metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--window", type=float, nargs=2, required=True, metavar=("START", "END"))
    ap.add_argument("--ref", type=float, required=True, help="source time where --rect was measured")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--color", default="255,90,0")
    ap.add_argument("--static", action="store_true", help="skip tracking (tripod footage)")
    a = ap.parse_args()

    W, H = dims(a.video)
    sw, sh = W // 4, H // 4
    color = tuple(int(c) for c in a.color.split(","))

    def grab(t):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(a.video),
                              "-frames:v", "1", "-vf", f"scale={sw}:{sh},format=gray",
                              "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.uint8)[: sw * sh].reshape(sh, sw).astype(np.float64)

    win = np.hanning(sh)[:, None] * np.hanning(sw)[None, :]

    def shift(ref, cur):
        R = np.fft.fft2((ref - ref.mean()) * win) * np.conj(np.fft.fft2((cur - cur.mean()) * win))
        R /= np.abs(R) + 1e-9
        c = np.fft.ifft2(R).real
        iy, ix = np.unravel_index(np.argmax(c), c.shape)
        return (iy - sh if iy > sh // 2 else iy), (ix - sw if ix > sw // 2 else ix)

    s, e = a.window
    n = int(round((e - s) * a.fps))
    if a.static:
        off = np.zeros((n, 2))
    else:
        ref = grab(a.ref)
        raw = np.array([[dx * 4.0, dy * 4.0] for dy, dx in (shift(ref, grab(s + i / a.fps)) for i in range(n))])
        off = np.stack([[np.median(raw[max(0, i - 2): i + 3, c]) for c in (0, 1)] for i in range(n)])

    x0, y0, x1, y1 = a.rect
    dur = n / a.fps
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
                          "-s", f"{W}x{H}", "-r", str(a.fps), "-i", "pipe:0", "-c:v", "prores_ks",
                          "-profile:v", "4444", "-pix_fmt", "yuva444p12le", "-an", str(a.out)],
                         stdin=subprocess.PIPE)
    offscreen = 0
    for i in range(n):
        t = i / a.fps
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        fade = 1.0 if t < dur - 0.3 else max(0.0, 1 - (t - (dur - 0.3)) / 0.3)
        pr = eo(t / 0.26)
        if pr > 0:
            dx, dy = -off[i][0], -off[i][1]
            g = (1 - pr) * 0.06
            gw, gh = (x1 - x0) * g, (y1 - y0) * g
            bx = (x0 + dx - gw, y0 + dy - gh, x1 + dx + gw, y1 + dy + gh)
            if bx[0] < -10 or bx[1] < -10 or bx[2] > W + 10 or bx[3] > H + 10:
                offscreen += 1
            al = int(255 * pr * fade)
            d.rounded_rectangle(bx, radius=12, outline=color + (int(al * 0.9),), width=5)
            cx0, cy0, cx1, cy1 = bx
            k = 34
            for seg in ((cx0, cy0, cx0 + k, cy0), (cx0, cy0, cx0, cy0 + k), (cx1 - k, cy0, cx1, cy0),
                        (cx1, cy0, cx1, cy0 + k), (cx0, cy1 - k, cx0, cy1), (cx0, cy1, cx0 + k, cy1),
                        (cx1, cy1 - k, cx1, cy1), (cx1 - k, cy1, cx1, cy1)):
                d.line(seg, fill=color + (al,), width=9)
        p.stdin.write(img.tobytes())
    p.stdin.close()
    if p.wait():
        raise SystemExit("encode failed")
    mx = np.abs(off).max(axis=0) if n else [0, 0]
    print(f"{a.out.name}: {n} frames {dur:.2f}s | drift dx±{mx[0]:.0f}px dy±{mx[1]:.0f}px"
          + (f" | WARNING box partly off-frame in {offscreen} frames — shorten --window" if offscreen else ""))


if __name__ == "__main__":
    main()
