---
name: global-conventions
description: Use when starting any conversation — establishes mandatory skill trigger rules, workflow constraints, and memory conventions inherited from CLAUDE.md
---

# 全局行为准则

## 技能触发规则

以下技能在对应场景**必须调用**，无需等用户手动指定：

| 场景 | 技能 | 排除（不触发） |
|------|------|--------------|
| 执行 superpowers plan 全部任务后 | `consistency-check` | per-task / 执行中途 / 文档撰写过程中 |
| spec/plan 等文档已写完、请用户批准或 review 之前 | `consistency-check` | 撰写过程中、文件未落盘或未自检 |
| Superpowers Plan 全部 Task 完成后的 final/whole-branch code review | `affected-path-review` | per-task / task-reviewer / plan/spec review / review comments / 验证链 / finishing / 未 opt-in 的 iterative-code-review |

验证仍走 Superpowers 原有步骤（计划内验证、`finishing-a-development-branch`，以及 `verification-before-completion` 自身的触发）。这张表不取消验证，也不再强制重跑 `pre-verification-check` → `verification-before-completion`。Plan 收尾时沿用已有验证结果再做 `consistency-check`；文档送审时写完并自检后直接做 `consistency-check`。

**brainstorming 排除判断：** 这个操作有没有设计选择空间？没有 = 跳过，直接执行。

## brainstorming 流程铁律

brainstorming 技能的全部步骤必须走完，不可跳步：

```
spec(书面) → 自检 → 用户审阅批准 → writing-plans → 实现
```

无用户批准的书面 spec = 不可开始实现。

## 记忆

重要讨论结论、用户偏好、纠正过的错误行为，主动建议保存到记忆。
