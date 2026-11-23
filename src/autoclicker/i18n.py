"""Đa ngôn ngữ Tiếng Việt / English.

Mỗi chuỗi hiển thị có một khóa; `tr("khoa", x=1)` trả về chuỗi theo ngôn ngữ hiện tại.
Thêm ngôn ngữ mới: thêm một dict vào STRINGS và một dòng vào LANGUAGES.
Module thuần Python (không import Qt) để backends cũng dùng được.
"""
from __future__ import annotations

LANGUAGES = {"vi": "Tiếng Việt", "en": "English"}  # luôn hiển thị bằng tên gốc của ngôn ngữ
DEFAULT = "en"

STRINGS: dict[str, dict[str, str]] = {
    "vi": {
        # Thanh trên cùng
        "language": "Ngôn ngữ",
        "theme": "Giao diện",
        "theme_system": "Theo hệ thống",
        "theme_light": "Sáng",
        "theme_dark": "Tối",
        "browser_ext": "🧩  Extension trình duyệt",
        # Vị trí
        "pos_box": "Vị trí click",
        "pick": "🎯  Chọn vị trí trên màn hình",
        "show_point": "Hiện điểm",
        "show_point_tip": "Nháy vòng tròn đỏ tại vị trí sẽ click",
        "cursor_now": "Chuột hiện tại:  X = {x:<6} Y = {y}",
        "cursor_wayland": "Wayland không cho đọc vị trí chuột ngoài app — dùng nút Chọn vị trí.",
        "target_on": "Điểm click trên màn hình: {name} ({w}×{h})",
        "target_off": "⚠️ Tọa độ nằm ngoài mọi màn hình",
        # Thời gian
        "time_box": "Thời gian",
        "every": "Click mỗi",
        "unit_s": "giây",
        "unit_m": "phút",
        "unit_h": "giờ",
        "jitter": "Ngẫu nhiên ±",
        "jitter_tip": "Cộng/trừ ngẫu nhiên vào chu kỳ để không quá đều",
        "suffix_s": " giây",
        "stop_after": "Dừng sau",
        "unlimited": "Không giới hạn",
        "suffix_times": " lần",
        "click_now": "Click ngay khi bấm Bắt đầu",
        # Kiểu click
        "click_box": "Kiểu click",
        "mouse_button": "Nút chuột",
        "btn_left": "Trái",
        "btn_right": "Phải",
        "btn_middle": "Giữa",
        "click_kind": "Loại",
        "single": "Click đơn",
        "double": "Click đôi",
        "pos_jitter": "Lệch vị trí ±",
        "pos_jitter_tip": "Lệch ngẫu nhiên quanh điểm click",
        "restore": "Trả con trỏ về chỗ cũ sau khi click",
        "keep_awake": "Không ngủ / khóa màn hình khi đang chạy",
        "failsafe": "Dừng khẩn cấp khi đưa chuột vào góc trên-trái",
        "wayland_tip": "Wayland không cho ứng dụng đọc vị trí chuột, nên tùy chọn này không dùng được.",
        # Trạng thái
        "next_click": "Lần click tiếp theo sau",
        "start": "▶  Bắt đầu   ({sc})",
        "stop": "■  Dừng   ({sc})",
        "running": "Đang chạy",
        "stopped": "Đang dừng",
        "clicks": "Đã click: {n}",
        "backend_info": "v{v}  ·  {platform}  ·  click qua {backend}",
        "outside_confirm": "Tọa độ nằm ngoài màn hình. Vẫn chạy?",
        # Khay hệ thống
        "tray_start": "Bắt đầu",
        "tray_stop": "Dừng",
        "tray_show": "Hiện cửa sổ",
        "tray_quit": "Thoát",
        "tray_next": "{app} — click tiếp sau {t}",
        "tray_bg": "Vẫn đang chạy ở nền. Mở lại từ icon Auto Clicker trên khay hệ thống.",
        # Nhật ký
        "log_picked": "Đã chọn vị trí ({x}, {y})",
        "log_no_awake": "Không xin được chế độ chống ngủ (không sao nếu chu kỳ ngắn hơn thời gian khóa màn hình).",
        "log_start": "▶ Bắt đầu: click {button} tại ({x}, {y}) mỗi {n} {unit}",
        "log_click": "Click #{n} tại ({x}, {y})",
        "log_dry": "  [mô phỏng]",
        "log_error": "Lỗi khi click: {e}",
        "reason_stopped": "Đã dừng",
        "reason_failsafe": "Dừng khẩn cấp (chuột ở góc trên-trái)",
        "reason_done": "Hoàn tất {n} lần click",
        # Lớp phủ chọn vị trí
        "overlay_hint": "Click chuột trái để chọn vị trí   •   Esc hoặc chuột phải để hủy",
        # Backend
        "backend_init_failed": "Không khởi tạo được backend '{kind}': {e}",
        "open_settings": "Mở cài đặt",
        "mac_no_ax": ("Chưa có quyền Accessibility nên app chưa click được. System Settings → Privacy & Security "
                      "→ Accessibility → bật Auto Clicker (hoặc Terminal nếu chạy từ Terminal)."),
        "win_blocked": ("SendInput bị chặn — cửa sổ đích có thể đang chạy bằng quyền Administrator "
                        "(hãy chạy Auto Clicker bằng 'Run as administrator')."),
        "uinput_missing": "Không thấy /dev/uinput (module uinput chưa nạp). Chạy scripts/setup_uinput.sh.",
        "uinput_denied": ("Chưa có quyền ghi /dev/uinput. Chạy scripts/setup_uinput.sh rồi đăng xuất và "
                          "đăng nhập lại."),
        "platform_dry": "Mô phỏng",
        # Hộp thoại extension
        "ext_title": "Cài extension cho Chrome / Edge",
        "ext_intro": ("Extension tự click vào một nút (hoặc một vị trí) <b>trong trang web</b> theo chu kỳ, "
                      "chạy được cả khi tab ở nền. Dùng cho Chrome, Edge và các trình duyệt nhân Chromium "
                      "(Brave, Cốc Cốc, Opera)."),
        "ext_step1": "1. Tạo thư mục extension",
        "ext_step1_btn": "Tạo và mở thư mục",
        "ext_step1_done": "Đã tạo tại:",
        "ext_step1_error": "Không tạo được thư mục: {e}",
        "ext_step2": "2. Mở trang quản lý extension",
        "ext_step2_text": "Chép địa chỉ rồi dán vào thanh địa chỉ của trình duyệt:",
        "ext_copy": "Chép {url}",
        "ext_copied": "Đã chép {url}",
        "ext_step3": "3. Tải extension vào trình duyệt",
        "ext_step3_text": ("Bật <b>Developer mode</b> (Chế độ dành cho nhà phát triển) → bấm <b>Load unpacked</b> "
                           "(Tải tiện ích đã giải nén) → chọn thư mục ở bước 1."),
        "ext_step4": "4. Ghim icon Auto Clicker lên thanh công cụ (biểu tượng mảnh ghép 🧩).",
        "ext_note": ("Không xóa thư mục này: trình duyệt đọc extension trực tiếp từ đó. Sau khi cập nhật app, "
                     "bấm lại bước 1 rồi bấm nút tải lại ↻ trên thẻ extension."),
        "close": "Đóng",
    },
    "en": {
        "language": "Language",
        "theme": "Theme",
        "theme_system": "System",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "browser_ext": "🧩  Browser extension",
        "pos_box": "Click position",
        "pick": "🎯  Pick position on screen",
        "show_point": "Show point",
        "show_point_tip": "Flash a red circle where the click will happen",
        "cursor_now": "Cursor:  X = {x:<6} Y = {y}",
        "cursor_wayland": "Wayland doesn't let apps read the cursor position — use Pick position.",
        "target_on": "Click point is on screen: {name} ({w}×{h})",
        "target_off": "⚠️ Coordinates are outside every screen",
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
        "next_click": "Next click in",
        "start": "▶  Start   ({sc})",
        "stop": "■  Stop   ({sc})",
        "running": "Running",
        "stopped": "Stopped",
        "clicks": "Clicks: {n}",
        "backend_info": "v{v}  ·  {platform}  ·  via {backend}",
        "outside_confirm": "The coordinates are outside every screen. Run anyway?",
        "tray_start": "Start",
        "tray_stop": "Stop",
        "tray_show": "Show window",
        "tray_quit": "Quit",
        "tray_next": "{app} — next click in {t}",
        "tray_bg": "Still running in the background. Reopen it from the Auto Clicker tray icon.",
        "log_picked": "Picked position ({x}, {y})",
        "log_no_awake": "Couldn't keep the computer awake (fine if the interval is shorter than the screen-lock timeout).",
        "log_start": "▶ Started: {button} click at ({x}, {y}) every {n} {unit}",
        "log_click": "Click #{n} at ({x}, {y})",
        "log_dry": "  [dry run]",
        "log_error": "Click failed: {e}",
        "reason_stopped": "Stopped",
        "reason_failsafe": "Emergency stop (cursor in the top-left corner)",
        "reason_done": "Finished {n} clicks",
        "overlay_hint": "Left-click to pick the position   •   Esc or right-click to cancel",
        "backend_init_failed": "Couldn't start the '{kind}' backend: {e}",
        "open_settings": "Open Settings",
        "mac_no_ax": ("Accessibility permission is missing, so the app can't click yet. System Settings → "
                      "Privacy & Security → Accessibility → turn on Auto Clicker (or Terminal if you run it from Terminal)."),
        "win_blocked": ("SendInput was blocked — the target window may be running as Administrator "
                        "(run Auto Clicker with 'Run as administrator')."),
        "uinput_missing": "/dev/uinput not found (the uinput module isn't loaded). Run scripts/setup_uinput.sh.",
        "uinput_denied": "No write access to /dev/uinput. Run scripts/setup_uinput.sh, then log out and back in.",
        "platform_dry": "Dry run",
        "ext_title": "Install the Chrome / Edge extension",
        "ext_intro": ("The extension clicks a button (or a position) <b>inside a web page</b> on a schedule, "
                      "even when the tab is in the background. Works in Chrome, Edge and other Chromium browsers "
                      "(Brave, Opera, Cốc Cốc)."),
        "ext_step1": "1. Create the extension folder",
        "ext_step1_btn": "Create and open folder",
        "ext_step1_done": "Created at:",
        "ext_step1_error": "Couldn't create the folder: {e}",
        "ext_step2": "2. Open the browser's extensions page",
        "ext_step2_text": "Copy the address and paste it into the browser's address bar:",
        "ext_copy": "Copy {url}",
        "ext_copied": "Copied {url}",
        "ext_step3": "3. Load the extension",
        "ext_step3_text": ("Turn on <b>Developer mode</b> → click <b>Load unpacked</b> → choose the folder from step 1."),
        "ext_step4": "4. Pin the Auto Clicker icon to the toolbar (the puzzle-piece 🧩 menu).",
        "ext_note": ("Don't delete this folder: the browser loads the extension from it. After updating the app, "
                     "repeat step 1 and press the reload ↻ button on the extension card."),
        "close": "Close",
    },
}

_current = DEFAULT


def set_language(code: str) -> str:
    global _current
    _current = code if code in STRINGS else DEFAULT
    return _current


def current_language() -> str:
    return _current


def tr(key: str, **kwargs) -> str:
    text = STRINGS[_current].get(key) or STRINGS[DEFAULT].get(key) or key
    return text.format(**kwargs) if kwargs else text
