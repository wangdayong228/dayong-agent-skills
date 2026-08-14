# Superpowers Extension V2 Execution Timing 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

本计划只实现 Execution Timing，不得自行选择 executor 或调度另外两个 Extension skill。

**Goal:** 实现一个旁路计时 skill，在原版 executor 自然产生的步骤边界记录真实起止时间，而不改变 Task、Round、Step 或原版流程。

**Architecture:** `SKILL.md` 约束触发和调用边界，一个 Python 标准库 helper 负责相邻 timing 文件、唯一临时 state、duration 和原子追加。库层只抛异常，CLI 是唯一 warning 边界；失败不重试并单次消费 state。

**Tech Stack:** 中文 Markdown、Agent Skills、Python 3 标准库、POSIX `fcntl` 可用时的并发锁、`unittest`。

**批准规格：** `docs/specs/2026-08-13-superpowers-extension-v2-design.md`

## Global Constraints

- 只有原版 executor 已经确定并开始执行 Plan 后才触发；本 skill 不选择、替换或建议 executor。
- 原版 Superpowers 独占工作流顺序、用户批准、Task dispatch 粒度、review/fix/retry、verification、finishing 以及 Plan 准入和完成条件。
- 每行只能对应一个自然存在、完整捕获起止的 upstream step；不得拆分、合并、重命名、创建或重新 dispatch Task/Round/Step。
- timing/state/helper 缺失、畸形、锁冲突或写入失败时，CLI 只 warning 一次并返回 0；不暂停、不重试、不阻断原版流程。
- 不读取、复制、迁移或兼容旧分支 `feat/superpowers-extension` 的任何材料。
- 不创建全局 timing index、审计字段、后台服务、hook、controller、scheduler 或 gate。
- 确定性失败最多两轮针对性修复和受影响测试重跑；仍失败则记录并停止，不能声称完成。
- 用户于 2026-08-14 再确认 LLM 行为不可控且不得成为交付门禁，因此不运行要求“必须
  失败”的无-skill LLM baseline；确定性测试提供 RED，只运行一次非门禁 enabled smoke。
  明确越界最多一次修改和一次受影响复查，不做 5/5 或“测到满意”。

## 文件与接口

**创建文件：**

- `skills/dy-workflow/superpowers-execution-timing/SKILL.md`
- `skills/dy-workflow/superpowers-execution-timing/agents/openai.yaml`
- `skills/dy-workflow/superpowers-execution-timing/scripts/execution_timing.py`
- `skills/dy-workflow/superpowers-execution-timing/scripts/test_execution_timing.py`

**输入：** Plan 路径，以及原版 executor 自然产生的 `Task`、`Round`、`Step` 开始和结束边界。

**输出：** 每次从头执行一个相邻 `<plan-stem>-timing-YYYYMMDDTHHMMSS.ffffff±HHMM.md`；正文只有 `Task | Round | Step | Start | End | Duration` 六列。同次恢复显式复用原路径，重新从头执行调用新的 `create`。

**Python 接口：**

| 名称 | 精确签名 | 合同 |
| --- | --- | --- |
| `TIMING_HEADER` | `str` | 精确六列表头，供单元和集成合同读取 |
| `Clock` | `Callable[[], datetime]` | 生产真实时钟，测试可注入 |
| `TimingError` | `class TimingError(Exception)` | 库层领域错误 |
| `system_now` | `() -> datetime` | 带本地时区的真实系统时间 |
| `create_timing` | `(plan: Path, *, clock: Clock = system_now) -> Path` | exclusive create 本次执行文件 |
| `start_step` | `(timing: Path, *, task: str, round: str = "1", step: str, clock: Clock = system_now) -> Path` | 创建唯一隐藏 state，不写数据行 |
| `finish_step` | `(state: Path, *, clock: Clock = system_now) -> Literal["recorded"]` | 先单次消费唯一 state，再追加一行；失败抛错，由 CLI 降级为 warning |
| `main` | `(argv: Sequence[str] \| None = None) -> int` | CLI 所有预期失败单 warning、返回 0 |

**CLI：**

```text
execution_timing.py create PLAN
execution_timing.py start TIMING --task TASK [--round ROUND] --step STEP
execution_timing.py end STATE
```

