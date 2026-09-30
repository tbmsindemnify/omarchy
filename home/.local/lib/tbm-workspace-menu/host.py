#!/usr/bin/env python3
"""Only accepts workspace moves from the matching local Edge extension."""
import importlib.machinery
import importlib.util
import json
import os
import struct
import subprocess
import sys

ALLOWED_ORIGIN = "chrome-extension://odacgeohnfjljnjfgapafamddgfgnlkj/"

def reply(payload):
    data = json.dumps(payload).encode()
    sys.stdout.buffer.write(struct.pack("=I", len(data)) + data)
    sys.stdout.buffer.flush()

def handle(request):
    if not isinstance(request, dict) or request.get("action") != "move":
        raise ValueError("Unsupported action")
    slot = request.get("workspace")
    if type(slot) is not int or slot not in range(1, 6):
        raise ValueError("Workspace must be a number from 1 to 5")
    title = request.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 4096:
        raise ValueError("Edge did not provide the tab title; nothing was moved.")
    loader = importlib.machinery.SourceFileLoader("workspace_menu", os.path.expanduser("~/.local/bin/tbm-workspace-menu"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    menu = importlib.util.module_from_spec(spec)
    loader.exec_module(menu)
    window = menu.query("activewindow")
    if window.get("class") != "microsoft-edge":
        raise ValueError("The Edge window is no longer focused; nothing was moved.")
    # Reject a stale request rather than move a different focused browser window.
    if title not in window.get("title", ""):
        raise ValueError("The focused Edge window no longer matches the clicked tab; nothing was moved.")
    destination = menu.move(window, slot)
    menu.notify("Moved Edge to workspace " + str(slot) + " on the same screen.")
    return {"ok": True, "workspace": slot, "destination": destination}

def main():
    try:
        if len(sys.argv) < 2 or sys.argv[1] != ALLOWED_ORIGIN:
            raise ValueError("Unrecognized extension origin")
        header = sys.stdin.buffer.read(4)
        if len(header) != 4:
            raise ValueError("Missing native message")
        length = struct.unpack("=I", header)[0]
        if not 0 < length <= 16384:
            raise ValueError("Invalid native message size")
        body = sys.stdin.buffer.read(length)
        if len(body) != length:
            raise ValueError("Incomplete native message")
        reply(handle(json.loads(body)))
    except Exception as error:
        reply({"ok": False, "error": str(error)})

if __name__ == "__main__":
    main()
