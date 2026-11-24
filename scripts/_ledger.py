"""Shared helpers for the decision-ledger hooks and scripts.

Design rule for everything in this package: a hook must never break the user's
session. Any unexpected failure is swallowed and the hook exits 0. The ledger is
a safety net, and a safety net that can crash the trapeze act is worse than none.

Second design rule: a project may already keep these files, by hand, for years.
Paths are resolved through an optional `.ledger.json` so the ledger can be
mapped onto what already exists instead of imposing its own layout. Nothing is
ever moved, reformatted or overwritten -- see ADR-0008 and ADR-0009.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG_NAME = ".ledger.json"
STATE_MAX_LINES = 150

# Every path the ledger knows about, relative to the project root. A project
# overrides any subset of these in .ledger.json; the rest keep these defaults.
DEFAULTS = {
    "briefing": "docs/project-memory/00-PROJECT-STATE.md",
    "changelog": "docs/project-memory/CHANGELOG.md",
    "journey": "docs/project-memory/JOURNEY.md",
    "constraints": "docs/project-memory/CONSTRAINTS.md",
    "index": "docs/project-memory/INDEX.md",
    "decisions": "docs/project-memory/decisions",
    "rejections": "docs/project-memory/rejections",
    "change_requests": "docs/project-memory/change-requests",
    "activity": "docs/project-memory/activity",
}

# Which configured path each record kind lives in.
KIND_KEY = {"adr": "decisions", "rej": "rejections", "cr": "change_requests"}
PREFIX = {"adr": "ADR", "rej": "REJ", "cr": "CR"}

# Back-compat names used across the scripts.
LEDGER_DIRNAME = Path("docs") / "project-memory"
STATE_FILE = "00-PROJECT-STATE.md"
CHANGELOG_FILE = "CHANGELOG.md"
JOURNEY_FILE = "JOURNEY.md"
CONSTRAINTS_FILE = "CONSTRAINTS.md"
SUBDIRS = {"adr": "decisions", "rej": "rejections", "cr": "change-requests"}


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


def config(payload=None):
    """The project's .ledger.json, or {} when it has none.

    A malformed config is treated as absent rather than fatal: a typo in a
    config file must not stop a session.
    """
    path = project_dir(payload) / CONFIG_NAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def path_for(key, payload=None):
    """Absolute path for a ledger key, honouring .ledger.json overrides."""
    paths = config(payload).get("paths") or {}
    rel = paths.get(key) or DEFAULTS[key]
    return project_dir(payload) / rel


def is_adopted(key, payload=None):
    """True when this file predates the ledger and belongs to someone else.

    Adopted files are appended to in whatever style is already there, and are
    never rewritten, reordered or reformatted.
    """
    return key in (config(payload).get("adopted") or [])


def ledger_dir(payload=None):
    """The default ledger directory. Still used where a project has no config."""
    return project_dir(payload) / LEDGER_DIRNAME


def ledger_exists(payload=None):
    """True only if this project actually uses the ledger.

    Either it has a .ledger.json, or it has the default directory. Every hook
    checks this first and exits silently when false, so installing the plugin
    globally does not spray files into unrelated projects.
    """
    if (project_dir(payload) / CONFIG_NAME).is_file():
        return True
    return ledger_dir(payload).is_dir()


def ledger_paths(payload=None):
    """Every path the ledger owns or has adopted, relative to the project.

    Used to tell ledger edits apart from code edits.
    """
    paths = config(payload).get("paths") or {}
    out = []
    for key, default in DEFAULTS.items():
        out.append(Path(paths.get(key) or default).as_posix())
    return out


def is_ledger_path(rel_path, payload=None):
    """True if a repo-relative path belongs to the ledger."""
    rel = Path(rel_path).as_posix()
    for known in ledger_paths(payload):
        if rel == known or rel.startswith(known.rstrip("/") + "/"):
            return True
    return False


def today():
    return datetime.now().strftime("%Y-%m-%d")


def now_iso():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def records(kind, payload=None):
    """All record paths of one kind, sorted."""
    d = path_for(KIND_KEY[kind], payload)
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.md") if p.name != "README.md")


# A record filename, with or without a letter prefix. `adr-tools` -- by far the
# most widespread ADR convention -- writes `0001-module-boundaries.md` with no
# prefix at all, so a prefix cannot be required.
#
# The `< YEAR_FLOOR` test is what keeps a bare number from matching a date.
# `2026-11-22-notes.md` would otherwise read as record 2026 and push the next
# id to 2027. No project has 1,900 decision records; many have filenames that
# begin with a year.
YEAR_FLOOR = 1900
RECORD_STEM_RE = re.compile(
    r"^(?:(ADR|REJ|CR|RFC|DEC)[-_]?)?(\d{1,4})(?:[-_]|$)", re.I)


def record_number(stem, prefix=None):
    """The numeric id in a record filename, or None if it is not one.

    `prefix` restricts the match to one kind. A bare-numeric name has no kind,
    so it counts towards whatever kind owns the directory it sits in -- which
    is the point: an adopted `docs/adr` holding 0001..0004 must make the next
    decision 0005, not 0001 again.
    """
    m = RECORD_STEM_RE.match(stem)
    if not m:
        return None
    found, digits = m.group(1), int(m.group(2))
    if found is None:
        return digits if digits < YEAR_FLOOR else None
    if prefix and found.upper() != prefix.upper():
        return None
    return digits


def record_name_style(kind=None, payload=None):
    """"prefixed" (ADR-0003-title.md) or "bare" (0003-title.md).

    Set by the adoption scanner from what the existing folder already does,
    and applied ONLY to a record kind whose folder was adopted. The ledger's
    own folders keep the prefixed names regardless: matching a convention is
    for fitting into someone else's directory, not for restyling ours.
    """
    style = (config(payload).get("record_names") or "prefixed").lower()
    if style != "bare":
        return "prefixed"
    if kind is not None and not is_adopted(KIND_KEY[kind], payload):
        return "prefixed"
    return "bare"


def next_id(kind, payload=None):
    """Next free numeric id for a record kind. Scans rather than counts, so a
    deleted or manually added file cannot cause a collision.

    Counts the project's own unprefixed records too. Restarting at 0001 beside
    someone's existing 0001 puts two different decisions under one number,
    which is worse than a gap in the sequence.
    """
    highest = 0
    for p in records(kind, payload):
        num = record_number(p.stem, PREFIX[kind])
        if num is not None:
            highest = max(highest, num)
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


DEFAULT_CHANGELOG_ENTRY = "- {date} **{id}** {title} - `{path}`"
# Surveying 82 real projects found 20 newest-first changelogs to 1
# oldest-first. The default follows the evidence; see ADR-0011.
DEFAULT_ORDER = "newest-first"


def _write_atomic(path, text):
    """Replace a file's contents without ever leaving it truncated.

    Writes a sibling temp file and renames over the target, so an interrupted
    write cannot destroy an adopted changelog that may be the only copy of
    years of work.

    `newline=""` disables translation: the bytes written are exactly the
    string given. Writing with newline="\\n" rewrote every line ending of a
    CRLF file, which git then hid behind its own normalisation.
    """
    tmp = path.with_name(path.name + ".ledger-tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(tmp, path)


def dominant_newline(text):
    """The line ending a file actually uses, so an insert can match it."""
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    return "\r\n" if crlf > lf else "\n"


def _as_newline(text, newline):
    """Re-express text with one consistent line ending."""
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalised if newline == "\n" else normalised.replace("\n", newline)


def changelog_entry(payload=None, **fields):
    """Render one changelog entry using the project's own format."""
    template = config(payload).get("changelog_entry") or DEFAULT_CHANGELOG_ENTRY
    try:
        return template.format(**fields)
    except Exception:
        return DEFAULT_CHANGELOG_ENTRY.format(**fields)


