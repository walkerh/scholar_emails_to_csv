from os import sep
import re
from csv import DictWriter
from dataclasses import asdict, astuple, dataclass, fields
from datetime import datetime
from email import parser, policy, utils
from pathlib import Path
from pprint import pprint as pp
from string import ascii_lowercase
from typing import Iterator

from addict import Dict
from bs4 import BeautifulSoup, element
from requests import get, head
from yarl import URL


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
    new_email_paths = move_emails(original_email_paths, new_batch)
    results = list(parse_emails(new_email_paths))
    output_csv_path = new_batch / f"{new_batch.name}.csv"
    output_fields = [f.name for f in fields(CitationRecord)]
    with output_csv_path.open("w", newline="") as fout:
        writer = DictWriter(fout, output_fields)
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))


def move_emails(original_email_paths, new_batch):
    new_email_paths = sorted(
        email_path.rename(new_batch / email_path.name)
        for email_path in original_email_paths
    )
    return new_email_paths


@dataclass
class CitationRecord:
    email_file_name: str
    email_timestamp: str
    query: str
    title: str
    url: str
    authors: str
    blurb: str


def parse_emails(new_email_paths: list[Path]) -> Iterator[CitationRecord]:
    for email_path in new_email_paths:
        print()
        print("starting", email_path)
        citations, query, email_datetime = parse_email(email_path)
        email_timestamp = email_datetime.astimezone().isoformat(sep=" ")[:19]
        print("Q:", query.text)
        for c in citations:
            print("*", c.title)
            print(" U:", c.url)
            print(" A:", c.authors)
            print(" =:", c.blurb)
            yield CitationRecord(
                email_file_name=email_path.name,
                email_timestamp=email_timestamp,
                query=query.text,
                title=c.title,
                url=c.url,
                authors=c.authors,
                blurb=c.blurb,
            )


Tag = element.Tag


class Block:
    "Just a common ancestor for CitationBlocks and QueryBlocks."


@dataclass
class Query(Block):
    payload: Tag

    @property
    def text(self) -> str:
        return self.payload.a.text.strip().strip("[]")


@dataclass
class Citation(Block):
    title_block: Tag
    authors_block: Tag
    blurb_block: Tag

    @property
    def title(self) -> str:
        return re.sub(r"\s+", " ", self.title_block.a.text).strip()

    @property
    def url(self) -> str:
        bad_url = self.title_block.a["href"]
        return clean_url(bad_url)

    @property
    def authors(self):
        return self.authors_block.text

    @property
    def blurb(self) -> str:
        return re.sub(r"\s+", " ", self.blurb_block.text).strip()


def clean_url(bad_url: str) -> str:
    u = URL(bad_url)
    while u.host != "scholar.google.com":
        response = head(str(u))
        if response.status_code != 302:
            print(response)
            print(response.headers)
            raise ValueError(response)
        u = URL(response.headers["Location"])
    assert u.host == "scholar.google.com", str(u)
    good_url = u.query["url"]
    return str(good_url)


def parse_email(email_path: Path) -> tuple[list[Citation], Query, datetime]:
    with email_path.open("rb") as fin:
        msg = eml_parser.parse(fin)
    # dump(msg, "Date")
    # dump(msg, "From")
    # dump(msg, "To")
    # dump(msg, "Subject")
    email_datetime = utils.parsedate_to_datetime(msg["Date"])
    body = msg.get_body()
    html_content = body.get_content()
    citations, query = parse_html(email_path, html_content)
    return citations, query, email_datetime


def parse_html(email_path, html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    elements = list(generate_elements(soup))
    print([e.name for e in elements])
    email_path.with_suffix(".html").write_text(soup.prettify())
    citations: list[Citation]
    query: Query
    *citations, query = generate_blocks(soup)
    pp([type(b) for b in citations])
    print(type(query))
    if not all(isinstance(b, Citation) for b in citations):
        raise ValueError(citations)
    if not isinstance(query, Query):
        raise ValueError(query)
    return citations, query


def dump(msg, header):
    value = msg[header]
    print(f"{header}: ({type(value)}) {value}")


eml_parser = parser.BytesParser(policy=policy.default)


def generate_blocks(soup: BeautifulSoup) -> Iterator[Block]:
    element_iter = generate_elements(soup)
    while True:
        try:
            first = next(element_iter)
        except StopIteration:
            return
        if first.name in ("h3", "div"):
            second = next(element_iter)
            if first.name == "h3":
                assert second.name == "div"
                third, fourth = next(element_iter), next(element_iter)
                assert third.name == "div"
                assert fourth.name == "br"
                yield Citation(first, second, third)
            elif first.name == "div":
                assert second.name == "p"
                yield Query(second)
                return  # Stop parsing.
        elif first.name == "p":
            pass  # Ignore: just a restatement of the query with " - new results".
        else:
            print("mystery element")
            print(first)
            print()
            print(first.parent.prettify())
            print()


def generate_elements(soup: BeautifulSoup) -> Iterator[Tag]:
    next_element = soup.h3
    while next_element:
        current_element = next_element
        if current_element.name == "p" and current_element.a:
            next_element = None
        else:
            try:
                next_element = current_element.next_sibling
            except:
                next_element = None
        t = type(current_element)
        if t is not element.Tag or current_element.table:
            continue
        yield current_element
