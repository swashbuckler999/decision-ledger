# Project state

**Updated:** 2026-11-24

Read this first. It is capped at 150 lines on purpose: it is the briefing, not
the history. Detail lives in the numbered records; see `INDEX.md` for the map.

## What this is

`decision-ledger` — a Claude Code plugin that records every discussion,
decision, rejection, change request and mid-flight pivot as numbered,
append-only files in the repository, and uses hooks to make the recording
happen rather than hoping the agent remembers.

The target it is built against: a person or an agent with no memory of the
originating conversation reads `docs/project-memory/` and is as current as the
author — including knowing which obvious-looking ideas have already been tried
and have already failed.

## Current status

Working skeleton, not yet exercised in anger.

- Plugin manifest, marketplace entry and layout — done
- Three skills: `decision-ledger`, `cold-start`, `wrap-session` — done
- Five hooks: SessionStart, PreCompact, PostToolUse, Stop, UserPromptSubmit — done
- Record scaffolding and index generation scripts — done
- Smoke tests — done
- Installed into the Forex ML project — **not yet**
- Published — **yes**, https://github.com/swashbuckler999/decision-ledger (public)

## How it works, in one paragraph

Three skills carry the protocol and the agent invokes them. Five hooks carry
the enforcement and fire whether or not the agent remembers: SessionStart
injects the briefing, PreCompact rescues reasoning before the context is
summarised away, PostToolUse keeps a raw activity trail, Stop notices code that
changed without a record, UserPromptSubmit catches decision-shaped phrasing in
the user's own words.

## Immediate next steps

1. Install into the Forex ML project and run it for a real session
2. Judge the Stop and UserPromptSubmit hooks on noise — tune or drop
3. Consider submitting to Anthropic's plugin directory once it has real use
   behind it — claude.ai/settings/plugins/submit

## Open questions

- Does the Stop reminder earn its place, or does it become wallpaper?
- Is `python` on PATH a safe assumption for installers on Windows?
- Should `00-PROJECT-STATE.md` be generated from the records rather than
  maintained by hand? Currently hand-maintained — see ADR-0005.

## Constraints

Recorded permanently in **[CONSTRAINTS.md](CONSTRAINTS.md)** — read it before
pushing or changing the runtime assumptions. In short: pushing needs
`gh auth switch --user swashbuckler999` first; Python 3.9+ on PATH as `python`
with no other dependencies; commit identity is repo-local; the repo is public.

This section is a pointer, not the record. Constraints are append-only and do
not live in this mutable file.
