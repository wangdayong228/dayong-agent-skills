| 决策主题 | 已确认决策 | 来源 | 确认日期 |
| --- | --- | --- | --- |
| Extension 控制边界 | Extension V2 只能补充信息和提供辅助能力；原版 Superpowers 始终独占工作流顺序、用户批准、executor、Task dispatch、review/fix/retry、verification、branch finishing 以及 Plan 准入和完成条件。Extension artifact 失败只能 warning，不得阻断或改变原版流程。 | 已批准 spec：2026-08-13-superpowers-extension-v2-design.md#2. 术语与最高约束 | 2026-08-13 |
| V2 skill 结构 | V2 由 `superpowers-decision-trace`、`superpowers-plan-assistant` 和 `superpowers-execution-timing` 三个独立阶段型 skill 构成；它们不互相调用，也不形成新的总控制器或调度器。 | 已批准 spec：2026-08-13-superpowers-extension-v2-design.md#3. 方案与结构 | 2026-08-13 |
| Decision Trace 记录内容 | Trace 只保存可独立理解的已确认决策及来源，并保留范围、条件、例外、关键数值和否定项；不得保存完整问题、完整对话、agent 推理、session path、turn ID 或其它会话元数据。 | 已批准 spec：2026-08-13-superpowers-extension-v2-design.md#4.1 Artifact | 2026-08-13 |
| Plan 检查中的人工核实范围 | Plan Assistant 必须把用户需要核实的事项集中在报告首节，并且只包含产品意图、风险授权、范围变化和已确认决策冲突；技术正确性由 agent 负责分析，不转交用户逐项 review。 | 已批准 spec：2026-08-13-superpowers-extension-v2-design.md#5.2 需要用户核实 | 2026-08-13 |
| Timing 记录粒度 | Timing 表每一行对应原版 executor 执行 Plan 时自然存在且完整捕获起止的一步；不得为了计时拆分、合并、重命名或重新 dispatch Task、Round 或 Step。 | 已批准 spec：2026-08-13-superpowers-extension-v2-design.md#6.3 非侵入记录 | 2026-08-13 |
| LLM 行为验证 | LLM 行为不可控，因此 LLM smoke 只作一次性观察，三态结果只记录风险，不控制提交或交付；不运行以必须观察到失败作为继续条件的无-skill baseline，也不进行 5/5 或测试到满意。 | 用户明确回答 | 2026-08-14 |
