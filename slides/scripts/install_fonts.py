"""Installs the deck's fonts for the current Windows user, so PowerPoint can render and embed them.

    python slides/scripts/install_fonts.py

Copies Fira Sans (regular, bold, italic, bold italic) and the static Lexend Medium from
slides/assets/fonts/ into %LOCALAPPDATA%\\Microsoft\\Windows\\Fonts and registers each one under
HKEY_CURRENT_USER, which needs no administrator rights. Safe to run again. Close PowerPoint first:
a running PowerPoint does not see fonts installed after it started.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
from pathlib import Path

FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts"
DECK_FONTS = {
    "fira-sans/FiraSans-Regular.ttf": "Fira Sans (TrueType)",
    "fira-sans/FiraSans-Bold.ttf": "Fira Sans Bold (TrueType)",
    "fira-sans/FiraSans-Italic.ttf": "Fira Sans Italic (TrueType)",
    "fira-sans/FiraSans-BoldItalic.ttf": "Fira Sans Bold Italic (TrueType)",
    "lexend/Lexend-Medium.ttf": "Lexend Medium (TrueType)",
}
REGISTRY = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"
WM_FONTCHANGE = 0x001D
HWND_BROADCAST = 0xFFFF


def main() -> int:
    if sys.platform != "win32":
        print("install_fonts.py installs fonts for a Windows user; nothing to do here")
        return 0
    import winreg

    target = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"
    target.mkdir(parents=True, exist_ok=True)
    gdi = ctypes.windll.gdi32
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY) as key:
        for relative, display in DECK_FONTS.items():
            source = FONTS / relative
            installed = target / source.name
            shutil.copyfile(source, installed)
            winreg.SetValueEx(key, display, 0, winreg.REG_SZ, str(installed))
            gdi.AddFontResourceW(str(installed))
            print(f"installed {display}: {installed}")
    ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0, 0, 1000, None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
