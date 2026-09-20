#!/usr/bin/env bash
# Thin bootstrap. The install logic lives in setup.py, shared with Windows.
# No system Python needed: uv brings its own when none is installed.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Windows consoles default to a legacy code page, so any script printing an arrow or
# an em dash dies with UnicodeEncodeError. UTF-8 mode makes output identical on all
# three platforms; it is a no-op where UTF-8 is already the default.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
if PY="$(command -v python3 || command -v python)"; then
  exec "$PY" "$DIR/setup.py" "$@"
elif command -v uv >/dev/null; then
  exec uv run --no-project --python 3.12 "$DIR/setup.py" "$@"
else
  echo "Install uv first, then re-run this script:" >&2
  case "$(uname -s)" in
    Darwin) echo "    brew install uv" >&2 ;;
    *)      echo "    curl -LsSf https://astral.sh/uv/install.sh | sh" >&2 ;;
  esac
  exit 1
fi
