# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import configparser
import os


def read_setup_cfg_version():
    here = os.path.split(__file__)[0]
    setup_cfg = os.path.join(here, "../setup.cfg")

    config = configparser.ConfigParser()
    config.read(setup_cfg)

    version = None
    if "metadata" in config.sections():
        version = config["metadata"].get("version", None)

    if version is None:
        version = "<unknown>"

    return version


VERSION = read_setup_cfg_version()


# -- Project information -----------------------------------------------------

project = "pytz_deprecation_shim"
copyright = "2020, Paul Ganssle"
author = "Paul Ganssle"

# The full version, including alpha/beta/rc tags
release = VERSION


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

# For cross-links to other documentation
intersphinx_mapping = {
    "python": ("https://docs.python.org/3.9", None),
    "dateutil": ("https://dateutil.readthedocs.io/en/stable/", None),
}

_repo = "https://github.com/pganssle/pytz-deprecation-shim/"
extlinks = {
    "gh": (_repo + "issues/%s", "GH-"),
    "gh-pr": (_repo + "pull/%s", "GH-"),
    "pypi": ("https://pypi.org/project/%s", ""),
    "bpo": ("https://bugs.python.org/issue%s", "bpo-"),
    "cpython-pr": ("https://github.com/python/cpython/pull/%s", "CPython PR #"),
}
