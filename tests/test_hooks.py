"""Hermetic tests for the decision-ledger hooks.

No dependencies. Run:  python tests/test_hooks.py

Each test builds a throwaway git repo with a ledger in it, feeds a hook the
JSON it would really receive on stdin, and asserts on what comes back. The
regression test near the bottom covers the one bug these hooks actually shipped
with: git collapses untracked directories, so an untracked ledger file never
appeared as docs/project-memory/... and the Stop gate fired when it should have
stayed quiet.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    (PASSED if condition else FAILED).append(name)
    mark = "ok  " if condition else "FAIL"
    print(f"  [{mark}] {name}" + (f"  -- {detail}" if detail and not condition else ""))


def run_hook(script, payload, env=None):
    e = dict(os.environ)
    e.pop("LEDGER_STRICT", None)
    if env:
        e.update(env)
    out = subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        input=json.dumps(payload), capture_output=True, text=True, env=e, timeout=30,
    )
    return out.stdout.strip(), out.stderr.strip(), out.returncode


def as_json(stdout):
    try:
        return json.loads(stdout) if stdout else None
    except json.JSONDecodeError:
        return None


def context_of(stdout):
    j = as_json(stdout)
    return (j or {}).get("hookSpecificOutput", {}).get("additionalContext", "")


def make_repo(with_ledger=True):
    d = Path(tempfile.mkdtemp(prefix="ledger-test-"))
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=d, check=True)
    if with_ledger:
        lm = d / "docs" / "project-memory"
        for sub in ("decisions", "rejections", "change-requests"):
            (lm / sub).mkdir(parents=True, exist_ok=True)
        (lm / "00-PROJECT-STATE.md").write_text(
            "# State\n\nAll good.\n", encoding="utf-8")
        (lm / "CONSTRAINTS.md").write_text(
            "# Constraints\n\n## Deploys need the VPN on\n\nDetail here.\n",
            encoding="utf-8")
        (lm / "rejections" / "REJ-0001-use-mongodb.md").write_text(
            "---\nid: REJ-0001\ntype: rejection\ntitle: Use MongoDB\n"
            "status: rejected\n---\n\n# REJ-0001: Use MongoDB\n", encoding="utf-8")
    return d


def commit_all(d, msg="base"):
    subprocess.run(["git", "add", "-A"], cwd=d, check=True, capture_output=True)
    subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-qm", msg],
                   cwd=d, check=True, capture_output=True)


def test_session_start():
    print("\nSessionStart")
    d = make_repo()
    try:
        out, _, code = run_hook("session_start.py", {
            "cwd": str(d), "hook_event_name": "SessionStart", "source": "startup"})
        j = as_json(out)
        ctx = context_of(out)
        check("exits 0", code == 0, f"code={code}")
        check("emits hookSpecificOutput", bool(j and "hookSpecificOutput" in j))
        check("names the event",
              (j or {}).get("hookSpecificOutput", {}).get("hookEventName") == "SessionStart")
        check("includes the state file", "All good." in ctx)
        check("surfaces rejections by title", "Use MongoDB" in ctx)
        check("surfaces constraints by heading", "Deploys need the VPN on" in ctx)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_briefing_without_constraints_file():
    """A project with no CONSTRAINTS.md must still brief cleanly.

    The file is new, so every ledger created before it exists lacks one. The
    briefing must omit the section rather than fail or print an empty heading.
    """
    print("\nSessionStart - no CONSTRAINTS.md")
    d = make_repo()
    try:
        (d / "docs" / "project-memory" / "CONSTRAINTS.md").unlink()
        out, _, code = run_hook("session_start.py", {"cwd": str(d)})
        ctx = context_of(out)
        check("exits 0", code == 0)
        check("still briefs", "All good." in ctx)
        check("omits the empty section", "Constraints in force" not in ctx)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_silent_without_ledger():
    """A project with no ledger gets nothing recorded and almost nothing said.

    `session_start.py` is the deliberate exception since ADR-0045: it says,
    once per project, that the plugin is installed and not active here.
    Without that one line a correct install is indistinguishable from a
    broken one. The other four stay silent -- a reminder on every edit, every
    prompt and every turn end in a project that never opted in is the noise
    that gets a plugin uninstalled.
    """
    print("\nNo ledger in project -> the hooks stay silent, bar one notice")
    d = make_repo(with_ledger=False)
    try:
        for script in ("post_tool_use.py", "stop_gate.py",
                       "user_prompt_submit.py"):
            out, _, code = run_hook(script, {
                "cwd": str(d), "prompt": "lets go with Parquet",
                "tool_name": "Edit", "tool_input": {"file_path": str(d / "a.py")},
            })
            check(f"{script} silent", out == "" and code == 0, f"out={out[:60]!r}")

        out, _, code = run_hook("session_start.py", {
            "cwd": str(d), "hook_event_name": "SessionStart"})
        check("session_start.py says the project is not opted in",
              code == 0 and "not opted in" in out, f"out={out[:80]!r}")
        check("and injects no briefing it does not have",
              "Settled rejections" not in out, f"out={out[:80]!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_pre_compact():
    print("\nPreCompact")
    d = make_repo()
    try:
        out, _, code = run_hook("pre_compact.py", {
            "cwd": str(d), "hook_event_name": "PreCompact", "trigger": "auto"})
        check("exits 0", code == 0)
        check("emits plain text, not JSON", as_json(out) is None and len(out) > 50)
        check("instructs on reasoning", "reasoning" in out.lower())
        check("within the 10k cap", len(out) < 10000, f"len={len(out)}")
        logs = list((d / "docs" / "project-memory" / "activity").glob("*.md"))
        check("writes a checkpoint to disk", len(logs) == 1)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_prompt_classifier():
    print("\nUserPromptSubmit")
    d = make_repo()
    try:
        fires = [
            ("lets go with Parquet for the tick data", "decision"),
            ("use duckdb instead of sqlite here", "diversion"),
            ("dont use pandas for this, it is too slow", "rejection"),
            ("that wont work, the broker rejects it", "rejection"),
            ("also need a drawdown cap on the backtest", "change request"),
        ]
        for prompt, kind in fires:
            out, _, _ = run_hook("user_prompt_submit.py", {"cwd": str(d), "prompt": prompt})
            got = context_of(out)
            check(f"fires on {prompt[:28]!r}", kind in got, f"got={got[:70]!r}")

        for prompt in ["what does this function do", "run the tests",
                       "show me the backtest results", "ok"]:
            out, _, _ = run_hook("user_prompt_submit.py", {"cwd": str(d), "prompt": prompt})
            check(f"quiet on {prompt[:28]!r}", out == "", f"got={out[:60]!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_stop_gate():
    print("\nStop gate")
    d = make_repo()
    try:
        commit_all(d)

        (d / "model.py").write_text("x = 1\n", encoding="utf-8")
        out, _, _ = run_hook("stop_gate.py", {"cwd": str(d), "stop_hook_active": False})
        check("reminds when only code changed", "model.py" in context_of(out),
              f"got={out[:80]!r}")

        out2, _, _ = run_hook("stop_gate.py", {"cwd": str(d), "stop_hook_active": False})
        check("de-duplicates the same change set", out2 == "", f"got={out2[:60]!r}")

        out3, _, _ = run_hook("stop_gate.py", {"cwd": str(d), "stop_hook_active": True})
        check("honours stop_hook_active", out3 == "")

        (d / ".git" / "ledger-last-nag").unlink(missing_ok=True)
        out4, _, _ = run_hook("stop_gate.py", {"cwd": str(d), "stop_hook_active": False},
                              env={"LEDGER_STRICT": "1"})
        j4 = as_json(out4)
        check("blocks under LEDGER_STRICT", (j4 or {}).get("decision") == "block")
        check("gives a reason when blocking", bool((j4 or {}).get("reason")))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_stop_gate_untracked_regression():
    """Regression: git status collapses untracked directories.

    With plain --porcelain, an untracked docs/project-memory/ADR file is
    reported as 'docs/', which does not match the ledger prefix, so the gate
    concluded nothing had been recorded and fired. --untracked-files=all fixes it.
    """
    print("\nStop gate - untracked directory regression")
    d = make_repo()
    try:
        commit_all(d)
        (d / "model.py").write_text("x = 1\n", encoding="utf-8")
        rec = d / "docs" / "project-memory" / "decisions" / "ADR-0001-x.md"
        rec.parent.mkdir(parents=True, exist_ok=True)
        rec.write_text("---\nid: ADR-0001\n---\n# ADR-0001\n", encoding="utf-8")

        out, _, _ = run_hook("stop_gate.py", {"cwd": str(d), "stop_hook_active": False})
        check("silent when an untracked ledger record exists", out == "",
              f"fired with: {out[:120]!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_orphan_detection():
    """Content dropped from the mutable state file with no copy elsewhere."""
    print("\nState-file orphan detection")
    d = make_repo()
    try:
        lm = d / "docs" / "project-memory"
        (lm / "00-PROJECT-STATE.md").write_text(
            "# State\n\n## Constraints\n\n"
            "- Deploys require the corporate VPN to be connected first\n"
            "- The staging database resets every Sunday at midnight\n",
            encoding="utf-8")
        commit_all(d)

        # Drop one line to an append-only file, delete the other outright.
        (lm / "CONSTRAINTS.md").write_text(
            "# Constraints\n\n## Deploys require the corporate VPN "
            "to be connected first\n", encoding="utf-8")
        (lm / "00-PROJECT-STATE.md").write_text(
            "# State\n\n## Constraints\n\nSee CONSTRAINTS.md\n", encoding="utf-8")

        env = dict(os.environ, LEDGER_PROJECT_DIR=str(d))
        r = subprocess.run([sys.executable, str(SCRIPTS / "check_state.py")],
                           capture_output=True, text=True, env=env,
                           cwd=str(d), timeout=30)
        check("exits 1 when something was orphaned", r.returncode == 1, r.stdout[:120])
        check("flags the line that went nowhere",
              "staging database resets" in r.stdout, r.stdout[:200])
        check("does not flag the line that was moved to CONSTRAINTS.md",
              "corporate VPN" not in r.stdout, r.stdout[:200])

        # Now move the second line too; nothing should be orphaned.
        with (lm / "CONSTRAINTS.md").open("a", encoding="utf-8") as fh:
            fh.write("\n## The staging database resets every Sunday at midnight\n")
        r2 = subprocess.run([sys.executable, str(SCRIPTS / "check_state.py")],
                            capture_output=True, text=True, env=env,
                            cwd=str(d), timeout=30)
        check("exits 0 once everything is preserved", r2.returncode == 0, r2.stdout[:200])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_index_refuses_to_clobber():
    """A hand-written INDEX.md must survive a build_index run."""
    print("\nIndex clobber guard")
    d = make_repo()
    try:
        lm = d / "docs" / "project-memory"
        handwritten = "# My own index\n\nNotes I maintain by hand.\n"
        (lm / "INDEX.md").write_text(handwritten, encoding="utf-8")
        env = dict(os.environ, LEDGER_PROJECT_DIR=str(d))

        r = subprocess.run([sys.executable, str(SCRIPTS / "build_index.py")],
                           capture_output=True, text=True, env=env, timeout=30)
        check("refuses to overwrite a foreign index", r.returncode == 1)
        check("says why", "refusing to overwrite" in r.stderr, r.stderr[:120])
        check("leaves the file untouched",
              (lm / "INDEX.md").read_text(encoding="utf-8") == handwritten)

        # Its own generated index may be replaced.
        (lm / "INDEX.md").unlink()
        r2 = subprocess.run([sys.executable, str(SCRIPTS / "build_index.py")],
                            capture_output=True, text=True, env=env, timeout=30)
        check("generates when absent", r2.returncode == 0, r2.stderr[:120])
        r3 = subprocess.run([sys.executable, str(SCRIPTS / "build_index.py")],
                            capture_output=True, text=True, env=env, timeout=30)
        check("regenerates its own output", r3.returncode == 0, r3.stderr[:120])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_new_record_refuses_to_clobber():
    """Record files are never overwritten, even on an id collision."""
    print("\nRecord clobber guard")
    d = make_repo()
    try:
        lm = d / "docs" / "project-memory"
        existing = lm / "rejections" / "REJ-0001-use-mongodb.md"
        original = existing.read_text(encoding="utf-8")
        env = dict(os.environ, LEDGER_PROJECT_DIR=str(d))
        subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"), "rej",
                        "Use MongoDB"], capture_output=True, text=True,
                       env=env, timeout=30)
        check("existing record is unchanged",
              existing.read_text(encoding="utf-8") == original)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def make_adopted_repo():
    """A project shaped like a mature one: big CHANGELOG and STATUS at root."""
    d = Path(tempfile.mkdtemp(prefix="ledger-adopt-"))
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=d, check=True)
    (d / "CHANGELOG.md").write_text(
        "# CHANGELOG\n\n## 2026-11-22 - real history\n\nYears of this.\n",
        encoding="utf-8")
    (d / "STATUS.md").write_text(
        "# STATUS\n\n" + "\n".join(f"status line {i}" for i in range(2000)),
        encoding="utf-8")
    lm = d / "docs" / "project-memory"
    lm.mkdir(parents=True)
    (lm / "00-BRIEFING.md").write_text(
        "# Briefing\n\nShort summary. Full log: STATUS.md\n", encoding="utf-8")
    (d / ".ledger.json").write_text(json.dumps({
        "version": 1,
        "paths": {
            "briefing": "docs/project-memory/00-BRIEFING.md",
            "changelog": "CHANGELOG.md",
            "journey": "docs/project-memory/JOURNEY.md",
            "constraints": "docs/project-memory/CONSTRAINTS.md",
            "index": "docs/project-memory/INDEX.md",
            "decisions": "docs/project-memory/decisions",
            "rejections": "docs/project-memory/rejections",
            "change_requests": "docs/project-memory/change-requests",
            "activity": "docs/project-memory/activity",
        },
        "adopted": ["changelog"],
    }, indent=2), encoding="utf-8")
    return d


def test_adopt_existing_project():
    """The ledger maps onto files a project already keeps, without duplicating."""
    print("\nAdopting a project that already keeps notes")
    d = make_adopted_repo()
    try:
        env = dict(os.environ, LEDGER_PROJECT_DIR=str(d))

        out, _, _ = run_hook("session_start.py", {"cwd": str(d)})
        ctx = context_of(out)
        check("config alone activates the ledger", bool(ctx))
        check("injects the small briefing", "Short summary" in ctx)
        check("does not inject the 2000-line STATUS.md",
              "status line 1500" not in ctx, "big status file leaked in")

        before = (d / "CHANGELOG.md").read_text(encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"),
                            "adr", "Use Parquet for tick storage"],
                           capture_output=True, text=True, env=env, timeout=30)
        check("creates the record", r.returncode == 0, r.stderr[:120])
        after = (d / "CHANGELOG.md").read_text(encoding="utf-8")
        check("adds to the adopted changelog", len(after) > len(before))
        # The default is newest-first, so the entry goes above the first entry
        # heading rather than at the end. Every original line must survive.
        check("keeps every original line",
              all(ln in after for ln in before.splitlines() if ln.strip()))
        check("entry lands above the newest existing entry",
              after.index("ADR-0001") < after.index("## 2026-11-22"))
        check("creates no duplicate changelog",
              not (d / "docs" / "project-memory" / "CHANGELOG.md").exists())

        idx = subprocess.run([sys.executable, str(SCRIPTS / "build_index.py")],
                             capture_output=True, text=True, env=env, timeout=30)
        check("builds the index at the configured path", idx.returncode == 0,
              idx.stderr[:120])
        check("index links the record",
              "ADR-0001" in (d / "docs" / "project-memory" / "INDEX.md")
              .read_text(encoding="utf-8"))

        commit_all(d)
        (d / "model.py").write_text("x = 1\n", encoding="utf-8")
        with (d / "CHANGELOG.md").open("a", encoding="utf-8") as fh:
            fh.write("- another entry\n")
        out2, _, _ = run_hook("stop_gate.py",
                              {"cwd": str(d), "stop_hook_active": False})
        check("counts the adopted root changelog as a ledger file", out2 == "",
              f"warned anyway: {out2[:90]!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_newest_first_changelog_insertion():
    """A newest-first changelog gets the entry at the top, not the bottom.

    Appending to the bottom of a newest-first file files the new entry under
    the oldest heading, which is wrong rather than merely untidy. Trade
    Manager's changelog is 220 entries newest-first, which is what prompted it.
    """
    print("\nNewest-first changelog insertion")
    d = Path(tempfile.mkdtemp(prefix="ledger-order-"))
    try:
        entries = [f"## 2026-11-{22 - (i % 20):02d} - Entry {i}\n\nProse {i}.\n"
                   for i in range(220)]
        original = ("# CHANGELOG\n\nIntro that must stay on top.\n\n"
                    + "\n".join(entries))
        (d / "CHANGELOG.md").write_text(original, encoding="utf-8")
        (d / ".ledger.json").write_text(json.dumps({
            "version": 1,
            "paths": {
                "changelog": "CHANGELOG.md",
                "decisions": "docs/project-memory/decisions",
                "briefing": "docs/project-memory/00-BRIEFING.md",
            },
            "adopted": ["changelog"],
            "changelog_order": "newest-first",
            "changelog_entry": "## {date} - {id} {title}\n\nRecorded in `{path}`.\n",
        }, indent=2), encoding="utf-8")

        env = dict(os.environ, LEDGER_PROJECT_DIR=str(d))
        r = subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"),
                            "adr", "Use Parquet"], capture_output=True,
                           text=True, env=env, timeout=30)
        check("creates the record", r.returncode == 0, r.stderr[:120])

        new = (d / "CHANGELOG.md").read_text(encoding="utf-8")
        headings = [ln for ln in new.splitlines() if ln.startswith("## ")]
        check("intro stays on top",
              new.startswith("# CHANGELOG\n\nIntro that must stay on top."))
        check("entry lands above the newest, not at the bottom",
              "ADR-0001" in headings[0], headings[0][:60])
        check("uses the project's own entry format", headings[0].startswith("## 2026-"))
        check("nothing else was lost", all(e.strip() in new for e in entries))
        check("file grew", len(new) > len(original))
        check("no temp file left behind", not list(d.glob("*.ledger-tmp")))

        # Oldest-first, declared explicitly, must still append to the bottom.
        (d / ".ledger.json").write_text(json.dumps({
            "version": 1,
            "paths": {"changelog": "CHANGELOG.md",
                      "decisions": "docs/project-memory/decisions",
                      "briefing": "docs/project-memory/00-BRIEFING.md"},
            "changelog_order": "oldest-first",
        }, indent=2), encoding="utf-8")
        subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"),
                        "adr", "Second one"], capture_output=True, text=True,
                       env=env, timeout=30)
        tail_text = (d / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()[-1]
        check("oldest-first appends to the bottom", "ADR-0002" in tail_text,
              tail_text[:70])

        # With no order declared at all, the default is newest-first.
        (d / ".ledger.json").write_text(json.dumps({
            "version": 1,
            "paths": {"changelog": "CHANGELOG.md",
                      "decisions": "docs/project-memory/decisions",
                      "briefing": "docs/project-memory/00-BRIEFING.md"},
        }, indent=2), encoding="utf-8")
        subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"),
                        "adr", "Third one"], capture_output=True, text=True,
                       env=env, timeout=30)
        text = (d / "CHANGELOG.md").read_text(encoding="utf-8")
        check("default is newest-first", text.index("ADR-0003") < text.index("ADR-0001"),
              "default did not insert at the top")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_scanner_detects_real_shapes():
    """The scanner against the shapes actually found in 82 real projects.

    Each fixture below is modelled on a specimen from that survey: a
    newest-first file with ## headings, one that declares its order in words,
    an oldest-first file, and a single-entry file that cannot be judged.
    """
    print("\nConvention scanner")
    import importlib
    sys.path.insert(0, str(SCRIPTS))
    scan_project = importlib.import_module("scan_project")

    cases = {
        "newest-first with ## headings": (
            "# CHANGELOG\n\n## 2026-11-22 - latest thing\n\nProse.\n\n"
            "## 2026-10-18 - older thing\n\nProse.\n",
            "newest-first", "##", True),
        "declares its own order": (
            "# CHANGELOG\n\nNewest first.\n\n## 2026-11-20 - a thing\n\nProse.\n",
            "newest-first", "##", True),
        "oldest-first": (
            "# CHANGELOG\n\n## 2026-01-02 - first\n\nProse.\n\n"
            "## 2026-11-20 - last\n\nProse.\n",
            "oldest-first", "##", True),
        "single entry, unjudgeable": (
            "# CHANGELOG\n\n## 2026-11-14 - only entry\n\nProse.\n",
            "single-entry", "##", False),
        "version headings, no ISO dates": (
            "# Changelog\n\n## v2 (Current - June 2026)\n\n- thing\n\n"
            "## v1\n\n- thing\n",
            None, "##", False),
    }
    d = Path(tempfile.mkdtemp(prefix="ledger-scan-"))
    try:
        for name, (text, want_order, want_style, want_conf) in cases.items():
            f = d / "CHANGELOG.md"
            f.write_text(text, encoding="utf-8")
            shape = scan_project.changelog_shape(f)
            check(f"{name}: order", shape["order"] == want_order,
                  f"got {shape['order']!r}")
            check(f"{name}: style", shape["entry_style"] == want_style,
                  f"got {shape['entry_style']!r}")
            check(f"{name}: confidence", shape["order_confident"] == want_conf,
                  f"got {shape['order_confident']!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # A project with a big STATUS.md must never have it adopted as the briefing.
    d2 = make_adopted_repo()
    try:
        (d2 / ".ledger.json").unlink()
        cfg, review = scan_project.propose(d2)
        check("adopts the existing changelog", "changelog" in cfg["adopted"])
        check("never adopts the status file", "status" not in cfg["adopted"])
        check("briefing stays ledger-owned",
              cfg["paths"]["briefing"].startswith("docs/project-memory/"))
        check("warns about the unadopted status file",
              any("STATUS.md" in r for r in review))
        check("copies the entry format", "changelog_entry" in cfg)
    finally:
        shutil.rmtree(d2, ignore_errors=True)

    # An unjudgeable changelog must be written down as unconfirmed, not omitted.
    d3 = Path(tempfile.mkdtemp(prefix="ledger-scan2-"))
    try:
        (d3 / "CHANGELOG.md").write_text(
            "# CHANGELOG\n\n## 2026-11-14 - only entry\n\nProse.\n",
            encoding="utf-8")
        cfg, review = scan_project.propose(d3)
        check("marks an undetermined order unconfirmed",
              cfg.get("unconfirmed") == ["changelog_order"], str(cfg.get("unconfirmed")))
        check("tells the caller to ask",
              any("ASK the user" in r for r in review))
    finally:
        shutil.rmtree(d3, ignore_errors=True)


def test_crlf_changelog_keeps_its_line_endings():
    """A CRLF changelog must keep CRLF everywhere, and grow by exactly the block.

    Found by simulating adoption against a clone of a real 369 KB changelog:
    writing with newline="\\n" rewrote all 5,349 line endings from CRLF to LF.
    git normalises line endings, so the diff showed only "8 insertions" while
    the whole file had in fact been rewritten.

    Byte count is the assertion, because it is the one thing git cannot hide.
    """
    print("\nCRLF changelog")
    for eol, label in ((b"\r\n", "CRLF"), (b"\n", "LF")):
        d = Path(tempfile.mkdtemp(prefix="ledger-eol-"))
        try:
            body = (b"# CHANGELOG" + eol + eol
                    + b"## 2026-11-22 - newest" + eol + eol
                    + b"Prose." + eol + eol
                    + b"## 2026-10-18 - oldest" + eol + eol
                    + b"Prose." + eol)
            (d / "CHANGELOG.md").write_bytes(body)
            (d / ".ledger.json").write_text(json.dumps({
                "version": 1,
                "paths": {"changelog": "CHANGELOG.md",
                          "decisions": "docs/project-memory/decisions",
                          "briefing": "docs/project-memory/00-BRIEFING.md"},
                "adopted": ["changelog"],
                "changelog_order": "newest-first",
                "changelog_entry": "## {date} - {id} {title}\n\nRecorded in `{path}`.\n",
            }), encoding="utf-8")

            env = dict(os.environ, LEDGER_PROJECT_DIR=str(d))
            r = subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"),
                                "adr", "A decision"], capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               env=env, timeout=30)
            check(f"{label}: record created", r.returncode == 0, r.stderr[:120])

            after = (d / "CHANGELOG.md").read_bytes()
            check(f"{label}: original lines all still present",
                  all(ln in after for ln in body.split(eol) if ln.strip()))
            check(f"{label}: no foreign line endings introduced",
                  after.count(b"\r\n") == (after.count(b"\n") if eol == b"\r\n" else 0),
                  f"crlf={after.count(b'crlf'[:0] + b'\\r\\n')} lf={after.count(b'\\n')}")
            # The file may only grow, never shrink: shrinkage means endings
            # were rewritten across the whole file.
            check(f"{label}: file grew, did not shrink", len(after) > len(body),
                  f"{len(body)} -> {len(after)}")
            # Every pre-existing line ending survives untouched.
            check(f"{label}: original ending count preserved",
                  after.count(eol) >= body.count(eol),
                  f"{body.count(eol)} -> {after.count(eol)}")
        finally:
            shutil.rmtree(d, ignore_errors=True)


def test_role_classification():
    """File-name classification, using the names that actually fooled it.

    Every "should not match" below is a real filename from the 82-project
    survey that the first implementation classified as a journey. Journey is
    an adopted role, so each one was a file the ledger would have started
    writing session narrative into.
    """
    print("\nRole classification")
    import importlib
    sys.path.insert(0, str(SCRIPTS))
    scan_project = importlib.import_module("scan_project")

    should_match = {
        "CHANGELOG.md": "changelog",
        "CHANGES.md": "changelog",
        "JOURNEY.md": "journey",
        "SESSION_LOG.md": "journey",
        "docs/DEVLOG.md": "journey",
        "STATUS.md": "status",
        "CONSTRAINTS.md": "constraints",
        "PLAN.md": "plan",
        "README.md": "readme",
        "NOTES.md": "journey",
    }
    should_not = [
        "docs/API_NOTES.md",
        "docs/PLATFORM_NOTES.md",
        "docs/02-research-notes.md",
        "VIDEO_DOWNLOAD_research_log.md",
        "docs/capturing-screenshots.md",
        "docs/news-names.md",
        "docs/HANDOVER.md",
    ]
    for name, want in should_match.items():
        got = scan_project.role_of(Path(name))
        check(f"{name} -> {want}", got == want, f"got {got!r}")
    for name in should_not:
        got = scan_project.role_of(Path(name))
        check(f"{name} -> nothing", got is None, f"wrongly classified as {got!r}")


def test_refuses_to_rewrite_non_utf8_changelog():
    """A changelog that is not valid UTF-8 is left completely alone.

    Reading with errors="replace" and writing the result back would swap
    U+FFFD in for every undecodable byte and rewrite the whole file. On a
    changelog that may be the only copy of years of work, that is silent
    corruption, so the write is refused instead.
    """
    print("\nNon-UTF-8 changelog")
    d = Path(tempfile.mkdtemp(prefix="ledger-enc-"))
    try:
        # cp1252 em dash and curly quote: invalid as UTF-8.
        raw = b"# CHANGELOG\n\n## 2026-11-22 \x97 a thing \x93quoted\x94\n\nProse.\n"
        (d / "CHANGELOG.md").write_bytes(raw)
        (d / ".ledger.json").write_text(json.dumps({
            "version": 1,
            "paths": {"changelog": "CHANGELOG.md",
                      "decisions": "docs/project-memory/decisions",
                      "briefing": "docs/project-memory/00-BRIEFING.md"},
            "adopted": ["changelog"],
        }), encoding="utf-8")

        env = dict(os.environ, LEDGER_PROJECT_DIR=str(d))
        r = subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"),
                            "adr", "Something"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, timeout=30)
        check("fails rather than corrupting", r.returncode != 0, f"rc={r.returncode}")
        check("says why", "not valid UTF-8" in (r.stderr + r.stdout),
              (r.stderr + r.stdout)[:150])
        check("leaves the file byte-identical",
              (d / "CHANGELOG.md").read_bytes() == raw)
        check("leaves no temp file", not list(d.glob("*.ledger-tmp")))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_malformed_config_is_not_fatal():
    """A typo in .ledger.json must not break a session."""
    print("\nMalformed config")
    d = make_repo()
    try:
        (d / ".ledger.json").write_text("{ this is not json", encoding="utf-8")
        out, _, code = run_hook("session_start.py", {"cwd": str(d)})
        check("exits 0", code == 0)
        check("falls back to the default layout", "All good." in context_of(out),
              f"got {out[:90]!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_record_scaffolding():
    print("\nRecord scaffolding")
    d = make_repo()
    try:
        env = dict(os.environ, LEDGER_PROJECT_DIR=str(d))

        def new_record(kind, title):
            return subprocess.run(
                [sys.executable, str(SCRIPTS / "new_record.py"), kind, title],
                capture_output=True, text=True, env=env, timeout=30)

        for kind, prefix in (("adr", "ADR"), ("rej", "REJ"), ("cr", "CR")):
            r = new_record(kind, "Some decision about storage")
            check(f"creates a {prefix}", r.returncode == 0, r.stderr[:120])
            if r.returncode == 0:
                check(f"{prefix} file exists", Path(r.stdout.strip()).is_file())

        # REJ-0001 exists in the fixture and REJ-0002 was just made, so next is 0003.
        r = new_record("rej", "Another idea")
        check("does not collide with an existing id", "REJ-0003" in r.stdout,
              r.stdout.strip())

        r = new_record("nonsense", "x")
        check("rejects an unknown record kind", r.returncode == 1)

        idx = subprocess.run([sys.executable, str(SCRIPTS / "build_index.py")],
                             capture_output=True, text=True, env=env, timeout=30)
        check("builds the index", idx.returncode == 0, idx.stderr[:120])
        content = (d / "docs" / "project-memory" / "INDEX.md").read_text(encoding="utf-8")
        check("index lists every type",
              all(s in content for s in ("Decisions", "Rejections", "Change requests")))
        check("index links a record", "REJ-0001" in content)
    finally:
        shutil.rmtree(d, ignore_errors=True)



def test_record_number_parsing():
    """Bare-numbered records, and the year trap.

    adr-tools writes 0001-title.md with no prefix at all, so requiring one
    made the scanner blind to the most common ADR convention there is. The
    YEAR_FLOOR test is what stops 2026-11-22-notes.md reading as record 2026
    and pushing the next id to 2027.
    """
    print("\nRecord filename parsing")
    sys.path.insert(0, str(SCRIPTS))
    import _ledger as L
    cases = [
        ("0001-module-boundaries", None, 1),
        ("ADR-0007-foo", None, 7),
        ("adr_12-x", None, 12),
        ("0004", None, 4),
        ("2026-11-22-notes", None, None),
        ("1900-x", None, None),
        ("1899-x", None, 1899),
        ("readme", None, None),
        ("notes-on-adr-0005", None, None),
        ("REJ-0003-x", "ADR", None),
        ("ADR-0003-x", "ADR", 3),
    ]
    for stem, prefix, want in cases:
        got = L.record_number(stem, prefix)
        check(f"{stem!r}" + (f" as {prefix}" if prefix else "") + f" -> {want}",
              got == want, f"got {got}")


def test_next_id_continues_adopted_numbering():
    """The bug this pins: restarting at 0001 beside someone's existing 0001.

    A project with docs/adr/0001..0002 that adopts the ledger must get 0003.
    Two different decisions filed under one number is worse than a gap.
    """
    print("\nAdopted decisions directory")
    d = make_repo(with_ledger=False)
    try:
        adr = d / "docs" / "adr"
        adr.mkdir(parents=True)
        for n, name in ((1, "single-threaded-router"), (2, "sqlite-fills")):
            (adr / f"{n:04d}-{name}.md").write_text(
                f"# {n}. {name}\n\nDate: 2026-07-10\n", encoding="utf-8")
        (adr / "README.md").write_text("# ADRs\n", encoding="utf-8")
        (d / ".ledger.json").write_text(json.dumps({
            "version": 1,
            "paths": {"decisions": "docs/adr"},
            "adopted": ["decisions"],
            "record_names": "bare",
        }), encoding="utf-8")
        commit_all(d)

        env = dict(os.environ, LEDGER_PROJECT_DIR=str(d))
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "new_record.py"), "adr", "Cap slippage"],
            capture_output=True, text=True, env=env, cwd=d, timeout=30)
        check("new_record succeeds", out.returncode == 0, out.stderr)
        created = Path(out.stdout.strip()) if out.stdout.strip() else None
        check("lands in the adopted directory",
              created is not None and created.parent == adr,
              str(created))
        check("continues their numbering at 0003",
              created is not None and created.name.startswith("0003-"),
              created.name if created else "none")
        check("does not re-use an existing number",
              created is not None and not created.name.startswith("0001"))
        check("the id inside the record is still prefixed",
              created is not None and "id: ADR-0003" in
              created.read_text(encoding="utf-8"))
        check("their files are untouched",
              (adr / "0001-single-threaded-router.md").read_text(encoding="utf-8")
              == "# 1. single-threaded-router\n\nDate: 2026-07-10\n")

        # The ledger's own folders keep their prefixes: matching a convention
        # is for fitting into someone else's directory, not restyling ours.
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "new_record.py"), "rej", "Threaded writer"],
            capture_output=True, text=True, env=env, cwd=d, timeout=30)
        rej = Path(out.stdout.strip()) if out.stdout.strip() else None
        check("our own rejection stays REJ-prefixed",
              rej is not None and rej.name.startswith("REJ-0001-"),
              rej.name if rej else "none")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_scanner_adopts_unprefixed_adr_dir():
    """Silence was the real defect: a record directory it did not understand
    produced no review note at all, so a second decisions folder appeared
    beside the project's own with nobody told."""
    print("\nScanner on an unprefixed ADR directory")
    d = make_repo(with_ledger=False)
    try:
        adr = d / "docs" / "adr"
        adr.mkdir(parents=True)
        for n in (1, 2, 3, 4):
            (adr / f"{n:04d}-decision.md").write_text(f"# {n}\n", encoding="utf-8")
        commit_all(d)
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "scan_project.py"), "--propose", str(d)],
            capture_output=True, text=True, timeout=60)
        cfg = json.loads(out.stdout)
        notes = out.stderr
        check("points decisions at the existing directory",
              cfg["paths"]["decisions"] == "docs/adr", cfg["paths"]["decisions"])
        check("marks decisions adopted", "decisions" in cfg["adopted"])
        check("records the bare naming convention",
              cfg.get("record_names") == "bare", str(cfg.get("record_names")))
        check("says where numbering continues", "0005" in notes, notes)
        check("does not stay silent about it", "docs/adr" in notes)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_scanner_ignores_its_own_directory():
    """A project that already has the ledger must not be warned about its own
    files. Making the review note unconditional introduced exactly that."""
    print("\nScanner on an already-installed ledger")
    d = make_repo(with_ledger=True)
    try:
        commit_all(d)
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "scan_project.py"), "--propose", str(d)],
            capture_output=True, text=True, timeout=60)
        check("no complaint about docs/project-memory",
              "no numbering this tool recognises" not in out.stderr, out.stderr)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_missing_briefing_warning():
    """Records can accumulate with no briefing and trip nothing else: writing
    records *is* touching the ledger, so the unrecorded-change nag stays quiet
    while the cold-start promise quietly fails."""
    print("\nMissing briefing")
    d = make_repo(with_ledger=True)
    try:
        state = d / "docs" / "project-memory" / "00-PROJECT-STATE.md"
        state.unlink()
        commit_all(d)
        out, _, code = run_hook("stop_gate.py",
                                {"cwd": str(d), "stop_hook_active": False},
                                env={"LEDGER_PROJECT_DIR": str(d)})
        ctx = context_of(out)
        check("exits 0", code == 0)
        check("warns that the briefing is missing", "no briefing file" in ctx, ctx[:200])
        check("names the record count", "1 ledger record" in ctx, ctx[:200])

        # And stays quiet once it exists.
        state.write_text("# State\n\nAll good.\n", encoding="utf-8")
        shutil.rmtree(d / ".git" / "ledger-last-briefing", ignore_errors=True)
        (d / ".git" / "ledger-last-briefing").unlink(missing_ok=True)
        out, _, code = run_hook("stop_gate.py",
                                {"cwd": str(d), "stop_hook_active": False},
                                env={"LEDGER_PROJECT_DIR": str(d)})
        check("silent once a briefing exists",
              "no briefing file" not in context_of(out), context_of(out)[:200])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_history_mining():
    """Backfill evidence, and the two bugs this found.

    1. str.splitlines() treats \x1e as a line break, so the sentinel-prefixed
       deletion format was shredded by the call parsing it -- deleted_paths
       returned [] on every repository while the git query was correct. No
       repository in the 82-project corpus has a deletion, so nothing caught it.
    2. Counting "has a body" as a signal flagged 98% of real commits, because
       in that corpus almost every commit has one.
    """
    print("\nHistory mining")
    sys.path.insert(0, str(SCRIPTS))
    import mine_history as M
    d = make_repo(with_ledger=False)
    try:
        (d / "keep.py").write_text("x = 1\n", encoding="utf-8")
        (d / "lstm.py").write_text("y = 2\n", encoding="utf-8")
        commit_all(d, "Add tick loader")
        subprocess.run(["git", "rm", "-q", "lstm.py"], cwd=d, check=True,
                       capture_output=True)
        subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-qm",
                        "Revert the LSTM experiment\n\nIt overfit on three "
                        "months and scored worse than the baseline."],
                       cwd=d, check=True, capture_output=True)

        dele = M.deleted_paths(d)
        check("finds the deleted file", len(dele) == 1, str(dele))
        check("names it", dele and dele[0]["path"] == "lstm.py", str(dele))
        check("carries a date", bool(dele) and dele[0]["date"].startswith("20"),
              str(dele))

        info = M.scan(d)
        subjects = {c["subject"].split("\n")[0]: c for c in info["candidates"]}
        check("flags the revert",
              any(s.startswith("Revert the LSTM") for s in subjects), str(subjects))
        rev = next((c for s, c in subjects.items()
                    if s.startswith("Revert the LSTM")), None)
        check("as a rejection", rev is not None and rev["kind"] == "rej",
              str(rev and rev["kind"]))
        check("skips the mechanical commit",
              not any(s == "Add tick loader" for s in subjects), str(subjects))
        check("writes nothing", not (d / "docs").exists())

        # Body weighting is decided per repository, not globally.
        check("body counts as a signal when bodies are rare",
              info["body_informative"] is True)
        many = make_repo(with_ledger=False)
        try:
            for i in range(6):
                (many / f"f{i}.py").write_text("x\n", encoding="utf-8")
                commit_all(many, f"Change {i}\n\nA body on every commit.")
            check("body stops being a signal when every commit has one",
                  M.scan(many)["body_informative"] is False)
        finally:
            shutil.rmtree(many, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_scanner_flags_undocumented_history():
    """A project with months of commits and no notes is not greenfield. If the
    scanner does not say so, the backfill skill is never discovered and the
    reasoning behind everything already built stays in the commit log."""
    print("\nUndocumented working project")
    d = make_repo(with_ledger=False)
    try:
        # Commits that actually carry reasoning. The original fixture used
        # "Switch module N to the new loader" six times, which scores below the
        # evidence threshold -- so it asserted that the backfill is recommended
        # for a history the miner can recover nothing from.
        for i in range(6):
            (d / f"mod{i}.py").write_text("x = 1\n", encoding="utf-8")
            commit_all(d, f"Switch module {i} to Parquet because load time "
                          f"dropped from 40s to 2s")
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "scan_project.py"), "--propose", str(d)],
            capture_output=True, text=True, timeout=60)
        check("says it is not greenfield", "NOT greenfield" in out.stderr, out.stderr)
        check("points at the backfill skill",
              "ledger-backfill" in out.stderr, out.stderr)
        check("counts the commits", "6 commits" in out.stderr, out.stderr)
        check("counts the evidence", "carry evidence" in out.stderr, out.stderr)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_fresh_project_is_not_told_to_backfill():
    """The mirror of the test above: a genuinely new project must not be sent
    to reconstruct a history it does not have."""
    print("\nFresh project")
    d = make_repo(with_ledger=False)
    try:
        (d / "README.md").write_text("# new\n", encoding="utf-8")
        commit_all(d, "Initial commit")
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "scan_project.py"), "--propose", str(d)],
            capture_output=True, text=True, timeout=60)
        check("no backfill advice", "ledger-backfill" not in out.stderr, out.stderr)
        check("defaults are proposed",
              json.loads(out.stdout)["paths"]["changelog"]
              == "docs/project-memory/CHANGELOG.md")
        check("nothing adopted", json.loads(out.stdout)["adopted"] == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_worktree_is_recognised_as_git():
    """A linked worktree has `.git` as a FILE, not a directory.

    `(root/'.git').is_dir()` was false there, so the scanner reported "not a
    git repository", the miner reported zero commits, and a project with
    months of history read as greenfield. Claude Code's own desktop sessions
    run in worktrees, so this was a default environment, not an exotic one.
    """
    print("\nGit worktrees")
    d = make_repo(with_ledger=False)
    holder = Path(tempfile.mkdtemp(prefix="ledger-wt-"))
    wt = holder / "linked"
    try:
        (d / "README.md").write_text("# p\n", encoding="utf-8")
        commit_all(d, "initial: add readme")
        for i in range(5):
            (d / "app.py").write_text(f"x{i}\n", encoding="utf-8")
            commit_all(d, "switch to parquet because load dropped from 40s to 2s")
        subprocess.run(["git", "worktree", "add", "-q", str(wt), "-b", "wtbranch"],
                       cwd=d, check=True, capture_output=True)
        check(".git is a file in the worktree", (wt / ".git").is_file())
        sys.path.insert(0, str(SCRIPTS))
        import _ledger as L
        import mine_history
        check("is_git_repo sees the worktree", L.is_git_repo(wt))
        gd = L.git_dir(wt)
        check("git_dir resolves the real git dir", gd is not None and gd.exists())
        info = mine_history.scan(wt)
        check("miner finds the history",
              info["is_git"] and info["total_commits"] == 6,
              f"is_git={info['is_git']} commits={info['total_commits']}")
        out = subprocess.run([sys.executable, str(SCRIPTS / "scan_project.py"), str(wt)],
                             capture_output=True, text=True, timeout=60)
        check("scanner reports is_git", json.loads(out.stdout)["is_git"])
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)],
                       cwd=d, capture_output=True)
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(holder, ignore_errors=True)


