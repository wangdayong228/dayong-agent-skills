# Evidence Extensions for OpenAPI 3.x

Use vendor extensions to preserve provenance. Required on every operation, parameter, and schema property assembled from sources.

## x-source-evidence

Array of `{ file, line, note? }` pointing to Tier A/B text.

```yaml
paths:
  /api/example:
    get:
      operationId: example
      x-source-evidence:
        - file: source/raw/example.md
          line: "73-77"
      parameters:
        - name: exchange
          in: query
          required: true
          schema:
            type: string
          x-source-evidence:
            - file: source/raw/example.md
              line: "80-87"
```

Rules:
- `file` is repo-relative from material root
- `line` is a single line or inclusive range (`117` or `80-87`)
- Tier C paths (`docs/api-source-report.md`) are forbidden as sole evidence

## x-readiness (document-level, optional)

On root OpenAPI object when user approved reduced scope:

```yaml
x-readiness: reduced-scope
x-readiness-notes: Response 200 types excluded per user approval 2026-07-12
```

For user-approved example fallback:

```yaml
x-readiness: example-fallback
x-readiness-notes: Response 200 schema inferred from official example because formal schema is empty.
```

## x-inferred-from

Required on every schema element inferred from examples after the user chooses option 2.

```yaml
properties:
  code:
    type: string
    x-source-evidence:
      - file: source/raw/example.md
        line: "20-41"
    x-inferred-from: example
```

Rules:
- Forbidden in `strict` mode; missing formal schema → NO-GO and ask the user to choose.
- Required in `example-fallback` mode for every example-derived schema object, array, and property.
- Never infer fields that do not appear in the documented Tier A/B example.
