#!/bin/bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
export CARGO_TARGET_DIR="$root/.build/voxtype-osd"
cargo build --locked --manifest-path "$root/vendor/voxtype-color-osd/Cargo.toml"
install -Dm755 "$CARGO_TARGET_DIR/debug/voxtype" "$HOME/.local/share/voxtype/tbm-osd/voxtype-osd-gtk4-colors"
echo 'Built custom popup. Enable with ./install.sh --apply --with-osd, then ./scripts/activate.sh.'
