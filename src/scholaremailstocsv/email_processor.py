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
    original_email_paths = list(here.glob("*.eml"))
    batches = here / "batches"
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H%M")
    new_batch = get_new_batch_dir(batches, timestamp)
    do_batch(original_email_paths, new_batch)


def get_new_batch_dir(batches: Path, timestamp: str) -> Path:
    for c in ascii_lowercase:
        batch = batches / (timestamp + c)
        if not batch.exists():
            batch.mkdir(parents=True)
            return batch
    raise RuntimeError(f"too many batches with {timestamp=}")


def do_batch(original_email_paths: list[Path], new_batch: Path) -> None:
    new_email_paths = [
        email_path.rename(new_batch / email_path.name)
        for email_path in original_email_paths
    ]
    pass  # TODO
