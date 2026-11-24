# Installing decision-ledger

## Requirements

- Claude Code 2.1 or later (`claude --version`)
- Python 3.9+ reachable on `PATH` as `python`
- git, optionally — the Stop hook stays quiet without it

Verify Python first. The hooks invoke `python`, not `python3`, because that is
what works on Windows; on a Linux or macOS box where only `python3` exists, see
*Troubleshooting* below.

```powershell
python --version
```

---

## Option 1 — install from GitHub

Add the repository as a marketplace, then install the plugin from it.

```powershell
claude plugin marketplace add swashbuckler999/decision-ledger
```

```powershell
claude plugin install decision-ledger@sayan-skills --scope project
```

### Which scope to use

| Scope | Lands in | Applies to |
|---|---|---|
| `--scope project` | the project's `.claude/settings.json` | that project; committed, so collaborators get it |
| `--scope user` | `~/.claude` | every project you open, existing ones included |
| `--scope local` | that project, that machine | you only, not committed |

**Prefer `--scope project`.** The hooks stay silent in any project without a
ledger directory, so a user-scope install will not create files where it is not
wanted — but silence is not free. Each inert hook still starts a Python
interpreter: roughly 106 ms on every prompt you submit and 129 ms at the end of
every turn, in every project, whether or not it uses the ledger. Install it
where you get the benefit.

## Option 2 — install from a local clone

```powershell
git clone https://github.com/swashbuckler999/decision-ledger.git
```

```powershell
claude plugin marketplace add .\decision-ledger
```

## Option 3 — try it for one session, without installing

```powershell
claude --plugin-dir .\decision-ledger
```

Useful for judging whether the Stop and UserPromptSubmit hooks are too noisy
before committing to them.

---

## Activating it in a project

Installing the plugin is not enough on its own. The hooks look for a ledger
directory and exit silently when there is none, so a project is opted in by
creating that directory — deliberately, so that installing once does not start
writing files into every repository you open.

### A new project

```powershell
mkdir docs\project-memory\decisions, docs\project-memory\rejections, docs\project-memory\change-requests
```

