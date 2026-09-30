#!/bin/bash
# Fresh-machine setup. Interactive package authentication occurs in this terminal.
set -euo pipefail
[[ $EUID -ne 0 ]] || { echo "Run as your normal desktop user, not root." >&2; exit 1; }
cd -- "$(dirname -- "$0")"
[[ -f /usr/share/omarchy/default/hypr/bootstrap.lua ]] || { echo 'Install Omarchy before running this setup.' >&2; exit 1; }
[[ -f "$HOME/.config/hypr/hyprland.lua" ]] || { echo 'This project requires the Lua-based Omarchy configuration. See docs/versions.txt.' >&2; exit 1; }
./scripts/dependencies.sh --build
if ! command -v voxtype >/dev/null; then omarchy voxtype install; fi
voxtype setup --download --model base.en
./scripts/build-photos.sh
./scripts/build-osd.sh
./install.sh --apply --with-osd "$@"
omarchy theme set kanagawa
./scripts/photo-defaults.sh
./scripts/activate.sh
python3 scripts/manage.py doctor
printf '\nDesktop setup complete. Follow docs/new-pc.md for app sign-ins and optional hardware.\n'
