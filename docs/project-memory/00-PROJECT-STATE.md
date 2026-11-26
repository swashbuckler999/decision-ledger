# Project state

**Updated:** 2026-11-26

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
- Tests — 352 unit checks (`tests/test_hooks.py`) plus a 23-check
  twelve-turn session replay (`tests/simulate_session.py`), no model needed.
  One of the 318 is a footprint guard: the suite now fails if it writes
  anything into this project's own ledger, which it had been doing for two
  days without a single check noticing (ADR-0044)
- The three adoption situations (fresh / undocumented / documented) —
  simulated against sandbox copies, all three now handled
- The three environments (worktree / no git / unusual config) — covered after
  an edge-case pass found eight defects, two of which lost data (ADR-0018..0020)
- File states (BOM, pipes in titles, concurrency, unwritable targets) — covered
  after a third edge-case round found seven more, including a lost changelog
  entry under concurrent writes (ADR-0022..0024)
- README rebuilt as a landing page with an SVG banner and an agent-followable
  install path, `docs/AGENT-INSTALL.md` (ADR-0025)
- Local machine references redacted from all tracked files (ADR-0021); the
  repository's **history** still contains them
- Installed into a throwaway project and exercised from the installed copy —
  done; measured at 658 tokens always-on per session then (ADR-0026),
  and at ~927 by `claude plugin details` on 2026-11-26 after the
  ADR-0030 rewrite of all five `when_to_use` fields. Both figures are
  estimates from the same tool at different versions; neither has been
  checked against real usage
- Installed into a real project — **not yet**
- First live session with the plugin installed — **done** (ADR-0031). Hooks
  fire, SessionStart context reaches the model, all five skills are visible
  and `decision-ledger` ran end to end. It also found that every script path
  in every instruction was unreachable outside this checkout, plus three
  smaller defects, all now fixed
- Second live session verified the path fix on all four routes, and found the
  changelog being written twice — by the script and by the skill (ADR-0032)
- Third live session: `cold-start` and `wrap-session` both work, including
  wrap-session finding an unrecorded decision unprompted. Five more defects,
  all fixed — the Stop hook was reporting pre-existing untracked files as this
  session's work (ADR-0033), and three instructions assumed ledger files that
  do not exist yet (ADR-0034)
- Fourth live session: the ADR-0034 commit step and the ADR-0033 baseline
  collided — a committed record read as no record at all. Fixed (ADR-0035).
  Four sessions, four sets of defects; this one came from two correct fixes
  meeting, which no test of either could catch
- The full write path trialled on copies of three real corpus projects, with
  the originals proved untouched (ADR-0029)
- Skill *selection* simulated in a fresh context over three rounds; all five
  `when_to_use` fields rewritten after it found three overlaps, and one
  regression the rewrite itself introduced (ADR-0030)
- A decisions document is now read into records, not pointed at (ADR-0039)
- Version marker, `check_version.py` and a weekly upgrade notice, with no
  network call (ADR-0040); release notes in `docs/RELEASES.md`
- Two real installs by other sessions found `enable --scope` landing hooks
  user-wide (ADR-0041), a session unable to verify its own install
  (ADR-0042), and outside paths in the activity trail (ADR-0043)
- Reading the project cold found the suite writing into the project under
  test: 270 of the activity trail's 271 lines were `pre_compact` run by a
  test, and every run reset the live Stop-gate baseline (ADR-0044)
- The silent opt-in gate is gone: a project-scope enable now creates the
  ledger itself, and a project that has not opted in is told once instead of
  looking broken (ADR-0045, REJ-0009). Raised by the user, who pointed out
  that a correct install and a broken one looked identical
- Installed and enabled at project scope in this repository, with the enable
  verified in `.claude/settings.json` and the user setting left `false`
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

1. ~~Run one interactive session.~~ **Done** (ADR-0031). Registration is
   **verified** — `claude plugin details` reports all five skills and all five
   hooks, and every hook was driven from the installed copy and behaved
   (ADR-0026). What is still unproven: that the harness *calls* them during a
   real session, and that a skill is ever *chosen* on its own from its
   `when_to_use`. A skill nobody invokes is invisible and no test here can
   detect it.
2. Judge the Stop and UserPromptSubmit hooks on noise — tune or drop
3. Consider submitting to Anthropic's plugin directory once it has real use
   behind it — claude.ai/settings/plugins/submit

## Open questions

- Does the Stop reminder earn its place, or does it become wallpaper? There
  are now three warnings on that hook, so the noise question is sharper.
- Are the mining weights in ADR-0016 too parochial? They are tuned on one
  developer's 82 projects, the same concern already noted against ADR-0011.
- Is `python` on PATH a safe assumption for installers on Windows?
- Does the ADR-0045 notice land? It reads `.claude/settings.json`, whose shape
  is Claude Code's, and degrades silently to "not opted in" if that changes.
  Nothing here would notice.
- Should `.claude/settings.json` be committed? It would enable the plugin for
  anyone who clones a public repo without their asking. Currently untracked
  and not gitignored.
- Four live sessions, four sets of defects, and the rate is not dropping. The
  fourth came from two correct fixes interacting. How many clean runs are
  enough before submitting to the directory?
- The concurrency test fails about once in seven full-suite runs and never in
  isolation. Not diagnosed; the failure now reports full stderr so the next
  occurrence can be.
- What other environment has this never run in? The last pass found every bug
  by asking that rather than by reading code. macOS and Linux are still
  untested, `python` vs `python3` included.
- Should `00-PROJECT-STATE.md` be generated from the records rather than
  maintained by hand? Currently hand-maintained — see ADR-0005.

## Constraints

Recorded permanently in **[CONSTRAINTS.md](CONSTRAINTS.md)** — read it before
pushing or changing the runtime assumptions. In short: pushing needs
the repo owner's gh account to be active first; Python 3.9+ on PATH as `python`
with no other dependencies; commit identity is repo-local; the repo is public.

This section is a pointer, not the record. Constraints are append-only and do
not live in this mutable file.
