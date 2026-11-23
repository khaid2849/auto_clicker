"""macOS: click bằng Quartz CGEvent; cần quyền Accessibility."""
from __future__ import annotations

import subprocess
import time

import Quartz  # pyobjc-framework-Quartz

from ..i18n import tr
from .base import Backend, KeepAwake

ACCESSIBILITY_URL = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"


def accessibility_trusted(prompt: bool = False) -> bool:
    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
    except ImportError:
        return True  # không kiểm tra được -> không chặn
    return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: prompt}))


class QuartzBackend(Backend):
    name = "Quartz CGEvent"
    fix_action = ("open_settings", lambda: subprocess.Popen(["open", ACCESSIBILITY_URL]))
    _EVENTS = {
        "left": (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp, Quartz.kCGMouseButtonLeft),
        "right": (Quartz.kCGEventRightMouseDown, Quartz.kCGEventRightMouseUp, Quartz.kCGMouseButtonRight),
        "middle": (Quartz.kCGEventOtherMouseDown, Quartz.kCGEventOtherMouseUp, Quartz.kCGMouseButtonCenter),
    }

    def status(self):
        return None if accessibility_trusted() else tr("mac_no_ax")

    def request_permission(self):
        accessibility_trusted(prompt=True)

    def move(self, x, y):
        ev = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, (x, y), Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

    def click(self, x, y, button="left", clicks=1):
        down, up, btn = self._EVENTS[button]
        self.move(x, y)
        for n in range(1, clicks + 1):  # clickState 1 rồi 2 -> macOS hiểu là double click
            for etype in (down, up):
                ev = Quartz.CGEventCreateMouseEvent(None, etype, (x, y), btn)
                Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventClickState, n)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
                time.sleep(0.015)


class MacKeepAwake(KeepAwake):
    """Luôn chặn App Nap (macOS làm trễ timer của app chạy nền); tùy chọn chặn ngủ/tắt màn hình."""

    def __init__(self):
        self._token = None

    def begin(self, prevent_sleep):
        import Foundation as F
        if self._token is not None:
            return True
        opts = getattr(F, "NSActivityUserInitiatedAllowingIdleSystemSleep", 0x00EFFFFF)
        opts |= getattr(F, "NSActivityLatencyCritical", 0xFF00000000)
        if prevent_sleep:
            opts |= getattr(F, "NSActivityIdleSystemSleepDisabled", 1 << 20)
            opts |= getattr(F, "NSActivityIdleDisplaySleepDisabled", 1 << 40)
        self._token = F.NSProcessInfo.processInfo().beginActivityWithOptions_reason_(opts, "Auto Clicker đang chạy")
        return True

    def end(self):
        if self._token is not None:
            import Foundation as F
            F.NSProcessInfo.processInfo().endActivity_(self._token)
            self._token = None
