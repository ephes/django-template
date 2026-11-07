.PHONY: release
release:
	git archive --format=zip --output=app_template.zip HEAD app_template
	git archive --format=zip --output=project_template.zip HEAD project_template
