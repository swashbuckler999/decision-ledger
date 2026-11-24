---
id: ADR-0020
type: decision
title: Treat a config of the wrong shape as absent
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0003, ADR-0008, ADR-0009, ADR-0019]
tags: [robustness, config, edge-cases, security]
---

# ADR-0020: Treat a config of the wrong shape as absent

## Discussion
`config()` promises in its own docstring that a malformed `.ledger.json` reads
as absent, because a typo in a config file must not stop a session. It
delivered that for invalid JSON only. Valid JSON of the wrong **shape** went
straight through:

| `.ledger.json` | what happened |
|---|---|
| `"paths": "docs"` | `AttributeError: 'str' object has no attribute 'get'` |
| `"changelog_order": true` | `AttributeError: 'bool' object has no attribute 'lower'` |
| `"record_names": 5` | same, on every record created |
| `"adopted": "decisions"` | no crash, and worse — see below |

Inside a hook the exception is swallowed by `guard()`, so the briefing silently
stops being injected. Outside one — `new_record.py`, `build_index.py` — it is a
traceback.

`"adopted": "decisions"` is the one that does not crash. `key in "decisions"`
is a substring test, so `is_adopted("decision")` came back true, and any key
whose name is a substring of the string reads as adopted. Adoption decides
whether a file is appended to in its own style or treated as ours, so getting
it wrong by accident is the ADR-0009 promise broken quietly.

Separately, `paths` is hand-editable and unvalidated. `Path(root) / "C:/x"`
discards the root entirely on Windows, and `../../..` walks out of it. Both
confirmed: a `changelog` of `C:/Windows/Temp/evil.md` resolved to exactly that,
and `/etc/passwd` to `C:\etc\passwd`. The ledger would have been appending to a
file outside the repository it was installed in — against the standing rule
that a script's blast radius stays inside the project.

## Decision
Three typed accessors in `_ledger`, and every read goes through one:

- `_mapping(key)` — a dict or `{}`
- `_choice(key, default)` — a non-empty string, lowercased, or the default
- `is_adopted` requires an actual `list`

`path_for` resolves the override and uses it **only** if it stays inside the
project root; otherwise the default. `ledger_paths` resolves through
`path_for`, so a rejected override cannot make a ledger file look like code —
which would fire the unrecorded-change nag on the ledger's own writes — or make
code look like a ledger file, which would silence it for real work.

## Reasoning
The promise was already made; this is honouring it. A config file is the one
input a user edits by hand with no schema in front of them, so wrong types are
the expected failure, not an exotic one.

Rejecting an escaping path silently, in favour of the default, is the right
trade. The scanner never proposes an absolute path, so the only way to get one
is a hand edit or a hostile repository, and in both cases writing inside the
project is the safe outcome. Refusing to run instead would turn a stray config
into a broken session, which is the thing `config()` exists to prevent.

`is_adopted` is where the strict type matters most, because the string case
fails *quietly* and in the direction of treating someone else's file as ours.
A crash would have been better; it got neither.

## Cost
A genuine override outside the project — a changelog on a shared drive, say —
is no longer possible. Nobody has asked for it, and the alternative is a hook
that writes outside the repository it was installed in.

Three accessors where there was one `.get`, and the next config key has to
remember to use them.

## Re-evaluation trigger
If a project legitimately needs a ledger file outside its own tree, this
becomes an explicit opt-in key rather than a widening of `paths`.

## Conclusion & consequences
Six shapes of bad config across five accessors crash nothing, a string never
substring-matches as adopted, three escaping paths are rejected, and a
legitimate relative override still resolves. Six checks pin it.

## Diversions & Pivots

## User's own words
> Please check if we are missing any edge cases?
