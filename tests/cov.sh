#!/bin/sh
venv/bin/coverage run --branch --include="*plata/plata*" ./manage.py test testapp
venv/bin/coverage html
