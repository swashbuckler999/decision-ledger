---
id: ADR-0024
type: decision
title: Harden reads and writes against hand-written input
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0008, ADR-0020, ADR-0023]
tags: [robustness, encoding, windows, edge-cases]
---

# ADR-0024: Harden reads and writes against hand-written input

## Discussion
A probe of thirteen hostile or unusual states found four defects, all in the
same category: **the plugin reads and writes files that humans also edit**, and
it assumed they would look exactly as it had written them.

**A UTF-8 BOM silently erased a record's frontmatter.** `frontmatter()` tests
whether the first line equals `---`. With a BOM it is `﻿---`, so the whole
block is skipped and the record loses its id, status and date in the index and
in every session briefing, falling back to its filename and first heading.
Several Windows editors write a BOM by default, so this is a likely state for
any record a person creates by hand rather than through the skill.

**A pipe in a title corrupted the index.** Markdown tables separate cells on
`|`, so a record titled *"Use | instead of comma as the delimiter"* opened an
extra column and shifted every value in its row — the rest of the title landed
where the status belongs.

**A record directory that is really a file crashed with a traceback.**
`mkdir(parents=True, exist_ok=True)` still raises `FileExistsError` when the
path exists as a file, which it does if someone keeps `decisions` as a notes
file.

**A failed write left its temp file behind**, so a read-only changelog left
`CHANGELOG.md.ledger-tmp` beside it permanently.

Nine other probes passed unchanged, and they are worth recording because they
were the ones expected to fail: non-ASCII paths through `git status` quoting,
an unborn HEAD, a detached HEAD, hook payloads with a missing, null, numeric or
non-existent `cwd`, a payload that is a list, empty stdin, non-JSON stdin, a
500 KB payload, two ledger roles pointed at one file, a record directory
pointed at the project root, and titles that slugify to nothing.

## Decision
- Record reads use `utf-8-sig`, which strips a BOM if present and is identical
  otherwise. Applied to `frontmatter`, `head`, `tail` and the scanner's reads,
  but **not** to `add_changelog_entry`, which must keep its strict decode and
  byte-exact round trip (ADR-0010).
- `build_index` escapes `|` and collapses newlines in every cell it emits.
- `new_record` catches `OSError` from the directory creation and prints what is
  wrong.
- `_write_atomic` removes its temp file on failure.

## Reasoning
`utf-8-sig` over stripping `﻿` by hand because it is the same decision
expressed once, at the point of reading, instead of at each of the places a BOM
could reach. The one read deliberately left strict is the one that writes the
file back out, where silently absorbing a BOM would change bytes in a file that
may be the only copy.

Escaping at the cell is the narrow fix; escaping the whole row would have
escaped the link syntax too. Titles are the only field a human writes freely,
and a pipe in one is a matter of time rather than an oddity.

The nine passing probes earned their place in the test suite as much as the
four failures. They are the states nobody will think to re-check after a
refactor, and three of them — the payload shapes — are the plugin's entire
contract with the harness.

## Cost
`utf-8-sig` silently accepts a BOM rather than reporting it, so a record saved
with one stays that way and the next editor may or may not preserve it.

The escaped pipe is visible in the index source as `\|`. It renders correctly
and reads oddly to anyone opening the raw file.

## Re-evaluation trigger
If a record is found whose frontmatter is skipped for some other reason — a
leading blank line, CRLF-only delimiters — the first-line equality test is too
strict and should become a match on a stripped line.

## Conclusion & consequences
Thirteen hostile states, four defects, all fixed, and all thirteen are now
checks in the suite rather than a script in a scratch directory.

The probe is worth keeping as a method. The three rounds of edge cases in this
project were found by asking three different questions — *what situation is the
project in*, *what environment is it running in*, and now *what state could the
files be in* — and each question found defects the previous two could not.

## Diversions & Pivots

## User's own words
> Also do deep analysis of any other edge cases which we might have missed.
