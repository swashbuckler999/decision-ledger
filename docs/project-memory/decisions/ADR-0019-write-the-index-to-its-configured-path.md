---
id: ADR-0019
type: decision
title: Write the index to its configured path
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0008, ADR-0009, ADR-0014]
tags: [data-loss, adoption, edge-cases]
---

# ADR-0019: Write the index to its configured path

## Discussion
`build_index.py` resolved the index through the config, checked that file for
the generated-by marker required by ADR-0008, and then wrote to
`L.ledger_dir() / "INDEX.md"` — the hardcoded default.

In a project that maps `index` elsewhere, which is exactly the adopted layout
ADR-0014 added support for, the two paths are different files. The sequence
that follows is the worst available:

1. the marker check runs against the configured path, which does not exist, so
   it passes;
2. the write lands on the default path;
3. anything already there is replaced.

Reproduced: a project with a hand-written `docs/project-memory/INDEX.md` and
`.ledger.json` pointing `index` at `docs/adr/INDEX.md`. The run exited 0,
printed a path, created nothing at the configured location, and overwrote the
hand-written file with a generated one.

The guard from ADR-0008 was in place and did not fire, because it was
inspecting a different file from the one being written. That is worse than
having no guard: it reported success.

## Decision
Write to `target` — the same path the marker was checked on — and print that
path.

## Reasoning
The bug is not really about the index. It is that a check and the operation it
guards were allowed to resolve their subject separately. ADR-0008 says never
overwrite a file we did not write; the implementation checked one file and
wrote another, so the invariant held on paper and not in the filesystem.

Keeping the two on one variable is the fix and also the guarantee: there is no
longer a path expressible in config where they can diverge.

Everything else in `build_index` already honoured the config — `_relative`
computes link targets against `path_for("index").parent`, so the generated
links were correct for a file written somewhere else entirely.

## Cost
None. The previous behaviour had no legitimate use.

## Re-evaluation trigger
If another script is found checking one path and writing another, this is a
class rather than an instance and the ADR-0008 guard belongs in a shared
helper that takes one path and does both.

## Conclusion & consequences
Four checks pin it, including that the hand-written file at the default
location is byte-identical afterwards.

This is the second time an adoption bug has been found by pointing the config
somewhere unusual and watching what happens to the files that were already
there, rather than by reading the code. It is now part of the simulation.

## Diversions & Pivots

## User's own words
> Please check if we are missing any edge cases?
