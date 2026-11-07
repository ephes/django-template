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
