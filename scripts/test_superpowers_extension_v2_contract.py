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
