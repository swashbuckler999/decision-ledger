# Project state

**Updated:** 2026-11-25

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
- Five skills: `decision-ledger`, `cold-start`, `wrap-session`,
  `ledger-adopt`, `ledger-backfill` — done
- Five hooks: SessionStart, PreCompact, PostToolUse, Stop, UserPromptSubmit — done
- Record scaffolding and index generation scripts — done
- Tests — 200 checks, dependency-free, `python tests/test_hooks.py`
- The three adoption situations (fresh / undocumented / documented) —
  simulated against sandbox copies, all three now handled
- The three environments (worktree / no git / unusual config) — covered after
  an edge-case pass found eight defects, two of which lost data (ADR-0018..0020)
- Installed into the Forex ML project — **not yet**
- Published — **yes**, https://github.com/swashbuckler999/decision-ledger (public)

## How it works, in one paragraph

Five skills carry the protocol and the agent invokes them. Which one applies
depends on what the project already has: `ledger-backfill` for a working
project with no notes, `ledger-adopt` for one that keeps its own, and
`decision-ledger` for everything after that. `scan_project.py --propose` says
which, and will not guess at a changelog's order. Five hooks carry
the enforcement and fire whether or not the agent remembers: SessionStart
injects the briefing, PreCompact rescues reasoning before the context is
summarised away, PostToolUse keeps a raw activity trail, Stop notices code that
changed without a record, UserPromptSubmit catches decision-shaped phrasing in
the user's own words.

## Immediate next steps

1. Run it inside one live Claude Code session. Hook *command strings* are
   verified end to end; hook *registration* by the harness is not, and no
   skill has ever been invoked. This is the largest remaining unknown.
2. Judge the Stop and UserPromptSubmit hooks on noise — tune or drop
3. Consider submitting to Anthropic's plugin directory once it has real use
   behind it — claude.ai/settings/plugins/submit

## Open questions

- Does the Stop reminder earn its place, or does it become wallpaper? There
  are now three warnings on that hook, so the noise question is sharper.
- Are the mining weights in ADR-0016 too parochial? They are tuned on one
  developer's 82 projects, the same concern already noted against ADR-0011.
- Is `python` on PATH a safe assumption for installers on Windows?
- What other environment has this never run in? The last pass found every bug
  by asking that rather than by reading code. macOS and Linux are still
  untested, `python` vs `python3` included.
- Should `00-PROJECT-STATE.md` be generated from the records rather than
  maintained by hand? Currently hand-maintained — see ADR-0005.

## Constraints

Recorded permanently in **[CONSTRAINTS.md](CONSTRAINTS.md)** — read it before
pushing or changing the runtime assumptions. In short: pushing needs
`gh auth switch --user swashbuckler999` first; Python 3.9+ on PATH as `python`
with no other dependencies; commit identity is repo-local; the repo is public.

This section is a pointer, not the record. Constraints are append-only and do
not live in this mutable file.
