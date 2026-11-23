#!/usr/bin/env bash
# Linux Wayland: cho phép người dùng đang ngồi trước máy ghi /dev/uinput để tạo chuột ảo.
# Cùng kiểu rule mà Steam dùng cho tay cầm (TAG uaccess), không cần thêm user vào group "input".
set -euo pipefail

RULE=/etc/udev/rules.d/60-autoclicker-uinput.rules
echo 'KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess", OPTIONS+="static_node=uinput"' \
  | sudo tee "$RULE" >/dev/null
echo uinput | sudo tee /etc/modules-load.d/autoclicker-uinput.conf >/dev/null
sudo modprobe uinput
sudo udevadm control --reload-rules
sudo udevadm trigger --action=add --sysname-match=uinput || true

if [ -w /dev/uinput ]; then
  echo "OK: đã ghi được /dev/uinput"
else
  echo "Đã cấu hình. Hãy ĐĂNG XUẤT rồi đăng nhập lại để quyền có hiệu lực."
fi
