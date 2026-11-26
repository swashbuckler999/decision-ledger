---
id: ADR-0045
type: decision
title: Installing into a project is the opt-in, and silence is never the answer
date: 2026-11-26
status: accepted
supersedes: []
superseded_by: null
related: [REJ-0009, ADR-0025, ADR-0041, ADR-0042, REJ-0006, ADR-0008]
tags: [install, hooks, ux]
---

# ADR-0045: Installing into a project is the opt-in, and silence is never the answer

## Discussion

REJ-0009 rejects the silence that made a correct install indistinguishable
from a broken one. This records what replaces it.

The user's proposal was "auto-start after install". Taken literally across
both scopes it would be wrong: an account-wide install is live in every
repository, and creating `docs/project-memory/` in all of them is the
behaviour the install guide already warns gets a plugin uninstalled. But the
proposal is right for the scope it was made about, and the diagnosis
underneath it is right for both.

So the question split in two. Who asked for a ledger in this project? And
what should happen when nobody did?

## Decision

Two changes, both in `session_start.py`, which is the only hook that runs once
per session and so the only one that can speak without becoming noise.

**1. A project-scope enable is the opt-in.** When `.claude/settings.json` (or
`settings.local.json`) in the project switches this plugin on, the ledger is
created on the next session start: the three record directories plus a
placeholder `00-PROJECT-STATE.md`. The user named this repository; that is
consent.

**2. When nobody asked, say so once.** Any other project with no ledger gets
one notice, the first time it is seen: a `systemMessage` for the user and an
`additionalContext` line telling the model to mention it once and then carry
on. Nothing is written. The notice is remembered in the plugin's own data
directory, keyed by a hash of the project path, so it is once per project
rather than once per session.

**Auto-creation never runs in a project that already keeps notes.** A cheap
check — file names in the root and one level into `docs/`, plus the known
memory directories — and if anything is found, the notice names `ledger-adopt`
and writes nothing, even though the project asked. Creating
`docs/project-memory/` beside somebody's `docs/adr/` is the duplication that
skill exists to prevent, and REJ-0006 settled that existing documents are
pointed at, never duplicated.

## Reasoning

A placeholder briefing rather than bare directories, because **git does not
track empty directories**. Create only the three folders and `git status` is
clean, there is nothing to commit, and the user is left exactly where they
started — unable to tell a working install from a broken one, which is the
whole defect. The placeholder therefore says, in its first lines, that nobody
has written it yet and that an empty section is not a statement that there is
nothing to say. Writing anything more would be inventing the project's state,
which every skill in this plugin is told not to do.

The notice goes through `systemMessage` **and** `additionalContext`. The first
reaches the user directly, which is who formed the wrong conclusion; the
second reaches the model, which is who can fix it. If `systemMessage` turns
out not to be honoured, the model still has the context and the behaviour
degrades to today's — a sentence from Claude instead of a harness line, not a
regression.

The de-duplication marker lives outside the project on purpose. The premise is
that this project has no ledger, so writing a dotfile into it to record that we
mentioned ourselves once is precisely the intrusion being avoided. When there
is nowhere to remember — no data directory, unwritable disk — the notice fires
anyway: a repeated line is a smaller failure than silence, and silence is the
defect.

Alternatives that lost:

- **Auto-create at any scope.** Creates directories in repositories the user
  never named. The install guide's own argument.
- **Keep it a documentation fix.** Tried, in ADR-0025, and the page now calls
  step 4 "the step people miss" in bold. Two later installs still hit it.
- **A nudge on every hook.** A reminder on every edit, prompt and turn end in
  a project that never opted in is the noise the gate exists to prevent.
- **Nudge every session rather than once.** Rejected as nagging; a user who
  has been told once and did nothing has chosen. Reversible if the once-only
  notice turns out to be too quiet to land.
- **Detect scope from the harness's install records.**
  `installed_plugins.json` carries a `projectPath`, which is more direct than
  reading settings — but it is deeper into Claude Code's internals and keyed
  by a path that a worktree or a moved checkout would not match.

## Cost

The scope signal reads Claude Code's own settings file, whose path and
`enabledPlugins` shape belong to the harness and not to this plugin. If either
changes, `project_scope_enabled` returns False and auto-creation stops
happening. That is the safe direction — the project is then treated as not
opted in and told so, which is the old behaviour plus a sentence — but it is a
silent degradation, and nothing in this repository would notice. Tested
against eight shapes of that file, including an explicit `false`, a
look-alike plugin name and a file that is not JSON.

The "already keeps notes" check is deliberately shallow for a hook with a
timeout, so a project whose notes live somewhere unusual can still be
auto-created beside them. `ledger-adopt` remains the way out, and it never
overwrites.

Auto-creation also writes into a repository without being asked **in that
session** — four paths, all new, never an overwrite (ADR-0008). The consent is
the project-scope enable, which happened earlier and elsewhere.

## Re-evaluation trigger

Any report of `docs/project-memory/` appearing in a project where the user did
not install the plugin at project scope. That is the failure this is built to
avoid, and one occurrence means the scope signal is not sound enough to write
files on.

Also: if `claude plugin install --scope project` ever creates the ledger
itself, both halves of this become redundant and should be deleted rather than
kept as a second mechanism.

## Conclusion & consequences

The gate in `ledger_exists()` stands — hooks still do nothing in a project
without a ledger. What changed is that the project is now told, and that a
project which asked for the plugin by name gets what it asked for without a
second step.

`AGENT-INSTALL.md` step 4 is no longer a step for a project-scope install. It
stays for account-wide installs, where it is the only way to opt a project in.

## Diversions & Pivots

Raised by the user while deciding something else: whether to commit
`.claude/settings.json` so cloners would get the plugin enabled. That question
dissolved on inspection — a cloner with the settings file and no ledger
directory still got silence, so committing it was never the fix. The settings
file remains an open question of its own.

## User's own words

> "I guess, what is the use of a plugin if you install it and don't use t.
> Everyone will think it is working after installation, but effectively it
> needs another command to start. It is better to auto-start after install,
> isn't it? User will think this plugin doesn't work after installtion."
