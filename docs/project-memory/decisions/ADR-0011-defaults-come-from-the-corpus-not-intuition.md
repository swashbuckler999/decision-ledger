---
id: ADR-0011
type: decision
title: Defaults come from the corpus, not intuition
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0010, ADR-0012]
tags: [evidence, adoption]
---

# ADR-0011: Defaults come from the corpus, not intuition

## Discussion
The owner pointed out that the machine holds 82 real projects, and that they
are a corpus to design against rather than a single test case. Scanning them
read-only settled several questions that had been answered by intuition.

The headline result: of 26 changelogs, **20 are newest-first and 1 is
oldest-first**. The plugin's default was oldest-first.

## Decision
`DEFAULT_ORDER = "newest-first"`. This repository declares `oldest-first` in
its own `.ledger.json`, because its changelog was written before the flip and
should stay internally consistent rather than growing from both ends.

Design decisions that rest on a convention now cite the corpus. Where the
corpus is silent, that is said rather than papered over.

## Reasoning
The old default was not a neutral choice. Appending to the bottom of a
newest-first changelog files each entry under the oldest heading — the wrong
place, not merely an untidy one. Applied across this corpus it would have been
wrong for 20 of 21 determinable cases.

Three further intuitions failed against the data and were corrected:

- The one-line bullet entry format: **0 of 26** changelogs use bullets; all 26
  use `##` headings. The format is now copied from the file.
- Adoption as an edge case: **37 of 82** projects already keep notes. It is
  nearly half, not a corner.
- Status files as briefings: 11 of 28 exceed 8 KB, the largest 98 KB. None is
  a briefing. This confirmed ADR-0009 rather than overturning it.

Full aggregates in `docs/corpus-survey.md`.

## Cost
A default derived from one developer's 82 projects is a default derived from
one developer. The sample is real but not representative of everyone, and the
corpus is homogeneous — one author, one domain, similar tooling. Another user
may find the opposite convention.

Mitigated by the fact that nothing relies on the default when a project is
adopted: detection sets the order explicitly, and the default only governs
greenfield projects, where no convention exists yet to violate.

## Re-evaluation trigger
If users outside this corpus report that new greenfield changelogs come out in
the wrong order, the default is parochial and should become a first-run
question instead.

## Conclusion & consequences
Two tests broke when the default flipped, both because they had encoded the
old one. That is the tests working. Both now pin their order explicitly, and a
third asserts the default.

## Diversions & Pivots

## User's own words
> In fact I got a great idea - you have 82 test cases under "[local corpus
> directory — path redacted]", you can simulate/test/check on all of them and
> design Skills accordingly. These all are your test cases to learn from!!!!

The directory name is redacted because it is a path on the owner's own machine;
the quote is otherwise verbatim. See REJ-0007 for why the corpus is described
and never named.
