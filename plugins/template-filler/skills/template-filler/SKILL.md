---
name: template-filler
description: Map a user's source data (CSV, XLSX, PDF, pasted tables) onto a Nodal bulk-import workbook and check it before the user uploads it. Use when the user wants to load, import or convert parcels (lotes) and establishments (campos), catalog entries or observations for the Nodal platform.
---

# Nodal bulk import

You turn the user's data into the platform's bulk-import workbook, and hand it back. You never upload anything: the user uploads the final file in the app.

## What is available

| Entity | Generate tool (MCP) | Reference |
|---|---|---|
| Parcels and establishments (nodes) | `generate_node_bulk_excel` | `references/nodes.md` |
| Catalog entries | `generate_catalog_bulk_excel` | `references/catalogs.md` |
| Observations | `generate_observation_bulk_excel` | `references/observations.md` |

Order of dependencies: nodes first, then catalog entries, then observations (they refer to
parcels and to catalog names). Observations also need the user's
date format and the campaign they will pick at upload: ask before generating (see the reference).

Read the reference file of the entity you are working on before you start.

## Workflow

1. **Get the blank template.** Call the generate tool with no `rows`. The workbook (and, for
   nodes and catalogs, its hidden `_meta` sheet) documents every field: key, type, required
   flag and allowed values. Read it to learn the fields.
2. **Map the data.** Read the user's source yourself. Match each source column to a template
   field. Ask the user instead of guessing when a value has no clear match.
3. **Fill it.** Call the generate tool again with `rows` set to the mapped data (see the entity
   reference for the shape). It returns a short-lived `download_url` and `sha256`; if the
   organization's network blocks the link's domain, call again with `inline=True` to get
   `content_base64`.
4. **Check it.** For observations and catalog entries, validate the generated file with the
   server's dry run: call `request_upload_url`, upload the exact file with
   `curl -X PUT --upload-file <file.xlsx> '<upload_url>'` (no other headers, never re-save it),
   then call `validate_observation_bulk_excel` or `validate_catalog_bulk_excel` with the
   `upload_id` (and the same `date_format` / `locale` as the template). Fix every `error` row,
   regenerate and validate again; mention warnings to the user. If the upload fails, the
   organization's network may block the link's domain (Settings > Capabilities > code execution >
   additional allowed domains): say so and fall back to checking against the rules in the entity
   reference. Parcels (nodes) have no dry run: use the reference rules.
5. **Hand over** the file in `<outputs>`, with a short summary: rows mapped,
   assumptions made, source values you could not map, warnings.

## Where the output goes

`<outputs>` is `/mnt/user-data/outputs` when that directory exists (claude.ai's sandbox, where it
is what reaches the user as an attachment). Anywhere else (Claude Code, a local checkout) use
the current working directory, and tell the user the full path of the file.

## Rules

- Never invent a value to satisfy a required column; ask.
- Do not rename headers, reorder columns or delete sheets, hidden ones included.
- Dates, numbers and list values follow the formats in the entity reference.
- `tenant_id` is never something you pass: the server resolves it from the user's login.
- Validation never writes anything. For nodes, you cannot know what is already stored: whether
  a row will create or update a record is decided by the app at upload time.
