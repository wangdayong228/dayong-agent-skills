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

    def test_same_text_user_reconfirmation_refreshes_provenance(self) -> None:
        approved = dt.Decision(
            "部署模式",
            "只使用本地文件。",
            dt.APPROVED_PREFIX + "api.v2-design.md#部署",
            date(2026, 8, 13),
        )
        confirmed = dt.Decision(
            "部署模式", "只使用本地文件。", dt.USER_SOURCE, date(2026, 8, 14)
        )
        dt.record_decision(self.design, approved)
        self.assertEqual(dt.record_decision(self.design, confirmed), "replaced")
        self.assertEqual(dt.load_decisions(self.design), [confirmed])

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
