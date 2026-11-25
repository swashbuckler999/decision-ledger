---
id: ADR-0040
type: decision
title: Tell users a newer version exists, without phoning home
date: 2026-11-26
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0003, ADR-0036]
tags: [upgrade, privacy, versioning]
---

# ADR-0040: Tell users a newer version exists, without phoning home

## Discussion
The owner asked for an upgrade path, and the reason was concrete: changes like
ADR-0039 are worthless to anyone already running an older copy who never finds
out they exist.

> The skill itself should have proper version marker so that it can understand
> which version is already installed... And user can simply ask them to check
> for upgrade, or we may have a force hook ran automatically every weekend...
> if last checking days is past 7 days then it will automatically check.

Claude Code already provides the mechanism: `claude plugin update <plugin>` and
`claude plugin marketplace update`. What is missing is **awareness** — nothing
tells a user a newer version exists, or what changed in it. So the thing to
build is the telling, not another updater.

The automatic weekly check raised the real design question. A version check
normally means asking a server, and the README's standing promise is **"No
network access. Nothing leaves the machine."** A weekly phone-home would make
that promise conditional, for a convenience.

## Decision
`check_version.py` and a weekly line in the session briefing, both of which
**read only directories already on disk.**

An installed plugin lives at `<cache>/<marketplace>/<plugin>/<version>/`, so
the sibling directories of the plugin root are the other versions already
fetched. Reading that directory is the entire mechanism. The user refreshes
the catalogue themselves with `claude plugin marketplace update`, so the
network request exists, is deliberate, and is theirs.

The briefing says it once a week at most, rate-limited by a stamp in
`CLAUDE_PLUGIN_DATA`, which survives upgrades. It states the fact and the
command and explicitly tells the agent not to act on it.

`docs/RELEASES.md` carries what changed, per version, linked from the notice.

## Reasoning
Refusing the network is the whole point of this record. The promise was made
in the README and is one of the few things a user can verify about a plugin
that runs code on their machine. Spending it on a version check would be a bad
trade, and a plugin whose first new feature quietly starts contacting a server
is one nobody should trust.

Reading the cache is not a workaround; it is better. It cannot report a
version the user has not already chosen to fetch, so the notice never
advertises something they have not consented to download.

The weekly stamp lives in the plugin's data directory rather than the project,
because the question "is my plugin current" is about the machine, not the
repository. Asking once per project per week would be noise.

Not auto-upgrading is deliberate. An upgrade changes code that runs on every
turn; that is the user's decision, and a plugin that silently rewrites itself
on a schedule is the kind of thing REJ-0004 was written about in a different
register.

## Cost
It can only report versions already fetched. A user who never runs
`marketplace update` will never be told anything, which is the direct cost of
not phoning home and the right side to err on.

Three more things to keep in step at release time: the manifest version, the
release notes and the tag.

## Re-evaluation trigger
If users report never hearing about upgrades, the answer is a clearer prompt
to run `marketplace update` — not a background fetch.

## Conclusion & consequences
Eleven checks pin it, including that the source contains no `urllib`,
`requests`, `http.client`, `socket` or `curl`, that `0.10.0` sorts above
`0.2.0`, and that a source checkout is reported as having no cache layout
rather than guessed at.

## Diversions & Pivots

## User's own words
> we must have an option in the Skill where any existing users can pick the
> latest version/change of the skill
