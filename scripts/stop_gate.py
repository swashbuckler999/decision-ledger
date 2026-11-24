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

    ledger_touched = [f for f in files if f.startswith(LEDGER_PREFIX)]
    code_touched = [f for f in files if not f.startswith(LEDGER_PREFIX)]
    if not code_touched or ledger_touched:
        return

    # Nag once per distinct change set, not once per turn.
    digest = hashlib.sha256("\n".join(sorted(code_touched)).encode()).hexdigest()[:16]
    marker = cwd / ".git" / "ledger-last-nag"
    try:
        if marker.is_file() and marker.read_text(encoding="utf-8").strip() == digest:
            return
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(digest, encoding="utf-8")
    except Exception:
        pass  # marker is an optimisation, not a requirement

    listing = "\n".join(f"  {f}" for f in code_touched[:20])
    if len(code_touched) > 20:
        listing += f"\n  ...and {len(code_touched) - 20} more"
    text = MESSAGE.format(changed=listing)

    if os.environ.get("LEDGER_STRICT") == "1":
        print(json.dumps({"decision": "block", "reason": text}))
    else:
        L.emit_context("Stop", text)


L.guard(body)
