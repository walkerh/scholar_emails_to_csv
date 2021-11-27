import re
from dataclasses import asdict, astuple, dataclass
from datetime import datetime
from email import parser, policy
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
    new_email_paths = sorted(
        email_path.rename(new_batch / email_path.name)
        for email_path in original_email_paths
    )
    for email_path in new_email_paths:
        print()
        print("starting", email_path)
        citations, query = parse_email(email_path)
        print("Q:", query.text)
        for c in citations:
            print("*", c.title)
            print(" U:", c.url)
            print(" A:", c.authors)
            print(" =:", c.blurb)
    pass


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
        r1 = head(bad_url)
        require(r1, 302)
        google_url = r1.headers["Location"]
        url = URL(google_url)
        good_url = url.query["url"]
        return str(good_url)
        return google_url
        r2 = get(google_url)
        require(r2, 200)
        soup = BeautifulSoup(r2.content, "html.parser")
        good_url = soup.head.noscript.meta["content"].split("=")[1]
        return good_url

    @property
    def authors(self):
        return self.authors_block.text

    @property
    def blurb(self) -> str:
        return re.sub(r"\s+", " ", self.blurb_block.text).strip()


def require(response, value) -> None:
    if response.status_code != value:
        print(response)
        print(response.headers)
        print(vars(response))
        raise ValueError(response)


def clean_url(url: str) -> str:
    pass  # TODO


def parse_email(email_path: Path) -> tuple[list[Citation], Query]:
    with email_path.open("rb") as fin:
        msg = eml_parser.parse(fin)
        body = msg.get_body()
        content = body.get_content()
        soup = BeautifulSoup(content, "html.parser")
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
