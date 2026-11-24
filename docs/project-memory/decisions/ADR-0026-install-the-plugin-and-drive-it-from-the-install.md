---
id: ADR-0026
type: decision
title: Install the plugin and drive it from the installed copy
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0003, ADR-0025, REJ-0004]
tags: [install, verification, live-trial, open-question]
---

# ADR-0026: Install the plugin and drive it from the installed copy

## Discussion
Every test so far ran scripts out of the working tree. The largest open
question in the briefing, named since the first week, was whether Claude Code
**registers** what the plugin declares — a question no amount of script testing
can answer.

A throwaway project was created outside any real repository: a git repo with a
README, one module, one commit. The local repository was added as a
marketplace, the plugin installed at project scope, and the project opted in
with the documented `mkdir`, plus a briefing carrying a deliberately unique
string and one rejection.

**Registration is confirmed by the harness itself.** `claude plugin details`
reports:

```
Skills (5)  cold-start, decision-ledger, ledger-adopt, ledger-backfill, wrap-session
Hooks  (5)  SessionStart, PreCompact, PostToolUse, Stop, UserPromptSubmit
Always-on:  ~658 tok added to every session
```

All five skills are discovered. All five hooks are registered. The always-on
cost is a number this project had never measured: **658 tokens in every
session**, before any skill is invoked.

Every hook was then driven from the **installed** copy, with
`${CLAUDE_PLUGIN_ROOT}` expanded as the harness expands it, using each event's
real payload:

| Hook | Result |
|---|---|
| SessionStart | 895 characters of context, containing the briefing's unique string, the rejection's title, and the do-not-re-propose instruction |
| PreCompact | Emitted its preservation instruction |
| PostToolUse | Wrote `Edit \`feed.py\`` to the activity trail, path correctly relative |
| Stop | Silent — correct: a briefing exists, and nothing outside the ledger had changed |
| UserPromptSubmit | Fired on "lets use Parquet instead of CSV", which is the diversion-shaped phrasing it exists to catch |

The ADR-0024 activity fix was confirmed in a real install: the `.gitignore` was
created and `git check-ignore` shows the trail is ignored.

**What did not happen: a model turn.** `claude -p` failed at authentication
before any hook ran, because the CLI in this environment is routed to a
third-party model gateway whose key is rejected. That is the environment's
configuration, not the plugin's, and not something to work around by touching
someone's credentials.

## Decision
Install into a throwaway project and exercise the installed copy. Treat
registration as **verified** and the live model turn as **still open**, and say
exactly which is which.

## Reasoning
The distinction is the whole point of doing this. Three claims were untested,
and the trial separates them:

1. *Does the harness register the skills and hooks?* — **Yes.** Answered
   directly by the harness's own inventory, not by inference.
2. *Do the registered commands work from where the harness invokes them?* —
   **Yes.** Driven from the install path with the harness's own variable
   expansion, which is a different thing from running them out of the source
   tree, where a packaging mistake is invisible.
3. *Does the harness actually call them during a session, and does the model
   act on what they emit?* — **Unknown.** This needs a working model and cannot
   be faked.

Claiming the trial "passed" would collapse all three. Two of them genuinely
did.

## Cost
The remaining unknown is the most behavioural one. Whether a skill's
`when_to_use` causes it to be *chosen* at the right moment, and whether the
Stop hook's three warnings read as useful or as noise, are judgements only a
real session produces. REJ-0004 deferred the noise question to real use, and it
is still deferred.

Adding the local path as a marketplace is a change to the environment that has
to be undone by hand if it is not wanted.

## Re-evaluation trigger
When a session runs with the plugin installed and a working model, record what
the briefing looked like in practice and whether any skill fired unprompted. If
no skill is ever chosen on its own, the `when_to_use` fields are wrong and the
skills need rewriting, not the hooks.

## Conclusion & consequences
The briefing's long-standing first next step — "run it inside one live Claude
Code session" — is now two steps, and the first is done. What remains is
narrow and clearly stated: one interactive session with a working model.

The 658-token always-on cost is new information and belongs in the install
guidance, because it is paid by every session in every project where the plugin
is enabled.

## Diversions & Pivots

## User's own words
> Do the trial
