import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_templates import ROOT


@unittest.skipUnless(os.environ.get("TEMPLATE_DEVELOPER_PYTHON"), "set TEMPLATE_DEVELOPER_PYTHON for notebook smoke")
class NotebookSmokeTests(unittest.TestCase):
    def test_generated_notebook_toolchain_and_authenticated_loopback_defaults(self):
        python = os.environ["TEMPLATE_DEVELOPER_PYTHON"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = os.environ.copy()
            for key in ("DJANGO_SETTINGS_MODULE", "PYTHONPATH", "JUPYTER_TOKEN", "JUPYTER_TOKEN_FILE"):
                env.pop(key, None)
            for key in ("JUPYTER_CONFIG_DIR", "JUPYTER_DATA_DIR", "JUPYTER_RUNTIME_DIR", "IPYTHONDIR"):
                env[key] = str(root / key.lower())
            project = root / "sample"
            project.mkdir()
            (project / "notebooks").mkdir()

            def run(*args):
                try:
                    return subprocess.run(
                        [python, *args], cwd=project, env=env, capture_output=True, text=True, check=True
                    )
                except subprocess.CalledProcessError as error:
                    error.add_note(error.stdout + error.stderr)
                    raise

            run("-m", "django", "startproject", "--template", str(ROOT / "project_template"), "sample", str(project))
            for module in ("jupyter_server", "jupyterlab", "notebook"):
                run("-m", module, "--version")
            # Exercise django-extensions' real modern Lab entry point, exiting
            # through version output before binding a socket or launching a browser.
            result = run("manage.py", "shell_plus", "--lab", "--", "--version")
            self.assertTrue(result.stdout.strip())
            auth_check = (
                "from django.conf import settings; "
                "from jupyter_server.serverapp import ServerApp; "
                "app = ServerApp(); app.parse_command_line(settings.NOTEBOOK_ARGUMENTS); "
                "assert app.ip == '127.0.0.1'; assert app.port == 8888; "
                "assert app.default_url == '/lab'; assert app.identity_provider_class(parent=app).auth_enabled"
            )
            run("manage.py", "shell", "-c", auth_check)
            with (project / "config/settings/base.py").open("a") as handle:
                handle.write('\nNOTEBOOK_ARGUMENTS += ["--IdentityProvider.token="]\n')
            with self.assertRaises(subprocess.CalledProcessError) as error:
                run("manage.py", "shell", "-c", auth_check)
            self.assertIn("AssertionError", error.exception.stderr)
