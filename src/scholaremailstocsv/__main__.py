"""
By naming the top-level module __main__, it is possible to run this module as
a script by running:
`python -m scholaremailstocsv [args...]`
"""

from pathlib import Path
from sys import argv, executable, path
from textwrap import dedent
from traceback import print_exc

from . import __version__
from .email_processor import process_emails


def main():
    cwd = str(Path().resolve())
    here = Path(argv[0]).parent.resolve()
    while not here.is_dir():
        here = here.parent
    print(
        dedent(
            f"""\
            {cwd=}
            {executable=}
            {__package__=} (v{__version__})
            {__name__=} @ {__file__}
            {here=}
            {argv=}
            """
        )
    )
    for p in path:
        print(p)
    try:
        process_emails(here)
    except:
        print_exc()
        input("\nPress return to exit.")


if __name__ == "__main__":
    main()
