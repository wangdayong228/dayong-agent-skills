# Superpowers Extension V2 设计规格

**状态：** 待书面审阅
**日期：** 2026-08-13

## 1. 目标

以三个跨代理、单职责 skill，为原版 Superpowers 增加旁路信息和辅助能力。
Extension V2 只增加信息，不增加原版 Superpowers 的状态、门禁或调度行为。

## 2. 术语与最高约束

- **原版 Superpowers**：`brainstorming`、`writing-plans`、executor、review、
  fix、retry、verification 和 branch finishing 等既有 skill 与工作流规则。
- **Extension V2**：本规格新增的三个辅助 skill。
- **用户**：负责批准 spec，以及决定产品意图、风险授权、范围变化和决策冲突。

原版 Superpowers 始终独占以下控制权：

- 工作流顺序和用户批准门禁；
- executor 选择和 Task dispatch 粒度；
- review、fix、retry 的次数和规则；
- verification 和 branch finishing 流程；
- Plan 的执行准入与完成条件。

Extension V2 不得修改、替代或绕过这些规则。Extension 建议与原版
Superpowers 冲突时，以原版 Superpowers 为准。若某项能力必须改变原版规则才能
实现，停止该项设计或实现并询问用户。

Extension artifact 缺失、过期、不可读、不可解析或写入失败时，只报告 warning，
不得阻塞、暂停或改变原版流程。

## 3. 方案与结构

采用三个阶段型、互不调度的 skill：

| Skill | 能力 | 输入 | 输出 | 触发时机 | 不改变控制流的原因 |
| --- | --- | --- | --- | --- | --- |
| `superpowers-decision-trace` | Decision trace | 当前 spec、相邻 trace、用户新确认的答案 | spec 相邻 trace | brainstorming 和 spec 修订期间 | 只减少重复提问；失败时原版 brainstorming 继续 |
| `superpowers-plan-assistant` | Plan Task 辅助分析、Plan 技术检查、DAG 与并行建议 | 完成原版 self-review 的 Plan、对应 spec、可用 trace | Plan 相邻的单一分析报告 | 原版 `writing-plans` 完成 self-review 后 | 不批准 Plan、不选择 executor，findings 不控制执行 |
| `superpowers-execution-timing` | Execution timing | Plan 路径及原版 executor 自然产生的步骤边界 | 每次 Plan 执行一个相邻 timing 文件 | 原版 executor 已确定并开始执行后 | 只记录已发生步骤，不创建步骤、轮次、Task 或调度决定 |

三个 skill 均按阶段尽力自动匹配，同时支持用户显式调用。它们不互相调用，也不以
另一个 Extension artifact 的存在作为运行前提。任一 skill 未触发都不影响原版流程。

## 4. Decision Trace

### 4.1 Artifact

每个 spec 只使用一个相邻 trace：

```text
feature-design.md
feature-design-decision-trace.md
```

不建立全局 trace，不创建 `specs/index.md`。相邻 trace 是已确认决策的唯一持久事实
来源；当前会话内容只作临时缓存，不能替代文件。

每条记录只包含：

```text
决策主题 | 已确认决策 | 来源 | 确认日期
```

来源只能是：

- 用户明确回答；
- 用户已批准 spec 的具体章节。

只保存可独立理解的已确认决策和来源引用。决策必须保留适用范围、条件、例外、关键
数值和明确否定项；不得保存脱离问题上下文的短答案，如“A”“是”或“同意”。短回答
必须结合当时的问题改写为完整命题。不保存完整问题、完整对话、agent 推理、
session path、turn ID 或其它会话元数据。

### 4.2 行为

每次准备提出关键需求问题前，轻量重读相邻 trace：

- 同一决策主题已有明确决策：直接采用，禁止重复询问；
- 可从多项已确认决策可靠推出：用于当前工作，但不把推论写成已确认决策；
- 无法可靠推出：一次只问用户一个问题，确认后立即更新 trace。

用户的新明确回答与旧记录冲突时，不自动覆盖。向用户说明新旧结论并请求决定，
随后只保留最新有效结论。

trace 仅在以下情况视为过期：

- 引用的 spec 路径或章节已不存在；
- 记录与当前已批准 spec 明确冲突。

不使用 hash 或文件时间判断过期。读取或写入失败时，当前会话可继续使用已经确认的
信息以避免当场重复询问，但必须 warning，且不得声称该信息已持久保存。

## 5. Plan Assistant

### 5.1 Artifact 与触发

在原版 `writing-plans` 写完 Plan 并完成自身 self-review 后运行，生成一个相邻报告：

```text
feature-plan.md
feature-plan-plan-auto-review-report.md
```

报告默认只提供分析和 findings，不包含 READY、hash 或其它执行准入状态，固定包含
以下三个章节。

报告不使用 hash 或文件时间判断是否过期。报告引用的 Plan Task 或章节已不存在，
或者报告内容与当前 Plan 明确冲突时，才视为过期；过期报告只失去参考价值，不形成
任何门禁。

### 5.2 Plan Task 辅助分析

逐个 Task 分析：

- 职责和验收目标；
- 前后依赖和接口；
- 文件或共享状态写入冲突；
- 是否能够独立实现、测试和审阅。

是否独立是 Task 边界的首要分析依据，预计时长只作提示。分析结果是对原版
`writing-plans` 的建议，不强制改变其 Plan 格式或 Task 粒度。

### 5.3 Plan 技术检查

agent 检查技术正确性、spec 覆盖、Task 间接口一致性、路径、命令、测试可执行性和
明显冲突。

检查循环严格有界：

