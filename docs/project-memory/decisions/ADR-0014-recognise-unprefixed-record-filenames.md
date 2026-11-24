---
id: ADR-0014
type: decision
title: Recognise unprefixed record filenames
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0008, ADR-0009, ADR-0013]
tags: [adoption, data-loss, simulation]
---

# ADR-0014: Recognise unprefixed record filenames

## Discussion
A simulation of the three adoption situations the owner named — fresh project,
working project with no notes, working project with notes — was run against
sandbox copies rather than real projects. The third case was given a
`docs/adr/` directory holding `0001-single-threaded-router.md` and
`0002-sqlite-fills.md`.

The scanner saw the directory, counted two files, and reported
`numbered: false`. Because the review note lived inside the `if numbered`
branch, nothing was printed at all. The proposed config pointed `decisions` at
the default `docs/project-memory/decisions`.

The cause was a single regex: `^(ADR|REJ|CR|RFC|DEC)[-_]?(\d+)`, which requires
a letter prefix. `adr-tools` — Nygard's original tooling and by far the most
widespread ADR convention — writes `0001-title.md` with no prefix.

Checked against the corpus: one real project, **Trading Tool V2**, has exactly
this layout with four records. Installing the ledger there today would have
created a second decisions folder beside the existing one and said nothing
about it.

## Decision
Three changes.

1. A record filename matches with or without a letter prefix. A bare number
   counts only when it is below `YEAR_FLOOR = 1900`.
2. `next_id` counts unprefixed records, so an adopted folder continues at the
   next free number instead of restarting at 0001.
3. A review note is emitted for **every** directory holding files, whether or
   not its numbering is understood. The ledger's own directory is excluded.

New records in an adopted folder also follow that folder's filename style —
`0003-title.md`, not `ADR-0003-title.md` — while the `id:` inside the record
stays `ADR-0003` so the index and cross-references are unaffected. The style
applies only to a kind whose folder was adopted; the ledger's own folders keep
their prefixes.

## Reasoning
The year floor is the part that needs defending. Accepting any leading digits
would make `2026-11-22-notes.md` read as record 2026 and push the next id to
2027. No project has 1,900 decision records; many have filenames that begin
with a year. The asymmetry is what makes the cutoff safe.

Numbering had to change with the regex. Without it the scanner would adopt the
folder correctly and then file a new decision as `ADR-0001` beside their
`0001-module-boundaries.md`: two different decisions under one number, which is
worse than the duplicate folder it replaces.

The unconditional review note is the most important of the three, and the
original defect was not really the regex — it was the silence. A mapping the
tool cannot work out is fine; a mapping it cannot work out and does not mention
is how the thing it was built to prevent happens anyway.

Filename style follows the same principle already accepted for changelog entry
format in ADR-0009: copy the shape that is already there. Scoping it to adopted
folders only was a correction made during the work, after the first
implementation restyled the ledger's own rejections as `0001-...`.

## Cost
`YEAR_FLOOR` is a heuristic and will be wrong for a project that numbers
records above 1899, which is to say never, and for one that numbers them by
year, which the floor deliberately rejects. Two naming conventions can now
coexist in one repository — bare in an adopted folder, prefixed in ours —
which reads as inconsistent until you know why.

## Re-evaluation trigger
If a project is found that numbers records by year on purpose, or one whose
adopted folder mixes kinds so that a bare filename is ambiguous, revisit the
filename rule rather than widening the floor.

## Conclusion & consequences
Adopting a project's existing decisions directory now works for the dominant
convention, continues its numbering, and matches its filenames. Twenty-two
checks pin it, including that their existing files are byte-identical
afterwards and that the ledger's own folders are unaffected.

## Diversions & Pivots

### 2026-11-24 — the first implementation restyled our own records
Scoping the filename convention globally renamed the ledger's own rejection to
`0001-multi-threaded-socket-writer.md`. Caught in the same simulation run and
scoped to adopted kinds. Matching someone else's convention is for fitting into
their directory, not for restyling ours.

## User's own words
> Working Project with already maintained documents almost related to the
> Skill: Properly structure and segregate and maintain, and keep on
> maintaining.
