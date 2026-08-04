import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate-sdk-readiness.sh"

class ValidateSdkReadinessTest(unittest.TestCase):
    def make_run_dir(self, root, operations):
        run_dir = root / "run"
        for directory in ("schema", "sdk", "docs"):
            (run_dir / directory).mkdir(parents=True, exist_ok=True)
        for path in ("generated/client.gen.go", "internal/transport/retry.go", "pkg/client/client.go", "scripts/regen.sh"):
            target = run_dir / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fixture\n", encoding="utf-8")
        openapi = {"openapi": "3.0.3", "info": {"title": "t", "version": "1"}, "paths": {
            "/reads": {"get": {"operationId": "GetReads", "responses": {"200": {"description": "ok"}}}},
            "/writes": {"post": {"responses": {"201": {"description": "created"}}}},
        }}
        (run_dir / "schema/openapi.yaml").write_text(json.dumps(openapi), encoding="utf-8")
        (run_dir / "sdk/retry-policy.yaml").write_text(json.dumps({"version": 1, "operations": operations}), encoding="utf-8")
        shim = root / "yaml.py"
        shim.write_text("import json\nsafe_load = json.loads\n", encoding="utf-8")
        (run_dir / "docs/sdk-readiness-report.md").write_text("approved\n", encoding="utf-8")
        return run_dir

    def validate(self, operations):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self.make_run_dir(Path(tmp), operations)
            env = os.environ.copy()
            env["PYTHONPATH"] = tmp
            return subprocess.run([str(VALIDATOR), str(run_dir)], env=env, text=True, capture_output=True, check=False)

    def test_missing_openapi_operation_is_no_go(self):
        result = self.validate({"GetReads": {"policy": "retryable", "confirmed": True}})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sdk_gate=NO-GO", result.stdout)

    def test_idempotent_key_required_without_header_is_no_go(self):
        result = self.validate({
            "GetReads": {"policy": "retryable", "confirmed": True},
            "PostWrites": {"policy": "idempotent_key_required", "idempotency_header": "", "confirmed": True},
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sdk_gate=NO-GO", result.stdout)

    def test_complete_confirmed_policy_is_go(self):
        result = self.validate({
            "GetReads": {"policy": "retryable", "confirmed": True},
            "PostWrites": {"policy": "non_retryable", "confirmed": True},
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sdk_gate=GO", result.stdout)

if __name__ == "__main__":
    unittest.main()
