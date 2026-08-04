# typed-sdk-from-openapi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add repo-local skill `typed-sdk-from-openapi` that generates a Go raw SDK (oapi-codegen) plus a refined typed client with user-confirmed idempotency-aware retry policy.

**Architecture:** Pin OpenAPI → draft `retry-policy.draft.yaml` → user batch confirm → `retry-policy.yaml` → oapi-codegen to `generated/` → `internal/transport` RetryPolicyRoundTripper → hand-written `pkg/client` facade. Offline verification via coinglass fixture + `verify.sh`.

**Tech Stack:** Go 1.22+, oapi-codegen v2, Python 3.11+ (draft script), bash validators, PyYAML

## Global Constraints

- **Language:** Go; codegen tool `oapi-codegen` v2.
- **Input:** `schema/openapi.yaml` from upstream with schema Gate **GO** (strict or user-approved example-fallback).
- **Generated code:** committed, reproducible, never hand-edited.
- **Public API:** only `pkg/client/` exported; `generated/` internal to module.
- **Retry default:** unlisted or unreviewed operations → **non_retryable** at runtime.
- **Retry confirmation:** batch interactive review required before SDK Gate **GO**.
- **Retriable status codes:** 429, 502, 503, 504 + transient network errors.
- **Retry budget:** max 3 attempts, exponential backoff with full jitter.
- **Write safety:** POST/PATCH/DELETE/PUT draft defaults to `non_retryable`; `retryable` on writes requires explicit user override with reason in report.

---

### Task 1: Skill Scaffold & Reference Docs

**Files:**
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/references/retry-policy-schema.md`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/references/sdk-readiness-report-template.md`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/references/refined-client-patterns.md`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/agents/openai.yaml`

**Interfaces:**
- Consumes: design spec at `docs/superpowers/specs/2026-07-12-typed-sdk-from-openapi-design.md`
- Produces: reference templates consumed by SKILL.md and agent runs

- [ ] **Step 1: Create reference directory**

```bash
mkdir -p skills/dy-api-extraction/typed-sdk-from-openapi/references
mkdir -p skills/dy-api-extraction/typed-sdk-from-openapi/agents
```

- [ ] **Step 2: Write retry-policy-schema.md**

```markdown
# retry-policy.yaml Schema (v1)

```yaml
version: 1
defaults:
  unlisted: non_retryable   # retryable | non_retryable

operations:
  <operationId>:
    method: GET
    path: /api/example
    policy: retryable       # retryable | non_retryable | idempotent_key_required | unreviewed
    idempotency_header: ""  # required when policy is idempotent_key_required
    reason: "human-readable justification"
    confirmed: false        # true only after user batch approval
```

Rules:
- Every in-scope OpenAPI operation must appear under `operations`.
- SDK Gate **GO** requires `confirmed: true` and `policy != unreviewed` for all operations.
- `retryable` on POST/PATCH/DELETE requires override reason recorded in sdk-readiness-report.
```

- [ ] **Step 3: Write sdk-readiness-report-template.md**

```markdown
# SDK Readiness Report

## Run Metadata
- material_root:
- spec_path: schema/openapi.yaml
- spec_sha256:
- openapi_version:
- operation_count:
- oapi_codegen_version:
- upstream_schema_gate:

## Preflight Checklist
| Check | Status | Notes |
| --- | --- | --- |
| schema/openapi.yaml exists | | |
| operationId unique (or derived) | | |
| servers.url present | | |
| security scheme documented | | |

## Retry Policy Review
- draft_path: sdk/retry-policy.draft.yaml
- confirmed_path: sdk/retry-policy.yaml
- user_approval:
- overrides:

## SDK Gate
**Verdict:** GO | NO-GO

## Deliverables
- [ ] generated/
- [ ] internal/transport/
- [ ] pkg/client/
- [ ] sdk/retry-policy.yaml
- [ ] scripts/regen.sh

## Regen
```bash
./scripts/regen.sh
go test ./...
```
```

- [ ] **Step 4: Write refined-client-patterns.md**

