# Superpowers Extension V2 集成与边界验证实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

本计划只能在三个独立 skill 均已实现后执行。

**Goal:** 为三个 V2 skill 增加仓库发现和独立安装说明，并用只读静态测试验证它们没有形成控制器、门禁或相互依赖。

**Architecture:** README 分别描述三个 skill；一个仓库级 `unittest` 读取源码、模板和 metadata，固定检查文件清单、headers、标准库依赖与 upstream 边界。没有运行时集成入口，测试结果不接入原版 Superpowers 控制流。

**Tech Stack:** 中文 Markdown、Python 3 标准库 AST、`unittest`。

**批准规格：** `docs/specs/2026-08-13-superpowers-extension-v2-design.md`

## Global Constraints

- 前置交付：`superpowers-decision-trace`、`superpowers-plan-assistant`、`superpowers-execution-timing` 三个 skill 已分别通过自身确定性测试。
- 本计划不创建 runtime controller、scheduler、registry、global index、自动触发链、共享配置或 Extension 状态。
- 三个 skill 独立安装、独立触发、独立失败；不互相调用，也不把兄弟 artifact 设为前置条件。
- 原版 Superpowers 独占所有工作流、批准、executor、dispatch、review/fix/retry、verification、finishing 和 Plan 准入/完成规则。
- 不读取、复制、迁移或兼容旧分支 `feat/superpowers-extension` 的任何材料。
- 确定性失败最多两轮针对性修复和受影响测试重跑；仍失败则记录并停止，不能声称完成。
- 人工边界只审阅一次；若发现批准 spec 的明确违反，最多统一修正一次，再只复查受影响边界一次。仍有问题则记录风险并停止，不继续循环。

## 文件与接口

- 创建：`scripts/test_superpowers_extension_v2_contract.py`
- 修改：`README.md`

**输入：** 三个已完成 skill 目录。

**输出：** 仓库发现/安装说明和只读静态合同测试；不产生运行时总入口。

---

### Task 1: 仓库集成合同与 README

- [x] **Step 1: 写入完整失败测试**

创建测试目录：

```bash
mkdir -p scripts
```

创建 `scripts/test_superpowers_extension_v2_contract.py`：

