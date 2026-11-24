---
id: ADR-0004
type: decision
title: Separate namespaces for decisions, rejections and change requests
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [REJ-0003]
tags: [schema]
---

# ADR-0004: Separate namespaces for decisions, rejections and change requests

## Discussion
The first design had one `decisions/` folder with a `status` field covering
accepted and rejected alike. Gemini's first answer proposed three ID-prefixed
namespaces: ADR, REJ, CR.

## Decision
Three folders, three ID prefixes: `ADR-NNNN`, `REJ-NNNN`, `CR-NNNN`. A fourth
concept, the diversion, is not a folder: it is an append-only section inside the
record it diverts from.

## Reasoning
Rejections have a different read path from decisions. The cold-start question
"what must I not re-propose?" is answered by scanning one folder of titles; mixed
in with accepted decisions behind a status field, that scan requires reading
every file. Giving rejections their own namespace makes the most valuable and
most-skipped step cheap enough to actually perform.

Change requests are what the owner asked for by name and have a genuinely
different shape: an origin, a scope impact, a blast radius.

The diversion-as-append idea came from Gemini's second answer and is the best
single contribution of either external opinion: a mid-flight pivot that does not
warrant a new decision still has to live somewhere, and appending preserves the
original reasoning rather than overwriting it.

## Cost
Three folders instead of one, and a judgement call at write time about which
namespace applies. The ID allocator handles the mechanics.

## Re-evaluation trigger
If in practice records are routinely filed under the wrong prefix, the
distinction is not as clear as assumed and should collapse to one namespace with
a type field.

## Conclusion & consequences
IDs are permanent. A record is never renumbered, renamed or deleted; a
superseded decision keeps its file and gains a `superseded_by` pointer.

## Diversions & Pivots

## User's own words
> n/a
