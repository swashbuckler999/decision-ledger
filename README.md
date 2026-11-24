# decision-ledger

A Claude Code plugin that keeps a project's **reasoning** — not just its code —
in the repository.

Every decision, every rejected idea, every change of scope and every mid-flight
pivot becomes a numbered, append-only file under `docs/project-memory/`. Five
hooks make the recording happen rather than hoping the agent remembers.

The bar it is built against:

> Someone on a different machine, with a different account and no memory of the
> originating conversation, reads `docs/project-memory/` and is current in
> twenty minutes — *including* knowing which obvious-looking ideas have already
> been tried and why they failed.

Documentation that records only the final state fails that bar, because the next
session re-proposes what was already rejected.

---

## Start here, in this order

1. **[docs/project-memory/00-PROJECT-STATE.md](docs/project-memory/00-PROJECT-STATE.md)**
   — where this project stands right now
2. **[docs/project-memory/INDEX.md](docs/project-memory/INDEX.md)** — the map of
   every decision, rejection and change request
3. **[docs/project-memory/JOURNEY.md](docs/project-memory/JOURNEY.md)** — the
   narrative, including what was built and thrown away
4. **[docs/INSTALL.md](docs/INSTALL.md)** — installing it into your own project

This repository uses its own plugin. The records under `docs/project-memory/`
are real: they are the design history of the thing you are reading about.

---

## What is in the box

### Five skills

| Skill | What it does |
|---|---|
| `decision-ledger` | Writes a record: decision, rejection, change request or pivot |
| `cold-start` | Briefs you on a project you have no memory of |
| `wrap-session` | Flushes unrecorded reasoning before the context is lost |
| `ledger-adopt` | Fits the ledger around a project that already keeps notes |
| `ledger-backfill` | Reconstructs the ledger for a project that kept none |

Which one you start with depends on what the project already has, and
`python scripts/scan_project.py --propose .` will tell you:

| The project | Start with |
|---|---|
| New, or nearly | nothing — just work, and `decision-ledger` records as you go |
| Months of commits, no notes | `/ledger-backfill` **first** |
| Keeps its own CHANGELOG, STATUS or `docs/adr/` | `/ledger-adopt` |

### Five hooks

| Hook | What it does |
|---|---|
| `SessionStart` | Injects the briefing — state, settled rejections, open questions |
| `PreCompact` | Rescues reasoning before compaction discards it |
| `PostToolUse` | Keeps a raw activity trail for later reconstruction |
| `Stop` | Notices code that changed with nothing recorded |
| `UserPromptSubmit` | Catches decision-shaped phrasing in your own words |

`PreCompact` is the one that matters most. Compaction keeps conclusions and
discards the argument that produced them; this hook writes a checkpoint to disk
and tells the summariser what to preserve.

### Four record types

```
docs/project-memory/
├── 00-PROJECT-STATE.md      # mutable, capped at 150 lines, the entry point
├── INDEX.md                 # generated map
├── CHANGELOG.md             # dated, append-only
├── JOURNEY.md               # the narrative, append-only
├── CONSTRAINTS.md           # environment and access rules, append-only
├── decisions/               # ADR-NNNN  what was chosen, and why
├── rejections/              # REJ-NNNN  what was turned down, and why
└── change-requests/         # CR-NNNN   what changed, and the blast radius
```

A **diversion** is not a file. It is an append-only `## Diversions & Pivots`
section inside the record it diverts from, so a change of plan never overwrites
the original reasoning.

Every record carries the two sections that are usually missing: the **cost**
accepted, and the **re-evaluation trigger** — the concrete, observable thing
that would make this the wrong call.

`00-PROJECT-STATE.md` is the **only** mutable file, and nothing is allowed to
exist solely inside it. Everything else is append-only and is never deleted —
a superseded decision keeps its file and gains a pointer to the one that
replaced it. A script checks this rather than trusting it: `check_state.py`
reports any line dropped from the state file that exists nowhere else, and the
Stop hook runs it every turn.

### Adopting it into a working project that kept no notes

Run `/ledger-backfill`. A project with eight months of commits and no notes is
not a new project, and treating it as one leaves every decision already made
sitting in the commit log where no future session will look for it.

`mine_history.py` scores the history for evidence — commits that undo earlier
work, that carry written reasoning, that name an environment limit — ranks the
strongest and caps the list at a sitting's worth. The skill then drafts records
from that evidence, and the rule it works under is strict: **a reconstructed
record may never state a reason the evidence does not support.** Each one
carries the commits it came from and whether its reasoning was `stated`,
`inferred` or `unconfirmed`, and is dated to the commit rather than to today.

