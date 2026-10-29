---
name: global-conventions
description: Use when starting any conversation — establishes mandatory skill trigger rules, workflow constraints
---

# 全局行为准则

## 语言风格

在不丢失语义的前提下，表达要直接、通顺、简洁，避免绕弯和重复。

## Superpowers 文档语言规则

使用 superpowers 创建 spec、 plan、report 文档时，必须使用中文。

## Spec 技术栈确认

- 制定 spec 时，必须一次列出本次技术栈，说明用途、推荐理由和必要的版本要求，标明沿用或新增、已确认或待确认。有重要取舍时，附上备选方案及影响。
- 请用户一次确认所有待确认项；已确认项只列出，不再询问。
- 将确认结果写入 spec，关键选型确认后再写 Plan。后续有调整，只集中确认变更项。

## Plan 边界规则

计划只落实已确认设计，不重复 spec、不预实现。耗时超 30 分钟或文档超 500 行时，立即检查是否扩张范围、重复审查或偏离目标；完成后停止，未经明确确认不得实施。

## 正确性优先

- 调查、设计和实现必须首先保证正确性；“更简单”只能在多个方案同样正确时作为取舍依据，不得为了降低复杂度接受不正确、不完整或无法证明的行为。
- 在判定时序、事务、状态转换和跨系统行为前，必须先核对已批准设计、绑定源码及可复现证据；若观测结果违反已证明的时序或不变量，必须按错误或完整性异常 fail-closed 处理，不得为了方便将其解释为正常竞态。
- 无法证明某个方案正确时，必须继续调查或请求裁决，不得凭假设选择“看起来更简单”的方案。

## 用户界面与交互

涉及 Web、App、桌面程序或 CLI 中面向用户的界面、文案或操作流程时，**必须先读取并遵守** [用户界面与交互规范](references/user-interface-and-interaction.md)，再按平台与场景调用技能；混合任务仅应用于相关部分，无用户交互变化的任务不加载该参考文件。

## 技能触发规则

以下技能在对应场景**必须调用**，无需等用户手动指定：

| 场景 | 技能 | 排除（不触发） |
|------|------|--------------|
| 执行 superpowers plan 全部任务后 | `consistency-check` | per-task / 执行中途 / 文档撰写过程中 |
| spec/plan 等文档已写完、请用户批准或 review 之前 | `consistency-check` | 撰写过程中、文件未落盘或未自检 |
| Superpowers Plan 全部 Task 完成后的 final/whole-branch code review | `affected-path-review` | per-task / task-reviewer / plan/spec review / review comments / 验证链 / finishing / 未 opt-in 的 iterative-code-review |
| 编写、修改或审查代码中的错误/异常/失败信息 | `fail-fast-with-evidence` | 未触及错误信息的改动；已写清失败点与实际值的既有错误、仅为统一形式而改写 |
| 使用 Go 设计或实现后端 HTTP 服务 | `logrus-http-response` | |
| Go Gin REST API 编写、修改或同步 Swagger 2.0 / swag 文档 | `gin-swagger` | 上游 OpenAPI 副本与 codegen 客户端；`openapi-from-sources` / `typed-sdk-from-openapi`；非 Gin / 非 swaggo |

验证仍走 Superpowers 原有步骤（计划内验证、`finishing-a-development-branch`，以及 `verification-before-completion` 自身的触发）。这张表不取消验证，也不再强制重跑 `pre-verification-check` → `verification-before-completion`。Plan 收尾时沿用已有验证结果再做 `consistency-check`；文档送审时写完并自检后直接做 `consistency-check`。

**brainstorming 排除判断：** 这个操作有没有设计选择空间？没有 = 跳过，直接执行。

## brainstorming 批准闸门

是否进入 brainstorming 按上面的排除判断。一旦进入：

- 未获用户明确批准，不得开始实现。“主动推进、减少确认”不能成为跳过方案讨论或批准的理由。
- spec 粒度随复杂度变化：
  - 单文件、取舍很少：可以在对话里给出简短方案（目标、方案、影响范围），用户确认即可，不必落盘。
  - 跨模块、有重要取舍、涉及资金、权限、数据迁移等高风险：必须写书面 spec 后送审。
- 只有多步骤实现才需要 `writing-plans`，单步改动批准后直接实现。
- 例外：用户在本次请求中明确授权跳过确认（如“直接做”、`small-feature-autopilot`）。

## 记忆

重要讨论结论、用户偏好、纠正过的错误行为，主动建议保存到记忆。
