---
id: ADR-0042
type: decision
title: The installing session cannot verify its own install
date: 2026-11-26
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0041, ADR-0026]
tags: [install, hooks, skills, docs]
---

# ADR-0042: The installing session cannot verify its own install

## Discussion

Also found installing into a real project. After a correct install — enabled
at project scope, opt-in directories created, config written, 268/0 tests —
invoking the skill the page tells you to use failed:

```
Skill: decision-ledger:ledger-adopt
→ Unknown skill: decision-ledger:ledger-adopt
```

Nothing was wrong. **Hooks and skills enabled mid-session are not picked up by
the running session.** `SessionStart` has already fired, and the skill list
was built before the plugin was enabled.

Step 6 already says to start a *new* session for the hook check, but it does
not say why, and it does not say that the installing agent cannot do that
check itself. So the agent is left with an install that looks broken by its
own documented next step, and the obvious wrong conclusions are available:
re-enable it, reinstall it, edit `hooks.json`, or report failure.

## Decision

Step 6 states plainly that the check requires a new session and **cannot be
done by the session that installed it**, names `Unknown skill` as the expected
symptom rather than a fault, and instructs the agent to follow
`skills/<name>/SKILL.md` directly for the rest of that session. Its last act
is to tell the user to restart or `/clear` and hand them the end-to-end check.

Two troubleshooting rows added: hooks not firing with the directory present,
and `Unknown skill`.

## Reasoning

A deterministic install page owes the reader the difference between "broken"
and "not yet live", because the remedies are opposite. Without it the likely
responses all make things worse: reinstalling churns the settings this
project already warns about in ADR-0041, and editing `hooks.json` damages a
working install.

Saying "follow the SKILL.md directly" also keeps the install finishable in one
sitting. The skills are plain markdown in a known location, so an agent that
cannot invoke them can still execute them — which is what happened, and the
adoption completed correctly.

Alternatives:

- **Say nothing and let the agent work it out.** It did, but only after
  reading `ADOPTABLE` in the scanner source to confirm the install was sound.
  That is luck, not a process.
- **Have the install tell the user to restart before step 3.** Rejected:
  adoption would then straddle two sessions, and the second would arrive
  without the scanner output or the mapping it approved.

## Cost

The page now asks the user to do something — restart — which an install page
would rather not need. Unavoidable: the plugin cannot register its own hooks
into a session already running.

## Re-evaluation trigger

Claude Code hot-loading plugin hooks and skills on enable. Then the check is
doable in the installing session and this step becomes noise.

## Conclusion & consequences

- Never treat `Unknown skill: decision-ledger:*` as a failed install.
- Follow `skills/<name>/SKILL.md` directly in the installing session.
- End the install by telling the user to restart, and that the hook check is
  theirs to run after it.

## Diversions & Pivots

<!-- Append-only. Empty at creation. Never edit entries above this line. -->

## User's own words

n/a — found by an agent following the install page.
