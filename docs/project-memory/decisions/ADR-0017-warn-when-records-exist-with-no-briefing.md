---
id: ADR-0017
type: decision
title: Warn when records exist with no briefing
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0009, ADR-0015]
tags: [cold-start, hooks]
---

# ADR-0017: Warn when records exist with no briefing

## Discussion
The fresh-project simulation wrote two records into an empty project, ran the
Stop gate, and got silence. Correct by the gate's own logic — it warns when
code changed and the ledger did not, and here the only changes *were* ledger
files — but the project had no `00-PROJECT-STATE.md` at all.

That is the one file the cold-start skill reads first and the one the owner's
requirement rests on: *"it should be always cold-start-ready for any other
account to pick it up any point of time."* A project can therefore fill up with
records, trip nothing, and still fail the only promise this plugin makes.

A fresh project is where this is most likely, because there is no existing
briefing to inherit and nothing yet feels worth summarising.

## Decision
A third independent Stop-hook warning: records exist and the configured
briefing file does not. It names the record count, says why the briefing
matters, and is de-duplicated on that count so it fires once per new record
rather than once per turn.

It stays silent when no records exist yet — nothing to brief — and when the
briefing is present.

## Reasoning
It has to be a separate check, for the same reason the orphan warning is
separate: the existing two cannot see it. Writing records *is* touching the
ledger, so the unrecorded-change nag is satisfied, and the orphan detector
compares a briefing against its committed version, which needs the file to
exist. The gap sits precisely between them.

Keyed on the record count rather than a content hash so that each new record
re-raises it once. A missing briefing is not a one-time notice; it gets worse
with every record added.

A warning rather than a block, consistent with the rest of the gate. Blocking a
turn because a file is missing trains people to uninstall the plugin, and
`LEDGER_STRICT=1` is there for anyone who wants it enforced.

## Cost
One more thing the gate can say, and a project deliberately using records
without a briefing will be nagged once per record. No way to silence it short
of writing the file or setting the briefing path to something that exists.

## Re-evaluation trigger
If users report this firing on projects where a briefing is genuinely not
wanted, add an opt-out to `.ledger.json` rather than removing the check.

## Conclusion & consequences
The cold-start entry point can no longer be silently absent. Four checks pin
it, including that it goes quiet once the briefing exists.

## Diversions & Pivots

## User's own words
> Remember it should be always cold-start-ready for any other account to pick
> it up any point of time.
