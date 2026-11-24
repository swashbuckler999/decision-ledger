---
id: ADR-0027
type: decision
title: Replay whole sessions, not single hooks
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0026, ADR-0028, ADR-0016]
tags: [testing, simulation, method]
---

# ADR-0027: Replay whole sessions, not single hooks

## Discussion
A live session could not be run: the CLI in this environment is routed to a
model gateway whose key is rejected (ADR-0026). The owner asked whether a
simulated one was possible instead.

It is, and the gap it fills turned out to be larger than expected. Every test
in this project drives **one hook, once, against a project in a state the test
itself constructed.** A real session is a state machine: the Stop gate's answer
depends on what the PostToolUse hook did three turns earlier, on whether a
record has been written since, and on what git has seen committed. None of
those transitions are reachable one hook at a time, because the condition that
produces them is created by an *earlier turn*.

## Decision
`tests/simulate_session.py`. It builds a throwaway project and plays twelve
turns of a plausible session through the hooks in order: a cold start, a
decision-shaped prompt, an ordinary question, an edit, a session ending with
nothing recorded, the same ending repeated, a record being written, the ending
again, compaction, a resume, a line dropped from the briefing, and finally a
project whose briefing has been deleted.

It asserts what the hooks should say at each point, needs no model and no API
key, and takes `--plugin-root` so it can run against the working tree or
against an installed copy.

## Reasoning
The sequence is the product. Any of those twelve turns could be written as a
unit test with its state hand-built, and that is exactly what hides the
defects: the author constructs the state they imagined, and the state a real
session produces is different.

It paid for itself on the first run. Turn 5 — code changed, nothing recorded —
was **silent**, where 231 unit tests said the gate fires. The cause was created
by turn 4 and is written up in ADR-0028. No single-hook test could have found
it, and the suite that could not find it was not a weak suite.

Keeping it in `tests/` rather than a scratch directory is the point of
difference from the three edge-case probes before it. Those were run once and
discarded, and their findings survive only as tests someone has to remember to
keep. This one is the harness itself.

`--plugin-root` exists because where the code runs from has already mattered
once: a packaging mistake is invisible when tests run from the source tree.
Running the same twelve turns against an installed copy costs one argument.

## Cost
A second test entry point. Someone changing hook behaviour now has two places
that can fail, and the simulation's failures are less precise than a unit
test's — it reports that turn 5 went wrong, not which line.

The twelve turns are one plausible session, not a generated space of them. A
different order could hide something this one does not.

## Re-evaluation trigger
If a hook defect is ever found that the simulation could have caught but did
not, add the turn that would have caught it rather than widening the unit
tests.

## Conclusion & consequences
Twenty-three checks across twelve turns, passing against both the working tree
and an install-shaped copy — and against the pre-fix build they correctly fail,
which is how the fix was confirmed rather than assumed.

Four questions have now each found defects nothing else did: what situation is
the project in, what environment is it running in, what state are the files in,
and now **what happened earlier in this session**.

## Diversions & Pivots

## User's own words
> Can we push it first, and check if we can do any sims CLI test?
