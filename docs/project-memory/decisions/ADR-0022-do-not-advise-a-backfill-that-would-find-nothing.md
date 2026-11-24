---
id: ADR-0022
type: decision
title: Do not advise a backfill that would find nothing
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0015, ADR-0016, ADR-0018, REJ-0004]
tags: [backfill, noise, corpus, false-positive]
---

# ADR-0022: Do not advise a backfill that would find nothing

## Discussion
A fourth read-only pass over all 82 corpus projects put four of them on the
backfill worklist. Two of those four should not have been there.

**The plugin's own repository was one.** It has a full ledger — 21 decisions, a
briefing, a `.ledger.json` — and the scanner told it:

> No memory files, but 20 commits exist and 2 of them carry evidence worth a
> record. This project is NOT greenfield. Run the `ledger-backfill` skill
> before starting new work.

The cause is a correct earlier fix with an unforeseen reach. ADR-0014 excluded
the ledger's own directory from role detection, so an installed project stops
being warned about its own files. That left `info["files"]` empty, which is
exactly the shape the ADR-0015 check reads as "no memory files". So **every
scan of every real installation** advised reconstructing a ledger that already
existed, and following that advice would duplicate records.

The second was a project with five commits and **zero** scoring as evidence.
The message still said `NOT greenfield. Run the ledger-backfill skill`,
promising reconstruction from a history the miner had already judged empty.

## Decision
Two guards on that one review note.

**Installed projects are skipped.** `installed` is true when the project has a
`.ledger.json`, or when any directory the ledger owns already holds files.
Checked on the records rather than the config alone, because a project can have
the directory without ever running the adopt skill.

**Zero evidence changes the advice, not the diagnosis.** The project is still
told it is not greenfield — that part is true and worth knowing. What changes is
what to do: the backfill would reconstruct almost nothing, so start the ledger
now and ask the owner directly for what they tried and dropped.

## Reasoning
The framing matters more than the suppression. Dropping the note entirely when
there is no evidence would be the easy fix and the wrong one: a project with
eight months of terse commits genuinely is not greenfield, and the reasoning
genuinely is lost. The honest message says both halves — *this is not a new
project, and the history cannot give you its reasoning back, so the only
remaining source is the person.*

That redirect is also the most valuable instruction in the skill. Work that was
considered and not done leaves no commit at all, so where mining returns
nothing, asking is not a fallback — it is the entire available method.

On the installed-project bug: this is the second time a correct exclusion has
had a reach nobody traced. ADR-0014 excluded our own directory from one check;
the consequence landed in a different check that happened to read the same
field. The lesson is not "be careful" — it is that a field meaning "memory
files found" and a field meaning "this project has no memory" were being
conflated, and only one of them was ever true.

## Cost
`installed` is a heuristic on the presence of files. A project that created the
directories and never wrote a record still reads as installed and will not be
offered a backfill it might genuinely want. That is the right direction to be
wrong in: the backfill is one command away and the advice would have been
wrong far more often than right.

## Re-evaluation trigger
If users with a half-set-up ledger report never being told about backfill,
narrow `installed` to require at least one record rather than any file.

## Conclusion & consequences
Of the four projects flagged in the corpus pass, two were false and are now
silent; one of those was this repository, which means the defect would have
greeted every real user on their first scan. Five checks pin it, including that
a `.ledger.json` with no records is enough to count as installed.

## Diversions & Pivots

## User's own words
> Also do deep analysis of any other edge cases which we might have missed.
