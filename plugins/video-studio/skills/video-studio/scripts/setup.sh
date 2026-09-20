#!/usr/bin/env bash
# Thin bootstrap. The install logic lives in setup.py, shared with Windows.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo "Python 3 is required to run setup. Install it, then re-run." >&2; exit 1; }
exec "$PY" "$DIR/setup.py" "$@"
