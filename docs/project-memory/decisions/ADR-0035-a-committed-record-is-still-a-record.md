---
id: ADR-0035
type: decision
title: A committed record is still a record
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0033, ADR-0034, REJ-0004]
tags: [stop-hook, regression, interaction, live-session]
---

# ADR-0035: A committed record is still a record

## Discussion
The fourth live session was meant to confirm the previous round of fixes. It
confirmed them and found a new defect, which the previous round had created.

ADR-0034 added a commit step to `wrap-session`, because a session had no way
to know whether committing was wanted. ADR-0033 made the Stop gate compare
against a session baseline, so it stops blaming pre-existing mess.

Together they produced this: the session recorded a decision, committed the
ledger as the skill now tells it to, and the gate then announced **"nothing
was written to the decision ledger"** — on the very turn a record had been
written *and* committed — listing the working tree's junk files as the
unrecorded work.

The gate decided whether anything had been recorded by looking for dirty
ledger files. Committing empties the dirty set. So the gate was reading the
absence of its own evidence as proof of the opposite, and the better the
session behaved, the more confidently it was wrong.

## Decision
A record counts if it is **dirty or committed since the session started.** The
baseline now stores the HEAD at session start alongside the dirty paths, and
the gate also checks what commits since then have touched.

## Reasoning
Neither contributing change was wrong. The commit step is right; the baseline
is right. The defect is in the join, and it existed only after both landed —
which is exactly the kind of fault that no test of either one would catch,
because each is correct in isolation.

Checking commits rather than removing the commit step keeps the property that
matters: committing the ledger is the only thing that makes it durable, since
`00-PROJECT-STATE.md` is rewritten in place and until the commit the previous
version exists only in git and the new one only in the working tree. A design
where being careful trips the alarm teaches people to be less careful.

The mirror case needed a test of its own: committing must not become a way to
silence the gate. Code committed with no record still warns, because the
check is for *recording* paths specifically, not for the act of committing.

## Cost
One extra `git diff --name-only` per Stop hook, bounded by the commits made
during a single session.

A record committed and then reverted within the same session still counts as
recorded. Vanishingly rare, and the failure is one spurious silence.

## Re-evaluation trigger
If the gate is found silent on a session that genuinely recorded nothing,
check whether an unrelated commit touched a ledger path — the check is by
path, not by content.

## Conclusion & consequences
Five checks pin it, including the mirror: a committed record is quiet, and
committed code with no record still warns.

The lesson is about the shape of the remaining risk. Three rounds of live
testing found defects in isolated pieces; this one found a defect produced by
**two correct fixes meeting**. That failure mode does not diminish as the
pieces improve, and no amount of testing the pieces separately will surface
it. It is the strongest argument yet that the live session is not a box to
tick before publishing but the only instrument that sees the plugin whole.

## Diversions & Pivots

## User's own words
> Fix those five and run the fourth session
