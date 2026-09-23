---
name: global-conventions
description: Use when starting any conversation — establishes mandatory skill trigger rules, workflow constraints
---

# 全局行为准则

## Superpowers 文档语言规则

使用 superpowers 创建 spec、 plan、report 文档时，必须使用中文。

## Plan 边界规则

计划只落实已确认设计，不重复 spec、不预实现。耗时超 30 分钟或文档超 500 行时，立即检查是否扩张范围、重复审查或偏离目标；完成后停止，未经明确确认不得实施。

## 正确性优先

- 调查、设计和实现必须首先保证正确性；“更简单”只能在多个方案同样正确时作为取舍依据，不得为了降低复杂度接受不正确、不完整或无法证明的行为。
- 在判定时序、事务、状态转换和跨系统行为前，必须先核对已批准设计、绑定源码及可复现证据；若观测结果违反已证明的时序或不变量，必须按错误或完整性异常 fail-closed 处理，不得为了方便将其解释为正常竞态。
- 无法证明某个方案正确时，必须继续调查或请求裁决，不得凭假设选择“看起来更简单”的方案。

## 技能触发规则

以下技能在对应场景**必须调用**，无需等用户手动指定：

| 场景 | 技能 | 排除（不触发） |
|------|------|--------------|
| 执行 superpowers plan 全部任务后 | `consistency-check` | per-task / 执行中途 / 文档撰写过程中 |
| spec/plan 等文档已写完、请用户批准或 review 之前 | `consistency-check` | 撰写过程中、文件未落盘或未自检 |
| Superpowers Plan 全部 Task 完成后的 final/whole-branch code review | `affected-path-review` | per-task / task-reviewer / plan/spec review / review comments / 验证链 / finishing / 未 opt-in 的 iterative-code-review |
| 编写、修改或审查代码中的错误/异常/失败信息 | `fail-fast-with-evidence` | 未触及错误信息的改动；已写清失败点与实际值的既有错误、仅为统一形式而改写 |
| 使用 Go 设计或实现后端 HTTP 服务 | `logrus-http-response` | |

验证仍走 Superpowers 原有步骤（计划内验证、`finishing-a-development-branch`，以及 `verification-before-completion` 自身的触发）。这张表不取消验证，也不再强制重跑 `pre-verification-check` → `verification-before-completion`。Plan 收尾时沿用已有验证结果再做 `consistency-check`；文档送审时写完并自检后直接做 `consistency-check`。

**brainstorming 排除判断：** 这个操作有没有设计选择空间？没有 = 跳过，直接执行。

## 记忆

重要讨论结论、用户偏好、纠正过的错误行为，主动建议保存到记忆。
