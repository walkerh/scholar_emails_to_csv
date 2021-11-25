from pathlib import Path


def process_emails(here: Path) -> None:
    assert here.is_dir(), here
    email_paths = here.glob("*.eml")
    print("\n".join(str(p) for p in email_paths))
    pass  # TODO
