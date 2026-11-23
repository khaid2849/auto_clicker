"""Windows: move the cursor with SetCursorPos, then click with SendInput (ctypes, no extra dependency).

Qt runs with QT_ENABLE_HIGHDPI_SCALING=0 and the process is Per-Monitor DPI aware (the Qt 6 default),
so Qt coordinates == physical pixels == what SetCursorPos expects, even at 125–200% scaling.
"""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

from ..i18n import tr
from .base import Backend, KeepAwake

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

INPUT_MOUSE = 0
MOUSEEVENTF = {  # (down, up)
    "left": (0x0002, 0x0004),
    "right": (0x0008, 0x0010),
    "middle": (0x0020, 0x0040),
}
ES_CONTINUOUS, ES_SYSTEM_REQUIRED, ES_DISPLAY_REQUIRED = 0x80000000, 0x00000001, 0x00000002


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]  # MOUSEINPUT is the largest member -> sizeof(INPUT) is correct


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT
user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
user32.SetCursorPos.restype = wintypes.BOOL
kernel32.SetThreadExecutionState.argtypes = (wintypes.DWORD,)
kernel32.SetThreadExecutionState.restype = wintypes.DWORD


class WindowsBackend(Backend):
    name = "SendInput"

    def move(self, x, y):
        if not user32.SetCursorPos(int(x), int(y)):
            raise ctypes.WinError(ctypes.get_last_error())

    def _send(self, flags: int) -> None:
        inp = INPUT(type=INPUT_MOUSE, u=_INPUTUNION(mi=MOUSEINPUT(0, 0, 0, flags, 0, 0)))
        if user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) != 1:
            raise OSError(tr("win_blocked"))

    def click(self, x, y, button="left", clicks=1):
        down, up = MOUSEEVENTF[button]
        self.move(x, y)
        for _ in range(clicks):
            self._send(down)
            time.sleep(0.02)
            self._send(up)
            time.sleep(0.06)


class WindowsKeepAwake(KeepAwake):
    """SetThreadExecutionState: prevents sleep and display-off (must be called from one thread — the UI thread)."""

    def __init__(self):
        self._active = False

    def begin(self, prevent_sleep):
        if not prevent_sleep:
            return True
        ok = kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED) != 0
        self._active = ok
        return ok

    def end(self):
        if self._active:
            kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            self._active = False
