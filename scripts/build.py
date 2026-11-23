#!/usr/bin/env python3
"""Đóng gói Auto Clicker thành app chạy độc lập cho hệ điều hành đang dùng (PyInstaller).

    python -m pip install ".[build]"
    python scripts/build.py

Kết quả trong dist/:
    macOS    AutoClicker.app             + AutoClicker-macos-<arch>.zip
    Windows  AutoClicker.exe (1 file)    + AutoClicker-windows-<arch>.zip
    Linux    AutoClicker/AutoClicker     + AutoClicker-linux-<arch>.tar.gz
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, DIST, BUILD = ROOT / "src", ROOT / "dist", ROOT / "build"
NAME = "AutoClicker"
BUNDLE_ID = "io.github.khaid2849.autoclicker"


def run(cmd, **kw):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def os_tag() -> str:
    return {"darwin": "macos", "win32": "windows"}.get(sys.platform, "linux")


def arch_tag() -> str:
    m = platform.machine().lower()
    return {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64"}.get(m, m)


def main() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        sys.exit('Thiếu PyInstaller. Chạy trước:  python -m pip install ".[build]"')

    BUILD.mkdir(exist_ok=True)
    env = {**os.environ, "PYTHONPATH": str(SRC), "QT_QPA_PLATFORM": "offscreen", "AUTOCLICKER_BACKEND": "dry"}

    # 1. Icon (PyInstaller + Pillow tự chuyển PNG sang .icns / .ico)
    icon = BUILD / "icon.png"
    run([sys.executable, "-m", "autoclicker", "--export-icon", icon], env=env)

    # 2. PyInstaller
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
           "--name", NAME, "--paths", SRC,
           "--distpath", DIST, "--workpath", BUILD / "pyinstaller", "--specpath", BUILD]
    if sys.platform == "darwin":
        cmd += ["--icon", icon, "--osx-bundle-identifier", BUNDLE_ID]
    elif sys.platform == "win32":
        cmd += ["--icon", icon, "--onefile"]  # một file .exe duy nhất, dễ chia sẻ
    # Linux: icon nằm trong file .desktop (scripts/install_linux.sh), không nhúng vào binary
    run([*cmd, ROOT / "scripts" / "entry.py"])

    # 3. Nén để phát hành
    base = DIST / f"{NAME}-{os_tag()}-{arch_tag()}"
    if sys.platform == "darwin":
        # ditto giữ nguyên symlink + chữ ký trong .app (shutil.make_archive làm hỏng)
        run(["ditto", "-c", "-k", "--keepParent", DIST / f"{NAME}.app", f"{base}.zip"])
        out = DIST / f"{NAME}.app"
    elif sys.platform == "win32":
        shutil.make_archive(str(base), "zip", DIST, f"{NAME}.exe")
        out = DIST / f"{NAME}.exe"
    else:
        shutil.make_archive(str(base), "gztar", DIST, NAME)
        out = DIST / NAME / NAME
    print(f"\n✅ Xong: {out}\n   Gói phát hành: {base.name}.*")


if __name__ == "__main__":
    main()
