"""Linux X11 (Ubuntu on Xorg): clicks via the XTest extension using python-xlib."""
from __future__ import annotations

import time

from Xlib import X, display
from Xlib.ext import xtest

from .base import Backend


class X11Backend(Backend):
    name = "XTest"
    BUTTONS = {"left": 1, "middle": 2, "right": 3}

    def __init__(self):
        self.d = display.Display()
        if not self.d.has_extension("XTEST"):
            raise RuntimeError("the X server does not support XTEST")

    def move(self, x, y):
        xtest.fake_input(self.d, X.MotionNotify, x=int(x), y=int(y))
        self.d.sync()

    def click(self, x, y, button="left", clicks=1):
        self.move(x, y)
        btn = self.BUTTONS[button]
        for _ in range(clicks):
            xtest.fake_input(self.d, X.ButtonPress, btn)
            self.d.sync()
            time.sleep(0.02)
            xtest.fake_input(self.d, X.ButtonRelease, btn)
            self.d.sync()
            time.sleep(0.06)

    def close(self):
        self.d.close()
