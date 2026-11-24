---
id: ADR-0002
type: decision
title: Visible docs/project-memory for the ledger
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [REJ-0001]
tags: [layout, documentation]
---

# ADR-0002: Visible docs/project-memory for the ledger

## Discussion
Three layouts were proposed for where records live: `.project-memory/`
(DeepSeek), `.ai/` or `docs/memory/` (Gemini), and `docs/project-memory/`.

## Decision
`docs/project-memory/`, visible, committed, with `decisions/`, `rejections/`,
`change-requests/`, plus `00-PROJECT-STATE.md`, `CHANGELOG.md`, `JOURNEY.md`
and a generated `INDEX.md`.

## Reasoning
The stated goal is that a human arriving cold can read the documents and
understand the project. A dotted directory is hidden by default in file
browsers, skipped by `ls`, excluded by many search tools and invisible to
anyone who did not already know to look. Hiding the thing whose purpose is to
be read is self-defeating.

`docs/` is also where the owner's existing documentation convention points, so
the ledger extends that convention instead of competing with it.

## Cost
`docs/` is slightly more intrusive in a repo whose docs folder is otherwise
user-facing. Accepted: the records are user-facing.

## Re-evaluation trigger
If a project's `docs/` is published verbatim as a public site, the ledger would
need either exclusion from that build or its own location.

## Conclusion & consequences
Hook scripts locate the ledger at `docs/project-memory` relative to the project
root and stay silent when it is absent, so installing the plugin globally does
not create files in unrelated projects.

## Diversions & Pivots

## User's own words
> n/a
