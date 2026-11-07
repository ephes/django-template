import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_templates import ROOT


class AuditGateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        shutil.copyfile(ROOT / "Makefile", self.root / "Makefile")
        requirements = self.root / "project_template/requirements"
        requirements.mkdir(parents=True)
        self.locks = [requirements / f"{name}.txt" for name in ("production", "develop")]
        for lock in self.locks:
            lock.write_text("synthetic clean graph")
        # Synthetic advisory-service outcomes: no network, package installation
        # or platform-specific executables are needed to exercise the make gate.
        (self.root / "pip_audit.py").write_text(
            "import pathlib, sys\n"
            "args = sys.argv[1:]\n"
            "for flag in ('--strict', '--no-deps', '--disable-pip', '--require-hashes'):\n"
            "    assert flag in args, flag\n"
            "path = pathlib.Path(args[args.index('-r') + 1])\n"
            "print(path, flush=True)\n"
            "outcome = path.read_text()\n"
            "sys.exit({'synthetic vulnerable graph': 1, 'lookup failure': 2, 'export failure': 3}.get(outcome, 0))\n"
        )

    def run_gate(self):
        return subprocess.run(
            ["make", "audit", f"PYTHON={sys.executable}"],
            cwd=self.root,
            env=os.environ | {"PYTHONPATH": str(self.root)},
            capture_output=True,
            text=True,
        )

    def test_audits_both_shipped_graphs(self):
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in ("production", "develop"):
            self.assertIn(f"project_template/requirements/{name}.txt", result.stdout)

    def test_vulnerability_and_service_failures_fail_the_gate(self):
        for index, lock in enumerate(self.locks):
            for outcome in ("synthetic vulnerable graph", "lookup failure", "export failure"):
                with self.subTest(lock=lock.name, outcome=outcome):
                    lock.write_text(outcome)
                    try:
                        result = self.run_gate()
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(str(lock.relative_to(self.root)), result.stdout)
                        if index == 0:
                            self.assertNotIn("develop.txt", result.stdout)
                    finally:
                        lock.write_text("synthetic clean graph")
