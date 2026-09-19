#!/usr/bin/env bash
# Preflight for video-studio: PASS / WARN / FAIL plus the exact fix for each line.
# Exit 0 when nothing is FAIL.

VS_HOME="${VS_HOME:-$HOME/.video-studio}"
VENV="$VS_HOME/venv"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0

pass() { printf '  PASS  %s\n' "$1"; }
warn() { printf '  WARN  %s\n        -> %s\n' "$1" "$2"; }
bad()  { printf '  FAIL  %s\n        -> %s\n' "$1" "$2"; fail=1; }

echo "video-studio preflight"

if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null; then
  pass "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}')"
  filters="$(ffmpeg -hide_banner -filters 2>/dev/null)"
  grep -qE '^ .* subtitles ' <<<"$filters" \
    && pass "ffmpeg has libass" \
    || warn "ffmpeg built without libass (no subtitles/drawtext filter)" \
            "nothing to do — captions.py rasterizes captions instead"
  grep -qE '^ .* prores_ks ' <<<"$(ffmpeg -hide_banner -encoders 2>/dev/null)" \
    && pass "prores_ks encoder (transparent overlays)" \
    || bad "no prores_ks encoder" "brew reinstall ffmpeg"
else
  bad "ffmpeg/ffprobe not installed" "brew install ffmpeg"
fi

command -v uv >/dev/null && pass "uv $(uv --version | awk '{print $2}')" \
  || bad "uv not installed" "brew install uv"

if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c "import numpy, PIL, requests, soundfile" 2>/dev/null; then
  pass "python env at $VENV"
else
  bad "python env missing or incomplete" "bash $SKILL_DIR/scripts/setup.sh"
fi

if [ -f "$SKILL_DIR/scripts/vendor/render.py" ] && [ -f "$SKILL_DIR/scripts/vendor/transcribe.py" ]; then
  pass "bundled editing engine (video-use, MIT)"
else
  bad "bundled engine missing from scripts/vendor" "reinstall the skill"
fi

# Transcription needs word-level timing; any one of these three provides it.
stt=""
has_key() { grep -qE "^$1=.{10,}" "$VS_HOME/.env" 2>/dev/null || [ -n "${!1:-}" ]; }
has_key ELEVENLABS_API_KEY && stt="$stt elevenlabs"
has_key OPENAI_API_KEY && stt="$stt openai"
has_key GEMINI_API_KEY && stt="$stt gemini"
"$VENV/bin/python" -c "import faster_whisper" 2>/dev/null && stt="$stt local"
if [ -n "$stt" ]; then
  pass "transcription:$stt"
else
  bad "no transcription provider (word-level timing is required)" \
      "one of:
             printf 'ELEVENLABS_API_KEY=%s\\n' \"KEY\" > $VS_HOME/.env   (paid, diarization)
             printf 'OPENAI_API_KEY=%s\\n' \"KEY\" >> $VS_HOME/.env      (paid, whisper-1)
             printf 'GEMINI_API_KEY=%s\\n' \"KEY\" >> $VS_HOME/.env      (paid, timing is best-effort)
             uv pip install --python $VENV/bin/python faster-whisper  (free, offline)
           see references/stt.md"
fi

if [ -f "$HOME/.claude/skills/hyperframes/SKILL.md" ]; then
  pass "HyperFrames skills (rich motion graphics)"
else
  warn "HyperFrames not installed — graphics fall back to the bundled PIL renderer" \
       "optional: npx --yes hyperframes@latest skills update  (needs Node 22+)"
fi

echo
[ "$fail" -eq 0 ] && echo "READY" || echo "NOT READY — fix the FAIL lines"
exit "$fail"
