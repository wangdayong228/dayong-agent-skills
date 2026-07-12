# Test: coinglass-fr-ohlc-history (strict NO-GO + generation)

验证 `openapi-from-sources` 对 CoinGlass `fr-ohlc-histroy` 素材的两段行为：

1. strict 模式：**Schema gate NO-GO**，报告写出 4 个用户选项，不写 `schema/openapi.yaml`
2. 用户选项 2（example-fallback）：**Schema gate GO (example-fallback)**，根据官方 example 生成带 `x-inferred-from: example` 的 `schema/openapi.yaml`

## 输入素材

**Committed fixture（CI/离线默认）：**

```text
test/coinglass-fr-ohlc-history/fixture-input/
  source/raw/
  docs/api-source-report.md   # optional
```

**Sibling fixture（可选，本地 live 重抓）：**

```text
skills/dy-api-extraction/strict-api-extraction/test/coinglass-fr-ohlc-history/
```

Extraction Gate 可为 **GO**，但 Response 200 正式 schema 为空 → strict schema 组装 **NO-GO**。若用户明确选择编号 2，则允许从 Tier A/B example 回退生成 schema。

## 离线校验（无需 agent）

```bash
chmod +x skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/verify.sh
chmod +x skills/dy-api-extraction/openapi-from-sources/scripts/*.sh
./skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/verify.sh
```

`verify.sh` 会：

1. 校验 skill 结构与 golden report
2. 对 golden 跑完整 `validate-readiness-output.sh`
3. 从 `fixture-input/` 运行 `generate-openapi-from-sources.sh` 生成 readiness 报告
4. 断言 strict 分支 `schema_gate=NO-GO` 且无 `schema/openapi.yaml`
5. 断言 example-fallback 分支 `schema_gate=GO (example-fallback)` 且 `schema/openapi.yaml` 含 `x-inferred-from: example`

## 单独运行生成器

```bash
OUT=$(mktemp -d)
./skills/dy-api-extraction/openapi-from-sources/scripts/generate-openapi-from-sources.sh \
  skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/fixture-input \
  "$OUT"
ls -la "$OUT/docs" "$OUT/schema" 2>/dev/null || true
```

用户选项 2（example-fallback）：

```bash
OUT=$(mktemp -d)
./skills/dy-api-extraction/openapi-from-sources/scripts/generate-openapi-from-sources.sh \
  skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/fixture-input \
  "$OUT" \
  --strictness example-fallback
ls -la "$OUT/docs" "$OUT/schema"
```

## Live agent 运行（可选）

```text
使用 openapi-from-sources，strict 模式，素材目录：
skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/fixture-input
scope: GET /api/futures/funding-rate/history
输出到：/tmp/coinglass-openapi-run
```

校验 agent strict 输出：

```bash
./skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/verify.sh /tmp/coinglass-openapi-run
```

校验 agent example-fallback 输出：

```bash
./skills/dy-api-extraction/openapi-from-sources/scripts/validate-readiness-output.sh \
  /tmp/coinglass-openapi-run \
  skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/expected-readiness-example-fallback.yaml
```

## Golden 期望

见 `expected/openapi-readiness-report.md` 与 `expected-readiness.yaml`。
