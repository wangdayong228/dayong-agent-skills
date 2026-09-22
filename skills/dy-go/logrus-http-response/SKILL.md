---
name: logrus-http-response
description: >-
  Use when a Go service logs with logrus and rainbow-goutils, including
  logger.Init, log levels, Gin ApiLogMiddleware, or when handlers return
  errors with c.JSON, GinError.Render, or a local logger instead of
  ginutils.RenderError.
---

# logrus 与 HTTP 响应

业务日志用全局 `logrus`。初始化、按日文件、控制台双写、请求日志和 panic 恢复都走 `rainbow-goutils`。

请求失败日志依赖错误响应路径：只有 `ginutils.RenderError` / `RenderResponse` 会写入 `c.Errors` 和 `error_stack`，`ApiLogMiddleware` 才能打出 `errors`。两条规则分开适用：

- 当前任务只加业务日志时，不改现有 HTTP 响应。
- 当前任务只改 HTTP 错误响应时，不新增 `logger.Init`、日志级别或业务日志格式。
- HTTP 错误响应规则只在该服务已经使用 `ginutils` 时适用。

## 依赖

- `github.com/sirupsen/logrus`
- `github.com/gin-gonic/gin`
- `github.com/nft-rainbow/rainbow-goutils` 的 `logger`、`middlewares`、`utils/ginutils`
- `github.com/pkg/errors`

## 初始化

启动时、业务开始前调用 `logger.Init(logConfig)`。

```yaml
log:
  level: info    # debug|info|warn|error；缺省 info
  folder: .log   # 按日文件 YYYY_MM_DD.log，并双写彩色控制台
  caller: false
  format: text   # text 给人看；json 字段为 ztimestamp/zlevel/@message
```

## 怎么打

```go
logrus.WithError(err).
    WithField("order_id", orderID).
    Info("[CardService] open card completed")
```

- 消息以 `[Component]` 开头，写清做了什么；ID、金额、状态放 Fields，错误用 `WithError`。
- **Debug**：高频内部细节、外部请求原文。**Info**：启停、一轮任务、正常业务结果。可预期的本轮失败也可以是 Info + `WithError`。**Warn**：已兜底的异常。**Error**：必须关注的失败。
- 按业务事件打，不要每个函数入口都打。Controller 不重复打请求日志。
- 不记密码、私钥、完整 captcha ticket、证件与登录 body。

GORM 使用 `logrus.StandardLogger().WriterLevel(logrus.WarnLevel)`，只记 Warn 与慢查询，并使用参数化 SQL。

## Gin 请求日志

`gin.New()`，顺序固定：

```go
engine.Use(gin.Logger())
engine.Use(pkgmiddlewares.ApiLogMiddleware(bodyIgnoredPaths))
engine.Use(pkgmiddlewares.Recovery())
```

`ApiLogMiddleware` 在请求结束后打一条 `Info("[ApiLogMiddleware] Request")`。忽略列表中的路径，以及 body ≥ 5KB，不记录 body。有 `c.Errors` 时带上 `errors` 和 `error_stack`。

`bodyIgnoredPaths` 放登录、上传、证件等不能记 body 的路径。Panic 由 `Recovery` 记 `logrus.Error`，并对客户端返回统一错误体。

## HTTP 错误响应

服务已经使用 `ginutils`，且当前任务在改 HTTP 错误响应时，失败只走：

```go
ginutils.RenderResponse(c, resp, err)
// 或
ginutils.RenderError(c, err)
```

`RenderError` 会 `c.Error(err)` 并写入 `error_stack`。业务错误用 `*ginutils.GinError`。普通 `error` 会变成 code `100`。成功与失败响应体都是 `{code, message, data}`。

业务失败主路径不用 `c.JSON(4xx/5xx, ...)`。也不只调用 `someGinError.Render(c)`：它只写 JSON，不调用 `c.Error`，日志里没有 `errors` / `stack`。

```go
// 错误
bimerrors.ErrInvalidInput.WithData(err.Error()).Render(c)
// 正确
ginutils.RenderError(c, bimerrors.ErrInvalidInput.WithData(err.Error()))
```

Handler 不另写一套请求错误日志。

## 验收

加请求日志时：有 `[ApiLogMiddleware] Request`；登录或上传路径的日志中没有 body。

改 HTTP 错误响应时：一次 `RenderError` 的响应为 `{code, message, data}`，同一条请求日志含 `errors`。Panic 有 recovery 日志和统一错误体。
