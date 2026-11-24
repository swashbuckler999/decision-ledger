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


def main():
    print("decision-ledger hook tests")
    for t in (test_session_start, test_briefing_without_constraints_file,
              test_silent_without_ledger, test_pre_compact,
              test_prompt_classifier, test_stop_gate,
              test_stop_gate_untracked_regression, test_orphan_detection,
              test_index_refuses_to_clobber, test_new_record_refuses_to_clobber,
              test_adopt_existing_project, test_newest_first_changelog_insertion,
              test_scanner_detects_real_shapes,
              test_refuses_to_rewrite_non_utf8_changelog,
              test_malformed_config_is_not_fatal,
              test_record_scaffolding):
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