```markdown
# Refined Go Client Patterns

## Module layout
- `generated/` — oapi-codegen output; never import from outside module except internal adapters.
- `internal/transport/` — RoundTripper, typed errors, operation context.
- `pkg/client/` — only public API.

## Constructor
```go
func New(cfg Config) (*Client, error)
```

## Naming
- Prefer domain names: `FundingRateHistory` over `GetApiFuturesFundingRateHistory`.
- Use parameter structs: `FundingRateHistoryParams`.

## Operation context (required for retry lookup)
```go
ctx = transport.WithOperationID(ctx, "GetFundingRateHistory")
```

## Do NOT
- Re-export generated types in public method signatures when mappable.
- Patch generated files.
```

- [ ] **Step 5: Write agents/openai.yaml**

```yaml
interface:
  display_name: "Typed SDK From OpenAPI"
  short_description: "Generate Go typed SDK from pinned OpenAPI with confirmed retry policy."
  default_prompt: "Use typed-sdk-from-openapi on schema/openapi.yaml: draft retry-policy, request user batch confirmation, then generate oapi-codegen raw SDK, transport retry layer, and refined pkg/client."
```

- [ ] **Step 6: Commit**

```bash
git add skills/dy-api-extraction/typed-sdk-from-openapi/references/ \
        skills/dy-api-extraction/typed-sdk-from-openapi/agents/
git commit -m "feat(typed-sdk-from-openapi): add reference docs and agent metadata"
```

---

### Task 2: draft-retry-policy.py + Unit Tests

**Files:**
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/scripts/draft-retry-policy.py`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/scripts/test_draft_retry_policy.py`
- Test: `skills/dy-api-extraction/typed-sdk-from-openapi/scripts/test_draft_retry_policy.py`

**Interfaces:**
- Consumes: OpenAPI 3.x YAML at `schema/openapi.yaml`
- Produces: `draft_retry_policy(openapi_path: str) -> dict` written as YAML; operation keys are `operationId` strings

- [ ] **Step 1: Write failing test**

```python
# scripts/test_draft_retry_policy.py
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from draft_retry_policy import draft_retry_policy, derive_operation_id


SAMPLE_OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "t", "version": "1"},
    "paths": {
        "/api/read": {
            "get": {
                "operationId": "GetRead",
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/api/write": {
            "post": {
                "operationId": "CreateWrite",
                "responses": {"201": {"description": "created"}},
            }
        },
        "/api/upsert": {
            "put": {
                "parameters": [
                    {
                        "name": "Idempotency-Key",
                        "in": "header",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
    },
}


class DraftRetryPolicyTest(unittest.TestCase):
    def test_derive_operation_id(self):
        self.assertEqual(
            derive_operation_id("get", "/api/foo/bar"),
            "GetApiFooBar",
        )

    def test_draft_policies(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "openapi.yaml"
            spec.write_text(yaml.safe_dump(SAMPLE_OPENAPI), encoding="utf-8")
            result = draft_retry_policy(str(spec))
        ops = result["operations"]
        self.assertEqual(ops["GetRead"]["policy"], "retryable")
        self.assertEqual(ops["CreateWrite"]["policy"], "non_retryable")
        upsert_id = derive_operation_id("put", "/api/upsert")
        self.assertEqual(ops[upsert_id]["policy"], "idempotent_key_required")
        self.assertEqual(ops[upsert_id]["idempotency_header"], "Idempotency-Key")
        self.assertFalse(ops["GetRead"]["confirmed"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/dy-api-extraction/typed-sdk-from-openapi/scripts && python3 -m unittest test_draft_retry_policy.py -v`

Expected: FAIL with `ModuleNotFoundError: draft_retry_policy`

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""Draft retry-policy.yaml from OpenAPI 3.x spec."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

IDEMPOTENCY_HEADER_NAMES = {
    "idempotency-key",
    "x-idempotency-key",
    "x-request-id",
}

READ_METHODS = {"get", "head", "options"}
WRITE_METHODS = {"post", "put", "patch", "delete"}


def derive_operation_id(method: str, path: str) -> str:
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", path.strip("/")) if p]
    tokens = [method.lower(), *parts]
    return "".join(t[:1].upper() + t[1:] for t in tokens if t)


