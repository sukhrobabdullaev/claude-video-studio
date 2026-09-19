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

script="$1"; shift
exec "$PY" "$SKILL_DIR/scripts/$script" "$@"
