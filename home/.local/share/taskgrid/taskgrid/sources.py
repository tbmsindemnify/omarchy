"""Data sources for TaskGrid.

Two kinds of rows show up in the grid:

  * manual tasks, stored in ``tasks.json`` and owned entirely by the user
  * discovered work, scraped read-only from the on-disk session logs that
    Claude Code, Codex and Hermes already write

Nothing here ever writes to an agent's data directory.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

HOME = Path.home()
# Throwaway session folders; they are not real projects and only add noise.
IGNORED_PATH_MARKERS = ("scratch-workspaces", "/tmp/")
CLAUDE_PROJECTS = HOME / ".claude" / "projects"
CODEX_SESSIONS = HOME / ".codex" / "sessions"
HERMES_STATE_DB = HOME / ".hermes" / "state.db"

# Only read the tail of a session log; these files grow into the megabytes.
TAIL_BYTES = 256 * 1024


# --------------------------------------------------------------------------
# manual tasks
# --------------------------------------------------------------------------

STATES = ("todo", "doing", "done")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class TaskStore:
    """A tiny JSON-backed task list with atomic writes."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.tasks: list[dict] = []
        self.mtime = 0.0
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text())
            self.mtime = self.path.stat().st_mtime
        except FileNotFoundError:
            self.tasks = []
            return
        except (json.JSONDecodeError, OSError):
            # Leave whatever is in memory alone rather than dropping tasks
            # because of a half-written file.
            return
        tasks = raw.get("tasks") if isinstance(raw, dict) else raw
        self.tasks = [t for t in (tasks or []) if isinstance(t, dict)]

    def changed_on_disk(self) -> bool:
        try:
            return self.path.stat().st_mtime > self.mtime
        except OSError:
            return False

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"tasks": self.tasks}, indent=2))
        os.replace(tmp, self.path)
        try:
            self.mtime = self.path.stat().st_mtime
        except OSError:
            pass

    def add(self, text: str, project: str = "", due: str = "") -> dict:
        task = {
            "id": uuid.uuid4().hex[:12],
            "text": text.strip(),
            "state": "todo",
            "project": project,
            "due": due,
            "created": _now_iso(),
        }
        self.tasks.insert(0, task)
        self.save()
        return task

    def cycle_state(self, task_id: str) -> None:
        for t in self.tasks:
            if t.get("id") == task_id:
                cur = t.get("state", "todo")
                nxt = STATES[(STATES.index(cur) + 1) % len(STATES)] if cur in STATES else "todo"
                t["state"] = nxt
                t["completed"] = _now_iso() if nxt == "done" else ""
                break
        self.save()

    def remove(self, task_id: str) -> None:
        self.tasks = [t for t in self.tasks if t.get("id") != task_id]
        self.save()

    def purge_done(self, older_than_days: int = 2) -> int:
        """Drop tasks finished a while ago so the list does not silently grow."""
        cutoff = time.time() - older_than_days * 86400
        keep, dropped = [], 0
        for t in self.tasks:
            if t.get("state") == "done":
                stamp = _parse_iso(t.get("completed") or t.get("created") or "")
                if stamp and stamp.timestamp() < cutoff:
                    dropped += 1
                    continue
            keep.append(t)
        if dropped:
            self.tasks = keep
            self.save()
        return dropped


def _parse_iso(value: str):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def bucket_for(task: dict) -> str:
    """Sort a manual task into one of the grid's sections."""
    if task.get("state") == "done":
        return "done"
    due = (task.get("due") or "").strip()
    today = date.today().isoformat()
    if due:
        return "agenda" if due <= today else "later"
    return "doing" if task.get("state") == "doing" else "unfinished"


# --------------------------------------------------------------------------
# session discovery
# --------------------------------------------------------------------------


def _tail_lines(path: Path, nbytes: int = TAIL_BYTES) -> list[str]:
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > nbytes:
                fh.seek(size - nbytes)
                fh.readline()  # discard the partial line
            data = fh.read()
    except OSError:
        return []
    return data.decode("utf-8", "replace").splitlines()


# Harness-injected envelopes that wrap the real prompt, e.g. <current_date>...</current_date>.
_ENVELOPE = re.compile(r"^\s*<([a-zA-Z0-9_-]+)(?:\s[^>]*)?>.*?</\1>\s*", re.DOTALL)
_LONE_TAG = re.compile(r"^\s*</?[a-zA-Z0-9_-]+(?:\s[^>]*)?/?>\s*")


