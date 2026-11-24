---
id: ADR-0001
type: decision
title: Package as a plugin rather than a bare skill
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0003]
tags: [packaging, distribution]
---

# ADR-0001: Package as a plugin rather than a bare skill

## Discussion
The first design put the skill in `.claude/skills/` and registered its hooks in
`.claude/settings.json`. Both external opinions consulted (DeepSeek, Gemini)
proposed the same shape, and Gemini argued explicitly for a project-scoped skill
directory on the grounds that anyone cloning the repo gets it automatically.

The problem surfaced when the publishing requirement was considered: hooks in
`settings.json` do not travel with a skill. An installer would receive the
instructions and none of the enforcement, which is precisely the half that does
not work on its own.

## Decision
The repository root is itself a Claude Code plugin: `.claude-plugin/plugin.json`,
`skills/`, `hooks/hooks.json`, `scripts/`. It is simultaneously a one-plugin
marketplace via `.claude-plugin/marketplace.json`.

## Reasoning
A plugin is the only packaging unit that carries skills, slash commands and
hooks together as one installable artefact. Verified against the official docs:
a plugin's `hooks/hooks.json` is loaded automatically and may reference
`${CLAUDE_PLUGIN_ROOT}`, so scripts resolve wherever the plugin lands.

Why the alternatives lost:
- Project-scoped `.claude/skills/` plus `settings.json` hooks: works for this
  one project, cannot be installed by anyone else without manual steps.
- Skill alone, no hooks: enforcement collapses to instruction-following, which
  is the documented failure mode this project exists to fix.

Making the repo its own marketplace costs one extra file and means installation
is `claude plugin marketplace add <repo>` with no separate marketplace to host.

## Cost
Slightly unusual layout for people expecting `.claude/skills/`. The repo root is
a plugin, so project files and plugin files share a namespace and the README has
to be explicit about which is which.

## Re-evaluation trigger
If Claude Code gains a way to ship hooks alongside a standalone skill, the
plugin wrapper stops earning its complexity.

## Conclusion & consequences
`claude plugin validate --strict .` must pass before any commit that touches the
manifests. Verified passing at the time of writing.

## Diversions & Pivots

## User's own words
> once fully develop, we will make it reusable by publishing in Skill Directory
> and make proper documentation and changes so that any other AL Coding agent
> like Claude Code will be able to use it
