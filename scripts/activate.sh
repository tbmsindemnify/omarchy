#!/bin/bash
# Explicit activation after file installation; never invoked during preview/tests.
set -euo pipefail
hyprctl reload
errors=$(hyprctl configerrors)
if [[ -n "$errors" && "$errors" != "ok" && "$errors" != '[]' ]]; then
  printf '%s\n' "$errors" >&2
  echo 'Resolve configuration errors or restore the installer backup before continuing.' >&2
  exit 1
fi
systemctl --user daemon-reload
if command -v voxtype >/dev/null; then
  systemctl --user enable --now voxtype.service
  if [[ -x "$HOME/.local/share/voxtype/tbm-osd/voxtype-osd-gtk4-colors" && -f "$HOME/.config/systemd/user/voxtype-color-osd.service" ]] && python3 -c 'import pathlib,tomllib,sys; sys.exit(tomllib.loads((pathlib.Path.home()/".config/voxtype/config.toml").read_text()).get("osd",{}).get("enabled",True))'; then
    systemctl --user enable --now voxtype-color-osd.service
  fi
fi
command -v update-desktop-database >/dev/null && update-desktop-database "$HOME/.local/share/applications"
omarchy restart shell
