"""PostToolUse hook: keep a raw activity trail of file changes.

Not documentation -- working notes. Its only job is to give wrap-session
something factual to reconstruct from when the conversation itself is gone.
The activity folder is self-ignoring, so this never pollutes the repository.

**The trail is best-effort and systematically incomplete.** The hook matches
`Edit|Write|NotebookEdit`, so a file changed through the shell -- a heredoc, a
`sed -i`, a Python one-liner -- leaves no entry. A live session found this
directly: the same file edited via Bash produced nothing and via Edit produced
an entry immediately, and in permission modes that encourage the shell the
under-recording is the normal case, not the exception.

Matching `Bash` as well was considered and rejected: it would log every `ls`
and `git status` into a file nobody reads, and still could not say which
commands wrote anything.

So the trail is a hint, never evidence. Anything that must survive goes in a
record, which is written deliberately. Nothing in the ledger's promises rests
on this file being complete.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ledger as L  # noqa: E402

GITIGNORE = "# Working notes, not documentation.\n*\n!.gitignore\n"


def body():
    payload = L.read_hook_input()
    if not L.ledger_exists(payload):
        return

    tool = payload.get("tool_name", "?")
    target = (payload.get("tool_input") or {}).get("file_path", "")
    if not target:
        return

    try:  # show the path relative to the project when we can
        target = str(Path(target).resolve().relative_to(L.project_dir(payload).resolve()))
    except Exception:
        pass

    if L.is_ledger_path(target, payload):
        return  # do not log edits to the ledger itself

    folder = L.activity_dir(payload)
    L.append_line(folder / f"{L.today()}.md", f"- {L.now_iso()} {tool} `{target}`")


L.guard(body)
