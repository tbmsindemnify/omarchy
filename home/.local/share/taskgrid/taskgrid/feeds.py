"""External work feeds for TaskGrid.

Every row that is not a manual task or an agent session is a *feed item*.
Two producers write them:

  * local scanners in this module, which need no credentials and run inside
    the widget (Indemnify git repos, the pa-agent outbox, TBM vault checkboxes)
  * JSON drop files in ``~/.config/taskgrid/feeds/*.json``, written by anything
    that can reach an account the widget cannot -- in practice the scheduled
    Claude sync that pulls Gmail, Outlook, calendars and Indemnify (Supabase)

Drop-file format (all item fields except ``title`` are optional)::

    {
      "source": "gmail",            # also the CSS colour class
      "label": "EMAIL · GMAIL",     # section heading
      "order": 30,                  # lower sorts higher in the grid
      "generated": "2026-09-28T09:00:00-05:00",
      "items": [
        {"id": "...", "title": "...", "detail": "...", "due": "2026-09-28",
         "when": "2026-09-27T14:02:00Z", "url": "https://...", "priority": 2}
      ]
    }

Nothing here writes outside TaskGrid's own config directory.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import date, datetime, timezone
from pathlib import Path

from .sources import _parse_iso, humanize

HOME = Path.home()
INDEMNIFY_ROOT = HOME / "Projects" / "project"
OUTBOX = INDEMNIFY_ROOT / "pa-agent" / "outbox"
VAULT = HOME / "Documents" / "Knowledge Hub"
# Where hand-written tasks live in the vault. The wiki and archived specs are
# full of design checklists that are not Tyler's to-dos, so they stay out.
VAULT_TASK_GLOBS = ("inbox/**/*.md", "projects/*.md", "Claude Memory/*.md", "*.md")
VAULT_SKIP = ("/Library/", "/archived-sources/", "/node_modules/")

_OPEN_BOX = re.compile(r"^\s*[-*] \[ \]\s+(.+)$")
_DUE_TAG = re.compile(r"(?:📅|due:)\s*(\d{4}-\d{2}-\d{2})")


def _item(source, id_, title, detail="", due="", when=0.0, url="", priority=0) -> dict:
    return {
        "source": source,
        "id": f"{source}:{id_}",
        "title": title,
        "detail": detail,
        "due": due,
        "when": when,
        "url": url,
        "priority": priority,
    }


# --------------------------------------------------------------------------
# local scanners
# --------------------------------------------------------------------------


def _git(repo: Path, *args) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=4,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def scan_git(root: Path = INDEMNIFY_ROOT) -> list[dict]:
    """Uncommitted or unpushed work in each Indemnify checkout / worktree."""
    out = []
    if not root.is_dir():
        return out
    for repo in sorted(root.iterdir()):
        if not (repo / ".git").exists():
            continue
        status = _git(repo, "status", "--porcelain=v1", "-b").splitlines()
        if not status:
            continue
        head = status[0].removeprefix("## ")
        branch = head.split("...")[0]
        dirty = len(status) - 1
        ahead = re.search(r"ahead (\d+)", head)
        upstream = "..." in head
        bits = []
        if dirty:
            bits.append(f"{dirty} uncommitted")
        if ahead:
            bits.append(f"{ahead.group(1)} unpushed")
        if not upstream and branch not in ("main", "master"):
            bits.append("branch never pushed")
        if not bits:
            continue
        try:
            when = (repo / ".git").stat().st_mtime
        except OSError:
            when = 0.0
        out.append(_item(
            "git", repo.name, f"{repo.name}: {', '.join(bits)}",
            detail=branch, when=when, url=repo.as_uri(),
            priority=1 if dirty > 20 else 0,
        ))
    return out


def scan_outbox(root: Path = OUTBOX) -> list[dict]:
    """Each folder in the pa-agent outbox is a package waiting to go out."""
    out = []
    if not root.is_dir():
        return out
    for pkg in sorted(root.iterdir()):
        if not pkg.is_dir() or pkg.name.startswith("."):
            continue
        files = [f for f in pkg.iterdir() if f.is_file() and not f.name.startswith(".")]
        drafts = [f.name for f in files if f.name.upper().startswith("DRAFT")]
        detail = f"draft: {drafts[0]}" if drafts else f"{len(files)} files staged"
        try:
            when = max(f.stat().st_mtime for f in files) if files else pkg.stat().st_mtime
        except OSError:
            when = 0.0
        out.append(_item("outbox", pkg.name, f"Send: {pkg.name.replace('-', ' ')}",
                         detail=detail, when=when, url=pkg.as_uri(), priority=1 if drafts else 0))
    return out


def scan_vault(root: Path = VAULT, limit: int = 25) -> list[dict]:
    """Open ``- [ ]`` checkboxes Tyler wrote in the vault's working areas."""
    out, seen = [], set()
    if not root.is_dir():
        return out
    for pattern in VAULT_TASK_GLOBS:
        for note in root.glob(pattern):
            path = str(note)
            if path in seen or any(s in path for s in VAULT_SKIP):
                continue
            seen.add(path)
            try:
                lines = note.read_text(errors="replace").splitlines()
                when = note.stat().st_mtime
            except OSError:
                continue
            for n, line in enumerate(lines, 1):
                m = _OPEN_BOX.match(line)
                if not m:
                    continue
                text = m.group(1).strip()
                due = (_DUE_TAG.search(text) or [None, ""])[1]
                text = _DUE_TAG.sub("", text).strip()
                out.append(_item("vault", f"{note.relative_to(root)}:{n}", text,
                                 detail=note.stem, due=due, when=when, url=note.as_uri()))
    out.sort(key=lambda i: (i["due"] or "9999", -i["when"]))
    return out[:limit]


