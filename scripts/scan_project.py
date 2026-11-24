"""Detect a project's existing memory conventions. Read-only.

This script never writes to the project it scans. It opens files, reads a
bounded prefix of each, and prints JSON. That is the whole blast radius.

Its job is the one judgement in adoption that must not be left to prose: what
files already exist, what each one is, and -- for a changelog -- what order and
entry format it uses. Getting the order wrong files new entries under the
oldest heading in a file that may hold years of work.

Usage:
    python scripts/scan_project.py [path]            # one project, JSON
    python scripts/scan_project.py --survey [parent] # every child, JSON array
"""

import json
import re
import subprocess
import sys
from pathlib import Path

MAX_READ = 400_000  # bytes read from any one file; enough to judge shape

# Two tiers, because matching loosely on an adoptable role is how a ledger
# ends up appending session narrative into someone's API reference.
#
#   strong: may match as the whole stem, a prefix or a suffix
#   exact:  must be the entire stem
#
# Surveying 82 projects found "notes" and "log" as suffixes catching
# API_NOTES.md, PLATFORM_NOTES.md, 02-research-notes.md and
# VIDEO_DOWNLOAD_research_log.md -- none of them journeys, all of them files
# the ledger would then have written into. See ADR-0013.
ROLE_PATTERNS = {
    "changelog": {
        "strong": ("changelog", "change-log", "changes", "release-notes", "releases"),
        "exact": ("history",),
    },
    "status": {
        "strong": ("status", "project-state"),
        "exact": ("state", "current", "progress"),
    },
    "journey": {
        "strong": ("journey", "devlog", "dev-log", "worklog", "work-log",
                   "session-log", "diary", "narrative"),
        "exact": ("log", "notes"),
    },
    "decisions": {
        "strong": ("decisions", "decision-log", "architecture-decisions"),
        "exact": ("adr",),
    },
    "rejections": {
        "strong": ("rejections", "rejected", "not-doing"),
        "exact": ("declined", "wontfix"),
    },
    "constraints": {
        "strong": ("constraints", "gotchas"),
        "exact": ("caveats", "limits", "environment"),
    },
    "plan": {
        "strong": ("plan", "roadmap"),
        "exact": ("todo", "backlog"),
    },
    "readme": {"strong": (), "exact": ("readme",)},
}

MEMORY_DIRS = (".ai", "docs/memory", "docs/project-memory", "docs/adr",
               "docs/decisions", "adr", "decisions", "docs/records")

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ledger as L  # noqa: E402
import mine_history  # noqa: E402


def role_of(path):
    """Classify a file by name, or None. Exact matches win over loose ones."""
    stem = path.stem.lower().replace("_", "-").strip("-")
    # Strip a leading sequence number: "02-research-notes" -> "research-notes".
    stem = re.sub(r"^\d+[-.]", "", stem)

    for role, tiers in ROLE_PATTERNS.items():
        if stem in tiers["exact"] or stem in tiers["strong"]:
            return role
    for role, tiers in ROLE_PATTERNS.items():
        for name in tiers["strong"]:
            if stem.startswith(name + "-") or stem.endswith("-" + name):
                return role
    return None


def read_prefix(path):
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            return fh.read(MAX_READ)
    except Exception:
        return ""


VERSION_RE = re.compile(r"^#{2,4}\s+v?\d+(\.\d+)*\b", re.I)
DECLARED_RE = re.compile(
    r"(newest|most recent|latest)\s*(entries\s*)?(first|at the top)"
    r"|reverse[- ]chronological"
    r"|(oldest|earliest)\s*(entries\s*)?(first|at the top)", re.I)


def entry_lines(text):
    """Lines that head an entry, at the shallowest level that has any.

    An entry heading is dated or versioned: "## 2026-11-22 - thing" or
    "## v2 (Current - June 2026)". Requiring two of them missed every
    single-entry changelog, of which this corpus has several.
    """
    for level in ("## ", "### ", "#### "):
        rows = [ln for ln in text.splitlines()
                if ln.startswith(level)
                and (DATE_RE.search(ln) or VERSION_RE.match(ln))]
        if rows:
            return level.strip(), rows
    bullets = [ln for ln in text.splitlines()
               if ln[:2] in ("- ", "* ") and DATE_RE.search(ln)]
    if len(bullets) >= 2:
        return "bullet", bullets
    return None, []


