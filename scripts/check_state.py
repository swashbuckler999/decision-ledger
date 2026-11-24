"""Detect content dropped from the mutable state file with no copy elsewhere.

`00-PROJECT-STATE.md` is the only file in the ledger that gets rewritten, which
makes it the only place content can vanish silently. The rule is move-it-before-
you-remove-it; this script checks whether the rule was actually followed.

It compares the working copy against the last committed version, and for every
removed line asks: does this content still exist anywhere else in the ledger?
Lines that exist nowhere else are orphans.

Usage:
    python scripts/check_state.py            # report orphans
    python scripts/check_state.py --quiet    # exit code only

Exit codes: 0 nothing orphaned (or nothing to compare), 1 orphans found.

The matching is a heuristic and deliberately errs toward false positives: it is
better to ask about a line that was in fact preserved than to miss one that was
not. Rewording a line while keeping its meaning may flag it.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ledger as L  # noqa: E402

# Words too common to make a line distinctive.
STOPWORDS = {
    "that", "this", "with", "from", "have", "been", "were", "they", "them",
    "then", "than", "when", "what", "which", "will", "would", "could", "should",
    "about", "there", "their", "these", "those", "into", "only", "also", "some",
    "more", "most", "such", "here", "does", "done", "make", "made", "need",
    "needs", "still", "very", "just", "like", "each", "every", "both", "where",
}
MATCH_RATIO = 0.6
MIN_WORDS = 3


def content_words(line):
    out = set()
    for raw in line.lower().split():
        word = "".join(ch for ch in raw if ch.isalnum())
        if len(word) > 3 and word not in STOPWORDS:
            out.add(word)
    return out


def committed_version(path, cwd):
    """The last committed text of path, or None if unavailable."""
    try:
        rel = path.relative_to(cwd).as_posix()
    except ValueError:
        return None
    try:
        out = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=cwd,
                             capture_output=True, text=True, timeout=15)
    except Exception:
        return None
    return out.stdout if out.returncode == 0 else None


def ledger_corpus(ledger, exclude):
    """Every line of every other file in the ledger."""
    lines = []
    for path in sorted(ledger.rglob("*.md")):
        if path == exclude or "activity" in path.parts:
            continue
        try:
            lines.extend(path.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            continue
    return lines


def is_preserved(removed, corpus_sets):
    """True if some line elsewhere carries most of this line's content words."""
    words = content_words(removed)
    if len(words) < MIN_WORDS:
        return True  # too thin to judge; do not cry wolf
    for other in corpus_sets:
        if not other:
            continue
        overlap = len(words & other) / len(words)
        if overlap >= MATCH_RATIO:
            return True
    return False


def find_orphans(cwd=None):
    """Lines dropped from the state file that exist nowhere else in the ledger.

    Returns (orphans, reason_if_not_checked).
    """
    cwd = Path(cwd) if cwd else L.project_dir()
    ledger = cwd / L.LEDGER_DIRNAME
    state = ledger / L.STATE_FILE
    if not state.is_file():
        return [], "no state file"

    old = committed_version(state, cwd)
    if old is None:
        return [], "no committed version to compare against"

    current = state.read_text(encoding="utf-8", errors="replace").splitlines()
    current_set = {line.strip() for line in current}

    removed = [line.strip() for line in old.splitlines()
               if line.strip() and line.strip() not in current_set]
    if not removed:
        return [], None

    corpus_sets = [content_words(line) for line in ledger_corpus(ledger, state)]
    corpus_sets += [content_words(line) for line in current]

    return [line for line in removed if not is_preserved(line, corpus_sets)], None


def main():
    quiet = "--quiet" in sys.argv
    orphans, reason = find_orphans()

    if reason:
        if not quiet:
            print(f"not checked: {reason}")
        return 0
    if not orphans:
        if not quiet:
            print("No orphaned content. Everything removed from the state file "
                  "still exists elsewhere in the ledger.")
        return 0

    if not quiet:
        print(f"{len(orphans)} line(s) removed from {L.STATE_FILE} with no copy "
              "elsewhere in the ledger:\n")
        for line in orphans:
            print(f"  {line}")
        print("\nIf any of that still matters, write it somewhere append-only "
              "before it is lost:")
        print(f"  a constraint or access rule -> {L.CONSTRAINTS_FILE}")
        print("  a decision, rejection or scope change -> a numbered record")
        print(f"  narrative, or an open question worth keeping -> {L.JOURNEY_FILE}")
        print("\nThe previous version is still in git: "
              f"git show HEAD:{L.LEDGER_DIRNAME.as_posix()}/{L.STATE_FILE}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
