#!/usr/bin/env bash
# Install Auto Clicker from source on Ubuntu/Debian: a private Python environment + an app menu entry.
#   ./scripts/install_linux.sh            also sets up uinput when running a Wayland session
#   ./scripts/install_linux.sh --uinput   always set up uinput (if you switch between Xorg and Wayland)
# Update: git pull && ./scripts/install_linux.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$HOME/.local/share/autoclicker"
VENV="$APP_DIR/venv"
BIN="$HOME/.local/bin/autoclicker"
DESKTOP="$HOME/.local/share/applications/autoclicker.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

echo "==> System packages (needs sudo)"
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv libxcb-cursor0 >/dev/null

echo "==> Installing into $VENV"
mkdir -p "$APP_DIR"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q --upgrade "$ROOT"

echo "==> 'autoclicker' command, icon and app menu entry"
mkdir -p "$(dirname "$BIN")" "$(dirname "$DESKTOP")" "$ICON_DIR"
ln -sf "$VENV/bin/autoclicker" "$BIN"
QT_QPA_PLATFORM=offscreen AUTOCLICKER_BACKEND=dry \
  "$VENV/bin/autoclicker" --export-icon "$ICON_DIR/autoclicker.png" --icon-size 256
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Auto Clicker
Comment=Click the mouse automatically on a schedule
Exec=$VENV/bin/autoclicker
Icon=autoclicker
Terminal=false
Categories=Utility;
StartupWMClass=autoclicker
EOF
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

if [[ "${XDG_SESSION_TYPE:-}" == "wayland" || "${1:-}" == "--uinput" ]]; then
  echo "==> Wayland session: setting up /dev/uinput access"
  "$ROOT/scripts/setup_uinput.sh"
else
  echo "==> X11 session: no uinput setup needed"
fi

echo
echo "✅ Done. Open 'Auto Clicker' from the app menu, or run: autoclicker"
