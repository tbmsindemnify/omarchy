#!/usr/bin/env python3
"""Detect editable fields, terminal input, and desktop controls."""
import json
import subprocess
import gi
gi.require_version('Atspi', '2.0')
from gi.repository import Atspi

TERMINAL_CLASSES = {'foot', 'footclient', 'alacritty', 'kitty', 'com.mitchellh.ghostty', 'org.gnome.terminal', 'org.wezfurlong.wezterm', 'org.kde.konsole', 'xterm'}
CHAT_CLASS_HINTS = ('chatgpt', 'chromium', 'chrome', 'edge', 'codex', 'claude')

def detect():
    active = json.loads(subprocess.check_output(['hyprctl', 'activewindow', '-j']))
    pid = active.get('pid')
    window_class = active.get('class', '').lower()
    if window_class in TERMINAL_CLASSES:
        return 'terminal'
    if window_class == 'org.omarchy.cliamp':
        return 'command'
    ambiguous_web_focus = any(hint in window_class for hint in CHAT_CLASS_HINTS)
    Atspi.set_timeout(50, 75)
    desktop = Atspi.get_desktop(0)
    editable_roles = {Atspi.Role.ENTRY, Atspi.Role.PASSWORD_TEXT}
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app.get_process_id() != pid:
            continue
        # Inactive Electron windows retain stale focus and large document trees.
        frames = [app.get_child_at_index(j) for j in range(app.get_child_count())]
        stack = [frame for frame in frames if frame.get_state_set().contains(Atspi.StateType.ACTIVE)]
        if not stack:
            return 'unknown'
        visited = 0
        noneditable_focused = False
        while stack and visited < 2000:
            item = stack.pop()
            visited += 1
            states = item.get_state_set()
            if states.contains(Atspi.StateType.FOCUSED):
                if item.get_role() == Atspi.Role.TERMINAL:
                    return 'terminal'
                # Check ancestors too: rich-text controls may focus a child.
                parent = item
                for _ in range(12):
                    if parent is None:
                        break
                    if parent.get_state_set().contains(Atspi.StateType.EDITABLE) or parent.get_role() in editable_roles:
                        return 'text'
                    parent = parent.get_parent()
                # Container focus alone does not prove a text field is absent.
                generic = {'frame', 'window', 'panel', 'root pane', 'filler', 'application', 'document web', 'embedded', 'unknown', 'invalid'}
                if item.get_role_name() not in generic:
                    # Browser/Electron accessibility focus is transient and can
                    # point at a toolbar or container while the caret remains in
                    # a chat composer. Unknown safely follows the normal dictation
                    # path; explicit button-chord command mode still overrides it.
                    return 'unknown' if ambiguous_web_focus else 'command'
                if item.get_role() == Atspi.Role.DOCUMENT_WEB:
                    noneditable_focused = True
            # Hidden chat/history branches cannot contain the visible input.
            # Still inspect a focused node above before pruning its children.
            if not states.contains(Atspi.StateType.SHOWING):
                continue
            count = item.get_child_count()
            if count > 10000:
                return 'unknown'
            for j in range(count):
                child = item.get_child_at_index(j)
                if child is not None:
                    stack.append(child)
        if not stack and noneditable_focused:
            # Chromium/Electron chat composers, including Claude, often expose
            # only DOCUMENT_WEB to AT-SPI even when their message field has focus.
            # Treat it as unknown so the normal non-terminal dictation path pastes
            # into the focused web control; terminals remain explicitly protected.
            return 'unknown'
    return 'unknown'

if __name__ == '__main__':
    try:
        print(detect())
    except Exception:
        print('unknown')
