"""UserPromptSubmit hook: catch decisions as they are spoken.

Narrow on purpose. A hook that fires on every prompt and injects a paragraph is
noise, and noise gets ignored -- so this matches a small set of phrases that
reliably mark a decision, a rejection or a scope change, and says one line.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ledger as L  # noqa: E402

PATTERNS = [
    (r"\b(let'?s go with|we'?ll use|going with|stick with|settle on|decided on)\b", "decision"),
    (r"\b(instead of|rather than|switch to|change to|pivot|actually,? let'?s)\b", "diversion"),
    (r"\b(don'?t use|not using|drop the|forget the|no longer|scrap|reject|avoid using)\b", "rejection"),
    (r"\b(i (don'?t|do not) (like|want)|that'?s wrong|that won'?t work|bad idea)\b", "rejection"),
    (r"\b(also need|now i (want|need)|add a requirement|change the scope|new requirement)\b", "change request"),
]

NUDGE = (
    "[decision-ledger] This prompt reads like a {kind}. If it settles something, "
    "record it in docs/project-memory/ with the decision-ledger skill before the "
    "session ends, and quote the user verbatim."
)


def body():
    payload = L.read_hook_input()
    if not L.ledger_exists(payload):
        return
    prompt = (payload.get("prompt") or "").lower()
    if len(prompt) < 12:
        return
    for pattern, kind in PATTERNS:
        if re.search(pattern, prompt):
            L.emit_context("UserPromptSubmit", NUDGE.format(kind=kind))
            return


L.guard(body)
