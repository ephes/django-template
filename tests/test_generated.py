import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from test_templates import ROOT


def smoke_templates(archives, destination, runtime_python=sys.executable):
    """Exercise release ZIPs outside their source repository with local SQLite."""
    project = destination / "sample"
    project.mkdir()
    env = os.environ.copy()
    for key in ("DJANGO_SETTINGS_MODULE", "PYTHONPATH", "DATABASE_URL"):
        env.pop(key, None)

    def run(*args, cwd=project, python=sys.executable):
        try:
            return subprocess.run([python, *args], cwd=cwd, env=env, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as error:
            error.add_note(error.stdout + error.stderr)
            raise

    run("-m", "django", "startproject", "--template", str(archives / "project_template.zip"), "sample", str(project))
    run(
        "../manage.py", "startapp", "--template", str(archives / "app_template.zip"), "sampleapp", cwd=project / "apps"
    )
    settings = project / "config/settings/test.py"
    with settings.open("a") as handle:
        handle.write('\nINSTALLED_APPS += ["sampleapp.apps.SampleappConfig"]\n')
    (project / "tests").mkdir()
    (project / "tests/test_smoke.py").write_text(
        "from django.apps import apps\n"
        "def test_generated_app():\n"
        '    assert apps.get_app_config("sampleapp").name == "sampleapp"\n'
    )
    run("-m", "compileall", "-q", ".")
    run("manage.py", "check", "--settings=config.settings.test")
    run("manage.py", "migrate", "--noinput", "--settings=config.settings.test")
    run("manage.py", "makemigrations", "--check", "--dry-run", "--settings=config.settings.test")
    # Synthetic production values and a real collected asset exercise the
    # shipped settings without contacting a host or external database.
    env.update(DJANGO_SECRET_KEY="synthetic-test-key", ALLOWED_HOST="testserver", DJANGO_ADMIN_URL="admin/")
    (project / "static").mkdir(exist_ok=True)
    (project / "static/synthetic.css").write_text("body { color: blue; }\n")
    for command in (("check",), ("migrate", "--noinput"), ("collectstatic", "--noinput")):
        run("manage.py", *command, "--settings=config.settings.production", python=runtime_python)
    run(
        "manage.py",
        "shell",
        "--settings=config.settings.production",
        "-c",
        "from django.core.files.storage import storages; "
        "from django.contrib.staticfiles.storage import staticfiles_storage; "
        "from django.test import Client; "
        "assert storages['default'].__class__.__name__ == 'FileSystemStorage'; "
        "assert staticfiles_storage.__class__.__name__ == 'CompressedManifestStaticFilesStorage'; "
        "url = staticfiles_storage.url('synthetic.css'); "
        "assert url.startswith('/static/synthetic.') and not url.endswith('/synthetic.css'); "
        "assert staticfiles_storage.exists(url.removeprefix('/static/')); "
        "assert Client().get('/admin/login/').status_code == 200",
        python=runtime_python,
    )
    result = run("-m", "pytest", "-q")
    if "1 passed" not in result.stdout:
        raise AssertionError(result.stdout + result.stderr)
    if not (project / "db.sqlite3").exists():
        raise AssertionError("Migrations did not create the local SQLite database")


class GeneratedTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.repo = self.root / "snapshot"
        self.repo.mkdir()
        # Commit a synthetic snapshot of tracked template files so uncommitted
        # template edits are exercised while make release retains HEAD semantics.
        tracked = (
            subprocess.check_output(
                [
                    "git",
                    "ls-files",
                    "-z",
                    "Makefile",
                    "project_template",
                    "app_template",
                ],
                cwd=ROOT,
            )
            .decode()
            .split("\0")
        )
        for name in filter(None, tracked):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        (self.root / "hooks").mkdir()
        subprocess.run(["git", "init", "--quiet"], cwd=self.repo, check=True)
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Template Test",
                "-c",
                "user.email=template@example.invalid",
                "-c",
                "commit.gpgsign=false",
                "-c",
                f"core.hooksPath={self.root / 'hooks'}",
                "commit",
                "--quiet",
                "-m",
                "Synthetic template fixture",
            ],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(["make", "release"], cwd=self.repo, check=True, capture_output=True)
        self.destination = self.root / "generated"
        self.destination.mkdir()

    def test_release_zips_generate_working_project_and_app(self):
        smoke_templates(self.repo, self.destination, os.environ.get("TEMPLATE_RUNTIME_PYTHON", sys.executable))

    def test_missing_app_module_fails_smoke(self):
        archive_path = self.repo / "app_template.zip"
        with zipfile.ZipFile(archive_path) as archive:
            entries = [(name, archive.read(name)) for name in archive.namelist() if name != "app_template/apps.py-tpl"]
        with zipfile.ZipFile(archive_path, "w") as archive:
            for name, content in entries:
                archive.writestr(name, content)
        with self.assertRaises(subprocess.CalledProcessError) as error:
            smoke_templates(self.repo, self.destination)
        self.assertIn("sampleapp.apps", error.exception.stderr)
