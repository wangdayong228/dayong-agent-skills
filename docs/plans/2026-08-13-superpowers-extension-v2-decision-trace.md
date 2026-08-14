# Superpowers Extension V2 Decision Trace 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

本计划只实现 Decision Trace，不得自行调度另外两个 Extension skill。

**Goal:** 实现一个轻量、相邻、非阻断的 Decision Trace skill，在关键提问前复用已确认决策，并安全记录用户新确认的完整决策。

**Architecture:** `SKILL.md` 负责判断性流程，一个 Python 标准库 helper 负责相邻路径、四列表格解析、非阻塞目录锁和原子更新。helper 的库层只抛异常，CLI 是唯一 warning 边界；任何失败都立即返回原版 Superpowers 流程。

**Tech Stack:** 中文 Markdown、Agent Skills、POSIX Python 3 标准库、`unittest`。

**批准规格：** `docs/specs/2026-08-13-superpowers-extension-v2-design.md`

## Global Constraints

- 原版 Superpowers 独占工作流顺序、用户批准、executor、Task dispatch、review/fix/retry、verification、finishing 以及 Plan 准入和完成条件。
- Decision Trace 只增加信息；trace/helper 缺失、过期、不可读、不可解析、锁冲突或写入失败时只 warning 一次，不暂停、不重试、不阻断原版流程。
- 不读取、复制、迁移或兼容旧分支 `feat/superpowers-extension` 的任何 Plan、实现、review report、evidence 或 timing。
- 不创建全局 trace、`specs/index.md`、hash、mtime 准入、审计数据、控制器、scheduler 或后台服务。
- 确定性失败最多两轮针对性修复和受影响测试重跑；仍失败则记录并停止，不能声称完成。
- 用户于 2026-08-14 再确认 LLM 行为不可控且不得成为交付门禁，因此不运行要求“必须
  失败”的无-skill LLM baseline；确定性测试提供 RED，只运行一次非门禁 enabled smoke。
  明确越界最多一次修改和一次受影响复查，不做 5/5 或“测到满意”。

## 文件与接口

**创建文件：**

- `skills/dy-workflow/superpowers-decision-trace/SKILL.md`
- `skills/dy-workflow/superpowers-decision-trace/agents/openai.yaml`
- `skills/dy-workflow/superpowers-decision-trace/scripts/decision_trace.py`
- `skills/dy-workflow/superpowers-decision-trace/scripts/test_decision_trace.py`

**输入：** 当前 spec、可选相邻 trace、用户新确认的决策、来源和确认日期。

**输出：** 唯一相邻 `<spec-stem>-decision-trace.md`，正文只有 `决策主题 | 已确认决策 | 来源 | 确认日期` 四列。

**Python 接口：**

| 名称 | 精确签名 | 合同 |
| --- | --- | --- |
| `TRACE_HEADER` | `str` | 精确四列表头，供单元和集成合同读取 |
| `Decision` | `topic: str`, `decision: str`, `source: str`, `confirmed_on: date` | 不可变值对象 |
| `TraceError` | `class TraceError(Exception)` | 库层领域错误 |
| `adjacent_trace_path` | `(spec: Path) -> Path` | 唯一相邻路径 |
| `load_decisions` | `(spec: Path) -> list[Decision]` | trace 不存在返回空列表；存在但畸形则抛错 |
| `record_decision` | `(spec: Path, entry: Decision, *, replace_conflict: bool = False) -> Literal["created", "unchanged", "replaced", "conflict"]` | 锁内原子记录并保护冲突 |
| `main` | `(argv: Sequence[str] \| None = None) -> int` | CLI 所有预期失败单 warning、返回 0 |

**CLI：**

```text
decision_trace.py read SPEC
decision_trace.py record SPEC --topic TOPIC --decision DECISION \
  --source-kind user|approved-spec [--source-ref SPEC#SECTION] \
  [--confirmed-on YYYY-MM-DD] [--replace-conflict]
```

---

### Task 1: Decision Trace skill 与确定性 helper

- [ ] **Step 1: 使用官方 initializer 创建 scaffold**

运行：

```bash
python3 /Users/dayong/.agents/skills/.system/skill-creator/scripts/init_skill.py \
  superpowers-decision-trace \
  --path skills/dy-workflow \
  --resources scripts \
  --interface 'display_name=Superpowers Decision Trace' \
  --interface 'short_description=Reuse confirmed decisions without repeat questions.' \
  --interface 'default_prompt=Use $superpowers-decision-trace while refining this written spec.'
```

