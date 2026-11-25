---
id: ADR-0036
type: decision
title: Fall back from python to python3 in the hook commands
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0031, ADR-0003]
tags: [install, cross-platform, hooks, silent-failure]
---

# ADR-0036: Fall back from python to python3 in the hook commands

## Discussion
All five hooks invoked `python`. On modern macOS and many Linux distributions
that command does not exist; only `python3` does. The plugin would install,
validate, list all five hooks, and do nothing — no briefing, no reminders, no
compaction rescue, and no error pointing at the cause.

This had been **documented** in three places and left unsolved, on the grounds
that detecting the right interpreter needed a cross-platform shell test nobody
had verified. The owner pushed back on exactly that: if the problem is known,
why ship a manual step instead of handling it?

Reading the documentation settled what is actually possible:

- **Shell form runs under `sh -c` on macOS and Linux, and Git Bash on
  Windows** — PowerShell only when Git Bash is absent. So `||` is available in
  the normal case on every platform.
- **There is no OS-conditional mechanism at all.** No platform field, no
  per-OS entries, no variable that reveals the platform. Per-OS configuration
  was never an option, which is worth recording so nobody looks again.
- The documented cross-platform pattern is `node` with exec form, which would
  mean rewriting every script in Node.
- A `userConfig` option could ask the user to pick an interpreter, which is
  explicit and puts the problem back on them.

## Decision
Each hook command becomes:

```
python "<script>" || python3 "<script>"
```

## Reasoning
Safe only because **every hook always exits 0.** All five end in `L.guard()`,
which swallows any exception and exits zero, so a non-zero status means one
thing: the interpreter itself is missing. The fallback therefore fires exactly
when it should and never double-runs — measured, not assumed: with `python`
present the hook runs once, and with the first name missing the second
produces correct output.

**The order is the part that needed evidence.** `python3` first looks more
natural for POSIX, and is wrong. On this Windows machine `python3` resolves to
a Microsoft Store stub at `WindowsApps/python3` which produces nothing useful;
putting it first would send every Windows hook into the stub. `python` first
means Windows never reaches it, and on macOS `python` is simply absent, so the
fallback fires immediately.

The residual risk is stated rather than hidden: on Windows **without** Git
Bash, hook commands run under PowerShell, and PowerShell 5.1 cannot parse
`||`. On such a machine this change turns a working plugin into a broken one.
That is the trade accepted here — a certain silent failure for most macOS and
Linux users, against a possible parse failure for Windows users who have no
Git Bash and have not upgraded to PowerShell 7 — and the README says exactly
what to do if it happens.

## Cost
A longer, uglier command string, and a Windows/PowerShell-5.1 scenario that
was previously fine and now needs one of three one-line fixes.

Neither branch is tested on macOS or Linux, because there is no such machine
here. The `||` semantics were verified under Git Bash, which the
documentation says is the same shell family used on POSIX.

## Re-evaluation trigger
If a Windows user without Git Bash reports hooks failing with a parse error,
the trade was wrong: revert to the single `python` form and solve the POSIX
case with a `userConfig` interpreter option instead.

## Conclusion & consequences
The most likely first experience on a Mac changes from "installs and silently
does nothing" to "works".

Also worth recording from the same reading, because it independently confirms
ADR-0031: the documentation states that these variables "aren't present in the
environment of commands Claude runs through the Bash tool." The empty
`CLAUDE_PLUGIN_ROOT` that the first live session found was specified
behaviour, not a quirk of this machine.

## Diversions & Pivots

## User's own words
> If you already know that why don't you have per OS code ready which will use
> the version as per OS? Is it possible for Skills?
