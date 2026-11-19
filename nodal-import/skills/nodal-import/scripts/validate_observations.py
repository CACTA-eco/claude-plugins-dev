#!/usr/bin/env python3
"""Check a filled observation template against the rules the bulk import applies.

Usage: validate_observations.py FILE.xlsx   (JSON report on stdout, exit 1 on errors)

Mirrors core's observation import (`_parse_rows` plus the schema check): each row names its
parcel by campo and lote (looked up in the template's own map, case-insensitive, nothing is
created); each cell is read by its field type (numbers with a decimal point, dates in the
template's date format, closed lists by code or label); required fields, ranges and the
earliest date (2000-01-01) are enforced. Rows that describe the same event are folded by the
import with their quantity summed; they are reported as warnings.

Not checked here, because they depend on the database or on the campaign chosen at upload:
the campaign's date window and closed state, the crop derived from the parcel's harvest and
cover-crop cycles, whether a row creates or repeats a stored observation, and whether a
product outside the tenant's catalog is a platform product.
"""

import json
import re
from datetime import date, datetime
from typing import Any

from common import (
    DATE_PATTERNS,
    CellError,
    Report,
    data_rows,
    is_blank,
    load_template,
    main_guard,
    parse_closed_value,
)

IDS_COLUMN = "_ids"
DECIMAL_COMMA = re.compile(r"^-?\d+,\d+$")
# Required by the schema, but the import fills it in for a perennial crop (campaign start).
DEFAULT_FILLED = {("harvest", "start_date")}


def parse_number(column: dict[str, Any], value: Any, report: Report, row: int) -> float | int:
    """A float or int cell: Python's own number reading, a decimal point, within the range."""
    try:
        number = float(value)
    except (ValueError, TypeError):
        if DECIMAL_COMMA.match(str(value).strip()):
            raise CellError("decimal comma: use a decimal point (10.5, not 10,5)") from None
        raise CellError(f"not a valid number: {value!r}") from None
    if column["type"] == "int":
        if number != int(number):
            report.warning(
                row, column["header"], f"decimal part dropped: {value!r} becomes {int(number)}"
            )
        number = int(number)
    if column.get("min") is not None and number < column["min"]:
        raise CellError(f"{number} is below the minimum allowed ({column['min']})")
    if column.get("max") is not None and number > column["max"]:
        raise CellError(f"{number} is above the maximum allowed ({column['max']})")
    return number


def parse_date(value: Any, date_format: str, min_date: str) -> str:
    """An Excel date cell as is, or text in `date_format` (separators / - . are interchangeable)."""
    if isinstance(value, (datetime, date)):
        parsed = value.date() if isinstance(value, datetime) else value
    else:
        separator = "/" if "/" in date_format else "-"
        text = re.sub(r"[/.\-]", separator, str(value).strip())
        try:
            parsed = datetime.strptime(text, DATE_PATTERNS[date_format]).date()
        except ValueError:
            raise CellError(f"{value!r} is not a valid date: expected {date_format}") from None
    if parsed < date.fromisoformat(min_date):
        raise CellError(f"date {parsed.isoformat()} is before {min_date[:4]}: not allowed")
    return parsed.isoformat()


def parse_bool(value: Any, rules: dict[str, Any], report: Report, row: int, header: str) -> bool:
    """The import reads any text as a bool; unknown words silently become false."""
    word = str(value).strip().lower()
    if word not in rules["bool_true_words"] and word not in rules["bool_false_words"]:
        report.warning(row, header, f"{value!r} is read as 'no': use yes or no")
    return word in rules["bool_true_words"]


def parse_cell(
    column: dict[str, Any], value: Any, meta: dict[str, Any], report: Report, row: int
) -> Any:
    """The parsed value of one non-blank cell, or CellError."""
    kind = column["type"]
    if kind in ("float", "int"):
        return parse_number(column, value, report, row)
    if kind in ("enum", "options", "unit"):
        return parse_closed_value(column, value)
    if kind == "date":
        return parse_date(value, meta["date_format"], meta["min_date"])
    if kind == "bool":
        return parse_bool(value, meta["rules"], report, row, column["header"])
    return str(value).strip()


def check_product(
    report: Report, row: int, column: dict[str, Any], name: str, meta: dict[str, Any]
) -> None:
    """Warn when a product is not in the tenant's catalog (it may still be a platform product)."""
    if name not in meta["catalog_names"].get(column["key"], []):
        report.warning(
            row,
            column["header"],
            f"{name!r} is not in the tenant's catalog: accepted only if it is a platform "
            "product (the import reports it otherwise)",
        )


