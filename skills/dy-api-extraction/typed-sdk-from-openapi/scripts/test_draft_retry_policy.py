import tempfile
import unittest
from pathlib import Path

import yaml

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


if __name__ == "__main__":
    unittest.main()
