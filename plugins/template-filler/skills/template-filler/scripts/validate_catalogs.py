#!/usr/bin/env python3
"""Check a filled catalog template against the rules the import applies.

Usage: validate_catalogs.py FILE.xlsx   (JSON report on stdout, exit 1 on errors)

Mirrors backend's catalog import and preview: a row without a `name` is skipped; each cell is
read by its field type (numbers with a decimal point, closed lists by code or label, dates as
text); the schema's required fields, ranges and unknown columns are enforced. Warnings never
block: fields needed for a calculation, implausible values, names already in the catalog.
Agrochemicals also have an "Active Ingredients" sheet (one row per product and ingredient),
checked here too. It cannot tell whether a name belongs to another catalog type or to the platform's own
products; the app's preview at upload time reports those.
"""

import re
from datetime import date, datetime
from typing import Any

from common import (
    CellError,
    Report,
    data_rows,
    header_positions,
    is_blank,
    load_template,
    main_guard,
    parse_closed_value,
)

DECIMAL_COMMA = re.compile(r"^-?\d+,\d+$")
YEAR_ONLY = re.compile(r"^\d{4}$")
CLOSED_LIST_TYPES = ("enum", "options", "unit")


def parse_number(column: dict[str, Any], value: Any, report: Report, row: int) -> float | int:
    """A float or int cell: decimal point only, within the schema's range."""
    if DECIMAL_COMMA.match(str(value).strip()):
        raise CellError("decimal comma: use a decimal point (10.5, not 10,5)")
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise CellError(f"not a valid number: {value!r}") from None
    if column["type"] == "int":
        if number != int(number):
            report.warning(
                row,
                column["header"],
                f"decimal part dropped: {value!r} becomes {int(number)}",
            )
        number = int(number)
    if column.get("min") is not None and number < column["min"]:
        raise CellError(f"{number} is below the minimum allowed ({column['min']})")
    if column.get("max") is not None and number > column["max"]:
        raise CellError(f"{number} is above the maximum allowed ({column['max']})")
    return number


def parse_date(value: Any) -> str:
    """Dates are text: YYYY-MM-DD or a bare year; an Excel date cell is not read back."""
    if isinstance(value, (date, datetime)):
        raise CellError("write the date as text YYYY-MM-DD, not as an Excel date cell")
    text = str(value).strip()
    if YEAR_ONLY.match(text):
        return text
    try:
        date.fromisoformat(text)
    except ValueError:
        raise CellError(f"not a valid date (use YYYY-MM-DD or a year): {text!r}") from None
    return text


def parse_bool(value: Any, rules: dict[str, Any], report: Report, row: int, header: str) -> bool:
    """The import reads any text as a bool; unknown words silently become false."""
    word = str(value).strip().lower()
    if word not in rules["bool_true_words"] and word not in rules["bool_false_words"]:
        report.warning(row, header, f"{value!r} is read as 'no': use yes or no")
    return word in rules["bool_true_words"]


def parse_cell(
    column: dict[str, Any], value: Any, rules: dict[str, Any], report: Report, row: int
) -> Any:
    """The parsed value of one non-blank cell, or CellError."""
    kind = column["type"]
    if kind in ("float", "int"):
        return parse_number(column, value, report, row)
    if kind in CLOSED_LIST_TYPES:
        return parse_closed_value(column, value)
    if kind == "date":
        return parse_date(value)
    if kind == "bool":
        return parse_bool(value, rules, report, row, column["header"])
    if kind == "array":
        return [part.strip() for part in str(value).split(";") if part.strip()]
    if kind == "catalog_ref":
        raise CellError("catalog_ref columns cannot be filled from a spreadsheet")
    return str(value).strip()


def check_plausibility(
    report: Report,
    row: int,
    attrs: dict[str, Any],
    columns: dict[str, dict[str, Any]],
    rules: dict[str, Any],
) -> None:
    """Warn about values that look wrong on their face (same rules as the import's review)."""
    for key, value in attrs.items():
        if columns[key]["type"] not in ("float", "int") or not isinstance(value, (int, float)):
            continue
        if value < 0:
            report.warning(row, columns[key]["header"], f"negative value: {value}")
        elif key.endswith("_percentage") and value > rules["percentage_max"]:
            report.warning(
                row,
                columns[key]["header"],
                f"{value} is above {rules['percentage_max']}%",
            )
    fields = rules["nutrient_sum_fields"]
    total = sum(attrs[field] for field in fields if isinstance(attrs.get(field), (int, float)))
    if fields and total > rules["percentage_max"]:
        report.warning(
            row,
            None,
            f"nutrient percentages add up to {total}, above {rules['percentage_max']}",
        )


def check_row(
    report: Report,
    row: int,
    cells: dict[str, Any],
    columns: dict[str, dict[str, Any]],
    rules: dict[str, Any],
) -> str | None:
    """Validate one row; returns its name, or None when the import skips the row."""
    by_header = {column["header"]: column for column in columns.values()}
    name = str(cells.get(columns["name"]["header"]) or "").strip()
    if not name:
        report.warning(row, "name", "no name: the import skips this row")
        return None
    attrs: dict[str, Any] = {}
    for header, value in cells.items():
        column = by_header.get(header)
        if header == columns["name"]["header"] or is_blank(value):
            continue
        if column is None:
            report.error(row, header, "column is not part of the template")
            continue
        try:
            attrs[column["key"]] = parse_cell(column, value, rules, report, row)
        except CellError as exc:
            report.error(row, header, str(exc))
    for key, column in columns.items():
        if column["required"] and key != "name" and is_blank(cells.get(column["header"])):
            report.error(row, column["header"], "required, empty")
    missing = [
        key
        for key, column in columns.items()
        if column.get("required_for_calculation") and key not in attrs
    ]
    if missing:
        report.warning(row, None, f"needed for calculations, still empty: {', '.join(missing)}")
    check_plausibility(report, row, attrs, columns, rules)
    return name


