---
name: decision-ledger
description: Record a decision, a rejection, a change request or a mid-flight pivot into the project's append-only ledger under docs/project-memory/. Captures the discussion, the reasoning, the alternatives that lost and the condition that would reverse it, so no reasoning is lost when the conversation ends.
when_to_use: Use when a discussion settles on a choice, when an option or library is turned down, when the user changes scope or direction, when a previous decision is reversed, or when the user corrects you in a way that sets a lasting constraint. Also use when asked to record a decision. Do NOT use for one-off style preferences or local edits -- only for something that will still bind next month. For ONE record as it happens; to flush a whole session use wrap-session instead. In a new project with no ledger yet, this skill creates it. Only if the project has history to fit around -- notes it already keeps, or months of commits -- use ledger-adopt or ledger-backfill first.
allowed-tools: Read, Write, Edit, Bash(python *), Bash(git diff *), Bash(git status *), Bash(git log *)
---

# Decision Ledger

> **Running a script from a skill.** `scripts/` is in the *plugin*, not in
> the user's project, so a bare `scripts/...` path resolves against their
> repository and finds nothing. `$CLAUDE_PLUGIN_ROOT` does not help either:
> the harness substitutes it for hook commands, but it is **empty** in a tool
> shell, and in Git Bash the empty expansion silently becomes a path under the
> Git install.
>
> Two reliable anchors, in order of preference:
>
> 1. The **absolute paths in the project-memory context block** injected at the
>    start of the session, under "Running the ledger scripts". Prefer these.
> 2. If that block is absent -- which it is in a project with no ledger yet --
>    the plugin root is **two levels up from this skill's base directory**, the
>    absolute path given at the top of this file. `scripts/` and `skills/` are
>    siblings there.
>
> Always pass `--project "<absolute project root>"`. The scripts otherwise fall
> back to the working directory, which the harness can change mid-session, and
> the ledger would be written somewhere else without any error.


You are the custodian of this project's institutional memory. Your job is to make
sure that a person or an agent arriving with no memory of this conversation can
read `docs/project-memory/` and know not only what was built, but **what was
considered and discarded, and why**.

A record that states only the conclusion has failed. The reasoning is the asset.

## The first rule: append, never rewrite

Someone may already be keeping these files. A project you are installed into
may have its own `CHANGELOG.md`, its own `JOURNEY.md`, its own conventions,
maintained by hand over years.

**Never rewrite a ledger file you did not create in this session.** Add to the
end of it, matching the style already there.

**If the file does not exist yet, create it.** The rule protects content that
exists; there is nothing to preserve in a file that is not there. A new
project has no `CHANGELOG.md`, no `JOURNEY.md` and no `CONSTRAINTS.md` until
the first record is written, and a literal reading of "append, never rewrite"
would skip the entry entirely. Create it with a one-line heading and add your
entry. Never create one by copying content out of an existing file.

Specifically:

- `CHANGELOG.md`, `JOURNEY.md`, `CONSTRAINTS.md` — append only, always. Do not
  reformat, reorder, deduplicate or "clean up" existing entries, however
  inconsistent they look. Someone chose that format.
- Numbered records — create new files. Never overwrite an existing one. The
  only edit permitted to an existing record is appending under
  `## Diversions & Pivots`, or changing `status` when it is superseded.
- `00-PROJECT-STATE.md` — the one file meant to be rewritten, and therefore the
  one place content can be lost. Before removing a line, confirm it exists
  somewhere append-only. See the table in the `wrap-session` skill.
- `INDEX.md` — generated. If it exists without the generator's marker line,
  someone wrote it by hand: leave it alone and say so.

If an existing file's structure does not match this skill's templates, adapt to
it rather than converting it. A ledger that loses a year of someone's notes to
a formatting preference has destroyed more than it will ever record.

## The four record types

| Type | ID | Folder | What it is |
|---|---|---|---|
| Decision | `ADR-NNNN` | `decisions/` | A choice with consequences |
| Rejection | `REJ-NNNN` | `rejections/` | An option considered and turned down |
| Change request | `CR-NNNN` | `change-requests/` | New or altered scope from the user |
| Diversion | *(appended)* | — | A pivot inside an existing record |

A diversion is **not** a new file. It is appended to the record it diverts from.
See "Handling diversions" below.

## When to write a record

Write one when:

