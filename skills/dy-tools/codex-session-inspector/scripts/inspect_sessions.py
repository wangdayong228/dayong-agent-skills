#!/usr/bin/env python3
"""Read-only inspector for local Codex session JSONL files."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


MODEL_LIMIT = 50
SESSION_LIMIT = 20


@dataclass
class SessionData:
    path: Path
    mtime: float
    meta: dict[str, Any] = field(default_factory=dict)
    turns: list[dict[str, str]] = field(default_factory=list)
    token_event: dict[str, Any] | None = None


def positive_int(value: str) -> int:
    try:
        limit = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("--limit must be a positive integer") from error
    if limit <= 0:
        raise argparse.ArgumentTypeError("--limit must be a positive integer")
    return limit


def nested(mapping: dict[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def text(value: Any) -> str:
    return "" if value is None else str(value)


def shorten(value: Any, width: int) -> str:
    value = text(value)
    return value if len(value) <= width else f"{value[: width - 1]}…"


def compact_path(value: Any, width: int) -> str:
    path = text(value)
    if len(path) <= width:
        return path
    parts = Path(path).parts
    compact = "/".join(parts[-2:]) if len(parts) > 1 else path
    return shorten(f"…/{compact}", width)


def format_number(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:,}"
    return text(value)


def format_percent(numerator: Any, denominator: Any) -> str:
    if not isinstance(numerator, (int, float)) or not isinstance(denominator, (int, float)):
        return ""
    if denominator == 0:
        return ""
    return f"{numerator / denominator * 100:.1f}%"


def format_rate(value: Any) -> str:
    return f"{value:.1f}%" if isinstance(value, (int, float)) else ""


def session_files(sessions_dir: Path) -> list[Path]:
    return sorted((path for path in sessions_dir.rglob("*.jsonl") if path.is_file()), key=lambda path: path.stat().st_mtime)


def iter_events(path: Path) -> Iterator[dict[str, Any]]:
    try:
        with path.open(encoding="utf-8") as source:
            for line in source:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    yield event
    except OSError:
        return


def read_session(path: Path) -> SessionData:
    session = SessionData(path=path, mtime=path.stat().st_mtime)
    for event in iter_events(path):
        event_type = event.get("type")
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        if event_type == "session_meta":
            session.meta = payload
        elif event_type == "turn_context":
            session.turns.append(
                {
                    "time": text(event.get("timestamp")),
                    "model": text(payload.get("model")),
                    "effort": text(payload.get("effort") or payload.get("reasoning_effort")),
                }
            )
        elif event_type == "event_msg" and payload.get("type") == "token_count":
            session.token_event = {"time": text(event.get("timestamp")), "payload": payload}
    return session


def source_for(session: SessionData) -> str:
    return text(session.meta.get("thread_source") or "main")


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    def render(row: list[str]) -> str:
        return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row)).rstrip()

    print(render(headers))
    for row in rows:
        print(render(row))


def command_model(sessions: list[SessionData], limit: int) -> None:
    rows = [
        (turn["time"], [turn["time"], shorten(source_for(session), 12), shorten(turn["model"], 28), shorten(turn["effort"], 12)])
        for session in sessions
        for turn in session.turns
    ]
    rows.sort(key=lambda row: row[0], reverse=True)
    output = [row for _, row in rows[:limit]]
    if not output:
        print("no data")
        return
    print_table(["TIME", "SOURCE", "MODEL", "EFFORT"], output)


def command_latest(sessions: list[SessionData]) -> None:
    if not sessions:
        print("no data")
        return
    session = sessions[-1]
    latest_turn = session.turns[-1] if session.turns else {}
    print(f"file: {session.path}")
    print(f"session_id: {text(session.meta.get('session_id'))}")
    print(f"thread_source: {source_for(session)}")
    print(f"cwd: {text(session.meta.get('cwd'))}")
    print(f"model: {text(latest_turn.get('model'))}")
    print(f"effort: {text(latest_turn.get('effort'))}")
    print(f"originator: {text(session.meta.get('originator'))}")
    print(f"git.branch: {text(nested(session.meta, 'git', 'branch'))}")
    print(f"cli_version: {text(session.meta.get('cli_version'))}")


def command_stats(sessions: list[SessionData]) -> None:
    models = Counter(turn["model"] for session in sessions for turn in session.turns if turn["model"])
    if not models:
        print("no data")
        return
    for model, count in models.most_common():
        print(f"{count} {model}")


def command_tokens(sessions: list[SessionData], limit: int) -> None:
    rows: list[tuple[str, list[str]]] = []
    for session in sessions:
        if not session.token_event:
            continue
        payload = session.token_event["payload"]
        info = nested(payload, "info", "total_token_usage")
        if not isinstance(info, dict):
            continue
        total = info.get("total_tokens")
        # Context fill uses last turn usage; cumulative total_tokens can exceed the window.
        last_total = nested(payload, "info", "last_token_usage", "total_tokens")
        rows.append(
            (
                session.token_event["time"],
                [
                    session.token_event["time"],
                    format_number(total),
                    format_number(info.get("input_tokens")),
                    format_number(info.get("cached_input_tokens")),
                    format_number(info.get("output_tokens")),
                    format_number(info.get("reasoning_output_tokens")),
                    format_percent(last_total, nested(payload, "info", "model_context_window")),
                    format_rate(nested(payload, "rate_limits", "primary", "used_percent")),
                    shorten(session.path.name, 36),
                ],
            )
        )
    rows.sort(key=lambda row: row[0], reverse=True)
    output = [row for _, row in rows[:limit]]
    if not output:
        print("no data")
        return
    print_table(["TIME", "TOTAL", "IN", "CACHED", "OUT", "REASON", "CTX%", "RATE%", "FILE"], output)


def read_index(index_path: Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    if not index_path.is_file():
        return titles
    for entry in iter_events(index_path):
        session_id = entry.get("id")
        title = entry.get("thread_name")
        if session_id and title:
            titles[text(session_id)] = text(title)
    return titles


def command_list(sessions: list[SessionData], titles: dict[str, str], limit: int) -> None:
    selected = list(reversed(sessions[-limit:]))
    if not selected:
        print("no data")
        return
    rows: list[list[str]] = []
    for session in selected:
        latest_turn = session.turns[-1] if session.turns else {}
        own_id = text(session.meta.get("id") or session.meta.get("session_id"))
        parent_or_session = text(session.meta.get("session_id") or session.meta.get("id"))
        title = titles.get(own_id) or titles.get(parent_or_session) or ""
        rows.append(
            [
                text(session.meta.get("timestamp")),
                shorten(source_for(session), 12),
                shorten(latest_turn.get("model"), 28),
                shorten(latest_turn.get("effort"), 12),
                compact_path(session.meta.get("cwd"), 34),
                shorten(title, 40),
                shorten(own_id, 12),
            ]
        )
    print_table(["TIME", "SOURCE", "MODEL", "EFFORT", "CWD", "TITLE", "ID"], rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect local Codex session history.",
        usage="%(prog)s {model|latest|stats|tokens|list} [--limit N]",
    )
    parser.add_argument("command", choices=["model", "latest", "stats", "tokens", "list"], nargs="?", default="model")
    parser.add_argument("--limit", type=positive_int, metavar="N")
    args = parser.parse_args()
    if args.limit is not None and args.command not in {"model", "tokens", "list"}:
        parser.error("--limit is only valid with model, tokens, or list")
    return args


def main() -> int:
    args = parse_args()
    codex_home = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
    sessions_dir = codex_home / "sessions"
    if not sessions_dir.is_dir():
        print(f"Codex session directory not found: {sessions_dir}", file=sys.stderr)
        return 1

    sessions = [read_session(path) for path in session_files(sessions_dir)]
    if args.command == "model":
        command_model(sessions, args.limit or MODEL_LIMIT)
    elif args.command == "latest":
        command_latest(sessions)
    elif args.command == "stats":
        command_stats(sessions)
    elif args.command == "tokens":
        command_tokens(sessions, args.limit or SESSION_LIMIT)
    else:
        command_list(sessions, read_index(codex_home / "session_index.jsonl"), args.limit or SESSION_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
