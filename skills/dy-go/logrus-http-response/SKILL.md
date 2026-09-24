---
name: logrus-http-response
description: >-
  Use when a Go service logs with logrus and rainbow-goutils, including
  logger.Init, log levels, Gin ApiLogMiddleware, when defining a GinError
  body code or HTTP status, or when handlers return errors with c.JSON,
  GinError.Render, or a local logger instead of ginutils.RenderError.
---

# logrus 与 HTTP 响应

## 日志系统

一套全局 `logrus`。`logger.Init` 之后，业务日志、请求日志和 panic 都进同一条输出：按日文件，并双写彩色控制台。`Init` 之前的调用不进这套输出。

| 部分 | 谁写 | 结果 |
|------|------|------|
| 业务日志 | 业务代码调用全局 `logrus` | 按事件写一条，带 `[Component]` 和 Fields |
| 请求日志 | `ApiLogMiddleware` | 每个请求结束写一条 `Info("[ApiLogMiddleware] Request")` |
| 失败出现在请求日志里 | `RenderError` / `RenderResponse` 写入 `c.Errors` 和 `error_stack` | Handler 不再为同一次失败另写一条请求错误日志 |
| Panic | `pkgmiddlewares.Recovery()` | 使用这份中间件，不要重写 |
| 报警 | 不属于本系统 | 不随日志改动一起加 |

请求日志能看见失败，是因为错误响应写进了 `c.Errors`，不是因为多打了一条 handler 日志。成功响应不写 `c.Errors`。

业务事件由业务代码写，请求日志由中间件写：

```go
logrus.WithField("order_id", orderID).Info("[CardService] open card completed")
```

按任务适用：

- 当前任务只加业务日志时，不改现有 HTTP 响应，不替换现有中间件链。
- 当前任务只改 HTTP 错误响应时，不新增 `logger.Init`、日志级别或业务日志格式，也不改成功响应。
- 成功响应和 HTTP 错误响应的写法只在该服务已经使用 `ginutils` 时适用。
- 本 skill 不管报警。改日志或错误响应时不要顺手加 `DingError`。`ErrUnexpected` 要报警是另一套规则。

## 依赖

- `github.com/sirupsen/logrus`
- `github.com/gin-gonic/gin`
- `github.com/nft-rainbow/rainbow-goutils` 的 `logger`、`middlewares`、`utils/ginutils`

## 初始化

业务开始前调用 `logger.Init(logConfig)`。在此之前的 `logrus` 调用不会进入按日文件，也不会走彩色控制台。

```yaml
log:
  level: info    # debug|info|warn|error；缺省 info
  folder: .log   # 按日文件 YYYY_MM_DD.log，并双写彩色控制台
  caller: false
  format: text   # text 给人看；json 字段为 ztimestamp/zlevel/@message
```

## 怎么打

```go
// 成功
logrus.WithField("order_id", orderID).Info("[CardService] open card completed")

// 失败
logrus.WithError(err).WithField("order_id", orderID).Error("[CardService] open card failed")
```

- 消息以 `[Component]` 开头，写清做了什么；ID、金额、状态放 Fields，错误用 `WithError`。
- **Debug**：高频内部细节。外部请求原文仅在不含密钥、证件、ticket 时使用。**Info**：启停、一轮任务、正常业务结果。后台任务本轮失败且还会重试时，可以用 Info + `WithError`。**Warn**：已兜底、调用仍继续。**Error**：必须有人看的失败。
- 余额不足、超过限额这类预期用户错误，HTTP 层已经记下时，service 不再打一条。
- 按业务事件打，不要每个函数入口都打。Controller 可以打业务判断；不要再打一条与访问日志重复的请求日志。
- 不记密码、私钥、完整 captcha ticket、证件与登录 body。

接入 GORM logger 时，用 `logrus.StandardLogger().WriterLevel(logrus.WarnLevel)`，只记 Warn 与慢查询，并使用参数化 SQL。

## Gin 请求日志

把下面两行加在现有中间件之前。不要用它们替换整条链，CORS 和鉴权保持不动。

