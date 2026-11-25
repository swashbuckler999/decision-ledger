"""Read a decisions document into candidate records. Read-only.

    python <plugin>/scripts/read_decisions_doc.py DECISIONS.md
    python <plugin>/scripts/read_decisions_doc.py DECISIONS.md --summary

A project that keeps every decision in one file -- `DECISIONS.md`,
`ARCHITECTURE.md`, a `## Decisions` section -- has exactly the material this
ledger is for, already written by the person who made the calls. Ignoring it
and starting at 0001 beside it is the loss the ledger exists to prevent.

**Why this is allowed when REJ-0006 refused to migrate documents.** That
rejection was written about a 369 KB *changelog*: undifferentiated prose where
"deciding what counts as a decision, where each one begins and ends" would
have to be invented. A decisions document is not that. The author already drew
the boundaries -- the headings ARE the decisions -- already wrote the dates,
already wrote the reasoning, and already marked what was superseded. Every
judgement that rejection feared inventing has been made by the author.

REJ-0006's own re-evaluation trigger set the terms: "an explicitly invoked,
one-document-at-a-time operation that backs up the original outside the
repository first, shows a diff, and requires confirmation". This script is the
read half of that. It writes nothing, ever.

The other half of the argument is consistency: `mine_history.py` already
reconstructs records from commit messages, a thinner and more incidental
source, and handles not having witnessed them with provenance and confidence
markers. Refusing to read a file called DECISIONS.md while mining one-line
commits was an oversight, not a principle.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ledger as L  # noqa: E402

# A heading that starts a decision. Level 2 and 3 only: level 1 is the
# document title, level 4+ is structure inside an entry.
HEADING_RE = re.compile(r"^(#{2,3})\s+(.*\S)\s*$")
DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

# Marks an author puts beside a heading when a decision stops applying. These
# are the single most valuable thing in the file: a flat document cannot
# express supersession as a link, which is exactly what the ledger adds.
SUPERSEDED_RE = re.compile(
    r"\b(superseded|superceded|obsolete|replaced|revoked|reversed|withdrawn|"
    r"no longer applies|overturned)\b", re.I)
REJECTED_RE = re.compile(
    r"\b(rejected|declined|turned down|not doing|won'?t do|wontfix|abandoned)\b",
    re.I)
# A heading that is a section of the document rather than a decision.
SECTION_WORDS = ("contents", "table of contents", "index", "introduction",
                 "overview", "about", "how to", "template", "format",
                 "conventions", "legend", "glossary", "references", "notes")


LEADING_DATE_RE = re.compile(r"^\s*\d{4}-\d{2}-\d{2}\s*[-–—:.,]?\s*")


def clean_title(title):
    """The heading without its date prefix or its trailing [status] mark.

    Both are carried in their own fields, so leaving them in the title would
    duplicate them into every record's heading."""
    t = re.sub(r"\s*\[[^\]]*\]\s*$", "", title).strip()
    t = LEADING_DATE_RE.sub("", t).strip()
    return t or title.strip()


def classify(title, body):
    """rej / adr, plus whether the author marked it superseded."""
    head = title.lower()
    superseded = bool(SUPERSEDED_RE.search(title) or
                      SUPERSEDED_RE.search(body[:400]))
    kind = "rej" if REJECTED_RE.search(head) else "adr"
    return kind, superseded


def looks_like_a_section(title):
    t = title.lower().strip("# ").strip().rstrip(":")
    return any(t == w or t.startswith(w + " ") or t.endswith(" " + w)
               for w in SECTION_WORDS)


def parse(path):
    """Split the document on its own headings. One entry per heading."""
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()

    marks = []
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            marks.append((i, len(m.group(1)), m.group(2)))
    if not marks:
        return []

    # Use the shallowest heading level present as the entry level, so a file
    # using ### throughout is read the same as one using ##.
    level = min(depth for _i, depth, _t in marks)
    starts = [(i, t) for i, depth, t in marks if depth == level]

    entries = []
    for n, (start, title) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        body = "\n".join(lines[start + 1:end]).strip()
        if looks_like_a_section(title) and not DATE_RE.search(title):
            continue
        d = DATE_RE.search(title) or DATE_RE.search(body[:200])
        kind, superseded = classify(title, body)
        entries.append({
            "title": clean_title(title),
            "raw_heading": title,
            "date": "-".join(d.groups()) if d else None,
            "kind": kind,
            "superseded": superseded,
            "line": start + 1,
            "words": len(body.split()),
            "body": body,
        })
    return entries


def report(path, entries):
    rel = Path(path).name
    dated = sum(1 for e in entries if e["date"])
    sup = sum(1 for e in entries if e["superseded"])
    rej = sum(1 for e in entries if e["kind"] == "rej")
    thin = [e for e in entries if e["words"] < 15]

    out = [
        f"{rel}: {len(entries)} candidate record(s) from the document's own "
        "headings.",
        f"  {dated} carry a date, {len(entries) - dated} do not.",
        f"  {rej} read as rejections, {len(entries) - rej} as decisions.",
        f"  {sup} are marked superseded by the author.",
        "",
        "Nothing has been written. The original file is not modified by this "
        "script, now or later.",
        "",
    ]
    if thin:
        out += [f"  {len(thin)} entr(ies) have under 15 words of body. Those "
                "are headings without reasoning: carry them across as titles "
                "and ask, rather than inventing a rationale.", ""]
    for e in entries:
        flag = " [superseded]" if e["superseded"] else ""
        out.append(f"  [{e['kind'].upper()} {e['date'] or 'no date'}] "
                   f"line {e['line']}: {e['title']}{flag}  ({e['words']} words)")
    out += [
        "",
        "Each becomes one record with:",
        "  provenance: from-document",
        f"  sources: [{rel}#<heading>]",
        "  confidence: stated   (the reasoning is the author's own words)",
        "",
        "Entries the author marked superseded become real supersedes /",
        "superseded_by links, which the flat file could not express. That is",
        "the upgrade; the prose itself is carried across, not rewritten.",
    ]
    return "\n".join(out)


def main():
    L.use_utf8_stdout()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        print("usage: read_decisions_doc.py <file.md> [--summary]",
              file=sys.stderr)
        return 1
    path = Path(args[0])
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 1
    entries = parse(path)
    if "--summary" in sys.argv:
        print(report(path, entries))
    else:
        print(json.dumps({"source": path.name, "count": len(entries),
                          "entries": entries}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