生产 CLI 不允许传入伪造时间；`clock` 只供单元测试。

---

### Task 1: Execution Timing skill 与确定性 helper

- [ ] **Step 1: 使用官方 initializer 创建 scaffold**

运行：

```bash
python3 /Users/dayong/.agents/skills/.system/skill-creator/scripts/init_skill.py \
  superpowers-execution-timing \
  --path skills/dy-workflow \
  --resources scripts \
  --interface 'display_name=Superpowers Execution Timing' \
  --interface 'short_description=Record natural Plan steps without blocking.' \
  --interface 'default_prompt=Use $superpowers-execution-timing after the original executor starts this Plan.'
```

预期：创建 skill、`scripts/` 和 metadata scaffold；不生成示例文件。

- [ ] **Step 2: 写入完整失败测试**

创建 `skills/dy-workflow/superpowers-execution-timing/scripts/test_execution_timing.py`：

```python
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).with_name("execution_timing.py")
SKILL = Path(__file__).parents[1] / "SKILL.md"
SPEC = importlib.util.spec_from_file_location("execution_timing_under_test", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
TIMING = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TIMING
SPEC.loader.exec_module(TIMING)


def fixed(value: str):
    instant = datetime.fromisoformat(value)
    return lambda: instant


def cells(row: str) -> list[str]:
    return [value.strip() for value in row.strip().strip("|").split("|")]


class ExecutionTimingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.plan = self.root / "feature-plan.md"
        self.plan.write_text("# Plan\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create(self, at: str = "2026-08-13T14:32:05.123456+08:00") -> Path:
        return TIMING.create_timing(self.plan, clock=fixed(at))

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = TIMING.main(list(argv))
        return result, stdout.getvalue(), stderr.getvalue()

    def assert_one_warning(self, stderr: str) -> None:
        self.assertEqual(stderr.count("WARNING: execution-timing:"), 1, stderr)
        self.assertEqual(len(stderr.strip().splitlines()), 1, stderr)

    def test_create_uses_adjacent_timestamp_name_and_exact_six_columns(self) -> None:
        timing = self.create()
        self.assertEqual(timing.parent, self.plan.parent)
        self.assertEqual(
            timing.name, "feature-plan-timing-20260813T143205.123456+0800.md"
        )
        self.assertEqual(timing.read_text(encoding="utf-8"), TIMING.TIMING_HEADER)
        lines = TIMING.TIMING_HEADER.splitlines()
        self.assertEqual(
            cells(lines[0]), ["Task", "Round", "Step", "Start", "End", "Duration"]
        )
        self.assertEqual(len(cells(lines[1])), 6)

    def test_system_now_is_timezone_aware_and_between_call_bounds(self) -> None:
        before = datetime.now().astimezone()
        observed = TIMING.system_now()
        after = datetime.now().astimezone()
        self.assertIsNotNone(observed.tzinfo)
        self.assertIsNotNone(observed.utcoffset())
        self.assertLessEqual(before, observed)
        self.assertLessEqual(observed, after)

    def test_start_creates_unique_state_without_timing_row(self) -> None:
        timing = self.create()
        state = TIMING.start_step(
            timing,
            task="Task 1",
            round="1",
            step="Run focused unit test",
            clock=fixed("2026-08-13T14:33:00.100000+08:00"),
        )
        self.assertNotEqual(state, timing)
        self.assertTrue(state.name.startswith(f".{timing.name}.step-"))
        data = json.loads(state.read_text(encoding="utf-8"))
        self.assertEqual(set(data), {"timing", "task", "round", "step", "start"})
        self.assertEqual(data["timing"], timing.name)
        self.assertEqual(timing.read_text(encoding="utf-8"), TIMING.TIMING_HEADER)

    def test_finish_writes_exact_start_end_and_six_decimal_duration(self) -> None:
        timing = self.create()
        state = TIMING.start_step(
            timing,
            task="Task 1",
            step="Run focused unit test",
            clock=fixed("2026-08-13T14:33:00.100000+08:00"),
        )
        result = TIMING.finish_step(
            state, clock=fixed("2026-08-13T14:33:12.445678+08:00")
        )
        self.assertEqual(result, "recorded")
        self.assertFalse(state.exists())
        self.assertEqual(
            timing.read_text(encoding="utf-8"),
            TIMING.TIMING_HEADER
            + "| Task 1 | 1 | Run focused unit test | "
            "2026-08-13T14:33:00.100000+08:00 | "
            "2026-08-13T14:33:12.445678+08:00 | 12.345678s |\n",
        )

    def test_unfinished_state_never_enters_timing(self) -> None:
        timing = self.create()
        state = TIMING.start_step(timing, task="Task 1", step="Implement")
        self.assertTrue(state.exists())
        self.assertEqual(timing.read_text(encoding="utf-8"), TIMING.TIMING_HEADER)

    def test_resume_explicitly_appends_to_same_timing_file(self) -> None:
        timing = self.create()
        first = TIMING.start_step(
            timing,
            task="Task 1",
            step="Test",
            clock=fixed("2026-08-13T14:33:00+08:00"),
        )
        TIMING.finish_step(first, clock=fixed("2026-08-13T14:33:01+08:00"))
        resumed = TIMING.start_step(
            timing,
            task="Task 1",
            round="2",
            step="Fix",
            clock=fixed("2026-08-13T14:34:00+08:00"),
        )
        TIMING.finish_step(resumed, clock=fixed("2026-08-13T14:34:02+08:00"))
        rows = timing.read_text(encoding="utf-8").splitlines()[2:]
        self.assertEqual(len(rows), 2)
        self.assertIn("| Task 1 | 2 | Fix |", rows[1])

    def test_restart_in_same_second_creates_a_new_timing_file(self) -> None:
        first = self.create("2026-08-13T14:32:05.100000+08:00")
        second = self.create("2026-08-13T14:32:05.200000+08:00")
        self.assertNotEqual(first, second)
        self.assertTrue(first.exists())
        self.assertTrue(second.exists())

    def test_parallel_same_named_steps_with_same_start_both_write_rows(self) -> None:
        timing = self.create()
        same_start = fixed("2026-08-13T14:33:00.123456+08:00")
        first = TIMING.start_step(
            timing, task="Task 1", step="Test", clock=same_start
        )
        second = TIMING.start_step(
            timing, task="Task 1", step="Test", clock=same_start
        )
        self.assertNotEqual(first, second)
        TIMING.finish_step(
            first, clock=fixed("2026-08-13T14:33:01.123456+08:00")
        )
        TIMING.finish_step(
            second, clock=fixed("2026-08-13T14:33:02.123456+08:00")
        )
        rows = timing.read_text(encoding="utf-8").splitlines()[2:]
        self.assertEqual(len(rows), 2)
        self.assertEqual(cells(rows[0])[:4], cells(rows[1])[:4])

    def test_missing_or_malformed_state_warns_once_and_writes_nothing(self) -> None:
        timing = self.create()
        original = timing.read_text(encoding="utf-8")
        missing = self.root / ".missing.json"
        result, _, stderr = self.run_cli("end", str(missing))
        self.assertEqual(result, 0)
        self.assert_one_warning(stderr)
        malformed = self.root / ".malformed.json"
        malformed.write_text("not json\n", encoding="utf-8")
        result, _, stderr = self.run_cli("end", str(malformed))
        self.assertEqual(result, 0)
        self.assert_one_warning(stderr)
        self.assertFalse(malformed.exists())
        self.assertEqual(timing.read_text(encoding="utf-8"), original)

    def test_malformed_timing_warns_once_and_preserves_original(self) -> None:
        timing = self.create()
        state = TIMING.start_step(timing, task="Task 1", step="Test")
        timing.write_text("malformed\n", encoding="utf-8")
        result, _, stderr = self.run_cli("end", str(state))
        self.assertEqual(result, 0)
        self.assert_one_warning(stderr)
        self.assertFalse(state.exists())
        self.assertEqual(timing.read_text(encoding="utf-8"), "malformed\n")

    def test_end_before_start_warns_once_and_writes_nothing(self) -> None:
        timing = self.create()
        state = TIMING.start_step(
            timing,
            task="Task 1",
            step="Test",
            clock=fixed("2999-01-01T00:00:00+00:00"),
        )
        result, _, stderr = self.run_cli("end", str(state))
        self.assertEqual(result, 0)
        self.assert_one_warning(stderr)
        self.assertFalse(state.exists())
        self.assertEqual(timing.read_text(encoding="utf-8"), TIMING.TIMING_HEADER)

    def test_second_end_warns_and_does_not_duplicate_row(self) -> None:
        timing = self.create()
        state = TIMING.start_step(
            timing,
            task="Task 1",
            step="Test",
            clock=fixed("2026-08-13T14:33:00+08:00"),
        )
        self.assertEqual(
            TIMING.finish_step(
                state, clock=fixed("2026-08-13T14:33:01+08:00")
            ),
            "recorded",
        )
        result, _, stderr = self.run_cli("end", str(state))
        self.assertEqual(result, 0)
        self.assert_one_warning(stderr)
        self.assertFalse(state.exists())
        self.assertEqual(len(timing.read_text(encoding="utf-8").splitlines()[2:]), 1)

    @unittest.skipIf(TIMING.fcntl is None, "requires POSIX fcntl")
    def test_nonblocking_lock_conflict_warns_once_and_consumes_state(self) -> None:
        timing = self.create()
        state = TIMING.start_step(timing, task="Task 1", step="Test")
        with mock.patch.object(
            TIMING.fcntl, "flock", side_effect=BlockingIOError("busy")
        ) as flock:
            result, _, stderr = self.run_cli("end", str(state))
        self.assertEqual(result, 0)
        self.assert_one_warning(stderr)
        self.assertEqual(flock.call_count, 1)
        self.assertFalse(state.exists())
        self.assertEqual(timing.read_text(encoding="utf-8"), TIMING.TIMING_HEADER)

    def test_atomic_replace_failure_warns_once_preserves_timing_and_consumes_state(self) -> None:
        timing = self.create()
        original = timing.read_text(encoding="utf-8")
        state = TIMING.start_step(timing, task="Task 1", step="Test")
        with mock.patch.object(TIMING.os, "replace", side_effect=OSError("disk error")):
            result, _, stderr = self.run_cli("end", str(state))
        self.assertEqual(result, 0)
        self.assert_one_warning(stderr)
        self.assertEqual(timing.read_text(encoding="utf-8"), original)
        self.assertFalse(state.exists())

    def test_state_delete_failure_warns_once_without_writing(self) -> None:
        timing = self.create()
        original = timing.read_text(encoding="utf-8")
        state = TIMING.start_step(timing, task="Task 1", step="Test")
        original_unlink = TIMING.Path.unlink

        def fail_target(path, *args, **kwargs):
            if path == state:
                raise PermissionError("denied")
            return original_unlink(path, *args, **kwargs)

        with mock.patch.object(TIMING.Path, "unlink", new=fail_target):
            result, _, stderr = self.run_cli("end", str(state))
        self.assertEqual(result, 0)
        self.assert_one_warning(stderr)
        self.assertEqual(timing.read_text(encoding="utf-8"), original)
        self.assertTrue(state.exists())

    def test_cli_argument_and_artifact_failures_warn_once_and_return_zero(self) -> None:
        for argv in (
            ("create", str(self.root / "missing.md")),
            ("start",),
            ("unknown",),
        ):
            with self.subTest(argv=argv):
                result, stdout, stderr = self.run_cli(*argv)
                self.assertEqual(result, 0)
                self.assertEqual(stdout, "")
                self.assert_one_warning(stderr)
                self.assertNotIn("usage:", stderr)

    def test_skill_contract_requires_upstream_executor_to_be_running(self) -> None:
        text = " ".join(SKILL.read_text(encoding="utf-8").split())
        self.assertIn("只有原版 executor 已经选择并开始执行 Plan 后才能触发", text)
        self.assertIn("不选择或替换 executor", text)

    def test_skill_contract_forbids_new_granularity_retry_and_gating(self) -> None:
        text = " ".join(SKILL.read_text(encoding="utf-8").split())
        for contract in (
            "不得拆分、合并、重命名、创建或重新 dispatch 任何 Task、Round 或 Step",
            "一条 warning 后立即继续原版流程，不重试",
            "不得控制 execution、review、verification 或 finishing",
        ):
            self.assertIn(contract, text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 运行 RED**

运行：

```bash
python3 -m unittest \
  skills/dy-workflow/superpowers-execution-timing/scripts/test_execution_timing.py -v
