#!/bin/bash
# Run manually on a fresh Omarchy installation, from an interactive terminal.
set -euo pipefail
packages=(python python-dbus python-gobject gtk4 gtk4-layer-shell at-spi2-core jq socat wtype wl-clipboard libnotify imv)
if [[ ${1:-} == --build ]]; then
  packages+=(base-devel meson ninja rust gtk4 gtk4-layer-shell wayland-protocols inih libpng libjpeg-turbo libtiff libheif libwebp librsvg libnsgif libjxl)
fi
sudo pacman -S --needed "${packages[@]}"
if ! command -v voxtype >/dev/null; then
  echo 'Install dictation using: omarchy voxtype install.'
fi
