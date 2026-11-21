# Parcels (lotes) and establishments (campos)

One row per parcel. Each row creates the parcel and, when needed, its parent establishment.

## Fields (keys for `rows.json`)

| Key | Column header (default) | Meaning | Required |
|---|---|---|---|
| `nombre` | Nombre Parcela | Parcel name. Unique within its campo | yes |
| `campo` | Campo | Establishment name. Created on import if it does not exist | yes |
| `area_ha` | Área (ha) | Area in hectares. A number with a **decimal point**, not a comma | yes |
| `lat` | Latitud (opcional) | Latitude, -90 to 90 | no |
| `lon` | Longitud (opcional) | Longitude, -180 to 180 | no |

`lat` and `lon` come together: both or neither. With them, the platform estimates the parcel's
slope and LS factor after import.

Headers are in Spanish whatever the user's language; the keys above are what you use.

## What to check

- `campo` and `area_ha` present, `area_ha` numeric.
- `lat` / `lon` both filled, numeric (a comma is accepted), in range.
- A row with an empty `nombre` is ignored by the import: reported as a warning.
- The same campo and parcel name twice: warning (the later row overwrites the earlier one).
- Headers unchanged.

You cannot tell whether a parcel or campo already exists.

## Mapping tips

- Source files often call the establishment "finca", "estancia", "establecimiento", "campo"
  or "field", and the parcel "lote", "potrero" or "parcela". Confirm with the user when unsure.
- Areas given in m2 or acres must be converted to hectares; say so in your summary.
- Coordinates in degrees-minutes-seconds must be converted to decimal degrees first.
