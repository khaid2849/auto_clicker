#!/usr/bin/env bash
# Cài Auto Clicker từ mã nguồn trên Ubuntu/Debian: môi trường Python riêng + icon trong menu ứng dụng.
#   ./scripts/install_linux.sh            tự cấu hình uinput nếu đang ở phiên Wayland
#   ./scripts/install_linux.sh --uinput   luôn cấu hình uinput (nếu hay đổi giữa Xorg và Wayland)
# Cập nhật: git pull && ./scripts/install_linux.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$HOME/.local/share/autoclicker"
VENV="$APP_DIR/venv"
BIN="$HOME/.local/bin/autoclicker"
DESKTOP="$HOME/.local/share/applications/autoclicker.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

echo "==> Gói hệ thống (cần sudo)"
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv libxcb-cursor0 >/dev/null

echo "==> Cài vào $VENV"
mkdir -p "$APP_DIR"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q --upgrade "$ROOT"

echo "==> Lệnh 'autoclicker', icon và mục trong menu ứng dụng"
mkdir -p "$(dirname "$BIN")" "$(dirname "$DESKTOP")" "$ICON_DIR"
ln -sf "$VENV/bin/autoclicker" "$BIN"
QT_QPA_PLATFORM=offscreen AUTOCLICKER_BACKEND=dry \
  "$VENV/bin/autoclicker" --export-icon "$ICON_DIR/autoclicker.png" --icon-size 256
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Auto Clicker
Comment=Tự động click chuột theo chu kỳ
Exec=$VENV/bin/autoclicker
Icon=autoclicker
Terminal=false
Categories=Utility;
StartupWMClass=autoclicker
EOF
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

if [[ "${XDG_SESSION_TYPE:-}" == "wayland" || "${1:-}" == "--uinput" ]]; then
  echo "==> Phiên Wayland: cấu hình quyền /dev/uinput"
  "$ROOT/scripts/setup_uinput.sh"
else
  echo "==> Phiên X11: không cần cấu hình uinput"
fi

echo
echo "✅ Xong. Mở 'Auto Clicker' trong menu ứng dụng, hoặc chạy lệnh: autoclicker"
