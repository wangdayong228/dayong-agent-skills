import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BOOTSTRAP = SCRIPT_DIR / "bootstrap-python.sh"

class BootstrapPythonTest(unittest.TestCase):
    def test_uses_existing_python_without_venv_or_pip(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_bin = Path(tmp) / "bin"
            fake_bin.mkdir()
            log = Path(tmp) / "calls.log"
            python3 = fake_bin / "python3"
            python3.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$CALL_LOG\"\n[ \"$1\" = '-c' ] && exit 0\nexit 9\n", encoding="utf-8")
            python3.chmod(0o755)
            env = os.environ.copy()
            env.update({"PATH": str(fake_bin) + os.pathsep + os.environ["PATH"], "CALL_LOG": str(log)})
            result = subprocess.run([str(BOOTSTRAP)], env=env, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(python3))
            calls = log.read_text(encoding="utf-8")
            self.assertIn("-c import yaml", calls)
            self.assertNotIn("venv", calls)
            self.assertNotIn("pip", calls)

    def test_reports_missing_pyyaml_without_installing(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_bin = Path(tmp) / "bin"
            fake_bin.mkdir()
            python3 = fake_bin / "python3"
            python3.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            python3.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + os.environ["PATH"]
            result = subprocess.run([str(BOOTSTRAP)], env=env, text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("PyYAML", result.stderr)

if __name__ == "__main__":
    unittest.main()
