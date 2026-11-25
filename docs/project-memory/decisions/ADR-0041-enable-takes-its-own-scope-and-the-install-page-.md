---
id: ADR-0041
type: decision
title: Enable takes its own scope, and the install page must say so
date: 2026-11-26
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0025, ADR-0026]
tags: [install, scope, docs]
---

# ADR-0041: Enable takes its own scope, and the install page must say so

## Discussion

Found in live use, installing the plugin into a real project by following
`docs/AGENT-INSTALL.md` literally, as an agent is meant to.

The plugin was **already installed at project scope but disabled** — an
earlier session had added the marketplace and installed it, and nobody enabled
it. The page has no step for that state. Its step 2 covers `install --scope`
carefully and warns, in bold, never to choose `--scope user` unprompted,
because it starts a Python interpreter on every prompt in every repository.

The obvious next command was:

```
claude plugin enable decision-ledger@sayan-skills
```

which reported:

```
✔ Successfully enabled plugin: decision-ledger (scope: user)
```

`enable` has its own `--scope`, defaulting to auto-detect rather than to the
scope the plugin was installed at. It wrote
`"decision-ledger@sayan-skills": true` into `~/.claude/settings.json`.

**And `claude plugin list` still said `Scope: project`.** The listing reflects
where the install is declared, not where the enable flag went — so the
verification the page gives ("`claude plugin list` includes
`decision-ledger`") passes while the actual outcome is the user-wide one the
page forbids.

## Decision

`AGENT-INSTALL.md` gains **step 2a** for the installed-but-disabled state. It
requires `--scope` on `enable`, states that `enable`'s scope defaults to
auto-detect and is not inherited from the install, warns that
`claude plugin list` will not reveal where the flag landed, gives the two
`grep` commands that will, and gives the disable/enable pair that moves it.

Step 2's check becomes "included **and** `Status: enabled`", so the disabled
state is detected rather than walked past.

## Reasoning

A page written for agents and described as deterministic has to be
deterministic about the state the project is actually in, and
installed-but-disabled is a state it will meet often — anyone who tried the
plugin once and did not finish is in it.

The failure is worse than a missing step, because **every check passes.** The
command prints a success line, the listing says `project`, and the hooks run
everywhere. An agent following the page exactly produces the outcome the page
spends a paragraph forbidding, without ever typing `--scope user`. That is a
documentation defect in the same class as ADR-0014: saying nothing, and
letting the reader draw a wrong conclusion from a clean result.

Alternatives, and why each lost:

- **Detect and correct it in a script.** The scripts deliberately do not touch
  Claude Code's settings files, and a plugin that rewrites a user's global
  config to fix its own scope is a plugin they uninstall.
- **Leave it; the user can fix it.** The user cannot see it. Nothing surfaces
  the discrepancy, and the cost lands in unrelated repositories.
- **Only add a troubleshooting row.** Insufficient alone — troubleshooting is
  read after noticing a symptom, and this symptom is invisible. A row was
  added as well, for whoever arrives from that direction.

## Cost

Step 2 grows, and the install page is already long — length is its own risk
when the reader is an agent with a budget. Accepted because the addition is a
state-machine branch rather than prose, and because the alternative is a
silent wrong outcome.

The verification names `~/.claude/settings.json` and `.claude/settings.json`,
which couples the page to Claude Code's current settings layout. If that
changes, the step goes stale — loudly, since the greps will find nothing,
rather than quietly.

## Re-evaluation trigger

`claude plugin enable` inheriting the install scope by default, or
`claude plugin list` reporting where the enable flag actually lives. Either
makes 2a's warning unnecessary, though the installed-but-disabled branch is
still worth keeping.

## Conclusion & consequences

- Always pass `--scope` to `enable`, matching the install.
- Never trust `claude plugin list`'s `Scope:` as evidence of where the enable
  flag landed. Check the settings files.
- The correct end state for a project-scope install is `true` in the project's
  `.claude/settings.json` and absent-or-`false` in the user's.

## Diversions & Pivots

<!-- Append-only. Empty at creation. Never edit entries above this line. -->

## User's own words

n/a — found by an agent following the install page, not raised by the user.
The instruction was only to install the plugin and run it.