def _clean(text: str, limit: int = 140) -> str:
    text = str(text or "")
    # Peel off every leading machine-generated block until real prose is left.
    for _ in range(12):
        stripped = _ENVELOPE.sub("", text, count=1)
        if stripped == text:
            stripped = _LONE_TAG.sub("", text, count=1)
        if stripped == text:
            break
        text = stripped
    return " ".join(text.split())[:limit].strip()


def _is_noise(text: str) -> bool:
    if not text or len(text) < 3:
        return True
    lowered = text.lower()
    return lowered.startswith((
        "<command-", "<local-command", "caveat:", "<system-reminder",
        "<app-context", "[request interrupted", "<automation_id", "<user_instructions",
        "<environment_context", "<editor_context", "this session is being continued",
        "here is a list of plugins", "current_date", "the user opened the file",
        "# files mentioned", "# agents.md", "<instructions", "this block",
    ))


class Session(dict):
    """One discovered 'where you left off' row."""


def _ignored(path: str) -> bool:
    return any(marker in (path or "") for marker in IGNORED_PATH_MARKERS)


def _session(agent, project, path, mtime, snippet, todos=None) -> Session:
    return Session(
        agent=agent,
        project=project or "(no project)",
        path=str(path or ""),
        last_active=mtime,
        snippet=snippet or "",
        todos=todos or [],
    )


def _scan_claude(max_age: float) -> list[Session]:
    out: list[Session] = []
    if not CLAUDE_PROJECTS.is_dir():
        return out
    for project_dir in CLAUDE_PROJECTS.iterdir():
        if not project_dir.is_dir():
            continue
        newest, newest_mtime = None, 0.0
        try:
            for f in project_dir.glob("*.jsonl"):
                m = f.stat().st_mtime
                if m > newest_mtime:
                    newest, newest_mtime = f, m
        except OSError:
            continue
        if newest is None or newest_mtime < max_age:
            continue
        cwd, snippet, todos = _read_claude_tail(newest)
        if _ignored(cwd) or _ignored(str(project_dir)):
            continue
        label = Path(cwd).name if cwd else project_dir.name.strip("-").split("-")[-1]
        out.append(_session("claude", label, cwd, newest_mtime, snippet, todos))
    return out


def _read_claude_tail(path: Path):
    cwd = ""
    snippet = ""
    todos: list[dict] = []
    for line in reversed(_tail_lines(path)):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not cwd:
            cwd = obj.get("cwd") or ""
        msg = obj.get("message") or {}
        content = msg.get("content")
        if not todos and isinstance(content, list):
            for block in content:
                if (isinstance(block, dict) and block.get("type") == "tool_use"
                        and block.get("name") == "TodoWrite"):
                    todos = [
                        {"text": t.get("content", ""), "status": t.get("status", "")}
                        for t in (block.get("input") or {}).get("todos", [])
                        if isinstance(t, dict)
                    ]
                    break
        if not snippet and obj.get("type") == "user":
            text = content if isinstance(content, str) else ""
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        break
            text = _clean(text)
            if not _is_noise(text):
                snippet = text
        if cwd and snippet and todos:
            break
    return cwd, snippet, todos


def _scan_codex(max_age: float, limit: int = 40) -> list[Session]:
    out: list[Session] = []
    if not CODEX_SESSIONS.is_dir():
        return out
    candidates: list[tuple[float, Path]] = []
    for root, dirs, files in os.walk(CODEX_SESSIONS):
        dirs.sort(reverse=True)  # newest date directories first
        for name in files:
            if not name.endswith(".jsonl"):
                continue
            p = Path(root) / name
            try:
                m = p.stat().st_mtime
            except OSError:
                continue
            if m >= max_age:
                candidates.append((m, p))
    candidates.sort(reverse=True)
    for mtime, path in candidates[:limit]:
        cwd, snippet = _read_codex_tail(path)
        if _ignored(cwd):
            continue
        out.append(_session("codex", Path(cwd).name if cwd else "", cwd, mtime, snippet))
    return _dedupe_by_project(out)


