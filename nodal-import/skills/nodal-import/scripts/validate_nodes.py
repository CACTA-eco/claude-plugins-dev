#!/usr/bin/env python3
"""Check a filled parcel (lote) template against the rules the import applies.

Usage: validate_nodes.py FILE.xlsx   (JSON report on stdout, exit 1 on errors)

Mirrors backend's structure importer: a row with an empty `nombre` is skipped, `campo` and
`area_ha` are required, `area_ha` must be a number, `lat` / `lon` come together, are numbers
and lie in range. It cannot tell whether a parcel already exists (create vs update).
"""

from typing import Any

from common import Report, data_rows, header_positions, is_blank, load_template, main_guard

LATITUDE_LIMIT = 90
LONGITUDE_LIMIT = 180


def as_number(value: Any, decimal_comma: bool) -> float | None:
    """The value as a float, or None when it is not a number."""
    text = str(value).strip()
    if decimal_comma:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def check_coordinates(report: Report, row: int, lat: Any, lon: Any) -> None:
    """Latitude and longitude: both or neither, numeric, in range."""
    if is_blank(lat) and is_blank(lon):
        return
    if is_blank(lat) or is_blank(lon):
        report.error(row, "lat/lon", "'lat' and 'lon' must be filled in together")
        return
    latitude, longitude = as_number(lat, True), as_number(lon, True)
    if latitude is None or longitude is None:
        report.error(row, "lat/lon", f"not numbers: {lat!r}, {lon!r}")
    elif abs(latitude) > LATITUDE_LIMIT or abs(longitude) > LONGITUDE_LIMIT:
        report.error(row, "lat/lon", f"out of range: {latitude}, {longitude}")


def check_row(report: Report, row: int, cell: dict[str, Any]) -> tuple[str, str] | None:
    """Validate one row; returns the (campo, nombre) identity, or None if the import skips it."""
    if is_blank(cell["nombre"]):
        report.warning(row, "nombre", "no parcel name: the import skips this row")
        return None
    if is_blank(cell["campo"]):
        report.error(row, "campo", "required, empty")
    if is_blank(cell["area_ha"]):
        report.error(row, "area_ha", "required, empty")
    elif as_number(cell["area_ha"], False) is None:
        report.error(row, "area_ha", f"not a number (use a decimal point): {cell['area_ha']!r}")
    check_coordinates(report, row, cell["lat"], cell["lon"])
    return str(cell["campo"] or "").strip().lower(), str(cell["nombre"]).strip().lower()


def validate(path: str) -> Report:
    """Run every node check on the workbook at `path`."""
    workbook, meta = load_template(path)
    sheet_meta = meta["sheets"][0]
    sheet = workbook[sheet_meta["name"]]
    positions = header_positions(sheet, sheet_meta["columns"])
    report = Report()
    for column in sheet_meta["columns"]:
        if column["key"] not in positions:
            report.error(1, column["header"], "header missing: do not rename or remove columns")
    if report.errors:
        return report
    seen: dict[tuple[str, str], int] = {}
    for row, values in data_rows(sheet):
        report.rows += 1
        cell = {
            key: values[index] if index < len(values) else None for key, index in positions.items()
        }
        identity = check_row(report, row, cell)
        if identity is None:
            continue
        if identity in seen:
            report.warning(
                row, "nombre", f"same parcel as row {seen[identity]}: the later row overwrites it"
            )
        seen.setdefault(identity, row)
    return report


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    return validate(argv[0]).emit()


if __name__ == "__main__":
    main_guard(main)
