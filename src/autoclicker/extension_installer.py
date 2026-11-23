"""Hộp thoại hướng dẫn cài extension Chrome/Edge bằng 'Load unpacked'.

Chrome/Edge không cho ứng dụng tự cài extension (chỉ qua store hoặc Developer mode), nên app:
  1. chép extension ra một thư mục cố định, dễ tìm (Documents/AutoClicker Extension),
  2. chép sẵn địa chỉ trang quản lý extension để dán vào trình duyệt,
  3. hướng dẫn bật Developer mode → Load unpacked.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QDialog, QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .common import mono_font
from .i18n import tr

EXTENSION_SRC = Path(__file__).resolve().parent / "browser_extension"
BROWSER_PAGES = ("chrome://extensions", "edge://extensions")


def install_dir() -> Path:
    docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation) or str(Path.home())
    return Path(docs) / "AutoClicker Extension"


def export_extension(dest: Path | None = None) -> Path:
    """Chép (ghi đè) extension ra thư mục cố định; trình duyệt sẽ load extension từ đây."""
    dest = dest or install_dir()
    shutil.copytree(EXTENSION_SRC, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
    return dest


class ExtensionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("ext_title"))
        self.setMinimumWidth(self.fontMetrics().averageCharWidth() * 70)
        root = QVBoxLayout(self)
        root.setSpacing(10)

        intro = QLabel(tr("ext_intro"), wordWrap=True, textFormat=Qt.RichText)
        root.addWidget(intro)

        # Bước 1
        step1 = QGroupBox(tr("ext_step1"))
        v1 = QVBoxLayout(step1)
        btn = QPushButton(tr("ext_step1_btn"))
        btn.clicked.connect(self._create_folder)
        self.path_lbl = QLabel(wordWrap=True, font=mono_font(10))
        self.path_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.path_lbl.hide()
        v1.addWidget(btn)
        v1.addWidget(self.path_lbl)
        root.addWidget(step1)

        # Bước 2
        step2 = QGroupBox(tr("ext_step2"))
        v2 = QVBoxLayout(step2)
        v2.addWidget(QLabel(tr("ext_step2_text"), wordWrap=True))
        row = QHBoxLayout()
        self.copy_btns = {}
        for url in BROWSER_PAGES:
            b = QPushButton(tr("ext_copy", url=url))
            b.setProperty("url", url)
            b.clicked.connect(self._on_copy_clicked)  # không dùng lambda: xem ghi chú trong app.py
            row.addWidget(b)
            self.copy_btns[url] = b
        v2.addLayout(row)
        root.addWidget(step2)

        # Bước 3, 4
        step3 = QGroupBox(tr("ext_step3"))
        v3 = QVBoxLayout(step3)
        v3.addWidget(QLabel(tr("ext_step3_text"), wordWrap=True, textFormat=Qt.RichText))
        v3.addWidget(QLabel(tr("ext_step4"), wordWrap=True))
        root.addWidget(step3)

        note = QLabel(tr("ext_note"), wordWrap=True, objectName="muted")
        root.addWidget(note)

        close = QPushButton(tr("close"))
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close)
        root.addLayout(row)

    def _create_folder(self):
        try:
            path = export_extension()
        except OSError as e:
            self.path_lbl.setText(tr("ext_step1_error", e=e))
        else:
            self.path_lbl.setText(f"{tr('ext_step1_done')}\n{path}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        self.path_lbl.show()

    def _on_copy_clicked(self):
        self._copy(self.sender().property("url"))

    def _copy(self, url: str):
        QGuiApplication.clipboard().setText(url)
        for u, b in self.copy_btns.items():
            b.setText(tr("ext_copied" if u == url else "ext_copy", url=u))
