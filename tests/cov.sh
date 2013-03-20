#!/bin/sh
coverage run --branch --include="*plata/plata*" ./manage.py test testapp
coverage html
