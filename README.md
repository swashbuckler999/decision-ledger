<div align="center">

# Decision Ledger

### Your repository remembers the code. This makes it remember **why**.

A Claude Code plugin that writes a project's reasoning into the repository —
every decision, every rejected idea, every change of scope, every mid-flight
pivot — as numbered, append-only files, and uses hooks to make the recording
happen instead of hoping the agent remembers.

[![Claude Code](https://img.shields.io/badge/Claude_Code-2.1+-d97757?style=flat-square)](https://claude.com/claude-code)
[![Python](https://img.shields.io/badge/Python-3.9+-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-success?style=flat-square)](#requirements)
[![Checks](https://img.shields.io/badge/checks-200_passing-success?style=flat-square)](#tests)
[![Designed against](https://img.shields.io/badge/designed_against-82_real_projects-6e5494?style=flat-square)](docs/corpus-survey.md)
[![License](https://img.shields.io/badge/license-MIT-black?style=flat-square)](LICENSE)

</div>

---

## The problem

Six weeks after a decision, the code shows **what** you chose. Nothing shows
what you turned down, or why. So the next person — or the next Claude session,
with none of the conversation — proposes the idea you already tried, and loses
a week rediscovering a paragraph.

<table>
<tr>
<th align="left" width="50%">Without a ledger</th>
<th align="left" width="50%">With one</th>
</tr>
<tr valign="top">
<td>

> *"Let's move the loader to threads — it'd be faster."*

Reasonable. Also tried in March, reverted in April, because the broker's
client library is not thread-safe above two connections.

Nobody is left who remembers. The commit that reverted it says `revert
threading`.

</td>
<td>

> *"Let's move the loader to threads."*

The session opens with the settled rejections already in context:

**REJ-0007** — Threaded loader. *Broker client is not thread-safe above two
connections; corrupted two fills in April. Revisit only if the vendor ships a
thread-safe client.*

The idea is answered before it costs anything.

</td>
</tr>
</table>

**The bar this is built against:**

> Someone on a different machine, with a different account and no memory of the
> originating conversation, reads `docs/project-memory/` and is current in
> twenty minutes — *including* knowing which obvious-looking ideas have already
> been tried and why they failed.

Documentation that records only the final state fails that bar. The final state
is the one thing the code already tells you.

---

## The lifecycle it captures

```
                    ┌──────────────┐
                    │  Discussion  │
                    └──────┬───────┘
                   ┌───────┴────────┐
                   ▼                ▼
            ┌─────────────┐  ┌─────────────┐
            │  Decision   │  │  Rejection  │
            └──────┬──────┘  └──────┬──────┘
                   ▼                ▼
            ┌─────────────┐  ┌─────────────┐
            │  Reasoning  │  │  Reasoning  │   ← why each alternative lost
            └──────┬──────┘  └──────┬──────┘
                   ▼                ▼
            ┌─────────────┐  ┌─────────────┐
            │ Conclusion  │  │ Re-evaluate │   ← what would reverse this
            └──────┬──────┘  └─────────────┘
                   │
                   ▼  plans change
            ┌──────────────────────┐
            │ Diversions & Pivots  │   ← appended inside the original record,
            └──────────────────────┘     never overwriting it
```

A diversion is **not a new file**. It is an append-only section inside the
record it diverts from, so a change of plan sits next to the reasoning it
changed and neither one wins.

Every record carries the two sections that are almost always missing:

| Section | The question it answers |
|---|---|
| **Cost** | What did this give up? What is now harder? |
| **Re-evaluation trigger** | What concrete, observable thing would make this the wrong call? |

A decision with no stated cost is a decision nobody argued with. A decision
with no re-evaluation trigger can never be revisited honestly, only overturned.

---

## What it looks like in your repo

```
docs/project-memory/
├── 00-PROJECT-STATE.md     the entry point · the only mutable file · ≤150 lines
├── INDEX.md                generated map of every record
├── CHANGELOG.md            dated, append-only
├── JOURNEY.md              the narrative — including what was thrown away
├── CONSTRAINTS.md          environment and access rules, append-only
├── decisions/              ADR-0001 …  what was chosen, and why
├── rejections/             REJ-0001 …  what was turned down, and why
└── change-requests/        CR-0001  …  what changed, and the blast radius
```

`00-PROJECT-STATE.md` is the only file that gets rewritten, and **nothing is
allowed to exist solely inside it.** Everything else is append-only and never
deleted — a superseded decision keeps its file and gains a pointer to the one
that replaced it.

That rule is checked, not trusted. `check_state.py` reports any line dropped
from the state file that exists nowhere else in the ledger, and the Stop hook
runs it every turn.

---

## Install

```powershell
claude plugin marketplace add swashbuckler999/decision-ledger
```

```powershell
claude plugin install decision-ledger@sayan-skills --scope project
```

Then opt this project in by creating the directory:

```powershell
mkdir docs\project-memory\decisions, docs\project-memory\rejections, docs\project-memory\change-requests
```

The hooks stay **completely silent** in any project without that directory — so
a wide install never sprays files into unrelated repositories, and equally,
installing alone does nothing until the directory exists.

> **Use `--scope project`, not `--scope user`.** An inert hook still starts a
> Python interpreter: about 235 ms per turn in projects that will never use it.

Full instructions, including system-wide installation and its trade-offs:
**[docs/INSTALL.md](docs/INSTALL.md)**.

---

## Which skill do I start with?

That depends entirely on what the project already has, and you do not have to
guess — a read-only scanner will tell you:

```powershell
python scripts\scan_project.py --propose .
```

| Your project | Start with | Because |
|---|---|---|
| New, or nearly | **nothing** — just work | `decision-ledger` records as decisions appear |
| Months of commits, no notes | **`/ledger-backfill`** first | It is not greenfield, and the reasoning is still in the log |
| Already keeps a `CHANGELOG`, `STATUS`, or `docs/adr/` | **`/ledger-adopt`** | Fit around what exists; never duplicate it |

<details>
<summary><b>A working project that kept no notes → <code>/ledger-backfill</code></b></summary>

<br>

A project with eight months of commits and no notes is **not a new project**,
and treating it as one leaves every decision already made sitting in the commit
log where no future session will look for it.

`mine_history.py` scores the history for evidence — commits that undo earlier
work, that carry written reasoning, that name an environment limit — ranks the
strongest, and caps the list at a sitting's worth of work.

The rule the skill works under is strict:

> **A reconstructed record may never state a reason the evidence does not
> support.**

So every backfilled record carries the commits it came from and whether its
reasoning is `stated`, `inferred` or `unconfirmed`, and is dated to the commit
rather than to today. A confident fabrication is worse than an admitted gap,
because it looks exactly like a witnessed record.

The part no script can do: work you *considered and did not do* leaves no
commit at all. The skill asks you for those directly, and three or four of them
are worth more than everything it reconstructs on its own.

</details>

<details>
<summary><b>A project that already keeps notes → <code>/ledger-adopt</code></b></summary>

<br>

A read-only scanner finds the `CHANGELOG`, `STATUS`, `DECISIONS` or `docs/adr/`
you already have, works out your changelog's **order** and **entry format** from
the file and its git history, proposes a mapping, and writes `.ledger.json`
only once you approve it. The ledger then appends to your files rather than
creating a parallel set beside them.

It matches what is already there rather than imposing a house style:

- a newest-first changelog gets new entries at the **top**, not appended under
  the oldest heading
- entries copy your own format — `## 2026-04-02 — Title` if that is what you
  use
- a `docs/adr/` numbered `0001-…` in the `adr-tools` convention is **adopted**,
  continues at the next free number, and new files match its naming
- CRLF files stay CRLF

**One thing it will not adopt: your status file.** The briefing is injected into
every session and rewritten as state changes, while a maintained `STATUS.md` is
usually a long append-only log. Pointing one at the other would inject a
fragment of it into every session and invite rewriting a file you never wanted
rewritten — so the briefing is always a new file that *points at* yours.

It never migrates existing content into records
([why](docs/project-memory/rejections/REJ-0006-migrate-existing-docs-into-records.md)),
and nothing here overwrites a file it did not create: `build_index.py` refuses
to touch an `INDEX.md` it did not generate, records are never overwritten, and
the skills append in whatever style is already there rather than reformatting,
reordering or deduplicating.

</details>

---

## What is in the box

### Five skills

| Skill | What it does |
|---|---|
| **`decision-ledger`** | Writes a record: decision, rejection, change request or pivot |
| **`cold-start`** | Briefs you on a project you have no memory of |
| **`wrap-session`** | Flushes unrecorded reasoning before the context is lost |
| **`ledger-adopt`** | Fits the ledger around a project that already keeps notes |
| **`ledger-backfill`** | Reconstructs the ledger for a project that kept none |

### Five hooks

Skills carry the protocol; hooks carry the enforcement, and fire whether or not
the agent remembers to.

| Hook | What it does |
|---|---|
| **`SessionStart`** | Injects the briefing — state, settled rejections, decisions in force, open questions |
| **`PreCompact`** | Rescues reasoning before compaction discards it |
| **`PostToolUse`** | Keeps a raw activity trail for later reconstruction |
| **`Stop`** | Notices code that changed with nothing recorded |
| **`UserPromptSubmit`** | Catches decision-shaped phrasing in your own words |

> **`PreCompact` is the one that matters most.** Compaction keeps conclusions
> and discards the argument that produced them — which is precisely the content
> this plugin exists to keep. The hook writes a checkpoint to disk and tells the
> summariser what to preserve.

The `Stop` hook **reminds, it does not block**. A wall across every turn that
touches a file trains you to uninstall the plugin within a day
([REJ-0004](docs/project-memory/rejections/REJ-0004-blocking-stop-hook-by-default.md)).
Set `LEDGER_STRICT=1` if you want it to block.

---

## Designed against real projects, not intuition

The adoption rules are not guesswork. They were built against a corpus of **82
real projects**, and several of this plugin's own defaults were wrong and were
corrected from that data — see **[docs/corpus-survey.md](docs/corpus-survey.md)**.

| What the corpus showed | What changed |
|---|---|
| 45% of projects already kept notes of some kind | Adoption became a first-class mode, not an afterthought |
| 20 of 26 changelogs were newest-first | The default insert position flipped |
| All 26 used `##` headings, none used bullets | Entry format is copied from the file, not imposed |
| One project's `.git` is a *file*, not a directory | Worktrees and submodules are real environments |

The same corpus is used as a **test**, not just a reference, and it has earned
that three times over. Twice it showed a filter to be badly wrong *after* it
had passed every hand-written fixture — once for file-role matching, and once
for history mining, where a rule that looked excellent on a fixture flagged
**98% of all real commits**. The third time it exposed a bug hiding behind an
empty result: a code path that returned nothing on all 82 projects, which was
indistinguishable from working.

The lesson is now the procedure. **A fixture tests the author's model of the
world. The corpus tests the world.**

---

## Using it

Mostly you do not. The hooks fire on their own and the agent invokes
`decision-ledger` when a decision appears. These are worth running by hand:

| Command | When |
|---|---|
| `/cold-start` | Picking up a project you do not remember |
| `/wrap-session` | Before you stop for the day |
| `python scripts\mine_history.py . --summary` | To see what your history still holds that the ledger does not |
| `python scripts\check_state.py` | Lists anything dropped from the state file that exists nowhere else |
| `python scripts\build_index.py` | After adding records by hand |

---

## Requirements

- **Claude Code** 2.1 or later
- **Python** 3.9+ on `PATH` as `python`
- **git** — optional; the Stop hook and orphan detection stay quiet without it

No third-party packages. No network access. Nothing leaves the machine.

## Tests

```powershell
python tests\test_hooks.py
```

**200 checks**, dependency-free. Each one drives a hook with the JSON payload
Claude Code really sends, or a script against a throwaway repository on disk.
Every bug this project has had keeps a named regression test — including the
untracked-directory bug it shipped with, the changelog write that silently
converted CRLF to LF, and the worktree blindness that made it call a real
repository unversioned.

---

## This repository uses its own plugin

The records under `docs/project-memory/` are not examples. They are the real
design history of the thing you are reading about — including the ideas that
were built and thrown away.

**Read in this order:**

1. **[00-PROJECT-STATE.md](docs/project-memory/00-PROJECT-STATE.md)** — where
   this project stands right now
2. **[INDEX.md](docs/project-memory/INDEX.md)** — the map of every decision,
   rejection and change request
3. **[JOURNEY.md](docs/project-memory/JOURNEY.md)** — the narrative, including
   every route abandoned and why
4. **[INSTALL.md](docs/INSTALL.md)** — getting it into your own project

### Current status

**v0.1.0 — early.** The scripts and hooks are covered by 200 checks and have
been run against all 82 corpus projects read-only, and the three adoption
situations are simulated end to end against sandbox copies. What has *not*
happened yet: a full live Claude Code session with the plugin installed. Hook
command strings are verified; harness registration and the skills themselves
are not. That is the largest remaining unknown, and it is recorded as such in
the briefing rather than glossed over here.

---

<div align="center">

**MIT** · [LICENSE](LICENSE) · built by [Sayan Majumder](https://github.com/swashbuckler999)

*If it is not written down, it is lost.*

</div>
