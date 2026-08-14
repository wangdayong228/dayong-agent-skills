# Superpowers Extension V2 Plan Assistant 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

本计划只实现 Plan Assistant，不得自行调度另外两个 Extension skill。

**Goal:** 实现一个非阻断 Plan Assistant，由 agent 检查完整技术 Plan，并把用户必须核实的少量权限事项集中在报告首节。

**Architecture:** `SKILL.md` 定义一次初查、最多一次统一技术修正和一次受影响复查；固定 Markdown 模板约束报告结构。没有程序化 reviewer、Plan 状态或 gate，技术判断仍由 agent 完成。

**Tech Stack:** 中文 Markdown、Agent Skills、Python 3 标准库静态合同测试、`unittest`。

**批准规格：** `docs/specs/2026-08-13-superpowers-extension-v2-design.md`

## Global Constraints

- 原版 Superpowers 独占工作流顺序、用户批准、executor、Task dispatch、review/fix/retry、verification、finishing 以及 Plan 准入和完成条件。
- 报告只增加信息；缺失、过期、不可读或写入失败只 warning 一次，不暂停、不重试、不阻断原版流程。
- “需要用户核实”只含产品意图、风险授权、范围变化和已确认决策冲突；技术 findings 不交给用户逐项核实。
- 不读取、复制、迁移或兼容旧分支 `feat/superpowers-extension` 的任何材料。
- 不创建 READY、hash、admission、executor、scheduler、额外 review/integration/verification Task 或新批准状态。
- 确定性失败最多两轮针对性修复和受影响测试重跑；仍失败则记录并停止，不能声称完成。
- 用户于 2026-08-14 再确认 LLM 行为不可控且不得成为交付门禁，因此不运行要求“必须
  失败”的无-skill LLM baseline；确定性测试提供 RED，只运行一次非门禁 enabled smoke。
  明确越界最多一次修改和一次受影响复查，不做 5/5 或“测到满意”。

## 文件与接口

**创建文件：**

- `skills/dy-workflow/superpowers-plan-assistant/SKILL.md`
- `skills/dy-workflow/superpowers-plan-assistant/agents/openai.yaml`
- `skills/dy-workflow/superpowers-plan-assistant/references/report-template.md`
- `skills/dy-workflow/superpowers-plan-assistant/scripts/test_plan_assistant_contract.py`

**输入：** 已完成原版 `writing-plans` self-review 的 Plan、对应批准 spec、可用但非必需的相邻 decision trace。

**输出：** 唯一相邻 `<plan-stem>-plan-auto-review-report.md`。

**报告章节：** `需要用户核实`、`Plan Task 辅助分析`、`Plan 技术检查`、`DAG 与并行建议`，顺序固定。

---

### Task 1: Plan Assistant skill、模板与静态合同

- [ ] **Step 1: 使用官方 initializer 创建 scaffold**

运行：

```bash
python3 /Users/dayong/.agents/skills/.system/skill-creator/scripts/init_skill.py \
  superpowers-plan-assistant \
  --path skills/dy-workflow \
  --resources scripts,references \
  --interface 'display_name=Superpowers Plan Assistant' \
  --interface 'short_description=Surface user decisions and review technical Plan risks.' \
  --interface 'default_prompt=Use $superpowers-plan-assistant after the original writing-plans self-review.'
```

预期：创建 skill、`scripts/`、`references/` 和 metadata scaffold；不使用 `--examples`。

- [ ] **Step 2: 写入完整失败测试**

创建 `skills/dy-workflow/superpowers-plan-assistant/scripts/test_plan_assistant_contract.py`：

```python
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
```

- [ ] **Step 3: 运行 RED**

运行：

```bash
python3 -m unittest \
  skills/dy-workflow/superpowers-plan-assistant/scripts/test_plan_assistant_contract.py -v
```

预期：FAIL，因为 scaffold 尚无模板和合同语句；不能通过删断言或放宽边界获得 GREEN。

- [ ] **Step 4: 写入固定报告模板**

创建 `skills/dy-workflow/superpowers-plan-assistant/references/report-template.md`：

```markdown
# Plan 自动审阅报告

## 需要用户核实

<!--
无事项时只保留“无”并删除空表。
有事项时删除“无”并填写表格。
类别只能是：产品意图、风险授权、范围变化、已确认决策冲突。
-->
无

| 类别 | Plan 位置 | 不能由 agent 技术决定的原因 | 需要用户回答的问题 |
| --- | --- | --- | --- |

## Plan Task 辅助分析

| Task | 职责与验收目标 | 前后依赖与接口 | 文件或共享状态写入冲突 | 独立实现、测试和审阅结论 | 时长提示 |
| --- | --- | --- | --- | --- | --- |

## Plan 技术检查

<!--
初查没有技术 finding 时只保留“未发现技术问题。”并删除空表。
存在已修正或剩余 finding 时删除该句并填写表格。
-->
未发现技术问题。

| 严重度 | Plan 位置 | Finding 与影响 | 建议修正 |
| --- | --- | --- | --- |

## DAG 与并行建议

### 可并行 Task

无

| Task 组合 | 原因 |
| --- | --- |

### 必须串行 Task

无

| Task 顺序 | 原因 |
| --- | --- |

### Worktree/Wave 建议

不适用：原版 executor 未决定并行。
```

