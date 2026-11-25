"""SessionStart hook: inject the cold-start briefing.

This is what makes a fresh session -- or a fresh Claude account -- start informed
instead of blind. Plain stdout would also work, but additionalContext inside
hookSpecificOutput is the documented field and keeps the output structured.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ledger as L  # noqa: E402

MAX_STATE_LINES = 160
MAX_REJECTIONS = 40
# Decisions and change requests are capped for the same reason rejections are.
# Uncapped, a project with 300 accepted ADRs injected 300 lines into the start
# of every session, crowding out the briefing -- which is the part that
# actually orients a cold start.
MAX_DECISIONS = 60
MAX_CHANGE_REQUESTS = 25


UPGRADE_INTERVAL_DAYS = 7


def upgrade_note():
    """One line about a newer version, at most once a week. Never fatal.

    Rate-limited by a stamp in the plugin's own data directory, which Claude
    Code keeps across updates, so the reminder survives an upgrade without
    following the user from project to project.

    The check only reads directories. Nothing here contacts the network: the
    plugin promises that nothing leaves the machine, and a version check is
    not worth making that promise conditional.
    """
    try:
        import time
        import check_version

        current, newer, _cached = check_version.status()
        if not newer:
            return None

        home = os.environ.get("CLAUDE_PLUGIN_DATA")
        stamp = Path(home) / "last-upgrade-notice" if home else None
        if stamp is not None:
            try:
                if stamp.is_file():
                    last = float(stamp.read_text(encoding="utf-8").strip() or 0)
                    seen = stamp.parent / "last-upgrade-version"
                    same = (seen.read_text(encoding="utf-8").strip()
                            if seen.is_file() else "")
                    fresh = time.time() - last < UPGRADE_INTERVAL_DAYS * 86400
                    if fresh and same == newer:
                        return None  # already said so this week
                stamp.parent.mkdir(parents=True, exist_ok=True)
                stamp.write_text(str(time.time()), encoding="utf-8")
                (stamp.parent / "last-upgrade-version").write_text(
                    newer, encoding="utf-8")
            except OSError:
                pass  # cannot remember: say it anyway rather than go silent

        return (
            f"You are running **{current}**; **{newer}** is already on this "
            "machine but not in use. Tell the user, once, in a single line -- "
            "do not act on it.\n\n"
            "```\nclaude plugin update decision-ledger@sayan-skills\n```\n\n"
            f"What changed: {check_version.RELEASES_URL}")
    except Exception:
        return None


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
            f"No {L.rel_path('briefing', payload)} exists yet. Do not infer the state from the code "
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
                f"Detail in {L.rel_path('constraints', payload)}. Read it before pushing, "
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
            parts.append(f"- ...and {len(rej) - MAX_REJECTIONS} more in {L.rel_path('rejections', payload)}/")
        parts += [
            "",
            "Before proposing a library, pattern or approach, check this list. "
            "If it is here, cite the rejection instead of re-proposing it. "
            "These are titles only: the reason and the re-evaluation trigger "
            "are in the record itself, so OPEN IT before claiming the trigger "
            "has fired -- you cannot tell from this list, and asserting it "
            "from a title alone is how a settled argument gets reopened on a "
            "guess.",
            "",
        ]
    else:
        parts += ["_None recorded yet._", ""]

    adr = [p for p in L.records("adr", payload)
           if L.frontmatter(p).get("status", "accepted") != "superseded"]
    parts += ["## Accepted decisions in force", ""]
    if adr:
        # Newest first, so what is cut is the oldest rather than the current.
        for p in sorted(adr, reverse=True)[:MAX_DECISIONS]:
            fm = L.frontmatter(p)
            parts.append(f"- **{fm.get('id', p.stem)}** {L.title_of(p)}")
        if len(adr) > MAX_DECISIONS:
            parts.append(f"- ...and {len(adr) - MAX_DECISIONS} older decisions; "
                         f"the full list is in {L.path_for('index', payload).name}.")
    else:
        parts.append("_None recorded yet._")
    parts.append("")

    openish = [p for p in L.records("cr", payload)
               if L.frontmatter(p).get("status") in ("open", "accepted")]
    if openish:
        parts += ["## Open change requests", ""]
        for p in sorted(openish, reverse=True)[:MAX_CHANGE_REQUESTS]:
            fm = L.frontmatter(p)
            parts.append(f"- **{fm.get('id', p.stem)}** {L.title_of(p)} ({fm.get('status')})")
        if len(openish) > MAX_CHANGE_REQUESTS:
            parts.append(f"- ...and {len(openish) - MAX_CHANGE_REQUESTS} more open.")
        parts.append("")

    journey = L.path_for("journey", payload)
    if journey.is_file():
        parts += ["## Journey, most recent", ""]
        parts += L.tail(journey, 30)
        parts.append("")

    # The two absolute paths every skill needs, resolved by something that
    # actually knows them. A live session established that CLAUDE_PLUGIN_ROOT
    # is empty in an agent's shell -- the harness substitutes it for hook
    # commands only -- and that the agent's working directory can be reset
    # mid-session. So neither path can be left to the agent to work out: a
    # relative `scripts/...` resolves against the user's project and finds
    # nothing, and a script left to infer the project from cwd can write the
    # ledger into whatever folder the harness last moved to.
    parts += [
        "## Running the ledger scripts",
        "",
        "Use these absolute paths. Do not use a bare `scripts/...` path, and "
        "do not rely on `$CLAUDE_PLUGIN_ROOT`, which is empty in tool shells.",
        "",
        f"- scripts:      `{(L.plugin_root() / 'scripts').as_posix()}`",
        f"- project root: `{L.project_dir(payload).resolve().as_posix()}`",
        "",
        "Always pass the project explicitly, so a changed working directory "
        "cannot send records somewhere else:",
        "",
        "```",
        f"python \"{(L.plugin_root() / 'scripts' / 'new_record.py').as_posix()}\" "
        f"--project \"{L.project_dir(payload).resolve().as_posix()}\" adr \"<title>\"",
        "```",
        "",
        "## Your obligation this session",
        "",
        "When a decision is made, an option is rejected, scope changes, or the "
        "user pushes back, record it with the `decision-ledger` skill before the "
        "session ends. If it is not written to docs/project-memory/, it is lost.",
    ]

    # Once a week at most, and only from what is already on disk: say if a
    # newer version has been fetched but not switched to. No network call --
    # see check_version.py for why that matters.
    note = upgrade_note()
    if note:
        parts += ["## Plugin update available", "", note, ""]

    # Snapshot what is already dirty, so the Stop hook can tell this session's
    # work from whatever was lying in the tree before it started.
    L.write_session_baseline(L.project_dir(payload))

    L.emit_context("SessionStart", "\n".join(parts))


L.guard(body)
