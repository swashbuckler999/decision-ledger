---
id: ADR-0012
type: decision
title: The scan is mechanical, the mapping is approved
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0003, ADR-0009, ADR-0011]
tags: [adoption, enforcement]
---

# ADR-0012: The scan is mechanical, the mapping is approved

## Discussion
The owner asked directly whether adoption was being performed by me or by the
skill. The honest answer was: by me. `ledger-adopt` was prose describing what I
had done by hand, and it had never been executed.

By ADR-0003's own argument — mechanisms beat instructions — leaving the
detection to prose was the weak choice, and detection is where a mistake lands
entries in the wrong part of a file that may hold years of work.

## Decision
Split adoption at the point where judgement actually begins.

- **Mechanical, in `scripts/scan_project.py`:** find the memory files, read
  each one's shape, establish changelog order and entry format, and emit a
  draft `.ledger.json` with `--propose`. Read-only; it never writes to the
  project it scans.
- **Human, via the `ledger-adopt` skill:** review the proposal, answer what
  the scanner could not determine, approve, then write the config and create
  what is missing.

The scanner never writes a config. The skill never guesses an order.

## Reasoning
Order and entry format are deterministic properties of a file. Reading them is
exactly the kind of work a script does better than prose: consistently, the
same way every time, and testable against fixtures drawn from real specimens.

The residue genuinely needs a person. Five of 26 changelogs in the corpus are
undecidable — one entry, or version headings with no dates. For those the
scanner writes the corpus default, marks it `unconfirmed` in the config, and
tells the skill to ask. Writing it down and flagging it beats omitting the key,
which would apply the same guess with no paper trail.

## Cost
A second entry point to maintain, and a scanner whose heuristics will meet
shapes this corpus does not contain. It degrades to "ask the user", which is
the right failure.

Adoption still is not fully mechanical: the skill decides what to do with the
proposal, and writing the briefing honestly remains a judgement. That residue
is correct — it is a one-time setup step with a human approving the result,
which is where instructions belong.

## Re-evaluation trigger
If `--propose` output is routinely edited before use, its mapping rules are
wrong and should be corrected rather than hand-patched each time.

## Conclusion & consequences
Verified by running `--propose` across all 82 projects: no crashes, 21 orders
determined confidently, 5 correctly refused. Tests cover each real shape found,
including the two the first implementation got wrong.

## Diversions & Pivots

## User's own words
> So are you doing it yourself, or the skills have that capabilities in-built?
