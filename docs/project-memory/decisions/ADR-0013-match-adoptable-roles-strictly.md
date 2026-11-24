---
id: ADR-0013
type: decision
title: Match adoptable roles strictly, loose roles loosely
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0009, ADR-0011, ADR-0012]
tags: [adoption, data-loss, evidence]
---

# ADR-0013: Match adoptable roles strictly, loose roles loosely

## Discussion
A second survey pass with the corrected scanner was run at the owner's
suggestion, while the previous work was under review. It confirmed the
improvements — 11 projects now read correctly that did not before, zero
errors — and then found a defect the first pass had hidden.

File-name classification matched `notes` and `log` as *suffixes* for the
journey role. Across the corpus that caught:

- `docs/API_NOTES.md` — an API reference
- `docs/PLATFORM_NOTES.md` — platform reference
- `docs/02-research-notes.md` — research notes
- `VIDEO_DOWNLOAD_research_log.md` — a log for one feature

Four of ten journey matches were wrong. Journey is an **adopted** role, so
each of those is a file the ledger would have begun appending session
narrative into. Appending to an API reference is not data loss in the strict
sense, but it damages a document someone maintains, which is the same promise
broken.

## Decision
Two match tiers per role.

- **strong** — may match as the whole stem, a prefix, or a suffix
- **exact** — must be the entire stem

Ambiguous words move to `exact`: `log`, `notes`, `history`, `state`,
`current`, `progress`, `todo`, `backlog`, `adr`, `caveats`, `limits`,
`environment`. Unambiguous ones stay `strong`: `journey`, `changelog`,
`devlog`, `session-log`, `constraints`, `plan`.

Exact matches are checked before loose ones, and a leading sequence number is
stripped first, so `02-research-notes` is judged as `research-notes`.

## Reasoning
The cost of a false positive is not symmetric across roles. A wrong `status`
or `plan` match only produces a misleading line in a review note, because
neither is adopted. A wrong `changelog`, `journey` or `constraints` match
attaches the ledger to a file it will then write into.

So the tiers are set by consequence, not by how confident the pattern feels.
Loose matching is fine where being wrong is cheap.

Why not drop `notes` and `log` entirely: `NOTES.md` as a whole file genuinely
is a project journal in some repositories, and the exact tier keeps that
without catching everything ending in `-notes`.

Verified against the corpus: all four false positives dropped, the one true
positive among them — `SESSION_LOG.md`, a real session journal — retained.
Changelog matching was unaffected at 26 of 26, all literally named
`CHANGELOG.md`.

## Cost
A project whose journey is called something unanticipated, say
`ENGINEERING-DIARY-2026.md`, now goes undetected and is treated as greenfield.
That is the safe failure: the ledger creates its own file and leaves theirs
alone, rather than writing into a document it guessed at.

## Re-evaluation trigger
If adoption reports keep missing a journey that exists under a name not in the
strong list, add that name — do not loosen the matching rule.

## Conclusion & consequences
Seventeen tests pin the classifier, and every "should not match" case in them
is a real filename from the survey that the first implementation got wrong.

A broader point this makes concrete: the first pass validated the scanner
against the question it was built to answer, changelog order, and missed a
defect in a different part of the same scan. Re-running a corpus after a fix
is not ceremony — it found this.

## Diversions & Pivots

## User's own words
> Meanwhile do another pass through all the projects with newly and corrected
> skill version.
