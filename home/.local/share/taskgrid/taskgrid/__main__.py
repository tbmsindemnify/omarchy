"""Entry point.

gtk4-layer-shell must be loaded before libwayland-client or the layer surface
silently fails. Python imports libwayland first via PyGObject, so we re-exec
ourselves once with LD_PRELOAD set. See gtk4-layer-shell's linking.md.
"""

import os
import sys
from pathlib import Path

PRELOAD_CANDIDATES = (
    "/usr/lib/libgtk4-layer-shell.so",
    "/usr/lib64/libgtk4-layer-shell.so",
    "/usr/local/lib/libgtk4-layer-shell.so",
)
_GUARD = "TASKGRID_PRELOADED"


def _ensure_preload() -> None:
    if os.environ.get(_GUARD):
        return
    lib = next((p for p in PRELOAD_CANDIDATES if Path(p).exists()), None)
    if lib is None:
        return  # fall through; the widget still runs, just not anchored
    existing = os.environ.get("LD_PRELOAD", "")
    if lib in existing.split(":"):
        return
    os.environ["LD_PRELOAD"] = f"{lib}:{existing}" if existing else lib
    os.environ[_GUARD] = "1"
    os.execv(sys.executable, [sys.executable, "-m", "taskgrid", *sys.argv[1:]])


_ensure_preload()

from .app import main  # noqa: E402

sys.exit(main())
