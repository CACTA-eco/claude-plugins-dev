"""Helpers shared by the template-filler scripts (stdlib plus openpyxl only).

The reader for the hidden `_meta` sheet mirrors `core/core/xlsx_meta.py`; a test in
mcp-server/tests keeps the two in step, since the skill cannot import `core`.
"""

import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.worksheet.worksheet import Worksheet

META_SHEET_TITLE = "_meta"
MAX_FINDINGS = 100


# How a date is written in each format the app offers (same table as core's bulk import).
DATE_PATTERNS = {"DD/MM/YYYY": "%d/%m/%Y", "MM/DD/YYYY": "%m/%d/%Y", "YYYY-MM-DD": "%Y-%m-%d"}


class TemplateError(Exception):
    """The workbook is not a template produced by the generate tools."""


class CellError(Exception):
    """A cell the import would reject; the message says why."""


def parse_closed_value(column: dict[str, Any], value: Any) -> str:
    """A closed-list cell: its code (or the label that maps to one) must be allowed."""
    options = column.get("options")
    text = str(value).strip()
    if not options:
        return text
    by_label = {option["label"]: option["code"] for option in options}
    code = by_label.get(text, text)
    if code not in {option["code"] for option in options}:
        shown = ", ".join(option["label"] for option in options[:8])
        more = "..." if len(options) > 8 else ""
        raise CellError(f"{text!r} is not an allowed value (for example: {shown}{more})")
    return code


def read_meta(workbook: openpyxl.Workbook) -> dict[str, Any] | None:
    """The template description on the hidden `_meta` sheet, or None when absent."""
    if META_SHEET_TITLE not in workbook.sheetnames:
        return None
    sheet = workbook[META_SHEET_TITLE]
    text = "".join(str(cell.value) for (cell,) in sheet.iter_rows(max_col=1) if cell.value)
    return json.loads(text) if text else None


def load_template(path: str) -> tuple[openpyxl.Workbook, dict[str, Any]]:
    """Open a workbook and its `_meta`; raise TemplateError if it has none."""
    workbook = openpyxl.load_workbook(path)
    meta = read_meta(workbook)
    if meta is None:
        raise TemplateError(
            "no _meta sheet: use a file produced by the generate_*_bulk_excel tool "
            "(and keep its hidden sheets)"
        )
    return workbook, meta


def is_blank(value: Any) -> bool:
    """True for None and for text that is only whitespace."""
    return value is None or str(value).strip() == ""


def header_positions(sheet: Worksheet, columns: list[dict[str, Any]]) -> dict[str, int]:
    """{field key: 0-based column index} for the `_meta` columns found in row 1."""
    headers = [str(cell.value).strip() if cell.value is not None else "" for cell in sheet[1]]
    return {
        column["key"]: headers.index(column["header"])
        for column in columns
        if column["header"] in headers
    }


def data_rows(sheet: Worksheet) -> list[tuple[int, tuple[Any, ...]]]:
    """(row number, values) for every row below the header that is not completely empty."""
    return [
        (number, values)
        for number, values in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2)
        if not all(is_blank(value) for value in values)
    ]


class Report:
    """Collects findings and prints them as JSON; exit code 1 when there are errors."""

    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.rows = 0

    def error(self, row: int | None, column: str | None, message: str) -> None:
        self.errors.append({"row": row, "column": column, "message": message})

    def warning(self, row: int | None, column: str | None, message: str) -> None:
        self.warnings.append({"row": row, "column": column, "message": message})

    def emit(self) -> int:
        """Print the report and return the process exit code."""
        print(
            json.dumps(
                {
                    "ok": not self.errors,
                    "rows": self.rows,
                    "error_count": len(self.errors),
                    "warning_count": len(self.warnings),
                    "errors": self.errors[:MAX_FINDINGS],
                    "warnings": self.warnings[:MAX_FINDINGS],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1 if self.errors else 0


def fail(message: str, code: int = 2) -> int:
    """Print a JSON error and return `code` (for problems with the input, not the data)."""
    print(json.dumps({"ok": False, "fatal": message}, indent=2, ensure_ascii=False))
    return code


def main_guard(function: Any) -> None:
    """Run `function(argv)` as the script entry point, turning TemplateError into JSON."""
    try:
        sys.exit(function(sys.argv[1:]))
    except TemplateError as exc:
        sys.exit(fail(str(exc)))
    except (OSError, KeyError, ValueError, InvalidFileException, zipfile.BadZipFile) as exc:
        sys.exit(fail(f"{type(exc).__name__}: {exc}"))


def script_dir() -> Path:
    """Directory holding the scripts (for locating sibling files)."""
    return Path(__file__).resolve().parent