```python
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / "skills" / "dy-workflow"
README = ROOT / "README.md"

SKILL_NAMES = (
    "superpowers-decision-trace",
    "superpowers-plan-assistant",
    "superpowers-execution-timing",
)
SKILL_DIRS = {name: WORKFLOW_DIR / name for name in SKILL_NAMES}
HELPERS = (
    SKILL_DIRS["superpowers-decision-trace"] / "scripts" / "decision_trace.py",
    SKILL_DIRS["superpowers-execution-timing"] / "scripts" / "execution_timing.py",
)

TRACE_HEADER = (
    "| 决策主题 | 已确认决策 | 来源 | 确认日期 |\n"
    "| --- | --- | --- | --- |\n"
)
TIMING_HEADER = (
    "| Task | Round | Step | Start | End | Duration |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
)
ALLOWED_TOP_LEVEL_IMPORTS = {
    "__future__",
    "argparse",
    "contextlib",
    "dataclasses",
    "datetime",
    "fcntl",
    "json",
    "os",
    "pathlib",
    "re",
    "sys",
    "tempfile",
    "typing",
}
README_DESCRIPTIONS = {
    "superpowers-decision-trace": (
        "brainstorming/spec 修订期间复用相邻已确认决策；失败仅 warning"
    ),
    "superpowers-plan-assistant": (
        "writing-plans self-review 后筛出用户必须核实事项并提供技术/DAG findings；"
        "不形成门禁"
    ),
    "superpowers-execution-timing": (
        "原版 executor 开始后旁路记录自然 step 的真实耗时；不改变粒度或调度"
    ),
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(document: str) -> str:
    lines = document.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("SKILL.md must begin with YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("SKILL.md frontmatter is not closed") from exc
    return "\n".join(lines[1:end])


def assigned_string(path: Path, name: str) -> str:
    tree = ast.parse(read_text(path), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            result = ast.literal_eval(value)
            if not isinstance(result, str):
                raise AssertionError(f"{path}:{name} must be a string literal")
            return result
    raise AssertionError(f"{path} does not define {name}")


def top_level_imports(path: Path) -> tuple[set[str], list[str]]:
    imports: set[str] = set()
    relative: list[str] = []
    tree = ast.parse(read_text(path), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                relative.append(node.module or "<relative>")
            elif node.module:
                imports.add(node.module.split(".", 1)[0])
    return imports, relative


class SuperpowersExtensionV2ContractTest(unittest.TestCase):
    def test_three_v2_skill_directories_exist(self) -> None:
        for name, skill_dir in SKILL_DIRS.items():
            with self.subTest(skill=name):
                self.assertTrue(skill_dir.is_dir())

    def test_each_skill_has_matching_frontmatter_and_openai_prompt(self) -> None:
        for name, skill_dir in SKILL_DIRS.items():
            with self.subTest(skill=name):
                skill = read_text(skill_dir / "SKILL.md")
                metadata = read_text(skill_dir / "agents" / "openai.yaml")
                yaml = frontmatter(skill)
                match = re.search(r"(?m)^name:\s*([a-z0-9-]+)\s*$", yaml)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(1), name)
                self.assertIn("description:", yaml)
                self.assertIn("Use when", yaml)
                prompt = next(
                    (
                        line
                        for line in metadata.splitlines()
                        if line.lstrip().startswith("default_prompt:")
                    ),
                    None,
                )
                self.assertIsNotNone(prompt)
                self.assertIn(f"${name}", prompt)
                self.assertIn("allow_implicit_invocation: true", metadata)

    def test_each_skill_declares_its_stage_contract(self) -> None:
        for name, skill_dir in SKILL_DIRS.items():
            with self.subTest(skill=name):
                skill = read_text(skill_dir / "SKILL.md")
                for heading in (
                    "| 输入 ",
                    "| 输出 ",
                    "| 触发时机 ",
                    "| 不改变控制流的原因 ",
                ):
                    self.assertIn(heading, skill)

    def test_no_skill_invokes_a_sibling_extension_skill(self) -> None:
        for name, skill_dir in SKILL_DIRS.items():
            payload = read_text(skill_dir / "SKILL.md") + read_text(
                skill_dir / "agents" / "openai.yaml"
            )
            for sibling in set(SKILL_NAMES) - {name}:
                with self.subTest(skill=name, sibling=sibling):
                    self.assertNotIn(sibling, payload)

    def test_no_controller_scheduler_or_global_index_file_exists(self) -> None:
        expected_files = {
            "superpowers-decision-trace": {
                "SKILL.md",
                "agents/openai.yaml",
                "scripts/decision_trace.py",
                "scripts/test_decision_trace.py",
            },
            "superpowers-plan-assistant": {
                "SKILL.md",
                "agents/openai.yaml",
                "references/report-template.md",
                "scripts/test_plan_assistant_contract.py",
            },
            "superpowers-execution-timing": {
                "SKILL.md",
                "agents/openai.yaml",
                "scripts/execution_timing.py",
                "scripts/test_execution_timing.py",
            },
        }
        for name, skill_dir in SKILL_DIRS.items():
            actual = {
                path.relative_to(skill_dir).as_posix()
                for path in skill_dir.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            }
            with self.subTest(skill=name):
                self.assertEqual(actual, expected_files[name])

        self.assertFalse((ROOT / "scripts" / "superpowers_extension_v2.py").exists())
        self.assertFalse(
            (ROOT / "scripts" / "superpowers_extension_v2_controller.py").exists()
        )

    def test_plan_template_has_no_ready_hash_or_admission_state(self) -> None:
        template = read_text(
            SKILL_DIRS["superpowers-plan-assistant"]
            / "references"
            / "report-template.md"
        )
        for token in (
            "ready",
            "hash",
            "admission",
            "执行准入",
            "执行状态",
            "批准状态",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, template.casefold())

    def test_timing_header_has_exactly_six_columns(self) -> None:
        self.assertEqual(assigned_string(HELPERS[1], "TIMING_HEADER"), TIMING_HEADER)

    def test_trace_header_has_exactly_four_columns(self) -> None:
        self.assertEqual(assigned_string(HELPERS[0], "TRACE_HEADER"), TRACE_HEADER)

    def test_readme_lists_all_three_skills_and_both_install_forms(self) -> None:
        readme = read_text(README)
        for name, description in README_DESCRIPTIONS.items():
            with self.subTest(skill=name):
                self.assertEqual(readme.count(f"| `{name}` |"), 1)
                self.assertIn(description, readme)
                self.assertIn(
                    "npx skills add wangdayong228/dayong-agent-skills "
                    f"--skill {name} -g -y",
                    readme,
                )
                self.assertIn(
                    f"npx skills add wangdayong228/dayong-agent-skills@{name} -g -y",
                    readme,
                )
        self.assertIn("三个 V2 skill 独立安装、独立触发，互不调用", readme)
        self.assertIn("**V2 运行要求：**", readme)
        self.assertIn("只使用 Python 标准库", readme)
        self.assertIn("不需要第三方运行时依赖", readme)
        self.assertIn("缺少 `fcntl` 时写入失败只 warning", readme)

    def test_helpers_use_only_python_standard_library(self) -> None:
        for helper in HELPERS:
            with self.subTest(helper=helper):
                imports, relative = top_level_imports(helper)
                self.assertEqual(relative, [])
                self.assertEqual(imports - ALLOWED_TOP_LEVEL_IMPORTS, set())


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: 运行 RED**

运行：

```bash
python3 -m unittest scripts/test_superpowers_extension_v2_contract.py -v
```

预期：FAIL，明确原因是 README 尚未列出三个 V2 skill；若失败原因来自 Task 1-3 未完成，先停止并完成其前置计划，不要伪造 GREEN。

- [x] **Step 3: 精确更新 README**

在 `README.md` 的“已包含的 Skills”表中，紧跟 `codex-session-inspector` 行加入：

```markdown
| `superpowers-decision-trace` | brainstorming/spec 修订期间复用相邻已确认决策；失败仅 warning |
| `superpowers-plan-assistant` | writing-plans self-review 后筛出用户必须核实事项并提供技术/DAG findings；不形成门禁 |
| `superpowers-execution-timing` | 原版 executor 开始后旁路记录自然 step 的真实耗时；不改变粒度或调度 |

