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

### Three skills

| Skill | What it does |
|---|---|
| `decision-ledger` | Writes a record: decision, rejection, change request or pivot |
| `cold-start` | Briefs you on a project you have no memory of |
| `wrap-session` | Flushes unrecorded reasoning before the context is lost |

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
- `/wrap-session` — before you stop for the day
- `python scripts/build_index.py` — after adding records outside the skill

Set `LEDGER_STRICT=1` to make the Stop hook block instead of remind. It is off
by default for a reason — see
[REJ-0004](docs/project-memory/rejections/REJ-0004-blocking-stop-hook-by-default.md).

---

## Licence

MIT. See [LICENSE](LICENSE).
