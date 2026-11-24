---
id: CR-0001
type: change-request
title: Build for the Forex ML project first, publish later
date: 2026-11-24
status: accepted
origin: user
diverts_from: null
related: [ADR-0001]
tags: [scope]
---

# CR-0001: Build for the Forex ML project first, publish later

## Request
Scope the work to the Forex ML project, but build it so that it can later be
published to the skill directory as a reusable plugin for other agents.

## Origin
Asked directly, in response to a question about whether this should be a global
reusable skill or project-scoped.

## Discussion & reasoning
Two-phase scoping changes the design even though phase one is the only phase
being built now. Had it been project-only, the project-scoped skill layout would
have been correct and simpler. The publishing intent is what forced plugin
packaging in ADR-0001, because hooks do not travel with a bare skill.

Building the packaging now rather than retrofitting it avoids restructuring
later, at the cost of some ceremony that phase one does not need.

Git is local only. Identity set per-repository to Sayan Majumder
<sayan.official@gmail.com>. No remote configured, nothing pushed, pending an
explicit decision — the owner stated the account but described the current state
as local.

## Scope impact
- Repo root becomes a plugin and a one-plugin marketplace
- Hook scripts must resolve via `${CLAUDE_PLUGIN_ROOT}`, not relative paths
- Hooks must stay silent in projects with no ledger, since the plugin may be
  installed globally
- README and install guide become deliverables, not optional extras
- Not yet done: install into the Forex ML project, real-session trial, publish

## Conclusion
Build the plugin in this repository, exercise it on the Forex ML project, judge
the noisy hooks against real use, then prepare for publication.

## User's own words
> It will be Forex ML project, once fully develop, we will make it reusable by
> publishing in Skill Directory and make proper documentation and changes so
> that any other AL Coding agent like Claude Code will be able to use it - may
> be a public repo (Sayan Majumder, sayan.official@gmail.com, from my personal
> Swashbuckler account, presently local git).
