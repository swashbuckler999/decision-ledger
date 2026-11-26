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


def _notice_already_given(root):
    """Has this project already been told? Remembered outside the project.

    The marker cannot live in the project: the whole point is that the
    project has no ledger, and writing a dotfile into a repository to say
    "we mentioned ourselves once" is the kind of thing a plugin gets
    uninstalled for. It goes in the plugin's own data directory, keyed by a
    hash of the project path.

    When there is nowhere to remember (no data directory, unwritable disk),
    say it anyway. A repeated line is a smaller failure than silence, which
    is the defect this whole mechanism exists to fix.
    """
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not data:
        return False
    try:
        import hashlib
        key = hashlib.sha256(
            str(Path(root).resolve()).lower().encode("utf-8")).hexdigest()[:16]
        stamp = Path(data) / "told-about-optin" / key
        if stamp.exists():
            return True
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text(L.now_iso(), encoding="utf-8")
    except Exception:
        return False
    return False


def not_opted_in(payload):
    """The project has no ledger. Say so, or create one, but never say nothing.

    Before ADR-0045 every hook returned here in silence, so a correct install
    and a broken one looked identical from the user's seat: `plugin list` says
    enabled, `plugin details` lists five hooks, the hooks fire, and nothing
    whatsoever happens. The user's words: "Everyone will think it is working
    after installation ... User will think this plugin doesn't work after
    installtion."

    Two cases:

    - The plugin is switched on in THIS project's settings. The user named
      this repository, so the ledger is created and the session proceeds as
      normal -- unless the project already keeps notes of its own, in which
      case creating a parallel structure is the one thing not to do, and
      `ledger-adopt` is named instead.
    - It is switched on account-wide. That makes the plugin available
      everywhere and chosen nowhere, so nothing is written. The project is
      told once how to opt in.
    """
    root = L.project_dir(payload)
    existing = L.keeps_own_notes(root)

    if L.project_scope_enabled(root) and not existing:
        made = L.create_ledger(root)
        if made:
            L.emit_context(
                "SessionStart",
                "# Project memory (decision-ledger)\n\n"
                "This project was switched on for decision-ledger and had no "
                "ledger, so one was just created:\n\n"
                + "\n".join(f"- `{m}`" for m in made)
                + "\n\nTell the user in one line that it is now active and "
                  "that `" + L.DEFAULTS["briefing"] + "` is a placeholder "
                  "nobody has written. Offer to fill it in from what can be "
                  "verified -- the code, the README, their own answers -- and "
                  "do not infer the project's state and present it as fact.",
                extra={"systemMessage":
                       "decision-ledger: created "
                       + L.DEFAULTS["briefing"].rsplit("/", 1)[0]
                       + "/ for this project. It is empty until something is "
                         "recorded."})
        return

    if _notice_already_given(root):
        return

    if existing:
        hint = ("This project already keeps its own notes ("
                + ", ".join(f"`{n}`" for n in existing[:5])
                + "). Do NOT create a second set beside them -- run the "
                  "`ledger-adopt` skill, which maps the ledger onto what is "
                  "already there and writes nothing until the mapping is "
                  "approved.")
        short = ("decision-ledger is installed but not active here. This "
                 "project keeps its own notes -- ask Claude to run "
                 "ledger-adopt.")
    else:
        hint = ("Nothing is being recorded in this project yet. To switch it "
                "on, create the directory the hooks look for:\n\n"
                "```\nmkdir -p docs/project-memory/"
                "{decisions,rejections,change-requests}\n```\n\n"
                "Then write `" + L.DEFAULTS["briefing"] + "`, or ask for the "
                "`decision-ledger` skill and it will do both.")
        short = ("decision-ledger is installed but this project has not "
                 "opted in, so nothing is being recorded. Ask Claude to set "
                 "it up, or see docs/project-memory in the plugin's install "
                 "guide.")

    L.emit_context(
        "SessionStart",
        "# Project memory (decision-ledger) -- not active here\n\n"
        "The plugin is installed and enabled, but this project has no ledger, "
        "so every hook is doing nothing. Mention this to the user once, in a "
        "single line, and then carry on with what they asked. Do not create "
        "anything unless they say so.\n\n" + hint,
        extra={"systemMessage": short})


def body():
    payload = L.read_hook_input()
    if not L.ledger_exists(payload):
        return not_opted_in(payload)

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
