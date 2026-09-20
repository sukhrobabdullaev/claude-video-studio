#!/usr/bin/env bash
# Thin bootstrap. The checks live in doctor.py so all three platforms share one.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="${VS_HOME:-$HOME/.video-studio}/venv/bin/python"
if [ -x "$VENV_PY" ]; then
  exec "$VENV_PY" "$DIR/doctor.py" "$@"
elif PY="$(command -v python3 || command -v python)"; then
  exec "$PY" "$DIR/doctor.py" "$@"
elif command -v uv >/dev/null; then
  exec uv run --no-project --python 3.12 "$DIR/doctor.py" "$@"
else
  echo "  FAIL  neither a python nor uv is installed" >&2
  echo "        -> install uv, then run scripts/setup.sh" >&2
  exit 1
fi
