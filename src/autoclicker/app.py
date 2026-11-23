"""Cửa sổ chính: cài đặt, đếm ngược, nhật ký, icon khay hệ thống."""
from __future__ import annotations

import getpass
import os
import random
import sys
import time
from datetime import datetime

from PySide6.QtCore import QEvent, QObject, QPoint, QSettings, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFormLayout, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
    QSpinBox, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from . import __version__, backends
from .backends import DryBackend
from .common import APP_ID, APP_NAME, ORG_NAME, fmt_duration, make_icon, mono_font
from .overlays import PositionPicker, TargetMarker

IS_MAC = backends.KIND == "macos"
SHORTCUT_LABEL = "⌘↩" if IS_MAC else "Ctrl+Enter"

STYLE = """
#warnBanner { background: #fff4e5; border: 1px solid #f5c26b; border-radius: 8px; }
#warnBanner QLabel { color: #7a4b00; }
#statusCard { border: 1px solid palette(mid); border-radius: 10px; }
#startBtn { font-size: 12pt; font-weight: 600; padding: 9px; border-radius: 8px;
            color: white; background: #16a34a; border: none; }
#startBtn:hover { background: #15803d; }
#startBtn[running="true"] { background: #dc2626; }
#startBtn[running="true"]:hover { background: #b91c1c; }
#backendLbl { color: gray; font-size: 8pt; }
QGroupBox { font-weight: 600; }
"""

UNITS = [("giây", 1), ("phút", 60), ("giờ", 3600)]
BUTTONS = [("Trái", "left"), ("Phải", "right"), ("Giữa", "middle")]
CLICK_TYPES = [("Click đơn", 1), ("Click đôi", 2)]


