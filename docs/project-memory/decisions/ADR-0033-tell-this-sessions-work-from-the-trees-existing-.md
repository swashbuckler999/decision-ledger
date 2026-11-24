---
id: ADR-0033
type: decision
title: Tell this session's work from the tree's existing mess
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0028, REJ-0004]
tags: [stop-hook, false-positive, live-session, noise]
---

# ADR-0033: Tell this session's work from the tree's existing mess

## Discussion
The third live session exercised `cold-start` and `wrap-session` — the two
skills that had never been invoked — and both did what they claim. It then
reported a defect in the Stop hook instead.

At the end of the turn the gate flagged `.claude/settings.json` as an
unrecorded change. The session had never written to it: the file was untracked
before the session began, and its own opening `git status` proved it. The real
decision from earlier in the session had already been recorded, so the hook's
**only** output that turn was a false positive.

The cause is a mismatch between what the gate measures and what it claims.
`git status --porcelain --untracked-files=all` answers *what is not committed*.
The gate presents the answer as *what you changed and did not record*. On a
clean fixture those are the same list; on a real working tree they are not.
Editor settings, local scratch files, build output not yet ignored, a file
someone modified yesterday and left — every one of them appears at the end of
every session, forever.

That is worse than it sounds. The reminder that matters is a line in a list,
and it looks exactly like the lines that do not matter. A user who sees four
irrelevant paths every turn stops reading the list, and the one turn it
reports a real unrecorded decision is the turn they skim past. REJ-0004
rejected a blocking Stop hook because a wall gets the plugin uninstalled
within a day; this is the same failure arriving quietly instead.

## Decision
SessionStart records a baseline: every dirty path with its size and mtime,
written to the per-worktree git directory. The Stop gate reports a path only
when it is absent from that baseline, or when its fingerprint has moved.

With no baseline — git unavailable, or SessionStart never ran — every dirty
path is reported, exactly as before.

## Reasoning
Size and mtime rather than a content hash because the gate runs at the end of
every turn and a hash of a large tree is not free. The pair is enough: a file
the session edited has a different mtime, and in the rare case of a
same-second same-size rewrite the cost is one missed reminder, not a wrong
one.

Falling back to over-reporting when the baseline is missing is the deliberate
asymmetry. An extra reminder is noise; a missed one is the unrecorded decision
this plugin exists to catch. When the hook genuinely cannot tell, it should
err toward the failure that is merely annoying.

The baseline lives in the git directory for the same reason the de-duplication
marker does (ADR-0018): it is per-worktree state, it is already outside the
working tree, and it cannot accidentally be committed.

## Cost
A file that was already dirty and is edited again within the same second of
its recorded mtime will not be reported. Rare, and it fails toward silence,
which is the direction this ADR otherwise argues against — but the alternative
is hashing every dirty file on every turn.

A session whose SessionStart hook did not run gets the old behaviour, so the
noise can still appear; it just no longer appears for everyone, always.

## Re-evaluation trigger
If a real unrecorded change is ever found to have been suppressed by the
baseline, replace size and mtime with a content hash for files under some size
and accept the cost.

## Conclusion & consequences
Nine checks pin it, including the two that matter in opposite directions: a
file modified *before* the session is not reported, and a file that existed
before but was edited *during* the session is.

Three live sessions have now produced three classes of defect, and this one
completes a pattern worth naming. Fixtures are clean; real working trees are
not. Every test in this project builds a repository containing exactly what
the test intends, and the one thing no fixture ever has is **somebody else's
mess** — which is the normal state of every project this will ever be
installed into.

## Diversions & Pivots

## User's own words
> Fix those five and run the fourth session
