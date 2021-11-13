# scholar_emails_to_csv

## Introduction

This is a minimal scholaremailstocsv world distribution package.
It is runnable in a variety of modes.

What little functionality is here serves to:

- Work with `pip`.
- Follow good packaging practices.
- Provide all metatadata in a static text file instead of a setup.py file.
- Provide transparency on important details of the Python runtime:
    - `__name__`
    - `__package__`
    - `__version__`
    - main script location
    - search path
- Use the build metadata to supply the version at runtime to your code.
- Support `zipapp`.

## Building and Running

This project skeleton can be run in multiple ways:

### 1. Normal Operation

`pip install [-e] .`

- Using the entry point: `scholaremailstocsv [ args... ]`
- Executing the module: `python -m scholaremailstocsv [ args... ]`

### 2. zipapp

This little-known feature of Python lets you turn an entire package and its dependencies
into a single ZIP file that you can run as if it were a single script.

https://docs.python.org/3/library/zipapp.html

This creates a ZIP file that can be run from Python:

```bash
pip install -t build/scholaremailstocsv .
# Creates build/scholaremailstocsv.pyz
python -m zipapp -m scholaremailstocsv.__main__:main build/scholaremailstocsv
# Any time later:
python build/scholaremailstocsv.pyz [ args... ]
# If moved:
python path/to/scholaremailstocsv.pyz [ args... ]
```

Or to build an executable ZIP file:

```bash
pip install -t build/scholaremailstocsv .
python -m zipapp -m scholaremailstocsv.__main__:main -p '/usr/bin/env python3' -o scholaremailstocsv build/scholaremailstocsv
# Any time later:
./scholaremailstocsv [ args... ]
# If moved:
path/to/scholaremailstocsv [ args... ]
```

Note that the resulting ZIP file will require that the `python3` that runs is compatible.
That Python runtime must:

- have a compatible version
- supply any dependencies not already in the ZIP file

### 3. Direct Invocation

Under the right circumstances you can run this repo without installing...

```bash
python setup.py sdist -d src
rm src/scholaremailstocsv*.tar.gz
python src foo bar
```

`python src [ args... ]`

This reqires either first removing the version harvesting code in `__init__.py`
or doing enough of a buld to generate the `src/scholaremailstocsv.egg-info` directory.

## Cleaning Up

You might want to have a script like this in your toolbox.

`clean`:
```bash
#!/usr/bin/env bash

TERMS='-name .eggs -o -name .pytest_cache -o -name __pycache__'
TERMS="$TERMS -o -name build -o -name dist"
find . -type d \( $TERMS -o -name \*.egg-info \) -exec rm -rf "$@" {} \; -prune
```
