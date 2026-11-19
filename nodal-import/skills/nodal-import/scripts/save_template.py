#!/usr/bin/env python3
"""Rebuild a template workbook from base64 text and verify it byte for byte.

The generate tools return the file as base64 plus its SHA-256. Pipe the base64 in; the
script decodes it, compares the hash, writes the file and checks that it opens.

One piece:   save_template.py --out FILE --sha256 HEX      < base64
In chunks:   save_template.py --out FILE --sha256 HEX --part 1 --of 3 < first third
             ... --part 2 --of 3, --part 3 --of 3: after the last part the file is built.
Chunks are the fallback when a single long paste is unreliable (a few thousand characters
each). Parts may arrive in any order; resend a part to replace it.
"""

import argparse
import base64
import binascii
import hashlib
import json
import sys
from pathlib import Path

import openpyxl


def part_path(out: Path, part: int) -> Path:
    return out.with_name(f"{out.name}.part{part}")


def assemble(text: str, expected_sha: str, out: Path) -> dict:
    """Decode `text`, verify the hash, write `out` and confirm it opens."""
    result: dict = {"ok": False, "copied_chars": len(text)}
    try:
        data = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError) as exc:
        return {**result, "error": f"not valid base64: {exc}"}
    actual = hashlib.sha256(data).hexdigest()
    result["sha256_actual"] = actual
    if actual != expected_sha:
        return {**result, "error": "sha256 mismatch: the copy differs from the original; resend it"}
    out.write_bytes(data)
    try:
        result["sheets"] = openpyxl.load_workbook(out).sheetnames
    except Exception as exc:  # noqa: BLE001 - report any open failure to the caller
        return {**result, "error": f"decoded but cannot be opened: {exc}"}
    return {**result, "ok": True, "saved": str(out), "bytes": len(data)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--part", type=int)
    parser.add_argument("--of", type=int)
    args = parser.parse_args()
    out = Path(args.out)
    text = "".join(sys.stdin.read().split())

    if args.part is None:
        result = assemble(text, args.sha256, out)
    else:
        if not args.of or not 1 <= args.part <= args.of:
            print(json.dumps({"ok": False, "error": "--part needs --of N with 1 <= part <= N"}))
            return 2
        part_path(out, args.part).write_text(text)
        missing = [i for i in range(1, args.of + 1) if not part_path(out, i).exists()]
        if missing:
            print(
                json.dumps({"ok": False, "waiting_for_parts": missing, "stored_chars": len(text)})
            )
            return 3
        result = assemble(
            "".join(part_path(out, i).read_text() for i in range(1, args.of + 1)), args.sha256, out
        )
        if result["ok"]:
            for i in range(1, args.of + 1):
                part_path(out, i).unlink()
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