The part no script can do: work you *considered and did not do* leaves no
commit at all. The skill asks you for those directly, and three or four of them
are worth more than everything it reconstructs on its own.

### Adopting it into a project that already keeps notes

Run `/ledger-adopt`. A read-only scanner finds the `CHANGELOG`, `STATUS`,
`DECISIONS` or `docs/adr/` you already have, works out your changelog's order
and entry format from the file and its git history, proposes a mapping, and
writes `.ledger.json` only once you approve it. The ledger then appends to your files instead of
creating a parallel set.

One thing it will not adopt: your status file. The briefing is injected into
every session and rewritten as state changes, while a maintained `STATUS.md` is
usually a long append-only log. Pointing one at the other would inject a
fragment of it into every session and invite rewriting a file you did not want
rewritten, so the briefing is always a new file that *points at* yours.

It never migrates existing content into records
([why](docs/project-memory/rejections/REJ-0006-migrate-existing-docs-into-records.md)).
Nothing here overwrites a file it did not create. `build_index.py` refuses to
touch an `INDEX.md` it did not generate, records are never overwritten, and the
skills are instructed to append to existing `CHANGELOG.md`, `JOURNEY.md` and
`CONSTRAINTS.md` files in whatever style is already there — not to reformat,
reorder or deduplicate them. If your project already maintains these files by
hand, the ledger adds to them.

---

## Install

```powershell
claude plugin marketplace add swashbuckler999/decision-ledger
```

```powershell
claude plugin install decision-ledger@sayan-skills --scope project
```

Use `--scope project`, not `--scope user`. The hooks are inert in any project
without a ledger, but an inert hook still starts a Python interpreter — about
235 ms per turn. Install it where you want it, not everywhere.

Then opt the project in by creating the ledger directory:

```powershell
mkdir docs\project-memory\decisions, docs\project-memory\rejections, docs\project-memory\change-requests
```

The hooks stay completely silent in any project without that directory, so
installing globally will not spray files into unrelated repositories. That also
means installing is not enough on its own — a project is tracked once the
directory exists, and not before.

| You want | Do this |
|---|---|
| A new project tracked | Install at project scope, create the directory |
| An **existing** project tracked | Same, then decide how much history to reconstruct — [guide](docs/INSTALL.md#an-existing-project-mid-flight) |
| It available in **every** project | Install at `--scope user`; each project still opts in with one `mkdir` — [why](docs/INSTALL.md#system-wide-across-every-project) |

Full instructions, including backfilling an existing project and the trade-offs
of system-wide installation, are in **[docs/INSTALL.md](docs/INSTALL.md)**.

---

## Designed against real projects

The adoption rules are not guesswork. They were built against a corpus of 82
real projects: 45% of them already kept notes, 20 of 26 changelogs were
newest-first, and all 26 used `##` headings rather than bullets. Several of this
plugin's own defaults were wrong and were corrected from that data — see
[docs/corpus-survey.md](docs/corpus-survey.md).

The same corpus is used as a test, not just a reference. It has twice shown a
filter to be badly wrong after it passed every hand-written fixture: once for
file-role matching, once for history mining, where a rule that looked right
flagged 98% of all real commits.

## Requirements

- Claude Code 2.1 or later
- Python 3.9+ on `PATH` as `python`
- git (optional — the Stop hook stays quiet without it)

No third-party packages. No network access. Nothing leaves the machine.

---

## Tests

```powershell
python tests\test_hooks.py
```

40 checks across all five hooks and both scripts, each one driving the hook with
the JSON payload Claude Code really sends. Includes a named regression test for
the one bug this plugin actually shipped with.

---

## Using it

Mostly you do not. The hooks fire on their own, and the agent invokes
`decision-ledger` when a decision appears. Three things are worth doing by hand:

- `/cold-start` — when picking up a project you do not remember
- `python scripts/mine_history.py . --summary` — what your history still holds
  that the ledger does not
- `/wrap-session` — before you stop for the day
- `python scripts/check_state.py` — lists anything dropped from the state file
  that exists nowhere else; the Stop hook runs it for you every turn
- `python scripts/build_index.py` — after adding records outside the skill

Set `LEDGER_STRICT=1` to make the Stop hook block instead of remind. It is off
by default for a reason — see
[REJ-0004](docs/project-memory/rejections/REJ-0004-blocking-stop-hook-by-default.md).

---

## Licence

MIT. See [LICENSE](LICENSE).
