"""SessionStart hook: inject the cold-start briefing.

This is what makes a fresh session -- or a fresh Claude account -- start informed
instead of blind. Plain stdout would also work, but additionalContext inside
hookSpecificOutput is the documented field and keeps the output structured.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ledger as L  # noqa: E402

MAX_STATE_LINES = 160
MAX_REJECTIONS = 40


def body():
    payload = L.read_hook_input()
    if not L.ledger_exists(payload):
        return  # project does not use the ledger; stay silent

    parts = ["# Project memory (decision-ledger)", ""]

    state = L.path_for("briefing", payload)
    if state.is_file():
        parts += ["## Current state", ""]
        parts += L.head(state, MAX_STATE_LINES)
        parts.append("")
    else:
        parts += [
            "## Current state",
            "",
            f"No {L.STATE_FILE} exists yet. Do not infer the state from the code "
            "and present it as fact -- say it is missing and offer to create it.",
            "",
        ]

    constraints = L.path_for("constraints", payload)
    if constraints.is_file():
        # One line per constraint: its heading is written to be self-contained.
        headings = [ln[3:].strip() for ln in L.head(constraints, 300)
                    if ln.startswith("## ")]
        if headings:
            parts += ["## Constraints in force", ""]
            parts += [f"- {h}" for h in headings]
            parts += [
                "",
                f"Detail in {L.CONSTRAINTS_FILE}. Read it before pushing, "
                "changing the runtime, or assuming a command will work.",
                "",
            ]

    rej = L.records("rej", payload)
    parts += ["## Settled rejections -- do not re-propose these", ""]
    if rej:
        for p in rej[:MAX_REJECTIONS]:
            fm = L.frontmatter(p)
            parts.append(f"- **{fm.get('id', p.stem)}** {L.title_of(p)}")
        if len(rej) > MAX_REJECTIONS:
            parts.append(f"- ...and {len(rej) - MAX_REJECTIONS} more in {L.SUBDIRS['rej']}/")
        parts += [
            "",
            "Before proposing a library, pattern or approach, check this list. "
            "If it is here, cite the rejection instead of re-proposing it -- "
            "unless its re-evaluation trigger has actually fired, in which case "
            "say so explicitly.",
            "",
        ]
    else:
        parts += ["_None recorded yet._", ""]

    adr = [p for p in L.records("adr", payload)
           if L.frontmatter(p).get("status", "accepted") != "superseded"]
    parts += ["## Accepted decisions in force", ""]
    if adr:
        for p in adr:
            fm = L.frontmatter(p)
            parts.append(f"- **{fm.get('id', p.stem)}** {L.title_of(p)}")
    else:
        parts.append("_None recorded yet._")
    parts.append("")

    openish = [p for p in L.records("cr", payload)
               if L.frontmatter(p).get("status") in ("open", "accepted")]
    if openish:
        parts += ["## Open change requests", ""]
        for p in openish:
            fm = L.frontmatter(p)
            parts.append(f"- **{fm.get('id', p.stem)}** {L.title_of(p)} ({fm.get('status')})")
        parts.append("")

    journey = L.path_for("journey", payload)
    if journey.is_file():
        parts += ["## Journey, most recent", ""]
        parts += L.tail(journey, 30)
        parts.append("")

    parts += [
        "## Your obligation this session",
        "",
        "When a decision is made, an option is rejected, scope changes, or the "
        "user pushes back, record it with the `decision-ledger` skill before the "
        "session ends. If it is not written to docs/project-memory/, it is lost.",
    ]

    L.emit_context("SessionStart", "\n".join(parts))


L.guard(body)
