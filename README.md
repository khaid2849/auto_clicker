# Auto Clicker

Tự động click chuột tại một vị trí cố định theo chu kỳ (mặc định 3 phút/lần), có giao diện đồ họa.
Một mã nguồn duy nhất chạy trên **macOS**, **Windows** và **Linux** (Ubuntu X11 lẫn Wayland).

<p align="center"><img src="docs/screenshot.png" width="360" alt="Giao diện Auto Clicker"></p>

## Tính năng

- **Chọn vị trí trực quan**: màn hình phủ mờ với tâm ngắm và tọa độ X/Y chạy theo chuột, click để chọn. Hỗ trợ nhiều màn hình.
- **Hiện điểm**: nháy vòng tròn đỏ đúng chỗ sẽ click để kiểm tra.
- **Tùy chỉnh**: chu kỳ theo giây/phút/giờ, cộng trừ ngẫu nhiên, dừng sau N lần, nút trái/phải/giữa, click đơn/đôi, lệch vị trí ngẫu nhiên.
- **Chạy nền an toàn**: trả con trỏ về chỗ cũ, chống ngủ/khóa màn hình, dừng khẩn cấp khi đưa chuột vào góc trên-trái, điều khiển từ icon khay hệ thống, phím tắt `Ctrl+Enter` (`⌘↩` trên Mac).
- **Tự lưu cài đặt** cho lần mở sau.

## Cài đặt

### Cách 1: tải bản dựng sẵn (không cần Python)

Vào trang [Releases](https://github.com/khaid2849/auto_clicker/releases), tải file đúng hệ điều hành:

| Hệ điều hành | File | Cách mở |
|---|---|---|
| Windows | `AutoClicker-windows-x64.zip` | Giải nén, chạy `AutoClicker.exe`. Nếu SmartScreen chặn: **More info → Run anyway** |
| macOS (Apple Silicon) | `AutoClicker-macos-arm64.zip` | Giải nén, kéo `AutoClicker.app` vào Applications. Lần đầu: chuột phải → **Open** (app chưa ký) |
| Linux | `AutoClicker-linux-x64.tar.gz` | `tar xzf AutoClicker-linux-x64.tar.gz && ./AutoClicker/AutoClicker` |

### Cách 2: chạy từ mã nguồn (giống nhau cho mọi hệ điều hành)

Cần Python 3.9 trở lên.

```bash
git clone https://github.com/khaid2849/auto_clicker.git
cd auto_clicker
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install .
autoclicker                      # hoặc: python -m autoclicker
```

`pip` tự cài đúng thư viện cho hệ điều hành của bạn (pyobjc trên macOS, python-xlib và jeepney trên Linux; Windows chỉ cần PySide6).

**Ubuntu**: thay vì các bước trên, chạy một lệnh để có sẵn icon trong menu ứng dụng và tự cấu hình Wayland:

```bash
./scripts/install_linux.sh       # gỡ: ./scripts/uninstall_linux.sh
```

### Cách 3: tự đóng gói thành app

```bash
pip install ".[build]"
python scripts/build.py
```

Kết quả trong `dist/`: `AutoClicker.app` trên macOS, `AutoClicker.exe` (một file duy nhất) trên Windows, thư mục `AutoClicker/` trên Linux. Muốn có app cho hệ điều hành nào thì chạy lệnh trên chính hệ điều hành đó.

## Lưu ý theo hệ điều hành

### macOS
macOS chỉ cho gửi click khi app có quyền **Accessibility**. Lần đầu bấm Bắt đầu, app sẽ hiện cảnh báo kèm nút **Mở cài đặt**: vào *System Settings → Privacy & Security → Accessibility* và bật **AutoClicker**. Nếu chạy từ Terminal thì bật cho **Terminal**.
Mỗi lần build lại `.app`, chữ ký thay đổi, nên phải xóa mục cũ trong danh sách Accessibility rồi thêm lại.

### Windows
Windows không cho app thường click vào cửa sổ đang chạy bằng quyền Administrator. Nếu cần click vào app như vậy, hãy chạy Auto Clicker bằng **Run as administrator**.

### Linux
| | X11 (Ubuntu on Xorg) | Wayland (mặc định từ Ubuntu 22.04) |
|---|---|---|
| Cách gửi click | XTest | Chuột ảo qua `/dev/uinput` |
| Cần cấu hình thêm | Không | `./scripts/setup_uinput.sh`, rồi đăng xuất và đăng nhập lại |
| Xem vị trí chuột trực tiếp / trả con trỏ về chỗ cũ / dừng khẩn cấp | Có | Không (Wayland không cho app đọc vị trí chuột) |

- Qt cần gói `libxcb-cursor0`: `sudo apt install libxcb-cursor0` (`install_linux.sh` đã tự cài).
- Trên Wayland nếu dùng nhiều màn hình mà click bị lệch, hãy chuyển sang phiên **Ubuntu on Xorg** ở màn hình đăng nhập (biểu tượng ⚙️).

## Cấu trúc dự án

```
src/autoclicker/
├── __main__.py          # điểm vào: lệnh `autoclicker` / `python -m autoclicker`
├── app.py               # cửa sổ chính (dùng chung mọi hệ điều hành)
├── overlays.py          # màn hình chọn vị trí, vòng tròn đánh dấu
├── common.py            # hằng số, icon, tiện ích
└── backends/            # phần duy nhất khác nhau giữa các hệ điều hành
    ├── __init__.py      # tự nhận diện hệ điều hành / phiên → chọn backend
    ├── base.py          # interface chung: move(), click(), status()...
    ├── macos.py         # Quartz CGEvent + chống App Nap
    ├── windows.py       # SetCursorPos + SendInput (ctypes)
    ├── x11.py           # XTest
    ├── wayland.py       # chuột ảo /dev/uinput
    └── linux_session.py # chống khóa màn hình qua D-Bus
scripts/                 # build.py (PyInstaller), cài đặt Linux, cấu hình uinput
tests/                   # pytest
```

Thêm hệ điều hành hoặc cách click mới chỉ cần viết một lớp kế thừa `backends.base.Backend` rồi đăng ký trong `backends/__init__.py`.

## Phát triển

```bash
pip install -e ".[dev]"
pytest
AUTOCLICKER_BACKEND=dry autoclicker   # chạy giao diện ở chế độ mô phỏng, không click thật
```

Biến môi trường `AUTOCLICKER_BACKEND` (`macos` | `windows` | `x11` | `wayland` | `dry`) dùng để ép chọn backend.

**Phát hành**: push một tag dạng `v*` để GitHub Actions chạy test, đóng gói app cho cả 3 hệ điều hành và tạo Release:

```bash
git tag v1.0.0 && git push origin v1.0.0
```
