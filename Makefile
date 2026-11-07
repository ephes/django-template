.PHONY: release
release:
	git archive --format=zip --output=app_template.zip HEAD app_template
	git archive --format=zip --output=project_template.zip HEAD project_template

PYTHON ?= python
.PHONY: check
check:
	$(PYTHON) -m ruff check tests project_template/commands.py
	$(PYTHON) -m ruff format --check tests project_template/commands.py
	$(PYTHON) -m mypy
	$(PYTHON) -m unittest discover -s tests -v

# Audit the shipped graphs without installing or resolving application packages.
AUDIT_CACHE_DIR ?= .cache/pip-audit
.PHONY: audit
audit:
	$(PYTHON) -m pip_audit -r project_template/requirements/production.txt --require-hashes --no-deps --disable-pip --strict --progress-spinner off --cache-dir "$(AUDIT_CACHE_DIR)"
	$(PYTHON) -m pip_audit -r project_template/requirements/develop.txt --require-hashes --no-deps --disable-pip --strict --progress-spinner off --cache-dir "$(AUDIT_CACHE_DIR)"
