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
