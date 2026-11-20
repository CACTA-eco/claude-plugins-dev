#!/usr/bin/env python3
"""Write rows into a template's Data sheet without touching its structure.

Usage: fill_template.py TEMPLATE.xlsx ROWS.json OUT.xlsx

ROWS.json is a list of objects keyed by the template's field keys (see the `_meta` sheet,
e.g. nombre, campo, area_ha, or name plus a catalog's fields). For a template with several data sheets, use an object
{"<sheet name>": [rows...]} instead. Rows are appended below any rows already present;
dropdown validations and hidden sheets are kept.
"""

import json
import re
from datetime import date, datetime
from typing import Any

from common import (
    DATE_PATTERNS,
    TemplateError,
    data_rows,
    header_positions,
    load_template,
    main_guard,
)

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def rows_by_sheet(raw: Any, sheet_names: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Normalise ROWS.json to {sheet name: rows}."""
    if isinstance(raw, list):
        if len(sheet_names) != 1:
            raise TemplateError(
                f"this template has {len(sheet_names)} sheets: key rows by sheet name"
            )
        return {sheet_names[0]: raw}
    unknown = set(raw) - set(sheet_names)
    if unknown:
        raise TemplateError(f"unknown sheet(s) {sorted(unknown)}; valid: {sheet_names}")
    return raw


def date_cell(value: Any, date_format: str | None) -> Any:
    """A date or ISO text written in the template's date format; anything else unchanged."""
    if isinstance(value, (date, datetime)):
        parsed = value.date() if isinstance(value, datetime) else value
    elif date_format and isinstance(value, str) and ISO_DATE.match(value.strip()):
        try:
            parsed = date.fromisoformat(value.strip())
        except ValueError:
            return value
    else:
        return value
    return parsed.strftime(DATE_PATTERNS[date_format]) if date_format else parsed.isoformat()


def cell_value(column: dict[str, Any], value: Any, date_format: str | None = None) -> Any:
    """The value as the cell should hold it, so the file reads like one filled in by hand.

    Closed-list values given as a code are written as the label the dropdown shows;
    dates are written as text (an Excel date cell would not be read back as a date);
    booleans as yes / no; lists joined with ";". A template with a `date_format` (observations)
    gets its dates in that format, from a date or an ISO "YYYY-MM-DD" text; otherwise ISO.
    """
    if value is None:
        return None
    labels = {option["code"]: option["label"] for option in column.get("options") or []}
    if isinstance(value, str) and value in labels:
        return labels[value]
    if column["type"] == "date":
        return date_cell(value, date_format)
    if column["type"] == "bool" and isinstance(value, bool):
        return "yes" if value else "no"
    if column["type"] == "array" and isinstance(value, list):
        return ";".join(str(item) for item in value)
    return value


def fill(template: str, rows_path: str, out: str) -> dict[str, int]:
    """Append the rows to each data sheet and save to `out`; returns rows written per sheet."""
    workbook, meta = load_template(template)
    with open(rows_path, encoding="utf-8") as handle:
        raw = json.load(handle)
    by_sheet = rows_by_sheet(raw, [sheet["name"] for sheet in meta["sheets"]])
    written: dict[str, int] = {}
    for sheet_meta in meta["sheets"]:
        rows = by_sheet.get(sheet_meta["name"], [])
        sheet = workbook[sheet_meta["name"]]
        positions = header_positions(sheet, sheet_meta["columns"])
        columns = {column["key"]: column for column in sheet_meta["columns"]}
        valid = set(positions)
        for row in rows:
            if set(row) - valid:
                raise TemplateError(
                    f"unknown field(s) {sorted(set(row) - valid)}; valid: {sorted(valid)}"
                )
        first_free = max((number for number, _ in data_rows(sheet)), default=1) + 1
        for offset, row in enumerate(rows):
            for key, value in row.items():
                sheet.cell(
                    row=first_free + offset,
                    column=positions[key] + 1,
                    value=cell_value(columns[key], value, meta.get("date_format")),
                )
        written[sheet_meta["name"]] = len(rows)
    workbook.save(out)
    return written


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    written = fill(*argv)
    print(json.dumps({"ok": True, "saved": argv[2], "rows_written": written}, indent=2))
    return 0


if __name__ == "__main__":
    main_guard(main)
