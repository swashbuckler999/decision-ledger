"""Shared helpers for the decision-ledger hooks and scripts.

Design rule for everything in this package: a hook must never break the user's
session. Any unexpected failure is swallowed and the hook exits 0. The ledger is
a safety net, and a safety net that can crash the trapeze act is worse than none.

Second design rule: a project may already keep these files, by hand, for years.
Paths are resolved through an optional `.ledger.json` so the ledger can be
mapped onto what already exists instead of imposing its own layout. Nothing is
ever moved, reformatted or overwritten -- see ADR-0008 and ADR-0009.
"""

import contextlib
import json
import os
import re
import sys
import time
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


def take_project_flag(argv):
    """Pop `--project <path>` (or `--project=<path>`) and pin the project to it.

    Without this every writing script resolved the project from the process
    working directory, and a live session showed why that is not safe: in an
    agent's shell `LEDGER_PROJECT_DIR`, `CLAUDE_PROJECT_DIR` and
    `CLAUDE_PLUGIN_ROOT` are all empty, so the fallback is cwd -- and the
    harness reset that session's cwd mid-session to an unrelated folder. The
    records would have been scaffolded there, silently and correctly as far as
    the script could tell.

    A flag rather than an environment variable because the instruction has to
    work in whatever shell the agent happens to use. `VAR=x command` is POSIX
    and does nothing in PowerShell, and the agent does not choose its shell.

    Returns argv with the flag removed.
    """
    out, i = [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--project" and i + 1 < len(argv):
            os.environ["LEDGER_PROJECT_DIR"] = argv[i + 1]
            i += 2
            continue
        if a.startswith("--project="):
            os.environ["LEDGER_PROJECT_DIR"] = a.split("=", 1)[1]
            i += 1
            continue
        out.append(a)
        i += 1
    return out


def plugin_root():
    """The installed plugin's own directory -- where `scripts/` and `skills/`
    sit side by side. Derived from this file's location, so it is right in the
    source checkout and in any install, and needs no environment variable."""
    return Path(__file__).resolve().parent.parent


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


def _mapping(payload, key):
    """A config value that must be a dict, or {} if it is anything else.

    `config()` already survives invalid JSON, but valid JSON of the wrong
    shape got through: `"paths": "docs"` raised AttributeError on the next
    `.get`, inside a hook, for every call in the session. The promise is that
    a bad config reads as absent, and that has to cover the shape too.
    """
    value = config(payload).get(key)
    return value if isinstance(value, dict) else {}


def _choice(payload, key, default):
    """A config value that must be a string, lowercased, or the default."""
    value = config(payload).get(key)
    return value.lower() if isinstance(value, str) and value else default


def path_for(key, payload=None):
    """Absolute path for a ledger key, honouring .ledger.json overrides.

    An override that leaves the project is ignored and the default is used.
    `paths` is hand-editable, and `Path(root) / "C:/Windows/x"` discards the
    root entirely while `../..` walks out of it -- either way the ledger
    would be writing outside the repository it was installed in. Nothing the
    scanner proposes is ever absolute, so rejecting those costs nothing.
    """
    root = project_dir(payload)
    rel = _mapping(payload, "paths").get(key)
    if isinstance(rel, str) and rel:
        candidate = root / rel
        try:
            inside = candidate.resolve().is_relative_to(root.resolve())
        except Exception:
            inside = False
        if inside:
            return candidate
    return root / DEFAULTS[key]


def rel_path(key, payload=None):
    """Project-relative configured path, for use in messages.

    Every instruction the hooks print has to name the file this project
    actually keeps. Printing the default name at a project that adopted
    `STATUS.md` sends the reader to a file that does not exist, which is the
    adoption promise broken in the one place the user reads.
    """
    root = project_dir(payload)
    try:
        return path_for(key, payload).relative_to(root).as_posix()
    except Exception:
        return DEFAULTS[key]


def is_adopted(key, payload=None):
    """True when this file predates the ledger and belongs to someone else.

    Adopted files are appended to in whatever style is already there, and are
    never rewritten, reordered or reformatted.

    The list must really be a list: `"adopted": "decisions"` would otherwise
    substring-match, so `is_adopted("decision")` came back true as well.
    """
    adopted = config(payload).get("adopted")
    return isinstance(adopted, list) and key in adopted


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
    root = project_dir(payload)
    out = []
    for key in DEFAULTS:
        # Via path_for so a rejected override cannot make a ledger file look
        # like code (which would fire the unrecorded-change nag on our own
        # writes) or make code look like a ledger file (which would silence
        # it for real work).
        try:
            out.append(path_for(key, payload).relative_to(root).as_posix())
        except Exception:
            out.append(Path(DEFAULTS[key]).as_posix())
    return out


def is_ledger_path(rel_path, payload=None):
    """True if a repo-relative path belongs to the ledger."""
    rel = Path(rel_path).as_posix()
    for known in ledger_paths(payload):
        if rel == known or rel.startswith(known.rstrip("/") + "/"):
            return True
    return False


def is_recording_path(rel_path, payload=None):
    """True if this path is somewhere reasoning actually gets recorded.

    Every recording path is a ledger path; the activity trail is the one that
    is not. It is written by the PostToolUse hook on every file edit, so it is
    evidence that something was *edited*, never that anything was *recorded*.

    Conflating the two silenced the Stop gate exactly when it mattered. On the
    first edit in a freshly installed project the hook creates
    `activity/.gitignore`, git reports it as untracked, the gate saw "a ledger
    file changed" and stayed quiet -- so the first session of every new
    project, the one where the habit is being set, got no reminder at all.
    Found by replaying a whole session in order; no single-hook test can see
    it, because it takes an earlier turn to create the condition.
    """
    if not is_ledger_path(rel_path, payload):
        return False
    try:
        activity = Path(path_for("activity", payload)).relative_to(
            project_dir(payload)).as_posix()
    except Exception:
        activity = DEFAULTS["activity"]
    rel = Path(rel_path).as_posix()
    return not (rel == activity or rel.startswith(activity.rstrip("/") + "/"))


_GIT_DIR_CACHE = {}


def is_git_repo(root):
    """True for a normal checkout, a worktree, or a submodule.

    `.git` is a *directory* only in a primary checkout. In a linked worktree
    and in a submodule it is a plain file holding `gitdir: <path>`, so
    `.is_dir()` is false and every caller concluded the project had no
    version control at all: the scanner reported "not a git repository", the
    miner returned zero commits, and a worked-on project read as greenfield.

    Claude Code's own desktop sessions run in worktrees, which is where this
    was found.
    """
    return (Path(root) / ".git").exists()


def git_dir(root):
    """The real git directory for `root`, or None.

    Asked of git rather than assumed, because in a worktree the per-worktree
    git directory lives under the primary repository's `.git/worktrees/<name>`
    and `root/.git` is a file. Anything writing state next to the repository
    has to go here, or it silently fails -- which is what broke the Stop
    hook's de-duplication, leaving it to repeat the same reminder every turn.
    """
    import subprocess
    key = str(root)
    if key in _GIT_DIR_CACHE:  # three callers per Stop hook; one subprocess
        return _GIT_DIR_CACHE[key]
    _GIT_DIR_CACHE[key] = None
    try:
        out = subprocess.run(["git", "rev-parse", "--absolute-git-dir"],
                             cwd=str(root), capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=10)
    except Exception:
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    _GIT_DIR_CACHE[key] = Path(out.stdout.strip())
    return _GIT_DIR_CACHE[key]


def dirty_paths(cwd):
    """Every path git reports as modified or untracked, with its fingerprint.

    Returns {path: "<size>:<mtime>"} or None when git is unavailable. Used to
    tell what a session actually changed from what was already lying around.
    """
    import subprocess
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=10)
    except Exception:
        return None
    if out.returncode != 0:
        return None
    found = {}
    for line in out.stdout.splitlines():
        if len(line) <= 3:
            continue
        path = line[3:].strip()
        if " -> " in path:  # rename: keep the destination
            path = path.split(" -> ")[-1]
        path = path.strip('"')
        try:
            st = (Path(cwd) / path).stat()
            found[path] = f"{st.st_size}:{int(st.st_mtime)}"
        except OSError:
            found[path] = "?"
    return found