预期：创建 skill、`scripts/` 和 `agents/openai.yaml` scaffold；不得生成示例或额外 resource。

- [ ] **Step 2: 写入完整失败测试**

创建 `skills/dy-workflow/superpowers-decision-trace/scripts/test_decision_trace.py`：

```python
from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "decision_trace.py"
SKILL = HERE.parent / "SKILL.md"
module_spec = importlib.util.spec_from_file_location("decision_trace", SCRIPT)
if module_spec is None or module_spec.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
dt = importlib.util.module_from_spec(module_spec)
sys.modules[module_spec.name] = dt
module_spec.loader.exec_module(dt)


class DecisionTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.design = self.root / "api.v2-design.md"
        self.design.write_text("# Spec\n", encoding="utf-8")

    def entry(self, decision: str = "只使用本地文件。"):
        return dt.Decision(
            "部署模式", decision, dt.USER_SOURCE, date(2026, 8, 13)
        )

    def test_adjacent_path_for_multi_suffix_spec(self) -> None:
        self.assertEqual(
            dt.adjacent_trace_path(self.design),
            self.root / "api.v2-design-decision-trace.md",
        )

    def test_first_record_creates_exact_four_column_table(self) -> None:
        self.assertEqual(dt.record_decision(self.design, self.entry()), "created")
        text = dt.adjacent_trace_path(self.design).read_text(encoding="utf-8")
        self.assertTrue(text.startswith(dt.TRACE_HEADER))
        self.assertEqual(len(dt._split_row(text.splitlines()[2])), 4)
        self.assertEqual(dt.load_decisions(self.design), [self.entry()])

    def test_markdown_escape_round_trip_and_newline_normalization(self) -> None:
        entry = dt.Decision(
            r"范围\路径|模式",
            "第一行\r\n第二行 | 保留 \\ 路径",
            dt.USER_SOURCE,
            date(2026, 8, 13),
        )
        normalized = dt.Decision(
            r"范围\路径|模式",
            "第一行 第二行 | 保留 \\ 路径",
            dt.USER_SOURCE,
            date(2026, 8, 13),
        )
        dt.record_decision(self.design, entry)
        self.assertEqual(dt.load_decisions(self.design), [normalized])

    def test_duplicate_is_unchanged(self) -> None:
        dt.record_decision(self.design, self.entry())
        trace = dt.adjacent_trace_path(self.design)
        before = trace.read_bytes()
        self.assertEqual(dt.record_decision(self.design, self.entry()), "unchanged")
        self.assertEqual(trace.read_bytes(), before)

    def test_conflict_preserves_original_bytes(self) -> None:
        dt.record_decision(self.design, self.entry())
        trace = dt.adjacent_trace_path(self.design)
        before = trace.read_bytes()
        self.assertEqual(
            dt.record_decision(self.design, self.entry("允许网络服务。")),
            "conflict",
        )
        self.assertEqual(trace.read_bytes(), before)

    def test_replace_after_confirmation_keeps_only_latest(self) -> None:
        dt.record_decision(self.design, self.entry())
        newer = self.entry("仍只使用本地文件，但允许临时状态文件。")
        self.assertEqual(
            dt.record_decision(self.design, newer, replace_conflict=True),
            "replaced",
        )
        self.assertEqual(dt.load_decisions(self.design), [newer])

    def test_rejects_empty_fields_invalid_date_and_invalid_source(self) -> None:
        invalid = [
            dt.Decision(" ", "决定", dt.USER_SOURCE, date(2026, 8, 13)),
            dt.Decision("主题", "决定", "用户说过", date(2026, 8, 13)),
            dt.Decision(
                "主题", "决定", dt.APPROVED_PREFIX + "spec.md", date(2026, 8, 13)
            ),
            dt.Decision("主题", "决定", dt.USER_SOURCE, "2026-08-13"),
        ]
        for entry in invalid:
            with self.subTest(entry=entry), self.assertRaises(dt.TraceError):
                dt.record_decision(self.design, entry)

    def test_empty_or_malformed_trace_is_not_overwritten(self) -> None:
        trace = dt.adjacent_trace_path(self.design)
        for payload in ("", "bad trace\n", dt.TRACE_HEADER + "bad row\n"):
            with self.subTest(payload=payload):
                trace.write_text(payload, encoding="utf-8")
                before = trace.read_bytes()
                with self.assertRaises(dt.TraceError):
                    dt.record_decision(self.design, self.entry())
                self.assertEqual(trace.read_bytes(), before)

    def test_atomic_replace_failure_preserves_original(self) -> None:
        dt.record_decision(self.design, self.entry())
        trace = dt.adjacent_trace_path(self.design)
        before = trace.read_bytes()
        with mock.patch.object(dt.os, "replace", side_effect=OSError("denied")):
            with self.assertRaises(OSError):
                dt.record_decision(
                    self.design,
                    self.entry("替换结论。"),
                    replace_conflict=True,
                )
        self.assertEqual(trace.read_bytes(), before)

    @unittest.skipIf(dt.fcntl is None, "requires POSIX fcntl")
    def test_nonblocking_lock_conflict_warns_once_and_preserves_original(self) -> None:
        dt.record_decision(self.design, self.entry())
        trace = dt.adjacent_trace_path(self.design)
        before = trace.read_bytes()
        holder = subprocess.Popen(
            [
                sys.executable,
                "-c",
                (
                    "import fcntl,os,time; "
                    f"fd=os.open({str(self.root)!r},os.O_RDONLY); "
                    "fcntl.flock(fd,fcntl.LOCK_EX); "
                    "print('READY',flush=True); time.sleep(5)"
                ),
            ],
            text=True,
            stdout=subprocess.PIPE,
        )
        try:
            self.assertIsNotNone(holder.stdout)
            self.assertEqual(holder.stdout.readline().strip(), "READY")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "record",
                    str(self.design),
                    "--topic",
                    "新主题",
                    "--decision",
                    "新决定。",
                    "--source-kind",
                    "user",
                    "--confirmed-on",
                    "2026-08-13",
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=2,
            )
        finally:
            holder.terminate()
            holder.wait(timeout=2)
            if holder.stdout is not None:
                holder.stdout.close()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr.count("WARNING: decision-trace:"), 1)
        self.assertEqual(trace.read_bytes(), before)

    def test_cli_missing_read_warns_once_and_outputs_empty_table(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(dt.main(["read", str(self.design)]), 0)
        self.assertEqual(stdout.getvalue(), dt.TRACE_HEADER)
        self.assertEqual(stderr.getvalue().count("WARNING: decision-trace:"), 1)
        self.assertEqual(len(stderr.getvalue().strip().splitlines()), 1)
        self.assertFalse(dt.adjacent_trace_path(self.design).exists())

    def test_cli_argument_failure_warns_once_and_returns_zero(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = dt.main(["record", str(self.design), "--topic", "缺参数"])
        self.assertEqual(result, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue().count("WARNING: decision-trace:"), 1)
        self.assertEqual(len(stderr.getvalue().strip().splitlines()), 1)
        self.assertNotIn("usage:", stderr.getvalue())

    def test_cli_artifact_failure_warns_once_and_returns_zero(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = dt.main(["read", str(self.root / "missing.md")])
        self.assertEqual(result, 0)
        self.assertEqual(stderr.getvalue().count("WARNING: decision-trace:"), 1)

    def test_skill_contract(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for required in (
            "每次关键需求问题前重读",
            "禁止重复询问",
            "一次只问一个问题",
            "可独立理解",
            "不得声称该信息已持久保存",
            "不得使用 hash 或 mtime",
            "不得保存完整问题",
            "session path",
            "turn ID",
            "不创建全局 trace",
            "不创建 `specs/index.md`",
            "逐条核对来源",
            "路径或章节不存在",
            "不得影响",
        ):
            self.assertIn(required, text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 运行 RED**

运行：

```bash
python3 -m unittest \
  skills/dy-workflow/superpowers-decision-trace/scripts/test_decision_trace.py -v