- [ ] **Step 5: 写入 skill 指令与元数据**

用以下内容完整替换 `skills/dy-workflow/superpowers-plan-assistant/SKILL.md`：

```markdown
---
name: superpowers-plan-assistant
description: >-
  Use when a written implementation Plan has completed its original
  writing-plans self-review and needs technical analysis before execution.
---

# Superpowers Plan Assistant

## 定位

本 skill 在原版 `writing-plans` 完成自身 self-review 后提供旁路分析。原版
Superpowers 指既有的 writing-plans、executor、review、verification 和 finishing
规则；本 skill 只增加信息，不批准或拒绝 Plan，也不增加原版状态机。

## 输入、输出与触发

| 输入 | 输出 | 触发时机 | 不改变控制流的原因 |
| --- | --- | --- | --- |
| 已完成原版 self-review 的 Plan、对应已批准 spec、可用但非必需的相邻 decision trace | 与 Plan 相邻的单一 `plan-auto-review-report` | 原版 `writing-plans` 完成 self-review 后 | 报告和 findings 只供参考，不决定暂停、批准、executor、dispatch、review、verification 或 finishing |

若 Plan 为 `feature-plan.md`，报告路径必须是
`feature-plan-plan-auto-review-report.md`。

## 进入条件

先确认原版 `writing-plans` 已完成其自身 self-review。若不能确认，只输出一条
`WARNING: superpowers-plan-assistant 需要等待原版 writing-plans 完成 self-review`，
立即把控制权交还原版 `writing-plans`；不创建或更新报告，也不把本次退出解释为
Plan 未通过。

读取完整 Plan、对应已批准 spec，以及存在且可用的相邻 decision trace。不得调用其它
Extension skill。Plan 或 spec 不可读时，warning 一次并返回原版流程；trace 缺失、
过期或不可读时，warning 一次并继续，不把 trace 当作前置条件。

## 有界分析

### 1. 一次初查

完整检查 Plan 一次，覆盖已批准 spec 的覆盖和范围、技术正确性、Task 间接口一致性、
路径和命令是否存在及可执行、测试能否按 Plan 运行，以及明显的文件、共享状态或行为冲突。

同一遍检查中逐个 Task 记录职责与验收目标、前后依赖与接口、文件或共享状态写入冲突，
以及能否独立实现、测试和审阅。是否能够独立实现、测试和审阅是 Task 边界的首要
依据；预计时长只作提示。分析只是对原版 `writing-plans` 的建议，不强制改变 Plan
格式或 Task dispatch 粒度。

### 2. 筛选用户事项

用户权限类别仅限：`产品意图`、`风险授权`、`范围变化`、`已确认决策冲突`。

每项必须写出具体的 Plan Task、Step 或章节位置、不能由 agent 技术决定的原因，并且
只提出一个明确问题。技术 findings、Task 分析细节和并行建议不得进入“需要用户核实”。
没有用户事项时写“无”。

正常审阅只引导用户阅读“需要用户核实”；后三个技术章节由 agent 处理和追溯，不要求
用户逐项核实。是否暂停或取得用户决定仍由原版 Superpowers 决定，本摘要不新增门禁。

### 3. 一次修正和一次局部复查

对不涉及上述四类用户事项、不会扩大已批准 spec 范围、且技术上结论明确的问题，在
原版规则允许当前 agent 修改 Plan 时，最多统一修正 Plan 一次。原版规则不允许修改时，
保留 finding，不绕过原版规则。

修正后只复查受修改影响的 Task、接口和直接依赖一次，不重新全量检查。复查后仍有
问题时，把剩余 findings 写入报告并退出，不再修改、不再复查。

硬上限：一次初查、最多一次统一修正、一次受影响复查；没有第二轮修正或复查。

### 4. DAG 与并行建议

根据 Task 依赖、接口稳定性、文件和共享状态冲突，分别列出可并行 Task、必须串行
Task 及原因。不得选择或替换 executor，不得改变 Task dispatch 粒度，不自行调度
Task。

只有原版 executor 已明确决定并行执行时，才可以给出 worktree 或 wave 建议；仅仅
分析出 Task 理论上可并行不满足此条件。不得新增 review、integration 或 verification
Task 或门禁。

## 写入报告

使用 `references/report-template.md`，保留四个二级章节及其顺序。生成报告时删除模板
注释和不适用的“无”或空表。技术检查没有 finding 时写“未发现技术问题”；存在 finding
时写明 Plan 位置、影响和建议修正，不要求用户核实技术细节。

既有报告仅在引用的 Plan Task 或章节不存在，或者内容与当前 Plan 明确冲突时视为
过期；过期报告只失去参考价值。不得用 hash 或文件修改时间判断过期。

## 非阻断边界

报告缺失、过期、不可读或写入失败都不得阻断、暂停或改变原版流程。每个失败事件在
本次调用中只输出一条 warning，不重试。

报告不包含执行准入或完成状态，findings 不控制 Plan 是否可以执行。原版 Superpowers
始终独占工作流顺序、用户批准、executor、Task dispatch、review、fix、retry、
verification 和 branch finishing。发生冲突时立即服从原版规则并停止相冲突的
Extension 动作。若任何建议可能需要改变原版规则，立即停止该项并先询问用户，不自行实施。
```

