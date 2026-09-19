"""Measure the real output-timeline offset of every EDL range.

render.py extracts one clip per range; each clip's duration rounds to whole frames,
so the output timeline drifts from the nominal EDL (≈+0.2s over 15 cuts). Time
graphics, captions and SFX against these measured offsets instead.

Clip dirs can hold leftovers from earlier renders under different names, so the
newest N clips (N = number of ranges) are used, ordered by their seg_NN index.

    offsets.py --edl edit/edl.json [--clips-dir edit/clips_preview] [--out edit/offsets.json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def probe_duration(p: Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, check=True).stdout.strip())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--edl", type=Path, required=True)
    ap.add_argument("--clips-dir", type=Path, help="default: newest edit/clips* dir")
    ap.add_argument("--out", type=Path, help="default: <edl dir>/offsets.json")
    a = ap.parse_args()

    edl = json.loads(a.edl.read_text())
    ranges = edl["ranges"]
    edit = a.edl.parent
    clips_dir = a.clips_dir
    if clips_dir is None:
        dirs = [d for d in edit.glob("clips*") if d.is_dir() and any(d.glob("seg_*.mp4"))]
        if not dirs:
            raise SystemExit("no clips* dir with seg_*.mp4 — render the EDL first")
        clips_dir = max(dirs, key=lambda d: max(f.stat().st_mtime for f in d.glob("seg_*.mp4")))

    clips = sorted(clips_dir.glob("seg_*.mp4"), key=lambda p: p.stat().st_mtime)[-len(ranges):]
    clips.sort(key=lambda p: int(re.search(r"seg_(\d+)", p.name).group(1)))
    if len(clips) != len(ranges):
        raise SystemExit(f"{len(clips)} clips in {clips_dir} but {len(ranges)} ranges")

    rows, off = [], 0.0
    for c, r in zip(clips, ranges):
        d = probe_duration(c)
        rows.append({"beat": r.get("beat", ""), "source": r["source"], "src_start": r["start"],
                     "src_end": r["end"], "out_start": round(off, 4), "dur": round(d, 4), "clip": c.name})
        off += d
    out = a.out or edit / "offsets.json"
    out.write_text(json.dumps(rows, indent=2))

    nominal = sum(r["end"] - r["start"] for r in ranges)
    for r in rows:
        print(f"  {r['beat'][:22]:22s} src {r['src_start']:8.2f}  out {r['out_start']:8.3f}  +{r['dur']:.3f}")
    print(f"total {off:.3f}s  nominal {nominal:.3f}s  drift {off - nominal:+.3f}s  -> {out}")
    print("map a source time t in range i to output time: t - src_start + out_start")


if __name__ == "__main__":
    main()
