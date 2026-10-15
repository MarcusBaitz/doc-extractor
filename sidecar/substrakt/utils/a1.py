"""A1 spreadsheet range utilities."""

from __future__ import annotations

import re

_CELL = re.compile(r"^\$?([A-Za-z]{1,3})\$?(\d{1,7})$")


def column_to_index(letters: str) -> int:
    """``A`` → 1, ``Z`` → 26, ``AA`` → 27."""
    index = 0
    for character in letters.upper():
        index = index * 26 + (ord(character) - ord("A") + 1)
    return index


def a1_to_row_column(a1: str) -> tuple[int, int]:
    cell = a1.split("!")[-1].strip()
    match = _CELL.match(cell)
    if not match:
        return 0, 0
    return int(match.group(2)), column_to_index(match.group(1))


def range_bounds(a1: str) -> tuple[int, int, int, int]:
    range_ = a1.split("!")[-1].strip()
    if ":" in range_:
        start, _, until = range_.partition(":")
        row1, column1 = a1_to_row_column(start)
        row2, column2 = a1_to_row_column(until)
    else:
        row1, column1 = a1_to_row_column(range_)
        row2, column2 = row1, column1

    return min(row1, row2), min(column1, column2), max(row1, row2), max(column1, column2)


def a1_in_range(cell: str, range_: str) -> bool:
    row, column = a1_to_row_column(cell)
    if row == 0:
        return False
    row_start, column_start, row_end, column_end = range_bounds(range_)
    return row_start <= row <= row_end and column_start <= column <= column_end
