---
id: REJ-0003
type: rejection
title: Single append-only DECISIONS.md
date: 2026-11-24
status: rejected
related: [ADR-0004]
tags: [schema]
---

# REJ-0003: Single append-only DECISIONS.md

## What was proposed
One `DECISIONS.md`, appended to over the life of the project, each entry a
dated heading. DeepSeek's design used this shape.

## Discussion
Simplest possible structure, nothing to generate, trivially greppable, and one
file to open. For a small project it would work for months.

## Why it was rejected
It degrades precisely as the project gets valuable. A single file grows past the
point where it can be read on cold start, which forces summarisation, which
destroys the reasoning that is the entire asset. It cannot carry per-record
frontmatter usefully, so status, supersession and relationships have to be
expressed in prose and cannot be indexed. Superseding a decision means editing
the file, which puts the append-only guarantee in tension with the data model.

Individual files make each decision addressable by a stable path, which matters
once records cross-reference each other.

## What was done instead
ADR-0004: one file per record, three namespaces, with a generated `INDEX.md`
providing the single-file overview that this proposal was really after.

## Re-evaluation trigger
Do not revisit. The failure is structural, not a matter of scale thresholds.

## User's own words
> n/a
