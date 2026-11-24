---
id: ADR-0009
type: decision
title: Adopt what exists, own only the briefing
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0006, ADR-0008, CR-0002, REJ-0006]
tags: [adoption, schema]
---

# ADR-0009: Adopt what exists, own only the briefing

## Discussion
Given CR-0002, the question is which ledger files can point at an existing file
and which cannot. The tempting answer is "all of them, it is just a path" —
and that is wrong for exactly one of them.

## Decision
Two categories.

**Adoptable** — `changelog`, `journey`, `constraints`, and the three record
directories. Mapped onto whatever exists, appended to in the style already
there, never reordered, reformatted or renumbered.

**Owned by the ledger** — `briefing` and `index`. Always new files, even when
the project has a `STATUS.md` or an `INDEX.md`.

A `.ledger.json` carries the overrides and an `adopted` list naming which files
belong to someone else.

## Reasoning
The briefing is not adoptable because its *design* conflicts with what a
maintained status file is. The briefing is injected into every session, capped
at 150 lines, and rewritten as state changes. A maintained `STATUS.md` is
typically a status log: long, append-only in practice, valuable because it is
long. They share a name and nothing else.

Mapping one onto the other fails twice over: the hook would inject the first
160 lines of a 98 KB file into every session, probably mid-sentence; and the
`wrap-session` skill would then rewrite a file nobody wanted rewritten. The
second failure is the serious one, because it reintroduces precisely the risk
ADR-0008 closed.

So the briefing is created new and *points at* the existing status file. The
index is owned for the same reason in miniature: it is generated, and pointing
it at a hand-written index would mean overwriting one.

Why a config file rather than runtime detection: detection would make the
answer non-deterministic and surprising — the same project could resolve
differently as files appear. Why a config file rather than hand-written setup:
almost nobody writes one, so the `ledger-adopt` skill generates it after
showing the user a mapping to approve.

## Cost
A config file is one more thing that can be wrong. Mitigated by treating a
malformed config as absent rather than fatal — tested — so the worst case is
the default layout, not a broken session.

Adoption also means the ledger no longer knows that everything it reads is in
its own format. Appending "in the existing style" is a judgement the scripts
cannot make; only the skills can, and that is instruction-level.

## Re-evaluation trigger
If adopted changelogs come back visibly inconsistent in style, the append
format needs to be declared in the config rather than inferred by the model.

## Conclusion & consequences
`is_ledger_path()` now answers "is this file part of the ledger" from the
config, so an adopted root `CHANGELOG.md` correctly counts as a ledger edit and
does not trigger the unrecorded-work warning. Verified by test.

## Diversions & Pivots

## User's own words
> Think and get the best and correct solution.
