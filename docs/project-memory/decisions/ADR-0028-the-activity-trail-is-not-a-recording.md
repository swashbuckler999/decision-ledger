---
id: ADR-0028
type: decision
title: The activity trail is not a recording
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0003, ADR-0027, REJ-0004]
tags: [stop-hook, silent-failure, first-run]
---

# ADR-0028: The activity trail is not a recording

## Discussion
The first run of the session simulation (ADR-0027) found the Stop gate silent
at the turn it exists for: code had changed, nothing had been recorded, and it
said nothing.

The gate sorted changed files into two buckets:

```python
ledger_touched = [f for f in files if L.is_ledger_path(f, payload)]
code_touched   = [f for f in files if not L.is_ledger_path(f, payload)]
if not code_touched or ledger_touched:
    return None
```

Any dirty ledger path counted as "something was recorded". The activity trail
is a ledger path — and it is written by the **PostToolUse hook, automatically,
on every file edit.** On the first edit in a freshly installed project the hook
creates `activity/.gitignore`, git reports it as untracked, and the gate
concluded the session had recorded something.

So the reminder was suppressed in the first session of every new project — the
session where the habit is being established and the reminder matters most.
After that first commit the trail is ignored and the gate recovers, which is
why it never showed up: the failure is confined to the run nobody tests twice.

The defect is conceptual rather than clerical. `is_ledger_path` answers *does
this file belong to the ledger*, and the gate needed *did a human record
reasoning here*. Those are different questions, and one function was answering
both.

## Decision
A second predicate, `is_recording_path`: true for a ledger path that is not
the activity trail.

The gate now sorts into three buckets. Recordings satisfy it, code triggers it,
and the activity trail is **ignored entirely** — it is neither, so it can
neither nag about the plugin's own bookkeeping nor silence a real warning.

## Reasoning
Excluding the trail rather than special-casing `.gitignore` is the fix that
matches the reason. Every file in that directory is written by a hook without
anyone deciding anything; none of it is evidence that reasoning was recorded.
A narrower fix aimed at the `.gitignore` would leave the same hole open for the
daily trail files in any project that does not ignore them.

Ignoring rather than counting as code matters too. The trail changes on
essentially every turn, so counting it as code would make the gate fire
constantly — the behaviour REJ-0004 says gets the plugin uninstalled.

## Cost
Two predicates where there was one, and a caller now has to know which question
it is asking. The distinction is real but easy to get wrong in new code.

## Re-evaluation trigger
If another ledger path is added that a hook writes automatically, it belongs on
the non-recording side, and the two-way split should become an explicit list of
which roles count as recordings.

## Conclusion & consequences
The gate warns on the first edit of a new project again. Twelve checks pin it:
eight in the unit suite, including that the trail is still a ledger path and
still not a recording path, and the simulation turn that found it.

This is the fourth silent data-or-behaviour failure in this project, and the
pattern holds exactly. The CRLF rewrite, the index overwriting a hand-written
file, the changelog dropping an entry while reporting success, and now a
reminder that simply never arrives. Every one of them reported success.

## Diversions & Pivots

## User's own words
> Can we push it first, and check if we can do any sims CLI test?
