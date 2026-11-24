---
id: REJ-0006
type: rejection
title: Migrate existing documents into ledger records
date: 2026-11-24
status: rejected
related: [ADR-0009, CR-0002]
tags: [adoption, data-loss]
---

# REJ-0006: Migrate existing documents into ledger records

## What was proposed
On adoption, parse an existing changelog or decisions document and split it
into numbered ADR / REJ / CR records, so a project's full history arrives in
the ledger format rather than starting from today. The user raised it directly
as one of the options worth considering — "either start appending, or
restructuring the files, etc."

## Discussion
It is the most complete-looking answer. A project with a 369 KB changelog has
years of reasoning in it, and leaving that outside the ledger means the
rejections folder starts empty even though plenty has surely been rejected.

## Why it was rejected
It is the one operation in this entire design that can destroy a large,
irreplaceable, hand-written file, and it has to get hundreds of judgements
right in a single pass to be worth anything. Splitting prose into records
requires deciding what counts as a decision, where each one begins and ends,
and what the reasoning was — on text written by someone else, often years ago,
with no way to check. A confident wrong split produces records that look
authoritative and misstate history, which is worse than no records: the whole
point of the ledger is to be trusted on exactly these questions.

Adoption delivers most of the value without it. The existing changelog stays
where it is, remains the record, and is appended to. Nothing is lost by not
migrating; a great deal could be lost by migrating badly.

## What was done instead
ADR-0009: adopt in place, append in the existing style, add only what is
missing. The `ledger-adopt` skill is explicitly told that if it finds itself
about to restructure a changelog, it must stop.

The gap is handled by telling the user the truth: the rejections folder starts
empty, and backfilling from memory is the highest-value thing they can do next,
about five minutes per entry.

## Re-evaluation trigger
Revisit only as an explicitly invoked, one-document-at-a-time operation that
backs up the original outside the repository first, shows a diff, and requires
confirmation — never as part of adoption, and never across a whole project in
one pass.

## User's own words
> either start appending, or restructuring the files, etc. Think and get the
> best and correct solution.
