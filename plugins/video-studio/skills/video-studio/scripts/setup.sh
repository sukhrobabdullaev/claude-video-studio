#!/usr/bin/env bash
# One-time install for video-studio. Safe to re-run: it only does missing work.
#
# Everything that must be writable lives in ~/.video-studio (the skill directory
# itself may be read-only), so this creates the Python environment there.
set -uo pipefail

VS_HOME="${VS_HOME:-$HOME/.video-studio}"
VENV="$VS_HOME/venv"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "video-studio setup"
mkdir -p "$VS_HOME"

need_brew=()
command -v ffmpeg >/dev/null || need_brew+=(ffmpeg)
command -v uv >/dev/null || need_brew+=(uv)

if [ ${#need_brew[@]} -gt 0 ]; then
  if ! command -v brew >/dev/null; then
    echo "MISSING: ${need_brew[*]}, and Homebrew is not installed."
    echo "Install Homebrew first: https://brew.sh   then re-run this script."
    exit 1
  fi
  echo "These need installing: ${need_brew[*]}"
  echo "Run (ask the user first — it changes their system):"
  echo "    brew install ${need_brew[*]}"
  exit 2
fi

if [ ! -x "$VENV/bin/python" ]; then
  echo "creating python env at $VENV"
  uv venv "$VENV" >/dev/null || { echo "FAILED: uv venv"; exit 1; }
fi
# Only the four packages the vendored helpers and our scripts actually import.
VIRTUAL_ENV="$VENV" uv pip install --quiet numpy pillow requests soundfile \
  || { echo "FAILED: uv pip install"; exit 1; }
echo "python env ready"

if [ ! -f "$VS_HOME/.env" ]; then
  touch "$VS_HOME/.env"
  chmod 600 "$VS_HOME/.env"
fi

echo
echo "SKILL_DIR=$SKILL_DIR"
echo "VS_HOME=$VS_HOME"
echo "PYTHON=$VENV/bin/python"
echo
echo "Next: the ElevenLabs key (transcription). The user runs this in THEIR OWN terminal,"
echo "so the key never goes through the chat transcript:"
echo
echo "    printf 'ELEVENLABS_API_KEY=%s\\n' \"PASTE_KEY_HERE\" > $VS_HOME/.env && chmod 600 $VS_HOME/.env"
echo
echo "Optional, for richer motion graphics (needs Node 22+):"
echo "    npx --yes hyperframes@latest skills update"
