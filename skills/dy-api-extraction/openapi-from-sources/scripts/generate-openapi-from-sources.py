#!/usr/bin/env python3
"""Deterministic openapi-from-sources generator for fixture tests.

Reads strict-api-extraction layout materials, runs readiness checklist,
writes docs/openapi-readiness-report.md, and schema/openapi.yaml only on GO.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def strip_json_line_comments(text: str) -> str:
    """Remove // comments only outside JSON string literals."""
    out_lines: list[str] = []
    for line in text.splitlines():
        in_string = False
        escape = False
        cleaned: list[str] = []
        i = 0
        while i < len(line):
            ch = line[i]
            if escape:
                cleaned.append(ch)
                escape = False
            elif ch == "\\" and in_string:
                cleaned.append(ch)
                escape = True
            elif ch == '"':
                in_string = not in_string
                cleaned.append(ch)
            elif not in_string and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break
            else:
                cleaned.append(ch)
            i += 1
        out_lines.append("".join(cleaned))
    return "\n".join(out_lines)


def extract_openapi_json(md_text: str) -> tuple[dict | None, int | None]:
    """Return parsed OpenAPI object and 1-based start line of JSON block."""
    marker = "# OpenAPI definition"
    idx = md_text.find(marker)
    if idx < 0:
        return None, None
    start_line = md_text[:idx].count("\n") + 1
    fence = re.search(r"```json\s*\n(.*?)\n```", md_text[idx:], re.DOTALL)
    if not fence:
        return None, start_line
    raw = fence.group(1)
    cleaned = strip_json_line_comments(raw)
    try:
        return json.loads(cleaned), start_line
    except json.JSONDecodeError:
        return None, start_line


def response_schema_empty(spec: dict, status: str = "200") -> bool:
    paths = spec.get("paths") or {}
    for _path, item in paths.items():
        for method in ("get", "post", "put", "patch", "delete"):
            op = item.get(method)
            if not op:
                continue
            resp = (op.get("responses") or {}).get(status) or {}
            content = resp.get("content") or {}
            for _mime, body in content.items():
                schema = body.get("schema") or {}
                props = schema.get("properties")
                if props == {} or (schema.get("type") == "object" and not props):
                    return True
    return False


def first_operation(spec: dict) -> tuple[str, str, dict] | None:
    for path, item in (spec.get("paths") or {}).items():
        for method in ("get", "post", "put", "patch", "delete"):
            op = item.get(method)
            if op:
                return path, method, op
    return None


def extract_response_example(spec: dict, status: str = "200") -> object | None:
    op_info = first_operation(spec)
    if not op_info:
        return None
    _, _, op = op_info
    resp = (op.get("responses") or {}).get(status) or {}
    content = resp.get("content") or {}
    for body in content.values():
        examples = body.get("examples") or {}
        for example in examples.values():
            value = example.get("value")
            if isinstance(value, str):
                try:
                    return json.loads(strip_json_line_comments(value))
                except json.JSONDecodeError:
                    return None
            if value is not None:
                return value
    return None


def infer_schema_from_example(value: object, evidence_file: str, evidence_line: str) -> dict:
    evidence = [{"file": evidence_file, "line": evidence_line}]
    if isinstance(value, dict):
        return {
            "type": "object",
            "properties": {
                str(k): infer_schema_from_example(v, evidence_file, evidence_line)
                for k, v in value.items()
            },
            "x-source-evidence": evidence,
            "x-inferred-from": "example",
        }
    if isinstance(value, list):
        item = value[0] if value else {}
        return {
            "type": "array",
            "items": infer_schema_from_example(item, evidence_file, evidence_line),
            "x-source-evidence": evidence,
            "x-inferred-from": "example",
        }
    if isinstance(value, bool):
        typ = "boolean"
    elif isinstance(value, int):
        typ = "integer"
    elif isinstance(value, float):
        typ = "number"
    elif value is None:
        typ = "string"
    else:
        typ = "string"
    return {
        "type": typ,
        "x-source-evidence": evidence,
        "x-inferred-from": "example",
    }


def annotate_spec(spec: dict, operation_evidence: tuple[str, str]) -> None:
    file, line = operation_evidence
    evidence = [{"file": file, "line": line}]
    for _path, item in (spec.get("paths") or {}).items():
        for method, op in item.items():
            if method.startswith("x-") or not isinstance(op, dict):
                continue
            op["x-source-evidence"] = evidence
            for param in op.get("parameters") or []:
                if isinstance(param, dict):
                    param["x-source-evidence"] = evidence