```

预期：ERROR/FAIL，明确原因是 `execution_timing.py` 尚不存在；不能通过放宽测试获得 GREEN。

- [ ] **Step 4: 写入最小 helper**

创建 `skills/dy-workflow/superpowers-execution-timing/scripts/execution_timing.py`：

```python
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
```

- [ ] **Step 5: 写入 skill 指令和元数据**

用以下内容完整替换 `skills/dy-workflow/superpowers-execution-timing/SKILL.md`：

````markdown
---
name: superpowers-execution-timing
description: >-
  Use when an original Superpowers executor is already running a written Plan
  and observable natural step timing should be recorded as sidecar data.
---

# Superpowers Execution Timing

## 合同

| 输入 | 输出 | 触发时机 | 不改变控制流的原因 |
| --- | --- | --- | --- |
| Plan 路径及原版自然步骤边界 | 本次执行的相邻 timing 文件 | 原版 executor 确定并开始执行 Plan 后 | 只记录已发生步骤；任何失败后一条 warning 后立即继续原版流程，不重试 |

只有原版 executor 已经选择并开始执行 Plan 后才能触发。本 skill 不选择或替换 executor，
也不读取 Plan Assistant 报告或依据 findings 决定执行。

## 一次执行

先把 `HELPER` 解析为当前 `SKILL.md` 所在目录下的
`scripts/execution_timing.py` 绝对路径；不得假设当前工作目录是 skill 目录。

每次从头执行 Plan 时调用一次 `create`，保留命令输出的 timing 路径：

```bash
python3 "$HELPER" create PLAN
```

同次执行恢复时显式继续使用已知 timing 路径；重新从头执行时调用一次新的 `create`。
无法确认是恢复还是重启时不猜测，保留一条 warning 并让原版执行继续；不使用 `latest`、
自动发现或全局 index。

## 自然 step 边界

在每个原版自然 step 开始时调用一次：

```bash
python3 "$HELPER" start TIMING \
  --task TASK --round ROUND --step STEP
