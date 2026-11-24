"""Allocate and scaffold a new ledger record.

Usage:  python scripts/new_record.py <adr|rej|cr> "short title"

Prints the created path. Exits 1 on bad input so a caller can tell the
difference between "created" and "nothing happened".
"""

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
    if len(sys.argv) < 3:
        print(__doc__.strip(), file=sys.stderr)
        return 1
    kind = sys.argv[1].lower()
    if kind not in BODIES:
        print(f"unknown record kind {kind!r}: expected adr, rej or cr", file=sys.stderr)
        return 1
    title = " ".join(sys.argv[2:]).strip()
    if not title:
        print("a title is required", file=sys.stderr)
        return 1

    folder = L.ledger_dir() / L.SUBDIRS[kind]
    folder.mkdir(parents=True, exist_ok=True)

    num = L.next_id(kind)
    rid = f"{L.PREFIX[kind]}-{num:04d}"
    path = folder / f"{rid}-{L.slugify(title)}.md"
    if path.exists():
        print(f"refusing to overwrite existing record {path}", file=sys.stderr)
        return 1

    path.write_text(
        BODIES[kind].format(rid=rid, title=title, date=L.today()),
        encoding="utf-8",
        newline="\n",
    )

    L.append_line(
        L.ledger_dir() / L.CHANGELOG_FILE,
        f"- {L.today()} **{rid}** {title} - `{path.relative_to(L.project_dir())}`",
    )
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
