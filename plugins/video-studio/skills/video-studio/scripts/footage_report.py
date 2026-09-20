"""Objective report on raw footage, before any editing decision is made.

An editor watches the material first and forms an opinion: is it sharp, is it shaky,
is the exposure blown, where are the pauses, how noisy is the room. This measures
those things so the plan is grounded in the footage rather than in assumptions —
and so the edit can compensate (heavy shake argues for shorter shots; soft focus
argues against punching in; a high noise floor argues for a quieter music bed).

Nothing here passes or fails. It describes.

    footage_report.py clip.mov [--out edit/footage_report.json] [--quick]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np

ANALYSIS_W = 320          # everything is measured on a downscale; 320px is plenty
SHAKE_FPS = 4


def sh(cmd: list[str]) -> str:
    """ffmpeg reports measurements on stderr; return both streams together."""
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout or "") + (r.stderr or "")


def probe(video: Path) -> dict:
    j = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)],
        capture_output=True, text=True).stdout or "{}")
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = [s for s in j.get("streams", []) if s.get("codec_type") == "audio"]
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    rot = 0
    for sd in v.get("side_data_list") or []:
        if sd.get("rotation") is not None:
            rot = int(round(float(sd["rotation"])))
    disp_w, disp_h = (h, w) if rot % 180 else (w, h)
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den or 0) else 0.0
    return {
        "stored": f"{w}x{h}", "rotation": rot, "displayed": f"{disp_w}x{disp_h}",
        "aspect": round(disp_w / disp_h, 3) if disp_h else 0,
        "orientation": "vertical" if disp_h > disp_w else ("square" if disp_h == disp_w else "horizontal"),
        "fps": round(fps, 3),
        "duration_s": round(float(j.get("format", {}).get("duration", 0)), 3),
        "video_bitrate_mbps": round(int(v.get("bit_rate", 0)) / 1e6, 2) if v.get("bit_rate") else None,
        "audio_tracks": [{"index": i, "codec": s.get("codec_name"),
                          "channels": s.get("channels"), "sample_rate": s.get("sample_rate")}
                         for i, s in enumerate(audio)],
        "mic_track_hint": 0 if len(audio) > 1 else 0,
    }


def picture_stats(video: Path, fps: float = 2.0) -> dict:
    out = sh(["ffmpeg", "-v", "info", "-i", str(video), "-an",
              "-vf", f"scale={ANALYSIS_W}:-2,fps={fps},signalstats,blurdetect,metadata=print:file=-",
              "-f", "null", "-"])
    vals = {k: [] for k in ("YMIN", "YMAX", "YAVG", "SATAVG", "blur")}
    for line in out.splitlines():
        m = re.search(r"lavfi\.signalstats\.(YMIN|YMAX|YAVG|SATAVG)=([-\d.]+)", line)
        if m:
            vals[m.group(1)].append(float(m.group(2)))
        m = re.search(r"lavfi\.blur=([-\d.]+)", line)
        if m:
            vals["blur"].append(float(m.group(1)))
    def stat(key, f=np.mean):
        return round(float(f(vals[key])), 2) if vals[key] else None
    n = max(len(vals["YMAX"]), 1)
    return {
        "frames_sampled": len(vals["YAVG"]),
        "luma_avg": stat("YAVG"),
        "luma_min": stat("YMIN", np.min),
        "luma_max": stat("YMAX", np.max),
        "highlight_clipping_pct": round(100 * sum(1 for v in vals["YMAX"] if v >= 254) / n, 1),
        "shadow_crush_pct": round(100 * sum(1 for v in vals["YMIN"] if v <= 1) / n, 1),
        "saturation_avg": stat("SATAVG"),
        "blur_score_avg": stat("blur"),
        "blur_score_worst": stat("blur", np.max),
    }


def events(video: Path) -> dict:
    out = sh(["ffmpeg", "-v", "info", "-i", str(video), "-an",
              "-vf", f"scale={ANALYSIS_W}:-2,scdet=threshold=10,blackdetect=d=0.2:pix_th=0.10,"
                     f"freezedetect=n=-60dB:d=0.5,cropdetect=24:2:0,metadata=print:file=-",
              "-f", "null", "-"])
    scenes = [round(float(m), 2) for m in re.findall(r"lavfi\.scd\.time=([\d.]+)", out)]
    crops = Counter(re.findall(r"crop=(\d+:\d+:\d+:\d+)", out))
    return {
        "scene_changes": scenes,
        "scene_change_count": len(scenes),
        "black_segments": len(re.findall(r"black_start:", out)),
        "freeze_segments": len(re.findall(r"freeze_start:", out)),
        "suggested_crop": crops.most_common(1)[0][0] if crops else None,
    }


def sound(video: Path, track: int = 0) -> dict:
    out = sh(["ffmpeg", "-v", "info", "-i", str(video), "-map", f"0:a:{track}",
              "-af", "silencedetect=noise=-35dB:d=0.25,astats=measure_perchannel=none",
              "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: ([-\d.]+)", out)]
    durs = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", out)]
    def number(text: str, label: str):
        """ffmpeg prints '-inf' or a bare '-' for digital silence, so a match is not
        the same as a number. Returning None keeps the report honest instead of
        crashing on a clip with a muted stretch."""
        m = re.search(rf"{label}:\s*(-?\d+(?:\.\d+)?|-?inf)", text)
        if not m:
            return None
        try:
            v = float(m.group(1))
        except ValueError:
            return None
        return round(v, 1) if v == v and abs(v) != float("inf") else None

    def grab(label):
        return number(out, label)
    loud = sh(["ffmpeg", "-v", "info", "-i", str(video), "-map", f"0:a:{track}",
               "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=summary", "-f", "null", "-"])
    def loudval(label):
        return number(loud, label)
    return {
        "silence_count": len(durs),
        "silence_total_s": round(sum(durs), 2),
        "longest_silence_s": round(max(durs), 2) if durs else 0.0,
        "silence_starts": [round(s, 2) for s in starts[:40]],
        "rms_level_db": grab("RMS level dB"),
        "peak_level_db": grab("Peak level dB"),
        "noise_floor_db": grab("Noise floor dB"),
        "integrated_lufs": loudval("Input Integrated"),
        "true_peak_dbtp": loudval("Input True Peak"),
    }


def shake(video: Path, basic: dict) -> dict:
    """Global camera motion by FFT phase correlation — the same trick track_box.py
    uses to pin a highlight to a moving target. This build has no vidstab.

    Dimensions come from the DISPLAYED size: ffmpeg autorotates before filtering, so
    a phone clip stored 1920x1080 arrives here as 1080x1920 and the raw frame buffer
    is sized accordingly. Using the stored size misreads every frame boundary.
    """
    w = ANALYSIS_W
    disp_w, disp_h = (int(x) for x in basic["displayed"].split("x"))
    h = int(round(w * disp_h / disp_w / 2) * 2)   # matches scale=W:-2 rounding
    sw = disp_w                                   # analysis px -> source px
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-an",
         "-vf", f"scale={w}:-2,fps={SHAKE_FPS},format=gray", "-f", "rawvideo", "-"],
        capture_output=True).stdout
    frame_size = w * h
    n = len(raw) // frame_size if frame_size else 0
    if n < 3:
        return {"frames": n, "median_px_per_s": None, "max_px_per_s": None,
                "note": "too few frames to measure motion"}
    frames = [np.frombuffer(raw[i*frame_size:(i+1)*frame_size], np.uint8).reshape(h, w).astype(float)
              for i in range(n)]
    win = np.hanning(h)[:, None] * np.hanning(w)[None, :]
    mags = []
    for a, b in zip(frames, frames[1:]):
        F = np.fft.fft2((a - a.mean()) * win) * np.conj(np.fft.fft2((b - b.mean()) * win))
        F /= np.abs(F) + 1e-9
        c = np.fft.ifft2(F).real
        iy, ix = np.unravel_index(np.argmax(c), c.shape)
        dy = iy - h if iy > h // 2 else iy
        dx = ix - w if ix > w // 2 else ix
        # back to source pixels, per second
        mags.append(float(np.hypot(dx, dy)) * (sw / w) * SHAKE_FPS)
    return {"frames": n,
            "median_px_per_s": round(float(np.median(mags)), 1),
            "max_px_per_s": round(float(np.max(mags)), 1)}


def read(report: dict) -> list[str]:
    """Turn numbers into the two or three things that actually change the edit."""
    notes = []
    p, s, snd = report["picture"], report["shake"], report["sound"]
    if p.get("highlight_clipping_pct", 0) > 5:
        notes.append(f"Highlights clip on {p['highlight_clipping_pct']}% of sampled frames — "
                     f"avoid lifting exposure; a bright screen or window is blowing out.")
    if p.get("luma_avg") is not None and p["luma_avg"] < 60:
        notes.append(f"Dark footage (avg luma {p['luma_avg']}) — a gentle lift helps, "
                     f"but grading hard will bring up noise.")
    if s.get("median_px_per_s") and s["median_px_per_s"] > 60:
        notes.append(f"Handheld and lively ({s['median_px_per_s']} px/s median motion) — "
                     f"shorter shots hide it; static overlays will drift, so track them.")
    if snd.get("noise_floor_db") is not None and snd["noise_floor_db"] > -50:
        notes.append(f"Noise floor {snd['noise_floor_db']} dB is audible — "
                     f"keep any music bed quiet or it will mask the voice.")
    if snd.get("integrated_lufs") is not None and snd["integrated_lufs"] < -20:
        notes.append(f"Source is quiet ({snd['integrated_lufs']} LUFS) — "
                     f"it needs normalizing to about -14 LUFS for social.")
    if snd.get("silence_total_s", 0) > 5:
        notes.append(f"{snd['silence_total_s']}s of silence across {snd['silence_count']} gaps — "
                     f"this is where the runtime gets shorter without losing content.")
    if report["basic"]["rotation"]:
        notes.append(f"Rotation {report['basic']['rotation']}° — it is stored "
                     f"{report['basic']['stored']} but plays {report['basic']['displayed']}. "
                     f"Compute every crop in displayed coordinates.")
    if len(report["basic"]["audio_tracks"]) > 1:
        notes.append("More than one audio track — transcribe the mic track explicitly "
                     "(--audio-track 0), or ffmpeg picks the one with most channels.")
    return notes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path, help="default: <video parent>/edit/footage_report.json")
    ap.add_argument("--audio-track", type=int, default=0)
    ap.add_argument("--quick", action="store_true", help="skip shake and event passes")
    a = ap.parse_args()

    basic = probe(a.video)
    report = {"file": str(a.video), "basic": basic,
              "picture": picture_stats(a.video),
              "sound": sound(a.video, a.audio_track)}
    report["events"] = {} if a.quick else events(a.video)
    report["shake"] = {} if a.quick else shake(a.video, basic)
    report["reading"] = read(report)

    out = a.out or a.video.parent / "edit" / "footage_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))

    b, p, s, e, k = basic, report["picture"], report["sound"], report["events"], report["shake"]
    print(f"{a.video.name}")
    print(f"  picture   {b['displayed']} {b['orientation']} · {b['fps']} fps · "
          f"{b['duration_s']}s · {b['video_bitrate_mbps']} Mbps"
          + (f" · rotation {b['rotation']}°" if b["rotation"] else ""))
    print(f"  exposure  luma {p['luma_avg']} (min {p['luma_min']}, max {p['luma_max']}) · "
          f"clipping {p['highlight_clipping_pct']}% · saturation {p['saturation_avg']}")
    print(f"  focus     blur score avg {p['blur_score_avg']} (worst {p['blur_score_worst']})")
    if k:
        print(f"  motion    median {k['median_px_per_s']} px/s, peak {k['max_px_per_s']} px/s")
    if e:
        print(f"  cuts      {e['scene_change_count']} scene changes · "
              f"black {e['black_segments']} · frozen {e['freeze_segments']} · crop {e['suggested_crop']}")
    print(f"  sound     {s['integrated_lufs']} LUFS · peak {s['peak_level_db']} dB · "
          f"noise floor {s['noise_floor_db']} dB")
    print(f"  pauses    {s['silence_count']} gaps, {s['silence_total_s']}s total, "
          f"longest {s['longest_silence_s']}s")
    if report["reading"]:
        print("\n  what this means for the edit:")
        for line in report["reading"]:
            print(f"   - {line}")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
