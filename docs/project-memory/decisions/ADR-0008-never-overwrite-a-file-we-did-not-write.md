---
id: ADR-0008
type: decision
title: Never overwrite a file we did not write
date: 2026-11-24
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0006, ADR-0007]
tags: [data-loss, safety, adoption]
---

# ADR-0008: Never overwrite a file we did not write

## Discussion
The owner raised it directly: a project adopting this plugin may already
maintain these files by hand. Appending is safe; rewriting is not.

The concern was correct and the design had a real hole. An audit of every write
path found:

- `build_index.py` wrote `INDEX.md` with an unconditional `write_text`. A
  project with its own hand-maintained `INDEX.md` would have lost it on the
  first run, silently, with no prompt and no backup.
- `new_record.py` already refused to overwrite an existing record — safe.
- `post_tool_use.py` guarded its `.gitignore` write with an existence check —
  safe.
- `append_line`, used for `CHANGELOG.md` and the activity log, appends — safe.
- The skills instructed the agent to "rewrite" `00-PROJECT-STATE.md` with no
  caveat about whose file it is.

So one real clobber in code, and an unqualified instruction to the agent, which
is the larger exposure: most writes to the ledger are made by the model, not by
the scripts.

## Decision
Nothing overwrites a file it did not create.

- `build_index.py` writes a marker line into its own output and refuses to
  overwrite any `INDEX.md` lacking it, exiting 1 with an explanation.
- The `decision-ledger` skill opens with append-never-rewrite as its first
  rule, covering each file by name and forbidding reformatting, reordering and
  deduplicating existing entries.
- The `wrap-session` skill adds: if the state file was written by someone else
  and uses different sections, keep their structure.

## Reasoning
Adoption is the whole point of publishing this, and the projects most worth
adopting it are the ones that already keep notes — the ones with the most to
lose. A tool whose first act is to flatten a year of someone's hand-written
changelog into its own format will be uninstalled immediately and deservedly.

The marker-line approach was chosen over alternatives because it is
self-describing: the generated file says it is generated, a human reading it
knows not to edit it, and the script can tell its own output from someone
else's with no state kept anywhere. Timestamps or a manifest of written files
would both need storage and could drift out of sync with reality.

Refusing with exit 1 is better than writing to a different filename. A tool
that silently produces `INDEX.generated.md` leaves two indexes and no
indication which is authoritative.

## Cost
A project that genuinely wants a generated index but already has an `INDEX.md`
must move it by hand first. That is a deliberate friction, not an oversight.

The skill-level rules are instructions, with the same limits as any instruction,
and have no mechanical backstop — unlike the index guard. Formatting judgement
is not something a script can check.

## Re-evaluation trigger
If a report ever comes in of this plugin damaging a file it did not create, the
instruction layer has failed and that write path needs a code-level guard like
the index one.

## Conclusion & consequences
Three tests pin it: the index guard preserves a hand-written file and still
regenerates its own; an existing record survives an id collision.

## Diversions & Pivots

## User's own words
> Also if someone somehow already maintaining the files we should append,
> instead of rewriting, rewriting will be dangerous.
