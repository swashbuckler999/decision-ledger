"""PreCompact hook: the single most important hook in this plugin.

Compaction is where reasoning dies. The conclusion survives the summary; the
argument that produced it usually does not. This hook does two things:

1. Writes a checkpoint to the activity log so there is an on-disk trace
   regardless of what the summary keeps.
2. Prints instructions for the compaction summary itself. On exit 0 a PreCompact
   hook's stdout becomes those instructions (capped at 10,000 characters).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ledger as L  # noqa: E402

INSTRUCTIONS = """\
Preserve decision reasoning above all else in this summary.

Keep, in full and in the user's own words where possible:
- every choice made and the argument that produced it, not just the conclusion
- every option considered and discarded, and the reason it lost
- every point where the user objected, corrected course, or changed scope
- constraints discovered, and assumptions still unverified
- anything agreed but not yet written to docs/project-memory/

Drop freely: tool output, file listings, command transcripts, intermediate
search results, and restatements of code already on disk. Those can be
recovered by reading the repository. Reasoning cannot.

After compaction, before continuing work, write any unrecorded decision,
rejection or change request into docs/project-memory/ using the
decision-ledger skill. Treat that as the first task, not a later one.
"""


def body():
    payload = L.read_hook_input()
    print(INSTRUCTIONS)  # becomes the compaction instructions

    if not L.ledger_exists(payload):
        return

    trigger = payload.get("trigger", "unknown")
    log = L.ledger_dir(payload) / "activity" / f"{L.today()}.md"
    L.append_line(log, f"- {L.now_iso()} **compaction checkpoint** (trigger: {trigger})")


L.guard(body)