def test_stop_gate_dedup_works_in_a_worktree():
    """The de-dup marker lived in cwd/.git, which is a file in a worktree.

    mkdir raised, the marker was never written, and the Stop hook repeated the
    identical reminder on every single turn -- the exact behaviour that trains
    someone to uninstall the plugin.
    """
    print("\nStop gate de-duplication in a worktree")
    d = make_repo(with_ledger=False)
    holder = Path(tempfile.mkdtemp(prefix="ledger-wt2-"))
    wt = holder / "linked"
    try:
        (d / "README.md").write_text("# p\n", encoding="utf-8")
        commit_all(d, "init")
        subprocess.run(["git", "worktree", "add", "-q", str(wt), "-b", "wt2branch"],
                       cwd=d, check=True, capture_output=True)
        (wt / "docs" / "project-memory").mkdir(parents=True, exist_ok=True)
        (wt / "newcode.py").write_text("x\n", encoding="utf-8")
        seen = []
        for _ in range(3):
            out, _e, _c = run_hook("stop_gate.py", {"cwd": str(wt),
                                                    "hook_event_name": "Stop"})
            seen.append(bool(out.strip()))
        check("warns the first time", seen[0] is True, str(seen))
        check("stays quiet afterwards", seen[1:] == [False, False], str(seen))
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)],
                       cwd=d, capture_output=True)
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(holder, ignore_errors=True)


