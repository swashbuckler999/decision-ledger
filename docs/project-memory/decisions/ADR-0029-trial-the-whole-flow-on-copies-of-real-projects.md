---
id: ADR-0029
type: decision
title: Trial the whole flow on copies of real projects
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0009, ADR-0010, ADR-0014, ADR-0026, ADR-0027]
tags: [corpus, trial, adoption, verification]
---

# ADR-0029: Trial the whole flow on copies of real projects

## Discussion
The corpus had been scanned four times, always read-only. The scanner was
therefore well tested against real material and **every write path was not**:
adoption, record creation, index generation and changelog insertion had only
ever run against fixtures this project wrote itself.

The owner's suggestion closed that gap directly:

> If require pull/copy a project from those 82 in a sandbox and do the trial
> run there.

Three projects were copied into a sandbox, one per situation: one with its own
`docs/adr` in `adr-tools` style, one with months of commits and no notes, and
one mature project whose changelog is 369,195 bytes of real work. The full flow
was then run **on the copies**: scan, propose, write `.ledger.json`, create the
record directories, record a decision, build the index, and replay the hooks.

Each original was fingerprinted before and after — every file's size and mtime,
a content hash of every file the ledger could plausibly touch, the git HEAD and
the dirty count.

## Decision
Run the write paths against copies of real projects, and prove the originals
untouched rather than asserting it.

## Reasoning
A fixture is the author's idea of what a project looks like. These three are
not: the `adr-tools` project numbers its records `0001`–`0004` with no prefix,
the mature one has a 369 KB changelog with prose entries, inline quotes and its
own heading style, and the third carries 36 commits of real reasoning and no
notes at all.

Fingerprinting the originals is not ceremony. The scanner is read-only by
design and has been since the first version, but "designed to be read-only" and
"demonstrated not to have written" are different claims, and only one of them
can be shown to someone else.

## Cost
A copy of an 85 MB project per run, and the trial takes about ten seconds. The
copies are disposable and live outside any repository.

A copy is not quite the original: file permissions, and anything depending on
an absolute path, differ. Nothing in the flow touches either.

## Re-evaluation trigger
If a write path is added that behaves differently on a large or unusual file,
add that project shape to the trial rather than to the fixtures.

## Conclusion & consequences
All three originals **unchanged** — identical file sets, hashes, HEADs and
dirty counts.

On the copies:

| Project | Result |
|---|---|
| `adr-tools` style | Adopted `docs/adr`, new record filed `0005-…` continuing their 0001–0004, bare naming matched, `id: ADR-0005` kept inside. Their four records **byte-identical**. |
| Months of commits, no notes | Correctly reported NOT greenfield with 18 commits carrying evidence, and routed to backfill |
| 369,195-byte changelog | **+138 bytes**, inserted at the top in the file's own `## date - title` format. Every original byte after the heading survives verbatim; LF endings unchanged; their 97,686-byte `STATUS.md` untouched and not adopted |

That last line is the one worth keeping. The adoption promise — append in the
file's own style, never reformat, never reorder — is now demonstrated against
a real file with years of someone's writing in it, not against a fixture
written to make it pass.

## Diversions & Pivots

## User's own words
> If require pull/copy a project from those 82 in a sandbox and do the trial
> run there.