```

预期：ERROR/FAIL，明确原因是 `decision_trace.py` 尚不存在；不能通过放宽测试获得 GREEN。

- [ ] **Step 4: 写入最小 helper**

创建 `skills/dy-workflow/superpowers-decision-trace/scripts/decision_trace.py`：

```python
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

TRACE_HEADER = (
    "| 决策主题 | 已确认决策 | 来源 | 确认日期 |\n"
    "| --- | --- | --- | --- |\n"
)
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
    if not isinstance(value, str):
        raise TraceError(f"{field} must be text")
    value = re.sub(r"\r\n?|\n", " ", value).strip()
    if not value:
        raise TraceError(f"{field} must not be empty")
    return value


def _normalize(entry: Decision) -> Decision:
    if type(entry.confirmed_on) is not date:
        raise TraceError("confirmed_on must be a date")
    topic = _one_line(entry.topic, "topic")
    decision = _one_line(entry.decision, "decision")
    source = _one_line(entry.source, "source")
    if source != USER_SOURCE:
        if not source.startswith(APPROVED_PREFIX):
            raise TraceError("source must be a user answer or approved spec section")
        path, mark, section = source[len(APPROVED_PREFIX) :].rpartition("#")
        if not mark or not path.strip() or not section.strip():
            raise TraceError("approved spec source must be SPEC#SECTION")
    return Decision(topic, decision, source, entry.confirmed_on)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|")


