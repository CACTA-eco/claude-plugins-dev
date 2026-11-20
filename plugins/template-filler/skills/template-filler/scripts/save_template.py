#!/usr/bin/env python3
"""Save a template workbook from the generate tool's result and verify it byte for byte.

The generate tools return a short-lived `download_url` plus the file's SHA-256. Preferred:

Download:    save_template.py --out FILE --sha256 HEX --url URL
             fetches the exact bytes, compares the hash, writes the file, checks it opens.

If the download is blocked (exit 4, "download failed"), call the tool again with
`inline=True` to get `content_base64`, and pipe the base64 in instead:

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
import urllib.error
import urllib.request
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
    return save_verified(data, expected_sha, out, result)


def download(url: str, expected_sha: str, out: Path, timeout: float = 60) -> dict:
    """Fetch `url`, verify the hash, write `out` and confirm it opens."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            data = response.read()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {
            "ok": False,
            "download_failed": True,
            "error": f"download failed ({exc}); the network may block this domain: "
            "call the tool again with inline=True and save the base64 instead",
        }
    return save_verified(data, expected_sha, out, {"ok": False, "downloaded_bytes": len(data)})


def save_verified(data: bytes, expected_sha: str, out: Path, result: dict) -> dict:
    """Check `data` against the hash, write it to `out` and confirm the workbook opens."""
    actual = hashlib.sha256(data).hexdigest()
    result["sha256_actual"] = actual
    if actual != expected_sha:
        return {**result, "error": "sha256 mismatch: the file differs from the original; fetch or resend it"}
    out.parent.mkdir(parents=True, exist_ok=True)
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
    parser.add_argument("--url", help="download_url from the tool result (preferred)")
    parser.add_argument("--part", type=int)
    parser.add_argument("--of", type=int)
    args = parser.parse_args()
    out = Path(args.out)
    if args.url:
        result = download(args.url, args.sha256, out)
        print(json.dumps(result, indent=2))
        if result["ok"]:
            return 0
        return 4 if result.get("download_failed") else 1
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