def add_changelog_entry(text, payload=None):
    """Add an entry to the changelog, respecting the project's ordering.

    Newest-first (the default) inserts above the most recent existing entry.
    Oldest-first appends. The distinction matters: appending to the bottom of
    a newest-first file files the entry under the oldest heading, which is
    actively wrong rather than merely inconsistent.

    Existing content is never reordered, reformatted or removed; the only
    change is the inserted block. A file that cannot be decoded as UTF-8 is
    left completely alone -- see below.
    """
    path = path_for("changelog", payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    block = text.rstrip("\n") + "\n"

    if not path.is_file():
        _write_atomic(path, block)
        return path

    # Strict decode, and no newline translation on the way in: reading with
    # errors="replace" would substitute U+FFFD for undecodable bytes, and
    # reading in text mode would hide whether the file is CRLF. Either way the
    # write-back rewrites a file that may be the only copy.
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            original = fh.read()
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"{path} is not valid UTF-8 ({exc.reason} at byte {exc.start}); "
            "refusing to rewrite it. Add the entry by hand, or convert the "
            "file to UTF-8 first."
        ) from None

    # Match the file's own line endings. Writing LF into a CRLF file rewrites
    # every line in it, and git's normalisation hides that in review.
    eol = dominant_newline(original)
    block = _as_newline(block, eol)
    order = (config(payload).get("changelog_order") or DEFAULT_ORDER).lower()
    tail_sep = "" if original.endswith(("\n", "\r")) else eol

    if order != "newest-first":
        _write_atomic(path, original + tail_sep + block)
        return path

    lines = original.splitlines(keepends=True)
    cut = next((i for i, ln in enumerate(lines) if ln.startswith("## ")), None)
    if cut is None:
        # No entry headings yet: nothing to insert above, so append.
        _write_atomic(path, original + tail_sep + block)
        return path

    before, after = "".join(lines[:cut]), "".join(lines[cut:])
    # Exact check: the two halves must rejoin into the original, character for
    # character. Anything else means the splice went wrong and the file stays
    # as it was.
    if before + after != original:
        raise RuntimeError("changelog insertion would alter existing content")
    _write_atomic(path, before + block + eol + after)
    return path


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
