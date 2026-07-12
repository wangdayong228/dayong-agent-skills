#!/usr/bin/env python3
"""Regression tests for generate-openapi-from-sources.py."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("generate-openapi-from-sources.py")
SPEC = importlib.util.spec_from_file_location("generator", SCRIPT)
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


class OpenAPIFromSourcesTests(unittest.TestCase):
    def test_schema_blockers_include_nested_response_and_inputs(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/users": {
                    "post": {
                        "parameters": [
                            {"name": "limit", "in": "query", "schema": {}},
                        ],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"email": {}},
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "items": {
                                                    "type": "array",
                                                    "items": {},
                                                }
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            },
        }

        blockers = generator.find_schema_blockers(spec)
        elements = {blocker["element"] for blocker in blockers}

        self.assertIn("Parameter limit schema (/users post)", elements)
        self.assertIn("Request body schema (/users post)", elements)
        self.assertIn("Response 200 formal schema (/users post)", elements)

    def test_composed_ref_and_map_schemas_are_not_empty(self) -> None:
        complete_shapes = [
            {"$ref": "#/components/schemas/User"},
            {"oneOf": [{"type": "string"}, {"type": "integer"}]},
            {"type": "object", "additionalProperties": {"type": "string"}},
        ]

        for schema in complete_shapes:
            with self.subTest(schema=schema):
                self.assertFalse(generator.schema_is_empty(schema))

    def test_scoped_security_and_servers_satisfy_readiness(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "CG-API-KEY",
                    }
                }
            },
            "paths": {
                "/users": {
                    "servers": [{"url": "https://api.example.test"}],
                    "get": {
                        "security": [{"ApiKeyAuth": []}],
                        "responses": {"204": {"description": "No content"}},
                    },
                }
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            material_root = Path(tmp)
            raw = material_root / "source" / "raw"
            raw.mkdir(parents=True)
            (raw / "authentication.md").write_text("Use CG-API-KEY header\n", encoding="utf-8")

            self.assertEqual(generator.auth_evidence(material_root, spec)[0], "sourced")
            self.assertTrue(generator.servers_ready(spec))

    def test_example_fallback_merges_nested_array_fields_and_does_not_invent_null_type(self) -> None:
        schema = generator.infer_schema_from_example(
            [{"data": {"a": 1}}, {"data": {"b": 2}}, {"empty": []}, {"missing": None}],
            "source/raw/example.md",
            "10-20",
        )

        item_props = schema["items"]["properties"]
        self.assertEqual(
            set(item_props["data"]["properties"]),
            {"a", "b"},
        )
        self.assertNotIn("items", item_props["empty"])
        self.assertNotIn("type", item_props["missing"])


if __name__ == "__main__":
    unittest.main()
