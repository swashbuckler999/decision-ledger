---
id: REJ-0004
type: rejection
title: Blocking Stop hook by default
date: 2026-11-24
status: rejected
related: [ADR-0003]
tags: [enforcement, ux]
---

# REJ-0004: Blocking Stop hook by default

## What was proposed
Make the Stop hook refuse to let the turn end when code changed without a
corresponding ledger record, using exit code 2 or a `decision: block` response.
Gemini's first answer suggested a Stop hook that checks `git diff` and reminds;
the stronger blocking form was considered during implementation.

## Discussion
Blocking is the only form of enforcement that genuinely cannot be ignored, and
the whole premise of ADR-0003 is that mechanisms which can be ignored get
ignored.

## Why it was rejected
Most turns that touch a file contain no decision worth recording — a rename, a
typo, a formatting pass. A gate that interrupts all of them to ask about a
decision that is not there trains the user to disable the plugin, and a disabled
plugin enforces nothing. The strict form also risks a continuation loop if the
guard condition is misjudged.

The asymmetry decided it: a missed record costs some reasoning, while a plugin
uninstalled in week one costs all of it.

## What was done instead
Quiet by default: a reminder via `additionalContext`, de-duplicated so the same
unrecorded change set is mentioned once rather than every turn. Blocking is
available behind `LEDGER_STRICT=1` for anyone who wants it, and honours
`stop_hook_active` so it cannot loop.

## Re-evaluation trigger
If real use shows the quiet reminder is reliably ignored and records are being
missed, revisit — but as an opt-in default for mature projects, never as the
out-of-box behaviour.

## User's own words
> n/a
