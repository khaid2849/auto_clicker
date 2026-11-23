"""Lớp phủ chọn vị trí click và vòng tròn đánh dấu điểm click."""
from __future__ import annotations

import time

from PySide6.QtCore import QObject, QPoint, QPointF, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .backends import CAN_POSITION_WINDOWS, OVERLAY_FULLSCREEN
from .common import mono_font

RED = QColor(255, 69, 58)


def cover_screen(w: QWidget, screen) -> None:
    """Phủ kín một màn hình."""
    w.setScreen(screen)
    w.setGeometry(screen.geometry())
    if OVERLAY_FULLSCREEN:
        w.showFullScreen()  # Wayland không đặt được vị trí cửa sổ; X11 cần để phủ thanh trên cùng
    else:
        w.show()  # macOS: fullscreen sẽ tạo Space mới có hiệu ứng chuyển cảnh -> không dùng


class PickerOverlay(QWidget):
    """Lớp phủ mờ một màn hình: tâm ngắm + tọa độ chạy theo chuột; click trái để chọn.

    Tọa độ toàn cục = góc màn hình + vị trí chuột trong overlay, nên không cần đọc vị trí chuột
    toàn cục -> chạy được cả trên Wayland.
    """

    picked = Signal(int, int)
    cancelled = Signal()

    def __init__(self, screen):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.scr = screen
        self.origin = screen.geometry().topLeft()
        self.local: QPoint | None = None
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 70))  # alpha > 0 để cửa sổ nhận được click
        self._draw_hint(p)
        if self.local is not None:
            self._draw_crosshair(p)

    def _draw_hint(self, p: QPainter):
        hint = "Click chuột trái để chọn vị trí   •   Esc hoặc chuột phải để hủy"
        f = QFont()
        f.setPointSize(15)
        f.setBold(True)
        p.setFont(f)
        fm = p.fontMetrics()
        box = QRect(0, 0, fm.horizontalAdvance(hint) + 44, fm.height() + 22)
        box.moveCenter(QPoint(self.width() // 2, self.height() - 70))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 190))
        p.drawRoundedRect(box, 10, 10)
        p.setPen(QColor("white"))
        p.drawText(box, Qt.AlignCenter, hint)

    def _draw_crosshair(self, p: QPainter):
        x, y = self.local.x(), self.local.y()
        g = self.origin + self.local
        p.setPen(QPen(QColor(255, 69, 58, 170), 1))
        p.drawLine(0, y, self.width(), y)
        p.drawLine(x, 0, x, self.height())
        p.setPen(QPen(RED, 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(self.local, 16, 16)

        geo = self.scr.geometry()
        lines = [f"X: {g.x()}    Y: {g.y()}", f"{self.scr.name()}  {geo.width()}×{geo.height()}"]
        p.setFont(mono_font(15, bold=True))
        fm = p.fontMetrics()
        w = max(fm.horizontalAdvance(t) for t in lines) + 24
        h = fm.height() * 2 + 16
        bx = x + 22 if x + 22 + w < self.width() else x - 22 - w
        by = y + 22 if y + 22 + h < self.height() else y - 22 - h
        label = QRect(bx, by, w, h)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(20, 20, 20, 225))
        p.drawRoundedRect(label, 8, 8)
        inner = label.adjusted(12, 8, -12, -8)
        p.setPen(QColor("white"))
        p.drawText(inner, Qt.AlignLeft | Qt.AlignTop, lines[0])
        p.setPen(QColor(200, 200, 200))
        p.setFont(mono_font(11))
        p.drawText(inner, Qt.AlignLeft | Qt.AlignBottom, lines[1])

    def enterEvent(self, _):
        self.activateWindow()  # để phím Esc tới đúng overlay đang có chuột
        self.setFocus()

    def mouseMoveEvent(self, e):
        self.local = e.position().toPoint()
        self.update()

    def leaveEvent(self, _):
        self.local = None
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            g = self.origin + e.position().toPoint()
            self.picked.emit(g.x(), g.y())
        else:
            self.cancelled.emit()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.cancelled.emit()


class PositionPicker(QObject):
    """Mở một overlay cho mỗi màn hình."""

    picked = Signal(int, int)
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.overlays: list[PickerOverlay] = []

    def start(self):
        for screen in QGuiApplication.screens():
            o = PickerOverlay(screen)
            o.picked.connect(self._on_picked)
            o.cancelled.connect(self._close)
            cover_screen(o, screen)
            self.overlays.append(o)
        if self.overlays:
            self.overlays[0].activateWindow()

    def _on_picked(self, x, y):
        self._close()
        self.picked.emit(x, y)

    def _close(self):
        for o in self.overlays:
            o.close()
            o.deleteLater()
        self.overlays.clear()
        self.finished.emit()


class TargetMarker(QWidget):
    """Vòng tròn nhấp nháy tại điểm click, không chặn chuột."""

    SIZE = 90

    def __init__(self, x: int, y: int, ms: int = 1600):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                         | Qt.WindowTransparentForInput)
        for attr in (Qt.WA_TranslucentBackground, Qt.WA_TransparentForMouseEvents,
                     Qt.WA_ShowWithoutActivating, Qt.WA_DeleteOnClose):
            self.setAttribute(attr)
        pt = QPoint(x, y)
        self.scr = QGuiApplication.screenAt(pt) or QGuiApplication.primaryScreen()
        if CAN_POSITION_WINDOWS:
            self.setGeometry(x - self.SIZE // 2, y - self.SIZE // 2, self.SIZE, self.SIZE)
            self.center = QPointF(self.SIZE / 2, self.SIZE / 2)
        else:  # Wayland: phủ cả màn hình rồi vẽ vòng tròn tại điểm
            self.center = QPointF(pt - self.scr.geometry().topLeft())
        self._t0 = time.monotonic()
        self._anim = QTimer(self)
        self._anim.timeout.connect(self.update)
        self._anim.start(16)
        QTimer.singleShot(ms, self.close)

    def present(self):
        if CAN_POSITION_WINDOWS:
            self.show()
        else:
            self.setScreen(self.scr)
            self.showFullScreen()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        phase = ((time.monotonic() - self._t0) * 1.6) % 1.0
        p.setPen(QPen(QColor(255, 69, 58, int(255 * (1 - phase))), 3))
        r = 8 + phase * (self.SIZE / 2 - 10)
        p.drawEllipse(self.center, r, r)
        p.setPen(QPen(RED, 2))
        p.drawEllipse(self.center, 10, 10)
        p.setBrush(RED)
        p.drawEllipse(self.center, 3, 3)
