# Project And App Structure for Django

This repository contains two templates: one for project structure and one for app structure.

You can use these by referring to their release files during project/app creation:

    django-admin startproject --template https://github.com/ephes/django-template/releases/download/v0.1.2/project_template.zip <project_name>


Create an app after you created the project:

    cd apps    
    ../manage.py startapp --template https://github.com/ephes/django-template/releases/download/v0.1.2/app_template.zip <app_name>

# Update Requirements

Change working directory and update dependencies:
    cd project_template
    python commands.py update
