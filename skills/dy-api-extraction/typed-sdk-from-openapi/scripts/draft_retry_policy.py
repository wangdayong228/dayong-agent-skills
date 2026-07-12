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
            if op_id in operations:
                raise ValueError(
                    f"duplicate operationId {op_id!r} for {method.upper()} {path}"
                )
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
