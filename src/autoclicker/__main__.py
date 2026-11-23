"""Điểm vào: lệnh `autoclicker` hoặc `python -m autoclicker`."""
from __future__ import annotations

import argparse
import sys

from . import __version__


def main() -> None:
    # Phải cấu hình biến môi trường của Qt TRƯỚC khi import bất kỳ module Qt nào
    from . import backends
    backends.configure_qt_env()

    parser = argparse.ArgumentParser(prog="autoclicker", description="Tự động click chuột theo chu kỳ.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--export-icon", metavar="PNG", help="xuất icon ra file PNG rồi thoát (dùng khi đóng gói)")
    parser.add_argument("--icon-size", type=int, default=1024, help=argparse.SUPPRESS)
    args, qt_args = parser.parse_known_args()

    if args.export_icon:
        from .common import export_icon
        export_icon(args.export_icon, args.icon_size)
        return

    from .app import run
    sys.exit(run([sys.argv[0], *qt_args]))


if __name__ == "__main__":
    main()