```

保存命令输出的唯一 state 路径。在同一自然 step 结束时调用一次：

```bash
python3 "$HELPER" end STATE
```

`Task`、`Round` 和 `Step` 沿用原版执行的实际名称与边界；原版没有 Round 时使用 `1`。
不得拆分、合并、重命名、创建或重新 dispatch 任何 Task、Round 或 Step，也不得为计时
重新执行自然 step。

只记录完整捕获的起止时间。缺少 start 或 end 的步骤不进入 timing，不估算、不回填历史。
Start 和 End 是 helper 调用时的带时区真实系统时间，Duration 由同一行确定性计算。

## 失败边界

每个 `create`、`start` 或 `end` 只调用一次。helper 是 warning 的唯一输出边界；出现一条
warning 后不要重复转述，也不要重试。timing/state/锁/写入失败不得暂停或改变 upstream
执行。`end` 一旦开始就对 state 做一次 best-effort 删除；不论删除是否成功，skill 都
立即放弃该 state，禁止再次调用 `end`。即使格式错误、结束早于开始、锁竞争或写入失败
也不重试；删除失败可能留下临时文件，但该文件不得被 skill 重新使用。

timing 正文只能包含 `Task | Round | Step | Start | End | Duration` 六列，不增加 execution
ID、状态、evaluator 输出、session path、turn ID 或模型字段。不建立全局 timing index。

本 skill 不增加任何状态机，timing artifact 不得控制 execution、review、verification 或
finishing。发生规则冲突时服从原版 Superpowers；若必须改变原版规则才能记录，停止记录
并先询问用户。
````

用以下内容完整替换 `skills/dy-workflow/superpowers-execution-timing/agents/openai.yaml`：

```yaml
interface:
  display_name: "Superpowers Execution Timing"
  short_description: "Record natural Plan steps without blocking."
  default_prompt: "Use $superpowers-execution-timing after the original executor starts this Plan."