```go
engine.Use(pkgmiddlewares.ApiLogMiddleware(bodyIgnoredPaths))
engine.Use(pkgmiddlewares.Recovery())
```

错误能进 ApiLog，是因为 `RenderError` 写了 `c.Errors`，不是因为 `gin.Logger()`。`gin.Logger()` 与 `ApiLogMiddleware` 同时使用会各打一遍访问日志。

`ApiLogMiddleware` 在请求结束后打一条 `Info("[ApiLogMiddleware] Request")`。有 `c.Errors` 时带上 `errors` 和 `error_stack`。`ContentLength` ≥ 5KB 不记录 body；`ContentLength` 未知（-1）时仍会读取 body。

`bodyIgnoredPaths` 与请求 URL 精确匹配，大小写不敏感，不是路由模板。`/v1/files/kyc/*filepath` 不会命中真实路径。登录、上传、证件用真实路径。Query 会拼进 `path`；token 在 query 里时，忽略 body 也挡不住。

Panic 使用上面的 `pkgmiddlewares.Recovery()`，不要自己重写恢复中间件。

## 成功响应

新 handler，且服务已经使用 `ginutils` 时，成功走 `RenderSuccess(c, obj)` 或 `RenderResponse(c, obj, nil)`。创建、更新、删除、异步受理和幂等重放都是 HTTP 200 加业务对象。同一把幂等键、同一份参数的重放返回同一份业务对象，不用 `201` 或 `202` 区分是否第一次创建。`obj` 为 `nil` 时响应是 `{}`。成功不写 `c.Errors`，也不包进 `{code, message, data}`。

已有 handler 的成功响应保持原样。

## HTTP 错误响应

服务已经使用 `ginutils`，且当前任务在改 HTTP 错误响应时，只改失败分支：

```go
ginutils.RenderError(c, err)
// 或
ginutils.RenderResponse(c, nil, err)
```

`RenderError` 会 `c.Error(err)` 并写入 `error_stack`。公开错误的 HTTP 状态和 body `code` 见「错误码」。

业务失败主路径不用 `c.JSON(4xx/5xx, ...)`。也不只调用 `someGinError.Render(c)`：它只写 JSON，不调用 `c.Error`，日志里没有 `errors` / `stack`。同一次失败不要再写 `logrus.Error`。

`message` 保持公开错误定义时的固定短文案，调用时不要覆盖，也不要用 `WithMessage` 追加本次详情。本次失败详情放进 `data`：先 `WithData(data)`，再交给 `RenderError`。承载详情的参数名是 `data`，不要叫 `message`。没有额外详情时不要设置 `data`，响应里它是 `null`。`data` 只放已可公开的失败检查和事实，不放凭证、私钥、SQL、DSN 或上游响应正文。

`fmt.Errorf("%w", ginErr)` 经 `pkg/errors.Cause` 解不开，会掉成业务码 `100`、HTTP `599`。要保住业务码，`Cause()` 必须仍是 `*GinError`（例如 `pkg/errors.Wrap`）。

```go
// 错误：用详情覆盖 message，data 仍是 null
cloned := *bimerrors.ErrInvalidInput
cloned.Message = data
ginutils.RenderError(c, &cloned)

// 错误：详情进了 data，但只 Render，不进 ApiLog
bimerrors.ErrInvalidInput.WithData(data).Render(c)

// 正确：message 仍是 "invalid input"，详情在 data
ginutils.RenderError(c, bimerrors.ErrInvalidInput.WithData(data))
```

下面这段只用于新 handler。已有 handler 只在任务是改错误响应时改失败分支，成功分支不动。

```go
func OpenCard(c *gin.Context) {
    if err := c.ShouldBindJSON(&req); err != nil {
        ginutils.RenderError(c, bimerrors.ErrInvalidInput.WithData(err.Error()))
        return
    }
    orderID, err := service.OpenCard(req)
    if err != nil {
        ginutils.RenderError(c, err)
        return
    }
    ginutils.RenderSuccess(c, gin.H{"orderID": orderID})
}
```

