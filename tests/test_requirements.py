import re
import unittest

from test_templates import ROOT


class RuntimeRequirementsTests(unittest.TestCase):
    def test_shipped_runtime_uses_patched_django_52(self):
        requirements = ROOT / "project_template/requirements"
        self.assertIn("Django>=5.2.19,<5.3", (requirements / "production.in").read_text())
        lock = (requirements / "production.txt").read_text()
        match = re.search(r"^django==5\.2\.(\d+) \\", lock, re.MULTILINE)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertGreaterEqual(int(match[1]), 19)
        for pin in (
            "gunicorn==20.1.0",
            "setuptools==67.7.2",
            "certifi==2022.12.7",
            "httpcore==0.17.0",
            "idna==3.4",
            "sqlparse==0.4.4",
            "h11==0.14.0",
            "anyio==3.6.2",
        ):
            with self.subTest(pin=pin):
                self.assertNotIn(pin + " ", lock)
