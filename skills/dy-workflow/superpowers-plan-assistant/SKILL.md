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
