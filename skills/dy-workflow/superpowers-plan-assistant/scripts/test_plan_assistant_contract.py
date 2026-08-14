from pathlib import Path
import re
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = SKILL_ROOT / "SKILL.md"
TEMPLATE_PATH = SKILL_ROOT / "references" / "report-template.md"
METADATA_PATH = SKILL_ROOT / "agents" / "openai.yaml"

REPORT_SECTIONS = [
    "## 需要用户核实",
    "## Plan Task 辅助分析",
    "## Plan 技术检查",
    "## DAG 与并行建议",
]
USER_COLUMNS = [
    "类别",
    "Plan 位置",
    "不能由 agent 技术决定的原因",
    "需要用户回答的问题",
]


class PlanAssistantContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")
        cls.template = TEMPLATE_PATH.read_text(encoding="utf-8")
        cls.metadata = METADATA_PATH.read_text(encoding="utf-8")

    def test_frontmatter_description_names_trigger_only(self) -> None:
        expected = (
            "description: >-\n"
            "  Use when a written implementation Plan has completed its original\n"
            "  writing-plans self-review and needs technical analysis before execution."
        )
        self.assertIn(expected, self.skill)

    def test_report_path_is_adjacent_and_deterministic(self) -> None:
        self.assertIn(
            "`feature-plan.md`，报告路径必须是\n"
            "`feature-plan-plan-auto-review-report.md`",
            self.skill,
        )

    def test_report_sections_are_present_once_and_in_order(self) -> None:
        actual = re.findall(r"^## .+$", self.template, flags=re.MULTILINE)
        self.assertEqual(actual, REPORT_SECTIONS)

    def test_user_section_has_only_four_authority_categories(self) -> None:
        expected = (
            "用户权限类别仅限：`产品意图`、`风险授权`、`范围变化`、"
            "`已确认决策冲突`。"
        )
        self.assertEqual(self.skill.count(expected), 1)

    def test_user_item_schema_has_exact_location_reason_and_one_question(self) -> None:
        self.assertIn("| " + " | ".join(USER_COLUMNS) + " |", self.template)
        self.assertIn(
            "每项必须写出具体的 Plan Task、Step 或章节位置、不能由 agent 技术决定的原因，并且\n"
            "只提出一个明确问题。",
            self.skill,
        )

    def test_user_section_excludes_technical_findings(self) -> None:
        self.assertIn(
            "技术 findings、Task 分析细节和并行建议不得进入“需要用户核实”。",
            self.skill,
        )
        self.assertIn("正常审阅只引导用户阅读“需要用户核实”", self.skill)

    def test_template_has_no_ready_hash_or_execution_status(self) -> None:
        for token in (
            "READY",
            "NOT READY",
            "hash",
            "执行准入",
            "执行状态",
            "完成状态",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, self.template)

    def test_task_analysis_prioritizes_independence_over_duration(self) -> None:
        self.assertIn(
            "是否能够独立实现、测试和审阅是 Task 边界的首要\n"
            "依据；预计时长只作提示。",
            self.skill,
        )
        self.assertIn(
            "分析只是对原版 `writing-plans` 的建议，不强制改变 Plan\n"
            "格式或 Task dispatch 粒度。",
            self.skill,
        )

    def test_review_loop_is_one_initial_one_fix_one_affected_recheck(self) -> None:
        self.assertIn(
            "硬上限：一次初查、最多一次统一修正、一次受影响复查；没有第二轮修正或复查。",
            self.skill,
        )
        self.assertIn(
            "修正后只复查受修改影响的 Task、接口和直接依赖一次，不重新全量检查。",
            self.skill,
        )

    def test_remaining_findings_exit_without_more_loops(self) -> None:
        self.assertIn(
            "复查后仍有\n问题时，把剩余 findings 写入报告并退出，不再修改、不再复查。",
            self.skill,
        )

    def test_dag_never_selects_executor_or_changes_dispatch_granularity(self) -> None:
        for contract in (
            "不得选择或替换 executor",
            "不得改变 Task dispatch 粒度",
            "不自行调度\nTask",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, self.skill)

    def test_worktree_wave_requires_original_parallel_decision(self) -> None:
        self.assertIn(
            "只有原版 executor 已明确决定并行执行时，才可以给出 worktree 或 wave 建议",
            self.skill,
        )
        self.assertIn(
            "仅仅\n分析出 Task 理论上可并行不满足此条件。",
            self.skill,
        )

    def test_no_extra_review_integration_verification_gate(self) -> None:
        self.assertIn(
            "不得新增 review、integration 或 verification\nTask 或门禁。",
            self.skill,
        )

    def test_missing_stale_or_unwritable_report_is_warning_only(self) -> None:
        self.assertIn(
            "报告缺失、过期、不可读或写入失败都不得阻断、暂停或改变原版流程。",
            self.skill,
        )
        self.assertIn(
            "每个失败事件在\n本次调用中只输出一条 warning，不重试。",
            self.skill,
        )

    def test_incomplete_original_self_review_warns_and_returns(self) -> None:
        self.assertIn(
            "若不能确认，只输出一条\n"
            "`WARNING: superpowers-plan-assistant 需要等待原版 writing-plans 完成 self-review`",
            self.skill,
        )
        self.assertIn(
            "立即把控制权交还原版 `writing-plans`；不创建或更新报告",
            self.skill,
        )
        self.assertIn("也不把本次退出解释为\nPlan 未通过。", self.skill)

    def test_report_staleness_does_not_use_hash_or_mtime(self) -> None:
        self.assertIn(
            "既有报告仅在引用的 Plan Task 或章节不存在，或者内容与当前 Plan 明确冲突时视为\n"
            "过期；过期报告只失去参考价值。",
            self.skill,
        )
        self.assertIn("不得用 hash 或文件修改时间判断过期。", self.skill)

    def test_original_superpowers_retains_all_control(self) -> None:
        self.assertIn(
            "原版 Superpowers\n"
            "始终独占工作流顺序、用户批准、executor、Task dispatch、review、fix、retry、\n"
            "verification 和 branch finishing。",
            self.skill,
        )
        self.assertIn(
            "发生冲突时立即服从原版规则并停止相冲突的\nExtension 动作",
            self.skill,
        )

    def test_metadata_supports_explicit_and_implicit_invocation(self) -> None:
        self.assertIn('display_name: "Superpowers Plan Assistant"', self.metadata)
        self.assertIn('default_prompt: "Use $superpowers-plan-assistant ', self.metadata)
        self.assertIn("allow_implicit_invocation: true", self.metadata)


if __name__ == "__main__":
    unittest.main()