三个 V2 skill 独立安装、独立触发，互不调用；它们只提供旁路信息，不组成自动串联工作流，也不控制原版 Superpowers 是否继续。
```

在“安装单个 skill（`--skill` 写法）”代码块中，紧跟 `codex-session-inspector` 命令加入：

```bash
npx skills add wangdayong228/dayong-agent-skills --skill superpowers-decision-trace -g -y
npx skills add wangdayong228/dayong-agent-skills --skill superpowers-plan-assistant -g -y
npx skills add wangdayong228/dayong-agent-skills --skill superpowers-execution-timing -g -y
```

在“安装单个 skill（`@` 简写）”代码块中，紧跟 `codex-session-inspector` 命令加入：

```bash
npx skills add wangdayong228/dayong-agent-skills@superpowers-decision-trace -g -y
npx skills add wangdayong228/dayong-agent-skills@superpowers-plan-assistant -g -y
npx skills add wangdayong228/dayong-agent-skills@superpowers-execution-timing -g -y
```

在第二个安装代码块之后加入：

```markdown
**V2 运行要求：** `superpowers-decision-trace` 与 `superpowers-execution-timing` 使用
`python3` helper；helper 只使用 Python 标准库，不需要第三方运行时依赖。并发安全写入使用 POSIX `fcntl`；
缺少 `fcntl` 时写入失败只 warning，原版 Superpowers 继续。
`superpowers-plan-assistant` 没有 helper 运行时依赖。
```

不要把三个 skill 描述为一个自动串联 workflow，也不要增加单一“安装 Extension V2”控制入口。

- [x] **Step 4: 运行跨 skill GREEN 与全量确定性测试**

运行：

```bash
python3 -m unittest scripts/test_superpowers_extension_v2_contract.py -v
python3 -m unittest \
  skills/dy-workflow/superpowers-decision-trace/scripts/test_decision_trace.py \
  skills/dy-workflow/superpowers-plan-assistant/scripts/test_plan_assistant_contract.py \
  skills/dy-workflow/superpowers-execution-timing/scripts/test_execution_timing.py \
  skills/dy-documentation/build-project-docs/scripts/test_check_relative_links.py -v
