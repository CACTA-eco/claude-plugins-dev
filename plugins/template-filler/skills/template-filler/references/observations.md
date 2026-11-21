# Observations (fertiliser, agrochemical, machinery, irrigation, harvest, seed, land use and more)

One row per recorded event on a parcel: a fertiliser application, a harvest, an irrigation. The
dimension is the `dimension` option of `generate_observation_bulk_excel`.

## Ask the user first

1. **Date format.** Pass `date_format` to the generate tool: `DD/MM/YYYY`, `MM/DD/YYYY` or
   `YYYY-MM-DD`. It is the one in the user's profile in the Nodal app, and a file whose dates do not
   match it is rejected at upload. If you do not know it, ask; do not guess.
2. **Campaign.** The campaign (and, for land use, the parcels) is chosen in the app when the user
   uploads. Tell them which campaign the rows belong to, so they pick the right one.

## Fields

The template lists each field's key, type, flags and allowed values. Headers equal the field
keys unless a locale was given; `rows.json` always uses the keys.

Rows go in `rows.json` as a list of objects, or, for `harvest`, as `{"Data": [...],
"Perennial crops": [...], "Cover crops": [...]}` (both companion sheets are part of the harvest
file; the exact sheet names are in the template). Besides the schema fields, every
dimension in the first table below, and the harvest companion sheets, has two parcel columns:

| Key | Meaning |
|---|---|
| `_establishment` | Name of the campo. Must already exist |
| `_parcel` | Name of the lote inside that campo. Must already exist |

Names are matched ignoring case and nothing is created: a parcel that is not on the platform yet
is an error. Load nodes first. `luluc` carries the same two columns, but its `_parcel` may be left
blank: the row then applies to the whole campo.

| Type | Write it as |
|---|---|
| number (float, int) | a number with a **decimal point**. `10,5` is an error |
| closed list (options, unit, enum) | the **code** from the list. The file shows its label |
| yes/no (bool) | `yes` / `no`. Any other word is read as no |
| date | the template's date format, or an ISO `YYYY-MM-DD` text (the fill step converts it). Nothing before 2000 |
| product (catalog_ref) | the product's **name** exactly as in the catalog |

## Per dimension

| Dimension | Required fields | Product column (catalog type) | Crop | Same-event rows add up on | Date |
|---|---|---|---|---|---|
| `fertiliser_use` | fertiliser, amount, amount_unit | `fertiliser` (fertilizer) | derived | `amount` | `application_date` |
| `agrochemical_use` | agrochemical, amount, amount_unit | `agrochemical` (agrochemical) | derived | `amount` | `application_date` |
| `own_machinery_use` | machine, amount, amount_unit | `machine` (machinery) | derived | `amount` | `operation_date` |
| `contracted_machinery_use` | operation_type | none | you write it | none | none |
| `irrigation_event` | irrigation_method, irrigation_water_source, amount, amount_unit | none | derived | `amount` | `event_date` |
| `harvest` | crop, yield_rate, yield_rate_unit, start_date | none | you write it | none | `start_date`, `harvest_date` |
| `harvest`, "Cover crops" sheet | cover_crop | none | n/a | none | `sowing_date`, `termination_date` |
| `seed_use` | seed, rate_unit | `seed` (seed) | you write it | none | none |
| `harvest`, "Perennial crops" sheet | crop, yield_rate, yield_rate_unit | none | you write it | none | `harvest_date` |
| `luluc` | year, prev/next land type, prev/next category | none | n/a | none | none |
| `irrigation_season` | irrigation_method, irrigation_water_source, amount, amount_unit, frequency | none | optional `crop` | none | `from_date`, `to_date` |
| `electricity_use` | electricity_source, amount, amount_unit | none | optional `crop` | none | `date` |
| `other_consumables` | other_supply_input, amount, unit | none | none | none | none |
| `others` | input, amount, unit | none | optional `crop` | none | none |
| `perennial_planting` | perennial_crop | `perennial_crop` (perennial_crop) | n/a | none | none |
| `regenerative_practice` | practice_type | none | none | none | none |

The template is authoritative: tenants can change their schemas.

- **Derived crop.** The import sets `crop` from the parcel's harvest and cover-crop cycles that
  contain the date; a date in several cycles splits the quantity between them by area. Without
  cycles stored for that campaign the crop stays empty. So load harvests and cover crops before
  the dated operations, and never put `crop` in those rows.
- **Hidden fields.** `packaging_disposal_method` (fertiliser, agrochemical, seed) is filled in by
  the import. Do not write it.
- **No parcel columns** for `irrigation_season`, `electricity_use`, `other_consumables`,
  `others`, `perennial_planting` and `regenerative_practice`: the user picks the parcels or nodes in
  the app at upload, and the rows carry no campo or lote. Do not add them. `crop`, where offered,
  is written by you and is optional.
- **Perennial crops sheet.** A perennial crop goes on that sheet, any other crop on the main
  harvest sheet. The sheet has no `start_date`, tillage or residue fields: the import starts the
  cycle with the campaign.
- **Harvest `start_date`** may be left empty only for a perennial crop (the import uses the
  campaign start); otherwise the row is rejected, and a missing one is easy to overlook.

## What to check

Errors: missing or unknown campo or lote (or a lote that is not in that campo), a date that does
not fit the date format or is before 2000, a decimal comma or non-numeric value, a value outside a
closed list, a required field left empty, a value outside the field's range, a removed sheet.

Warnings: negative values, an unrecognised yes/no word, a column that is not part of the template
(ignored by the import), an unavailable option list, a product that is not in the tenant's catalog
(fine only if it is a platform product), and rows that describe the same event: the import folds
them into the first one with the quantities added, and the warning shows the running total.

## Not checked

You have no database access, so these are decided at upload and shown in the app's
preview:

- the campaign's date window and whether it is closed;
- the crop derived from the parcel's cycles;
- whether a row creates a new observation or repeats a stored one;
- whether a product outside the catalog is a platform product.

## Mapping tips

- Source columns for the area or the rate often use other units (kg/ha, L/ha, t). Map each to the
  unit codes of the template and convert the number if the unit is not offered.
- Several products applied the same day on the same parcel are separate rows; the same product
  reported in instalments is folded by the import, which is expected.
- A "date applied" column becomes the dimension's date field. A season or year column is not a
  date: ask the user which campaign it belongs to instead.
- Product names must match the catalog: load catalog entries first, and use the names exactly.
