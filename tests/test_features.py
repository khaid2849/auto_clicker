"""UI strings, theme and the browser extension."""
import json
import re
from pathlib import Path

from autoclicker import __version__, i18n

ROOT = Path(__file__).resolve().parent.parent
EXT_DIR = ROOT / "src" / "autoclicker" / "browser_extension"


def test_tr_formats_and_falls_back_to_key():
    assert i18n.tr("clicks", n=5) == "Clicks: 5"
    assert i18n.tr("no-such-key") == "no-such-key"


def test_every_tr_key_exists():
    used = set()
    for path in (ROOT / "src" / "autoclicker").rglob("*.py"):
        if path.name == "i18n.py":  # its docstring contains a tr("key", ...) example
            continue
        used |= set(re.findall(r'\btr\(\s*f?["\']([a-z0-9_]+)["\']', path.read_text(encoding="utf-8")))
    used.discard("theme_")  # built as f"theme_{mode}"
    assert not used - set(i18n.STRINGS)


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
    export_extension(dest)  # running it again (update) works


def test_theme_combo_and_palette(qapp):
    from autoclicker import theme
    from autoclicker.app import MainWindow
    w = MainWindow()
    w.theme_combo.setCurrentIndex(w.theme_combo.findData("dark"))
    assert w.theme_mode == "dark"
    assert qapp.palette().window().color().name() == "#1f2023"
    assert theme.apply_theme("light") is False
    assert qapp.palette().window().color().name() == "#f3f4f6"
    assert "@" not in theme.stylesheet(True)  # every color variable was substituted


def test_window_fits_a_short_screen(qapp):
    """1366×768 laptops: the window must fit the work area, the settings scroll instead."""
    from autoclicker.app import MainWindow
    w = MainWindow()
    assert w.minimumSizeHint().height() <= 600  # room for a taskbar + title bar on a 768 px screen
    w.show()
    w._fit_to_screen()
    assert w.frameGeometry().height() <= w.screen().availableGeometry().height()
    assert w.start_btn.isVisibleTo(w)
    w.hide()
