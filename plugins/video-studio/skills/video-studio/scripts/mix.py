"""Mix speech + music bed + SFX, master to a loudness target, mux onto the video.

Input video should be rendered with `render.py --no-loudnorm` so loudness is set
once, on the full mix. The video stream is copied, never re-encoded.

Ducking is computed from a measured speech envelope (fast attack, slow release), so
the gain reduction is a stated number. Every level is measured and gated at the end
— including on the final AAC file, since lossy encoding raises true peak.

cues.json:  [{"file": "whoosh_up.wav", "at": 8.63, "gain_db": -11}, ...]
            ("file" is resolved against --sfx-dir unless absolute; "at" is output seconds)

    mix.py --video edit/video.mp4 --bed edit/audio/music_bed.wav --sfx-dir edit/audio \
           --cues edit/cues.json --mute-until 1.2 --out edit/final.mp4
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 48_000


def db(x):
    return 10 ** (x / 20)


def mono(x):
    return x.mean(axis=1) if x.ndim > 1 else x


def measure(path: Path) -> dict:
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af",
                          "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    blob = json.loads(re.findall(r"\{[^{}]*\}", err)[-1])
    return blob


def envelope(x, attack_ms=15, release_ms=320):
    hop = int(SR * 0.005)
    frames = int(np.ceil(len(x) / hop))
    rms = np.sqrt((np.pad(x, (0, frames * hop - len(x))).reshape(frames, hop) ** 2).mean(axis=1))
    pres = np.clip((rms - db(-45)) / (np.percentile(rms, 90) + 1e-9), 0, 1) ** 0.5
    a, r = np.exp(-hop / (SR * attack_ms / 1000)), np.exp(-hop / (SR * release_ms / 1000))
    sm, acc = np.zeros_like(pres), 0.0
    for i, v in enumerate(pres):
        c = a if v > acc else r
        acc = c * acc + (1 - c) * v
        sm[i] = acc
    return np.interp(np.arange(len(x)), np.arange(frames) * hop, sm)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--bed", type=Path, help="music bed; omit for no music")
    ap.add_argument("--sfx-dir", type=Path)
    ap.add_argument("--cues", type=Path, help="SFX cue list JSON")
    ap.add_argument("--mute-until", type=float, default=0.0, help="mute speech before this output time (cold open)")
    ap.add_argument("--music-db", type=float, default=-16.0, help="static bed trim before ducking")
    ap.add_argument("--duck-db", type=float, default=9.0)
    ap.add_argument("--silent-lift-db", type=float, default=6.0, help="bed lift inside the muted window")
    ap.add_argument("--lufs", type=float, default=-14.0)
    ap.add_argument("--tp", type=float, default=-1.5, help="true-peak ceiling on the FINAL file")
    ap.add_argument("--stems", type=Path, help="write stems here (default: next to --out)")
    a = ap.parse_args()

    stems = a.stems or a.out.parent
    stems.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())

    sp_path = stems / "stem_speech.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a.video), "-map", "0:a:0", "-ac", "2",
                    "-ar", str(SR), str(sp_path)], check=True)
    sp, _ = sf.read(sp_path, always_2d=True)
    n = len(sp)
    cut = int(a.mute_until * SR)
    if cut:
        sp[:cut] = 0
        ramp = int(0.03 * SR)
        sp[cut:cut + ramp] *= np.linspace(0, 1, ramp)[:, None]
    sf.write(sp_path, sp.astype(np.float32), SR)

    music = np.zeros(n)
    if a.bed:
        bed = mono(sf.read(a.bed, always_2d=True)[0])
        bed = np.tile(bed, int(np.ceil(n / len(bed))))[:n] * db(a.music_db)
        pres = envelope(mono(sp))
        music = bed * (db(-a.duck_db) + (1 - db(-a.duck_db)) * (1 - pres))
        if cut:
            music[:cut] *= db(a.silent_lift_db)
        fade = int(1.0 * SR)
        music[-fade:] *= np.linspace(1, 0, fade)
    mu_path = stems / "stem_music.wav"
    sf.write(mu_path, np.stack([music, music], 1).astype(np.float32), SR)

    sfx = np.zeros(n)
    for c in json.loads(a.cues.read_text()) if a.cues else []:
        f = Path(c["file"])
        f = f if f.is_absolute() else a.sfx_dir / f
        x = mono(sf.read(f, always_2d=True)[0])
        i = int(c["at"] * SR)
        seg = x[: max(0, n - i)]
        sfx[i:i + seg.size] += seg * db(c.get("gain_db", -11))
    fx_path = stems / "stem_sfx.wav"
    sf.write(fx_path, np.stack([sfx, sfx], 1).astype(np.float32), SR)

    mix = sp + np.stack([music, music], 1) + np.stack([sfx, sfx], 1)
    if np.abs(mix).max() > 0.99:
        mix *= 0.99 / np.abs(mix).max()
    pre = tmp / "premaster.wav"
    sf.write(pre, mix.astype(np.float32), SR)

    m = measure(pre)
    # Aim the WAV below the ceiling: AAC encoding typically adds ~0.5 dB of true peak.
    af = (f"loudnorm=I={a.lufs}:TP={a.tp - 1.0}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
          f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}"
          f":linear=true,alimiter=limit={a.tp - 0.6}dB:level=disabled")
    master = stems / "mix_master.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pre), "-af", af, "-ar", str(SR), str(master)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a.video), "-i", str(master), "-map", "0:v:0",
                    "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                    str(a.out)], check=True)

    speech_i = float(measure(sp_path)["input_i"])
    music_i = float(measure(mu_path)["input_i"]) if a.bed else float("-inf")
    sfx_peak = 20 * np.log10(np.abs(sfx).max()) if sfx.any() else float("-inf")
    fin = measure(a.out)
    fi, ftp = float(fin["input_i"]), float(fin["input_tp"])

    def gate(name, ok, detail):
        print(f"  {'PASS' if ok else 'FAIL'}  {name:26s} {detail}")
    print(f"out {a.out}")
    gate("integrated loudness", abs(fi - a.lufs) <= 0.5, f"{fi:.1f} LUFS (target {a.lufs})")
    gate("true peak (final AAC)", ftp <= a.tp, f"{ftp:.1f} dBTP (ceiling {a.tp})")
    if a.bed:
        gate("music under speech", speech_i - music_i >= 14, f"{speech_i - music_i:.1f} LU (need >= 14)")
    if sfx.any():
        gate("sfx headroom", sfx_peak <= -12, f"{sfx_peak:.1f} dBFS peak (need <= -12)")
    if cut:
        body = mono(sf.read(master, always_2d=True)[0])
        r = lambda x: 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)
        diff = r(body[:cut]) - r(body[cut:])
        gate("cold open not hot", diff <= 2, f"{diff:+.1f} dB vs body (need <= +2)")


if __name__ == "__main__":
    main()
