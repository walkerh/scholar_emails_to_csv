import re
from datetime import datetime, time
from email import parser, policy
from pathlib import Path
from pprint import pprint as pp
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
    new_email_paths = sorted(
        email_path.rename(new_batch / email_path.name)
        for email_path in original_email_paths
    )
    # print("\n".join(str(p) for p in new_email_paths))
    for email_path in new_email_paths:
        print("starting", email_path)
        citations, query = parse_email(email_path)
    pass


def parse_email(email_path: Path) -> tuple[list[tuple], tuple]:
    with email_path.open("rb") as fin:
        msg = eml_parser.parse(fin)
        b = msg.get_body()
        c = b.get_content()
        email_path.with_suffix(".html").write_text(c)
        # elements = list(generate_elements(c))
        # pp([e.name for e in elements])
        blocks = list(generate_blocks(c))
        # pp([(code, e.name) for code, e, *_ in blocks])
        *citation_blocks, query_block = blocks
        if any(b[0] != "citation" for b in citation_blocks):
            raise ValueError(citation_blocks)
        if query_block[0] != "query":
            raise ValueError(query_block)  # TODO
        assert all((len(cb) == 4) for cb in citation_blocks)
        assert len(query_block) == 2, query_block
        citations = [cb[1:] for cb in citation_blocks]
        query = query_block[1]
        return citations, query


eml_parser = parser.BytesParser(policy=policy.default)


def generate_blocks(content):
    element_iter = generate_elements(content)
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
                yield "citation", first, second, third
            elif first.name == "div":
                assert second.name == "p"
                yield "query", second
        elif first.name == "p":
            pass  # Ignore: just a restatement of the query with " - new results".
        else:
            print("mystery element")
            print(first)
            print()
            print(first.parent.prettify())
            print()


def generate_elements(content):
    soup = BeautifulSoup(content, "html.parser")
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
