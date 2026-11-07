# Project And App Structure for Django

This repository contains two templates: one for project structure and one for app structure.

You can use these by referring to their release files during project/app creation:

    django-admin startproject --template https://github.com/ephes/django-template/releases/download/v0.1.6/project_template.zip <project_name>


Create an app after you created the project:

    cd apps    
    ../manage.py startapp --template https://github.com/ephes/django-template/releases/download/v0.1.6/app_template.zip <app_name>

# Update Requirements

Change working directory and update dependencies:

    cd project_template
    python commands.py update

# Template maintenance

`make release` builds both ZIPs from **committed HEAD**, with the
`project_template/` and `app_template/` prefixes. Commit intended template edits
before building. Uncommitted edits, untracked files, virtual environments and
caches are excluded; tracked hidden configuration is included. This command
only builds local archives; it does not publish or tag a release.

In a generated project, `python commands.py clean` removes root-level `build/`,
`dist/`, `*.egg-info` and `__pycache__`, then recursively removes `.pyc`, `.pyo`
and editor backup (`*~`) files. Paths are rooted at `commands.py`, regardless of
the working directory. Directory symlinks are not traversed; artifact symlinks
are unlinked without deleting their targets. Other files are retained.

Run the synthetic archive and generated-project helper regressions with an
active Python environment containing Django, Typer and Rich:

    python -m unittest discover -s tests -v

Generated developer commands run children from the project root, check child
exit statuses and stop at the first failure (except the WSL report viewer, whose
exit status is advisory because Explorer can report 1 after opening a file). Compilation failures prevent either
pip-sync step; failed tests or coverage generation prevent subsequent reports
and viewers. The CLI returns the failed child's status. pip-tools, pytest, mypy and coverage use the
active interpreter (`sys.executable`). Install the generated project's developer
requirements before running `test`, `mypy` or `coverage`.

# Validation before building release artifacts

The supported smoke baseline is Python **3.11 and 3.13** with **Django 5.2**.
From a fresh virtual environment in this repository:

    python -m pip install -r requirements-ci.txt
    make check
    make release

`make check` runs Ruff lint/format checks, mypy and 14 synthetic unittest cases.
The smoke commits a temporary snapshot of tracked template sources (including
current edits), builds both ZIPs with `make release`, and generates a project
and app outside the checkout. It registers the app with local test settings,
runs Django checks, SQLite migrations, the missing-migration check and a real
pytest test using the generated pytest configuration. A negative smoke removes
the app configuration module and must fail. Other regressions cover archive
canaries, cleanup symlinks and fake failing child processes. Nothing invokes
deployment scripts, remote databases or real user data.

GitHub Actions runs the same `make check` on pushes and pull requests for both
Python versions. `requirements-ci.in` describes this small validation toolchain;
`requirements-ci.txt` pins its resolved dependencies. It is separate from the
application dependency files shipped inside the project template. No publishing
or release action is configured. This repository has no changelog.
