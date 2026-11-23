#!/usr/bin/env bash
# Remove what install_linux.sh installed (keeps your settings in ~/.config/KhaiTools/).
set -uo pipefail

rm -rf "$HOME/.local/share/autoclicker"
rm -f "$HOME/.local/bin/autoclicker" \
      "$HOME/.local/share/applications/autoclicker.desktop" \
      "$HOME/.local/share/icons/hicolor/256x256/apps/autoclicker.png"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

if [ -f /etc/udev/rules.d/60-autoclicker-uinput.rules ]; then
  sudo rm -f /etc/udev/rules.d/60-autoclicker-uinput.rules /etc/modules-load.d/autoclicker-uinput.conf
  sudo udevadm control --reload-rules
fi
echo "Auto Clicker has been removed."
