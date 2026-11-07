# Project And App Structure for Django

This repository contains two templates: one for project structure and one for app structure.

You can use these by referring to their release files during project/app creation:

    django-admin startproject --template https://github.com/ephes/django-template/releases/download/v0.1.6/project_template.zip <project_name>


Create an app after you created the project:

    cd apps    
    ../manage.py startapp --template https://github.com/ephes/django-template/releases/download/v0.1.6/app_template.zip <app_name>

# Generated application baseline

Templates built from this checkout with `make release` support Python
**3.11–3.13** and Django **5.2 LTS** (at least 5.2.19). The published
v0.1.6 ZIPs linked above predate this baseline; use locally built ZIPs for
these settings and dependency updates until a future release includes them. Create an isolated virtual environment and install the shipped runtime
lock before running migrations or starting the application:

    python -m pip install --require-hashes -r requirements/production.txt

Production settings use Django's `STORAGES`: uploaded files retain the default
`FileSystemStorage`, while static assets use WhiteNoise's compressed manifest
storage. Set `DJANGO_SECRET_KEY`, `ALLOWED_HOST` and `DJANGO_ADMIN_URL`, then run
`python manage.py collectstatic --noinput --settings=config.settings.production`
before serving production traffic. Collection writes hashed asset names and a
manifest under `staticfiles/`; production static URLs use that manifest.
Development and test settings retain Django's ordinary static storage.
These template changes apply to newly generated projects; existing projects
must update their requirements and settings separately.

# Update Requirements

Change working directory and update dependencies:

    cd project_template
    python commands.py update

Locks are refreshed with pip-tools on Python 3.11, with hashes retained. The
developer lock includes the runtime graph and supports Jupyter Server 2,
JupyterLab 4 and Notebook 7. `python commands.py jupyterlab` uses
`manage.py shell_plus --lab` and the public ServerApp settings. It binds to
127.0.0.1:8888, opens `/lab`, and retains Jupyter's default authentication;
use the generated login link. Notebook 6 frontend extensions need compatible
Notebook 7/JupyterLab replacements. See the
[Jupyter security documentation](https://jupyter-server.readthedocs.io/en/latest/operators/security.html).

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

`make check` runs Ruff lint/format checks, mypy and synthetic unittest cases.
The smoke commits a temporary snapshot of tracked template sources (including
current edits), builds both ZIPs with `make release`, and generates a project
and app outside the checkout. It registers the app with local test settings,
runs Django checks, SQLite migrations, the missing-migration check and a real
pytest test using the generated pytest configuration. Production smoke also
runs checks, migrations, admin login rendering and static collection with dummy
environment values, then verifies a synthetic asset resolves to its hashed URL.
Set `TEMPLATE_RUNTIME_PYTHON` to an isolated interpreter installed from the
production lock to exercise that environment through the same production smoke. A negative smoke removes
the app configuration module and must fail. Other regressions cover archive
canaries, cleanup symlinks and fake failing child processes. Nothing invokes
deployment scripts, remote databases or real user data.

GitHub Actions runs the same `make check` on pushes and pull requests for both
Python versions, installing the hashed production and developer locks in separate
virtual environments. Notebook smoke exercises CLI/import compatibility, the
real django-extensions Lab entry point (version only), loopback settings and enabled
authentication from the parsed configuration, including an empty-token negative
fixture, without opening a browser or binding a socket. To run it locally,
set `TEMPLATE_DEVELOPER_PYTHON` to the developer environment's Python; when unset,
that one integration case is explicitly skipped. `requirements-ci.in` describes this small validation toolchain;
`requirements-ci.txt` pins its resolved dependencies. It is separate from the
application dependency files shipped inside the project template. No publishing
or release action is configured. This repository has no changelog.

# Audit generated application locks

CI has a separate audit job using **pip-audit 2.10.1**, installed from the
hashed `requirements-audit.txt` tool lock (`requirements-audit.in` is its input). It reads both shipped
application locks, requires their hashes, and does not install or resolve
application dependencies. Vulnerabilities, missing package/advisory information
and audit command failures fail the job; no advisories are suppressed. Use a
separate audit virtual environment locally:

    python -m venv /tmp/template-audit
    /tmp/template-audit/bin/python -m pip install --require-hashes -r requirements-audit.txt
    make audit PYTHON=/tmp/template-audit/bin/python

`make audit` runs `python -m pip_audit -r <lock> --require-hashes --no-deps
--disable-pip --strict --progress-spinner off` for
`project_template/requirements/production.txt` and `develop.txt`, stopping on
failure. Its cache defaults to `.cache/pip-audit`; set `AUDIT_CACHE_DIR` on
the make command to use another writable directory.
`make check` uses synthetic advisory outcomes to verify that vulnerabilities and
lookup/export errors propagate as gate failures. Real frozen audits must also
pass against the advisory service; an unavailable service is a failed check.
