---
id: ADR-0038
type: decision
title: Report a record history kept in one file
date: 2026-11-26
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0009, ADR-0014, REJ-0003, REJ-0006]
tags: [adoption, silence, real-install]
---

# ADR-0038: Report a record history kept in one file

## Discussion
The first installation into a real project outside this corpus found the gap,
and found it the right way round: the **skill** reasoned correctly and the
**script** was silent.

That project keeps its entire decision history in a single `DECISIONS.md` —
around 800 lines, six entries added in one session, with superseded and
corrected items marked by editing the file. The agent installing the plugin
read REJ-0003, recognised the shape, and quoted it back:

> It degrades precisely as the project gets valuable... Superseding a decision
> means editing the file, which puts the append-only guarantee in tension with
> the data model.

and then observed: *"We have already hit exactly that."*

That is the product working. A settled argument surfaced at the moment it
mattered, with its reasoning intact, and was recognised in the wild rather
than in a fixture.

The scanner was not working. `ROLE_PATTERNS` matches `DECISIONS.md` as the
`decisions` role, but `ADOPTABLE` is only changelog, journey and constraints,
so the role is **detected and then never mentioned**. Reproduced on a 406-line
fixture: the review notes discussed the changelog's entry format and said
nothing whatsoever about the file holding every decision the project has made.

The consequence is concrete. The proposed config points `decisions` at a new
empty directory, the first record is written as `0001`, and 800 lines of real
reasoning sit unreferenced beside it — invisible to the cold start this plugin
exists to serve.

## Decision
Any record role found as a single file — decisions, rejections or change
requests — gets a review note naming it, its size, why it is not adopted,
where new records will go instead, and what to do with the existing file.

The instruction is the ADR-0009 pattern already used for a status file: leave
it exactly as it is, do not migrate it (REJ-0006), and link it from the
briefing so a cold start still finds it. With one addition — if the file is
still being written to, say so in the briefing, because two live places for
one kind of record is worse than one old one.

## Reasoning
This is ADR-0014's lesson arriving a second time: *"A mapping the tool cannot
work out is fine; a mapping it cannot work out and does not mention is how the
thing it was built to prevent happens anyway."* That was written about
unprefixed record directories. The same silence was sitting one branch away,
for a shape that is at least as common — a single `DECISIONS.md` is the most
obvious way for a project to start recording decisions.

Not adopting the file remains right. REJ-0003 rejected the single-file model
on its merits, and that project is live evidence for the rejection rather than
against it. What was wrong was refusing silently.

Worth recording about how this was found: the skill caught what the script
missed. The mechanical layer is the one with tests and corpus passes behind
it, and it was the layer that failed. The judgement layer, which cannot be
tested here at all, did the right thing because a rejection record told it
what this shape costs.

## Cost
Two more paragraphs in an already long review, on a path that fires only for
projects keeping records in one file.

The advice ends in a manual step — somebody must actually add the link to the
briefing — and nothing checks that they did.

## Re-evaluation trigger
If projects are found with both a `DECISIONS.md` and a records directory, the
note needs to say which one wins rather than describing both.

## Conclusion & consequences
Eight checks pin the warning and three pin the mirror case, because the fix
must not stop an `adr-tools` directory being adopted.

The wider point, now shown twice: every adoption defect in this project has
been a **silence**, not a wrong answer. The scanner has never once mapped a
file incorrectly. It has twice failed to mention one.

## Diversions & Pivots

## User's own words
> Now while I was installing in one project I got an interesting output.
