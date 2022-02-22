"""
By naming the top-level module __main__, it is possible to run this module as
a script by running:
`python -m scholaremailstocsv [args...]`
"""

from pathlib import Path
from sys import argv, executable, path

from traceback import print_exc

from . import __version__
from .email_processor import process_emails


def main():
    here = Path(argv[0]).parent.resolve()
    while not here.is_dir():
        here = here.parent
    try:
        process_emails(here)
    except:
        print_exc()
        input("\nPress return to exit.")


if __name__ == "__main__":
    main()