def write_session_baseline(cwd):
    """Record what was already dirty when the session started.

    Without this the Stop hook reported every untracked file in the working
    tree as an unrecorded change of this session -- editor settings, local
    scratch, anything not yet gitignored. A live session had it flag a file it
    had never written to. The warning that matters then looks exactly like the
    noise, which is how a reminder gets ignored.
    """
    gd = git_dir(cwd)
    paths = dirty_paths(cwd)
    if gd is None or paths is None:
        return False
    try:
        (gd / "ledger-baseline").write_text(
            json.dumps({"paths": paths, "head": head_sha(cwd)}),
            encoding="utf-8")
        return True
    except OSError:
        return False


def head_sha(cwd):
    """The current commit, or None where there is none yet."""
    import subprocess
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(cwd),
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=10)
    except Exception:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def committed_since(cwd, base_head):
    """Paths touched by commits made since `base_head`, or [] if unknown."""
    import subprocess
    if not base_head:
        return []
    try:
        out = subprocess.run(["git", "diff", "--name-only", f"{base_head}..HEAD"],
                             cwd=str(cwd), capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=15)
    except Exception:
        return []
    if out.returncode != 0:
        return []
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def read_session_baseline(cwd):
    """The session-start snapshot: {"paths": {...}, "head": sha}, or None."""
    gd = git_dir(cwd)
    if gd is None:
        return None
    try:
        data = json.loads((gd / "ledger-baseline").read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(data, dict) and "paths" in data:
        return data
    # An older baseline held the path map alone.
    return {"paths": data if isinstance(data, dict) else {}, "head": None}


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
    style = _choice(payload, "record_names", "prefixed")
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


ACTIVITY_GITIGNORE = "# Working notes, not documentation.\n*\n!.gitignore\n"


def activity_dir(payload=None):
    """The activity folder, created with its .gitignore already in place.

    Both writers go through here. Only one of them used to create the
    .gitignore, so whichever wrote first decided whether the trail was ignored
    -- and the PreCompact hook, which writes first in most sessions, did not.
    The result was a raw working-notes trail committed into the repository,
    which is the one thing its own ignore file says it must not be.
    """
    folder = path_for("activity", payload)
    folder.mkdir(parents=True, exist_ok=True)
    gi = folder / ".gitignore"
    if not gi.exists():
        try:
            gi.write_text(ACTIVITY_GITIGNORE, encoding="utf-8", newline="\n")
        except OSError:
            pass
    return folder


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

    The temp name carries the pid. With a fixed name, two sessions appending at
    the same moment wrote the same temp file and one `os.replace` then failed
    because the other had already renamed it -- measured as two of four
    concurrent records landing on disk with no changelog entry and a traceback
    for the caller. And the temp file is removed on failure, or a read-only
    target leaves `CHANGELOG.md.ledger-tmp` lying beside it forever.
    """
    tmp = path.with_name(f"{path.name}.{os.getpid()}.ledger-tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


@contextlib.contextmanager
def _exclusive(path, timeout=10.0, stale=30.0):
    """Hold a lock beside `path` for one read-modify-write.

    Unique temp names stopped two concurrent writers from clobbering each
    other's temp file, and did nothing about the real problem: both read the
    changelog, both spliced their own entry into what they read, and both
    wrote. The second write was complete and correct and silently dropped the
    first entry -- measured as five records producing three changelog lines.
    On Windows `os.replace` also fails outright while another process holds
    the destination open, which is how it surfaced.

    A lock file rather than a library: this plugin has no dependencies, and
    `O_CREAT | O_EXCL` is atomic on every filesystem that matters. A lock left
    behind by a killed process is stolen once it goes stale, so a crash cannot
    wedge the ledger permanently.
    """
    lock = path.with_name(path.name + ".ledger-lock")
    deadline = time.time() + timeout
    fd = None
    while fd is None:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age = time.time() - lock.stat().st_mtime
            except OSError:
                continue  # it vanished between the failure and the stat; retry
            if age > stale:
                try:
                    lock.unlink()
                except OSError:
                    pass
                continue
            if time.time() > deadline:
                raise RuntimeError(
                    f"timed out waiting for {lock.name}; another session may be "
                    "writing the ledger. Delete it if nothing else is running.")
            time.sleep(0.05)
        except OSError:
            # The directory may not be writable. Carry on unlocked rather than
            # refusing to record anything at all.
            break
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                lock.unlink()
            except OSError:
                pass


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


def _add_changelog_entry_locked(text, payload=None):
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
    order = _choice(payload, "changelog_order", DEFAULT_ORDER)
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


def add_changelog_entry(text, payload=None):
    """Add an entry to the changelog, serialised against other sessions.

    The lock covers the whole read-modify-write, because that is the unit that
    has to be atomic: two sessions that each read, splice and write produce one
    complete, correct file that is missing the other's entry.
    """
    path = path_for("changelog", payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive(path):
        return _add_changelog_entry_locked(text, payload)


def tail(path, n):
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except Exception:
        return []
    return lines[-n:] if n else lines


def head(path, n):
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except Exception:
        return []
    return lines[:n]


def frontmatter(path):
    """Minimal YAML frontmatter reader. Flat key: value pairs only -- the
    records are written by us and deliberately keep frontmatter flat.

    Read as utf-8-sig, because a UTF-8 BOM made the first line `\\ufeff---`
    instead of `---`, so the whole block was skipped: the record lost its id,
    status and date in the index and in the session briefing, and fell back to
    its filename and its first heading. Several Windows editors write a BOM by
    default, so this is a likely state for a record a human created by hand.
    """
    data = {}
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
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
