# Releases

What changed in each version, for people using the plugin. For the reasoning
behind each change, follow the record it links to — every entry here has one.

## How to check which version you have

```powershell
python "<plugin>/scripts/check_version.py"
```

It prints the version in use, whether a newer one is already on disk, and the
commands to switch. It makes **no network request** — it reads only Claude
Code's own plugin cache, which you refresh yourself.

Find `<plugin>` with `claude plugin details decision-ledger`; it is typically
`~/.claude/plugins/cache/sayan-skills/decision-ledger/<version>`.

## How to upgrade

```powershell
claude plugin marketplace update sayan-skills
```

```powershell
claude plugin update decision-ledger@sayan-skills
```

The first fetches the latest catalogue; the second switches your installation
to it. Your ledger files are never touched by an upgrade — they live in your
project, not in the plugin.

## How you find out a new version exists

Three ways, in increasing order of effort:

- **It tells you.** Once a week at most, if a newer version is already on your
  machine but not in use, the session briefing says so in one line. It will
  not act on it or upgrade anything.
- **Ask.** Run `check_version.py` above, any time.
- **Watch the repository.** Releases are tagged at
  [swashbuckler999/decision-ledger](https://github.com/swashbuckler999/decision-ledger).

---

## 0.1.0

First public release.

Five skills — `decision-ledger`, `cold-start`, `wrap-session`, `ledger-adopt`,
`ledger-backfill` — and five hooks that fire whether or not the agent
remembers to: `SessionStart`, `PreCompact`, `PostToolUse`, `Stop`,
`UserPromptSubmit`.

Adoption for projects that already keep notes, reconstruction for projects
that kept none, and an append-only record model in which nothing is ever
deleted and a superseded decision keeps its file.

Designed against 82 real projects rather than intuition, and exercised in four
live sessions. Known limits are stated in the README rather than hidden.
