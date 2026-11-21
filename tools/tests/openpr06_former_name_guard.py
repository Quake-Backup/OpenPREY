#!/usr/bin/env python3
"""Keep the project's former name, openPREY, out of tracked files.

openPR06 was named openPREY until November 2026. The old name survives only
where this build still reads files written under it, in dated history, and in
the local checkout path some development notes record.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve().relative_to(ROOT).as_posix()

FORMER_NAME = re.compile(r"openPREY|OPENPREY|openprey")

# Dated records that describe the project under its old name.
HISTORY_FILES = {
    "docs/dev/prey-rebase/report-narrative.md",
    "docs/dev/releases/unreleased.md",
}

# Allowed anywhere: the local checkout path, and the save stamp of game
# libraries built without git history (changing it would reject their saves).
ALLOWED_EVERYWHERE = (
    re.compile(r"Repositories(?:\\\\|\\|/)openPREY"),
    re.compile(re.escape("standalone-openprey-game")),
)

# Allowed in engine sources: names the engine still reads or migrates from.
ALLOWED_IN_SOURCE = tuple(
    re.compile(re.escape(text))
    for text in (
        '"openPREY RDEMO"',
        "requiredopenPREYVersion",
        "openPREYConfig.cfg",
        '"/openprey"',
        '"/openprey-demo"',
        '"openPREY"',
        '"openPREY Demo"',
        "was named openPREY",
        "former openPREY name",
        "renamed from openPREY to openPR06",
        "before the openPREY casing",
        "The openPREY and",
    )
)


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"], check=True, capture_output=True
    ).stdout.decode("utf-8")
    return [name for name in out.split("\0") if name]


def main() -> int:
    failures: list[str] = []
    for name in tracked_files():
        if name == SELF or name in HISTORY_FILES:
            continue
        if FORMER_NAME.search(name):
            failures.append(f"{name}: path uses the former name")
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            continue
        text = data.decode("utf-8", errors="replace")
        if not FORMER_NAME.search(text):
            continue
        allowed = ALLOWED_EVERYWHERE
        if name.startswith("src/"):
            allowed = allowed + ALLOWED_IN_SOURCE
        for number, line in enumerate(text.splitlines(), 1):
            for pattern in allowed:
                line = pattern.sub("", line)
            if FORMER_NAME.search(line):
                failures.append(f"{name}:{number}: {line.strip()[:160]}")

    if failures:
        print("Former project name openPREY found; use openPR06:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("openPR06 former-name guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
