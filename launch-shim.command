#!/usr/bin/env python3 
from pathlib import Path
from subprocess import run
from time import sleep
import sys

me = Path(__file__).resolve()
here = me.parent
app = str(here / "scholaremailstocsv.pyz")
command = [
    sys.executable,
    app,
    *sys.argv[1:],
]
print(command)
run(command)
input("press return to exit")
