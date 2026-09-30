"""Pull colors from the active Omarchy theme so the widget matches the desktop."""

from __future__ import annotations

import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    tomllib = None

THEME_DIR = Path.home() / ".local" / "state" / "omarchy" / "current" / "theme"
THEME_NAME = Path.home() / ".local" / "state" / "omarchy" / "current" / "theme.name"

FALLBACK = {
    "mode": "dark",
    "background": "#1f1f28",
    "foreground": "#dcd7ba",
    "dark_foreground": "#727169",
    "accent": "#dcd7ba",
    "selection": "#363646",
    "red": "#c34043",
    "yellow": "#c0a36e",
    "green": "#76946a",
    "blue": "#7e9cd8",
    "magenta": "#957fb8",
    "cyan": "#6a9589",
}

# One hue per agent, so a glance tells you who you were working with.
AGENT_KEY = {"claude": "orange", "codex": "cyan", "hermes": "magenta"}


def load_colors() -> dict:
    colors = dict(FALLBACK)
    path = THEME_DIR / "colors.toml"
    try:
        text = path.read_text()
    except OSError:
        return colors
    parsed = {}
    if tomllib:
        try:
            parsed = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            parsed = {}
    if not parsed:
        parsed = dict(re.findall(r'^\s*([a-z_]+)\s*=\s*"([^"]+)"', text, re.MULTILINE))
    colors.update({k: v for k, v in parsed.items() if isinstance(v, str)})
    colors.setdefault("orange", colors.get("yellow", FALLBACK["yellow"]))
    return colors


def theme_name() -> str:
    try:
        return THEME_NAME.read_text().strip()
    except OSError:
        return "unknown"


def hex_to_rgba(value: str, alpha: float) -> str:
    value = (value or "").lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) != 6:
        return f"rgba(30, 30, 40, {alpha:.3f})"
    r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


def mix(a: str, b: str, ratio: float) -> str:
    """Blend two hex colors; ratio 0 returns a, 1 returns b."""
    def parts(v):
        v = (v or "").lstrip("#")
        if len(v) == 3:
            v = "".join(c * 2 for c in v)
        if len(v) != 6:
            v = "1f1f28"
        return [int(v[i:i + 2], 16) for i in (0, 2, 4)]
    pa, pb = parts(a), parts(b)
    return "#" + "".join(f"{int(x + (y - x) * ratio):02x}" for x, y in zip(pa, pb))


def build_css(opacity: float, template: str) -> str:
    """Substitute @name tokens in the stylesheet with live theme values."""
    c = load_colors()
    bg = c["background"]
    fg = c["foreground"]
    panel_alpha = max(0.0, min(1.0, opacity))

    values = {
        "panel_bg": hex_to_rgba(bg, panel_alpha),
        "header_bg": hex_to_rgba(mix(bg, fg, 0.08), min(1.0, panel_alpha + 0.18)),
        "card_bg": hex_to_rgba(mix(bg, fg, 0.10), min(1.0, panel_alpha * 0.65 + 0.08)),
        "row_hover": hex_to_rgba(c["selection"], min(1.0, panel_alpha + 0.20)),
        "border": hex_to_rgba(mix(bg, fg, 0.28), min(1.0, panel_alpha + 0.18)),
        "fg": fg,
        "fg_dim": c["dark_foreground"],
        "fg_faint": mix(bg, fg, 0.45),
        "accent": c["accent"],
        "done": c["green"],
        "doing": c["yellow"],
        "overdue": c["red"],
        "claude": c.get(AGENT_KEY["claude"], c["yellow"]),
        "codex": c.get(AGENT_KEY["codex"], c["cyan"]),
        "hermes": c.get(AGENT_KEY["hermes"], c["magenta"]),
        # Feed sources (see feeds.py); unknown sources fall back to fg_dim.
        "src_indemnify": c["red"],
        "src_mail": c["blue"],
        "src_calendar": c["green"],
        "src_git": c["cyan"],
        "src_outbox": c["yellow"],
        "src_vault": c["magenta"],
    }
    out = template
    for key, val in values.items():
        out = out.replace(f"@{key}@", val)
    return out
