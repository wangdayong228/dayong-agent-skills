---
name: global-conventions
description: Use when starting any conversation — establishes mandatory skill trigger rules, workflow constraints, and memory conventions inherited from CLAUDE.md
---

# 全局行为准则

## 技能触发规则

以下技能在对应场景**必须调用**，无需等用户手动指定：

| 场景 | 技能 | 排除（不触发） |
|------|------|--------------|
| 创建/修改产出物（文件、功能、规则、模块、行为） | `brainstorming` | typo/格式化、纯粹执行用户精确指令（「把 X 改名为 Y」）、回答问题、查 bug 原因 |
| 声称完成/通过/修好 | `pre-verification-check` → `verification-before-completion` → `consistency-check` | — |
| 执行 plan 全部任务后 | `pre-verification-check` → `verification-before-completion` → `consistency-check` | — |
| 遇到 bug、测试失败、异常行为 | `systematic-debugging` | — |
| 收到 code review 反馈 | `receiving-code-review` | — |

**brainstorming 排除判断：** 这个操作有没有设计选择空间？没有 = 跳过，直接执行。

## brainstorming 流程铁律

brainstorming 技能的全部步骤必须走完，不可跳步：

```
spec(书面) → 自检 → 用户审阅批准 → writing-plans → 实现
```

无用户批准的书面 spec = 不可开始实现。

## 记忆

重要讨论结论、用户偏好、纠正过的错误行为，主动建议保存到记忆。
