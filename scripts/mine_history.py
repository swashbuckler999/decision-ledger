"""Mine a project's git history for candidate ledger records. Read-only.

For a project that has been worked on for months but never kept notes, the
commit log is the only surviving record of why anything is the way it is. This
script finds the commits that carry reasoning and classifies them. It writes
nothing: the output is a worklist for the `ledger-backfill` skill, which drafts
records with the user rather than from this script alone.

Why a script and not just reading the log: the log is long, most of it is
mechanical, and the judgement of which commits matter should not depend on how
much of it fits in a context window. The filter here is deterministic and the
same every run.

Usage:
    python scripts/mine_history.py [path]            # JSON candidates
    python scripts/mine_history.py [path] --summary  # human-readable
"""

import json
import re
import subprocess
import sys
from pathlib import Path

# Commits whose subject carries one of these are about a route changed or
# closed, which is the material rejections are made of. Found by reading the
# subjects in the corpus rather than guessed: "switch", "drop" and "revert"
# between them cover most abandoned work that leaves any trace at all.
REJECTION_WORDS = (
    "revert", "roll back", "rollback", "abandon", "give up", "back out",
    "drop ", "remove ", "delete ", "disable ", "stop using", "no longer",
)
DECISION_WORDS = (
    "switch", "replace", "migrate", "move to", "instead of", "rewrite",
    "adopt", "pin ", "standardise", "standardize", "consolidate",
    "introduce", "choose", "use ",
)
CONSTRAINT_WORDS = (
    "only works", "requires", "must be", "cannot", "fails when", "workaround",
    "timezone", "rate limit", "permission", "credential", "elevated",
)

# A subject that states a reason, even without a keyword above: two clauses
# joined by punctuation, an explicit "to avoid X", or a measurement.
#
# Matching loosely is right here, and it is the opposite of the rule for file
# roles (ADR-0013). There, a false positive attached the ledger to a file it
# would then write into. Here a false positive is one extra line in a list the
# user reads and dismisses. The tier follows the consequence, not the
# confidence.
REASON_RE = re.compile(
    r"(because|so that|to stop\b|to avoid\b|to prevent\b|to fix\b|"
    r";|\s-\s|\s--\s|\d+\s*(s|ms|m|h|gb|mb|kb|%|x|minutes?|seconds?|hours?)\b)",
    re.I)

# A commit header line in the deletion log: full sha, space, ISO date. Matched
# by its own shape so no sentinel character is needed -- see deleted_paths().
HEADER_RE = re.compile(r"^([0-9a-f]{40}) (\d{4}-\d{2}-\d{2})$")

# Field separator for commits(). Split explicitly with .split(), never with
# .splitlines(), which treats this character as a line break.
SEP = "\x1e"


def git(root, *args):
    """Run git, decoding explicitly. text=True uses the ANSI code page on
    Windows and raises on any non-ASCII byte in a commit message."""
    try:
        out = subprocess.run(("git",) + args, cwd=root, capture_output=True,
                             encoding="utf-8", errors="replace", timeout=60)
    except Exception:
        return None
    return out.stdout if out.returncode == 0 else None


def commits(root):
    raw = git(root, "log", "--no-merges", f"--format=%H{SEP}%ad{SEP}%s{SEP}%b%x00",
              "--date=short")
    if not raw:
        return []
    out = []
    for chunk in raw.split("\x00"):
        parts = chunk.strip("\n").split(SEP)
        if len(parts) < 4:
            continue
        sha, date, subject, body = parts[0].strip(), parts[1], parts[2], parts[3]
        if not sha:
            continue
        out.append({"sha": sha[:10], "date": date, "subject": subject,
                    "body": body.strip()})
    return out


# The strongest words there are: someone did not merely change direction, they
# undid work. These are scored above everything else because a rejection is
# the record type no other source can reconstruct.
UNDO_WORDS = ("revert", "roll back", "rollback", "abandon", "back out",
              "give up", "no longer", "stop using")

# How many candidates a single run offers by default. A backfill is a sitting
# worth of work, not a migration: the corpus has repositories with 400+ commits
# that state a reason, and a worklist that long is abandoned rather than done.
# The rest stay in git, which is where they already are and is not lost.
DEFAULT_LIMIT = 40


def classify(c, body_informative=True):
    """Score a commit as evidence, or return None.

    A commit can only ever be *evidence*. The kind proposed here is a starting
    point for the skill to confirm, never a conclusion -- "drop the nightly
    job" might be a rejection of the job or a decision to run it manually, and
    only the body or the user can say which.

    `body_informative` is decided per repository, not globally. In a project
    where 97% of commits carry a written body -- which the corpus behind this
    design actually contains -- "has a body" separates nothing, and treating it
    as a signal flagged 98% of all commits. Where bodies are rare, one is the
    single best indicator that reasoning was written down at the time.
    """
    subject, body = c["subject"], c["body"]
    text = (subject + "\n" + body).lower()
    signals, kinds, score = [], [], 0

    if body:
        if body_informative:
            signals.append("has a message body (reasoning written at the time)")
            score += 2
        else:
            signals.append("has a message body (common in this repo)")

    hit = next((w for w in UNDO_WORDS if w in text), None)
    if hit:
        signals.append(f"undoes earlier work: {hit!r}")
        kinds.append("rej")
        score += 3
    else:
        hit = next((w for w in REJECTION_WORDS if w in text), None)
        if hit:
            signals.append(f"closes a route: {hit.strip()!r}")
            kinds.append("rej")
            score += 1

    hit = next((w for w in DECISION_WORDS if w in text), None)
    if hit:
        signals.append(f"decision word: {hit.strip()!r}")
        kinds.append("adr")
        score += 1

    if any(w in text for w in CONSTRAINT_WORDS):
        signals.append("mentions an environment limit (constraint candidate)")
        kinds.append("constraint")
        score += 1

    m = REASON_RE.search(subject)
    if m:
        signals.append(f"subject states a reason: {m.group(0).strip()!r}")
        score += 1

    if score < 2:
        return None  # one weak signal is not evidence
    return {"kind": kinds[0] if kinds else "adr", "score": score,
            "signals": signals}


