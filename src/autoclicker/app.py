"""Main window: settings, countdown, log and system tray icon."""
from __future__ import annotations

import getpass
import os
import random
import sys
import time
from datetime import datetime

from PySide6.QtCore import QEvent, QObject, QPoint, QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFormLayout, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
    QScrollArea, QSpinBox, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from . import __version__, backends, theme
from .backends import DryBackend
from .common import APP_ID, APP_NAME, ORG_NAME, fmt_duration, make_icon, mono_font
from .i18n import tr
from .overlays import PositionPicker, TargetMarker

IS_MAC = backends.KIND == "macos"
SHORTCUT_LABEL = "⌘↩" if IS_MAC else "Ctrl+Enter"

UNITS = [("unit_s", 1), ("unit_m", 60), ("unit_h", 3600)]
BUTTONS = [("btn_left", "left"), ("btn_right", "right"), ("btn_middle", "middle")]
CLICK_TYPES = [("single", 1), ("double", 2)]


class SettingsScroll(QScrollArea):
    """Scrolls the settings boxes when the screen is too short (e.g. 1366×768), so the window can
    shrink while the Start button below it stays visible. On a tall screen it shows everything."""

    def __init__(self, content: QWidget):
        super().__init__(objectName="settingsScroll", widgetResizable=True, frameShape=QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(content)
        self.verticalScrollBar().rangeChanged.connect(self._on_range_changed)

    def _on_range_changed(self, _min: int, max_: int):
        """A small gap between the boxes and the scrollbar, only while the scrollbar is shown."""
        self.widget().layout().setContentsMargins(0, 0, 6 if max_ > 0 else 0, 0)

    def _bar_width(self) -> int:
        return self.verticalScrollBar().sizeHint().width()

    def sizeHint(self) -> QSize:  # QScrollArea caps its hint at 24 lines; we want the whole content
        hint = self.widget().sizeHint()
        return QSize(hint.width() + self._bar_width(), hint.height() + 2 * self.frameWidth())

    def minimumSizeHint(self) -> QSize:  # full width (room for the scrollbar), but any height
        return QSize(self.widget().minimumSizeHint().width() + self._bar_width(),
                     self.fontMetrics().lineSpacing() * 6)


def make_settings() -> QSettings:
    path = os.environ.get("AUTOCLICKER_SETTINGS")  # used by the tests
    return QSettings(path, QSettings.IniFormat) if path else QSettings(ORG_NAME, "AutoClicker")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(make_icon()))

        self.settings = make_settings()
        self.theme_mode = self.settings.value("theme", "system")
        self._applying_theme = False

        self.backend = backends.create_backend()
        self.keepawake = backends.create_keepawake()
        self.running = False
        self.count = 0
        self.next_at = 0.0
        self._marker = None
        self._ext_dialog = None
        self.tray = None

        self.picker = PositionPicker(self)
        self.picker.picked.connect(self._on_picked)
        self.picker.finished.connect(self.show_window)

        self._fitted = False
        self._apply_theme()
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_system_scheme_changed)

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

        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.toggle)  # ⌘↩ on macOS
        QApplication.instance().aboutToQuit.connect(self._cleanup)

    # ───────────── UI ─────────────
    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(10)

        root.addLayout(self._build_top_bar())

        self.warn_banner = QFrame(objectName="warnBanner")
        hb = QHBoxLayout(self.warn_banner)
        self.warn_lbl = QLabel(wordWrap=True)
        hb.addWidget(self.warn_lbl, 1)
        if self.backend.fix_action:
            fix_btn = QPushButton(tr(self.backend.fix_action[0]))
            fix_btn.clicked.connect(self._run_fix_action)
            hb.addWidget(fix_btn)
        root.addWidget(self.warn_banner)

        content = QWidget(objectName="settingsPane")
        boxes = QVBoxLayout(content)
        boxes.setContentsMargins(0, 0, 0, 0)
        boxes.setSpacing(10)
        boxes.addWidget(self._build_position_box())
        boxes.addWidget(self._build_time_box())
        boxes.addWidget(self._build_click_box())
        boxes.addStretch()
        self.settings_scroll = SettingsScroll(content)
        root.addWidget(self.settings_scroll, 1)
        root.addWidget(self._build_status_card())

        self.log_view = QPlainTextEdit(readOnly=True)
        self.log_view.setMaximumBlockCount(300)
        self.log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_view.setFont(mono_font(10))
        self.log_view.setFixedHeight(self.log_view.fontMetrics().lineSpacing() * 6 + 12)
        root.addWidget(self.log_view)

        self.setCentralWidget(central)
        # Width follows the font size so the window still fits at 125–200% display scaling
        self.setMinimumWidth(self.fontMetrics().averageCharWidth() * 60)
        self.resize(self.minimumWidth(), self.sizeHint().height())
        self._fit_to_screen()
        self._set_running_ui(self.running)

    def _build_top_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.setToolTip(tr("theme"))
        for mode in theme.THEMES:
            self.theme_combo.addItem({"system": "◐", "light": "☀", "dark": "☾"}[mode] + "  " + tr(f"theme_{mode}"), mode)
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(self.theme_mode)))
        self.theme_combo.currentIndexChanged.connect(self._on_theme_combo)

        ext_btn = QPushButton(tr("browser_ext"))
        ext_btn.clicked.connect(self.open_extension_dialog)

        row.addWidget(self.theme_combo)
        row.addStretch()
        row.addWidget(ext_btn)
        return row

    def _build_position_box(self) -> QGroupBox:
        box = QGroupBox(tr("pos_box"))
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
        self.pick_btn = QPushButton(tr("pick"))
        self.pick_btn.clicked.connect(self.start_pick)
        self.show_btn = QPushButton(tr("show_point"))
        self.show_btn.setToolTip(tr("show_point_tip"))
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
        box = QGroupBox(tr("time_box"))
        f = QFormLayout(box)
        row = QHBoxLayout()
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 99999)
        self.unit_combo = QComboBox()
        for key, mult in UNITS:
            self.unit_combo.addItem(tr(key), mult)
        row.addWidget(self.interval_spin, 1)
        row.addWidget(self.unit_combo)
        f.addRow(tr("every"), row)
        self.jitter_spin = QSpinBox()
        self.jitter_spin.setRange(0, 3600)
        self.jitter_spin.setSuffix(tr("suffix_s"))
        self.jitter_spin.setToolTip(tr("jitter_tip"))
        f.addRow(tr("jitter"), self.jitter_spin)
        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(0, 1_000_000)
        self.repeat_spin.setSpecialValueText(tr("unlimited"))
        self.repeat_spin.setSuffix(tr("suffix_times"))
        f.addRow(tr("stop_after"), self.repeat_spin)
        self.click_now_cb = QCheckBox(tr("click_now"))
        f.addRow(self.click_now_cb)
        self.time_box = box
        return box

    def _build_click_box(self) -> QGroupBox:
        box = QGroupBox(tr("click_box"))
        f = QFormLayout(box)
        self.button_combo = QComboBox()
        for key, val in BUTTONS:
            self.button_combo.addItem(tr(key), val)
        self.type_combo = QComboBox()
        for key, val in CLICK_TYPES:
            self.type_combo.addItem(tr(key), val)
        self.pos_jitter_spin = QSpinBox()
        self.pos_jitter_spin.setRange(0, 200)
        self.pos_jitter_spin.setSuffix(" px")
        self.pos_jitter_spin.setToolTip(tr("pos_jitter_tip"))
        f.addRow(tr("mouse_button"), self.button_combo)
        f.addRow(tr("click_kind"), self.type_combo)
        f.addRow(tr("pos_jitter"), self.pos_jitter_spin)
        self.restore_cb = QCheckBox(tr("restore"))
        self.awake_cb = QCheckBox(tr("keep_awake"))
        self.failsafe_cb = QCheckBox(tr("failsafe"))
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
        v.addWidget(QLabel(tr("next_click"), alignment=Qt.AlignCenter))
        self.countdown_lbl = QLabel("--:--", alignment=Qt.AlignCenter)
        self.countdown_lbl.setFont(mono_font(28, bold=True))
        v.addWidget(self.countdown_lbl)
        self.start_btn = QPushButton(objectName="startBtn")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.toggle)
        v.addWidget(self.start_btn)
        self.backend_lbl = QLabel(objectName="muted", alignment=Qt.AlignCenter)
        v.addWidget(self.backend_lbl)
        return card

    def _apply_backend_limits(self):
        self.backend_lbl.setText(tr("backend_info", v=__version__, platform=backends.platform_label(),
                                    backend=self.backend.name))
        if not self.backend.can_read_cursor:
            for cb in (self.restore_cb, self.failsafe_cb):
                cb.setChecked(False)
                cb.setEnabled(False)
                cb.setToolTip(tr("wayland_tip"))

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(QIcon(make_icon(64)), self)
        self._tray_menu = QMenu()
        self.tray_toggle = self._tray_menu.addAction("", self.toggle)
        self.tray_show = self._tray_menu.addAction("", self.show_window)
        self._tray_menu.addSeparator()
        self.tray_quit = self._tray_menu.addAction("", QApplication.quit)
        self.tray.setContextMenu(self._tray_menu)
        if not IS_MAC:  # on macOS clicking the icon already opens the menu
            self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()
        self._set_running_ui(self.running)

    # ───────────── Slots ─────────────
    # Always connect signals to methods of the window, NEVER to a lambda/partial: for those PySide
    # creates an extra receiver QObject holding a reference cycle back to self, and at interpreter
    # exit they are destroyed in the wrong order -> "shared QObject was deleted directly", then a
    # crash (SIGABRT/SIGBUS).
    def _on_theme_combo(self, _index: int):
        self.set_theme(self.theme_combo.currentData())

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_window()

    def _on_ext_dialog_finished(self, _result: int):
        self._ext_dialog = None

    def _run_fix_action(self):
        self.backend.fix_action[1]()

    def _on_instance_ping(self):
        """Another instance was launched: bring this one's window to the front."""
        server = self.sender()
        while server.hasPendingConnections():
            server.nextPendingConnection().deleteLater()
        self.show_window()

    # ───────────── Theme ─────────────
    def set_theme(self, mode: str):
        self.theme_mode = mode
        self.settings.setValue("theme", mode)
        self._apply_theme()

    def _apply_theme(self):
        self._applying_theme = True
        try:
            dark = theme.apply_theme(self.theme_mode)
            self.setStyleSheet(theme.stylesheet(dark))
        finally:
            self._applying_theme = False

    def _on_system_scheme_changed(self, *_):
        if self.theme_mode == "system" and not self._applying_theme:
            self._apply_theme()

    def open_extension_dialog(self):
        from .extension_installer import ExtensionDialog
        if self._ext_dialog is None:
            self._ext_dialog = ExtensionDialog(self)
            self._ext_dialog.finished.connect(self._on_ext_dialog_finished)
        self._ext_dialog.show()
        self._ext_dialog.raise_()
        self._ext_dialog.activateWindow()

    # ───────────── Settings ─────────────
    def _load_settings(self):
        s = self.settings
        center = QGuiApplication.primaryScreen().geometry().center()
        self.x_spin.setValue(s.value("x", center.x(), type=int))
        self.y_spin.setValue(s.value("y", center.y(), type=int))
        self.interval_spin.setValue(s.value("interval", 3, type=int))
        self.unit_combo.setCurrentIndex(s.value("unit", 1, type=int))  # default: every 3 minutes
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
            "theme": self.theme_mode,
        }
        if self.backend.can_read_cursor:  # disabled on Wayland -> keep the saved values
            values.update(restore=self.restore_cb.isChecked(), failsafe=self.failsafe_cb.isChecked())
        for key, val in values.items():
            self.settings.setValue(key, val)
        self.settings.sync()

    # ───────────── Position ─────────────
    def start_pick(self):
        self.hide()
        QTimer.singleShot(300, self.picker.start)  # wait until the window is really hidden

    def _on_picked(self, x, y):
        self.x_spin.setValue(x)
        self.y_spin.setValue(y)
        self.log(tr("log_picked", x=x, y=y))
        self._save_settings()
        QTimer.singleShot(300, self.show_target)

    def show_target(self):
        self._marker = TargetMarker(self.x_spin.value(), self.y_spin.value())
        self._marker.present()

    def _update_cursor_label(self):
        if not self.backend.can_read_cursor:
            self.cursor_lbl.setText(tr("cursor_wayland"))
            self.cursor_timer.stop()
            return
        p = QCursor.pos()
        self.cursor_lbl.setText(tr("cursor_now", x=p.x(), y=p.y()))

    def _update_target_label(self):
        scr = QGuiApplication.screenAt(QPoint(self.x_spin.value(), self.y_spin.value()))
        if scr:
            geo = scr.geometry()
            self.target_lbl.setText(tr("target_on", name=scr.name(), w=geo.width(), h=geo.height()))
        else:
            self.target_lbl.setText(tr("target_off"))

    # ───────────── Start / stop ─────────────
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
            if QMessageBox.question(self, APP_NAME, tr("outside_confirm")) != QMessageBox.Yes:
                return
        self._save_settings()
        self.running = True
        self.count = 0
        self.next_at = time.monotonic() + (0 if self.click_now_cb.isChecked() else self._next_interval())
        if not self.keepawake.begin(self.awake_cb.isChecked()):
            self.log(tr("log_no_awake"))
        self._set_running_ui(True)
        self.log(tr("log_start", button=self.button_combo.currentText().lower(), x=x, y=y,
                    n=self.interval_spin.value(), unit=self.unit_combo.currentText()))
        self.tick_timer.start(200)
        self._tick()

    def stop(self, reason: str | None = None):
        if not self.running:
            return
        self.running = False
        self.tick_timer.stop()
        self.keepawake.end()
        self._set_running_ui(False)
        self.log(f"■ {reason or tr('reason_stopped')}")

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
                self.stop(tr("reason_failsafe"))
                return
        now = time.monotonic()
        if now >= self.next_at:
            self._do_click()
            limit = self.repeat_spin.value()
            if limit and self.count >= limit:
                self.stop(tr("reason_done", n=self.count))
                return
            self.next_at = now + self._next_interval()
        remaining = fmt_duration(self.next_at - now)
        self.countdown_lbl.setText(remaining)
        if self.tray:
            self.tray.setToolTip(tr("tray_next", app=APP_NAME, t=remaining))

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
            self.log(tr("log_error", e=e))
            return
        self.count += 1
        self.count_lbl.setText(tr("clicks", n=self.count))
        self.log(tr("log_click", n=self.count, x=x, y=y)
                 + (tr("log_dry") if isinstance(self.backend, DryBackend) else ""))

    def _set_running_ui(self, running: bool):
        for box in (self.position_box, self.time_box, self.click_box):
            box.setEnabled(not running)
        self.start_btn.setText(tr("stop" if running else "start", sc=SHORTCUT_LABEL))
        self.start_btn.setProperty("running", running)
        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)
        color = "#16a34a" if running else "#9ca3af"
        self.state_lbl.setText(f"<span style='color:{color}'>●</span> {tr('running' if running else 'stopped')}")
        self.count_lbl.setText(tr("clicks", n=self.count))
        if not running:
            self.countdown_lbl.setText("--:--")
        if self.tray:
            self.tray_toggle.setText(tr("tray_stop" if running else "tray_start"))
            self.tray_show.setText(tr("tray_show"))
            self.tray_quit.setText(tr("tray_quit"))
            self.tray.setToolTip(APP_NAME)

    # ───────────── Window size ─────────────
    def _fit_to_screen(self):
        """Keep the whole window, title bar included, inside the screen's work area (taskbar/panels
        excluded). On a short screen such as 1366×768 the settings scroll instead of the Start button
        ending up below the bottom edge."""
        avail = (self.screen() or QGuiApplication.primaryScreen()).availableGeometry()
        frame_h = self.frameGeometry().height() - self.height()  # 0 until the window is shown
        if frame_h <= 0:
            frame_h = self.fontMetrics().height() * 3  # estimate of the title bar + borders
        h = max(self.minimumSizeHint().height(), min(self.sizeHint().height(), avail.height() - frame_h))
        self.resize(self.width(), h)
        frame = self.frameGeometry()
        if frame.bottom() > avail.bottom() or frame.top() < avail.top():  # no-op on Wayland
            self.move(frame.x(), max(avail.top(), avail.bottom() - frame.height() + 1))

    def showEvent(self, e):
        super().showEvent(e)
        if not self._fitted:  # first show: now the real title bar height is known
            self._fitted = True
            QTimer.singleShot(0, self._fit_to_screen)

    # ───────────── Misc ─────────────
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
        # While running (with a tray icon) closing the window keeps clicking in the background; otherwise quit.
        e.accept()
        if self.running and self.tray:
            self.tray.showMessage(APP_NAME, tr("tray_bg"), QSystemTrayIcon.Information, 2500)
        else:
            QTimer.singleShot(0, QApplication.quit)

    def _cleanup(self):
        self.stop()
        self._save_settings()
        self.backend.close()


class _ReopenOnActivate(QObject):
    """macOS: clicking the Dock icon while the window is hidden shows it again."""

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
    """If the app is already running (maybe hidden), tell it to show its window; this instance then exits."""
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
        QGuiApplication.setDesktopFileName(APP_ID)  # app_id (Wayland) so GNOME shows the right icon
    else:
        QApplication.setApplicationName(APP_NAME)
    if sys.platform == "win32":  # taskbar shows the app icon instead of the Python icon
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"{ORG_NAME}.AutoClicker")

    app = QApplication(argv)
    if _notify_running_instance():
        return 0
    app.setStyle("Fusion")  # same look on every OS and reliable light/dark switching
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(make_icon(256)))

    window = MainWindow()
    QLocalServer.removeServer(SOCKET_NAME)
    server = QLocalServer(window)
    server.listen(SOCKET_NAME)
    server.newConnection.connect(window._on_instance_ping)
    if IS_MAC:
        reopen = _ReopenOnActivate(window)
        app.installEventFilter(reopen)

    window.show()
    return app.exec()