def resolve_parcel(
    cells: dict[str, Any], meta: dict[str, Any]
) -> tuple[tuple[str, str] | None, str | None]:
    """((campo, lote) key, None) when the row's parcel exists, else (None, why not)."""
    establishment = str(cells.get("_establishment") or "").strip()
    parcel = str(cells.get("_parcel") or "").strip()
    if not establishment or not parcel:
        return None, "the Establishment and Parcel columns are required"
    by_campo = {name.lower(): lotes for name, lotes in meta["parcels_by_establishment"].items()}
    if establishment.lower() not in by_campo:
        return None, f"establishment {establishment!r} does not exist"
    if parcel.lower() not in {lote.lower() for lote in by_campo[establishment.lower()]}:
        return None, f"parcel {parcel!r} does not exist under establishment {establishment!r}"
    return (establishment.lower(), parcel.lower()), None


def check_row(
    report: Report, row: int, cells: dict[str, Any], sheet: dict[str, Any], meta: dict[str, Any]
) -> tuple[dict[str, Any], Any] | None:
    """Validate one row; returns (parsed value, parcel key) when it has no error."""
    failed = False
    node = None
    if sheet["has_parcel_columns"]:
        node, problem = resolve_parcel(cells, meta)
        if problem:
            report.error(row, "Establishment / Parcel", problem)
            failed = True
    value: dict[str, Any] = {}
    for column in sheet["columns"]:
        key = column["key"]
        if key in ("_establishment", "_parcel"):
            continue
        raw = cells.get(key)
        if is_blank(raw):
            if column["required"] and (sheet["dimension"], key) in DEFAULT_FILLED:
                report.warning(
                    row, column["header"], "empty: the import fills it in only for a perennial crop"
                )
            elif column["required"]:
                report.error(row, column["header"], "required, empty")
                failed = True
            continue
        try:
            value[key] = parse_cell(column, raw, meta, report, row)
        except CellError as exc:
            report.error(row, column["header"], str(exc))
            failed = True
            continue
        if column["type"] == "catalog_ref":
            check_product(report, row, column, value[key], meta)
        if column["type"] in ("float", "int") and value[key] < 0:
            report.warning(row, column["header"], f"negative value: {value[key]}")
    return None if failed else (value, node)


def sheet_cells(sheet_ws: Any, sheet: dict[str, Any], report: Report) -> list[tuple[int, dict]]:
    """(row number, {field key: cell}) for each non-empty row; warns on unknown columns."""
    headers = [str(cell.value).strip() if cell.value is not None else "" for cell in sheet_ws[1]]
    by_header = {column["header"]: column["key"] for column in sheet["columns"]}
    by_header.update({column["key"]: column["key"] for column in sheet["columns"]})
    unknown = [h for h in headers if h and h not in by_header and h != IDS_COLUMN]
    rows = []
    for number, values in data_rows(sheet_ws):
        rows.append(
            (
                number,
                {
                    by_header[header]: values[index]
                    for index, header in enumerate(headers)
                    if header in by_header and index < len(values)
                },
            )
        )
        for index, header in enumerate(headers):
            if header in unknown and index < len(values) and not is_blank(values[index]):
                report.warning(number, header, "column is not part of the template: ignored")
    return rows


def fold_same_events(
    report: Report, sheet: dict[str, Any], parsed: list[tuple[int, dict, Any]]
) -> None:
    """Warn about rows the import folds into an earlier one (quantity summed)."""
    quantity = sheet.get("quantity_field")
    if not quantity:
        return
    first: dict[str, int] = {}
    totals: dict[str, float] = {}
    for row, value, node in parsed:
        if value.get(quantity) is None:
            continue
        rest = {key: item for key, item in value.items() if key != quantity}
        group = json.dumps([node, rest], sort_keys=True, default=str)
        totals[group] = totals.get(group, 0) + value[quantity]
        if group in first:
            report.warning(
                row,
                quantity,
                f"same event as row {first[group]}: the import adds the quantities "
                f"(running total {round(totals[group], 6)})",
            )
        else:
            first[group] = row


def validate(path: str) -> Report:
    """Run every observation check on the workbook at `path`."""
    workbook, meta = load_template(path)
    report = Report()
    for sheet in meta["sheets"]:
        if sheet["name"] not in workbook.sheetnames:
            report.error(None, sheet["name"], "sheet missing: do not rename or remove sheets")
            continue
        for column in sheet["columns"]:
            if column["type"] in ("enum", "options", "unit") and "options" not in column:
                report.warning(
                    None,
                    column["header"],
                    "allowed values unavailable when the template was made: not checked",
                )
        parsed = []
        for number, cells in sheet_cells(workbook[sheet["name"]], sheet, report):
            report.rows += 1
            outcome = check_row(report, number, cells, sheet, meta)
            if outcome is not None:
                parsed.append((number, *outcome))
        fold_same_events(report, sheet, parsed)
    return report


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    return validate(argv[0]).emit()


if __name__ == "__main__":
    main_guard(main)
