# Catalog entries (fertilizer, seed, machinery, other_input, agrochemical)

One row per catalog entry (a product, machine or input the tenant uses). Observations refer to
these entries by name, so load them before the observations that use them.

Supported types are the `catalog_type` options of `generate_catalog_bulk_excel`. Fuel and
packaging are managed by the platform; recipes, perennial crops and soil tests have no
spreadsheet form.

## Fields

Read them from the template rather than from here: the type's fields differ and tenants can
customise them. Headers are the field keys, so `rows.json` uses the same names. Each field's type,
flags and allowed values are in the template's `_meta` sheet.

Every row needs a `name`. The rest follow these rules:

| Type | Write it as |
|---|---|
| number (float, int) | a number with a **decimal point**. `10,5` is an error |
| closed list (options, unit, enum) | the **code** from the list (for example `tractor`). The file shows its label |
| yes/no (bool) | `true` / `false` or `yes` / `no`. Any other word is read as no |
| date | text `YYYY-MM-DD`, or a year such as `2015` |
| list (array) | a list of strings in `rows.json` |
| text | text |

Percentages are plain numbers (`46`, not `0.46`).

## What to check

Errors (the import would reject the row): unknown column, wrong number format, a value outside a
closed list, a date that is not text in ISO form, a value outside the schema's range, a required
field left empty.

Warnings (the import accepts the row): fields needed for calculations that are still empty,
negative values, a `*_percentage` above 100, nutrient percentages adding above 100, an
unrecognised yes/no word, a name already in the catalog (stored values win and only blank fields
are filled), the same name twice in the file, a list of allowed values that could not be loaded.

Rows without a `name` are skipped by the import and reported as a warning.

## Agrochemical ingredients

Active ingredients are not a column of the Data sheet (putting them there is an error). They go
on the **Active Ingredients** sheet, one row per product and ingredient, and the fill step takes
both sheets in one JSON keyed by sheet name:

```json
{"Data": [{"name": "Roundup", "agrochemical_type": "herbicide", "density": 1.2}],
 "Active Ingredients": [{"product_name": "Roundup", "ingredient_name": "glyphosate",
                        "concentration": 480, "unit": "g/L"}]}
```

`product_name` must equal a `name` on the Data sheet exactly. `ingredient_name` and `unit` are
closed lists (code or label); a blank unit means g/L. The concentration is a number, and a
decimal comma is accepted here.

Errors: a product that is not on the Data sheet (the import would drop
its ingredients silently), an ingredient or unit outside its list (the import rejects the row), a
missing or non-numeric concentration.
Warnings: a product with no ingredients (needed for calculations), the same product and
ingredient twice, a negative concentration, a row missing its product or ingredient (the import
skips it).

## Not checked

- Names that belong to another catalog type, or that match a platform product. The app's preview
  reports these when the user uploads.

## Mapping tips

- Source columns often mix a brand with a product type. Put the commercial name in `name` and
  map the rest onto the fields; ask when a value has no matching code.
- A name must be unique across the whole catalog, not only within its type.
- Nutrient content as "20-10-10" means N, P, K percentages in that order.
