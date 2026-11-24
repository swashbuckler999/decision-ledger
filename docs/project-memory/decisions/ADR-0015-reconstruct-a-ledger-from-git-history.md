---
id: ADR-0015
type: decision
title: Reconstruct a ledger from git history
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0009, ADR-0016, REJ-0006, REJ-0008]
tags: [adoption, backfill, cold-start]
---

# ADR-0015: Reconstruct a ledger from git history

## Discussion
The owner named three situations the skill must handle. The second was a
working project with no memory files at all: *"Properly extract whatever
happened till then, properly document them arrange them, and then structure it
properly, and then keep on maintaining."*

The skill had no path for it. The adoption scanner classified such a project
as `greenfield` or `readme-only`, the ledger started at ADR-0001, and the
`ledger-adopt` skill said so in its own closing step — that nothing was read
into records and backfilling was the highest-value thing the user could do
next. The work was acknowledged and then handed to the user.

Simulated on a sandbox project with nine commits carrying real reasoning —
Parquet chosen over CSV with measured load times, an LSTM reverted for
overfitting, a nightly retrain dropped because it corrupted a run, a broker API
pinned because the next version changes the tick schema. All of it stayed in
`git log`. The ledger was created as though the project had begun that morning.

Three of the 82 projects in the corpus are in exactly this state.

## Decision
A new skill, `ledger-backfill`, and a read-only script, `mine_history.py`,
that scores commits as evidence for records.

The adoption scanner now reports when a project has five or more commits and no
memory files: *"This project is NOT greenfield. Run the `ledger-backfill`
skill."*

The governing rule of the skill: **a reconstructed record may never state a
reason the evidence does not support.** Every record carries
`provenance: reconstructed`, the commit shas it came from, and a `confidence`
of `stated`, `inferred` or `unconfirmed`. Dates are the commit's, never today's.

## Reasoning
Mining is a script and not prose because the log is long, mostly mechanical,
and the judgement of which commits matter must not depend on how much of the
log fits in a context window. The same argument as ADR-0012.

Drafting is a skill and not a script because the reasoning in a commit message
is thin and a fabricated ADR is worse than none. The project already holds this
position about briefings — a confident briefing on a stale state file is worse
than admitting the gap — and it applies with more force here, because a
reconstructed record looks exactly like a witnessed one.

The ordering in the skill is deliberate: constraints, then briefing, then
journey, then records. The first three need no judgement about intent and are
cheap, so a session that ends early still leaves the project cold-start ready.
Records are slowest and easiest to get wrong, so they come last.

Rejections get their own step and an explicit script to read to the user,
because work that was *considered and not done* leaves no commit at all. The
miner can only find rejections that got far enough to be committed and then
undone. Everything else has to be asked for, and it is the highest-value
content in the ledger.

## Cost
A reconstruction is weaker than a record written at the time, and the ledger now
contains two tiers of record that look alike on the page and are only
distinguished by a frontmatter field. A reader who ignores `provenance` will
over-trust the backfilled ones.

Backfill is also a sitting of work. For a project with hundreds of commits it is
an afternoon, and an afternoon is enough to make people skip it.

## Re-evaluation trigger
If backfilled records are found being cited as settled fact without their
`confidence` being checked, the honesty markers are not working and belong in
the record body rather than the frontmatter.

## Conclusion & consequences
The three situations are now distinct: a fresh project gets the ledger, a
documented project gets adoption, and an undocumented working project gets
reconstruction before new work starts. The scanner tells the user which it is
rather than leaving them to notice.

## Diversions & Pivots

## User's own words
> Working Project with no such maintenance: Properly extract whatever happened
> till then, properly document them arrange them, and then structure it
> properly, and then keep on maintaining. Remember it should be always
> cold-start-ready for any other account to pick it up any point of time.
