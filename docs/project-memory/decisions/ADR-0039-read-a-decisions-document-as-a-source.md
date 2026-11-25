---
id: ADR-0039
type: decision
title: Read a decisions document as a source
date: 2026-11-26
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0015, ADR-0038, REJ-0003, REJ-0006]
tags: [backfill, adoption, user-pushback, rejection-revisited]
---

# ADR-0039: Read a decisions document as a source

## Discussion
ADR-0038 made the scanner *mention* a single-file decision history instead of
ignoring it, and told the user to link it from the briefing. The owner
rejected that as a half-answer, in these words:

> So it is ignoring something very important in the project just because it
> isn't a smaller filesize or such very small factors?????!!! Most stupid
> reason to throwaway anything!!! It would be better to read them, structure
> them as per the skills mechanism, break into multiple files with reasoning
> as per the skills structure, understand it, and prepare it properly -
> INSTEAD OF THROWING IT AWAY!!!!

They were right, and the project's own records showed it faster than argument
could.

**REJ-0006 was being applied beyond what it rejected.** It was written about a
369 KB *changelog* — undifferentiated prose, where *"deciding what counts as a
decision, where each one begins and ends"* would have to be invented. A
decisions document is not that. The author already drew the boundaries: the
headings **are** the decisions. The dates are written. The reasoning is
written. The supersession marks are written. Every judgement that rejection
feared having to invent has already been made by the person who made the
calls.

**And the plugin was inconsistent with itself.** `mine_history.py` already
reconstructs records from commit messages — a thinner, more incidental, less
deliberate source — and handles not having witnessed them with `provenance`,
`sources` and `confidence` markers. Refusing to read a file called
`DECISIONS.md` while mining one-line commits is not a principle; it is an
oversight.

**The rejection's own trigger had fired.** REJ-0006 set the terms:

> Revisit only as an explicitly invoked, one-document-at-a-time operation that
> backs up the original outside the repository first, shows a diff, and
> requires confirmation — never as part of adoption, and never across a whole
> project in one pass.

It never said *never read it*. It said not silently, not during adoption, not
wholesale. Those are exactly the conditions under which this is now built.

## Decision
`read_decisions_doc.py`, read-only, splitting a document on its own headings,
and a new first step in `ledger-backfill` that uses it under the trigger's
terms: explicitly invoked, one document, backed up outside the repository,
candidates confirmed before anything is written.

Records from this source carry `provenance: from-document`,
`sources: [<file>#<heading>]` and `confidence: stated` — stated, not inferred,
because the reasoning is the author's own prose, carried across rather than
summarised.

The original is never modified, moved, renamed or deleted. That half of
REJ-0006 stands absolutely and is asserted by a byte-comparison in the tests.

## Reasoning
The supersession handling is what makes this an upgrade rather than a
reformat. A flat file cannot express "this decision replaced that one" as a
link — marking it means editing the file, which is precisely the tension
REJ-0003 identified and which the project that prompted this had already hit.
Resolving those marks into real `supersedes` / `superseded_by` links turns a
chronological document into a navigable graph, and it is the one thing the
original file structurally could not do.

Everything else is carried, not improved. The author's words go into
`Discussion` and `Reasoning` verbatim. A heading with no reasoning beneath it
produces a record that says so, rather than one with a plausible rationale
supplied.

Ordering matters too: the document comes *before* git history in the skill,
because it is the better source. Mining commits to reconstruct decisions that
are already written down, in a file, with dates, would be absurd.

## Cost
This is the most dangerous operation the plugin performs, by the measure
REJ-0006 used: it reads a large irreplaceable hand-written file and produces
records that will be trusted. The safeguards — read-only script, backup
first, confirmation, provenance markers, original untouched — reduce that; they
do not remove it.

A document with headings that are not decisions will produce candidate records
that are not decisions. The section-heading filter is a heuristic and will be
wrong somewhere.

## Re-evaluation trigger
If a backfilled document produces records whose reasoning does not appear in
the source, the carrying has become summarising and the step must stop and ask
rather than write.

## Conclusion & consequences
Fourteen checks pin the reader, including that the source file is
byte-identical afterwards — the assertion that matters most.

The wider lesson is about rejections rather than documents. REJ-0003 and
REJ-0006 both did their jobs: one was cited correctly by an installing agent,
the other stopped a dangerous operation for months and then named the exact
conditions under which it should be revisited. A rejection with a real
re-evaluation trigger is not a closed door. It is a door with the key taped to
it, and this is the first time this project has used one.

## Diversions & Pivots

## User's own words
> It would be better to read them, structure them as per the skills mechanism,
> break into multiple files with reasoning as per the skills structure,
> understand it, and prepare it properly - INSTEAD OF THROWING IT AWAY!!!!
