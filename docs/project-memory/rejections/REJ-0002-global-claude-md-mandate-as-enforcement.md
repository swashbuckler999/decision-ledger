---
id: REJ-0002
type: rejection
title: Global CLAUDE.md mandate as the enforcement mechanism
date: 2026-11-24
status: rejected
related: [ADR-0003]
tags: [enforcement]
---

# REJ-0002: Global CLAUDE.md mandate as the enforcement mechanism

## What was proposed
Add a directive to the global `~/.claude/CLAUDE.md` instructing the agent, on
every response, to load the memory skill and log any decision. DeepSeek
presented this as one of two main strategies; Gemini's second answer presented a
"CRITICAL OPERATING DIRECTIVE" prompt block as the whole mechanism, stating
explicitly that no native skill was required.

## Discussion
It is genuinely the cheapest thing to implement — a paragraph of text, no code,
no dependency, works instantly. CLAUDE.md is loaded every session, so the reach
is real.

## Why it was rejected
Instruction-following is strongest at the start of a session and weakest exactly
where this system earns its keep: deep into a long session, and across
compaction. Enforcement that degrades under load is not enforcement. The failure
mode being designed against is "the agent forgot", and the proposed fix is "tell
the agent not to forget".

Secondary objection: the owner's global CLAUDE.md is already long. A per-response
mandate competes for attention with every other standing rule in it, and
weakens them by crowding.

## What was done instead
ADR-0003: five hooks carry enforcement. A one-line pointer in CLAUDE.md is kept;
a mandate is not.

## Re-evaluation trigger
Do not revisit as a replacement for hooks. It remains correct as a supplement.

## User's own words
> n/a
