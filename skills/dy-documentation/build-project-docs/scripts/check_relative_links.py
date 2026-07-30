#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from pathlib import Path


INLINE_LINK_START = re.compile(r"!?\[[^\]]*\]\(\s*")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))", re.MULTILINE)
HTML_LINK = re.compile(r"\b(?:href|src)\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
TITLE_SUFFIX = re.compile(r"""\s+["'][^"']*["']\s*$""")
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel", "data", "javascript"}


def strip_fenced_code(text: str) -> str:
    lines: list[str] = []
    fence: str | None = None
    for raw in text.splitlines(keepends=True):
        marker = raw.lstrip()
        if fence is None and (marker.startswith("```") or marker.startswith("~~~")):
            fence = marker[:3]
            lines.append("\n")
            continue
        if fence is not None:
            if marker.startswith(fence):
                fence = None
            lines.append("\n")
            continue
        lines.append(raw)
    return "".join(lines)


def slug_base(heading: str) -> str:
    heading = re.sub(r"<[^>]+>", "", heading).strip().lower()
    heading = re.sub(r"[^\w\- ]", "", heading, flags=re.UNICODE)
    return re.sub(r"[\s\-]+", "-", heading).strip("-")


def anchors(path: Path) -> set[str]:
    counts: dict[str, int] = {}
    result: set[str] = set()
    text = strip_fenced_code(path.read_text(encoding="utf-8"))
    for line in text.splitlines():
        match = HEADING.match(line)
        if not match:
            continue
        base = slug_base(match.group(2))
        index = counts.get(base, 0)
        counts[base] = index + 1
        result.add(base if index == 0 else f"{base}-{index}")
    return result


def inline_destinations(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for match in INLINE_LINK_START.finditer(text):
        cursor = match.end()
        if cursor < len(text) and text[cursor] == "<":
            end = text.find(">", cursor + 1)
            if end == -1:
                continue
            target = text[cursor + 1 : end]
        else:
            start = cursor
            depth = 0
            escaped = False
            while cursor < len(text):
                character = text[cursor]
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == "(":
                    depth += 1
                elif character == ")":
                    if depth == 0:
                        break
                    depth -= 1
                cursor += 1
            if cursor == len(text):
                continue
            target = text[start:cursor]
        line = text.count("\n", 0, match.start()) + 1
        found.append((line, TITLE_SUFFIX.sub("", target.strip())))
    return found


def destinations(text: str) -> list[tuple[int, str]]:
    clean = strip_fenced_code(text)
    found = inline_destinations(clean)
    for pattern in (REFERENCE_LINK, HTML_LINK):
        for match in pattern.finditer(clean):
            groups = [group for group in match.groups() if group is not None]
            target = TITLE_SUFFIX.sub("", groups[-1].strip())
            line = clean.count("\n", 0, match.start()) + 1
            found.append((line, target))
    return found


def markdown_files(root: Path, selected: list[str]) -> list[Path]:
    if not selected:
        return sorted(
            {
                path
                for suffix in ("*.md", "*.markdown")
                for path in root.rglob(suffix)
                if ".git" not in path.relative_to(root).parts
            }
        )
    files: list[Path] = []
    for raw in selected:
        path = (root / raw).resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"selected path escapes repository root: {raw}") from error
        if path.is_file() and path.suffix.lower() in {".md", ".markdown"}:
            files.append(path)
        elif path.is_dir():
            for suffix in ("*.md", "*.markdown"):
                files.extend(sorted(path.rglob(suffix)))
        else:
            raise ValueError(f"selected path does not exist: {raw}")
    return sorted(set(files))


def check_file(root: Path, source: Path) -> list[str]:
    errors: list[str] = []
    text = source.read_text(encoding="utf-8")
    for line, raw_target in destinations(text):
        target = raw_target.strip()
        parsed = urllib.parse.urlsplit(target)
        if (
            parsed.scheme.lower() in EXTERNAL_SCHEMES
            or parsed.netloc
            or target.startswith("/")
        ):
            continue
        relative = urllib.parse.unquote(parsed.path)
        resolved = source if not relative else (source.parent / relative).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            errors.append(
                f"{source.relative_to(root)}:{line}: {target}: escapes repository root"
            )
            continue
        if not resolved.exists():
            errors.append(
                f"{source.relative_to(root)}:{line}: {target}: target does not exist"
            )
            continue
        if parsed.fragment:
            if resolved.suffix.lower() not in {".md", ".markdown"}:
                errors.append(
                    f"{source.relative_to(root)}:{line}: {target}: "
                    "anchor target is not Markdown"
                )
                continue
            wanted = urllib.parse.unquote(parsed.fragment).lower()
            if wanted not in anchors(resolved):
                errors.append(
                    f"{source.relative_to(root)}:{line}: {target}: "
                    "anchor does not exist"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check repository-local Markdown links."
    )
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("paths", nargs="*", help="Markdown files or directories")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"invalid repository root: {root}", file=sys.stderr)
        return 2
    try:
        files = markdown_files(root, args.paths)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    errors = [error for path in files for error in check_file(root, path)]
    for error in errors:
        print(error)
    if errors:
        print(f"{len(errors)} broken repository-local link(s)")
        return 1
    print(f"checked {len(files)} Markdown file(s): no broken repository-local links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