def test_miner_summary_survives_a_non_git_path():
    """`--summary` died with KeyError: 'first_commit' on any non-git path.

    The early return built a dict with fewer keys than the normal one. The
    backfill skill's first instruction is to run exactly this command, so the
    crash sat on the entry point of the feature.
    """
    print("\nMiner on a path with no history")
    d = Path(tempfile.mkdtemp(prefix="ledger-nogit-"))
    try:
        out = subprocess.run([sys.executable, str(SCRIPTS / "mine_history.py"),
                              str(d), "--summary"], capture_output=True,
                             text=True, timeout=60)
        check("exits 0", out.returncode == 0, out.stderr[-200:])
        check("says there is no repository", "not a git repository" in out.stdout)
        sys.path.insert(0, str(SCRIPTS))
        import mine_history
        expected = set(mine_history.EMPTY)
        got = set(mine_history.scan(d))
        check("same keys as a real scan", expected <= got, f"missing {expected - got}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_index_writes_to_the_configured_path():
    """build_index checked the marker on the configured path and then wrote to
    the default one, destroying a hand-written INDEX.md that sat there.

    The guard was looking at a different file from the one being written,
    which is worse than no guard: it reported success.
    """
    print("\nIndex honours a configured path")
    d = make_repo(with_ledger=False)
    try:
        (d / "docs" / "adr").mkdir(parents=True)
        (d / "docs" / "adr" / "0001-router.md").write_text(
            "---\nid: 0001\ntitle: Router\n---\n# Router\n", encoding="utf-8")
        (d / "docs" / "project-memory").mkdir(parents=True)
        precious = d / "docs" / "project-memory" / "INDEX.md"
        precious.write_text("# Hand-written index\n\nYears of work.\n",
                            encoding="utf-8")
        (d / ".ledger.json").write_text(json.dumps({
            "paths": {"index": "docs/adr/INDEX.md", "decisions": "docs/adr"},
            "adopted": ["decisions"]}), encoding="utf-8")
        out = subprocess.run([sys.executable, str(SCRIPTS / "build_index.py")],
                             capture_output=True, text=True, timeout=60,
                             env=dict(os.environ, LEDGER_PROJECT_DIR=str(d)))
        check("exits 0", out.returncode == 0, out.stderr[-200:])
        check("writes the configured index",
              (d / "docs" / "adr" / "INDEX.md").is_file())
        check("leaves the hand-written file alone",
              precious.read_text(encoding="utf-8").startswith("# Hand-written"))
        check("reports the file it actually wrote",
              "adr" in out.stdout and out.stdout.strip().endswith("INDEX.md"),
              out.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_configured_paths_cannot_leave_the_project():
    """`paths` is hand-editable and `root / "C:/x"` discards the root entirely.

    An absolute or `../` override pointed the ledger outside the repository it
    was installed in. Rejected in favour of the default; legitimate relative
    overrides are untouched.
    """
    print("\nConfigured paths stay inside the project")
    d = Path(tempfile.mkdtemp(prefix="ledger-esc-"))
    try:
        sys.path.insert(0, str(SCRIPTS))
        import _ledger as L
        payload = {"cwd": str(d)}
        for bad in ("../../outside/CHANGELOG.md", "/etc/passwd", "C:/Windows/evil.md"):
            (d / ".ledger.json").write_text(
                json.dumps({"paths": {"changelog": bad}}), encoding="utf-8")
            got = L.path_for("changelog", payload)
            check(f"rejects {bad}", str(got).startswith(str(d)), str(got))
        (d / ".ledger.json").write_text(
            json.dumps({"paths": {"changelog": "notes/CHANGELOG.md"}}),
            encoding="utf-8")
        check("keeps a legitimate override",
              L.path_for("changelog", payload) == d / "notes" / "CHANGELOG.md")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_config_of_the_wrong_shape_is_not_fatal():
    """Valid JSON of the wrong type crashed inside the hooks.

    `"paths": "docs"` raised AttributeError on the next `.get`, and
    `"changelog_order": true` on `.lower()`. The contract is that a bad config
    reads as absent, which has to cover the shape as well as the syntax.
    `"adopted": "decisions"` was worse than a crash: it substring-matched, so
    unrelated keys came back adopted.
    """
    print("\nConfig of the wrong shape")
    d = Path(tempfile.mkdtemp(prefix="ledger-shape-"))
    try:
        sys.path.insert(0, str(SCRIPTS))
        import _ledger as L
        payload = {"cwd": str(d)}
        bad_shapes = [{"paths": "docs"}, {"adopted": "decisions"},
                      {"changelog_order": True}, {"record_names": 5},
                      {"adopted": {"a": 1}}, {"paths": {"changelog": None}}]
        crashes = []
        for cfg in bad_shapes:
            (d / ".ledger.json").write_text(json.dumps(cfg), encoding="utf-8")
            calls = (lambda: L.path_for("changelog", payload),
                     lambda: L.is_adopted("decisions", payload),
                     lambda: L.record_name_style("adr", payload),
                     lambda: L.ledger_paths(payload),
                     lambda: L.rel_path("briefing", payload))
            for call in calls:
                try:
                    call()
                except Exception as exc:
                    crashes.append(f"{cfg}: {type(exc).__name__}")
        check("nothing crashes", not crashes, "; ".join(crashes[:3]))
        (d / ".ledger.json").write_text(
            json.dumps({"adopted": "decisions-and-more"}), encoding="utf-8")
        check("a string never substring-matches as adopted",
              not L.is_adopted("decisions", payload))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_session_start_caps_what_it_injects():
    """Rejections were capped at 40; decisions and change requests were not.

    A long-lived project injected one line per accepted ADR into the start of
    every session, crowding out the briefing -- which is the part that
    actually orients a cold start.
    """
    print("\nSessionStart stays bounded")
    d = make_repo()
    try:
        # Read the constant out of the source rather than importing it: the
        # hook scripts call L.guard(body) at module level, so importing one
        # runs the hook and then sys.exit()s, which takes the test run with it.
        src = (SCRIPTS / "session_start.py").read_text(encoding="utf-8")
        cap = int(re.search(r"^MAX_DECISIONS = (\d+)", src, re.M).group(1))
        folder = d / "docs" / "project-memory" / "decisions"
        total = cap + 25
        for i in range(1, total + 1):
            (folder / f"ADR-{i:04d}-decision.md").write_text(
                f"---\nid: ADR-{i:04d}\ntitle: Decision {i}\nstatus: accepted\n"
                f"---\n\n# ADR-{i:04d}: Decision {i}\n", encoding="utf-8")
        out, _e, _c = run_hook("session_start.py",
                               {"cwd": str(d), "hook_event_name": "SessionStart"})
        ctx = context_of(out)
        listed = sum(1 for ln in ctx.splitlines() if ln.startswith("- **ADR-"))
        check("caps the decision list", listed == cap, f"listed {listed}")
        check("says how many were withheld", f"{total - cap} older" in ctx)
        check("keeps the newest", f"**ADR-{total:04d}**" in ctx)
        check("drops the oldest", "**ADR-0001**" not in ctx)
        check("still includes the briefing", "All good." in ctx)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_messages_name_the_projects_own_files():
    """Hook messages printed the default filenames even at a project that
    adopted different ones, sending the reader to a file that does not exist.
    """
    print("\nMessages name the configured files")
    d = make_repo(with_ledger=False)
    try:
        (d / "docs").mkdir()
        (d / ".ledger.json").write_text(json.dumps({
            "paths": {"briefing": "docs/STATUS.md",
                      "constraints": "docs/GOTCHAS.md"}}), encoding="utf-8")
        (d / "docs" / "GOTCHAS.md").write_text(
            "# Gotchas\n\n## Deploys need the VPN on\n", encoding="utf-8")
        out, _e, _c = run_hook("session_start.py",
                               {"cwd": str(d), "hook_event_name": "SessionStart"})
        ctx = context_of(out)
        check("names the adopted briefing", "docs/STATUS.md" in ctx, ctx[:200])
        check("does not name our default", "00-PROJECT-STATE.md" not in ctx)
        check("names the adopted constraints file", "docs/GOTCHAS.md" in ctx)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_installed_project_is_not_told_to_backfill():
    """The ledger's own files are excluded from role detection, so a project
    that already has the ledger looked exactly like one with no memory files.

    Every scan of every real installation was therefore advising a backfill
    that would reconstruct what was already recorded. This fired for the
    plugin's own repository, which is how it was noticed.
    """
    print("\nAn already-installed project")
    d = make_repo()
    try:
        folder = d / "docs" / "project-memory" / "decisions"
        for i in range(1, 4):
            (folder / f"ADR-{i:04d}-choice.md").write_text(
                f"---\nid: ADR-{i:04d}\ntitle: Choice {i}\nstatus: accepted\n"
                f"---\n\n# x\n", encoding="utf-8")
        for i in range(6):
            (d / "app.py").write_text(f"x{i}\n", encoding="utf-8")
            commit_all(d, "switch to Parquet because load time dropped 40s to 2s")
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "scan_project.py"), "--propose", str(d)],
            capture_output=True, text=True, timeout=60)
        check("no backfill advice for an installed ledger",
              "greenfield" not in out.stderr,
              [ln.strip() for ln in out.stderr.splitlines() if "greenfield" in ln])
        # ...and a .ledger.json alone is enough, with no records yet
        d2 = make_repo(with_ledger=False)
        try:
            (d2 / ".ledger.json").write_text("{}", encoding="utf-8")
            for i in range(6):
                (d2 / "app.py").write_text(f"x{i}\n", encoding="utf-8")
                commit_all(d2, "switch to Parquet because load dropped 40s to 2s")
            out2 = subprocess.run(
                [sys.executable, str(SCRIPTS / "scan_project.py"), "--propose", str(d2)],
                capture_output=True, text=True, timeout=60)
            check("a .ledger.json alone also counts as installed",
                  "greenfield" not in out2.stderr, out2.stderr[-200:])
        finally:
            shutil.rmtree(d2, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_history_with_no_recoverable_reasoning():
    """Advising a reconstruction that will find nothing is noise, and noise is
    what gets a tool uninstalled. The project is still not greenfield, so say
    that -- but say the backfill will not help, and what to do instead.
    """
    print("\nHistory with nothing to recover")
    d = make_repo(with_ledger=False)
    try:
        for i in range(8):
            (d / "app.py").write_text(f"x{i}\n", encoding="utf-8")
            commit_all(d, f"wip {i}")
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "scan_project.py"), "--propose", str(d)],
            capture_output=True, text=True, timeout=60)
        err = out.stderr
        check("still says it is not greenfield", "NOT greenfield" in err, err[-200:])
        check("says the backfill would recover almost nothing",
              "reconstruct almost nothing" in err, err[-200:])
        check("redirects to asking for the rejections",
              "rejections directly" in err, err[-200:])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_index_escapes_a_pipe_in_a_title():
    """An unescaped `|` in a title opened an extra column and shifted every
    value in that row: the title spilled into the status cell.
    """
    print("\nIndex cell escaping")
    d = make_repo()
    try:
        env = dict(os.environ, LEDGER_PROJECT_DIR=str(d))
        subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"), "adr",
                        "Use | instead of comma as the delimiter"],
                       capture_output=True, text=True, env=env, timeout=30)
        subprocess.run([sys.executable, str(SCRIPTS / "build_index.py")],
                       capture_output=True, text=True, env=env, timeout=30)
        idx = (d / "docs" / "project-memory" / "INDEX.md").read_text(encoding="utf-8")
        row = next((ln for ln in idx.splitlines() if "ADR-0001" in ln), "")
        # Count only the pipes that still act as cell separators.
        separators = len(re.findall(r"(?<!\\)\|", row))
        check("the row still has exactly four cells", separators == 5,
              f"{separators} separators in {row.strip()[:120]}")
        check("the pipe survives in the title, escaped", r"\|" in row, row[:120])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_record_reads_survive_a_bom():
    """A UTF-8 BOM made the first line `\\ufeff---`, so the frontmatter block
    was skipped entirely and the record lost its id, status and date in both
    the index and the session briefing. Several Windows editors write one.
    """
    print("\nRecords written with a BOM")
    d = make_repo()
    try:
        folder = d / "docs" / "project-memory" / "decisions"
        (folder / "ADR-0002-bom.md").write_text(
            "---\nid: ADR-0002\ntitle: Written with a BOM\nstatus: accepted\n"
            "date: 2026-05-01\n---\n\n# x\n", encoding="utf-8-sig")
        env = dict(os.environ, LEDGER_PROJECT_DIR=str(d))
        subprocess.run([sys.executable, str(SCRIPTS / "build_index.py")],
                       capture_output=True, text=True, env=env, timeout=30)
        idx = (d / "docs" / "project-memory" / "INDEX.md").read_text(encoding="utf-8")
        row = next((ln for ln in idx.splitlines() if "bom.md" in ln), "")
        check("the id is read from the frontmatter", "ADR-0002]" in row, row[:140])
        check("the title is read", "Written with a BOM" in row, row[:140])
        check("the status is read", "accepted" in row, row[:140])
        check("the date is read", "2026-05-01" in row, row[:140])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_concurrent_records_get_distinct_ids():
    """Two sessions recording at the same moment both computed the same next id.

    Either they wrote the same filename, where one silently replaced the other,
    or two filenames under one number. The changelog write raced too: both
    processes used one fixed temp name, so one os.replace failed and that
    record landed with no changelog entry.
    """
    print("\nConcurrent record allocation")
    import threading
    d = make_repo()
    try:
        env = dict(os.environ, LEDGER_PROJECT_DIR=str(d))
        outcomes = []

        def go(i):
            p = subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"),
                                "adr", f"Concurrent choice {i}"],
                               capture_output=True, text=True, env=env, timeout=60)
            outcomes.append((p.returncode, p.stderr))

        threads = [threading.Thread(target=go, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        failures = [e for rc, e in outcomes if rc != 0]
        # Full stderr, not a tail: this check has failed once under full-suite
        # load and never in isolation, so the one chance to diagnose it is the
        # run that fails. A truncated message wasted that chance already.
        check("every run succeeded", not failures,
              " || ".join(" ".join(f.split()) for f in failures))
        made = sorted((d / "docs" / "project-memory" / "decisions").glob("*.md"))
        nums = [L_record_number(p.stem) for p in made]
        check("no two records share an id", len(set(nums)) == len(nums), str(nums))
        check("one file per run", len(made) == 5, str([p.name for p in made]))
        cl = (d / "docs" / "project-memory" / "CHANGELOG.md")
        entries = [ln for ln in cl.read_text(encoding="utf-8").splitlines() if ln.strip()]
        check("no changelog entry was lost to the write race",
              len(entries) == len(made), f"{len(made)} records, {len(entries)} entries")
        leftovers = list((d / "docs" / "project-memory").glob("*.ledger-tmp"))
        check("no temp file left behind", not leftovers, str(leftovers))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def L_record_number(stem):
    sys.path.insert(0, str(SCRIPTS))
    import _ledger as L
    return L.record_number(stem, "ADR")


def test_record_directory_that_is_a_file():
    """`mkdir(exist_ok=True)` still raises when the path exists as a file."""
    print("\nA record directory that is really a file")
    d = make_repo(with_ledger=False)
    try:
        (d / "docs" / "project-memory").mkdir(parents=True)
        (d / "docs" / "project-memory" / "decisions").write_text("notes\n",
                                                                  encoding="utf-8")
        out = subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"),
                              "adr", "Something"], capture_output=True, text=True,
                             env=dict(os.environ, LEDGER_PROJECT_DIR=str(d)),
                             timeout=30)
        check("fails cleanly", out.returncode == 1, f"rc={out.returncode}")
        check("no traceback", "Traceback" not in out.stderr, out.stderr[-160:])
        check("says what is wrong", "decisions" in out.stderr, out.stderr[-160:])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_failed_write_leaves_no_temp_file():
    """A read-only changelog left CHANGELOG.md.ledger-tmp beside it forever."""
    print("\nA write that cannot complete")
    d = make_repo()
    cl = d / "docs" / "project-memory" / "CHANGELOG.md"
    try:
        cl.write_text("# Changelog\n\n## 2026-01-01\n- x\n", encoding="utf-8")
        os.chmod(cl, 0o444)
        subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"), "adr",
                        "Something"], capture_output=True, text=True,
                       env=dict(os.environ, LEDGER_PROJECT_DIR=str(d)), timeout=30)
        leftovers = list((d / "docs" / "project-memory").glob("*ledger-tmp*"))
        check("no temp file left behind", not leftovers, str(leftovers))
        check("the read-only file is untouched",
              cl.read_text(encoding="utf-8").startswith("# Changelog"))
    finally:
        try:
            os.chmod(cl, 0o666)
        except OSError:
            pass
        shutil.rmtree(d, ignore_errors=True)


