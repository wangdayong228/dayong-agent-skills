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
| `iterative-code-review` | 主代理与子代理并行审查本地改动（传 context、默认同 LLM 跳过子代理）；合并 findings 后循环修复直至通过 |
| `strict-api-extraction` | 从官方 API 文档站完整采集原始素材（`pipeline/extract/raw/` + `pipeline/extract/snapshots/`）并产出 `pipeline/extract/report.md`；coverage 不足时继续抓取，禁止猜测未文档化的 schema 元素。**依赖：** 需单独安装 `ego-browser`；可选 `firecrawl-scrape` / `firecrawl-map` |
| `openapi-from-sources` | 基于已有素材（含 strict-api-extraction 产出）校验是否足够生成 OpenAPI 3.x；strict NO-GO 时报告 4 个编号选项，用户选 example-fallback 后可从官方 example 生成带标注的 `pipeline/openapi/openapi.yaml`。**依赖：** 素材需已采集；下游可用 `api-client-generator` 或 `typed-sdk-from-openapi`（Go） |
| `typed-sdk-from-openapi` | 输入可信且 pinned 的 OpenAPI 3.x 文档（优先 `pipeline/openapi/openapi.yaml`），先通过 preflight + 依赖检查，加载 `api-client-generator` 约束后先完成 retry policy 草案/审阅/确认 gate，再进入 Phase A/B 生成与封装，最终产出 2 层 Go SDK（`internal/generated/` + `pkg/client/`，`internal/transport/` 作为内部实现），并写入 `config/` 与 `tools/`；中间产物落到 `.sdkgen/`，NO-GO fail-fast 仅输出报告。**依赖：** `api-client-generator`；若存在 `retryable` 操作还需 `rate-limit-handler` |
| `small-feature-autopilot` | 用户要求小功能自动做到底、无需中途确认时（如「自动到底」「小功能」「无需确认」）；单子系统、低风险、无 breaking。超出门禁则停并建议完整 `brainstorming` → 审阅 → `writing-plans` 流程 |

> **BREAKING CHANGE：** `dy-api-extraction` 默认采用 `pipeline/` 布局，**不兼容**旧顶层路径：
> - 采集：`source/raw|snapshots` → `pipeline/extract/raw|snapshots`；报告 `docs/api-source-report.md` → `pipeline/extract/report.md`
> - OpenAPI：`schema/openapi.yaml` → `pipeline/openapi/openapi.yaml`；报告 `docs/openapi-readiness-report.md` → `pipeline/openapi/readiness-report.md`
> - Go SDK：`generated/` → `internal/generated/`；元数据 `sdk/` → `config/`；`scripts/regen.sh` → `tools/regen.sh`
> - 不再写入交付层 `schema/openapi.yaml` 副本；manifest 记录输入 spec 的 path + SHA256

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

同一 category 下放置职责相关的 skills（如 `dy-code-review/`、`dy-api-extraction/`、`dy-workflow/`）。新增独立职责域时再建 category；否则放入已有 category。

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
npx skills add wangdayong228/dayong-agent-skills --skill typed-sdk-from-openapi -g -y
npx skills add wangdayong228/dayong-agent-skills --skill small-feature-autopilot -g -y
# strict-api-extraction 还需单独安装 ego-browser（必需）及 firecrawl 相关 skills（可选）
# typed-sdk-from-openapi 依赖 api-client-generator 能力（需在运行环境中可用）
# 若存在 retryable / idempotent_key_required 操作，还需 rate-limit-handler（backoff）
```

**安装单个 skill（`@` 简写）：**

```bash
npx skills add wangdayong228/dayong-agent-skills@affected-path-review -g -y
npx skills add wangdayong228/dayong-agent-skills@pr-comment-review -g -y
npx skills add wangdayong228/dayong-agent-skills@iterative-code-review -g -y
npx skills add wangdayong228/dayong-agent-skills@strict-api-extraction -g -y
npx skills add wangdayong228/dayong-agent-skills@openapi-from-sources -g -y
npx skills add wangdayong228/dayong-agent-skills@typed-sdk-from-openapi -g -y
npx skills add wangdayong228/dayong-agent-skills@small-feature-autopilot -g -y
# strict-api-extraction 还需单独安装 ego-browser（必需）及 firecrawl 相关 skills（可选）
# typed-sdk-from-openapi 依赖 api-client-generator 能力（需在运行环境中可用）
# 若存在 retryable / idempotent_key_required 操作，还需 rate-limit-handler（backoff）
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
