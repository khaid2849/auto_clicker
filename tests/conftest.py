import os

# Must be set before autoclicker / Qt is imported
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["AUTOCLICKER_BACKEND"] = "dry"

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def qapp(tmp_path_factory):
    os.environ["AUTOCLICKER_SETTINGS"] = str(tmp_path_factory.mktemp("cfg") / "settings.ini")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
