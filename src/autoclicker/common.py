"""Hằng số và tiện ích dùng chung cho giao diện."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPainter, QPen, QPixmap

APP_NAME = "Auto Clicker"
APP_ID = "autoclicker"
ORG_NAME = "KhaiTools"


def fmt_duration(sec: float) -> str:
    """179.2 -> '03:00', 3725 -> '1:02:05'."""
    sec = max(0, math.ceil(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def mono_font(pt: int, bold: bool = False) -> QFont:
    f = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    f.setPointSize(pt)
    f.setBold(bold)
    return f


def make_icon(size: int = 256) -> QPixmap:
    """Icon tâm ngắm vẽ bằng code (cửa sổ, khay hệ thống, file icon khi đóng gói)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s, c = float(size), size / 2
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#2563eb"))
    p.drawRoundedRect(QRectF(s * .06, s * .06, s * .88, s * .88), s * .22, s * .22)
    p.setPen(QPen(QColor("white"), s * .06, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(c, c), s * .23, s * .23)
    for a, b in ((.17, .33), (.67, .83)):
        p.drawLine(QPointF(c, s * a), QPointF(c, s * b))
        p.drawLine(QPointF(s * a, c), QPointF(s * b, c))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("white"))
    p.drawEllipse(QPointF(c, c), s * .06, s * .06)
    p.end()
    return pm


def export_icon(path: str, size: int = 1024) -> None:
    _app = QGuiApplication.instance() or QGuiApplication([])
    if not make_icon(size).save(path):
        raise SystemExit(f"Không ghi được icon: {path}")
