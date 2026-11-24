---
id: ADR-0025
type: decision
title: A deterministic install page written for agents
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0012, ADR-0015, ADR-0022]
tags: [install, adoption, documentation, published]
---

# ADR-0025: A deterministic install page written for agents

## Discussion
The owner's requirement:

> it should be smartly designed steps so that if someone paste the link to
> Claude or any AI coding agent and ask to install, it can easily install
> without any hiccup.

The existing install documentation was written for a person: prose, trade-offs
discussed inline, scope choices explained and left open. An agent handed that
page has to infer which commands to run, in what order, whether a step
succeeded, and which of the three adoption situations applies — and the one
step that is easy to miss, creating the opt-in directory, reads as an
afterthought while being the step without which nothing works at all.

A wrong guess is not harmless here. An agent that picks `--scope user` on its
own starts a Python interpreter on every prompt in every repository the user
owns. An agent that skips the scanner installs the ledger over a project that
already keeps its own notes, which is the duplication `ledger-adopt` exists to
prevent.

## Decision
A separate page, `docs/AGENT-INSTALL.md`, addressed to the agent, and a
copy-paste prompt at the top of the README that points at it.

The page is deterministic by construction:

- **Preconditions first**, each with a check and an instruction to report
  rather than work around a failure.
- **Every step has an exact command and a check that proves it worked.**
- **A decision table, not prose**, for the three situations — the scanner's own
  output strings are the keys, so the agent matches text it can see rather than
  judging the project itself.
- **Explicit prohibitions** where a plausible-looking choice is wrong:
  do not pick user scope unasked, do not backfill a project whose history holds
  no reasoning, do not reformat files the plugin did not create.
- **A troubleshooting table** keyed on the symptom.

The README keeps the human path beside it. Both are above the fold.

## Reasoning
This is the same split already made inside the plugin itself and recorded in
ADR-0012: the mechanical part is a script, the judgement is approved by a
human. Here the mechanical part is the install and the judgement is the scope
and the situation, so the page makes the mechanical steps unambiguous and
forces the two judgements back to the user.

Keying the decision table on the scanner's literal output rather than on
descriptions of the project is the part that makes it reliable. "Months of
commits, no notes" requires the agent to assess a repository; `This project is
NOT greenfield` requires it to read a line it was just shown. One of those
degrades under a long context and the other does not — the same reasoning that
put enforcement in hooks rather than instructions (ADR-0003).

The prohibitions are there because an agent asked to install something tends to
install it as widely as possible and to be maximally helpful about history. Both
instincts are wrong here, and neither is obvious.

## Cost
Two install documents to keep in step: `AGENT-INSTALL.md` and `INSTALL.md`. If
a command changes and only one is updated, an agent follows the stale one
confidently and silently.

The page also asserts behaviour the plugin has never demonstrated in a live
session — the verification step in particular describes what a working
`SessionStart` hook looks like, which is still untested end to end.

## Re-evaluation trigger
If the two install pages drift even once, merge them into a single document
with an agent-facing section, and accept the worse reading experience.

## Conclusion & consequences
Pasting the repository link with "install this" is now a complete instruction.

Open question, recorded rather than claimed: no agent other than this one has
been handed that page. Whether it is genuinely unambiguous is untested, and the
first real user is the test.

## Diversions & Pivots

## User's own words
> Write a proper introduction of the Skill with clear explanation of the
> purpose and use of the skill. Also it should be smartly designed steps so
> that if someone paste the link to Claude or any AI coding agent and ask to
> install, it can easily install without any hiccup.
