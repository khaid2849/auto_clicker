"""Start / stop schedule: at a time of day or after a countdown."""
import time
from datetime import datetime

from autoclicker.schedule import fmt_when, next_clock, plan

NOW = datetime(2026, 11, 26, 18, 0, 0)


def test_next_clock_today_or_tomorrow():
    assert next_clock(NOW, 19, 30) == datetime(2026, 11, 26, 19, 30)
    assert next_clock(datetime(2026, 11, 26, 20, 0), 19, 30) == datetime(2026, 11, 27, 19, 30)
    assert next_clock(datetime(2026, 11, 26, 19, 30), 19, 30) == datetime(2026, 11, 27, 19, 30)  # already that minute
    assert next_clock(datetime(2026, 12, 31, 23, 0), 1, 0) == datetime(2027, 1, 1, 1, 0)


def test_start_at_stop_at():
    start, stop = plan(NOW, "at", (19, 30), 0, "at", (21, 0), 0)
    assert start == datetime(2026, 11, 26, 19, 30)
    assert stop == datetime(2026, 11, 26, 21, 0)


def test_stop_time_counts_from_the_start():
    # start 22:00, stop 01:00 -> the night after
    start, stop = plan(NOW, "at", (22, 0), 0, "at", (1, 0), 0)
    assert stop == datetime(2026, 11, 27, 1, 0)
    # start right away at 18:00, stop 17:00 -> tomorrow
    _, stop = plan(NOW, "now", (0, 0), 0, "at", (17, 0), 0)
    assert stop == datetime(2026, 11, 27, 17, 0)


def test_start_in_stop_after():
    start, stop = plan(NOW, "in", (0, 0), 20 * 60, "after", (0, 0), 90 * 60)
    assert start == datetime(2026, 11, 26, 18, 20)
    assert stop == datetime(2026, 11, 26, 19, 50)  # 1 h 30 of clicking after the countdown


def test_no_schedule():
    assert plan(NOW, "now", (19, 30), 60, "none", (21, 0), 60) == (NOW, None)


def test_stop_after_is_at_least_one_second():
    _, stop = plan(NOW, "now", (0, 0), 0, "after", (0, 0), 0)
    assert (stop - NOW).total_seconds() == 1


def test_fmt_when():
    assert fmt_when(datetime(2026, 11, 26, 19, 30), NOW) == "19:30"
    assert fmt_when(datetime(2026, 11, 26, 18, 20, 5), NOW) == "18:20:05"
    assert fmt_when(datetime(2026, 11, 27, 1, 0), NOW) == "01:00 tomorrow"
    assert fmt_when(datetime(2026, 11, 30, 1, 0), NOW).startswith("01:00 ")


def _pump(qapp, seconds: float):
    """Run the Qt event loop for a while (the window's timers keep ticking)."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        qapp.processEvents()
        time.sleep(0.01)


def test_window_waits_then_clicks_then_stops_on_time(qapp):
    from PySide6.QtCore import QTime

    from autoclicker.app import MainWindow

    w = MainWindow()
    w.interval_spin.setValue(1)
    w.unit_combo.setCurrentIndex(0)  # seconds
    w.click_now_cb.setChecked(True)
    w.repeat_spin.setValue(0)
    w.start_mode_combo.setCurrentIndex(w.start_mode_combo.findData("in"))
    w.start_in_edit.setTime(QTime(0, 0, 1))
    w.stop_mode_combo.setCurrentIndex(w.stop_mode_combo.findData("after"))
    w.stop_after_edit.setTime(QTime(0, 0, 2))
    w.start()
    assert w.running and w.waiting and w.count == 0
    assert w.next_lbl.text() == "Starts in"
    assert "Starts" in w.plan_lbl.text() and "Stops" in w.plan_lbl.text()
    assert not w.schedule_box.isEnabled()

    _pump(qapp, 1.6)
    assert not w.waiting and w.count == 1  # clicked right away when the countdown ended
    assert w.next_lbl.text() == "Next click in"
    assert w.plan_lbl.text().startswith("Stops")

    _pump(qapp, 2.0)
    assert not w.running  # stopped 2 s after the start
    assert 2 <= w.count <= 3
    assert "Stop time reached" in w.log_view.toPlainText()

    w2 = MainWindow()  # the schedule is saved like the other settings
    assert w2.start_mode_combo.currentData() == "in"
    assert w2.stop_after_edit.time() == QTime(0, 0, 2)
    assert not w2.start_in_edit.isHidden() and w2.start_at_edit.isHidden()


def test_stop_cancels_the_wait(qapp):
    from PySide6.QtCore import QTime

    from autoclicker.app import MainWindow

    w = MainWindow()
    w.start_mode_combo.setCurrentIndex(w.start_mode_combo.findData("in"))
    w.start_in_edit.setTime(QTime(1, 0, 0))
    w.stop_mode_combo.setCurrentIndex(w.stop_mode_combo.findData("none"))
    w.start()
    assert w.waiting and w.state_lbl.text().endswith("Waiting to start")
    w.toggle()
    assert not w.running and not w.waiting and w.count == 0
    assert w.countdown_lbl.text() == "--:--"
    assert w.plan_lbl.text() == "" and w.plan_lbl.isHidden()
    w.start_mode_combo.setCurrentIndex(w.start_mode_combo.findData("now"))
    w._save_settings()  # leave the defaults for the other tests
