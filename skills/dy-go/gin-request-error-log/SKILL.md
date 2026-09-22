---
name: gin-request-error-log
description: >-
  Use when a Gin service uses rainbow-goutils and HTTP failures must be logged,
  or when handlers return errors with c.JSON, GinError.Render, or a local logger
  instead of ginutils.RenderError.
---

# Gin 请求失败日志

失败请求的错误由 `rainbow-goutils` 统一打印。Handler 只负责把错误交给 `ginutils`；`ApiLogMiddleware` 在请求结束后读取 `c.Errors` 和 `error_stack` 打日志。不要在每个 handler 里手写错误日志，也不要另做一套互斥的 request error logger。

## 依赖

- `github.com/gin-gonic/gin`
- `github.com/nft-rainbow/rainbow-goutils`（`logger`、`middlewares`、`utils/ginutils`）
- `github.com/sirupsen/logrus`
- `github.com/pkg/errors`

## 接入

1. 启动时 `logger.Init(logConfig)`。
2. 使用 `gin.New()`，按此顺序挂中间件：

```go
engine.Use(gin.Logger())
engine.Use(pkgmiddlewares.ApiLogMiddleware(bodyIgnoredPaths))
engine.Use(pkgmiddlewares.Recovery())
```

`bodyIgnoredPaths` 放登录、上传等不能记 body 的路径。

3. 业务失败只走：

```go
ginutils.RenderResponse(c, resp, err)
// 或
ginutils.RenderError(c, err)
```

业务错误用 `*ginutils.GinError`。普通 `error` 会被转成 code `100`。`RenderError` 内部会 `c.Error(err)` 并写入 `error_stack`，这是 ApiLog 能打出错误的前提。

## 禁止

- 业务失败主路径使用 `c.JSON(4xx/5xx, ...)`。
- 只调用 `someGinError.Render(c)`。它只写 JSON，不调用 `c.Error`，日志里没有 `errors` / `stack`。

```go
// 错误
bimerrors.ErrInvalidInput.WithData(err.Error()).Render(c)
// 正确
ginutils.RenderError(c, bimerrors.ErrInvalidInput.WithData(err.Error()))
```

## 验收

制造一次 `RenderError` 失败：响应是 `{code, message, data}`，日志有 `[ApiLogMiddleware] Request` 且含 `errors`。Panic 由 `Recovery` 记录并返回统一错误体。
