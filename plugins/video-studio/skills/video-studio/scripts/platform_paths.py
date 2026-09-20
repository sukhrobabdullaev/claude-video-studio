"""Everything that differs between macOS, Windows and Linux, in one place.

Three things change per platform and nothing else does: where the Python
environment lives, how you install ffmpeg, and which fonts exist. Keeping them
here means the rest of the scripts never branch on the operating system.

Fonts are bundled rather than borrowed from the system so a caption renders
identically on every machine — and so Uzbek `o'` / `g'` are guaranteed present.
Both are variable fonts, so the weight is selected by axis, not by file.
"""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = SKILL_DIR / "assets" / "fonts"

IS_WINDOWS = os.name == "nt"
IS_MAC = platform.system() == "Darwin"


def vs_home() -> Path:
    return Path(os.environ.get("VS_HOME") or Path.home() / ".video-studio")


def venv_python(home: Path | None = None) -> Path:
    home = home or vs_home()
    return home / "venv" / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def env_file(home: Path | None = None) -> Path:
    return (home or vs_home()) / ".env"


def install_hint(tool: str) -> str:
    """How to install a missing command line tool on this machine."""
    if IS_MAC:
        return f"brew install {tool}"
    if IS_WINDOWS:
        return f"winget install {'Gyan.FFmpeg' if tool == 'ffmpeg' else 'astral-sh.uv'}"
    for mgr, cmd in (("apt-get", f"sudo apt-get install -y {tool}"),
                     ("dnf", f"sudo dnf install -y {tool}"),
                     ("pacman", f"sudo pacman -S {tool}")):
        if shutil.which(mgr):
            return cmd
    return f"install {tool} with your package manager"


# ------------------------------------------------------------------ fonts

BUNDLED = {"sans": FONT_DIR / "Inter-Bold.ttf",
           "mono": FONT_DIR / "JetBrainsMono-Bold.ttf"}

# Used only when the bundle is missing — a stripped install, or a font override
# pointing somewhere that no longer exists.
SYSTEM_FALLBACKS = {
    "sans": ["/System/Library/Fonts/Helvetica.ttc",
             "C:/Windows/Fonts/arialbd.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"],
    "mono": ["/System/Library/Fonts/Menlo.ttc",
             "C:/Windows/Fonts/consolab.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
             "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf"],
}


def font_path(kind: str = "sans") -> tuple[str, bool]:
    """(path, is_bundled). Honors VS_FONT_SANS / VS_FONT_MONO overrides."""
    override = os.environ.get(f"VS_FONT_{kind.upper()}")
    if override and Path(override).exists():
        return override, False
    if BUNDLED[kind].exists():
        return str(BUNDLED[kind]), True
    for candidate in SYSTEM_FALLBACKS[kind]:
        if Path(candidate).exists():
            return candidate, False
    raise SystemExit(
        f"No {kind} font found. The bundled font should be at {BUNDLED[kind]}; "
        f"point VS_FONT_{kind.upper()} at a .ttf to override.")


def load_font(kind: str, size: int, weight: str = "Bold"):
    """A font object at the requested weight, whether or not it is variable."""
    from PIL import ImageFont
    path, bundled = font_path(kind)
    index = 1 if (not bundled and path.endswith(".ttc")) else 0   # .ttc bold face
    font = ImageFont.truetype(path, size, index=index)
    if bundled:
        try:
            font.set_variation_by_name(weight)
        except Exception:
            pass          # static build of the same family: already the right weight
    return font


def describe() -> str:
    sans, sans_bundled = font_path("sans")
    mono, mono_bundled = font_path("mono")
    return (f"{platform.system()} {platform.machine()} | python env {venv_python()} | "
            f"sans {'bundled' if sans_bundled else sans} | "
            f"mono {'bundled' if mono_bundled else mono}")


if __name__ == "__main__":
    print(describe())
