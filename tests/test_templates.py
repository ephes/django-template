import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_commands(project):
    spec = importlib.util.spec_from_file_location("generated_commands", project / "commands.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ArchiveTests(unittest.TestCase):
    def test_release_contains_only_committed_templates(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(repo)], check=True)
            # Exercise the working Makefile, including before this fix is committed.
            (repo / "Makefile").write_bytes((ROOT / "Makefile").read_bytes())
            for template in ("project_template", "app_template"):
                for name in (".env", ".venv/canary", "__pycache__/canary.pyc"):
                    path = repo / template / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("synthetic canary")
                (repo / template / "templates/.gitignore").write_text("uncommitted change")
            subprocess.run(["make", "release"], cwd=repo, check=True, capture_output=True)
            for template in ("project_template", "app_template"):
                with zipfile.ZipFile(repo / f"{template}.zip") as archive:
                    names = archive.namelist()
                    self.assertTrue(all(name.startswith(f"{template}/") for name in names))
                    for unwanted in (".env", ".venv/canary", "__pycache__/canary.pyc"):
                        self.assertNotIn(f"{template}/{unwanted}", names)
                    hidden = f"{template}/templates/.gitignore"
                    expected = subprocess.check_output(["git", "show", f"HEAD:{hidden}"], cwd=repo)
                    self.assertEqual(archive.read(hidden), expected)
                    module = "manage.py-tpl" if template == "project_template" else "apps.py-tpl"
                    self.assertIn(f"{template}/{module}", names)


class CleanupTests(unittest.TestCase):
    def test_generated_cleanup_is_rooted_and_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "sample"
            project.mkdir()
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "django",
                    "startproject",
                    "--template",
                    str(ROOT / "project_template"),
                    "sample",
                    str(project),
                ],
                check=True,
                capture_output=True,
            )
            commands = load_commands(project)
            external = root / "external"
            external.mkdir()
            (external / "keep.pyc").write_text("keep")
            for name in ("build", "dist", "sample.egg-info", "__pycache__"):
                (project / name).mkdir()
                (project / name / "artifact").touch()
            nested = project / "apps/nested"
            nested.mkdir()
            for name in ("old.pyc", "old.pyo", "backup~", "keep.py", "keep.txt"):
                (nested / name).touch()
            (project / "linked").symlink_to(external, target_is_directory=True)
            (project / "outside.egg-info").symlink_to(external, target_is_directory=True)
            (nested / "link.pyc").symlink_to(external / "keep.pyc")
            before = Path.cwd()
            try:
                os.chdir(external)
                commands.clean()
                commands.clean()  # Missing artifacts are harmless.
            finally:
                os.chdir(before)
            for name in ("build", "dist", "sample.egg-info", "__pycache__", "outside.egg-info"):
                self.assertFalse((project / name).exists(), name)
            for name in ("old.pyc", "old.pyo", "backup~", "link.pyc"):
                self.assertFalse((nested / name).exists(), name)
            self.assertTrue((nested / "keep.py").exists())
            self.assertTrue((nested / "keep.txt").exists())
            self.assertTrue((external / "keep.pyc").exists())
            self.assertTrue((project / "linked").is_symlink())


if __name__ == "__main__":
    unittest.main()
