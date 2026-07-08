# dayong-agent-skills

面向多种编码代理共享的可复用 skills 仓库。

本仓库采用开放 Agent Skills 布局：每个 skill 位于 `skills/` 下的独立目录，
并以 `SKILL.md` 作为唯一事实来源（source of truth）。

## 已包含的 Skills

- `affected-path-review`：将代码审查从“改动行”扩展到“完整受影响行为路径”。
- `pr-comment-review`：拉取、评估并处理 GitHub PR 评审意见。
- `iterative-code-review`：执行有边界的子代理评审循环，由主代理确认并修复有效问题。

## 仓库结构

```text
skills/
  <skill-name>/
    SKILL.md
    agents/
      openai.yaml
```

`agents/openai.yaml` 为可选元数据文件；跨代理场景优先读取 `SKILL.md`。

## 安装

GitHub 仓库：

- `https://github.com/wangdayong228/dayong-agent-skills.git`

使用 `npx skills` 安装（适用于 Codex / Claude Code / Cursor）：

```bash
npx skills add wangdayong228/dayong-agent-skills@affected-path-review
npx skills add wangdayong228/dayong-agent-skills@pr-comment-review
npx skills add wangdayong228/dayong-agent-skills@iterative-code-review
```

如需全局安装并自动确认，可加参数 `-g -y`：

```bash
npx skills add wangdayong228/dayong-agent-skills@affected-path-review -g -y
npx skills add wangdayong228/dayong-agent-skills@pr-comment-review -g -y
npx skills add wangdayong228/dayong-agent-skills@iterative-code-review -g -y
```

## 更新

```bash
npx skills update
```

## 编写规范

- 每个 skill 聚焦单一职责。
- 可复用流程统一写入 `SKILL.md`。
- `description` 保持简洁，突出触发条件。
- 仅在确有需要时添加脚本或大型参考资料。
- 不要提交密钥、本地日志、临时生成文件或会话转录。
