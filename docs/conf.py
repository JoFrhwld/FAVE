# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# pylint: skip-file
import os
import tempfile
import sys
# conf.py

from sphinx_pyproject import SphinxConfig

# Until Poetry supports PEP 621 we're gonna need to do this silly hack
## Read the pyproject.toml file
with open("../pyproject.toml") as f:
    pyproj = f.read()
## Do string replacements until it's in PEP 621 format
pyproj = pyproj.replace("tool.poetry", "project")
pyproj = pyproj.replace("	", "	{ name = ")
pyproj = pyproj.replace('",\n','"},\n')
pyproj = pyproj.replace('"\n]','"}\n]')
pyproj = pyproj.replace(' <', '", email = "')
pyproj = pyproj.replace('.edu>"','.edu"')
## Write our transformed string to a temporary file
tmp = tempfile.NamedTemporaryFile(mode="w",delete=False)
try:
    tmp.write(pyproj)
    tmp.flush()  # Required, or later read won't work
    # Below line imports our project info from the toml file
    config = SphinxConfig(tmp.name, globalns=globals())  # tmp.name to open file is Unix only
finally:
    tmp.close()
    os.unlink(tmp.name)  # deletes the temporary file

sys.path.insert(0, os.path.abspath('..'))


# -- Project information -----------------------------------------------------

project = 'Forced Alignment and Vowel Extraction (FAVE)'
copyright = '2022, '+ author

# The full version, including alpha/beta/rc tags
release = version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc','sphinx.ext.napoleon', "myst_parser"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'pyramid'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
