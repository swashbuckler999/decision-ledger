---
id: REJ-0001
type: rejection
title: Hidden directory for project memory
date: 2026-11-24
status: rejected
related: [ADR-0002]
tags: [layout]
---

# REJ-0001: Hidden directory for project memory

## What was proposed
Store the ledger in a dotted directory: `.project-memory/` (DeepSeek) or `.ai/`
(Gemini). The stated benefit is isolation — keeping tracking artefacts visually
separate from the codebase so they do not clutter the project tree.

## Discussion
The isolation argument is real. A repo root with a `docs/project-memory/` tree
does carry more visible weight than one with a hidden folder, and both external
opinions independently reached for a dotted directory.

## Why it was rejected
The requirement is that a human or an agent arriving cold can find and read
these files. A dotted directory is hidden in file browsers by default, omitted
from plain `ls`, excluded by default from many search and indexing tools, and
invisible to anyone who does not already know it exists. The system's entire
value depends on being discovered by someone with no prior knowledge, and the
proposal optimises for not being seen.

## What was done instead
ADR-0002: visible `docs/project-memory/`.

## Re-evaluation trigger
Do not revisit on aesthetic grounds. Reconsider only if a project publishes
`docs/` verbatim as a public site, where the records would need excluding or
relocating.

## User's own words
> n/a
