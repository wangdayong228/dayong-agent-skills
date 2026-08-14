#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterator, Literal, Sequence

try:
    import fcntl
except ImportError:  # Non-POSIX environments degrade at the CLI boundary.
    fcntl = None

TRACE_HEADER = ("| 决策主题 | 已确认决策 | 来源 | 确认日期 |\n" "| --- | --- | --- | --- |\n")
USER_SOURCE = "用户明确回答"
APPROVED_PREFIX = "已批准 spec："
Status = Literal["created", "unchanged", "replaced", "conflict"]


class TraceError(Exception):
    pass


@dataclass(frozen=True)
class Decision:
    topic: str
    decision: str
    source: str
    confirmed_on: date


def adjacent_trace_path(spec: Path) -> Path:
    return spec.with_name(f"{spec.stem}-decision-trace.md")


def _one_line(value: str, field: str) -> str:
    if not isinstance(value, str): raise TraceError(f"{field} must be text")
    value = re.sub(r"\r\n?|\n", " ", value).strip()
    if not value: raise TraceError(f"{field} must not be empty")
    return value


def _normalize(entry: Decision) -> Decision:
    if type(entry.confirmed_on) is not date: raise TraceError("confirmed_on must be a date")
    topic, decision, source = (_one_line(entry.topic, "topic"), _one_line(entry.decision, "decision"), _one_line(entry.source, "source"))
    if source != USER_SOURCE:
        if not source.startswith(APPROVED_PREFIX): raise TraceError("source must be a user answer or approved spec section")
        path, mark, section = source[len(APPROVED_PREFIX):].rpartition("#")
        if not mark or not path.strip() or not section.strip(): raise TraceError("approved spec source must be SPEC#SECTION")
    return Decision(topic, decision, source, entry.confirmed_on)


def _escape(value: str) -> str: return value.replace("\\", "\\\\").replace("|", "\\|")


def _split_row(line: str) -> list[str]:
    if not line.startswith("|") or not line.endswith("|"): raise TraceError("malformed decision row")
    fields, current, escaped = [], [], False
    for char in line[1:-1]:
        if escaped:
            if char not in ("\\", "|"): raise TraceError("invalid markdown escape")
            current.append(char); escaped = False
        elif char == "\\": escaped = True
        elif char == "|": fields.append("".join(current).strip()); current = []
        else: current.append(char)
    if escaped: raise TraceError("unfinished markdown escape")
    fields.append("".join(current).strip())
    if len(fields) != 4: raise TraceError("decision row must have four columns")
    return fields


def _render(entries: list[Decision]) -> str:
    return TRACE_HEADER + "".join("| " + " | ".join(_escape(v) for v in (e.topic, e.decision, e.source, e.confirmed_on.isoformat())) + " |\n" for e in entries)


def _require_spec(spec: Path) -> None:
    if not spec.is_file(): raise TraceError(f"spec does not exist: {spec}")


def load_decisions(spec: Path) -> list[Decision]:
    spec = Path(spec); _require_spec(spec); trace = adjacent_trace_path(spec)
    try: text = trace.read_text(encoding="utf-8")
    except FileNotFoundError: return []
    except (OSError, UnicodeError) as exc: raise TraceError(f"cannot read trace: {exc}") from exc
    if not text.startswith(TRACE_HEADER): raise TraceError("trace must start with the exact four-column header")
    payload = text[len(TRACE_HEADER):]
    if not payload: return []
    if not text.endswith("\n"): raise TraceError("trace must end with a newline")
    entries, topics = [], set()
    for line in payload.splitlines():
        if not line: raise TraceError("blank rows are not allowed")
        topic, decision, source, confirmed = _split_row(line)
        try: confirmed_on = date.fromisoformat(confirmed)
        except ValueError as exc: raise TraceError("confirmed date must be YYYY-MM-DD") from exc
        entry = _normalize(Decision(topic, decision, source, confirmed_on))
        if entry.topic in topics: raise TraceError(f"duplicate decision topic: {entry.topic}")
        topics.add(entry.topic); entries.append(entry)
    return entries


@contextmanager
def _directory_lock(parent: Path) -> Iterator[None]:
    if fcntl is None: raise TraceError("nonblocking file locking is unavailable")
    try: descriptor = os.open(parent, os.O_RDONLY)
    except OSError as exc: raise TraceError(f"cannot open trace directory: {exc}") from exc
    try:
        try: fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc: raise TraceError("trace directory is busy") from exc
        yield
    finally: os.close(descriptor)


def _atomic_write(path: Path, text: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try: os.unlink(temporary)
        except FileNotFoundError: pass


def record_decision(spec: Path, entry: Decision, *, replace_conflict: bool = False) -> Status:
    spec = Path(spec); entry = _normalize(entry); _require_spec(spec); trace = adjacent_trace_path(spec)
    with _directory_lock(spec.parent):
        entries = load_decisions(spec)
        for index, current in enumerate(entries):
            if current.topic != entry.topic: continue
            if current.decision == entry.decision: return "unchanged"
            if not replace_conflict: return "conflict"
            entries[index] = entry; _atomic_write(trace, _render(entries)); return "replaced"
        entries.append(entry); _atomic_write(trace, _render(entries)); return "created"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None: raise TraceError(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="decision_trace.py")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    read = commands.add_parser("read"); read.add_argument("spec", type=Path)
    record = commands.add_parser("record"); record.add_argument("spec", type=Path)
    record.add_argument("--topic", required=True); record.add_argument("--decision", required=True)
    record.add_argument("--source-kind", required=True, choices=("user", "approved-spec")); record.add_argument("--source-ref")
    record.add_argument("--confirmed-on"); record.add_argument("--replace-conflict", action="store_true")
    return parser


def _source(kind: str, reference: str | None) -> str:
    if kind == "user":
        if reference: raise TraceError("user source does not accept --source-ref")
        return USER_SOURCE
    if not reference: raise TraceError("approved-spec source requires --source-ref SPEC#SECTION")
    return APPROVED_PREFIX + reference


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
        if args.command == "read":
            trace = adjacent_trace_path(args.spec); sys.stdout.write(_render(load_decisions(args.spec)))
            if not trace.exists(): print(f"WARNING: decision-trace: trace does not exist: {trace}", file=sys.stderr)
            return 0
        try: confirmed_on = date.fromisoformat(args.confirmed_on) if args.confirmed_on else date.today()
        except ValueError as exc: raise TraceError("confirmed date must be YYYY-MM-DD") from exc
        print(record_decision(args.spec, Decision(args.topic, args.decision, _source(args.source_kind, args.source_ref), confirmed_on), replace_conflict=args.replace_conflict))
    except (TraceError, OSError, UnicodeError, ValueError, TypeError) as exc:
        reason = " ".join(str(exc).splitlines()) or type(exc).__name__
        print(f"WARNING: decision-trace: {reason}", file=sys.stderr)
    return 0


if __name__ == "__main__": raise SystemExit(main())
