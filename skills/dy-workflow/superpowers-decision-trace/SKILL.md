---
name: superpowers-decision-trace
description: >-
  Use when brainstorming or revising a written spec where confirmed user
  decisions may already exist in an adjacent decision trace.
---

# Superpowers Decision Trace

## 合同

| 输入 | 输出 | 触发时机 | 不改变控制流的原因 |
| --- | --- | --- | --- |
| 当前 spec、相邻 trace、用户新确认的答案 | 唯一相邻 `<spec-stem>-decision-trace.md` | brainstorming 或 spec 修订期间，每次关键需求问题前 | 只复用和补充信息；任何失败后原版 brainstorming 继续 |

相邻 trace 是已确认决策的唯一持久事实来源。当前会话只能临时缓存已知信息，不能替代文件。

## 提问前

1. 每次关键需求问题前重读相邻 trace。
2. 同一主题已有明确决策时直接采用，禁止重复询问。
3. 可由已确认决策可靠推出的结论只用于当前工作，不写成确认决策。
4. 无法可靠推断时，一次只问一个问题。

先把 `HELPER` 解析为当前 `SKILL.md` 所在目录下的 `scripts/decision_trace.py` 绝对路径；不得假设当前工作目录是 skill 目录。读取命令：

```bash
python3 "$HELPER" read SPEC
```

trace 缺失时命令输出空四列表头和一条 warning，但不创建文件。读取失败时 helper 也只输出一条 warning；不要为同一次失败再输出第二条 warning，也不得影响原版 brainstorming。

## 确认后

把用户短回答结合问题上下文改写为可独立理解的已确认决策。完整保留适用范围、条件、例外、关键数值和明确否定项；不得保存完整问题、完整对话、agent 推理、session path、turn ID 或其它会话元数据。

用户确认后立即调用 `record`。来源只能是 `用户明确回答`，或 `已批准 spec：SPEC#SECTION`。不得把可靠推论或未确认内容写入 trace。

```bash
python3 "$HELPER" record SPEC \
  --topic TOPIC --decision DECISION --source-kind user

python3 "$HELPER" record SPEC \
  --topic TOPIC --decision DECISION --source-kind approved-spec \
  --source-ref SPEC#SECTION
```

同主题新旧决策冲突时先向用户说明两者。只有用户决定采用新结论后才使用 `--replace-conflict`；trace 只保留最新有效结论，不保存历史版本。

## 过期与失败

读取后，逐条核对来源为 `已批准 spec：SPEC#SECTION` 的记录：相对路径以当前 spec 所在目录解析，并确认引用文件及对应 Markdown 章节仍存在。路径或章节不存在，或记录与当前批准 spec 明确冲突时才判过期；不得使用 hash 或 mtime。过期记录只失去参考价值，不删除、不自动覆盖，也不阻断原版流程。读取或写入失败时，可以继续使用本会话已确认的信息避免当场重复询问，但必须保留 helper 的单条 warning，且不得声称该信息已持久保存。

不创建全局 trace，不创建 `specs/index.md`。trace、锁或 helper 状态不得成为 spec 批准、Plan 执行或任何原版 Superpowers 步骤的前置条件。发生规则冲突时服从原版 Superpowers；若必须改变原版规则才能实现，停止并询问用户。
