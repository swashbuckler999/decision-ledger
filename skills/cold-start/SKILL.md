---
name: cold-start
description: Brief yourself on a project you have no memory of by reading its decision ledger. Produces an orientation covering current state, accepted decisions, settled rejections you must not re-propose, open questions and the next step.
when_to_use: Use at the start of work on an unfamiliar project, when resuming after a break, when the user asks "where were we", "catch up", "what is the state of this", or when handing the project to someone else.
allowed-tools: Read, Glob, Grep, Bash(python *), Bash(git log *)
---

# Cold start

Goal: in a few minutes of reading, reach the state a person who has been on this
project all along would be in — including knowing which obvious-looking ideas
have already been tried and have already failed.

## Read in this order

1. `docs/project-memory/00-PROJECT-STATE.md` — current truth, capped at 150
   lines. If this file is missing or stale, say so plainly rather than inferring
   the state from code.
2. `docs/project-memory/INDEX.md` — the generated map of every record. If it is
   absent or out of date, regenerate it: `python scripts/build_index.py`
3. **Every file in `docs/project-memory/rejections/`** — titles at minimum, and
   the "Why it was rejected" section of any that touch what you are about to
   work on. This step is not optional and not skippable for speed. Skipping it is
   how a settled argument gets re-opened.
4. Accepted ADRs relevant to the area you are touching. You do not need all of
   them; you do need the ones that bind the files you will edit.
5. `docs/project-memory/JOURNEY.md` — the last few entries, for narrative and
   for the user's own recorded words.
6. `docs/project-memory/CHANGELOG.md` — the last ten lines, for recency.

## Then report back

Give the user, in this shape and nothing longer:

- **Where it stands** — two or three sentences from the state file
- **What is settled** — the accepted decisions that constrain the work ahead
- **What is closed** — rejections relevant to this area, each one line, so the
  user can see you will not re-propose them
- **What is open** — unresolved questions and anything marked unverified
- **Next step** — what the state file says comes next

## Honesty rules

- If the ledger is thin, empty or contradicts the code, say that. A confident
  briefing built on a stale state file is worse than admitting the gap, because
  the user will act on it.
- Distinguish what the ledger records from what you inferred by reading code.
  Label inferences as inferences.
- If a rejection's re-evaluation trigger appears to have fired, flag it. That is
  the one case where raising a settled idea again is correct.
