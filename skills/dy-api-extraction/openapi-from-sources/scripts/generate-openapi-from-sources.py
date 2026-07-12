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


def parse_example_value(value: object) -> object | None:
    if isinstance(value, str):
        try:
            return json.loads(strip_json_line_comments(value))
        except json.JSONDecodeError:
            return None
    return value


def media_type_example(body: dict) -> object | None:
    if "example" in body:
        return parse_example_value(body["example"])
    for example in (body.get("examples") or {}).values():
        parsed = parse_example_value(example.get("value"))
        if parsed is not None:
            return parsed
    return None


def schema_is_empty(schema: dict, body: dict | None = None) -> bool:
    if schema.get("x-inferred-from"):
        return False
    if schema.get("$ref"):
        return False
    if not schema:
        return True
    if schema.get("additionalProperties") is not None:
        return False
    props = schema.get("properties")
    if props:
        return False
    schema_type = schema.get("type")
    if schema_type and schema_type != "object":
        return False
    return True


def find_empty_response_schemas(spec: dict) -> list[tuple[str, str, str]]:
    missing: list[tuple[str, str, str]] = []
    for path, item in (spec.get("paths") or {}).items():
        for method in ("get", "post", "put", "patch", "delete"):
            op = item.get(method)
            if not op:
                continue
            for status, resp in (op.get("responses") or {}).items():
                content = resp.get("content") or {}
                if not content:
                    continue
                for _mime, body in content.items():
                    schema = body.get("schema") or {}
                    if schema_is_empty(schema, body):
                        missing.append((path, method, status))
    seen: set[tuple[str, str, str]] = set()
    deduped: list[tuple[str, str, str]] = []
    for item in missing:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def iter_operations(spec: dict):
    for path, item in (spec.get("paths") or {}).items():
        for method in ("get", "post", "put", "patch", "delete"):
            op = item.get(method)
            if op:
                yield path, method, op


def infer_schema_from_example(value: object, evidence_file: str, evidence_line: str) -> dict:
    evidence = [{"file": evidence_file, "line": evidence_line}]
    if isinstance(value, dict):
        if not value:
            return {
                "type": "object",
                "x-source-evidence": evidence,
                "x-inferred-from": "example",
            }
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
        if not value:
            return {
                "type": "array",
                "x-source-evidence": evidence,
                "x-inferred-from": "example",
            }
        return {
            "type": "array",
            "items": infer_schema_from_example(value[0], evidence_file, evidence_line),
            "x-source-evidence": evidence,
            "x-inferred-from": "example",
        }
    if value is None:
        return {
            "type": "string",
            "nullable": True,
            "x-source-evidence": evidence,
            "x-inferred-from": "example",
        }
    if isinstance(value, bool):
        typ = "boolean"
    elif isinstance(value, int):
        typ = "integer"
    elif isinstance(value, float):
        typ = "number"
    else:
        typ = "string"
    return {
        "type": typ,
        "x-source-evidence": evidence,
        "x-inferred-from": "example",
    }


def annotate_node(node: object, evidence: list[dict]) -> None:
    if isinstance(node, dict):
        if "x-source-evidence" not in node and any(
            k in node
            for k in (
                "type",
                "properties",
                "items",
                "schema",
                "content",
                "responses",
                "operationId",
                "parameters",
                "name",
                "in",
            )
        ):
            node["x-source-evidence"] = evidence
        for key in ("schema", "items", "additionalProperties", "not"):
            if key in node and isinstance(node[key], dict):
                annotate_node(node[key], evidence)
        for key in ("allOf", "oneOf", "anyOf"):
            for sub in node.get(key) or []:
                if isinstance(sub, dict):
                    annotate_node(sub, evidence)
        props = node.get("properties")
        if isinstance(props, dict):
            for prop_schema in props.values():
                annotate_node(prop_schema, evidence)
        for key in ("content", "responses", "requestBody", "components"):
            child = node.get(key)
            if isinstance(child, dict):
                annotate_node(child, evidence)
        paths = node.get("paths")
        if isinstance(paths, dict):
            for path_item in paths.values():
                if isinstance(path_item, dict):
                    annotate_node(path_item, evidence)
        for method in ("get", "post", "put", "patch", "delete"):
            op = node.get(method)
            if isinstance(op, dict):
                annotate_node(op, evidence)
        if isinstance(node.get("parameters"), list):
            for param in node["parameters"]:
                annotate_node(param, evidence)
    elif isinstance(node, list):
        for item in node:
            annotate_node(item, evidence)


def annotate_spec(spec: dict, operation_evidence: tuple[str, str]) -> None:
    file, line = operation_evidence
    evidence = [{"file": file, "line": line}]
    annotate_node(spec, evidence)


def apply_example_fallback(
    spec: dict, evidence_file: str, evidence_line: str
) -> tuple[bool, set[str]]:
    changed = False
    filled: set[str] = set()
    for _path, _method, op in iter_operations(spec):
        for status, resp in (op.get("responses") or {}).items():
            for body in (resp.get("content") or {}).values():
                schema = body.get("schema") or {}
                if not schema_is_empty(schema, body):
                    continue
                example = media_type_example(body)
                if example is None:
                    continue
                body["schema"] = infer_schema_from_example(example, evidence_file, evidence_line)
                changed = True
                filled.add(status)
    if changed:
        spec["x-readiness"] = "example-fallback"
        spec["x-readiness-notes"] = (
            "Missing response schemas inferred from official examples because formal schemas are empty."
        )
    return changed, filled


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
    lower = text.lower()
    if lower in {"true", "false", "null", "yes", "no", "on", "off"}:
        return json.dumps(text, ensure_ascii=False)
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return json.dumps(text, ensure_ascii=False)
    if text == "" or any(c in text for c in ':{}[],&*#?|<>=!%@\\"'):
        return json.dumps(text, ensure_ascii=False)
    return text


