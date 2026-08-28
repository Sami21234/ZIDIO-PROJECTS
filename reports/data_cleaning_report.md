# Data Cleaning Report
**Project FORESIGHT — NorthBay Living** · Deliverable D1 support document

This report documents the raw-data inspection findings and each cleaning decision made,
with before/after evidence, per the brief's D1 requirement that *"cleaning steps are
coded, not manual"* and *"documented with their rationale."* The corresponding automated
code lives in `src/pipeline.py`.

---

## 1. Raw data profile (before any cleaning)

| Check | Result |
|---|---|
| Shape | 1,067,371 rows × 8 columns |
| `InvoiceDate` datatype | Loaded as text (`object`), not a real date — required conversion |
| `Customer ID` datatype | `float64`, not whole-number, because missing values force pandas to use decimals |
| Missing `Description` | 4,382 rows |
| Missing `Customer ID` | 243,007 rows (~23%) — not used in this project, left as-is |
| Fully duplicated rows | 34,335 |
| Unique invoices / products / countries | 53,628 / 5,305 / 43 |
| `Quantity` range | -80,995 to 80,995 |
| `Price` range | **-53,594.36** to 38,970.00 |
| Negative `Quantity` rows | 22,950 |
| `Price <= 0` rows | 6,207 |
| Cancellation invoices (start with 'C') | 19,494 |

The negative `Quantity` extreme and the negative `Price` extreme both turned out to trace
back to non-product administrative codes (see Fix 7) rather than real product sales.

---

## 2. Cleaning steps, in order, with before/after evidence

| # | Fix | Rows removed | Rationale |
|---|---|---|---|
| 1 | Convert `InvoiceDate` to real datetime | 0 (type fix, not a row removal) | Needed for any date math (sorting, month/week extraction, date ranges) |
| 2 | Drop rows with missing `Description` | small subset of 4,382 nulls | Product category assignment depends on reading the description text; unusable without it |
| 3 | Drop fully duplicated rows | 34,335 | Exact repeats would double-count real sales in every downstream aggregation |
| 4 | Drop cancellation invoices (`Invoice` starts with 'C') | 19,494 | A cancellation reverses a sale — keeping it would let it wrongly offset the real sale it cancels |
| 5 | Drop `Quantity <= 0` or `Price <= 0` | subset of the 22,950 / 6,207 found above | Non-positive values represent returns, adjustments, or data errors — not real sales |
| 6 | Drop near-zero "giveaway" prices (`Price < £0.01`) | 18 | e.g. `PADS` at £0.001 — technically positive so Fix 5 doesn't catch it, but rounds to £0.00 later and produces a nonsensical zero-price sales row. Found via a deeper notebook check, not anticipated upfront |
| 7 | Drop non-product administrative stock codes (`POST`, `DOT`, `D`, `M`, `C2`, `BANK CHARGES`, `AMAZONFEE`, `CRUK`, `ADJUST`, `B`, `S`, `GIFT`, etc.) | 4,571 | Bookkeeping entries (postage, fees, manual adjustments, discounts) mixed into the same column as real products — would appear as fake "SKUs" with no genuine demand pattern otherwise |

**Net result:** 1,067,371 raw rows → **1,003,417 rows** after all cleaning steps (roughly 6.0% removed).

---

## 3. Post-cleaning validation

Re-checked on the cleaned/processed output (`data/processed/sales_daily.csv`):

- Nulls: 0 across all columns
- Duplicate (date, sku_id) pairs: 0
- `units_sold < 0`: 0 · `revenue < 0`: 0 · `unit_price <= 0`: 0
- Result: 4,731 SKUs, 739 calendar days, 529,935 sales_daily rows, 319,574 inventory snapshot rows

This confirms the cleaning logic actually worked as intended, not just that it ran without errors.

---

## 4. Known, documented assumptions carried forward

These aren't cleaning fixes but estimates required because the source data lacks certain
fields entirely — flagged here for transparency (see `src/pipeline.py` docstring for full detail):

- **`unit_cost`**: not in source data; estimated from list price using an assumed category-level gross margin (45–55%)
- **`inventory_snapshots`**: entirely simulated via an (s, S) reorder policy, since the source data has no stock-level information at all
- **`promo_flag`**: inferred from a ≥15% rolling-median price drop, since the source data has no explicit promotion field
- **`category` / `subcategory`**: derived from keyword matching on free-text `Description`, since the source data has no product hierarchy
