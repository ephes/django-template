import os
import platform
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path


def get_project_root():
    return Path(__file__).parent.resolve()


def update_via_pip_tools(upgrade: bool):
    base_command = [sys.executable, "-m", "piptools", "compile"]
    if upgrade:
        base_command.append("--upgrade")
    base_command.extend(
        [
            "--resolver=backtracking",
            "--allow-unsafe",
            "--generate-hashes",
            "requirements/production.in",
        ]
    )

    subprocess.run(  # develop + production
        [
            *base_command,
            "requirements/develop.in",
            "--output-file",
            "requirements/develop.txt",
        ],
        check=True,
        cwd=get_project_root(),
    )
    subprocess.run(  # production only
        [
            *base_command,
            "--output-file",
            "requirements/production.txt",
        ],
        check=True,
        cwd=get_project_root(),
    )
    subprocess.run(
        [sys.executable, "-m", "piptools", "sync", "requirements/production.txt"], check=True, cwd=get_project_root()
    )
    subprocess.run(
        [sys.executable, "-m", "piptools", "sync", "requirements/develop.txt"], check=True, cwd=get_project_root()
    )


def bootstrap():
    """
    Called when first non-standard lib import fails.

    We need at least pip-tools, typer and rich to use this script.
    """

    def get_base_prefix_compat():
        """Get base/real prefix, or sys.prefix if there is none."""
        return getattr(sys, "base_prefix", None) or getattr(sys, "real_prefix", None) or sys.prefix

    def in_virtualenv():
        return get_base_prefix_compat() != sys.prefix

    def pip_install(package):
        subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)

    if not in_virtualenv():
        print("Please create a virtual environment first and activate it!")
        sys.exit(1)

    print("Empty virtualenv, installing development requirements..")
    pip_install("pip-tools")
    update_via_pip_tools(upgrade=True)


try:
    import typer
except ImportError:
    try:
        bootstrap()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
    import typer

from rich import print  # noqa

cli = typer.Typer()


def get_pythonpath():
    """Add project root and model directory to string"""
    project_root = str(get_project_root())
    model_root = str(Path(__file__).parent / "model")
    return os.pathsep.join((project_root, model_root))


def env_with_pythonpath():
    """Get en environment dict with includes PYTHONPATH"""
    env = os.environ.copy()
    env["PYTHONPATH"] = get_pythonpath()
    return env


@cli.command()
def mypy():
    """Run Mypy (configured in pyproject.toml)"""
    subprocess.run([sys.executable, "-m", "mypy", "."], check=True, cwd=get_project_root())


@cli.command()
def test():
    subprocess.run([sys.executable, "-m", "pytest"], check=True, cwd=get_project_root(), env=env_with_pythonpath())


@cli.command()
def coverage():
    """
    Run and show coverage.
    """
    subprocess.run(
        [sys.executable, "-m", "coverage", "run", "-m", "pytest"],
        check=True,
        cwd=get_project_root(),
        env=env_with_pythonpath(),
    )
    subprocess.run([sys.executable, "-m", "coverage", "html"], check=True, cwd=get_project_root())
    if platform.system() == "Darwin":
        subprocess.run(["open", "htmlcov/index.html"], check=True, cwd=get_project_root())
    elif platform.system() == "Linux" and "Microsoft" in platform.release():  # on WSL
        # Explorer may return 1 even when it opens the report (microsoft/WSL#6565).
        subprocess.run(["explorer.exe", r"htmlcov\index.html"], check=False, cwd=get_project_root())


@cli.command()
def jupyterlab():
    """
    Start a jupyterlab server.
    """
    project_root = get_project_root()
    notebook_dir = project_root / "notebooks"
    notebook_dir.mkdir(exist_ok=True)
    env = env_with_pythonpath() | {"DJANGO_ALLOW_ASYNC_UNSAFE": "true"}
    subprocess.run([sys.executable, "manage.py", "shell_plus", "--notebook"], env=env, check=True, cwd=project_root)


@cli.command()
def update(upgrade: bool = typer.Option(True, "--upgrade/--no-upgrade")):
    """
    Update the development environment by calling:
    - pip-compile production.in develop.in -> develop.txt
    - pip-compile production.in -> production.txt
    - pip-sync develop.txt
    """
    update_via_pip_tools(upgrade)


def remove_artifact(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


@cli.command()
def clean_build():
    root = get_project_root()
    for name in ("build", "dist", "__pycache__"):
        remove_artifact(root / name)
    for path in root.glob("*.egg-info"):
        remove_artifact(path)


@cli.command()
def clean_pyc():
    for directory, _, files in os.walk(get_project_root(), followlinks=False):
        for name in files:
            if name.endswith((".pyc", ".pyo", "~")):
                (Path(directory) / name).unlink()


@cli.command()
def clean():
    clean_build()
    clean_pyc()


@cli.command()
def docs():
    autogenerated = [
        "cast.api.rst",
        "cast.migrations.rst",
        "cast.rst",
        "cast.templatetags.rst",
        "modules.rst",
    ]
    for rst_name in autogenerated:
        (get_project_root() / "docs" / rst_name).unlink(missing_ok=True)
    commands = [
        ["sphinx-apidoc", "-o", "docs/", "cast"],
        ["make", "-C", "docs", "clean"],
        ["make", "-C", "docs", "html"],
    ]
    for command in commands:
        subprocess.run(command, check=True, cwd=get_project_root())
    file_url = "file://" + str(get_project_root() / "docs/_build/html/index.html")
    webbrowser.open_new_tab(file_url)


if __name__ == "__main__":
    try:
        cli()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
