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
