Personal imv v5.0.1 build. Cursor on image: standard zoom. Cursor in empty viewer background: scroll down for next, up for previous; 200 ms navigation delay. Moving the cursor resets gesture mode. Supports rotated and mirrored images.

Binary: ~/.local/lib/imv-photo-scroll/imv
Launcher: ~/.local/bin/photo-folder-viewer
Restore original default: xdg-mime default imv-dir.desktop image/jpeg image/png image/webp image/heif image/avif image/tiff image/gif image/bmp

Build: PATH="$PWD/.build-tools/bin:$PATH" meson compile -C build
Geometry test: cc test-photo-scroll.c -lm -o build/test-photo-scroll && build/test-photo-scroll
