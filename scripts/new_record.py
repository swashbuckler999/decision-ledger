"""Allocate and scaffold a new ledger record.

Usage:  python <plugin>/scripts/new_record.py <adr|rej|cr> "short title"

Prints the created path. Exits 1 on bad input so a caller can tell the
difference between "created" and "nothing happened".
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ledger as L  # noqa: E402

ADR = """---
id: {rid}
type: decision
title: {title}
date: {date}
status: accepted
supersedes: []
superseded_by: null
related: []
tags: []
---

# {rid}: {title}

## Discussion
<!-- The problem, and the options genuinely on the table. -->

## Decision
<!-- What was chosen. One or two unambiguous sentences. -->

## Reasoning
<!-- Why this won. Why each alternative lost - one line each, but each gets one. -->

## Cost
<!-- What this gives up: the trade-off, the debt, the thing now harder. -->

## Re-evaluation trigger
<!-- The observable condition that would make this the wrong call.
     Or: No known trigger - treat as settled. -->

## Conclusion & consequences
<!-- The rule that now applies, and what it binds. -->

## Diversions & Pivots
<!-- Append-only. Empty at creation. Never edit entries above this line. -->

## User's own words
<!-- Verbatim quote if the user drove this, otherwise n/a. -->
"""

REJ = """---
id: {rid}
type: rejection
title: {title}
date: {date}
status: rejected
related: []
tags: []
---

# {rid}: {title}

## What was proposed
<!-- The idea in its strongest form. Misrepresent it and the next reader
     will dismiss this record and try it anyway. -->

## Discussion
<!-- The case made for it. What was attractive. -->

## Why it was rejected
<!-- The disqualifying reason. Specific enough to be checkable. -->

## What was done instead
<!-- Pointer to the ADR carrying the chosen path, if any. -->

## Re-evaluation trigger
<!-- Concrete condition for reconsidering.
     Or: Do not revisit - the objection is structural. -->

## User's own words
<!-- Verbatim quote if the user rejected it, otherwise n/a. -->
"""

CR = """---
id: {rid}
type: change-request
title: {title}
date: {date}
status: open
origin: user
diverts_from: null
related: []
tags: []
---

# {rid}: {title}

## Request
<!-- What is being asked for, in the user's framing. -->

## Origin
<!-- Where it came from and what prompted it now. -->

## Discussion & reasoning
<!-- Why the change is being made and what was weighed.
     If it reverses an earlier decision, link it. -->

## Scope impact
<!-- Files, interfaces, timelines, assumptions. The blast radius, honestly,
     including what might break. -->

## Conclusion
<!-- What was agreed and the next concrete step. -->

## User's own words
<!-- Verbatim quote of the request. Rarely n/a. -->
"""

BODIES = {"adr": ADR, "rej": REJ, "cr": CR}


def main():
    # Pin the project before anything resolves a path from cwd.
    argv = L.take_project_flag(sys.argv)
    if len(argv) < 3:
        print(__doc__.strip(), file=sys.stderr)
        return 1
    kind = argv[1].lower()
    if kind not in BODIES:
        print(f"unknown record kind {kind!r}: expected adr, rej or cr", file=sys.stderr)
        return 1
    title = " ".join(argv[2:]).strip()
    if not title:
        print("a title is required", file=sys.stderr)
        return 1

    folder = L.path_for(L.KIND_KEY[kind])
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        # exist_ok=True still raises when the path exists as a FILE, which it
        # does if someone keeps `decisions` as a notes file, or a config points
        # a record kind at one. A traceback here reads as a broken tool.
        print(f"cannot use {folder} as a {kind} directory: {exc.strerror or exc}",
              file=sys.stderr)
        return 1

    slug = L.slugify(title)
    bare = L.record_name_style(kind) == "bare"

    # Claiming the id is a loop, not a read-then-write. Two sessions recording
    # at the same moment both computed the same next id and both wrote: either
    # the same filename, where one silently replaced the other, or two
    # filenames under one number. O_EXCL makes the filesystem pick the winner,
    # and the loser re-reads and takes the next free number.
    rid = path = None
    for _attempt in range(8):
        num = L.next_id(kind)
        # The id inside the record stays ADR-0003 so the index and
        # cross-references are stable; only the filename follows the folder's
        # own convention. A project using adr-tools has 0001-foo.md, and
        # dropping ADR-0003-foo.md beside it is the same visible foreignness
        # the changelog format avoids.
        rid = f"{L.PREFIX[kind]}-{num:04d}"
        candidate = folder / f"{(f'{num:04d}' if bare else rid)}-{slug}.md"
        try:
            fd = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue  # someone got here first; take the next number
        except OSError as exc:
            print(f"cannot create {candidate}: {exc.strerror or exc}", file=sys.stderr)
            return 1
        os.close(fd)
        # A different title can still have claimed this number between the scan
        # and the create, which would put two records under one id.
        clash = [p for p in L.records(kind)
                 if p != candidate and L.record_number(p.stem, L.PREFIX[kind]) == num]
        if clash:
            candidate.unlink()
            continue
        path = candidate
        break
    else:
        print(f"could not allocate a free {kind} id after 8 attempts",
              file=sys.stderr)
        return 1

    path.write_text(
        BODIES[kind].format(rid=rid, title=title, date=L.today()),
        encoding="utf-8",
        newline="\n",
    )

    L.add_changelog_entry(
        L.changelog_entry(
            date=L.today(), id=rid, title=title,
            path=path.relative_to(L.project_dir()).as_posix(),
        )
    )
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
