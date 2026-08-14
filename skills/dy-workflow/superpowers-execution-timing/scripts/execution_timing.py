#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator, Literal, Sequence

try:
    import fcntl
except ImportError:  # Non-POSIX environments degrade at the CLI boundary.
    fcntl = None

Clock = Callable[[], datetime]
TIMING_HEADER = (
    "| Task | Round | Step | Start | End | Duration |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
)
_STATE_KEYS = {"timing", "task", "round", "step", "start"}


class TimingError(Exception):
    pass


def system_now() -> datetime:
    return datetime.now().astimezone()


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise TimingError("clock returned a timezone-naive datetime")
    return value


def _timestamp(value: datetime) -> str:
    return _aware(value).isoformat(timespec="microseconds")


def _duration(start: datetime, end: datetime) -> str:
    delta = end - start
    micros = ((delta.days * 86400) + delta.seconds) * 1_000_000 + delta.microseconds
    if micros < 0:
        raise TimingError("step end precedes step start")
    return f"{micros // 1_000_000}.{micros % 1_000_000:06d}s"


def _identifier(value: str) -> str:
    if not isinstance(value, str):
        raise TimingError("Task, Round, and Step must be text")
    if not value.strip():
        raise TimingError("Task, Round, and Step must be non-empty")
    if value != value.strip() or "\r" in value or "\n" in value:
        raise TimingError(
            "Task, Round, and Step must be one line without surrounding whitespace"
        )
    return value


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|")


def _split_row(line: str) -> list[str]:
    if not line.startswith("|") or not line.endswith("|"):
        raise TimingError("malformed timing row")
    fields: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line[1:-1]:
        if escaped:
            if char not in ("\\", "|"):
                raise TimingError("invalid markdown escape")
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            fields.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if escaped:
        raise TimingError("unfinished markdown escape")
    fields.append("".join(current).strip())
    if len(fields) != 6:
        raise TimingError("timing row must have six columns")
    return fields


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise TimingError(f"{label} does not exist: {path}")


def _read_timing(path: Path) -> tuple[str, list[list[str]]]:
    _require_file(path, "timing file")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise TimingError(f"timing file is not valid UTF-8: {path}") from exc
    if not text.startswith(TIMING_HEADER):
        raise TimingError(f"timing file has an invalid six-column header: {path}")
    payload = text[len(TIMING_HEADER) :]
    if payload and not text.endswith("\n"):
        raise TimingError("timing file must end with a newline")
    rows: list[list[str]] = []
    for line in payload.splitlines():
        if not line:
            raise TimingError("blank timing rows are not allowed")
        fields = _split_row(line)
        for value in fields[:3]:
            _identifier(value)
        try:
            start = _aware(datetime.fromisoformat(fields[3]))
            end = _aware(datetime.fromisoformat(fields[4]))
        except ValueError as exc:
            raise TimingError("timing row has an invalid timestamp") from exc
        if fields[3] != _timestamp(start) or fields[4] != _timestamp(end):
            raise TimingError("timing timestamps must use canonical ISO 8601")
        if fields[5] != _duration(start, end):
            raise TimingError("timing duration does not match Start and End")
        rows.append(fields)
    return text, rows


def create_timing(plan: Path, *, clock: Clock = system_now) -> Path:
    plan = Path(plan)
    _require_file(plan, "Plan")
    now = _aware(clock())
    name = f"{plan.stem}-timing-{now.strftime('%Y%m%dT%H%M%S.%f%z')}.md"
    timing = plan.with_name(name)
    with timing.open("x", encoding="utf-8", newline="") as handle:
        handle.write(TIMING_HEADER)
        handle.flush()
        os.fsync(handle.fileno())
    return timing


def start_step(
    timing: Path,
    *,
    task: str,
    round: str = "1",
    step: str,
    clock: Clock = system_now,
) -> Path:
    timing = Path(timing)
    _read_timing(timing)
    state_data = {
        "timing": timing.name,
        "task": _identifier(task),
        "round": _identifier(round),
        "step": _identifier(step),
        "start": _timestamp(clock()),
    }
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{timing.name}.step-", suffix=".json", dir=timing.parent
    )
    state = Path(raw_path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(state_data, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        state.unlink(missing_ok=True)
        raise
    return state


def _load_state(state: Path) -> dict[str, str]:
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TimingError(f"invalid timing state: {state}") from exc
    if not isinstance(data, dict) or set(data) != _STATE_KEYS:
        raise TimingError(f"invalid timing state fields: {state}")
    if not all(isinstance(data[key], str) for key in _STATE_KEYS):
        raise TimingError(f"invalid timing state values: {state}")
    if Path(data["timing"]).name != data["timing"]:
        raise TimingError(f"invalid timing basename in state: {state}")
    for key in ("task", "round", "step"):
        _identifier(data[key])
    return data


@contextmanager
def _parent_lock(parent: Path) -> Iterator[None]:
    if fcntl is None:
        raise TimingError("nonblocking file locking is unavailable")
    descriptor = os.open(parent, os.O_RDONLY)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise TimingError(f"timing directory is busy: {parent}") from exc
        yield
    finally:
        os.close(descriptor)


def _atomic_replace(path: Path, text: str) -> None:
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{path.name}.write-", dir=path.parent
    )
    temporary = Path(raw_path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def finish_step(
    state: Path, *, clock: Clock = system_now
) -> Literal["recorded"]:
    state = Path(state)
    consume_attempted = False
    try:
        end = _aware(clock())
        data = _load_state(state)
        try:
            start = _aware(datetime.fromisoformat(data["start"]))
        except ValueError as exc:
            raise TimingError(f"invalid start timestamp in state: {state}") from exc
        start_text = _timestamp(start)
        if start_text != data["start"]:
            raise TimingError(f"noncanonical start timestamp in state: {state}")
        end_text = _timestamp(end)
        duration = _duration(start, end)
        timing = state.parent / data["timing"]
        row = (
            "| "
            + " | ".join(
                _escape(data[key]) for key in ("task", "round", "step")
            )
            + f" | {start_text} | {end_text} | {duration} |\n"
        )
        consume_attempted = True
        try:
            state.unlink()
        except OSError as exc:
            raise TimingError(f"cannot consume timing state: {state}") from exc
        with _parent_lock(timing.parent):
            current, _ = _read_timing(timing)
            _atomic_replace(timing, current + row)
        return "recorded"
    finally:
        if not consume_attempted:
            try:
                state.unlink(missing_ok=True)
            except OSError:
                pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise TimingError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="execution_timing.py")
    commands = parser.add_subparsers(
        dest="command", required=True, parser_class=_Parser
    )
    create = commands.add_parser("create")
    create.add_argument("plan", type=Path)
    start = commands.add_parser("start")
    start.add_argument("timing", type=Path)
    start.add_argument("--task", required=True)
    start.add_argument("--round", default="1")
    start.add_argument("--step", required=True)
    end = commands.add_parser("end")
    end.add_argument("state", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.command == "create":
            print(create_timing(args.plan))
        elif args.command == "start":
            print(
                start_step(
                    args.timing,
                    task=args.task,
                    round=args.round,
                    step=args.step,
                )
            )
        else:
            print(finish_step(args.state))
    except (TimingError, OSError, UnicodeError, ValueError, TypeError) as exc:
        reason = " ".join(str(exc).splitlines()) or type(exc).__name__
        print(f"WARNING: execution-timing: {reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
