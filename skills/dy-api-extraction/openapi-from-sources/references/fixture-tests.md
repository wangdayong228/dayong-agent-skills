# Fixture Tests (maintainers / CI only)

All test-only assets live under `test/` (gitignored). End users who install this skill via `npx skills add` do **not** receive `test/` — only this reference doc is tracked.

Production OpenAPI assembly is **Agent-driven** per `SKILL.md`. The scripts below are a deterministic reference generator and validators for offline regression — not the production path.

## Layout

```text
test/
  scripts/
    generate-openapi-from-sources.py   # reference generator (CoinGlass fixture)
    generate-openapi-from-sources.sh
    validate-readiness-output.sh
    test_generate_openapi_from_sources.py
  coinglass-fr-ohlc-history/
    fixture-input/                     # minimal Tier A/B materials
    expected/                          # golden readiness report
    expected-readiness.yaml
    expected-readiness-example-fallback.yaml
    verify.sh
```

Copy or restore `test/` locally before running checks (not shipped with skill install).

## Scenario: coinglass-fr-ohlc-history

Validates two behaviors for CoinGlass `fr-ohlc-histroy`:

1. **strict** — Schema gate **NO-GO**; report lists 4 user options; no `pipeline/openapi/openapi.yaml`
2. **example-fallback** (user option 2) — Schema gate **GO (example-fallback)**; `pipeline/openapi/openapi.yaml` with `x-inferred-from: example`

Extraction gate may be **GO**, but official response schemas are empty → strict assembly **NO-GO**.

### Input materials

**Default fixture (`fixture-input/`):**

```text
test/coinglass-fr-ohlc-history/fixture-input/
  pipeline/extract/raw/
  pipeline/extract/report.md   # optional
```

**Optional sibling (live re-fetch):**

```text
skills/dy-api-extraction/strict-api-extraction/test/coinglass-fr-ohlc-history/
```

## Offline verification (no agent)

```bash
chmod +x skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/verify.sh
chmod +x skills/dy-api-extraction/openapi-from-sources/test/scripts/*.sh
./skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/verify.sh
```

`verify.sh`:

1. Checks skill structure and golden report
2. Runs `validate-readiness-output.sh` on golden output
3. Runs reference generator from `fixture-input/` (strict → NO-GO)
4. Runs reference generator with `--strictness example-fallback` (GO)
5. Asserts strict rerun does not delete a prior fallback `pipeline/openapi/openapi.yaml`

## Reference generator (manual)

Strict mode:

```bash
OUT=$(mktemp -d)
./skills/dy-api-extraction/openapi-from-sources/test/scripts/generate-openapi-from-sources.sh \
  skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/fixture-input \
  "$OUT"
ls -la "$OUT/pipeline/extract" "$OUT/pipeline/openapi" 2>/dev/null || true
```

Example-fallback:

```bash
OUT=$(mktemp -d)
./skills/dy-api-extraction/openapi-from-sources/test/scripts/generate-openapi-from-sources.sh \
  skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/fixture-input \
  "$OUT" \
  --strictness example-fallback
ls -la "$OUT/pipeline/openapi"
```

## Unit tests

```bash
python3 -m unittest \
  skills/dy-api-extraction/openapi-from-sources/test/scripts/test_generate_openapi_from_sources.py
```

## Validate agent run output (optional)

Prompt agent with strict mode, material root `test/coinglass-fr-ohlc-history/fixture-input`, output e.g. `/tmp/coinglass-openapi-run`.

Strict output:

```bash
./skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/verify.sh \
  /tmp/coinglass-openapi-run
```

Example-fallback output:

```bash
./skills/dy-api-extraction/openapi-from-sources/test/scripts/validate-readiness-output.sh \
  /tmp/coinglass-openapi-run \
  skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/expected-readiness-example-fallback.yaml
```

## Golden expectations

Agent/run output path (production layout): `pipeline/openapi/readiness-report.md` and `pipeline/openapi/openapi.yaml`.

Fixture goldens live under `test/.../expected/` (basename may differ from production path; validators compare content / YAML gates):

- `test/coinglass-fr-ohlc-history/expected/openapi-readiness-report.md` (golden for readiness report content)
- `test/coinglass-fr-ohlc-history/expected-readiness.yaml`
- `test/coinglass-fr-ohlc-history/expected-readiness-example-fallback.yaml`
