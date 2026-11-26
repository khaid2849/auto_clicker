"""User-facing strings.

Every visible text has a key; `tr("key", x=1)` returns it formatted. Keeping all strings in one
place makes the wording consistent and leaves room for translations later.
Pure Python (no Qt import) so the backends can use it too.
"""
from __future__ import annotations

STRINGS: dict[str, str] = {
    # Top bar
    "theme": "Theme",
    "theme_system": "System",
    "theme_light": "Light",
    "theme_dark": "Dark",
    "browser_ext": "🧩  Browser extension",
    # Position
    "pos_box": "Click position",
    "pick": "🎯  Pick position on screen",
    "show_point": "Show point",
    "show_point_tip": "Flash a red circle where the click will happen",
    "cursor_now": "Cursor:  X = {x:<6} Y = {y}",
    "cursor_wayland": "Wayland doesn't let apps read the cursor position — use Pick position.",
    "target_on": "Click point is on screen: {name} ({w}×{h})",
    "target_off": "⚠️ Coordinates are outside every screen",
    # Timing
    "time_box": "Timing",
    "every": "Click every",
    "unit_s": "seconds",
    "unit_m": "minutes",
    "unit_h": "hours",
    "jitter": "Random ±",
    "jitter_tip": "Add or subtract a random amount so clicks aren't perfectly regular",
    "suffix_s": " s",
    "stop_after": "Stop after",
    "unlimited": "Unlimited",
    "suffix_times": " clicks",
    "click_now": "Click immediately on Start",
    # Schedule
    "sched_box": "Schedule",
    "sched_start": "Start",
    "sched_stop": "Stop",
    "sched_start_now": "Right away",
    "sched_start_at": "At (time of day)",
    "sched_start_in": "After a countdown",
    "sched_stop_none": "No time limit",
    "sched_stop_at": "At (time of day)",
    "sched_stop_after": "After running for",
    "duration_tip": "Hours : minutes : seconds",
    "when_tomorrow": "{t} tomorrow",
    "when_date": "{t} {date}",
    # Click type
    "click_box": "Click type",
    "mouse_button": "Mouse button",
    "btn_left": "Left",
    "btn_right": "Right",
    "btn_middle": "Middle",
    "click_kind": "Kind",
    "single": "Single click",
    "double": "Double click",
    "pos_jitter": "Position offset ±",
    "pos_jitter_tip": "Random offset around the click point",
    "restore": "Move the cursor back after clicking",
    "keep_awake": "Keep the computer awake while running",
    "failsafe": "Emergency stop when the cursor hits the top-left corner",
    "wayland_tip": "Wayland doesn't let apps read the cursor position, so this option is unavailable.",
    # Status
    "next_click": "Next click in",
    "starts_in": "Starts in",
    "waiting": "Waiting to start",
    "plan_start": "Starts {t}",
    "plan_stop": "Stops {t}",
    "start": "▶  Start   ({sc})",
    "stop": "■  Stop   ({sc})",
    "running": "Running",
    "stopped": "Stopped",
    "clicks": "Clicks: {n}",
    "backend_info": "v{v}  ·  {platform}  ·  via {backend}",
    "outside_confirm": "The coordinates are outside every screen. Run anyway?",
    # System tray
    "tray_start": "Start",
    "tray_stop": "Stop",
    "tray_show": "Show window",
    "tray_quit": "Quit",
    "tray_next": "{app} — next click in {t}",
    "tray_starts": "{app} — starts in {t}",
    "tray_bg": "Still running in the background. Reopen it from the Auto Clicker tray icon.",
    # Log
    "log_picked": "Picked position ({x}, {y})",
    "log_no_awake": "Couldn't keep the computer awake (fine if the interval is shorter than the screen-lock timeout).",
    "log_start": "▶ Started: {button} click at ({x}, {y}) every {n} {unit}",
    "log_scheduled": "⏳ Scheduled: starts {t}",
    "log_stop_at": "Will stop {t}",
    "log_click": "Click #{n} at ({x}, {y})",
    "log_dry": "  [dry run]",
    "log_error": "Click failed: {e}",
    "reason_stopped": "Stopped",
    "reason_failsafe": "Emergency stop (cursor in the top-left corner)",
    "reason_done": "Finished {n} clicks",
    "reason_time_up": "Stop time reached ({n} clicks)",
    # Position picker overlay
    "overlay_hint": "Left-click to pick the position   •   Esc or right-click to cancel",
    # Backends
    "backend_init_failed": "Couldn't start the '{kind}' backend: {e}",
    "open_settings": "Open Settings",
    "mac_no_ax": ("Accessibility permission is missing, so the app can't click yet. System Settings → "
                  "Privacy & Security → Accessibility → turn on Auto Clicker (or Terminal if you run it from Terminal)."),
    "win_blocked": ("SendInput was blocked — the target window may be running as Administrator "
                    "(run Auto Clicker with 'Run as administrator')."),
    "uinput_missing": "/dev/uinput not found (the uinput module isn't loaded). Run scripts/setup_uinput.sh.",
    "uinput_denied": "No write access to /dev/uinput. Run scripts/setup_uinput.sh, then log out and back in.",
    "platform_dry": "Dry run",
    # Browser extension dialog
    "ext_title": "Install the Chrome / Edge extension",
    "ext_intro": ("The extension clicks a button (or a position) <b>inside a web page</b> on a schedule, "
                  "even when the tab is in the background. Works in Chrome, Edge and other Chromium browsers "
                  "(Brave, Opera, Vivaldi)."),
    "ext_step1": "1. Create the extension folder",
    "ext_step1_btn": "Create and open folder",
    "ext_step1_done": "Created at:",
    "ext_step1_error": "Couldn't create the folder: {e}",
    "ext_step2": "2. Open the browser's extensions page",
    "ext_step2_text": "Copy the address and paste it into the browser's address bar:",
    "ext_copy": "Copy {url}",
    "ext_copied": "Copied {url}",
    "ext_step3": "3. Load the extension",
    "ext_step3_text": "Turn on <b>Developer mode</b> → click <b>Load unpacked</b> → choose the folder from step 1.",
    "ext_step4": "4. Pin the Auto Clicker icon to the toolbar (the puzzle-piece 🧩 menu).",
    "ext_note": ("Don't delete this folder: the browser loads the extension from it. After updating the app, "
                 "repeat step 1 and press the reload ↻ button on the extension card."),
    "close": "Close",
}


def tr(key: str, **kwargs) -> str:
    text = STRINGS.get(key, key)
    return text.format(**kwargs) if kwargs else text
