# Strict API Extraction: CoinGlass fr-ohlc-histroy

## Summary
- Target: OpenAPI 3.x
- Entry URL: https://docs.coinglass.com/v4.0-zh/reference/getting-started-with-your-api
- Scope: `fr-ohlc-histroy`（资金费率历史 K 线）单端点 + 认证/错误/交叉引用
- Tier A raw: `source/raw/` (5 files)
- Tier B snapshots: `source/snapshots/` (1 file)
- Tier B auxiliary: `.firecrawl/` (none)
- Coverage: sourced 12 / total 13
- Gate: **GO**（1 项为文档自身缺口，非抓取失败）

## Source Index
| File | Tier | page_type | source_url | capture_method | Role |
| --- | --- | --- | --- | --- | --- |
| source/raw/llms.txt | A | machine-spec | https://docs.coinglass.com/llms.txt | serverFetch | index |
| source/raw/fr-ohlc-histroy.md | A | machine-spec | https://docs.coinglass.com/reference/fr-ohlc-histroy.md | serverFetch | endpoint-ref (含内嵌 OpenAPI) |
| source/snapshots/fr-ohlc-histroy-zh.md | B | spa | https://docs.coinglass.com/v4.0-zh/reference/fr-ohlc-histroy | ego-browser-snapshotText | endpoint-ref (中文 SPA) |
| source/raw/authentication.md | A | machine-spec | https://docs.coinglass.com/reference/authentication.md | serverFetch | auth |
| source/raw/responses-error-codes.md | A | machine-spec | https://docs.coinglass.com/reference/responses-error-codes.md | serverFetch | errors |
| source/raw/instruments.md | A | machine-spec | https://docs.coinglass.com/reference/instruments.md | serverFetch | cross-ref (exchange/symbol 枚举来源) |

## Coverage Report
| Element | Status | Source (Tier A/B path:line) | Notes |
| --- | --- | --- | --- |
| GET /api/futures/funding-rate/history | sourced | source/raw/fr-ohlc-histroy.md:73-77 | operationId: `fr-ohlc-histroy` |
| Base URL | sourced | source/raw/fr-ohlc-histroy.md:55-56 | `https://open-api-v4.coinglass.com` |
| Query: exchange (required) | sourced | source/raw/fr-ohlc-histroy.md:80-87 | 枚举值见 instruments 交叉引用 |
| Query: symbol (required) | sourced | source/raw/fr-ohlc-histroy.md:90-97 | 枚举值见 instruments 交叉引用 |
| Query: interval (required) | sourced | source/raw/fr-ohlc-histroy.md:100-107 | 1m,3m,5m,15m,30m,1h,4h,6h,8h,12h,1d,1w |
| Query: limit (optional) | sourced | source/raw/fr-ohlc-histroy.md:110-118 | Default 1000, Max 1000；SPA 表单显示 "Defaults to 10" 与正文不一致 |
| Query: start_time (optional) | sourced | source/raw/fr-ohlc-histroy.md:121-129 | 毫秒时间戳 |
| Query: end_time (optional) | sourced | source/raw/fr-ohlc-histroy.md:132-140 | 毫秒时间戳 |
| Request body | N/A | — | GET 无 body |
| Response 200 body shape | sourced | source/raw/fr-ohlc-histroy.md:20-41,150 | `{code,msg,data:[{time,open,high,low,close}]}`；内嵌 OpenAPI schema properties 为空 |
| Response 400 | sourced | source/raw/fr-ohlc-histroy.md:160-171 | 示例为空 `{}` |
| Response field types (formal schema) | missing_from_docs | source/raw/fr-ohlc-histroy.md:153-157 | 内嵌 OpenAPI 200 schema 为 `{}`，类型仅能从示例推断 |
| Authentication CG-API-KEY header | sourced | source/raw/fr-ohlc-histroy.md:60-63; source/raw/authentication.md:22-33 | apiKey in header |
| Global error codes (401/429/500 等) | sourced | source/raw/responses-error-codes.md:11-21 | 端点页仅列 200/400 |
| Plan interval limits | sourced | source/raw/fr-ohlc-histroy.md:11-14 | Hobbyist >=4h, Startup >=30m |
| Cross-ref: supported exchange/pairs | sourced | source/raw/instruments.md:5-7,80-97 | 参数 description 指向此 API |

## Unresolved Items
| Item | Status | Notes |
| --- | --- | --- |
| Response 200 formal JSON Schema | missing_from_docs | 官方内嵌 OpenAPI 的 `schema.properties` 为空；仅有 example |
| limit 默认值 SPA vs markdown | unresolved_ref | Tier B snapshot 表单显示 default 10；Tier A markdown 写 default 1000 |

## Discovery Log
- Round 1: 从 entry URL 探测 `llms.txt`（Tier A），发现 `fr-ohlc-histroy.md`
- Round 1: `serverFetch` 抓取 endpoint + auth + errors
- Round 1: ego-browser 抓取中文 SPA 页面 snapshot
- Round 2: 补抓 `instruments.md`（exchange/symbol 交叉引用）
- `/openapi.json` 等全局 spec 路径不存在；各 endpoint 页内嵌 partial OpenAPI

## Next Step
Extraction Gate **GO** — 单端点 Tier A/B 已覆盖。Schema 组装请用 `openapi-from-sources`（strict 模式）；本素材 Response 200 正式 schema 为空，预期 Schema gate **NO-GO**，勿从 example 推断类型。