def dump_yaml(value: object, indent: int = 0) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, child in value.items():
            if isinstance(child, dict):
                if child:
                    lines.append(f"{pad}{yaml_scalar(key)}:")
                    lines.extend(dump_yaml(child, indent + 2))
                else:
                    lines.append(f"{pad}{yaml_scalar(key)}: {{}}")
            elif isinstance(child, list):
                if child:
                    lines.append(f"{pad}{yaml_scalar(key)}:")
                    lines.extend(dump_yaml(child, indent + 2))
                else:
                    lines.append(f"{pad}{yaml_scalar(key)}: []")
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


def auth_evidence(material_root: Path, _spec: dict) -> tuple[str, str]:
    auth_md = material_root / "source/raw/authentication.md"
    if auth_md.is_file() and "CG-API-KEY" in auth_md.read_text(encoding="utf-8"):
        return "sourced", "source/raw/authentication.md:22-33"
    return "missing", "—"


def build_report(
    *,
    material_root: Path,
    scope: str,
    extraction_gate: str,
    schema_gate: str,
    strictness: str,
    endpoint_evidence: str,
    empty_responses: list[tuple[str, str, str]],
    inferred_response_statuses: set[str],
    auth_status: str,
    auth_evidence_line: str,
    output_note: str,
) -> str:
    empty_statuses = {status for _, _, status in empty_responses} | inferred_response_statuses
    response_checklist = ""
    for status in sorted(empty_statuses, key=int):
        row_status = "inferred-from-example" if status in inferred_response_statuses else "missing"
        response_checklist += (
            f"| Response {status} formal schema | {row_status} | "
            f"source/raw/fr-ohlc-histroy.md:20-41,153-157 | embedded OpenAPI schema properties empty |\n"
        )
    if not response_checklist:
        response_checklist = (
            "| Response 200 formal schema | sourced | "
            f"source/raw/fr-ohlc-histroy.md:20-41,153-157 | formal schema present |\n"
        )
    user_decision = ""
    if strictness == "strict" and schema_gate == "NO-GO":
        gap_summary = ", ".join(f"{status}" for _, _, status in empty_responses) or "Response schema"
        user_decision = f"""
## User Decision Required
Schema gate **NO-GO** — blocking gap: formal schema missing for documented response(s): {gap_summary}.

Reply with one option number:

1. **Re-fetch** — run `strict-api-extraction` for additional official pages.
2. **Example fallback** — generate schema from documented Tier A/B examples and mark inferred fields with `x-inferred-from: example`.
3. **Reduced scope** — exclude missing elements from the spec (`out_of_scope`) and generate only the sourced contract.
4. **Stop** — keep `docs/openapi-readiness-report.md` only; do not write `schema/openapi.yaml`.
"""
    elif strictness == "example-fallback" and schema_gate != "NO-GO":
        user_decision = """
## User Decision Applied
User selected option 2: **Example fallback**. Missing response schema fields are inferred only from Tier A/B documented examples and marked with `x-inferred-from: example`.
"""
    gaps_section = ""
    if schema_gate == "NO-GO" or empty_responses:
        gaps_heading = (
            "## Gaps Resolved By User Decision"
            if strictness == "example-fallback" and schema_gate != "NO-GO"
            else "## Gaps (blocking schema generation)"
        )
        gap_rows = "\n".join(
            f"| Response {status} formal schema ({path} {method}) | official embedded schema empty | "
            f"{'resolved by option 2 example-fallback' if strictness == 'example-fallback' and schema_gate != 'NO-GO' else 'cannot assemble strict schema; run strict-api-extraction or approve reduced scope'} |"
            for path, method, status in empty_responses
        ) or "| Response formal schema | official embedded schema empty | cannot assemble strict schema |"
        gaps_section = f"""
{gaps_heading}
| Element | What's missing | Suggested action |
| --- | --- | --- |
{gap_rows}
"""
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
{response_checklist}| Authentication CG-API-KEY | {auth_status} | {auth_evidence_line} | |
{gaps_section}{user_decision}
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

    empty_responses = find_empty_response_schemas(spec)
    inferred_response_statuses: set[str] = set()
    extraction_gate = "n/a"
    if (material_root / "docs/api-source-report.md").is_file():
        report_text = (material_root / "docs/api-source-report.md").read_text(encoding="utf-8")
        if "Gate: **GO**" in report_text:
            extraction_gate = "GO"
        elif "Gate: **NO-GO**" in report_text:
            extraction_gate = "NO-GO"

    auth_status, auth_evidence_line = auth_evidence(material_root, spec)

    if extraction_gate == "NO-GO":
        schema_gate = "NO-GO"
    elif empty_responses and args.strictness == "example-fallback":
        changed, inferred_response_statuses = apply_example_fallback(
            spec, "source/raw/fr-ohlc-histroy.md", "20-41"
        )
        if not changed:
            print("ERROR: example-fallback requested but no parseable examples found", file=sys.stderr)
            return 1
        empty_responses = find_empty_response_schemas(spec)
        if empty_responses or auth_status == "missing":
            schema_gate = "NO-GO"
        else:
            schema_gate = "GO (example-fallback)"
    elif empty_responses or auth_status == "missing":
        schema_gate = "NO-GO"
    else:
        schema_gate = "GO"

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
        empty_responses=empty_responses,
        inferred_response_statuses=inferred_response_statuses,
        auth_status=auth_status,
        auth_evidence_line=auth_evidence_line,
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
