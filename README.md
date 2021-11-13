# minimal_hello_world

## Introduction

This is a minimal hello world distribution package.
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

- Using the entry point: `hello [ args... ]`
- Executing the module: `python -m minimalhello [ args... ]`

### 2. zipapp

This little-known feature of Python lets you turn an entire package and its dependencies
into a single ZIP file that you can run as if it were a single script.

https://docs.python.org/3/library/zipapp.html

This creates a ZIP file that can be run from Python:

```bash
pip install -t build/hello .
# Creates build/hello.pyz
python -m zipapp -m minimalhello.__main__:main build/hello
# Any time later:
python build/hello.pyz [ args... ]
# If moved:
python path/to/hello.pyz [ args... ]
```

Or to build an executable ZIP file:

```bash
pip install -t build/hello .
python -m zipapp -m minimalhello.__main__:main -p '/usr/bin/env python3' -o hello build/hello
# Any time later:
./hello [ args... ]
# If moved:
path/to/hello [ args... ]
```

Note that the resulting ZIP file will require that the `python3` that runs is compatible.
That Python runtime must:

- have a compatible version
- supply any dependencies not already in the ZIP file

### 3. Direct Invocation

Under the right circumstances you can run this repo without installing...

```bash
python setup.py sdist -d src
rm src/minimalhello*.tar.gz
python src foo bar
```

`python src [ args... ]`

This reqires either first removing the version harvesting code in `__init__.py`
or doing enough of a buld to generate the `src/minimalhello.egg-info` directory.

## Touring the Code


```
$ tree -pugsCa -I .git\|.venv
.
├── [-rw-r--r-- hale     staff           1822]  .gitignore
├── [-rw-r--r-- hale     staff           1071]  LICENSE
├── [-rw-r--r-- hale     staff           4196]  README.md
├── [-rw-r--r-- hale     staff             90]  pyproject.toml
├── [-rw-r--r-- hale     staff           1252]  setup.cfg
├── [-rw-r--r-- hale     staff            238]  setup.py
└── [drwxr-xr-x hale     staff            128]  src
    ├── [-rw-r--r-- hale     staff            300]  __main__.py
    └── [drwxr-xr-x hale     staff            128]  minimalhello
        ├── [-rw-r--r-- hale     staff            604]  __init__.py
        └── [-rw-r--r-- hale     staff            532]  __main__.py

2 directories, 9 files
```

### Very Little Code

Most of this repo is either the README, LICENSE, or .gitignore:

```
$ find . -name .git -prune -o -type f -print | fgrep -v -e .egg -e .pyc -e ./hello | xargs wc -l
   21 ./LICENSE
    3 ./pyproject.toml
  143 ./README.md
   10 ./setup.py
  132 ./.gitignore
   47 ./setup.cfg
   17 ./src/minimalhello/__init__.py
   29 ./src/minimalhello/__main__.py
   14 ./src/__main__.py
  416 total
```

### Interesting Files

- `pyproject.toml`: Current standard selection build tools
- `setup.py`: Almost empty. Only needed to suppor `pip install -e ...`
- `setup.cfg`: Where *all* of the metadata lives, including version
- `src/__main__.py`: Only necessary if you want to support running without installing.
- `src/minimalhello/__init__.py`: Demonstrates fetching `__version__` from build.
- `src/minimalhello/__main__.py`: Top-level script, supports `python -m minimalhello ...`

## Cleaning Up

You might want to have a script like this in your toolbox.

`clean`:
```bash
#!/usr/bin/env bash

TERMS='-name .eggs -o -name .pytest_cache -o -name __pycache__'
TERMS="$TERMS -o -name build -o -name dist"
find . -type d \( $TERMS -o -name \*.egg-info \) -exec rm -rf "$@" {} \; -prune
```
