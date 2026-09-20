"""Convert an alpha overlay to ProRes 4444 so compositing keeps the transparency.

ffmpeg's native VP9 decoder ignores WebM alpha and render.py does not force
libvpx-vp9, so a WebM overlay would composite as an opaque black rectangle — no
error, no warning. ProRes 4444 is decoded natively with its alpha intact.

    to_prores.py in.webm out.mov
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: to_prores.py <in> <out.mov>")
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dec = ["-c:v", "libvpx-vp9"] if src.suffix.lower() == ".webm" else []
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", *dec, "-i", str(src),
                        "-c:v", "prores_ks", "-profile:v", "4444",
                        "-pix_fmt", "yuva444p12le", "-an", str(dst)])
    if r.returncode:
        sys.exit("conversion failed")
    print(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height,pix_fmt,nb_frames",
                          "-of", "csv=p=0", str(dst)],
                         capture_output=True, text=True).stdout.strip())

if __name__ == "__main__":
    main()
