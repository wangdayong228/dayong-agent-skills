---
name: superpowers-execution-timing
description: >-
  Use when an original Superpowers executor is already running a written Plan
  and observable natural step timing should be recorded as sidecar data.
---

# Superpowers Execution Timing

## 合同

| 输入 | 输出 | 触发时机 | 不改变控制流的原因 |
| --- | --- | --- | --- |
| Plan 路径及原版自然步骤边界 | 本次执行的相邻 timing 文件 | 原版 executor 确定并开始执行 Plan 后 | 只记录已发生步骤；任何失败后一条 warning 后立即继续原版流程，不重试 |

只有原版 executor 已经选择并开始执行 Plan 后才能触发。本 skill 不选择或替换 executor，
也不读取 Plan Assistant 报告或依据 findings 决定执行。

## 一次执行

先把 `HELPER` 解析为当前 `SKILL.md` 所在目录下的
`scripts/execution_timing.py` 绝对路径；不得假设当前工作目录是 skill 目录。

每次从头执行 Plan 时调用一次 `create`，保留命令输出的 timing 路径：

```bash
python3 "$HELPER" create PLAN
```

同次执行恢复时显式继续使用已知 timing 路径；重新从头执行时调用一次新的 `create`。
无法确认是恢复还是重启时不猜测，保留一条 warning 并让原版执行继续；不使用 `latest`、
自动发现或全局 index。

## 自然 step 边界

在每个原版自然 step 开始时调用一次：

```bash
python3 "$HELPER" start TIMING \
  --task TASK --round ROUND --step STEP
```

保存命令输出的唯一 state 路径。在同一自然 step 结束时调用一次：

```bash
python3 "$HELPER" end STATE
```

`Task`、`Round` 和 `Step` 沿用原版执行的实际名称与边界；原版没有 Round 时使用 `1`。
不得拆分、合并、重命名、创建或重新 dispatch 任何 Task、Round 或 Step，也不得为计时
重新执行自然 step。

只记录完整捕获的起止时间。缺少 start 或 end 的步骤不进入 timing，不估算、不回填历史。
Start 和 End 是 helper 调用时的带时区真实系统时间，Duration 由同一行确定性计算。

## 失败边界

每个 `create`、`start` 或 `end` 只调用一次。helper 是 warning 的唯一输出边界；出现一条
warning 后不要重复转述，也不要重试。timing/state/锁/写入失败不得暂停或改变 upstream
执行。`end` 一旦开始就对 state 做一次 best-effort 删除；不论删除是否成功，skill 都
立即放弃该 state，禁止再次调用 `end`。即使格式错误、结束早于开始、锁竞争或写入失败
也不重试；删除失败可能留下临时文件，但该文件不得被 skill 重新使用。

timing 正文只能包含 `Task | Round | Step | Start | End | Duration` 六列，不增加 execution
ID、状态、evaluator 输出、session path、turn ID 或模型字段。不建立全局 timing index。

本 skill 不增加任何状态机，timing artifact 不得控制 execution、review、verification 或
finishing。发生规则冲突时服从原版 Superpowers；若必须改变原版规则才能记录，停止记录
并先询问用户。
