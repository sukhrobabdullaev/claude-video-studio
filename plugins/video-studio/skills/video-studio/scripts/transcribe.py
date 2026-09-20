"""Transcribe speech with word-level timing, from whichever provider the user has.

Word-level timing is not a nice-to-have here: every cut edge, every caption cue and
every graphic sync point is derived from it. Providers differ in how well they deliver
it, so every transcript is checked against the audio afterwards — words timed inside
silence mean the numbers are decorative and must not be cut on.

Providers:
  elevenlabs  Scribe. Word timing + speaker diarization + audio events. Paid per minute.
  openai      whisper-1 with timestamp_granularities=["word"]. Paid per minute, 25MB limit.
  gemini      Word timing asked for via a JSON schema. Google documents MM:SS segment
              timestamps, so treat the per-word numbers as best effort and read the
              timing check this script prints before cutting on them.
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
import re
import subprocess
import sys
import tempfile
import time
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
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    try:
        import faster_whisper  # noqa: F401
        return "local"
    except ImportError:
        sys.exit(
            "No transcription provider available.\n"
            "  ElevenLabs: put ELEVENLABS_API_KEY in ~/.video-studio/.env\n"
            "  OpenAI:     put OPENAI_API_KEY in ~/.video-studio/.env\n"
            "  Gemini:     put GEMINI_API_KEY in ~/.video-studio/.env\n"
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


GEMINI_INLINE_LIMIT = 18 * 1024 * 1024      # request must stay under ~20MB total
GEMINI_PROMPT = (
    "Transcribe this audio verbatim, in the language spoken. Return every word "
    "separately with its start and end time in SECONDS from the beginning of the "
    "audio (decimals, e.g. 12.34). Do not translate, do not paraphrase, do not "
    "merge words, do not skip filler words or repetitions. Timing accuracy matters "
    "more than punctuation."
)
GEMINI_SCHEMA = {
    "type": "object",
    "properties": {
        "language": {"type": "string"},
        "words": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"word": {"type": "string"},
                               "start": {"type": "number"},
                               "end": {"type": "number"}},
                "required": ["word", "start", "end"],
            },
        },
    },
    "required": ["words"],
}


def via_gemini(audio: Path, language: str | None, model: str) -> dict:
    """Gemini transcription.

    Google's audio docs describe MM:SS segment timestamps, so word-level timing here
    is the model following a schema rather than a documented guarantee. That is why
    every transcript is timing-checked afterwards: this provider is the one most
    likely to return plausible-looking numbers that do not line up with the audio.
    """
    import base64
    import requests
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not set (put it in ~/.video-studio/.env)")

    prompt = GEMINI_PROMPT + (f" The spoken language is {language}." if language else "")
    size = audio.stat().st_size
    if size <= GEMINI_INLINE_LIMIT:
        part = {"inline_data": {"mime_type": "audio/mpeg",
                                "data": base64.b64encode(audio.read_bytes()).decode()}}
    else:
        print(f"  audio is {size/1e6:.1f}MB — uploading via the Files API")
        up = requests.post(
            f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={key}",
            headers={"X-Goog-Upload-Protocol": "raw", "Content-Type": "audio/mpeg"},
            data=audio.read_bytes(), timeout=600)
        if up.status_code != 200:
            sys.exit(f"gemini file upload failed [{up.status_code}]: {up.text[:300]}")
        part = {"file_data": {"mime_type": "audio/mpeg",
                              "file_uri": up.json()["file"]["uri"]}}

    body = {"contents": [{"parts": [{"text": prompt}, part]}],
            "generationConfig": {"response_mime_type": "application/json",
                                 "response_schema": GEMINI_SCHEMA}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    # 503 "high demand" is common on the flash models and clears on its own.
    for attempt in range(4):
        resp = requests.post(url, json=body, timeout=900)
        if resp.status_code != 503:
            break
        wait = 5 * (attempt + 1)
        print(f"  model busy (503), retrying in {wait}s")
        time.sleep(wait)
    if resp.status_code != 200:
        hint = ""
        if resp.status_code == 404:
            names = requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", timeout=60)
            if names.status_code == 200:
                usable = [m["name"].split("/")[-1] for m in names.json().get("models", [])
                          if "generateContent" in (m.get("supportedGenerationMethods") or [])]
                hint = "\nmodels available to this key: " + ", ".join(usable[:20])
        sys.exit(f"gemini transcription failed [{resp.status_code}]: {resp.text[:300]}{hint}")

    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(text)
    words = [{"text": str(w["word"]).strip(), "start": round(float(w["start"]), 3),
              "end": round(float(w["end"]), 3), "type": "word", "speaker_id": "S0"}
             for w in parsed.get("words", []) if str(w.get("word", "")).strip()]
    return {"words": words, "language_code": parsed.get("language") or language,
            "text": " ".join(w["text"] for w in words)}


def check_timing(video: Path, words: list[dict], duration: float, track: int) -> list[str]:
    """Does this transcript's timing actually match the audio?

    Cheap and provider-agnostic: real speech does not happen during silence. If a large
    share of words is timed inside detected silence, or the times run backwards, the
    numbers are decorative and cutting on them will slice mid-word.
    """
    problems = []
    starts = [w["start"] for w in words]
    if any(b < a for a, b in zip(starts, starts[1:])):
        problems.append("word times run backwards in places")
    if duration and max(w["end"] for w in words) > duration + 1.0:
        problems.append("words are timed past the end of the audio")

    out = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(video), "-map", f"0:a:{track}",
         "-af", "silencedetect=noise=-35dB:d=0.4", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    del out  # silence spans alone are too weak a signal; see below

    # Cross-correlate "where words claim to be" against "where sound actually is".
    # A silence-overlap test is not enough: dense speech has few long gaps, so a
    # transcript shifted by a whole second still lands almost every word on speech.
    # Correlation catches both failures at once — a constant offset appears as a
    # non-zero best lag, invented timing as no correlation at any lag.
    import numpy as np
    hop = 0.02
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-map", f"0:a:{track}",
         "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        capture_output=True).stdout
    pcm = np.frombuffer(raw, np.int16).astype(np.float32)
    if pcm.size < 16000:
        return problems
    per = int(16000 * hop)
    energy = np.sqrt((pcm[: (pcm.size // per) * per].reshape(-1, per) ** 2).mean(axis=1))
    energy = energy / (energy.max() + 1e-9)
    mask = np.zeros_like(energy)
    for w in words:
        a = int(w["start"] / hop)
        b = int(min(w["end"], len(energy) * hop) / hop)
        if 0 <= a < len(mask):
            mask[a:max(b, a + 1)] = 1.0

    e, m = energy - energy.mean(), mask - mask.mean()
    denom = (np.linalg.norm(e) * np.linalg.norm(m)) or 1e-9
    max_lag = int(2.0 / hop)
    lags = list(range(-max_lag, max_lag + 1))
    corrs = [float(np.dot(np.roll(m, k), e) / denom) for k in lags]
    best_i = int(np.argmax(corrs))
    best_lag_s, best_corr, zero_corr = lags[best_i] * hop, corrs[best_i], corrs[max_lag]

    if best_corr < 0.15:
        problems.append(f"word times do not track the audio at any offset "
                        f"(best correlation {best_corr:.2f}) — this timing is invented")
    elif abs(best_lag_s) > 0.15:
        problems.append(f"the transcript is offset by about {best_lag_s*1000:+.0f} ms "
                        f"(correlation {zero_corr:.2f} as given, {best_corr:.2f} shifted)")
    return problems


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

def report_timing(video: Path, words: list[dict], track: int) -> bool:
    """Run the timing check and print the verdict. True when the timing is usable."""
    duration = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(video)]).stdout.strip() or 0)
    problems = check_timing(video, words, duration, track)
    if problems:
        print("\n  TIMING CHECK FAILED:")
        for pr in problems:
            print(f"   - {pr}")
        print("  Do not cut on these timings. Captions would drift and cuts would land "
              "mid-word.\n  Use a provider with documented word-level output "
              "(elevenlabs, openai, local) for the cut.")
        return False
    print("  timing check: words line up with the audio")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--provider", default="auto",
                    choices=["auto", "elevenlabs", "openai", "gemini", "local"])
    ap.add_argument("--gemini-model", default="gemini-flash-latest",
                    help="override if the key has no access; a 404 lists what it can use")
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
        words = [w for w in cached.get("words", []) if w.get("type") == "word"]
        print(f"cached: {out_path} ({len(words)} words, "
              f"provider={cached.get('provider', 'elevenlabs')})")
        print("nothing re-transcribed, nothing charged")
        # The cache is the common path, so skipping the timing check here would mean
        # the check almost never runs — including on a transcript produced by some
        # earlier tool with no timing guarantees at all.
        report_timing(a.video, words, a.audio_track)
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
        compressed = provider in ("openai", "gemini")
        ext = ".mp3" if compressed else ".wav"
        audio = extract_audio(a.video, a.audio_track, tmp / f"{a.video.stem}{ext}",
                              mp3=compressed)
        if provider == "openai":
            payload = via_openai(audio, a.language)
        elif provider == "gemini":
            payload = via_gemini(audio, a.language, a.gemini_model)
        else:
            payload = via_local(audio, a.language, a.model)

    payload["provider"] = provider
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    words = [w for w in payload.get("words", []) if w.get("type") == "word"]
    if not words:
        sys.exit("no words returned — this provider gave no word-level timing, "
                 "which this pipeline cannot work without (see references/stt.md)")
    span = words[-1]["end"] - words[0]["start"]
    print(f"{len(words)} words, speech {words[0]['start']:.2f}–{words[-1]['end']:.2f}s "
          f"({span:.1f}s), language={payload.get('language_code')}")

    report_timing(a.video, words, a.audio_track)

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
