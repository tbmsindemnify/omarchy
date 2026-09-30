#!/bin/bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
build="$root/.build/imv"
meson setup "$build" "$root/vendor/imv" -Dwindows=wayland -Dtest=disabled -Dman=disabled -Dcontrib-commands=false
meson compile -C "$build"
cc "$root/vendor/imv/test-photo-scroll.c" -lm -o "$build/test-photo-scroll"
"$build/test-photo-scroll"
install -Dm755 "$build/imv" "$HOME/.local/lib/imv-photo-scroll/imv"
echo 'Custom photo viewer installed.'
