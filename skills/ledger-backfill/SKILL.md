---
name: ledger-backfill
description: Reconstruct a decision ledger for a project that has been worked on for months but never kept notes. Mines git history for the decisions, rejections and constraints behind what already exists, drafts records marked as reconstructed, and leaves the project cold-start ready. Writes no record whose reasoning cannot be sourced or confirmed.
when_to_use: Use when installing the ledger into a project that has real history but no memory files, when the adoption scanner reports "NOT greenfield", or when the user asks to document a project retroactively, catch the docs up, or make an existing project cold-start ready.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(python *), Bash(git log *), Bash(git show *), Bash(git status *)
---

# Backfill the ledger from existing history

A project with eight months of commits and no notes is **not greenfield**, and
treating it as greenfield is the single most expensive mistake available here.
Every decision already made stays in the commit log, where no future session
will look, and within a month the project is re-litigating choices it settled
in May.

Your job: produce a ledger that makes this project cold-start ready, built only
from evidence that actually exists.

## The rule that governs everything below

**A reconstructed record may never state a reason the evidence does not
support.**

You are writing about work you did not witness. The temptation is to fill a
`Reasoning` section with a plausible argument — the commit says "switch to
Parquet", you know why someone would, so you write it. Do not. A record that
reads as settled fact but is actually your inference will be trusted by the
next session and acted on, and nobody will ever know which parts were guessed.

Where the evidence is silent, say so in the record itself:

```markdown
## Reasoning
Not recorded at the time. Commit 3f2273c395 states only what changed.
INFERRED from the code: the loader reads column subsets, which is the main
thing Parquet buys over CSV. **Unconfirmed — ask whoever chose this.**
```

That record is useful. A confident fabrication is worse than nothing.

## 1. Mine the history

```
python scripts/mine_history.py <project path> --summary
```

Read-only. It scores every commit for evidence and prints the strongest, worth
one sitting of work — not every commit that ever mentioned a reason.

What it reports and why each matters:

| Signal | Why it is evidence |
|---|---|
| Undoes earlier work (`revert`, `abandon`, `roll back`) | The highest-value signal there is. A rejection is the one record type that nothing else can reconstruct — abandoned work leaves almost no other trace. |
| Has a message body | Someone wrote reasoning down at the time. Use their words. |
| Closes a route (`drop`, `remove`, `disable`) | Usually a rejection, sometimes a decision to do it differently. Only the body or the user can say which. |
| Decision word (`switch`, `replace`, `pin`, `migrate`) | A choice between options was made. |
| Environment limit | A constraint, which belongs in `CONSTRAINTS.md` and not in a record at all. |
| Subject states a reason | Weakest signal; needs the diff or the user to confirm. |

Two things to understand about what it gives you:

- **It decides per repository whether a message body counts.** In a project
  where nearly every commit has a written body, a body separates nothing —
  treating it as a signal flagged 98% of commits in the corpus this was built
  against, which is not a worklist. Where bodies are rare, one is the best
  indicator available.
- **It caps the list.** Commits it does not show are still in git and are not
  lost. Backfilling everything produces a ledger nobody reads, which is the
  failure mode the core skill warns about.

## 2. Do the cheap, high-value files first

In this order, because each is useful on its own and the early ones make the
later ones easier:

1. **`CONSTRAINTS.md`** — environment limits, access rules, the things that
   only work one particular way. Cheapest to write, most expensive to
   rediscover, and needs no judgement about intent. Mine them from the
   constraint-flagged commits, from `README`, and from comments that start
   "note:", "careful", "do not", "only works".
2. **`00-PROJECT-STATE.md`** — the briefing. Write it from the code and the
   README as they are **now**, which you can verify, rather than from history,
   which you cannot. Mark every inference as one.
3. **`JOURNEY.md`** — the narrative, oldest first, one short paragraph per
   phase of the project. This is where reconstruction is most honest, because
   a narrative can say "between May and July the work was X" without claiming
   to know why.
4. **Records** — decisions and rejections, strongest evidence first.

Doing records last is deliberate. They are the slowest and the easiest to get
wrong, and if the session ends early the first three already make the project
cold-start ready.

## 3. Write each record

Use `new_record.py` as normal, then add provenance to the frontmatter:

```yaml
provenance: reconstructed
sources: [3f2273c395, 88732c0510]
confidence: stated | inferred | unconfirmed
```

- `stated` — the commit body gives the reasoning. Quote it.
- `inferred` — you worked it out from the diff or the code. Say what from.
- `unconfirmed` — you have the decision but not the reason. Ask the user.

Set `date:` to the **commit's** date, not today's. A decision made in May
belongs in May; dating it today destroys the one thing history gives you for
free, which is the order things happened in.

Quote the commit body verbatim in `Discussion`. It is the closest thing to the
user's own words that survives, and the core skill's rule about quoting rather
than paraphrasing applies to it for the same reason.

## 4. Rejections need the user, not the log

This is the part that cannot be automated and the part worth the most.

Work that was *considered and not done* leaves no commit at all. A library
evaluated and declined, an architecture sketched on a whiteboard and dropped,
a feature the user vetoed — none of it is in git. The miner can only find
rejections that got far enough to be committed and then undone.

So ask, directly, and in these words or close to them:

> The commit log shows what was built. It cannot show what you decided
> *against*. What did you try and drop, or consider and turn down? Even three
> or four of those are worth more than everything I reconstructed above,
> because they are the ones a new session will otherwise propose again.

Write each answer as a `REJ` with `provenance: user-recall` and their words
quoted. Do not paraphrase into something tidier.

## 5. Report honestly

Tell the user, plainly:

- How many records you wrote, and the split between `stated`, `inferred` and
  `unconfirmed`
- Which `unconfirmed` ones need their answer, as a short numbered list they can
  work through
- That rejections are thin unless they answered step 4, and why that matters
- That everything you did not record is still in git history and nothing was
  deleted or rewritten

Then run `python scripts/build_index.py` so the index covers the new records.

## What not to do

- **Do not rewrite history files.** If the project has a changelog, append to
  it in its own style; the backfill does not reformat anything. The
  `ledger-adopt` rules apply in full.
- **Do not backfill a changelog entry per record.** Dozens of same-day entries
  for decisions made over eight months is noise and misdates everything. Write
  one entry saying the ledger was backfilled, with the range of dates covered.
- **Do not invent dates, authors or alternatives.** "Considered X and Y" when
  the evidence shows only that X was chosen is a fabrication, and the
  alternatives section is exactly where it is most tempting.
- **Do not delete or move the project's existing files** to make room for the
  ledger. Nothing is ever moved.
