---
name: ledger-adopt
description: Set up the decision ledger in a project that already keeps its own notes. Finds existing changelogs, status files and decision records, proposes a mapping onto them, and writes .ledger.json only after you approve it. Never moves, reformats or overwrites anything.
when_to_use: Use when setting up the ledger in a project that ALREADY KEEPS NOTES -- a CHANGELOG, STATUS, DECISIONS or docs/adr it maintains by hand -- or when the user asks to adopt or retrofit it. If the project keeps no notes at all but has months of commits, use ledger-backfill instead; if it has both, run this one first and backfill after.
allowed-tools: Read, Write, Glob, Grep, Bash(python *), Bash(git log *), Bash(git status *)
---

# Adopt the ledger into an existing project

A project that has kept notes for years has more to lose than one starting
fresh, and it is also the project where this is worth the most. Your job is to
fit the ledger around what exists, not to replace it.

**Nothing is moved, renamed, reformatted or rewritten. Ever.** The output of
this skill is one new config file and some new directories. If you find
yourself about to restructure someone's changelog, stop — that is the migrate
operation, and it is deliberately not built.

## 1. Run the scanner. Do not do this by eye.

```
python scripts/scan_project.py --propose <project path>
```

It prints a draft `.ledger.json` on stdout and review notes on stderr. It is
read-only — it never writes to the project it scans.

This step is mechanical on purpose. Establishing a changelog's order and entry
format decides where every future entry lands, in a file that may hold years
of work, and it is a deterministic property of the file rather than a
judgement. The scanner reads it the same way every time; prose does not. See
ADR-0012.

It uses three signals in order of authority: an order the file **declares** in
words, the **position** of its newest and oldest dates, and finally **git
history** — whether added lines land near the top or the bottom. In the corpus
behind this design, git history was the only thing that settled 7 of 26 files.

What it cannot settle, it marks `unconfirmed` and you must ask about. Do not
quietly accept the default in that case: that is the one place a wrong answer
puts entries where nobody will look.

For reference, the shapes this was built against are in `docs/corpus-survey.md`.

## 1b. What the scanner looks for

At the project root and one level into `docs/`:

| Looking for | Typical names |
|---|---|
| Changelog | `CHANGELOG*`, `CHANGES*`, `HISTORY*`, `RELEASES*` |
| Status / state | `STATUS*`, `STATE*`, `CURRENT*`, `PROJECT-STATE*` |
| Narrative | `JOURNEY*`, `DIARY*`, `LOG*`, `NOTES*` |
| Decisions | `DECISIONS*`, `docs/adr/`, `docs/decisions/`, `ADR-*.md` |
| Rejections | `REJECT*`, `NOT-DOING*`, `declined/` |
| Constraints | `CONSTRAINTS*`, `GOTCHAS*`, `ENVIRONMENT*` |
| Other memory | `.ai/`, `docs/memory/`, `docs/project-memory/` |

Record each one's **size and shape**, not just its name. A 300 KB changelog
and a 10-line stub need different treatment, and the shape decides the mapping
in step 2.

## 2. Decide what to adopt and what to add

Two categories, and the split is not negotiable:

**Adoptable — map onto the existing file, append in its style**

- `changelog` — append new record lines in whatever format is already used.
  Match their date style, their heading level, their bullet character.
- `journey` — same.
- `constraints` — same, if one exists.
- `decisions` / `rejections` / `change_requests` — if the project already has a
  decisions directory, point at it and continue its numbering. Do not
  renumber anything.

**Not adoptable — the ledger owns these**

- `briefing` — always a new file, even when `STATUS.md` exists.

  This is the part people get wrong, so be explicit about why. The briefing is
  injected into every session, is capped at 150 lines, and is rewritten as
  state changes. A maintained `STATUS.md` is often a status *log* — tens or
  hundreds of kilobytes, append-only in practice, valuable precisely because
  it is long. Mapping the briefing onto it would inject its first 160 lines
  into every session, probably mid-sentence, and invite rewriting a file
  nobody wanted rewritten.

  So: create a new briefing file and have it **point at** the existing status
  file. They are different artifacts that happen to share a name.

- `index` — generated; never point it at a hand-written index.

## 3. Propose, then wait

Show the user a table: each ledger key, what you propose to map it to, whether
that is adopt or create, and why. Call out anything surprising, especially a
large status file you are deliberately not adopting.

**Do not write the config until they agree.** This is the step where a wrong
guess silently attaches the ledger to the wrong file.

## 4. Write the config

`.ledger.json` at the project root. Paths are relative to the project root.
Include only the keys that differ from the defaults, plus `adopted`:

```json
{
  "version": 1,
  "paths": {
    "briefing": "docs/project-memory/00-BRIEFING.md",
    "changelog": "CHANGELOG.md",
    "decisions": "docs/adr"
  },
  "adopted": ["changelog", "decisions"],
  "notes": "STATUS.md (98 KB) is a status log, not a briefing - see ADR-0009."
}
```

`adopted` is what tells every other skill that a file belongs to someone else
and must only ever be appended to.

### Match the changelog's order and format

Check both before writing the config, because getting either wrong puts entries
somewhere nobody will look:

- **Order.** Read the first and last dated entries. If the first is the most
  recent, the file is newest-first and needs
  `"changelog_order": "newest-first"` — otherwise every entry is filed under
  the oldest heading at the bottom.
- **Format.** Copy the shape already used. If entries are headed sections, set
  a matching multi-line template, for example
  `"changelog_entry": "## {date} - {id} {title}

Recorded in `{path}`.
"`.
  If they are bullets, leave the default.

A malformed config is ignored rather than fatal, so validate it after writing:

```
python scripts/build_index.py
```

If that resolves to the paths you intended, the config parsed.

## 5. Create only what is missing

Make the directories for any record type the project lacks, and write the
briefing. Do not create a changelog, journey or constraints file that is being
adopted — the existing one is the file.

## 6. Seed the briefing honestly

Draft it from the project's own documents first, and only then from the code.
Mark anything inferred as inferred. A briefing that presents guesses as settled
fact is worse than no briefing, because the next session acts on it.

Point at what you did not absorb:

```markdown
Full history: CHANGELOG.md (369 KB, maintained by hand since 2026-03).
Detailed status log: STATUS.md. This briefing summarises; those are the record.
```

## 7. Tell the user what is not covered

Say plainly:

- Which existing files are now adopted, and that they will only be appended to
- That no existing content was read into records, so the rejections folder
  starts empty even though the project has surely rejected things before

Then hand over to **`ledger-backfill`**, which is the skill for exactly that.
Adoption maps the ledger onto the files a project keeps; it does not read the
project's past into records, and a project that has been worked on for months
has a past whether or not it wrote any of it down.

If the scanner reported `NOT greenfield`, this is not optional — run the
backfill before new work starts.