def _find_idempotency_header(operation: dict[str, Any]) -> str | None:
    for param in operation.get("parameters") or []:
        if param.get("in") != "header":
            continue
        name = str(param.get("name", ""))
        if name.lower() in IDEMPOTENCY_HEADER_NAMES:
            return name
    return None


def _suggest_policy(method: str, operation: dict[str, Any]) -> tuple[str, str, str]:
    method = method.lower()
    header = _find_idempotency_header(operation) or ""
    if operation.get("x-idempotent") is True:
        return "retryable", header, "x-idempotent: true on operation"
    if header:
        return "idempotent_key_required", header, f"header parameter {header}"
    if method in READ_METHODS:
        return "retryable", "", f"read-only {method.upper()}"
    if method in WRITE_METHODS:
        return "non_retryable", "", f"state-changing {method.upper()}"
    return "unreviewed", "", f"unclassified method {method.upper()}"


def draft_retry_policy(openapi_path: str) -> dict[str, Any]:
    spec = yaml.safe_load(Path(openapi_path).read_text(encoding="utf-8"))
    operations: dict[str, Any] = {}
    for path, path_item in (spec.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in READ_METHODS | WRITE_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            op_id = operation.get("operationId") or derive_operation_id(method, path)
            policy, header, reason = _suggest_policy(method, operation)
            operations[op_id] = {
                "method": method.upper(),
                "path": path,
                "policy": policy,
                "idempotency_header": header,
                "reason": reason,
                "confirmed": False,
            }
    return {
        "version": 1,
        "defaults": {"unlisted": "non_retryable"},
        "operations": dict(sorted(operations.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft retry-policy.yaml from OpenAPI")
    parser.add_argument("openapi_path")
    parser.add_argument("output_path")
    args = parser.parse_args()
    doc = draft_retry_policy(args.openapi_path)
    out = Path(args.output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"operations={len(doc['operations'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/dy-api-extraction/typed-sdk-from-openapi/scripts && python3 -m unittest test_draft_retry_policy.py -v`

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
chmod +x skills/dy-api-extraction/typed-sdk-from-openapi/scripts/draft-retry-policy.py
git add skills/dy-api-extraction/typed-sdk-from-openapi/scripts/
git commit -m "feat(typed-sdk-from-openapi): add draft-retry-policy script with tests"
```

---

### Task 3: validate-sdk-readiness.sh

**Files:**
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/scripts/validate-sdk-readiness.sh`
- Test: manual via Task 7 verify.sh

**Interfaces:**
- Consumes: `run_dir`, optional `expected_retry_policy.yaml`
- Produces: exit 0 on GO; prints `sdk_gate=GO|NO-GO`

- [ ] **Step 1: Write validator script**

```bash
#!/usr/bin/env bash
# validate-sdk-readiness.sh RUN_DIR [EXPECTED_RETRY_POLICY_YAML]
set -euo pipefail

RUN_DIR="${1:?run dir required}"
EXPECTED_POLICY="${2:-}"

fail() { echo "validate-sdk-readiness: $*" >&2; exit 1; }

[[ -f "$RUN_DIR/schema/openapi.yaml" ]] || fail "missing schema/openapi.yaml"
[[ -f "$RUN_DIR/docs/sdk-readiness-report.md" ]] || fail "missing docs/sdk-readiness-report.md"

if [[ ! -f "$RUN_DIR/sdk/retry-policy.yaml" ]]; then
  echo "sdk_gate=NO-GO"
  exit 0
fi

python3 - <<'PY' "$RUN_DIR/sdk/retry-policy.yaml"
import sys, yaml
from pathlib import Path
doc = yaml.safe_load(Path(sys.argv[1]).read_text())
ops = doc.get("operations") or {}
for op_id, entry in ops.items():
    if entry.get("policy") == "unreviewed":
        print(f"unreviewed:{op_id}")
        sys.exit(2)
    if not entry.get("confirmed"):
        print(f"unconfirmed:{op_id}")
        sys.exit(3)
print(f"operations={len(ops)}")
PY

if [[ -n "$EXPECTED_POLICY" ]]; then
  python3 - <<'PY' "$RUN_DIR/sdk/retry-policy.yaml" "$EXPECTED_POLICY"
import sys, yaml
from pathlib import Path
actual = yaml.safe_load(Path(sys.argv[1]).read_text())
expected = yaml.safe_load(Path(sys.argv[2]).read_text())
for op_id, exp in (expected.get("operations") or {}).items():
    act = (actual.get("operations") or {}).get(op_id)
    if not act:
        raise SystemExit(f"missing operation {op_id}")
    if act.get("policy") != exp.get("policy"):
        raise SystemExit(f"policy mismatch {op_id}")
PY
fi

for path in \
  "$RUN_DIR/generated/client.gen.go" \
  "$RUN_DIR/internal/transport/retry.go" \
  "$RUN_DIR/pkg/client/client.go" \
  "$RUN_DIR/scripts/regen.sh"; do
  [[ -f "$path" ]] || fail "missing deliverable $path"
done

echo "sdk_gate=GO"
```

- [ ] **Step 2: Make executable and smoke-test NO-GO**

```bash
chmod +x skills/dy-api-extraction/typed-sdk-from-openapi/scripts/validate-sdk-readiness.sh
TMP=$(mktemp -d)
mkdir -p "$TMP/schema" "$TMP/docs"
echo "openapi: 3.0.3" > "$TMP/schema/openapi.yaml"
echo "# report" > "$TMP/docs/sdk-readiness-report.md"
skills/dy-api-extraction/typed-sdk-from-openapi/scripts/validate-sdk-readiness.sh "$TMP" | grep sdk_gate=NO-GO
```

Expected: `sdk_gate=NO-GO`

- [ ] **Step 3: Commit**

```bash
git add skills/dy-api-extraction/typed-sdk-from-openapi/scripts/validate-sdk-readiness.sh
git commit -m "feat(typed-sdk-from-openapi): add sdk readiness validator"
```

---

### Task 4: regen-generated.sh + Fixture OpenAPI

**Files:**
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/scripts/regen-generated.sh`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/schema/openapi.yaml`

**Interfaces:**
- Consumes: `schema/openapi.yaml` in run dir
- Produces: `generated/client.gen.go`

- [ ] **Step 1: Generate fixture openapi.yaml from upstream generator**

```bash
OPENAPI_OUT=$(mktemp -d)
./skills/dy-api-extraction/openapi-from-sources/scripts/generate-openapi-from-sources.sh \
  skills/dy-api-extraction/openapi-from-sources/test/coinglass-fr-ohlc-history/fixture-input \
  "$OPENAPI_OUT" \
  --strictness example-fallback
mkdir -p skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/schema
cp "$OPENAPI_OUT/schema/openapi.yaml" \
  skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/schema/openapi.yaml
```

- [ ] **Step 2: Write regen-generated.sh**

```bash
#!/usr/bin/env bash
# regen-generated.sh [RUN_DIR]
set -euo pipefail
RUN_DIR="${1:-.}"
SPEC="$RUN_DIR/schema/openapi.yaml"
OUT="$RUN_DIR/generated/client.gen.go"
mkdir -p "$RUN_DIR/generated"
oapi-codegen -generate types,client -package generated -o "$OUT" "$SPEC"
echo "generated=$OUT"
```

- [ ] **Step 3: Install oapi-codegen and run regen in temp module**

```bash
go install github.com/oapi-codegen/oapi-codegen/v2/cmd/oapi-codegen@latest
FIXTURE=skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input
bash skills/dy-api-extraction/typed-sdk-from-openapi/scripts/regen-generated.sh "$FIXTURE"
test -f "$FIXTURE/generated/client.gen.go"
```

Expected: generated file exists

- [ ] **Step 4: Commit**

```bash
chmod +x skills/dy-api-extraction/typed-sdk-from-openapi/scripts/regen-generated.sh
git add skills/dy-api-extraction/typed-sdk-from-openapi/scripts/regen-generated.sh \
        skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/schema/
git commit -m "feat(typed-sdk-from-openapi): add regen script and coinglass fixture openapi"
```

Note: commit `generated/client.gen.go` in Task 7 after full module scaffold, not here (fixture module incomplete).

---

### Task 5: Transport Layer (TDD)

**Files:**
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/go.mod`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/internal/transport/context.go`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/internal/transport/policy.go`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/internal/transport/retry.go`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/internal/transport/errors.go`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/internal/transport/retry_test.go`
- Test: `internal/transport/retry_test.go`

**Interfaces:**
- Consumes: `PolicyRegistry` map keyed by operationId; `WithOperationID(ctx, id)`
- Produces: `NewRetryRoundTripper(base http.RoundTripper, registry PolicyRegistry, cfg RetryConfig) http.RoundTripper`

- [ ] **Step 1: Write go.mod**

```go
module github.com/dayong-agent-skills/coinglass-sdk-fixture

go 1.22

require gopkg.in/yaml.v3 v3.0.1
```

- [ ] **Step 2: Write failing retry tests**

```go
// internal/transport/retry_test.go
package transport_test

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"

	"github.com/dayong-agent-skills/coinglass-sdk-fixture/internal/transport"
)

type countingTransport struct{ n atomic.Int32 }

func (c *countingTransport) RoundTrip(*http.Request) (*http.Response, error) {
	c.n.Add(1)
	return &http.Response{
		StatusCode: 503,
		Body:       io.NopCloser(strings.NewReader("")),
		Header:     make(http.Header),
	}, nil
}

func TestRetryableRetriesOn503(t *testing.T) {
	base := &countingTransport{}
	reg := transport.PolicyRegistry{
		"GetRead": {Policy: transport.PolicyRetryable},
	}
	rt := transport.NewRetryRoundTripper(base, reg, transport.RetryConfig{MaxAttempts: 3})
	req, _ := http.NewRequest(http.MethodGet, "http://example.com", nil)
	req = req.WithContext(transport.WithOperationID(context.Background(), "GetRead"))
	_, _ = rt.RoundTrip(req)
	if base.n.Load() != 3 {
		t.Fatalf("attempts=%d want 3", base.n.Load())
	}
}

func TestNonRetryableSingleAttempt(t *testing.T) {
	base := &countingTransport{}
	reg := transport.PolicyRegistry{
		"CreateWrite": {Policy: transport.PolicyNonRetryable},
	}
	rt := transport.NewRetryRoundTripper(base, reg, transport.RetryConfig{MaxAttempts: 3})
	req, _ := http.NewRequest(http.MethodPost, "http://example.com", nil)
	req = req.WithContext(transport.WithOperationID(context.Background(), "CreateWrite"))
	_, _ = rt.RoundTrip(req)
	if base.n.Load() != 1 {
		t.Fatalf("attempts=%d want 1", base.n.Load())
	}
}

func TestIdempotentKeyRequiredWithoutHeaderNoRetry(t *testing.T) {
	base := &countingTransport{}
	reg := transport.PolicyRegistry{
		"PutUpsert": {
			Policy:            transport.PolicyIdempotentKeyRequired,
			IdempotencyHeader: "Idempotency-Key",
		},
	}
	rt := transport.NewRetryRoundTripper(base, reg, transport.RetryConfig{MaxAttempts: 3})
	req, _ := http.NewRequest(http.MethodPut, "http://example.com", nil)
	req = req.WithContext(transport.WithOperationID(context.Background(), "PutUpsert"))
	_, _ = rt.RoundTrip(req)
	if base.n.Load() != 1 {
		t.Fatalf("attempts=%d want 1", base.n.Load())
	}
}

func TestIdempotentKeyRequiredWithHeaderRetries(t *testing.T) {
	base := &countingTransport{}
	reg := transport.PolicyRegistry{
		"PutUpsert": {
			Policy:            transport.PolicyIdempotentKeyRequired,
			IdempotencyHeader: "Idempotency-Key",
		},
	}
	rt := transport.NewRetryRoundTripper(base, reg, transport.RetryConfig{MaxAttempts: 3})
	req, _ := http.NewRequest(http.MethodPut, "http://example.com", nil)
	req.Header.Set("Idempotency-Key", "abc")
	req = req.WithContext(transport.WithOperationID(context.Background(), "PutUpsert"))
	_, _ = rt.RoundTrip(req)
	if base.n.Load() != 3 {
		t.Fatalf("attempts=%d want 3", base.n.Load())
	}
}
```

Add `import "strings"` to test file.

- [ ] **Step 3: Run tests to verify failure**

Run: `cd skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input && go test ./internal/transport/... -v`

Expected: FAIL (packages/files missing)

- [ ] **Step 4: Implement transport package**

```go
// internal/transport/context.go
package transport

import "context"

type ctxKey struct{}

func WithOperationID(ctx context.Context, operationID string) context.Context {
	return context.WithValue(ctx, ctxKey{}, operationID)
}

func OperationIDFromContext(ctx context.Context) (string, bool) {
 v, ok := ctx.Value(ctxKey{}).(string)
 return v, ok && v != ""
}
```

```go
// internal/transport/policy.go
package transport

type Policy string

const (
	PolicyRetryable              Policy = "retryable"
	PolicyNonRetryable           Policy = "non_retryable"
	PolicyIdempotentKeyRequired  Policy = "idempotent_key_required"
)

type OperationPolicy struct {
	Policy            Policy
	IdempotencyHeader string
}

type PolicyRegistry map[string]OperationPolicy

func (r PolicyRegistry) ForOperation(id string) OperationPolicy {
	if p, ok := r[id]; ok {
		return p
	}
	return OperationPolicy{Policy: PolicyNonRetryable}
}
```

```go
// internal/transport/retry.go
package transport

import (
	"math/rand"
	"net/http"
	"time"
)

type RetryConfig struct {
	MaxAttempts int
	BaseDelay   time.Duration
}

func NewRetryRoundTripper(base http.RoundTripper, registry PolicyRegistry, cfg RetryConfig) http.RoundTripper {
	if base == nil {
		base = http.DefaultTransport
	}
	if cfg.MaxAttempts <= 0 {
		cfg.MaxAttempts = 3
	}
	if cfg.BaseDelay <= 0 {
		cfg.BaseDelay = 100 * time.Millisecond
	}
	return &retryRoundTripper{base: base, registry: registry, cfg: cfg}
}

type retryRoundTripper struct {
	base     http.RoundTripper
	registry PolicyRegistry
	cfg      RetryConfig
}

func (r *retryRoundTripper) RoundTrip(req *http.Request) (*http.Response, error) {
	opID, _ := OperationIDFromContext(req.Context())
	policy := r.registry.ForOperation(opID)
	max := 1
	if r.shouldRetry(policy, req) {
		max = r.cfg.MaxAttempts
	}
	var lastResp *http.Response
	var lastErr error
	for attempt := 1; attempt <= max; attempt++ {
		resp, err := r.base.RoundTrip(req)
		lastResp, lastErr = resp, err
		if !r.canRetryAttempt(policy, req, resp, err) || attempt == max {
			return resp, err
		}
		time.Sleep(r.backoff(attempt, resp))
	}
	return lastResp, lastErr
}

func (r *retryRoundTripper) shouldRetry(policy OperationPolicy, req *http.Request) bool {
	switch policy.Policy {
	case PolicyRetryable:
		return true
	case PolicyIdempotentKeyRequired:
		if policy.IdempotencyHeader == "" {
			return false
		}
		return req.Header.Get(policy.IdempotencyHeader) != ""
	default:
		return false
	}
}

func (r *retryRoundTripper) canRetryAttempt(policy OperationPolicy, req *http.Request, resp *http.Response, err error) bool {
	if !r.shouldRetry(policy, req) {
		return false
	}
	if err != nil {
		return true
	}
	if resp == nil {
		return false
	}
	switch resp.StatusCode {
	case 429, 502, 503, 504:
		return true
	default:
		return false
	}
}

func (r *retryRoundTripper) backoff(attempt int, resp *http.Response) time.Duration {
	if resp != nil {
		if ra := resp.Header.Get("Retry-After"); ra != "" {
			if sec, err := time.ParseDuration(ra + "s"); err == nil && sec <= 60*time.Second {
				return sec
			}
		}
	}
	max := float64(r.cfg.BaseDelay) * float64(1<<(attempt-1))
	jitter := rand.Float64() * max
	return time.Duration(jitter)
}
```

```go
// internal/transport/errors.go
package transport

import "fmt"

type APIError struct {
	Kind       string
	StatusCode int
	Body       []byte
}

func (e *APIError) Error() string {
	return fmt.Sprintf("api error kind=%s status=%d", e.Kind, e.StatusCode)
}
```

- [ ] **Step 5: Run tests to verify pass**

Run: `cd skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input && go test ./internal/transport/... -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/
git commit -m "feat(typed-sdk-from-openapi): add retry transport with tests"
```

---

### Task 6: Refined Client (pkg/client)

**Files:**
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/pkg/client/client.go`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/pkg/client/funding_rate.go`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/pkg/client/client_test.go`
- Modify: use generated client from Task 4 regen output

**Interfaces:**
- Consumes: `generated.ClientWithResponses`, `transport.NewRetryRoundTripper`, `PolicyRegistry` loaded from YAML
- Produces: `client.New(cfg Config) (*Client, error)`, `(*Client) FundingRateHistory(ctx, params FundingRateHistoryParams) (*FundingRateHistoryResult, error)`

- [ ] **Step 1: Regenerate and write failing client test**

```go
// pkg/client/client_test.go
package client_test

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/dayong-agent-skills/coinglass-sdk-fixture/pkg/client"
)

func TestFundingRateHistoryReturnsData(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(200)
		_, _ = w.Write([]byte(`{"code":"0","data":[]}`))
	}))
	defer srv.Close()

	c, err := client.New(client.Config{BaseURL: srv.URL, APIKey: "k"})
	if err != nil {
		t.Fatal(err)
	}
	_, err = c.FundingRateHistory(context.Background(), client.FundingRateHistoryParams{
		Symbol: "BTCUSDT",
	})
	if err != nil {
		t.Fatal(err)
	}
}
```

- [ ] **Step 2: Run test to verify failure**

Run: `go test ./pkg/client/... -v`

Expected: FAIL (client not defined)

- [ ] **Step 3: Implement client.go and funding_rate.go**

Implement `Config`, `New`, load policy registry from `sdk/retry-policy.yaml`, wire generated client with custom HTTP client using retry transport, attach operation ID per call.

Key pattern in `funding_rate.go`:

```go
func (c *Client) FundingRateHistory(ctx context.Context, params FundingRateHistoryParams) (*FundingRateHistoryResult, error) {
	const op = "GetFundingRateHistory" // must match registry operationId from openapi
	ctx = transport.WithOperationID(ctx, op)
	// call generated client method; map response to FundingRateHistoryResult
}
```

Match actual generated operationId from `generated/client.gen.go` after regen — update const if generator differs.

- [ ] **Step 4: Run full module tests**

Run: `cd fixture-input && go test ./... -v`

Expected: PASS

- [ ] **Step 5: Commit generated + client**

```bash
git add skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/
git commit -m "feat(typed-sdk-from-openapi): add refined pkg/client for coinglass fixture"
```

---

### Task 7: Golden Fixtures, verify.sh, scripts/regen.sh in Fixture

**Files:**
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/expected/retry-policy.yaml`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/expected/sdk-readiness-report.md`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/SCENARIO.md`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/verify.sh`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/sdk/retry-policy.yaml`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/docs/sdk-readiness-report.md`
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/fixture-input/scripts/regen.sh`

**Interfaces:**
- Consumes: fixture-input module, draft script, validator, golden expected files
- Produces: `verify.sh` exit 0 = PASS

- [ ] **Step 1: Produce golden retry-policy.yaml**

Run draft script on fixture openapi, set `confirmed: true` on all operations, save copy to:
- `fixture-input/sdk/retry-policy.yaml`
- `expected/retry-policy.yaml`

Example entry (adjust operationId to match generated openapi):

```yaml
version: 1
defaults:
  unlisted: non_retryable
operations:
  GetFundingRateHistory:
    method: GET
    path: /api/futures/funding-rate/history
    policy: retryable
    idempotency_header: ""
    reason: read-only GET
    confirmed: true
```

- [ ] **Step 2: Write fixture scripts/regen.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/../../../../../scripts/regen-generated.sh" "$ROOT"
```

Adjust relative path to skill scripts/regen-generated.sh correctly from fixture depth.

- [ ] **Step 3: Write verify.sh**

Pattern after openapi-from-sources verify.sh:
1. Check skill structure (SKILL.md, scripts, references)
2. Run draft-retry-policy.py; diff policy keys against golden
3. Copy fixture to temp dir OR use fixture-input in place
4. Run validate-sdk-readiness.sh → expect `sdk_gate=GO`
5. Run `go test ./...` in fixture-input

- [ ] **Step 4: Run verify.sh**

```bash
chmod +x skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/verify.sh
chmod +x skills/dy-api-extraction/typed-sdk-from-openapi/scripts/*.sh
./skills/dy-api-extraction/typed-sdk-from-openapi/test/coinglass-fr-ohlc-history/verify.sh
```

Expected: `PASS: coinglass-fr-ohlc-history typed-sdk-from-openapi check`

- [ ] **Step 5: Write SCENARIO.md** (document offline + live agent run like sibling skills)

- [ ] **Step 6: Commit**

```bash
git add skills/dy-api-extraction/typed-sdk-from-openapi/test/
git commit -m "test(typed-sdk-from-openapi): add coinglass fixture verify harness"
```

---

### Task 8: SKILL.md

**Files:**
- Create: `skills/dy-api-extraction/typed-sdk-from-openapi/SKILL.md`
- Modify: `skills/dy-api-extraction/openapi-from-sources/SKILL.md` (downstream reference)

**Interfaces:**
- Consumes: all references, scripts, test verify path
- Produces: agent-executable workflow matching design spec

- [ ] **Step 1: Write SKILL.md**

Frontmatter:

```yaml
---
name: typed-sdk-from-openapi
description: Use when a pinned OpenAPI 3.x spec exists and a Go typed SDK with confirmed idempotency-aware retry policy is needed. Use after openapi-from-sources schema Gate GO. Do NOT crawl docs or assemble OpenAPI here. Do NOT hand-edit generated SDK files.
---
```

Include sections mirroring openapi-from-sources style:
- Core Rule
- When to Use / NOT
- Scope Boundary (SDK Gate vs schema Gate)
- Workflow steps 1–10 from spec
- Interactive batch confirmation template
- NO-GO deliverables
- Deliverables table
- Verification commands pointing to verify.sh
- References links
- Do NOT list

- [ ] **Step 2: Update openapi-from-sources/SKILL.md**

Change line ~126:
`- After **GO**, suggest `api-client-generator` for client work.`
to:
`- After **GO**, suggest `typed-sdk-from-openapi` for Go typed SDK work in this pipeline (transport principles align with `api-client-generator`).`

Update description frontmatter downstream reference similarly.

- [ ] **Step 3: Run verify.sh again**

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add skills/dy-api-extraction/typed-sdk-from-openapi/SKILL.md \
        skills/dy-api-extraction/openapi-from-sources/SKILL.md
git commit -m "feat(typed-sdk-from-openapi): add skill definition and pipeline link"
```

---

## Plan Self-Review

**Spec coverage:**
| Spec requirement | Task |
| --- | --- |
| Raw oapi-codegen SDK | Task 4, 6 |
| Refined pkg/client | Task 6 |
| retry-policy draft + confirm | Task 2, 7 |
| Transport retry | Task 5 |
| SDK Gate validator | Task 3, 7 |
| coinglass fixture test | Task 4, 7 |
| SKILL.md + pipeline link | Task 8 |
| Reference docs | Task 1 |

**Gap addressed in plan:** `idempotent_key_required` covered in transport unit tests (Task 5) even though coinglass fixture is GET-only.

**Placeholder scan:** none.

**Type consistency:** `PolicyRegistry`, `WithOperationID`, `draft_retry_policy`, `sdk_gate=GO|NO-GO` consistent across tasks.
