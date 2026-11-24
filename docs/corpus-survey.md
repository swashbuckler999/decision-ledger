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

## A third pass, simulating the three real situations

The adoption design was then tested by simulation rather than by scanning:
three sandbox projects with real git history — fresh, undocumented, documented
— with the actual scripts run against them. Two defects surfaced that two
corpus passes had not.

### An ADR directory the scanner could not see

Record filenames were matched by `^(ADR|REJ|CR|RFC|DEC)[-_]?(\d+)`, requiring a
letter prefix. `adr-tools`, the original and most widespread ADR tooling, writes
`0001-title.md` with no prefix. One project in the corpus uses exactly that,
with four records, and the scanner reported `numbered: false` and — because the
review note sat inside the `if numbered` branch — printed nothing at all.

Adoption there would have created a second decisions folder beside the first
and filed a new decision as `0001` next to the existing `0001`.

Both halves were wrong, and the silence was the worse half. A mapping the tool
cannot determine is acceptable; one it cannot determine and does not mention is
how the duplication it exists to prevent happens anyway. Review notes are now
emitted for every directory holding records, understood or not.

### Mining history: 98% is not a filter

A project with months of commits and no notes was being classified as
greenfield. The history miner built for it matched loosely, on the reasoning
that mining writes nothing so a false positive is cheap.

| Version | Commits flagged, of 4,380 |
|---|---|
| Loose filter | **4,273 (98%)** |
| Scored, threshold 2, capped | 1,327 (30%) |

The dominant signal was "has a message body", true of 4,238 commits — 97%. The
first explanation was that `Co-Authored-By` trailers were being counted as
reasoning. They were not: those bodies are genuine, substantive reasoning,
because these repositories were written under guidelines requiring it.

That is the finding worth keeping. **In this corpus a commit body carries no
information; in a typical repository it is the single best indicator that
reasoning was written down at the time.** A fixed weight cannot be right for
both, so the weight is now decided per repository from its own body rate.

Per-project worklists went from 100% in twenty-seven of thirty-eight
repositories to a median in single digits, capped at 40.

### A bug behind an empty result

Not one of the 82 projects has ever deleted a file. The function that looks for
deleted files — abandoned routes, the clearest evidence of work thrown away —
therefore returned an empty list on every real run, which was indistinguishable
from it working. A sandbox repository with one deletion showed it was broken:
`str.splitlines()` treats `\x1e` as a line boundary, so the sentinel in the git
format string was destroyed by the call parsing it.

The CRLF bug showed that git's own normalisation can hide a defect in review.
This is the quieter version: a code path that returns nothing across all
available real data is untested, not working.

## A fourth pass: what the corpus says about environments

The third pass simulated the three *situations* the owner named. This one asked
a different question — what environment has the plugin never run in — and the
corpus answered one of them directly.

**One project is a linked git worktree.** Its `.git` is a file, not a
directory, so every `is_dir()` test in the plugin read it as having no version
control at all. The survey had been reporting it that way too: **39 git
repositories under the old test, 40 under the new one.** The miscount was in
every earlier pass in this document.

That single project is worth more than its share, because Claude Code's own
desktop sessions run in worktrees. The environment the plugin is most likely to
be installed into was the one it handled worst: the scanner called the
repository unversioned, the history miner found none of its commits, and the
Stop hook could not write its de-duplication marker, so it repeated the same
reminder every turn.

The pattern is now familiar enough to state as a rule. Every defect this
project has shipped was found by running against something real — 82 projects,
a worktree, a repository with a deletion in it, a config pointing somewhere
unusual — and none by writing a fixture and reading the code against it. A
fixture tests the author's model of the world. The corpus tests the world.
