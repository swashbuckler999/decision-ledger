---
id: ADR-0031
type: decision
title: Anchor every script path the instructions give
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0003, ADR-0012, ADR-0023, ADR-0026, ADR-0030]
tags: [install, skills, silent-failure, live-session]
---

# ADR-0031: Anchor every script path the instructions give

## Discussion
The first live session with the plugin installed found the defect that every
other form of testing had been structurally unable to see.

Every instruction in this project that tells an agent or a user to run one of
its scripts said `python scripts/<name>.py`. A bare relative path. In a real
installation the scripts live in the **plugin**, and the agent's working
directory is the **user's project**, so that resolves to
`<their repo>/scripts/<name>.py` and finds nothing.

Twenty-one call sites: nine in the five skills, eight in `README.md` and the
two install guides, and six usage strings in the scripts themselves.

It had never shown up because every test, every simulation and every corpus
pass ran from the development checkout, where `scripts/` happens to resolve.
The session reported it plainly: *"`scripts/new_record.py` does not exist"* —
from where it was standing, true.

The consequence is worse than a missing file, because the skill tells the
agent what to do when the script is unavailable. It fell back to allocating
the id by hand and writing the changelog directly. **So the atomic id
allocation from ADR-0023, the CRLF-preserving insert from ADR-0010 and the
adoption-aware ordering were all bypassed, and the session reported success.**
Months of careful work on the deterministic layer, unreachable in production.

Asked to establish the right fix empirically, the session returned three facts
that decided the design:

1. **`CLAUDE_PLUGIN_ROOT` is empty in a tool shell.** The harness substitutes
   it for hook commands — all five hooks fired, which is why the hooks were
   never affected — but not in the environment of a `Bash` call. Worse, in Git
   Bash `"$CLAUDE_PLUGIN_ROOT/scripts/x.py"` expands to `/scripts/x.py`, which
   MSYS rewrites to a path inside the Git installation. It fails only because
   nothing happens to live there.
2. **`scripts/` and `skills/` are siblings** at the plugin root, and a skill is
   given its own absolute base directory, so `../../scripts/` is a reliable
   anchor from inside skill prose.
3. **A second, independent bug.** `project_dir()` falls back to `os.getcwd()`
   when its three environment variables are unset, which in an agent's shell
   they all are — and the harness **reset that session's working directory
   mid-session**. Fixing only the script path would have scaffolded records
   into an unrelated folder, silently.

## Decision
Three changes, because one would not have been enough.

**The SessionStart hook hands over both absolute paths.** It runs where
`${CLAUDE_PLUGIN_ROOT}` works and can locate itself, so the briefing now
carries the scripts directory and the project root, with a runnable example.
The agent is told the answer instead of deriving it.

**A `--project <path>` flag** on `new_record.py`, `build_index.py` and
`check_state.py`, and every instruction passes it. A flag, not an environment
variable: `VAR=x command` is POSIX and does nothing in PowerShell, and the
agent does not choose its shell.

**All 21 call sites anchored**, with the fallback written into each skill: use
the paths from the context block; if it is absent — as it is in a project with
no ledger yet — the plugin root is two levels up from the skill's own base
directory.

## Reasoning
Having the hook supply the path is the part that makes this robust rather than
merely correct. Every other candidate asks the agent to work something out: an
environment variable that turns out to be empty, a relative path that depends
on where it is standing, a discovery command that depends on the install
layout. The hook already knows, with certainty, and is already speaking to the
agent at the start of every session.

The fallback exists because the hook is silent in exactly the case the
adoption skills are for. A project with no ledger gets no briefing, so
`ledger-adopt` and `ledger-backfill` cannot rely on it, and they are the two
skills a brand-new user reaches first.

The `--project` flag is the lesson of the second bug generalised: **a script
that infers where to write from ambient state will eventually write somewhere
else.** Nothing about the failure is visible — correct exit code, a file
created, a path printed. It took a harness that moves the working directory
out from under a session to expose it.

## Cost
Every command in the instructions is now longer and carries two placeholders a
reader must substitute. That is worse to read and worse to copy-paste, and it
is the price of being correct outside one checkout.

The `<plugin>` placeholder asks the user to find their install path, which the
README now explains with `claude plugin details`.

## Re-evaluation trigger
If Claude Code starts exporting `CLAUDE_PLUGIN_ROOT` into tool shells, collapse
all of this to that one variable and keep the `--project` flag.

## Conclusion & consequences
Zero unanchored script paths, zero absolute machine paths, zero dead
references. Thirteen checks pin it, and one of them is a **repository-wide
scan that fails the suite if a bare `python scripts/...` is ever added back**
— the regression guard matters more than the fix, because this bug was
invisible from inside the checkout for the project's entire life.

The wider lesson, and the reason the live trial was worth insisting on: **the
development checkout is a privileged environment, and testing in it is testing
the one place the bug cannot appear.** Four rounds of edge cases, 241 unit
checks, a twelve-turn session replay and four corpus passes all ran inside it.
None of them could have found this. One real session found it in minutes.

## Diversions & Pivots

## User's own words
> So please check if any such bare relative path, or any wrong absolute path
> is there!!
