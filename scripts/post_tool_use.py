"""PostToolUse hook: keep a raw activity trail of file changes.

Not documentation -- working notes. Its only job is to give wrap-session
something factual to reconstruct from when the conversation itself is gone.
The activity folder is self-ignoring, so this never pollutes the repository.
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

    if L.LEDGER_DIRNAME.as_posix() in Path(target).as_posix():
        return  # do not log edits to the ledger itself

    folder = L.ledger_dir(payload) / "activity"
    folder.mkdir(parents=True, exist_ok=True)
    gi = folder / ".gitignore"
    if not gi.exists():
        gi.write_text(GITIGNORE, encoding="utf-8", newline="\n")

    L.append_line(folder / f"{L.today()}.md", f"- {L.now_iso()} {tool} `{target}`")


L.guard(body)