Then create the entry point, `docs/project-memory/00-PROJECT-STATE.md`. Ask
Claude to write the first version — `/cold-start` will tell you it is missing —
or copy the structure from
[this repository's own state file](project-memory/00-PROJECT-STATE.md).

Add one line to the project's `CLAUDE.md` so the convention is visible to
anyone reading the repo rather than only enforced by hooks:

```markdown
Project memory lives in `docs/project-memory/`. Read `00-PROJECT-STATE.md`
before planning, and scan `rejections/` before proposing anything new.
```

That line is a pointer, not the enforcement. The enforcement is the hooks — see
[REJ-0002](project-memory/rejections/REJ-0002-global-claude-md-mandate-as-enforcement.md)
for why a CLAUDE.md mandate was rejected as the primary mechanism.

### An existing project, mid-flight

Same four steps, plus one decision about the past. An existing project already
has decisions behind it; the question is whether to reconstruct them.

**1. Install into the project**

```powershell
claude plugin install decision-ledger@sayan-skills --scope project
```

**2. Create the ledger and the state file**

```powershell
mkdir docs\project-memory\decisions, docs\project-memory\rejections, docs\project-memory\change-requests
```

Start a session and ask Claude to write `00-PROJECT-STATE.md` from the codebase.
Insist that it marks what it inferred from the code as inferred. A state file
that presents guesses as settled fact is worse than no state file, because the
next session acts on it.

**3. Decide how much history to reconstruct**

Three honest options, in ascending order of effort:

- **Start from today.** The ledger covers decisions from now on. Cheapest, and
  it still prevents all future loss. Fine for most projects.
- **Backfill the load-bearing decisions only.** Ask Claude: *"List the
  architectural choices this codebase has clearly already made, and the ones
  where you can see an alternative was available."* Record the handful that
  still constrain the work. Mark each one `Reconstructed from the codebase on
  <date>; the reasoning is inferred, not contemporaneous.`
- **Backfill rejections from memory.** The highest-value and most perishable
  category. Anything you remember trying and abandoning is worth five minutes
  as a REJ record, because that knowledge exists nowhere else and vanishes when
  you forget it.

Never let reconstructed reasoning pass as contemporaneous. An honest
reconstruction is useful; a reconstruction presented as a record of what was
actually argued will mislead someone later.

**4. Commit the ledger with the project**

```powershell
git add docs/project-memory && git commit -m "Add project memory ledger"
```

### System-wide, across every project

```powershell
claude plugin install decision-ledger@sayan-skills --scope user
```

This makes the plugin available in **every** project you open — existing ones
included, not just new ones. What it does not do is activate it everywhere:
each project still opts in by having a `docs/project-memory/` directory.

That limit is deliberate, and worth being clear about. There is no setting that
forces every repository to start keeping a ledger, because a plugin that
creates directories in unrelated projects is a plugin people uninstall in week
one. Opting in is one `mkdir`.

Two things to weigh before choosing user scope:

- **It costs latency everywhere.** An inert hook still starts a Python
  interpreter: roughly 106 ms per prompt and 129 ms per turn end, in every
  project, whether or not it uses the ledger. Across many unrelated
  repositories that is pure waste.
- **A global `CLAUDE.md` line helps, but is not enforcement.** Adding the
  pointer to `~/.claude/CLAUDE.md` makes the convention visible in every
  session, which is worth doing. It will not make it happen — instruction
  following degrades in exactly the long sessions where this matters, which is
  why the hooks exist. See
  [REJ-0002](project-memory/rejections/REJ-0002-global-claude-md-mandate-as-enforcement.md).

If you want it in a known set of projects rather than all of them, install at
project scope in each. You pay the latency only where you get the benefit.

---

## Verify it is working

Start a new Claude Code session in the tracked project. The `SessionStart` hook
should inject a briefing. Ask Claude:

> What does the project memory say about this project?

If it answers from `00-PROJECT-STATE.md` without reading any files first, the
hook fired. If it starts opening files to find out, it did not.

To check the hooks directly, without a session:

```powershell
python tests\test_hooks.py
```

---

## Configuration

| Variable | Effect |
|---|---|
| `LEDGER_STRICT=1` | Stop hook blocks the turn instead of reminding |
| `LEDGER_PROJECT_DIR` | Override where the ledger is looked for |
| `LEDGER_DEBUG=1` | Print hook tracebacks to stderr instead of swallowing them |

Hooks swallow all unexpected errors and exit 0 by design: a memory aid that can
crash your session is worse than no memory aid. `LEDGER_DEBUG=1` turns that off
while you are diagnosing something.

---

## Troubleshooting

**No briefing at session start.** Confirm the plugin is enabled with
`claude plugin list`, and that `docs/project-memory/` exists in the project —
the hooks deliberately stay silent without it. Then run the hook by hand:

```powershell
'{"cwd":"."}' | python "<plugin>\scripts\session_start.py"
```

Output means the script works and the problem is registration. No output means
the ledger directory was not found where the hook looked.

**`python` is not found, but `python3` is.** Edit `hooks/hooks.json` and change
`python` to `python3` in all five commands. A future version should detect this;
it currently does not.

**The Stop reminder appears too often.** It de-duplicates per change set, so
repeats mean the changed files really are changing. If it is still noise, that
is worth knowing — the reminder was designed to be cut rather than tuned
forever if it does not earn its place.

**Records are not being written even though hooks fire.** The hooks remind; they
do not write records. Writing is the `decision-ledger` skill's job, and the
agent invokes it. If it is being skipped, invoke it directly, or use
`/wrap-session` before you stop.

---

## Uninstalling

```powershell
claude plugin uninstall decision-ledger@sayan-skills
```

The records stay. They are ordinary markdown in your repository and have no
dependency on the plugin that created them — which is the point.