- A discussion settles on a technical or scope choice — **ADR**
- An option, library, approach or feature is turned down — **REJ**
- The user changes what they want, or adds a constraint — **CR**
- A previously accepted decision is reversed — **ADR** that supersedes the old one
- The user pushes back on something you proposed — **REJ**, quoting their words

Do **not** write one for: variable naming, formatting, a one-line fix, a question
answered, or anything you would not bother telling a new teammate about. A ledger
with four hundred trivial records is as useless as an empty one. If you are
unsure, ask yourself: *would someone six months from now waste a day
rediscovering this?* If no, skip it.

## How to write a record

### 1. Allocate the ID

Never guess the next number and never scan the folder by hand. Run:

```
python "<plugin root>/scripts/new_record.py" --project "<project root>" <adr|rej|cr> "<short title>"
```

It allocates the next free ID atomically, creates the file from the right
template and prints the path. If the script is unavailable, fall back to reading
the folder and using the highest number plus one.

### 2. Fill every section

Use the templates in `templates.md`. The sections are not optional. If a section
genuinely does not apply, write `n/a` and why — never delete the heading, because
a missing heading reads as an oversight rather than a judgement.

Two sections carry most of the value and are the ones most often written badly:

**Reasoning** — the actual argument, not a restatement of the decision.
"Chose Parquet because it is better" is worthless. "Chose Parquet over CSV
because the tick files are 40 GB and column pruning cuts the backtest load from
90 s to 4 s; CSV stays for the 20-row config files where readability wins" is a
record.

**Re-evaluation trigger** — the concrete, observable thing that would make this
the wrong call. "If the data volume drops below 1 GB" or "if the vendor ships a
streaming API". If you cannot name one, say `No known trigger — treat as
settled`, which is itself useful information.

### 3. Quote the user verbatim

When the record exists because the user chose, objected or redirected, quote them
exactly under **User's own words**. Paraphrase loses the signal. User corrections
are the highest-value content in the whole ledger and they vanish with the chat.

### 4. Update the master files

Every record, without exception:

- Append a dated line to `docs/project-memory/CHANGELOG.md` linking the ID
- Append the narrative to `docs/project-memory/JOURNEY.md` if the record changes
  direction or abandons a route — the story, not the bullet
- Update `docs/project-memory/00-PROJECT-STATE.md` so it still describes reality

Separately from records: when you discover a **constraint** — an access rule, an
environment limit, a thing that only works one particular way — append it to
`docs/project-memory/CONSTRAINTS.md`. A constraint is not a decision, because
nobody chose it, so it fits none of the three record types. It is append-only
and never deleted; when one stops applying, mark it `LIFTED` with the date
rather than removing it.

`00-PROJECT-STATE.md` is the only mutable file and it is **capped at 150 lines**.
It is the cold-start entry point; a state file that grows into a history is a
state file nobody reads. When it approaches the cap, move detail out into the
numbered records and leave a pointer.

## Handling diversions

When the plan changes mid-implementation but the original decision still stands
in spirit, **append** to the existing record under `## Diversions & Pivots`:

```markdown
## Diversions & Pivots

### 2026-11-24 — switched from nightly to on-demand rebuild
**Catalyst:** backtest run time dropped to 4 s, so the nightly job stopped
earning its complexity.
**What changed:** the scheduler is dropped; `rebuild()` is called from the CLI.
**What did not change:** the Parquet storage decision in section 3 is unaffected.
```

Never edit the original reasoning. The point of an append-only record is that the
history cannot be laundered after the fact.

When the new decision **replaces** the old one rather than refining it, write a
new ADR and link both directions:

- New record: `Supersedes: ADR-0007`
- Old record: set `Status: Superseded by ADR-0019` and add nothing else

The old record stays in the folder, intact, forever. That is what stops the next
session re-proposing it.

## Before proposing anything new

Scan `docs/project-memory/rejections/` first. If what you are about to suggest is
already there, do not suggest it — either cite the rejection and move on, or, if
its re-evaluation trigger has actually fired, say so explicitly and propose
revisiting it. Re-proposing a settled rejection without acknowledging it is the
exact failure this ledger exists to prevent.

## Style

Records are read by people. Write plainly, no filler, no ceremony. A good record
is usually under 40 lines. Length is not thoroughness — a long record with a
hollow Reasoning section is worse than a short honest one.
