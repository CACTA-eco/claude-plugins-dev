---
name: nodal-import
description: Map a user's source data (CSV, XLSX, PDF, pasted tables) onto a Nodal bulk-import workbook and check it before the user uploads it. Use when the user wants to load, import or convert parcels (lotes) and establishments (campos), catalog entries or observations for the Nodal platform.
---

# Nodal bulk import

You turn the user's data into the platform's bulk-import workbook, check it with the scripts
here, and hand it back. You never upload anything: the user uploads the final file in the app.

## What is available

| Entity | Generate tool (MCP) | Local check | Reference |
|---|---|---|---|
| Parcels and establishments (nodes) | `generate_node_bulk_excel` | `scripts/validate_nodes.py` | `references/nodes.md` |
| Catalog entries | `generate_catalog_bulk_excel` | `scripts/validate_catalogs.py` | `references/catalogs.md` |
| Observations | `generate_observation_bulk_excel` | `scripts/validate_observations.py` | `references/observations.md` |

Order of dependencies: nodes first, then catalog entries, then observations (they refer to
parcels and to catalog names). Observations also need the user's
date format and the campaign they will pick at upload: ask before generating (see the reference).

Read the reference file of the entity you are working on before you start.

## Workflow

1. **Get the blank template.** Call the generate tool with no `rows`. It returns
   `content_base64` and `sha256`. The workbook carries a hidden `_meta` sheet the scripts rely
   on: never convert, re-save or rebuild the file with anything but these scripts.
2. **Save it in the sandbox.** Run `python3 scripts/save_template.py --out /tmp/template.xlsx
   --sha256 <sha256>` and write the base64 text yourself as a heredoc on stdin. Copy it exactly.
   A mismatch is reported and nothing is written: resend. If the result looks cut off, or
   `content_base64` is over about 20,000 characters, or a single copy fails once, send it in
   parts of about 5,000 characters (`--part 1 --of 4`, and so on); the file is built after the
   last part arrives. Never copy from a result you only saw partly.
3. **Map the data.** Run `python3 scripts/describe_template.py /tmp/template.xlsx` to see the
   template's fields, types and allowed values. Read the user's source yourself. Match each source column to a template
   field. Ask the user instead of guessing when a value has no clear match.
4. **Fill it.** Write the mapped rows to `rows.json` (a list of objects keyed by field key, see the
   entity reference) and run `python3 scripts/fill_template.py /tmp/template.xlsx rows.json
   /mnt/user-data/outputs/<name>.xlsx`.
5. **Check it.** Run the entity's validate script on that file. It prints JSON and exits 1 when
   there are errors: fix the data, refill from the blank template, and check again until
   `"ok": true`. Warnings do not block, but mention them to the user.
6. **Hand over** the file in `/mnt/user-data/outputs`, with a short summary: rows mapped,
   assumptions made, source values you could not map, warnings.

## Rules

- Never invent a value to satisfy a required column; ask.
- Do not rename headers, reorder columns or delete sheets, hidden ones included.
- Dates, numbers and list values follow the formats in the entity reference.
- A generated template can be long: for observations expect the chunked save in step 2.
- `tenant_id` is never something you pass: the server resolves it from the user's login.
- The local check cannot know what is already stored. Whether a row will create or update a
  record is decided by the app at upload time, and the user sees it in the app's preview.
