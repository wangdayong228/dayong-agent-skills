---
name: handling-connection-loss
description: >-
  Use when a long-running worker or service exits because a database or
  other dependency connection dropped, when a transient outage is handled
  by crashing the process, or when deciding whether a failed persistence
  step should retry, alert, or stop.
---

# 连接中断时保持进程

## 规则

1. 连接中断只认当前驱动的闭集，依据错误类型和哨兵。错误文本不能单独作为依据。结果不明的总哨兵不算连接中断。
2. 一轮只有连接中断时，结束这一轮，按已有退避等待，再从已持久化的状态进入下一轮。进程继续运行。
3. 同一轮还有完整性错误、冲突或非法输入时，停止进程。对外服务开始前，迁移或恢复失败也退出。收到取消时退出，不为取消发送中断告警或恢复通知。
4. 提交可能已经落库时，下一轮沿已有记录继续，不新造幂等键。
5. 告警沿用已有的连续失败阈值和退避，不另设告警间隔。未到阈值不报警。达到阈值的当次，以及之后每次失败，都报警。
6. 中断计数与单个工作项的失败计数分开，只留在进程内存中。进程重启后从零开始。
7. 已经发过失败告警后，某一轮成功就发一条恢复通知，然后计数归零。未到阈值就成功时，计数归零，不发恢复通知。
8. 本地日志保留检查句和诊断。告警不改变业务状态。发送失败不影响退避、重试和计数归零。

## 不适用

单次请求已经把错误返回给调用方时，不用这套进程内重试。
