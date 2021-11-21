"""
By naming the top-level module __main__, it is possible to run this module as
a script by running:
`python -m scholaremailstocsv [args...]`
"""

from pathlib import Path
from sys import argv, path
from textwrap import dedent

from . import __version__


def main():
    cwd = str(Path().absolute())
    print(
        dedent(
            f"""\
            {cwd=}
            {__package__=} (v{__version__})
            {__name__=} @ {__file__}

            {argv=}
            """  # This f-string syntax requires 3.8+
        )
    )
    for p in path:
        print(p)


if __name__ == "__main__":
    main()
