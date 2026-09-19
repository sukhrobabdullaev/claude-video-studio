"""Transcribe speech with word-level timing, from whichever provider the user has.

Word-level timing is not a nice-to-have here: every cut edge, every caption cue and
every graphic sync point is derived from it. A provider that only returns segment
or sentence timing cannot drive this pipeline, which is why Gemini is not offered
(its audio docs promise MM:SS segment timestamps, i.e. one-second granularity).

Providers:
  elevenlabs  Scribe. Word timing + speaker diarization + audio events. Paid per minute.
  openai      whisper-1 with timestamp_granularities=["word"]. Paid per minute, 25MB limit.
  local       faster-whisper on this machine. Free, offline, no diarization.

All three are normalized to the same JSON shape, so captions.py, offsets.py and the
bundled pack_transcripts.py never need to know which one produced it:

  {"words": [{"text","start","end","type":"word","speaker_id"}],
   "language_code": "...", "provider": "...", "text": "..."}

    transcribe.py clip.mov --provider auto --audio-track 0
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
OPENAI_LIMIT_BYTES = 25 * 1024 * 1024


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def audio_track_count(video: Path) -> int:
    out = run(["ffprobe", "-v", "error", "-select_streams", "a",
               "-show_entries", "stream=index", "-of", "csv=p=0", str(video)]).stdout
    return len([l for l in out.splitlines() if l.strip()])


def extract_audio(video: Path, track: int, dest: Path, mp3: bool = False) -> Path:
    """16 kHz mono — every ASR downsamples to this anyway, and it keeps uploads small."""
    codec = ["-c:a", "libmp3lame", "-b:a", "64k"] if mp3 else []
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-map", f"0:a:{track}",
           "-ac", "1", "-ar", "16000", *codec, str(dest)]
    r = run(cmd)
    if r.returncode or not dest.exists():
        sys.exit(f"audio extraction failed: {r.stderr.strip()[:400]}")
    return dest


def pick_provider(explicit: str) -> str:
    if explicit != "auto":
        return explicit
    if os.environ.get("ELEVENLABS_API_KEY"):
        return "elevenlabs"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    try:
        import faster_whisper  # noqa: F401
        return "local"
    except ImportError:
        sys.exit(
            "No transcription provider available.\n"
            "  ElevenLabs: put ELEVENLABS_API_KEY in ~/.video-studio/.env\n"
            "  OpenAI:     put OPENAI_API_KEY in ~/.video-studio/.env\n"
            "  Local/free: uv pip install --python ~/.video-studio/venv/bin/python faster-whisper\n"
            "See references/stt.md for the trade-offs."
        )


# ---------------------------------------------------------------- providers

def via_elevenlabs(video: Path, edit_dir: Path, track: int, language: str | None,
                   speakers: int | None) -> dict:
    """Delegate to the bundled video-use helper, which already speaks Scribe."""
    cmd = [sys.executable, str(SKILL_DIR / "scripts/vendor/transcribe.py"), str(video),
           "--edit-dir", str(edit_dir), "--audio-track", str(track)]
    if language:
        cmd += ["--language", language]
    if speakers:
        cmd += ["--num-speakers", str(speakers)]
    r = subprocess.run(cmd)
    if r.returncode:
        sys.exit("elevenlabs transcription failed")
    return json.loads((edit_dir / "transcripts" / f"{video.stem}.json").read_text())


def via_openai(audio: Path, language: str | None) -> dict:
    import requests
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("OPENAI_API_KEY not set (put it in ~/.video-studio/.env)")

    chunks = plan_chunks(audio)
    words: list[dict] = []
    text_parts: list[str] = []
    lang = None
    for offset, part in chunks:
        data = {"model": "whisper-1", "response_format": "verbose_json",
                "timestamp_granularities[]": "word"}
        if language:
            data["language"] = language
        with part.open("rb") as fh:
            resp = requests.post("https://api.openai.com/v1/audio/transcriptions",
                                 headers={"Authorization": f"Bearer {key}"},
                                 data=data, files={"file": (part.name, fh)}, timeout=600)
        if resp.status_code != 200:
            sys.exit(f"openai transcription failed [{resp.status_code}]: {resp.text[:300]}")
        payload = resp.json()
        lang = lang or payload.get("language")
        text_parts.append(payload.get("text", ""))
        for w in payload.get("words", []):
            words.append({"text": w["word"], "start": round(w["start"] + offset, 3),
                          "end": round(w["end"] + offset, 3), "type": "word",
                          "speaker_id": "S0"})
    return {"words": words, "language_code": lang, "text": " ".join(text_parts).strip()}


def plan_chunks(audio: Path) -> list[tuple[float, Path]]:
    """whisper-1 caps uploads at 25MB. Split on time and carry the offset."""
    size = audio.stat().st_size
    if size <= OPENAI_LIMIT_BYTES:
        return [(0.0, audio)]
    dur = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(audio)]).stdout.strip() or 0)
    parts = int(size // OPENAI_LIMIT_BYTES) + 1
    span = dur / parts
    out = []
    for i in range(parts):
        p = audio.with_name(f"{audio.stem}_part{i}{audio.suffix}")
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{i * span:.3f}", "-t", f"{span:.3f}",
             "-i", str(audio), "-c", "copy", str(p)])
        out.append((i * span, p))
    print(f"  audio is {size/1e6:.1f}MB — split into {parts} chunks for the 25MB limit")
    return out


def via_local(audio: Path, language: str | None, model_size: str) -> dict:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is not installed.\n"
                 "  uv pip install --python ~/.video-studio/venv/bin/python faster-whisper\n"
                 "First run also downloads the model (~1GB for medium).")
    print(f"  loading local model '{model_size}' (first run downloads it)")
    model = WhisperModel(model_size, device="auto", compute_type="int8")
    segments, info = model.transcribe(str(audio), language=language, word_timestamps=True)
    words, text = [], []
    for seg in segments:
        text.append(seg.text)
        for w in seg.words or []:
            words.append({"text": w.word.strip(), "start": round(w.start, 3),
                          "end": round(w.end, 3), "type": "word", "speaker_id": "S0"})
    return {"words": words, "language_code": info.language, "text": " ".join(text).strip()}


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--provider", default="auto",
                    choices=["auto", "elevenlabs", "openai", "local"])
    ap.add_argument("--edit-dir", type=Path, help="default: <video parent>/edit")
    ap.add_argument("--audio-track", type=int, default=0,
                    help="0 is usually the mic; iPhone clips carry a 4-channel spatial track "
                         "that ffmpeg would otherwise prefer")
    ap.add_argument("--language", help="ISO code, e.g. uz. Omit to auto-detect")
    ap.add_argument("--num-speakers", type=int, help="elevenlabs only, improves diarization")
    ap.add_argument("--model", default="medium", help="local model size (tiny..large-v3)")
    ap.add_argument("--force", action="store_true", help="re-transcribe even if cached")
    a = ap.parse_args()

    edit_dir = a.edit_dir or a.video.parent / "edit"
    out_path = edit_dir / "transcripts" / f"{a.video.stem}.json"
    if out_path.exists() and not a.force:
        cached = json.loads(out_path.read_text())
        n = len([w for w in cached.get("words", []) if w.get("type") == "word"])
        print(f"cached: {out_path} ({n} words, provider={cached.get('provider','elevenlabs')})")
        print("nothing re-transcribed, nothing charged")
        return

    tracks = audio_track_count(a.video)
    if tracks > 1:
        print(f"  note: {tracks} audio tracks; using track {a.audio_track}. "
              f"On iPhone clips track 0 is the mic and the other is spatial audio.")

    provider = pick_provider(a.provider)
    print(f"provider: {provider}")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if provider == "elevenlabs":
        payload = via_elevenlabs(a.video, edit_dir, a.audio_track, a.language, a.num_speakers)
    else:
        tmp = Path(tempfile.mkdtemp())
        ext = ".mp3" if provider == "openai" else ".wav"
        audio = extract_audio(a.video, a.audio_track, tmp / f"{a.video.stem}{ext}",
                              mp3=(provider == "openai"))
        payload = (via_openai(audio, a.language) if provider == "openai"
                   else via_local(audio, a.language, a.model))

    payload["provider"] = provider
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    words = [w for w in payload.get("words", []) if w.get("type") == "word"]
    if not words:
        sys.exit("no words returned — this provider gave no word-level timing, "
                 "which this pipeline cannot work without (see references/stt.md)")
    span = words[-1]["end"] - words[0]["start"]
    print(f"{len(words)} words, speech {words[0]['start']:.2f}–{words[-1]['end']:.2f}s "
          f"({span:.1f}s), language={payload.get('language_code')}")

    # A transcript far too sparse for the runtime means the model misheard the language
    # rather than that the speaker was quiet. Caught here it costs nothing; caught after
    # the edit is built on it, everything downstream is wrong.
    duration = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(a.video)]).stdout.strip() or 0)
    wpm = len(words) / (duration / 60) if duration else 0
    if duration and wpm < 40:
        print(f"\n  WARNING: only {wpm:.0f} words per minute of video — speech is normally "
              f"100–160.\n  The model probably misheard the language. Try a bigger model "
              f"(--model large-v3),\n  force the language (--language uz), or use a paid "
              f"provider. Small local models\n  are weak on languages outside the top few.")
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()
