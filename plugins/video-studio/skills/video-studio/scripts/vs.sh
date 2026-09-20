#!/usr/bin/env bash
# Run any bundled python script with the right interpreter and the API key loaded.
#
#   bash scripts/vs.sh vendor/transcribe.py clip.mov --audio-track 0
#   bash scripts/vs.sh captions.py --edl edit/edl.json ...
#
# The key lives in ~/.video-studio/.env and is exported here, so the vendored
# helpers find it no matter which directory the edit runs in.
set -euo pipefail

VS_HOME="${VS_HOME:-$HOME/.video-studio}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$VS_HOME/venv/bin/python"

[ -x "$PY" ] || { echo "python env missing — run: bash $SKILL_DIR/scripts/setup.sh" >&2; exit 1; }
if [ -f "$VS_HOME/.env" ]; then set -a; . "$VS_HOME/.env"; set +a; fi

# A bare name is one of the bundled scripts; anything with a slash is a path the
# caller wrote themselves (the graphics workflow tells you to write PIL scripts, and
# they need this same interpreter — the system python has no Pillow).
script="$1"; shift
if [ -f "$SKILL_DIR/scripts/$script" ]; then
  exec "$PY" "$SKILL_DIR/scripts/$script" "$@"
elif [ -f "$script" ]; then
  exec "$PY" "$script" "$@"
else
  echo "no such script: $script" >&2
  echo "bundled scripts: $(cd "$SKILL_DIR/scripts" && ls *.py | tr '\n' ' ')" >&2
  exit 1
fi