def test_hooks_survive_hostile_payloads():
    """Every hook, against every shape of wrong input a harness might send.

    Half of these payloads carry no usable `cwd`, which is the point: a hook
    must survive one. But `project_dir()` then falls back to the process
    working directory, and that fallback is load-bearing in real use -- a live
    session had `LEDGER_PROJECT_DIR`, `CLAUDE_PROJECT_DIR` and
    `CLAUDE_PLUGIN_ROOT` all empty, leaving cwd as the only thing left.

    So these subprocesses run with cwd pinned to a sandbox. Without that they
    inherit the suite's own working directory, find THIS repository's ledger,
    and write to it for real: four compaction checkpoints into the activity
    trail on every run, plus a rewrite of `.git/ledger-baseline`, which is the
    Stop gate's record of what was already dirty when the session began. 270
    of the 271 lines in this repo's trail were put there by this test, not by
    any compaction. `test_the_suite_leaves_this_repository_alone` now fails if
    it happens again.

    `LEDGER_PROJECT_DIR` is deliberately not used for the pinning: it outranks
    the payload, so it would also neutralise the `cwd` each payload carries,
    and those are the subject of the test.
    """
    print("\nHostile hook payloads")
    d = make_repo()
    try:
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(d))
        env.pop("LEDGER_PROJECT_DIR", None)
        env.pop("LEDGER_STRICT", None)
        payloads = [
            {"hook_event_name": "Stop"},
            {"cwd": r"Z:\no\such\place", "hook_event_name": "Stop"},
            {"cwd": None, "hook_event_name": "Stop"},
            {"cwd": 42, "hook_event_name": "Stop"},
            [],
        ]
        for script in ("session_start.py", "stop_gate.py", "post_tool_use.py",
                       "user_prompt_submit.py", "pre_compact.py"):
            bad = []
            for payload in payloads:
                p = subprocess.run([sys.executable, str(SCRIPTS / script)],
                                   input=json.dumps(payload), capture_output=True,
                                   text=True, timeout=30, cwd=str(d), env=env)
                if p.returncode != 0 or "Traceback" in p.stderr:
                    bad.append(f"{payload}(rc={p.returncode})")
            for raw in ("", "not json at all"):
                p = subprocess.run([sys.executable, str(SCRIPTS / script)], input=raw,
                                   capture_output=True, text=True, timeout=30,
                                   cwd=str(d), env=env)
                if p.returncode != 0 or "Traceback" in p.stderr:
                    bad.append(f"raw {raw!r}(rc={p.returncode})")
            check(f"{script} survives every bad payload", not bad, "; ".join(bad[:3]))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_unborn_and_detached_head():
    """A repository with no commits at all, and a detached HEAD."""
    print("\nUnborn and detached HEAD")
    d = make_repo()
    try:
        for script in ("session_start.py", "stop_gate.py", "pre_compact.py"):
            out, err, code = run_hook(script, {"cwd": str(d),
                                               "hook_event_name": "X"})
            check(f"{script} survives an unborn HEAD",
                  code == 0 and "Traceback" not in err, err[-140:])
        commit_all(d, "one")
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=d,
                             capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "checkout", "-q", sha], cwd=d, capture_output=True)
        out, err, code = run_hook("stop_gate.py", {"cwd": str(d),
                                                   "hook_event_name": "Stop"})
        check("stop_gate survives a detached HEAD",
              code == 0 and "Traceback" not in err, err[-140:])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_activity_trail_does_not_silence_the_nag():
    """The PostToolUse hook writes the activity trail on every edit, and the
    trail is a ledger path. The Stop gate treated any dirty ledger path as
    "something was recorded", so on the first edit in a freshly installed
    project the hook created `activity/.gitignore`, git reported it untracked,
    and the gate went quiet.

    The first session of every new project -- the one where the habit is being
    set -- therefore got no reminder at all. Found by replaying a session in
    order; no single-hook test can reach it, because an earlier turn has to
    create the condition.
    """
    print("\nThe activity trail is not a recording")
    d = make_repo()
    try:
        (d / "README.md").write_text("# p\n", encoding="utf-8")
        commit_all(d, "initial")
        # Turn 1: an edit, which makes the PostToolUse hook create the trail.
        (d / "feed.py").write_text("x = 1\n", encoding="utf-8")
        run_hook("post_tool_use.py", {
            "cwd": str(d), "hook_event_name": "PostToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": str(d / "feed.py")}})
        gi = d / "docs" / "project-memory" / "activity" / ".gitignore"
        check("the hook created the trail's .gitignore", gi.is_file())
        # Turn 2: the session ends with code changed and nothing recorded.
        out, _e, _c = run_hook("stop_gate.py", {"cwd": str(d),
                                                "hook_event_name": "Stop"})
        ctx = context_of(out)
        check("the gate still warns", "decision ledger" in ctx,
              ctx[:160] or "(silent)")
        check("and names the changed file", "feed.py" in ctx, ctx[:160])
        check("but does not name the activity trail", "activity" not in ctx,
              ctx[:200])

        sys.path.insert(0, str(SCRIPTS))
        import _ledger as L
        payload = {"cwd": str(d)}
        trail = "docs/project-memory/activity/2026-01-01.md"
        check("the trail is still a ledger path", L.is_ledger_path(trail, payload))
        check("but is not a recording path",
              not L.is_recording_path(trail, payload))
        check("a decision record is a recording path",
              L.is_recording_path("docs/project-memory/decisions/ADR-0001-x.md",
                                   payload))
        check("ordinary code is neither",
              not L.is_ledger_path("feed.py", payload)
              and not L.is_recording_path("feed.py", payload))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_recording_a_decision_still_silences_the_nag():
    """The mirror: writing an actual record must satisfy the gate, or the
    reminder becomes unanswerable and people turn it off."""
    print("\nA real record satisfies the gate")
    d = make_repo()
    try:
        (d / "README.md").write_text("# p\n", encoding="utf-8")
        commit_all(d, "initial")
        (d / "feed.py").write_text("x = 1\n", encoding="utf-8")
        out, _e, _c = run_hook("stop_gate.py", {"cwd": str(d),
                                                "hook_event_name": "Stop"})
        check("warns before anything is recorded",
              "decision ledger" in context_of(out), context_of(out)[:120])
        subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"), "adr",
                        "Store ticks as Parquet"], capture_output=True, text=True,
                       env=dict(os.environ, LEDGER_PROJECT_DIR=str(d)), timeout=30)
        out, _e, _c = run_hook("stop_gate.py", {"cwd": str(d),
                                                "hook_event_name": "Stop"})
        check("quiet once the decision is recorded", not context_of(out).strip(),
              context_of(out)[:160])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_no_unanchored_script_paths_in_instructions():
    r"""Every instruction telling anyone to run a plugin script must anchor it.

    `scripts/` ships with the PLUGIN; an agent's working directory is the
    USER'S project. A bare `python scripts/new_record.py` therefore resolves
    to `<their repo>/scripts/...` and finds nothing. A live session hit this
    on all nine skill call sites and fell back to numbering records by hand --
    bypassing the atomic id allocation, the CRLF-safe changelog insert and the
    whole deterministic layer, while appearing to work.

    `$CLAUDE_PLUGIN_ROOT` is not the fix: the harness substitutes it for hook
    commands, but it is empty in a tool shell, and in Git Bash the empty
    expansion silently becomes a path under the Git installation.
    """
    print("\nScript paths in instructions are anchored")
    import re
    cmd = re.compile(r"(?:python3?|py)\s+[\"']?([^\s\"'`]+\.py)")
    script_names = {p.name for p in (ROOT / "scripts").glob("*.py")}
    targets = (list((ROOT / "skills").rglob("*.md"))
               + [ROOT / "README.md", ROOT / "docs" / "INSTALL.md",
                  ROOT / "docs" / "AGENT-INSTALL.md"]
               + list((ROOT / "scripts").glob("*.py")))
    bad = []
    for f in targets:
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for m in cmd.finditer(line):
                path = m.group(1).replace("\\", "/")
                if path.rsplit("/", 1)[-1] not in script_names:
                    continue
                anchored = ("CLAUDE_PLUGIN_ROOT" in line or "<plugin" in line
                            or "skill base directory" in line
                            or path.startswith(("$", "${")))
                if not anchored:
                    bad.append(f"{f.relative_to(ROOT).as_posix()}:{i}")
    check("no bare 'python scripts/...' anywhere", not bad, "; ".join(bad[:5]))

    abs_re = re.compile(r"(?<![\w`])([A-Za-z]:[\\/][^\s`'\"<>|)]{3,})")
    stray = []
    for f in targets:
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for m in abs_re.finditer(line):
                if m.group(1).startswith(("C:/Windows", "C:\\Windows")):
                    continue  # the deliberate hostile-path examples
                stray.append(f"{f.relative_to(ROOT).as_posix()}:{i} {m.group(1)[:50]}")
    check("no absolute machine paths in instructions", not stray,
          "; ".join(stray[:3]))