```

预期：跨 skill 合同全部 PASS；三个新测试文件全部 PASS；现有 8 个链接测试仍 PASS。

同一确定性失败最多两轮针对性修复，只重跑受影响测试；仍失败时记录命令和剩余问题并停止，不全量循环。

- [x] **Step 5: 执行一次有界人工边界审阅**

逐项对照批准 spec，只审阅一次并记录：

```text
三个 skill 都明确列出输入、输出、触发时机和不改变控制流的原因
没有 extension artifact 被用作 upstream 准入或完成条件
没有 executor 选择、Task 重分粒度、scheduler 或 wave 调度
Plan review 恰好为一次初查、最多一次修正、一次受影响复查
需要用户核实只含四类权限事项，技术 findings 不混入
timing 每行只来自自然 step，正文只有六列
trace 决策可独立理解且不存完整问题、对话或会话元数据
所有 failure、review 和 smoke 循环都有批准 spec 中的退出上限
没有读取或继承旧分支材料
```

若发现明确违反，最多统一修正一次，再只复查受影响边界一次。发生修正时，按改动路径
只执行下面对应命令一次；不得全量重跑：

```bash
# 修改 Decision Trace 时
python3 -m unittest skills/dy-workflow/superpowers-decision-trace/scripts/test_decision_trace.py -v

# 修改 Plan Assistant 时
python3 -m unittest skills/dy-workflow/superpowers-plan-assistant/scripts/test_plan_assistant_contract.py -v

# 修改 Execution Timing 时
python3 -m unittest skills/dy-workflow/superpowers-execution-timing/scripts/test_execution_timing.py -v

# 修改上述任一 skill、README 或集成合同时
python3 -m unittest scripts/test_superpowers_extension_v2_contract.py -v
```

只运行实际受影响的 skill 命令，并在任一 artifact 改动后运行跨 skill 合同。复查或测试仍
有问题时记录剩余风险并停止，不提交、不声称完成。该审阅不产生 READY/hash 或执行 gate。
若修正必须改变原版 Superpowers 规则，立即停止并询问用户。

- [x] **Step 6: 运行原版完成验证链**

依次使用：

```text
pre-verification-check
verification-before-completion
consistency-check
post-verification-check
```

这是原版 Superpowers 的既有完成流程，不由 Extension V2 增加、跳过或重复。不得根据 report、trace 或 timing 状态改变该流程。

- [x] **Step 7: 提交集成改动**

```bash
git status --short -- \
  README.md scripts/test_superpowers_extension_v2_contract.py \
  skills/dy-workflow/superpowers-decision-trace \
  skills/dy-workflow/superpowers-plan-assistant \
  skills/dy-workflow/superpowers-execution-timing
git add README.md scripts/test_superpowers_extension_v2_contract.py \
  skills/dy-workflow/superpowers-decision-trace \
  skills/dy-workflow/superpowers-plan-assistant \
  skills/dy-workflow/superpowers-execution-timing
git commit -m "test(workflow): add extension integration contract"
```

预期：`git status --short` 同时列出已跟踪和未跟踪的 README、集成测试，以及本次人工
边界修正实际影响的 V2 skill 路径；提交包含所列全部路径。出现其它路径时停止并核对，
不扩大提交范围。

## 完成条件

- README 分别说明三个 skill 和两种单独安装方式，不存在总入口。
- 静态合同锁定三个 V2 skill 自身的精确文件清单、四/六列表头、标准库范围和互不调用，
  不限制仓库未来新增其它独立 skill。
- 只有全部确定性测试通过才能声称本计划完成；若批准的两轮修复用尽后仍失败，则记录
  剩余问题并停止，明确不得声称完成。
- 人工边界审阅及复查不超过批准次数，且不创建新的执行状态或门禁。
