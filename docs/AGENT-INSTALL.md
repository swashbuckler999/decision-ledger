# Install instructions for an AI coding agent

This page is written for an agent, not a person. It is deterministic: every
step has an exact command, a check that proves it worked, and what to do when
the check fails. Follow it in order and do not improvise.

**Repository:** `https://github.com/swashbuckler999/decision-ledger`
**Marketplace name:** `sayan-skills`
**Plugin name:** `decision-ledger`

---

## 0. Preconditions

Check these first and report any that fail instead of working around them.

| Requirement | Check | If it fails |
|---|---|---|
| Claude Code 2.1+ | `claude --version` | Tell the user to update; do not continue |
| Python 3.9+ on `PATH` as `python` | `python --version` | See "python3 only" below |
| A project directory | You are in the repository the user wants tracked | Ask which project |

> If `python` is missing but `python3` exists, the plugin still installs. After
> installing, edit `hooks/hooks.json` in the plugin directory and replace
> `python` with `python3`. Tell the user you did this.

---

## 1. Add the marketplace

```
claude plugin marketplace add swashbuckler999/decision-ledger
```

**Check:** the command exits 0 and `claude plugin marketplace list` includes
`sayan-skills`.

---

## 2. Choose the scope, then install

There are two scopes and the user picks, not you. Match what they actually
said:

| What the user said | Scope | Command |
|---|---|---|
| "install it here", "add it to this project", or nothing about scope | **project** | `claude plugin install decision-ledger@sayan-skills --scope project` |
| "for all my projects", "every project", "machine-wide", "account-wide", "globally", "so I can use it anywhere" | **user** | `claude plugin install decision-ledger@sayan-skills --scope user` |

**Check:** `claude plugin list` includes `decision-ledger` **and its `Status:`
is `enabled`**. If it says `disabled`, do 2a before going on.

If the user said nothing about scope, use **project** and tell them in one line
that `--scope user` would make it available everywhere. Do not ask them to
choose before doing anything — install here, say the other option exists, and
move on.

### 2a. If it is already installed but disabled

This happens when an earlier session installed it and nobody enabled it, and
it is the one place the scope you just chose can be thrown away silently.

```
claude plugin enable decision-ledger@sayan-skills --scope project
```

**`enable` has its own `--scope`, and it defaults to auto-detect rather than
to the scope the plugin was installed at.** Run it bare and it can write
`"decision-ledger@sayan-skills": true` into the **user** settings file while
`claude plugin list` still reports `Scope: project`. The listing looks
correct, and the hooks now run in every repository the user opens — exactly
the outcome the warning below says never to choose on your own initiative,
reached without ever typing `--scope user`.

**So always pass `--scope` to `enable`, matching the install.** Then check
where the flag landed, because the listing will not tell you:

```
grep -n decision-ledger ~/.claude/settings.json      # absent, or false
grep -n decision-ledger .claude/settings.json        # true
```

If it went to the wrong file, move it rather than leaving both set:

```
claude plugin disable decision-ledger@sayan-skills --scope user
claude plugin enable  decision-ledger@sayan-skills --scope project
```

That leaves `false` in the user settings and `true` in the project's: on
here, silent everywhere else.

**Never pick `--scope user` on your own initiative.** It starts a Python
interpreter on every prompt and every turn end in *every* repository they open,
including ones that will never use the ledger.

### If you installed at user scope

Say this to the user, because it surprises people:

> Installed account-wide. It is now available in every project, but it does
> nothing in a project until that project opts in — one `mkdir`, step 4 below.
> Until then the hooks are completely silent.

Then do steps 3–7 **for the current project only.** Do not create
`docs/project-memory/` in the user's other repositories, and do not go looking
for them. There is deliberately no way to opt every project in at once: a
plugin that creates directories in projects the user did not ask about is a
plugin they uninstall. When they want another project tracked, they run step 4
there.

---

## 3. Work out which situation this project is in

This step decides what you do next, so do not skip it. Run the read-only
scanner from the installed plugin directory:

```
python "<plugin>/scripts/scan_project.py" --propose .
```

It writes nothing. It prints a proposed configuration on stdout and review
notes on stderr. Read the notes, then pick exactly one row:

| What the notes say | What the project is | Do this |
|---|---|---|
| Nothing notable, few or no commits | **New project** | Go to step 4, then just work |
| `This project is NOT greenfield` **and** `Run the ledger-backfill skill` | **Worked on, no notes** | Go to step 4, then run the `ledger-backfill` skill before any new work |
| `NOT greenfield` **but** `reconstruct almost nothing` | **Worked on, history has no reasoning in it** | Go to step 4. Do **not** backfill. Ask the user what they tried and rejected, and record those |
| Any `Adopted:` or `Entry format copied` line | **Already keeps its own notes** | Run the `ledger-adopt` skill. It will handle step 4 itself |

