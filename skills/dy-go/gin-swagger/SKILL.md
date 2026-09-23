---
name: gin-swagger
description: >-
  Use when a Go Gin service needs Swagger 2.0 docs, swaggo
  handler comments or annotations, swag init, gin-swagger UI, DTO
  swaggertype or example tags, or generated docs drift after API changes.
---

# Gin Swagger

服务自己的 HTTP API 文档只有三条手写来源：进程入口的全局注解、handler 上方的 swag 注释、DTO 上的 `swaggertype` / `example`。用 `swag init` 生成 Go 包，运行时空白导入。`swag` 产出的是 **Swagger 2.0**，不是 OpenAPI 3。只提交生成的 `docs.go`。不要手写或手改 `swagger.json` / `swagger.yaml`，不要按 OAS3 写注解或改生成格式。

本 skill 只管服务对外 HTTP 文档，且只覆盖**一份**生成文档（一个 `docs/<api>`、一个 `swag.Register`）。不要为第二个文档目录或第二套 UI 自行扩展。上游 OpenAPI 副本和 `swagger-codegen` / `openapi-generator` 生成客户端不走这里。

按任务适用：

- 只补或改 handler 注解 / DTO 文档标签：只改这些注释。已有 `docs.go` 时按项目现有命令重新生成。不要新增或升级依赖，不要改 Makefile / CI / 路由 / UI。
- 项目还没有 swag 文档，或用户明确要求整套接入：才加依赖、生成目录、空白导入、非生产 UI，以及已有 Makefile / CI 时的生成与漂移检查。
- 未要求整套接入时，不要把下面的依赖、Makefile、CI 段落当必做清单。

## 依赖

项目已有 `swag` / `gin-swagger` / `files` 时，沿用 `go.mod` 版本；CLI 与库同一版本。只改文档时不要升级。

首次接入且 `go.mod` 里没有这三项时，三个模块一起加上，版本固定为：

- `github.com/swaggo/swag v1.16.6`
- `github.com/swaggo/gin-swagger v1.6.1`
- `github.com/swaggo/files v1.0.1`

CLI：`go install github.com/swaggo/swag/cmd/swag@<go.mod 里的 swag 版本>`。首次接入用 `v1.16.6`。

## 目录

```text
docs/<api>/docs.go     # 提交；swag 生成，package 名由目录名决定，init 里 swag.Register
docs/<api>/swagger.*   # .gitignore，不提交
```

已有输出目录就用已有的。没有时用一个目录，例如 `docs/internal-api` → `package internal_api`。空白导入必须指向这个生成包。不要手改生成文件。不要再开第二个 `docs/<api>`。

## 全局注解

写在 `swag` 当作 general info 的入口文件上方，默认是仓库根目录 `main.go`：

```go
//	@title			Example Service API
//	@version		1.0
//	@description	This is the Example Service API.
//	@host			localhost:8000
//	@BasePath		/

// @securityDefinitions.apikey	ApiKeyAuth
// @in							header
// @name						Authorization
```

只在首次接入、且入口还没有这些注释时补。`@Security ApiKeyAuth` 只写在路由上挂了鉴权中间件的 handler。公开接口（登录、发码、健康检查）不要写。不要把 `Authorization` 再写成 `@Param`。

## Handler 注解

注释紧贴 handler 函数。`@Router` 写**最终对外 path**（把所有 `Group` 前缀拼进去），不是相对某个 group 的片段；方法与路由注册一致。同一函数挂多条路径就写多条 `@Router`。

```go
// @Tags			Orders
// @Summary		查询订单
// @Description	按状态筛选当前用户订单。只读，可安全重试。
// @Security		ApiKeyAuth
// @Produce		json
// @Param			status	query		string	false	"订单状态"	Enums(OPEN, CLOSED)	example(OPEN)
// @Success		200		{object}	dtos.OrderListResponse
// @Failure		400		{object}	existing.ErrorBody
// @Failure		401
// @Router			/v1/orders [get]
func (h *OrderHandler) List(c *gin.Context) {}
```

必写：

- `@Tags`、`@Summary`
- `@Description`：约束、副作用、成功与失败含义；鉴权是否需要、空值、语言回退、调用方要据此判断的行为
- 幂等：可安全重试，或写明非幂等及重试后果（频控、重复创建、待确认）
- `@Param` / `@Success` / `@Failure` / `@Router` 与真实绑定、返回类型、最终对外 path 一致
- 有 JSON body 时 `@Accept json`；上传时 `@Accept multipart/form-data`，文件参数用 `formData`
- 路径参数写成 `@Param id path ...`，名字与 `@Router` 的 `{id}` 一致
- header 只写在 handler 的 `@Param ... header`，不塞进 body DTO

