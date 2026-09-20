"""One-time install for video-studio. macOS, Windows and Linux.

Standard library only, because it runs before the project's environment exists.
Safe to re-run: it only does the work that is missing.

Everything writable lives in ~/.video-studio, since the skill directory itself may
be read-only when installed as a plugin.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from platform_paths import (IS_WINDOWS, SKILL_DIR, env_file,  # noqa: E402
                            install_hint, venv_python, vs_home)

PACKAGES = ["numpy", "pillow", "requests", "soundfile"]


def main() -> None:
    print("video-studio setup")
    home = vs_home()
    home.mkdir(parents=True, exist_ok=True)

    missing = [t for t in ("ffmpeg", "uv") if not shutil.which(t)]
    if missing:
        print(f"\nThese are missing: {', '.join(missing)}")
        print("Ask the user before running these — they change the system:\n")
        for tool in missing:
            print(f"    {install_hint(tool)}")
        print("\nThen run this script again.")
        sys.exit(2)

    py = venv_python(home)
    if not py.exists():
        print(f"creating python env at {home / 'venv'}")
        if subprocess.run(["uv", "venv", str(home / "venv")],
                          capture_output=True).returncode:
            sys.exit("FAILED: uv venv")

    if subprocess.run(["uv", "pip", "install", "--quiet", "--python", str(py), *PACKAGES],
                      ).returncode:
        sys.exit("FAILED: uv pip install")
    print(f"python env ready ({len(PACKAGES)} packages)")

    env = env_file(home)
    if not env.exists():
        env.touch()
        if not IS_WINDOWS:
            env.chmod(0o600)

    key_cmd = (f'Add-Content "{env}" "ELEVENLABS_API_KEY=PASTE_KEY_HERE"'
               if IS_WINDOWS else
               f"printf 'ELEVENLABS_API_KEY=%s\\n' \"PASTE_KEY_HERE\" >> {env}")

    print(f"""
SKILL_DIR={SKILL_DIR}
VS_HOME={home}
PYTHON={py}

Next: a transcription key. ASK THE USER which service they already have — any one of
these works and the edit is identical afterwards:

  ElevenLabs  most accurate, speaker labels     ELEVENLABS_API_KEY
  OpenAI      whisper-1, word timing            OPENAI_API_KEY
  Gemini      good text, unreliable timing      GEMINI_API_KEY
  local       free, offline, no key at all      uv pip install --python {py} faster-whisper

The user runs the command themselves so the key never enters the chat transcript. In
the Claude Code desktop app that is the Terminal tab beside the conversation; in the
CLI it is any shell. Swap in the variable name for the service they picked:

    {key_cmd}

Optional, for richer motion graphics (needs Node 22+):
    npx --yes hyperframes@latest skills update
""")


if __name__ == "__main__":
    main()
