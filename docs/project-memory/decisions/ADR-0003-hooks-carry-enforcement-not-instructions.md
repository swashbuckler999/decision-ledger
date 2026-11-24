---
id: ADR-0003
type: decision
title: Hooks carry enforcement, instructions carry the protocol
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0001, REJ-0002, REJ-0004]
tags: [enforcement, hooks]
---

# ADR-0003: Hooks carry enforcement, instructions carry the protocol

## Discussion
Both external opinions leaned on prompt-based enforcement. DeepSeek proposed a
global CLAUDE.md mandate as one of two main strategies; Gemini proposed a
"CRITICAL OPERATING DIRECTIVE" block as the entire mechanism and stated that no
native skill was needed.

The objection is that instruction-following degrades exactly where this system
is most needed: late in a long session, and across compaction. A mechanism that
fails under load is not a mechanism.

## Decision
Five hooks carry enforcement; the skills carry the protocol.

| Hook | Job |
|---|---|
| SessionStart | Inject the cold-start briefing, including settled rejections |
| PreCompact | Flush a checkpoint and steer what the summary preserves |
| PostToolUse | Keep a raw activity trail for later reconstruction |
| Stop | Notice code changed with nothing recorded |
| UserPromptSubmit | Catch decision-shaped phrasing in the user's own words |

## Reasoning
Hooks are executed by the harness, not chosen by the model, so they fire whether
or not the agent remembers. PreCompact matters most: compaction preserves
conclusions and discards the argument that produced them, and neither external
opinion mentioned it at all. Its stdout becomes the compaction instructions,
capped at 10,000 characters, so one hook both writes to disk and steers the
summary.

Instructions still matter for judgement the harness cannot encode: what deserves
a record, how to write the reasoning section, when a diversion is an append
rather than a new file.

## Cost
Five hook processes per session touchpoint, a Python dependency, and a real
noise risk from the Stop and UserPromptSubmit hooks. Mitigated by making both
quiet by default and narrowly triggered; to be judged after real use.

## Re-evaluation trigger
If the Stop or UserPromptSubmit reminders are ignored in practice, they are
noise and should be cut rather than tuned forever.

## Conclusion & consequences
Every hook exits 0 on any unexpected failure. A memory aid that can crash the
session is worse than no memory aid.

## Diversions & Pivots

### 2026-11-24 - SessionStart no longer fires on resume
**Catalyst:** measuring the plugin's token cost on request. The briefing is
~1,490 tokens and the matcher was `""`, which fires on every source including
`resume` - where the conversation is already in context and the briefing is
pure waste.
**What changed:** matcher is now `startup|clear|compact|fork`.
**What did not change:** the briefing still fires after compaction, which is the
case it exists for.
**Measured:** ~1,892 tokens resident per session, under 1% of a 200k context;
~17 tokens per additional record.

## User's own words
> n/a
