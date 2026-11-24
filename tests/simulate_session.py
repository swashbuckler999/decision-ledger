"""Replay a whole working session against the hooks and check what they do.

The unit tests drive each hook once, in isolation. A real session is a state
machine: the Stop gate's answer depends on what happened earlier in the same
session, whether anything was recorded since, and what git has seen. That
sequence is where the interesting behaviour lives, and none of it is reachable
one hook at a time.

This builds a throwaway project, then plays twelve turns of a plausible
session through the hooks in order -- a decision is discussed, code changes,
nothing is recorded, something is recorded, the context is compacted, the
session resumes, content is dropped from the briefing -- and asserts what the
hooks should say at each point.

It needs no model and no API key, so it runs anywhere.

    python tests/simulate_session.py                 # the working tree
    python tests/simulate_session.py --plugin-root X # an installed copy

What it proves: the hooks behave correctly across a realistic sequence, from
wherever they are installed. What it cannot prove: that Claude Code calls them
during a real session, or that the model acts on what they emit. That needs a
live session -- see ADR-0026.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO
PASSED, FAILED = [], []


def check(name, condition, detail=""):
    (PASSED if condition else FAILED).append(name)
    print(f"    {'[ok  ]' if condition else '[FAIL]'} {name}"
          + (f"\n           {detail}" if detail and not condition else ""))


def turn(n, what):
    print(f"\n  Turn {n}: {what}")


def hook(script, payload, project):
    payload = dict(payload)
    payload["cwd"] = str(project)
    p = subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "scripts" / script)],
        input=json.dumps(payload), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60, cwd=str(project),
        env=dict(os.environ, CLAUDE_PLUGIN_ROOT=str(PLUGIN_ROOT)))
    if p.returncode != 0 or "Traceback" in p.stderr:
        return {"crashed": p.stderr[-300:], "context": "", "raw": p.stdout}
    ctx = ""
    if p.stdout.strip():
        try:
            data = json.loads(p.stdout)
            ctx = (data.get("hookSpecificOutput", {}).get("additionalContext")
                   or data.get("reason") or "")
        except json.JSONDecodeError:
            ctx = p.stdout
    return {"crashed": None, "context": ctx, "raw": p.stdout}


def script(name, *args, project=None):
    p = subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "scripts" / name), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, cwd=str(project),
        env=dict(os.environ, LEDGER_PROJECT_DIR=str(project)))
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def git(project, *args):
    return subprocess.run(("git",) + args, cwd=str(project), capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def build_project():
    d = Path(tempfile.mkdtemp(prefix="ledger-session-"))
    git(d, "init", "-q", "-b", "main")
    git(d, "config", "user.email", "t@t.t")
    git(d, "config", "user.name", "t")
    (d / "README.md").write_text("# Tick feed\n\nReads XAUUSD ticks.\n",
                                 encoding="utf-8")
    (d / "feed.py").write_text("def load(path):\n    return []\n", encoding="utf-8")
    for sub in ("decisions", "rejections", "change-requests"):
        (d / "docs" / "project-memory" / sub).mkdir(parents=True)
    (d / "docs" / "project-memory" / "00-PROJECT-STATE.md").write_text(
        "# Project state\n\n**Updated:** today\n\n## Current status\n\n"
        "The loader is pinned to the GREENFINCH-7 endpoint and must not move.\n"
        "Ticks are stored as CSV.\n\n## Next step\n\nDecide on a tick store.\n",
        encoding="utf-8")
    (d / "docs" / "project-memory" / "rejections"
       / "REJ-0001-threaded-loader.md").write_text(
        "---\nid: REJ-0001\ntype: rejection\ntitle: Threaded tick loader\n"
        "status: rejected\n---\n\n# REJ-0001: Threaded tick loader\n\n"
        "## Why it was rejected\nThe client is not thread-safe above two "
        "connections.\n", encoding="utf-8")
    git(d, "add", "-A")
    git(d, "-c", "commit.gpgsign=false", "commit", "-qm", "Initial commit")
    return d


def main():
    global PLUGIN_ROOT
    for i, a in enumerate(sys.argv):
        if a == "--plugin-root" and i + 1 < len(sys.argv):
            PLUGIN_ROOT = Path(sys.argv[i + 1]).resolve()

    print(f"simulating a session against: {PLUGIN_ROOT}")
    d = build_project()
    print(f"throwaway project:            {d}")

    try:
        # ------------------------------------------------ 1
        turn(1, "session starts cold")
        r = hook("session_start.py", {"hook_event_name": "SessionStart",
                                      "source": "startup"}, d)
        check("no crash", not r["crashed"], r["crashed"] or "")
        check("the briefing is injected", "GREENFINCH-7" in r["context"])
        check("settled rejections come with it",
              "Threaded tick loader" in r["context"])
        check("and the instruction not to re-propose them",
              "do not re-propose" in r["context"].lower())

        # ------------------------------------------------ 2
        turn(2, "the user says something decision-shaped")
        r = hook("user_prompt_submit.py",
                 {"hook_event_name": "UserPromptSubmit",
                  "prompt": "let's switch the tick store to Parquet instead of CSV"}, d)
        check("the prompt is flagged as a decision", "decision-ledger" in r["context"],
              r["context"][:120])

        # ------------------------------------------------ 3
        turn(3, "an ordinary question is not flagged")
        r = hook("user_prompt_submit.py",
                 {"hook_event_name": "UserPromptSubmit",
                  "prompt": "what does feed.py do?"}, d)
        check("no false positive on a plain question", not r["context"].strip(),
              r["context"][:120])

        # ------------------------------------------------ 4
        turn(4, "code is edited")
        (d / "feed.py").write_text(
            "import pyarrow.parquet as pq\n\n\ndef load(path):\n"
            "    return pq.read_table(path)\n", encoding="utf-8")
        r = hook("post_tool_use.py",
                 {"hook_event_name": "PostToolUse", "tool_name": "Edit",
                  "tool_input": {"file_path": str(d / "feed.py")}}, d)
        check("no crash", not r["crashed"], r["crashed"] or "")
        trail = list((d / "docs" / "project-memory" / "activity").glob("*.md"))
        check("the edit lands in the activity trail", bool(trail))
        if trail:
            body = trail[0].read_text(encoding="utf-8")
            check("recorded with a relative path", "`feed.py`" in body, body[:120])
        check("the trail ignores itself",
              (d / "docs" / "project-memory" / "activity" / ".gitignore").is_file())

        # ------------------------------------------------ 5
        turn(5, "the session tries to end with nothing recorded")
        r = hook("stop_gate.py", {"hook_event_name": "Stop"}, d)
        check("the gate notices", "nothing was written to the decision ledger"
              in r["context"], r["context"][:160] or "(silent)")
        check("and names the changed file", "feed.py" in r["context"],
              r["context"][:160])

        # ------------------------------------------------ 6
        turn(6, "the same unrecorded change, a second time")
        r = hook("stop_gate.py", {"hook_event_name": "Stop"}, d)
        check("it does not repeat itself", not r["context"].strip(),
              r["context"][:160])

        # ------------------------------------------------ 7
        turn(7, "the decision is recorded")
        rc, out, err = script("new_record.py", "adr", "Store ticks as Parquet",
                              project=d)
        check("the record is created", rc == 0, err[-160:])
        made = sorted((d / "docs" / "project-memory" / "decisions").glob("*.md"))
        check("filed as ADR-0001", made and made[0].name.startswith("ADR-0001"),
              str([p.name for p in made]))
        cl = (d / "docs" / "project-memory" / "CHANGELOG.md")
        check("the changelog gains one entry",
              cl.is_file() and len(
                  [l for l in cl.read_text(encoding="utf-8").splitlines() if l.strip()]
              ) == 1)

        # ------------------------------------------------ 8
        turn(8, "the session ends again, this time with a record")
        r = hook("stop_gate.py", {"hook_event_name": "Stop"}, d)
        check("the gate is satisfied", not r["context"].strip(),
              r["context"][:160])

        # ------------------------------------------------ 9
        turn(9, "the context fills up and is compacted")
        r = hook("pre_compact.py", {"hook_event_name": "PreCompact",
                                    "trigger": "auto"}, d)
        check("the summariser is told what to keep",
              "decision" in r["raw"].lower(), r["raw"][:160])
        trail = (d / "docs" / "project-memory" / "activity")
        check("a checkpoint is left on disk",
              any("checkpoint" in p.read_text(encoding="utf-8")
                  for p in trail.glob("*.md")))

        # ------------------------------------------------ 10
        turn(10, "the session resumes after compaction")
        r = hook("session_start.py", {"hook_event_name": "SessionStart",
                                      "source": "compact"}, d)
        check("the new decision is now in the briefing",
              "Store ticks as Parquet" in r["context"], r["context"][:200])

        # ------------------------------------------------ 11
        turn(11, "the briefing is rewritten and a line is dropped")
        git(d, "add", "-A")
        git(d, "-c", "commit.gpgsign=false", "commit", "-qm", "Record the decision")
        state = d / "docs" / "project-memory" / "00-PROJECT-STATE.md"
        state.write_text(
            state.read_text(encoding="utf-8").replace(
                "The loader is pinned to the GREENFINCH-7 endpoint and must not move.\n",
                ""), encoding="utf-8")
        r = hook("stop_gate.py", {"hook_event_name": "Stop"}, d)
        check("the dropped line is caught", "GREENFINCH-7" in r["context"],
              r["context"][:200] or "(silent)")
        check("with somewhere to put it", "CONSTRAINTS" in r["context"].upper(),
              r["context"][:200])

        # ------------------------------------------------ 12
        turn(12, "a project with records but no briefing at all")
        state.unlink()
        git(d, "add", "-A")
        git(d, "-c", "commit.gpgsign=false", "commit", "-qm", "Drop the briefing")
        r = hook("stop_gate.py", {"hook_event_name": "Stop"}, d)
        check("the missing cold-start entry point is reported",
              "no briefing file" in r["context"], r["context"][:200] or "(silent)")

        print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
        for name in FAILED:
            print(f"  failed: {name}")
        return 1 if FAILED else 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
