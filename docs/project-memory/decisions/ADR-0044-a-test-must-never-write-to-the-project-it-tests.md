---
id: ADR-0044
type: decision
title: A test must never write to the project it tests
date: 2026-11-26
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0028, ADR-0031, ADR-0033]
tags: [testing, hooks, footprint]
---

# ADR-0044: A test must never write to the project it tests

## Discussion

Reading this repository's activity trail turned up 271 lines across three
files, 270 of them `**compaction checkpoint** (trigger: unknown)`, arriving in
groups of four one second apart. Only one line in the whole trail is real:
`2026-11-24 16:56:31 (trigger: auto)`.

The cause is in the suite, not the plugin.
`test_hooks_survive_hostile_payloads` feeds every hook the shapes of input a
harness might get wrong, and four of those shapes carry no usable `cwd`:
`{"hook_event_name": "Stop"}`, `{"cwd": None}`, raw `""`, and raw
`"not json at all"`. Alone among the tests in the file it set no project
override. So `project_dir()` did what it is built to do and fell back to
`os.getcwd()` — this repository — `ledger_exists()` said yes, and the hooks
wrote for real:

- `pre_compact.py` appended four compaction checkpoints to the live activity
  trail on every run. 186 lines on 2026-11-25, 84 by midday on 2026-11-26:
  roughly 46 and 21 suite runs.
- `session_start.py` overwrote `.git/ledger-baseline`, which is the Stop
  gate's record of what was already dirty when the session began (ADR-0033).
  A test run resets it to `{"paths": {}, "head": <current>}` — nothing was
  dirty, no commits yet — so running the suite mid-session silently changes
  what the Stop hook reports for the rest of it.

Measured rather than reasoned about: 76 lines before the test, 80 after, four
timestamps one second apart, and `ledger-baseline`'s mtime moving with it.

Three things were on the table. Stop the hooks writing when the payload has no
`cwd` — rejected: that fallback is load-bearing, and `take_project_flag`
already records the live session where `LEDGER_PROJECT_DIR`,
`CLAUDE_PROJECT_DIR` and `CLAUDE_PLUGIN_ROOT` were all empty and cwd was the
only thing left. Pin the test with `LEDGER_PROJECT_DIR` — rejected: it
outranks the payload, so it would also neutralise the `cwd` each payload
carries, and those payloads are the subject of the test. Pin the process
instead.

## Decision

The hostile-payload subprocesses run with `cwd` set to a throwaway repo and
`CLAUDE_PROJECT_DIR` pointed at the same place, so the fallback resolves
inside the sandbox with every payload's own meaning intact. A new check,
`test_the_suite_leaves_this_repository_alone`, fingerprints this project's
activity trail and `.git/ledger-*` markers before any test runs and compares
after the last one.

## Reasoning

Pinning the process is the only one of the three that changes nothing about
what is being tested. The payloads still say what they said; `Z:\no\such\place`
is still a path that does not exist; the fallback is still exercised, just
aimed somewhere harmless.

The guard matters more than the fix. Nothing failed while this was happening —
317 checks passed on every one of those ~67 runs. Every hook was behaving
correctly; it was aimed at the wrong project. No assertion looked at the one
thing that would have shown it, so now one does, and it is positioned last,
after every test has had its chance to leak. Proved by re-introducing the
leak: the guard fails and names both artefacts, `.git/ledger-baseline` and
`activity/2026-11-26.md`.

The fingerprint covers the ledger rather than the whole tree deliberately. The
suite is expected to leave the source alone and a diff would catch it if it
did not; what it actually damaged is gitignored or inside `.git`, where no
diff looks.

## Cost

The fingerprint is a denylist of the two places already known to have been
written. A test that leaks somewhere else — a stray file in `docs/`, a commit
in this repo — still passes. Widening it to the whole tree would mean teaching
it about every legitimately-generated file, which is how guards become
unmaintained.

## Re-evaluation trigger

A test leaks into this project somewhere the fingerprint does not look. Then
the fingerprint is the wrong shape and the check should move to "the tree is
byte-identical except for a known list".

## Conclusion & consequences

Any test that runs a hook or a script as a subprocess pins the project it acts
on — by payload `cwd`, by `--project`, by `LEDGER_PROJECT_DIR`, or by the
process's own working directory. Inheriting the suite's cwd is not neutral:
this repository has a ledger in it, and the hooks will find it.

The 270 polluted trail lines are left in place. They are gitignored working
notes, they are now explained here, and deleting data to tidy a finding is a
worse habit than the finding.

## Diversions & Pivots

Began as two separate observations while reading the project cold: duplicate
compaction entries, and an activity trail with no tool entries at all. The
second turned out to be settled and documented — `post_tool_use.py` says in
its own docstring that the hook matches `Edit|Write|NotebookEdit`, that
shell-driven edits leave nothing, and that matching `Bash` was considered and
rejected; ADR-0028 settles the standing. Only the first was a defect.

## User's own words

n/a — the oddity was noticed while reading the project, and the user's
instruction was "Yes, investigate", then "Yes, fix it".