LOCAL_SCANNERS = {
    "git": ("INDEMNIFY · UNSHIPPED CODE", 60, scan_git),
    "outbox": ("OUTBOX · READY TO SEND", 45, scan_outbox),
    "vault": ("TBM VAULT", 50, scan_vault),
}


# --------------------------------------------------------------------------
# drop-file feeds
# --------------------------------------------------------------------------


def _epoch(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    parsed = _parse_iso(str(value or ""))
    if parsed is None:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def read_drop_feeds(feed_dir: Path) -> list[dict]:
    """Parse every ``*.json`` in the feeds directory into a section dict."""
    sections = []
    if not feed_dir.is_dir():
        return sections
    for path in sorted(feed_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        source = re.sub(r"[^a-z0-9_-]", "", str(raw.get("source") or path.stem).lower()) or "feed"
        items = []
        for n, it in enumerate(raw.get("items") or []):
            if not isinstance(it, dict) or not str(it.get("title") or "").strip():
                continue
            items.append(_item(
                source, it.get("id") or n, str(it["title"]).strip(),
                detail=str(it.get("detail") or ""), due=str(it.get("due") or "")[:10],
                when=_epoch(it.get("when")), url=str(it.get("url") or ""),
                priority=int(it.get("priority") or 0),
            ))
        generated = _epoch(raw.get("generated")) or path.stat().st_mtime
        sections.append({
            "source": source,
            "label": str(raw.get("label") or source.upper()),
            "order": int(raw.get("order") or 40),
            "generated": generated,
            "stale": time.time() - generated > float(raw.get("stale_after_hours") or 6) * 3600,
            "items": items,
        })
    return sections


# --------------------------------------------------------------------------
# dismissals
# --------------------------------------------------------------------------


class Dismissed:
    """Item ids the user has hidden. Entries expire so nothing is lost forever."""

    def __init__(self, path: Path, keep_days: int = 21):
        self.path = Path(path)
        self.keep = keep_days * 86400
        try:
            self.ids = dict(json.loads(self.path.read_text()))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            self.ids = {}
        cutoff = time.time() - self.keep
        self.ids = {k: v for k, v in self.ids.items() if isinstance(v, (int, float)) and v > cutoff}

    def __contains__(self, item_id: str) -> bool:
        return item_id in self.ids

    def add(self, item_id: str) -> None:
        self.ids[item_id] = time.time()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.ids))
        os.replace(tmp, self.path)


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------


def local_sections(enabled=("git", "outbox", "vault")) -> list[dict]:
    """Run the credential-free scanners. Slow-ish (git); callers should cache."""
    sections = []
    for key in enabled:
        if key not in LOCAL_SCANNERS:
            continue
        label, order, scanner = LOCAL_SCANNERS[key]
        try:
            items = scanner()
        except Exception:  # one broken source must not take the widget down
            items = []
        sections.append({"source": key, "label": label, "order": order,
                         "generated": time.time(), "stale": False, "items": items})
    return sections


def arrange(local: list[dict], feed_dir: Path) -> list[dict]:
    """Merge cached local sections with freshly read drop files, sorted for display."""
    sections = [dict(s, items=list(s["items"])) for s in local]
    try:
        sections.extend(read_drop_feeds(feed_dir))
    except Exception:
        pass
    today = date.today().isoformat()
    for s in sections:
        s["items"].sort(key=lambda i: (
            0 if i["due"] and i["due"] <= today else 1,
            -i["priority"],
            i["due"] or "9999",
            -i["when"],
        ))
    sections.sort(key=lambda s: (s["order"], s["label"]))
    return sections


def item_meta(item: dict, today: str) -> tuple[str, bool]:
    """Second-line text for a feed row, and whether it is overdue."""
    bits, overdue = [], False
    if item.get("detail"):
        bits.append(item["detail"])
    due = item.get("due") or ""
    if due:
        overdue = due < today
        bits.append("due today" if due == today else (f"overdue {due}" if overdue else f"due {due}"))
    elif item.get("when"):
        bits.append(humanize(item["when"]))
    return " · ".join(bits), overdue