def _split_row(line: str) -> list[str]:
    if not line.startswith("|") or not line.endswith("|"):
        raise TraceError("malformed decision row")
    fields: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line[1:-1]:
        if escaped:
            if char not in ("\\", "|"):
                raise TraceError("invalid markdown escape")
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
        raise TraceError("unfinished markdown escape")
    fields.append("".join(current).strip())
    if len(fields) != 4:
        raise TraceError("decision row must have four columns")
    return fields


def _render(entries: list[Decision]) -> str:
    rows = [TRACE_HEADER]
    for entry in entries:
        rows.append(
            "| "
            + " | ".join(
                _escape(value)
                for value in (
                    entry.topic,
                    entry.decision,
                    entry.source,
                    entry.confirmed_on.isoformat(),
                )
            )
            + " |\n"
        )
    return "".join(rows)


def _require_spec(spec: Path) -> None:
    if not spec.is_file():
        raise TraceError(f"spec does not exist: {spec}")


def load_decisions(spec: Path) -> list[Decision]:
    spec = Path(spec)
    _require_spec(spec)
    trace = adjacent_trace_path(spec)
    try:
        text = trace.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except (OSError, UnicodeError) as exc:
        raise TraceError(f"cannot read trace: {exc}") from exc
    if not text.startswith(TRACE_HEADER):
        raise TraceError("trace must start with the exact four-column header")
    payload = text[len(TRACE_HEADER) :]
    if not payload:
        return []
    if not text.endswith("\n"):
        raise TraceError("trace must end with a newline")
    entries: list[Decision] = []
    topics: set[str] = set()
    for line in payload.splitlines():
        if not line:
            raise TraceError("blank rows are not allowed")
        topic, decision, source, confirmed = _split_row(line)
        try:
            confirmed_on = date.fromisoformat(confirmed)
        except ValueError as exc:
            raise TraceError("confirmed date must be YYYY-MM-DD") from exc
        entry = _normalize(Decision(topic, decision, source, confirmed_on))
        if entry.topic in topics:
            raise TraceError(f"duplicate decision topic: {entry.topic}")
        topics.add(entry.topic)
        entries.append(entry)
    return entries


@contextmanager
def _directory_lock(parent: Path) -> Iterator[None]:
    if fcntl is None:
        raise TraceError("nonblocking file locking is unavailable")
    try:
        descriptor = os.open(parent, os.O_RDONLY)
    except OSError as exc:
        raise TraceError(f"cannot open trace directory: {exc}") from exc
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise TraceError("trace directory is busy") from exc
        yield
    finally:
        os.close(descriptor)


def _atomic_write(path: Path, text: str) -> None:
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def record_decision(
    spec: Path,
    entry: Decision,
    *,
    replace_conflict: bool = False,
) -> Status:
    spec = Path(spec)
    entry = _normalize(entry)
    _require_spec(spec)
    trace = adjacent_trace_path(spec)
    with _directory_lock(spec.parent):
        entries = load_decisions(spec)
        for index, current in enumerate(entries):
            if current.topic != entry.topic:
                continue
            if current.decision == entry.decision:
                return "unchanged"
            if not replace_conflict:
                return "conflict"
            entries[index] = entry
            _atomic_write(trace, _render(entries))
            return "replaced"
        entries.append(entry)
        _atomic_write(trace, _render(entries))
        return "created"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise TraceError(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="decision_trace.py")
    commands = parser.add_subparsers(
        dest="command", required=True, parser_class=_Parser
    )
    read = commands.add_parser("read")
    read.add_argument("spec", type=Path)
    record = commands.add_parser("record")
    record.add_argument("spec", type=Path)
    record.add_argument("--topic", required=True)
    record.add_argument("--decision", required=True)
    record.add_argument(
        "--source-kind", required=True, choices=("user", "approved-spec")
    )
    record.add_argument("--source-ref")
    record.add_argument("--confirmed-on")
    record.add_argument("--replace-conflict", action="store_true")
    return parser