def apply_example_fallback(spec: dict, evidence_file: str, evidence_line: str) -> bool:
    example = extract_response_example(spec, "200")
    if example is None:
        return False
    op_info = first_operation(spec)
    if not op_info:
        return False
    _, _, op = op_info
    resp = (op.get("responses") or {}).get("200") or {}
    for body in (resp.get("content") or {}).values():
        body["schema"] = infer_schema_from_example(example, evidence_file, evidence_line)
    spec["x-readiness"] = "example-fallback"
    spec["x-readiness-notes"] = (
        "Response 200 schema inferred from official example because formal schema is empty."
    )
    return True


def yaml_scalar(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or any(c in text for c in ':{}[],&*#?|<>=!%@\\"'):
        return json.dumps(text, ensure_ascii=False)
    return text


def dump_yaml(value: object, indent: int = 0) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                lines.append(f"{pad}{yaml_scalar(key)}:")
                lines.extend(dump_yaml(child, indent + 2))
            else:
                lines.append(f"{pad}{yaml_scalar(key)}: {yaml_scalar(child)}")
        return lines
    if isinstance(value, list):
        lines = []
        for child in value:
            if isinstance(child, dict):
                lines.append(f"{pad}-")
                lines.extend(dump_yaml(child, indent + 2))
            elif isinstance(child, list):
                lines.append(f"{pad}-")
                lines.extend(dump_yaml(child, indent + 2))
            else:
                lines.append(f"{pad}- {yaml_scalar(child)}")
        return lines
    return [f"{pad}{yaml_scalar(value)}"]


def dump_openapi_yaml(spec: dict) -> str:
    return "\n".join(dump_yaml(spec)) + "\n"


def build_report(
    *,
    material_root: Path,
    scope: str,
    extraction_gate: str,
    schema_gate: str,
    strictness: str,
    endpoint_evidence: str,
    empty_200: bool,
    output_note: str,
) -> str:
    status = "inferred-from-example" if strictness == "example-fallback" and empty_200 else (
        "missing" if empty_200 else "sourced"
    )
    user_decision = ""
    if strictness == "strict" and schema_gate == "NO-GO":
        user_decision = """
## User Decision Required
Schema gate **NO-GO** — blocking gap: Response 200 formal schema is missing.

Reply with one option number:

1. **Re-fetch** — run `strict-api-extraction` for additional official pages.
2. **Example fallback** — generate schema from documented Tier A/B examples and mark inferred fields with `x-inferred-from: example`.
3. **Reduced scope** — exclude missing elements from the spec (`out_of_scope`) and generate only the sourced contract.
4. **Stop** — keep `docs/openapi-readiness-report.md` only; do not write `schema/openapi.yaml`.
"""
    elif strictness == "example-fallback":
        user_decision = """
## User Decision Applied
User selected option 2: **Example fallback**. Missing response schema fields are inferred only from Tier A/B documented examples and marked with `x-inferred-from: example`.
"""
    gaps_heading = (
        "## Gaps Resolved By User Decision"
        if strictness == "example-fallback"
        else "## Gaps (blocking schema generation)"
    )
    gap_suggestion = (
        "resolved by option 2 example-fallback; inferred fields are marked"
        if strictness == "example-fallback"
        else "cannot assemble strict schema; run strict-api-extraction or approve reduced scope"
    )
    return f"""# OpenAPI Readiness: CoinGlass fr-ohlc-histroy

## Summary
- Dialect: OpenAPI 3.x
- Material profile: strict-api-extraction
- Material root: {material_root}
- Scope: {scope}
- Strictness: {strictness}
- Extraction gate (if report present): **{extraction_gate}**
- Schema gate: **{schema_gate}**
- Output: {output_note}

## Material Inventory
| File | Tier | Role | Notes |
| --- | --- | --- | --- |
| source/raw/fr-ohlc-histroy.md | A | endpoint-ref | embedded partial OpenAPI |
| source/raw/authentication.md | A | auth | CG-API-KEY header |
| source/raw/responses-error-codes.md | A | errors | global error codes |
| source/raw/instruments.md | A | cross-ref | exchange/symbol reference |

## Readiness Checklist
| Element | Status | Evidence (Tier A/B path:line) | Notes |
| --- | --- | --- | --- |
| GET /api/futures/funding-rate/history | sourced | {endpoint_evidence} | operationId fr-ohlc-histroy |
| Request body (GET) | N/A | — | GET has no body |
| Response 200 formal schema | {status} | source/raw/fr-ohlc-histroy.md:20-41,153-157 | embedded OpenAPI schema properties empty |
| Authentication CG-API-KEY | sourced | source/raw/authentication.md:22-33 | |

{gaps_heading}
| Element | What's missing | Suggested action |
| --- | --- | --- |
| Response 200 formal JSON Schema | official embedded OpenAPI `schema.properties` empty | {gap_suggestion} |
{user_decision}

## Next Step
Schema **{schema_gate}** — {'do not write `schema/openapi.yaml` in strict mode' if schema_gate == 'NO-GO' else 'run api-client-generator on schema/openapi.yaml'}.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("material_root", type=Path, help="Root with source/raw/ layout")
    parser.add_argument("output_dir", type=Path, help="Write docs/ and schema/ here")
    parser.add_argument(
        "--scope",
        default="GET /api/futures/funding-rate/history (fr-ohlc-histroy)",
    )
    parser.add_argument(
        "--strictness",
        choices=("strict", "example-fallback"),
        default="strict",
        help="strict stops on missing formal schemas; example-fallback infers from documented examples",
    )
    args = parser.parse_args()

    material_root = args.material_root.resolve()
    output_dir = args.output_dir.resolve()
    endpoint_md = material_root / "source/raw/fr-ohlc-histroy.md"
    if not endpoint_md.is_file():
        print(f"ERROR: missing {endpoint_md}", file=sys.stderr)
        return 1

    md_text = endpoint_md.read_text(encoding="utf-8")
    spec, json_line = extract_openapi_json(md_text)
    if spec is None:
        print("ERROR: could not parse embedded OpenAPI from fr-ohlc-histroy.md", file=sys.stderr)
        return 1

    empty_200 = response_schema_empty(spec)
    if empty_200 and args.strictness == "example-fallback":
        if not apply_example_fallback(spec, "source/raw/fr-ohlc-histroy.md", "20-41"):
            print("ERROR: example-fallback requested but no parseable 200 example found", file=sys.stderr)
            return 1
        schema_gate = "GO (example-fallback)"
    else:
        schema_gate = "NO-GO" if empty_200 else "GO"
    extraction_gate = "GO"
    if (material_root / "docs/api-source-report.md").is_file():
        report_text = (material_root / "docs/api-source-report.md").read_text(encoding="utf-8")
        if "Gate: **GO**" in report_text:
            extraction_gate = "GO"
        elif "Gate: **NO-GO**" in report_text:
            extraction_gate = "NO-GO"

    endpoint_evidence = f"source/raw/fr-ohlc-histroy.md:{json_line or 73}-77"
    output_note = "(none — gaps only)" if schema_gate == "NO-GO" else "`schema/openapi.yaml`"

    docs_dir = output_dir / "docs"
    schema_dir = output_dir / "schema"
    docs_dir.mkdir(parents=True, exist_ok=True)

    report = build_report(
        material_root=material_root,
        scope=args.scope,
        extraction_gate=extraction_gate,
        schema_gate=schema_gate,
        strictness=args.strictness,
        endpoint_evidence=endpoint_evidence,
        empty_200=empty_200,
        output_note=output_note,
    )
    (docs_dir / "openapi-readiness-report.md").write_text(report, encoding="utf-8")

    openapi_path = schema_dir / "openapi.yaml"
    if schema_gate != "NO-GO":
        schema_dir.mkdir(parents=True, exist_ok=True)
        rel_file = "source/raw/fr-ohlc-histroy.md"
        line_ref = f"{json_line or 44}-187"
        annotate_spec(spec, (rel_file, line_ref))
        yaml_text = dump_openapi_yaml(spec)
        openapi_path.write_text(yaml_text, encoding="utf-8")

    print(f"schema_gate={schema_gate}")
    print(f"report={docs_dir / 'openapi-readiness-report.md'}")
    if schema_gate != "NO-GO":
        print(f"openapi={openapi_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
