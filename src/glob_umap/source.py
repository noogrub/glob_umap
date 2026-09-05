import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


_HASH_BLOCK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class PreflightResult:
    name: str
    path: Path
    sha256: str
    row_count: int


def preflight(root: Path, source: dict[str, Any]) -> PreflightResult:
    path = root / source["path"]
    actual_hash = _sha256(path)
    if actual_hash != source["sha256"]:
        raise ValueError(
            f"Checksum mismatch for {source['name']}: "
            f"expected {source['sha256']}, found {actual_hash}"
        )

    count = sum(1 for _ in rows(root, source))
    if count != source["expected_rows"]:
        raise ValueError(
            f"Row-count mismatch for {source['name']}: "
            f"expected {source['expected_rows']}, found {count}"
        )
    return PreflightResult(source["name"], path, actual_hash, count)


def target_columns(source: dict[str, Any]) -> list[str]:
    if source["format"] == "csv":
        return [pair[1] for pair in source["columns"]]
    return [field[0] for field in source["fields"]]


def rows(
    root: Path, source: dict[str, Any]
) -> Iterator[tuple[int, list[str | None]]]:
    path = root / source["path"]
    if source["format"] == "csv":
        yield from _csv_rows(path, source["columns"])
    else:
        yield from _fixed_width_rows(path, source["fields"])


def _csv_rows(
    path: Path, columns: list[list[Any]]
) -> Iterator[tuple[int, list[str | None]]]:
    expected_header = [pair[0] for pair in columns]
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_header:
            raise ValueError(
                f"CSV header mismatch for {path}: "
                f"expected {expected_header}, found {reader.fieldnames}"
            )
        for row_number, row in enumerate(reader, start=1):
            values = [_empty_to_none(row[name]) for name in expected_header]
            yield row_number, values


def _fixed_width_rows(
    path: Path, fields: list[list[Any]]
) -> Iterator[tuple[int, list[str | None]]]:
    with path.open(encoding="ascii") as handle:
        for row_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\r\n")
            values = []
            for _, first, last in fields:
                value = line[first - 1 : last].strip()
                values.append(_empty_to_none(value))
            yield row_number, values


def _empty_to_none(value: str) -> str | None:
    return value if value != "" else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_HASH_BLOCK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()
