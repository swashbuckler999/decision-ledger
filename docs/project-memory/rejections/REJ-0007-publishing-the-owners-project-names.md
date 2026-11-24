---
id: REJ-0007
type: rejection
title: Publishing the owner's project names
date: 2026-11-24
status: rejected
related: [ADR-0011]
tags: [privacy]
---

# REJ-0007: Publishing the owner's project names

## What was proposed
Write the corpus survey with its per-project detail intact — 82 project names
against their conventions, sizes and verdicts. It is the most useful form of
the data: concrete, checkable, and it shows exactly which specimen produced
which design decision.

## Discussion
Named examples make the survey far stronger as evidence. A reader can see that
a particular shape is real rather than hypothetical, and a future session could
re-run the scan and compare like for like.

## Why it was rejected
The repository is public. The folder names are the owner's private working
set and several are personal or client names — individuals, an academy, a
named capital firm, a named channel. Publishing the list would expose who the
owner works with and what they are building, which has nothing to do with what
this plugin does and cannot be undone once pushed.

The aggregates carry the entire argument anyway. "20 of 26 changelogs are
newest-first" is exactly as persuasive without naming any of them.

## What was done instead
`docs/corpus-survey.md` reports counts, distributions and anonymised shape
examples only. No project names, no paths from the development machine.

Two earlier records (CR-0002, ADR-0010) name one project as the specimen that
prompted them. That name is generic and the records would lose their meaning
without a concrete case, so they stand — but flagged here so the decision is
visible rather than accidental, and so it can be revisited if the owner would
rather it were scrubbed.

## Re-evaluation trigger
Do not revisit for a public repository. If the survey is ever needed in full,
it belongs in a private note outside this repo.

## User's own words
> n/a - raised during the work, not requested
