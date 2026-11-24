---
id: ADR-0030
type: decision
title: Test skill selection against the advertised text
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0003, ADR-0026, ADR-0027]
tags: [skills, selection, testing, self-review]
---

# ADR-0030: Test skill selection against the advertised text

## Discussion
One claim had resisted every form of testing: **is a skill ever chosen?** A
skill whose `when_to_use` does not fire is invisible — it ships, it validates,
it is never invoked, and nothing reports a problem. No script can detect that,
because selection is a model judgement.

But it is a judgement made from exactly one input: the `name`, `description`
and `when_to_use` the harness advertises, roughly 658 tokens of it. That makes
it simulable. Give a model **only** that text plus a user message, with no
other context, and ask which skill it would invoke. That is the real decision,
reproduced.

The author cannot run this test on their own skills. The whole question is
whether the text works for a reader who did not write it, and this session
wrote it.

So it was run in a fresh context, on ten messages: five that should each fire a
different skill, and five ordinary coding messages that should fire nothing.

**All ten were classified correctly. No false positives on the four plain
coding requests.**

The value was in the review that came back with it. Three genuine overlaps,
none of which were visible from the inside:

- **"hand off" appeared in three skills at once** — `decision-ledger`,
  `wrap-session` and `cold-start` all claimed it. A real tie.
- **`ledger-adopt` and `ledger-backfill` both said "installing the ledger into
  a project"**, with nothing saying which runs first on a project that is both.
  `ledger-backfill` resolved it by citing *"when the adoption scanner reports
  NOT greenfield"* — a tool output the model cannot see when it is choosing.
- **"when the user pushes back on something"** would fire on any correction at
  all, including *"use single quotes"*.

Two more: `wrap-session`'s *"when a long session is about to be compacted"* is
a condition the model cannot observe, and the sign-off list had no casual forms
— *"I'm off"* matched nothing and was inferred.

## Decision
Rewrite the five `when_to_use` fields to state boundaries explicitly, and
re-run the simulation to check the rewrite.

Each skill now says what it is **not** for, and names the skill that is:
one record versus a whole session, arriving versus leaving, notes-already-kept
versus history-with-no-notes, with the sequencing stated in both.

## Reasoning
Saying what a skill is *not* for is what fixed the overlaps. A description
listing only its own triggers invites every neighbouring case, because nothing
contradicts it — three skills could each honestly claim "hand off".

Re-running the simulation after the rewrite was not a formality, and this is
the part worth remembering. **The rewrite introduced a worse bug than the ones
it fixed.** Adding *"if the project has no ledger yet, use ledger-adopt or
ledger-backfill first"* to `decision-ledger` was correct for a project with
history and wrong for a new one: adopt requires existing notes, backfill
requires existing commits, and a brand-new repository has neither. The second
run caught it immediately — a decision in a fresh project now selected nothing,
at low confidence, with the model noting there was no bootstrap path.

A greenfield project is the simplest case this plugin has, and the fix for an
overlap had quietly closed the door on it.

## Cost
The simulation is not the real thing. A model choosing in a long session with a
codebase in context may behave differently from one given the text alone, and
subagents know they are being asked to classify. It tests whether the
descriptions **discriminate**, which is the part that was unexamined; it does
not prove the harness offers the skill at the right moment.

The descriptions are now longer, and some of the added words exist only to
prevent a sibling from matching.

## Re-evaluation trigger
If a real session is ever observed invoking the wrong skill, or none, add that
message to the scenario list and re-run before changing anything.

## Conclusion & consequences
Three rounds, twenty-two scenarios, each round's traps written from the last
round's findings. The final round put all four traps together — a trivial style
correction that must *not* fire, a future handover that is not a session
ending, a project that is both adoptable and backfillable, and a decision in an
empty repository — and all eight messages were classified correctly, the
greenfield decision now at high confidence where the previous round had it at
none.

The lesson generalises past this project: **a description written by the person
who built the thing cannot be reviewed by them.** The overlaps were obvious in
the report and invisible in the writing, and the only reason they surfaced is
that something with no memory of writing them was asked to use them.

## Diversions & Pivots

### 2026-11-25 — the first fix broke the greenfield case
Resolving the overlap sent new projects to two skills that both refuse them.
Caught by re-running the simulation rather than by review, and fixed by saying
plainly that `decision-ledger` creates the ledger when there is none.

## User's own words
> Can't it be simulate?
