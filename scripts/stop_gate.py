"""Stop hook: notice when code changed but nothing was recorded.

Deliberately a reminder, not a wall. Blocking every turn that touches a file
would train the user to disable the plugin within a day, and most turns do not
contain a decision worth recording. Set LEDGER_STRICT=1 to make it block
instead; the loop guard below honours stop_hook_active either way.

It also de-duplicates: it nags once per distinct set of unrecorded changes, not
once per turn, so a long session does not repeat the same reminder ten times.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ledger as L  # noqa: E402
import check_state  # noqa: E402

LEDGER_PREFIX = L.LEDGER_DIRNAME.as_posix()

MESSAGE = """\
Code changed this session but nothing was written to the decision ledger.

Changed outside docs/project-memory/:
{changed}

If any of that involved a choice between options, an idea you tried and
dropped, a scope change, or a point where the user corrected you, record it now
with the `decision-ledger` skill. One record per decision.

If it was purely mechanical -- a rename, a typo, a formatting pass -- no record
is needed and you can ignore this.
"""

ORPHAN_MESSAGE = """\
Content was removed from {state} and exists nowhere else in the ledger:

{orphans}

{state} is the only mutable file here, so this content has no other copy. If it
still matters, write it somewhere append-only before the change is committed:

  a constraint or access rule     -> {constraints}
  a decision, rejection or change -> a numbered record
  narrative, or an open question  -> {journey}

If it is genuinely obsolete, removing it is correct and you can ignore this.
The previous version remains in git until the working tree is committed.
"""


def changed_files(cwd):
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=cwd, capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    files = []
    for line in out.stdout.splitlines():
        if len(line) > 3:
            path = line[3:].strip()
            if " -> " in path:  # rename: keep the destination
                path = path.split(" -> ")[-1]
            files.append(path.strip('"'))
    return files


def already_reported(cwd, key, digest):
    """Report once per distinct situation, not once per turn."""
    marker = cwd / ".git" / f"ledger-{key}"
    try:
        if marker.is_file() and marker.read_text(encoding="utf-8").strip() == digest:
            return True
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(digest, encoding="utf-8")
    except Exception:
        pass  # the marker is an optimisation, not a requirement
    return False


def digest_of(items):
    return hashlib.sha256("\n".join(sorted(items)).encode()).hexdigest()[:16]


def orphan_warning(cwd):
    """Content dropped from the state file with no copy anywhere else.

    Checked independently of the code-change nag below: editing the state file
    counts as touching the ledger, so the two must not suppress each other --
    the state file is exactly where silent loss happens.
    """
    try:
        orphans, _ = check_state.find_orphans(cwd)
    except Exception:
        return None
    if not orphans:
        return None
    if already_reported(cwd, "last-orphans", digest_of(orphans)):
        return None
    listing = "\n".join(f"  {line}" for line in orphans[:15])
    if len(orphans) > 15:
        listing += f"\n  ...and {len(orphans) - 15} more"
    return ORPHAN_MESSAGE.format(state=L.STATE_FILE, orphans=listing,
                                 constraints=L.CONSTRAINTS_FILE,
                                 journey=L.JOURNEY_FILE)


def unrecorded_warning(cwd, files):
    ledger_touched = [f for f in files if f.startswith(LEDGER_PREFIX)]
    code_touched = [f for f in files if not f.startswith(LEDGER_PREFIX)]
    if not code_touched or ledger_touched:
        return None
    if already_reported(cwd, "last-nag", digest_of(code_touched)):
        return None
    listing = "\n".join(f"  {f}" for f in code_touched[:20])
    if len(code_touched) > 20:
        listing += f"\n  ...and {len(code_touched) - 20} more"
    return MESSAGE.format(changed=listing)


def body():
    payload = L.read_hook_input()
    if payload.get("stop_hook_active"):
        return  # already continuing once; never loop
    if not L.ledger_exists(payload):
        return

    cwd = L.project_dir(payload)
    files = changed_files(cwd)
    if files is None:
        return  # not a git repo, or git unavailable: stay quiet

    warnings = [w for w in (orphan_warning(cwd), unrecorded_warning(cwd, files)) if w]
    if not warnings:
        return
    text = "\n\n".join(warnings)

    if os.environ.get("LEDGER_STRICT") == "1":
        print(json.dumps({"decision": "block", "reason": text}))
    else:
        L.emit_context("Stop", text)


L.guard(body)
