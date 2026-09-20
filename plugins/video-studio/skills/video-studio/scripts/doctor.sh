#!/usr/bin/env bash
# Thin bootstrap. The checks live in doctor.py so macOS, Windows and Linux share one.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo "Python 3 is required to run the check." >&2; exit 1; }
exec "$PY" "$DIR/doctor.py" "$@"
