"""Chọn backend gửi click theo hệ điều hành / loại phiên đăng nhập.

    macos    Quartz CGEvent              (backends/macos.py)
    windows  Win32 SetCursorPos+SendInput (backends/windows.py)
    x11      XTest                       (backends/x11.py)
    wayland  chuột ảo /dev/uinput        (backends/wayland.py)
    dry      không click thật, để thử giao diện

Ép backend bằng biến môi trường AUTOCLICKER_BACKEND=<tên ở trên>.
Module này không import Qt: configure_qt_env() phải chạy trước khi import Qt.
"""
from __future__ import annotations

import os
import sys

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
PLATFORM_LABEL = {
    "macos": "macOS", "windows": "Windows", "x11": "Linux · X11",
    "wayland": "Linux · Wayland", "dry": "Mô phỏng",
}.get(KIND, KIND)

# Wayland không cho ứng dụng tự đặt vị trí cửa sổ
CAN_POSITION_WINDOWS = KIND != "wayland"
# Trên Linux overlay chọn vị trí dùng fullscreen để phủ cả thanh trên cùng của GNOME
OVERLAY_FULLSCREEN = KIND in ("x11", "wayland")


def configure_qt_env() -> None:
    """Đồng bộ hệ tọa độ của Qt với hệ tọa độ mà backend dùng để click."""
    if KIND == "wayland":
        os.environ.setdefault("QT_QPA_PLATFORM", "wayland")
    elif KIND in ("x11", "windows"):
        # XTest / SendInput dùng pixel vật lý -> tắt scale của Qt để tọa độ Qt == pixel vật lý.
        # (macOS dùng "point" ở cả hai phía; Wayland dùng tọa độ logic ở cả hai phía.)
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
        return DryBackend(f"Không khởi tạo được backend '{KIND}': {e}")


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
