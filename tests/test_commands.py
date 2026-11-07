import builtins
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_templates import ROOT, load_commands


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.project = Path(self.directory.name).resolve() / "sample"
        self.project.mkdir()
        subprocess.run(
            [
                sys.executable,
                "-m",
                "django",
                "startproject",
                "--template",
                str(ROOT / "project_template"),
                "sample",
                str(self.project),
            ],
            check=True,
            capture_output=True,
        )
        self.commands = load_commands(self.project)

    def test_compile_failures_prevent_sync(self):
        for failure in (0, 1):
            with self.subTest(failure=failure):
                error = subprocess.CalledProcessError(7, "synthetic compile")
                with (
                    patch.object(self.commands.subprocess, "run", side_effect=[None] * failure + [error]) as run,
                    patch.object(self.commands.subprocess, "call", return_value=7),
                ):
                    with self.assertRaises(subprocess.CalledProcessError):
                        self.commands.update_via_pip_tools(True)
                self.assertEqual(run.call_count, failure + 1)
                for call in run.call_args_list:
                    self.assertEqual(call.args[0][:4], [sys.executable, "-m", "piptools", "compile"])
                    self.assertTrue(call.kwargs["check"])
                    self.assertEqual(call.kwargs["cwd"], self.project)

    def test_successful_update_uses_active_interpreter_and_checked_steps(self):
        with patch.object(self.commands.subprocess, "run") as run:
            self.commands.update_via_pip_tools(False)
        self.assertEqual(run.call_count, 4)
        self.assertEqual([call.args[0][3] for call in run.call_args_list], ["compile", "compile", "sync", "sync"])
        for call in run.call_args_list:
            self.assertEqual(call.args[0][:3], [sys.executable, "-m", "piptools"])
            self.assertNotIn("--upgrade", call.args[0])
            self.assertTrue(call.kwargs["check"])
            self.assertEqual(call.kwargs["cwd"], self.project)

    def test_quality_failures_stop_before_reports_or_viewers(self):
        for command, module in (("test", "pytest"), ("mypy", "mypy"), ("coverage", "coverage")):
            for system in ("Darwin", "Linux", "Windows"):
                with self.subTest(command=command, system=system):

                    def fail(argv, **kwargs):
                        if kwargs.get("check"):
                            raise subprocess.CalledProcessError(9, argv)
                        return subprocess.CompletedProcess(argv, 9)

                    with (
                        patch.object(self.commands.subprocess, "run", side_effect=fail) as run,
                        patch.object(self.commands.subprocess, "call", return_value=9) as old_call,
                        patch.object(self.commands.platform, "system", return_value=system),
                        patch.object(self.commands.platform, "release", return_value="Microsoft"),
                    ):
                        with self.assertRaises(subprocess.CalledProcessError):
                            getattr(self.commands, command)()
                    self.assertEqual(old_call.call_count, 0)
                    run.assert_called_once()
                    self.assertEqual(run.call_args.args[0][:3], [sys.executable, "-m", module])
                    self.assertEqual(run.call_args.kwargs["cwd"], self.project)

    def test_successful_coverage_and_viewer_exit_status(self):
        cases = (
            ("Darwin", "native", "open"),
            ("Linux", "Microsoft", "explorer.exe"),
            ("Linux", "native", None),
            ("Windows", "native", None),
        )
        for system, release, viewer in cases:
            with self.subTest(system=system, release=release):

                def child(argv, **kwargs):
                    status = 1 if argv[0] == "explorer.exe" else 0
                    if status and kwargs.get("check"):
                        raise subprocess.CalledProcessError(status, argv)
                    return subprocess.CompletedProcess(argv, status)

                with (
                    patch.object(self.commands.subprocess, "run", side_effect=child) as run,
                    patch.object(self.commands.platform, "system", return_value=system),
                    patch.object(self.commands.platform, "release", return_value=release),
                ):
                    self.commands.coverage()
                self.assertEqual(run.call_count, 3 if viewer else 2)
                for call in run.call_args_list[:2]:
                    self.assertTrue(call.kwargs["check"])
                if viewer:
                    self.assertEqual(run.call_args.args[0][0], viewer)

    def test_bootstrap_failures_return_child_status(self):
        original_import = builtins.__import__

        def without_typer(name, *args, **kwargs):
            if name == "typer":
                raise ImportError("synthetic empty environment")
            return original_import(name, *args, **kwargs)

        for successful_steps in (0, 1):
            with self.subTest(successful_steps=successful_steps):
                with (
                    patch.object(builtins, "__import__", side_effect=without_typer),
                    patch.object(sys, "base_prefix", sys.prefix + "-base"),
                    patch.object(
                        subprocess,
                        "run",
                        side_effect=[None] * successful_steps
                        + [subprocess.CalledProcessError(7, "synthetic bootstrap")],
                    ) as run,
                ):
                    with self.assertRaises(SystemExit) as result:
                        runpy.run_path(str(self.project / "commands.py"), run_name="__main__")
                self.assertEqual(result.exception.code, 7)
                self.assertEqual(run.call_count, successful_steps + 1)

    def test_failed_coverage_html_does_not_open_stale_report(self):
        with patch.object(
            self.commands.subprocess, "run", side_effect=[None, subprocess.CalledProcessError(4, "html")]
        ) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                self.commands.coverage()
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args.args[0], [sys.executable, "-m", "coverage", "html"])

    def test_docs_failure_stops_build_and_browser(self):
        with (
            patch.object(self.commands.subprocess, "run", side_effect=subprocess.CalledProcessError(5, "docs")) as run,
            patch.object(self.commands.webbrowser, "open_new_tab") as browser,
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                self.commands.docs()
        run.assert_called_once()
        self.assertIsInstance(run.call_args.args[0], list)
        self.assertTrue(run.call_args.kwargs["check"])
        browser.assert_not_called()

    def test_notebook_failure_is_checked(self):
        with patch.object(
            self.commands.subprocess, "run", side_effect=subprocess.CalledProcessError(6, "notebook")
        ) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                self.commands.jupyterlab()
        self.assertEqual(run.call_args.args[0], [sys.executable, "manage.py", "shell_plus", "--lab"])
        self.assertTrue(run.call_args.kwargs["check"])

    def test_cli_returns_child_exit_status(self):
        def fail(argv, **kwargs):
            if kwargs.get("check"):
                raise subprocess.CalledProcessError(7, argv)
            return subprocess.CompletedProcess(argv, 7)

        with (
            patch.object(sys, "argv", ["commands.py", "test"]),
            patch.object(subprocess, "run", side_effect=fail),
            patch.object(subprocess, "call", return_value=7),
        ):
            with self.assertRaises(SystemExit) as result:
                runpy.run_path(str(self.project / "commands.py"), run_name="__main__")
        self.assertEqual(result.exception.code, 7)

    def test_pythonpath_uses_platform_separator(self):
        self.assertEqual(self.commands.get_pythonpath().split(os.pathsep)[0], str(self.project))
