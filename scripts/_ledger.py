"""Shared helpers for the decision-ledger hooks and scripts.

Design rule for everything in this package: a hook must never break the user's
session. Any unexpected failure is swallowed and the hook exits 0. The ledger is
a safety net, and a safety net that can crash the trapeze act is worse than none.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LEDGER_DIRNAME = Path("docs") / "project-memory"
STATE_FILE = "00-PROJECT-STATE.md"
CHANGELOG_FILE = "CHANGELOG.md"
JOURNEY_FILE = "JOURNEY.md"
SUBDIRS = {"adr": "decisions", "rej": "rejections", "cr": "change-requests"}
PREFIX = {"adr": "ADR", "rej": "REJ", "cr": "CR"}
STATE_MAX_LINES = 150


def read_hook_input():
    """Parse the hook JSON delivered on stdin. Returns {} if anything is off."""
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def project_dir(payload=None):
    """Locate the project root: explicit override, then hook cwd, then env."""
    override = os.environ.get("LEDGER_PROJECT_DIR")
    if override:
        return Path(override)
    if payload and payload.get("cwd"):
        return Path(payload["cwd"])
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))


def ledger_dir(payload=None):
    return project_dir(payload) / LEDGER_DIRNAME


def ledger_exists(payload=None):
    """True only if this project actually uses the ledger.

    Every hook checks this first and exits silently when false, so installing
    the plugin globally does not spray files into unrelated projects.
    """
    return ledger_dir(payload).is_dir()


def today():
    return datetime.now().strftime("%Y-%m-%d")


def now_iso():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def records(kind, payload=None):
    """All record paths of one kind, sorted."""
    d = ledger_dir(payload) / SUBDIRS[kind]
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.md") if p.name != "README.md")


def next_id(kind, payload=None):
    """Next free numeric id for a record kind. Scans rather than counts, so a
    deleted or manually added file cannot cause a collision."""
    highest = 0
    pre = PREFIX[kind] + "-"
    for p in records(kind, payload):
        stem = p.stem
        if not stem.upper().startswith(pre):
            continue
        digits = stem[len(pre):].split("-")[0]
        if digits.isdigit():
            highest = max(highest, int(digits))
    return highest + 1


def slugify(text, max_len=48):
    out = []
    for ch in text.lower().strip():
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_/":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:max_len] or "untitled"


def append_line(path, line):
    """Append one line, creating the file if needed. Append-only by contract."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line.rstrip("\n") + "\n")


def tail(path, n):
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []
    return lines[-n:] if n else lines


def head(path, n):
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []
    return lines[:n]


def frontmatter(path):
    """Minimal YAML frontmatter reader. Flat key: value pairs only -- the
    records are written by us and deliberately keep frontmatter flat."""
    data = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return data
    if not lines or lines[0].strip() != "---":
        return data
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            k, _, v = line.partition(":")
            data[k.strip()] = v.strip()
    return data


def title_of(path):
    fm = frontmatter(path)
    if fm.get("title"):
        return fm["title"]
    for line in head(path, 40):
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def emit_context(event, text, extra=None):
    """Emit additionalContext in the shape Claude Code actually reads.

    The docs are explicit that additionalContext must sit inside
    hookSpecificOutput; placed at the top level it is silently ignored.
    """
    payload = {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": text,
        }
    }
    if extra:
        payload["hookSpecificOutput"].update(extra)
    print(json.dumps(payload))


def guard(fn):
    """Run a hook body so that no failure can ever break the session."""
    try:
        fn()
    except Exception:
        if os.environ.get("LEDGER_DEBUG"):
            import traceback
            traceback.print_exc(file=sys.stderr)
    sys.exit(0)