def test_project_flag_pins_the_project():
    """Scripts fell back to the working directory to find the project.

    In an agent's shell LEDGER_PROJECT_DIR, CLAUDE_PROJECT_DIR and
    CLAUDE_PLUGIN_ROOT are all empty, so the fallback is cwd -- and a live
    session had its cwd reset mid-session by the harness. The record would
    have been scaffolded into an unrelated folder, silently, with the script
    reporting success.
    """
    print("\n--project pins the project")
    d = make_repo()
    elsewhere = Path(tempfile.mkdtemp(prefix="ledger-elsewhere-"))
    try:
        env = dict(os.environ)
        env.pop("LEDGER_PROJECT_DIR", None)
        env.pop("CLAUDE_PROJECT_DIR", None)
        # Run FROM the wrong directory, with the right one passed explicitly.
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "new_record.py"), "--project", str(d),
             "adr", "Pinned correctly"],
            capture_output=True, text=True, cwd=str(elsewhere), env=env, timeout=30)
        check("exits 0", out.returncode == 0, out.stderr[-200:])
        made = list((d / "docs" / "project-memory" / "decisions").glob("*.md"))
        check("the record lands in the named project", len(made) == 1,
              str([p.name for p in made]))
        check("and nothing is written to the working directory",
              not (elsewhere / "docs").exists(),
              str(list(elsewhere.iterdir())))
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "build_index.py"), f"--project={d}"],
            capture_output=True, text=True, cwd=str(elsewhere), env=env, timeout=30)
        check("build_index accepts --project=<path> too", out.returncode == 0,
              out.stderr[-160:])
        check("the index lands in the named project",
              (d / "docs" / "project-memory" / "INDEX.md").is_file())
        check("still nothing in the working directory",
              not (elsewhere / "docs").exists())
    finally:
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(elsewhere, ignore_errors=True)


