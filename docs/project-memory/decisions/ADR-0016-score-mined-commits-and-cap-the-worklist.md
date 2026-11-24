---
id: ADR-0016
type: decision
title: Score mined commits and cap the worklist
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0011, ADR-0013, ADR-0015, REJ-0008]
tags: [backfill, evidence, corpus]
---

# ADR-0016: Score mined commits and cap the worklist

## Discussion
The first version of the history miner used a boolean filter: any commit with a
message body, a keyword, or a reason-shaped subject was a candidate. Against
the sandbox fixture it looked excellent — 7 of 10 commits flagged, and the 3 it
skipped were exactly the mechanical ones.

The fixture was written by the same hand as the miner, so it was then run
against the corpus. **It flagged 4,273 of 4,380 real commits: 98%.** Per
project the match rate was 100% in twenty-seven of thirty-eight repositories.

The dominant cause was `has a message body`, true of 4,238 commits — 97%. The
first guess was that the `Co-Authored-By` trailer was being counted as a body.
It was not. The bodies are genuine, substantive reasoning, because the
repositories were written under guidelines that require it. In *this* corpus a
body carries no information at all; in a typical project it is the single best
indicator that reasoning was written down at the time.

## Decision
Score instead of filter, and cap the output.

| Signal | Score |
|---|---|
| Undoes earlier work (`revert`, `abandon`, `roll back`) | 3 |
| Message body, **where bodies are not the norm in that repository** | 2 |
| Closes a route (`drop`, `remove`, `disable`) | 1 |
| Decision word (`switch`, `replace`, `pin`) | 1 |
| Environment limit | 1 |
| Subject states a reason | 1 |

A commit needs a score of 2 to be a candidate: one weak signal is not evidence.
Candidates are ranked strongest-first and the top 40 are shown, with a count of
what was withheld.

Whether a body counts is decided **per repository**, from its own body rate:
above 50%, a body is reported but scores nothing.

## Reasoning
The per-repository weighting is the useful part. A fixed weight for "has a
body" cannot be right for both a repository where 3% of commits have one and a
repository where 97% do — in the first it is the strongest available signal, in
the second it is noise. Measuring the rate and adapting costs one division.

The cap exists because a worklist is not a filter output. The core skill already
holds that four hundred trivial records are as useless as none; mining 1,327
candidates and handing them over would produce exactly that, or more likely be
abandoned. Commits not shown stay in git, which is where they already are and
is not lost.

This is also where the tier rule from ADR-0013 — match strictly where being
wrong is expensive, loosely where it is cheap — had to be re-reasoned rather
than reused. Mining writes nothing, so a false positive is one line in a list,
which argued for loose matching, and that argument produced the 98% result. The
real consequence of a false positive at volume is not a bad record; it is that
the user abandons the backfill. Volume itself is the cost.

Result: 98% → 30% overall, with per-project worklists of 0 to 40 and a median
in single digits.

## Cost
A genuinely important decision can now fall below the threshold or below the
cap — a one-line commit with no keyword and no body is invisible to this, and
some of those matter. Eleven corpus projects produce zero candidates.

The scoring weights are tuned against one developer's corpus, the same
parochialism already recorded against ADR-0011.

## Re-evaluation trigger
If backfill sessions keep finding important decisions by reading the log by
hand after the miner has run, the threshold is too high. Lower the threshold
before adding signals.

## Conclusion & consequences
The miner is bounded, ranked and honest about what it withheld. Nine checks
pin it, including that the adaptive body weighting flips in both directions.

The wider lesson, which has now happened twice in this project: a filter
validated against fixtures written by its own author tells you nothing. The
corpus is the test.

## Diversions & Pivots

## User's own words
> Need to simulation in all once more.
