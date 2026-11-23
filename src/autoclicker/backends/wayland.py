"""Linux Wayland: tạo chuột ảo tọa độ tuyệt đối qua /dev/uinput (ioctl thuần, không cần thư viện C).

Wayland không cho ứng dụng đọc vị trí chuột toàn cục hay tự gửi sự kiện, nên đi qua kernel.
Cần quyền ghi /dev/uinput: chạy scripts/setup_uinput.sh (hoặc scripts/install_linux.sh).
"""
from __future__ import annotations

import fcntl
import os
import struct
import time

from ..i18n import tr
from .base import Backend


class UinputBackend(Backend):
    name = "uinput"
    can_read_cursor = False
    PATH = "/dev/uinput"
    ABS_MAX = 65535

    # linux/input-event-codes.h
    EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03
    SYN_REPORT, ABS_X, ABS_Y = 0, 0x00, 0x01
    BUTTONS = {"left": 0x110, "right": 0x111, "middle": 0x112}
    BUS_VIRTUAL = 0x06
    # linux/uinput.h: _IOW('U', 100/101/103, int), _IO('U', 1/2)
    UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_ABSBIT = 0x40045564, 0x40045565, 0x40045567
    UI_DEV_CREATE, UI_DEV_DESTROY = 0x5501, 0x5502

    # struct uinput_user_dev: name[80], input_id{bustype,vendor,product,version}, ff_effects_max,
    #                         absmax[64], absmin[64], absfuzz[64], absflat[64]
    DEV_FMT = "=80sHHHHI256i"
    # struct input_event: timeval{long,long}, u16 type, u16 code, s32 value
    EVENT_FMT = "llHHi"

    def __init__(self):
        self.fd = None

    def status(self):
        if not os.path.exists(self.PATH):
            return tr("uinput_missing")
        if not os.access(self.PATH, os.W_OK):
            return tr("uinput_denied")
        return None

    def _open(self):
        if self.fd is not None:
            return
        fd = os.open(self.PATH, os.O_WRONLY | os.O_NONBLOCK)
        for ev in (self.EV_SYN, self.EV_KEY, self.EV_ABS):
            fcntl.ioctl(fd, self.UI_SET_EVBIT, ev)
        for code in self.BUTTONS.values():
            fcntl.ioctl(fd, self.UI_SET_KEYBIT, code)
        for axis in (self.ABS_X, self.ABS_Y):
            fcntl.ioctl(fd, self.UI_SET_ABSBIT, axis)
        absmax = [0] * 64
        absmax[self.ABS_X] = absmax[self.ABS_Y] = self.ABS_MAX
        dev = struct.pack(self.DEV_FMT, b"AutoClicker virtual pointer",
                          self.BUS_VIRTUAL, 0x1D6B, 0x0104, 1, 0, *absmax, *([0] * 192))
        os.write(fd, dev)
        fcntl.ioctl(fd, self.UI_DEV_CREATE)
        self.fd = fd
        time.sleep(0.6)  # đợi compositor nhận thiết bị mới

    def _emit(self, etype, code, value):
        os.write(self.fd, struct.pack(self.EVENT_FMT, 0, 0, etype, code, value))

    def _syn(self):
        self._emit(self.EV_SYN, self.SYN_REPORT, 0)

    @staticmethod
    def _desktop_bounds():
        """Hình chữ nhật bao mọi màn hình (tọa độ logic) — compositor map trục ABS lên vùng này."""
        from PySide6.QtCore import QRect
        from PySide6.QtGui import QGuiApplication
        rect = QRect()
        for s in QGuiApplication.screens():
            rect = rect.united(s.geometry())
        return rect

    def move(self, x, y):
        self._open()
        b = self._desktop_bounds()
        ax = round((x - b.x()) * (self.ABS_MAX + 1) / max(1, b.width()))
        ay = round((y - b.y()) * (self.ABS_MAX + 1) / max(1, b.height()))
        self._emit(self.EV_ABS, self.ABS_X, min(max(ax, 0), self.ABS_MAX))
        self._emit(self.EV_ABS, self.ABS_Y, min(max(ay, 0), self.ABS_MAX))
        self._syn()

    def click(self, x, y, button="left", clicks=1):
        self.move(x, y)
        time.sleep(0.03)
        code = self.BUTTONS[button]
        for _ in range(clicks):
            self._emit(self.EV_KEY, code, 1)
            self._syn()
            time.sleep(0.02)
            self._emit(self.EV_KEY, code, 0)
            self._syn()
            time.sleep(0.06)

    def close(self):
        if self.fd is not None:
            fcntl.ioctl(self.fd, self.UI_DEV_DESTROY)
            os.close(self.fd)
            self.fd = None
