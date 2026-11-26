---
id: REJ-0009
type: rejection
title: Silence when a project has not opted in
status: rejected
date: 2026-11-26
supersedes: []
superseded_by: null
related: [ADR-0045, ADR-0025, REJ-0006]
tags: [install, hooks, ux]
---

# REJ-0009: Silence when a project has not opted in

## Discussion

From the first commit, every hook began with the same two lines:

```python
if not L.ledger_exists(payload):
    return  # project does not use the ledger; stay silent
```

The gate is right and is not what is rejected here. What is rejected is the
**silence** — the decision that a project without a ledger should be told
nothing at all.

The consequence, in the user's own words:

> "I guess, what is the use of a plugin if you install it and don't use t.
> Everyone will think it is working after installation, but effectively it
> needs another command to start. It is better to auto-start after install,
> isn't it? User will think this plugin doesn't work after installtion."

They are describing an unfalsifiable state. After a correct install,
`claude plugin list` reports `enabled`, `claude plugin details` lists five
hooks, the hooks genuinely fire — and produce nothing whatsoever. A working
install and a broken one are byte-for-byte identical from the user's seat.
There is no observation that distinguishes them.

## Reasoning for the original design

Not a bad reason: an account-wide install makes the plugin live in every
repository the user opens, and a plugin that announces itself on every prompt
in every one of them is a plugin they uninstall. `AGENT-INSTALL.md` says so
in as many words — *"a plugin that creates directories in projects the user
did not ask about is a plugin they uninstall"*.

## Why it is rejected

That reasoning covers **noise**, and silence is not the only alternative to
noise. One line, once per project, is neither.

It had already been diagnosed once and misfiled as a documentation problem.
ADR-0025 records it: *"the one step that is easy to miss, creating the opt-in
directory, reads as an afterthought while being the step without which
nothing works at all."* The response was a better install page. The page now
labels step 4 **"the step people miss"** in bold — a product shipping a trap
and annotating it. Two real installs later (ADR-0041, ADR-0042) the trap was
still there, which is the evidence that documentation was the wrong layer.

The gate was also designed for the account-wide case and then applied to both.
At project scope the user has typed the repository's name; requiring a second
confirmation of the thing they just asked for protects nobody.

## What replaces it

ADR-0045. The gate stays; the silence goes.

## Re-evaluation trigger

If the notice turns out to fire in projects the user never intended to see it
in — a stale project-scope enable, say, or a settings shape that changes
under us — then "say something" is too blunt and the condition needs
narrowing. The thing that would **not** reverse this is the notice being
unwelcome once in a project that genuinely has the plugin on: that is the
price of being able to tell working from broken.

## User's own words

> "I guess, what is the use of a plugin if you install it and don't use t.
> Everyone will think it is working after installation, but effectively it
> needs another command to start. It is better to auto-start after install,
> isn't it? User will think this plugin doesn't work after installtion."