policy:
  allow_implicit_invocation: true
```

- [ ] **Step 6: 运行 GREEN**

运行：

```bash
python3 -m unittest \
  skills/dy-workflow/superpowers-execution-timing/scripts/test_execution_timing.py -v
```

预期：全部 PASS。若失败，只修正实现或明确的测试错误，不放宽自然 step 或非阻断合同。

- [ ] **Step 7: 运行一次 enabled LLM smoke**

运行一次：

```bash
mktemp -d /private/tmp/superpowers-execution-timing-smoke.XXXXXX
```

预期：stdout 只有一个新建目录的绝对路径。把这次 stdout 记为 `SMOKE_DIR`，不要运行第二次
`mktemp`。使用 `apply_patch`，以该真实绝对路径创建以下固定 Plan；不得使用 shell 重定向
写文件：

```markdown
# Timing Smoke Plan

## Task 1: Focused test

- Step: Run focused unit test
```

调用 `collaboration.spawn_agent` 一次，参数固定为
`task_name="execution_timing_enabled_smoke"`、`fork_turns="none"`。发送前把下方消息中的
`ABSOLUTE_SMOKE_DIR` 替换成 `mktemp` stdout 的真实绝对路径；不得发送字面占位符。这是
语义检查，不实际执行 Plan 或伪造 timing 行。消息为：

```text
Use $superpowers-execution-timing at
skills/dy-workflow/superpowers-execution-timing/SKILL.md. The original executor
has already been selected and is about to run the existing natural step
"Run focused unit test" in Task 1 of ABSOLUTE_SMOKE_DIR/timing-smoke-plan.md.
Only describe the exact timing helper calls and boundaries you would use.
```

随后只调用 `collaboration.wait_agent` 等待该 agent 完成，不追加 follow-up prompt。

结果只分三态。新增 Task/Round/Step、重新 dispatch、要求 timing 成功后才能继续、估算未捕获时间、读取 Plan review report，任一为“发现明确越界”；只复用自然 step 且失败非阻断为“未发现明显问题”；证据不足为“无法判断”。只在本 Task 最终 handoff 记录三态，不保存原文、会话路径、turn ID 或模型信息。

若发现明确越界，最多修改 `SKILL.md` 一次，并用同一 fixture/prompt 复查一次；同一次
受影响复查还必须重跑本 skill 的确定性测试一次，确认 timing 与非阻断合同未被修改破坏。
确定性测试失败时停止，不提交、不声称完成。LLM 复查后仍越界或无法判断时，只记录三态
和剩余风险并结束本 smoke，不再修改或采样；LLM 结果本身不控制提交或完成。措辞或格式
差异不触发修改或重跑。

- [ ] **Step 8: 验证 metadata（前置依赖可用时）**

先运行：

```bash
python3 -c 'import yaml'
```

若命令失败，按 `pre-verification-check` 停止当前 Task 并询问用户是否允许在开发验证
环境提供 PyYAML；不得擅自加入产品依赖、提交或声称已运行 validator。用户提供依赖后，
先重新运行上面的 import 命令确认成功，再运行：

```bash
python3 /Users/dayong/.agents/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/dy-workflow/superpowers-execution-timing
```

预期：`Skill is valid!`。validator 未运行不改变原版 Superpowers 流程；确定性单元测试仍是本 Task 的完成证据。

- [ ] **Step 9: 提交本 Task**

```bash
git add skills/dy-workflow/superpowers-execution-timing
git commit -m "feat(workflow): add nonblocking execution timing"
```

## 完成条件

- 每个新执行文件名包含真实开始时间和微秒；恢复显式复用，重启新建。
- timing 正文精确六列，每行来自自然 step 的完整真实起止，Duration 可确定性复算。
- finish 在写入前对唯一 state 做一次 best-effort 删除；skill 不重试、不复用残留 state；
  成功删除后的第二次 end 只 warning，且不会重复落行。
- 锁冲突、写入失败和参数错误均单 warning、返回 0、无重试。
- smoke 三态结果只记录风险，不控制提交或完成。
- skill 不选择 executor、不改 dispatch 粒度、不读取 report，也不新增 gate。
