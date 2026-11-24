---
id: CR-0002
type: change-request
title: Adapt to projects that already keep notes
date: 2026-11-24
status: accepted
origin: user
diverts_from: null
related: [ADR-0009, REJ-0006]
tags: [adoption, data-loss]
---

# CR-0002: Adapt to projects that already keep notes

## Request
When a project already maintains its own memory files, the ledger must append
to them or fit around them — never rewrite them.

## Origin
The first real installation attempt. Trade Manager was chosen as the trial
project and turned out to hold `CHANGELOG.md` at 369 KB, `STATUS.md` at 98 KB,
`PLAN.md` at 35 KB and `README.md` at 34 KB, all hand-maintained, with the
changelog already quoting the user verbatim and recording reasoning.

Installing the published layout would have created
`docs/project-memory/CHANGELOG.md` beside the 369 KB one: two changelogs,
neither authoritative.

## Discussion & reasoning
The request was made twice, and the second time was the one that mattered. The
earlier concern — "if someone somehow already maintaining the files we should
append, instead of rewriting" — produced ADR-0008, which stopped the *scripts*
clobbering files. This one goes a level deeper: even with nothing overwritten,
a hardcoded layout forces a second, parallel set of files, which is its own
kind of damage.

Three options were put to the user: add config support, install records-only
with instruction-level mapping, or install as published and accept the
duplication. The user rejected the framing and asked for a proper design
instead. That was correct — two of the three options were bad, and one of them
was my recommendation.

Designing it properly also exposed a second flaw neither the user nor I had
seen: the briefing hook assumes the state file is small. Mapping the briefing
onto a 98 KB `STATUS.md` would inject its first 160 lines into every session.
The recommended option would have shipped that.

## Scope impact
- `.ledger.json`, optional, path overrides relative to the project root
- `_ledger.py` gains `config()`, `path_for()`, `is_adopted()`, `is_ledger_path()`
- All four scripts and five hooks resolve paths through it
- New `ledger-adopt` skill: scan, propose, write config on approval
- Defaults unchanged, so every greenfield project behaves exactly as before
- Not in scope: migrating existing content into records — see REJ-0006

## Conclusion
Built and tested. Tests 54 → 66, with the new ones covering an adopted project,
a malformed config, and the briefing not absorbing a large status file.

## User's own words
> This is the challenge I was talking about, our previous version would have
> rewritten the whole memory, and project reference. Now you need to analyze
> and plan how this can be handled smartly. Is it possible develop the
> capability in the skill when there is already maintained files then either
> start appending, or restructuring the files, etc. Think and get the best and
> correct solution.
