import os
import re
import subprocess
import sys
from datetime import date

import django
from django.conf import settings


sys.path.append(os.path.abspath(".."))
sys.path.append(os.path.abspath("../tests"))

project = "plata"
author = "Feinheit AG"
copyright = f"2010-{date.today().year}, {author}"
version = __import__("plata").__version__
release = subprocess.check_output(
    "git fetch --tags; git describe", shell=True, universal_newlines=True
).strip()
language = "en"

#######################################
settings.configure(
    DATABASES={
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
    },
    INSTALLED_APPS=(
        "django.contrib.auth",
        "django.contrib.admin",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.sitemaps",
        "django.contrib.sites",
        "django.contrib.staticfiles",
        "plata",
        "plata.contact",
        "plata.discount",
        "plata.payment",
        "plata.product",
        "plata.product.stock",
        "plata.shop",
        "testapp",
    ),
    STATIC_URL="/static/",
    SECRET_KEY="tests",
    ALLOWED_HOSTS=["*"],
    MIDDLEWARE=(
        "django.middleware.common.CommonMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.locale.LocaleMiddleware",
    ),
    USE_TZ=True,
    LANGUAGES=(("en", "English"), ("de", "German")),
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.debug",
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            },
        }
    ],
)
django.setup()

#######################################
project_slug = re.sub(r"[^a-z]+", "", project)

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
]
templates_path = ["_templates"]
source_suffix = ".txt"
master_doc = "index"

exclude_patterns = ["build", "Thumbs.db", ".DS_Store"]
pygments_style = "sphinx"
todo_include_todos = False

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
htmlhelp_basename = project_slug + "doc"

latex_elements = {
    "papersize": "a4",
}
latex_documents = [
    (
        master_doc,
        project_slug + ".tex",
        project + " Documentation",
        author,
        "manual",
    )
]
man_pages = [
    (
        master_doc,
        project_slug,
        project + " Documentation",
        [author],
        1,
    )
]
texinfo_documents = [
    (
        master_doc,
        project_slug,
        project + " Documentation",
        author,
        project_slug,
        "",  # Description
        "Miscellaneous",
    )
]
