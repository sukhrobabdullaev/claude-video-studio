#!/usr/bin/env bash
# Run any bundled python script with the right interpreter and the API key loaded.
#
#   bash scripts/vs.sh transcribe.py clip.mov --audio-track 0
#   bash scripts/vs.sh captions.py --edl edit/edl.json ...
#   bash scripts/vs.sh edit/animations/make_label.py     (a script you wrote;
#                                                        path resolves from cwd)
#
# The key lives in ~/.video-studio/.env and is exported here, so the vendored
# helpers find it no matter which directory the edit runs in.
set -euo pipefail

VS_HOME="${VS_HOME:-$HOME/.video-studio}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Windows consoles default to a legacy code page, so any script printing an arrow or
# an em dash dies with UnicodeEncodeError. UTF-8 mode makes output identical on all
# three platforms; it is a no-op where UTF-8 is already the default.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
PY="$VS_HOME/venv/bin/python"

[ -x "$PY" ] || { echo "python env missing — run: bash $SKILL_DIR/scripts/setup.sh" >&2; exit 1; }
if [ -f "$VS_HOME/.env" ]; then set -a; . "$VS_HOME/.env"; set +a; fi

# A bare name is one of the bundled scripts; anything with a slash is a path the
# caller wrote themselves (the graphics workflow tells you to write PIL scripts, and
# they need this same interpreter — the system python has no Pillow).
if [ $# -eq 0 ]; then
  echo "usage: vs.sh <script> [args]" >&2
  echo "bundled: $(cd "$SKILL_DIR/scripts" && ls *.py | tr '\n' ' ')" >&2
  echo "or pass a path to a script you wrote (resolved from the current directory)" >&2
  exit 2
fi

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