def test_session_start_hands_over_absolute_paths():
    """The briefing carries the two paths an agent cannot work out itself."""
    print("\nSessionStart hands over the paths")
    d = make_repo()
    try:
        out, _e, _c = run_hook("session_start.py", {"cwd": str(d),
                                                    "hook_event_name": "SessionStart"})
        ctx = context_of(out)
        scripts_dir = (ROOT / "scripts").resolve().as_posix()
        check("names the absolute scripts directory", scripts_dir in ctx,
              ctx[-400:])
        check("names the absolute project root",
              Path(d).resolve().as_posix() in ctx, ctx[-400:])
        check("shows a runnable example with --project", "--project" in ctx)
        check("warns off the empty plugin-root variable",
              "CLAUDE_PLUGIN_ROOT" in ctx and "empty" in ctx)
        sys.path.insert(0, str(SCRIPTS))
        import _ledger as L
        check("plugin_root finds scripts and skills as siblings",
              (L.plugin_root() / "scripts").is_dir()
              and (L.plugin_root() / "skills").is_dir(), str(L.plugin_root()))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_stop_gate_ignores_what_was_already_dirty():
    """The gate listed every pre-existing untracked file as this session's
    unrecorded work.

    A live session had it flag an editor settings file that predated the
    session and that the session never wrote to -- on a turn where the real
    decision had already been recorded, so the hook's only output was a false
    positive. On a real project every untracked file would appear at the end
    of every session, and the warning that matters would look exactly like the
    noise. That is the failure REJ-0004 exists to avoid, arriving by a
    different route.
    """
    print("\nStop gate ignores pre-existing mess")
    d = make_repo()
    try:
        (d / "README.md").write_text("# p\n", encoding="utf-8")
        commit_all(d, "initial")
        # Mess that predates the session: untracked, and a modified tracked file.
        (d / ".editor-settings.json").write_text("{}\n", encoding="utf-8")
        (d / "scratch.tmp").write_text("x\n", encoding="utf-8")
        (d / "README.md").write_text("# p\n\nedited before the session\n",
                                     encoding="utf-8")

        out, _e, _c = run_hook("session_start.py", {"cwd": str(d),
                                                    "hook_event_name": "SessionStart"})
        check("SessionStart still emits its briefing", bool(context_of(out)))
        sys.path.insert(0, str(SCRIPTS))
        import _ledger as L
        base = L.read_session_baseline(d)
        check("a baseline was recorded", bool(base), str(base))
        paths = (base or {}).get("paths") or {}
        check("the baseline holds the pre-existing paths",
              ".editor-settings.json" in paths and "README.md" in paths,
              str(sorted(paths)))
        check("and the commit the session started from",
              bool((base or {}).get("head")), str(base)[:120])

        out, _e, _c = run_hook("stop_gate.py", {"cwd": str(d),
                                                "hook_event_name": "Stop"})
        check("the gate is silent about pre-existing mess",
              not context_of(out).strip(), context_of(out)[:200])

        # Now the session actually changes something.
        (d / "feed.py").write_text("x = 1\n", encoding="utf-8")
        out, _e, _c = run_hook("stop_gate.py", {"cwd": str(d),
                                                "hook_event_name": "Stop"})
        ctx = context_of(out)
        check("it warns about the real change", "feed.py" in ctx,
              ctx[:200] or "(silent)")
        check("and does not name the pre-existing untracked file",
              ".editor-settings.json" not in ctx, ctx[:250])
        check("nor the file modified before the session started",
              "README.md" not in ctx, ctx[:250])

        # A pre-existing file edited DURING the session is this session's work.
        d2 = make_repo()
        try:
            (d2 / "README.md").write_text("# q\n", encoding="utf-8")
            commit_all(d2, "initial")
            (d2 / "already.py").write_text("before\n", encoding="utf-8")
            run_hook("session_start.py", {"cwd": str(d2),
                                          "hook_event_name": "SessionStart"})
            time.sleep(1.1)  # mtime has one-second resolution in the baseline
            (d2 / "already.py").write_text("before and after\n", encoding="utf-8")
            out, _e, _c = run_hook("stop_gate.py", {"cwd": str(d2),
                                                    "hook_event_name": "Stop"})
            check("a pre-existing file edited during the session IS reported",
                  "already.py" in context_of(out),
                  context_of(out)[:200] or "(silent)")
        finally:
            shutil.rmtree(d2, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_stop_gate_without_a_baseline_reports_everything():
    """With no baseline -- git unavailable, or SessionStart never ran -- the
    gate must over-report rather than go quiet. A missed reminder is the
    failure that matters; an extra one is only noise."""
    print("\nStop gate with no baseline")
    d = make_repo()
    try:
        (d / "README.md").write_text("# p\n", encoding="utf-8")
        commit_all(d, "initial")
        (d / "feed.py").write_text("x = 1\n", encoding="utf-8")
        sys.path.insert(0, str(SCRIPTS))
        import _ledger as L
        gd = L.git_dir(d)
        if gd is not None:
            marker = gd / "ledger-baseline"
            if marker.exists():
                marker.unlink()
        out, _e, _c = run_hook("stop_gate.py", {"cwd": str(d),
                                                "hook_event_name": "Stop"})
        check("still warns with no baseline", "feed.py" in context_of(out),
              context_of(out)[:160] or "(silent)")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_a_committed_record_still_counts_as_recorded():
    """Committing the ledger used to erase the gate's evidence of it.

    wrap-session tells the agent to commit; committing empties the dirty set,
    which was the only place the gate looked for proof anything was recorded.
    A live session wrote a record, committed it, and was told on the same turn
    that nothing was written to the ledger -- with the working tree's junk
    listed as the unrecorded work. The gate read the absence of its own
    evidence as proof of the opposite, and only because the skill had just
    been fixed to commit.
    """
    print("\nA committed record still counts")
    d = make_repo()
    try:
        (d / "README.md").write_text("# p\n", encoding="utf-8")
        commit_all(d, "initial")
        run_hook("session_start.py", {"cwd": str(d),
                                      "hook_event_name": "SessionStart"})
        (d / "feed.py").write_text("x = 1\n", encoding="utf-8")
        (d / "junk.log").write_text("noise\n", encoding="utf-8")
        subprocess.run([sys.executable, str(SCRIPTS / "new_record.py"),
                        "--project", str(d), "adr", "Compress with zstd"],
                       capture_output=True, text=True, timeout=30)
        out, _e, _c = run_hook("stop_gate.py", {"cwd": str(d),
                                                "hook_event_name": "Stop"})
        check("quiet while the record is still uncommitted",
              not context_of(out).strip(), context_of(out)[:160])

        commit_all(d, "Record the decision and the work")
        out, _e, _c = run_hook("stop_gate.py", {"cwd": str(d),
                                                "hook_event_name": "Stop"})
        ctx = context_of(out)
        check("still quiet once it is committed",
              "nothing was written to the decision ledger" not in ctx,
              ctx[:220] or "(silent)")
        check("and does not blame the junk file", "junk.log" not in ctx,
              ctx[:220])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_code_committed_without_a_record_still_warns():
    """The mirror: committing must not become a way to silence the gate."""
    print("\nCommitting code alone does not silence it")
    d = make_repo()
    try:
        (d / "README.md").write_text("# p\n", encoding="utf-8")
        commit_all(d, "initial")
        run_hook("session_start.py", {"cwd": str(d),
                                      "hook_event_name": "SessionStart"})
        (d / "feed.py").write_text("x = 1\n", encoding="utf-8")
        commit_all(d, "Change the loader, record nothing")
        (d / "feed.py").write_text("x = 2\n", encoding="utf-8")
        out, _e, _c = run_hook("stop_gate.py", {"cwd": str(d),
                                                "hook_event_name": "Stop"})
        check("warns about code changed with no record",
              "decision ledger" in context_of(out),
              context_of(out)[:200] or "(silent)")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_skill_frontmatter_is_valid_yaml():
    """Every SKILL.md frontmatter must survive a strict YAML parser.

    `wrap-session` shipped with an unquoted `: ` inside its `when_to_use`
    value -- "...is not a session ending: if it changes the plan...". A strict
    parser raises `mapping values are not allowed here` on that, which would
    drop the whole frontmatter and with it the trigger that makes the skill
    fire at all.

    It went out because the lenient parsers accepted it: `claude plugin
    validate --strict` passed, and a live session invoked the skill normally.
    The directory's own validator caught it. A plain-text check is used here
    rather than a YAML library, because this project ships no dependencies.
    """
    print("\nSkill frontmatter is strict-YAML safe")
    problems, checked = [], 0
    for p in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = p.read_text(encoding="utf-8")
        parts = text.split("---")
        if len(parts) < 3 or parts[0].strip():
            problems.append(f"{p.parent.name}: no leading frontmatter block")
            continue
        keys = set()
        for line in parts[1].strip().splitlines():
            if line.startswith((" ", "\t")) or ":" not in line:
                continue
            key, value = line.split(":", 1)
            keys.add(key.strip())
            v = value.strip()
            if v.startswith(('"', "'")):
                continue  # quoted: anything goes inside
            if ": " in v:
                problems.append(f"{p.parent.name}/{key.strip()}: unquoted ': ' "
                                "- a strict parser reads this as a nested mapping")
            if "#" in v:
                problems.append(f"{p.parent.name}/{key.strip()}: unquoted '#' "
                                "- a strict parser reads the rest as a comment")
        for required in ("name", "description", "when_to_use"):
            if required not in keys:
                problems.append(f"{p.parent.name}: missing '{required}'")
        checked += 1
    check(f"all {checked} skills parse safely", not problems,
          "; ".join(problems[:4]))

    # And prove the guard actually catches the shape that shipped.
    bad = 'when_to_use: a handover is not a session ending: if it changes the plan\n'
    line = bad.split(":", 1)
    caught = ": " in line[1].strip() and not line[1].strip().startswith('"')
    check("the guard catches the exact line that shipped", caught)


def test_single_file_decision_history_is_reported():
    """A project keeping all its decisions in one DECISIONS.md must be told
    what will happen to it.

    The role is detected but is not adoptable: records are one file each, and
    REJ-0003 rejected the single-file shape. The scanner used to detect it and
    then say nothing -- a real installation met a project whose entire
    decision history was an 800-line DECISIONS.md, and the review notes
    discussed changelog formatting while ignoring it entirely.

    Silence is the defect, exactly as ADR-0014 found for unprefixed record
    directories. The file would sit unreferenced while new records started at
    0001 beside it, which is the loss this tool exists to prevent.
    """
    print("\nSingle-file decision history is reported")
    d = make_repo(with_ledger=False)
    try:
        lines = ["# Decisions", ""]
        for i in range(1, 120):
            lines += [f"## 2026-03-{i % 28 + 1:02d} - Decision {i}", "Reasoning.", ""]
        (d / "DECISIONS.md").write_text("\n".join(lines), encoding="utf-8")
        (d / "CHANGELOG.md").write_text("# Changelog\n\n## 2026-01-01\n- start\n",
                                        encoding="utf-8")
        commit_all(d, "init")
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "scan_project.py"), "--propose", str(d)],
            capture_output=True, text=True, timeout=60)
        err, cfg = out.stderr, json.loads(out.stdout)

        check("the file is named in the review", "DECISIONS.md" in err, err[-300:])
        check("it says the file is not adopted", "Not adopted" in err, err[-300:])
        check("it cites the rejection that explains why", "REJ-0003" in err)
        check("it says where new records will go",
              "docs/project-memory/decisions" in err)
        # Deliberately changed in ADR-0039: the note no longer says "do not
        # migrate, just link". It routes to ledger-backfill, which reads the
        # document as a source. What must never change is that the original
        # file is not touched.
        check("it routes to the backfill skill", "ledger-backfill" in err, err[-300:])
        check("it names the reader script", "read_decisions_doc.py" in err)
        check("it promises the original is not modified",
              "never modified, moved or deleted" in err, err[-300:])
        check("it says to link it from the briefing", "briefing" in err)
        check("and decisions is NOT in the adopted list",
              "decisions" not in (cfg.get("adopted") or []),
              str(cfg.get("adopted")))
        check("the config still points decisions at our own directory",
              (cfg.get("paths") or {}).get("decisions")
              == "docs/project-memory/decisions",
              str((cfg.get("paths") or {}).get("decisions")))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_a_decisions_directory_is_still_adopted():
    """The mirror: a DIRECTORY of records is adoptable and must stay so.

    The fix above must not make the scanner refuse the adr-tools layout that
    ADR-0014 added support for.
    """
    print("\nA decisions directory is still adopted")
    d = make_repo(with_ledger=False)
    try:
        (d / "docs" / "adr").mkdir(parents=True)
        for i in (1, 2, 3):
            (d / "docs" / "adr" / f"000{i}-choice.md").write_text(
                f"# Choice {i}\n", encoding="utf-8")
        commit_all(d, "init")
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "scan_project.py"), "--propose", str(d)],
            capture_output=True, text=True, timeout=60)
        cfg = json.loads(out.stdout)
        check("the directory is adopted",
              "decisions" in (cfg.get("adopted") or []), str(cfg.get("adopted")))
        check("and the config points at theirs",
              (cfg.get("paths") or {}).get("decisions") == "docs/adr",
              str((cfg.get("paths") or {}).get("decisions")))
        check("no single-file warning fires for a directory",
              "holds decision history in ONE file" not in out.stderr)
    finally:
        shutil.rmtree(d, ignore_errors=True)