def make_settings() -> QSettings:
    path = os.environ.get("AUTOCLICKER_SETTINGS")  # dùng cho test
    return QSettings(path, QSettings.IniFormat) if path else QSettings(ORG_NAME, "AutoClicker")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(make_icon()))
        self.setStyleSheet(STYLE)

        self.settings = make_settings()
        self.backend = backends.create_backend()
        self.keepawake = backends.create_keepawake()
        self.running = False
        self.count = 0
        self.next_at = 0.0
        self._marker = None
        self.tray = None

        self.picker = PositionPicker(self)
        self.picker.picked.connect(self._on_picked)
        self.picker.finished.connect(self.show_window)

        self._build_ui()
        self._load_settings()
        self._apply_backend_limits()
        self._build_tray()

        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self._update_cursor_label)
        self.cursor_timer.start(50)
        self._update_cursor_label()

        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self._tick)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._check_backend)
        self.status_timer.start(2000)
        self._check_backend()

        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.toggle)  # ⌘↩ trên Mac
        QApplication.instance().aboutToQuit.connect(self._cleanup)

    # ───────────── Giao diện ─────────────
    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        self.warn_banner = QFrame(objectName="warnBanner")
        hb = QHBoxLayout(self.warn_banner)
        self.warn_lbl = QLabel(wordWrap=True)
        hb.addWidget(self.warn_lbl, 1)
        if self.backend.fix_action:
            label, action = self.backend.fix_action
            fix_btn = QPushButton(label)
            fix_btn.clicked.connect(action)
            hb.addWidget(fix_btn)
        root.addWidget(self.warn_banner)

        root.addWidget(self._build_position_box())
        root.addWidget(self._build_time_box())
        root.addWidget(self._build_click_box())
        root.addWidget(self._build_status_card())

        self.log_view = QPlainTextEdit(readOnly=True)
        self.log_view.setMaximumBlockCount(300)
        self.log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_view.setFont(mono_font(10))
        self.log_view.setFixedHeight(self.log_view.fontMetrics().lineSpacing() * 6 + 12)
        root.addWidget(self.log_view)

        self.setCentralWidget(central)
        # Rộng theo cỡ chữ, để vẫn vừa khi màn hình scale 125–200%
        self.setMinimumWidth(self.fontMetrics().averageCharWidth() * 58)
        self.resize(self.minimumWidth(), self.sizeHint().height())
        self._set_running_ui(False)

    def _build_position_box(self) -> QGroupBox:
        box = QGroupBox("Vị trí click")
        g = QGridLayout(box)
        self.x_spin, self.y_spin = QSpinBox(), QSpinBox()
        for sp in (self.x_spin, self.y_spin):
            sp.setRange(-20000, 20000)
            sp.setFont(mono_font(12))
            sp.valueChanged.connect(self._update_target_label)
        g.addWidget(QLabel("X"), 0, 0)
        g.addWidget(self.x_spin, 0, 1)
        g.addWidget(QLabel("Y"), 0, 2)
        g.addWidget(self.y_spin, 0, 3)
        self.pick_btn = QPushButton("🎯  Chọn vị trí trên màn hình")
        self.pick_btn.clicked.connect(self.start_pick)
        self.show_btn = QPushButton("Hiện điểm")
        self.show_btn.setToolTip("Nháy vòng tròn đỏ tại vị trí sẽ click")
        self.show_btn.clicked.connect(self.show_target)
        g.addWidget(self.pick_btn, 1, 0, 1, 3)
        g.addWidget(self.show_btn, 1, 3)
        self.cursor_lbl = QLabel(font=mono_font(11), wordWrap=True)
        self.target_lbl = QLabel(wordWrap=True)
        g.addWidget(self.cursor_lbl, 2, 0, 1, 4)
        g.addWidget(self.target_lbl, 3, 0, 1, 4)
        self.position_box = box
        return box

    def _build_time_box(self) -> QGroupBox:
        box = QGroupBox("Thời gian")
        f = QFormLayout(box)
        row = QHBoxLayout()
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 99999)
        self.unit_combo = QComboBox()
        for name, mult in UNITS:
            self.unit_combo.addItem(name, mult)
        row.addWidget(self.interval_spin, 1)
        row.addWidget(self.unit_combo)
        f.addRow("Click mỗi", row)
        self.jitter_spin = QSpinBox()
        self.jitter_spin.setRange(0, 3600)
        self.jitter_spin.setSuffix(" giây")
        self.jitter_spin.setToolTip("Cộng/trừ ngẫu nhiên vào chu kỳ để không quá đều")
        f.addRow("Ngẫu nhiên ±", self.jitter_spin)
        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(0, 1_000_000)
        self.repeat_spin.setSpecialValueText("Không giới hạn")
        self.repeat_spin.setSuffix(" lần")
        f.addRow("Dừng sau", self.repeat_spin)
        self.click_now_cb = QCheckBox("Click ngay khi bấm Bắt đầu")
        f.addRow(self.click_now_cb)
        self.time_box = box
        return box

    def _build_click_box(self) -> QGroupBox:
        box = QGroupBox("Kiểu click")
        f = QFormLayout(box)
        self.button_combo = QComboBox()
        for name, val in BUTTONS:
            self.button_combo.addItem(name, val)
        self.type_combo = QComboBox()
        for name, val in CLICK_TYPES:
            self.type_combo.addItem(name, val)
        self.pos_jitter_spin = QSpinBox()
        self.pos_jitter_spin.setRange(0, 200)
        self.pos_jitter_spin.setSuffix(" px")
        self.pos_jitter_spin.setToolTip("Lệch ngẫu nhiên quanh điểm click")
        f.addRow("Nút chuột", self.button_combo)
        f.addRow("Loại", self.type_combo)
        f.addRow("Lệch vị trí ±", self.pos_jitter_spin)
        self.restore_cb = QCheckBox("Trả con trỏ về chỗ cũ sau khi click")
        self.awake_cb = QCheckBox("Không ngủ / khóa màn hình khi đang chạy")
        self.failsafe_cb = QCheckBox("Dừng khẩn cấp khi đưa chuột vào góc trên-trái")
        for cb in (self.restore_cb, self.awake_cb, self.failsafe_cb):
            f.addRow(cb)
        self.click_box = box
        return box

    def _build_status_card(self) -> QFrame:
        card = QFrame(objectName="statusCard")
        v = QVBoxLayout(card)
        top = QHBoxLayout()
        self.state_lbl = QLabel()
        self.count_lbl = QLabel()
        top.addWidget(self.state_lbl)
        top.addStretch()
        top.addWidget(self.count_lbl)
        v.addLayout(top)
        v.addWidget(QLabel("Lần click tiếp theo sau", alignment=Qt.AlignCenter))
        self.countdown_lbl = QLabel("--:--", alignment=Qt.AlignCenter)
        self.countdown_lbl.setFont(mono_font(28, bold=True))
        v.addWidget(self.countdown_lbl)
        self.start_btn = QPushButton(objectName="startBtn")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.toggle)
        v.addWidget(self.start_btn)
        self.backend_lbl = QLabel(objectName="backendLbl", alignment=Qt.AlignCenter)
        v.addWidget(self.backend_lbl)
        return card

    def _apply_backend_limits(self):
        self.backend_lbl.setText(f"v{__version__}  ·  {backends.PLATFORM_LABEL}  ·  click qua {self.backend.name}")
        if not self.backend.can_read_cursor:
            tip = "Wayland không cho ứng dụng đọc vị trí chuột, nên tùy chọn này không dùng được."
            for cb in (self.restore_cb, self.failsafe_cb):
                cb.setChecked(False)
                cb.setEnabled(False)
                cb.setToolTip(tip)

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(QIcon(make_icon(64)), self)
        menu = QMenu()
        self.tray_toggle = menu.addAction("Bắt đầu", self.toggle)
        menu.addAction("Hiện cửa sổ", self.show_window)
        menu.addSeparator()
        menu.addAction("Thoát", QApplication.quit)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip(APP_NAME)
        if not IS_MAC:  # macOS: click icon đã mở menu
            self.tray.activated.connect(
                lambda reason: self.show_window() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.show()
        self._tray_menu = menu
        self._set_running_ui(self.running)

    # ───────────── Lưu cài đặt ─────────────
    def _load_settings(self):
        s = self.settings
        center = QGuiApplication.primaryScreen().geometry().center()
        self.x_spin.setValue(s.value("x", center.x(), type=int))
        self.y_spin.setValue(s.value("y", center.y(), type=int))
        self.interval_spin.setValue(s.value("interval", 3, type=int))
        self.unit_combo.setCurrentIndex(s.value("unit", 1, type=int))  # mặc định: 3 phút
        self.jitter_spin.setValue(s.value("jitter", 0, type=int))
        self.repeat_spin.setValue(s.value("repeat", 0, type=int))
        self.click_now_cb.setChecked(s.value("click_now", False, type=bool))
        self.button_combo.setCurrentIndex(s.value("button", 0, type=int))
        self.type_combo.setCurrentIndex(s.value("click_type", 0, type=int))
        self.pos_jitter_spin.setValue(s.value("pos_jitter", 0, type=int))
        self.restore_cb.setChecked(s.value("restore", True, type=bool))
        self.awake_cb.setChecked(s.value("keep_awake", True, type=bool))
        self.failsafe_cb.setChecked(s.value("failsafe", True, type=bool))

    def _save_settings(self):
        values = {
            "x": self.x_spin.value(), "y": self.y_spin.value(),
            "interval": self.interval_spin.value(), "unit": self.unit_combo.currentIndex(),
            "jitter": self.jitter_spin.value(), "repeat": self.repeat_spin.value(),
            "click_now": self.click_now_cb.isChecked(),
            "button": self.button_combo.currentIndex(), "click_type": self.type_combo.currentIndex(),
            "pos_jitter": self.pos_jitter_spin.value(), "keep_awake": self.awake_cb.isChecked(),
        }
        if self.backend.can_read_cursor:  # Wayland khóa 2 tùy chọn này -> giữ nguyên giá trị cũ
            values.update(restore=self.restore_cb.isChecked(), failsafe=self.failsafe_cb.isChecked())
        for key, val in values.items():
            self.settings.setValue(key, val)
        self.settings.sync()

    # ───────────── Chọn vị trí ─────────────
    def start_pick(self):
        self.hide()
        QTimer.singleShot(300, self.picker.start)  # đợi cửa sổ ẩn hẳn

    def _on_picked(self, x, y):
        self.x_spin.setValue(x)
        self.y_spin.setValue(y)
        self.log(f"Đã chọn vị trí ({x}, {y})")
        self._save_settings()
        QTimer.singleShot(300, self.show_target)

    def show_target(self):
        self._marker = TargetMarker(self.x_spin.value(), self.y_spin.value())
        self._marker.present()

    def _update_cursor_label(self):
        if not self.backend.can_read_cursor:
            self.cursor_lbl.setText("Wayland không cho đọc vị trí chuột ngoài app — dùng nút Chọn vị trí.")
            self.cursor_timer.stop()
            return
        p = QCursor.pos()
        self.cursor_lbl.setText(f"Chuột hiện tại:  X = {p.x():<6} Y = {p.y()}")

    def _update_target_label(self):
        scr = QGuiApplication.screenAt(QPoint(self.x_spin.value(), self.y_spin.value()))
        if scr:
            geo = scr.geometry()
            self.target_lbl.setText(f"Điểm click trên màn hình: {scr.name()} ({geo.width()}×{geo.height()})")
        else:
            self.target_lbl.setText("⚠️ Tọa độ nằm ngoài mọi màn hình")

    # ───────────── Chạy / dừng ─────────────
    def toggle(self):
        self.stop() if self.running else self.start()

    def start(self):
        self.backend.request_permission()
        err = self.backend.status()
        if err:
            self._check_backend()
            QMessageBox.warning(self, APP_NAME, err)
            return
        x, y = self.x_spin.value(), self.y_spin.value()
        if QGuiApplication.screenAt(QPoint(x, y)) is None:
            if QMessageBox.question(self, APP_NAME, "Tọa độ nằm ngoài màn hình. Vẫn chạy?") != QMessageBox.Yes:
                return
        self._save_settings()
        self.running = True
        self.count = 0
        self.next_at = time.monotonic() + (0 if self.click_now_cb.isChecked() else self._next_interval())
        if not self.keepawake.begin(self.awake_cb.isChecked()):
            self.log("Không xin được chế độ chống ngủ (không sao nếu chu kỳ ngắn hơn thời gian khóa màn hình).")
        self._set_running_ui(True)
        self.log(f"▶ Bắt đầu: click {self.button_combo.currentText().lower()} tại ({x}, {y}) "
                 f"mỗi {self.interval_spin.value()} {self.unit_combo.currentText()}")
        self.tick_timer.start(200)
        self._tick()

    def stop(self, reason: str = "Đã dừng"):
        if not self.running:
            return
        self.running = False
        self.tick_timer.stop()
        self.keepawake.end()
        self._set_running_ui(False)
        self.log(f"■ {reason}")

    def _next_interval(self) -> float:
        base = self.interval_spin.value() * self.unit_combo.currentData()
        j = self.jitter_spin.value()
        return max(1.0, base + random.uniform(-j, j))

    def _tick(self):
        if not self.running:
            return
        if self.failsafe_cb.isChecked() and self.backend.can_read_cursor:
            p = QCursor.pos()
            if p.x() <= 2 and p.y() <= 2:
                self.stop("Dừng khẩn cấp (chuột ở góc trên-trái)")
                return
        now = time.monotonic()
        if now >= self.next_at:
            self._do_click()
            limit = self.repeat_spin.value()
            if limit and self.count >= limit:
                self.stop(f"Hoàn tất {self.count} lần click")
                return
            self.next_at = now + self._next_interval()
        remaining = fmt_duration(self.next_at - now)
        self.countdown_lbl.setText(remaining)
        if self.tray:
            self.tray.setToolTip(f"{APP_NAME} — click tiếp sau {remaining}")

    def _do_click(self):
        x, y = self.x_spin.value(), self.y_spin.value()
        j = self.pos_jitter_spin.value()
        if j:
            x, y = x + random.randint(-j, j), y + random.randint(-j, j)
        restore = self.restore_cb.isChecked() and self.backend.can_read_cursor
        prev = QCursor.pos()
        try:
            self.backend.click(x, y, self.button_combo.currentData(), self.type_combo.currentData())
            if restore:
                self.backend.move(prev.x(), prev.y())
        except Exception as e:  # noqa: BLE001
            self.log(f"Lỗi khi click: {e}")
            return
        self.count += 1
        self.count_lbl.setText(f"Đã click: {self.count}")
        self.log(f"Click #{self.count} tại ({x}, {y})"
                 + ("  [mô phỏng]" if isinstance(self.backend, DryBackend) else ""))

    def _set_running_ui(self, running: bool):
        for box in (self.position_box, self.time_box, self.click_box):
            box.setEnabled(not running)
        self.start_btn.setText(f"■  Dừng   ({SHORTCUT_LABEL})" if running else f"▶  Bắt đầu   ({SHORTCUT_LABEL})")
        self.start_btn.setProperty("running", running)
        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)
        color = "#16a34a" if running else "#9ca3af"
        self.state_lbl.setText(f"<span style='color:{color}'>●</span> {'Đang chạy' if running else 'Đang dừng'}")
        self.count_lbl.setText(f"Đã click: {self.count}")
        if not running:
            self.countdown_lbl.setText("--:--")
        if self.tray:
            self.tray_toggle.setText("Dừng" if running else "Bắt đầu")
            self.tray.setToolTip(APP_NAME)

    # ───────────── Khác ─────────────
    def _check_backend(self):
        err = self.backend.status()
        self.warn_lbl.setText(f"⚠️  {err}" if err else "")
        self.warn_banner.setVisible(bool(err))

    def log(self, text: str):
        self.log_view.appendPlainText(f"[{datetime.now():%H:%M:%S}] {text}")

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, e):
        # Đang chạy (có icon khay): đóng cửa sổ nhưng vẫn click ở nền. Đang dừng: thoát app.
        e.accept()
        if self.running and self.tray:
            self.tray.showMessage(APP_NAME, "Vẫn đang chạy ở nền. Mở lại từ icon Auto Clicker trên khay hệ thống.",
                                  QSystemTrayIcon.Information, 2500)
        else:
            QTimer.singleShot(0, QApplication.quit)

    def _cleanup(self):
        self.stop()
        self._save_settings()
        self.backend.close()