def _read_codex_tail(path: Path):
    cwd, snippet = "", ""
    lines = _tail_lines(path)
    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = obj.get("payload") or {}
        if not cwd:
            cwd = payload.get("cwd") or (payload.get("state") or {}).get("cwd") or ""
        if not snippet and payload.get("type") == "message" and payload.get("role") == "user":
            parts = payload.get("content") or []
            text = ""
            for block in parts:
                if isinstance(block, dict) and block.get("type") in ("input_text", "text"):
                    text = block.get("text", "")
                    break
            text = _clean(text)
            if not _is_noise(text):
                snippet = text
        if cwd and snippet:
            break
    if not snippet:
        snippet = _first_user_prompt(path)
    if not cwd:  # session_meta lives at the head of the file
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                head = json.loads(fh.readline() or "{}")
            cwd = (head.get("payload") or {}).get("cwd", "")
        except (OSError, json.JSONDecodeError):
            pass
    return cwd, snippet


def _first_user_prompt(path: Path, max_lines: int = 400) -> str:
    """The prompt that opened the session -- a good label when the tail is all tool output."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for _, line in zip(range(max_lines), fh):
                try:
                    payload = (json.loads(line).get("payload") or {})
                except json.JSONDecodeError:
                    continue
                if payload.get("type") == "message" and payload.get("role") == "user":
                    for block in payload.get("content") or []:
                        if isinstance(block, dict) and block.get("type") in ("input_text", "text"):
                            text = _clean(block.get("text", ""))
                            if not _is_noise(text):
                                return text
    except OSError:
        pass
    return ""


def _scan_hermes(max_age: float) -> list[Session]:
    out: list[Session] = []
    if not HERMES_STATE_DB.exists():
        return out
    try:
        conn = sqlite3.connect(f"file:{HERMES_STATE_DB}?mode=ro", uri=True, timeout=1.0)
    except sqlite3.Error:
        return out
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.display_name, s.source,
                   MAX(m.timestamp) AS last_ts
              FROM sessions s
              JOIN messages m ON m.session_id = s.id
             GROUP BY s.id
             ORDER BY last_ts DESC
             LIMIT 12
            """
        ).fetchall()
        for sid, name, source, last_ts in rows:
            stamp = _to_epoch(last_ts)
            if stamp < max_age:
                continue
            snippet = ""
            for (content,) in conn.execute(
                "SELECT content FROM messages WHERE session_id=? AND role='user' "
                "ORDER BY timestamp DESC LIMIT 5",
                (sid,),
            ):
                text = _clean(_hermes_text(content))
                if not _is_noise(text):
                    snippet = text
                    break
            out.append(_session("hermes", name or source or f"session {sid}", "", stamp, snippet))
    except sqlite3.Error:
        return out
    finally:
        conn.close()
    return out


def _hermes_text(content) -> str:
    if isinstance(content, (bytes, bytearray)):
        content = content.decode("utf-8", "replace")
    if isinstance(content, str) and content.lstrip().startswith(("[", "{")):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return content
        if isinstance(parsed, list):
            for block in parsed:
                if isinstance(block, dict) and block.get("type") == "text":
                    return block.get("text", "")
            return " ".join(str(b) for b in parsed)
        if isinstance(parsed, dict):
            return parsed.get("text") or parsed.get("content") or content
    return content or ""


def _to_epoch(value) -> float:
    if isinstance(value, (int, float)):
        # Hermes stores milliseconds in some builds.
        return float(value) / 1000.0 if value > 1e11 else float(value)
    parsed = _parse_iso(str(value))
    if parsed:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    return 0.0


def _dedupe_by_project(sessions: list[Session]) -> list[Session]:
    best: dict[str, Session] = {}
    for s in sessions:
        key = s["path"] or s["project"]
        if key not in best or s["last_active"] > best[key]["last_active"]:
            best[key] = s
    return list(best.values())


def scan_sessions(max_age_days: int = 10, limit: int = 12) -> list[Session]:
    """Return recent agent sessions, newest first. Never raises."""
    cutoff = time.time() - max_age_days * 86400
    found: list[Session] = []
    for scanner in (_scan_claude, _scan_codex, _scan_hermes):
        try:
            found.extend(scanner(cutoff))
        except Exception:  # a broken log must not take the widget down
            continue
    found.sort(key=lambda s: s["last_active"], reverse=True)
    return found[:limit]


def humanize(epoch: float) -> str:
    delta = max(0, time.time() - epoch)
    if delta < 90:
        return "just now"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    days = int(delta // 86400)
    return "yesterday" if days == 1 else f"{days}d ago"
