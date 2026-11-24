# Constraints

Facts about the world that bind this project: environment limits, access rules,
things discovered the hard way. **Append-only.** Nothing here is deleted.

A constraint is not a decision — nobody chose it. It is something true that you
have to work within, and the cost of not knowing it is usually an hour of
rediscovery. That is why it lives here, permanently, and not in the mutable
state file.

When a constraint stops applying, do not remove it. Mark it `LIFTED` with the
date and what changed, so the next reader learns both the constraint and its
resolution.

---

## Pushing requires the right gh account active

**Discovered:** 2026-11-24, by hitting it.

Two GitHub accounts are authenticated on the development machine:
`<the account that was active before>` (usually active) and `swashbuckler999` (owns this repo).

A push while `<the account that was active before>` is active fails with:

```
remote: Permission to swashbuckler999/decision-ledger.git denied to <the account that was active before>.
fatal: ... The requested URL returned error: 403
```

The working sequence:

```powershell
gh auth switch --user swashbuckler999
git push origin main
gh auth switch --user <the account that was active before>
```

**What does not work:** putting the username in the remote URL
(`https://swashbuckler999@github.com/...`). That bypasses the gh credential
helper, git falls back to an interactive password prompt, and it dies with
`/dev/tty: No such device or address` in a non-interactive shell. This was
tried and reverted — do not try it again.

---

## Runtime: Python 3.9+ on PATH as `python`, nothing else

The hooks invoke `python`, not `python3`, because that is what resolves on
Windows. On a system where only `python3` exists, `hooks/hooks.json` must be
edited. No third-party packages, no network access at runtime.

**Why it binds:** a plugin that needs a dependency install before it works will
not be installed. The cost is the `python3` rough edge, which is documented in
the install guide rather than solved.

---

## Commit identity is repository-local

`user.name` and `user.email` are set in this repo's config only, never globally.
Identity: Sayan Majumder <sayan.official@gmail.com>.

**Why it binds:** the owner works across projects with different identities.
A global git identity would silently attribute other work to the wrong person.

---

## The repo is public

Published 2026-11-24 at https://github.com/swashbuckler999/decision-ledger with
explicit approval.

Anything committed here is visible to anyone. The owner's email address is
already public in `LICENSE`, both manifests and the commit metadata — that was
intended. Nothing else personal should join it: no paths from the development
machine, no account names beyond the repo owner, no project details from the
Forex ML work this plugin was built for.

---

## The corpus this was designed against is private

The adoption rules were derived from 82 real projects on the owner's machine.
Aggregate findings are published in `docs/corpus-survey.md`; the project names
are not, and must not be added. Several are personal or client names.

Re-running `python scripts/scan_project.py --survey <parent>` reproduces the
data locally. Keep its output out of this repository.

---

## Hooks need a shell where `python` resolves

Verified on Windows with Git Bash: all five hook commands run, with a plugin
root containing a space, whether the harness substitutes `${CLAUDE_PLUGIN_ROOT}`
or the shell expands it.

They do **not** run under WSL bash, where the Windows Python install is not on
PATH. Bare `bash` on Windows often resolves to WSL, so a hook failing with
`python: command not found` usually means the wrong shell, not a missing
interpreter. Check with `which python` in the shell that actually runs hooks.

Unverified: macOS and Linux, where `python` frequently does not exist at all
and only `python3` does.

---

## LIFTED 2026-11-24: the changelog write converted CRLF to LF

Found 2026-11-24 by simulating adoption against a sandbox clone of a real
369 KB changelog. The real project was never touched and is verified
byte-identical; the bug is in the plugin.

`_write_atomic` writes with `newline="
"`. On Windows a CRLF changelog is
therefore rewritten entirely in LF: the sandbox file went from 374,851 to
369,502 bytes after adding 8 lines, a difference of 5,349 - one byte per line.

`git diff` showed only "8 insertions" because git normalises line endings, so
the damage is invisible in review and visible in the working tree. That is
worse than a loud failure.

It contradicted ADR-0008 and ADR-0010: the only change was supposed to be the
inserted block.

**LIFTED.** Reads and writes now use `newline=""` so Python performs no
translation, the file's dominant line ending is detected, and the inserted
block is converted to match. Re-running the same simulation against the same
369 KB CRLF changelog: 374,851 -> 375,011 bytes, a growth of exactly 160, the
measured size of the inserted block. CRLF line count went 5,656 -> 5,660, one
per inserted line.

Tests cover both CRLF and LF fixtures and assert on byte count, because that
is the one thing git's normalisation cannot hide.

## 2026-11-24: Python's splitlines() breaks on \x1e, \x1c, \x1d and \x85

`str.splitlines()` treats the C0 separator characters — RECORD SEPARATOR
`\x1e`, FILE SEPARATOR `\x1c`, GROUP SEPARATOR `\x1d` — and NEL `\x85` as line
boundaries, not just `\n` and `\r\n`.

This made `mine_history.deleted_paths()` return an empty list on every
repository while the git query underneath was correct: the format string used
`\x1e` as a sentinel, and the parse used `splitlines()`, which destroyed the
sentinel it was looking for.

Parsing `git` output with a sentinel character therefore needs `.split("\n")`,
never `.splitlines()` — or no sentinel at all, which is what was done: commit
header lines are matched by their own shape, `^[0-9a-f]{40} \d{4}-\d{2}-\d{2}$`.

Why it went unnoticed: not one of the 82 projects in the corpus has ever
deleted a file, so the code path returned nothing in every real run and nothing
distinguished that from working correctly. It was found by building a sandbox
repository with a deletion in it.

`add_changelog_entry` uses `splitlines(keepends=True)` and is safe, because it
verifies `before + after == original` before writing and `keepends` preserves
whatever it split on.
