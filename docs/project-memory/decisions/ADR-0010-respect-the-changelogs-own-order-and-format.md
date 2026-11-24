---
id: ADR-0010
type: decision
title: Respect the changelog's own order and format
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0009, CR-0002]
tags: [adoption, data-loss]
---

# ADR-0010: Respect the changelog's own order and format

## Discussion
ADR-0009 set the re-evaluation trigger: "If adopted changelogs come back
visibly inconsistent in style, the append format needs to be declared in the
config rather than inferred by the model."

It fired before shipping. Scanning Trade Manager found 220 changelog entries in
**newest-first** order, headed `## YYYY-MM-DD - Title` with prose beneath. The
ledger appended a one-line bullet to the bottom of the file, which on a
newest-first changelog files every new entry under the oldest heading.

That is not a style mismatch. The entry lands somewhere actively wrong, where
nobody will look for it and where it misrepresents when the work happened.

## Decision
Two config keys:

- `changelog_order`: `oldest-first` (default, appends) or `newest-first`
  (inserts above the most recent entry, below any title and intro).
- `changelog_entry`: a template over `{date}`, `{id}`, `{title}`, `{path}`,
  defaulting to the existing one-line bullet. Multi-line templates are allowed
  so a project whose entries are headed sections gets a headed section.

Writes go through `_write_atomic`: a sibling temp file renamed over the target.

## Reasoning
Insertion into a 369 KB file that may be the only copy of years of work is the
most dangerous thing this plugin does, so it is the thing most worth making
boring. Three guards, all cheap:

1. The insertion point is the first `## ` line, found by scanning — no regex
   over the whole document, no parsing of prose.
2. Before writing, the result is checked to confirm the original text is still
   present intact; a result that would alter anything but the insertion raises
   rather than writes.
3. The write is atomic. An interrupted write leaves the original untouched,
   never a half-written file.

Why not infer the order at write time instead of configuring it: inference
would make the same project behave differently as its content changes, and
getting it wrong writes into the file. Config is read once and is inspectable.

Why a template rather than matching the surrounding style by model judgement:
the scripts write changelog entries without a model in the loop. A template is
the only way the script can match a convention it cannot read.

## Cost
Two more config keys, and a project with an unusual changelog shape — entries
not headed `## `, or several interleaved sections — gets the fallback append.
That is the conservative failure, not a corrupting one.

## Re-evaluation trigger
If a project's changelog has no `## ` headings but does have a meaningful
order, the heading-based insertion point is too narrow and the config needs an
explicit anchor instead.

## Conclusion & consequences
Eight tests cover it, including a 220-entry newest-first fixture that asserts
the intro stays on top, the entry lands first, every original entry survives,
and no temp file is left behind.

## Diversions & Pivots

## User's own words
> Add insert position
