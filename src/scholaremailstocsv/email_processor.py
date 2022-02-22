import logging
import re
from csv import DictWriter
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from email import parser, policy, utils
from pathlib import Path
from shutil import copyfile
from string import ascii_lowercase
from sys import executable, stderr
from typing import Iterable, Iterator, Optional

import coloredlogs
from bs4 import BeautifulSoup, element
from extract_msg import openMsg
from humanfriendly.terminal import terminal_supports_colors
from requests import head
from rtfparse.parser import Rtf_Parser
from rtfparse.renderers import de_encapsulate_html
from yarl import URL

from . import __version__


LOG_FILE_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
STDERR_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logger = logging.getLogger(__name__)


def process_emails(here: Path) -> None:
    assert here.is_dir(), here
    batches = here / "batches"
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H%M")
    new_batch = get_new_batch_dir(batches, timestamp)
    log_file_path = configure_logging(new_batch)
    log_startup(here, log_file_path)
    logger.info(f"batch_dir={new_batch!s}")
    original_email_paths = list(here.glob("*.eml")) + list(here.glob("*.msg"))
    do_batch(original_email_paths, new_batch)


def get_new_batch_dir(batches: Path, timestamp: str) -> Path:
    for c in ascii_lowercase:
        batch = batches / (timestamp + c)
        if not batch.exists():
            batch.mkdir(parents=True)
            return batch
    raise RuntimeError(f"too many batches with {timestamp=}")


def configure_logging(new_batch: Path) -> str:
    set_logging_level(None, logging.NOTSET)
    set_logging_level("rtfparse", logging.INFO)
    set_logging_level("urllib3.connectionpool", logging.INFO)
    plain_log_formatter = logging.Formatter(LOG_FILE_FORMAT)
    stderr_log_formatter = (
        coloredlogs.ColoredFormatter(STDERR_LOG_FORMAT)
        if terminal_supports_colors(stderr)
        else plain_log_formatter
    )
    stderr_handler = coloredlogs.StandardErrorHandler(level=logging.INFO)
    stderr_handler.setFormatter(stderr_log_formatter)
    stderr_handler.addFilter(stderr_handler_filter)
    file_path = new_batch / f"{new_batch.name}.log"
    file_handler = logging.FileHandler(file_path)
    file_handler.setLevel(logging.NOTSET)
    file_handler.setFormatter(plain_log_formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(stderr_handler)
    root_logger.addHandler(file_handler)
    return file_path


def set_logging_level(logger_name: Optional[str], level) -> None:
    target_logger = logging.getLogger(logger_name)
    target_logger.setLevel(level)


CHATTY_LOGGERS = set(
    [
        "extract_msg.message_base",
        "rtfparse.parser",
        "rtfparse.renderers.de_encapsulate_html",
    ]
)


def stderr_handler_filter(record: logging.LogRecord) -> bool:
    if record.name in CHATTY_LOGGERS:
        if record.levelno <= logging.INFO:
            return False
    return True


def log_startup(here: Path, log_file_path: str) -> None:
    # breakpoint()
    cwd = str(Path().resolve())
    logger.info(f"{__package__} version={__version__}")
    logger.info(f"logging to '{log_file_path}'")
    logger.info(f"{cwd=}")
    logger.info(f"here={here!s}")
    logger.info(f"{executable=}")
    logger.info(f"{__name__=}")
    logger.info(f"{__file__=}")


def do_batch(original_email_paths: list[Path], new_batch: Path) -> None:
    new_email_paths = move_emails(original_email_paths, new_batch)
    results = parse_emails(new_email_paths)
    output_csv_path = new_batch / f"{new_batch.name}.csv"
    output_fields = [f.name for f in fields(CitationRecord)]
    with output_csv_path.open("w", newline="") as fout:
        writer = DictWriter(fout, output_fields)
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))
    logger.info(f"wrote {output_csv_path}")


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


