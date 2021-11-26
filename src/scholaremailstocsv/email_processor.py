from os import times
import re
from email import parser, policy
from pathlib import Path
from datetime import datetime, time
from string import ascii_lowercase

from addict import Dict
from bs4 import BeautifulSoup, element
from requests import get, head


def process_emails(here: Path) -> None:
    assert here.is_dir(), here
    email_paths = list(here.glob("*.eml"))
    print("\n".join(str(p) for p in email_paths))
    batches = here / "batches"
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H%M")
    new_batch = get_new_batch_dir(batches, timestamp)
    pass  # TODO


def get_new_batch_dir(batches: Path, timestamp: str) -> Path:
    print(timestamp, ascii_lowercase)
    for c in ascii_lowercase:
        batch = batches / (timestamp + c)
        if not batch.exists():
            batch.mkdir(parents=True)
            return batch
    raise RuntimeError
