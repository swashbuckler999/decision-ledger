# Ledger record templates

These are the exact schemas. `scripts/new_record.py` writes them for you; this
file is the reference for what each section must contain.

Every record carries YAML frontmatter so the files stay machine-readable for
indexing and so status can be checked without parsing prose.

---

## 1. Decision — `decisions/ADR-NNNN-short-title.md`

```markdown
---
id: ADR-NNNN
type: decision
title: Short title
date: YYYY-MM-DD
status: accepted          # proposed | accepted | superseded
supersedes: []            # e.g. [ADR-0007]
superseded_by: null       # e.g. ADR-0019
related: []               # e.g. [REJ-0003, CR-0002]
tags: []
---

## Discussion
What problem triggered this, and what was on the table. Name the options that
were genuinely considered, not a strawman list.

## Decision
What was chosen. One or two sentences. Unambiguous.

## Reasoning
Why this option won. Constraints, numbers, benchmarks, business drivers.
Why each alternative lost — one line each is enough, but each must have one.

## Cost
What this gives up: the trade-off accepted, the debt taken on, the thing that
is now harder. A decision with no cost recorded is a decision not thought through.

## Re-evaluation trigger
The concrete, observable condition that would make this the wrong call.
Or: `No known trigger — treat as settled.`

## Conclusion & consequences
The rule that now applies going forward, and which files or interfaces it binds.

## Diversions & Pivots
*(Append-only. Empty at creation. Never edit entries above this line.)*

## User's own words
> Verbatim quote, if the user drove this. Otherwise: n/a
```

---

## 2. Rejection — `rejections/REJ-NNNN-short-title.md`

The most undervalued file in the system. Its whole purpose is to stop a future
session — human or agent — spending a week rediscovering why this does not work.

```markdown
---
id: REJ-NNNN
type: rejection
title: Short title
date: YYYY-MM-DD
status: rejected          # rejected | revisited
related: []
tags: []
---

## What was proposed
The idea, stated fairly and in its strongest form. If the record misrepresents
the idea, the next reader will dismiss the rejection and try it anyway.

## Discussion
The case made for it. What was attractive about it.

## Why it was rejected
The actual disqualifying reason. Cost, complexity, a benchmark, an edge case,
a constraint discovered. Be specific enough to be checkable.

## What was done instead
Pointer to the ADR that carries the chosen path, if there is one.

## Re-evaluation trigger
Under what future condition this should be reconsidered. Be concrete.
Or: `Do not revisit — the objection is structural.`

## User's own words
> Verbatim quote, if the user rejected it. Otherwise: n/a
```

---

## 3. Change request — `change-requests/CR-NNNN-short-title.md`

```markdown
---
id: CR-NNNN
type: change-request
title: Short title
date: YYYY-MM-DD
status: open              # open | accepted | done | declined
origin: user              # user | bug | external constraint | pivot
diverts_from: null        # ADR-NNNN or spec reference, if this changes direction
related: []
tags: []
---

## Request
What is being asked for, in the user's framing.

## Origin
Where it came from and what prompted it now.

## Discussion & reasoning
Why the change is being made, and what was weighed. If it reverses an earlier
decision, say which and link it.

## Scope impact
Which files, interfaces, timelines or assumptions change as a result.
Name the blast radius honestly, including what might break.

## Conclusion
What was agreed, and what the next concrete step is.

## User's own words
> Verbatim quote of the request. This one is rarely n/a.
```

---

## Writing notes

- Frontmatter `date` is the date the record was written, never backdated.
- `status` on a superseded ADR is changed in place; nothing else in it is.
- IDs are permanent. A record is never renumbered, renamed or deleted.
- If a record turns out to be wrong, do not edit it — write a new one that
  supersedes it and say what the earlier reasoning got wrong. The mistake and
  its correction are both part of the record.
