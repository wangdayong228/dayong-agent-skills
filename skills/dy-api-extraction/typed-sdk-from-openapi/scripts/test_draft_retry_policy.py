import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    yaml = types.ModuleType("yaml")
    yaml.safe_load = json.loads
    yaml.safe_dump = lambda value, **_kwargs: json.dumps(value)
    sys.modules["yaml"] = yaml

from draft_retry_policy import derive_operation_id, draft_retry_policy

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

    def test_duplicate_operation_id_raises(self):
        dup_spec = {
            "openapi": "3.0.3",
            "info": {"title": "t", "version": "1"},
            "paths": {
                "/a": {"get": {"operationId": "Dup", "responses": {"200": {"description": "ok"}}}},
                "/b": {"get": {"operationId": "Dup", "responses": {"200": {"description": "ok"}}}},
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "openapi.yaml"
            spec.write_text(yaml.safe_dump(dup_spec), encoding="utf-8")
            with self.assertRaises(ValueError):
                draft_retry_policy(str(spec))

    def test_path_item_idempotency_header_is_inherited(self):
        spec_doc = {
            "openapi": "3.0.3",
            "info": {"title": "t", "version": "1"},
            "paths": {
                "/items": {
                    "parameters": [{"name": "Idempotency-Key", "in": "header", "schema": {"type": "string"}}],
                    "post": {"operationId": "CreateItem", "responses": {"201": {"description": "created"}}},
                }
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "openapi.yaml"
            spec.write_text(yaml.safe_dump(spec_doc), encoding="utf-8")
            result = draft_retry_policy(str(spec))
        entry = result["operations"]["CreateItem"]
        self.assertEqual(entry["policy"], "idempotent_key_required")
        self.assertEqual(entry["idempotency_header"], "Idempotency-Key")

    def test_request_id_header_does_not_make_write_retryable(self):
        spec_doc = {
            "openapi": "3.0.3",
            "info": {"title": "t", "version": "1"},
            "paths": {
                "/items": {
                    "post": {
                        "operationId": "CreateItem",
                        "parameters": [{"name": "X-Request-ID", "in": "header", "schema": {"type": "string"}}],
                        "responses": {"201": {"description": "created"}},
                    }
                }
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "openapi.yaml"
            spec.write_text(yaml.safe_dump(spec_doc), encoding="utf-8")
            result = draft_retry_policy(str(spec))
        entry = result["operations"]["CreateItem"]
        self.assertEqual(entry["policy"], "non_retryable")
        self.assertEqual(entry["idempotency_header"], "")


if __name__ == "__main__":
    unittest.main()