绑定失败和 `OpenCard` 失败都会出现在 `[ApiLogMiddleware] Request` 的 `errors` 里。`order_id` 那条业务日志不是请求日志。

## 错误码

公开错误是 `*ginutils.GinError`，响应体为 `{code, message, data}`。调用方看 body `code`。body `code` 取 200 以内或 600 以外，并且不要用 `100`。

- `NewBusinessGinError(code, message)`：HTTP 599
- `NewBadRequestGinError(code, message)`：HTTP 400
- `NewConflictGinError(code, message)`：HTTP 409

一个场景只用一个整数。公开错误定义在同一个包里，handler 只引用这些变量，不在 handler 里新造一个公开错误。定义时的 `message` 是固定短文案；这次失败的详情用 `WithData`，不改 `code`、HTTP 状态和 `message`。

应用只使用这些 HTTP 状态：成功 `200`；参数或校验失败 `400`（`NewBadRequestGinError`）；未认证 `401`（`NewGinError`）；不存在 `404`（`NewGinError`，方法不允许也用 404）；冲突 `409`（`NewConflictGinError`）；应用判定的服务端失败 `599`（`NewBusinessGinError`，或 `NewGinError(599, code, message)`）。

应用不返回 `201`、`202`、`403`、`405`、`422`、`429`，也不返回 `500`、`502`、`503`、`504`。这些 `5xx` 只留给网关、反向代理和负载均衡。已知还是未知看 body `code`：完整性、依赖失败、暂时不可用、健康检查失败、关停中都是 HTTP `599` 加各自的业务码；未分类内部错误才是 HTTP `599` 加通用内部码。网关不要按 `599` 自动重试。

`NewGinError` 的 status 只能是 `401`、`404` 或 `599`。body `code` 仍然避开 `200`–`600`，并且不要用 `100`。

上述 HTTP 状态用于新 handler。已有响应是否改成这组状态，先问用户。用户明确要求按该白名单调整时才改；未说明则保持原状态，不要把 `201` / `202` 收成 `200`，不要把 `405` 收成 `404`，也不要把 `500` / `502` / `503` / `504` 收成 `599`。

```go
// errors/errors.go
var ErrNotEnoughBalance = ginutils.NewBusinessGinError(120, "insufficient balance")
```

```go
// handler
if err != nil {
    ginutils.RenderError(c, errors.ErrNotEnoughBalance.WithData(data))
    return
}
```

`120` 只分配一次。响应仍是 HTTP 599、body `code` 120、`message` 为 `insufficient balance`，本次详情在 `data`。

不是 `*GinError` 的错误经 `RenderError` 变成 body `code` `100`、HTTP `599`，`message` 为 `err.Error()`。

Gin 或中间件已经写完的响应保持原样，不要改成 `GinError`。路由未命中是 Gin 的 404。方法不允许同样返回 404 和「不存在」的业务码，不要返回 405。`gin-jwt` 未认证沿用回调给出的 HTTP 401 和它自己的响应体 `{code, message}`。

## 验收

加请求日志时：有 `[ApiLogMiddleware] Request`；登录或上传的真实路径日志中没有 body；现有中间件、成功响应和失败响应都不变。

新 handler：成功是 HTTP 200 加业务对象；`*GinError` 的失败响应是 `{code, message, data}`，且同一条请求日志含 `errors`。普通 `error` 才是业务码 `100`、HTTP `599`。

改已有 HTTP 响应时：只改当前任务点名的失败分支。成功响应仍是原来的业务对象。用户没有明确要求调整 HTTP 状态时，先询问，不要改现有状态码。用户明确要求按白名单调整时：`400` / `401` / `404` / `409` 保持不变，不要收成 `599`；`405` 改为 `404`；成功 `201` / `202` 改为 `200`，响应体仍是原来的业务对象，不要为了区分首次创建和重放新增字段；`500` / `502` / `503` / `504` 改为 `599`，body `code` 不变。Panic 走 `pkgmiddlewares.Recovery()`，没有另写的恢复中间件。
