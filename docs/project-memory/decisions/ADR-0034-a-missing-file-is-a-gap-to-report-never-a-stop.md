---
id: ADR-0034
type: decision
title: A missing file is a gap to report, never a stop
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0032, ADR-0006, ADR-0007]
tags: [skills, instructions, live-session]
---

# ADR-0034: A missing file is a gap to report, never a stop

## Discussion
The third live session found four instruction defects, and three of them are
the same mistake in different places: **an instruction written as though every
ledger file already exists.**

1. `cold-start` step 3 names `CONSTRAINTS.md` as mandatory reading, in a list
   where steps 1 and 2 both say what to do if their file is absent. There was
   no `CONSTRAINTS.md`. The session had to improvise a way to say so.
2. `wrap-session`'s destination table is headed *"Where it must already
   exist"*. The session was looking at a hard-won environment fact — an
   endpoint pin — living only in the mutable state file, with no
   `CONSTRAINTS.md` to move it to. Read literally, the table forbids moving
   it, so **the one fact the table exists to rescue was stranded in the one
   file that gets rewritten.** The session correctly refused to delete it and
   reported the contradiction instead.
3. `cold-start`'s report shape ends *"in this shape and nothing longer"*, and
   the honesty rules below it demand saying when the ledger is thin or
   contradicts the code. The session found exactly that — the state file
   promised a Parquet writer the code did not contain — and had nowhere in the
   prescribed shape to put it.

The fourth is different: `wrap-session` never says whether to commit. Its last
step is reporting. The session committed anyway, under a convention it found
elsewhere, and flagged that it had to.

This is the third time this class has appeared. ADR-0032 fixed "append, never
rewrite" having no clause for a file that does not exist yet. The same
assumption was sitting in two more skills.

## Decision
Every instruction that names a ledger file now says what to do when it is not
there.

- `cold-start`: an absent file is a finding to report, not a blocker, and
  never a reason to create one empty. An empty rejections folder is itself
  worth reporting — a project with no recorded rejections has lost that
  history rather than never having had any.
- `wrap-session`: "where it must already exist" names the **destination**, not
  a precondition. If the destination file does not exist, create it and write
  the entry.
- `cold-start`'s report gains a section for what the ledger does not cover —
  omitted when there is nothing to say, never omitted when there is — and the
  shape instruction no longer forbids length at the cost of completeness.
- `wrap-session` gains a commit step: follow the project's own conventions,
  and if nothing grants that permission, say the ledger is written and
  uncommitted and leave it to the user. Never commit beyond the ledger files,
  never push.

## Reasoning
These are one-line clauses, and the reason they were all missing is that every
one of them was written while looking at this repository, where all these
files have existed since the first week. The author's project is the worst
possible reference for instructions about a project that has nothing yet.

The `wrap-session` table is the one that mattered most, because it inverted
the skill's purpose. The whole point of that step is to stop content being
lost from the only mutable file, and as written it blocked the rescue whenever
the destination had not been created — which is precisely when the content is
most at risk, because a project with no `CONSTRAINTS.md` is one that has never
moved a constraint out before.

The commit step needed care in the other direction. Committing is not the
skill's to assume: it is the user's repository and their conventions. Saying
"follow what the project says, and otherwise do not" leaves the decision where
it belongs while removing the ambiguity that made a session guess.

## Cost
The skills are longer, and each is now carrying a conditional that only
matters on a project's first few sessions.

## Re-evaluation trigger
If a fourth instance of "assumes the file exists" turns up, stop patching
instances and put one statement at the top of every skill: every ledger file
is optional until something needs it.

## Conclusion & consequences
All four fixed. None is testable — they are prose, and the only instrument
that has ever found this class is a live session.

Three sessions, three sets of findings, no sign of the rate dropping. That is
the honest state of the agent-facing layer: the code is well covered and the
660 lines of instructions around it are still being read for the first time by
someone other than their author.

## Diversions & Pivots

## User's own words
> Fix those five and run the fourth session