用以下内容完整替换 `skills/dy-workflow/superpowers-plan-assistant/agents/openai.yaml`：

```yaml
interface:
  display_name: "Superpowers Plan Assistant"
  short_description: "Surface user decisions and review technical Plan risks."
  default_prompt: "Use $superpowers-plan-assistant after the original writing-plans self-review to analyze this implementation Plan."

policy:
  allow_implicit_invocation: true
```

- [ ] **Step 6: 运行 GREEN**

运行：

```bash
python3 -m unittest \
  skills/dy-workflow/superpowers-plan-assistant/scripts/test_plan_assistant_contract.py -v
```

预期：全部 PASS。若失败，只修正内容或明确的测试错误，不放宽 upstream 边界。

- [ ] **Step 7: 运行一次 enabled LLM smoke**

运行一次：

```bash
mktemp -d /private/tmp/superpowers-plan-assistant-smoke.XXXXXX
```

预期：stdout 只有一个新建目录的绝对路径。把这次 stdout 记为 `SMOKE_DIR`，不要运行第二次
`mktemp`。使用 `apply_patch`，以该真实绝对路径创建以下固定 `feature-design.md`；不得
使用 shell 重定向写文件：

```markdown
# Feature 设计规格

**状态：** 已批准

## 范围

保持公开 API 向后兼容。使用仓库现有 Python 工具链。
```

再使用 `apply_patch` 在同一真实目录创建以下固定 `feature-plan.md`：

```markdown
# Feature Implementation Plan

## Task 1

- 运行 `python3 scripts/missing_check.py` 验证输入。

## Task 2

- 删除旧公开 API，并只保留不兼容的新 API。
```

fixture 表达两个问题：不存在的命令是纯技术 finding；breaking API 是未经批准的范围变化和风险事项。

调用 `collaboration.spawn_agent` 一次，参数固定为
`task_name="plan_assistant_enabled_smoke"`、`fork_turns="none"`。发送前把下方消息中的两个
`ABSOLUTE_SMOKE_DIR` 都替换成 `mktemp` stdout 的同一真实绝对路径；不得发送字面占位符，
只给原始 artifacts，不泄漏评判答案。消息为：

```text
Use $superpowers-plan-assistant at
skills/dy-workflow/superpowers-plan-assistant/SKILL.md to review
ABSOLUTE_SMOKE_DIR/feature-plan.md against ABSOLUTE_SMOKE_DIR/feature-design.md. The original
writing-plans self-review for this Plan is complete. Generate the adjacent report.
```

随后只调用 `collaboration.wait_agent` 等待该 agent 完成，不追加 follow-up prompt。

结果只分三态。出现任一情况为“发现明确越界”：要求用户核实纯技术 finding；遗漏 breaking 范围/风险；声称 READY/NOT READY；选择 executor；增加 review、integration 或 verification gate。正确区分并保持报告非阻断为“未发现明显问题”；证据不足为“无法判断”。只在本 Task 最终 handoff 记录三态，不保存原文、会话路径、turn ID 或模型信息。

若发现明确越界，最多修改 `SKILL.md` 一次，并用同一 fixture/prompt 复查一次；同一次
受影响复查还必须重跑本 skill 的确定性合同测试一次。确定性测试失败时停止，不提交、
不声称完成。LLM 复查后仍越界或无法判断时，只记录三态和剩余风险并结束本 smoke，
不再修改或采样；LLM 结果本身不控制提交或完成。措辞或格式差异不触发修改或重跑。

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
  skills/dy-workflow/superpowers-plan-assistant
```

预期：`Skill is valid!`。validator 未运行不改变原版 Superpowers 流程；静态合同测试仍是本 Task 的完成证据。

- [ ] **Step 9: 提交本 Task**

```bash
git add skills/dy-workflow/superpowers-plan-assistant
git commit -m "feat(workflow): add plan analysis assistant"
```

## 完成条件

- 用户首节只含四类权限事项，技术 findings 不混入。
- agent 一次初查、最多一次统一技术修正、一次受影响复查，然后保留剩余 findings 并退出。
- DAG 只给依赖建议，不选择 executor、不改 dispatch、不新增 gate。
- smoke 三态结果只记录风险，不控制提交或完成。
- 任何报告或输入 artifact 失败都不阻断或改变原版 Superpowers。
