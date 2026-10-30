"""Small reusable helpers only; no SQL statements or credentials here."""
from pathlib import Path
import re

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def safe_identifier(value: str) -> str:
    if not _IDENT.fullmatch(value):
        raise ValueError(f"unsafe SQL identifier: {value!r}")
    return value


def read_sql(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
