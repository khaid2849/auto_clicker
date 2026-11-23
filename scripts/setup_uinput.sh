#!/usr/bin/env bash
# Linux Wayland: let the user sitting at the computer write to /dev/uinput to create a virtual mouse.
# Same kind of rule Steam uses for game controllers (TAG uaccess); no need to join the "input" group.
set -euo pipefail

RULE=/etc/udev/rules.d/60-autoclicker-uinput.rules
echo 'KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess", OPTIONS+="static_node=uinput"' \
  | sudo tee "$RULE" >/dev/null
echo uinput | sudo tee /etc/modules-load.d/autoclicker-uinput.conf >/dev/null
sudo modprobe uinput
sudo udevadm control --reload-rules
sudo udevadm trigger --action=add --sysname-match=uinput || true

if [ -w /dev/uinput ]; then
  echo "OK: /dev/uinput is writable"
else
  echo "Done. LOG OUT and log back in for the permission to take effect."
fi