class _ReopenOnActivate(QObject):
    """macOS: bấm icon trên Dock khi cửa sổ đang ẩn -> hiện lại."""

    def __init__(self, window: MainWindow):
        super().__init__()
        self.window = window

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.ApplicationActivate and not self.window.isVisible() \
                and not self.window.picker.overlays:
            self.window.show_window()
        return False


SOCKET_NAME = f"{APP_ID}-{getpass.getuser()}"


def _notify_running_instance() -> bool:
    """Nếu app đang chạy (có thể đang ẩn) thì bảo nó hiện cửa sổ; bản mới tự thoát."""
    sock = QLocalSocket()
    sock.connectToServer(SOCKET_NAME)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.waitForBytesWritten(300)
        return True
    return False


def run(argv: list[str]) -> int:
    if sys.platform.startswith("linux"):
        QApplication.setApplicationName(APP_ID)  # WM_CLASS (X11)
        QGuiApplication.setDesktopFileName(APP_ID)  # app_id (Wayland) -> GNOME hiện đúng icon
    else:
        QApplication.setApplicationName(APP_NAME)
    if sys.platform == "win32":  # taskbar hiện icon của app thay vì icon Python
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"{ORG_NAME}.AutoClicker")

    app = QApplication(argv)
    if _notify_running_instance():
        return 0
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(make_icon(256)))

    window = MainWindow()
    QLocalServer.removeServer(SOCKET_NAME)
    server = QLocalServer()
    server.listen(SOCKET_NAME)
    server.newConnection.connect(lambda: (server.nextPendingConnection(), window.show_window()))
    if IS_MAC:
        reopen = _ReopenOnActivate(window)
        app.installEventFilter(reopen)

    window.show()
    return app.exec()
