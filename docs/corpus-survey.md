# What real projects actually do

The adoption design is not guesswork. It was built against a corpus of **82
real projects** on one developer's machine, scanned read-only with
`scripts/scan_project.py`.

Project names are deliberately omitted — they are private. Only aggregates
appear here.

## How many projects need adoption at all

| Verdict | Projects |
|---|---|
| Greenfield — no memory files | 40 |
| **Adopt — already keeps notes** | **37** |
| README only | 5 |

**45% already keep notes.** Adoption is not an edge case for mature
repositories; it is nearly half of everything. A greenfield-only design would
have been wrong more often than right.

## What they keep

| File | Projects |
|---|---|
| README | 40 |
| PLAN | 29 |
| STATUS | 28 |
| CHANGELOG | 26 |
| JOURNEY / devlog | 10 |
| DECISIONS | 7 |
| Decision *directory* | 2 |

Changelogs and status files are common; structured decision records are rare.
That is the gap this plugin fills, and it is why adoption adds `decisions/`,
`rejections/` and `constraints` while mapping onto the rest.

## Changelog order — the finding that changed a default

| Order | Changelogs |
|---|---|
| **Newest-first** | **20** |
| Oldest-first | 1 |
| Undetermined | 5 |

Twenty to one. The plugin's original default was *oldest-first*, which would
have filed every new entry under the oldest heading in nearly every project
that has a changelog. The default now follows the evidence.

### How the order is established

| Source | Changelogs |
|---|---|
| Inferred from date positions | 10 |
| Read from git history | 7 |
| Declared in the file's own words | 4 |
| Undetermined — a human must say | 5 |

Three detection methods, in descending priority, because no single one covers
the corpus:

1. **Declared.** Four files simply say "Newest first." near the top. Nothing
   beats being told.
2. **Inferred from date positions.** Comparing where the newest and oldest
   dates sit. Comparing merely the *first and last* date — the obvious
   approach, and the first one tried — reported 8 files as undetermined that
   were not: short changelogs often share a single date across entries.
3. **Git history.** For a repository, compare the file against an earlier
   revision and see whether added lines land near the top or the bottom. This
   is the strongest signal and resolved 7 files nothing else could.

The remaining 5 are genuinely undecidable — one or two entries, or version
headings with no dates. The scanner refuses to guess, writes the corpus
default, marks it `unconfirmed`, and tells the skill to ask.

## Entry format

All 26 changelogs use `##` headings for entries; none uses bullets. Many nest
`### Added` / `### Fixed` beneath. The ledger's original one-line bullet would
have been visibly foreign in every one of them, so the entry format is copied
from the file's own style.

Date formats vary more than expected: `## 2026-11-22 - title`,
`## 2026-09-27 (later)`, `## 2026-11-04 — title` with an em dash, bare
`## 2026-10-06`, and `## v2 (Current — June 2026)` with no date at all.

## Status files — why the briefing is never adopted

| Size | Projects |
|---|---|
| Under 8 KB | 17 |
| Over 8 KB | 11 |
| Largest | 98 KB |

Eleven status files are far too large to inject into a session, and the
largest is a 98 KB running log. Even the small ones are *logs*, not briefings.
Mapping the ledger's briefing onto one would inject a fragment into every
session and then invite rewriting a file nobody wanted rewritten, so the
briefing is always a new file that points at the existing one.

## Bugs this survey found

Running against real data found three defects that fixtures had not:

1. **A Windows decoding crash.** `subprocess(text=True)` decodes with the ANSI
   code page, so any non-ASCII byte in git output raised `UnicodeDecodeError`
   and silently dropped two projects from the survey. The same latent bug was
   present in two already-shipped scripts.
2. **A regex that could never match.** A stray control byte had replaced a word
   boundary, so version-style headings were never recognised.
3. **Too-strict entry detection.** Requiring two dated headings missed every
   single-entry changelog, of which the corpus has several.

None of these would have surfaced from a handful of hand-written fixtures.

## A second pass found what the first one hid

Re-running the corpus after those fixes confirmed the gains — 11 projects read
correctly that had not before, no errors — and exposed a separate defect the
first pass had masked.

File-name matching treated `notes` and `log` as suffixes for the journey
role, which caught four files that are not journeys: an API reference, a
platform reference, a set of research notes, and a log for one feature. Four
of ten journey matches were wrong, and journey is an *adopted* role, so each
was a file the ledger would have written into.

Match tiers are now set by consequence. Roles that get adopted match strictly;
roles that only inform a review note may match loosely. All four false
positives dropped; the one genuine session journal among them was kept.

The general lesson: the first pass validated the scanner against the question
it was built to answer and missed a defect elsewhere in the same scan.
Re-running a corpus after a fix is not ceremony.
