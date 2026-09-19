"""Check every cut boundary of a rendered video for audio pops.

A click shows up as a transient far above local RMS. Ratio = peak within ±20ms of the
boundary / RMS within ±500ms. Boundaries carrying an intentional SFX hit can be exempted.

    check_boundaries.py --video edit/final.mp4 --offsets edit/offsets.json --exempt 1.2 8.63
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", type=Path, required=True)
    ap.add_argument("--offsets", type=Path, required=True)
    ap.add_argument("--exempt", type=float, nargs="*", default=[], help="output times with intentional SFX")
    ap.add_argument("--threshold", type=float, default=6.0)
    a = ap.parse_args()

    wav = Path(tempfile.mkdtemp()) / "a.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(a.video), "-ac", "1", "-ar", "48000", str(wav), "-y"], check=True)
    x, sr = sf.read(wav)
    rows = json.loads(a.offsets.read_text())
    bounds = [r["out_start"] for r in rows[1:]]
    fails = []
    for b in bounds:
        i = int(b * sr)
        pk = np.abs(x[max(0, i - int(0.02 * sr)): i + int(0.02 * sr)]).max()
        rms = np.sqrt((x[max(0, i - int(0.5 * sr)): i + int(0.5 * sr)] ** 2).mean())
        ratio = pk / rms if rms else 0.0
        exempt = any(abs(b - e) < 0.1 for e in a.exempt)
        status = "sfx" if exempt else ("POP" if ratio > a.threshold else "ok")
        if status == "POP":
            fails.append(b)
        print(f"  {b:8.3f}s  ratio {ratio:5.2f}  {status}")
    print(f"{'PASS' if not fails else 'FAIL'}  {len(bounds)} boundaries, unexplained pops: {fails or 'none'}")
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
