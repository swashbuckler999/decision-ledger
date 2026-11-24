---
id: ADR-0018
type: decision
title: Recognise worktrees and submodules as git
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0015, ADR-0016, REJ-0004]
tags: [git, worktree, edge-cases, corpus]
---

# ADR-0018: Recognise worktrees and submodules as git

## Discussion
An edge-case pass after the three-situation simulation asked what environments
the plugin had never been run in. The first answer was a linked git worktree,
and it was wrong in every component that looked at git.

`.git` is a directory only in a primary checkout. In a linked worktree and in
a submodule it is a plain **file** containing `gitdir: <path>`. Three places
tested `(root / ".git").is_dir()`:

- `scan_project.scan` reported `is_git: false`, so the scanner printed *"Not a
  git repository: the Stop hook and orphan detection stay silent here"* about a
  repository with full history, and the `NOT greenfield` backfill advice from
  ADR-0015 could never fire.
- `mine_history.scan` returned zero commits. Reproduced on a sandbox worktree
  over a six-commit repository: `main` reported 7 commits and 6 candidates, the
  worktree reported none.
- `stop_gate.already_reported` wrote its de-duplication marker to
  `cwd/.git/ledger-*`. With `.git` a file, `mkdir` raised, the marker was never
  written, and the exception was swallowed by design. Measured: three
  consecutive Stop hooks in a worktree warned three times with identical text,
  where the same test in a primary checkout warned once.

Claude Code's own desktop sessions run in worktrees, so this was a default
environment rather than an exotic one. One project in the 82-project corpus is
a linked worktree too, and the survey had been counting it as unversioned: 39
git repositories under the old test, 40 under the new one.

A second defect sat behind the first. `mine_history.scan`'s non-git early
return built a dict with fewer keys than the normal one, so `--summary` died
with `KeyError: 'first_commit'` — on the exact command `ledger-backfill` gives
as its first instruction.

## Decision
`L.is_git_repo(root)` tests `.exists()`, not `.is_dir()`, and all three callers
use it.

`L.git_dir(root)` asks git itself, via `git rev-parse --absolute-git-dir`, and
the Stop hook writes its marker there. Result cached per root, since three
warnings call it per hook.

`mine_history` returns the same keys on every path, from one `EMPTY` template,
and `summary()` says plainly when there is no repository or no commits.

## Reasoning
Asking git beats deriving the path. A worktree's per-worktree git directory
lives at `<primary>/.git/worktrees/<name>`, and a submodule's somewhere else
again; parsing the `gitdir:` line would work today and is one more format to
track. `rev-parse` is the supported question and costs one subprocess per hook.

The marker belongs in the per-worktree git directory specifically, not the
shared one: two worktrees of the same repository have different working trees
and should nag independently.

`git_dir` returning None now means **warn**, not stay quiet. A hook that
cannot remember whether it has already spoken should repeat itself rather than
go silent — the cost of the first is noise, the cost of the second is the
unrecorded change this plugin exists to catch.

The missing-key crash is the more instructive half. Two return paths from one
function had different shapes, and the shape only mattered on the path that
never ran in a test. A fixture directory is a git repository; nobody had asked
what the miner does when pointed somewhere that is not.

## Cost
One `git rev-parse` per Stop hook, cached. `is_git_repo` is now true for a
stray `.git` file that is not a real gitlink, where `git_dir` returns None and
the hook warns every turn rather than once — noisier, and the right direction
to fail in.

## Re-evaluation trigger
If the Stop hook is found repeating itself in an environment where `git
rev-parse` works, the marker location is wrong rather than the detection.

## Conclusion & consequences
The plugin works in a worktree and a submodule. Fourteen checks pin it,
including that `.git` really is a file in the fixture — without that assertion
the test would pass against a primary checkout and prove nothing.

The wider lesson, matching ADR-0016's: the corpus found this one too. It was
not visible in any fixture, because every fixture this project writes is a
primary checkout.

## Diversions & Pivots

## User's own words
> Please check if we are missing any edge cases?
