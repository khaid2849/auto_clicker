"""Interface chung mà mọi backend phải tuân theo."""
from __future__ import annotations

from typing import Callable, Optional, Tuple


class Backend:
    """Gửi sự kiện chuột. Tọa độ là tọa độ màn hình toàn cục, cùng hệ với Qt (QCursor.pos)."""

    name = "?"
    #: Đọc được vị trí chuột toàn cục không (Wayland: không)
    can_read_cursor = True
    #: (khóa i18n của nhãn nút, hàm) hiện cạnh cảnh báo để người dùng tự sửa, vd. mở cài đặt quyền
    fix_action: Optional[Tuple[str, Callable[[], None]]] = None

    def status(self) -> Optional[str]:
        """None = sẵn sàng; chuỗi = lý do chưa click được (hiện trên banner cảnh báo)."""
        return None

    def request_permission(self) -> None:
        """Gọi khi bấm Bắt đầu, để hệ điều hành hỏi cấp quyền nếu cần."""

    def move(self, x: int, y: int) -> None:
        raise NotImplementedError

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class DryBackend(Backend):
    """Không gửi click thật: để thử giao diện, hoặc khi backend thật không khởi tạo được."""

    name = "dry-run"

    def __init__(self, error: Optional[str] = None):
        self.error = error

    def status(self):
        return self.error

    def move(self, x, y):
        pass

    def click(self, x, y, button="left", clicks=1):
        pass


class KeepAwake:
    """Giữ máy không ngủ / không khóa màn hình khi đang chạy. Mặc định: không làm gì."""

    def begin(self, prevent_sleep: bool) -> bool:
        """Trả về False nếu được yêu cầu chống ngủ mà không làm được."""
        return not prevent_sleep

    def end(self) -> None:
        pass
