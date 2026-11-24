---
name: wrap-session
description: Flush the session's unrecorded reasoning into the ledger before the context is lost. Checks what changed, finds decisions and rejections that were discussed but never written down, writes the missing records and refreshes the project state file.
when_to_use: Use when the user says they are done, stopping, wrapping up, signing off, or asks to save the state or hand off. Also use when a long session is about to be compacted.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(python *), Bash(git diff *), Bash(git status *), Bash(git log *)
---

# Wrap session

The moment the conversation ends, everything not on disk is gone. This is the
last chance to move it.

## Steps

### 1. See what actually happened

```
git status --short
git diff --stat
git log --oneline -10
```

### 2. Find the gaps

Walk back over the session and list every point where:

- a choice was made between options
- something was tried and abandoned
- the user objected, corrected you, or changed direction
- scope moved

For each, check whether a record exists in `docs/project-memory/`. Most of the
gaps will be rejections and pivots, because those feel like conversation rather
than output and are the first thing to be lost.

### 3. Write the missing records

Use the `decision-ledger` skill. Do not batch unrelated decisions into one
record to save time — one decision, one file.

Where you are reconstructing reasoning from earlier in the session, mark it:
`Reconstructed at session end; confirm before relying on it.` An honest
reconstruction is useful. A reconstruction passed off as a contemporaneous
record is a trap for the next reader.

### 4. Update the state file

Rewrite `docs/project-memory/00-PROJECT-STATE.md` so it describes reality now:
what is done, what is in progress, what is blocked, what is next. Keep it under
150 lines — move detail into numbered records and leave pointers.

### 5. Append to the journey

One dated entry in `docs/project-memory/JOURNEY.md`: what was attempted, what
was chosen, what was thrown away and why, and any verbatim user pushback.

### 6. Report what you could not capture

Tell the user plainly what you were unsure about or could not reconstruct. A
gap that is named can be filled by the user in thirty seconds. A gap that is
silently papered over becomes a wrong fact in the record.
