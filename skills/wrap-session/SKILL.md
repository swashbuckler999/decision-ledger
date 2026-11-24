---
name: wrap-session
description: Flush the session's unrecorded reasoning into the ledger before the context is lost. Checks what changed, finds decisions and rejections that were discussed but never written down, writes the missing records and refreshes the project state file.
when_to_use: Use when the user signals the session is over -- "that is enough for today", "I am off", "see you tomorrow", "done for now", "wrapping up", "sign off", "save the state", "hand this over now" -- or asks what is unrecorded. A handover mentioned as a future plan is not a session ending: if it changes the plan use decision-ledger, otherwise just carry on. This flushes a WHOLE session; for one decision as it happens, use decision-ledger.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(python *), Bash(git diff *), Bash(git status *), Bash(git log *)
---

# Wrap session

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

### 4. Update the state file — move it before you remove it

`docs/project-memory/00-PROJECT-STATE.md` is the only mutable file in the
ledger, which makes it the only place content can be lost. Before rewriting it,
check every line you are about to drop:

| What you are removing | Where it must already exist |
|---|---|
| A decision or its reasoning | an ADR |
| An idea that was turned down | a REJ |
| A scope change | a CR |
| A constraint, access rule or environment fact | `CONSTRAINTS.md` |
| An unresolved question still worth asking | keep it, or move it to `JOURNEY.md` |
| Narrative — what was tried, what was abandoned | `JOURNEY.md` |

If it exists nowhere else, **write it somewhere append-only first**, then
remove it. If the destination file does not exist yet, create it and write the
entry: "where it must already exist" names the destination, not a
precondition. A live session read it as a precondition, found the only copy of
a hard-won environment fact sitting in the state file with no `CONSTRAINTS.md`
to move it to, and correctly refused to delete it -- which left the one thing
this table exists to rescue stranded in the one file that gets rewritten. Dropping the last copy of something from a mutable file is silent:
nothing errors, nothing warns, and the loss is only discovered when someone
rediscovers the fact the hard way.

To check rather than trust your judgement:

```
python "<plugin root>/scripts/check_state.py" --project "<project root>"
```

It compares the state file against its last committed version and lists lines
that were removed and exist nowhere else in the ledger. It errs toward false
positives — rewording a line may flag it — so read what it reports rather than
acting on the exit code alone.

Then rewrite the file so it describes reality now — what is done, in progress,
blocked, and next. Keep it under 150 lines by moving detail out into records
and leaving pointers, never by deleting.

If the state file was written by someone else and uses different sections,
keep their structure. Update the content within it; do not convert it to this
skill's layout.

### 5. Append to the journey

One dated entry in `docs/project-memory/JOURNEY.md`: what was attempted, what
was chosen, what was thrown away and why, and any verbatim user pushback.

### 6. Report what you could not capture

Tell the user plainly what you were unsure about or could not reconstruct. A
gap that is named can be filled by the user in thirty seconds. A gap that is
silently papered over becomes a wrong fact in the record.

### 7. Commit, if the project's conventions allow it

The ledger is only safe once it is committed: `00-PROJECT-STATE.md` is
rewritten in place, so until then the previous version exists only in git and
the new one only in the working tree.

Follow whatever the project says about committing -- a `CLAUDE.md`, a
contributing guide, or the user's own instruction. If nothing grants that
permission, do not commit: say the ledger is written and uncommitted, and
leave it to the user. Never commit anything beyond the ledger files you just
wrote, and never push.

This step was missing, and a live session wrapping up had to fall back on a
global convention to know whether committing was wanted.
