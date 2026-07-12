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

    def test_schema_blockers_resolve_refs_and_validate_composed_and_map_values(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Missing"}
                                    }
                                }
                            },
                            "400": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/EmptyUser"}
                                    }
                                }
                            },
                            "500": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "oneOf": [
                                                {"type": "string"},
                                                {},
                                            ]
                                        }
                                    }
                                }
                            },
                            "default": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "additionalProperties": {},
                                        }
                                    }
                                }
                            },
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "EmptyUser": {
                        "type": "object",
                        "properties": {"name": {}},
                    }
                }
            },
        }

        blockers = generator.find_schema_blockers(spec)
        elements = {blocker["element"] for blocker in blockers}

        self.assertIn("Response 200 formal schema (/users get)", elements)
        self.assertIn("Response 400 formal schema (/users get)", elements)
        self.assertIn("Response 500 formal schema (/users get)", elements)
        self.assertIn("Response default formal schema (/users get)", elements)

    def test_empty_composed_schema_array_is_blocking(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {"oneOf": []},
                                    }
                                }
                            }
                        }
                    }
                }
            },
        }

        self.assertTrue(generator.schema_is_empty({"oneOf": []}, spec=spec))
        self.assertIn(
            "Response 200 formal schema (/users get)",
            {blocker["element"] for blocker in generator.find_schema_blockers(spec)},
        )

    def test_path_level_parameters_are_schema_blockers(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/users/{id}": {
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {}}
                    ],
                    "get": {"responses": {"204": {"description": "No content"}}},
                }
            },
        }

        blockers = generator.find_schema_blockers(spec)

        self.assertIn(
            "Parameter id schema (/users/{id} get)",
            {blocker["element"] for blocker in blockers},
        )

    def test_referenced_path_level_parameters_are_not_schema_blockers(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/users/{id}": {
                    "parameters": [{"$ref": "#/components/parameters/UserId"}],
                    "get": {"responses": {"204": {"description": "No content"}}},
                }
            },
            "components": {
                "parameters": {
                    "UserId": {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                }
            },
        }

        blockers = generator.find_schema_blockers(spec)

        self.assertEqual([], blockers)

    def test_referenced_response_and_request_body_schemas_are_blockers(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {"$ref": "#/components/requestBodies/UserBody"},
                        "responses": {
                            "200": {"$ref": "#/components/responses/UserResponse"}
                        },
                    }
                }
            },
            "components": {
                "requestBodies": {
                    "UserBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"email": {}},
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "UserResponse": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"id": {}},
                                }
                            }
                        }
                    }
                },
            },
        }

        self.assertEqual(
            [("/users", "post", "200")],
            generator.find_empty_response_schemas(spec),
        )
        self.assertIn(
            "Request body schema (/users post)",
            {blocker["element"] for blocker in generator.find_schema_blockers(spec)},
        )

    def test_nullable_object_and_array_type_arrays_follow_underlying_shape_rules(self) -> None:
        spec = {"openapi": "3.1.0", "paths": {"/users": {"get": {"responses": {}}}}}

        self.assertTrue(
            generator.schema_is_empty(
                {"type": ["object", "null"], "properties": {}},
                spec=spec,
            )
        )
        self.assertTrue(
            generator.schema_is_empty(
                {"type": ["array", "null"]},
                spec=spec,
            )
        )
        self.assertFalse(
            generator.schema_is_empty(
                {"type": ["array", "null"], "items": {"type": "string"}},
                spec=spec,
            )
        )

    def test_example_fallback_replaces_empty_referenced_response_schema(self) -> None:
        spec = {
            "openapi": "3.1.0",
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/EmptyUser"},
                                        "example": {"id": "abc"},
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "EmptyUser": {
                        "type": "object",
                        "properties": {"id": {}},
                    }
                }
            },
        }

        changed, inferred = generator.apply_example_fallback(
            spec, "source/raw/users.md", "10-20"
        )

        body = spec["paths"]["/users"]["get"]["responses"]["200"]["content"]["application/json"]
        self.assertTrue(changed)
        self.assertEqual({"200"}, inferred)
        self.assertEqual("object", body["schema"]["type"])
        self.assertEqual([], generator.find_empty_response_schemas(spec))

    def test_user_decision_summary_names_non_response_blockers(self) -> None:
        report = generator.build_report(
            material_root=Path("/tmp/material"),
            scope="GET /users",
            extraction_gate="GO",
            schema_gate="NO-GO",
            strictness="strict",
            endpoint_evidence="source/raw/users.md:1-5",
            empty_responses=[],
            inferred_response_statuses=set(),
            auth_status="sourced",
            auth_evidence_line="source/raw/authentication.md:1-5",
            servers_status="sourced",
            report_schema_gaps=[],
            schema_blockers=[
                {
                    "kind": "parameter",
                    "element": "Parameter id schema (/users/{id} get)",
                    "path": "/users/{id}",
                    "method": "get",
                }
            ],
            output_note="(none -- gaps only)",
        )

        self.assertIn("Parameter id schema (/users/{id} get)", report)
        self.assertNotIn("blocking gap: formal schema missing for documented response(s): Response schema", report)

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
