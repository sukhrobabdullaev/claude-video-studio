"""Preflight for video-studio. Runs on macOS, Windows and Linux, on any Python 3.

Standard library only and no dependency on the project's own environment, because
its whole job is to tell you when that environment is missing.

Exit 0 when nothing is FAIL.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from platform_paths import (BUNDLED, IS_WINDOWS, SKILL_DIR, env_file,  # noqa: E402
                            install_hint, venv_python, vs_home)

fail = 0


def ok(msg): print(f"  PASS  {msg}")
def warn(msg, fix): print(f"  WARN  {msg}\n        -> {fix}")
def bad(msg, fix):
    global fail
    fail = 1
    print(f"  FAIL  {msg}\n        -> {fix}")


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def ffmpeg_has(kind: str, name: str) -> bool:
    out = subprocess.run(["ffmpeg", "-hide_banner", f"-{kind}"],
                         capture_output=True, text=True).stdout
    return any(line.split()[1:2] == [name] for line in out.splitlines() if line.strip())


def main() -> None:
    print("video-studio preflight")
    home = vs_home()
    py = venv_python(home)

    if have("ffmpeg") and have("ffprobe"):
        ver = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout
        ok(f"ffmpeg {ver.split()[2] if len(ver.split()) > 2 else ''}")
        if ffmpeg_has("filters", "subtitles"):
            ok("ffmpeg has libass")
        else:
            warn("ffmpeg built without libass (no subtitles/drawtext filter)",
                 "nothing to do — captions.py rasterizes captions instead")
        if ffmpeg_has("encoders", "prores_ks"):
            ok("prores_ks encoder (transparent overlays)")
        else:
            bad("no prores_ks encoder", install_hint("ffmpeg") + " (a fuller build)")
    else:
        bad("ffmpeg/ffprobe not installed", install_hint("ffmpeg"))

    if have("uv"):
        ok("uv " + subprocess.run(["uv", "--version"], capture_output=True,
                                  text=True).stdout.split()[-1])
    else:
        bad("uv not installed", install_hint("uv"))

    if py.exists() and subprocess.run(
            [str(py), "-c", "import numpy, PIL, requests, soundfile"],
            capture_output=True).returncode == 0:
        ok(f"python env at {py.parent.parent}")
    else:
        bad("python env missing or incomplete",
            f"{'powershell -File ' if IS_WINDOWS else 'bash '}"
            f"{SKILL_DIR / 'scripts' / ('setup.ps1' if IS_WINDOWS else 'setup.sh')}")

    vendor = SKILL_DIR / "scripts" / "vendor"
    if (vendor / "render.py").exists() and (vendor / "transcribe.py").exists():
        ok("bundled editing engine (video-use, MIT)")
    else:
        bad("bundled engine missing from scripts/vendor", "reinstall the skill")

    missing_fonts = [k for k, p in BUNDLED.items() if not p.exists()]
    if not missing_fonts:
        ok("bundled fonts (Inter, JetBrains Mono)")
    else:
        warn(f"bundled font missing: {', '.join(missing_fonts)}",
             "captions fall back to a system font; output will differ between machines")

    # Transcription needs word-level timing. Any one of these provides it.
    text = env_file(home).read_text() if env_file(home).exists() else ""
    def has_key(name: str) -> bool:
        return bool(re.search(rf"^{name}=.{{10,}}", text, re.M)) or bool(os.environ.get(name))
    providers = [n for n, k in (("elevenlabs", "ELEVENLABS_API_KEY"),
                                ("openai", "OPENAI_API_KEY"),
                                ("gemini", "GEMINI_API_KEY")) if has_key(k)]
    if py.exists() and subprocess.run([str(py), "-c", "import faster_whisper"],
                                      capture_output=True).returncode == 0:
        providers.append("local")
    if providers:
        ok("transcription: " + " ".join(providers))
    else:
        bad("no transcription provider (word-level timing is required)",
            f"add one key to {env_file(home)} — ELEVENLABS_API_KEY, OPENAI_API_KEY or "
            f"GEMINI_API_KEY — or install the free offline model:\n"
            f"             uv pip install --python {py} faster-whisper\n"
            f"           see references/stt.md")

    hyper = Path.home() / ".claude" / "skills" / "hyperframes" / "SKILL.md"
    if hyper.exists():
        ok("HyperFrames skills (rich motion graphics)")
    else:
        warn("HyperFrames not installed — graphics fall back to the bundled renderer",
             "optional: npx --yes hyperframes@latest skills update  (needs Node 22+)")

    print()
    print("READY" if not fail else "NOT READY — fix the FAIL lines")
    sys.exit(fail)


if __name__ == "__main__":
    main()