1. 执行一次技术检查；
2. 如有不涉及用户决策的明确技术问题，最多统一修正 Plan 一次；
3. 修正后，只对受修改影响的 Task、接口和直接依赖复查一次；
4. 仍有问题则保留 findings 并退出，不再修正或复查。

涉及产品意图、风险授权、范围变化或已确认决策冲突时，不自动修改，交给用户决定。
技术检查不得扩大已批准 spec 的范围。

报告无 findings 时写明“未发现技术问题”。报告存在 findings、缺失、过期或写入失败
均不得阻止原版后续流程。

### 5.4 DAG 与并行建议

根据依赖关系、接口稳定性、文件和共享状态冲突，列出：

- 可并行 Task 及原因；
- 必须串行 Task 及原因。

该分析不选择或替换 executor，不自行调度 Task。只有原版 Superpowers 已决定并行
执行时，才补充 worktree 或 wave 建议。不得自行增加 review、integration、
verification Task 或门禁。

## 6. Execution Timing

### 6.1 Artifact 生命周期

每次从头执行 Plan 时创建一个相邻文件：

```text
feature-plan-timing-20260813T143205+0800.md
```

同一次执行中断恢复时继续使用原文件；重新从头执行时创建新文件。Extension 不建立
全局 timing 索引。

文件正文只包含：

```text
Task | Round | Step | Start | End | Duration
```

### 6.2 行语义

- 一行对应原版 Superpowers 执行 Plan 时自然出现、且完整观测到起止时间的一个步骤；
- `Task` 是该步骤所属的现有 Plan Task；
- `Round` 沿用原版执行自然产生的轮次；原版没有轮次概念时使用 `1`；
- `Step` 沿用原版实际步骤名称，不预设枚举或固定粒度；
- `Start` 和 `End` 是调用记录工具时取得的带时区 ISO 8601 真实系统时间；
- `Duration` 由同一行的真实起止时间确定性计算，不手写、不估算。

### 6.3 非侵入记录

- 只在原版自然步骤的开始和结束边界各进行一次轻量本地调用；
- 开始时间暂存于轻量临时状态，结束时才追加完整表格行；
- 未同时捕获开始和结束的步骤不进入表格，不推断、不补造历史时间；
- 不为计时拆分、合并、重命名或重新 dispatch 任何 Task、Round 或 Step；
- 每次记录操作只尝试一次；timing 文件、临时状态或调用失败时，最多报告一次
  warning 并立即返回，不重试、不暂停原版流程；
- 不记录 evaluator 输出、session path、turn ID、模型信息或其它审计字段；
- timing 不读取 Plan Assistant 报告，也不依据 findings 决定是否执行。

## 7. 最小实现边界

交付目录：

```text
skills/dy-workflow/
  superpowers-decision-trace/
  superpowers-plan-assistant/
  superpowers-execution-timing/
```

只为反复且需要确定性的文件操作提供小型 Python 标准库脚本：

- trace 的读取、校验和原子更新；
- timing 文件创建、步骤开始/结束记录和 duration 计算。

Plan 技术判断、Task 分析和 DAG 分析由 agent 完成。不建设总控制器、平台专属 hook、
数据库、后台服务、全局配置、scheduler、审计系统、旧版兼容层或旧数据迁移。

## 8. 验证与明确退出条件

可靠性主要由以下证据保证：

- 确定性脚本单元测试；
- artifact 格式和字段校验；
- 对禁止状态、字段和控制行为的静态边界检查；
- 人工审阅三个 skill 是否越过原版 Superpowers 边界。

确定性测试覆盖：相邻路径生成、trace 更新和冲突保护、timing 六列格式、真实时间解析
与 duration 计算、未完成步骤不进入表格、同次执行恢复，以及失败返回 warning。

所有验证循环必须预先有界：

- 测试场景和执行次数在测试开始前固定，不因单次结果临时扩充；
- 同一个确定性失败在一次验证过程中最多进行两轮针对性修复和重跑；仍失败则记录并停止；
- Plan 技术检查只执行第 5.3 节规定的一次修正和一次局部复查；
- 少量代理行为冒烟检查只用于发现明显触发、理解或越界问题，不证明行为稳定性、
  不统计通过率，也不作为交付准入条件；
- 每个预先确定的代理行为场景只采样一次，结果仅为“未发现明显问题”、
  “发现明确越界”或“无法判断”；
- 单次措辞、格式或随机差异不得触发 skill 修改、重复采样或全量重跑；
- 每个明确越界最多允许一次针对性修改，并只复查受影响场景一次；复查后仍越界或
  无法判断时，记录结果与剩余风险并停止，本次交付不再继续测试；
- 禁止连续 5/5 等重复行为评测，不存在“测试直到满意”。

## 9. 明确不做

- 改变原版 Superpowers 的工作流、门禁、executor、Task、review、retry、verification
  或 branch finishing 规则；
- 让 Extension artifact 控制原版 Superpowers 是否可以继续；
- 全局 trace、`specs/index.md`、Plan hash、READY 状态或执行准入机制；
- 无限 review/fix/re-review 或无限测试循环；
- evaluator 逐字输出、session path、turn ID 等审计系统；
- 因单次模型措辞或格式差异修改 skill 并全量重跑；
- review 自动扩大需求范围；
- 旧版实现、Plan、review report、评测 evidence、timing 数据的继承、迁移或兼容。

## 10. 验收标准

- 三个 skill 的输入、输出、触发时机和非阻断行为均与本规格一致；
- 五项保留能力全部覆盖，且不新增原版 Superpowers 状态或门禁；
- 所有循环均有明确退出条件和最大次数；
- timing 只含六列真实数据，无法捕获的数据不估算；
- 确定性逻辑具备单元测试，代理行为检查保持少量、语义化和非硬门禁；
- 仓库实现不读取或继承旧分支材料。
