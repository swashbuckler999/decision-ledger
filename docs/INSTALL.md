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

## Option 1 — install from this local repository

Add the repository as a marketplace, then install the plugin from it.

```powershell
claude plugin marketplace add "D:\Personal\Forex\[local corpus directory - path redacted]\Skill Development"
```

```powershell
claude plugin install decision-ledger@sayan-skills --scope project
```

`--scope project` installs it for the current project only. Use `--scope user`
to install it for every project you work on; the hooks remain silent in any
project that has no ledger directory, so this is safe.

## Option 2 — install from GitHub, once published

```powershell
claude plugin marketplace add sayan-majumder/decision-ledger
```

```powershell
claude plugin install decision-ledger@sayan-skills --scope project
```

## Option 3 — try it for one session, without installing

```powershell
claude --plugin-dir "D:\Personal\Forex\[local corpus directory - path redacted]\Skill Development"
```

Useful for judging whether the Stop and UserPromptSubmit hooks are too noisy
before committing to them.

---

## Set up a project to be tracked

The plugin only activates in a project that has a ledger directory. Create one:

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
'{"cwd":"."}' | python scripts\session_start.py
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
