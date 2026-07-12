# dayong-agent-skills

面向多种编码代理共享的可复用 skills 仓库。

本仓库采用开放 Agent Skills 布局：每个 skill 位于 `skills/` 下的独立目录，
并以 `SKILL.md` 作为唯一事实来源（source of truth）。

## 已包含的 Skills

安装后，代理会根据 `SKILL.md` 的 `description` 自动匹配场景并加载 skill（非系统硬 hook，偶发可能漏触发）。

| Skill | 默认触发场景 |
| --- | --- |
| `affected-path-review` | 任何 code review、PR review、review 子代理或 review comments 处理；将审查范围从 diff 扩展到完整行为路径 |
| `pr-comment-review` | 拉取、评估、处理或汇总 GitHub PR 评论与可执行的 review thread |
| `iterative-code-review` | 要求子代理/AI reviewer 审查本地改动，并由主代理循环修复直至通过 |
| `strict-api-extraction` | 从官方 API 文档站完整采集原始素材（`source/raw` + `source/snapshots`）并产出 `api-source-report.md`；coverage 不足时继续抓取，禁止猜测未文档化的 schema 元素。**依赖：** 需单独安装 `ego-browser`；可选 `firecrawl-scrape` / `firecrawl-map` |
| `openapi-from-sources` | 基于已有素材（含 strict-api-extraction 产出）校验是否足够生成 OpenAPI 3.x；strict NO-GO 时报告 4 个编号选项，用户选 example-fallback 后可从官方 example 生成带标注的 `schema/openapi.yaml`。**依赖：** 素材需已采集；下游可用 `api-client-generator` |

例外：若你明确要求 `diff-only review`，则只审查 diff，不会按 `affected-path-review` 扩展到完整行为路径。

## 仓库结构

```text
skills/
  <category>/
    <skill-name>/
      SKILL.md
      agents/
        openai.yaml
```

同一 category 下放置职责相关的 skills（如 `dy-code-review/`、`dy-api-extraction/`）。新增独立职责域时再建 category；否则放入已有 category。

`agents/openai.yaml` 为可选元数据文件；跨代理场景优先读取 `SKILL.md`。

## 安装

GitHub 仓库：`https://github.com/wangdayong228/dayong-agent-skills.git`

使用 `npx skills` 安装（适用于 Codex / Claude Code / Cursor）。

**一次安装全部：**

```bash
npx skills add wangdayong228/dayong-agent-skills --all -g -y
```

**安装单个 skill（`--skill` 写法）：**

```bash
npx skills add wangdayong228/dayong-agent-skills --skill affected-path-review -g -y
npx skills add wangdayong228/dayong-agent-skills --skill pr-comment-review -g -y
npx skills add wangdayong228/dayong-agent-skills --skill iterative-code-review -g -y
npx skills add wangdayong228/dayong-agent-skills --skill strict-api-extraction -g -y
npx skills add wangdayong228/dayong-agent-skills --skill openapi-from-sources -g -y
# strict-api-extraction 还需单独安装 ego-browser（必需）及 firecrawl 相关 skills（可选）
```

**安装单个 skill（`@` 简写）：**

```bash
npx skills add wangdayong228/dayong-agent-skills@affected-path-review -g -y
npx skills add wangdayong228/dayong-agent-skills@pr-comment-review -g -y
npx skills add wangdayong228/dayong-agent-skills@iterative-code-review -g -y
npx skills add wangdayong228/dayong-agent-skills@strict-api-extraction -g -y
npx skills add wangdayong228/dayong-agent-skills@openapi-from-sources -g -y
# strict-api-extraction 还需单独安装 ego-browser（必需）及 firecrawl 相关 skills（可选）
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
