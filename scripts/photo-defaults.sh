#!/bin/bash
set -euo pipefail
xdg-mime default photo-folder-viewer.desktop image/jpeg image/png image/webp image/heif image/avif image/tiff image/gif image/bmp
echo 'Photo Folder Viewer selected. Restore with: xdg-mime default imv-dir.desktop <MIME type>'
