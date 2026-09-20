"""End-to-end smoke test on a synthetic clip. No API calls, no user footage.

Every bundled script is exercised against a clip this script generates, so the
whole chain can be verified on a fresh machine — including a Windows one — in
about a minute, without spending a transcription credit or touching real video.

    bash   scripts/vs.sh  selftest.py
    pwsh -File scripts\\vs.ps1 selftest.py

Exit code is 0 only when every step passes.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from platform_paths import describe  # noqa: E402

FPS = 30
CLIP_S = 6.0
# Four "words" placed inside the four tone bursts the clip contains, so timing
# checks and caption placement have something real to agree with.
WORDS = [(0.40, 1.10), (1.30, 2.00), (3.20, 3.90), (4.10, 4.80)]

results: list[tuple[str, bool, str]] = []


def step(name: str):
    def wrap(fn):
        try:
            detail = fn() or ""
            results.append((name, True, detail))
        except Exception as e:                       # noqa: BLE001
            results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


def run(cmd: list[str], **kw) -> str:
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[:300])
    return (r.stdout or "") + (r.stderr or "")


def py(script: str, *args) -> str:
    return run([sys.executable, HERE / script, *args])


def main() -> int:
    print(f"video-studio selftest\n  {describe()}\n")
    tmp = Path(tempfile.mkdtemp(prefix="vs_selftest_"))
    edit = tmp / "edit"
    (edit / "transcripts").mkdir(parents=True)
    clip = tmp / "clip.mp4"

    @step("synthetic clip")
    def _clip():
        # Vertical, with four tone bursts separated by silence.
        gate = "+".join(f"between(t,{a},{b})" for a, b in WORDS)
        run(["ffmpeg", "-v", "error", "-y",
             "-f", "lavfi", "-i", f"testsrc2=size=1080x1920:rate={FPS}:duration={CLIP_S}",
             "-f", "lavfi", "-i", f"sine=frequency=220:duration={CLIP_S}:sample_rate=48000",
             "-filter_complex", f"[1:a]volume='0.6*({gate})':eval=frame[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "ultrafast",
             "-crf", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", clip])
        return f"{CLIP_S}s 1080x1920"

    @step("transcript fixture")
    def _tr():
        words = [{"text": t, "start": a, "end": b, "type": "word", "speaker_id": "S0"}
                 for (a, b), t in zip(WORDS, ["birinchi", "ikkinchi", "uchinchi", "to'rtinchi"])]
        (edit / "transcripts" / "clip.json").write_text(json.dumps(
            {"words": words, "language_code": "uz", "provider": "fixture",
             "text": " ".join(w["text"] for w in words)}, ensure_ascii=False))
        return "4 words"

    @step("footage_report.py")
    def _report():
        py("footage_report.py", clip, "--out", edit / "footage_report.json")
        d = json.loads((edit / "footage_report.json").read_text())
        assert d["basic"]["displayed"] == "1080x1920", d["basic"]
        assert d["sound"]["silence_count"] >= 1, "no silence detected in a clip built with gaps"
        assert d["shake"]["median_px_per_s"] is not None
        return f"{d['basic']['displayed']}, {d['sound']['silence_count']} gaps"

    @step("transcribe.py cache + timing check")
    def _tc():
        out = py("transcribe.py", clip, "--edit-dir", edit)
        assert "nothing re-transcribed" in out, out
        assert "timing check" in out, "cache path skipped the timing check"
        return "cache hit, timing verdict printed"

    @step("vendor/render.py")
    def _render():
        edl = {"version": 1, "sources": {"clip": str(clip)},
               "ranges": [{"source": "clip", "start": 0.30, "end": 2.10, "beat": "A"},
                          {"source": "clip", "start": 3.10, "end": 4.90, "beat": "B"}]}
        (edit / "edl.json").write_text(json.dumps(edl))
        py("vendor/render.py", edit / "edl.json", "-o", edit / "cut.mp4",
           "--draft", "--fps", str(FPS), "--no-subtitles", "--no-loudnorm")
        assert (edit / "cut.mp4").exists()
        return "2 ranges concatenated"

    @step("offsets.py")
    def _offsets():
        out = py("offsets.py", "--edl", edit / "edl.json", "--out", edit / "offsets.json")
        rows = json.loads((edit / "offsets.json").read_text())
        assert len(rows) == 2, rows
        assert rows[0]["out_start"] == 0.0
        return out.strip().splitlines()[-2].split("->")[0].strip()

    @step("captions.py")
    def _captions():
        out = py("captions.py", "--edl", edit / "edl.json", "--offsets", edit / "offsets.json",
                 "--transcripts", edit / "transcripts", "--out", edit / "captions.mov",
                 "--fps", str(FPS))
        drift = float(out.split("drift")[1].split("s")[0])
        assert abs(drift) <= 1.0 / FPS, f"caption drift {drift}s exceeds one frame"
        assert (edit / "captions.mov").exists()
        return f"drift {drift:+.3f}s"

    @step("bundled fonts render")
    def _fonts():
        from platform_paths import load_font
        f = load_font("sans", 64)
        assert f.getlength("QA TESTER o'zi g'alaba") > 0
        m = load_font("mono", 32)
        assert m.getlength("> verify e2e") > 0
        return "Inter + JetBrains Mono, Uzbek glyphs present"

    @step("synth_audio.py")
    def _synth():
        py("synth_audio.py", "--out", edit / "audio", "--duration", "8")
        made = sorted(p.name for p in (edit / "audio").glob("*.wav"))
        assert len(made) == 6, made
        return f"{len(made)} files"

    @step("mix.py")
    def _mix():
        cues = [{"file": "tick.wav", "at": 1.0, "gain_db": -17}]
        (edit / "cues.json").write_text(json.dumps(cues))
        out = py("mix.py", "--video", edit / "cut.mp4", "--bed", edit / "audio/music_bed.wav",
                 "--sfx-dir", edit / "audio", "--cues", edit / "cues.json",
                 "--out", edit / "final.mp4", "--stems", edit / "stems")
        assert "FAIL" not in out, out
        assert (edit / "final.mp4").exists()
        loud = [l for l in out.splitlines() if "integrated loudness" in l][0]
        return loud.split("integrated loudness")[1].strip()

    @step("check_boundaries.py")
    def _bounds():
        r = subprocess.run([sys.executable, HERE / "check_boundaries.py",
                            "--video", edit / "final.mp4", "--offsets", edit / "offsets.json"],
                           capture_output=True, text=True)
        assert "PASS" in r.stdout, r.stdout + r.stderr
        return r.stdout.strip().splitlines()[-1]

    @step("track_box.py")
    def _track():
        py("track_box.py", "--video", clip, "--rect", "200", "400", "800", "900",
           "--window", "0.5", "1.5", "--ref", "1.0", "--out", edit / "box.mov",
           "--fps", str(FPS))
        assert (edit / "box.mov").exists()
        return "motion-tracked overlay rendered"

    @step("to_prores.py alpha")
    def _prores():
        png = edit / "card.png"
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
        ImageDraw.Draw(img).rounded_rectangle((20, 20, 380, 180), 12, fill=(10, 10, 10, 230))
        img.save(png)
        webm = edit / "card.webm"
        run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", png, "-t", "1",
             "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "30", webm])
        out = py("to_prores.py", webm, edit / "card.mov")
        assert "yuva444p12le" in out, out
        return "alpha preserved"

    @step("cover.py")
    def _cover():
        frame = edit / "frame.jpg"
        run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", clip, "-frames:v", "1", frame])
        out = py("cover.py", "--frame", frame, "--line1", "QA TESTER",
                 "--line2", "KERAK EMAS", "--kicker", "TEST", "--chip", "> e2e",
                 "--out", edit / "cover.jpg")
        assert (edit / "cover.jpg").exists()
        return out.strip().split("|", 1)[1].strip()

    for name, passed, detail in results:
        print(f"  {'PASS' if passed else 'FAIL'}  {name:34} {detail}")
    bad = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} passed" + (f" — FAILED: {bad}" if bad else ""))
    print(f"workspace: {tmp}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