def deleted_paths(root):
    """Files that were added and later deleted: routes that were abandoned.

    These are the clearest evidence of work thrown away, and the thing a
    changelog never records because the file simply stops being mentioned.
    """
    # No sentinel character here. str.splitlines() treats \x1e, \x1c, \x1d and
    # \x85 as line boundaries, so a separator-prefixed format is shredded by
    # the very call used to read it -- which is how this returned nothing at
    # all while the git query underneath was correct. Commit lines are matched
    # by their own unambiguous shape instead.
    raw = git(root, "log", "--diff-filter=D", "--name-only",
              "--format=%H %ad", "--date=short")
    if not raw:
        return []
    out, sha, date = [], None, None
    for line in raw.split("\n"):
        head = HEADER_RE.match(line.strip())
        if head:
            sha, date = head.group(1), head.group(2)
            continue
        if line.strip() and sha:
            out.append({"sha": sha[:10], "date": date, "path": line.strip()})
    return out


EMPTY = {"is_git": False, "total_commits": 0, "commits_with_body": 0,
         "body_informative": False, "matched": 0, "limit": DEFAULT_LIMIT,
         "first_commit": None, "last_commit": None, "candidates": [],
         "deleted": []}


def scan(root, limit=DEFAULT_LIMIT):
    root = Path(root)
    # `.git` is a file in a worktree and in a submodule, so `.is_dir()` read
    # those as having no history at all -- and the result had fewer keys than
    # the normal one, so `--summary` then died on KeyError: 'first_commit'.
    # Same keys either way now.
    if not (Path(root) / ".git").exists():
        return {**EMPTY, "project": root.name, "limit": limit}
    all_commits = commits(root)
    with_body = sum(1 for c in all_commits if c["body"])
    # Decided per repository: see classify().
    informative = bool(all_commits) and with_body / len(all_commits) <= 0.5

    scored = []
    for c in all_commits:
        verdict = classify(c, informative)
        if verdict:
            scored.append({**c, **verdict})
    # Strongest first, then most recent, because recent decisions are the ones
    # still binding the work.
    scored.sort(key=lambda c: (-c["score"], c["date"]), reverse=False)
    scored.sort(key=lambda c: -c["score"])
    return {
        "project": root.name,
        "is_git": True,
        "total_commits": len(all_commits),
        "commits_with_body": with_body,
        "body_informative": informative,
        "matched": len(scored),
        "limit": limit,
        "first_commit": all_commits[-1]["date"] if all_commits else None,
        "last_commit": all_commits[0]["date"] if all_commits else None,
        "candidates": scored[:limit],
        "deleted": deleted_paths(root),
    }


def summary(info):
    if not info.get("is_git"):
        return (f"{info['project']}: not a git repository (no .git here). "
                "There is no history to mine, so the ledger starts from now.")
    if not info["total_commits"]:
        return (f"{info['project']}: a git repository with no commits yet. "
                "Nothing to reconstruct -- this really is greenfield.")
    shown, matched = len(info["candidates"]), info.get("matched", 0)
    lines = [
        f"{info['project']}: {info['total_commits']} commits"
        + (f", {info['first_commit']} to {info['last_commit']}"
           if info["first_commit"] else ""),
        f"{info.get('commits_with_body', 0)} carry a message body; "
        + ("a body is treated as a signal here."
           if info.get("body_informative")
           else "most commits have one, so a body alone is not treated as a signal."),
        f"{matched} commit(s) carry evidence worth a record"
        + (f"; showing the strongest {shown}." if matched > shown else "."),
        "",
    ]
    for c in info["candidates"]:
        lines.append(f"  [{c['kind'].upper():3} {c['score']}] {c['date']}  "
                     f"{c['sha']}  {c['subject']}")
        for s in c["signals"]:
            lines.append(f"         - {s}")
        if c["body"]:
            for bl in c["body"].splitlines():
                lines.append(f"         | {bl}")
        lines.append("")
    if info["deleted"]:
        lines.append(f"{len(info['deleted'])} file(s) were added and later deleted "
                     "-- candidate abandoned routes:")
        for d in info["deleted"][:20]:
            lines.append(f"    {d['date']}  {d['path']}  ({d['sha']})")
        lines.append("")
    if matched > shown:
        lines.append(f"{matched - shown} weaker candidate(s) are not shown. They "
                     "remain in git history, which is not lost. Backfilling "
                     "every commit would produce a ledger nobody reads.")
        lines.append("")
    lines.append("Nothing was written. Every candidate needs the reasoning "
                 "confirmed before it becomes a record.")
    return "\n".join(lines)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = args[0] if args else "."
    limit = DEFAULT_LIMIT
    for a in sys.argv[1:]:
        if a.startswith("--limit="):
            try:
                limit = max(1, int(a.split("=", 1)[1]))
            except ValueError:
                print(f"ignoring {a}: not a number", file=sys.stderr)
    info = scan(root, limit)
    if "--summary" in sys.argv:
        print(summary(info))
    else:
        print(json.dumps(info, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
