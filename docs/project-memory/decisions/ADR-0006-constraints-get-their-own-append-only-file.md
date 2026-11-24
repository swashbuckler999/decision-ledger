---
id: ADR-0006
type: decision
title: Constraints get their own append-only file
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0005]
tags: [schema, data-loss]
---

# ADR-0006: Constraints get their own append-only file

## Discussion
The owner asked whether the 150-line cap on `00-PROJECT-STATE.md` risked losing
anything. Checking rather than reassuring found a real hole.

The state file had six sections. Three of them — Open questions, Constraints,
Immediate next steps — had no corresponding record type, so they existed
*only* in the one mutable file in the ledger. ADR-0005's instruction to "move
detail out into the numbered records" had no destination for them.

It was not hypothetical. The gh account constraint discovered during publishing
— switch accounts before pushing, and do not put the username in the remote URL
— existed in exactly one file, and that file was the one designed to be
rewritten. A tidy-up pass would have dropped it silently, and the next session
would have rediscovered it by getting a 403.

## Decision
`docs/project-memory/CONSTRAINTS.md`, append-only, beside `CHANGELOG.md` and
`JOURNEY.md`. The state file's Constraints section becomes a pointer.

Supporting changes: the `wrap-session` skill gains a move-it-before-you-remove-it
table mapping every kind of state-file content to the append-only file that must
already hold it; `cold-start` reads constraints third, after state and index;
the SessionStart hook lists constraint headings in the briefing.

## Reasoning
A constraint is not a decision — nobody chose it. It is a fact about the world
that binds the work, so it fits none of ADR, REJ or CR. Forcing it into an ADR
would misrepresent it and make the decisions folder harder to scan.

Why it belongs in the briefing: a constraint written down but not surfaced is
only marginally better than one not written down. These are the cheapest
high-value lines a cold session can receive — each one is typically an hour of
rediscovery avoided. Measured cost of adding them: the briefing went from ~1,490
to ~1,651 tokens, about 160 tokens for four constraints.

Why not generate the state file instead, which would remove the mutability
entirely: rejected in ADR-0005, and the reasoning stands. The state file's value
is synthesis, which cannot be generated from records.

Why not a mechanical check that diffs the state file against its last committed
version and reports dropped lines: it is the only non-instruction-dependent
option and is consistent with ADR-0003's argument that instructions degrade. It
is deferred, not rejected — see the trigger below. The two changes made here
close most of the hole at a fraction of the complexity.

## Cost
A fourth top-level file in the ledger, and one more judgement call when writing:
is this a decision or a constraint. The distinction is usually obvious — if
nobody chose it, it is a constraint.

Open questions and next steps remain state-file-only. They are genuinely
transient, and the move-it-before-you-remove-it rule now directs anything
durable among them into the journey.

## Re-evaluation trigger
If a constraint or an open question is ever found to have been dropped from the
state file without landing somewhere append-only, the instruction-level rule has
failed and the diff-check script should be built. Git history is the backstop
until then — every version of the state file is committed — but recovering by
`git log -p` fails this project's own bar, which is that reading the documents
is enough.

## Conclusion & consequences
Decisions, rejections, change requests and constraints are all append-only and
cannot be lost. `00-PROJECT-STATE.md` is the only mutable file, and nothing may
exist solely inside it.

## Diversions & Pivots

## User's own words
> Why "mutable, capped at 150 lines, the entry point" is there in Project
> state? Is it okay? Nothing will be lost?
