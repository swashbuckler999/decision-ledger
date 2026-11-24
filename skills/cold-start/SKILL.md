---
name: cold-start
description: Brief yourself on a project you have no memory of by reading its decision ledger. Produces an orientation covering current state, accepted decisions, settled rejections you must not re-propose, open questions and the next step.
when_to_use: Use at the start of work on an unfamiliar project, when resuming after a break, or when the user asks "where were we", "catch up", "what is the state of this", or "bring me up to speed". This is for ARRIVING at a project; to write the state down before leaving one, use wrap-session.
allowed-tools: Read, Glob, Grep, Bash(python *), Bash(git log *)
---

# Cold start

> **Running a script from a skill.** `scripts/` is in the *plugin*, not in
> the user's project, so a bare `scripts/...` path resolves against their
> repository and finds nothing. `$CLAUDE_PLUGIN_ROOT` does not help either:
> the harness substitutes it for hook commands, but it is **empty** in a tool
> shell, and in Git Bash the empty expansion silently becomes a path under the
> Git install.
>
> Two reliable anchors, in order of preference:
>
> 1. The **absolute paths in the project-memory context block** injected at the
>    start of the session, under "Running the ledger scripts". Prefer these.
> 2. If that block is absent -- which it is in a project with no ledger yet --
>    the plugin root is **two levels up from this skill's base directory**, the
>    absolute path given at the top of this file. `scripts/` and `skills/` are
>    siblings there.
>
> Always pass `--project "<absolute project root>"`. The scripts otherwise fall
> back to the working directory, which the harness can change mid-session, and
> the ledger would be written somewhere else without any error.


Goal: in a few minutes of reading, reach the state a person who has been on this
project all along would be in — including knowing which obvious-looking ideas
have already been tried and have already failed.

## Read in this order

1. `docs/project-memory/00-PROJECT-STATE.md` — current truth, capped at 150
   lines. If this file is missing or stale, say so plainly rather than inferring
   the state from code.
2. `docs/project-memory/INDEX.md` — the generated map of every record. If it is
   absent or out of date, regenerate it: `python "<plugin root>/scripts/build_index.py" --project "<project root>"`
3. **`docs/project-memory/CONSTRAINTS.md`** — the environment and access rules
   that bind the work. Short, and the cheapest file in the ledger to read: each
   entry is something that would otherwise cost an hour to rediscover. If the
   file does not exist, note that in your report and move on. Several of these
   files only appear once there is something to put in them, and an absent one
   is a gap to mention, never a reason to stop or to create it empty.
4. **Every file in `docs/project-memory/rejections/`** — titles at minimum, and
   the "Why it was rejected" section of any that touch what you are about to
   work on. This step is not optional and not skippable for speed. Skipping it is
   how a settled argument gets re-opened. An empty or missing folder is a valid
   finding -- report it, because a project with no recorded rejections has lost
   that history rather than never having any.
5. Accepted ADRs relevant to the area you are touching. You do not need all of
   them; you do need the ones that bind the files you will edit.
6. `docs/project-memory/JOURNEY.md` — the last few entries, for narrative and
   for the user's own recorded words.
7. `docs/project-memory/CHANGELOG.md` — the last ten lines, for recency.

## Then report back

Give the user, in this shape. Keep it short, but never drop a
section to stay short -- an omission the reader cannot see is worse than a
longer report:

- **Where it stands** — two or three sentences from the state file
- **What is settled** — the accepted decisions that constrain the work ahead
- **What is closed** — rejections relevant to this area, each one line, so the
  user can see you will not re-propose them
- **What is open** — unresolved questions and anything marked unverified
- **Next step** — what the state file says comes next
- **What the ledger does not cover** — leave this out when there is nothing to
  say, and never leave it out when there is. Missing files, a state file that
  contradicts the code, anything you had to infer. The honesty rules below
  require this and the shape above has no other place for it: a live session
  found the state file promising a writer the code did not have, and had
  nowhere to put it.

## Honesty rules

- If the ledger is thin, empty or contradicts the code, say that. A confident
  briefing built on a stale state file is worse than admitting the gap, because
  the user will act on it.
- Distinguish what the ledger records from what you inferred by reading code.
  Label inferences as inferences.
- If a rejection's re-evaluation trigger appears to have fired, flag it. That is
  the one case where raising a settled idea again is correct.
