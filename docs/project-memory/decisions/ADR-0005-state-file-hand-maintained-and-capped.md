---
id: ADR-0005
type: decision
title: State file is hand-maintained and capped at 150 lines
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0004]
tags: [schema, cold-start]
---

# ADR-0005: State file is hand-maintained and capped at 150 lines

## Discussion
`00-PROJECT-STATE.md` is the cold-start entry point and the only mutable file in
the ledger. Two options: generate it from the records, or maintain it by hand.

Gemini's second answer made the supporting argument for a cap without proposing
one: segmenting files prevents an agent reading a 50-page document on cold
start. Gemini's first answer proposed 150 lines.

## Decision
Hand-maintained, capped at 150 lines, with the cap stated in the file itself and
in the skills that write it.

## Reasoning
A generated state file can only restate what the records already say. The value
of the state file is the part no record contains: what is half-finished, what is
blocked, what the next concrete step is, and what is uncertain. That is
synthesis, not aggregation.

The cap is the load-bearing part. An uncapped state file accretes history, stops
being a briefing, and gets skimmed — at which point the cold start silently
degrades to reading code. 150 lines is roughly what a person reads before
deciding whether to keep reading.

Why generation lost: it would produce a file that is always accurate and never
useful.

## Cost
It can go stale, and nothing detects staleness. The `wrap-session` skill is the
only defence, and it depends on being invoked.

## Re-evaluation trigger
If the state file is repeatedly found contradicting the records, add a generated
"records added since this file was last touched" footer rather than generating
the whole file.

## Conclusion & consequences
`INDEX.md` is generated and carries the map; `00-PROJECT-STATE.md` is written and
carries the judgement. They are not the same file and must not merge.

## Diversions & Pivots

## User's own words
> n/a
