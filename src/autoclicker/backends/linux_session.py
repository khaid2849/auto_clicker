"""Linux: xin desktop không khóa màn hình / suspend qua D-Bus (dùng chung cho X11 và Wayland)."""
from __future__ import annotations

from jeepney import DBusAddress, new_method_call
from jeepney.io.blocking import open_dbus_connection

from .base import KeepAwake

APP = "Auto Clicker"
REASON = "Auto clicking"

# (địa chỉ, method xin, chữ ký, tham số, method hủy)
INHIBITORS = [
    # GNOME: flags 4 = suspend, 8 = idle (khóa / tắt màn hình)
    (DBusAddress("/org/gnome/SessionManager", "org.gnome.SessionManager", "org.gnome.SessionManager"),
     "Inhibit", "susu", (APP, 0, REASON, 4 | 8), "Uninhibit"),
    # KDE, XFCE và các desktop khác
    (DBusAddress("/org/freedesktop/ScreenSaver", "org.freedesktop.ScreenSaver", "org.freedesktop.ScreenSaver"),
     "Inhibit", "ss", (APP, REASON), "UnInhibit"),
]


class DBusKeepAwake(KeepAwake):
    def __init__(self):
        self.conn = None
        self._release = None

    def begin(self, prevent_sleep):
        if not prevent_sleep or self.conn:
            return True
        try:
            conn = open_dbus_connection(bus="SESSION")
        except Exception:  # noqa: BLE001
            return False
        for addr, method, sig, args, undo in INHIBITORS:
            try:
                cookie = conn.send_and_get_reply(new_method_call(addr, method, sig, args)).body[0]
            except Exception:  # noqa: BLE001
                continue
            self.conn = conn
            self._release = lambda a=addr, u=undo, c=cookie: conn.send_and_get_reply(new_method_call(a, u, "u", (c,)))
            return True
        conn.close()
        return False

    def end(self):
        if self.conn:
            try:
                self._release()
            except Exception:  # noqa: BLE001
                pass
            self.conn.close()  # đóng kết nối D-Bus cũng tự hủy inhibit
            self.conn = self._release = None