def _source(kind: str, reference: str | None) -> str:
    if kind == "user":
        if reference:
            raise TraceError("user source does not accept --source-ref")
        return USER_SOURCE
    if not reference:
        raise TraceError("approved-spec source requires --source-ref SPEC#SECTION")
    return APPROVED_PREFIX + reference


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
        if args.command == "read":
            trace = adjacent_trace_path(args.spec)
            sys.stdout.write(_render(load_decisions(args.spec)))
            if not trace.exists():
                print(
                    f"WARNING: decision-trace: trace does not exist: {trace}",
                    file=sys.stderr,
                )
            return 0
        try:
            confirmed_on = (
                date.fromisoformat(args.confirmed_on)
                if args.confirmed_on
                else date.today()
            )
        except ValueError as exc:
            raise TraceError("confirmed date must be YYYY-MM-DD") from exc
        status = record_decision(
            args.spec,
            Decision(
                args.topic,
                args.decision,
                _source(args.source_kind, args.source_ref),
                confirmed_on,
            ),
            replace_conflict=args.replace_conflict,
        )
        print(status)
    except (TraceError, OSError, UnicodeError, ValueError, TypeError) as exc:
        reason = " ".join(str(exc).splitlines()) or type(exc).__name__
        print(f"WARNING: decision-trace: {reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: 写入 skill 指令和元数据**

用以下内容完整替换 `skills/dy-workflow/superpowers-decision-trace/SKILL.md`：

````markdown
---
name: superpowers-decision-trace
description: >-
  Use when brainstorming or revising a written spec where confirmed user
  decisions may already exist in an adjacent decision trace.
---

# Superpowers Decision Trace

## 合同

| 输入 | 输出 | 触发时机 | 不改变控制流的原因 |
| --- | --- | --- | --- |
| 当前 spec、相邻 trace、用户新确认的答案 | 唯一相邻 `<spec-stem>-decision-trace.md` | brainstorming 或 spec 修订期间，每次关键需求问题前 | 只复用和补充信息；任何失败后原版 brainstorming 继续 |

相邻 trace 是已确认决策的唯一持久事实来源。当前会话只能临时缓存已知信息，不能替代文件。

## 提问前

1. 每次关键需求问题前重读相邻 trace。
2. 同一主题已有明确决策时直接采用，禁止重复询问。
3. 可由已确认决策可靠推出的结论只用于当前工作，不写成确认决策。
4. 无法可靠推断时，一次只问一个问题。

先把 `HELPER` 解析为当前 `SKILL.md` 所在目录下的
`scripts/decision_trace.py` 绝对路径；不得假设当前工作目录是 skill 目录。读取命令：

```bash
python3 "$HELPER" read SPEC
```

trace 缺失时命令输出空四列表头和一条 warning，但不创建文件。读取失败时 helper 也只
输出一条 warning；不要为同一次失败再输出第二条 warning，也不得影响原版
brainstorming。

## 确认后

把用户短回答结合问题上下文改写为可独立理解的已确认决策。完整保留适用范围、条件、
例外、关键数值和明确否定项；不得保存完整问题、完整对话、agent 推理、session path、
turn ID 或其它会话元数据。

用户确认后立即调用 `record`。来源只能是 `用户明确回答`，或
`已批准 spec：SPEC#SECTION`。不得把可靠推论或未确认内容写入 trace。

```bash
python3 "$HELPER" record SPEC \
  --topic TOPIC --decision DECISION --source-kind user

python3 "$HELPER" record SPEC \
  --topic TOPIC --decision DECISION --source-kind approved-spec \
  --source-ref SPEC#SECTION
```

同主题新旧决策冲突时先向用户说明两者。只有用户决定采用新结论后才使用
`--replace-conflict`；trace 只保留最新有效结论，不保存历史版本。

## 过期与失败

读取后，逐条核对来源为 `已批准 spec：SPEC#SECTION` 的记录：相对路径以当前 spec
所在目录解析，并确认引用文件及对应 Markdown 章节仍存在。路径或章节不存在，或记录与
当前批准 spec 明确冲突时才判过期；不得使用 hash 或 mtime。过期记录只失去参考价值，
不删除、不自动覆盖，也不阻断原版流程。读取或写入失败时，可以继续使用本会话已确认的
信息避免当场重复询问，但必须保留 helper 的单条 warning，且不得声称该信息已持久保存。

不创建全局 trace，不创建 `specs/index.md`。trace、锁或 helper 状态不得成为 spec
批准、Plan 执行或任何原版 Superpowers 步骤的前置条件。发生规则冲突时服从原版
Superpowers；若必须改变原版规则才能实现，停止并询问用户。
````

用以下内容完整替换 `skills/dy-workflow/superpowers-decision-trace/agents/openai.yaml`：

```yaml
interface:
  display_name: "Superpowers Decision Trace"
  short_description: "Reuse confirmed decisions without repeat questions."
  default_prompt: "Use $superpowers-decision-trace while refining this written spec."

policy:
  allow_implicit_invocation: true
```

- [ ] **Step 6: 运行 GREEN 和现有回归测试**

运行：

```bash
python3 -m unittest \
  skills/dy-workflow/superpowers-decision-trace/scripts/test_decision_trace.py -v
python3 -m unittest \
  skills/dy-documentation/build-project-docs/scripts/test_check_relative_links.py -v
```

预期：Decision Trace 测试全部 PASS；现有 8 个链接测试仍 PASS。若失败，只修正实现或明确的测试错误，不放宽批准合同。

- [ ] **Step 7: 运行一次 enabled LLM smoke**

运行一次：

```bash
mktemp -d /private/tmp/superpowers-decision-trace-smoke.XXXXXX
```

预期：stdout 只有一个新建目录的绝对路径。把这次 stdout 记为 `SMOKE_DIR`，不要运行第二次
`mktemp`。使用 `apply_patch`，以该真实绝对路径分别创建 `feature-design.md` 和相邻的
`feature-design-decision-trace.md`；不得使用 shell 重定向写文件。文件内容固定为：

```markdown
# Feature 设计规格

## 已知范围

该功能仍在需求澄清阶段。
```

```markdown
| 决策主题 | 已确认决策 | 来源 | 确认日期 |
| --- | --- | --- | --- |
| 部署模式 | Extension V2 只在本地以轻量文件辅助能力运行，不增加网络服务。 | 用户明确回答 | 2026-08-13 |
```

调用 `collaboration.spawn_agent` 一次，参数固定为
`task_name="decision_trace_enabled_smoke"`、`fork_turns="none"`。发送前把下方消息中的
`ABSOLUTE_SMOKE_DIR` 替换成 `mktemp` stdout 的真实绝对路径；不得发送这个字面占位符，
也不得提供预期答案或本计划的评判标准。消息为：

```text
Use $superpowers-decision-trace at
skills/dy-workflow/superpowers-decision-trace/SKILL.md to continue requirement
clarification for ABSOLUTE_SMOKE_DIR/feature-design.md. Only output the next message to the user.
```

随后只调用 `collaboration.wait_agent` 等待该 agent 完成，不追加 follow-up prompt。

结果只分三态：重复询问已确认的部署模式为“发现明确越界”；直接采用该决策且不新增门禁为“未发现明显问题”；证据不足为“无法判断”。只在本 Task 最终 handoff 记录三态，不保存原文、会话路径、turn ID 或模型信息。

若发现明确越界，最多修改 `SKILL.md` 一次，并用同一 fixture/prompt 复查一次；同一次
受影响复查还必须重跑本 skill 的确定性测试一次，确认静态与 helper 合同未被修改破坏。
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
  skills/dy-workflow/superpowers-decision-trace
```

预期：`Skill is valid!`。validator 未运行不改变原版 Superpowers 流程；确定性单元测试仍是本 Task 的完成证据。

- [ ] **Step 9: 提交本 Task**

```bash
git add skills/dy-workflow/superpowers-decision-trace
git commit -m "feat(workflow): add decision trace assistant"
```

## 完成条件

- 四列 trace、来源校验、冲突保护、锁内重读、原子替换和单 warning CLI 均通过确定性测试。
- 已确认问题不重复询问；推论不伪装为确认决策；完整问题、对话和会话元数据不落盘。
- smoke 遵守一次采样及最多一次受影响复查上限；三态结果只记录风险，不控制提交或完成。
- 任何 helper/artifact 失败都不阻断或改变原版 Superpowers。
