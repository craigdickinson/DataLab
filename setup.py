"""
Installs user modules as packages, such as the folders core and views (required if using VSCode, for example).
How to run: Activate venv and run "pip install -e .".
"""
__author__ = "Craig Dickinson"

from setuptools import setup, find_packages

setup(name="datalab", packages=find_packages())