DECISION_DOC = """# Decisions

## Table of contents

Links to everything below.

## 2026-01-04 — Use Postgres, not SQLite

We need concurrent writers for the ingest workers. SQLite's single-writer
lock showed up as timeouts under four workers. Cost: an extra service.

## 2026-02-11 — Single-file decision log [superseded]

Keeping everything in this file. Superseded 2026-08-02: it grew past the
point where anyone reads it on a cold start.

## 2026-03-19 — Rejected: move ingest to Lambda

Cold starts pushed p99 past the 400 ms budget and the vendor SDK needs a
persistent connection pool.

## 2026-08-02 — Split decisions into one file each

Because the single file stopped being readable.

## Formatting conventions

Use ISO dates.
"""


def test_decisions_document_is_read_not_ignored():
    """A decisions document is better source material than git history.

    REJ-0006 refused to migrate documents, but it was written about a 369 KB
    changelog -- prose where the boundaries would have to be invented. In a
    decisions document the author drew the boundaries, wrote the dates, wrote
    the reasoning and marked what was superseded. Its own re-evaluation
    trigger allowed exactly this: explicitly invoked, one document, backed up,
    confirmed.
    """
    print("\nReading a decisions document")
    d = Path(tempfile.mkdtemp(prefix="ledger-doc-"))
    try:
        doc = d / "DECISIONS.md"
        doc.write_text(DECISION_DOC, encoding="utf-8")
        before = doc.read_bytes()

        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "read_decisions_doc.py"), str(doc)],
            capture_output=True, text=True, encoding="utf-8", timeout=30)
        check("exits 0", out.returncode == 0, out.stderr[-200:])
        data = json.loads(out.stdout)
        entries = data["entries"]
        titles = [e["title"] for e in entries]

        check("one candidate per decision heading", len(entries) == 4,
              f"{len(entries)}: {titles}")
        check("the table of contents is not a decision",
              not any("contents" in t.lower() for t in titles), str(titles))
        check("a trailing section heading is not a decision either",
              not any("conventions" in t.lower() for t in titles), str(titles))
        check("dates are lifted out of the headings",
              all(e["date"] for e in entries),
              str([(e["title"], e["date"]) for e in entries]))
        check("and removed from the titles",
              not any(t.startswith("2026-") for t in titles), str(titles))
        check("the rejection is classified as one",
              [e["kind"] for e in entries if "Lambda" in e["title"]] == ["rej"],
              str([(e["title"], e["kind"]) for e in entries]))
        check("the author's superseded mark is carried",
              [e["superseded"] for e in entries if "Single-file" in e["title"]]
              == [True], str([(e["title"], e["superseded"]) for e in entries]))
        check("the status mark is stripped from the title",
              not any("[" in t for t in titles), str(titles))
        check("the author's own prose is carried across verbatim",
              any("single-writer" in e["body"] for e in entries))

        check("THE ORIGINAL IS BYTE-IDENTICAL", doc.read_bytes() == before)

        s = subprocess.run(
            [sys.executable, str(SCRIPTS / "read_decisions_doc.py"), str(doc),
             "--summary"], capture_output=True, text=True, encoding="utf-8",
            timeout=30)
        check("the summary says nothing was written",
              "Nothing has been written" in s.stdout, s.stdout[:200])
        check("and explains the supersession upgrade",
              "superseded_by" in s.stdout)
        check("the original is still byte-identical after --summary",
              doc.read_bytes() == before)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_non_ascii_survives_the_scripts():
    """Printing used to re-encode to the console code page on Windows, so a
    commit or a heading containing an accent or an em dash reached the skill
    as replacement characters -- in the worklist used to quote an author's own
    words verbatim. The data was always read correctly; only the printing was
    lossy."""
    print("\nNon-ASCII survives to stdout")
    d = Path(tempfile.mkdtemp(prefix="ledger-utf8-"))
    try:
        doc = d / "DECISIONS.md"
        doc.write_text("# Decisions\n\n## 2026-04-02 — Café ingest, naïve parser\n\n"
                       "Chose the naïve parser — it is 3× faster.\n",
                       encoding="utf-8")
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "read_decisions_doc.py"), str(doc),
             "--summary"], capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30)
        for ch, label in (("Café", "an accented word"), ("naïve", "a diaeresis")):
            check(f"{label} survives in the summary", ch in out.stdout,
                  repr(out.stdout[:160]))
        check("no replacement characters in the summary",
              "�" not in out.stdout, repr(out.stdout[:160]))

        # The em dash after the date is consumed as a separator, correctly, so
        # look for one in the body instead -- which is the text that gets
        # quoted into a record.
        raw = subprocess.run(
            [sys.executable, str(SCRIPTS / "read_decisions_doc.py"), str(doc)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30)
        body = json.loads(raw.stdout)["entries"][0]["body"]
        check("an em dash survives in the body", "—" in body, repr(body[:120]))
        check("a multiplication sign survives too", "×" in body, repr(body[:120]))
        check("the date separator was stripped from the title, not mangled",
              json.loads(raw.stdout)["entries"][0]["title"]
              == "Café ingest, naïve parser",
              repr(json.loads(raw.stdout)["entries"][0]["title"]))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_version_check_reports_and_never_phones_home():
    """The upgrade check reads directories only. The plugin promises nothing
    leaves the machine, and a weekly version ping would make that conditional."""
    print("\nVersion check")
    sys.path.insert(0, str(SCRIPTS))
    import check_version

    src = (ROOT / "scripts" / "check_version.py").read_text(encoding="utf-8")
    for banned in ("urllib", "requests", "http.client", "socket", "curl"):
        check(f"makes no use of {banned}", banned not in src)

    check("reports this plugin's own version",
          check_version.installed_version(ROOT) == "0.1.1",
          str(check_version.installed_version(ROOT)))

    d = Path(tempfile.mkdtemp(prefix="ledger-ver-"))
    try:
        for v in ("0.1.0", "0.2.0", "0.10.0"):
            (d / v / ".claude-plugin").mkdir(parents=True)
            (d / v / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"name": "decision-ledger", "version": v}),
                encoding="utf-8")
        current, newer, cached = check_version.status(d / "0.1.0")
        check("sees a newer version beside it", newer == "0.10.0",
              f"current={current} newer={newer}")
        check("0.10.0 sorts above 0.2.0, not below",
              check_version.parse("0.10.0") > check_version.parse("0.2.0"))
        _c, newest_from_top, _x = check_version.status(d / "0.10.0")
        check("the newest version is told nothing is newer",
              newest_from_top is None, str(newest_from_top))
        check("a source checkout reports no cache layout",
              check_version.status(ROOT)[2] is False)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_activity_trail_never_records_a_path_outside_the_project():
    """An out-of-project edit used to be logged with its full absolute path.

    A real installation spotted its own edit to a file under `~/.ssh` being
    written out in full, into a file that lives in the project. The trail is
    gitignored so it never reaches a remote, but it still carried a home
    directory and a username into the repository folder, and an outside path
    does not help reconstruct work on THIS project, which is the trail's only
    job.
    """
    print("\nThe activity trail stays inside the project")
    d = make_repo()
    outside = Path(tempfile.mkdtemp(prefix="ledger-outside-"))
    try:
        (d / "inside.py").write_text("x\n", encoding="utf-8")
        secret = outside / "config"
        secret.write_text("Host example\n", encoding="utf-8")

        for target in (d / "inside.py", secret):
            run_hook("post_tool_use.py", {
                "cwd": str(d), "hook_event_name": "PostToolUse",
                "tool_name": "Edit", "tool_input": {"file_path": str(target)}})

        trail = next((d / "docs" / "project-memory" / "activity").glob("*.md"))
        body = trail.read_text(encoding="utf-8")

        check("the in-project edit is recorded by its relative path",
              "`inside.py`" in body, body)
        check("the outside edit is still recorded as having happened",
              "outside the project" in body, body)
        check("but its path is not written down",
              str(outside) not in body, body)
        check("and no drive letter or home directory leaks in",
              not re.search(r"[A-Za-z]:[\\/]", body)
              and "/home/" not in body and "/Users/" not in body, body)
    finally:
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(outside, ignore_errors=True)



