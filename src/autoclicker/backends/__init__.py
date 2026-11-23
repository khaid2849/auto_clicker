"""Pick the click backend for the current OS / session type.

    macos    Quartz CGEvent              (backends/macos.py)
    windows  Win32 SetCursorPos+SendInput (backends/windows.py)
    x11      XTest                       (backends/x11.py)
    wayland  /dev/uinput virtual mouse   (backends/wayland.py)
    dry      no real clicks, for trying the UI

Force a backend with the environment variable AUTOCLICKER_BACKEND=<name above>.
This module does not import Qt: configure_qt_env() must run before Qt is imported.
"""
from __future__ import annotations

import os
import sys

from ..i18n import tr
from .base import Backend, DryBackend, KeepAwake


def detect() -> str:
    forced = os.environ.get("AUTOCLICKER_BACKEND", "").strip().lower()
    if forced:
        return forced
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    if os.environ.get("XDG_SESSION_TYPE") == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    return "x11"


KIND = detect()


def platform_label() -> str:
    return {"macos": "macOS", "windows": "Windows", "x11": "Linux · X11",
            "wayland": "Linux · Wayland", "dry": tr("platform_dry")}.get(KIND, KIND)

# Wayland doesn't let applications position their own windows
CAN_POSITION_WINDOWS = KIND != "wayland"
# On Linux the position picker goes fullscreen so it also covers the GNOME top bar
OVERLAY_FULLSCREEN = KIND in ("x11", "wayland")


def configure_qt_env() -> None:
    """Make Qt use the same coordinate system as the backend that sends the clicks."""
    if KIND == "wayland":
        os.environ.setdefault("QT_QPA_PLATFORM", "wayland")
    elif KIND in ("x11", "windows"):
        # XTest / SendInput use physical pixels -> turn off Qt scaling so Qt coordinates == physical pixels.
        # (macOS uses points on both sides; Wayland uses logical coordinates on both sides.)
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")


def create_backend() -> Backend:
    try:
        if KIND == "macos":
            from .macos import QuartzBackend as Impl
        elif KIND == "windows":
            from .windows import WindowsBackend as Impl
        elif KIND == "x11":
            from .x11 import X11Backend as Impl
        elif KIND == "wayland":
            from .wayland import UinputBackend as Impl
        else:
            return DryBackend()
        return Impl()
    except Exception as e:  # noqa: BLE001
        return DryBackend(tr("backend_init_failed", kind=KIND, e=e))


def create_keepawake() -> KeepAwake:
    try:
        if KIND == "macos":
            from .macos import MacKeepAwake
            return MacKeepAwake()
        if KIND == "windows":
            from .windows import WindowsKeepAwake
            return WindowsKeepAwake()
        if KIND in ("x11", "wayland"):
            from .linux_session import DBusKeepAwake
            return DBusKeepAwake()
    except Exception:  # noqa: BLE001
        pass
    return KeepAwake()
