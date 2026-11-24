---
id: ADR-0032
type: decision
title: Let the script own the changelog entry
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0009, ADR-0010, ADR-0012, ADR-0031]
tags: [skills, duplication, live-session]
---

# ADR-0032: Let the script own the changelog entry

## Discussion
A second live session verified the ADR-0031 path fix — all four routes worked
first time, with no guessing and no workarounds — and then found three things
wrong with the instructions around it.

**The changelog was being written twice.** `new_record.py` appends the dated
entry as it creates the record. The skill's step 4 said, of every record
"without exception", to *"append a dated line to `CHANGELOG.md` linking the
ID"*. Both are correct on their own; following both produces two lines for one
decision. The session avoided shipping the duplicate only because it read the
file first, which is luck rather than instruction.

**The two writers disagreed about format.** The hand-written line used the
style already in the file; the script used its default, so the two sat side by
side in one changelog. The skill's own first rule is to match the style that
is already there, and a second writer cannot honour it.

**And a literal reader was sent looking for something that does not exist.**
Step 4 said to update `00-PROJECT-STATE.md` so it "still describes reality",
but that file has no rejections or decisions section to maintain. Those lists
are composed by the SessionStart hook from the record folders. There was
nothing to edit, and the instruction implied there was.

## Decision
One writer per file. The script owns the changelog entry; the skill is told
explicitly not to add another, and to write the line by hand only in the rare
case where a record was created without the script.

The briefing instruction now says what the file actually contains: update it
when what is *true now* changes, and leave the rejection and decision lists
alone because the hook composes them.

## Reasoning
This is the ADR-0012 split applied one level deeper. The mechanical part —
which end of the file, which format, preserving the line endings — is the
script's, and it is the part this project spent ADR-0010, ADR-0011 and
ADR-0023 getting right. Having the skill also write the entry does not merely
duplicate it; it **routes around all of that work**, because a model appending
a line by hand does not match the project's order, copy its entry format, or
hold the lock.

So "do not write the entry" is not a tidiness rule. It is what keeps the
careful path the only path.

The briefing fix is smaller but the same shape: an instruction that describes
a file as containing something it does not will send a careful reader hunting,
and a less careful one will add the section to make the instruction true.

## Cost
The skill now depends on `new_record.py` having run. A record created by hand
gets no changelog entry unless the author notices the exception, which is
exactly the kind of conditional instruction that gets missed.

## Re-evaluation trigger
If backfilled or hand-written records are found missing from the changelog,
the exception is being missed and `build_index.py` should report entries that
have no changelog line.

## Conclusion & consequences
The duplicate is gone and the format question with it. No test covers this —
it is an instruction, not code — which is precisely why it took a second live
session to find, two rounds after the suite was passing.

Worth recording about method: the first live session found a defect that made
the plugin not work. The second, run only to confirm that fix, found three
more. **A verification run is not a formality; it is another sample of the one
environment this project cannot simulate.**

## Diversions & Pivots

## User's own words
> Push and re-test
