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
