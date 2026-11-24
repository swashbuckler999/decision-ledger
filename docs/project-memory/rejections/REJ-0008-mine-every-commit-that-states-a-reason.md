---
id: REJ-0008
type: rejection
title: Mine every commit that states a reason
date: 2026-11-24
status: rejected
related: [ADR-0013, ADR-0016]
tags: [backfill, corpus]
---

# REJ-0008: Mine every commit that states a reason

## What was proposed
Treat history mining as a loose filter: flag every commit carrying a message
body, a decision or rejection keyword, or a subject that states a reason, and
hand the whole list to the backfill skill for review.

The argument was explicit and drawn from a decision already accepted here.
ADR-0013 set match strictness by consequence: strict where a false positive
attaches the ledger to a file it will write into, loose where being wrong is
cheap. Mining writes nothing at all. A wrong candidate is one line in a list
the user reads and dismisses. By that rule, mining should match as loosely as
possible, and missing a real decision is the only expensive error.

## Discussion
It performed well on the fixture: 7 of 10 commits flagged, the 3 skipped being
exactly the mechanical ones. Two commits that the stricter first draft had
missed — a walk-forward split added to stop look-ahead bias, a cache added
because recompute took eleven minutes — were picked up by loosening.

## Why it was rejected
Run against the 82-project corpus it flagged **4,273 of 4,380 commits, 98%**,
with a 100% match rate in twenty-seven of thirty-eight repositories.

The reasoning error was in valuing the consequence wrongly, not in applying the
rule. A false positive does cost almost nothing — *once*. At 1,327 candidates
for one project the cost is not a bad record, it is that nobody does the
backfill at all, and the capability is worth nothing unused. Volume is itself
the consequence, and the loose tier never accounted for it.

The fixture could not have revealed this. It had ten commits, written by the
same author as the filter.

## What was done instead
ADR-0016: score rather than filter, require two points, weight a message body
by whether bodies are common in that repository, rank strongest-first and cap
at 40 with a count of what was withheld. 98% → 30%.

## Re-evaluation trigger
If backfill sessions routinely find important decisions by hand that the miner
scored below threshold, lower the threshold. Do not return to an uncapped list.

## User's own words
n/a — this was a self-correction found by re-running the corpus, which the
owner had earlier insisted on as the standard: "you have 82 test cases under
'[local corpus directory - path redacted]', you can simulate/test/check on all of them and design Skills
accordingly."
