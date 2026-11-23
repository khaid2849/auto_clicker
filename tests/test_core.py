import struct
import sys

import pytest

from autoclicker import backends
from autoclicker.common import fmt_duration


def test_fmt_duration():
    assert fmt_duration(0) == "00:00"
    assert fmt_duration(179.2) == "03:00"
    assert fmt_duration(3725) == "1:02:05"


@pytest.mark.parametrize("platform, env, expected", [
    ("darwin", {}, "macos"),
    ("win32", {}, "windows"),
    ("linux", {"XDG_SESSION_TYPE": "x11"}, "x11"),
    ("linux", {"XDG_SESSION_TYPE": "wayland"}, "wayland"),
    ("linux", {"WAYLAND_DISPLAY": "wayland-0"}, "wayland"),
    ("linux", {"AUTOCLICKER_BACKEND": "dry", "XDG_SESSION_TYPE": "wayland"}, "dry"),
])
def test_detect(monkeypatch, platform, env, expected):
    for key in ("AUTOCLICKER_BACKEND", "XDG_SESSION_TYPE", "WAYLAND_DISPLAY"):
        monkeypatch.delenv(key, raising=False)
    for key, val in env.items():
        monkeypatch.setenv(key, val)
    monkeypatch.setattr(sys, "platform", platform)
    assert backends.detect() == expected


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="uinput only exists on Linux")
def test_uinput_struct_layout():
    from autoclicker.backends.wayland import UinputBackend
    assert struct.calcsize(UinputBackend.DEV_FMT) == 1116  # sizeof(struct uinput_user_dev)
    assert struct.calcsize(UinputBackend.EVENT_FMT) in (16, 24)  # sizeof(struct input_event) 32/64-bit


def test_main_window_clicks_and_stops(qapp):
    from PySide6.QtCore import QTimer

    from autoclicker.app import MainWindow

    w = MainWindow()
    w.interval_spin.setValue(1)
    w.unit_combo.setCurrentIndex(0)  # seconds
    w.click_now_cb.setChecked(True)
    w.repeat_spin.setValue(2)
    w.start()
    assert w.running
    QTimer.singleShot(2500, qapp.quit)
    qapp.exec()
    assert w.count == 2
    assert not w.running
