---
id: ADR-0023
type: decision
title: Serialise ledger writes with a lock file
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0008, ADR-0010, ADR-0024]
tags: [concurrency, data-loss, windows]
---

# ADR-0023: Serialise ledger writes with a lock file

## Discussion
Nothing in the plugin had ever been run twice at once. Claude Code supports
several sessions on one repository, and this project's own app runs them
routinely, so "two sessions record a decision in the same second" is ordinary
rather than exotic.

Four records allocated concurrently produced three distinct failures:

1. **Duplicate ids.** `next_id` scans, then `new_record` writes. Two processes
   between the scan and the write computed the same number. With the same
   title they produced the same filename and one silently replaced the other;
   with different titles, two records under one id.
2. **A failed write.** `_write_atomic` used one fixed temp name,
   `CHANGELOG.md.ledger-tmp`. Both processes wrote it, one renamed it first,
   and the other's `os.replace` failed on a file that no longer existed.
3. **A lost entry, which is the serious one.** Both processes read the
   changelog, both spliced their entry into the copy they had read, both wrote.
   Each write was complete and internally correct. The file ended up missing
   the other's entry, with nothing anywhere reporting a problem.

Measured: five concurrent records, three changelog entries. On Windows
`os.replace` additionally fails outright while another process holds the
destination open, which is how it first surfaced as an error rather than as
silence.

## Decision
Three layers, each for a different failure.

**Id allocation is a claim, not a check.** `new_record` loops: read the next
id, create the file with `O_CREAT | O_EXCL`, and on collision take the next
number. After winning the create it re-scans for any other file carrying the
same number — a different title can still have claimed it — and retries if so.

**Temp files carry the pid**, so two writers never contend for one, and are
removed on failure instead of being left beside the target.

**The whole read-modify-write of the changelog holds a lock.** A `.ledger-lock`
file created with `O_CREAT | O_EXCL`, waited on for up to ten seconds, and
stolen if it is older than thirty.

## Reasoning
A lock, not atomic writes, because the unit that has to be atomic is the whole
read-modify-write. Unique temp names and `os.replace` guarantee that each
*write* is all-or-nothing, and that was never the problem: both writes
succeeded. The losing entry was dropped in the gap between the read and the
write, where no amount of write atomicity reaches.

A lock *file* rather than a library because the plugin has no dependencies and
is not going to acquire one for this. `O_CREAT | O_EXCL` is atomic on every
filesystem worth supporting.

The stale timeout is the part that needed a judgement. A lock left by a killed
process would otherwise wedge the ledger permanently, which is a worse failure
than the one being fixed — a plugin that stops recording until someone deletes
a file they have never heard of. Thirty seconds is far longer than any real
write and short enough that a user never waits on a dead process.

Where the lock cannot be created at all — an unwritable directory — the write
proceeds unlocked. Recording something is better than recording nothing, and
the directory being unwritable is a larger problem that will surface on the
write itself.

## Cost
A `.ledger-lock` file can be left behind if a process is killed, and will
briefly be visible in `git status`. It is stolen after thirty seconds, and the
troubleshooting table says what it is.

Id allocation now does up to eight scans in the pathological case, and the
re-scan after each claim costs one directory listing per record. Both are
invisible next to writing a record.

Two sessions recording simultaneously will see one wait briefly for the other.

## Re-evaluation trigger
If the ten-second wait is ever hit in normal use, the lock is being held too
long and the locked region should shrink to the write alone, with the splice
recomputed inside it.

## Conclusion & consequences
Five concurrent records now produce five distinct ids, five files and five
changelog entries, with no temp files left behind. Six checks pin it, and they
genuinely run concurrently rather than simulating it — the sequential version
of this test passed throughout.

The wider point: every data-loss bug this project has had was silent. The CRLF
rewrite, the index overwriting a hand-written file, and now a changelog write
that drops an entry while reporting success. Noisy failures get fixed by
whoever hits them. These do not.

## Diversions & Pivots

## User's own words
> Also do deep analysis of any other edge cases which we might have missed.
