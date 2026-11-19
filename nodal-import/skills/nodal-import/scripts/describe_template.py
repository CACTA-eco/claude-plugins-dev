#!/usr/bin/env python3
"""List a template's fields from its hidden `_meta` sheet, to map data onto.

Usage: describe_template.py FILE.xlsx [--all-options]   (JSON on stdout)

Prints, per data sheet, each column's key, type and flags (required, required_for_calculation,
min, max) and its allowed values (code and label; only the first few unless --all-options),
plus template-wide facts such as the catalog type.
"""

import json
import sys
from typing import Any

from common import load_template, main_guard

PREVIEW_OPTIONS = 12
SKIPPED_FACTS = {
    "version",
    "sheets",
    "existing_names",
    "rules",
    "parcels_by_establishment",
    "catalog_names",
}
SAMPLE_NAMES = 5


def describe_column(column: dict[str, Any], all_options: bool) -> dict[str, Any]:
    """One column, with its option list shortened unless `all_options`."""
    described = {key: value for key, value in column.items() if key != "options"}
    options = column.get("options")
    if options is not None:
        shown = options if all_options else options[:PREVIEW_OPTIONS]
        described["options"] = shown
        described["option_count"] = len(options)
    return described


def describe_names(names: list[str], all_names: bool) -> dict[str, Any]:
    """A count and the first few names (all of them with --all-options)."""
    return {"count": len(names), "names": names if all_names else names[:SAMPLE_NAMES]}


def describe_parcels(by_establishment: dict[str, list[str]], all_names: bool) -> dict[str, Any]:
    """How many campos and lotes the tenant has, and a sample (the whole map with --all-options)."""
    summary = {
        "establishments": len(by_establishment),
        "parcels": sum(len(lotes) for lotes in by_establishment.values()),
    }
    shown = by_establishment if all_names else dict(list(by_establishment.items())[:SAMPLE_NAMES])
    return {**summary, "map": shown}


def describe(path: str, all_options: bool) -> dict[str, Any]:
    """The template facts and per-sheet columns."""
    _, meta = load_template(path)
    facts = {key: value for key, value in meta.items() if key not in SKIPPED_FACTS}
    if "existing_names" in meta:
        facts["existing_names_count"] = len(meta["existing_names"])
    if "parcels_by_establishment" in meta:
        facts["parcels"] = describe_parcels(meta["parcels_by_establishment"], all_options)
    if "catalog_names" in meta:
        facts["catalog_names"] = {
            field: describe_names(names, all_options)
            for field, names in meta["catalog_names"].items()
        }
    facts["sheets"] = [
        {
            "name": sheet["name"],
            "columns": [describe_column(column, all_options) for column in sheet["columns"]],
        }
        for sheet in meta["sheets"]
    ]
    return facts


def main(argv: list[str]) -> int:
    paths = [arg for arg in argv if not arg.startswith("--")]
    if len(paths) != 1:
        print(__doc__)
        return 2
    print(json.dumps(describe(paths[0], "--all-options" in argv), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    main_guard(main)