INGREDIENTS_SHEET = "Active Ingredients"


def ingredient_cells(sheet: Any, columns: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    """(row number, {field key: cell value}) for each non-empty row of the ingredients sheet."""
    positions = header_positions(sheet, columns)
    return [
        (
            row,
            {
                key: values[index] if index < len(values) else None
                for key, index in positions.items()
            },
        )
        for row, values in data_rows(sheet)
    ]


def check_ingredient_row(
    report: Report, row: int, cells: dict[str, Any], columns: dict[str, dict[str, Any]]
) -> tuple[str, str] | None:
    """Validate one ingredients row; returns (product, ingredient) when the import keeps it."""
    product = str(cells.get("product_name") or "").strip()
    ingredient = str(cells.get("ingredient_name") or "").strip()
    if not product or not ingredient:
        report.warning(
            row,
            INGREDIENTS_SHEET,
            "needs a product_name and an ingredient_name: the import skips it",
        )
        return None
    try:
        parse_closed_value(columns["ingredient_name"], ingredient)
    except CellError as exc:
        report.error(
            row,
            "ingredient_name",
            f"{exc}; a label in another language may also be read",
        )
    if not is_blank(cells.get("unit")):
        try:
            parse_closed_value(columns["unit"], cells["unit"])
        except CellError as exc:
            report.error(row, "unit", str(exc))
    concentration = str(cells.get("concentration") or "").strip().replace(",", ".")
    try:
        if float(concentration) < 0:
            report.warning(row, "concentration", f"negative value: {concentration}")
    except ValueError:
        report.error(row, "concentration", f"not a valid number: {cells.get('concentration')!r}")
    return product, ingredient


def check_ingredients(
    sheet: Any, sheet_meta: dict[str, Any], names: dict[str, int], report: Report
) -> None:
    """Check the ingredients sheet against the Data sheet's product names."""
    columns = {column["key"]: column for column in sheet_meta["columns"]}
    for column in columns.values():
        if column["type"] in CLOSED_LIST_TYPES and "options" not in column:
            report.warning(
                None,
                column["header"],
                "allowed values unavailable when the template was made: not checked",
            )
    listed: dict[tuple[str, str], int] = {}
    products: set[str] = set()
    for row, cells in ingredient_cells(sheet, sheet_meta["columns"]):
        kept = check_ingredient_row(report, row, cells, columns)
        if kept is None:
            continue
        product, _ = kept
        products.add(product)
        if product not in names:
            report.error(
                row,
                "product_name",
                f"{product!r} is not a name on the Data sheet: the import drops these ingredients",
            )
        if kept in listed:
            report.warning(
                row,
                "ingredient_name",
                f"same product and ingredient as row {listed[kept]}",
            )
        listed.setdefault(kept, row)
    for name, row in names.items():
        if name not in products:
            report.warning(row, "name", "no ingredients listed: needed for calculations")


def validate(path: str) -> Report:
    """Run every catalog check on the workbook at `path`."""
    workbook, meta = load_template(path)
    sheet_meta = meta["sheets"][0]
    sheet = workbook[sheet_meta["name"]]
    columns = {column["key"]: column for column in sheet_meta["columns"]}
    headers = [str(cell.value).strip() if cell.value is not None else "" for cell in sheet[1]]
    report = Report()
    if columns["name"]["header"] not in headers:
        report.error(
            1,
            columns["name"]["header"],
            "header missing: do not rename or remove columns",
        )
        return report
    for column in columns.values():
        if column["type"] in CLOSED_LIST_TYPES and "options" not in column:
            report.warning(
                None,
                column["header"],
                "allowed values unavailable when the template was made: not checked",
            )
    existing, seen = set(meta.get("existing_names", [])), {}
    for row, values in data_rows(sheet):
        report.rows += 1
        cells = {
            header: values[index] if index < len(values) else None
            for index, header in enumerate(headers)
            if header
        }
        name = check_row(report, row, cells, columns, meta["rules"])
        if name is None:
            continue
        if name in existing:
            report.warning(
                row,
                "name",
                "already in the catalog: stored values win, only blank fields are filled",
            )
        if name in seen:
            report.warning(
                row,
                "name",
                f"same name as row {seen[name]}: the later row only fills blank fields",
            )
        seen.setdefault(name, row)
    if len(meta["sheets"]) > 1:
        if INGREDIENTS_SHEET in workbook.sheetnames:
            check_ingredients(workbook[INGREDIENTS_SHEET], meta["sheets"][1], seen, report)
        else:
            report.error(None, INGREDIENTS_SHEET, "sheet missing: do not remove sheets")
    return report


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    return validate(argv[0]).emit()


if __name__ == "__main__":
    main_guard(main)
