---
id: ADR-0021
type: decision
title: Redact local machine references from the repo
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [REJ-0007, ADR-0006]
tags: [privacy, append-only, published]
---

# ADR-0021: Redact local machine references from the repo

## Discussion
The owner, mid-task:

> None of the git files should have any reference of my local laptop.

The repository is public, so this is a privacy requirement rather than a
preference. An audit of all 64 tracked files found three classes:

1. **The corpus directory name.** `ADR-0011` and `REJ-0008` quote the owner
   verbatim naming the folder their 82 projects live in. REJ-0007 already
   refuses to publish the project *names*; the folder holding them was missed.
2. **The second GitHub account.** `CONSTRAINTS.md` named both authenticated
   accounts, said which was usually active, and gave the exact switch commands.
   One of those accounts has nothing to do with this repository.
3. **Local auth state in the briefing.** `00-PROJECT-STATE.md` named the
   account to switch to.

What is **not** redacted, and why: the publishing identity — name, email, the
owner's public GitHub handle — which the owner supplied explicitly for
publication, and which appears in `LICENSE`, both manifests and the install
instructions. Also kept are the synthetic hostile paths in the ADR-0020 tests
(`C:/Windows/Temp/evil.md`, `/etc/passwd`); they name no user and no real
directory, and removing them would weaken the test they document.

## Decision
Redact in place, in the current tree, and leave the records otherwise intact.

The two verbatim quotes keep their wording and replace only the path with
`[local corpus directory — path redacted]`, with a line saying what was removed
and why. The constraint is rewritten to describe the *shape* of the problem —
more than one account authenticated, a 403 under the wrong one, switch and
switch back — which is the part that is actually useful, and names only the
account that owns this repository.

**History is not rewritten as part of this.** The strings are in six of
nineteen commits, including the initial one, and all of it is pushed.

## Reasoning
This bends the project's own append-only rule, and the bend is narrower than it
looks. Append-only exists so that *reasoning* cannot be quietly dropped — the
risk being a future session re-proposing a settled idea. Removing a directory
name costs no reasoning: ADR-0011's argument is that defaults came from a real
corpus of 82 projects, and that survives naming it "a local corpus directory".
Nothing a future reader needs is gone.

What matters is that the redaction is **visible**. A silent edit to an
append-only file is the failure mode; a marked one, with this ADR naming every
file touched, is a record. That is also why the quotes keep their wording
rather than being paraphrased into something tidier.

The history rewrite is a separate decision because it is destructive and the
consequences are not reversible in the usual sense. `git filter-repo` changes
every commit SHA from the initial commit onward, requires a force push over a
public branch, and — this is the part that makes it a judgement call rather
than a chore — **it does not reliably erase anything from a public GitHub
repository.** Unreachable objects stay fetchable by direct SHA until GitHub
garbage-collects, forks and caches are not rewritten, and anything already
cloned is untouched. So a rewrite buys a cleaner `git log` and not a guarantee,
at the cost of every SHA referenced from this project's own records.

Those are the owner's trade-offs to weigh, not something to do unasked.

## Cost
Two records now contain a redaction marker instead of a complete quote, and the
gh constraint is less immediately actionable than the copy-pasteable version it
replaces — the owner has to remember which account was active.

The repository's history still contains all three classes of reference.

## Re-evaluation trigger
If the owner decides the history should be rewritten, that is its own ADR with
the force-push and the SHA churn recorded, and this one gets a Diversions entry
pointing at it.

## Conclusion & consequences
`git grep` over all tracked files finds no path, username, drive letter or
second account belonging to the owner's machine. The only absolute paths left
are synthetic examples in tests.

The standing rule, from here on: a published repository names the corpus and
the environment, never the machine. Treat a filesystem path the same way
REJ-0007 treats a project name.

## Diversions & Pivots

## User's own words
> None of the git files should have any reference of my local laptop.