def _session_start_in(d, env_extra=None):
    """SessionStart against a project, with no project override in the env."""
    e = dict(os.environ)
    e.pop("LEDGER_PROJECT_DIR", None)
    e.pop("LEDGER_STRICT", None)
    e.pop("CLAUDE_PLUGIN_DATA", None)
    if env_extra:
        e.update(env_extra)
    p = subprocess.run(
        [sys.executable, str(SCRIPTS / "session_start.py")],
        input=json.dumps({"cwd": str(d), "hook_event_name": "SessionStart",
                          "source": "startup"}),
        capture_output=True, text=True, env=e, timeout=30)
    j = as_json(p.stdout)
    hso = (j or {}).get("hookSpecificOutput", {})
    return hso.get("additionalContext", ""), hso.get("systemMessage", ""), p


def _enable_for_project(d):
    (d / ".claude").mkdir(exist_ok=True)
    (d / ".claude" / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"decision-ledger@sayan-skills": True}}),
        encoding="utf-8")


def test_a_project_that_has_not_opted_in_is_told_so():
    """The defect that made a correct install look like a broken one.

    Every hook used to return in silence when `docs/project-memory/` was
    absent, so `plugin list` said enabled, `plugin details` listed five
    hooks, the hooks fired, and nothing happened -- indistinguishable from a
    plugin that does not work. The user, in their own words: "Everyone will
    think it is working after installation, but effectively it needs another
    command to start."

    The gate still holds: nothing is written in a project that only has the
    plugin available account-wide. But it now says so.
    """
    print("\nNot opted in")
    d = make_repo(with_ledger=False)
    data = Path(tempfile.mkdtemp(prefix="ledger-pdata-"))
    try:
        ctx, msg, p = _session_start_in(d)
        check("the hook survives a project with no ledger", p.returncode == 0,
              p.stderr[-140:])
        check("it no longer stays silent", bool(ctx) and bool(msg), repr(ctx[:60]))
        check("the user is told the plugin is not active here",
              "not opted in" in msg or "not active" in msg, msg)
        check("the model is told to mention it and then carry on",
              "single line" in ctx and "carry on" in ctx, ctx[:200])
        check("it names the command that switches it on",
              "mkdir" in ctx and "docs/project-memory" in ctx, ctx[:200])
        check("and it still writes nothing",
              not (d / "docs").exists(), str(list(d.iterdir())))

        env = {"CLAUDE_PLUGIN_DATA": str(data)}
        first = _session_start_in(d, env)[1]
        second = _session_start_in(d, env)[1]
        check("it says it once per project, not once per session",
              bool(first) and not second, f"{first[:40]!r} then {second[:40]!r}")
        check("remembering it leaves nothing in the project",
              not any(x.name.startswith(".ledger") for x in d.iterdir()),
              str(list(d.iterdir())))
    finally:
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(data, ignore_errors=True)


def test_a_project_scope_enable_creates_the_ledger():
    """Installing into THIS project is the opt-in; asking twice buys nothing.

    A user who runs `--scope project` named the repository. Making them then
    create a directory to confirm what they just asked for is the step the
    install guide itself calls "the step people miss".
    """
    print("\nProject-scope enable opts the project in")
    d = make_repo(with_ledger=False)
    try:
        _enable_for_project(d)
        ctx, msg, p = _session_start_in(d)
        lm = d / "docs" / "project-memory"
        check("the ledger directories are created",
              (lm / "decisions").is_dir() and (lm / "rejections").is_dir()
              and (lm / "change-requests").is_dir(), str(lm))
        check("a placeholder briefing is created too, so git has something to see",
              (lm / "00-PROJECT-STATE.md").is_file())
        body = (lm / "00-PROJECT-STATE.md").read_text(encoding="utf-8")
        check("the placeholder says plainly that nobody has written it",
              "Nobody has written this yet" in body, body[:200])
        check("the user is told what was created", "created" in msg, msg)
        check("the model is told not to invent the project's state",
              "present it as fact" in ctx, ctx[-300:])

        ctx2, _msg2, _p2 = _session_start_in(d)
        check("the next session gets the real briefing instead",
              "Settled rejections" in ctx2, ctx2[:120])

        (lm / "00-PROJECT-STATE.md").write_text("# Mine\n", encoding="utf-8")
        _session_start_in(d)
        check("a briefing that exists is never overwritten",
              (lm / "00-PROJECT-STATE.md").read_text(encoding="utf-8") == "# Mine\n")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_a_project_with_its_own_notes_is_never_given_a_second_set():
    """The one thing auto-creation must not do.

    `docs/project-memory/` created beside a project's own `docs/adr/` is the
    duplication `ledger-adopt` exists to prevent, and REJ-0006 settled that
    existing documents are pointed at, not migrated. So the scope signal is
    not enough on its own: a project that already keeps notes gets named the
    adopt skill and nothing is written, even when it is the one that asked.
    """
    print("\nA project that already keeps notes")
    for note in ("CHANGELOG.md", "DECISIONS.md", "docs/STATUS.md"):
        d = make_repo(with_ledger=False)
        try:
            _enable_for_project(d)
            target = d / note
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# Notes\n\n- 2026-01-01 a thing\n", encoding="utf-8")
            ctx, msg, _p = _session_start_in(d)
            check(f"{note}: no parallel ledger is created",
                  not (d / "docs" / "project-memory").exists())
            check(f"{note}: ledger-adopt is named instead",
                  "ledger-adopt" in ctx and "ledger-adopt" in msg, msg)
            check(f"{note}: the file it found is quoted back",
                  Path(note).name in ctx, ctx[-200:])
        finally:
            shutil.rmtree(d, ignore_errors=True)


def test_the_scope_signal_reads_only_a_real_project_enable():
    """What may and may not stand in for "the user chose this project"."""
    print("\nThe project-scope signal")
    on = '{"enabledPlugins": {"decision-ledger@sayan-skills": true}}'
    other_market = '{"enabledPlugins": {"decision-ledger@other-market": true}}'
    off = '{"enabledPlugins": {"decision-ledger@sayan-skills": false}}'
    someone_else = '{"enabledPlugins": {"something-else@x": true}}'
    lookalike = '{"enabledPlugins": {"decision-ledger-extra@x": true}}'
    wrong_shape = '{"enabledPlugins": []}'
    cases = [
        (on, True, "a project enable"),
        (other_market, True, "the same plugin from another marketplace"),
        (off, False, "an explicit disable"),
        (someone_else, False, "somebody else's plugin"),
        (lookalike, False, "a plugin whose name merely starts the same"),
        (wrong_shape, False, "the wrong shape"),
        ("not json at all", False, "a file that is not JSON"),
        ("", False, "an empty file"),
    ]
    sys.path.insert(0, str(SCRIPTS))
    import _ledger as L
    for text, expected, name in cases:
        d = Path(tempfile.mkdtemp(prefix="ledger-scope-"))
        try:
            (d / ".claude").mkdir()
            (d / ".claude" / "settings.json").write_text(text, encoding="utf-8")
            got = L.project_scope_enabled(d)
            check(f"{name} -> {expected}", got is expected, f"got {got}")
        finally:
            shutil.rmtree(d, ignore_errors=True)
    d = Path(tempfile.mkdtemp(prefix="ledger-scope-"))
    try:
        check("no settings file at all -> False",
              L.project_scope_enabled(d) is False)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _own_ledger_fingerprint():
    """What this repository's own ledger state looks like, byte for byte.

    Deliberately not a hash of the whole tree: the suite is expected to leave
    the source alone, and what it has actually damaged in the past is the
    ledger -- the activity trail and the Stop gate's markers in `.git/`.
    """
    fp = {}
    activity = ROOT / "docs" / "project-memory" / "activity"
    if activity.is_dir():
        for f in sorted(activity.iterdir()):
            if f.is_file():
                fp[f"activity/{f.name}"] = f.stat().st_size
    gd = ROOT / ".git"
    if gd.is_dir():
        for f in sorted(gd.glob("ledger-*")):
            fp[f".git/{f.name}"] = f.read_bytes()
    return fp


def test_the_suite_leaves_this_repository_alone(before):
    """The tests must not write to the project they are testing.

    They had been. `test_hooks_survive_hostile_payloads` ran hooks with
    payloads carrying no `cwd`, so `project_dir()` fell back to the suite's
    own working directory -- this repository -- and the hooks did exactly what
    they are built to do: `pre_compact` appended four compaction checkpoints
    to the real activity trail on every run, and `session_start` overwrote
    `.git/ledger-baseline`, the Stop gate's record of what was already dirty
    when the session began (ADR-0033). A test run therefore changed what the
    Stop hook reported for the rest of a live session, and 270 of the 271
    lines in the trail turned out to be test output rather than compactions.

    Nothing failed, which is the point. Every hook was behaving correctly; it
    was aimed at the wrong project. No assertion in 317 checks looked at the
    one thing that would have shown it, so this looks at it: run the suite,
    then compare the ledger with what it was before.

    Takes the fingerprint from `main()` rather than recomputing a baseline,
    because by the time this runs the damage would already be done.
    """
    print("\nFootprint on this repository")
    after = _own_ledger_fingerprint()
    changed = sorted(set(before) ^ set(after)) + \
        sorted(k for k in set(before) & set(after) if before[k] != after[k])
    check("the suite wrote nothing into this project's own ledger",
          not changed, ", ".join(changed[:4]))


def main():
    print("decision-ledger hook tests")
    before = _own_ledger_fingerprint()
    for t in (test_session_start, test_briefing_without_constraints_file,
              test_silent_without_ledger, test_pre_compact,
              test_prompt_classifier, test_stop_gate,
              test_stop_gate_untracked_regression, test_orphan_detection,
              test_index_refuses_to_clobber, test_new_record_refuses_to_clobber,
              test_adopt_existing_project, test_newest_first_changelog_insertion,
              test_scanner_detects_real_shapes,
              test_crlf_changelog_keeps_its_line_endings,
              test_role_classification,
              test_refuses_to_rewrite_non_utf8_changelog,
              test_malformed_config_is_not_fatal,
              test_record_scaffolding,
              test_record_number_parsing,
              test_next_id_continues_adopted_numbering,
              test_scanner_adopts_unprefixed_adr_dir,
              test_scanner_ignores_its_own_directory,
              test_missing_briefing_warning,
              test_history_mining,
              test_scanner_flags_undocumented_history,
              test_fresh_project_is_not_told_to_backfill,
              test_worktree_is_recognised_as_git,
              test_stop_gate_dedup_works_in_a_worktree,
              test_miner_summary_survives_a_non_git_path,
              test_index_writes_to_the_configured_path,
              test_configured_paths_cannot_leave_the_project,
              test_config_of_the_wrong_shape_is_not_fatal,
              test_session_start_caps_what_it_injects,
              test_messages_name_the_projects_own_files,
              test_installed_project_is_not_told_to_backfill,
              test_history_with_no_recoverable_reasoning,
              test_index_escapes_a_pipe_in_a_title,
              test_record_reads_survive_a_bom,
              test_concurrent_records_get_distinct_ids,
              test_record_directory_that_is_a_file,
              test_failed_write_leaves_no_temp_file,
              test_hooks_survive_hostile_payloads,
              test_unborn_and_detached_head,
              test_activity_trail_does_not_silence_the_nag,
              test_recording_a_decision_still_silences_the_nag,
              test_no_unanchored_script_paths_in_instructions,
              test_project_flag_pins_the_project,
              test_session_start_hands_over_absolute_paths,
              test_stop_gate_ignores_what_was_already_dirty,
              test_stop_gate_without_a_baseline_reports_everything,
              test_a_committed_record_still_counts_as_recorded,
              test_code_committed_without_a_record_still_warns,
              test_skill_frontmatter_is_valid_yaml,
              test_single_file_decision_history_is_reported,
              test_a_decisions_directory_is_still_adopted,
              test_decisions_document_is_read_not_ignored,
              test_non_ascii_survives_the_scripts,
              test_version_check_reports_and_never_phones_home,
              test_activity_trail_never_records_a_path_outside_the_project,
              test_a_project_that_has_not_opted_in_is_told_so,
              test_a_project_scope_enable_creates_the_ledger,
              test_a_project_with_its_own_notes_is_never_given_a_second_set,
              test_the_scope_signal_reads_only_a_real_project_enable):
        try:
            t()
        except Exception as exc:  # a crashing test is a failing test
            FAILED.append(t.__name__)
            print(f"  [FAIL] {t.__name__} raised {exc!r}")

    try:  # last, and after every other test has had its chance to leak
        test_the_suite_leaves_this_repository_alone(before)
    except Exception as exc:
        FAILED.append("test_the_suite_leaves_this_repository_alone")
        print(f"  [FAIL] footprint check raised {exc!r}")

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        for name in FAILED:
            print(f"  failed: {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
