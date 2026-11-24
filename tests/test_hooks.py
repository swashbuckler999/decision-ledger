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
    print("\nNo ledger in project -> every hook stays silent")
    d = make_repo(with_ledger=False)
    try:
        for script in ("session_start.py", "post_tool_use.py", "stop_gate.py",
                       "user_prompt_submit.py"):
            out, _, code = run_hook(script, {
                "cwd": str(d), "prompt": "lets go with Parquet",
                "tool_name": "Edit", "tool_input": {"file_path": str(d / "a.py")},
            })
            check(f"{script} silent", out == "" and code == 0, f"out={out[:60]!r}")
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
        check("every run succeeded", not failures,
              "; ".join(f.strip()[-120:] for f in failures[:2]))
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
    """Every hook, against every shape of wrong input a harness might send."""
    print("\nHostile hook payloads")
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
                               text=True, timeout=30)
            if p.returncode != 0 or "Traceback" in p.stderr:
                bad.append(f"{payload}(rc={p.returncode})")
        for raw in ("", "not json at all"):
            p = subprocess.run([sys.executable, str(SCRIPTS / script)], input=raw,
                               capture_output=True, text=True, timeout=30)
            if p.returncode != 0 or "Traceback" in p.stderr:
                bad.append(f"raw {raw!r}(rc={p.returncode})")
        check(f"{script} survives every bad payload", not bad, "; ".join(bad[:3]))


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


def main():
    print("decision-ledger hook tests")
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
              test_unborn_and_detached_head):
        try:
            t()
        except Exception as exc:  # a crashing test is a failing test
            FAILED.append(t.__name__)
            print(f"  [FAIL] {t.__name__} raised {exc!r}")

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        for name in FAILED:
            print(f"  failed: {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
