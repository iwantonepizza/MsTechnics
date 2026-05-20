#!/usr/bin/env python3
"""Detect BOM, invalid UTF-8, and common mojibake markers in text files."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

UTF8_BOM = b"\xef\xbb\xbf"
TEXT_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
MOJIBAKE_MARKERS = (
    "\u0420\u045f\u0420",
    "\u0420\u040e\u0420",
    "\u0420\u045c\u0420",
    "\u0421\u201a\u0420",
    "\u0421\u0403\u0421",
    "\u0421\u201a\u0421",
    "\u0420\xb0\u0420",
    "\u0420\u0451\u0420",
    "\u0420\xb5\u0420",
    "\u0420\u0455\u0420",
    "\u0432\u0402\u201d",
    "\u0432\u0402\u2122",
    "\u0432\u0402\u045a",
    "\u0432\u0402\u045c",
    "\u0432\u0402\xa6",
    "\u0432\u2020\u2019",
)
STRONG_MOJIBAKE_MARKERS = (
    "\u0432\u0402",
    "\u0432\u2020",
    "\u0420\u045f\u0420",
    "\u0420\u040e\u0420",
)
MIN_MOJIBAKE_HITS = 3


def is_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def has_mojibake(text: str) -> str | None:
    strong_hit = next((marker for marker in STRONG_MOJIBAKE_MARKERS if marker in text), None)
    if strong_hit is not None:
        return strong_hit

    hits = [marker for marker in MOJIBAKE_MARKERS if marker in text]
    if len(hits) >= MIN_MOJIBAKE_HITS:
        return hits[0]
    return None


def check_file(path: Path) -> list[str]:
    problems: list[str] = []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return [f"unreadable: {exc}"]

    if raw.startswith(UTF8_BOM):
        problems.append("starts with UTF-8 BOM")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        problems.append(f"not valid UTF-8: {exc}")
        return problems

    mojibake_marker = has_mojibake(text)
    if mojibake_marker is not None:
        problems.append(f"mojibake marker found: {mojibake_marker!r}")

    return problems


def collect_paths(args: list[str]) -> list[Path]:
    if args:
        return [Path(arg) for arg in args]

    output = subprocess.check_output(["git", "ls-files"], text=True)
    return [Path(path) for path in output.splitlines()]


def main() -> int:
    paths = [path for path in collect_paths(sys.argv[1:]) if is_text(path)]
    failed = 0

    for path in paths:
        if not path.exists():
            continue

        problems = check_file(path)
        if not problems:
            continue

        print(f"FAIL {path}")
        for problem in problems:
            print(f"  - {problem}")
        failed += 1

    if failed:
        print(f"\n{failed} file(s) with encoding issues.")
        return 1

    print(f"OK {len(paths)} text files checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