---

## 4. Opt this project in

**If you installed at project scope, this already happened.** A project-scope
enable *is* the opt-in: the next session start creates the three record
directories and a placeholder `00-PROJECT-STATE.md`, and tells the user it did
(ADR-0045). Skip to step 5 and fill the placeholder in.

Two exceptions where you still do this by hand:

- **You installed at user scope.** The plugin is available everywhere and
  active nowhere. Each project opts in separately, with the command below, and
  an unopted project says so once per project rather than staying silent.
- **This project already keeps its own notes.** Auto-creation deliberately
  refuses, because a second set of records beside an existing `docs/adr/` is
  the duplication `ledger-adopt` exists to prevent. Run that skill instead —
  it maps the ledger onto what is there and writes nothing until you approve
  the mapping.

PowerShell:

```
mkdir docs\project-memory\decisions, docs\project-memory\rejections, docs\project-memory\change-requests
```

bash / zsh:

```
mkdir -p docs/project-memory/{decisions,rejections,change-requests}
```

**Check:** `docs/project-memory/decisions` exists.

---

## 5. Write the entry point

Create `docs/project-memory/00-PROJECT-STATE.md`. It is the file a future
session with no memory reads first, and the plugin's one promise depends on it
existing.

Keep it under 150 lines and include: what the project is, current status, what
is in progress, what is blocked, the next concrete step, and open questions.

Write it from what you can **verify** — the code, the README, the user's own
answers. Do not infer the project's state and present the inference as fact. If
you do not know something, write that you do not know it.

**Check:** the file exists and the Stop hook stops warning about a missing
briefing.

---

## 6. Verify the install end to end

```
python tests/test_hooks.py
```

**Check:** it prints `N passed, 0 failed`.

Then confirm the hooks are actually registered, which the tests cannot prove:
start a new Claude Code session in the project and ask

> What does the project memory say about this project?

If the answer comes from `00-PROJECT-STATE.md` with no file reads first, the
`SessionStart` hook fired. If the session starts opening files to find out, it
did not — check that the plugin is enabled for this project.

**It must be a NEW session, and you cannot do this check yourself in the
session that installed it.** Hooks and skills enabled mid-session are not
picked up by the running session: `SessionStart` has already been and gone,
and the five skills are not in the skill list, so invoking
`decision-ledger:ledger-adopt` fails with `Unknown skill` even though the
install is correct. Nothing is wrong when that happens.

So the last thing you do in the installing session is **tell the user to
restart or `/clear`**, and say that the end-to-end check above is theirs to
run on the other side of it. Until then, follow the skill files directly —
`skills/<name>/SKILL.md` in the plugin directory — rather than reporting the
install as broken.

---

## 7. Commit it

```
git add docs/project-memory .ledger.json
git commit -m "Add decision-ledger project memory"
```

`.ledger.json` only exists if the adopt skill created it.

---

## Rules that apply while using this plugin

- **Never overwrite or reformat a file the plugin did not create.** Adoption
  appends in the file's existing style.
- **Never migrate existing documents into records.** Point at them instead.
- **Never invent reasoning.** A reconstructed record carries the commits it came
  from and whether its reasoning is `stated`, `inferred` or `unconfirmed`.
- **`00-PROJECT-STATE.md` is the only mutable file.** Nothing may exist solely
  inside it; move content out before removing it.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Hooks never fire, and nothing is said | Pre-0.1.1 copy: the hooks used to exit silently with no ledger | Update the plugin; a current copy says so once per project |
| Hooks never fire | The opt-in directory is missing | Step 4 |
| `docs/project-memory/` appeared without being asked for | The plugin is enabled in this project's `.claude/settings.json`, which counts as the opt-in | Expected (ADR-0045). To undo: delete the directory and disable the plugin for this project |
| Hooks never fire, and the directory exists | The plugin was enabled during this session | Restart or `/clear`. Mid-session enables do not register — step 6 |
| `Unknown skill: decision-ledger:...` | Same cause | Not a broken install. Follow `skills/<name>/SKILL.md` directly this session; the skills appear after a restart |
| Enabled for one project, but hooks run everywhere | `claude plugin enable` was run without `--scope`, so the flag went to user settings | Step 2a |
| `python: command not found` in hook output | Only `python3` exists | Edit `hooks/hooks.json`, replace `python` with `python3` |
| Stop hook repeats the same reminder every turn | `git rev-parse` is failing in this directory | Confirm it is a git repository; the reminder is intentionally repeated when the de-duplication marker cannot be written |
| `build_index.py` refuses to run | An `INDEX.md` exists that the script did not generate | Rename it, or point `paths.index` elsewhere in `.ledger.json` |
| `timed out waiting for ...ledger-lock` | A previous process was killed mid-write | Delete the `.ledger-lock` file if nothing else is running |
