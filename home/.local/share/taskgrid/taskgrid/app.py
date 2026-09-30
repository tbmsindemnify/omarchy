"""TaskGrid -- a transparent, collapsible task overlay pinned to the top-right.

Implemented as a Wayland layer-shell surface, so it sits above normal windows
on every workspace without being a window Hyprland has to manage.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from datetime import date
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

from . import feeds, sources, theme  # noqa: E402

APP_ID = "dev.tbm.taskgrid"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "taskgrid"
CONFIG_FILE = CONFIG_DIR / "config.json"
TASKS_FILE = CONFIG_DIR / "tasks.json"
FEEDS_DIR = CONFIG_DIR / "feeds"
DISMISSED_FILE = CONFIG_DIR / "dismissed.json"
STYLE_TEMPLATE = Path(__file__).with_name("style.css")

OPACITY_STEPS = [0.35, 0.55, 0.72, 0.88, 1.0]

DEFAULT_CONFIG = {
    "opacity": 0.72,
    "width": 380,
    "height_fraction": 0.74,
    "margin_top": 8,
    "margin_right": 8,
    "collapsed": False,
    "layer": "top",
    "refresh_seconds": 45,
    "session_days": 10,
    "session_limit": 12,
    "show_sessions": True,
    # Credential-free scanners run in-process; see feeds.LOCAL_SCANNERS.
    "local_feeds": ["git", "outbox", "vault"],
    "local_scan_seconds": 300,
    # Rows shown per feed section before "+N more"; click the heading to expand.
    "feed_limit": 5,
    "collapsed_sections": [],
    "expanded_sections": [],
    # Connector name such as "DP-1" or "HDMI-A-1"; empty means the compositor
    # picks. `hyprctl monitors` lists them.
    "monitor": "",
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        cfg.update(json.loads(CONFIG_FILE.read_text()))
    except (OSError, json.JSONDecodeError):
        pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2))
    os.replace(tmp, CONFIG_FILE)


def _label(text, css=(), xalign=0.0, ellipsize=True, wrap=False):
    lbl = Gtk.Label(label=text, xalign=xalign)
    if wrap:
        lbl.set_wrap(True)
        lbl.set_wrap_mode(2)  # WORD_CHAR
    elif ellipsize:
        lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
    for name in css:
        lbl.add_css_class(name)
    return lbl


def _icon_button(icon_name, fallback, tooltip, handler):
    """Prefer a themed symbolic icon; fall back to a glyph if it is missing."""
    display = Gdk.Display.get_default()
    has_icon = False
    if display and icon_name:
        try:
            has_icon = Gtk.IconTheme.get_for_display(display).has_icon(icon_name)
        except Exception:
            has_icon = False
    btn = Gtk.Button.new_from_icon_name(icon_name) if has_icon else Gtk.Button(label=fallback)
    btn.add_css_class("tg-iconbtn")
    btn.set_tooltip_text(tooltip)
    btn.set_has_frame(False)
    btn.set_valign(Gtk.Align.CENTER)
    btn.connect("clicked", handler)
    return btn


class TaskGridWindow(Gtk.ApplicationWindow):
    def __init__(self, app, config):
        super().__init__(application=app)
        self.config = config
        self.store = sources.TaskStore(TASKS_FILE)
        self.sessions: list[sources.Session] = []
        self.dismissed = feeds.Dismissed(DISMISSED_FILE)
        self._local_feeds: list[dict] = []
        self._local_scanned = 0.0
        self.feed_sections: list[dict] = []
        self.collapsed = bool(config.get("collapsed"))
        self.opacity_value = float(config.get("opacity", 0.72))
        self._css = Gtk.CssProvider()

        self.set_title("TaskGrid")
        self.add_css_class("taskgrid")
        self.set_decorated(False)
        self.set_resizable(False)

        self._init_layer_shell()
        self._build_ui()
        self._install_css()
        self._wire_events()

        self.refresh(rescan=True)
        self._apply_collapsed()

    # ------------------------------------------------------------------
    # layer shell placement
    # ------------------------------------------------------------------

    def _init_layer_shell(self):
        LayerShell.init_for_window(self)
        LayerShell.set_namespace(self, "taskgrid")
        layers = {"top": LayerShell.Layer.TOP, "overlay": LayerShell.Layer.OVERLAY,
                  "bottom": LayerShell.Layer.BOTTOM, "background": LayerShell.Layer.BACKGROUND}
        LayerShell.set_layer(self, layers.get(self.config.get("layer", "top"), LayerShell.Layer.TOP))
        self._monitor = self._pick_monitor()
        if self._monitor is not None:
            LayerShell.set_monitor(self, self._monitor)
        # Anchored top-left with explicit margins (rather than top-right) so the
        # surface can be dragged to an arbitrary position -- see _on_drag_update.
        LayerShell.set_anchor(self, LayerShell.Edge.TOP, True)
        LayerShell.set_anchor(self, LayerShell.Edge.LEFT, True)
        margin_left = self.config.get("margin_left")
        if margin_left is None:
            # First run after upgrading from the old top-right anchored layout:
            # convert the saved right-margin into an equivalent left-margin.
            geo = self._monitor_geometry()
            monitor_width = geo.width if geo else 1920
            width = int(self.config.get("width", 380))
            margin_right = int(self.config.get("margin_right", 8))
            margin_left = max(0, monitor_width - width - margin_right)
        LayerShell.set_margin(self, LayerShell.Edge.LEFT, int(margin_left))
        LayerShell.set_margin(self, LayerShell.Edge.TOP, int(self.config.get("margin_top", 8)))
        # Zero, not -1: overlap windows but never reserve screen space of our own.
        LayerShell.set_exclusive_zone(self, 0)
        LayerShell.set_keyboard_mode(self, LayerShell.KeyboardMode.ON_DEMAND)

    def _pick_monitor(self):
        """Resolve the configured connector name to a GdkMonitor."""
        wanted = (self.config.get("monitor") or "").strip()
        if not wanted:
            return None
        display = Gdk.Display.get_default()
        if display is None:
            return None
        monitors = display.get_monitors()
        for i in range(monitors.get_n_items()):
            monitor = monitors.get_item(i)
            if (monitor.get_connector() or "").lower() == wanted.lower():
                return monitor
        return None  # named monitor is unplugged; fall back to the default

    def _monitor_geometry(self):
        """Geometry of the monitor this surface is anchored to, if known."""
        monitor = getattr(self, "_monitor", None)
        if monitor is None:
            display = Gdk.Display.get_default()
            if display:
                monitors = display.get_monitors()
                if monitors.get_n_items():
                    monitor = monitors.get_item(0)
        return monitor.get_geometry() if monitor is not None else None

    def _max_body_height(self) -> int:
        fraction = float(self.config.get("height_fraction", 0.74))
        geo = self._monitor_geometry()
        height = geo.height if geo else 1080
        return max(220, int(height * fraction))

    # ------------------------------------------------------------------
    # widget tree
    # ------------------------------------------------------------------

    def _build_ui(self):
        width = int(self.config.get("width", 380))
        self.set_default_size(width, -1)

        self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.root.add_css_class("tg-root")
        self.root.set_size_request(width, -1)
        self.set_child(self.root)

        self.root.append(self._build_header())

        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.body.add_css_class("tg-body")

        self.entry = Gtk.Entry(placeholder_text="Add a task…  (text  @project  !today)")
        self.entry.add_css_class("tg-entry")
        self.entry.connect("activate", self.on_add_task)
        self.body.append(self.entry)

        self.sections = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_propagate_natural_height(True)
        scroller.set_max_content_height(self._max_body_height())
        scroller.set_child(self.sections)
        scroller.set_vexpand(True)
        self.body.append(scroller)

        self.root.append(self.body)

    def _build_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.add_css_class("tg-header")

        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        titles.add_css_class("tg-draghandle")
        titles.set_cursor(Gdk.Cursor.new_from_name("grab"))
        titles.set_hexpand(True)
        titles.append(_label("TASKGRID", ("tg-title",)))
        self.subtitle = _label("", ("tg-subtitle",))
        titles.append(self.subtitle)
        header.append(titles)

        self.count_open = _label("", ("tg-count",))
        self.count_due = _label("", ("tg-count", "hot"))
        header.append(self.count_due)
        header.append(self.count_open)

        header.append(_icon_button("display-brightness-symbolic", "◐",
                                   "Cycle transparency", self.on_cycle_opacity))
        header.append(_icon_button("view-refresh-symbolic", "⟳",
                                   "Refresh now", self.on_force_refresh))
        self.collapse_btn = _icon_button(None, "▾", "Collapse / expand", self.on_toggle_collapse)
        header.append(self.collapse_btn)

        # Dragging the title area moves the whole overlay; a click with no
        # real movement (the common case) toggles collapse instead.
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        titles.add_controller(drag)
        return header

    # ------------------------------------------------------------------
    # styling / events
    # ------------------------------------------------------------------

    def _install_css(self):
        try:
            template = STYLE_TEMPLATE.read_text()
        except OSError:
            return
        self._css.load_from_data(theme.build_css(self.opacity_value, template).encode())
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display, self._css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _wire_events(self):
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_key)
        self.add_controller(keys)

        self._monitors = []
        self._watch(TASKS_FILE, lambda *_: self.refresh(rescan=False))
        FEEDS_DIR.mkdir(parents=True, exist_ok=True)
        self._watch(FEEDS_DIR, self._on_feeds_changed)
        self._watch(theme.THEME_NAME, lambda *_: self._install_css())

        interval = max(10, int(self.config.get("refresh_seconds", 45)))
        GLib.timeout_add_seconds(interval, self._tick)

    def _watch(self, path: Path, callback):
        try:
            monitor = Gio.File.new_for_path(str(path)).monitor(Gio.FileMonitorFlags.NONE, None)
        except GLib.Error:
            return
        monitor.connect("changed", callback)
        self._monitors.append(monitor)  # keep alive

    def _tick(self):
        self.refresh(rescan=True)
        return GLib.SOURCE_CONTINUE

    def _on_feeds_changed(self, _mon, file, _other, event):
        # A sync writes foo.json.tmp then renames; react once, to the final file.
        if file.get_path().endswith(".json") and event in (
                Gio.FileMonitorEvent.CHANGES_DONE_HINT, Gio.FileMonitorEvent.RENAMED,
                Gio.FileMonitorEvent.MOVED_IN, Gio.FileMonitorEvent.DELETED,
                Gio.FileMonitorEvent.CREATED):
            GLib.timeout_add(300, lambda: (self.refresh(rescan=False), GLib.SOURCE_REMOVE)[1])

    def on_key(self, _ctrl, keyval, _code, _state):
        name = Gdk.keyval_name(keyval)
        if name == "Escape":
            if self.entry.has_focus():
                self.entry.set_text("")
                self.root.grab_focus()
            else:
                self.toggle_collapse()
            return True
        return False

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------

    def on_add_task(self, entry):
        raw = entry.get_text().strip()
        if not raw:
            return
        project, due, words = "", "", []
        for word in raw.split():
            if word.startswith("@") and len(word) > 1:
                project = word[1:]
            elif word.lower() in ("!today", "!t"):
                due = date.today().isoformat()
            elif word.startswith("!") and len(word) > 1:
                due = word[1:]
            else:
                words.append(word)
        text = " ".join(words)
        if text:
            self.store.add(text, project=project, due=due)
            entry.set_text("")
            self.refresh(rescan=False)

    def on_cycle_opacity(self, *_):
        current = min(OPACITY_STEPS, key=lambda v: abs(v - self.opacity_value))
        self.opacity_value = OPACITY_STEPS[(OPACITY_STEPS.index(current) + 1) % len(OPACITY_STEPS)]
        self.config["opacity"] = self.opacity_value
        save_config(self.config)
        self._install_css()

    def on_force_refresh(self, *_):
        self._local_scanned = 0.0
        self.refresh(rescan=True)

    def on_toggle_collapse(self, *_):
        self.toggle_collapse()

    # ------------------------------------------------------------------
    # drag-to-move
    # ------------------------------------------------------------------

    DRAG_CLICK_THRESHOLD = 4  # px; below this, treat a drag as a plain click

    def _on_drag_begin(self, _gesture, _x, _y):
        self._drag_start_left = LayerShell.get_margin(self, LayerShell.Edge.LEFT)
        self._drag_start_top = LayerShell.get_margin(self, LayerShell.Edge.TOP)
        self._drag_moved = False
        self._pending_left = self._drag_start_left
        self._pending_top = self._drag_start_top

    def _on_drag_update(self, _gesture, offset_x, offset_y):
        if abs(offset_x) > self.DRAG_CLICK_THRESHOLD or abs(offset_y) > self.DRAG_CLICK_THRESHOLD:
            self._drag_moved = True

        geo = self._monitor_geometry()
        mon_w = geo.width if geo else 1920
        mon_h = geo.height if geo else 1080
        width = self.get_width() or int(self.config.get("width", 380))
        height = self.get_height() or 100
        max_left = max(0, mon_w - width)
        max_top = max(0, mon_h - height)

        new_left = min(max(0, self._drag_start_left + int(offset_x)), max_left)
        new_top = min(max(0, self._drag_start_top + int(offset_y)), max_top)
        LayerShell.set_margin(self, LayerShell.Edge.LEFT, new_left)
        LayerShell.set_margin(self, LayerShell.Edge.TOP, new_top)
        self._pending_left, self._pending_top = new_left, new_top

    def _on_drag_end(self, _gesture, _offset_x, _offset_y):
        if not self._drag_moved:
            self.toggle_collapse()
            return
        self.config["margin_left"] = self._pending_left
        self.config["margin_top"] = self._pending_top
        save_config(self.config)

    def toggle_collapse(self):
        self.collapsed = not self.collapsed
        self.config["collapsed"] = self.collapsed
        save_config(self.config)
        self._apply_collapsed()

    def _apply_collapsed(self):
        self.body.set_visible(not self.collapsed)
        self.collapse_btn.set_label("▸" if self.collapsed else "▾")
        if self.collapsed:
            self.root.add_css_class("collapsed")
        else:
            self.root.remove_css_class("collapsed")

    # ------------------------------------------------------------------
    # rendering
    # ------------------------------------------------------------------

    def refresh(self, rescan: bool):
        if self.store.changed_on_disk():
            self.store.load()
        if rescan and self.config.get("show_sessions", True):
            self.sessions = sources.scan_sessions(
                max_age_days=int(self.config.get("session_days", 10)),
                limit=int(self.config.get("session_limit", 12)),
            )
        every = max(30, int(self.config.get("local_scan_seconds", 300)))
        if rescan and time.time() - self._local_scanned >= every:
            self._local_feeds = feeds.local_sections(self.config.get("local_feeds") or ())
            self._local_scanned = time.time()
        self.feed_sections = feeds.arrange(self._local_feeds, FEEDS_DIR)
        self._render()

    def _clear(self, box):
        child = box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            box.remove(child)
            child = nxt

    def _render(self):
        self._clear(self.sections)
        today = date.today().isoformat()

        buckets = {"agenda": [], "unfinished": [], "doing": [], "later": [], "done": []}
        for task in self.store.tasks:
            buckets[sources.bucket_for(task)].append(task)

        overdue = [t for t in buckets["agenda"] if (t.get("due") or "") < today]
        open_count = sum(len(buckets[k]) for k in ("agenda", "unfinished", "doing", "later"))

        for section in self.feed_sections:
            section["items"] = [i for i in section["items"] if i["id"] not in self.dismissed]
        feed_items = [i for s in self.feed_sections for i in s["items"]]
        feed_overdue = sum(1 for i in feed_items if i["due"] and i["due"] < today)
        open_count += len(feed_items)

        self.count_open.set_text(f"{open_count} open")
        if overdue or feed_overdue:
            self.count_due.set_text(f"{len(overdue) + feed_overdue} overdue")
            self.count_due.set_visible(True)
        else:
            self.count_due.set_visible(False)
        stale = [s["label"].split(" · ")[-1].title() for s in self.feed_sections if s["stale"]]
        sub = date.today().strftime("%a %d %b") + f" · {len(self.sessions)} sessions"
        if stale:
            sub += " · stale: " + ", ".join(stale)
        self.subtitle.set_text(sub)

        manual_first = [
            ("TODAY", buckets["agenda"] + buckets["doing"]),
            ("UNFINISHED", buckets["unfinished"]),
        ]
        manual_last = [
            ("UPCOMING", buckets["later"]),
            ("DONE", buckets["done"][:6]),
        ]
        rendered = False
        for title, items in manual_first:
            rendered |= self._manual_section(title, items, today)
        for section in self.feed_sections:
            rendered |= self._feed_section(section, today)
        for title, items in manual_last:
            rendered |= self._manual_section(title, items, today)

        if not rendered:
            self.sections.append(_label(
                "Nothing queued. Add one above — try  call adjuster @indemnify !today",
                ("tg-empty",), wrap=True, ellipsize=False))

        if self.sessions and self.config.get("show_sessions", True):
            self.sections.append(_label("WHERE YOU LEFT OFF", ("tg-section-label",)))
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            card.add_css_class("tg-card")
            for session in self.sessions:
                card.append(self._session_row(session))
            self.sections.append(card)

    def _manual_section(self, title, items, today) -> bool:
        if not items:
            return False
        self.sections.append(_label(title, ("tg-section-label",)))
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        card.add_css_class("tg-card")
        for task in items:
            card.append(self._task_row(task, today))
        self.sections.append(card)
        return True

    def _feed_section(self, section, today) -> bool:
        items = section["items"]
        if not items:
            return False
        key = section["label"]
        folded = key in (self.config.get("collapsed_sections") or [])
        expanded = key in (self.config.get("expanded_sections") or [])

        heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        heading.add_css_class("tg-section-head")
        heading.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        # The name keeps its natural width; the count is what gives way when
        # space runs out (an ellipsizing, letter-spaced name clipped its first glyph).
        heading.append(_label(("▸ " if folded else "") + key, ("tg-section-label",), ellipsize=False))
        due = sum(1 for i in items if i["due"] and i["due"] <= today)
        tail = f"{len(items)}" + (f" · {due} due" if due else "")
        if section["stale"]:
            tail += f" · synced {sources.humanize(section['generated'])}"
        count = _label(tail, ("tg-section-label", "tg-section-count")
                       + (("hot",) if due or section["stale"] else ()), xalign=1.0)
        count.set_hexpand(True)
        heading.append(count)
        click = Gtk.GestureClick()
        click.connect("released", lambda *_: self._toggle_section(key, "collapsed_sections"))
        heading.add_controller(click)
        self.sections.append(heading)
        if folded:
            return True

        limit = max(1, int(self.config.get("feed_limit", 5)))
        shown = items if expanded else items[:limit]
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        card.add_css_class("tg-card")
        for item in shown:
            card.append(self._feed_row(item, today))
        if len(items) > limit:
            more = Gtk.Button(label="show less" if expanded else f"+{len(items) - limit} more")
            more.add_css_class("tg-more")
            more.set_has_frame(False)
            more.connect("clicked", lambda *_: self._toggle_section(key, "expanded_sections"))
            card.append(more)
        self.sections.append(card)
        return True

    def _toggle_section(self, key, list_name):
        keys = list(self.config.get(list_name) or [])
        keys.remove(key) if key in keys else keys.append(key)
        self.config[list_name] = keys
        save_config(self.config)
        self._render()

    def _feed_row(self, item, today):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        row.add_css_class("tg-row")

        dot = _label("●", ("tg-dot", item["source"]))
        dot.set_valign(Gtk.Align.START)
        row.append(dot)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_hexpand(True)
        meta, is_overdue = feeds.item_meta(item, today)
        # Only the meta line turns red; a whole column of red titles is unreadable.
        title_classes = ["tg-task"]
        if item.get("priority", 0) >= 2:
            title_classes.append("urgent")
        box.append(_label(item["title"], title_classes, wrap=True, ellipsize=False))
        if meta:
            box.append(_label(meta, ("tg-meta",) + (("overdue",) if is_overdue else ())))
        row.append(box)

        if item.get("url"):
            row.set_cursor(Gdk.Cursor.new_from_name("pointer"))
            row.set_tooltip_text(item["url"])
            click = Gtk.GestureClick()
            click.connect("released", lambda *_: self._open(item["url"]))
            box.add_controller(click)

        promote = Gtk.Button(label="+")
        promote.add_css_class("tg-del")
        promote.set_has_frame(False)
        promote.set_valign(Gtk.Align.START)
        promote.set_tooltip_text("Copy into my tasks")
        promote.connect("clicked", self._on_promote, item)
        row.append(promote)

        hide = Gtk.Button(label="×")
        hide.add_css_class("tg-del")
        hide.set_has_frame(False)
        hide.set_valign(Gtk.Align.START)
        hide.set_tooltip_text("Hide this (returns in 3 weeks if still open)")
        hide.connect("clicked", self._on_dismiss, item["id"])
        row.append(hide)
        return row

    def _open(self, url):
        try:
            Gio.AppInfo.launch_default_for_uri(url, None)
        except GLib.Error as exc:
            print(f"taskgrid: cannot open {url}: {exc.message}", file=sys.stderr)

    def _on_promote(self, _btn, item):
        project = {"indemnify": "indemnify", "git": "indemnify"}.get(item["source"], item["source"])
        self.store.add(item["title"], project=project, due=item.get("due") or "")
        self.dismissed.add(item["id"])
        self.refresh(rescan=False)

    def _on_dismiss(self, _btn, item_id):
        self.dismissed.add(item_id)
        self._render()

    def _task_row(self, task, today):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        row.add_css_class("tg-row")

        state = task.get("state", "todo")
        mark = {"todo": "", "doing": "◗", "done": "✓"}.get(state, "")
        check = Gtk.Button(label=mark)
        check.add_css_class("tg-check")
        if state in ("doing", "done"):
            check.add_css_class(state)
        check.set_valign(Gtk.Align.START)
        check.set_has_frame(False)
        check.set_tooltip_text("todo → doing → done")
        check.connect("clicked", self._on_check, task.get("id"))
        row.append(check)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        text_box.set_hexpand(True)
        due = (task.get("due") or "").strip()
        is_overdue = bool(due) and due < today and state != "done"

        classes = ["tg-task"] + (["done"] if state == "done" else []) + (["overdue"] if is_overdue else [])
        title = _label(task.get("text", ""), classes, wrap=True, ellipsize=False)
        if state == "done":
            title.set_markup(f"<s>{GLib.markup_escape_text(task.get('text', ''))}</s>")
        text_box.append(title)

        bits = []
        if task.get("project"):
            bits.append(f"@{task['project']}")
        if due:
            bits.append("today" if due == today else ("overdue " + due if is_overdue else due))
        if bits:
            text_box.append(_label(" · ".join(bits), ("tg-meta",) + (("overdue",) if is_overdue else ())))
        row.append(text_box)

        delete = Gtk.Button(label="×")
        delete.add_css_class("tg-del")
        delete.set_has_frame(False)
        delete.set_valign(Gtk.Align.START)
        delete.set_tooltip_text("Remove")
        delete.connect("clicked", self._on_delete, task.get("id"))
        row.append(delete)
        return row

    def _on_check(self, _btn, task_id):
        self.store.cycle_state(task_id)
        self.refresh(rescan=False)

    def _on_delete(self, _btn, task_id):
        self.store.remove(task_id)
        self.refresh(rescan=False)

    def _session_row(self, session):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        row.add_css_class("tg-row")

        dot = _label("●", ("tg-dot", session["agent"]))
        dot.set_valign(Gtk.Align.START)
        row.append(dot)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_hexpand(True)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name = _label(session["project"], ("tg-project",))
        name.set_hexpand(True)
        top.append(name)
        top.append(_label(f"{session['agent']} · {sources.humanize(session['last_active'])}",
                          ("tg-meta",), ellipsize=False))
        box.append(top)

        detail = session["snippet"] or session["path"] or ""
        if detail:
            box.append(_label(detail, ("tg-snippet",)))

        pending = [t for t in session.get("todos", []) if t.get("status") != "completed"]
        if pending:
            box.append(_label(f"↳ {len(pending)} open: {pending[0].get('text', '')}", ("tg-meta",)))

        row.append(box)
        row.set_tooltip_text(session["path"] or session["project"])
        return row


class TaskGridApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None
        self.add_main_option("toggle", 0, GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
                             "Collapse or expand the running widget", None)

    def do_command_line(self, command_line):
        options = command_line.get_options_dict().end().unpack()
        self.activate()
        if options.get("toggle") and self.window:
            self.window.toggle_collapse()
        return 0

    def do_activate(self):
        if self.window is None:
            config = load_config()
            self.window = TaskGridWindow(self, config)
            self.window.store.purge_done(older_than_days=2)
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self._on_signal)
        self.window.present()

    def _on_signal(self):
        if self.window:
            self.window.toggle_collapse()
        return GLib.SOURCE_CONTINUE


def main(argv=None):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not TASKS_FILE.exists():
        TASKS_FILE.write_text(json.dumps({"tasks": []}, indent=2))
    return TaskGridApp().run(argv if argv is not None else sys.argv)
