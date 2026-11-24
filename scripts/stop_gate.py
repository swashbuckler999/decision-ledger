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

MESSAGE = """\
Code changed this session but nothing was written to the decision ledger.

Changed outside the ledger:
{changed}

If any of that involved a choice between options, an idea you tried and
dropped, a scope change, or a point where the user corrected you, record it now
with the `decision-ledger` skill. One record per decision.

If it was purely mechanical -- a rename, a typo, a formatting pass -- no record
is needed and you can ignore this.
"""

ORPHAN_MESSAGE = """\
Content was removed from the briefing file and exists nowhere else in the
ledger ({state}):

{orphans}

That file is the only mutable one here, so this content has no other copy. If
it still matters, write it somewhere append-only before the change is
committed:

  a constraint or access rule     -> {constraints}
  a decision, rejection or change -> a numbered record
  narrative, or an open question  -> {journey}

If it is genuinely obsolete, removing it is correct and you can ignore this.
The previous version remains in git until the working tree is committed.
"""


BRIEFING_MESSAGE = """This project has {n} ledger record(s) but no briefing file ({state}).

The briefing is the cold-start entry point: without it, someone arriving with
no memory of this work has to read every record to find out where things
stand, and a new session will say the state is unknown.

Write it now -- current state, what is in progress, what is blocked, the next
step, and pointers to the fuller files. Keep it under {cap} lines.
"""


def missing_briefing_warning(cwd, payload):
    """Records accumulating with no briefing.

    Checked on its own because the other two warnings cannot see it: writing
    records *is* touching the ledger, so a project can fill up with records,
    never trip anything, and still fail the one promise this plugin makes.
    """
    if L.path_for("briefing", payload).is_file():
        return None
    n = sum(len(L.records(k, payload)) for k in L.KIND_KEY)
    if not n:
        return None  # nothing recorded yet; nothing to brief
    if already_reported(cwd, "last-briefing", str(n)):
        return None
    return BRIEFING_MESSAGE.format(
        n=n, state=L.path_for("briefing", payload).name, cap=L.STATE_MAX_LINES)


def changed_files(cwd):
    """What this session changed -- not everything the tree happens to be
    carrying.

    A path is this session's work if it was not already dirty at session
    start, or if its size or mtime has moved since. Without the baseline the
    gate listed every pre-existing untracked file as an unrecorded decision:
    a live session had it flag an editor settings file it had never written
    to, on a turn where the real decision had already been recorded. The only
    output was a false positive, and a reminder that cries wolf is one people
    learn to dismiss -- the failure REJ-0004 exists to avoid.

    With no baseline -- git unavailable, or SessionStart never ran -- every
    dirty path is reported, as before. Over-reporting is the safe direction
    when the hook genuinely cannot tell.
    """
    now = L.dirty_paths(cwd)
    if now is None:
        return None
    base = L.read_session_baseline(cwd)
    if not base:
        return list(now)
    return [p for p, fp in now.items() if base.get(p) != fp]


def already_reported(cwd, key, digest):
    """Report once per distinct situation, not once per turn."""
    # The real git directory, which in a worktree is not cwd/.git -- that is a
    # file there, so mkdir raised FileExistsError, the marker was never
    # written, and the de-duplication this function exists for silently did
    # nothing: the same reminder every single turn.
    gd = L.git_dir(cwd)
    if gd is None:
        return False  # cannot remember; warn rather than go quiet
    marker = gd / f"ledger-{key}"
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


def orphan_warning(cwd, payload):
    """Content dropped from the state file with no copy anywhere else.

    Checked independently of the code-change nag below: editing the state file
    counts as touching the ledger, so the two must not suppress each other --
    the state file is exactly where silent loss happens.
    """
    try:
        orphans, _ = check_state.find_orphans(cwd, payload)
    except Exception:
        return None
    if not orphans:
        return None
    if already_reported(cwd, "last-orphans", digest_of(orphans)):
        return None
    listing = "\n".join(f"  {line}" for line in orphans[:15])
    if len(orphans) > 15:
        listing += f"\n  ...and {len(orphans) - 15} more"
    return ORPHAN_MESSAGE.format(state=L.rel_path("briefing", payload),
                                 orphans=listing,
                                 constraints=L.rel_path("constraints", payload),
                                 journey=L.rel_path("journey", payload))


def unrecorded_warning(cwd, files, payload):
    # Three buckets, not two. The activity trail is a ledger path but not a
    # recording, so it belongs in neither: counting it as code would nag about
    # the plugin's own bookkeeping, and counting it as a recording silences the
    # nag on the first edit of every new project. It is simply ignored.
    ledger_touched = [f for f in files if L.is_recording_path(f, payload)]
    code_touched = [f for f in files if not L.is_ledger_path(f, payload)]
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

    warnings = [w for w in (orphan_warning(cwd, payload),
                            missing_briefing_warning(cwd, payload),
                            unrecorded_warning(cwd, files, payload)) if w]
    if not warnings:
        return
    text = "\n\n".join(warnings)

    if os.environ.get("LEDGER_STRICT") == "1":
        print(json.dumps({"decision": "block", "reason": text}))
    else:
        L.emit_context("Stop", text)


L.guard(body)
