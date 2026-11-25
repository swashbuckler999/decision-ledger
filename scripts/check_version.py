"""Report the installed plugin version and whether a newer one is on disk.

    python <plugin>/scripts/check_version.py
    python <plugin>/scripts/check_version.py --quiet   # one line, or nothing

**This makes no network request.** The plugin's standing promise is that
nothing leaves the machine, and a weekly phone-home would break it for a
convenience. What it reads instead is Claude Code's own plugin cache, which
the user refreshes themselves with `claude plugin marketplace update`. So the
network call is theirs, deliberate, and visible -- ours is never made at all.

How "available" is known without asking anything: an installed plugin lives at
`<cache>/<marketplace>/<plugin>/<version>/`, so sibling directories of the
plugin root are the other versions already fetched. Reading that directory is
the whole mechanism.

A plugin loaded in place from a source checkout has no such layout, and the
script says so rather than guessing.
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ledger as L  # noqa: E402

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def parse(version):
    """A sortable tuple, or None when it is not a plain version string."""
    m = SEMVER.match(str(version).strip())
    return tuple(int(g) for g in m.groups()) if m else None


def installed_version(root=None):
    root = Path(root) if root else L.plugin_root()
    try:
        data = json.loads(
            (root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        return str(data.get("version") or "").strip() or None
    except Exception:
        return None


def available_versions(root=None):
    """Versions already fetched into the cache beside this one.

    Returns [] when the plugin is not laid out as <plugin>/<version>/, which is
    the case for a source checkout loaded in place.
    """
    root = Path(root) if root else L.plugin_root()
    if parse(root.name) is None:
        return []  # not a version directory: loaded from source, not the cache
    try:
        siblings = [p.name for p in root.parent.iterdir() if p.is_dir()]
    except OSError:
        return []
    return sorted((v for v in siblings if parse(v)), key=parse)


def status(root=None):
    """(installed, newest_available_or_None, in_cache_layout)."""
    root = Path(root) if root else L.plugin_root()
    current = installed_version(root)
    versions = available_versions(root)
    newer = None
    if current and parse(current):
        ahead = [v for v in versions if parse(v) > parse(current)]
        newer = max(ahead, key=parse) if ahead else None
    return current, newer, bool(versions)


UPDATE_HINT = (
    "  claude plugin marketplace update sayan-skills\n"
    "  claude plugin update decision-ledger@sayan-skills")


def main():
    L.use_utf8_stdout()
    quiet = "--quiet" in sys.argv
    root = L.plugin_root()
    current, newer, cached = status(root)

    if quiet:
        if newer:
            print(f"decision-ledger {current} installed; {newer} is available. "
                  "Run `claude plugin update decision-ledger@sayan-skills`.")
        return 0

    print(f"decision-ledger {current or '(version unknown)'}")
    print(f"  plugin root : {root}")
    if newer:
        print(f"  available   : {newer}  <-- newer than the one in use")
        print("\nTo upgrade:")
        print(UPDATE_HINT)
    elif cached:
        print("  available   : nothing newer has been fetched")
        print("\nTo look for a newer release, refresh the marketplace first:")
        print(UPDATE_HINT)
    else:
        print("  available   : unknown -- this plugin is loaded from a source")
        print("                checkout, not from the plugin cache, so there")
        print("                are no other versions on disk to compare with.")
        print("\nIf you installed it from the marketplace, upgrade with:")
        print(UPDATE_HINT)
    print(f"\nWhat changed in each release: {RELEASES_URL}")
    return 0


RELEASES_URL = "https://github.com/swashbuckler999/decision-ledger/blob/main/docs/RELEASES.md"


if __name__ == "__main__":
    sys.exit(main())