def declared_order(text):
    """An order the file states outright, which beats any inference."""
    head = "\n".join(text.splitlines()[:25])
    m = DECLARED_RE.search(head)
    if not m:
        return None
    if m.group(0).lower().startswith(("oldest", "earliest")):
        return "oldest-first"
    return "newest-first"


def infer_order(rows):
    """Compare where the newest and oldest dates sit, not first versus last.

    First-versus-last is wrong whenever several entries share a date, which is
    most short changelogs -- it reports them as undetermined.
    """
    dated = [(DATE_RE.search(r).group(1), i) for i, r in enumerate(rows)
             if DATE_RE.search(r)]
    if len(dated) < 2:
        return "single-entry" if len(dated) == 1 else None
    newest = min(i for dt, i in dated if dt == max(d for d, _ in dated))
    oldest = min(i for dt, i in dated if dt == min(d for d, _ in dated))
    if newest == oldest:
        return "undetermined"
    return "newest-first" if newest < oldest else "oldest-first"


def git_order(path, root):
    """Where does new content actually land? The strongest available signal.

    Dates cannot settle a changelog whose entries all share one day, which is
    most short ones. Git can: compare the file against an earlier revision and
    see whether the added lines sit near the top or the bottom.
    """
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return None
    try:
        log = subprocess.run(
            ["git", "log", "--format=%H", "-n", "8", "--", rel],
            cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        commits = log.stdout.split()
        if len(commits) < 2:
            return None
        old = subprocess.run(["git", "show", f"{commits[-1]}:{rel}"],
                             cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        if old.returncode != 0:
            return None
    except Exception:
        return None

    old_lines = old.stdout.splitlines()
    new_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not old_lines or len(new_lines) <= len(old_lines):
        return None

    # The first line where the two versions diverge, as a fraction of the file.
    cut = next((i for i, (a, b) in enumerate(zip(new_lines, old_lines)) if a != b),
               len(old_lines))
    fraction = cut / max(len(new_lines), 1)
    if fraction < 0.25:
        return "newest-first"
    if fraction > 0.75:
        return "oldest-first"
    return None


def changelog_shape(path, root=None):
    """Order, heading style and entry count for a changelog-like file."""
    text = read_prefix(path)
    style, rows = entry_lines(text)
    declared = declared_order(text)
    inferred = infer_order(rows)

    order, source = declared, "declared"
    if not order or order in ("undetermined", "single-entry"):
        if inferred in ("newest-first", "oldest-first"):
            order, source = inferred, "inferred"
        else:
            from_git = git_order(path, root) if root else None
            if from_git:
                order, source = from_git, "git-history"
            else:
                order, source = inferred, None

    return {
        "order": order,
        "order_source": source,
        "order_confident": order in ("newest-first", "oldest-first"),
        "entry_style": style,
        "entry_sample": rows[0][:90] if rows else None,
        "dated_entries": len(rows),
        "truncated": path.stat().st_size > MAX_READ,
    }


def record_dir_shape(d):
    """Numbering convention inside an existing decisions directory."""
    files = [p for p in d.glob("*.md") if p.name.lower() != "readme.md"]
    prefixes, widths, highest = set(), set(), 0
    for p in files:
        m = L.RECORD_STEM_RE.match(p.stem)
        num = L.record_number(p.stem)
        if m and num is not None:
            # No prefix is itself a convention -- adr-tools writes 0001-foo.md.
            prefixes.add((m.group(1) or "").upper() or "(none)")
            widths.add(len(m.group(2)))
            highest = max(highest, num)
    return {
        "files": len(files),
        "prefixes": sorted(prefixes),
        "id_widths": sorted(widths),
        "highest_id": highest,
        "numbered": bool(prefixes),
    }


def scan(root):
    root = Path(root)
    out = {
        "project": root.name,
        "is_git": (root / ".git").is_dir(),
        "files": {},
        "memory_dirs": [],
        "has_ledger_config": (root / ".ledger.json").is_file(),
    }
    if not root.is_dir():
        out["error"] = "not a directory"
        return out

    candidates = []
    try:
        candidates += [p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".md"]
    except Exception:
        pass
    docs = root / "docs"
    if docs.is_dir():
        try:
            candidates += [p for p in docs.iterdir()
                           if p.is_file() and p.suffix.lower() == ".md"]
        except Exception:
            pass

    for p in candidates:
        role = role_of(p)
        if not role:
            continue
        try:
            size = p.stat().st_size
        except Exception:
            continue
        rel = p.relative_to(root).as_posix()
        entry = {"path": rel, "bytes": size,
                 "lines": read_prefix(p).count("\n") + 1}
        if role in ("changelog", "journey", "status"):
            entry.update(changelog_shape(p, root))
        # Keep the largest candidate per role; a project may have several.
        if role not in out["files"] or size > out["files"][role]["bytes"]:
            out["files"][role] = entry

    for rel in MEMORY_DIRS:
        d = root / rel
        if d.is_dir():
            info = {"path": rel}
            info.update(record_dir_shape(d))
            out["memory_dirs"].append(info)

    roles = set(out["files"])
    out["verdict"] = (
        "greenfield" if not roles and not out["memory_dirs"]
        else "adopt" if roles - {"readme"} or out["memory_dirs"]
        else "readme-only"
    )
    return out


ENTRY_TEMPLATES = {
    "##": "## {date} - {id} {title}\n\nRecorded in `{path}`.\n",
    "###": "### {date} - {id} {title}\n\nRecorded in `{path}`.\n",
    "####": "#### {date} - {id} {title}\n\nRecorded in `{path}`.\n",
}

LEDGER_DEFAULTS = {
    "briefing": "docs/project-memory/00-BRIEFING.md",
    "changelog": "docs/project-memory/CHANGELOG.md",
    "journey": "docs/project-memory/JOURNEY.md",
    "constraints": "docs/project-memory/CONSTRAINTS.md",
    "index": "docs/project-memory/INDEX.md",
    "decisions": "docs/project-memory/decisions",
    "rejections": "docs/project-memory/rejections",
    "change_requests": "docs/project-memory/change-requests",
    "activity": "docs/project-memory/activity",
}

# The briefing and index are never adopted: the briefing is injected into every
# session and rewritten as state changes, which is incompatible with a
# maintained status log, and the index is generated. See ADR-0009.
ADOPTABLE = ("changelog", "journey", "constraints")


def propose(root):
    """Draft a .ledger.json from a scan, plus the questions a human must settle.

    Returns (config, review). Nothing is written; the caller decides.
    """
    info = scan(root)
    paths = dict(LEDGER_DEFAULTS)
    adopted, review = [], []

    for role in ADOPTABLE:
        found = info["files"].get(role)
        if found:
            paths[role] = found["path"]
            adopted.append(role)

    # Every directory that holds records gets a line, whether or not its
    # numbering is understood. Silence here is how a second decisions folder
    # appears beside someone's existing one with nobody told.
    # The ledger's own directory is not someone else's record folder. Without
    # this, a project that already has the ledger installed gets warned about
    # its own files on every scan.
    own = {Path(v).parent.as_posix() for v in LEDGER_DEFAULTS.values()}
    own |= {Path(v).as_posix() for v in LEDGER_DEFAULTS.values()}

    cfg_names = {}
    claimed = False
    for d in info.get("memory_dirs", []):
        if not d["files"] or d["path"] in own:
            continue
        if d.get("numbered") and not claimed:
            paths["decisions"] = d["path"]
            adopted.append("decisions")
            claimed = True
            review.append(
                f"{d['path']} already holds {d['files']} numbered records "
                f"(prefixes {', '.join(d['prefixes'])}, highest {d['highest_id']}). "
                f"Adopted: new decisions continue at "
                f"{d['highest_id'] + 1:04d}; nothing is renumbered.")
            if d["prefixes"] == ["(none)"]:
                cfg_names["record_names"] = "bare"
                review.append(
                    f"{d['path']} names records without a letter prefix "
                    "(adr-tools style), so new ones match: "
                    f"{d['highest_id'] + 1:04d}-title.md. The id inside each "
                    "record is still ADR-NNNN.")
        else:
            review.append(
                f"{d['path']} holds {d['files']} file(s) with no numbering this "
                "tool recognises. NOT adopted -- decisions default to "
                f"{LEDGER_DEFAULTS['decisions']}. Check it by hand: if those are "
                "records, point `paths.decisions` at that directory instead, or "
                "you will end up with two decision folders.")

    cfg = {"version": 1, "paths": paths, "adopted": sorted(set(adopted))}
    cfg.update(cfg_names)

    cl = info["files"].get("changelog")
    if cl:
        if cl["order_confident"]:
            cfg["changelog_order"] = cl["order"]
            review.append(
                f"Changelog order is {cl['order']}, from {cl['order_source']}.")
        else:
            # Leaving the key out would silently fall back to the default,
            # which is the same guess with none of the paper trail. Write it
            # down, mark it unconfirmed, and make the skill ask.
            cfg["changelog_order"] = "newest-first"
            cfg["unconfirmed"] = ["changelog_order"]
            review.append(
                f"CANNOT DETERMINE changelog order (saw '{cl['order']}' from "
                f"{cl['dated_entries']} entries). Proposed newest-first as the "
                "corpus default and marked it unconfirmed. ASK the user before "
                "writing this config -- a wrong order files entries where "
                "nobody will look.")
        template = ENTRY_TEMPLATES.get(cl["entry_style"])
        if template:
            cfg["changelog_entry"] = template
            review.append(
                f"Entry format copied from the file's own style "
                f"({cl['entry_style']}): {cl['entry_sample']}")

    status = info["files"].get("status")
    if status:
        review.append(
            f"{status['path']} ({status['bytes']:,} bytes) is NOT adopted. The "
            "briefing is a new file that points at it -- see ADR-0009.")

    if not info["is_git"]:
        review.append(
            "Not a git repository: the Stop hook and orphan detection stay "
            "silent here, because both compare against committed history.")

    # A project with months of commits and no notes is not greenfield, however
    # empty its docs directory looks. Treating it as greenfield is how the
    # reasoning behind everything already built gets left in the commit log
    # where no future session will look for it.
    if info["is_git"] and not (set(info["files"]) - {"readme"}):
        try:
            hist = mine_history.scan(root)
        except Exception:
            hist = None
        if hist and hist["total_commits"] >= 5:
            review.append(
                f"No memory files, but {hist['total_commits']} commits exist "
                f"({hist['first_commit']} to {hist['last_commit']}) and "
                f"{hist['matched']} of them carry evidence worth a record. "
                "This project is NOT greenfield. Run the `ledger-backfill` "
                "skill before starting new work, or everything decided so far "
                "stays invisible to the next session.")

    return cfg, review


def main():
    flags = {"--survey", "--propose"}
    args = [a for a in sys.argv[1:] if a not in flags]
    target = Path(args[0]) if args else Path.cwd()

    if "--propose" in sys.argv:
        cfg, review = propose(target)
        print(json.dumps(cfg, indent=2))
        if review:
            print("\n--- review before writing this config ---", file=sys.stderr)
            for note in review:
                print(f"  * {note}", file=sys.stderr)
        return 0

    if "--survey" not in sys.argv:
        print(json.dumps(scan(target), indent=2))
        return 0

    results = []
    for child in sorted(q for q in target.iterdir() if q.is_dir()):
        if child.name.startswith("."):
            continue
        try:
            results.append(scan(child))
        except Exception as exc:
            results.append({"project": child.name, "error": repr(exc)})
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
