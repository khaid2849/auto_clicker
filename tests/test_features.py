"""Đa ngôn ngữ, theme và extension trình duyệt."""
import json
import re
from pathlib import Path

from autoclicker import __version__, i18n

EXT_DIR = Path(__file__).resolve().parent.parent / "src" / "autoclicker" / "browser_extension"


def test_desktop_languages_have_same_keys():
    keys = {lang: set(d) for lang, d in i18n.STRINGS.items()}
    assert keys["vi"] == keys["en"]
    assert set(i18n.LANGUAGES) == set(i18n.STRINGS)


def test_tr_formats_and_falls_back():
    i18n.set_language("vi")
    assert i18n.tr("clicks", n=5) == "Đã click: 5"
    i18n.set_language("en")
    assert i18n.tr("clicks", n=5) == "Clicks: 5"
    assert i18n.set_language("xx") == i18n.DEFAULT  # ngôn ngữ lạ -> mặc định


def test_extension_languages_have_same_keys():
    src = (EXT_DIR / "i18n.js").read_text(encoding="utf-8")
    vi_block, en_block = re.search(r"vi: \{(.*?)\n  \},\n  en: \{(.*?)\n  \},", src, re.S).groups()
    keys = lambda block: set(re.findall(r"^\s+(\w+):", block, re.M))  # noqa: E731
    assert keys(vi_block) == keys(en_block)


def test_extension_manifest_matches_package_version():
    manifest = json.loads((EXT_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3
    assert manifest["version"] == __version__
    for icon in manifest["icons"].values():
        assert (EXT_DIR / icon).is_file()


def test_export_extension(qapp, tmp_path):
    from autoclicker.extension_installer import export_extension
    dest = export_extension(tmp_path / "ext")
    assert (dest / "manifest.json").is_file()
    assert (dest / "icons" / "icon128.png").is_file()
    export_extension(dest)  # chạy lại (cập nhật) không lỗi


def test_language_switch_keeps_state(qapp):
    from autoclicker.app import MainWindow
    w = MainWindow()
    w.set_language("en")
    qapp.processEvents()
    w.x_spin.setValue(1234)
    w.set_language("vi")
    qapp.processEvents()
    assert w.x_spin.value() == 1234
    assert w.time_box.title() == "Thời gian"
    assert w.lang_combo.currentData() == "vi"
    w.set_language("en")
    qapp.processEvents()
    assert w.time_box.title() == "Timing"


def test_theme_palette(qapp):
    from autoclicker import theme
    assert theme.apply_theme("dark") is True
    assert qapp.palette().window().color().name() == "#1f2023"
    assert theme.apply_theme("light") is False
    assert qapp.palette().window().color().name() == "#f3f4f6"
    assert "@" not in theme.stylesheet(True)  # mọi biến màu đã được thay
