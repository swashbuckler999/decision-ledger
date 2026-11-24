---
id: ADR-0007
type: decision
title: Mechanical check for state-file loss
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0003, ADR-0006]
tags: [data-loss, enforcement]
---

# ADR-0007: Mechanical check for state-file loss

## Discussion
ADR-0006 closed the state-file hole with an instruction: move content somewhere
append-only before removing it. It also noted the weakness — by this project's
own ADR-0003, instructions degrade under load, and the hole being closed is
exactly a silent-loss hole, where nothing errors and nobody notices.

The deferred option was a script that compares the state file against its last
committed version and reports what was dropped. The owner asked for it to be
built rather than left pending.

## Decision
`scripts/check_state.py`. It diffs the working copy of `00-PROJECT-STATE.md`
against `git show HEAD:<path>`, and for every removed line asks whether that
content still exists anywhere else in the ledger. Lines that exist nowhere else
are reported as orphans. The Stop hook runs it on every turn.

Matching is by content-word overlap at a 0.6 threshold, ignoring short and
common words, not exact string equality — a line that was moved and lightly
reworded must still count as preserved.

## Reasoning
A check that runs without being invoked is the only kind that survives the
conditions this project is designed for. Running it from the Stop hook means it
fires on every turn whether or not anyone remembers it exists, which is the same
argument that produced the hook set in ADR-0003.

The Stop hook had to be restructured for this. It previously returned early when
any ledger file was touched, on the reasoning that a touched ledger means
something was recorded. That logic suppressed the new check exactly when it
matters, because editing the state file *is* touching the ledger. The two
warnings are now independent and can both fire in one turn.

Threshold choice: 0.6 overlap errs toward false positives. Flagging a line that
was in fact preserved costs the reader five seconds; missing one that was not
costs the thing the project exists to prevent. The asymmetry is not close.

## Cost
A heuristic, not a proof. Reword a line heavily while keeping its meaning and it
will be flagged; split one line into three and each fragment may fall under the
threshold. It also only compares against the last *commit*, so several
uncommitted rewrites in a row are judged against the oldest of them — which is
the conservative direction, but means the report can name content already
handled earlier in the session.

It cannot see loss in a project that is not a git repository. That case reports
"no committed version to compare against" and stays silent.

## Re-evaluation trigger
If the false-positive rate makes the warning ignorable, raise the threshold or
narrow it to lines in specific sections rather than abandoning it. If orphans
are still slipping through at 0.6, lower it.

## Conclusion & consequences
`check_state.py` is runnable by hand, referenced from the `wrap-session` skill,
and wired into the Stop hook. Tests cover both directions: a line moved to
`CONSTRAINTS.md` is not flagged, a line simply deleted is.

## Diversions & Pivots

## User's own words
> Build it.