`@ID` 可选。同文件或同模块已有 handler 在用，或两个操作会撞上默认 operationId 时再写。不要只因为示例里曾经出现过就每个接口都加。

`@Failure` 按代码能看到的错误体写，不要编新 DTO：

1. 已有命名错误结构体（或项目统一错误类型）→ `{object}` 用那个类型。
2. 实际返回的是已有的 `gin.H` / `map` / 匿名结构 → `{object}` 复用那个类型，不要另起名字。
3. 只能确定 HTTP status、没有可复用的 body 类型 → 只写 `@Failure 400`，不加 `{object}`。
4. 从代码看不出错误体 → 问用户，停在这里。不要猜，不要新建 `YourErrorBody`。

认证失败与权限不足若返回体不同，按上面 1–3 分别写；都看不到 body 就都只标 status。

上传：

```go
// @Accept		multipart/form-data
// @Param		file	formData	file	true	"文件"
```

## DTO

```go
Status  enums.OrderStatus   `json:"status" swaggertype:"string" example:"OPEN"`
Reasons []enums.RefuseReason `json:"reasons" swaggertype:"array,string" example:"[\"ID_WRONG\"]"`
```

- JSON body 里的自定义枚举：`swaggertype:"string"`（数组用 `array,string`），加 `example`；取值可写 `enums:"A,B"`。
- query / form 不要用底层为 `int` 的枚举直接绑定。DTO 字段用 `string`，handler 再解析；取值写在该 `@Param` 的 `Enums(...)`。
- 时间字段对外用秒级 Unix 时间戳。

## 生成

入口在根目录 `main.go` 时：

```bash
swag init --parseDependency -o ./docs/<api>
```

入口在别处时加 `-g`，例如 `-g cmd/api/main.go`。默认扫描目录不够时加 `-d`。`--parseDependency` 用来解析其他包里的请求/响应类型。输出目录用项目已有的；没有才新建一个。

已有 Makefile 生成目标就改那一条，不要另起名字。没有生成目标、且这次不是整套接入时，直接跑上面的命令，不要新增 Makefile。

只提交 `docs.go`。生成后 `git diff -- docs/<api>` 只应反映本次接口变更。

## 运行时

整套接入时，在注册路由的包里空白导入生成包，让 `init` 执行 `swag.Register`。Swagger UI 挂在**未加鉴权中间件**的已有公开 API 前缀上，且只在非生产注册。

生产判断用项目里已有的（现成函数、`Environment`、config、env）。没有现成判断时，与现有 env/config 字段对齐。不要新增一套 `isProd` 或新的环境开关。

```go
import (
	_ "example.com/service/docs/internal-api"
	swaggerFiles "github.com/swaggo/files"
	gs "github.com/swaggo/gin-swagger"
)

if !alreadyProd { // 替换成项目已有的生产判断
	public.GET("swagger/*any", gs.WrapHandler(swaggerFiles.Handler))
}
```

`public` 是项目已有的公开 API group。`@Router` 和这里一样写拼好前缀后的 path，例如 `GET /v1/swagger/*any`。生产环境不注册。只改注解时不要动这条路由。

## 漂移检查

只在整套接入、或项目已经有文档生成 CI 时处理。安装 **go.mod 里的** `swag` 版本（不是本文首次接入示例版），跑项目现有生成命令，然后：

```bash
git diff --exit-code -- docs/<api>
```

workflow 的 `paths` 若有 `!docs/**`，必须再写 `docs/<api>/**`，否则只改 `docs.go` 时 job 不会跑。注解或 DTO 文档元数据变了却没刷新 `docs.go`，这一步必须失败。

只补 handler 注解时：已有这条 CI 就保持原样；没有就不要新增。

## 常见错误

- 只改一个 handler 注解却顺手加依赖、Makefile 或 CI
- 手改 `docs/<api>/` 或提交 `swagger.json` / `swagger.yaml`
- 有鉴权的接口漏 `@Security`；公开接口多写 `@Security`；把 `Authorization` 写成普通参数
- `@Router` 写成 group 相对路径，漏了前缀
- 看不出错误体却编了新 DTO，或把 `@ID` 当成必写
- query/form 用 int 枚举直接绑定
- JSON 接口漏 `@Accept json`，或上传仍标 `json`
- 漏 `--parseDependency`，或入口不在 `./main.go` 却没加 `-g`
- 空白导入的包名与输出目录不一致；或新增了第二套 `docs/<api>`
- 按 OpenAPI 3 写注解或改生成格式
- 文档任务里升级了已有 swag 版本
- 新造生产判断；生产环境挂了 Swagger UI，或把 UI 挂到鉴权路由组
- CLI 版本和 `go.mod` 里的 `swag` 不一致
- CI 排除了 `docs/**` 却没把 `docs/<api>/**` 加回 `paths`
