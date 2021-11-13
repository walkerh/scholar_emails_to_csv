"""
This file is currently required in order to support:
`pip install --editable .`

This is due to a limitation in PEP 517:
https://www.python.org/dev/peps/pep-0517/#get-requires-for-build-sdist
"""
import setuptools

setuptools.setup()