def parse_emails(new_email_paths: list[Path]) -> list[CitationRecord]:
    results = []
    error_paths = []
    for email_path in new_email_paths:
        logger.info(f"STARTING {email_path.name}")
        try:
            citations, query, email_datetime = parse_email(email_path)
            email_timestamp = email_datetime.astimezone().isoformat(sep=" ")[:19]
            logger.debug(f"Q: {query.text}")
            for c in citations:
                logger.debug(f"* {c.title}")
                logger.debug(f" U: {c.url}")
                logger.debug(f" A: {c.authors}")
                logger.debug(f" =: {c.blurb}")
                results.append(
                    CitationRecord(
                        email_file_name=email_path.name,
                        email_timestamp=email_timestamp,
                        query=query.text,
                        title=c.title,
                        url=c.url,
                        authors=c.authors,
                        blurb=c.blurb,
                    )
                )
        except Exception as e:
            logger.exception(email_path.name)
            batch_dir = email_path.parent
            error_dir = batch_dir / "errors"
            error_dir.mkdir(exist_ok=True)
            error_email_path = error_dir / email_path.name
            error_paths.append(email_path)
            copyfile(email_path, error_email_path)
        else:
            logger.info(f"number of citations={len(citations)}")
    logger.info(f"finished with {len(results)} results")
    if error_paths:
        logger.error(f"encountered {len(error_paths)} errors")
    return results


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
            logger.debug(response)
            logger.debug(response.headers)
            raise ValueError(response)
        u = URL(response.headers["Location"])
    assert u.host == "scholar.google.com", str(u)
    good_url = u.query["url"]
    return str(good_url)


def parse_email(email_path: Path) -> tuple[list[Citation], Query, datetime]:
    if email_path.suffix == ".eml":
        with email_path.open("rb") as fin:
            msg = eml_parser.parse(fin)
        email_datetime_str = msg["Date"]
        body = msg.get_body()
        html_content = body.get_content()
    else:
        email_datetime_str, html_content = parse_msg_file(email_path)
    email_datetime = utils.parsedate_to_datetime(email_datetime_str)
    citations, query = parse_html(email_path, html_content)
    return citations, query, email_datetime


def parse_msg_file(email_path: Path) -> tuple[str, str]:
    assert email_path.suffix == ".msg", email_path
    msg = openMsg(str(email_path))
    email_datetime_str = msg.date
    rtf_encapsulated_html = msg.rtfBody
    rtf_path = email_path.with_suffix(".rtf")
    rtf_path.write_bytes(rtf_encapsulated_html)
    raw_html_path = email_path.with_suffix(".rtf.html")
    parser = Rtf_Parser(rtf_path=rtf_path)
    parsed = parser.parse_file()
    renderer = de_encapsulate_html.De_encapsulate_HTML()
    with open(raw_html_path, mode="w", encoding="utf-8") as html_file:
        renderer.render(parsed, html_file)
    html_content = raw_html_path.read_text(encoding="utf-8")
    return email_datetime_str, html_content


def parse_html(email_path, html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    elements = list(generate_elements(soup))
    logger.debug([e.name for e in elements])
    email_path.with_suffix(".html").write_text(soup.prettify(), encoding="utf-8")
    citations: list[Citation]
    query: Query
    *citations, query = generate_blocks(elements)
    logger.debug(f"citation_types={[type(b) for b in citations]}")
    if not all(isinstance(b, Citation) for b in citations):
        raise ValueError(citations)
    if not isinstance(query, Query):
        raise ValueError(query)
    return citations, query


eml_parser = parser.BytesParser(policy=policy.default)


def generate_blocks(elements: Iterable[Tag]) -> Iterator[Block]:
    element_iter = iter(elements)
    while True:
        try:
            first = next(element_iter)
        except StopIteration:
            return
        if first.name == "h3":
            second = next(element_iter)
            assert second.name == "div"
            third = next(element_iter)
            assert third.name == "div"
            yield Citation(first, second, third)
        elif first.name == "p":
            yield Query(first)
            return  # Stop parsing.
        else:
            logger.warning("mystery element")
            logger.warning(first.name)
            logger.warning(first.parent.prettify())
            raise ValueError


def generate_elements(soup: BeautifulSoup) -> Iterator[Tag]:
    first_a_tag = soup.find(class_="gse_alrt_title")
    next_element = first_a_tag.parent
    if not next_element.name == "h3":
        raise ValueError(next_element)
    while next_element:
        current_element = next_element
        if current_element.name == "p":
            if current_element.a:
                next_element = None
            else:
                next_element = current_element.next_sibling
                continue
        else:
            try:
                next_element = current_element.next_sibling
            except:
                next_element = None
        if type(current_element) is not element.Tag or current_element.table:
            continue
        text = current_element.text
        if not text.strip():
            continue
        yield current_element
