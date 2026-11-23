# Mapping: date reference

Grain: one distinct date represented by accepted observations. Primary key: `date_id`.

| Target | Source | Rule |
| --- | --- | --- |
| date_id | parsed source date | Assign an auto-incrementing integer ID in the initial database. Retain the database; incremental ID reuse is not implemented. |
| calendar_date | `date` | Require a valid ISO calendar date and preserve its value. |
| year, quarter, month, day | calendar_date | Derive calendar attributes. |

Dates represented in the dataset do not establish an authoritative exchange trading calendar or prove that every expected stock observation is present.
